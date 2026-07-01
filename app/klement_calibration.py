import copy
import json
import random
from collections import Counter
from pathlib import Path

from app.fwc26_predictor import (
    DEFAULT_DB_PATH,
    _simulate_group_stage,
    load_world_cup,
)
from app.klement_model import DEFAULT_CONFIG, load_algorithm_config, normalize_teams
from app.klement_published_forecast import load_klement_2026_forecast


ROOT = Path(__file__).resolve().parents[1]
CALIBRATED_CONFIG_PATH = ROOT / "data" / "klement_algorithm_config.calibrated.json"
CALIBRATION_REPORT_PATH = ROOT / "data" / "klement_calibration_report.json"


def load_calibrated_config(path=CALIBRATED_CONFIG_PATH):
    if Path(path).exists():
        return load_algorithm_config(path)
    return DEFAULT_CONFIG


def load_calibration_report(path=CALIBRATION_REPORT_PATH):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return {
        "status": "missing",
        "message": "No calibration report has been generated yet.",
        "path": str(path),
    }


def published_advancement_targets():
    forecast = load_klement_2026_forecast()["forecast"]
    targets = {}
    for rows in forecast["group_advancement_probabilities"].values():
        for country, fifa_code, probability in rows:
            targets[fifa_code] = {
                "country": country,
                "fifa_code": fifa_code,
                "target_probability": probability,
            }
    return targets


def published_knockout_targets(db_path=DEFAULT_DB_PATH):
    teams, _, _, _ = load_world_cup(db_path)
    code_by_country = {
        team.country.lower().replace(".", "").replace("-", " "): code
        for code, team in teams.items()
    }
    aliases = {
        "czechia": "CZE",
        "czech rep": "CZE",
        "dr congo": "COD",
        "south korea": "KOR",
        "ivory coast": "CIV",
        "usa": "USA",
    }
    forecast = load_klement_2026_forecast()["forecast"]
    targets = []

    for round_name, matches in forecast["knockout_rounds"].items():
        for team_a, team_b, winner in matches:
            key_a = team_a.lower().replace(".", "").replace("-", " ")
            key_b = team_b.lower().replace(".", "").replace("-", " ")
            key_winner = winner.lower().replace(".", "").replace("-", " ")
            code_a = aliases.get(key_a) or code_by_country.get(key_a)
            code_b = aliases.get(key_b) or code_by_country.get(key_b)
            winner_code = aliases.get(key_winner) or code_by_country.get(key_winner)
            if code_a and code_b and winner_code:
                targets.append(
                    {
                        "round": round_name,
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner,
                        "team_a_code": code_a,
                        "team_b_code": code_b,
                        "winner_code": winner_code,
                    }
                )
    return targets


def estimate_top_two_probabilities(config, simulations=800, seed=2026, db_path=DEFAULT_DB_PATH):
    teams, group_members, group_matches, _ = load_world_cup(db_path)
    normalized_by_country = normalize_teams(list(teams.values()), config=config)
    normalized = {
        code: normalized_by_country[team.country]
        for code, team in teams.items()
    }
    rng = random.Random(seed)
    top_two = Counter()

    for _ in range(simulations):
        group_rankings, _ = _simulate_group_stage(
            group_members,
            group_matches,
            normalized,
            rng,
            config,
        )
        for rankings in group_rankings.values():
            top_two.update([rankings[0]["code"], rankings[1]["code"]])

    return {
        code: {
            "country": teams[code].country,
            "fifa_code": code,
            "estimated_probability": count / simulations,
            "model_score": normalized[code]["score"],
        }
        for code, count in top_two.items()
    }


