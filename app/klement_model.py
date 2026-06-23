import math
import random
from collections import Counter


DEFAULT_WEIGHTS = {
    "fifa_rank": 0.45,
    "population_pool": 0.22,
    "gdp_per_capita": 0.15,
    "climate": 0.11,
    "host": 0.07,
}

MODEL_SHARE = 0.55
LUCK_SHARE = 0.45
FIFA_MEMBER_COUNT = 211


def _gaussian_score(value, target, sigma):
    return math.exp(-((value - target) ** 2) / (2 * sigma**2))


def _wealth_score(gdp_per_capita_usd):
    if gdp_per_capita_usd <= 0:
        return 0.0
    return _gaussian_score(math.log(gdp_per_capita_usd), math.log(60000), 0.9)


def _climate_score(avg_temp_c):
    return _gaussian_score(avg_temp_c, 14.0, 10.0)


def _fifa_rank_score(fifa_rank):
    bounded_rank = min(max(fifa_rank, 1), FIFA_MEMBER_COUNT)
    return (FIFA_MEMBER_COUNT - bounded_rank + 1) / FIFA_MEMBER_COUNT


def _population_pool_score(team, max_pool):
    pool = max(team.population * team.football_popularity, 0)
    if max_pool <= 0:
        return 0.0
    return math.log1p(pool) / math.log1p(max_pool)


def normalize_teams(teams, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    max_pool = max((t.population * t.football_popularity for t in teams), default=0)
    normalized = {}

    for team in teams:
        factors = {
            "fifa_rank": _fifa_rank_score(team.fifa_rank),
            "population_pool": _population_pool_score(team, max_pool),
            "gdp_per_capita": _wealth_score(team.gdp_per_capita_usd),
            "climate": _climate_score(team.avg_temp_c),
            "host": 1.0 if team.is_host else 0.0,
        }
        score = sum(factors[name] * weights.get(name, 0.0) for name in factors)
        normalized[team.country] = {
            "country": team.country,
            "score": round(score, 6),
            "factors": {k: round(v, 6) for k, v in factors.items()},
            "weights": weights,
        }

    return normalized


def match_probability(team_a, team_b, weights=None):
    if team_a.country == team_b.country:
        raise ValueError("Match simulations require two different country names.")

    teams = [team_a, team_b]
    normalized = normalize_teams(teams, weights)
    a_score = normalized[team_a.country]["score"]
    b_score = normalized[team_b.country]["score"]
    probability = 1.0 / (1.0 + math.exp(-4.0 * (a_score - b_score)))

    return {
        "team_a": normalized[team_a.country],
        "team_b": normalized[team_b.country],
        "team_a_win_probability": round(probability, 6),
        "team_b_win_probability": round(1.0 - probability, 6),
        "model_share": MODEL_SHARE,
        "luck_share": LUCK_SHARE,
    }


def simulate_match(team_a_name, team_b_name, normalized, rng):
    score_delta = normalized[team_a_name]["score"] - normalized[team_b_name]["score"]
    luck = rng.gauss(0.0, LUCK_SHARE / 3.0)
    outcome = (MODEL_SHARE * score_delta) + luck
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


def simulate_knockout_tournament(teams, simulations=10000, seed=None, weights=None):
    _validate_knockout_size(len(teams))
    _validate_unique_countries(teams)

    rng = random.Random(seed)
    normalized = normalize_teams(teams, weights)
    starting_bracket = [team.country for team in teams]
    titles = Counter()
    finals = Counter()
    semifinalists = Counter()

    for _ in range(simulations):
        round_teams = list(starting_bracket)
        while len(round_teams) > 1:
            winners = []
            for i in range(0, len(round_teams), 2):
                winner = simulate_match(round_teams[i], round_teams[i + 1], normalized, rng)
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
        "model_share": MODEL_SHARE,
        "luck_share": LUCK_SHARE,
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
