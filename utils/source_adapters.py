"""Explicit compatibility adapters; freshness always uses source timestamps."""
from copy import deepcopy
from math import isfinite

from utils.data_quality import parse_timestamp

LEGACY_TIERS = {
    "portugal-soccer", "netherlands-soccer", "belgium-soccer",
    "scotland-premiership", "turkey-soccer", "horse-racing-predictions", "golf-predictions",
}


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def edge_tier(edge):
    edge = edge / 100 if abs(edge) > 1 else edge
    return "Elite" if edge >= .06 else "Strong" if edge >= .03 else "Good" if edge >= .01 else "Standard"


def normalize_source(data, repo):
    if not isinstance(data, dict):
        return data
    if repo == "wnba-predictions" and "games" in data:
        return adapt_wnba(data)
    if repo not in LEGACY_TIERS or not isinstance(data.get("meta"), dict) or not isinstance(data.get("bets"), list):
        return data
    result = deepcopy(data)
    changed = 0
    for bet in result["bets"]:
        if isinstance(bet, dict) and numeric(bet.get("edge")):
            tier = edge_tier(bet["edge"])
            if bet.get("tier") != tier:
                bet["source_tier"] = bet.get("tier")
                bet["tier"] = tier
                changed += 1
    result["meta"]["tier_definition"] = "edge-v1"
    if changed:
        result["meta"]["normalized_tier_count"] = changed
    if not result["bets"] and "no odds artifact" in str(result["meta"].get("notes", "")).lower():
        result["meta"]["status"] = "pipeline_pending"
    return result


def adapt_wnba(data):
    games = data.get("games")
    if not isinstance(games, list):
        return data  # Let the normal schema validator reject a broken envelope.
    timestamps = [data.get("generated_at")]
    timestamps.extend(g.get("generated_at") for g in games if isinstance(g, dict))
    valid = [(parse_timestamp(t), t) for t in timestamps if parse_timestamp(t)]
    generated = min(valid, key=lambda item: item[0])[1] if valid else data.get("generated_at", "")
    bets = []
    for game in games:
        if not isinstance(game, dict) or game.get("status") != "ready" or game.get("paper_only") is not False or game.get("release_gate_status") != "production_ready":
            continue
        probability, market = game.get("home_win_prob"), game.get("market_home_prob")
        if not numeric(probability) or not numeric(market) or not 0 <= probability <= 1 or not 0 < market < 1:
            continue
        home = probability >= market
        confidence = probability if home else 1 - probability
        edge = round(abs(probability - market), 6)
        if edge < .01:
            continue
        bets.append({
            "game_id": game.get("game_id"), "game_date": game.get("game_date"),
            "game_time": game.get("scheduled_start"),
            "game": f"{game.get('away_team')} @ {game.get('home_team')}",
            "home_team": game.get("home_team"), "away_team": game.get("away_team"),
            "bet_type": "Moneyline", "pick": game.get("home_team" if home else "away_team"),
            "confidence": confidence, "edge": edge, "tier": edge_tier(edge),
            "odds": None, "line": None, "generated_at": game.get("generated_at", generated),
            "paper_only": False, "release_gate_status": "production_ready",
        })
    return {"meta": {
        "sport": "WNBA", "generated_at": generated, "tier_definition": "edge-v1",
        "source_format": "wnba-web-v1", "source_generated_at": data.get("generated_at"),
        "withheld_games": len(games) - len(bets),
        "notes": "WNBA web predictions; paper-only, no-bet, unreleased, and unpriced rows are withheld",
    }, "bets": bets}
