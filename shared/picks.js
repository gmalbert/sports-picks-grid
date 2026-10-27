import sources from '../data_files/sources.json' with { type: 'json' };

export const SOURCES = sources;
export const TIERS = ['Elite', 'Strong', 'Good', 'Standard'];
export const BADGES = { Elite: '🔥', Strong: '✅', Good: '➡', Standard: '⚪' };
export const DEFAULT_SETTINGS = { min_confidence: 0, min_edge: 0, tiers: TIERS.slice(0, 3), max_picks: { __default__: 50, TableTennis: 20, Cricket: 20, Darts: 15, Boxing: 15, Tennis: 30 } };
export const STATUS_LABELS = {
  ok: 'Current', no_picks: 'No qualifying picks today', off_season: 'Off-season',
  pipeline_pending: "Pipeline has not produced today's data", pipeline_failed: 'Pipeline failed',
  export_missing: 'Export file missing', fetch_failed: 'Fetch failed; last valid snapshot retained', stale: 'Source is stale',
};
export const statusLabel = value => STATUS_LABELS[value] || 'Unknown source status';
export const numeric = value => value !== null && value !== '' && value !== undefined && Number.isFinite(Number(value)) ? Number(value) : null;
export const edgeDecimal = value => numeric(value) === null ? null : Math.abs(Number(value)) > 1 ? Number(value) / 100 : Number(value);
export const confidence = value => numeric(value) === null ? '—' : `${(Number(value) * 100).toFixed(1)}%`;
export const edge = value => {
  const n = edgeDecimal(value);
  if (n === null) return '—';
  const percent = Math.max(-99.9, Math.min(99.9, n * 100));
  return `${percent >= 0 ? '+' : ''}${percent.toFixed(1)}%`;
};
export const odds = value => numeric(value) === null ? '—' : `${Number(value) >= 0 ? '+' : ''}${Math.trunc(Number(value))}`;
export const todayISO = (now = new Date()) => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
export const dateLabel = value => value ? new Date(`${value}T12:00:00Z`).toLocaleDateString('en-US', { timeZone: 'UTC', month: 'short', day: '2-digit', year: 'numeric' }) : '—';
export function timeLabel(value) {
  if (!value) return '—';
  if (!String(value).includes('T')) return String(value);
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return `${parsed.toLocaleTimeString('en-US', { timeZone: 'UTC', hour: 'numeric', ...(parsed.getUTCMinutes() ? { minute: '2-digit' } : {}) })} UTC`;
}
export const sortPicks = picks => [...picks].sort((a, b) => (TIERS.indexOf(a.tier) - TIERS.indexOf(b.tier)) || ((numeric(b.confidence) ?? -Infinity) - (numeric(a.confidence) ?? -Infinity)));
export function applySettings(picks, settings, today = todayISO()) {
  const end = new Date(`${today}T12:00:00Z`);
  end.setUTCDate(end.getUTCDate() + 7);
  const cutoff = end.toISOString().slice(0, 10);
  const tiers = settings.tiers.length ? settings.tiers : DEFAULT_SETTINGS.tiers;
  const groups = new Map();
  for (const pick of picks) {
    if (!pick.game_date || pick.game_date < today || pick.game_date > cutoff || !tiers.includes(pick.tier)) continue;
    if (settings.min_confidence > 0 && (numeric(pick.confidence) ?? 0) < settings.min_confidence) continue;
    if (settings.min_edge > 0 && (edgeDecimal(pick.edge) ?? 0) < settings.min_edge) continue;
    if (!groups.has(pick.sport)) groups.set(pick.sport, []);
    groups.get(pick.sport).push(pick);
  }
  return sortPicks([...groups.entries()].flatMap(([sport, rows]) => rows.sort((a, b) => (numeric(b.confidence) ?? -Infinity) - (numeric(a.confidence) ?? -Infinity)).slice(0, settings.max_picks[sport] ?? DEFAULT_SETTINGS.max_picks[sport] ?? settings.max_picks.__default__ ?? 50)));
}
export function validateExport(data, sport, now = new Date()) {
  const errors = [];
  if (!data || typeof data !== 'object' || Array.isArray(data)) return { status: 'pipeline_failed', errors: ['export is not a JSON object'], bets: [] };
  const meta = data.meta && typeof data.meta === 'object' && !Array.isArray(data.meta) ? data.meta : {};
  if (meta !== data.meta) errors.push('meta must be an object');
  let bets = Array.isArray(data.bets) ? data.bets : [];
  if (!Array.isArray(data.bets)) errors.push('bets must be an array');
  const generated = Date.parse(meta.generated_at);
  if (!Number.isFinite(generated)) errors.push('meta.generated_at must be a valid ISO-8601 timestamp');
  bets.forEach((bet, i) => {
    if (!bet || typeof bet !== 'object' || Array.isArray(bet)) { errors.push(`bets[${i}] must be an object`); return; }
    for (const field of ['game_date', 'pick', 'confidence', 'edge', 'odds', 'tier']) if (!(field in bet)) errors.push(`bets[${i}] missing ${field}`);
    if (bet.game_date != null && (!/^\d{4}-\d{2}-\d{2}$/.test(bet.game_date) || !Number.isFinite(Date.parse(bet.game_date)) || new Date(bet.game_date).toISOString().slice(0, 10) !== bet.game_date)) errors.push(`bets[${i}].game_date is invalid`);
    if (!TIERS.includes(bet.tier)) errors.push(`bets[${i}].tier is invalid`);
    if (typeof bet.edge === 'number' && Number.isFinite(bet.edge)) {
      const n = edgeDecimal(bet.edge);
      const expected = n >= .06 ? 'Elite' : n >= .03 ? 'Strong' : n >= .01 ? 'Good' : 'Standard';
      if (bet.tier !== expected) errors.push(`bets[${i}].tier=${bet.tier} disagrees with edge-v1 (${expected})`);
    }
  });
  const notes = String(meta.notes || '').toLowerCase();
  // A daily export can outlive its quote or its match. Never display those
  // esports recommendations from a retained cache, even when the file is valid.
  if (sport === 'Esports') bets = bets.filter(bet => {
    const quote = Date.parse(bet?.quote_observed_at);
    const start = Date.parse(bet?.game_time);
    return Number.isFinite(quote) && quote <= now.getTime() && now.getTime() - quote <= 13 * 3600000 && Number.isFinite(start) && start > now.getTime();
  });
  let status = STATUS_LABELS[meta.status] ? meta.status : /off[- ]season/.test(notes) ? 'off_season' : /not found|pending|may not have run/.test(notes) ? 'pipeline_pending' : /failed|error/.test(notes) ? 'pipeline_failed' : bets.length ? 'ok' : 'no_picks';
  const age_hours = Number.isFinite(generated) ? Math.max(0, (now.getTime() - generated) / 3600000) : null;
  if (['ok', 'no_picks'].includes(status) && age_hours > (['TableTennis', 'Cricket', 'Darts', 'Tennis'].includes(sport) ? 18 : 36)) status = 'stale';
  if (errors.length) status = 'pipeline_failed';
  return { sport, status, errors, age_hours, generated_at: meta.generated_at || '', bets: errors.length ? [] : bets.map(bet => ({ ...bet, sport, generated_at: bet.generated_at || meta.generated_at })) };
}
