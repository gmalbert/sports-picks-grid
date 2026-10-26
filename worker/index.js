import snapshots from './snapshots.json' with { type: 'json' };
import { SOURCES, validateExport } from '../shared/picks.js';

const json = (data, status = 200) => Response.json(data, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
const raw = (repo, path, branch = 'main') => `https://raw.githubusercontent.com/${repo}/${branch}/${path}`;
async function fetchJSON(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(8000), headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
async function optionalJSON(url) { try { return await fetchJSON(url); } catch { return null; } }

export async function loadPicks(env, ctx, cache) {
  const repo = env.DATA_REPO || 'gmalbert/sports-picks-grid';
  const branch = env.DATA_BRANCH || 'main';
  const liveManifest = await optionalJSON(raw(repo, 'data_cache/status_manifest.json', branch));
  const manifest = liveManifest?.sources && typeof liveManifest.sources === 'object' ? liveManifest : snapshots.manifest;
  const sources = {};
  const picks = await Promise.all(Object.entries(SOURCES).map(async ([sport, { key, repo: sourceRepo }]) => {
    const cacheKey = new Request(`https://sports-picks-grid.internal/last-valid/${key}`);
    let candidate = await optionalJSON(raw(repo, `data_cache/${key}.json`, branch));
    let record = validateExport(candidate, sport);
    if (record.errors.length) {
      candidate = await optionalJSON(raw(`gmalbert/${sourceRepo}`, 'data_files/best_bets_today.json'));
      record = validateExport(candidate, sport);
    }
    const live = record.errors.length === 0;
    if (live) {
      ctx.waitUntil(cache.put(cacheKey, Response.json(candidate, { headers: { 'Cache-Control': 'public, max-age=604800' } })));
    } else {
      const retained = await cache.match(cacheKey);
      const cached = retained ? await retained.json() : null;
      const retainedRecord = validateExport(cached, sport);
      record = retainedRecord.errors.length ? validateExport(snapshots.sources[sport]?.picks, sport) : retainedRecord;
    }
    const manifestRecord = manifest?.sources?.[key] || {};
    // Source failures in the aggregator remain visible even when it retained valid rows.
    const manifestFailure = liveManifest && ['fetch_failed', 'pipeline_failed', 'export_missing'].includes(manifestRecord.status);
    sources[sport] = {
      ...manifestRecord, ...record, bets: undefined, repo: sourceRepo,
      status: !live ? 'fetch_failed' : manifestFailure ? manifestRecord.status : record.status,
      errors: !live ? ['Live sources unavailable; showing the last valid snapshot.', ...record.errors] : manifestFailure ? manifestRecord.errors || [] : record.errors,
      last_valid_cache: !live, bets_count: record.bets.length,
    };
    return record.bets;
  }));
  return { picks: picks.flat(), sources: Object.fromEntries(Object.keys(SOURCES).map(sport => [sport, sources[sport]])), updated_at: manifest?.aggregation_completed_at || null, fetched_at: new Date().toISOString() };
}

export async function loadPerformance(env) {
  const aggregateTask = optionalJSON(raw(env.DATA_REPO || 'gmalbert/sports-picks-grid', 'data_files/model_performance.json', env.DATA_BRANCH || 'main'));
  const results = await Promise.all(Object.entries(SOURCES).map(async ([sport, source]) => {
    const perf = await optionalJSON(raw(`gmalbert/${source.repo}`, 'data_files/model_performance.json')) || snapshots.sources[sport]?.performance;
    return [sport, perf && typeof perf === 'object' && !Array.isArray(perf) ? perf : null];
  }));
  return { aggregate: await aggregateTask || snapshots.performance, sports: Object.fromEntries(results) };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    if (request.method !== 'GET') return json({ error: 'Method not allowed' }, 405);
    if (!['/api/picks', '/api/performance'].includes(url.pathname)) return json({ error: 'Not found' }, 404);
    const cache = caches.default;
    const cacheKey = new Request(`${url.origin}${url.pathname}`);
    const existing = url.searchParams.get('refresh') !== '1' ? await cache.match(cacheKey) : null;
    if (existing) {
      const response = new Response(existing.body, existing);
      response.headers.set('Cache-Control', 'no-store');
      return response;
    }
    try {
      const data = url.pathname === '/api/picks' ? await loadPicks(env, ctx, cache) : await loadPerformance(env);
      // Never cache a recommendation beyond its quote expiry or match start.
      let maxAge = 3600;
      for (const pick of data.picks || []) if (pick.sport === 'Esports') {
        const expiry = Math.min(Date.parse(pick.quote_observed_at) + 13 * 3600000, Date.parse(pick.game_time));
        maxAge = Math.min(maxAge, Math.max(0, Math.floor((expiry - Date.now()) / 1000)));
      }
      const response = Response.json(data, { headers: { 'Cache-Control': `public, max-age=${maxAge}`, 'X-Content-Type-Options': 'nosniff' } });
      ctx.waitUntil(cache.put(cacheKey, response.clone()));
      // Browsers should revalidate via the Worker cache so Refresh always works.
      const result = new Response(response.body, response);
      result.headers.set('Cache-Control', 'no-store');
      return result;
    } catch (error) {
      console.error('API load failed', error);
      return json({ error: 'Unable to load data. Please try refreshing picks.' }, 502);
    }
  },
};
