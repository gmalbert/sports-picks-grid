import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from utils.source_adapters import normalize_source
from utils.data_quality import validate_export
from utils.sources import SOURCES, source_url

NOW = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)


class SourceAdapterTests(unittest.TestCase):
    def test_shared_contract_fixtures(self):
        fixtures = json.loads((Path(__file__).parent / "fixtures/source_adapters.json").read_text(encoding="utf-8"))
        for case in fixtures:
            with self.subTest(name=case["name"]):
                original = json.loads(json.dumps(case["data"]))
                data = normalize_source(case["data"], case["repo"])
                record = validate_export(data, case["sport"], now=NOW)
                self.assertEqual(record["status"], case["status"])
                self.assertEqual(len(record["errors"]), case.get("errors", 0))
                self.assertEqual([b["tier"] for b in data.get("bets", [])], case["tiers"])
                self.assertEqual(data.get("meta", {}).get("generated_at"), case["generated_at"])
                self.assertEqual(normalize_source(data, case["repo"]), data)
                self.assertEqual(case["data"], original)

    def test_registry_has_all_requested_sources_and_alternate_wnba_path(self):
        self.assertEqual(len(SOURCES), 26)
        repos = {s["repo"] for s in SOURCES.values()}
        self.assertTrue({"portugal-soccer", "netherlands-soccer", "belgium-soccer", "scotland-premiership", "turkey-soccer", "horse-racing-predictions", "golf-predictions", "wnba-predictions"}.issubset(repos))
        self.assertTrue(source_url("wnba-predictions").endswith("frontend/public/data/predictions.json"))
        self.assertEqual(len({s["key"] for s in SOURCES.values()}), 26)


if __name__ == "__main__":
    unittest.main()
