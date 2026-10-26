import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { loadPicks, loadPerformance } from '../../worker/index.js';
import { SOURCES } from '../../shared/picks.js';

function harness() {
  const values = new Map();
  const pending = [];
  const cache = { async match(key) { return values.get(key.url)?.clone(); }, async put(key, response) { values.set(key.url, response.clone()); } };
  const ctx = { waitUntil(task) { pending.push(task); } };
  return { cache, ctx, pending };
}
const exportData = (sport = 'MLB') => ({ meta: { generated_at: new Date().toISOString(), sport }, bets: [{ game_date: '2026-10-23', pick: 'Home', confidence: .7, edge: .08, odds: 120, tier: 'Elite', quote_observed_at: new Date().toISOString(), game_time: new Date(Date.now() + 86400000).toISOString() }] });

test('live data is normalized, ordered, validated, and retained; failures reuse the last valid snapshot', async () => {
  const originalFetch = globalThis.fetch;
  const { cache, ctx, pending } = harness();
  globalThis.fetch = async url => String(url).includes('status_manifest') ? Response.json({ sources: {}, aggregation_completed_at: '2026-10-23T16:00:00Z' }) : Response.json(exportData());
  try {
    const live = await loadPicks({}, ctx, cache);
    assert.equal(live.picks.length, Object.keys(SOURCES).length);
    assert.deepEqual(Object.keys(live.sources), Object.keys(SOURCES));
    assert.equal(live.sources.MLB.status, 'ok');
    assert.equal(live.picks.find(p => p.sport === 'NFL').sport, 'NFL');
    assert.equal(live.picks.find(p => p.sport === 'Esports').sport, 'Esports');
    await Promise.all(pending);
    globalThis.fetch = async () => { throw new Error('Network unavailable'); };
    const offline = await loadPicks({}, ctx, cache);
    assert.equal(offline.picks.length, Object.keys(SOURCES).length);
    assert.equal(offline.sources.MLB.status, 'fetch_failed');
    assert.equal(offline.sources.MLB.last_valid_cache, true);
    assert.match(offline.sources.MLB.errors[0], /last valid snapshot/);
  } finally { globalThis.fetch = originalFetch; }
});
test('invalid new exports do not replace retained valid picks', async () => {
  const originalFetch = globalThis.fetch;
  const { cache, ctx } = harness();
  await cache.put(new Request('https://sports-picks-grid.internal/last-valid/baseball'), Response.json(exportData()));
  globalThis.fetch = async () => Response.json({ meta: {}, bets: [{ pick: 'Invalid' }] });
  try {
    const result = await loadPicks({}, ctx, cache);
    assert.equal(result.picks.find(p => p.sport === 'MLB').pick, 'Home');
    assert.equal(result.sources.MLB.status, 'fetch_failed');
  } finally { globalThis.fetch = originalFetch; }
});
test('API dispatch preserves JSON 404s, method restrictions, caching and refresh bypass', async () => {
  const originalFetch = globalThis.fetch;
  const oldCaches = globalThis.caches;
  const { cache, ctx, pending } = harness();
  globalThis.caches = { default: cache };
  globalThis.fetch = async () => { throw new Error('Offline'); };
  const env = { ASSETS: { fetch: async () => new Response('Frontend') } };
  try {
    assert.equal((await worker.fetch(new Request('http://localhost/api/missing'), env, ctx)).status, 404);
    assert.equal((await worker.fetch(new Request('http://localhost/api/picks', { method: 'POST' }), env, ctx)).status, 405);
    assert.equal(await (await worker.fetch(new Request('http://localhost/'), env, ctx)).text(), 'Frontend');
    await cache.put(new Request('http://localhost/api/picks'), Response.json({ sentinel: true }));
    assert.deepEqual(await (await worker.fetch(new Request('http://localhost/api/picks'), env, ctx)).json(), { sentinel: true });
    const refreshed = await worker.fetch(new Request('http://localhost/api/picks?refresh=1'), env, ctx);
    assert.equal(refreshed.status, 200); assert.equal(refreshed.headers.get('cache-control'), 'no-store');
    assert.equal(Object.keys((await refreshed.json()).sources).length, Object.keys(SOURCES).length);
    await Promise.all(pending);
  } finally { globalThis.fetch = originalFetch; globalThis.caches = oldCaches; }
});
test('performance degrades to bundled unavailable grading without fabricated results', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('Offline'); };
  try {
    const result = await loadPerformance({});
    assert.equal(result.aggregate.status, 'unavailable');
    assert.equal(Object.keys(result.sports).length, Object.keys(SOURCES).length);
    assert.equal(Object.values(result.sports).filter(Boolean).length, 0);
  } finally { globalThis.fetch = originalFetch; }
});
