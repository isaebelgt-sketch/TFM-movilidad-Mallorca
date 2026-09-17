from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from project_tools import calculate_emissions_scenarios  # noqa: E402


def test_massive_validation_artifacts_are_consistent():
    report = pd.read_json(ROOT / "docs" / "async_massive_processing_validation_report.json", typ="series")
    assert report["validation_status"] == "passed"
    assert report["pairs_screened"] == 1463
    assert report["routing"]["ok"] == 1441
    assert (ROOT / "data" / "curated" / "od_multimodal_routes_massive_summary.parquet").exists()


def test_emissions_scenarios_expose_assumptions_and_increase_monotonically():
    scenarios = [
        {"name": "Conservador", "occupancy_rate": 0.55, "average_stay_nights": 4.5, "modal_shift_rate": 0.10},
        {"name": "Central", "occupancy_rate": 0.70, "average_stay_nights": 4.0, "modal_shift_rate": 0.20},
        {"name": "Ambicioso", "occupancy_rate": 0.82, "average_stay_nights": 3.5, "modal_shift_rate": 0.35},
    ]
    result = calculate_emissions_scenarios(pd.Series([10, 20, None]), 0.474, scenarios)
    assert list(result["Escenario"]) == ["Conservador", "Central", "Ambicioso"]
    assert result["CO2eq evitado estimado (kg/año)"].is_monotonic_increasing
    assert {"Ocupación (%)", "Estancia media (noches)", "Adopción modal (%)"}.issubset(result.columns)
