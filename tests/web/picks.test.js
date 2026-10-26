import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SETTINGS, applySettings, validateExport, edge, odds, confidence, timeLabel, todayISO } from '../../shared/picks.js';

const now = new Date('2026-10-23T16:00:00Z');
const bet = (overrides = {}) => ({ sport: 'MLB', game_date: '2026-10-23', pick: 'Home', tier: 'Elite', confidence: .7, edge: .08, odds: 120, ...overrides });
const payload = bets => ({ meta: { generated_at: now.toISOString() }, bets });

test('esports never displays expired quotes, future quote timestamps, or started matches', () => {
  const good = bet({ sport: 'Esports', quote_observed_at: '2026-10-23T12:00:00Z', game_time: '2026-10-23T22:00:00Z' });
  const data = payload([good, { ...good, quote_observed_at: '2026-10-22T12:00:00Z' },
    { ...good, quote_observed_at: '2026-10-24T12:00:00Z' }, { ...good, game_time: '2026-10-23T15:00:00Z' }]);
  const record = validateExport(data, 'Esports', now);
  assert.equal(record.errors.length, 0);
  assert.equal(record.bets.length, 1);
  assert.equal(record.bets[0].sport, 'Esports');
});
test('window includes today through day seven and excludes historical and day eight', () => {
  const dates = ['2026-10-22', '2026-10-23', '2026-10-30', '2026-10-31'];
  assert.deepEqual(applySettings(dates.map(game_date => bet({ game_date })), DEFAULT_SETTINGS, '2026-10-23').map(b => b.game_date), dates.slice(1, 3));
});
test('filters tiers and thresholds before capping each sport by confidence', () => {
  const settings = { ...DEFAULT_SETTINGS, min_confidence: .6, min_edge: .06, max_picks: { MLB: 1 } };
  const rows = [bet({ pick: 'Low', confidence: .55 }), bet({ pick: 'Best', confidence: .9, edge: 8 }), bet({ pick: 'Second' }), bet({ sport: 'NFL' }), bet({ tier: 'Standard' }), bet({ edge: null })];
  assert.deepEqual(applySettings(rows, settings, '2026-10-23').map(b => b.pick), ['Best', 'Home']);
});
test('null market fields are allowed but malformed rows reject the entire export', () => {
  assert.equal(validateExport(payload([bet({ edge: null, odds: null, confidence: null })]), 'MLB', now).errors.length, 0);
  for (const row of [null, [], { ...bet(), tier: 'Other' }, { ...bet(), game_date: '2026-02-30' }, { pick: 'Missing fields' }]) {
    const record = validateExport(payload([row]), 'MLB', now);
    assert.equal(record.status, 'pipeline_failed'); assert.equal(record.bets.length, 0);
  }
});
test('canonical edge tiers include percentage units and negative Standard edge', () => {
  assert.equal(validateExport(payload([bet({ edge: 8 })]), 'MLB', now).errors.length, 0);
  assert.equal(validateExport(payload([bet({ edge: -.01, tier: 'Standard' })]), 'MLB', now).errors.length, 0);
  assert.equal(validateExport(payload([bet({ edge: .04 })]), 'MLB', now).status, 'pipeline_failed');
});
test('source freshness is sport specific and off-season is preserved', () => {
  const data = payload([]); data.meta.generated_at = '2026-10-22T20:00:00Z';
  assert.equal(validateExport(data, 'Tennis', now).status, 'stale');
  assert.equal(validateExport(data, 'MLB', now).status, 'no_picks');
  data.meta.status = 'off_season'; data.meta.generated_at = '2020-01-01T00:00:00Z';
  assert.equal(validateExport(data, 'MLB', now).status, 'off_season');
});
test('formatters retain Streamlit odds, confidence, edge and time conventions', () => {
  assert.equal(edge(.08), '+8.0%'); assert.equal(edge(8), '+8.0%'); assert.equal(edge(null), '—');
  assert.equal(odds(135), '+135'); assert.equal(odds(-140), '-140'); assert.equal(odds(null), '—');
  assert.equal(confidence(.725), '72.5%'); assert.equal(timeLabel('2026-10-23T19:05:00Z'), '7:05 PM UTC');
});
test('dashboard date uses Eastern time around UTC midnight', () => {
  assert.equal(todayISO(new Date('2026-10-24T01:00:00Z')), '2026-10-23');
});
