import json
import tempfile
import unittest
from pathlib import Path

from app.core.versioned_config import VersionedConfigStore, ConfigError


class TestVersionedConfigStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.media = self.base / "music"
        self.media.mkdir(parents=True, exist_ok=True)
        (self.media / "a.mp3").touch()
        (self.media / "b.mp3").touch()
        self.config = self.base / "bells.conf"
        self.store = VersionedConfigStore(self.config, self.media)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reject_missing_version(self):
        with self.assertRaises(ConfigError):
            self.store.parse_payload(json.dumps({"entries": []}))

    def test_expand_collection_and_all_day_preset(self):
        payload = {
            "version": "v1",
            "collections": {"pool": ["a.mp3", "b.mp3"]},
            "presets": {
                "hourly": {
                    "mode": "all_day",
                    "days": [1],
                    "start": "08:00",
                    "end": "10:00",
                    "interval_minutes": 60,
                }
            },
            "entries": [{"preset": "hourly", "sources": ["@pool"], "days": [], "times": []}],
        }
        self.store.save_payload(payload)
        entries = self.store.load_runtime_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["filenames"], ["a.mp3", "b.mp3"])
        self.assertEqual([t["time"] for t in entries[0]["times"]], [(8, 0), (9, 0), (10, 0)])
        self.assertEqual(entries[0]["days"], [1])

    def test_migrate_legacy(self):
        self.config.write_text("a.mp3, 08:00\n", encoding="utf-8")
        migrated = self.store.migrate_legacy_config(create_backup=True)
        self.assertEqual(migrated["version"], "v1")
        self.assertTrue((self.base / "bells.legacy.bak").exists())
        payload = self.store.load_payload()
        self.assertEqual(payload["entries"][0]["sources"], ["a.mp3"])
        self.assertEqual(payload["entries"][0]["times"], ["08:00"])

    def test_validate_preview(self):
        payload = {
            "version": "v1",
            "collections": {},
            "presets": {},
            "entries": [{"preset": "", "days": [1], "times": ["08:00-08:30"], "sources": ["a.mp3"]}],
        }
        errors, warnings, preview = self.store.validate_payload(payload)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIn("08:00-08:30", preview["1"])


if __name__ == "__main__":
    unittest.main()
