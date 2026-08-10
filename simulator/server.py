#!/usr/bin/env python3
"""Serveur local du simulateur de DEL."""

import importlib.util
import argparse
import copy
import json
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PICO = ROOT / "pico"
SIMULATOR = ROOT / "simulator"
MAP_FILE = ROOT / "metro-montreal-stm-fidele-18x24-led12.svg"
SETUP_PAGE = PICO / "setup.html"
ADMIN_PAGE = PICO / "admin.html"
UPDATES = ROOT / "updates"
sys.path.insert(0, str(PICO))
sys.path.insert(0, str(SIMULATOR))

from stations import LINE_COLORS, STATION_LINES, STATION_ORDER
from stm_status import empty_status, parse_service_status
from train_provider import current_train_payload
from runtime_settings import DEFAULTS, validate_settings

STM_URL = "https://api.stm.info/pub/od/i3/v2/messages/etatservice"
CACHE_SECONDS = 55
SIMULATOR_STARTED_AT = time.time()
CONTROL_PREVIEW_PIN = "metro68"
CONTROL_PREVIEW_SETTINGS = dict(DEFAULTS)
CONTROL_PREVIEW_LOCK = threading.Lock()


def _load_local_secrets():
    path = PICO / "secrets.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location("metro_user_secrets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        name: getattr(module, name, "")
        for name in ("STM_API_KEY",)
    }


LOCAL_SECRETS = _load_local_secrets()


def _secret(name):
    return os.environ.get(name) or LOCAL_SECRETS.get(name, "")


def _get_stm_status(api_key):
    request = Request(
        STM_URL,
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "User-Agent": "metro-montreal-led-simulator/1.0",
        },
    )
    with urlopen(request, timeout=20) as response:
        return parse_service_status(json.load(response))


def _merge(target, incoming):
    for line_name, severity in incoming["lines"].items():
        target["lines"][line_name] = max(
            target["lines"].get(line_name, 0), severity
        )
    for station_name, severity in incoming["stations"].items():
        target["stations"][station_name] = max(
            target["stations"].get(station_name, 0), severity
        )
    for message in incoming.get("messages", []):
        if message not in target["messages"]:
            target["messages"].append(message)
    target["message_count"] = len(target["messages"])


def _layout():
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    root = ET.parse(MAP_FILE).getroot()
    circles = root.findall(".//svg:circle", namespace)
    if len(circles) != len(STATION_ORDER):
        raise RuntimeError("Le SVG et la table de stations ne concordent pas")

    stations = []
    for station_name, circle in zip(STATION_ORDER, circles):
        stations.append({
            "name": station_name,
            "x": float(circle.get("cx")),
            "y": float(circle.get("cy")),
            "lines": STATION_LINES[station_name],
        })
    return {
        "width": 457.2,
        "height": 609.6,
        "stations": stations,
        "colors": {
            name: "#{:02x}{:02x}{:02x}".format(*rgb)
            for name, rgb in LINE_COLORS.items()
        },
    }


class StatusProvider:
    def __init__(self):
        self.cached = None
        self.cached_at = 0
        self.last_valid = None

    def get(self, force=False):
        now = time.time()
        if (
            not force
            and self.cached is not None
            and now - self.cached_at < CACHE_SECONDS
        ):
            return self.cached

        metadata = {
            "source": [],
            "errors": [],
            "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "live": False,
            "stale": False,
        }
        result = empty_status()
        result.update(metadata)

        stm_key = _secret("STM_API_KEY")

        if stm_key:
            try:
                _merge(result, _get_stm_status(stm_key))
                result["source"].append("STM i3 v2")
                result["live"] = True
                self.last_valid = copy.deepcopy(result)
            except Exception as error:
                if self.last_valid is not None:
                    # Le Pico conserve lui aussi le dernier état STM valide si
                    # une requête échoue. Le simulateur doit montrer exactement
                    # cette même information, sans revenir artificiellement à
                    # un réseau normal.
                    result = copy.deepcopy(self.last_valid)
                    result.update(metadata)
                    result["source"] = ["STM i3 v2 — dernier état valide"]
                    result["live"] = True
                    result["stale"] = True
                result["errors"].append("STM: {}".format(error))

        if not stm_key:
            result["messages"].append(
                "Les trains théoriques fonctionnent sans clé. Ajoute une clé "
                "STM pour superposer les mêmes alertes réseau que le Pico."
            )
            result["message_count"] = len(result["messages"])

        self.cached = result
        self.cached_at = now
        return result


PROVIDER = StatusProvider()
LAYOUT = _layout()


