"""Portail Web local pour associer les 68 DEL physiques aux stations."""

import json
import time
from machine import Pin, reset
from neopixel import NeoPixel
import network

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from config import (
    DATA_PIN,
    NUMBER_OF_LEDS,
    PIXEL_TIMING,
    SETUP_AP_IP,
    SETUP_AP_PASSWORD,
    SETUP_AP_SSID,
    SETUP_BLINK_PERIOD_MS,
    STATUS_BRIGHTNESS,
)
from led_mapping import (
    load_draft,
    remove_draft,
    save_draft,
    save_led_mapping,
    validate_physical_to_logical,
)
from power_safety import write_limited
from stations import LINE_COLORS, STATION_LINES, STATION_ORDER
from status_animation import SETUP_PORTAL, state_frame

OFF = (0, 0, 0)
IDENTIFY_COLOR = (36, 36, 32)
SUCCESS_COLOR = (0, 28, 8)


def _scaled(color, factor=STATUS_BRIGHTNESS):
    return tuple(int(channel * factor + 0.5) for channel in color)


class PixelIdentifier:
    def __init__(self):
        self.pixels = NeoPixel(
            Pin(DATA_PIN, Pin.OUT),
            NUMBER_OF_LEDS,
            timing=PIXEL_TIMING,
        )
        self.index = 0
        self.phase = False
        self.completed = False
        self.portal_started_ms = time.ticks_ms()
        self.confirmed_index = None
        self.confirmed_started_ms = 0
        write_limited(self.pixels, [OFF] * NUMBER_OF_LEDS)

    def select(self, physical_index):
        self.index = physical_index
        self.phase = True

    def confirm(self, physical_index):
        self.confirmed_index = physical_index
        self.confirmed_started_ms = time.ticks_ms()

    def show_success(self, physical_to_logical):
        self.completed = True
        frame = [OFF] * NUMBER_OF_LEDS
        for physical_index, logical_index in enumerate(physical_to_logical):
            station_name = STATION_ORDER[logical_index]
            lines = STATION_LINES[station_name]
            color = (
                (180, 180, 165)
                if len(lines) > 1
                else LINE_COLORS[lines[0]]
            )
            frame[physical_index] = _scaled(color)
        write_limited(
            self.pixels,
            frame,
        )

    async def blink_loop(self):
        half_period = max(100, SETUP_BLINK_PERIOD_MS // 2)
        while True:
            if self.completed:
                await asyncio.sleep_ms(half_period)
                continue
            now_ms = time.ticks_ms()
            portal_elapsed = time.ticks_diff(now_ms, self.portal_started_ms)
            if portal_elapsed < 1800:
                frame = state_frame(
                    SETUP_PORTAL,
                    portal_elapsed,
                    NUMBER_OF_LEDS,
                )
                write_limited(
                    self.pixels,
                    [_scaled(color) for color in frame],
                )
                await asyncio.sleep_ms(60)
                continue
            if self.confirmed_index is not None:
                confirmed_elapsed = time.ticks_diff(
                    now_ms,
                    self.confirmed_started_ms,
                )
                if confirmed_elapsed < 650:
                    frame = [OFF] * NUMBER_OF_LEDS
                    if (confirmed_elapsed % 300) < 130:
                        frame[self.confirmed_index] = SUCCESS_COLOR
                    write_limited(self.pixels, frame)
                    await asyncio.sleep_ms(60)
                    continue
                self.confirmed_index = None
            frame = [OFF] * NUMBER_OF_LEDS
            if self.phase:
                frame[self.index] = IDENTIFY_COLOR
            write_limited(self.pixels, frame)
            self.phase = not self.phase
            await asyncio.sleep_ms(half_period)


class SetupAssistant:
    def __init__(self, stations_map):
        self.station_names = stations_map["stations"]
        self.station_count = len(self.station_names)
        self.assignments = load_draft(station_count=self.station_count)
        self.current = self._next_unassigned(-1)
        self.identifier = PixelIdentifier()
        self.identifier.select(self.current)
        self.server = None
        self.ap = None
        self.page = self._load_page()

    def _load_page(self):
        try:
            with open("setup.html", "r") as handle:
                return handle.read()
        except OSError:
            return (
                "<!doctype html><meta charset=utf-8>"
                "<h1>setup.html est absent</h1>"
                "<p>Recopiez tous les fichiers du dossier pico sur le Pico.</p>"
            )

    def _next_unassigned(self, after):
        for offset in range(1, self.station_count + 1):
            candidate = (after + offset) % self.station_count
            if self.assignments[candidate] is None:
                return candidate
        return 0

    def _state(self):
        assigned_count = sum(
            1 for value in self.assignments if value is not None
        )
        return {
            "ok": True,
            "stations": self.station_names,
            "assignments": self.assignments,
            "current": self.current,
            "assigned_count": assigned_count,
            "complete": assigned_count == self.station_count,
            "ssid": SETUP_AP_SSID,
            "ip": SETUP_AP_IP,
        }

    def _identify(self, payload):
        physical_index = int(payload.get("physical_index", -1))
        if physical_index < 0 or physical_index >= self.station_count:
            raise ValueError("Numéro de DEL invalide")
        self.current = physical_index
        self.identifier.select(physical_index)
        return self._state()

    def _assign(self, payload):
        physical_index = int(payload.get("physical_index", -1))
        logical_index = int(payload.get("station_index", -1))
        if physical_index < 0 or physical_index >= self.station_count:
            raise ValueError("Numéro de DEL invalide")
        if logical_index < 0 or logical_index >= self.station_count:
            raise ValueError("Station invalide")

        for other_physical, assigned in enumerate(self.assignments):
            if assigned == logical_index and other_physical != physical_index:
                raise ValueError(
                    "Cette station est déjà associée à la DEL {}".format(
                        other_physical + 1
                    )
                )

        self.assignments[physical_index] = logical_index
        save_draft(self.assignments)
        self.identifier.confirm(physical_index)
        self.current = self._next_unassigned(physical_index)
        self.identifier.select(self.current)
        return self._state()

    def _complete(self):
        if not validate_physical_to_logical(
            self.assignments,
            self.station_count,
        ):
            raise ValueError(
                "Les 68 DEL doivent être associées à 68 stations différentes"
            )
        save_led_mapping(self.assignments)
        remove_draft()
        self.identifier.show_success(self.assignments)
        asyncio.create_task(self._restart_after_delay())
        state = self._state()
        state["restarting"] = True
        return state

    async def _restart_after_delay(self):
        await asyncio.sleep(3)
        reset()

    async def _send(self, writer, status, content_type, body):
        if isinstance(body, str):
            body = body.encode("utf-8")
        reasons = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
        }
        reason = reasons.get(status, "OK")
        header = (
            "HTTP/1.1 {} {}\r\n"
            "Content-Type: {}\r\n"
            "Content-Length: {}\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        ).format(status, reason, content_type, len(body))
        writer.write(header.encode("utf-8"))
        writer.write(body)
        await writer.drain()

    async def _send_json(self, writer, payload, status=200):
        await self._send(
            writer,
            status,
            "application/json; charset=utf-8",
            json.dumps(payload),
        )

    async def handle_request(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                return
            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                raise ValueError("Requête HTTP invalide")
            method, raw_path = parts[0], parts[1]
            path = raw_path.split("?", 1)[0]

            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"", b"\r\n", b"\n"):
                    break
                key, value = line.decode().split(":", 1)
                headers[key.lower().strip()] = value.strip()

            body = b""
            content_length = int(headers.get("content-length", "0"))
            if content_length > 4096:
                raise ValueError("Requête trop volumineuse")
            if content_length:
                body = await reader.readexactly(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            if method == "GET" and path == "/api/state":
                await self._send_json(writer, self._state())
            elif method == "POST" and path == "/api/identify":
                await self._send_json(writer, self._identify(payload))
            elif method == "POST" and path == "/api/assign":
                await self._send_json(writer, self._assign(payload))
            elif method == "POST" and path == "/api/complete":
                await self._send_json(writer, self._complete())
            elif method == "GET" and not path.startswith("/api/"):
                await self._send(
                    writer,
                    200,
                    "text/html; charset=utf-8",
                    self.page,
                )
            else:
                await self._send_json(
                    writer,
                    {"ok": False, "error": "Route inconnue"},
                    404,
                )
        except Exception as error:
            try:
                await self._send_json(
                    writer,
                    {"ok": False, "error": str(error)},
                    400,
                )
            except Exception:
                pass
        finally:
            writer.close()
            wait_closed = getattr(writer, "wait_closed", None)
            if wait_closed is not None:
                await wait_closed()

    def start_access_point(self):
        self.ap = network.WLAN(network.AP_IF)
        self.ap.config(
            essid=SETUP_AP_SSID,
            password=SETUP_AP_PASSWORD,
        )
        self.ap.active(True)
        self.ap.ifconfig(
            (
                SETUP_AP_IP,
                "255.255.255.0",
                SETUP_AP_IP,
                SETUP_AP_IP,
            )
        )

    async def run(self):
        self.start_access_point()
        self.server = await asyncio.start_server(
            self.handle_request,
            "0.0.0.0",
            80,
        )
        print("")
        print("ASSISTANT DE CONFIGURATION DES DEL")
        print("Wi-Fi:", SETUP_AP_SSID)
        print("Mot de passe:", SETUP_AP_PASSWORD)
        print("Ouvrir: http://{}".format(SETUP_AP_IP))
        print("")
        await self.identifier.blink_loop()


def run_setup_assistant(stations_map):
    assistant = SetupAssistant(stations_map)
    try:
        asyncio.run(assistant.run())
    finally:
        write_limited(
            assistant.identifier.pixels,
            [OFF] * NUMBER_OF_LEDS,
        )
