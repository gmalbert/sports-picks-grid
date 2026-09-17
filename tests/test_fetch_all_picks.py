import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import fetch_all_picks


NOW = datetime(2026, 7, 21, 12, tzinfo=timezone.utc)


class FetchAllPicksTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cache_dir = fetch_all_picks.CACHE_DIR
        self.original_fetch_json = fetch_all_picks.fetch_json
        self.original_fetch_sha = fetch_all_picks.fetch_source_sha
        fetch_all_picks.CACHE_DIR = self.temp_dir

    def tearDown(self):
        fetch_all_picks.CACHE_DIR = self.original_cache_dir
        fetch_all_picks.fetch_json = self.original_fetch_json
        fetch_all_picks.fetch_source_sha = self.original_fetch_sha

    def test_fetch_failure_preserves_last_valid_cache(self):
        cache_file = self.temp_dir / "darts.json"
        cache_file.write_text(json.dumps({"meta": {"status": "ok"}, "bets": []}), encoding="utf-8")
        fetch_all_picks.fetch_json = lambda session, url: (None, 404, "HTTP 404")

        result = fetch_all_picks.fetch_one("darts", "darts", object(), NOW)

        self.assertEqual(result["status"], "export_missing")
        self.assertTrue(result["last_valid_cache"])
        self.assertEqual(json.loads(cache_file.read_text())["meta"]["status"], "ok")

    def test_valid_export_is_cached_and_archived(self):
        payload = {
            "meta": {"sport": "Boxing", "generated_at": "2026-07-21T08:00:00+00:00"},
            "bets": [],
        }
        fetch_all_picks.fetch_json = lambda session, url: (payload, 200, None)
        fetch_all_picks.fetch_source_sha = lambda session, repo: "test-sha"

        result = fetch_all_picks.fetch_one("boxing", "boxing", object(), NOW)

        self.assertEqual(result["status"], "no_picks")
        self.assertEqual(result["source_commit"], "test-sha")
        self.assertTrue((self.temp_dir / "boxing.json").exists())
        cached = json.loads((self.temp_dir / "boxing.json").read_text())
        self.assertEqual(cached["meta"]["source_commit"], "test-sha")
        self.assertTrue((self.temp_dir / "history" / "2026-07-21" / "boxing.json").exists())


if __name__ == "__main__":
    unittest.main()
