from src.mobility.routing import RouteAlternative
from src.mobility.scoring import recommend_sustainable_mode


def alternative(mode: str, duration: float, status: str = "ok") -> RouteAlternative:
    return RouteAlternative(mode=mode, status=status, duration_min=duration)


def test_short_walk_has_priority_over_bicycle():
    result = recommend_sustainable_mode([alternative("WALK", 12), alternative("BICYCLE", 4)])
    assert result["recommended_mode"] == "WALK"
    assert result["recommendation_code"] == "walk_under_20min"


def test_transit_without_a_transit_leg_is_not_recommended():
    result = recommend_sustainable_mode([alternative("WALK", 45), alternative("TRANSIT", 10, status="no_transit_leg")])
    assert result["recommended_mode"] is None


def test_medium_length_bicycle_is_recommended_when_walk_is_too_long():
    result = recommend_sustainable_mode([alternative("WALK", 50), alternative("BICYCLE", 26)])
    assert result["recommended_mode"] == "BICYCLE"
