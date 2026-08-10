import sys
import unittest
from pathlib import Path

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

from status_animation import (
    API_STALE,
    BOOT,
    CLOCK_SYNC,
    CONFIG_ERROR,
    FATAL_ERROR,
    GTFS_ERROR,
    GTFS_EXPIRED,
    GTFS_UPDATE_ERROR,
    GTFS_UPDATE_SUCCESS,
    GTFS_UPDATING,
    LINE_TEST,
    POWER_LIMITED,
    READY,
    SCHEDULE_LOADING,
    SETUP_PORTAL,
    WIFI_CONNECTED,
    WIFI_CONNECTING,
    WIFI_RECONNECTING,
    WIFI_RETRY,
    WIFI_UNAVAILABLE,
    recovery_frame,
    select_runtime_state,
    state_frame,
)


class StatusAnimationTests(unittest.TestCase):
    def test_every_state_returns_a_safe_sized_rgb_frame(self):
        states = (
            BOOT,
            LINE_TEST,
            WIFI_CONNECTING,
            WIFI_RETRY,
            WIFI_CONNECTED,
            CLOCK_SYNC,
            SCHEDULE_LOADING,
            READY,
            CONFIG_ERROR,
            SETUP_PORTAL,
            WIFI_UNAVAILABLE,
            WIFI_RECONNECTING,
            GTFS_ERROR,
            GTFS_EXPIRED,
            GTFS_UPDATING,
            GTFS_UPDATE_SUCCESS,
            GTFS_UPDATE_ERROR,
            API_STALE,
            FATAL_ERROR,
            POWER_LIMITED,
        )
        line_groups = {
            "green": (0, 1),
            "orange": (2, 3),
            "yellow": (4,),
            "blue": (5, 6),
        }
        line_colors = {
            "green": (0, 255, 10),
            "orange": (255, 65, 0),
            "yellow": (255, 170, 0),
            "blue": (0, 8, 255),
        }
        for state in states:
            frame = state_frame(
                state,
                400,
                68,
                station_colors=[(10, 20, 30)] * 68,
                line_groups=line_groups,
                line_colors=line_colors,
            )
            self.assertEqual(len(frame), 68, state)
            self.assertTrue(
                all(
                    len(color) == 3
                    and all(0 <= channel <= 255 for channel in color)
                    for color in frame
                ),
                state,
            )

    def test_configuration_error_uses_long_short_short_signature(self):
        long_flash = state_frame(CONFIG_ERROR, 100)
        pause = state_frame(CONFIG_ERROR, 650)
        short_flash = state_frame(CONFIG_ERROR, 850)

        self.assertTrue(any(color != (0, 0, 0) for color in long_flash))
        self.assertTrue(all(color == (0, 0, 0) for color in pause))
        self.assertTrue(any(color != (0, 0, 0) for color in short_flash))

    def test_runtime_warning_priority_is_deterministic(self):
        self.assertEqual(
            select_runtime_state(False, False, explicit_state=GTFS_UPDATING),
            GTFS_UPDATING,
        )
        self.assertEqual(select_runtime_state(False, True), WIFI_RECONNECTING)
        self.assertEqual(select_runtime_state(True, False), GTFS_EXPIRED)
        self.assertEqual(select_runtime_state(True, True, api_stale=True), API_STALE)
        self.assertIsNone(select_runtime_state(True, True))

    def test_expired_schedule_warning_is_quiet_between_sweeps(self):
        active = state_frame(GTFS_EXPIRED, 600)
        quiet = state_frame(GTFS_EXPIRED, 5000)
        self.assertTrue(any(color != (0, 0, 0) for color in active))
        self.assertTrue(all(color == (0, 0, 0) for color in quiet))

    def test_recovery_sweep_only_uses_recovered_line(self):
        groups = {"orange": (10, 11, 12), "green": (0, 1, 2)}
        colors = {"orange": (255, 65, 0), "green": (0, 255, 10)}
        frame = recovery_frame(800, ("orange",), 68, groups, colors)
        active = [index for index, color in enumerate(frame) if color != (0, 0, 0)]
        self.assertEqual(len(active), 1)
        self.assertIn(active[0], groups["orange"])


if __name__ == "__main__":
    unittest.main()
