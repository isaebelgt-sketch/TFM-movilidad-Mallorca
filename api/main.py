"""API local y de solo lectura para indicadores y rutas del TFM."""

from datetime import date, time
from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Literal

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.mobility.catalog import Place, TourismCatalog
from src.mobility.routing import EMISSION_FACTORS_KG_CO2EQ_PER_KM, OtpClient
from src.mobility.scoring import PROFILES, rank_alternatives


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
OTP_ENDPOINT = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
TSMAI_V9_FILE = CURATED / "accommodations_tsmai_v9_seasonal_transit.parquet"
TSMAI_V9_LATEST_FILE = CURATED / "latest_tsmai_v9.json"
TSMAI_V9_SENSITIVITY_FILE = CURATED / "municipality_tsmai_v9_sensitivity.parquet"
TSMAI_V9_SENSITIVITY_LATEST_FILE = CURATED / "latest_tsmai_v9_sensitivity.json"
LEGACY_MUNICIPAL_INDEX_FILE = CURATED / "municipality_tourism_sustainable_mobility_index.parquet"

app = FastAPI(
    title="Mallorca Sustainable Mobility API",
    version="2.0.0",
    description=(
        "API local, trazable y de solo lectura del TFM. El contrato principal "
        "publica TSMAI V9 por alojamiento y agregación municipal."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501"], allow_methods=["GET", "POST"], allow_headers=["*"])


class CatalogReference(BaseModel):
    """Origen o destino procedente del catálogo curado o de un punto manual."""

    source: Literal["accommodation", "destination", "coordinate"]
    id: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    name: str | None = Field(default=None, max_length=160)


class RouteComparisonRequest(BaseModel):
    origin: CatalogReference
    destination: CatalogReference
    routing_date: date
    routing_time: time
    profile: Literal["balanced", "low_carbon", "low_walking", "fastest"] = "balanced"


def records(frame: pd.DataFrame) -> list[dict]:
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


@lru_cache
def catalog() -> TourismCatalog:
    return TourismCatalog(ROOT)


@lru_cache
def load_tsmai_v9() -> pd.DataFrame:
    """Carga el índice actual, calculado con redes y calendarios versionados."""
    return pd.read_parquet(TSMAI_V9_FILE)


@lru_cache
def municipality_tsmai_v9() -> pd.DataFrame:
    """Agrega TSMAI V9 sin sustituir las evidencias individuales."""
    data = load_tsmai_v9().copy()
    grouped = (
        data.groupby("municipality", dropna=False)
        .agg(
            accommodations=("accommodation_id", "size"),
            tsmai_v9_score=("tsmai_v9_score", "mean"),
            summer_transit_score=("summer_transit_score", "mean"),
            winter_transit_score=("winter_transit_score", "mean"),
            seasonal_transit_destination_score=("seasonal_transit_destination_score", "mean"),
            priority_improvement_pct=(
                "tsmai_v9_level",
                lambda values: 100 * values.astype("string").eq("prioridad de mejora").mean(),
            ),
            winter_worsening_pct=(
                "seasonal_change",
                lambda values: 100 * values.astype("string").eq("worsens").mean(),
            ),
        )
        .reset_index()
    )
    grouped["tsmai_v9_level"] = pd.cut(
        grouped["tsmai_v9_score"],
        bins=[-0.01, 0.40, 0.67, 1.01],
        labels=["prioridad de mejora", "intermedio", "favorable"],
    ).astype("string")
    numeric_columns = [
        "tsmai_v9_score",
        "summer_transit_score",
        "winter_transit_score",
        "seasonal_transit_destination_score",
        "priority_improvement_pct",
        "winter_worsening_pct",
    ]
    grouped.loc[:, numeric_columns] = grouped.loc[:, numeric_columns].round(3)
    return grouped


@lru_cache
def load_legacy_index() -> pd.DataFrame:
    """Conserva la línea base v1 únicamente para reproducibilidad histórica."""
    return pd.read_parquet(LEGACY_MUNICIPAL_INDEX_FILE)


@lru_cache
def load_tsmai_v9_sensitivity() -> pd.DataFrame:
    return pd.read_parquet(TSMAI_V9_SENSITIVITY_FILE)


@lru_cache
def load_cases() -> pd.DataFrame:
    priorities = pd.read_parquet(CURATED / "od_multimodal_priority_index.parquet")
    recommendations = pd.read_parquet(CURATED / "multimodal_intervention_recommendations.parquet")
    return priorities.merge(recommendations[["od_id", "recommendation_code", "recommendation", "evidence"]], on="od_id", how="left", validate="one_to_one")


@app.get("/")
def root() -> dict:
    return {"service": "Mallorca Sustainable Mobility API", "documentation": "/docs", "version": app.version}


@app.get("/health")
def health() -> dict:
    report = json.loads(TSMAI_V9_LATEST_FILE.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "index_version": "TSMAI V9",
        "accommodations": report["records"],
        "validation_status": report["status"],
        "otp_endpoint": OTP_ENDPOINT,
        "routing_profiles": sorted(PROFILES),
        "data_contract": (
            "TSMAI V9 combina alojamiento oficial, OSM, GTFS TIB, rutas OTP y "
            "escenarios estacionales versionados. Los puntos del catálogo proceden "
            "exclusivamente de capas curated validadas."
        ),
    }


@app.get("/municipalities")
def municipalities(level: str | None = Query(default=None, description="favorable, intermedio o prioridad de mejora")) -> list[dict]:
    """Resumen municipal del producto vigente TSMAI V9."""
    data = municipality_tsmai_v9().copy()
    if level:
        data = data.loc[data["tsmai_v9_level"].astype("string").eq(level)]
    columns = [
        "municipality",
        "accommodations",
        "tsmai_v9_score",
        "tsmai_v9_level",
        "summer_transit_score",
        "winter_transit_score",
        "seasonal_transit_destination_score",
        "priority_improvement_pct",
        "winter_worsening_pct",
    ]
    return records(data.loc[:, columns].sort_values("tsmai_v9_score", ascending=False))


@app.get("/accommodations/tsmai")
def accommodations_tsmai(
    municipality: str | None = Query(default=None, max_length=120),
    level: str | None = Query(default=None, description="favorable, intermedio o prioridad de mejora"),
    limit: int = Query(default=200, ge=1, le=1500),
) -> list[dict]:
    """Evidencia TSMAI V9 por alojamiento, sin inferir accesibilidad certificada."""
    data = load_tsmai_v9().copy()
    if municipality:
        data = data.loc[data["municipality"].astype("string").str.casefold().eq(municipality.casefold())]
    if level:
        data = data.loc[data["tsmai_v9_level"].astype("string").eq(level)]
    columns = [
        "accommodation_id",
        "commercial_name",
        "municipality",
        "group",
        "subgroup",
        "tsmai_v9_score",
        "tsmai_v9_level",
        "summer_transit_score",
        "winter_transit_score",
        "seasonal_transit_destination_score",
        "seasonal_change",
        "transit_ok_share_delta_pp",
        "tib_stop_access_band",
        "walk_15min",
        "bicycle_20min",
    ]
    return records(data.loc[:, columns].sort_values(["tsmai_v9_score", "commercial_name"]).head(limit))


@app.get("/sensitivity/tsmai-v9")
def tsmai_v9_sensitivity() -> dict:
    """Metodología y métricas de estabilidad de las ponderaciones de TSMAI V9."""
    return json.loads(TSMAI_V9_SENSITIVITY_LATEST_FILE.read_text(encoding="utf-8"))


@app.get("/sensitivity/tsmai-v9/municipalities")
def tsmai_v9_sensitivity_municipalities(
    robust_only: bool = Query(default=False, description="Devuelve sólo municipios robustos del top decil."),
) -> list[dict]:
    """Resultados municipales de sensibilidad; no son un nuevo índice oficial."""
    data = load_tsmai_v9_sensitivity().copy()
    if robust_only:
        data = data.loc[data["robust_top_decile"]]
    columns = [
        "municipality",
        "accommodations",
        "balanced_score",
        "balanced_rank",
        "rank_spread",
        "level_changes_vs_balanced",
        "level_stable_all_scenarios",
        "top_decile_scenarios",
        "robust_top_decile",
    ]
    return records(data.loc[:, columns].sort_values(["balanced_rank", "municipality"]))


@app.get("/legacy/municipalities-v1")
def legacy_municipalities_v1() -> list[dict]:
    """Línea base histórica v1; no debe usarse como resultado principal."""
    columns = [
        "municipality",
        "tsmai_v1_score",
        "tsmai_v1_level",
        "coverage_800m_pct",
        "gap_over_1200m_pct",
        "route_success_pct",
        "transit_screening_pct",
    ]
    return records(load_legacy_index().loc[:, columns].sort_values("tsmai_v1_score", ascending=False))


@app.get("/cases/{od_id}")
def case(od_id: str) -> dict:
    data = load_cases().loc[lambda frame: frame["od_id"].eq(od_id.upper())]
    if data.empty:
        raise HTTPException(status_code=404, detail="Caso OD no encontrado")
    row = records(data)[0]
    return row


@app.get("/catalog/accommodations")
def catalog_accommodations(
    municipality: str | None = Query(default=None, max_length=120),
    group: str | None = Query(default=None, max_length=120),
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=200, ge=1, le=1500),
) -> list[dict]:
    """Lista alojamientos con geometría validada sin exponer datos personales."""
    return [place.as_dict() for place in catalog().list_accommodations(municipality, group, query)[:limit]]


@app.get("/catalog/destinations")
def catalog_destinations(
    category: str | None = Query(default=None, max_length=80),
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=200, ge=1, le=1500),
) -> list[dict]:
    """Lista destinos OSM nombrados y validados como candidatos turísticos."""
    return [place.as_dict() for place in catalog().list_destinations(category, query)[:limit]]


