import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.etl_05_analizar_datos as etl_05  # noqa: E402


def test_prioritize_access_interventions_orders_by_value_density(tmp_path, monkeypatch):
    scenarios = pd.DataFrame([
        {"municipality": "ALFA", "accommodations": 100, "tourist_places": 1000.0, "first_last_mile_candidates": 10},
        {"municipality": "BETA", "accommodations": 50, "tourist_places": 100.0, "first_last_mile_candidates": 10},
        {"municipality": "GAMMA", "accommodations": 20, "tourist_places": 0.0, "first_last_mile_candidates": 0},
    ])
    input_path = tmp_path / "scenarios.parquet"
    scenarios.to_parquet(input_path, index=False)
    output_path = tmp_path / "priority.parquet"
    report_path = tmp_path / "report.json"

    monkeypatch.setattr(etl_05, "INTERVENTION_PRIORITY_INPUT", input_path)
    monkeypatch.setattr(etl_05, "INTERVENTION_PRIORITY_OUT", output_path)
    monkeypatch.setattr(etl_05, "INTERVENTION_PRIORITY_REPORT", report_path)

    etl_05.main_prioritize_access_interventions()

    result = pd.read_parquet(output_path)
    # GAMMA no tiene candidatos: queda fuera de la priorización.
    assert set(result["municipality"]) == {"ALFA", "BETA"}
    # Mismo coste (10 candidatos); ALFA tiene mas demanda turistica relativa -> mayor value_density -> va primero.
    assert list(result["municipality"]) == ["ALFA", "BETA"]
    assert list(result["priority_rank"]) == [1, 2]
    # La densidad de valor debe ser estrictamente decreciente en el orden de prioridad.
    assert result["value_density"].is_monotonic_decreasing
    # El coste acumulado debe sumar el total de candidatos considerados.
    assert result["cumulative_cost_accommodations"].iloc[-1] == 20
    assert result["cumulative_cost_pct"].iloc[-1] == 100.0
    assert result["cumulative_value_pct"].iloc[-1] == 100.0

    import json

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["totals"]["total_candidate_accommodations"] == 20
    assert report["totals"]["municipalities_with_candidates"] == 2
    checkpoint_100 = next(c for c in report["budget_checkpoints"] if c["budget_pct_of_total_candidates"] == 100)
    assert checkpoint_100["accommodations_resolved"] == 20
    assert checkpoint_100["municipalities_funded"] == 2


def test_prioritize_access_interventions_requires_candidates(tmp_path, monkeypatch):
    scenarios = pd.DataFrame([
        {"municipality": "ALFA", "accommodations": 10, "tourist_places": 100.0, "first_last_mile_candidates": 0},
    ])
    input_path = tmp_path / "scenarios.parquet"
    scenarios.to_parquet(input_path, index=False)

    monkeypatch.setattr(etl_05, "INTERVENTION_PRIORITY_INPUT", input_path)
    monkeypatch.setattr(etl_05, "INTERVENTION_PRIORITY_OUT", tmp_path / "priority.parquet")
    monkeypatch.setattr(etl_05, "INTERVENTION_PRIORITY_REPORT", tmp_path / "report.json")

    try:
        etl_05.main_prioritize_access_interventions()
    except ValueError as exc:
        assert "nada que priorizar" in str(exc)
    else:
        raise AssertionError("Se esperaba ValueError cuando no hay municipios candidatos.")
