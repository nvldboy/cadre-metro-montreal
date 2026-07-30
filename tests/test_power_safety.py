import sys
import unittest
from pathlib import Path

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

from config import (
    LED_CURRENT_LIMIT_MA,
    LED_MAX_CHANNEL_VALUE,
    NUMBER_OF_LEDS,
)
from night_mode import is_night, is_night_hour
from power_safety import estimate_frame_current_ma, limit_frame


class PowerSafetyTests(unittest.TestCase):
    def test_full_white_frame_is_clamped_below_current_budget(self):
        frame = [(255, 255, 255)] * NUMBER_OF_LEDS
        limited = limit_frame(frame)

        self.assertLessEqual(
            estimate_frame_current_ma(limited),
            LED_CURRENT_LIMIT_MA,
        )
        self.assertTrue(
            all(
                channel <= LED_MAX_CHANNEL_VALUE
                for color in limited
                for channel in color
            )
        )

    def test_negative_and_excessive_channels_are_clamped(self):
        frame = [(-50, 12, 999)] + [(0, 0, 0)] * (NUMBER_OF_LEDS - 1)
        limited = limit_frame(frame)
        self.assertEqual(limited[0], (0, 12, LED_MAX_CHANNEL_VALUE))

    def test_invalid_frame_size_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_frame([(0, 0, 0)])

    def test_night_mode_crosses_midnight(self):
        self.assertFalse(is_night_hour(22))
        self.assertTrue(is_night_hour(23))
        self.assertTrue(is_night_hour(0))
        self.assertTrue(is_night_hour(5))
        self.assertFalse(is_night_hour(6))

    def test_night_mode_can_be_disabled(self):
        self.assertFalse(is_night_hour(1, enabled=False))

    def test_late_train_keeps_display_awake(self):
        local_parts = (2026, 7, 31, 1, 15, 0, 4, 212)
        self.assertFalse(is_night(local_parts, trains_running=True))
        self.assertTrue(is_night(local_parts, trains_running=False))


if __name__ == "__main__":
    unittest.main()
