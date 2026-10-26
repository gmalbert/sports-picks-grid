"""Source registry shared by the aggregator, legacy pages, and web app."""
import json
from pathlib import Path

SOURCES = json.loads((Path(__file__).resolve().parents[1] / "data_files/sources.json").read_text(encoding="utf-8"))
DEFAULT_EXPORT_PATH = "data_files/best_bets_today.json"
REPOS = {source["key"]: source["repo"] for source in SOURCES.values()}
DISPLAY_NAMES = {source["key"]: sport for sport, source in SOURCES.items()}
SOURCE_PATHS = {source["repo"]: source.get("path", DEFAULT_EXPORT_PATH) for source in SOURCES.values()}
SOURCE_URLS = {source["repo"]: source["picksUrl"] for source in SOURCES.values() if source.get("picksUrl")}


def source_url(repo: str) -> str:
    return SOURCE_URLS.get(repo) or f"https://raw.githubusercontent.com/gmalbert/{repo}/main/{SOURCE_PATHS.get(repo, DEFAULT_EXPORT_PATH)}"
