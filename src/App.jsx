import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { SOURCES, TIERS, BADGES, DEFAULT_SETTINGS, statusLabel, todayISO, applySettings, sortPicks } from '../shared/picks.js';
import { Notice, Metrics, PicksTable, DataTable, BestCard, Footer } from './components.jsx';

const PAGES = [ ['today', '📅', "Today's Picks"], ['sport', '🏆', 'By Sport'], ['best', '🔥', 'Best Bets'], ['performance', '📊', 'Performance'], ['about', 'ℹ️', 'About'], ['settings', '⚙️', 'Settings'] ];
const cloneDefaults = () => structuredClone(DEFAULT_SETTINGS);
function savedSettings() {
  try {
    const value = JSON.parse(sessionStorage.getItem('sports-picks-settings-v1'));
    if (!value || !Array.isArray(value.tiers) || !value.max_picks) return cloneDefaults();
    return {
      min_confidence: Math.max(0, Math.min(.95, Number(value.min_confidence) || 0)),
      min_edge: Math.max(0, Math.min(.2, Number(value.min_edge) || 0)),
      tiers: value.tiers.filter(t => TIERS.includes(t)),
      max_picks: Object.fromEntries(Object.entries({ ...DEFAULT_SETTINGS.max_picks, ...value.max_picks }).map(([s, n]) => [s, Math.max(5, Math.min(100, Number(n) || 50))])),
    };
  } catch { return cloneDefaults(); }
}
const currentPage = () => PAGES.some(([key]) => key === location.hash.slice(1)) ? location.hash.slice(1) : 'today';
async function getData(path, signal) {
  const response = await fetch(path, { cache: 'no-store', signal });
  if (!response.ok) throw new Error('Unable to load data. Please try refreshing picks.');
  return response.json();
}

