import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"


def test_final_artifacts_are_present():
    names = ["accommodations_transport_access_baseline.parquet", "tourism_destinations_transport_access_baseline.parquet", "od_multimodal_priority_index.parquet", "od_multimodal_priority_sensitivity.parquet", "multimodal_intervention_recommendations.parquet", "od_multimodal_emissions.parquet", "municipality_accessibility_clusters.parquet"]
    assert all((CURATED / name).exists() for name in names)


def test_spatial_baseline_contract():
    lodgings = gpd.read_parquet(CURATED / "accommodations_transport_access_baseline.parquet")
    destinations = gpd.read_parquet(CURATED / "tourism_destinations_transport_access_baseline.parquet")
    assert len(lodgings) == 1463 and lodgings.geometry.notna().all() and lodgings.geometry.is_valid.all()
    assert lodgings["distance_to_nearest_stop_euclidean_m"].notna().all()
    assert len(destinations) == 1423 and destinations.geometry.notna().all() and destinations.geometry.is_valid.all()


def test_priority_and_recommendation_contract():
    priorities = pd.read_parquet(CURATED / "od_multimodal_priority_index.parquet")
    sensitivity = pd.read_parquet(CURATED / "od_multimodal_priority_sensitivity.parquet")
    recommendations = pd.read_parquet(CURATED / "multimodal_intervention_recommendations.parquet")
    assert len(priorities) == len(sensitivity) == len(recommendations) == 20
    assert priorities.od_id.is_unique and sensitivity.od_id.is_unique and recommendations.od_id.is_unique
    joined = priorities.merge(sensitivity[["od_id", "robust_priority"]], on="od_id", validate="one_to_one").merge(recommendations[["od_id", "recommendation_code"]], on="od_id", validate="one_to_one")
    assert joined.recommendation_code.notna().all() and joined.robust_priority.sum() == 5


def test_environmental_comparison_contract():
    emissions = pd.read_parquet(CURATED / "od_multimodal_emissions.parquet")
    comparable = emissions.loc[emissions.car_status.eq("ok")]
    assert len(emissions) == 7 and len(comparable) == 6
    assert comparable.estimated_avoided_kg_co2eq.notna().all() and comparable.estimated_avoided_kg_co2eq.sum() > 0


def test_current_tsmai_v9_dashboard_contract():
    v9 = gpd.read_parquet(CURATED / "accommodations_tsmai_v9_seasonal_transit.parquet")
    sensitivity = pd.read_parquet(CURATED / "municipality_tsmai_v9_sensitivity.parquet")
    manifest = json.loads((CURATED / "latest_dashboard_current_layers.json").read_text(encoding="utf-8"))

    assert len(v9) == 1461
    assert v9.geometry.notna().all() and v9.geometry.is_valid.all()
    assert {"tsmai_v9_score", "tsmai_v9_level", "seasonal_transit_destination_score"}.issubset(v9.columns)
    assert {"municipality", "accommodations", "balanced_score", "robust_top_decile"}.issubset(sensitivity.columns)
    assert set(manifest["outputs"]) == {"accommodations", "stops", "destinations", "cycling"}
    assert manifest["counts"]["accommodations"] == len(v9)


def test_tsmai_v9_reports_are_internally_consistent():
    v9_report = json.loads((ROOT / "docs" / "tsmai_v9_seasonal_transit_report.json").read_text(encoding="utf-8"))
    sensitivity_report = json.loads((ROOT / "docs" / "tsmai_v9_sensitivity_report.json").read_text(encoding="utf-8"))

    assert v9_report["records"] == 1461
    assert sum(v9_report["weights"].values()) == 1.0
    assert sum(v9_report["levels"].values()) == v9_report["records"]
    assert sum(v9_report["seasonal_transit_component"]["seasonal_change_counts"].values()) == v9_report["records"]
    assert sensitivity_report["input"]["records"] == v9_report["records"]
    assert sensitivity_report["accommodation_results"]["level_stable_all_scenarios"] + sensitivity_report["accommodation_results"]["level_changed_in_any_scenario"] == v9_report["records"]
