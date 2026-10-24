# React / Cloudflare Workers migration

The web application is now React. A Cloudflare Worker serves `/api/picks` and
`/api/performance`; Workers Static Assets serves the Vite bundle. Python is used
only by the existing aggregation and grading jobs, not by the deployed website.
The original Streamlit pages remain available as the visual reference during migration.

## Local development

Requires Node.js 22.12+ (Node 24 recommended).

```sh
npm ci
npm run dev
```

Open `http://localhost:8787`. This builds React and runs the actual Worker locally.
For React hot reload, leave Wrangler running and run `npm run dev:ui` in another
terminal; Vite proxies `/api` requests to Wrangler on port 8787.

```sh
npm run check
```

Runs data/filter contract tests, builds the frontend, and bundles the Worker in a
deployment dry run. No Cloudflare login is required for the dry run.
The `Validate React and Worker` GitHub Action runs this same check on web code changes.

## Deploy

```sh
npx wrangler login
npm run deploy
```

Alternatively, connect this repository in Cloudflare Workers Builds. Use
`npm run build` as the build command and `npx wrangler deploy` as the deploy
command. The project root is the repository root. No KV namespace, D1 database,
Python runtime, or application secrets are required. Configure a custom domain
in Cloudflare after the first deployment if desired.

The Worker name and data repository/branch are configured in `wrangler.jsonc`.
The production domains are `sportspickgrid.com` and `sportspicksgrid.com`.
Their `/*` Worker routes take precedence over the existing proxied website DNS
records, preserving those DNS records and verification records. Keep the apex
records proxied in Cloudflare; these hostnames use Worker routes rather than
the Custom Domains binding because Cloudflare rejected replacing the existing
externally managed DNS records. The `workers.dev` address remains enabled.
Only `/api/*` invokes the Worker before asset routing. Unknown API routes return
JSON 404s; normal frontend navigation uses the SPA fallback.

## Data and continuity

- The Worker reads the aggregation manifest and all 17 sport cache files from
  the configured public GitHub repository. Missing or invalid aggregated files
  fall back to the individual sport repository's export.
- Valid exports are retained for seven days in the local Cloudflare edge cache.
  If both remote sources fail, the Worker uses the last valid cached export,
  then the snapshot bundled at build time. The response explicitly reports a
  fetch failure; historical data is never labeled current.
- Each export is validated for required fields, valid dates and edge-v1 tier
  consistency. Freshness is recalculated from its generation time. Aggregator
  failure statuses remain visible when last valid records are retained.
- API payloads are cached at the edge for one hour. The API's `?refresh=1`
  parameter bypasses that cache and refetches source files; upstream GitHub
  caching may still delay updates. The sidebar has no manual refresh control.
  Edge cache is best-effort, per location, and not durable storage. The existing
  GitHub snapshots remain the durable fallback. Updates from the aggregation
  Action become available without redeploying the React site.
- `npm run build` generates the bundled snapshots from `data_cache/` and
  `data_files/model_performance.json`, and copies the existing sidebar logo.
  Do not edit `worker/snapshots.json` or `public/logo.png` directly.
- Performance is loaded when its page opens. Unsettled outcomes are never
  converted to losses or invented performance statistics.

## Interface parity

All six pages retain their titles, emoji, navigation order, metric labels,
table columns, tier order, Best Bets card layout, sport links, branding and
empty states. CSS reproduces Streamlit's default light/dark colors, spacing,
Source Sans font, borders and controls. The font is bundled locally (see
`public/fonts/OFL.txt`). Tables support sorting, horizontal scrolling, CSV
download and expansion. Settings apply immediately across pages and persist for
the browser tab via versioned session storage; Reset restores the Python defaults.
The sidebar refresh button, cache timestamp and source-health panel are omitted,
as are the Performance page's two unavailable-data notices. Source status remains
available on By Sport and through the API.

The dashboard date follows America/New_York, including daylight-saving changes.
The canonical picks window remains today through seven days ahead. Only By Sport
shows the most recent 20 historical rows when that sport has no qualifying picks,
matching the Streamlit implementation (which bypasses user filters for this
explicit historical fallback). Edge filters normalize percentage-form exports
before comparison, matching the validator and displayed percentage.

Browser-native sliders, dropdowns, table rendering and emoji can differ slightly
from Streamlit's widget implementation across browsers and operating systems.
Streamlit's hosting toolbar is not part of the migrated product UI.

## Reference

[Cloudflare Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/)
and [SPA routing](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/).
