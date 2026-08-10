import json
import sys
import tempfile
import unittest
from pathlib import Path

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

import runtime_settings


class RuntimeSettingsTests(unittest.TestCase):
    def setUp(self):
        runtime_settings._settings = dict(runtime_settings.DEFAULTS)
        runtime_settings._loaded = True

    def tearDown(self):
        runtime_settings._settings = dict(runtime_settings.DEFAULTS)
        runtime_settings._loaded = True

    def test_partial_update_preserves_other_safe_defaults(self):
        updated = runtime_settings.validate_settings(
            {"day_brightness": 0.12, "display_mode": "night"},
            runtime_settings.DEFAULTS,
        )
        self.assertEqual(updated["day_brightness"], 0.12)
        self.assertEqual(updated["display_mode"], "night")
        self.assertEqual(
            updated["night_brightness"],
            runtime_settings.DEFAULTS["night_brightness"],
        )

    def test_unsafe_brightness_is_rejected(self):
        with self.assertRaises(ValueError):
            runtime_settings.validate_settings({"day_brightness": 0.8})
        with self.assertRaises(ValueError):
            runtime_settings.validate_settings({"night_brightness": 0.5})

    def test_settings_are_saved_and_loaded_from_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "user_settings.json")
            saved = runtime_settings.save_settings(
                {
                    "day_brightness": 0.11,
                    "night_brightness": 0.004,
                    "status_brightness": 0.08,
                    "night_enabled": False,
                    "night_start_hour": 1,
                    "night_end_hour": 7,
                    "display_mode": "off",
                },
                path,
            )
            self.assertEqual(saved["display_mode"], "off")
            self.assertEqual(
                json.loads(Path(path).read_text(encoding="utf-8"))["day_brightness"],
                0.11,
            )
            runtime_settings._loaded = False
            loaded = runtime_settings.load_settings(path)
            self.assertEqual(loaded["night_start_hour"], 1)
            self.assertFalse(loaded["night_enabled"])


if __name__ == "__main__":
    unittest.main()
