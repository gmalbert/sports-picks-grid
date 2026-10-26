// Compatibility is scoped to known sources; the canonical validator stays strict.
const LEGACY_TIERS = new Set(['portugal-soccer', 'netherlands-soccer', 'belgium-soccer', 'scotland-premiership', 'turkey-soccer', 'horse-racing-predictions', 'golf-predictions']);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const tier = edge => {
  const value = Math.abs(edge) > 1 ? edge / 100 : edge;
  return value >= .06 ? 'Elite' : value >= .03 ? 'Strong' : value >= .01 ? 'Good' : 'Standard';
};
const object = value => value && typeof value === 'object' && !Array.isArray(value);

export function normalizeSource(data, repo) {
  if (!object(data)) return data;
  if (repo === 'wnba-predictions' && 'games' in data) return adaptWNBA(data);
  if (!LEGACY_TIERS.has(repo) || !object(data.meta) || !Array.isArray(data.bets)) return data;
  const result = structuredClone(data);
  let changed = 0;
  for (const bet of result.bets) {
    if (object(bet) && finite(bet.edge) && bet.tier !== tier(bet.edge)) {
      bet.source_tier = bet.tier ?? null;
      bet.tier = tier(bet.edge);
      changed++;
    }
  }
  result.meta.tier_definition = 'edge-v1';
  if (changed) result.meta.normalized_tier_count = changed;
  if (!result.bets.length && String(result.meta.notes || '').toLowerCase().includes('no odds artifact')) result.meta.status = 'pipeline_pending';
  return result;
}

function adaptWNBA(data) {
  if (!Array.isArray(data.games)) return data;
  const timestamps = [data.generated_at, ...data.games.filter(object).map(g => g.generated_at)].filter(t => typeof t === 'string' && Number.isFinite(Date.parse(t)));
  const generated = timestamps.sort((a, b) => Date.parse(a) - Date.parse(b))[0] || data.generated_at || '';
  const bets = [];
  for (const game of data.games) {
    if (!object(game) || game.status !== 'ready' || game.paper_only !== false || game.release_gate_status !== 'production_ready') continue;
    const probability = game.home_win_prob, market = game.market_home_prob;
    if (!finite(probability) || !finite(market) || probability < 0 || probability > 1 || market <= 0 || market >= 1) continue;
    const home = probability >= market;
    const edge = Math.round(Math.abs(probability - market) * 1e6) / 1e6;
    if (edge < .01) continue;
    bets.push({
      game_id: game.game_id ?? null, game_date: game.game_date ?? null, game_time: game.scheduled_start ?? null,
      game: `${game.away_team} @ ${game.home_team}`, home_team: game.home_team, away_team: game.away_team,
      bet_type: 'Moneyline', pick: home ? game.home_team : game.away_team,
      confidence: home ? probability : 1 - probability, edge, tier: tier(edge), odds: null, line: null,
      generated_at: game.generated_at || generated, paper_only: false, release_gate_status: 'production_ready',
    });
  }
  return { meta: {
    sport: 'WNBA', generated_at: generated, tier_definition: 'edge-v1', source_format: 'wnba-web-v1',
    source_generated_at: data.generated_at, withheld_games: data.games.length - bets.length,
    notes: 'WNBA web predictions; paper-only, no-bet, unreleased, and unpriced rows are withheld',
  }, bets };
}
