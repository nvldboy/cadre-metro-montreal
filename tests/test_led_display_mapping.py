import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICO = ROOT / "pico"
sys.path.insert(0, str(PICO))


class FakePin:
    OUT = 1

    def __init__(self, number, mode):
        self.number = number
        self.mode = mode


class FakeNeoPixel:
    def __init__(self, pin, count, timing=1):
        self.values = [(0, 0, 0)] * count
        self.write_count = 0

    def fill(self, color):
        self.values = [color] * len(self.values)

    def write(self):
        self.write_count += 1

    def __getitem__(self, index):
        return self.values[index]

    def __setitem__(self, index, value):
        self.values[index] = value


machine = types.ModuleType("machine")
machine.Pin = FakePin
neopixel = types.ModuleType("neopixel")
neopixel.NeoPixel = FakeNeoPixel
sys.modules["machine"] = machine
sys.modules["neopixel"] = neopixel

import led_display
from led_display import MetroDisplay
from stations import STATION_INDEX
from stm_status import STOPPED, empty_status

led_display.time.ticks_diff = lambda first, second: first - second


class LedDisplayMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stations_map = json.loads(
            (PICO / "stations_map.json").read_text(encoding="utf-8")
        )

    def test_alert_is_rendered_on_mapped_physical_pixel(self):
        logical_to_physical = list(reversed(range(68)))
        display = MetroDisplay(self.stations_map, logical_to_physical)
        status = empty_status()
        status["stations"]["Radisson"] = STOPPED

        display.render(status, now_ms=0)

        logical_index = STATION_INDEX["Radisson"]
        physical_index = logical_to_physical[logical_index]
        self.assertEqual(display.pixels[physical_index], (51, 0, 0))
        self.assertNotEqual(display.pixels[logical_index], (51, 0, 0))

    def test_rejects_out_of_range_physical_indexes(self):
        invalid = list(range(68))
        invalid[-1] = 99
        with self.assertRaises(ValueError):
            MetroDisplay(self.stations_map, invalid)

    def test_night_mode_dims_alerts(self):
        display = MetroDisplay(self.stations_map)
        status = empty_status()
        status["stations"]["Radisson"] = STOPPED

        display.render(status, now_ms=0, night_mode=True)

        physical_index = STATION_INDEX["Radisson"]
        self.assertEqual(display.pixels[physical_index], (7, 0, 0))

    def test_night_ambient_breathes_slowly(self):
        status = empty_status()
        train_levels = [0.0] * 68

        dim_display = MetroDisplay(self.stations_map)
        dim_display.render(
            status,
            now_ms=0,
            train_levels=train_levels,
            night_mode=True,
        )
        bright_display = MetroDisplay(self.stations_map)
        bright_display.render(
            status,
            now_ms=9000,
            train_levels=train_levels,
            night_mode=True,
        )

        index = STATION_INDEX["Berri-UQAM"]
        self.assertGreater(
            sum(bright_display.pixels[index]),
            sum(dim_display.pixels[index]),
        )


if __name__ == "__main__":
    unittest.main()
