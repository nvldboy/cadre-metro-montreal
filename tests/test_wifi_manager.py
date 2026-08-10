import sys
import types
import unittest
from pathlib import Path

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

# Le module réseau existe sur le Pico, mais pas dans Python sur le Mac.
fake_network_module = types.ModuleType("network")
fake_network_module.STA_IF = 0
fake_network_module.WLAN = lambda interface: None
sys.modules.setdefault("network", fake_network_module)

import wifi_manager


class FakeWlan:
    def __init__(self, visible=()):
        self.visible = visible
        self.enabled = False

    def active(self, enabled=None):
        if enabled is not None:
            self.enabled = enabled
        return self.enabled

    def isconnected(self):
        return False

    def scan(self):
        return [
            (ssid.encode("utf-8"), b"", 1, -50, 0, False)
            for ssid in self.visible
        ]


class WifiManagerTests(unittest.TestCase):
    def test_normalize_removes_placeholders_invalid_entries_and_duplicates(self):
        networks = wifi_manager.normalize_networks(
            [
                ("Maison", "secret"),
                ("Maison", "autre-secret"),
                ("NOM_DU_WIFI", "MOT_DE_PASSE_WIFI"),
                ("Sans mot de passe", ""),
                ("invalide",),
            ]
        )
        self.assertEqual(networks, [("Maison", "secret")])

    def test_visible_backup_moves_before_missing_primary(self):
        networks = [
            ("Maison", "secret-maison"),
            ("Téléphone", "secret-mobile"),
        ]
        ordered = wifi_manager.prioritize_networks(
            networks,
            visible_ssids={"Téléphone"},
        )
        self.assertEqual(
            ordered,
            [
                ("Téléphone", "secret-mobile"),
                ("Maison", "secret-maison"),
            ],
        )

    def test_original_priority_is_kept_when_both_are_visible(self):
        networks = [
            ("Maison", "secret-maison"),
            ("Téléphone", "secret-mobile"),
        ]
        ordered = wifi_manager.prioritize_networks(
            networks,
            visible_ssids={"Téléphone", "Maison"},
        )
        self.assertEqual(ordered, networks)

    def test_connect_any_tries_the_detected_backup_first(self):
        wlan = FakeWlan(visible=("Téléphone",))
        attempts = []
        original_wlan = wifi_manager.network.WLAN
        original_connect = wifi_manager.connect
        wifi_manager.network.WLAN = lambda interface: wlan

        def fake_connect(ssid, password, wlan=None):
            attempts.append(ssid)
            return wlan

        wifi_manager.connect = fake_connect
        try:
            result = wifi_manager.connect_any(
                [
                    ("Maison", "secret-maison"),
                    ("Téléphone", "secret-mobile"),
                ]
            )
        finally:
            wifi_manager.network.WLAN = original_wlan
            wifi_manager.connect = original_connect

        self.assertIs(result, wlan)
        self.assertEqual(attempts, ["Téléphone"])

    def test_connect_any_forwards_animation_progress(self):
        wlan = FakeWlan(visible=("Maison",))
        events = []
        original_wlan = wifi_manager.network.WLAN
        original_connect = wifi_manager.connect
        wifi_manager.network.WLAN = lambda interface: wlan

        def fake_connect(
            ssid,
            password,
            wlan=None,
            progress_callback=None,
            attempt=0,
        ):
            progress_callback("wifi_connecting", 400, attempt)
            return wlan

        wifi_manager.connect = fake_connect
        try:
            wifi_manager.connect_any(
                [("Maison", "secret")],
                progress_callback=lambda *event: events.append(event),
            )
        finally:
            wifi_manager.network.WLAN = original_wlan
            wifi_manager.connect = original_connect

        self.assertEqual(events, [("wifi_connecting", 400, 0)])


if __name__ == "__main__":
    unittest.main()
