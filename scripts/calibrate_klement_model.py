import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.klement_calibration import (
    CALIBRATED_CONFIG_PATH,
    CALIBRATION_REPORT_PATH,
    calibrate_config,
)


def write_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Inverse-fit the public Klement reconstruction to published 2026 targets."
    )
    parser.add_argument("--candidates", type=int, default=120)
    parser.add_argument("--simulations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--config-out", default=str(CALIBRATED_CONFIG_PATH))
    parser.add_argument("--report-out", default=str(CALIBRATION_REPORT_PATH))
    args = parser.parse_args()

    config, report = calibrate_config(
        candidates=args.candidates,
        simulations=args.simulations,
        seed=args.seed,
    )
    write_json(args.config_out, config)
    write_json(args.report_out, report)
    validation = report["validation_score"]
    print(
        "calibration complete: "
        f"objective={validation['objective_score']} "
        f"group_rmse={validation['group_root_mean_squared_error']} "
        f"knockout_rmse={validation['knockout_root_mean_squared_error']} "
        f"config={args.config_out} report={args.report_out}"
    )


if __name__ == "__main__":
    main()
