"""Cliente OTP tipado y sin estado para comparaciones multimodales."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any

import requests

from .catalog import Place


SUPPORTED_MODES = ("WALK", "BICYCLE", "TRANSIT", "CAR")
EMISSION_FACTORS_KG_CO2EQ_PER_KM = {"WALK": 0.0, "BICYCLE": 0.0, "TRANSIT": 0.065, "CAR": 0.095}

ROUTE_QUERY = """
query PlanRoute($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!, $modes: [TransportMode]!) {
  plan(from: $from, to: $to, date: $date, time: $time, transportModes: $modes, numItineraries: 1) {
    itineraries {
      duration
      walkDistance
      legs { mode distance duration legGeometry { points } route { shortName longName } }
    }
    routingErrors { code description inputField }
  }
}
"""


@dataclass(frozen=True)
class RouteLeg:
    mode: str
    distance_m: float
    duration_min: float
    line: str | None = None
    geometry: str | None = None

    def as_dict(self) -> dict[str, str | float | None]:
        return {
            "mode": self.mode,
            "distance_m": round(self.distance_m, 1),
            "duration_min": round(self.duration_min, 2),
            "line": self.line,
            "geometry": self.geometry,
        }


@dataclass(frozen=True)
class RouteAlternative:
    mode: str
    status: str
    duration_min: float | None = None
    walk_distance_m: float | None = None
    distance_m: float | None = None
    transfers: int | None = None
    estimated_kg_co2eq: float | None = None
    legs: tuple[RouteLeg, ...] = field(default_factory=tuple)
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "status": self.status,
            "duration_min": _round_or_none(self.duration_min),
            "walk_distance_m": _round_or_none(self.walk_distance_m),
            "distance_m": _round_or_none(self.distance_m),
            "transfers": self.transfers,
            "estimated_kg_co2eq": _round_or_none(self.estimated_kg_co2eq, 4),
            "legs": [leg.as_dict() for leg in self.legs],
            "message": self.message,
        }


class OtpClient:
    """Consulta una instancia OTP y conserva los errores como resultados trazables."""

    def __init__(self, endpoint: str, timeout_seconds: int = 45):
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def plan(self, origin: Place, destination: Place, mode: str, routing_date: date, routing_time: time) -> RouteAlternative:
        mode = mode.upper()
        if mode not in SUPPORTED_MODES:
            raise ValueError(f"Modo no soportado: {mode}")
        _validate_coordinates(origin)
        _validate_coordinates(destination)
        variables = {
            "from": {"lat": origin.latitude, "lon": origin.longitude},
            "to": {"lat": destination.latitude, "lon": destination.longitude},
            "date": routing_date.isoformat(),
            "time": routing_time.strftime("%H:%M"),
            "modes": [{"mode": mode}],
        }
        try:
            response = requests.post(self.endpoint, json={"query": ROUTE_QUERY, "variables": variables}, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return RouteAlternative(mode=mode, status="service_unavailable", message=str(exc))
        except ValueError:
            return RouteAlternative(mode=mode, status="invalid_response", message="OTP no devolvió JSON válido.")

        if payload.get("errors"):
            return RouteAlternative(mode=mode, status="graphql_error", message="OTP rechazó la consulta.")
        plan = payload.get("data", {}).get("plan") or {}
        errors = plan.get("routingErrors") or []
        itineraries = plan.get("itineraries") or []
        if errors or not itineraries:
            reason = errors[0].get("description") if errors else "No existe itinerario para la fecha y hora solicitadas."
            return RouteAlternative(mode=mode, status="no_route", message=reason)
        return _parse_itinerary(mode, itineraries[0])

    def compare(self, origin: Place, destination: Place, routing_date: date, routing_time: time) -> list[RouteAlternative]:
        """Obtiene alternativas en paralelo para no convertir cuatro modos en una espera serial."""
        results: dict[str, RouteAlternative] = {}
        with ThreadPoolExecutor(max_workers=len(SUPPORTED_MODES)) as executor:
            futures = {
                executor.submit(self.plan, origin, destination, mode, routing_date, routing_time): mode
                for mode in SUPPORTED_MODES
            }
            for future in as_completed(futures):
                mode = futures[future]
                try:
                    results[mode] = future.result()
                except Exception as exc:  # Nunca ocultar un fallo de un modo como si fuera ausencia de ruta.
                    results[mode] = RouteAlternative(mode=mode, status="internal_error", message=str(exc))
        return [results[mode] for mode in SUPPORTED_MODES]


def _parse_itinerary(mode: str, itinerary: dict[str, Any]) -> RouteAlternative:
    legs = tuple(_parse_leg(leg) for leg in itinerary.get("legs") or [])
    if mode == "TRANSIT" and not any(leg.mode not in {"WALK", "BICYCLE", "CAR"} for leg in legs):
        return RouteAlternative(
            mode=mode,
            status="no_transit_leg",
            message="OTP devolvió un itinerario sin tramo de transporte público para esta consulta.",
            legs=legs,
        )
    total_distance = sum(leg.distance_m for leg in legs)
    transit_distance = sum(leg.distance_m for leg in legs if leg.mode not in {"WALK", "BICYCLE", "CAR"})
    emission_distance = transit_distance if mode == "TRANSIT" else total_distance
    transfers = max(sum(leg.mode not in {"WALK", "BICYCLE", "CAR"} for leg in legs) - 1, 0) if mode == "TRANSIT" else 0
    return RouteAlternative(
        mode=mode,
        status="ok",
        duration_min=float(itinerary.get("duration", 0)) / 60,
        walk_distance_m=float(itinerary.get("walkDistance", 0)),
        distance_m=total_distance,
        transfers=transfers,
        estimated_kg_co2eq=emission_distance / 1000 * EMISSION_FACTORS_KG_CO2EQ_PER_KM[mode],
        legs=legs,
    )


def _parse_leg(leg: dict[str, Any]) -> RouteLeg:
    route = leg.get("route") or {}
    return RouteLeg(
        mode=str(leg.get("mode", "UNKNOWN")),
        distance_m=float(leg.get("distance", 0)),
        duration_min=float(leg.get("duration", 0)) / 60,
        line=route.get("shortName") or route.get("longName"),
        geometry=(leg.get("legGeometry") or {}).get("points"),
    )


def _validate_coordinates(place: Place) -> None:
    if not (-90 <= place.latitude <= 90 and -180 <= place.longitude <= 180):
        raise ValueError(f"Coordenadas fuera de rango para {place.id}")


def _round_or_none(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None
