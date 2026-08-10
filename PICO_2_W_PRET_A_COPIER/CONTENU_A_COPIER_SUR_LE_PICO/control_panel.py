"""Petit panneau de contrôle HTTP servi par le Pico sur le réseau local."""

import json
import os

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


async def _sleep_ms(milliseconds):
    sleep_ms = getattr(asyncio, "sleep_ms", None)
    if sleep_ms is not None:
        await sleep_ms(milliseconds)
    else:
        await asyncio.sleep(milliseconds / 1000)


class ControlPanel:
    def __init__(
        self,
        pin,
        state_provider,
        settings_updater,
        action_handler,
        page_path="admin.html",
    ):
        pin = str(pin or "")
        if len(pin) < 4 or len(pin) > 32:
            raise ValueError("Le NIP du panneau doit contenir de 4 à 32 caractères")
        self.pin = pin
        self.state_provider = state_provider
        self.settings_updater = settings_updater
        self.action_handler = action_handler
        self.page_path = page_path
        self.server = None

    def _authorized(self, headers, payload=None):
        supplied = headers.get("x-control-pin", "")
        if not supplied and isinstance(payload, dict):
            supplied = str(payload.get("pin", ""))
        return len(supplied) == len(self.pin) and supplied == self.pin

    async def _header(self, writer, status, content_type, length):
        reasons = {
            200: "OK",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
            413: "Payload Too Large",
            500: "Internal Server Error",
        }
        header = (
            "HTTP/1.1 {} {}\r\n"
            "Content-Type: {}\r\n"
            "Content-Length: {}\r\n"
            "Cache-Control: no-store\r\n"
            "X-Content-Type-Options: nosniff\r\n"
            "Connection: close\r\n\r\n"
        ).format(
            status,
            reasons.get(status, "OK"),
            content_type,
            length,
        )
        writer.write(header.encode("utf-8"))
        await writer.drain()

    async def _send(self, writer, status, content_type, body):
        if isinstance(body, str):
            body = body.encode("utf-8")
        await self._header(writer, status, content_type, len(body))
        if body:
            writer.write(body)
            await writer.drain()

    async def _send_json(self, writer, payload, status=200):
        await self._send(
            writer,
            status,
            "application/json; charset=utf-8",
            json.dumps(payload),
        )

    async def _send_page(self, writer):
        try:
            length = os.stat(self.page_path)[6]
            handle = open(self.page_path, "rb")
        except OSError:
            await self._send(
                writer,
                500,
                "text/plain; charset=utf-8",
                "admin.html est absent du Pico",
            )
            return
        await self._header(
            writer,
            200,
            "text/html; charset=utf-8",
            length,
        )
        try:
            while True:
                chunk = handle.read(1024)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        finally:
            handle.close()

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
                decoded = line.decode().split(":", 1)
                if len(decoded) == 2:
                    headers[decoded[0].lower().strip()] = decoded[1].strip()

            content_length = int(headers.get("content-length", "0"))
            if content_length > 4096:
                await self._send_json(
                    writer,
                    {"ok": False, "error": "Requête trop volumineuse"},
                    413,
                )
                return
            body = b""
            if content_length:
                body = await reader.readexactly(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            if method == "GET" and path in ("/", "/admin", "/admin/"):
                await self._send_page(writer)
            elif method == "GET" and path == "/favicon.ico":
                await self._send(writer, 204, "image/x-icon", b"")
            elif method == "POST" and path == "/api/login":
                if not self._authorized(headers, payload):
                    await _sleep_ms(450)
                    await self._send_json(
                        writer,
                        {"ok": False, "error": "NIP incorrect"},
                        401,
                    )
                else:
                    await self._send_json(writer, {"ok": True})
            elif path.startswith("/api/") and not self._authorized(
                headers,
                payload,
            ):
                await self._send_json(
                    writer,
                    {"ok": False, "error": "Accès refusé"},
                    401,
                )
            elif method == "GET" and path == "/api/state":
                await self._send_json(writer, self.state_provider())
            elif method == "POST" and path == "/api/settings":
                updated = self.settings_updater(payload.get("settings", {}))
                await self._send_json(
                    writer,
                    {"ok": True, "settings": updated},
                )
            elif method == "POST" and path == "/api/action":
                result = self.action_handler(
                    str(payload.get("action", "")),
                    payload,
                )
                response = {"ok": True}
                if isinstance(result, dict):
                    response.update(result)
                await self._send_json(writer, response)
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

    async def run(self, host="0.0.0.0", port=80):
        self.server = await asyncio.start_server(
            self.handle_request,
            host,
            port,
        )
        while True:
            await asyncio.sleep(3600)
