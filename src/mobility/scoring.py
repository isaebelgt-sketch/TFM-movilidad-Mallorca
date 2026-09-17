"""Ranking multiobjetivo explicable de alternativas OTP.

No intenta inferir preferencias reales ni certificar accesibilidad. Cada
puntuación se compone sólo de métricas que devuelve la consulta actual y sus
pesos se entregan junto al resultado para que el usuario pueda auditarlos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .routing import RouteAlternative


@dataclass(frozen=True)
class PreferenceProfile:
    name: str
    time_weight: float
    emissions_weight: float
    walking_weight: float
    transfers_weight: float

    def normalized(self) -> "PreferenceProfile":
        total = self.time_weight + self.emissions_weight + self.walking_weight + self.transfers_weight
        if total <= 0:
            raise ValueError("La suma de pesos debe ser positiva.")
        return PreferenceProfile(
            name=self.name,
            time_weight=self.time_weight / total,
            emissions_weight=self.emissions_weight / total,
            walking_weight=self.walking_weight / total,
            transfers_weight=self.transfers_weight / total,
        )


PROFILES = {
    "balanced": PreferenceProfile("balanced", 0.40, 0.30, 0.20, 0.10),
    "low_carbon": PreferenceProfile("low_carbon", 0.20, 0.55, 0.15, 0.10),
    "low_walking": PreferenceProfile("low_walking", 0.30, 0.15, 0.45, 0.10),
    "fastest": PreferenceProfile("fastest", 0.70, 0.10, 0.10, 0.10),
}


def rank_alternatives(alternatives: Iterable[RouteAlternative], profile: PreferenceProfile) -> list[dict]:
    """Devuelve puntuaciones 0--100 y mantiene fuera del ranking rutas no resueltas."""
    viable = [alternative for alternative in alternatives if alternative.status == "ok"]
    if not viable:
        return []
    profile = profile.normalized()
    durations = _normalise([item.duration_min or 0 for item in viable])
    emissions = _normalise([item.estimated_kg_co2eq or 0 for item in viable])
    walking = _normalise([item.walk_distance_m or 0 for item in viable])
    transfers = _normalise([float(item.transfers or 0) for item in viable])
    ranked = []
    for index, alternative in enumerate(viable):
        penalty = (
            profile.time_weight * durations[index]
            + profile.emissions_weight * emissions[index]
            + profile.walking_weight * walking[index]
            + profile.transfers_weight * transfers[index]
        )
        ranked.append({
            **alternative.as_dict(),
            "sustainability_score": round(100 * (1 - penalty), 1),
            "score_components": {
                "duration_penalty": round(durations[index], 4),
                "emissions_penalty": round(emissions[index], 4),
                "walking_penalty": round(walking[index], 4),
                "transfers_penalty": round(transfers[index], 4),
            },
            "profile": profile.name,
        })
    return sorted(ranked, key=lambda row: (-row["sustainability_score"], row["duration_min"], row["mode"]))


def recommend_sustainable_mode(alternatives: Iterable[RouteAlternative]) -> dict:
    """Aplica reglas de decisión explícitas antes del ranking relativo.

    El ranking normaliza alternativas dentro de cada par y sirve para comparar
    sus costes relativos. Esta política evita que una bicicleta se recomiende
    automáticamente para un paseo de pocos minutos sólo por ser más rápida.
    """
    viable = {item.mode: item for item in alternatives if item.status == "ok"}
    walk = viable.get("WALK")
    bicycle = viable.get("BICYCLE")
    transit = viable.get("TRANSIT")

    if walk and (walk.duration_min or float("inf")) <= 20:
        return {"recommended_mode": "WALK", "recommendation_code": "walk_under_20min", "recommendation_reason": "Recorrido a pie de hasta 20 minutos."}
    if transit and (transit.duration_min or float("inf")) <= 90 and (not bicycle or (bicycle.duration_min or float("inf")) > 30):
        return {"recommended_mode": "TRANSIT", "recommendation_code": "transit_available", "recommendation_reason": "Alternativa con transporte público real y duración acotada."}
    if bicycle and (bicycle.duration_min or float("inf")) <= 30:
        return {"recommended_mode": "BICYCLE", "recommendation_code": "bicycle_under_30min", "recommendation_reason": "Alternativa ciclista de hasta 30 minutos."}
    if transit and (transit.duration_min or float("inf")) <= 120:
        return {"recommended_mode": "TRANSIT", "recommendation_code": "transit_longer_trip", "recommendation_reason": "Transporte público disponible para un desplazamiento que no cumple el umbral activo."}
    if bicycle and (bicycle.duration_min or float("inf")) <= 45:
        return {"recommended_mode": "BICYCLE", "recommendation_code": "bicycle_review_comfort", "recommendation_reason": "Alternativa ciclista posible, pero requiere revisar pendiente, confort y seguridad."}
    return {"recommended_mode": None, "recommendation_code": "no_sustainable_option_under_policy", "recommendation_reason": "No hay alternativa sostenible dentro de los umbrales definidos."}


def _normalise(values: list[float]) -> list[float]:
    minimum, maximum = min(values), max(values)
    if maximum == minimum:
        return [0.0] * len(values)
    return [(value - minimum) / (maximum - minimum) for value in values]
