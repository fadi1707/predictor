import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from app.klement_model import DEFAULT_CONFIG, normalize_teams
from app.models import KlementTeam


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "klement_world_cup_2026.db"


def connect(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_world_cup(db_path=DEFAULT_DB_PATH):
    conn = connect(db_path)
    try:
        team_rows = conn.execute(
            """
            SELECT country, fifa_code, group_letter, group_position,
                   gdp_per_capita_usd, population, football_popularity,
                   avg_temp_c, fifa_rank, fifa_points, is_host
            FROM teams
            ORDER BY group_letter, group_position
            """
        ).fetchall()
        match_rows = conn.execute(
            """
            SELECT match_number, stage, group_letter, slot_a, slot_b
            FROM matches
            ORDER BY match_number
            """
        ).fetchall()
    finally:
        conn.close()

    missing = []
    teams = {}
    group_members = defaultdict(list)
    for row in team_rows:
        missing_fields = [
            field
            for field in (
                "gdp_per_capita_usd",
                "population",
                "football_popularity",
                "avg_temp_c",
                "fifa_rank",
            )
            if row[field] is None
        ]
        if missing_fields:
            missing.append({"fifa_code": row["fifa_code"], "country": row["country"], "fields": missing_fields})
            continue

        team = KlementTeam(
            country=row["country"],
            gdp_per_capita_usd=row["gdp_per_capita_usd"],
            population=row["population"],
            football_popularity=row["football_popularity"],
            avg_temp_c=row["avg_temp_c"],
            fifa_rank=row["fifa_rank"],
            fifa_points=row["fifa_points"],
            is_host=bool(row["is_host"]),
        )
        teams[row["fifa_code"]] = team
        group_members[row["group_letter"]].append(row["fifa_code"])

    if missing:
        raise ValueError(f"Missing model inputs for {len(missing)} teams: {missing[:8]}")

    group_matches = [dict(row) for row in match_rows if row["stage"] == "Group"]
    knockout_matches = [dict(row) for row in match_rows if row["stage"] != "Group"]
    return teams, dict(group_members), group_matches, knockout_matches


def _match_outcome(code_a, code_b, normalized, rng, config):
    score_delta = normalized[code_a]["score"] - normalized[code_b]["score"]
    luck = rng.gauss(0.0, config["luck_share"] / config["match_probability"]["luck_sigma_divisor"])
    outcome = (config["deterministic_share"] * score_delta) + luck
    draw_band = config["match_probability"]["draw_band"]

    if abs(outcome) <= draw_band:
        return "draw"
    return code_a if outcome > 0 else code_b


def _record_group_result(table, code_a, code_b, outcome):
    table[code_a]["played"] += 1
    table[code_b]["played"] += 1

    if outcome == "draw":
        table[code_a]["points"] += 1
        table[code_b]["points"] += 1
        return

    loser = code_b if outcome == code_a else code_a
    table[outcome]["points"] += 3
    table[outcome]["wins"] += 1
    table[loser]["losses"] += 1


def _sort_group(table, normalized):
    return sorted(
        table.values(),
        key=lambda row: (
            row["points"],
            row["wins"],
            normalized[row["code"]]["score"],
        ),
        reverse=True,
    )


def _slot_to_code(slot, group_rankings, third_place_pool):
    if slot.startswith("W") or slot.startswith("L"):
        return slot
    if slot[0].isdigit() and len(slot) == 2:
        position = int(slot[0]) - 1
        group = slot[1]
        return group_rankings[group][position]["code"]
    if slot.startswith("3rd "):
        allowed_groups = slot.replace("3rd ", "").split("/")
        for group in allowed_groups:
            if group in third_place_pool:
                return third_place_pool.pop(group)
        return third_place_pool.pop(next(iter(third_place_pool)))
    return slot


def _simulate_group_stage(group_members, group_matches, normalized, rng, config):
    tables = {
        group: {
            code: {"code": code, "points": 0, "wins": 0, "losses": 0, "played": 0}
            for code in members
        }
        for group, members in group_members.items()
    }

    for match in group_matches:
        outcome = _match_outcome(match["slot_a"], match["slot_b"], normalized, rng, config)
        _record_group_result(tables[match["group_letter"]], match["slot_a"], match["slot_b"], outcome)

    rankings = {group: _sort_group(table, normalized) for group, table in tables.items()}
    thirds = [rankings[group][2] | {"group": group} for group in rankings]
    best_thirds = sorted(
        thirds,
        key=lambda row: (row["points"], row["wins"], normalized[row["code"]]["score"]),
        reverse=True,
    )[:8]
    third_place_pool = {row["group"]: row["code"] for row in best_thirds}
    return rankings, third_place_pool


def _simulate_knockout(knockout_matches, group_rankings, third_place_pool, normalized, rng, config):
    resolved = {}
    finalist_codes = []

    for match in knockout_matches:
        code_a = resolved.get(match["slot_a"], None) or _slot_to_code(match["slot_a"], group_rankings, third_place_pool)
        code_b = resolved.get(match["slot_b"], None) or _slot_to_code(match["slot_b"], group_rankings, third_place_pool)
        winner = _match_outcome(code_a, code_b, normalized, rng, config)
        if winner == "draw":
            winner = code_a if normalized[code_a]["score"] >= normalized[code_b]["score"] else code_b
        loser = code_b if winner == code_a else code_a
        resolved[f'W{match["match_number"]}'] = winner
        resolved[f'L{match["match_number"]}'] = loser

        if match["stage"] == "Final":
            finalist_codes = [code_a, code_b]
            return winner, finalist_codes

    raise ValueError("Final match was not found in knockout schedule.")


def predict_fwc26_winner(simulations=10000, seed=None, db_path=DEFAULT_DB_PATH, config=None):
    config = config or DEFAULT_CONFIG
    teams, group_members, group_matches, knockout_matches = load_world_cup(db_path)
    rng = random.Random(seed)
    normalized_by_country = normalize_teams(list(teams.values()), config=config)
    normalized = {
        code: normalized_by_country[team.country]
        for code, team in teams.items()
    }

    titles = Counter()
    final_appearances = Counter()

    for _ in range(simulations):
        group_rankings, third_place_pool = _simulate_group_stage(group_members, group_matches, normalized, rng, config)
        champion, finalists = _simulate_knockout(
            knockout_matches,
            group_rankings,
            dict(third_place_pool),
            normalized,
            rng,
            config,
        )
        titles[champion] += 1
        final_appearances.update(finalists)

    def row(code, count, field):
        return {
            "country": teams[code].country,
            "fifa_code": code,
            field: count,
            "probability": round(count / simulations, 6),
            "model_score": normalized[code]["score"],
        }

    champion_odds = [row(code, count, "titles") for code, count in titles.most_common()]
    final_odds = [row(code, count, "finals") for code, count in final_appearances.most_common()]

    return {
        "simulations": simulations,
        "seed": seed,
        "algorithm": {
            "id": config["algorithm_id"],
            "name": config["algorithm_name"],
        },
        "most_probable_winner": champion_odds[0] if champion_odds else None,
        "champion_odds": champion_odds,
        "final_odds": final_odds,
        "team_scores": [
            {
                "country": teams[code].country,
                "fifa_code": code,
                "model_score": normalized[code]["score"],
                "factors": normalized[code]["factors"],
            }
            for code in sorted(normalized, key=lambda item: normalized[item]["score"], reverse=True)
        ],
    }
