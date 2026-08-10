import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator"))

import server
from stm_status import STOPPED, empty_status


class SimulatorCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.original_secret = server._secret
        self.original_get_stm_status = server._get_stm_status

    def tearDown(self):
        server._secret = self.original_secret
        server._get_stm_status = self.original_get_stm_status

    def test_live_status_uses_the_same_stm_source_as_the_pico(self):
        requested_secrets = []

        def fake_secret(name):
            requested_secrets.append(name)
            return "stm-key"

        parsed = empty_status()
        parsed["lines"]["blue"] = STOPPED
        server._secret = fake_secret
        server._get_stm_status = lambda _key: parsed

        status = server.StatusProvider().get(force=True)

        self.assertEqual(requested_secrets, ["STM_API_KEY"])
        self.assertEqual(status["source"], ["STM i3 v2"])
        self.assertEqual(status["lines"]["blue"], STOPPED)
        self.assertFalse(status["stale"])

    def test_failed_refresh_keeps_the_last_valid_status_like_the_pico(self):
        parsed = empty_status()
        parsed["lines"]["orange"] = STOPPED
        responses = [parsed, OSError("réseau indisponible")]

        server._secret = lambda _name: "stm-key"

        def fake_get(_key):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        server._get_stm_status = fake_get
        provider = server.StatusProvider()

        first = provider.get(force=True)
        second = provider.get(force=True)

        self.assertEqual(first["lines"]["orange"], STOPPED)
        self.assertEqual(second["lines"]["orange"], STOPPED)
        self.assertTrue(second["stale"])
        self.assertTrue(second["live"])
        self.assertIn("dernier état valide", second["source"][0])
        self.assertTrue(second["errors"])


if __name__ == "__main__":
    unittest.main()
