from fastapi.testclient import TestClient

import api.main as api
from src.mobility.catalog import Place
from src.mobility.routing import RouteAlternative


class FakeCatalog:
    def accommodation(self, accommodation_id: str) -> Place:
        assert accommodation_id == "A1"
        return Place("A1", "Hotel de prueba", 39.6, 2.9, "accommodation", "Palma")

    def destination(self, poi_id: str) -> Place:
        assert poi_id == "P1"
        return Place("P1", "Museo de prueba", 39.61, 2.91, "destination")


class FakeOtpClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def compare(self, origin, destination, routing_date, routing_time):
        return [
            RouteAlternative("WALK", "ok", duration_min=22, walk_distance_m=1800, distance_m=1800, transfers=0, estimated_kg_co2eq=0),
            RouteAlternative("BICYCLE", "ok", duration_min=9, walk_distance_m=0, distance_m=1900, transfers=0, estimated_kg_co2eq=0),
            RouteAlternative("TRANSIT", "no_route", message="Sin servicio"),
            RouteAlternative("CAR", "ok", duration_min=6, walk_distance_m=0, distance_m=2400, transfers=0, estimated_kg_co2eq=0.228),
        ]


def test_route_comparison_returns_ranked_and_unavailable_routes(monkeypatch):
    monkeypatch.setattr(api, "catalog", lambda: FakeCatalog())
    monkeypatch.setattr(api, "OtpClient", FakeOtpClient)
    client = TestClient(api.app)
    response = client.post(
        "/routes/compare",
        json={
            "origin": {"source": "accommodation", "id": "A1"},
            "destination": {"source": "destination", "id": "P1"},
            "routing_date": "2026-09-03",
            "routing_time": "12:00:00",
            "profile": "low_carbon",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"] == "BICYCLE"
    assert len(payload["alternatives"]) == 3
    assert payload["unavailable_alternatives"][0]["mode"] == "TRANSIT"
    assert payload["method"]["criteria"] == ["duration", "estimated_co2eq", "walk_distance", "transfers"]
