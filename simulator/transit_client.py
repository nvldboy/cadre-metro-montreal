"""Client Transit v4 utilisé par le simulateur local."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT_URL = "https://external.transitapp.com"
MONTREAL = {"lat": 45.5017, "lon": -73.5673}
SHORT_NAME_TO_LINE = {
    "1": "green",
    "2": "orange",
    "4": "yellow",
    "5": "blue",
}


def _get_json(path, api_key, params=None):
    query = "?" + urlencode(params or {}) if params else ""
    request = Request(
        ROOT_URL + path + query,
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "Accept-Language": "fr-CA",
            "User-Agent": "metro-montreal-led-simulator/1.0",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def _normalize(value):
    text = str(value).lower()
    replacements = {
        "à": "a", "â": "a", "ç": "c", "é": "e", "è": "e",
        "ê": "e", "ë": "e", "î": "i", "ï": "i", "ô": "o",
        "ù": "u", "û": "u", "ü": "u", "’": "'", "–": "-",
    }
    return "".join(replacements.get(character, character) for character in text)


class TransitClient:
    def __init__(self, api_key, station_names, network_ids=""):
        self.api_key = api_key
        self.station_names = tuple(station_names)
        self.network_ids = network_ids
        self.route_map = {}
        self.stop_map = {}

    def _discover_networks(self):
        payload = _get_json(
            "/v4/public/available_networks",
            self.api_key,
            {
                **MONTREAL,
                "locale": "fr-CA",
                "include_network_geometry": "false",
            },
        )
        matches = []
        for network in payload.get("networks", []):
            name = _normalize(network.get("network_name", ""))
            if "stm" in name or "societe de transport de montreal" in name:
                matches.append(network["network_id"])
        if not matches:
            names = [
                network.get("network_name", "?")
                for network in payload.get("networks", [])
            ]
            raise RuntimeError(
                "Réseau STM introuvable dans Transit: " + ", ".join(names)
            )
        self.network_ids = ",".join(matches)

    def _load_routes(self):
        payload = _get_json(
            "/v4/public/routes_for_networks",
            self.api_key,
            {
                "network_ids": self.network_ids,
                **MONTREAL,
                "locale": "fr-CA",
                "include_itineraries": "false",
            },
        )
        for route in payload.get("routes", []):
            short_name = str(route.get("route_short_name", "")).strip()
            line_name = SHORT_NAME_TO_LINE.get(short_name)
            if line_name and int(route.get("route_type", -1)) == 1:
                self.route_map[route["global_route_id"]] = line_name

        if not self.route_map:
            raise RuntimeError("Aucune ligne de métro trouvée dans Transit")

    def _load_stops(self):
        canonical = {
            _normalize(name).replace("–", "-"): name
            for name in self.station_names
        }
        for route_id in self.route_map:
            payload = _get_json(
                "/v4/public/route_details",
                self.api_key,
                {
                    "global_route_id": route_id,
                    "locale": "fr-CA",
                    "include_next_departure": "false",
                    "stop_detailed": "false",
                },
            )
            for itinerary in payload.get("itineraries", []):
                for stop in itinerary.get("stops", []):
                    stop_text = _normalize(stop.get("stop_name", ""))
                    for normalized_name, station_name in canonical.items():
                        if normalized_name in stop_text:
                            self.stop_map[stop["global_stop_id"]] = station_name
                            break

    def ensure_metadata(self):
        if not self.network_ids:
            self._discover_networks()
        if not self.route_map:
            self._load_routes()
        if not self.stop_map:
            self._load_stops()

    def fetch_alerts(self):
        self.ensure_metadata()
        return _get_json(
            "/v4/public/alerts_for_networks",
            self.api_key,
            {
                "network_ids": self.network_ids,
                **MONTREAL,
                "show_active_alerts_only": "true",
                "locale": "fr-CA",
            },
        )
