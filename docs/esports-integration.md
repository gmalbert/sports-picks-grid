# Esports source

Esports is sourced from `gmalbert/esports/main/data_files/best_bets_today.json`.
The source's GitHub Action publishes at 00:10 and 12:10 UTC, using saved quotes
from Sidequest's existing Cloudflare capture. Grid aggregation additionally runs
at 00:30 and 12:30 UTC; its existing 15:00 UTC refresh remains active.

League labels identify LoL, CS2, Dota 2, VALORANT, Rainbow Six, or Overwatch.
Only future, source-verified fixtures with medium/high-confidence historical Elo
and a qualifying YES ask are exported. One selection per fixture is allowed.
Source forecasts, quotes, and market IDs remain attached for review. Empty
qualifying sets explicitly publish `no_picks`; absent/stale feeds publish their
own source status, and upstream request failures preserve the previous export.

Edge-v1 tiers use model probability minus the saved YES ask and a $0.02 cost
allowance per $1 contract. This is an estimated allowance, not the actual fee.
American odds are equivalent to that effective contract cost, not a sportsbook
line. Notes on each pick explain this distinction. Recheck prices before betting.
Home/away fields represent display order for these neutral-site matchups.

The Worker additionally removes picks whose quote is older than 13 hours or
whose match has started, including when using a retained cache. No new Kalshi
requests, provider credentials, or cross-repo write tokens are needed by Grid.
Settled-result delivery and realized performance reporting are separate work;
this connection publishes prospective selections only.
