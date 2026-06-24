import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORECAST_PATH = ROOT / "data" / "klement_2026_published_forecast.json"


def load_klement_2026_forecast(path=DEFAULT_FORECAST_PATH):
    with open(path, "r", encoding="utf-8") as handle:
        forecast = json.load(handle)

    winner = forecast["winner"]
    return {
        "mode": "klement_published_forecast",
        "most_probable_winner": {
            "country": winner["country"],
            "fifa_code": winner["fifa_code"],
        },
        "forecast": forecast,
    }