class SetupPreviewProvider:
    """État temporaire de l'assistant Web, sans aucun matériel."""

    def __init__(self):
        self.lock = threading.Lock()
        self.assignments = [None] * len(STATION_ORDER)
        self.current = 0

    def _next_unassigned(self, after):
        for offset in range(1, len(STATION_ORDER) + 1):
            candidate = (after + offset) % len(STATION_ORDER)
            if self.assignments[candidate] is None:
                return candidate
        return 0

    def _state(self):
        assigned_count = sum(
            value is not None for value in self.assignments
        )
        return {
            "ok": True,
            "stations": list(STATION_ORDER),
            "assignments": self.assignments,
            "current": self.current,
            "assigned_count": assigned_count,
            "complete": assigned_count == len(STATION_ORDER),
            "ssid": "Metro-Setup",
            "ip": "192.168.4.1",
            "preview": True,
        }

    def state(self):
        with self.lock:
            return self._state()

    def identify(self, payload):
        physical_index = int(payload.get("physical_index", -1))
        if physical_index < 0 or physical_index >= len(STATION_ORDER):
            raise ValueError("Numéro de DEL invalide")
        with self.lock:
            self.current = physical_index
            return self._state()

    def assign(self, payload):
        physical_index = int(payload.get("physical_index", -1))
        station_index = int(payload.get("station_index", -1))
        if physical_index < 0 or physical_index >= len(STATION_ORDER):
            raise ValueError("Numéro de DEL invalide")
        if station_index < 0 or station_index >= len(STATION_ORDER):
            raise ValueError("Station invalide")

        with self.lock:
            for other_physical, assigned in enumerate(self.assignments):
                if (
                    assigned == station_index
                    and other_physical != physical_index
                ):
                    raise ValueError(
                        "Cette station est déjà associée à la DEL {}".format(
                            other_physical + 1
                        )
                    )
            self.assignments[physical_index] = station_index
            self.current = self._next_unassigned(physical_index)
            return self._state()

    def complete(self):
        with self.lock:
            if (
                any(value is None for value in self.assignments)
                or len(set(self.assignments)) != len(STATION_ORDER)
            ):
                raise ValueError(
                    "Les 68 DEL doivent être associées avant de terminer"
                )
            state = self._state()
            state["restarting"] = True
            return state


SETUP_PREVIEW = SetupPreviewProvider()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SIMULATOR), **kwargs)

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 4096:
            raise ValueError("Requête trop volumineuse")
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _control_authorized(self, payload=None):
        supplied = self.headers.get("X-Control-Pin", "")
        if not supplied and isinstance(payload, dict):
            supplied = str(payload.get("pin", ""))
        return supplied == CONTROL_PREVIEW_PIN

    def _control_state(self):
        trains = current_train_payload()
        status = PROVIDER.get()
        severity_names = {0: "ok", 1: "slow", 2: "interrupted"}
        with CONTROL_PREVIEW_LOCK:
            settings = dict(CONTROL_PREVIEW_SETTINGS)
        return {
            "ok": True,
            "preview": True,
            "wifi": {
                "connected": True,
                "ssid": "Simulation locale",
                "ip": "127.0.0.1",
            },
            "local_time": datetime.now().astimezone().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "trains": trains["train_count"],
            "active_stations": sum(level > 0.02 for level in trains["levels"]),
            "lines": {
                name: severity_names.get(severity, "ok")
                for name, severity in status["lines"].items()
            },
            "api_failures": len(status.get("errors", ())),
            "gtfs_current": trains["feed_current"],
            "memory_free": 330000,
            "uptime_seconds": int(time.time() - SIMULATOR_STARTED_AT),
            "night_active": settings["display_mode"] == "night",
            "settings": settings,
        }

    def do_GET(self):
        if self.path in (
            "/updates/latest.json",
            "/updates/metro_schedule_data.py",
        ):
            filename = self.path.rsplit("/", 1)[-1]
            update_file = UPDATES / filename
            body = update_file.read_bytes()
            content_type = (
                "application/json; charset=utf-8"
                if filename.endswith(".json")
                else "text/x-python; charset=utf-8"
            )
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/setup-preview"):
            body = SETUP_PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/admin-preview"):
            body = ADMIN_PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/api/state"):
            if not self._control_authorized():
                self._json({"ok": False, "error": "Accès refusé"}, 401)
                return
            self._json(self._control_state())
            return
        if self.path.startswith("/api/setup/state"):
            self._json(SETUP_PREVIEW.state())
            return
        if self.path.startswith("/api/layout"):
            self._json(LAYOUT)
            return
        if self.path.startswith("/api/status"):
            force = "force=1" in self.path
            self._json(PROVIDER.get(force=force))
            return
        if self.path.startswith("/api/trains"):
            self._json(current_train_payload())
            return
        if self.path == "/map.svg":
            body = MAP_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        try:
            payload = self._read_json()
            if self.path.startswith("/api/login"):
                if not self._control_authorized(payload):
                    self._json({"ok": False, "error": "NIP incorrect"}, 401)
                    return
                self._json({"ok": True, "preview": True})
                return
            if self.path.startswith("/api/settings"):
                if not self._control_authorized(payload):
                    self._json({"ok": False, "error": "Accès refusé"}, 401)
                    return
                with CONTROL_PREVIEW_LOCK:
                    CONTROL_PREVIEW_SETTINGS.update(
                        validate_settings(
                            payload.get("settings", {}),
                            CONTROL_PREVIEW_SETTINGS,
                        )
                    )
                    updated = dict(CONTROL_PREVIEW_SETTINGS)
                self._json({"ok": True, "settings": updated, "preview": True})
                return
            if self.path.startswith("/api/action"):
                if not self._control_authorized(payload):
                    self._json({"ok": False, "error": "Accès refusé"}, 401)
                    return
                self._json({"ok": True, "preview": True})
                return
            if self.path.startswith("/api/setup/identify"):
                self._json(SETUP_PREVIEW.identify(payload))
                return
            if self.path.startswith("/api/setup/assign"):
                self._json(SETUP_PREVIEW.assign(payload))
                return
            if self.path.startswith("/api/setup/complete"):
                self._json(SETUP_PREVIEW.complete())
                return
            self._json({"ok": False, "error": "Route inconnue"}, 404)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self._json({"ok": False, "error": str(error)}, 400)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("METRO_SIMULATOR_PORT", "8765")),
    )
    args = parser.parse_args()
    port = args.port
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Simulateur: http://127.0.0.1:{}".format(port))
    print("Arrêter avec Ctrl-C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du simulateur")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
