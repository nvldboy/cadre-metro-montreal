"""Client HTTPS asynchrone minimal pour l'état du service STM."""

import json
import socket

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

STM_HOST = "api.stm.info"
STM_PATH = "/pub/od/i3/v2/messages/etatservice"
STM_CONNECT_HOST = STM_HOST
_STM_ETAG = None
# Des blocs de 4 ko réduisent fortement le nombre d'attentes réseau tout en
# restant modestes pour la mémoire disponible du Pico 2 W.
STREAM_READ_SIZE = 4096
# Le filtre JSON est volontairement découpé plus finement que la lecture
# réseau. Sur le Pico, analyser 4 ko octet par octet peut prendre plusieurs
# centaines de millisecondes; rendre la main tous les 256 octets maintient
# l'affichage fluide pendant la grosse réponse STM.
FILTER_SLICE_SIZE = 256
MAX_ALERT_BYTES = 8192

_ALERTS_TOKEN = b'"alerts"'
_ROUTE_TOKEN = b'"route_short_name"'
_METRO_ROUTE_BYTES = (49, 50, 52, 53)  # 1, 2, 4 et 5


class AsyncStmApiError(Exception):
    pass


async def _yield_to_animation():
    """Laisse les tâches DEL s'exécuter pendant le filtrage de la réponse."""
    sleep_ms = getattr(asyncio, "sleep_ms", None)
    if sleep_ms is not None:
        await sleep_ms(0)
    else:
        await asyncio.sleep(0)


async def _feed_stream_data(stream_filter, data):
    view = memoryview(data)
    for offset in range(0, len(data), FILTER_SLICE_SIZE):
        stream_filter.feed(view[offset:offset + FILTER_SLICE_SIZE])
        await _yield_to_animation()


class MetroAlertStreamFilter:
    """Extrait les seules alertes métro sans conserver la réponse complète."""

    SEARCH_ALERTS = 0
    WAIT_COLON = 1
    WAIT_ARRAY = 2
    READ_ARRAY = 3

    def __init__(self):
        self.state = self.SEARCH_ALERTS
        self.token_index = 0
        self.alert_buffer = bytearray(MAX_ALERT_BYTES)
        self.alert_length = 0
        self.reading_alert = False
        self.depth = 0
        self.in_string = False
        self.escaped = False
        self.alerts = []
        self.finished = False

    def _search_token(self, byte):
        expected = _ALERTS_TOKEN[self.token_index]
        if byte == expected:
            self.token_index += 1
            if self.token_index == len(_ALERTS_TOKEN):
                self.state = self.WAIT_COLON
                self.token_index = 0
        else:
            self.token_index = 1 if byte == _ALERTS_TOKEN[0] else 0

    def _contains_metro_route(self):
        start = 0
        while True:
            index = self.alert_buffer.find(
                _ROUTE_TOKEN,
                start,
                self.alert_length,
            )
            if index < 0:
                return False
            position = index + len(_ROUTE_TOKEN)
            while (
                position < self.alert_length
                and self.alert_buffer[position] in (9, 10, 13, 32)
            ):
                position += 1
            if (
                position < self.alert_length
                and self.alert_buffer[position] == 58
            ):
                position += 1
            while (
                position < self.alert_length
                and self.alert_buffer[position] in (9, 10, 13, 32)
            ):
                position += 1
            if (
                position + 2 < self.alert_length
                and self.alert_buffer[position] == 34
                and self.alert_buffer[position + 1] in _METRO_ROUTE_BYTES
                and self.alert_buffer[position + 2] == 34
            ):
                return True
            start = index + len(_ROUTE_TOKEN)

    def _finish_alert(self):
        is_metro = self._contains_metro_route()
        self.reading_alert = False
        if not is_metro:
            self.alert_length = 0
            return
        raw_alert = bytes(
            memoryview(self.alert_buffer)[:self.alert_length]
        )
        self.alert_length = 0
        try:
            self.alerts.append(json.loads(raw_alert.decode("utf-8")))
        except Exception as error:
            raise AsyncStmApiError(
                "Alerte STM invalide: {}".format(error)
            )

    def _read_alert_byte(self, byte):
        if self.alert_length >= MAX_ALERT_BYTES:
            raise AsyncStmApiError(
                "Une alerte STM dépasse la limite de {} octets".format(
                    MAX_ALERT_BYTES
                )
            )
        self.alert_buffer[self.alert_length] = byte
        self.alert_length += 1

        if self.in_string:
            if self.escaped:
                self.escaped = False
            elif byte == 92:  # barre oblique inverse
                self.escaped = True
            elif byte == 34:  # guillemet
                self.in_string = False
            return

        if byte == 34:
            self.in_string = True
        elif byte in (123, 91):  # { ou [
            self.depth += 1
        elif byte in (125, 93):  # } ou ]
            self.depth -= 1
            if self.depth == 0:
                self._finish_alert()

    def feed(self, data):
        for byte in data:
            if self.finished:
                return
            if self.state == self.SEARCH_ALERTS:
                self._search_token(byte)
            elif self.state == self.WAIT_COLON:
                if byte == 58:  # :
                    self.state = self.WAIT_ARRAY
            elif self.state == self.WAIT_ARRAY:
                if byte == 91:  # [
                    self.state = self.READ_ARRAY
            elif self.reading_alert:
                self._read_alert_byte(byte)
            elif byte == 123:  # début d'un objet d'alerte
                self.reading_alert = True
                self.alert_length = 0
                self.depth = 0
                self.in_string = False
                self.escaped = False
                self._read_alert_byte(byte)
            elif byte == 93:  # fin du tableau alerts
                self.finished = True

    def result(self):
        if not self.finished:
            raise AsyncStmApiError("Tableau alerts absent ou tronqué")
        if self.reading_alert:
            raise AsyncStmApiError("Réponse STM tronquée dans une alerte")
        return {"alerts": self.alerts}


