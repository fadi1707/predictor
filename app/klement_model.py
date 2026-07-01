import json
import math
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "data" / "klement_algorithm_config.json"


def load_algorithm_config(path=DEFAULT_CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


DEFAULT_CONFIG = load_algorithm_config()
MODEL_SHARE = DEFAULT_CONFIG["deterministic_share"]
LUCK_SHARE = DEFAULT_CONFIG["luck_share"]
FIFA_MEMBER_COUNT = DEFAULT_CONFIG["transforms"]["fifa_member_count"]


def _fifa_rank_score(fifa_rank, config):
    member_count = config["transforms"]["fifa_member_count"]
    bounded_rank = min(max(fifa_rank, 1), member_count)
    return (member_count - bounded_rank + 1) / member_count


def _population_share(team, config):
    return team.population / config["world_population"]


def _raw_strength(team, config):
    coefficients = config["coefficients"]
    transforms = config["transforms"]
    temp_target = transforms["temperature_target_c"]
    fifa_rank_score = _fifa_rank_score(team.fifa_rank, config)
    fifa_points = team.fifa_points or 0.0
    culture_population = team.football_popularity * _population_share(team, config)
    host_multipliers = transforms.get("host_country_multipliers", {})
    host_multiplier = host_multipliers.get(team.country, 1.0)

    terms = {
        "intercept": coefficients["intercept"],
        "gdp_per_capita": coefficients["gdp_per_capita"] * team.gdp_per_capita_usd,
        "gdp_per_capita_squared": coefficients["gdp_per_capita_squared"] * (team.gdp_per_capita_usd**2),
        "temperature_deviation_squared": coefficients["temperature_deviation_squared"]
        * ((team.avg_temp_c - temp_target) ** 2),
        "host": coefficients["host"] * (host_multiplier if team.is_host else 0.0),
        "football_culture_population_share": coefficients["football_culture_population_share"] * culture_population,
        "fifa_rank_score": coefficients["fifa_rank_score"] * fifa_rank_score,
        "fifa_points": coefficients["fifa_points"] * fifa_points,
    }
    return sum(terms.values()), terms


def normalize_teams(teams, weights=None, config=None):
    config = config or DEFAULT_CONFIG
    raw = {}
    term_map = {}
    for team in teams:
        raw_score, terms = _raw_strength(team, config)
        raw[team.country] = raw_score
        term_map[team.country] = terms

    score_output = config["score_output"]
    min_score = min(raw.values(), default=0.0)
    max_score = max(raw.values(), default=1.0)
    spread = max_score - min_score
    normalized = {}

    for team in teams:
        if score_output.get("mode") == "tournament_minmax" and spread:
            score = (raw[team.country] - min_score) / spread
        elif score_output.get("mode") == "raw_divisor":
            score = raw[team.country] / score_output["raw_score_divisor"]
        else:
            score = raw[team.country]
        normalized[team.country] = {
            "country": team.country,
            "score": round(score, 6),
            "raw_score": round(raw[team.country], 6),
            "factors": {k: round(v, 6) for k, v in term_map[team.country].items()},
            "algorithm": {
                "id": config["algorithm_id"],
                "name": config["algorithm_name"],
            },
        }

    return normalized


def match_probability(team_a, team_b, weights=None, config=None):
    if team_a.country == team_b.country:
        raise ValueError("Match simulations require two different country names.")

    config = config or DEFAULT_CONFIG
    teams = [team_a, team_b]
    normalized = normalize_teams(teams, weights, config)
    a_score = normalized[team_a.country]["score"]
    b_score = normalized[team_b.country]["score"]
    scale = config["match_probability"]["logistic_scale"]
    probability = 1.0 / (1.0 + math.exp(-scale * (a_score - b_score)))

    return {
        "team_a": normalized[team_a.country],
        "team_b": normalized[team_b.country],
        "team_a_win_probability": round(probability, 6),
        "team_b_win_probability": round(1.0 - probability, 6),
        "model_share": config["deterministic_share"],
        "luck_share": config["luck_share"],
        "algorithm": {
            "id": config["algorithm_id"],
            "name": config["algorithm_name"],
        },
    }


def simulate_match(team_a_name, team_b_name, normalized, rng, config=None):
    config = config or DEFAULT_CONFIG
    score_delta = normalized[team_a_name]["score"] - normalized[team_b_name]["score"]
    luck = rng.gauss(0.0, config["luck_share"] / config["match_probability"]["luck_sigma_divisor"])
    outcome = (config["deterministic_share"] * score_delta) + luck
    if outcome == 0:
        return team_a_name if rng.random() < 0.5 else team_b_name
    return team_a_name if outcome > 0 else team_b_name


def _validate_knockout_size(team_count):
    if team_count < 2 or team_count & (team_count - 1):
        raise ValueError("Tournament simulations require a power-of-two team count.")


def _validate_unique_countries(teams):
    countries = [team.country for team in teams]
    if len(countries) != len(set(countries)):
        raise ValueError("Team country names must be unique within a simulation.")


def simulate_knockout_tournament(teams, simulations=10000, seed=None, weights=None, config=None):
    config = config or DEFAULT_CONFIG
    _validate_knockout_size(len(teams))
    _validate_unique_countries(teams)

    rng = random.Random(seed)
    normalized = normalize_teams(teams, weights, config)
    starting_bracket = [team.country for team in teams]
    titles = Counter()
    finals = Counter()
    semifinalists = Counter()

    for _ in range(simulations):
        round_teams = list(starting_bracket)
        while len(round_teams) > 1:
            winners = []
            for i in range(0, len(round_teams), 2):
                winner = simulate_match(round_teams[i], round_teams[i + 1], normalized, rng, config)
                winners.append(winner)

            if len(round_teams) == 4:
                semifinalists.update(round_teams)
            if len(round_teams) == 2:
                finals.update(round_teams)

            round_teams = winners

        titles.update(round_teams)

    champion_odds = [
        {"country": country, "titles": count, "probability": round(count / simulations, 6)}
        for country, count in titles.most_common()
    ]

    return {
        "simulations": simulations,
        "seed": seed,
        "model_share": config["deterministic_share"],
        "luck_share": config["luck_share"],
        "algorithm": {
            "id": config["algorithm_id"],
            "name": config["algorithm_name"],
        },
        "bracket_order": starting_bracket,
        "champion_odds": champion_odds,
        "final_odds": _stage_odds(finals, simulations),
        "semifinal_odds": _stage_odds(semifinalists, simulations),
        "team_scores": sorted(normalized.values(), key=lambda item: item["score"], reverse=True),
    }


def _stage_odds(counter, simulations):
    return [
        {"country": country, "appearances": count, "probability": round(count / simulations, 6)}
        for country, count in counter.most_common()
    ]
