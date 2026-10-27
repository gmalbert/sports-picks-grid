import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { normalizeSource } from '../../shared/source-adapters.js';
import { SOURCES, validateExport } from '../../shared/picks.js';

const fixtures = JSON.parse(readFileSync(new URL('../fixtures/source_adapters.json', import.meta.url), 'utf8'));
for (const c of fixtures) test(`source contract: ${c.name}`, () => {
  const original = structuredClone(c.data);
  const data = normalizeSource(c.data, c.repo);
  const result = validateExport(data, c.sport, new Date('2026-10-26T18:00:00Z'));
  assert.equal(result.status, c.status);
  assert.equal(result.errors.length, c.errors || 0);
  assert.deepEqual((data.bets || []).map(b => b.tier), c.tiers);
  assert.equal(data.meta?.generated_at ?? null, c.generated_at);
  assert.deepEqual(normalizeSource(data, c.repo), data);
  assert.deepEqual(c.data, original);
});

test('registry includes all eight requested sources with distinct cache keys', () => {
  assert.equal(Object.keys(SOURCES).length, 26);
  assert.equal(new Set(Object.values(SOURCES).map(s => s.key)).size, 26);
  assert.equal(SOURCES.WNBA.path, 'frontend/public/data/predictions.json');
});
