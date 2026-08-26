import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publish_gtfs_update import _metadata


class GtfsPublicationTests(unittest.TestCase):
    def test_published_schedule_and_manifest_match_source(self):
        source = ROOT / "pico" / "metro_schedule_data.py"
        published = ROOT / "updates" / "metro_schedule_data.py"
        packaged = (
            ROOT
            / "PICO_2_W_PRET_A_COPIER"
            / "CONTENU_A_COPIER_SUR_LE_PICO"
            / "metro_schedule_data.py"
        )
        manifest_path = ROOT / "updates" / "latest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        feed, generated_at = _metadata(source)

        self.assertEqual(source.read_bytes(), published.read_bytes())
        self.assertEqual(source.read_bytes(), packaged.read_bytes())
        self.assertEqual(
            manifest["sha256"],
            hashlib.sha256(published.read_bytes()).hexdigest(),
        )
        self.assertEqual(manifest["size"], published.stat().st_size)
        self.assertEqual(
            (
                manifest["feed_start"],
                manifest["feed_end"],
                manifest["feed_version"],
            ),
            feed,
        )
        self.assertEqual(manifest["generated_at"], generated_at)

        package_manifest = {
            line.split(None, 1)[1]: line.split(None, 1)[0]
            for line in (
                ROOT / "PICO_2_W_PRET_A_COPIER" / "MANIFEST_SHA256.txt"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertEqual(
            package_manifest["metro_schedule_data.py"],
            hashlib.sha256(packaged.read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
