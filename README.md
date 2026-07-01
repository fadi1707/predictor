# Predictor

Predictor is a FastAPI-based FIFA World Cup prediction service. It includes
Joachim Klement's published 2026 World Cup forecast from the Panmure Liberum
strategy note, plus a separate transparent Klement-style Monte Carlo simulator
for experimentation.

Klement's exact private regression coefficients are not public in the PDF. The
default endpoint therefore returns his exact published 2026 forecast output:
Netherlands over Portugal. The simulation mode remains an approximation based on
the public Hoffmann, Ging, and Ramasamy-style factors.

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
GET  /api/klement/fwc26/winner
POST /api/klement/fwc26/winner
GET  /api/klement/model/config
GET  /api/klement/model/calibration
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
population, temperature, and FIFA rank are populated from
`data/fwc26_model_inputs.json`, which is a starter dataset for running the
model end-to-end.

Return Klement's exact published 2026 forecast:

```bash
curl "http://127.0.0.1:8080/api/klement/fwc26/winner"
```

Run the separate approximation/simulation mode from the DB:

```bash
curl "http://127.0.0.1:8080/api/klement/fwc26/winner?mode=simulation&simulations=10000&seed=7"
```

Run the inverse-fitted calibration mode:

```bash
curl "http://127.0.0.1:8080/api/klement/fwc26/winner?mode=calibrated&simulations=10000&seed=7"
```

Inspect the calibration report:

```bash
curl "http://127.0.0.1:8080/api/klement/model/calibration"
```

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

## Updating The Algorithm

The simulation algorithm is intentionally data/config driven:

```text
data/klement_algorithm_config.json
data/fwc26_model_inputs.json
```

Update `klement_algorithm_config.json` when better coefficients, FIFA-points
transforms, luck settings, or probability mappings become available. Update
`fwc26_model_inputs.json` when team-level GDP, population, temperature, FIFA
ranking, FIFA points, or football-culture inputs change. Then rebuild:

```bash
python scripts/build_klement_db.py
```

Generate a calibrated reconstruction fitted to Klement's published 2026 output
targets:

```bash
python scripts/calibrate_klement_model.py --candidates 1000 --simulations 500 --seed 2029
```

This writes:

```text
data/klement_algorithm_config.calibrated.json
data/klement_calibration_report.json
```

The calibrated file is an inverse fit to published outputs, not proof of
Klement's private formula.

Inspect the active algorithm:

```bash
curl "http://127.0.0.1:8080/api/klement/model/config"
```