def prepare_stm_endpoint():
    """Résout le DNS avant le lancement des tâches pour éviter de les bloquer."""
    global STM_CONNECT_HOST
    STM_CONNECT_HOST = socket.getaddrinfo(
        STM_HOST,
        443,
        0,
        socket.SOCK_STREAM,
    )[0][-1][0]
    return STM_CONNECT_HOST


async def _feed_exactly(reader, size, stream_filter):
    remaining = size
    while remaining:
        data = await reader.read(min(STREAM_READ_SIZE, remaining))
        if not data:
            raise AsyncStmApiError("Réponse HTTP tronquée")
        await _feed_stream_data(stream_filter, data)
        remaining -= len(data)


async def _read_chunked(reader, stream_filter):
    while True:
        size_line = await reader.readline()
        if not size_line:
            raise AsyncStmApiError("Réponse HTTP tronquée")
        size = int(size_line.split(b";", 1)[0], 16)
        if size == 0:
            await reader.readline()
            break
        await _feed_exactly(reader, size, stream_filter)
        terminator = await reader.readexactly(2)
        if terminator != b"\r\n":
            raise AsyncStmApiError("Séparateur HTTP chunked invalide")


async def _read_content_length(reader, size, stream_filter):
    await _feed_exactly(reader, size, stream_filter)


async def _read_until_close(reader, stream_filter):
    while True:
        data = await reader.read(STREAM_READ_SIZE)
        if not data:
            break
        await _feed_stream_data(stream_filter, data)


async def _close_writer(writer):
    writer.close()
    wait_closed = getattr(writer, "wait_closed", None)
    if wait_closed is not None:
        await wait_closed()


async def fetch_service_status_async(api_key):
    """Effectue la requête sans bloquer la boucle uasyncio."""
    global _STM_ETAG
    if not api_key or api_key == "CLE_API_STM":
        raise AsyncStmApiError("La clé API STM n'est pas configurée")

    reader = None
    writer = None
    try:
        reader, writer = await asyncio.open_connection(
            STM_CONNECT_HOST,
            443,
            ssl=True,
            server_hostname=STM_HOST,
        )
        conditional_header = (
            "If-None-Match: {}\r\n".format(_STM_ETAG)
            if _STM_ETAG
            else ""
        )
        request = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "apiKey: {}\r\n"
            "Accept: application/json\r\n"
            "Accept-Encoding: identity\r\n"
            "User-Agent: metro-montreal-led-pico/1.0\r\n"
            "{}"
            "Connection: close\r\n\r\n"
        ).format(STM_PATH, STM_HOST, api_key, conditional_header)
        writer.write(request.encode())
        drain = getattr(writer, "drain", None)
        if drain is not None:
            await drain()

        status_line = await reader.readline()
        parts = status_line.decode().strip().split(" ", 2)
        if len(parts) < 2:
            raise AsyncStmApiError("Réponse HTTP invalide")
        status_code = int(parts[1])

        headers = {}
        while True:
            line = await reader.readline()
            if line in (b"", b"\r\n", b"\n"):
                break
            key, value = line.decode().split(":", 1)
            # Les noms d'en-tête sont insensibles à la casse, mais la valeur
            # opaque d'un ETag ne doit jamais être modifiée.
            headers[key.lower().strip()] = value.strip()

        if status_code == 304:
            return None
        if status_code != 200:
            raise AsyncStmApiError("Réponse HTTP STM: {}".format(status_code))

        stream_filter = MetroAlertStreamFilter()
        if headers.get("transfer-encoding", "").lower() == "chunked":
            await _read_chunked(reader, stream_filter)
        elif "content-length" in headers:
            await _read_content_length(
                reader,
                int(headers["content-length"]),
                stream_filter,
            )
        else:
            await _read_until_close(reader, stream_filter)

        result = stream_filter.result()
        response_etag = headers.get("etag")
        if response_etag:
            _STM_ETAG = response_etag
        return result
    finally:
        if writer is not None:
            await _close_writer(writer)
