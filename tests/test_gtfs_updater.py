import asyncio
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PICO = Path(__file__).resolve().parents[1] / "pico"
sys.path.insert(0, str(PICO))

import gtfs_updater


def manifest(**overrides):
    result = {
        "schema": 1,
        "file": "metro_schedule_data.py",
        "size": 1234,
        "sha256": "a" * 64,
        "feed_start": "20260824",
        "feed_end": "20261231",
        "feed_version": "nouvelle-version",
        "generated_at": "2026-08-10T12:00:00+00:00",
    }
    result.update(overrides)
    return result


def schedule_text(item):
    return (
        '"""Horaire métro compact généré depuis le GTFS planifié de la STM."""\n'
        "FEED = {!r}\n"
        "GENERATED_AT = {!r}\n"
        "DATA = {!r}\n"
    ).format(
        (
            item["feed_start"],
            item["feed_end"],
            item["feed_version"],
        ),
        item["generated_at"],
        "horaire",
    )


class GtfsUpdaterTests(unittest.TestCase):
    def test_url_parser_supports_https_and_custom_http_port(self):
        self.assertEqual(
            gtfs_updater.parse_url(
                "https://raw.githubusercontent.com/user/repo/main/latest.json"
            ),
            (
                "https",
                "raw.githubusercontent.com",
                443,
                "/user/repo/main/latest.json",
            ),
        )
        self.assertEqual(
            gtfs_updater.parse_url("http://127.0.0.1:8765/updates/latest.json"),
            ("http", "127.0.0.1", 8765, "/updates/latest.json"),
        )

    def test_relative_file_cannot_escape_update_directory(self):
        with self.assertRaises(gtfs_updater.GtfsUpdateError):
            gtfs_updater.resolve_relative_url(
                "https://example.test/updates/latest.json",
                "../secrets.py",
            )

    def test_manifest_validation_and_version_comparison(self):
        candidate = gtfs_updater.validate_manifest(manifest())
        self.assertTrue(
            gtfs_updater.update_available(
                candidate,
                ("20260323", "20260823", "ancienne-version"),
                "2026-07-29T00:00:00+00:00",
            )
        )
        older = manifest(
            feed_start="20260323",
            feed_end="20260701",
            generated_at="2026-07-01T00:00:00+00:00",
        )
        self.assertFalse(
            gtfs_updater.update_available(
                older,
                ("20260323", "20260823", "actuelle"),
                "2026-07-29T00:00:00+00:00",
            )
        )

    def test_installation_can_be_confirmed_or_rolled_back(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            target = directory / "metro_schedule_data.py"
            temporary = directory / "metro_schedule_data.py.download"
            backup = directory / "metro_schedule_data.py.backup"
            target.write_text("ancien", encoding="utf-8")
            temporary.write_text("nouveau", encoding="utf-8")

            gtfs_updater.install_schedule(
                str(temporary),
                str(target),
                str(backup),
            )
            self.assertEqual(target.read_text(encoding="utf-8"), "nouveau")
            self.assertEqual(backup.read_text(encoding="utf-8"), "ancien")

            self.assertTrue(
                gtfs_updater.rollback_schedule(
                    str(target),
                    str(temporary),
                    str(backup),
                )
            )
            self.assertEqual(target.read_text(encoding="utf-8"), "ancien")

            temporary.write_text("nouveau", encoding="utf-8")
            gtfs_updater.install_schedule(
                str(temporary),
                str(target),
                str(backup),
            )
            gtfs_updater.confirm_schedule(str(backup))
            self.assertFalse(backup.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "nouveau")

    def test_recovery_restores_backup_after_interrupted_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            target = directory / "metro_schedule_data.py"
            temporary = directory / "metro_schedule_data.py.download"
            backup = directory / "metro_schedule_data.py.backup"
            backup.write_text("horaire intact", encoding="utf-8")
            temporary.write_text("partiel", encoding="utf-8")

            restored = gtfs_updater.recover_schedule(
                str(target),
                str(temporary),
                str(backup),
            )
            self.assertTrue(restored)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "horaire intact",
            )
            self.assertFalse(temporary.exists())

    def test_end_to_end_install_uses_manifest_and_relative_file(self):
        candidate = manifest()
        content = schedule_text(candidate).encode()
        candidate["size"] = len(content)
        candidate["sha256"] = hashlib.sha256(content).hexdigest()
        original_manifest_loader = gtfs_updater._download_manifest
        original_schedule_loader = gtfs_updater._download_schedule
        requested_urls = []

        async def fake_manifest_loader(url):
            requested_urls.append(url)
            return json.loads(json.dumps(candidate))

        async def fake_schedule_loader(url, path, expected_size, expected_hash):
            requested_urls.append(url)
            self.assertEqual(expected_size, len(content))
            self.assertEqual(expected_hash, hashlib.sha256(content).hexdigest())
            Path(path).write_bytes(content)
            return len(content)

        gtfs_updater._download_manifest = fake_manifest_loader
        gtfs_updater._download_schedule = fake_schedule_loader
        try:
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "metro_schedule_data.py"
                target.write_text("ancien horaire", encoding="utf-8")
                updated = asyncio.run(
                    gtfs_updater.check_and_install_update(
                        "https://example.test/updates/latest.json",
                        ("20260323", "20260823", "ancienne"),
                        "2026-07-29T00:00:00+00:00",
                        target=str(target),
                    )
                )
                self.assertTrue(updated)
                self.assertEqual(target.read_bytes(), content)
                self.assertTrue(Path(str(target) + ".backup").exists())
        finally:
            gtfs_updater._download_manifest = original_manifest_loader
            gtfs_updater._download_schedule = original_schedule_loader

        self.assertEqual(
            requested_urls,
            [
                "https://example.test/updates/latest.json",
                "https://example.test/updates/metro_schedule_data.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
