import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

import async_stm_api
from async_stm_api import (
    FILTER_SLICE_SIZE,
    STREAM_READ_SIZE,
    MetroAlertStreamFilter,
    fetch_service_status_async,
    _read_chunked,
)


def alert(route, text="Service normal du métro", stop_code=None):
    entity = {"route_short_name": route}
    if stop_code is not None:
        entity["stop_code"] = stop_code
    return {
        "informed_entities": [entity],
        "description_texts": [{"language": "fr", "text": text}],
    }


class FakeChunkedReader:
    def __init__(self, body):
        self.body = body
        self.position = 0
        self.lines = [
            "{:x}\r\n".format(len(body)).encode(),
            b"0\r\n",
            b"\r\n",
        ]
        self.max_read = 0

    async def readline(self):
        return self.lines.pop(0)

    async def read(self, size):
        self.max_read = max(self.max_read, size)
        chunk = self.body[self.position:self.position + size]
        self.position += len(chunk)
        return chunk

    async def readexactly(self, size):
        if size == 2 and self.position == len(self.body):
            return b"\r\n"
        raise AssertionError("Lecture exacte inattendue: {}".format(size))


class FakeHttpReader:
    def __init__(self, status, headers=(), body=b""):
        self.lines = [status] + list(headers) + [b"\r\n"]
        self.body = body
        self.position = 0

    async def readline(self):
        return self.lines.pop(0)

    async def read(self, size):
        chunk = self.body[self.position:self.position + size]
        self.position += len(chunk)
        return chunk


class FakeHttpWriter:
    def __init__(self):
        self.data = bytearray()

    def write(self, data):
        self.data.extend(data)

    async def drain(self):
        return None

    def close(self):
        return None

    async def wait_closed(self):
        return None


class MetroAlertStreamFilterTests(unittest.TestCase):
    def test_filter_keeps_only_metro_alerts_across_tiny_chunks(self):
        payload = {
            "header": {"timestamp": 1},
            "alerts": [
                alert("24", "Autobus détourné"),
                alert("2", "Service normal du métro"),
                alert("5", "Interruption de service"),
            ],
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        stream_filter = MetroAlertStreamFilter()

        for byte in body:
            stream_filter.feed(bytes((byte,)))

        result = stream_filter.result()
        routes = [
            item["informed_entities"][0]["route_short_name"]
            for item in result["alerts"]
        ]
        self.assertEqual(routes, ["2", "5"])

    def test_filter_accepts_whitespace_around_route_value(self):
        body = (
            b'{"alerts": [{"informed_entities": ['
            b'{"route_short_name" : "4"}]}]}'
        )
        stream_filter = MetroAlertStreamFilter()
        stream_filter.feed(body)
        result = stream_filter.result()
        self.assertEqual(len(result["alerts"]), 1)

    def test_chunked_reader_never_allocates_the_transport_chunk(self):
        # Simule une grosse réponse STM dans un seul chunk HTTP de plus de
        # 80 Ko. Le lecteur doit toujours la traiter par blocs de 1 Ko.
        alerts = [alert("24", "Autobus détourné")] * 1200
        alerts.append(alert("1", "Service normal du métro"))
        body = json.dumps(
            {"header": {}, "alerts": alerts},
            separators=(",", ":"),
        ).encode()
        self.assertGreater(len(body), 81920)

        reader = FakeChunkedReader(body)
        stream_filter = MetroAlertStreamFilter()
        asyncio.run(_read_chunked(reader, stream_filter))

        result = stream_filter.result()
        self.assertLessEqual(reader.max_read, STREAM_READ_SIZE)
        self.assertEqual(len(result["alerts"]), 1)

    def test_large_buffered_response_yields_to_the_animation(self):
        alerts = [alert("24", "Autobus détourné")] * 300
        alerts.append(alert("2", "Service normal du métro"))
        body = json.dumps(
            {"alerts": alerts},
            separators=(",", ":"),
        ).encode()

        async def scenario():
            running = True
            heartbeat_count = 0

            async def heartbeat():
                nonlocal heartbeat_count
                while running:
                    heartbeat_count += 1
                    await asyncio.sleep(0)

            heartbeat_task = asyncio.create_task(heartbeat())
            stream_filter = MetroAlertStreamFilter()
            await _read_chunked(FakeChunkedReader(body), stream_filter)
            running = False
            await heartbeat_task
            return heartbeat_count, stream_filter.result()

        heartbeat_count, result = asyncio.run(scenario())
        self.assertGreater(
            heartbeat_count,
            len(body) // (FILTER_SLICE_SIZE * 2),
        )
        self.assertEqual(len(result["alerts"]), 1)

    def test_etag_turns_an_unchanged_refresh_into_a_small_304(self):
        body = json.dumps(
            {"alerts": [alert("2")]},
            separators=(",", ":"),
        ).encode()
        readers = [
            FakeHttpReader(
                b"HTTP/1.1 200 OK\r\n",
                (
                    b'ETag: W/"metro-1"\r\n',
                    "Content-Length: {}\r\n".format(len(body)).encode(),
                ),
                body,
            ),
            FakeHttpReader(b"HTTP/1.1 304 Not Modified\r\n"),
        ]
        writers = [FakeHttpWriter(), FakeHttpWriter()]

        async def fake_connection(*args, **kwargs):
            return readers.pop(0), writers[len(writers) - len(readers) - 1]

        async def scenario():
            async_stm_api._STM_ETAG = None
            with patch.object(
                async_stm_api.asyncio,
                "open_connection",
                new=fake_connection,
            ):
                first = await fetch_service_status_async("test-key")
                second = await fetch_service_status_async("test-key")
            return first, second

        first, second = asyncio.run(scenario())
        self.assertEqual(len(first["alerts"]), 1)
        self.assertIsNone(second)
        self.assertNotIn(b"If-None-Match", writers[0].data)
        self.assertIn(b'If-None-Match: W/"metro-1"', writers[1].data)


if __name__ == "__main__":
    unittest.main()
