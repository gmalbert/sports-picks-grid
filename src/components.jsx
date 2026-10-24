import { useState } from 'react';
import { SOURCES, BADGES, confidence, edge, odds, dateLabel, timeLabel } from '../shared/picks.js';

export function Notice({ children, warning = false }) {
  return <div className={`notice ${warning ? 'warning' : ''}`} role={warning ? 'alert' : 'status'}>{children}</div>;
}
export function Metrics({ items }) {
  return <div className="metrics" style={{ '--columns': items.length }}>{items.map(([label, value]) => <div key={label}><div className="metric-label">{label}</div><div className="metric-value">{value}</div></div>)}</div>;
}
const COLUMNS = [
  ['game_date', 'Date', dateLabel], ['sport', 'Sport', v => `${SOURCES[v]?.icon || '🎯'} ${v}`],
  ['tier', 'Tier', v => `${BADGES[v] || '⚪'} ${v}`], ['game', 'Game'], ['game_time', 'Time', timeLabel],
  ['bet_type', 'Bet Type'], ['pick', 'Pick'], ['confidence', 'Confidence', confidence], ['edge', 'Edge', edge], ['odds', 'Odds', odds], ['league', 'League'],
];
export function PicksTable({ picks, label = 'Picks' }) {
  const columns = COLUMNS.filter(([key]) => picks.some(pick => key in pick));
  return <DataTable rows={picks} columns={columns} label={label} />;
}
export function DataTable({ rows, columns, label }) {
  const [sort, setSort] = useState({ key: null, asc: true });
  const [expanded, setExpanded] = useState(false);
  const ordered = sort.key ? [...rows].sort((a, b) => {
    const av = a[sort.key], bv = b[sort.key];
    const value = av == null ? bv == null ? 0 : 1 : bv == null ? -1 : typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
    return sort.asc ? value : -value;
  }) : rows;
  function download() {
    const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const csv = [columns.map(([, title]) => quote(title)).join(','), ...ordered.map(row => columns.map(([key, , format]) => {
      const value = String(format ? format(row[key]) : row[key] ?? '—');
      return quote(/^[=+@\-\t\r]/.test(value) ? `'${value}` : value);
    }).join(','))].join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'sports-picks.csv'; anchor.click(); URL.revokeObjectURL(url);
  }
  return <div className={`dataframe ${expanded ? 'expanded-table' : ''}`}>
    <div className="table-tools"><button aria-label="Download table as CSV" title="Download as CSV" onClick={download}>⇩</button><button aria-label={expanded ? 'Close expanded table' : 'Expand table'} title="Expand table" onClick={() => setExpanded(!expanded)}>{expanded ? '✕' : '⛶'}</button></div>
    <div className="table-scroll" tabIndex={0} aria-label={`${label} scrollable table`} onKeyDown={event => { if (event.key === 'Escape') setExpanded(false); }}>
      <table aria-label={label}><thead><tr>{columns.map(([key, title]) => <th key={key} aria-sort={sort.key === key ? sort.asc ? 'ascending' : 'descending' : 'none'}><button onClick={() => setSort({ key, asc: sort.key === key ? !sort.asc : true })}>{title}{sort.key === key ? sort.asc ? ' ↑' : ' ↓' : ''}</button></th>)}</tr></thead>
        <tbody>{ordered.map((row, i) => <tr key={`${row.sport || ''}-${row.game_date || ''}-${row.game || ''}-${row.pick || ''}-${i}`}>{columns.map(([key, , format]) => <td key={key}>{format ? format(row[key]) : row[key] ?? '—'}</td>)}</tr>)}</tbody></table>
    </div>
  </div>;
}
export function BestCard({ pick }) {
  return <article className="bet-card">
    <p className="card-heading"><strong>{BADGES[pick.tier]} {pick.tier}</strong> · {SOURCES[pick.sport]?.icon} {pick.sport}{pick.league ? <> · <em>{pick.league}</em></> : null} · 📆 {dateLabel(pick.game_date)}{pick.game_time ? <> · 🕐 {timeLabel(pick.game_time)}</> : null}</p>
    <div className="card-columns"><div><strong>{pick.game || 'Unknown Matchup'}</strong><p>Bet: <code>{pick.bet_type}</code></p>{odds(pick.odds) !== '—' ? <p>Odds: <code>{odds(pick.odds)}</code></p> : null}</div><div><h3>{pick.pick}</h3>{pick.notes ? <p className="caption">{pick.notes}</p> : null}</div><div>{pick.confidence != null ? <Metrics items={[["Confidence", confidence(pick.confidence)]]} /> : null}{pick.edge != null ? <Metrics items={[["Edge", edge(pick.edge)]]} /> : null}</div></div>
  </article>;
}
export function Footer() {
  return <footer><p>Powered by <a href="https://www.betting-oracle.com" target="_blank" rel="noreferrer">Betting Oracle</a></p><p>Sports Prediction Analytics<br />All content is for informational purposes only and does not constitute betting advice. Wager responsibly.</p><a href="https://www.betting-oracle.com" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/gmalbert/betting-oracle/main/data_files/logo.png" alt="Betting Oracle Logo" height="60" /></a></footer>;
}
