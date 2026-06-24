import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "data" / "fwc26_seed.json"
DEFAULT_MODEL_INPUTS = ROOT / "data" / "fwc26_model_inputs.json"
DEFAULT_OUTPUT = ROOT / "data" / "klement_world_cup_2026.db"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def create_schema(conn):
    conn.executescript(
        """
        DROP VIEW IF EXISTS team_model_inputs;
        DROP TABLE IF EXISTS matches;
        DROP TABLE IF EXISTS teams;
        DROP TABLE IF EXISTS source_files;
        DROP TABLE IF EXISTS tournaments;

        CREATE TABLE tournaments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE source_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL REFERENCES tournaments(id),
            name TEXT NOT NULL,
            original_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            sha256 TEXT,
            exists_on_build INTEGER NOT NULL
        );

        CREATE TABLE teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL REFERENCES tournaments(id),
            country TEXT NOT NULL,
            fifa_code TEXT NOT NULL,
            group_letter TEXT NOT NULL,
            group_position INTEGER NOT NULL,
            gdp_per_capita_usd REAL,
            population INTEGER,
            football_popularity REAL,
            avg_temp_c REAL,
            fifa_rank INTEGER,
            is_host INTEGER NOT NULL DEFAULT 0,
            UNIQUE(tournament_id, fifa_code)
        );

        CREATE TABLE matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL REFERENCES tournaments(id),
            match_number INTEGER,
            stage TEXT NOT NULL,
            group_letter TEXT,
            kickoff_date_label TEXT,
            kickoff_time_label TEXT,
            team_a_code TEXT,
            team_b_code TEXT,
            team_a_country TEXT,
            team_b_country TEXT,
            slot_a TEXT NOT NULL,
            slot_b TEXT NOT NULL,
            source TEXT NOT NULL
        );

        CREATE INDEX idx_teams_group ON teams(tournament_id, group_letter, group_position);
        CREATE INDEX idx_matches_stage ON matches(tournament_id, stage);
        CREATE INDEX idx_matches_group ON matches(tournament_id, group_letter);

        CREATE VIEW team_model_inputs AS
        SELECT
            country,
            fifa_code,
            group_letter,
            group_position,
            gdp_per_capita_usd,
            population,
            football_popularity,
            avg_temp_c,
            fifa_rank,
            is_host
        FROM teams;
        """
    )


def insert_tournament(conn, seed):
    tournament = seed["tournament"]
    conn.execute(
        "INSERT INTO tournaments(id, name, notes) VALUES (?, ?, ?)",
        (tournament["id"], tournament["name"], tournament["notes"]),
    )


def insert_sources(conn, seed):
    tournament_id = seed["tournament"]["id"]
    for source in seed["sources"]:
        path = Path(source["path"])
        if not path.is_absolute():
            path = ROOT / path
        exists = path.exists()
        conn.execute(
            """
            INSERT INTO source_files(
                tournament_id, name, original_path, file_name, sha256, exists_on_build
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                tournament_id,
                source["name"],
                str(path),
                path.name,
                sha256_file(path) if exists else None,
                1 if exists else 0,
            ),
        )


def insert_teams(conn, seed, model_inputs):
    tournament_id = seed["tournament"]["id"]
    for group_letter, teams in seed["groups"].items():
        for position, (country, code) in enumerate(teams, start=1):
            is_host = 1 if code in {"CAN", "MEX", "USA"} else 0
            inputs = model_inputs.get(code, [None, None, None, None, None])
            conn.execute(
                """
                INSERT INTO teams(
                    tournament_id, country, fifa_code, group_letter, group_position,
                    gdp_per_capita_usd, population, football_popularity, avg_temp_c,
                    fifa_rank, is_host
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tournament_id,
                    country,
                    code,
                    group_letter,
                    position,
                    inputs[0],
                    inputs[1],
                    inputs[2],
                    inputs[3],
                    inputs[4],
                    is_host,
                ),
            )


def country_lookup(seed):
    lookup = {}
    for teams in seed["groups"].values():
        for country, code in teams:
            lookup[code] = country
    return lookup


def insert_group_matches(conn, seed):
    tournament_id = seed["tournament"]["id"]
    names = country_lookup(seed)
    for match_number, (group, date_label, time_label, code_a, code_b) in enumerate(
        seed["group_matches"], start=1
    ):
        conn.execute(
            """
            INSERT INTO matches(
                tournament_id, match_number, stage, group_letter,
                kickoff_date_label, kickoff_time_label,
                team_a_code, team_b_code, team_a_country, team_b_country,
                slot_a, slot_b, source
            ) VALUES (?, ?, 'Group', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'predictor_pdf')
            """,
            (
                tournament_id,
                match_number,
                group,
                date_label,
                time_label,
                code_a,
                code_b,
                names[code_a],
                names[code_b],
                code_a,
                code_b,
            ),
        )


def insert_knockout_matches(conn, seed):
    tournament_id = seed["tournament"]["id"]
    for match_number, stage, date_label, time_label, slot_a, slot_b in seed["knockout_matches"]:
        conn.execute(
            """
            INSERT INTO matches(
                tournament_id, match_number, stage, group_letter,
                kickoff_date_label, kickoff_time_label,
                team_a_code, team_b_code, team_a_country, team_b_country,
                slot_a, slot_b, source
            ) VALUES (?, ?, ?, NULL, ?, ?, NULL, NULL, NULL, NULL, ?, ?, 'combined_pdfs')
            """,
            (tournament_id, match_number, stage, date_label, time_label, slot_a, slot_b),
        )


def build(seed_path, model_inputs_path, output_path):
    with open(seed_path, "r", encoding="utf-8") as handle:
        seed = json.load(handle)
    with open(model_inputs_path, "r", encoding="utf-8") as handle:
        model_inputs = json.load(handle)

    conn = connect(output_path)
    try:
        create_schema(conn)
        insert_tournament(conn, seed)
        insert_sources(conn, seed)
        insert_teams(conn, seed, model_inputs)
        insert_group_matches(conn, seed)
        insert_knockout_matches(conn, seed)
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Build the Klement World Cup SQLite seed DB.")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--model-inputs", type=Path, default=DEFAULT_MODEL_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    build(args.seed, args.model_inputs, args.output)
    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
