from app.api.routes import klement_fwc26_winner, klement_model_calibration
from app.klement_calibration import load_calibrated_config, load_calibration_report


def test_calibrated_config_is_inverse_fit():
    config = load_calibrated_config()

    assert config["algorithm_id"] == "klement_inverse_fit_public_targets_v1"
    assert "calibration" in config
    assert "host_country_multipliers" in config["transforms"]


def test_calibration_report_is_available():
    report = load_calibration_report()

    assert report["status"] == "complete"
    assert report["validation_score"]["target_count"] > 0
    assert report["validation_score"]["knockout_target_count"] > 0


def test_calibrated_winner_endpoint_uses_calibrated_algorithm():
    payload = klement_fwc26_winner(mode="calibrated", simulations=20, seed=7)
    assert payload["algorithm"]["id"] == "klement_inverse_fit_public_targets_v1"
    assert payload["most_probable_winner"] is not None


def test_calibration_report_endpoint():
    assert klement_model_calibration()["status"] == "complete"
