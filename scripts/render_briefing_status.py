"""Render the validated manifest in a deterministic Hermes-friendly format."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.data_quality import status_label


MANIFEST = Path("data_cache/status_manifest.json")


def render(manifest: dict) -> str:
    sources = manifest.get("sources", {})
    problem_count = sum(
        record.get("status") not in {"ok", "no_picks", "off_season"}
        for record in sources.values()
    )
    lines = [
        f"Aggregation completed: {manifest.get('aggregation_completed_at', 'unknown')}",
        f"Sources checked: {manifest.get('source_count', len(sources))}",
        f"Health warnings: {problem_count}",
        "",
        "| Sport | Status | Generated | Age (hours) | Bets | Source commit | Action |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for key, record in sources.items():
        status = record.get("status", "unknown")
        action = "; ".join(record.get("errors", [])) or "-"
        lines.append(
            f"| {record.get('sport', key)} | {status_label(status)} | "
            f"{record.get('generated_at', '') or '-'} | "
            f"{record.get('age_hours', '') or '-'} | {record.get('bets_count', 0)} | "
            f"{record.get('source_commit', '')[:12] or '-'} | {action} |"
        )
    return "\n".join(lines)


def main() -> int:
    if not MANIFEST.exists():
        print("Source health manifest is missing; aggregation has not completed.")
        return 1
    print(render(json.loads(MANIFEST.read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
