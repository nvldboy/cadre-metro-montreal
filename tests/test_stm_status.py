import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pico"))

from stm_status import NORMAL, SLOW, STOPPED, parse_service_status
from transit_status import parse_transit_alerts


class ServiceStatusParserTests(unittest.TestCase):
    def test_normal_lines(self):
        payload = [
            {"ligne": "1", "etat": "Service normal"},
            {"ligne": "2", "etat": "Service normal"},
            {"ligne": "4", "etat": "Service normal"},
            {"ligne": "5", "etat": "Service normal"},
        ]
        result = parse_service_status(payload)
        self.assertEqual(result["lines"]["green"], NORMAL)
        self.assertEqual(result["lines"]["orange"], NORMAL)
        self.assertEqual(result["lines"]["yellow"], NORMAL)
        self.assertEqual(result["lines"]["blue"], NORMAL)

    def test_line_interruption(self):
        payload = {
            "messages": [
                {
                    "ligne": "verte",
                    "message": "Interruption de service sur la ligne verte.",
                }
            ]
        }
        result = parse_service_status(payload)
        self.assertEqual(result["lines"]["green"], STOPPED)
        self.assertEqual(result["lines"]["orange"], NORMAL)

    def test_station_and_line_delay(self):
        payload = {
            "status": [
                {
                    "route_id": "5",
                    "description": (
                        "Service ralenti sur la ligne bleue à Jean-Talon."
                    ),
                }
            ]
        }
        result = parse_service_status(payload)
        self.assertEqual(result["lines"]["blue"], SLOW)
        self.assertEqual(result["stations"]["Jean-Talon"], SLOW)

    def test_accents_and_long_station_name(self):
        payload = [{
            "line": "4",
            "message": (
                "Station Longueuil-Université-de-Sherbrooke fermée."
            ),
        }]
        result = parse_service_status(payload)
        self.assertEqual(result["lines"]["yellow"], STOPPED)
        self.assertEqual(
            result["stations"]["Longueuil–Université-de-Sherbrooke"],
            STOPPED,
        )

    def test_transit_structured_alert(self):
        payload = {
            "alerts": [{
                "effect": "NO_SERVICE",
                "severity": "Severe",
                "title": "Interruption",
                "description": "Service suspendu à Berri-UQAM.",
                "informed_entities": [{
                    "global_route_id": "stm:green",
                    "global_stop_id": "stm:berri",
                }],
            }]
        }
        result = parse_transit_alerts(
            payload,
            route_map={"stm:green": "green"},
            stop_map={"stm:berri": "Berri-UQAM"},
        )
        self.assertEqual(result["lines"]["green"], STOPPED)
        self.assertEqual(result["stations"]["Berri-UQAM"], STOPPED)

    def test_i3_ignores_station_access_closure(self):
        payload = {
            "alerts": [
                {
                    "informed_entities": [
                        {"route_short_name": "5"},
                        {"stop_code": "10546"},
                    ],
                    "description_texts": [{
                        "language": "fr",
                        "text": (
                            "L'accès B situé sur le boulevard Saint-Laurent "
                            "est fermé pour une durée indéterminée."
                        ),
                    }],
                },
                {
                    "informed_entities": [{"route_short_name": "1"}],
                    "description_texts": [{
                        "language": "fr",
                        "text": "Service normal du métro",
                    }],
                },
            ]
        }
        result = parse_service_status(payload)
        self.assertEqual(result["lines"]["blue"], NORMAL)
        self.assertEqual(result["lines"]["green"], NORMAL)
        self.assertNotIn("Saint-Laurent", result["stations"])
        self.assertEqual(result["message_count"], 0)

    def test_i3_line_interruption(self):
        payload = {
            "alerts": [{
                "informed_entities": [{"route_short_name": "2"}],
                "description_texts": [{
                    "language": "fr",
                    "text": (
                        "Interruption de service sur la ligne orange entre "
                        "Berri-UQAM et Henri-Bourassa."
                    ),
                }],
            }]
        }
        result = parse_service_status(payload)
        self.assertEqual(result["lines"]["orange"], STOPPED)
        self.assertEqual(result["stations"]["Berri-UQAM"], STOPPED)
        self.assertEqual(result["stations"]["Henri-Bourassa"], STOPPED)


if __name__ == "__main__":
    unittest.main()
