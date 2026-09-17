from pathlib import Path
import sys

import pandas as pd
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.main import app  # noqa: E402


def test_legacy_tsmai_contract_and_universal_proxy():
    """Los artefactos anteriores se conservan sólo para reproducibilidad."""
    index = pd.read_parquet(ROOT / "data" / "curated" / "municipality_tourism_sustainable_mobility_index.parquet")
    universal = pd.read_parquet(ROOT / "data" / "curated" / "accommodations_universal_access_proximity.parquet")
    assert len(index) == 51
    assert index["tsmai_v1_score"].between(0, 1).all()
    assert set(index["tsmai_v1_level"].astype(str)).issubset({"favorable", "intermedio", "prioridad de mejora"})
    assert len(universal) == 1463
    assert "wheelchair_stop_within_800m" in universal.columns


def test_api_exposes_current_tsmai_v9_and_legacy_case():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["index_version"] == "TSMAI V9"
    assert health.json()["accommodations"] == 1461
    municipalities = client.get("/municipalities")
    assert municipalities.status_code == 200
    assert len(municipalities.json()) == 51
    assert {"tsmai_v9_score", "tsmai_v9_level", "winter_worsening_pct"}.issubset(municipalities.json()[0])
    accommodations = client.get("/accommodations/tsmai", params={"level": "prioridad de mejora", "limit": 10})
    assert accommodations.status_code == 200
    assert 1 <= len(accommodations.json()) <= 10
    assert {"accommodation_id", "tsmai_v9_score", "seasonal_change"}.issubset(accommodations.json()[0])
    sensitivity = client.get("/sensitivity/tsmai-v9")
    assert sensitivity.status_code == 200
    assert sensitivity.json()["accommodation_results"]["records"] == 1461
    municipal_sensitivity = client.get("/sensitivity/tsmai-v9/municipalities", params={"robust_only": True})
    assert municipal_sensitivity.status_code == 200
    assert len(municipal_sensitivity.json()) == 5
    assert municipal_sensitivity.json()[0]["robust_top_decile"] is True
    legacy = client.get("/legacy/municipalities-v1")
    assert legacy.status_code == 200
    assert "tsmai_v1_score" in legacy.json()[0]
    case = client.get("/cases/OD03")
    assert case.status_code == 200
    assert case.json()["od_id"] == "OD03"
