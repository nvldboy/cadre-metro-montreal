import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICO = ROOT / "pico"
sys.path.insert(0, str(PICO))

from stations import LINE_STATIONS, STATION_ORDER
from night_mode import is_night
from train_schedule import (
    _montreal_utc_offset,
    _timing_variation,
    feed_is_current,
    positions_at,
    station_levels,
    without_interrupted_lines,
)


class TrainScheduleTests(unittest.TestCase):
    def test_departures_receive_independent_stable_timing_variations(self):
        departures = (19800, 20400, 21000, 21600, 22200)
        variations = [_timing_variation(0, value) for value in departures]
        self.assertGreater(len(set(variations)), 1)
        self.assertEqual(
            variations,
            [_timing_variation(0, value) for value in departures],
        )

    def test_weekday_evening_has_trains_on_every_line(self):
        local = (2026, 7, 28, 20, 42, 0, 1, 209)
        previous = (2026, 7, 27, 20, 42, 0, 0, 208)
        positions = positions_at(local, previous)
        _, counts = station_levels(positions)

        self.assertGreater(len(positions), 20)
        self.assertTrue(all(count > 0 for count in counts))

    def test_fractional_time_interpolates_between_stations(self):
        local = (2026, 7, 28, 20, 42, 0, 1, 209)
        previous = (2026, 7, 27, 20, 42, 0, 0, 208)
        first = positions_at(local, previous, 0.1)
        second = positions_at(local, previous, 0.9)

        self.assertEqual(len(first), len(second))
        self.assertNotEqual(first, second)
        self.assertTrue(any(0.0 < position[3] < 1.0 for position in first))

    def test_station_levels_stay_in_valid_range(self):
        positions = [
            (0, 0, 1, 0.25, 0),
            (0, 2, 3, 0.75, 1),
        ]
        levels, counts = station_levels(positions)
        self.assertEqual(levels[0], 1.0)
        self.assertEqual(levels[1], 0.0)
        self.assertEqual(levels[2], 0.0)
        self.assertEqual(levels[3], 1.0)
        self.assertEqual(counts[0], 2)
        self.assertTrue(all(0.0 <= level <= 1.0 for level in levels))

    def test_marker_stays_at_departure_before_halfway(self):
        levels, _ = station_levels([(0, 0, 1, 0.49, 0)])
        self.assertEqual(levels[0], 1.0)
        self.assertEqual(levels[1], 0.0)

    def test_marker_moves_to_arrival_at_halfway(self):
        levels, _ = station_levels([(0, 0, 1, 0.50, 0)])
        self.assertEqual(levels[0], 0.0)
        self.assertEqual(levels[1], 1.0)

    def test_empty_network_keeps_every_station_off(self):
        levels, counts = station_levels([])
        self.assertTrue(all(level == 0.0 for level in levels))
        self.assertTrue(all(count == 0 for count in counts))

    def test_interruption_removes_only_affected_line(self):
        positions = [
            (0, 0, 1, 0.25, 0),
            (1, 27, 28, 0.50, 0),
            (2, 12, 56, 0.75, 0),
        ]
        status = {
            "green": "ok",
            "orange": "interrupted",
            "yellow": "ok",
            "blue": "ok",
        }
        running = without_interrupted_lines(positions, status)
        self.assertEqual([position[0] for position in running], [0, 2])

    def test_montreal_dst_offsets(self):
        self.assertEqual(
            _montreal_utc_offset((2026, 1, 15, 12, 0, 0, 3, 15)),
            -5 * 3600,
        )
        self.assertEqual(
            _montreal_utc_offset((2026, 7, 15, 12, 0, 0, 2, 196)),
            -4 * 3600,
        )

    def test_feed_covers_project_date(self):
        self.assertTrue(feed_is_current((2026, 7, 28, 20, 0, 0, 1, 209)))

    def test_extended_service_delays_night_mode(self):
        late = (2026, 8, 1, 1, 15, 0, 5, 213)
        previous_late = (2026, 7, 31, 1, 15, 0, 4, 212)
        closed = (2026, 8, 1, 2, 15, 0, 5, 213)
        previous_closed = (2026, 7, 31, 2, 15, 0, 4, 212)
        morning = (2026, 8, 1, 5, 45, 0, 5, 213)
        previous_morning = (2026, 7, 31, 5, 45, 0, 4, 212)

        late_positions = positions_at(late, previous_late)
        closed_positions = positions_at(closed, previous_closed)
        morning_positions = positions_at(morning, previous_morning)

        self.assertGreater(len(late_positions), 0)
        self.assertFalse(is_night(late, bool(late_positions)))
        self.assertEqual(closed_positions, [])
        self.assertTrue(is_night(closed, bool(closed_positions)))
        self.assertGreater(len(morning_positions), 0)
        self.assertFalse(is_night(morning, bool(morning_positions)))

    def test_stations_map_matches_python_station_table(self):
        station_map = json.loads(
            (PICO / "stations_map.json").read_text(encoding="utf-8")
        )
        self.assertEqual(tuple(station_map["stations"]), STATION_ORDER)
        for line_name, station_names in LINE_STATIONS.items():
            expected = [STATION_ORDER.index(name) for name in station_names]
            self.assertEqual(station_map["lines"][line_name], expected)


if __name__ == "__main__":
    unittest.main()
