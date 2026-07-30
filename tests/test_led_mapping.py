import json
import sys
import tempfile
import unittest
from pathlib import Path

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

from led_mapping import (
    load_draft,
    load_led_mapping,
    logical_to_physical,
    save_draft,
    save_led_mapping,
    validate_physical_to_logical,
)


class LedMappingTests(unittest.TestCase):
    def test_inverts_physical_chain_into_logical_station_lookup(self):
        # DEL physique 1 = station logique 2, etc.
        physical_to_logical = [2, 0, 3, 1]
        self.assertEqual(
            logical_to_physical(physical_to_logical),
            [1, 3, 0, 2],
        )

    def test_rejects_duplicates_missing_values_and_wrong_types(self):
        self.assertFalse(validate_physical_to_logical([0, 0, 2, 3], 4))
        self.assertFalse(validate_physical_to_logical([0, 1, 2], 4))
        self.assertFalse(validate_physical_to_logical([0, 1, 2, 4], 4))
        self.assertFalse(validate_physical_to_logical([0, 1, 2, True], 4))

    def test_partial_draft_accepts_unique_assignments(self):
        self.assertTrue(
            validate_physical_to_logical(
                [None, 2, None, 0],
                4,
                allow_partial=True,
            )
        )
        self.assertFalse(
            validate_physical_to_logical(
                [None, 2, None, 2],
                4,
                allow_partial=True,
            )
        )

    def test_final_mapping_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "led_mapping.json"
            save_led_mapping([2, 0, 3, 1], str(path))
            self.assertEqual(
                load_led_mapping(str(path), station_count=4),
                [1, 3, 0, 2],
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["physical_to_logical"], [2, 0, 3, 1])

    def test_draft_resumes_after_an_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "led_mapping_draft.json"
            draft = [None, 2, None, 0]
            save_draft(draft, str(path))
            self.assertEqual(load_draft(str(path), station_count=4), draft)

    def test_invalid_or_obsolete_files_start_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            final_path = Path(directory) / "led_mapping.json"
            draft_path = Path(directory) / "led_mapping_draft.json"
            final_path.write_text("{broken", encoding="utf-8")
            draft_path.write_text(
                json.dumps({
                    "version": 0,
                    "physical_to_logical": [0, 1, 2, 3],
                }),
                encoding="utf-8",
            )
            self.assertIsNone(
                load_led_mapping(str(final_path), station_count=4)
            )
            self.assertEqual(
                load_draft(str(draft_path), station_count=4),
                [None, None, None, None],
            )


if __name__ == "__main__":
    unittest.main()
