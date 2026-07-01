# Klement Model Reconstruction

This note separates three things that are easy to conflate:

1. The exact published Joachim Klement 2026 forecast.
2. The public Hoffmann/Ging/Ramasamy econometric equation Klement cites.
3. The still-private pieces of Klement's proprietary tournament implementation.

## What Klement Publishes

The Panmure Liberum note says Klement developed a proprietary econometric
model in 2014 and used the same model for 2014, 2018, 2022, and 2026.

The 2026 note discloses the model inputs:

- GDP per capita.
- Population size, conditional on football being a mainstream sport.
- Average annual temperature, with 14 C described as the ideal football climate.
- Host-country advantage.
- Current FIFA ranking points.
- A chance/luck component.

The note says the socioeconomic variables explain about 55% of World Cup
success, with about 45% determined by luck.

The note does not publish:

- Klement's regression coefficients.
- The exact transformation of FIFA ranking points.
- The exact country-level dataset used in 2026.
- The random distribution used for match luck.
- The number of simulations.
- The exact match-to-match probability conversion.

Therefore, the exact mathematical model cannot be reproduced from the PDF
alone. What can be reproduced exactly is the published 2026 forecast output:
Netherlands beat Portugal in the final.

## Public Academic Base Equation

Klement cites Hoffmann, Ging, and Ramasamy, "The Socio-Economic Determinants
of International Soccer Performance", Journal of Applied Economics, 2002.
That paper estimates the following OLS equation:

```text
Y_i = alpha
    + beta_1 * GNP_i
    + beta_2 * GNP_i^2
    + eta * (TEMP_i - 14)^2
    + kappa * HOST_i
    + phi * LATIN_i * POP_i
    + epsilon_i
```

Where:

- `Y_i` is FIFA/Coca-Cola World Ranking points in January 2001.
- `GNP_i` is GNP per capita.
- `TEMP_i` is average annual Celsius temperature in the capital.
- `HOST_i` is 1 for countries that hosted the World Cup, else 0.
- `LATIN_i` is a Latin/catholic-cultural-origin dummy.
- `POP_i` is country share of world population.

The coefficient table in that paper is:

```text
alpha                  492.5865
GNP                      0.0107
GNP^2                   -2.45e-7
(TEMP - 14)^2           -0.4895
HOST                    81.0510
LATIN * POP           8587.4616
R^2                      0.3180
```

This equation is not itself Klement's 2026 model. It is the public academic
ancestor. Klement adds current FIFA ranking points and a simulation layer, and
he likely recalibrates coefficients on World Cup/tournament data.

## Reconstructable Algorithm

The closest defensible reconstruction is:

1. Build a deterministic country strength score.

```text
base_strength_i =
    b_0
  + b_1 * GDPpc_i
  + b_2 * GDPpc_i^2
  + b_3 * (TEMP_i - 14)^2
  + b_4 * HOST_i
  + b_5 * FOOTBALL_CULTURE_i * POP_SHARE_i
  + b_6 * FIFA_POINTS_i
```

2. Convert two country scores into match probabilities.

```text
P(i beats j) = logistic(gamma * (base_strength_i - base_strength_j))
```

3. Add luck/noise at match level.

```text
match_score_i = deterministic_component_i + random_luck_i
```

with the luck variance calibrated so the deterministic model explains roughly
55% and randomness explains roughly 45% of match outcomes.

4. Simulate the tournament format:

- Group stage.
- Rank group tables.
- Select the eight best third-place teams.
- Resolve the round of 32 bracket.
- Simulate knockouts with increased luck impact.

5. Aggregate simulation results as title probabilities.

## Repository Implementation

The reconstruction is implemented as a configurable algorithm rather than a
hard-coded formula.

```text
data/klement_algorithm_config.json
```

This file stores:

- Hoffmann/Ging/Ramasamy coefficients.
- FIFA-form coefficient/transform settings.
- World population denominator for population share.
- Deterministic/luck shares.
- Logistic match-probability scale.
- Draw band.

The current implementation uses:

```text
base_strength_i =
    intercept
  + b_gdp * GDPpc_i
  + b_gdp2 * GDPpc_i^2
  + b_temp * (TEMP_i - 14)^2
  + b_host * HOST_i
  + b_pop * FOOTBALL_POPULARITY_i * POP_SHARE_i
  + b_rank * FIFA_RANK_SCORE_i
  + b_points * FIFA_POINTS_i
```

Then raw strengths are scaled by the configurable `raw_score_divisor` before
match probabilities are computed. This avoids a single-match normalization bug
where comparing only two teams would force one team to 0 and the other to 1.
If a future calibration works better with tournament min-max scaling, set
`score_output.mode` to `tournament_minmax`.

Team-level values live in:

```text
data/fwc26_model_inputs.json
```

The JSON supports an optional sixth value for FIFA ranking points:

```text
"NED": [gdp_per_capita_usd, population, football_popularity, avg_temp_c, fifa_rank, fifa_points]
```

If FIFA points are not present, the model uses the rank-score term only.

## What We Need To Recover The Exact Klement Model

One of the following is required:

- The private Panmure Liberum spreadsheet/code.
- A table of Klement country strength scores or match probabilities.
- Klement's coefficient vector and random simulation specification.
- Enough published intermediate probabilities to fit an inverse model.

The 2026 PDF gives group advancement percentages and a deterministic-looking
knockout path. Those outputs can be used to calibrate an approximation, but not
to prove the private equations exactly.

## Inverse-Fit Calibration

The repository includes a calibration script:

```text
scripts/calibrate_klement_model.py
```

It searches coefficient/config combinations and writes:

```text
data/klement_algorithm_config.calibrated.json
data/klement_calibration_report.json
```

The objective combines the published group top-two probabilities with the
published knockout winner path. The generated config is available through
`mode=calibrated`, but it remains an inverse-fitted approximation. It should be
recalibrated whenever better published targets, country inputs, or real
coefficient disclosures become available.
