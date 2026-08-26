import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICO = ROOT / "pico"
PAGE = PICO / "admin.html"
PACKAGED_PAGE = (
    ROOT
    / "PICO_2_W_PRET_A_COPIER"
    / "CONTENU_A_COPIER_SUR_LE_PICO"
    / "admin.html"
)
sys.path.insert(0, str(PICO))

from control_panel import ControlPanel


class FakeReader:
    def __init__(self, request):
        self.lines = request.splitlines(keepends=True)
        self.body = b""
        marker = b"\r\n\r\n"
        if marker in request:
            head, self.body = request.split(marker, 1)
            self.lines = (head + b"\r\n\r\n").splitlines(keepends=True)

    async def readline(self):
        return self.lines.pop(0) if self.lines else b""

    async def readexactly(self, length):
        return self.body[:length]


class FakeWriter:
    def __init__(self):
        self.data = bytearray()

    def write(self, value):
        self.data.extend(value)

    async def drain(self):
        pass

    def close(self):
        pass

    async def wait_closed(self):
        pass


class ControlPanelTests(unittest.TestCase):
    def _panel(self):
        return ControlPanel(
            "metro68",
            lambda: {"ok": True},
            lambda settings: settings,
            lambda action, payload: {"action": action},
        )

    def test_pin_is_required_and_not_accepted_by_prefix(self):
        panel = self._panel()
        self.assertTrue(panel._authorized({"x-control-pin": "metro68"}))
        self.assertFalse(panel._authorized({"x-control-pin": "metro"}))
        self.assertFalse(panel._authorized({"x-control-pin": "metro680"}))

    def test_authenticated_state_route_returns_json(self):
        panel = self._panel()
        request = (
            b"GET /api/state HTTP/1.1\r\n"
            b"Host: pico\r\n"
            b"X-Control-Pin: metro68\r\n\r\n"
        )
        writer = FakeWriter()
        asyncio.run(panel.handle_request(FakeReader(request), writer))
        response = bytes(writer.data)
        self.assertIn(b"HTTP/1.1 200 OK", response)
        payload = json.loads(response.split(b"\r\n\r\n", 1)[1])
        self.assertTrue(payload["ok"])

    def test_state_route_rejects_an_invalid_pin(self):
        panel = self._panel()
        request = (
            b"GET /api/state HTTP/1.1\r\n"
            b"Host: pico\r\n"
            b"X-Control-Pin: wrong\r\n\r\n"
        )
        writer = FakeWriter()
        asyncio.run(panel.handle_request(FakeReader(request), writer))
        self.assertIn(b"HTTP/1.1 401 Unauthorized", bytes(writer.data))

    def test_page_supports_four_languages_and_all_commands(self):
        page = PAGE.read_text(encoding="utf-8")
        for language in ("fr", "en", "es", "it"):
            self.assertIn("{}:{{".format(language), page)
        for action in (
            "test_pixels",
            "test_lines",
            "test_all",
            "preview_night",
            "refresh_stm",
            "refresh_gtfs",
            "reconnect_wifi",
            "restart",
            "reset_mapping",
        ):
            self.assertIn(action, page)

    def test_page_stays_small_enough_for_the_pico(self):
        self.assertLess(PAGE.stat().st_size, 40_000)

    def test_packaged_page_matches_source(self):
        self.assertEqual(PACKAGED_PAGE.read_bytes(), PAGE.read_bytes())


if __name__ == "__main__":
    unittest.main()