def resolve_reference(reference: CatalogReference) -> Place:
    if reference.source == "accommodation":
        if not reference.id:
            raise HTTPException(status_code=422, detail="Un alojamiento requiere su accommodation_id.")
        try:
            return catalog().accommodation(reference.id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if reference.source == "destination":
        if not reference.id:
            raise HTTPException(status_code=422, detail="Un destino requiere su poi_id.")
        try:
            return catalog().destination(reference.id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if reference.latitude is None or reference.longitude is None:
        raise HTTPException(status_code=422, detail="Un punto manual requiere latitude y longitude.")
    return Place(
        id="manual",
        name=reference.name or "Punto seleccionado",
        latitude=reference.latitude,
        longitude=reference.longitude,
        kind="coordinate",
    )


@app.post("/routes/compare")
def compare_routes(request: RouteComparisonRequest) -> dict:
    """Compara rutas reales de OTP y explica la función de decisión aplicada.

    La clasificación no equivale a una certificación de seguridad o
    accesibilidad universal: sólo pondera duración, emisiones estimadas,
    caminata y transbordos de la consulta actual.
    """
    origin = resolve_reference(request.origin)
    destination = resolve_reference(request.destination)
    alternatives = OtpClient(OTP_ENDPOINT).compare(origin, destination, request.routing_date, request.routing_time)
    ranked = rank_alternatives(alternatives, PROFILES[request.profile])
    return {
        "origin": origin.as_dict(),
        "destination": destination.as_dict(),
        "routing_date": request.routing_date.isoformat(),
        "routing_time": request.routing_time.strftime("%H:%M"),
        "profile": request.profile,
        "recommendation": ranked[0]["mode"] if ranked else None,
        "alternatives": ranked,
        "unavailable_alternatives": [item.as_dict() for item in alternatives if item.status != "ok"],
        "method": {
            "criteria": ["duration", "estimated_co2eq", "walk_distance", "transfers"],
            "emission_factors_kg_co2eq_per_km": EMISSION_FACTORS_KG_CO2EQ_PER_KM,
            "limitations": [
                "No incorpora tráfico en tiempo real, disponibilidad de bicicletas ni ocupación observada.",
                "No certifica seguridad vial, continuidad de infraestructura ni accesibilidad universal.",
                "La disponibilidad de transporte depende del GTFS cargado y de la fecha y hora solicitadas.",
            ],
        },
    }


@app.get("/routes/walk")
def walk_route(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float, date: str = "2026-09-03", time: str = "12:00") -> dict:
    """Consulta OTP y devuelve solamente la ruta a pie solicitada por el cliente."""
    query = '''query Walk($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
      plan(from: $from, to: $to, date: $date, time: $time, transportModes: [{mode: WALK}], numItineraries: 1) {
        itineraries { duration walkDistance legs { mode distance duration legGeometry { points } steps { streetName relativeDirection absoluteDirection distance } } }
        routingErrors { code description }
      }}'''
    variables = {"from": {"lat": origin_lat, "lon": origin_lon}, "to": {"lat": destination_lat, "lon": destination_lon}, "date": date, "time": time}
    try:
        response = requests.post(OTP_ENDPOINT, json={"query": query, "variables": variables}, timeout=45)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"OTP no disponible: {exc}") from exc
    payload = response.json()
    if payload.get("errors"):
        raise HTTPException(status_code=502, detail="OTP rechazó la consulta de ruta")
    return payload["data"]["plan"]
