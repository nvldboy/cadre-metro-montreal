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
from night_mode import anchored_clock_parts, is_night, is_night_hour
from power_safety import (
    color_for_pixel_driver,
    estimate_frame_current_ma,
    frame_requires_limiting,
    limit_frame,
)


class PowerSafetyTests(unittest.TestCase):
    def test_large_epoch_keeps_milliseconds_separate_from_float(self):
        epoch, milliseconds = anchored_clock_parts(1786327680, 1234)
        self.assertEqual(epoch, 1786327681)
        self.assertEqual(milliseconds, 234)
        self.assertIs(type(epoch), int)
        self.assertIs(type(milliseconds), int)

    def test_pixel_driver_compensates_red_green_order(self):
        self.assertEqual(color_for_pixel_driver((10, 20, 30)), (20, 10, 30))

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
        self.assertTrue(frame_requires_limiting(frame))

    def test_low_power_frame_does_not_trigger_warning(self):
        frame = [(0, 20, 0)] * NUMBER_OF_LEDS
        self.assertFalse(frame_requires_limiting(frame))

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