def evaluate_config(config, simulations=800, seed=2026, db_path=DEFAULT_DB_PATH):
    teams, _, _, _ = load_world_cup(db_path)
    normalized_by_country = normalize_teams(list(teams.values()), config=config)
    normalized = {
        code: normalized_by_country[team.country]
        for code, team in teams.items()
    }
    targets = published_advancement_targets()
    estimates = estimate_top_two_probabilities(config, simulations, seed, db_path)
    group_errors = []
    rows = []

    for code, target in targets.items():
        estimate = estimates.get(code, {})
        estimated_probability = estimate.get("estimated_probability", 0.0)
        error = estimated_probability - target["target_probability"]
        group_errors.append(error * error)
        rows.append(
            {
                **target,
                "estimated_probability": round(estimated_probability, 6),
                "error": round(error, 6),
                "squared_error": round(error * error, 6),
                "model_score": estimate.get("model_score"),
            }
        )

    knockout_targets = published_knockout_targets(db_path)
    knockout_errors = []
    knockout_rows = []
    scale = config["match_probability"]["logistic_scale"]

    for target in knockout_targets:
        winner_code = target["winner_code"]
        loser_code = target["team_b_code"] if winner_code == target["team_a_code"] else target["team_a_code"]
        winner_score = normalized[winner_code]["score"]
        loser_score = normalized[loser_code]["score"]
        probability = 1.0 / (1.0 + pow(2.718281828459045, -scale * (winner_score - loser_score)))
        error = 1.0 - probability
        knockout_errors.append(error * error)
        knockout_rows.append(
            {
                **target,
                "winner_model_score": winner_score,
                "loser_code": loser_code,
                "loser_model_score": loser_score,
                "winner_probability_proxy": round(probability, 6),
                "squared_error": round(error * error, 6),
            }
        )

    group_mse = sum(group_errors) / len(group_errors) if group_errors else None
    knockout_mse = sum(knockout_errors) / len(knockout_errors) if knockout_errors else None
    objective = (group_mse or 0.0) + (1.5 * (knockout_mse or 0.0))

    return {
        "target_count": len(targets),
        "simulations": simulations,
        "seed": seed,
        "objective_score": round(objective, 8),
        "group_mean_squared_error": round(group_mse, 8) if group_mse is not None else None,
        "group_root_mean_squared_error": round(group_mse**0.5, 8) if group_mse is not None else None,
        "knockout_target_count": len(knockout_targets),
        "knockout_mean_squared_error": round(knockout_mse, 8) if knockout_mse is not None else None,
        "knockout_root_mean_squared_error": round(knockout_mse**0.5, 8) if knockout_mse is not None else None,
        "targets": sorted(rows, key=lambda row: abs(row["error"]), reverse=True),
        "knockout_targets": sorted(knockout_rows, key=lambda row: row["squared_error"], reverse=True),
    }


def _candidate_config(base_config, rng):
    config = copy.deepcopy(base_config)
    coefficients = config["coefficients"]
    match = config["match_probability"]

    coefficients["fifa_rank_score"] = rng.uniform(80.0, 650.0)
    coefficients["host"] = rng.uniform(0.0, 160.0)
    coefficients["football_culture_population_share"] = rng.uniform(1000.0, 18000.0)
    coefficients["gdp_per_capita"] = rng.uniform(0.002, 0.025)
    coefficients["gdp_per_capita_squared"] = -rng.uniform(0.00000003, 0.0000006)
    coefficients["temperature_deviation_squared"] = -rng.uniform(0.05, 1.25)
    match["draw_band"] = rng.uniform(0.0, 0.11)
    match["luck_sigma_divisor"] = rng.uniform(2.0, 6.0)
    config["score_output"]["raw_score_divisor"] = rng.uniform(650.0, 1450.0)
    config["transforms"]["host_country_multipliers"] = {
        "United States": rng.uniform(0.0, 0.45),
        "Canada": rng.uniform(0.0, 0.45),
        "Mexico": rng.uniform(0.3, 1.2),
    }
    return config


def calibrate_config(candidates=120, simulations=500, seed=2026, db_path=DEFAULT_DB_PATH):
    rng = random.Random(seed)
    best_config = copy.deepcopy(DEFAULT_CONFIG)
    best_score = evaluate_config(best_config, simulations, seed, db_path)
    best_objective = best_score["objective_score"]

    for _ in range(candidates):
        candidate = _candidate_config(DEFAULT_CONFIG, rng)
        score = evaluate_config(candidate, simulations, seed, db_path)
        if score["objective_score"] < best_objective:
            best_config = candidate
            best_score = score
            best_objective = score["objective_score"]

    best_config["algorithm_id"] = "klement_inverse_fit_public_targets_v1"
    best_config["algorithm_name"] = "Klement inverse fit from published 2026 targets"
    best_config["description"] = (
        "Inverse-fitted reconstruction calibrated against Klement's published "
        "2026 advancement probabilities. This is not Klement's private formula."
    )
    best_config["calibration"] = {
        "method": "random_search_against_published_top_two_group_probabilities",
        "candidate_count": candidates,
        "simulations_per_candidate": simulations,
        "seed": seed,
        "target_count": best_score["target_count"],
        "knockout_target_count": best_score["knockout_target_count"],
        "objective": "minimize group top-two error plus weighted knockout-path error",
    }

    final_score = evaluate_config(best_config, max(simulations * 2, simulations), seed + 1, db_path)
    report = {
        "status": "complete",
        "algorithm_id": best_config["algorithm_id"],
        "calibration": best_config["calibration"],
        "training_score": best_score,
        "validation_score": final_score,
        "limitations": [
            "Klement's private coefficients and simulation distribution are not published.",
            "Calibration targets cover only the published group-advancement probabilities captured in data/klement_2026_published_forecast.json.",
            "The result is an inverse fit to outputs, not proof of the exact private model.",
        ],
    }
    return best_config, report
