import json
import tempfile
import unittest
from pathlib import Path

from scripts import grade_results


class GradeResultsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.archive = self.root / "history" / "2026-07-21"
        self.archive.mkdir(parents=True)
        self.results_json = self.root / "results.json"
        self.output = self.root / "graded_results.json"
        self.performance = self.root / "model_performance.json"
        self.originals = (
            grade_results.ARCHIVE_DIR,
            grade_results.RESULTS_JSON,
            grade_results.RESULTS_CSV,
            grade_results.OUTPUT,
            grade_results.PERFORMANCE,
        )
        grade_results.ARCHIVE_DIR = self.root / "history"
        grade_results.RESULTS_JSON = self.results_json
        grade_results.RESULTS_CSV = self.root / "missing.csv"
        grade_results.OUTPUT = self.output
        grade_results.PERFORMANCE = self.performance

    def tearDown(self):
        (
            grade_results.ARCHIVE_DIR,
            grade_results.RESULTS_JSON,
            grade_results.RESULTS_CSV,
            grade_results.OUTPUT,
            grade_results.PERFORMANCE,
        ) = self.originals

    def test_grades_win_loss_and_push_with_flat_stakes(self):
        archive = {
            "meta": {"sport": "Test", "generated_at": "2026-07-21T08:00:00Z"},
            "bets": [
                {"game_date": "2026-07-21", "game": "A vs B", "pick": "A", "tier": "Elite", "odds": 150},
                {"game_date": "2026-07-21", "game": "C vs D", "pick": "C", "tier": "Elite", "odds": -110},
                {"game_date": "2026-07-21", "game": "E vs F", "pick": "E", "tier": "Elite", "odds": 100},
            ],
        }
        self.archive.joinpath("test.json").write_text(json.dumps(archive), encoding="utf-8")
        self.results_json.write_text(json.dumps([
            {"sport": "Test", "game_date": "2026-07-21", "game": "A vs B", "pick": "A", "outcome": "win"},
            {"sport": "Test", "game_date": "2026-07-21", "game": "C vs D", "pick": "C", "outcome": "loss"},
            {"sport": "Test", "game_date": "2026-07-21", "game": "E vs F", "pick": "E", "outcome": "push"},
        ]), encoding="utf-8")

        self.assertEqual(grade_results.main(), 0)
        performance = json.loads(self.performance.read_text(encoding="utf-8"))
        group = performance["groups"]["Test:Elite"]
        self.assertEqual(group["settled_bets"], 2)
        self.assertEqual(group["wins"], 1)
        self.assertAlmostEqual(group["win_rate"], 0.5)
        self.assertAlmostEqual(group["profit_units"], 0.5, places=3)
        self.assertAlmostEqual(group["roi"], 0.1667, places=3)


if __name__ == "__main__":
    unittest.main()