export default function App() {
  const [page, setPage] = useState(currentPage);
  const [sidebar, setSidebar] = useState(() => window.innerWidth > 760);
  const [data, setData] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [settings, setSettings] = useState(savedSettings);
  const [loading, setLoading] = useState(true);
  const [perfLoading, setPerfLoading] = useState(false);
  const [error, setError] = useState('');
  const [perfError, setPerfError] = useState('');
  const [today, setToday] = useState(todayISO);
  const picksRequest = useRef(null);
  const perfRequest = useRef(null);

  const loadPicks = useCallback(async (refresh = false) => {
    picksRequest.current?.abort();
    const controller = new AbortController(); picksRequest.current = controller;
    setLoading(true); setError('');
    try { setData(await getData(`/api/picks${refresh ? '?refresh=1' : ''}`, controller.signal)); }
    catch (e) { if (!controller.signal.aborted) setError(e.message); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, []);
  const loadPerformance = useCallback(async (refresh = false) => {
    perfRequest.current?.abort();
    const controller = new AbortController(); perfRequest.current = controller;
    setPerfLoading(true); setPerfError('');
    try { setPerformance(await getData(`/api/performance${refresh ? '?refresh=1' : ''}`, controller.signal)); }
    catch (e) { if (!controller.signal.aborted) setPerfError(e.message); }
    finally { if (!controller.signal.aborted) setPerfLoading(false); }
  }, []);
  useEffect(() => { loadPicks(); return () => picksRequest.current?.abort(); }, [loadPicks]);
  useEffect(() => { if (page === 'performance' && !performance) loadPerformance(); return () => perfRequest.current?.abort(); }, [page, performance, loadPerformance]);
  useEffect(() => { const navigate = () => { setPage(currentPage()); window.scrollTo(0, 0); }; window.addEventListener('hashchange', navigate); return () => window.removeEventListener('hashchange', navigate); }, []);
  useEffect(() => { try { sessionStorage.setItem('sports-picks-settings-v1', JSON.stringify(settings)); } catch { /* Storage may be disabled. */ } }, [settings]);
  useEffect(() => { const timer = setInterval(() => setToday(todayISO()), 60000); return () => clearInterval(timer); }, []);
  const picks = useMemo(() => applySettings(data?.picks || [], settings, today), [data, settings, today]);

  return <div className={sidebar ? 'app sidebar-open' : 'app'}>
    <a className="skip-link" href="#main" onClick={e => { e.preventDefault(); document.getElementById('main').focus(); }}>Skip to content</a>
    <header className="topbar"><button className="sidebar-toggle" aria-label={sidebar ? 'Collapse sidebar' : 'Open sidebar'} aria-expanded={sidebar} aria-controls="sidebar" onClick={() => setSidebar(!sidebar)}>{sidebar ? '«' : '☰'}</button></header>
    {sidebar ? <><button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebar(false)} /><aside id="sidebar">
      <nav aria-label="Main navigation">{PAGES.map(([key, icon, title]) => <a key={key} className={page === key ? 'selected' : ''} aria-current={page === key ? 'page' : undefined} href={`#${key}`} onClick={() => { if (window.innerWidth <= 760) setSidebar(false); }}><span>{icon}</span>{title}</a>)}</nav>
      <img className="sidebar-logo" src="/logo.png" alt="Sports Picks Grid" width="220" />
      <p className="caption">Daily picks from all Betting Oracle models</p>
    </aside></> : null}
    <main id="main" tabIndex={-1}>
      {error ? <Notice warning>{error}{data ? ' Previously loaded picks remain visible.' : ''} <button onClick={() => loadPicks(true)}>Retry</button></Notice> : null}
      {loading && !data && !['about', 'settings'].includes(page) ? <p className="loading" role="status"><span className="spinner" />Loading picks from all sport models...</p> : null}
      {page === 'today' && data ? <Today picks={picks} today={today} /> : null}
      {page === 'sport' && data ? <BySport picks={picks} data={data} /> : null}
      {page === 'best' && data ? <BestBets picks={picks} /> : null}
      {page === 'performance' ? <Performance data={performance} loading={perfLoading} error={perfError} retry={() => loadPerformance(true)} /> : null}
      {page === 'about' ? <About /> : null}
      {page === 'settings' ? <Settings settings={settings} setSettings={setSettings} /> : null}
      <Footer />
    </main>
  </div>;
}
function Today({ picks, today }) {
  const [tier, setTier] = useState('Elite');
  const counts = { today: picks.filter(p => p.game_date === today).length, future: picks.filter(p => p.game_date > today).length };
  const date = new Date(`${today}T12:00:00Z`).toLocaleDateString('en-US', { timeZone: 'UTC', weekday: 'long', month: 'long', day: '2-digit', year: 'numeric' });
  const filtered = tier === 'All Picks' ? picks : picks.filter(p => p.tier === tier);
  return <><h2>📅 Today's Picks — {date}</h2>
    {picks.length ? <><p className="caption">{[counts.today ? `${counts.today} pick${counts.today !== 1 ? 's' : ''} today` : '', counts.future ? `${counts.future} upcoming` : ''].filter(Boolean).join(' · ')}</p>
      <Metrics items={[["Total Picks", picks.length], ["🔥 Elite", picks.filter(p => p.tier === 'Elite').length], ["✅ Strong", picks.filter(p => p.tier === 'Strong').length], ["Sports Active", new Set(picks.map(p => p.sport)).size]]} /><hr />
      <div className="tabs" role="tablist" aria-label="Pick tiers" onKeyDown={event => {
        const keys = ['Elite', 'Strong', 'Good', 'All Picks'];
        const index = keys.indexOf(tier);
        const next = event.key === 'ArrowRight' ? (index + 1) % 4 : event.key === 'ArrowLeft' ? (index + 3) % 4 : event.key === 'Home' ? 0 : event.key === 'End' ? 3 : -1;
        if (next >= 0) { event.preventDefault(); setTier(keys[next]); document.getElementById(`tab-${keys[next]}`).focus(); }
      }}>{['Elite', 'Strong', 'Good', 'All Picks'].map(t => <button key={t} id={`tab-${t}`} role="tab" tabIndex={tier === t ? 0 : -1} aria-selected={tier === t} aria-controls="tier-panel" className={tier === t ? 'active' : ''} onClick={() => setTier(t)}>{BADGES[t]} {t}</button>)}</div>
      <div role="tabpanel" id="tier-panel" aria-labelledby={`tab-${tier}`}>{filtered.length ? <PicksTable picks={filtered} /> : <Notice>No {tier} picks today.</Notice>}</div>
    </> : <Notice>No picks available. Models may not have run yet, or all sports are currently in their off-season.</Notice>}
  </>;
}
function BySport({ picks, data }) {
  const [sport, setSport] = useState('MLB');
  const visible = picks.filter(p => p.sport === sport);
  const recent = [...(data?.picks || [])].filter(p => p.sport === sport).sort((a, b) => String(b.game_date).localeCompare(String(a.game_date))).slice(0, 20);
  const record = data?.sources?.[sport];
  const generated = [...(data?.picks || [])].filter(p => p.sport === sport && p.generated_at).map(p => p.generated_at).sort().at(-1);
  return <><h2>🏆 Picks by Sport</h2><label className="field">Select Sport<select value={sport} onChange={e => setSport(e.target.value)}>{Object.entries(SOURCES).map(([s, source]) => <option key={s} value={s}>{source.icon} {s}</option>)}</select></label>
    {generated ? <p className="caption">Last model run: {generated}</p> : null}<p className="caption">Source status: {statusLabel(record?.status)}</p>
    {record?.age_hours != null ? <p className="caption">Source age: {record.age_hours.toFixed(1)} hours</p> : null}{record?.errors?.length ? <Notice warning>{record.errors.join('; ')}</Notice> : null}<hr />
    {visible.length ? <><Metrics items={[["Picks", visible.length], ["🔥 Elite", visible.filter(p => p.tier === 'Elite').length], ["✅ Strong", visible.filter(p => p.tier === 'Strong').length]]} /><PicksTable picks={visible} /></> : recent.length ? <><Notice>No picks for today or upcoming. Showing most recent picks ({recent[0].game_date}).</Notice><PicksTable picks={sortPicks(recent)} /></> : <Notice>No picks for {sport}. The sport may be in off-season.</Notice>}
  </>;
}
function BestBets({ picks }) {
  const best = picks.filter(p => ['Elite', 'Strong'].includes(p.tier));
  return <><h2>🔥 Best Bets</h2><p className="caption">Elite and Strong picks across all active sports — curated for highest confidence.</p>
    {!picks.length ? <Notice>No picks available for today.</Notice> : !best.length ? <Notice>No Elite or Strong bets today. Check the Today's Picks page for Good-tier picks.</Notice> : <><p className="caption">{best.length} high-confidence pick{best.length !== 1 ? 's' : ''}</p><hr />{best.map((pick, i) => <BestCard key={`${pick.sport}-${pick.game}-${pick.pick}-${i}`} pick={pick} />)}</>}
  </>;
}
function Performance({ data, loading, error, retry }) {
  const groups = Object.values(data?.aggregate?.groups || {}).filter(g => g && typeof g === 'object').map(g => ({ sport: g.sport || '—', tier: g.tier || '—', settled: g.settled_bets || 0, wins: g.wins || 0, win_rate: g.win_rate, profit: Number(g.profit_units) || 0, roi: g.roi }));
  const rows = Object.entries(data?.sports || {}).flatMap(([sport, perf]) => Object.entries(perf?.bet_types || {}).filter(([, stats]) => stats && typeof stats === 'object').map(([type, stats]) => ({ sport: `${SOURCES[sport].icon} ${sport}`, season: perf.season || '—', type, bets: stats.total_bets ?? '—', win_rate: stats.win_rate, roi: stats.roi, avg_edge: stats.avg_edge, updated: perf.last_updated || '—' })));
  const percent = v => v == null ? '—' : `${(v * 100).toFixed(1)}%`;
  return <><h2>📊 Model Performance</h2><p className="caption">Validated performance metrics from settled, archived picks. Unsettled picks are never counted as losses.</p><hr />
    {loading ? <p role="status" className="loading"><span className="spinner" />Loading performance data...</p> : null}
    {error ? <Notice warning>{error} <button onClick={retry}>Retry</button></Notice> : null}
    {data?.aggregate?.status !== 'unavailable' && groups.length ? <><h3>Validated Archive Grading</h3><DataTable label="Validated Archive Grading" rows={groups} columns={[["sport", "Sport"], ["tier", "Tier"], ["settled", "Settled Bets"], ["wins", "Wins"], ["win_rate", "Win Rate", percent], ["profit", "Profit (u)", v => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`], ["roi", "ROI", percent]]} /><hr /></> : null}
    {rows.length ? <><DataTable label="Model performance" rows={rows} columns={[["sport", "Sport"], ["season", "Season"], ["type", "Bet Type"], ["bets", "Bets"], ["win_rate", "Win Rate", percent], ["roi", "ROI", v => v == null ? '—' : `${v >= 0 ? '+' : ''}${percent(v)}`], ["avg_edge", "Avg Edge", v => v == null ? '—' : `+${percent(v)}`], ["updated", "Updated"]]} /><hr /></> : null}
    <h3>Open Individual Sport Apps</h3><div className="sport-links">{Object.entries(SOURCES).filter(([, source]) => source.app).map(([sport, source]) => <a className="button" key={sport} href={`https://${source.app}.streamlit.app`} target="_blank" rel="noreferrer">{source.icon} {sport}</a>)}</div>
  </>;
}
function Slider({ label, value, min = 0, max, step, onChange, help, percent = false }) {
  return <label className="field slider-field" title={help} style={{ '--progress': `${(value - min) / (max - min) * 100}%` }}>{label}<span className="slider-value">{value}{percent ? '%' : ''}</span><input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))} aria-label={label} aria-valuetext={percent ? `${value}%` : String(value)} /><span className="range-ends"><span>{min}{percent ? '%' : ''}</span><span>{max}{percent ? '%' : ''}</span></span></label>;
}
function TierSelect({ tiers, onChange }) {
  const [open, setOpen] = useState(false);
  return <div className="tier-select" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); }} onKeyDown={e => { if (e.key === 'Escape') setOpen(false); }}>
    <div className="tier-select-label" id="tiers-label">Tiers to Include</div>
    <div className="tier-input"><div className="tier-tags">{tiers.map(t => <span className="tier-tag" key={t}>{t}<button aria-label={`Remove ${t}`} onClick={() => onChange(tiers.filter(x => x !== t))}>×</button></span>)}</div>{tiers.length ? <button className="clear-tiers" aria-label="Clear all tiers" onClick={() => onChange([])}>⊗</button> : null}<button aria-label="Tiers to Include" aria-haspopup="listbox" aria-expanded={open} aria-controls="tier-options" onClick={() => setOpen(!open)}>⌄</button></div>
    {open ? <div id="tier-options" role="listbox" aria-labelledby="tiers-label" aria-multiselectable="true" className="tier-options">{TIERS.map(t => <button key={t} role="option" aria-selected={tiers.includes(t)} onClick={() => onChange(tiers.includes(t) ? tiers.filter(x => x !== t) : [...tiers, t])}>{t}{tiers.includes(t) ? ' ✓' : ''}</button>)}</div> : null}
  </div>;
}
function Settings({ settings, setSettings }) {
  const change = (key, value) => setSettings(s => ({ ...s, [key]: value }));
  return <><h2>⚙️ Filter Settings</h2><p className="caption">Adjust these settings to control which picks appear across all pages. Changes take effect immediately.</p><h3>Global Filters</h3>
    <div className="settings-global"><Slider label="Minimum Confidence" value={Math.round(settings.min_confidence * 100)} max={95} step={5} percent onChange={n => change('min_confidence', n / 100)} help="Hide picks where the model's win probability is below this level." /><Slider label="Minimum Edge" value={Math.round(settings.min_edge * 100)} max={20} step={1} percent onChange={n => change('min_edge', n / 100)} help="Hide picks where the edge over implied odds is below this level." /></div>
    <TierSelect tiers={settings.tiers} onChange={tiers => change('tiers', tiers)} /><hr />
    <h3>Max Picks Per Sport</h3><p className="caption">High-volume sports (Table Tennis, Cricket, Darts, Tennis) can generate hundreds of picks per day. Use these sliders to cap how many are shown per sport — always the highest-confidence picks first.</p>
    <div className="sport-sliders">{[0, 1, 2].map(col => <div key={col}>{Object.keys(SOURCES).sort().filter((_, i) => i % 3 === col).map(sport => <Slider key={sport} label={`${SOURCES[sport].icon} ${sport}`} value={settings.max_picks[sport] ?? DEFAULT_SETTINGS.max_picks[sport] ?? 50} min={5} max={100} step={5} onChange={n => setSettings(s => ({ ...s, max_picks: { ...s.max_picks, [sport]: n } }))} />)}</div>)}</div>
    <hr /><button onClick={() => setSettings(cloneDefaults())}>↩️ Reset to Defaults</button><details><summary>Current settings (debug)</summary><pre>{JSON.stringify(settings, null, 2)}</pre></details>
  </>;
}
function About() {
  return <div className="about"><h2>ℹ️ About Sports Picks Grid</h2><p><strong>Sports Picks Grid</strong> is a unified daily dashboard that aggregates betting recommendations from machine learning models across 17 sport-specific prediction repositories.</p><hr />
    <h3>How It Works</h3><p>Each sport repo runs a nightly GitHub Action that:</p><ol><li>Fetches the latest data (schedules, odds, stats)</li><li>Re-runs the prediction model</li><li>Writes a standardized <code>best_bets_today.json</code> to its <code>data_files/</code> folder</li></ol><p>Sports Picks Grid reads those JSON files and displays today's top picks in one place. <strong>No models run here</strong> — this app is a reader and aggregator only.</p><hr />
    <h3>Confidence Tiers</h3><div className="table-scroll"><table className="markdown-table"><thead><tr><th>Tier</th><th>Badge</th><th>Description</th></tr></thead><tbody>{TIERS.map((t, i) => <tr key={t}><td>{t}</td><td>{BADGES[t]}</td><td>{['Edge ≥ 6% under the canonical edge-v1 definition', 'Edge ≥ 3% and < 6%', 'Edge ≥ 1% and < 3%', 'Tracked internally but not displayed by default'][i]}</td></tr>)}</tbody></table></div><p>Edge is defined as <strong>model probability minus the market's implied probability</strong> (derived from the bookmaker's odds). A positive edge means the model believes the bet is underpriced.</p><hr />
    <h3>Sports Covered</h3><div className="table-scroll"><table className="markdown-table"><thead><tr><th>Sport</th><th>League</th><th>Model Type</th></tr></thead><tbody>{Object.entries(SOURCES).map(([sport, source]) => <tr key={sport}><td>{source.icon} {sport}</td><td>{source.league}</td><td>{source.model}</td></tr>)}</tbody></table></div><hr />
    <h3>Source Repositories</h3><p>All models are open-source and hosted on GitHub:</p><ul>{Object.values(SOURCES).map(source => <li key={source.repo}><a href={`https://github.com/gmalbert/${source.repo}`} target="_blank" rel="noreferrer">{source.repo}</a></li>)}</ul><hr />
    <h3>⚠️ Responsible Gambling Disclaimer</h3><blockquote>These picks are generated by statistical models for <strong>entertainment and research purposes only</strong>. They are not financial advice. Models can and do lose. Never bet more than you can afford to lose. If gambling is causing you harm, visit <a href="https://www.ncpgambling.org">ncpgambling.org</a> or call 1-800-GAMBLER.</blockquote>
  </div>;
}
