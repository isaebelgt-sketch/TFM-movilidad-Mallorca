from src.mobility.routing import RouteAlternative
from src.mobility.scoring import PROFILES, rank_alternatives


def alternative(mode: str, duration: float, emissions: float, walking: float, transfers: int = 0) -> RouteAlternative:
    return RouteAlternative(
        mode=mode,
        status="ok",
        duration_min=duration,
        estimated_kg_co2eq=emissions,
        walk_distance_m=walking,
        distance_m=1000,
        transfers=transfers,
    )


def test_low_carbon_profile_prefers_zero_emission_alternative():
    routes = [
        alternative("CAR", 8, 0.5, 0),
        alternative("WALK", 18, 0, 1800),
        alternative("TRANSIT", 90, 0.08, 8000, 0),
    ]
    result = rank_alternatives(routes, PROFILES["low_carbon"])
    assert result[0]["mode"] == "WALK"
    assert result[0]["sustainability_score"] >= result[-1]["sustainability_score"]


def test_unresolved_routes_do_not_receive_a_score():
    result = rank_alternatives([RouteAlternative(mode="TRANSIT", status="no_route")], PROFILES["balanced"])
    assert result == []


def test_scores_include_auditable_components():
    result = rank_alternatives(
        [alternative("BICYCLE", 10, 0, 50), alternative("CAR", 8, 0.3, 0)],
        PROFILES["balanced"],
    )
    assert {"duration_penalty", "emissions_penalty", "walking_penalty", "transfers_penalty"} == set(result[0]["score_components"])
