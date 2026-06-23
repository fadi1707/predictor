# Predictor

Predictor is a FastAPI-based Joachim Klement-style FIFA World Cup prediction
engine. It includes a seeded FIFA World Cup 2026 tournament database generated
from the supplied tournament PDFs, plus endpoints for single-match probability
checks and Monte Carlo knockout simulations.

Klement's exact private coefficients are not public. This implementation uses a
transparent approximation based on the public Hoffmann, Ging, and Ramasamy
framework: FIFA ranking, football-adjusted population, GDP per capita with
diminishing returns around $60,000, temperature fit around 14 C, host advantage,
and a Monte Carlo luck component.

## Run Locally

Windows:

```cmd
scripts\install_win.bat
scripts\run_win.bat
```

Linux/macOS:

```bash
./scripts/install.sh
source .venv/bin/activate
./scripts/run.sh
```

Open:

```text
http://127.0.0.1:8080/
```

## Main Endpoints

```text
POST /api/klement/match
POST /api/klement/tournament
GET  /api/health/local
```

Single match example:

```bash
curl -X POST http://127.0.0.1:8080/api/klement/match ^
  -H "Content-Type: application/json" ^
  -d "{\"team_a\":{\"country\":\"Argentina\",\"gdp_per_capita_usd\":13730,\"population\":45800000,\"football_popularity\":0.9,\"avg_temp_c\":14.8,\"fifa_rank\":1},\"team_b\":{\"country\":\"France\",\"gdp_per_capita_usd\":44400,\"population\":68200000,\"football_popularity\":0.75,\"avg_temp_c\":11.7,\"fifa_rank\":2}}"
```

Knockout simulation example:

```bash
curl -X POST http://127.0.0.1:8080/api/klement/tournament ^
  -H "Content-Type: application/json" ^
  -d "{\"simulations\":10000,\"seed\":7,\"teams\":[{\"country\":\"Argentina\",\"gdp_per_capita_usd\":13730,\"population\":45800000,\"football_popularity\":0.9,\"avg_temp_c\":14.8,\"fifa_rank\":1},{\"country\":\"France\",\"gdp_per_capita_usd\":44400,\"population\":68200000,\"football_popularity\":0.75,\"avg_temp_c\":11.7,\"fifa_rank\":2},{\"country\":\"Brazil\",\"gdp_per_capita_usd\":10000,\"population\":203000000,\"football_popularity\":0.9,\"avg_temp_c\":25.0,\"fifa_rank\":5},{\"country\":\"England\",\"gdp_per_capita_usd\":48900,\"population\":57000000,\"football_popularity\":0.65,\"avg_temp_c\":9.3,\"fifa_rank\":4}]}"
```

## Tournament Database

The seed data lives in:

```text
data/fwc26_seed.json
data/klement_world_cup_2026.db
source_pdfs/
```

Rebuild the SQLite DB:

```bash
python scripts/build_klement_db.py
```

The DB contains 48 teams, 12 groups, 72 group-stage matches, and 104 total
matches including knockout placeholders. Model input columns such as GDP,
population, temperature, and FIFA rank are nullable because the PDFs provide
tournament structure, not economic or ranking data.

## CI/CD

Artifact versioning is configured in:

```text
config/artifact-version.yml
```

The GitHub Actions pipeline:

- builds release artifacts only from `main`
- builds `SNAPSHOT` artifacts from every other branch
- uploads the packaged zip as a workflow artifact
- publishes a GitHub release from `main`
- bumps the next patch version after a release build

Local package build:

```bash
python scripts/resolve_artifact_version.py --config config/artifact-version.yml
python scripts/package_predictor.py --artifact-name predictor-local
```
