import unittest
from datetime import datetime, timezone

from utils.data_quality import (
    STATUS_NO_PICKS,
    STATUS_OFF_SEASON,
    STATUS_PIPELINE_PENDING,
    STATUS_STALE,
    validate_export,
)


NOW = datetime(2026, 7, 21, 12, tzinfo=timezone.utc)


def export(generated_at="2026-07-21T08:00:00+00:00", notes=None, bets=None):
    meta = {"sport": "Test", "generated_at": generated_at}
    if notes:
        meta["notes"] = notes
    return {"meta": meta, "bets": bets or []}


class DataQualityTests(unittest.TestCase):
    def test_empty_current_export_is_no_picks(self):
        result = validate_export(export(), "Test", now=NOW)
        self.assertEqual(result["status"], STATUS_NO_PICKS)
        self.assertEqual(result["errors"], [])

    def test_missing_pipeline_is_not_no_picks(self):
        result = validate_export(export(notes="picks_today.parquet not found"), "MLB", now=NOW)
        self.assertEqual(result["status"], STATUS_PIPELINE_PENDING)

    def test_explicit_off_season_can_be_old(self):
        result = validate_export(export("2026-04-30T02:00:00+00:00", notes="NFL off-season"), "NFL", now=NOW)
        self.assertEqual(result["status"], STATUS_OFF_SEASON)

    def test_unlabelled_old_export_is_stale(self):
        result = validate_export(export("2026-06-09T08:00:00+00:00"), "NBA", now=NOW)
        self.assertEqual(result["status"], STATUS_STALE)

    def test_bet_rows_require_canonical_fields(self):
        result = validate_export(export(bets=[{"game_date": "2026-07-22", "pick": "A"}]), "Test", now=NOW)
        self.assertEqual(result["status"], "pipeline_failed")
        self.assertTrue(any("missing confidence" in error for error in result["errors"]))
