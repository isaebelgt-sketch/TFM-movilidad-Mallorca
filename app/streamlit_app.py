"""Dashboard trazable del TFM de accesibilidad turística en Mallorca."""

from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import os
import sys

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(IMPORT_ROOT))

from src.mobility.catalog import Place
from src.mobility.routing import OtpClient, RouteAlternative
from src.mobility.scoring import PROFILES, rank_alternatives

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
from project_tools import build_case_html, build_case_pdf, calculate_emissions_scenarios


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRIC_CRS = "EPSG:25831"
OTP_ENDPOINT = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
CURRENT_DASHBOARD_LATEST_FILE = PROJECT_ROOT / "data" / "curated" / "latest_dashboard_current_layers.json"
CLUSTERS_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_accessibility_clusters.parquet"
PRIORITY_FILE = PROJECT_ROOT / "data" / "curated" / "od_multimodal_priority_index.parquet"
SENSITIVITY_FILE = PROJECT_ROOT / "data" / "curated" / "od_multimodal_priority_sensitivity.parquet"
EMISSIONS_FILE = PROJECT_ROOT / "data" / "curated" / "od_multimodal_emissions.parquet"
RECOMMENDATIONS_FILE = PROJECT_ROOT / "data" / "curated" / "multimodal_intervention_recommendations.parquet"
MASSIVE_SUMMARY_FILE = PROJECT_ROOT / "data" / "curated" / "od_multimodal_routes_massive_summary.parquet"
GTFS_QUALITY_FILE = PROJECT_ROOT / "docs" / "data_quality_gtfs.json"
FINAL_VALIDATION_FILE = PROJECT_ROOT / "docs" / "final_reproducibility_validation_report.json"
MASSIVE_VALIDATION_FILE = PROJECT_ROOT / "docs" / "async_massive_processing_validation_report.json"
TSMAI_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_tourism_sustainable_mobility_index.parquet"
TSMAI_V2_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_tourism_sustainable_mobility_index_v2.parquet"
ACTIVE_ACCOMMODATIONS_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_active_mobility_access.parquet"
ACTIVE_DESTINATIONS_FILE = PROJECT_ROOT / "data" / "curated" / "tourism_destinations_active_mobility_access.parquet"
CYCLEWAYS_FILE = PROJECT_ROOT / "data" / "curated" / "dashboard_current_cycling_evidence_osm.parquet"
ISOCHRONES_FILE = PROJECT_ROOT / "data" / "curated" / "isochrones" / "otp_walk_isochrones.parquet"
ISOCHRONES_REPORT_FILE = PROJECT_ROOT / "docs" / "otp_walk_isochrones_report.json"
SLOPE_FILE = PROJECT_ROOT / "data" / "curated" / "route_slope_profiles_ign_mdp05.parquet"
CURRENT_SAMPLE_SLOPE_LATEST_FILE = PROJECT_ROOT / "data" / "curated" / "latest_current_sample_slope_profiles.json"
ACTIVE_MOBILITY_REPORT_FILE = PROJECT_ROOT / "docs" / "active_mobility_osm_report.json"
UNIVERSAL_ACCESS_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_documented_accessibility_evidence.parquet"
UNIVERSAL_ACCESS_LATEST_FILE = PROJECT_ROOT / "data" / "curated" / "latest_universal_access_evidence.json"
UNIVERSAL_ACCESS_REPORT_FILE = PROJECT_ROOT / "docs" / "universal_access_evidence_report.json"
SUSTAINABLE_ROUTE_RECOMMENDATIONS_FILE = PROJECT_ROOT / "data" / "curated" / "od_sustainable_route_recommendations.parquet"
INTERVENTION_SCENARIOS_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_access_intervention_scenarios.parquet"
TSMAI_SENSITIVITY_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_tsmai_v2_sensitivity.parquet"
ROUTE_INFRASTRUCTURE_FILE = PROJECT_ROOT / "data" / "curated" / "route_osm_infrastructure_profiles.parquet"
AIR_QUALITY_STATIONS_FILE = PROJECT_ROOT / "data" / "unified" / "caib_air_quality_stations.parquet"
AIR_QUALITY_REPORT_FILE = PROJECT_ROOT / "docs" / "air_quality_context_report.json"
TOURIST_OFFER_SEASONALITY_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_tourist_offer_seasonality.parquet"
ROAD_SAFETY_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_road_safety_context_dgt_2024.parquet"
ROAD_SAFETY_REPORT_FILE = PROJECT_ROOT / "docs" / "road_safety_context_dgt_2024_report.json"
AEMET_WEATHER_LATEST_FILE = PROJECT_ROOT / "data" / "curated" / "latest_aemet_weather_context.json"
ACCOMMODATION_TSMAI_V3_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tourism_sustainable_mobility_index_v3.parquet"
MOBILITY_SENTIMENT_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_mobility_sentiment.parquet"
TSMAI_V4_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v4_current.parquet"
TSMAI_V5_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v5_network.parquet"
TSMAI_V6_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v6_multimodal_network.parquet"
TSMAI_V7_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v7_complete_multimodal.parquet"
TSMAI_V8_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v8_temporal_transit.parquet"
TSMAI_V9_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v9_seasonal_transit.parquet"
TSMAI_V9_SENSITIVITY_ACCOMMODATIONS_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_v9_sensitivity.parquet"
TSMAI_V9_SENSITIVITY_MUNICIPALITIES_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_tsmai_v9_sensitivity.parquet"
TSMAI_V9_SENSITIVITY_REPORT_FILE = PROJECT_ROOT / "data" / "curated" / "latest_tsmai_v9_sensitivity.json"
BICYCLE_VALIDATION_FILE = PROJECT_ROOT / "data" / "curated" / "otp_bicycle_route_validation.parquet"
TSMAI_EXTENDED_FILE = PROJECT_ROOT / "data" / "curated" / "accommodations_tsmai_extended.parquet"
TSMAI_EXTENDED_REPORT_FILE = PROJECT_ROOT / "docs" / "tsmai_extended_report.json"
DEMAND_ACCESSIBILITY_ANOMALIES_FILE = PROJECT_ROOT / "data" / "curated" / "municipality_demand_accessibility_anomalies.parquet"
DEMAND_ACCESSIBILITY_ANOMALIES_REPORT_FILE = PROJECT_ROOT / "docs" / "demand_accessibility_anomalies_report.json"

BAND_ORDER = ["alta_0_400m", "media_400_800m", "baja_800_1200m", "brecha_mas_1200m"]
BAND_LABELS = {
    "alta_0_400m": "Alta: 0–400 m",
    "media_400_800m": "Media: 400–800 m",
    "baja_800_1200m": "Baja: 800–1.200 m",
    "brecha_mas_1200m": "Brecha: más de 1.200 m",
}
BAND_COLORS = {
    "alta_0_400m": "#1a9850",
    "media_400_800m": "#91cf60",
    "baja_800_1200m": "#fdae61",
    "brecha_mas_1200m": "#d73027",
}
ROUTE_STATUS_LABELS = {
    "ok": "Ruta válida",
    "no_route": "Sin ruta",
    "service_unavailable": "Servicio caído",
    "no_transit_leg": "Sin red pública",
    "internal_error": "Error interno",
}
DESTINATION_LABELS = {
    "cultural": "Cultura y patrimonio",
    "nature": "Naturaleza",
    "coastal": "Litoral",
    "leisure": "Ocio al aire libre",
    "tourism": "Turismo",
}
DESTINATION_COLORS = {
    "cultural": "#b15928",
    "nature": "#1b9e77",
    "coastal": "#0284c7",
    "leisure": "#65a30d",
    "tourism": "#6a3d9a",
}
CLUSTER_LABELS = {
    "C1": "Alta intensidad turística y cobertura elevada",
    "C2": "Escala turística reducida y cobertura intermedia",
    "C3": "Brecha estructural de accesibilidad",
}
RECOMMENDATION_LABELS = {
    "audit_pedestrian_network": "Auditar conectividad peatonal",
    "first_last_mile_assessment": "Evaluar primera/última milla",
    "timetable_service_review": "Revisar calendario y frecuencia",
    "service_feasibility_review": "Evaluar viabilidad del servicio",
    "walking_quality_preservation": "Preservar calidad peatonal",
    "reduce_multimodal_walk_burden": "Reducir caminata multimodal",
    "promote_existing_low_emission_route": "Promover ruta de bajas emisiones",
    "monitor_and_validate": "Monitorizar y validar",
}
TSMAI_V4_ORDER = ["favorable", "intermedio", "prioridad de mejora"]
TSMAI_V4_LABELS = {
    "favorable": "Favorable",
    "intermedio": "Intermedio",
    "prioridad de mejora": "Prioridad de mejora",
}
TSMAI_V4_COLORS = {
    "favorable": "#1a9850",
    "intermedio": "#fdae61",
    "prioridad de mejora": "#d73027",
}


def cluster_label(code: str) -> str:
    """Etiqueta de negocio; el código K-Means se conserva por trazabilidad."""
    return CLUSTER_LABELS.get(str(code), f"Perfil {code}")


@st.cache_data(show_spinner=False)
def load_quality_context() -> dict:
    """Carga evidencias de calidad sin recalcular ni alterar los artefactos."""
    def read_json(path: Path) -> dict:
        if not path.exists():
            return {"status": "not_available", "file": path.name}
        return json.loads(path.read_text(encoding="utf-8"))

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gtfs": read_json(GTFS_QUALITY_FILE),
        "final": read_json(FINAL_VALIDATION_FILE),
        "massive": read_json(MASSIVE_VALIDATION_FILE),
    }


@st.cache_data(show_spinner=False)
def load_tsmai() -> pd.DataFrame:
    return pd.read_parquet(TSMAI_FILE)


@st.cache_data(show_spinner=False)
def load_bicycle_route_validation() -> pd.DataFrame:
    if not BICYCLE_VALIDATION_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(BICYCLE_VALIDATION_FILE)


@st.cache_data(show_spinner=False)
def load_active_mobility() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame, dict]:
    """Carga las extensiones OSM/OTP/IGN sin alterar la línea base."""
    accommodation_active = gpd.read_parquet(ACTIVE_ACCOMMODATIONS_FILE)
    destination_active = gpd.read_parquet(ACTIVE_DESTINATIONS_FILE)
    cycleways = gpd.read_parquet(CYCLEWAYS_FILE)
    isochrones = gpd.read_parquet(ISOCHRONES_FILE)
    slopes = pd.read_parquet(SLOPE_FILE)
    report = json.loads(ACTIVE_MOBILITY_REPORT_FILE.read_text(encoding="utf-8"))
    return accommodation_active, destination_active, cycleways, isochrones, slopes, report


@st.cache_data(show_spinner=False)
def load_current_sample_slope_profiles() -> tuple[pd.DataFrame, dict]:
    """Carga P10 sólo cuando la consulta real MDP05 se completó correctamente."""
    if not CURRENT_SAMPLE_SLOPE_LATEST_FILE.exists():
        return pd.DataFrame(), {}
    report = json.loads(CURRENT_SAMPLE_SLOPE_LATEST_FILE.read_text(encoding="utf-8"))
    profile_reference = report.get("profile_output")
    if report.get("status") != "passed" or not profile_reference:
        return pd.DataFrame(), report
    profile_path = PROJECT_ROOT / profile_reference
    if not profile_path.exists():
        return pd.DataFrame(), report
    profiles = pd.read_parquet(profile_path)
    required = {
        "od_id", "origin_tib_access_band", "destination_theme", "route_status",
        "samples_requested", "samples_valid", "mean_slope_degrees",
        "p95_slope_degrees", "max_slope_degrees", "slope_difficulty",
    }
    if missing := required.difference(profiles.columns):
        raise ValueError(f"El perfil actual de pendiente no contiene: {sorted(missing)}")
    return profiles, report


@st.cache_data(show_spinner=False)
def load_pending_challenge_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Extensiones sin sentimiento: índice v2, evidencia documental y escenarios."""
    tsmai_v2 = pd.read_parquet(TSMAI_V2_FILE)
    if UNIVERSAL_ACCESS_LATEST_FILE.exists():
        latest_universal = json.loads(UNIVERSAL_ACCESS_LATEST_FILE.read_text(encoding="utf-8"))
        universal_path = PROJECT_ROOT / latest_universal["accommodation_evidence_output"]
    else:
        universal_path = UNIVERSAL_ACCESS_FILE
    universal = pd.read_parquet(universal_path)
    recommendations = pd.read_parquet(SUSTAINABLE_ROUTE_RECOMMENDATIONS_FILE)
    scenarios = pd.read_parquet(INTERVENTION_SCENARIOS_FILE)
    report = json.loads(UNIVERSAL_ACCESS_REPORT_FILE.read_text(encoding="utf-8"))
    return tsmai_v2, universal, recommendations, scenarios, report


@st.cache_data(show_spinner=False)
def load_advanced_evaluation_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga sensibilidad, contexto OSM de rutas y oferta turística oficial."""
    return pd.read_parquet(TSMAI_SENSITIVITY_FILE), pd.read_parquet(ROUTE_INFRASTRUCTURE_FILE), pd.read_parquet(TOURIST_OFFER_SEASONALITY_FILE)


@st.cache_data(show_spinner=False)
def load_air_quality_context() -> tuple[gpd.GeoDataFrame, dict]:
    return gpd.read_parquet(AIR_QUALITY_STATIONS_FILE), json.loads(AIR_QUALITY_REPORT_FILE.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_road_safety_context() -> tuple[pd.DataFrame, dict]:
    """Carga un contexto provincial DGT que no participa en el routing."""
    return pd.read_parquet(ROAD_SAFETY_FILE), json.loads(ROAD_SAFETY_REPORT_FILE.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_tsmai_extended() -> tuple[pd.DataFrame, dict]:
    """Índice extendido OPCIONAL (TSMAI V9 + evidencia de accesibilidad universal).

    No es el TSMAI V9 oficial; ver docs/tsmai_extended_report.json.
    """
    return pd.read_parquet(TSMAI_EXTENDED_FILE), json.loads(TSMAI_EXTENDED_REPORT_FILE.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_demand_accessibility_anomalies() -> tuple[pd.DataFrame, dict]:
    """Anomalías municipales de demanda turística vs. accesibilidad (umbral z-score).

    Umbral estadístico simple, no un modelo entrenado; ver
    docs/demand_accessibility_anomalies_report.json.
    """
    return (
        pd.read_parquet(DEMAND_ACCESSIBILITY_ANOMALIES_FILE),
        json.loads(DEMAND_ACCESSIBILITY_ANOMALIES_REPORT_FILE.read_text(encoding="utf-8")),
    )


@st.cache_data(show_spinner=False)
def load_aemet_weather_context() -> tuple[gpd.GeoDataFrame, dict]:
    """Carga contexto observado AEMET ya filtrado a Mallorca; no crea proxies."""
    if not AEMET_WEATHER_LATEST_FILE.exists():
        return gpd.GeoDataFrame(), {}
    metadata = json.loads(AEMET_WEATHER_LATEST_FILE.read_text(encoding="utf-8"))
    if metadata.get("status") != "passed":
        return gpd.GeoDataFrame(), {}
    output = PROJECT_ROOT / metadata["output"]
    return gpd.read_parquet(output), metadata


@st.cache_data(show_spinner=False)
def load_new_decision_artifacts() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga sólo resultados realmente generados; no crea proxies en la interfaz."""
    index = pd.read_parquet(ACCOMMODATION_TSMAI_V3_FILE) if ACCOMMODATION_TSMAI_V3_FILE.exists() else pd.DataFrame()
    sentiment = pd.read_parquet(MOBILITY_SENTIMENT_FILE) if MOBILITY_SENTIMENT_FILE.exists() else pd.DataFrame()
    return index, sentiment


@st.cache_data(show_spinner=False)
def load_current_tsmai_v4() -> pd.DataFrame:
    """Índice individual reproducible construido sólo con los artefactos actuales."""
    return pd.read_parquet(TSMAI_V4_FILE) if TSMAI_V4_FILE.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_current_tsmai_v5() -> pd.DataFrame:
    """Índice principal con acceso WALK calculado por la red OTP."""
    return pd.read_parquet(TSMAI_V5_FILE) if TSMAI_V5_FILE.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_current_tsmai_v6() -> pd.DataFrame:
    """Índice principal con tiempos efectivos WALK y BICYCLE de OTP."""
    return pd.read_parquet(TSMAI_V6_FILE) if TSMAI_V6_FILE.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_current_tsmai_v7() -> pd.DataFrame:
    """Índice P0 completo con rutas WALK, BICYCLE y TRANSIT de OTP."""
    return pd.read_parquet(TSMAI_V7_FILE) if TSMAI_V7_FILE.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_current_tsmai_v8() -> pd.DataFrame:
    """Índice P1 con robustez TRANSIT en cuatro escenarios GTFS."""
    return pd.read_parquet(TSMAI_V8_FILE) if TSMAI_V8_FILE.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_current_tsmai_v9() -> pd.DataFrame:
    """Índice P2 con campañas TRANSIT de verano e invierno del GTFS real."""
    return pd.read_parquet(TSMAI_V9_FILE) if TSMAI_V9_FILE.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_current_tsmai_v9_sensitivity() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Resultados P6 de pesos alternativos sobre componentes reales de TSMAI."""
    if not all(path.exists() for path in [
        TSMAI_V9_SENSITIVITY_ACCOMMODATIONS_FILE,
        TSMAI_V9_SENSITIVITY_MUNICIPALITIES_FILE,
        TSMAI_V9_SENSITIVITY_REPORT_FILE,
    ]):
        return pd.DataFrame(), pd.DataFrame(), {}
    return (
        pd.read_parquet(TSMAI_V9_SENSITIVITY_ACCOMMODATIONS_FILE),
        pd.read_parquet(TSMAI_V9_SENSITIVITY_MUNICIPALITIES_FILE),
        json.loads(TSMAI_V9_SENSITIVITY_REPORT_FILE.read_text(encoding="utf-8")),
    )


def load_data() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga las capas P7 actuales; los casos OD se conservan como referencia histórica."""
    if not CURRENT_DASHBOARD_LATEST_FILE.exists():
        raise FileNotFoundError("Falta el manifiesto P7. Ejecuta build_current_dashboard_layers.py.")
    current_layers = json.loads(CURRENT_DASHBOARD_LATEST_FILE.read_text(encoding="utf-8"))
    if current_layers.get("status") != "passed":
        raise ValueError("El manifiesto P7 no declara una publicación correcta.")
    try:
        accommodations_path = PROJECT_ROOT / current_layers["outputs"]["accommodations"]
        stops_path = PROJECT_ROOT / current_layers["outputs"]["stops"]
        destinations_path = PROJECT_ROOT / current_layers["outputs"]["destinations"]
    except KeyError as exc:
        raise ValueError("El manifiesto P7 no declara las tres capas del mapa.") from exc
    accommodations = gpd.read_parquet(accommodations_path)
    stops = gpd.read_parquet(stops_path)
    destinations = gpd.read_parquet(destinations_path)
    clusters = pd.read_parquet(CLUSTERS_FILE)
    priorities = pd.read_parquet(PRIORITY_FILE)
    sensitivity = pd.read_parquet(SENSITIVITY_FILE)
    emissions = pd.read_parquet(EMISSIONS_FILE)
    recommendations = pd.read_parquet(RECOMMENDATIONS_FILE)
    
    # --- INTEGRA AI NARRATIVES ---
    import os
    ai_narratives_file = PROJECT_ROOT / "data" / "curated" / "od_ai_route_narratives.parquet"
    if ai_narratives_file.exists():
        ai_df = pd.read_parquet(ai_narratives_file)
        if "ai_narrative" in ai_df.columns and "od_id" in ai_df.columns:
            recommendations = recommendations.merge(ai_df[["od_id", "ai_narrative"]], on="od_id", how="left")
    # -----------------------------

    priorities = priorities.merge(sensitivity[["od_id", "top5_scenarios", "robust_priority"]], on="od_id", how="left", validate="one_to_one")
    
    # Agregar ai_narrative si existe
    cols_to_merge = ["od_id", "recommendation_code", "recommendation", "evidence", "recommendation_scope", "evidence_summary"]
    if "ai_narrative" in recommendations.columns:
        cols_to_merge.append("ai_narrative")
        
    priorities = priorities.merge(
        recommendations[cols_to_merge],
        on="od_id", how="left", validate="one_to_one",
    )
    if priorities["robust_priority"].isna().any():
        raise ValueError("Falló la unión de los casos OD históricos: revisa los artefactos curated.")
    location_type = stops["location_type"].fillna("0").astype("string").str.strip()
    return accommodations, stops.loc[location_type.isin(["0", ""])].copy(), destinations, clusters, priorities, emissions



# Para estos desenlaces, "evidence" sólo parafrasea "analysis_outcome" (mismo hecho, otras palabras);
# se omite para no repetir la misma frase dos veces seguidas en la ficha del caso.
OUTCOMES_WITH_REDUNDANT_EVIDENCE = {
    "no_scheduled_connection_at_time",
    "endpoint_without_stop_in_range",
    "walk_only_itineraries",
    "walking_preferable_by_otp",
    "direct_walk_network_disconnect",
}


def explain_case(row: pd.Series) -> str:
    action = RECOMMENDATION_LABELS.get(row["recommendation_code"], row["recommendation_code"])
    evidence_sentence = (
        "" if row.get("analysis_outcome_code") in OUTCOMES_WITH_REDUNDANT_EVIDENCE
        else f" {row['evidence']}"
    )
    return (
        f"**Diagnóstico del caso {row['od_id']}.** La prioridad es **{row['priority_level']}** "
        f"({row['priority_index_score']:.3f}). El desenlace OTP fue: **{row['analysis_outcome']}**."
        f"{evidence_sentence} La acción de revisión sugerida es **{action}**. "
        "Es una recomendación de diagnóstico: debe comprobarse en campo antes de intervenir."
    )


def format_walk_step(step: dict, number: int) -> str:
    """Traduce los enumerados de OTP sin modificar la ruta ni sus distancias."""
    raw_direction = (step.get("relativeDirection") or step.get("absoluteDirection") or "CONTINUE").upper()
    direction = {
        "DEPART": "Sal",
        "CONTINUE": "Continúa",
        "LEFT": "Gira a la izquierda",
        "RIGHT": "Gira a la derecha",
        "SLIGHTLY_LEFT": "Gira ligeramente a la izquierda",
        "SLIGHTLY_RIGHT": "Gira ligeramente a la derecha",
        "HARD_LEFT": "Gira pronunciadamente a la izquierda",
        "HARD_RIGHT": "Gira pronunciadamente a la derecha",
        "CIRCLE_CLOCKWISE": "Toma la rotonda en sentido horario",
        "CIRCLE_COUNTERCLOCKWISE": "Toma la rotonda en sentido antihorario",
        "ELEVATOR": "Usa el ascensor",
        "UTURN_LEFT": "Haz un cambio de sentido a la izquierda",
        "UTURN_RIGHT": "Haz un cambio de sentido a la derecha",
    }.get(raw_direction, "Continúa")
    street = (step.get("streetName") or "").strip()
    if not street or street.lower() in {"road", "path", "footway", "cycleway"}:
        street = "la vía indicada"
    return f"{number}. {direction} por **{street}** durante {step['distance']:.0f} m."


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decodifica la polilínea de Google que OTP devuelve para cada tramo."""
    index = latitude = longitude = 0
    coordinates: list[tuple[float, float]] = []
    while index < len(encoded):
        values = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += values[0]
        longitude += values[1]
        coordinates.append((latitude / 1e5, longitude / 1e5))
    return coordinates


@st.cache_data(ttl="5m", show_spinner="Consultando instrucciones peatonales en OTP…")
def get_walk_steps(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float, date: str, time: str) -> dict:
    query = '''
    query Walk($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
      plan(from: $from, to: $to, date: $date, time: $time,
           transportModes: [{mode: WALK}], numItineraries: 1) {
        itineraries { duration walkDistance legs { mode distance duration legGeometry { points }
          steps { streetName absoluteDirection relativeDirection distance } } }
        routingErrors { code description }
      }
    }'''
    variables = {
        "from": {"lat": origin_lat, "lon": origin_lon},
        "to": {"lat": destination_lat, "lon": destination_lon},
        "date": date,
        "time": time,
    }
    try:
        response = requests.post(OTP_ENDPOINT, json={"query": query, "variables": variables}, timeout=45)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"status": "offline", "message": f"OTP no está disponible en {OTP_ENDPOINT}: {exc}"}
    if payload.get("errors"):
        return {"status": "graphql_error", "message": "OTP no expone pasos peatonales en esta configuración."}
    plan = payload["data"]["plan"]
    if plan["routingErrors"] or not plan["itineraries"]:
        return {"status": "no_route", "message": "OTP no devolvió una ruta peatonal para esta consulta."}
    itinerary = plan["itineraries"][0]
    steps = [step for leg in itinerary["legs"] for step in (leg.get("steps") or []) if step.get("distance", 0) > 0]
    return {
        "status": "ok",
        "distance_m": itinerary["walkDistance"],
        "duration_min": itinerary["duration"] / 60,
        "steps": steps,
        "itinerary": itinerary,
    }


@st.cache_data(ttl="5m", show_spinner="Recuperando geometría real de la ruta en OTP…")
def get_multimodal_geometry(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float, date: str, time: str) -> dict:
    """Solicita a OTP sus polilíneas reales; no se dibujan líneas rectas inventadas."""
    query = '''
    query GeometryRoute($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!, $modes: [TransportMode]!) {
      plan(from: $from, to: $to, date: $date, time: $time, transportModes: $modes, numItineraries: 5) {
        itineraries { duration walkDistance legs { mode distance duration legGeometry { points } route { shortName longName } } }
        routingErrors { code description inputField }
      }
    }'''
    variables = {
        "from": {"lat": origin_lat, "lon": origin_lon},
        "to": {"lat": destination_lat, "lon": destination_lon},
        "date": date,
        "time": time,
        "modes": [{"mode": "WALK"}, {"mode": "TRANSIT"}],
    }
    try:
        response = requests.post(OTP_ENDPOINT, json={"query": query, "variables": variables}, timeout=90)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"status": "offline", "message": f"OTP no está disponible en {OTP_ENDPOINT}: {exc}"}
    if payload.get("errors"):
        return {"status": "graphql_error", "message": "OTP no pudo devolver la geometría de esta consulta."}
    plan = payload["data"]["plan"]
    if plan["routingErrors"] or not plan["itineraries"]:
        return {"status": "no_route", "message": "OTP no devolvió una ruta multimodal para esta fecha y hora."}
    options = [item for item in plan["itineraries"] if any(leg["mode"] != "WALK" for leg in item["legs"])]
    itinerary = min(options or plan["itineraries"], key=lambda item: item["duration"])
    return {"status": "ok", "itinerary": itinerary}


@st.cache_data(ttl="5m", show_spinner="Calculando ruta ciclista real en OTP…")
def get_bicycle_geometry(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float, date: str, time: str) -> dict:
    """Consulta una alternativa BICYCLE real; no transforma una ruta a pie en bici."""
    query = '''
    query BicycleRoute($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
      plan(from: $from, to: $to, date: $date, time: $time,
           transportModes: [{mode: BICYCLE}], numItineraries: 1) {
        itineraries { duration walkDistance legs { mode distance duration legGeometry { points } } }
        routingErrors { code description inputField }
      }
    }'''
    variables = {
        "from": {"lat": origin_lat, "lon": origin_lon},
        "to": {"lat": destination_lat, "lon": destination_lon},
        "date": date,
        "time": time,
    }
    try:
        response = requests.post(OTP_ENDPOINT, json={"query": query, "variables": variables}, timeout=90)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"status": "offline", "message": f"OTP no está disponible en {OTP_ENDPOINT}: {exc}"}
    if payload.get("errors"):
        return {"status": "graphql_error", "message": "Esta compilación de OTP no ha podido calcular el modo bicicleta."}
    plan = payload["data"]["plan"]
    if plan["routingErrors"] or not plan["itineraries"]:
        return {"status": "no_route", "message": "OTP no devolvió una ruta ciclista para esta fecha y hora."}
    return {"status": "ok", "itinerary": plan["itineraries"][0]}


@st.cache_data(ttl="5m", show_spinner=False)
def get_dynamic_comparison(
    origin_id: str, origin_name: str, origin_lat: float, origin_lon: float,
    destination_id: str, destination_name: str, destination_lat: float, destination_lon: float,
    routing_date: str, routing_time: str,
) -> tuple[RouteAlternative, ...]:
    """Consulta WALK, BICYCLE, TRANSIT y CAR en paralelo para el planificador."""
    origin = Place(origin_id, origin_name, origin_lat, origin_lon, "accommodation")
    destination = Place(destination_id, destination_name, destination_lat, destination_lon, "destination")
    requested_date = pd.Timestamp(routing_date).date()
    requested_time = pd.Timestamp(f"1970-01-01 {routing_time}").time()
    # Las cuatro consultas se ejecutan en paralelo. Un límite acotado evita que la
    # interfaz quede esperando indefinidamente cuando el servicio OTP no responde.
    return tuple(OtpClient(OTP_ENDPOINT, timeout_seconds=25).compare(origin, destination, requested_date, requested_time))


def itinerary_from_alternative(alternative: RouteAlternative) -> dict:
    """Adapta la respuesta tipada para reutilizar el mapa de geometrías OTP."""
    return {
        "duration": (alternative.duration_min or 0) * 60,
        "walkDistance": alternative.walk_distance_m or 0,
        "legs": [
            {
                "mode": leg.mode,
                "distance": leg.distance_m,
                "duration": leg.duration_min * 60,
                "legGeometry": {"points": leg.geometry},
                "route": {"shortName": leg.line},
            }
            for leg in alternative.legs
        ],
    }


def build_territorial_map(accommodations: gpd.GeoDataFrame, stops: gpd.GeoDataFrame, destinations: gpd.GeoDataFrame, priority_cases: pd.DataFrame, show_stops: bool, show_destinations: bool, show_priority_cases: bool, show_gap_heatmap: bool, cycleways: gpd.GeoDataFrame | None = None, isochrones: gpd.GeoDataFrame | None = None, air_quality_stations: gpd.GeoDataFrame | None = None, aemet_weather_stations: gpd.GeoDataFrame | None = None, show_cycleways: bool = False, show_isochrones: bool = False, show_air_quality: bool = False, show_aemet_weather: bool = False, show_tsmai_v9: bool = False, show_documented_accessibility: bool = False) -> folium.Map:
    access_map = folium.Map(location=[39.64, 3.00], zoom_start=9, tiles="OpenStreetMap", control_scale=True)
    if show_tsmai_v9 and "tsmai_v9_level" in accommodations.columns:
        accommodation_groups = [
            (level, TSMAI_V4_LABELS[level], TSMAI_V4_COLORS[level], accommodations.loc[accommodations["tsmai_v9_level"].astype("string") == level])
            for level in TSMAI_V4_ORDER
        ]
    else:
        accommodation_groups = [
            (band, BAND_LABELS[band], BAND_COLORS[band], accommodations.loc[accommodations["walk_access_band_euclidean"].astype("string") == band])
            for band in BAND_ORDER
        ]
    for _, label, color, subset in accommodation_groups:
        group = folium.FeatureGroup(name=f"{label} ({len(subset):,})", show=True)
        for _, row in subset.iterrows():
            tsmai_detail = ""
            if pd.notna(row.get("tsmai_v9_score")):
                tsmai_detail = (
                    f"<br>TSMAI estacional: {row['tsmai_v9_score']:.3f} "
                    f"({TSMAI_V4_LABELS.get(str(row.get('tsmai_v9_level')), row.get('tsmai_v9_level'))})"
                )
            documented_accessibility_detail = ""
            if show_documented_accessibility and pd.notna(row.get("documented_accessibility_evidence_level")):
                osm_evidence = "sí" if bool(row.get("osm_evidence_within_400m", False)) else "no"
                gtfs_evidence = "sí" if bool(row.get("gtfs_wheelchair_stop_within_800m", False)) else "no"
                documented_accessibility_detail = (
                    f"<br>Evidencia OSM positiva a =400 m: {osm_evidence}"
                    f"<br>Parada GTFS con wheelchair_boarding=1 a =800 m: {gtfs_evidence}"
                    "<br><i>Es evidencia cartográfica cercana; no es certificación de ruta ni del alojamiento.</i>"
                )
            popup = (
                f"<b>{row['commercial_name']}</b><br>Municipio: {row['municipality_raw']}<br>"
                f"Parada más próxima: {row['stop_name']}<br>Distancia euclídea: {row['distance_to_nearest_stop_euclidean_m']:.0f} m"
                f"{tsmai_detail}{documented_accessibility_detail}"
            )
            folium.CircleMarker(location=[row.geometry.y, row.geometry.x], radius=3, color=color, weight=1, fill=True, fill_color=color, fill_opacity=0.8, popup=popup, tooltip=row["commercial_name"]).add_to(group)
        group.add_to(access_map)
    if show_documented_accessibility and {
        "osm_evidence_within_400m", "gtfs_wheelchair_stop_within_800m"
    }.issubset(accommodations.columns):
        documented_mask = (
            accommodations["osm_evidence_within_400m"].fillna(False).astype(bool)
            | accommodations["gtfs_wheelchair_stop_within_800m"].fillna(False).astype(bool)
        )
        documented = accommodations.loc[documented_mask]
        group = folium.FeatureGroup(
            name=f"Evidencia documentada cercana ({len(documented):,})", show=True
        )
        for _, row in documented.iterrows():
            details = [
                f"<b>{row['commercial_name']}</b>",
                "Marcador de evidencia documentada cercana",
            ]
            if bool(row.get("osm_evidence_within_400m", False)):
                distance = row.get("distance_to_osm_accessibility_evidence_m")
                distance_text = f" ({distance:.0f} m)" if pd.notna(distance) else ""
                details.append(f"Etiqueta OSM positiva a =400 m{distance_text}")
            if bool(row.get("gtfs_wheelchair_stop_within_800m", False)):
                distance = row.get("distance_to_gtfs_wheelchair_stop_m")
                distance_text = f" ({distance:.0f} m)" if pd.notna(distance) else ""
                details.append(f"Parada GTFS wheelchair_boarding=1 a =800 m{distance_text}")
            details.append("No acredita accesibilidad universal del alojamiento ni continuidad de la ruta.")
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x], radius=6, color="#6d28d9", weight=2,
                fill=False, popup="<br>".join(details),
            ).add_to(group)
        group.add_to(access_map)
    if show_stops:
        group = folium.FeatureGroup(name=f"Paradas GTFS ({len(stops):,})", show=True)
        for _, row in stops.iterrows():
            folium.CircleMarker(location=[row.geometry.y, row.geometry.x], radius=2, color="#2166ac", weight=1, fill=True, fill_color="#2166ac", fill_opacity=0.8, popup=f"{row['stop_name']} ({row['stop_id']})").add_to(group)
        group.add_to(access_map)
    if show_destinations:
        for category, label in DESTINATION_LABELS.items():
            subset = destinations.loc[destinations["destination_theme"].astype("string") == category]
            group = folium.FeatureGroup(name=f"{label} ({len(subset):,})", show=True)
            for _, row in subset.iterrows():
                popup = (
                    f"<b>{row['name']}</b><br>Tema: {label}<br>Etiqueta OSM: {row['destination_category']}"
                    "<br>POI representativo: no garantiza entrada física, horario ni accesibilidad universal."
                )
                folium.CircleMarker(location=[row.geometry.y, row.geometry.x], radius=3, color=DESTINATION_COLORS[category], weight=1, fill=True, fill_color=DESTINATION_COLORS[category], fill_opacity=0.8, popup=popup).add_to(group)
            group.add_to(access_map)
    if show_priority_cases:
        group = folium.FeatureGroup(name=f"Casos OD históricos de referencia ({len(priority_cases):,})", show=True)
        for _, row in priority_cases.iterrows():
            action = RECOMMENDATION_LABELS.get(row["recommendation_code"], row["recommendation_code"])
            details = f"<b>Prioridad de revisión: {row['priority_level']}</b><br>{row['origin_name']} → {row['destination_name']}<br>Acción: {action}"
            if "ai_narrative" in row and pd.notna(row["ai_narrative"]):
                details += f"<hr><b>Narrativa de la ruta (reglas heurísticas):</b><br><i>{row['ai_narrative']}</i>"
            folium.CircleMarker(location=[row["origin_lat"], row["origin_lon"]], radius=7, color="#7f0000", weight=2, fill=True, fill_color="#d73027", fill_opacity=0.9, popup=details).add_to(group)
            folium.CircleMarker(location=[row["destination_lat"], row["destination_lon"]], radius=6, color="#7f0000", weight=2, fill=True, fill_color="#ff8c00", fill_opacity=0.9, popup=details).add_to(group)
        group.add_to(access_map)
    if show_cycleways and cycleways is not None and not cycleways.empty:
        group = folium.FeatureGroup(name=f"Infraestructura ciclista OSM ({len(cycleways):,})", show=False)
        for geometry in cycleways.geometry:
            if geometry is None or geometry.is_empty:
                continue
            folium.GeoJson(geometry.__geo_interface__, style_function=lambda _: {"color": "#06b6d4", "weight": 2, "opacity": 0.75}, tooltip="Infraestructura ciclista etiquetada en OSM").add_to(group)
        group.add_to(access_map)
    if show_isochrones and isochrones is not None and not isochrones.empty:
        colors = {5: "#22c55e", 10: "#84cc16", 15: "#f59e0b", 30: "#ef4444"}
        for threshold, subset in isochrones.groupby("threshold_min"):
            group = folium.FeatureGroup(name=f"Isócrona a pie OTP ={threshold} min", show=False)
            for _, row in subset.iterrows():
                tooltip = f"{row['origin_name']} · ={threshold} min a pie (malla OTP de {row['grid_spacing_m']} m)"
                folium.GeoJson(row.geometry.__geo_interface__, style_function=lambda _, color=colors.get(int(threshold), '#64748b'): {"color": color, "weight": 2, "fillColor": color, "fillOpacity": 0.12}, tooltip=tooltip).add_to(group)
            group.add_to(access_map)
    if show_air_quality and air_quality_stations is not None and not air_quality_stations.empty:
        group = folium.FeatureGroup(name=f"Estaciones calidad del aire CAIB ({len(air_quality_stations):,})", show=True)
        label_columns = [column for column in ["name", "nom", "nombre", "station_name", "id"] if column in air_quality_stations.columns]
        for _, row in air_quality_stations.iterrows():
            label = next((str(row[column]) for column in label_columns if pd.notna(row[column])), "Estación CAIB")
            folium.CircleMarker(location=[row.geometry.y, row.geometry.x], radius=6, color="#7c3aed", weight=2, fill=True, fill_color="#a78bfa", fill_opacity=0.9, popup=f"<b>{label}</b><br>Medición puntual CAIB; no representa exposición de la ruta.").add_to(group)
        group.add_to(access_map)
    if show_aemet_weather and aemet_weather_stations is not None and not aemet_weather_stations.empty:
        group = folium.FeatureGroup(name=f"Estaciones AEMET históricas ({len(aemet_weather_stations):,})", show=True)
        for _, row in aemet_weather_stations.iterrows():
            station_name = row.get("nombre") or row.get("nombre_station") or row.get("indicativo")
            details = [
                f"<b>{station_name}</b>",
                f"Fecha observada: {row.get('observation_date', '—')}",
            ]
            for column, label, unit in [
                ("tmed_c", "Temperatura media", " °C"),
                ("prec_mm", "Precipitación", " mm"),
                ("wind_mean_ms", "Viento medio", " m/s"),
            ]:
                value = row.get(column)
                if pd.notna(value):
                    details.append(f"{label}: {value:.1f}{unit}")
            details.append("Contexto de estación histórica; no se aplica a rutas ni TSMAI.")
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x], radius=5, color="#0369a1", weight=2,
                fill=True, fill_color="#38bdf8", fill_opacity=0.9, popup="<br>".join(details),
            ).add_to(group)
        group.add_to(access_map)
    if show_gap_heatmap:
        gaps = accommodations.loc[accommodations["distance_to_nearest_stop_euclidean_m"].gt(800)].copy()
        heat_points = [[row.geometry.y, row.geometry.x, min((row.distance_to_nearest_stop_euclidean_m - 800) / 3000, 1.0)] for row in gaps.itertuples()]
        if heat_points:
            HeatMap(heat_points, name="Intensidad de brecha (>800 m)", min_opacity=0.25, radius=20, blur=16).add_to(access_map)
    folium.LayerControl(collapsed=False).add_to(access_map)
    return access_map


def build_route_map(case: pd.Series, itinerary: dict) -> folium.Map:
    """Mapa de una alternativa OTP; verde para caminar y azul para transporte público."""
    route_map = folium.Map(location=[(case.origin_lat + case.destination_lat) / 2, (case.origin_lon + case.destination_lon) / 2], zoom_start=12, tiles="OpenStreetMap", control_scale=True)
    all_points = [(case.origin_lat, case.origin_lon), (case.destination_lat, case.destination_lon)]
    for leg in itinerary["legs"]:
        encoded = (leg.get("legGeometry") or {}).get("points")
        if not encoded:
            continue
        points = decode_polyline(encoded)
        all_points.extend(points)
        mode = leg["mode"]
        is_walk = mode == "WALK"
        is_bicycle = mode == "BICYCLE"
        route = leg.get("route") or {}
        line_name = route.get("shortName") or route.get("longName") or "sin línea"
        label = "Tramo a pie" if is_walk else "Ruta ciclista" if is_bicycle else f"Transporte público · {line_name}"
        color = "#22c55e" if is_walk else "#f59e0b" if is_bicycle else "#38bdf8"
        folium.PolyLine(points, color=color, weight=6, opacity=0.9, dash_array="7, 8" if is_walk else None, tooltip=f"{label}: {leg['distance']:.0f} m").add_to(route_map)
    folium.Marker([case.origin_lat, case.origin_lon], tooltip=f"Origen · {case.origin_name}", icon=folium.Icon(color="green", icon="play")).add_to(route_map)
    folium.Marker([case.destination_lat, case.destination_lon], tooltip=f"Destino · {case.destination_name}", icon=folium.Icon(color="red", icon="flag")).add_to(route_map)
    route_map.fit_bounds(all_points)
    return route_map


def _zoom_for_distance(distance_m: float) -> int:
    """Nivel de zoom fijo aproximado para que ambos puntos quepan con margen.

    Se evita `fit_bounds`: al renderizarse en una pestaña que no está activa al
    cargar la página, el contenedor del mapa mide 0px y Leaflet calcula un
    zoom absurdo (vista de todo el mundo) que luego queda fijado.
    """
    thresholds = [(200, 17), (500, 16), (1000, 15), (2000, 14), (5000, 13), (10000, 12)]
    for limit, zoom in thresholds:
        if distance_m < limit:
            return zoom
    return 11


def build_intervention_map(accommodation_lat: float, accommodation_lon: float, accommodation_name: str, stop_lat: float | None, stop_lon: float | None, stop_name: str, distance_m: float) -> folium.Map:
    """Mapa mínimo de un alojamiento y su parada más próxima; sólo distancia euclídea, no una ruta real."""
    center_lat, center_lon = accommodation_lat, accommodation_lon
    zoom_start = 16
    if stop_lat is not None and stop_lon is not None:
        center_lat = (accommodation_lat + stop_lat) / 2
        center_lon = (accommodation_lon + stop_lon) / 2
        zoom_start = _zoom_for_distance(distance_m)
    intervention_map = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles="OpenStreetMap", control_scale=True, prefer_canvas=True)
    folium.Marker([accommodation_lat, accommodation_lon], tooltip=f"Alojamiento · {accommodation_name}", icon=folium.Icon(color="red", icon="home")).add_to(intervention_map)
    if stop_lat is not None and stop_lon is not None:
        folium.Marker([stop_lat, stop_lon], tooltip=f"Parada más próxima · {stop_name}", icon=folium.Icon(color="blue", icon="bus", prefix="fa")).add_to(intervention_map)
        folium.PolyLine(
            [[accommodation_lat, accommodation_lon], [stop_lat, stop_lon]],
            color="#94a3b8", weight=3, dash_array="6, 8",
            tooltip=f"Distancia en línea recta: {distance_m:.0f} m",
        ).add_to(intervention_map)
    return intervention_map


st.set_page_config(page_title="Accesibilidad turistica - Mallorca", page_icon=":material/directions_walk:", layout="wide")
st.markdown("""
<style>
/* Style tabs to look like pill buttons (Redis Tour style) */
div[data-testid="stTabs"] > div > div > div {
    gap: 10px;
    justify-content: center;
}
button[data-baseweb="tab"], button[data-testid="stTab"] {
    border: 1px solid #ddd !important;
    border-radius: 20px !important;
    padding: 10px 20px !important;
    background-color: white !important;
    color: #1b115c !important;
}
button[data-baseweb="tab"][aria-selected="true"], button[data-testid="stTab"][aria-selected="true"] {
    background-color: #f4fafd !important;
    border-color: #d40e14 !important;
    border-width: 2px !important;
    color: #d40e14 !important;
    font-weight: bold !important;
}
/* Style containers to look like the cards in the screenshot (blue left border) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-left: 5px solid #1b115c !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Movilidad turística sostenible en Mallorca")
st.info(
    "**TSMAI** (Índice de Movilidad Sostenible y Accesibilidad Turística): una puntuación de 0 a 1 "
    "que resume qué tan bien conectado está cada alojamiento con transporte público, bicicleta y a pie; "
    "no es una certificación. Resultado vigente: **TSMAI V9** por alojamiento."
)
try:
    accommodations, stops, destinations, clusters, priorities, emissions = load_data()
except (FileNotFoundError, ValueError) as exc:
    st.error(f"No se han podido cargar las capas analíticas: {exc}")
    st.stop()


quality_context = load_quality_context()
massive_summary = pd.read_parquet(MASSIVE_SUMMARY_FILE) if MASSIVE_SUMMARY_FILE.exists() else pd.DataFrame()
tsmai = load_tsmai() if TSMAI_FILE.exists() else pd.DataFrame()
bicycle_route_validation = load_bicycle_route_validation()
try:
    active_accommodations, active_destinations, cycleways, isochrones, slope_profiles, active_mobility_report = load_active_mobility()
except (FileNotFoundError, ValueError, OSError) as exc:
    active_accommodations, active_destinations = gpd.GeoDataFrame(), gpd.GeoDataFrame()
    cycleways, isochrones, slope_profiles, active_mobility_report = gpd.GeoDataFrame(), gpd.GeoDataFrame(), pd.DataFrame(), {}
    st.info(f"Extensiones de movilidad activa aún no disponibles: {exc}")
try:
    tsmai_v2, universal_access, sustainable_mode_recommendations, intervention_scenarios, universal_access_report = load_pending_challenge_artifacts()
except (FileNotFoundError, ValueError, OSError) as exc:
    tsmai_v2, universal_access = pd.DataFrame(), pd.DataFrame()
    sustainable_mode_recommendations, intervention_scenarios, universal_access_report = pd.DataFrame(), pd.DataFrame(), {}
    st.info(f"Extensiones analíticas adicionales aún no disponibles: {exc}")
try:
    tsmai_sensitivity, route_infrastructure_profiles, tourist_offer_seasonality = load_advanced_evaluation_artifacts()
except (FileNotFoundError, ValueError, OSError) as exc:
    tsmai_sensitivity, route_infrastructure_profiles, tourist_offer_seasonality = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    st.info(f"Evaluación avanzada aún no disponible: {exc}")
try:
    air_quality_stations, air_quality_report = load_air_quality_context()
except (FileNotFoundError, ValueError, OSError) as exc:
    air_quality_stations, air_quality_report = gpd.GeoDataFrame(), {}
    st.info(f"Contexto de calidad del aire aún no disponible: {exc}")
try:
    road_safety_context, road_safety_report = load_road_safety_context()
except (FileNotFoundError, ValueError, OSError) as exc:
    road_safety_context, road_safety_report = pd.DataFrame(), {}
    st.info(f"Contexto de siniestralidad DGT aún no disponible: {exc}")
try:
    tsmai_extended, tsmai_extended_report = load_tsmai_extended()
except (FileNotFoundError, ValueError, OSError) as exc:
    tsmai_extended, tsmai_extended_report = pd.DataFrame(), {}
    st.info(f"Índice TSMAI extendido (opcional) aún no disponible: {exc}")
try:
    demand_accessibility_anomalies, demand_accessibility_anomalies_report = load_demand_accessibility_anomalies()
except (FileNotFoundError, ValueError, OSError) as exc:
    demand_accessibility_anomalies, demand_accessibility_anomalies_report = pd.DataFrame(), {}
    st.info(f"Detección de anomalías demanda-accesibilidad aún no disponible: {exc}")
try:
    aemet_weather_stations, aemet_weather_report = load_aemet_weather_context()
except (FileNotFoundError, ValueError, OSError, KeyError) as exc:
    aemet_weather_stations, aemet_weather_report = gpd.GeoDataFrame(), {}
    st.info(f"Contexto meteorológico AEMET aún no disponible: {exc}")
accommodation_tsmai_v3, mobility_sentiment = load_new_decision_artifacts()
accommodation_tsmai_v4 = load_current_tsmai_v4()
accommodation_tsmai_v5 = load_current_tsmai_v5()
accommodation_tsmai_v6 = load_current_tsmai_v6()
accommodation_tsmai_v7 = load_current_tsmai_v7()
accommodation_tsmai_v8 = load_current_tsmai_v8()
accommodation_tsmai_v9 = load_current_tsmai_v9()
accommodation_tsmai_v9_sensitivity, municipality_tsmai_v9_sensitivity, tsmai_v9_sensitivity_report = load_current_tsmai_v9_sensitivity()
with st.expander("Alcance de los resultados mostrados", expanded=False):
    st.caption("**¿Qué es TSMAI?** Siglas de *Índice de Movilidad Sostenible y Accesibilidad Turística* (Tourism Sustainable Mobility & Accessibility Index). Puntuación de 0 a 1 por alojamiento: cuanto más alta, mejor conectado está con transporte público, bicicleta y a pie según los datos analizados.")
    st.caption("**¿Qué es OTP?** El motor de rutas reales que usa este proyecto (OpenTripPlanner). Calcula caminos a pie, en bicicleta y en transporte público sobre calles, carriles y horarios reales, igual que un buscador de rutas.")
    scope_cols = st.columns(3)
    with scope_cols[0]:
        st.markdown("**Resultado vigente**\n\nTSMAI V9 por alojamiento, con los mapas y datos actuales. Es evidencia de accesibilidad sostenible, no una certificación ni un promedio anual.")
    with scope_cols[1]:
        st.markdown("**Contexto y muestras**\n\nPendiente, emisiones, calidad del aire, meteorología, siniestralidad y oferta turística no alimentan el índice.")
    with scope_cols[2]:
        st.markdown("**Trazabilidad histórica**\n\nTSMAI V1–V8, perfiles municipales y casos OD sirven para explicar la evolución, no como resultado final.")
    st.markdown("---")
    mot_col, obj_col = st.columns(2)
    with mot_col:
        st.markdown(
            "**🎯 Motivación del proyecto**\n\n"
            "Mallorca afronta el reto de gestionar el crecimiento turístico garantizando la sostenibilidad y calidad de vida, sin mermar la experiencia del visitante.\n"
            "- Presión sobre infraestructuras y recursos en picos estacionales.\n"
            "- Impacto ambiental y dependencia del vehículo privado.\n"
            "- Necesidad de redistribuir flujos hacia zonas con alto potencial infrautilizado."
        )
    with obj_col:
        st.markdown(
            "**🚀 Objetivo del sistema**\n\n"
            "Proveer una plataforma de análisis y apoyo a la decisión para fomentar un turismo sostenible, informado y eficiente.\n"
            "- Identificación de brechas de accesibilidad en transporte público.\n"
            "- Auditoría masiva de conectividad ciclista y peatonal.\n"
            "- Soporte a políticas públicas orientadas a la reducción de la huella de carbono."
        )
    technical_mode = st.checkbox(
        "Mostrar análisis técnico e histórico",
        value=False,
        help="Activa las versiones anteriores del índice y las muestras metodológicas. La vista inicial mantiene sólo el resultado vigente.",
    )
try:
    current_sample_slope_profiles, current_sample_slope_report = load_current_sample_slope_profiles()
except (OSError, ValueError, json.JSONDecodeError) as exc:
    current_sample_slope_profiles, current_sample_slope_report = pd.DataFrame(), {"status": "invalid", "error": str(exc)}

# La vista de decisión sólo mezcla el resultado vigente (V9) con las capas P7.
# Los artefactos siguientes siguen disponibles cuando se solicita la trazabilidad.
if not technical_mode:
    accommodation_tsmai_v3 = accommodation_tsmai_v4 = accommodation_tsmai_v5 = pd.DataFrame()
    accommodation_tsmai_v6 = accommodation_tsmai_v7 = accommodation_tsmai_v8 = pd.DataFrame()
    active_accommodations = active_destinations = gpd.GeoDataFrame()
    cycleways = isochrones = air_quality_stations = aemet_weather_stations = gpd.GeoDataFrame()
    universal_access = road_safety_context = mobility_sentiment = pd.DataFrame()
    tsmai = tsmai_v2 = tsmai_sensitivity = route_infrastructure_profiles = pd.DataFrame()
    sustainable_mode_recommendations = intervention_scenarios = tourist_offer_seasonality = pd.DataFrame()
    slope_profiles = current_sample_slope_profiles = massive_summary = pd.DataFrame()
    tsmai_extended = demand_accessibility_anomalies = pd.DataFrame()

decision_tab, intervention_tab, territorial_tab, clustering_tab, chat_tab, explorer_tab, planner_tab = st.tabs([
    "✅ Resumen de decisión", "📋 Ficha de intervención",
    "🗺️ Análisis territorial", "🎯 Zonas de interés",
    "💬 Consulta guiada", "🔎 Validación técnica", "🧭 Planificador",
])

def format_case_id(od_id):
    if not isinstance(od_id, str): return od_id
    b_map = {"alta_0_400m": "Alta", "media_400_800m": "Media", "brecha_mas_800m": "Brecha"}
    t_map = {"nature": "Naturaleza", "leisure": "Ocio", "coastal": "Litoral", "cultural": "Cultura"}
    for b_k, b_v in b_map.items():
        if od_id.startswith(b_k):
            t_k = od_id.replace(b_k + "_", "")
            return f"{b_v} - {t_map.get(t_k, t_k.capitalize())}"
    return od_id


def build_intervention_messages(record: pd.Series) -> tuple[list[str], str, str]:
    """Traduce evidencias V9 a una ficha de revisión sin inventar una intervención."""
    distance = float(record["distance_to_nearest_stop_euclidean_m"])
    summer_ok = int(record.get("summer_transit_ok_scenarios", 0) or 0)
    summer_total = int(record.get("summer_transit_scenarios", 4) or 4)
    winter_ok = int(record.get("winter_transit_ok_scenarios", 0) or 0)
    winter_total = int(record.get("winter_transit_scenarios", 4) or 4)
    seasonal_change = str(record.get("seasonal_change", "unchanged"))
    reasons = [f"TSMAI V9: {float(record['tsmai_v9_score']):.3f}, clasificado como Prioridad de mejora."]
    if distance > 1200:
        reasons.append(f"Brecha de proximidad: la parada GTFS más cercana está a {distance:.0f} m en línea recta.")
        action = "Revisar en campo la primera y última milla entre el alojamiento y la parada, antes de plantear cualquier actuación."
    elif distance > 800:
        reasons.append(f"Proximidad baja: la parada GTFS más cercana está a {distance:.0f} m en línea recta.")
        action = "Revisar continuidad peatonal, señalización y conexión de primera y última milla hacia la parada más próxima."
    else:
        reasons.append(f"La proximidad a la parada es de {distance:.0f} m; la prioridad requiere revisar los componentes de servicio y conectividad, no sólo la distancia.")
        action = "Revisar la evidencia de servicio y conectividad en red antes de definir una medida de mejora."
    if seasonal_change == "worsens":
        reasons.append(f"De {summer_total} horarios de autobús probados para este alojamiento, {summer_ok} tenían conexión en verano frente a {winter_ok} en invierno; no implica ausencia total de servicio, sino menos conexiones en los horarios muestreados.")
        action = "Contrastar calendario y servicio programado de invierno, además de la conexión peatonal, antes de proponer cambios."
    elif seasonal_change == "unchanged":
        reasons.append("No se detecta empeoramiento entre las campañas de verano e invierno analizadas.")
    limitation = (
        "La distancia a parada es euclídea y los escenarios TRANSIT describen servicio programado. "
        "La ficha no mide continuidad de aceras, seguridad, puntualidad observada, demanda ni accesibilidad universal certificada."
    )
    return reasons, action, limitation


decision_accommodations = accommodations.copy()
if not accommodation_tsmai_v9_sensitivity.empty:
    decision_accommodations = decision_accommodations.merge(
        accommodation_tsmai_v9_sensitivity[[
            "accommodation_id", "rank_spread", "level_stable_all_scenarios", "robust_top_decile",
        ]],
        on="accommodation_id",
        how="left",
        validate="one_to_one",
    )
else:
    decision_accommodations["rank_spread"] = pd.NA
    decision_accommodations["level_stable_all_scenarios"] = False
    decision_accommodations["robust_top_decile"] = False


with decision_tab:
    st.header("Resumen de decisión")
    st.caption("Vista de cliente basada exclusivamente en el resultado vigente TSMAI V9 y los datos actuales del mapa. Orienta qué revisar; no certifica alojamientos ni determina inversiones.")

    with st.expander("🧭 Guía rápida: qué encontrarás en cada pestaña", expanded=True):
        st.markdown(
            "- **📋 Ficha de intervención** — diagnóstico detallado de un alojamiento concreto en prioridad de mejora.\n"
            "- **🗺️ Análisis territorial** — mapa interactivo con el nivel TSMAI de cada alojamiento, ranking municipal y filtros y capas avanzadas (transporte, ciclovías, evidencia de accesibilidad).\n"
            "- **🎯 Zonas de interés** — agrupaciones automáticas de destinos turísticos por proximidad.\n"
            "- **💬 Consulta guiada** — pregunta en lenguaje natural sobre los resultados (sin inteligencia artificial generativa).\n"
            "- **🔎 Validación técnica** — casos de prueba reales y trazabilidad de la metodología.\n"
            "- **🧭 Planificador** — compara rutas a pie, en bicicleta, en transporte público y en coche entre dos puntos."
        )

    priority_mask = decision_accommodations["tsmai_v9_level"].eq("prioridad de mejora")
    priority_count = int(priority_mask.sum())
    robust_priority_count = int((priority_mask & decision_accommodations["level_stable_all_scenarios"].fillna(False)).sum())
    gap_count = int(decision_accommodations["distance_to_nearest_stop_euclidean_m"].gt(1200).sum())
    winter_worsens = int(decision_accommodations["seasonal_change"].eq("worsens").sum())
    decision_metrics = st.columns(5)
    decision_metrics[0].metric("Alojamientos analizados", f"{len(decision_accommodations):,}")
    decision_metrics[1].metric("Prioridad de mejora", f"{priority_count:,}")
    decision_metrics[2].metric(
        "Prioridades robustas",
        f"{robust_priority_count:,}",
        help="De los alojamientos en «Prioridad de mejora», cuántos mantienen ese nivel aunque cambiemos los pesos del índice (5 escenarios de ponderación).",
    )
    decision_metrics[3].metric("Brechas >1.200 m", f"{gap_count:,}")
    decision_metrics[4].metric("Empeoran en invierno", f"{winter_worsens:,}")
    st.caption(f"Fuentes de contexto: {len(stops):,} paradas GTFS TIB y {len(destinations):,} destinos OSM. Las rutas prioritarias OTP pertenecen a una muestra metodológica, no al ranking V9.")
    summer_service_share = 100 * (decision_accommodations["summer_transit_ok_scenarios"] / decision_accommodations["summer_transit_scenarios"]).mean()
    winter_service_share = 100 * (decision_accommodations["winter_transit_ok_scenarios"] / decision_accommodations["winter_transit_scenarios"]).mean()
    st.subheader("Resultado estacional")
    st.info(
        f"Probamos 4 horarios concretos de autobús por alojamiento, en verano y en invierno. En verano, se encontró conexión en el "
        f"**{summer_service_share:.0f} % de esos horarios**; en invierno, casi ninguno (**{winter_service_share:.0f} %**). "
        f"No significa que no exista transporte público en Mallorca en invierno, sino que en los horarios muestreados no se encontró conexión; "
        f"esto es coherente con la reducción de frecuencias en temporada baja. "
        f"Los {winter_worsens:,} alojamientos que empeoran deben revisarse con el horario oficial de autobuses (GTFS) y con validación de red antes de comunicar una intervención.",
        icon=":material/calendar_month:",
    )

    distribution_col, steps_col = st.columns([1, 1])
    with distribution_col:
        st.subheader("Distribución de acceso a parada")
        if not decision_accommodations.empty:
            access_distribution = decision_accommodations[["walk_access_band_euclidean"]].dropna().copy()
            access_distribution["Banda de acceso"] = access_distribution["walk_access_band_euclidean"].astype("string").map(BAND_LABELS)
            access_distribution["Banda de acceso"] = pd.Categorical(
                access_distribution["Banda de acceso"],
                categories=[BAND_LABELS[band] for band in BAND_ORDER],
                ordered=True,
            )
            fig = px.pie(
                access_distribution,
                names="Banda de acceso",
                title="Distancia euclídea a parada",
                hole=0.4,
                color="Banda de acceso",
                color_discrete_map={BAND_LABELS[band]: BAND_COLORS[band] for band in BAND_ORDER},
                category_orders={"Banda de acceso": [BAND_LABELS[band] for band in BAND_ORDER]},
            )
            fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=280)
            st.plotly_chart(fig, width="stretch")
    with steps_col:
        st.subheader("Cómo usar esta pantalla")
        st.markdown("**1. Localizar**\n\nMira los alojamientos en «Prioridad de mejora» (arriba) y los que tienen «Brechas >1.200 m»: son los más alejados de una parada de autobús.")
        st.markdown("**2. Contrastar**\n\nDe esos, quédate primero con los que aparecen en «Prioridades robustas» (se repiten aunque cambiemos los criterios de cálculo) y con los que están en «Empeoran en invierno».")
        st.markdown("**3. Revisar**\n\nAntes de proponer ninguna obra o inversión, abre la pestaña «Ficha de intervención» para ver el detalle de ese alojamiento concreto.")
        st.info("El sentimiento de usuarios no se publica sin corpus licenciado o consentimiento.", icon=":material/info:")


with intervention_tab:
    st.header("Ficha de intervención")
    st.caption("Ficha de diagnóstico para cada alojamiento en Prioridad de mejora. Propone una revisión, no una obra, ruta o certificación automática.")
    intervention_candidates = decision_accommodations.loc[
        decision_accommodations["tsmai_v9_level"].eq("prioridad de mejora")
    ].copy()
    intervention_candidates = intervention_candidates.sort_values(
        ["level_stable_all_scenarios", "tsmai_v9_score", "commercial_name"],
        ascending=[False, True, True],
    )
    intervention_candidates["intervention_label"] = intervention_candidates.apply(
        lambda row: f"{row['commercial_name']} · {row['municipality_raw']}", axis=1
    )
    selected_intervention_label = st.selectbox(
        "Selecciona un alojamiento prioritario",
        intervention_candidates["intervention_label"].tolist(),
        key="intervention_accommodation",
    )
    intervention_record = intervention_candidates.loc[
        intervention_candidates["intervention_label"].eq(selected_intervention_label)
    ].iloc[0]
    reasons, review_action, limitation = build_intervention_messages(intervention_record)
    intervention_metrics = st.columns(4)
    intervention_metrics[0].metric("TSMAI V9", f"{intervention_record['tsmai_v9_score']:.3f}")
    intervention_metrics[1].metric("Parada más próxima", f"{intervention_record['distance_to_nearest_stop_euclidean_m']:.0f} m")
    intervention_metrics[2].metric(
        "Autobús en verano",
        f"{int(intervention_record.get('summer_transit_ok_scenarios', 0) or 0)}/{int(intervention_record.get('summer_transit_scenarios', 4) or 4)} horarios",
        help="Horarios de los 4 probados en los que se encontró conexión de autobús en verano.",
    )
    intervention_metrics[3].metric(
        "Autobús en invierno",
        f"{int(intervention_record.get('winter_transit_ok_scenarios', 0) or 0)}/{int(intervention_record.get('winter_transit_scenarios', 4) or 4)} horarios",
        help="Horarios de los 4 probados en los que se encontró conexión de autobús en invierno.",
    )
    stop_lat = stop_lon = None
    stop_id = intervention_record.get("nearest_tib_stop_id")
    if stop_id is not None and not stops.empty:
        stop_match = stops.loc[stops["stop_id"].astype(str) == str(stop_id)]
        if not stop_match.empty:
            stop_lat = float(stop_match.iloc[0].geometry.y)
            stop_lon = float(stop_match.iloc[0].geometry.x)
    st.subheader("Ubicación y distancia a la parada")
    st_folium(
        build_intervention_map(
            float(intervention_record.geometry.y), float(intervention_record.geometry.x),
            str(intervention_record["commercial_name"]),
            stop_lat, stop_lon, str(intervention_record["stop_name"]),
            float(intervention_record["distance_to_nearest_stop_euclidean_m"]),
        ),
        height=300, width=None, returned_objects=[], key=f"intervention_map_{intervention_record['accommodation_id']}",
    )
    st.subheader("Motivo de priorización")
    for reason in reasons:
        st.markdown(f"- {reason}")
    detail_columns = st.columns(2)
    with detail_columns[0]:
        st.subheader("Parada y evidencia disponible")
        st.markdown(
            f"**Parada GTFS más próxima:** {intervention_record['stop_name']}  \n"
            f"**Banda de accesibilidad:** {BAND_LABELS.get(str(intervention_record['walk_access_band_euclidean']), intervention_record['walk_access_band_euclidean'])}  \n"
            f"**Cobertura de evidencia V9:** {intervention_record['tsmai_v9_evidence_coverage_pct']:.1f} %  \n"
            f"**Estabilidad del nivel:** {'Sí, en los cinco escenarios de pesos' if bool(intervention_record['level_stable_all_scenarios']) else 'No, sensible a cambios de pesos'}"
        )
    with detail_columns[1]:
        st.subheader("Limitación de interpretación")
        st.warning(limitation, icon=":material/info:")
    st.subheader("Acción de revisión propuesta")
    st.success(review_action, icon=":material/fact_check:")
    st.caption("Siguiente paso recomendado: contrastar esta ficha con itinerario OTP para la fecha de interés y comprobación de campo antes de priorizar presupuesto, obra o comunicación pública.")
    if st.button("🧭 Preparar este alojamiento en Planificador", key="intervention_to_planner"):
        st.session_state["planner_municipality"] = "Todos"
        st.session_state["planner_group"] = "Todos"
        st.session_state["planner_origin"] = f"{intervention_record['commercial_name']} ({intervention_record['municipality_raw']})"
        st.success("Alojamiento preseleccionado. Abre la pestaña «Planificador» para elegir el destino y comparar rutas.", icon=":material/arrow_forward:")

with territorial_tab:
    map_col, filter_col = st.columns([7, 3])
    with filter_col:

        st.header("Filtros territoriales")
        selected_municipalities = st.multiselect("Municipio", sorted(accommodations["municipality_raw"].dropna().unique().tolist()))
        selected_bands = st.multiselect("Banda de accesibilidad", BAND_ORDER, default=BAND_ORDER, format_func=BAND_LABELS.get)
        selected_tsmai_v9_levels = st.multiselect(
            "Nivel TSMAI (Índice de Movilidad Sostenible y Accesibilidad Turística)",
            TSMAI_V4_ORDER,
            default=TSMAI_V4_ORDER,
            format_func=TSMAI_V4_LABELS.get,
            disabled=accommodation_tsmai_v9.empty,
            help="Índice individual con campañas OTP reales de verano e invierno; no equivale a promedio anual ni puntualidad observada.",
        )
        show_tsmai_v9 = st.toggle(
            "Colorear por nivel TSMAI V9",
            value=True,
            disabled=accommodation_tsmai_v9.empty,
            help="Colorea el mapa con el índice multimodal vigente, calculado con evidencia TRANSIT de verano e invierno.",
        )
        with st.expander("Capas del mapa", expanded=False):
            show_stops = st.toggle("Mostrar paradas GTFS", value=True)
            show_destinations = st.toggle("Mostrar destinos turísticos", value=False)
            selected_destination_categories = st.multiselect("Temas de destino OSM", list(DESTINATION_LABELS), default=list(DESTINATION_LABELS), format_func=DESTINATION_LABELS.get, disabled=not show_destinations)
        show_cycleways = show_isochrones = show_air_quality = show_aemet_weather = False
        show_documented_accessibility = show_priority_cases = show_gap_heatmap = False
        if technical_mode:
            with st.expander("Capas técnicas y de contexto", expanded=False):
                show_cycleways = st.toggle("Mostrar infraestructura ciclista OSM", value=False, disabled=cycleways.empty)
                show_isochrones = st.toggle("Mostrar isócronas peatonales OTP", value=False, disabled=isochrones.empty)
                show_air_quality = st.toggle("Mostrar estaciones de calidad del aire CAIB", value=False, disabled=air_quality_stations.empty)
                show_aemet_weather = st.toggle("Mostrar observaciones AEMET históricas", value=False, disabled=aemet_weather_stations.empty)
                show_documented_accessibility = st.toggle("Mostrar evidencia documentada de accesibilidad", value=False, disabled=universal_access.empty)
                show_priority_cases = st.toggle("Mostrar casos OD históricos de referencia", value=False)
                show_gap_heatmap = st.toggle("Mostrar intensidad de brechas", value=False)
    
    
    filtered = accommodations.loc[accommodations["walk_access_band_euclidean"].astype("string").isin(selected_bands)].copy()
    if selected_municipalities:
        filtered = filtered.loc[filtered["municipality_raw"].isin(selected_municipalities)].copy()
    filtered_destinations = destinations.loc[destinations["destination_theme"].astype("string").isin(selected_destination_categories)].copy()
    filtered_priorities = priorities.loc[priorities["robust_priority"]].copy()
    if selected_municipalities:
        filtered_priorities = filtered_priorities.loc[filtered_priorities["origin_municipality"].isin(selected_municipalities)]
    if not active_accommodations.empty:
        active_columns = ["accommodation_id", "distance_to_cycle_infrastructure_m", "cycle_infrastructure_access_band", "distance_to_pedestrian_infrastructure_m", "pedestrian_infrastructure_access_band"]
        filtered = filtered.merge(active_accommodations[active_columns], on="accommodation_id", how="left", validate="one_to_one")
    if not universal_access.empty:
        universal_columns = [
            "accommodation_id", "distance_to_osm_accessibility_evidence_m",
            "distance_to_osm_pedestrian_context_m", "distance_to_gtfs_wheelchair_stop_m",
            "osm_evidence_within_400m", "osm_pedestrian_context_within_400m",
            "gtfs_wheelchair_stop_within_800m", "documented_accessibility_evidence_level",
        ]
        filtered = filtered.merge(
            universal_access[universal_columns], on="accommodation_id", how="left", validate="one_to_one"
        )
    if not active_destinations.empty:
        destination_columns = ["poi_id", "distance_to_cycle_infrastructure_m", "cycle_infrastructure_access_band", "distance_to_pedestrian_infrastructure_m", "pedestrian_infrastructure_access_band"]
        filtered_destinations = filtered_destinations.merge(active_destinations[destination_columns], on="poi_id", how="left", validate="one_to_one")
    if not accommodation_tsmai_v3.empty:
        filtered = filtered.merge(
            accommodation_tsmai_v3[["accommodation_id", "tsmai_v3_accommodation_score", "tsmai_v3_accommodation_level", "evidence_coverage_pct"]],
            on="accommodation_id", how="left", validate="one_to_one"
        )
    if not accommodation_tsmai_v4.empty and "tsmai_v4_score" not in filtered.columns:
        tsmai_v4_columns = [
            "accommodation_id", "tsmai_v4_score", "tsmai_v4_level", "evidence_coverage_pct",
            "public_transport_proximity_score", "public_transport_service_score",
            "cycling_evidence_proximity_score", "pedestrian_evidence_proximity_score",
            "tourism_destination_proximity_score", "distance_to_nearest_tib_stop_m",
            "distance_to_cycle_evidence_m", "distance_to_pedestrian_evidence_m",
            "distance_to_nearest_tourism_destination_m", "nearest_tib_stop_name",
            "nearest_tourism_destination_name",
        ]
        tsmai_v4_display = accommodation_tsmai_v4[tsmai_v4_columns].rename(
            columns={"evidence_coverage_pct": "tsmai_v4_evidence_coverage_pct"}
        )
        filtered = filtered.merge(tsmai_v4_display, on="accommodation_id", how="left", validate="one_to_one")
    if not accommodation_tsmai_v5.empty and "tsmai_v5_score" not in filtered.columns:
        tsmai_v5_columns = [
            "accommodation_id", "tsmai_v5_score", "tsmai_v5_level", "tsmai_v5_evidence_coverage_pct",
            "route_status", "route_duration_min", "route_walk_distance_m", "walk_5min", "walk_10min",
            "walk_15min", "walk_30min", "destination_name", "destination_category",
        ]
        filtered = filtered.merge(
            accommodation_tsmai_v5[tsmai_v5_columns], on="accommodation_id", how="left", validate="one_to_one"
        )
    if not accommodation_tsmai_v6.empty and "tsmai_v6_score" not in filtered.columns:
        tsmai_v6_columns = [
            "accommodation_id", "tsmai_v6_score", "tsmai_v6_level", "tsmai_v6_evidence_coverage_pct",
            "bicycle_route_status", "bicycle_route_duration_min", "route_bicycle_distance_m",
            "bicycle_10min", "bicycle_20min", "bicycle_30min", "bicycle_45min",
            "bicycle_destination_name", "bicycle_destination_category",
        ]
        filtered = filtered.merge(
            accommodation_tsmai_v6[tsmai_v6_columns], on="accommodation_id", how="left", validate="one_to_one"
        )
    if not accommodation_tsmai_v7.empty and "tsmai_v7_score" not in filtered.columns:
        tsmai_v7_columns = [
            "accommodation_id", "tsmai_v7_score", "tsmai_v7_level", "tsmai_v7_evidence_coverage_pct",
            "transit_route_status", "transit_route_duration_min", "transit_route_walk_distance_m",
            "transit_leg_count", "transfers", "transit_lines", "transit_30min", "transit_60min",
            "transit_90min", "transit_120min", "transit_destination_name", "transit_destination_category",
        ]
        filtered = filtered.merge(
            accommodation_tsmai_v7[tsmai_v7_columns], on="accommodation_id", how="left", validate="one_to_one"
        )
    if not accommodation_tsmai_v8.empty and "tsmai_v8_score" not in filtered.columns:
        tsmai_v8_columns = [
            "accommodation_id", "tsmai_v8_score", "tsmai_v8_level", "tsmai_v8_evidence_coverage_pct",
            "temporal_transit_destination_score", "temporal_transit_level", "temporal_transit_scenarios",
            "temporal_transit_ok_scenarios", "temporal_transit_duration_median_min",
            "transit_ok_share_pct", "transit_60min_share_pct", "transit_90min_share_pct",
            "transit_120min_share_pct",
        ]
        filtered = filtered.merge(
            accommodation_tsmai_v8[tsmai_v8_columns], on="accommodation_id", how="left", validate="one_to_one"
        )
    if not accommodation_tsmai_v9.empty:
        if "tsmai_v9_score" not in filtered.columns:
            tsmai_v9_columns = [
                "accommodation_id", "tsmai_v9_score", "tsmai_v9_level", "tsmai_v9_evidence_coverage_pct",
                "summer_transit_score", "winter_transit_score", "seasonal_transit_destination_score",
                "seasonal_change", "transit_ok_share_delta_pp", "tsmai_v8_to_v9_delta",
            ]
            filtered = filtered.merge(
                accommodation_tsmai_v9[tsmai_v9_columns], on="accommodation_id", how="left", validate="one_to_one"
            )
        filtered = filtered.loc[filtered["tsmai_v9_level"].astype("string").isin(selected_tsmai_v9_levels)].copy()
    if not accommodation_tsmai_v9_sensitivity.empty:
        sensitivity_columns = [
            "accommodation_id", "rank_spread", "level_changes_vs_balanced",
            "level_stable_all_scenarios", "top_decile_scenarios", "robust_top_decile",
        ]
        filtered = filtered.merge(
            accommodation_tsmai_v9_sensitivity[sensitivity_columns], on="accommodation_id", how="left", validate="one_to_one"
        )
    

    coverage_800 = 100 * (filtered["distance_to_nearest_stop_euclidean_m"] <= 800).mean() if len(filtered) else 0
    median_distance = filtered["distance_to_nearest_stop_euclidean_m"].median() if len(filtered) else 0
    gap_count = int((filtered["distance_to_nearest_stop_euclidean_m"] > 1200).sum())
    metric_columns = st.columns(6)
    metric_columns[0].metric("Alojamientos mostrados", f"{len(filtered):,}")
    metric_columns[1].metric("Cobertura a ≤800 m", f"{coverage_800:.1f} %")
    metric_columns[2].metric("Mediana a parada", f"{median_distance:.0f} m")
    metric_columns[3].metric("Brechas >1.200 m", f"{gap_count:,}")
    metric_columns[4].metric("Destinos analizados", f"{len(filtered_destinations):,}")
    metric_columns[5].metric("Temas OSM incluidos", f"{filtered_destinations['destination_theme'].nunique():,}" if len(filtered_destinations) else "0")

    with map_col:
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("🏨 Alojamientos", f"{len(filtered):,}")
        
        good_bands = filtered["distance_to_nearest_stop_euclidean_m"].le(400)
        coverage = (good_bands.sum() / len(filtered) * 100) if len(filtered) > 0 else 0
        kpi_cols[1].metric("A ≤400 m de una parada", f"{coverage:.1f}%")
        
        if show_tsmai_v9 and not accommodation_tsmai_v9.empty and "tsmai_v9_score" in filtered.columns:
            kpi_cols[2].metric("TSMAI Medio", f"{filtered['tsmai_v9_score'].mean():.2f}" if len(filtered) > 0 else "-")
        else:
            kpi_cols[2].metric("🏖️ Destinos Cercanos", f"{len(filtered_destinations):,}")
            
        kpi_cols[3].metric("Mediana a Parada", f"{filtered['distance_to_nearest_stop_euclidean_m'].median():.0f} m" if len(filtered) > 0 else "-")
        
        st.subheader("🗺️ Mapa interactivo de cobertura (Haz clic en un hotel)")
        if filtered.empty:
            st.warning("No hay registros para la combinación de filtros seleccionada.")
        else:
            map_data = st_folium(
                build_territorial_map(filtered, stops, filtered_destinations, filtered_priorities, show_stops, show_destinations, show_priority_cases, show_gap_heatmap, cycleways, isochrones, air_quality_stations, aemet_weather_stations, show_cycleways, show_isochrones, show_air_quality, show_aemet_weather, show_tsmai_v9, show_documented_accessibility), 
                height=650, width=None, returned_objects=["last_object_clicked"], key="territorial_coverage_map"
            )
            
            if map_data and map_data.get("last_object_clicked"):
                clicked = map_data["last_object_clicked"]
                dx = filtered.geometry.x - clicked["lng"]
                dy = filtered.geometry.y - clicked["lat"]
                distances = dx*dx + dy*dy
                closest_idx = distances.idxmin()
                if distances[closest_idx] < 0.0001:
                    hotel = filtered.loc[closest_idx]
                    st.success(f"**🏨 Hotel Seleccionado:** {hotel['commercial_name']} (A {hotel['distance_to_nearest_stop_euclidean_m']:.0f}m de la parada {hotel['stop_name']})")
    with filter_col:
        st.subheader("Distribución de alojamientos")
        distribution = filtered["walk_access_band_euclidean"].astype("string").value_counts().reindex(BAND_ORDER, fill_value=0).rename_axis("band_code").reset_index(name="Alojamientos")
        distribution["Banda"] = distribution["band_code"].map(BAND_LABELS)
        chart = px.bar(distribution, x="Banda", y="Alojamientos", color="Banda", color_discrete_map={BAND_LABELS[key]: value for key, value in BAND_COLORS.items()}, labels={"Banda": "", "Alojamientos": "Alojamientos"})
        chart.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(chart, width="stretch")

    st.subheader("Ranking municipal")
    municipality_table = (
        filtered.groupby("municipality_raw", dropna=False)
        .agg(
            Alojamientos=("accommodation_id", "size"),
            **{
                "TSMAI V9 medio": ("tsmai_v9_score", "mean"),
                "Prioridades de mejora": ("tsmai_v9_level", lambda values: values.eq("prioridad de mejora").sum()),
                "Brechas >1.200 m": ("distance_to_nearest_stop_euclidean_m", lambda values: values.gt(1200).sum()),
                "Mediana a parada (m)": ("distance_to_nearest_stop_euclidean_m", "median"),
                "Cobertura a ≤800 m (%)": ("distance_to_nearest_stop_euclidean_m", lambda values: 100 * (values <= 800).mean()),
            },
        )
        .reset_index()
        .rename(columns={"municipality_raw": "Municipio"})
        .sort_values(["TSMAI V9 medio", "Alojamientos"], ascending=[True, False])
    )
    municipality_table[["TSMAI V9 medio", "Mediana a parada (m)", "Cobertura a ≤800 m (%)"]] = municipality_table[["TSMAI V9 medio", "Mediana a parada (m)", "Cobertura a ≤800 m (%)"]].round(2)
    client_municipality_table = municipality_table.loc[municipality_table["Alojamientos"].ge(5)].copy()
    st.caption("Ordenado de menor a mayor TSMAI V9 medio; sólo se muestran municipios con al menos cinco alojamientos para evitar conclusiones sobre muestras muy pequeñas.")
    with st.expander("📊 Ver datos detallados", expanded=False):
        st.dataframe(client_municipality_table, width="stretch", hide_index=True)

    if show_destinations:
        st.subheader("Destinos OSM actuales por tema")
        destination_table = (
            filtered_destinations.groupby("destination_theme", dropna=False)
            .agg(Destinos=("poi_id", "size"), Etiquetas_OSM=("destination_category", "nunique"))
            .reset_index()
            .assign(Categoria=lambda frame: frame["destination_theme"].map(DESTINATION_LABELS))
            .loc[:, ["Categoria", "Destinos", "Etiquetas_OSM"]]
            .sort_values("Destinos", ascending=False)
        )
        with st.expander("📊 Ver datos detallados", expanded=False):
            st.dataframe(destination_table, width="stretch", hide_index=True)

    if not accommodation_tsmai_v8.empty:
        with st.container(border=True):
            st.subheader("TSMAI v8 — robustez temporal del transporte público")
            st.caption("Referencia histórica P1. El componente TRANSIT es la media de cuatro escenarios GTFS: martes 08:00, 10:00 y 18:00; sábado 10:00. Mide servicio programado en esos escenarios, no puntualidad u ocupación observadas. El resultado vigente es TSMAI V9.")
            temporal_metrics = st.columns(6)
            temporal_metrics[0].metric("Puntuación media", f"{filtered['tsmai_v8_score'].mean():.3f}" if len(filtered) else "—")
            temporal_metrics[1].metric("Servicio TRANSIT consistente", f"{int(filtered['temporal_transit_level'].eq('servicio_consistente').sum()):,}")
            temporal_metrics[2].metric("Servicio TRANSIT inestable", f"{int(filtered['temporal_transit_level'].eq('servicio_inestable').sum()):,}")
            temporal_metrics[3].metric("Sin TRANSIT en escenarios", f"{int(filtered['temporal_transit_level'].eq('sin_servicio_en_escenarios').sum()):,}")
            temporal_metrics[4].metric("TRANSIT =60 min (media)", f"{filtered['transit_60min_share_pct'].mean():.1f} %" if len(filtered) else "—")
            temporal_metrics[5].metric("TRANSIT =120 min (media)", f"{filtered['transit_120min_share_pct'].mean():.1f} %" if len(filtered) else "—")
            temporal_table = filtered[[
                "commercial_name", "municipality_raw", "tsmai_v8_score", "tsmai_v8_level",
                "temporal_transit_level", "temporal_transit_destination_score", "temporal_transit_ok_scenarios",
                "temporal_transit_duration_median_min", "transit_60min_share_pct", "transit_120min_share_pct",
                "tsmai_v8_evidence_coverage_pct",
            ]].rename(columns={
                "commercial_name": "Alojamiento", "municipality_raw": "Municipio",
                "tsmai_v8_score": "TSMAI v8", "tsmai_v8_level": "Nivel",
                "temporal_transit_level": "Estabilidad TRANSIT",
                "temporal_transit_destination_score": "Puntuación TRANSIT temporal",
                "temporal_transit_ok_scenarios": "Escenarios con TRANSIT",
                "temporal_transit_duration_median_min": "Mediana TRANSIT (min)",
                "transit_60min_share_pct": "TRANSIT =60 min (%)",
                "transit_120min_share_pct": "TRANSIT =120 min (%)",
                "tsmai_v8_evidence_coverage_pct": "Cobertura de evidencia (%)",
            }).sort_values(["TSMAI v8", "Puntuación TRANSIT temporal"], ascending=[False, False], na_position="last")
            temporal_table["Nivel"] = temporal_table["Nivel"].map(TSMAI_V4_LABELS)
            temporal_table["Estabilidad TRANSIT"] = temporal_table["Estabilidad TRANSIT"].map({
                "servicio_consistente": "Servicio consistente",
                "servicio_inestable": "Servicio inestable",
                "sin_servicio_en_escenarios": "Sin servicio en escenarios",
            })
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    temporal_table,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "TSMAI v8": st.column_config.NumberColumn(format="%.3f"),
                        "Puntuación TRANSIT temporal": st.column_config.NumberColumn(format="%.3f"),
                        "Mediana TRANSIT (min)": st.column_config.NumberColumn(format="%.1f"),
                        "TRANSIT =60 min (%)": st.column_config.NumberColumn(format="%.1f %%"),
                        "TRANSIT =120 min (%)": st.column_config.NumberColumn(format="%.1f %%"),
                        "Cobertura de evidencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    },
                )

    if not accommodation_tsmai_v7.empty:
        with st.container(border=True):
            st.subheader("TSMAI v7 — movilidad sostenible multimodal completa")
            st.caption("Referencia histórica P0: combina acceso y servicio GTFS, evidencia OSM, rutas WALK, BICYCLE y TRANSIT de OTP. El componente TRANSIT sólo puntúa itinerarios con un tramo real de transporte público hacia un POI situado entre 8 y 20 km. El resultado vigente es TSMAI V9.")
            tsmai_v7_metrics = st.columns(8)
            tsmai_v7_metrics[0].metric("Puntuación media", f"{filtered['tsmai_v7_score'].mean():.3f}" if len(filtered) else "—")
            tsmai_v7_metrics[1].metric("WALK =15 min", f"{100 * filtered['walk_15min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v7_metrics[2].metric("BICYCLE =20 min", f"{100 * filtered['bicycle_20min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v7_metrics[3].metric("TRANSIT =60 min", f"{100 * filtered['transit_60min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v7_metrics[4].metric("TRANSIT =120 min", f"{100 * filtered['transit_120min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v7_metrics[5].metric("Sin ruta WALK", f"{int(filtered['route_status'].eq('no_route').sum()):,}")
            tsmai_v7_metrics[6].metric("Sin ruta BICYCLE", f"{int(filtered['bicycle_route_status'].eq('no_route').sum()):,}")
            tsmai_v7_metrics[7].metric("Sin TRANSIT efectivo", f"{int(filtered['transit_route_status'].ne('ok').sum()):,}")
            tsmai_v7_table = filtered[[
                "commercial_name", "municipality_raw", "tsmai_v7_score", "tsmai_v7_level",
                "route_duration_min", "bicycle_route_duration_min", "transit_route_duration_min",
                "transit_destination_name", "transit_lines", "transfers", "transit_route_status",
                "tsmai_v7_evidence_coverage_pct",
            ]].rename(columns={
                "commercial_name": "Alojamiento", "municipality_raw": "Municipio",
                "tsmai_v7_score": "TSMAI v7", "tsmai_v7_level": "Nivel",
                "route_duration_min": "Tiempo WALK (min)",
                "bicycle_route_duration_min": "Tiempo BICYCLE (min)",
                "transit_route_duration_min": "Tiempo TRANSIT (min)",
                "transit_destination_name": "Destino TRANSIT", "transit_lines": "Líneas TIB",
                "transfers": "Transbordos", "transit_route_status": "Estado TRANSIT",
                "tsmai_v7_evidence_coverage_pct": "Cobertura de evidencia (%)",
            }).sort_values(["TSMAI v7", "Tiempo TRANSIT (min)"], ascending=[False, True], na_position="last")
            tsmai_v7_table["Nivel"] = tsmai_v7_table["Nivel"].map(TSMAI_V4_LABELS)
            tsmai_v7_table["Estado TRANSIT"] = tsmai_v7_table["Estado TRANSIT"].map(ROUTE_STATUS_LABELS).fillna(tsmai_v7_table["Estado TRANSIT"])
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    tsmai_v7_table,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "TSMAI v7": st.column_config.NumberColumn(format="%.3f"),
                        "Tiempo WALK (min)": st.column_config.NumberColumn(format="%.1f"),
                        "Tiempo BICYCLE (min)": st.column_config.NumberColumn(format="%.1f"),
                        "Tiempo TRANSIT (min)": st.column_config.NumberColumn(format="%.1f"),
                        "Transbordos": st.column_config.NumberColumn(format="%d"),
                        "Cobertura de evidencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    },
                )

    if not accommodation_tsmai_v6.empty:
        with st.container(border=True):
            st.subheader("TSMAI v6 — accesibilidad multimodal efectiva")
            st.caption("Referencia histórica V6. Combina GTFS TIB, evidencia de ciclovías y red peatonal OSM, rutas WALK y BICYCLE reales de OTP. Las rutas sin itinerario se mantienen como tales y no certifica seguridad, continuidad, pendiente ni accesibilidad universal.")
            tsmai_v6_metrics = st.columns(7)
            tsmai_v6_metrics[0].metric("Puntuación media", f"{filtered['tsmai_v6_score'].mean():.3f}" if len(filtered) else "—")
            tsmai_v6_metrics[1].metric("WALK =15 min", f"{100 * filtered['walk_15min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v6_metrics[2].metric("WALK =30 min", f"{100 * filtered['walk_30min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v6_metrics[3].metric("BICYCLE =10 min", f"{100 * filtered['bicycle_10min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v6_metrics[4].metric("BICYCLE =20 min", f"{100 * filtered['bicycle_20min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v6_metrics[5].metric("Sin ruta WALK", f"{int(filtered['route_status'].eq('no_route').sum()):,}")
            tsmai_v6_metrics[6].metric("Sin ruta BICYCLE", f"{int(filtered['bicycle_route_status'].eq('no_route').sum()):,}")
            tsmai_v6_table = filtered[[
                "commercial_name", "municipality_raw", "tsmai_v6_score", "tsmai_v6_level",
                "route_duration_min", "bicycle_route_duration_min", "destination_name",
                "bicycle_destination_name", "route_status", "bicycle_route_status",
                "tsmai_v6_evidence_coverage_pct",
            ]].rename(columns={
                "commercial_name": "Alojamiento", "municipality_raw": "Municipio",
                "tsmai_v6_score": "TSMAI v6", "tsmai_v6_level": "Nivel",
                "route_duration_min": "Tiempo WALK (min)",
                "bicycle_route_duration_min": "Tiempo BICYCLE (min)",
                "destination_name": "Destino WALK", "bicycle_destination_name": "Destino BICYCLE",
                "route_status": "Estado WALK", "bicycle_route_status": "Estado BICYCLE",
                "tsmai_v6_evidence_coverage_pct": "Cobertura de evidencia (%)",
            }).sort_values(["TSMAI v6", "Tiempo WALK (min)"], ascending=[False, True], na_position="last")
            tsmai_v6_table["Nivel"] = tsmai_v6_table["Nivel"].map(TSMAI_V4_LABELS)
            tsmai_v6_table["Estado WALK"] = tsmai_v6_table["Estado WALK"].map(ROUTE_STATUS_LABELS).fillna(tsmai_v6_table["Estado WALK"])
            tsmai_v6_table["Estado BICYCLE"] = tsmai_v6_table["Estado BICYCLE"].map(ROUTE_STATUS_LABELS).fillna(tsmai_v6_table["Estado BICYCLE"])
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    tsmai_v6_table,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "TSMAI v6": st.column_config.NumberColumn(format="%.3f"),
                        "Tiempo WALK (min)": st.column_config.NumberColumn(format="%.1f"),
                        "Tiempo BICYCLE (min)": st.column_config.NumberColumn(format="%.1f"),
                        "Cobertura de evidencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    },
                )

    if not accommodation_tsmai_v5.empty:
        with st.container(border=True):
            st.subheader("TSMAI v5 — acceso turístico WALK por red")
            st.caption("Referencia histórica V5. Sustituye la proximidad geométrica al destino por una ruta WALK real de OTP hacia el POI elegible más próximo. Los siete casos sin itinerario se conservan con puntuación de acceso WALK 0; no son datos inventados ni registros eliminados.")
            tsmai_v5_metrics = st.columns(6)
            tsmai_v5_metrics[0].metric("Puntuación media", f"{filtered['tsmai_v5_score'].mean():.3f}" if len(filtered) else "—")
            tsmai_v5_metrics[1].metric("Destino a =5 min", f"{100 * filtered['walk_5min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v5_metrics[2].metric("Destino a =10 min", f"{100 * filtered['walk_10min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v5_metrics[3].metric("Destino a =15 min", f"{100 * filtered['walk_15min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v5_metrics[4].metric("Destino a =30 min", f"{100 * filtered['walk_30min'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v5_metrics[5].metric("Sin ruta WALK", f"{int(filtered['route_status'].eq('no_route').sum()):,}")
            tsmai_v5_table = filtered[[
                "commercial_name", "municipality_raw", "tsmai_v5_score", "tsmai_v5_level",
                "destination_name", "destination_category", "route_status", "route_duration_min",
                "route_walk_distance_m", "tsmai_v5_evidence_coverage_pct",
            ]].rename(columns={
                "commercial_name": "Alojamiento", "municipality_raw": "Municipio",
                "tsmai_v5_score": "TSMAI v5", "tsmai_v5_level": "Nivel",
                "destination_name": "Destino WALK", "destination_category": "Categoria de destino",
                "route_status": "Estado de ruta", "route_duration_min": "Tiempo WALK (min)",
                "route_walk_distance_m": "Distancia WALK (m)",
                "tsmai_v5_evidence_coverage_pct": "Cobertura de evidencia (%)",
            }).sort_values(["TSMAI v5", "Tiempo WALK (min)"], ascending=[False, True], na_position="last")
            tsmai_v5_table["Nivel"] = tsmai_v5_table["Nivel"].map(TSMAI_V4_LABELS)
            tsmai_v5_table["Estado de ruta"] = tsmai_v5_table["Estado de ruta"].map(ROUTE_STATUS_LABELS).fillna(tsmai_v5_table["Estado de ruta"])
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    tsmai_v5_table,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "TSMAI v5": st.column_config.NumberColumn(format="%.3f"),
                        "Tiempo WALK (min)": st.column_config.NumberColumn(format="%.1f"),
                        "Distancia WALK (m)": st.column_config.NumberColumn(format="%.0f"),
                        "Cobertura de evidencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    },
                )

    if not accommodation_tsmai_v4.empty:
        with st.container(border=True):
            st.subheader("TSMAI v4 actual — alojamiento individual")
            st.caption("Referencia histórica V4 sobre 1.461 alojamientos oficiales georreferenciados. Combina proximidad y servicio GTFS TIB (40 %), evidencia ciclista y peatonal OSM (40 %) y proximidad a destinos turísticos OSM (20 %). No certifica continuidad, seguridad ni accesibilidad universal.")
            tsmai_v4_metrics = st.columns(4)
            tsmai_v4_metrics[0].metric("Puntuación media", f"{filtered['tsmai_v4_score'].mean():.3f}" if len(filtered) else "—")
            tsmai_v4_metrics[1].metric("Nivel favorable", f"{int(filtered['tsmai_v4_level'].eq('favorable').sum()):,}")
            tsmai_v4_metrics[2].metric("Prioridad de mejora", f"{int(filtered['tsmai_v4_level'].eq('prioridad de mejora').sum()):,}")
            tsmai_v4_metrics[3].metric("Cobertura de evidencia", f"{filtered['tsmai_v4_evidence_coverage_pct'].mean():.1f} %" if len(filtered) else "—")
            tsmai_v4_table = filtered[[
                "commercial_name", "municipality_raw", "tsmai_v4_score", "tsmai_v4_level",
                "distance_to_nearest_tib_stop_m", "distance_to_cycle_evidence_m",
                "distance_to_pedestrian_evidence_m", "distance_to_nearest_tourism_destination_m",
                "tsmai_v4_evidence_coverage_pct",
            ]].rename(columns={
                "commercial_name": "Alojamiento", "municipality_raw": "Municipio",
                "tsmai_v4_score": "TSMAI v4", "tsmai_v4_level": "Nivel",
                "distance_to_nearest_tib_stop_m": "Parada TIB más cercana (m)",
                "distance_to_cycle_evidence_m": "Evidencia ciclista (m)",
                "distance_to_pedestrian_evidence_m": "Evidencia peatonal (m)",
                "distance_to_nearest_tourism_destination_m": "Destino turístico OSM (m)",
                "tsmai_v4_evidence_coverage_pct": "Cobertura de evidencia (%)",
            }).sort_values("TSMAI v4", ascending=False)
            tsmai_v4_table["Nivel"] = tsmai_v4_table["Nivel"].map(TSMAI_V4_LABELS)
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    tsmai_v4_table,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "TSMAI v4": st.column_config.NumberColumn(format="%.3f"),
                        "Parada TIB más cercana (m)": st.column_config.NumberColumn(format="%.0f"),
                        "Evidencia ciclista (m)": st.column_config.NumberColumn(format="%.0f"),
                        "Evidencia peatonal (m)": st.column_config.NumberColumn(format="%.0f"),
                        "Destino turístico OSM (m)": st.column_config.NumberColumn(format="%.0f"),
                        "Cobertura de evidencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    },
                )

    if not active_accommodations.empty:
        with st.container(border=True):
            st.subheader("Movilidad activa: ciclovías, evidencia peatonal e isócronas")
            st.caption("Proximidad calculada sobre infraestructura etiquetada en OpenStreetMap. La evidencia peatonal describe la cartografía disponible; no certifica continuidad, seguridad ni accesibilidad universal.")
            active_columns = st.columns(4)
            cycle_near = 100 * filtered["distance_to_cycle_infrastructure_m"].le(400).mean() if len(filtered) else 0
            pedestrian_near = 100 * filtered["distance_to_pedestrian_infrastructure_m"].le(400).mean() if len(filtered) else 0
            active_columns[0].metric("Aloj. a =400 m de ciclovía", f"{cycle_near:.1f} %")
            active_columns[1].metric("Aloj. a =400 m de evidencia peatonal", f"{pedestrian_near:.1f} %")
            active_columns[2].metric("Tramos ciclistas OSM", f"{active_mobility_report.get('cycling_features', 0):,}")
            active_columns[3].metric("Elementos peatonales OSM", f"{active_mobility_report.get('pedestrian_features', 0):,}")
            active_table = filtered[["commercial_name", "municipality_raw", "distance_to_cycle_infrastructure_m", "cycle_infrastructure_access_band", "distance_to_pedestrian_infrastructure_m", "pedestrian_infrastructure_access_band"]].rename(columns={"commercial_name": "Alojamiento", "municipality_raw": "Municipio", "distance_to_cycle_infrastructure_m": "Distancia a ciclovía (m)", "cycle_infrastructure_access_band": "Acceso a ciclovía", "distance_to_pedestrian_infrastructure_m": "Distancia a evidencia peatonal (m)", "pedestrian_infrastructure_access_band": "Acceso a evidencia peatonal"}).sort_values("Distancia a ciclovía (m)")
            active_table["Acceso a ciclovía"] = active_table["Acceso a ciclovía"].map({"alta_0_400m": "Alta: =400 m", "media_400_800m": "Media: 400–800 m", "brecha_mas_800m": "Brecha: >800 m"})
            active_table["Acceso a evidencia peatonal"] = active_table["Acceso a evidencia peatonal"].map({"alta_0_400m": "Alta: =400 m", "media_400_800m": "Media: 400–800 m", "brecha_mas_800m": "Brecha: >800 m"})
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(active_table, width="stretch", hide_index=True, column_config={"Distancia a ciclovía (m)": st.column_config.NumberColumn(format="%.0f"), "Distancia a evidencia peatonal (m)": st.column_config.NumberColumn(format="%.0f")})
            if not isochrones.empty:
                st.caption("Las isócronas son una malla de 750 m consultada contra rutas WALK reales de OTP, para cuatro alojamientos representativos de las bandas de accesibilidad.")
                iso_table = isochrones[["origin_name", "origin_access_band", "threshold_min", "reachable_grid_cells"]].rename(columns={"origin_name": "Origen", "origin_access_band": "Banda de origen", "threshold_min": "Umbral (min)", "reachable_grid_cells": "Celdas alcanzables"}).sort_values(["Origen", "Umbral (min)"])
                iso_table["Banda de origen"] = iso_table["Banda de origen"].map(BAND_LABELS)
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(iso_table, width="stretch", hide_index=True)

    if not universal_access.empty:
        with st.container(border=True):
            st.subheader("Evidencia documental de accesibilidad universal")
            st.caption("La métrica fuerte sólo cuenta `wheelchair=yes/designated`, pavimento táctil o bordillo rebajado. Los cruces se muestran como contexto peatonal y no como accesibilidad universal. GTFS conserva `wheelchair_boarding=1` separado.")
            universal_columns = st.columns(4)
            universal_columns[0].metric("Evidencias OSM fuertes", f"{universal_access_report.get('osm_strong_features', 0):,}")
            universal_columns[1].metric("Cruces OSM contextuales", f"{universal_access_report.get('osm_contextual_crossings', 0):,}")
            universal_columns[2].metric("Aloj. filtrados con evidencia OSM a =400 m", f"{int(filtered['osm_evidence_within_400m'].fillna(False).sum()):,}")
            universal_columns[3].metric("Aloj. filtrados con parada GTFS etiquetada a =800 m", f"{int(filtered['gtfs_wheelchair_stop_within_800m'].fillna(False).sum()):,}")
            documented_access_table = filtered.loc[
                filtered["osm_evidence_within_400m"].fillna(False)
                | filtered["gtfs_wheelchair_stop_within_800m"].fillna(False),
                [
                    "commercial_name", "municipality_raw", "documented_accessibility_evidence_level",
                    "distance_to_osm_accessibility_evidence_m", "distance_to_gtfs_wheelchair_stop_m",
                    "osm_evidence_within_400m", "gtfs_wheelchair_stop_within_800m",
                ],
            ].copy()
            documented_access_table = documented_access_table.rename(columns={
                "commercial_name": "Alojamiento",
                "municipality_raw": "Municipio",
                "documented_accessibility_evidence_level": "Nivel de evidencia",
                "distance_to_osm_accessibility_evidence_m": "Distancia a evidencia OSM (m)",
                "distance_to_gtfs_wheelchair_stop_m": "Distancia a parada GTFS etiquetada (m)",
                "osm_evidence_within_400m": "OSM positiva =400 m",
                "gtfs_wheelchair_stop_within_800m": "GTFS wheelchair =800 m",
            }).sort_values(["OSM positiva =400 m", "GTFS wheelchair =800 m", "Municipio"], ascending=[False, False, True])
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    documented_access_table,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Distancia a evidencia OSM (m)": st.column_config.NumberColumn(format="%.0f m"),
                        "Distancia a parada GTFS etiquetada (m)": st.column_config.NumberColumn(format="%.0f m"),
                    },
                )
                st.info("La ausencia de etiqueta no equivale a una barrera física. La validación en campo y normativa es obligatoria antes de comunicar accesibilidad universal.", icon=":material/info:")
    if not accommodation_tsmai_v3.empty:
        with st.container(border=True):
            st.subheader("Índice individual de alojamiento TSMAI v3")
            st.caption("Referencia histórica V3 basada en proximidad disponible y evidencia documental. El porcentaje de cobertura identifica qué registros tienen señales incompletas; no convierte un dato ausente en una barrera.")
            index_columns = st.columns(3)
            index_columns[0].metric("Puntuación media", f"{filtered['tsmai_v3_accommodation_score'].mean():.3f}" if len(filtered) else "—")
            index_columns[1].metric("Cobertura media de evidencia", f"{filtered['evidence_coverage_pct'].mean():.1f} %" if len(filtered) else "—")
            index_columns[2].metric("Alojamientos indexados", f"{filtered['tsmai_v3_accommodation_score'].notna().sum():,}")
            index_table = filtered[["commercial_name", "municipality_raw", "tsmai_v3_accommodation_score", "tsmai_v3_accommodation_level", "evidence_coverage_pct"]].rename(columns={"commercial_name": "Alojamiento", "municipality_raw": "Municipio", "tsmai_v3_accommodation_score": "TSMAI v3", "tsmai_v3_accommodation_level": "Nivel", "evidence_coverage_pct": "Cobertura de evidencia (%)"}).sort_values("TSMAI v3", ascending=False)
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(index_table, width="stretch", hide_index=True, column_config={"TSMAI v3": st.column_config.NumberColumn(format="%.3f"), "Cobertura de evidencia (%)": st.column_config.NumberColumn(format="%.1f %%")})

    if not mobility_sentiment.empty:
        with st.container(border=True):
            st.subheader("Sentimiento de movilidad autorizado")
            st.caption("Sólo se muestran municipios con el tamaño muestral mínimo y reseñas con licencia o consentimiento. Este indicador describe tono de comentarios sobre movilidad, no seguridad percibida certificada.")
            publishable_sentiment = mobility_sentiment["mobility_sentiment_mean"].notna()
            sentiment_metrics = st.columns(3)
            sentiment_metrics[0].metric("Menciones de movilidad", f"{int(mobility_sentiment['mobility_review_count'].sum()):,}")
            sentiment_metrics[1].metric("Municipios con menciones", f"{int(mobility_sentiment['mobility_review_count'].gt(0).sum())}")
            sentiment_metrics[2].metric("Municipios publicables (≥10 menciones)", f"{int(publishable_sentiment.sum())}")
            if not publishable_sentiment.any():
                st.info("Ningún municipio alcanza el mínimo de 10 menciones de movilidad, por lo que no se publica ninguna media. Es una limitación del volumen de reseñas disponible, no un resultado neutro.", icon=":material/info:")
            sentiment_display = mobility_sentiment.assign(publication_status=mobility_sentiment["publication_status"].map({"insufficient_sample": "Muestra insuficiente"}).fillna(mobility_sentiment["publication_status"])).rename(columns={"municipality": "Municipio", "mobility_review_count": "Menciones de movilidad", "mobility_sentiment_mean": "Sentimiento medio", "positive_share_pct": "Positivo (%)", "negative_share_pct": "Negativo (%)", "publication_status": "Estado de publicación"}).sort_values("Menciones de movilidad", ascending=False)
            if not publishable_sentiment.any():
                sentiment_display = sentiment_display[["Municipio", "Menciones de movilidad", "Estado de publicación"]]
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(sentiment_display, width="stretch", hide_index=True, column_config={"Sentimiento medio": st.column_config.NumberColumn(format="%.3f"), "Positivo (%)": st.column_config.NumberColumn(format="%.1f %%"), "Negativo (%)": st.column_config.NumberColumn(format="%.1f %%")})

    if not air_quality_stations.empty:
        with st.container(border=True):
            st.subheader("Contexto ambiental: calidad del aire")
            st.caption("Capa oficial CC-BY del Govern de les Illes Balears. Localiza estaciones y sus mediciones disponibles; no interpola contaminación ni asigna exposición a alojamientos o rutas.")
            air_columns = st.columns(2)
            air_columns[0].metric("Estaciones CAIB disponibles", f"{len(air_quality_stations):,}")
            air_columns[1].metric("Campos de contaminantes detectados", f"{len(air_quality_report.get('pollutant_columns_detected', []))}")
            st.info("Activa la capa en el panel lateral para ver las estaciones. Para usarla en una decisión de ruta se necesitaría una serie temporal validada y un modelo espacial de exposición.", icon=":material/info:")
    if not aemet_weather_stations.empty:
        with st.container(border=True):
            period = aemet_weather_report.get("period", {})
            st.subheader("Contexto meteorológico AEMET — observación histórica")
            st.caption(
                f"Observaciones diarias de estaciones dentro de Mallorca para {period.get('start', 'fecha no disponible')} "
                f"a {period.get('end', 'fecha no disponible')}. {aemet_weather_report.get('attribution', 'AEMET, datos abiertos meteorológicos.')} "
                "No es una previsión, no se interpola a rutas y no participa en TSMAI."
            )
            weather_columns = st.columns(4)
            weather_columns[0].metric("Estaciones de Mallorca", f"{aemet_weather_stations['indicativo'].nunique():,}")
            weather_columns[1].metric("Temperatura media", f"{aemet_weather_stations['tmed_c'].mean():.1f} °C" if "tmed_c" in aemet_weather_stations else "—")
            weather_columns[2].metric("Estaciones con precipitación", f"{int(aemet_weather_stations['prec_mm'].gt(0).sum()):,}" if "prec_mm" in aemet_weather_stations else "—")
            weather_columns[3].metric("Racha máxima observada", f"{aemet_weather_stations['wind_gust_ms'].max():.1f} m/s" if "wind_gust_ms" in aemet_weather_stations and aemet_weather_stations['wind_gust_ms'].notna().any() else "—")
            weather_display_columns = [
                "nombre", "indicativo", "observation_date", "tmin_c", "tmed_c", "tmax_c",
                "prec_mm", "wind_mean_ms", "wind_gust_ms", "relative_humidity_mean_pct",
            ]
            weather_display_columns = [column for column in weather_display_columns if column in aemet_weather_stations.columns]
            weather_table = aemet_weather_stations.loc[:, weather_display_columns].rename(columns={
                "nombre": "Estación", "indicativo": "Código", "observation_date": "Fecha",
                "tmin_c": "T. mínima (°C)", "tmed_c": "T. media (°C)", "tmax_c": "T. máxima (°C)",
                "prec_mm": "Precipitación (mm)", "wind_mean_ms": "Viento medio (m/s)",
                "wind_gust_ms": "Racha (m/s)", "relative_humidity_mean_pct": "Humedad media (%)",
            }).sort_values("Estación")
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(weather_table, width="stretch", hide_index=True)
            st.info("Activa la capa AEMET en el panel lateral para localizar las estaciones de estas observaciones históricas.", icon=":material/info:")
    if not road_safety_context.empty:
        with st.container(border=True):
            st.subheader("Contexto de siniestralidad vial DGT — Baleares")
            st.caption("Microdatos DGT 2024 agregados por municipio de la provincia de Baleares. Se muestran como contexto anual: no contienen geometrías de tramo, no son una tasa ajustada por exposición y no se usan para clasificar ni recomendar una ruta.")
            road_columns = st.columns(3)
            road_columns[0].metric("Siniestros con víctimas registrados", f"{road_safety_report.get('balearic_accident_records', 0):,}")
            road_columns[1].metric("Códigos municipales con datos", f"{road_safety_report.get('municipal_codes', 0):,}")
            road_columns[2].metric("Municipios vinculados a la fuente local", f"{road_safety_report.get('municipalities_named_from_ibestat', 0):,}")
            st.warning("No se presenta como un resultado exclusivo de Mallorca hasta disponer de una delimitación insular plenamente verificada. Por ello, este contexto no entra en el TSMAI ni en el motor OTP.", icon=":material/warning:")
            named_safety = road_safety_context.loc[road_safety_context["municipality_name_available"].fillna(False)].copy()
            if not named_safety.empty:
                selected_safety_municipalities = st.multiselect(
                    "Filtrar municipios con nombre verificado",
                    sorted(named_safety["municipality"].dropna().unique().tolist()),
                    key="road_safety_municipality_filter",
                    help="Sólo se listan los códigos municipales que la fuente local pudo vincular a un nombre; el resto se mantiene fuera por no estar verificado.",
                )
                if selected_safety_municipalities:
                    named_safety = named_safety.loc[named_safety["municipality"].isin(selected_safety_municipalities)]
                safety_table = named_safety[[
                    "municipality", "accidents_with_victims_2024", "victims_30_days",
                    "deaths_30_days", "pedestrian_deaths_30_days", "bicycle_deaths_30_days",
                ]].rename(columns={
                    "municipality": "Municipio",
                    "accidents_with_victims_2024": "Siniestros con víctimas 2024",
                    "victims_30_days": "Víctimas (30 días)",
                    "deaths_30_days": "Fallecidos (30 días)",
                    "pedestrian_deaths_30_days": "Fallecidos peatones (30 días)",
                    "bicycle_deaths_30_days": "Fallecidos ciclistas (30 días)",
                }).sort_values("Siniestros con víctimas 2024", ascending=False)
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(safety_table, width="stretch", hide_index=True)

    if not tsmai_extended.empty:
        with st.container(border=True):
            st.subheader("🧪 TSMAI extendido (experimental, opcional)")
            st.warning(
                "No es el TSMAI V9 oficial. Combina el TSMAI V9 (75 %) con evidencia de accesibilidad "
                "universal documentada en OSM y GTFS (25 %) para explorar su efecto; no sustituye el "
                "índice publicado ni sus pesos justificados. No incorpora seguridad vial: los microdatos "
                "DGT sólo identifican con confianza 15 de 43 municipios y no son atribuibles a un alojamiento.",
                icon=":material/science:",
            )
            ext_columns = st.columns(3)
            ext_columns[0].metric("Alojamientos evaluados", f"{tsmai_extended_report.get('records', 0):,}")
            ext_columns[1].metric("Cambian de nivel vs. TSMAI V9", f"{tsmai_extended_report.get('level_changed_vs_v9', 0):,}")
            ext_columns[2].metric("Delta medio vs. TSMAI V9", f"{tsmai_extended_report.get('mean_delta_vs_v9', 0):+.4f}")
            show_only_changed = st.toggle(
                "Mostrar sólo alojamientos que cambian de nivel",
                value=False,
                key="tsmai_extended_only_changed",
            )
            extended_table = tsmai_extended.loc[tsmai_extended["level_changed_vs_v9"]] if show_only_changed else tsmai_extended
            extended_display = extended_table[[
                "commercial_name", "municipality", "tsmai_v9_score", "tsmai_v9_level",
                "universal_access_evidence_score", "tsmai_extended_score", "tsmai_extended_level",
                "tsmai_extended_delta_vs_v9",
            ]].rename(columns={
                "commercial_name": "Alojamiento", "municipality": "Municipio",
                "tsmai_v9_score": "TSMAI V9 (oficial)", "tsmai_v9_level": "Nivel V9",
                "universal_access_evidence_score": "Evidencia accesibilidad universal",
                "tsmai_extended_score": "TSMAI extendido", "tsmai_extended_level": "Nivel extendido",
                "tsmai_extended_delta_vs_v9": "Δ vs. V9",
            }).sort_values("Δ vs. V9", ascending=False)
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(
                    extended_display, width="stretch", hide_index=True,
                    column_config={
                        "TSMAI V9 (oficial)": st.column_config.NumberColumn(format="%.3f"),
                        "Evidencia accesibilidad universal": st.column_config.NumberColumn(format="%.3f"),
                        "TSMAI extendido": st.column_config.NumberColumn(format="%.3f"),
                        "Δ vs. V9": st.column_config.NumberColumn(format="%+.3f"),
                    },
                )

    if technical_mode:
        with st.container(border=True):
            st.subheader("Referencia histórica — perfiles territoriales de accesibilidad (ML)")
            cluster_table = (clusters.groupby("cluster_code").agg(Municipios=("municipality", "size"), Alojamientos=("accommodations", "sum"), **{"Cobertura media a =800 m (%)": ("coverage_800m_pct", "mean"), "Brecha media >1.200 m (%)": ("gap_over_1200m_pct", "mean"), "Mediana a parada (m)": ("median_distance_to_stop_m", "median")}).reset_index().rename(columns={"cluster_code": "Código"}).sort_values("Código").round(2))
            cluster_table.insert(1, "Perfil territorial", cluster_table["Código"].map(cluster_label))
            st.caption("K-Means seleccionó 3 perfiles mediante silhouette (0,502). La etiqueta explica el patrón y el código mantiene la trazabilidad del modelo.")
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(cluster_table, width="stretch", hide_index=True)

    if not tsmai_v2.empty:
        with st.container(border=True):
            st.subheader("Referencia histórica — TSMAI v2 municipal")
            st.caption("Índice municipal explicable de ocho componentes: transporte público, éxito OTP, ciclovías OSM, evidencia peatonal OSM y proximidad a destinos turísticos. No incorpora sentimiento, seguridad percibida, accesibilidad universal certificada, tráfico ni calidad del aire.")
            tsmai_table = tsmai_v2[["municipality", "tsmai_v2_score", "tsmai_v2_level", "coverage_800m_pct", "cycle_infrastructure_400m_pct", "pedestrian_evidence_400m_pct", "tourism_destination_3km_pct", "route_success_pct"]].rename(columns={"municipality": "Municipio", "tsmai_v2_score": "TSMAI v2", "tsmai_v2_level": "Nivel", "coverage_800m_pct": "Cobertura GTFS =800 m (%)", "cycle_infrastructure_400m_pct": "Ciclovía OSM =400 m (%)", "pedestrian_evidence_400m_pct": "Evidencia peatonal =400 m (%)", "tourism_destination_3km_pct": "Destino turístico =3 km (%)", "route_success_pct": "Rutas OTP válidas (%)"}).sort_values("TSMAI v2", ascending=False)
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(tsmai_table, width="stretch", hide_index=True, column_config={"TSMAI v2": st.column_config.NumberColumn(format="%.3f"), "Cobertura GTFS =800 m (%)": st.column_config.NumberColumn(format="%.1f %%"), "Ciclovía OSM =400 m (%)": st.column_config.NumberColumn(format="%.1f %%"), "Evidencia peatonal =400 m (%)": st.column_config.NumberColumn(format="%.1f %%"), "Destino turístico =3 km (%)": st.column_config.NumberColumn(format="%.1f %%"), "Rutas OTP válidas (%)": st.column_config.NumberColumn(format="%.1f %%")})
            if not tsmai_sensitivity.empty:
                with st.expander("Ver sensibilidad de los pesos del TSMAI v2"):
                    st.caption("Se comparan cuatro escenarios de pesos. Un municipio robusto permanece entre los diez primeros en al menos tres escenarios; esto no valida causalmente el índice.")
                    sensitivity_display = tsmai_sensitivity.loc[tsmai_sensitivity["robust_top10"], ["municipality", "balanced_rank", "public_transport_focus_rank", "active_mobility_focus_rank", "tourism_proximity_focus_rank", "top10_scenarios"]].rename(columns={"municipality": "Municipio", "balanced_rank": "Rango equilibrado", "public_transport_focus_rank": "Rango transporte", "active_mobility_focus_rank": "Rango movilidad activa", "tourism_proximity_focus_rank": "Rango turismo", "top10_scenarios": "Escenarios top 10"}).sort_values(["Escenarios top 10", "Rango equilibrado"], ascending=[False, True])
                    with st.expander("📊 Ver datos detallados", expanded=False):
                        st.dataframe(sensitivity_display, width="stretch", hide_index=True)
            if not tsmai.empty:
                with st.expander("Ver índice anterior TSMAI v1 para comparación"):
                    legacy_table = tsmai[["municipality", "tsmai_v1_score", "tsmai_v1_level"]].rename(columns={"municipality": "Municipio", "tsmai_v1_score": "TSMAI v1", "tsmai_v1_level": "Nivel"}).sort_values("TSMAI v1", ascending=False)
                    with st.expander("📊 Ver datos detallados", expanded=False):
                        st.dataframe(legacy_table, width="stretch", hide_index=True, column_config={"TSMAI v1": st.column_config.NumberColumn(format="%.3f")})

    if technical_mode and not emissions.empty:
        emissions_comparable = emissions.loc[emissions["car_status"].eq("ok")].copy()
        avoided_per_shift = emissions_comparable["estimated_avoided_kg_co2eq"].mean() if len(emissions_comparable) else 0.0
        with st.container(border=True):
            st.subheader("Escenarios de impacto ambiental potencial")
            st.caption("Simulación anual, no resultado observado. Parte de las plazas del filtro territorial y del ahorro medio de los pares coche-autobús comparables.")
            scenario_columns = st.columns(3)
            scenario_columns[0].metric("Plazas incluidas", f"{pd.to_numeric(filtered['places'], errors='coerce').fillna(0).sum():,.0f}")
            scenario_columns[1].metric("Ahorro medio por cambio modal", f"{avoided_per_shift:.3f} kg CO2eq")
            scenario_columns[2].metric("Base empírica", f"{len(emissions_comparable)} pares comparables")

    if not intervention_scenarios.empty:
        with st.container(border=True):
            st.subheader("Escenarios de mejora de cobertura")
            st.caption("Análisis de sensibilidad municipal. No sitúa paradas, no estima coste y no recomienda obras: muestra el potencial si una intervención de primera/última milla redujera la distancia de los grupos definidos hasta 800 m.")
            scenario_display = intervention_scenarios[["municipality", "accommodations", "tourist_places", "baseline_coverage_800m_pct", "scenario_first_last_mile_coverage_800m_pct", "scenario_upper_bound_connection_coverage_800m_pct", "first_last_mile_candidates", "critical_gap_candidates"]].rename(columns={"municipality": "Municipio", "accommodations": "Alojamientos", "tourist_places": "Plazas turísticas", "baseline_coverage_800m_pct": "Cobertura base =800 m (%)", "scenario_first_last_mile_coverage_800m_pct": "Escenario última milla (%)", "scenario_upper_bound_connection_coverage_800m_pct": "Límite teórico de conexión (%)", "first_last_mile_candidates": "Candidatos última milla", "critical_gap_candidates": "Brechas críticas"})
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(scenario_display, width="stretch", hide_index=True, column_config={"Plazas turísticas": st.column_config.NumberColumn(format="%.0f"), "Cobertura base =800 m (%)": st.column_config.NumberColumn(format="%.1f %%"), "Escenario última milla (%)": st.column_config.NumberColumn(format="%.1f %%"), "Límite teórico de conexión (%)": st.column_config.NumberColumn(format="%.1f %%")})

    if not tourist_offer_seasonality.empty:
        with st.container(border=True):
            st.subheader("Oferta turística reglada y estacionalidad")
            st.caption("Plazas turísticas oficiales de IBESTAT por municipio y mes. Miden oferta reglada, no ocupación, pernoctaciones ni demanda observada; por ello no se emplean como impacto real de movilidad.")
            offer_display = tourist_offer_seasonality.rename(columns={"municipality": "Municipio", "periods": "Meses disponibles", "first_period": "Primer mes", "latest_period": "Último mes", "minimum_official_places": "Mínimo de plazas", "maximum_official_places": "Máximo de plazas", "mean_official_places": "Media de plazas", "latest_official_places": "Plazas último mes", "seasonal_offer_range_pct": "Rango estacional de oferta (%)"}).sort_values("Plazas último mes", ascending=False)
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(offer_display, width="stretch", hide_index=True, column_config={"Mínimo de plazas": st.column_config.NumberColumn(format="%.0f"), "Máximo de plazas": st.column_config.NumberColumn(format="%.0f"), "Media de plazas": st.column_config.NumberColumn(format="%.1f"), "Plazas último mes": st.column_config.NumberColumn(format="%.0f"), "Rango estacional de oferta (%)": st.column_config.NumberColumn(format="%.1f %%")})

    with st.container(border=True):
        st.subheader("Calidad, cobertura y trazabilidad")
        gtfs_quality = quality_context["gtfs"]
        final_validation = quality_context["final"]
        massive_validation = quality_context["massive"]
        massive_routing = massive_validation.get("routing", {})
        quality_columns = st.columns(4)
        quality_columns[0].metric("Validación reproducible", "Superada" if final_validation.get("validation_status") == "passed" else "Pendiente")
        quality_columns[1].metric("Integridad GTFS", "Sin incidencias" if not any(gtfs_quality.get("integrity_checks", {}).values()) else "Revisar")
        quality_columns[2].metric("Barrido OTP validado", f"{massive_routing.get('ok', 0):,} / {massive_validation.get('pairs_screened', 0):,}")
        quality_columns[3].metric("Tasa de ruta OTP", f"{massive_routing.get('ok_rate_pct', 0):.1f} %")
        trace_table = pd.DataFrame([
            {"Artefacto": "GTFS TIB", "Estado": "Integridad verificada", "Detalle": f"{gtfs_quality.get('table_rows', {}).get('stops', '—')} paradas; SHA-256 {gtfs_quality.get('source_sha256', '—')[:12]}..."},
            {"Artefacto": "Línea base y resultados", "Estado": final_validation.get("validation_status", "no disponible"), "Detalle": f"Validación: {final_validation.get('generated_at_utc', '—')}"},
            {"Artefacto": "Barrido masivo OTP", "Estado": massive_validation.get("validation_status", "no disponible"), "Detalle": f"Fecha/hora experimental documentada; {massive_routing.get('no_itinerary', '—')} sin itinerario"},
        ])
        with st.expander("📊 Ver datos detallados", expanded=False):
            st.dataframe(trace_table, width="stretch", hide_index=True)
        if not massive_summary.empty:
            with st.expander("Ver resumen territorial del barrido masivo"):
                massive_display = massive_summary.rename(columns={"origin_municipality": "Municipio", "origin_access_band": "Banda de origen", "pares": "Pares", "rutas_otp_ok": "Rutas OTP válidas", "con_transporte_publico": "Con transporte público", "duracion_mediana_min": "Duración mediana (min)", "caminata_mediana_m": "Caminata mediana (m)", "tasa_ruta_otp_ok_pct": "Tasa ruta OTP (%)", "tasa_transporte_publico_pct": "Tasa transporte público (%)"})
                massive_display["Banda de origen"] = massive_display["Banda de origen"].map(BAND_LABELS)
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(massive_display, width="stretch", hide_index=True)


with clustering_tab:
    st.header("🎯 Zonas turísticas agrupadas")
    st.markdown("El algoritmo espacial DBSCAN agrupa destinos OSM próximos (radio de 500 m) para facilitar su exploración. No elimina registros de la fuente ni mide accesibilidad; es una vista resumida de los destinos disponibles.")

    import math
    cluster_file = PROJECT_ROOT / "data" / "curated" / "destination_clusters_dbscan.parquet"
    if cluster_file.exists():
        clusters_df = pd.read_parquet(cluster_file)
        cluster_colors = {"nature": "green", "cultural": "orange", "leisure": "purple", "coastal": "blue", "tourism": "red", "mixed": "gray"}
        cluster_theme_labels = {**DESTINATION_LABELS, "mixed": "Mixta"}

        if not accommodations.empty:
            accs_metric = accommodations.to_crs(METRIC_CRS)
            cluster_points_metric = gpd.GeoSeries(
                gpd.points_from_xy(clusters_df["lon_center"], clusters_df["lat_center"]), crs="EPSG:4326"
            ).to_crs(METRIC_CRS)
            nearby_scores, nearby_counts, nearest_municipalities = [], [], []
            for center in cluster_points_metric:
                distances = accs_metric.geometry.distance(center)
                nearby_mask = distances.le(800)
                nearby = accommodations.loc[nearby_mask, "tsmai_v9_score"]
                nearby_scores.append(round(float(nearby.mean()), 3) if len(nearby) else None)
                nearby_counts.append(int(nearby_mask.sum()))
                nearest_municipalities.append(accommodations.iloc[distances.values.argmin()]["municipality_raw"] if len(distances) else None)
            clusters_df["tsmai_v9_medio_cercano"] = nearby_scores
            clusters_df["alojamientos_a_800m"] = nearby_counts
            clusters_df["municipio_mas_cercano"] = nearest_municipalities
        else:
            clusters_df["tsmai_v9_medio_cercano"] = None
            clusters_df["alojamientos_a_800m"] = 0
            clusters_df["municipio_mas_cercano"] = None

        st.metric("Zonas de interés agrupadas", f"{len(clusters_df):,}", help="Cada zona resume varios destinos OSM cercanos.")
        st.caption(f"Resumen de {len(destinations):,} destinos OSM; la fuente original permanece intacta. «TSMAI medio cercano» es la media del índice de los alojamientos a ≤800 m del centro de la zona; no mide la accesibilidad de la zona turística en sí. «Municipio más cercano» es el del alojamiento más próximo al centro de la zona; es una referencia orientativa, no una asignación oficial por límite municipal.")

        theme_options = sorted(clusters_df["dominant_theme"].dropna().unique().tolist())
        selected_themes = st.multiselect(
            "Filtrar por temática dominante",
            theme_options,
            default=theme_options,
            format_func=lambda value: cluster_theme_labels.get(value, value.capitalize()),
            key="cluster_theme_filter",
        )
        filtered_clusters = clusters_df.loc[clusters_df["dominant_theme"].isin(selected_themes)].copy() if selected_themes else clusters_df.iloc[0:0].copy()

        st.subheader("📍 Mapa de Macro-Zonas Turísticas")
        legend_html = "".join(
            f'<span style="display:inline-flex;align-items:center;margin-right:16px;">'
            f'<span style="width:12px;height:12px;border-radius:50%;background:{color};display:inline-block;margin-right:6px;"></span>'
            f'{cluster_theme_labels.get(theme, theme.capitalize())}</span>'
            for theme, color in cluster_colors.items()
        )
        st.markdown(f'<div style="margin-bottom:10px;">{legend_html}</div>', unsafe_allow_html=True)
        if filtered_clusters.empty:
            st.warning("No hay zonas para la temática seleccionada.")
        else:
            cluster_map = folium.Map(location=[39.61, 2.9], zoom_start=10, tiles="OpenStreetMap", prefer_canvas=True)
            for _, row in filtered_clusters.iterrows():
                tsmai_line = (
                    f"TSMAI medio cercano (≤800 m): {row['tsmai_v9_medio_cercano']:.2f} ({row['alojamientos_a_800m']} alojamientos)"
                    if pd.notna(row["tsmai_v9_medio_cercano"])
                    else "Sin alojamientos a ≤800 m"
                )
                folium.Circle(
                    location=[row['lat_center'], row['lon_center']],
                    radius=math.sqrt(row['poi_count']) * 300,
                    color=cluster_colors.get(row['dominant_theme'], "gray"),
                    fill=True,
                    fill_opacity=0.7,
                    tooltip=f"<b>{row['macro_destination_name']}</b><br>POIs agrupados: {row['poi_count']}<br>{tsmai_line}"
                ).add_to(cluster_map)

            st_folium(cluster_map, height=500, width=None, returned_objects=[])

        st.subheader("📊 Directorio de Macro-Destinos")
        display_df = filtered_clusters.copy()
        display_df["dominant_theme"] = display_df["dominant_theme"].map(cluster_theme_labels).fillna(display_df["dominant_theme"])
        display_df = display_df.rename(columns={
            "macro_destination_name": "Nombre de la Zona",
            "dominant_theme": "Temática Dominante",
            "poi_count": "POIs Agrupados",
            "municipio_mas_cercano": "Municipio más cercano",
            "tsmai_v9_medio_cercano": "TSMAI medio cercano",
            "alojamientos_a_800m": "Alojamientos a ≤800 m",
        })[["Nombre de la Zona", "Municipio más cercano", "Temática Dominante", "POIs Agrupados", "TSMAI medio cercano", "Alojamientos a ≤800 m"]].sort_values(by="POIs Agrupados", ascending=False)
        with st.expander("📊 Ver datos detallados", expanded=False):
            st.dataframe(
                display_df, width="stretch", hide_index=True,
                column_config={"TSMAI medio cercano": st.column_config.NumberColumn(format="%.3f")},
            )
    else:
        st.error("El modelo DBSCAN aún no se ha ejecutado. Faltan datos.")
        

with chat_tab:
    st.header("💬 Consulta guiada de resultados")
    st.caption("Responde mediante reglas deterministas sobre TSMAI V9; no usa un modelo generativo ni emite certificaciones de sostenibilidad, seguridad o accesibilidad universal.")
    st.markdown("Ejemplos: *«¿Cuántos alojamientos están en prioridad de mejora?»*, *«¿Qué significa que empeoren en invierno?»* o *«¿Cuál es el municipio con mayor TSMAI medio?»*.")
    with st.expander("Ver todas las preguntas que puedo responder", expanded=False):
        st.markdown(
            "- «¿Cuántos alojamientos están en prioridad de mejora?»\n"
            "- «¿Cuál es el municipio con mayor / menor TSMAI medio?»\n"
            "- «¿Cuáles son los mejores hoteles?»\n"
            "- «¿Qué significa que empeoren en invierno?»\n"
            "- «¿Hay alojamientos desconectados o con brecha de parada?»\n"
            "- «¿Qué dice el índice TSMAI extendido?» *(requiere activar «Mostrar análisis técnico e histórico»)*\n"
            "- «¿Hay anomalías de demanda y accesibilidad?» *(requiere activar «Mostrar análisis técnico e histórico»)*"
        )

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Puedo explicar los resultados del TSMAI V9 y sus límites. Las puntuaciones van de 0 a 1 y sirven para priorizar revisiones, no para certificar alojamientos o municipios."}]
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Pregunta sobre los resultados V9..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Reglas locales, deliberadamente limitadas a afirmaciones que los datos sostienen.
        prompt_lower = prompt.lower()
        response = "Puedo responder sobre la puntuación TSMAI V9, prioridad de mejora, estacionalidad, distancia a paradas, el índice extendido y las anomalías de demanda-accesibilidad. Prueba con «prioridad de mejora», «invierno», «mayor TSMAI medio», «brechas de parada», «índice extendido» o «anomalías»; también puedes abrir «Ver todas las preguntas que puedo responder» arriba."
        
        try:
            municipal_scores = accommodations.groupby("municipality_raw")["tsmai_v9_score"].agg(["mean", "size"])
            if "mejor municipio" in prompt_lower or "municipio más sostenible" in prompt_lower or "mayor tsmai" in prompt_lower:
                best_muni = municipal_scores["mean"].idxmax()
                score = municipal_scores.loc[best_muni, "mean"]
                sample_size = municipal_scores.loc[best_muni, "size"]
                response = f"El municipio con mayor **TSMAI V9 medio** es **{best_muni}** ({score:.3f}; {sample_size:,} alojamientos). Es una comparación dentro de esta muestra e índice; no significa que sea «el mejor» municipio ni certifica sostenibilidad o seguridad."
                
            elif "peor municipio" in prompt_lower or "municipio menos sostenible" in prompt_lower:
                worst_muni = municipal_scores["mean"].idxmin()
                score = municipal_scores.loc[worst_muni, "mean"]
                sample_size = municipal_scores.loc[worst_muni, "size"]
                response = f"El municipio con menor **TSMAI V9 medio** es **{worst_muni}** ({score:.3f}; {sample_size:,} alojamientos). Es una señal para revisar la evidencia desagregada, no una prueba de dependencia del coche ni una recomendación automática de intervención."
                
            elif "hoteles más sostenibles" in prompt_lower or "mejores hoteles" in prompt_lower:
                top_hotels = accommodations.sort_values(by="tsmai_v9_score", ascending=False).head(3)
                response = "Estos son los tres alojamientos con mayor **TSMAI V9** de la muestra; no son una clasificación de sostenibilidad certificada:\n"
                for _, row in top_hotels.iterrows():
                    response += f"- **{row['commercial_name']}** ({row['municipality_raw']}) — TSMAI V9: {row['tsmai_v9_score']:.3f}\n"
                    
            elif "invierno" in prompt_lower or "estacional" in prompt_lower:
                worsens = int(accommodations["seasonal_change"].eq("worsens").sum())
                response = f"**{worsens:,} alojamientos** empeoran en invierno según el componente TRANSIT de V9. Significa que su resultado programado de transporte público es peor en los escenarios de invierno analizados; no mide puntualidad, ocupación ni todo el año."
            elif "prioridad" in prompt_lower:
                priority_count = int(accommodations["tsmai_v9_level"].eq("prioridad de mejora").sum())
                response = f"Hay **{priority_count:,} alojamientos** en el nivel «Prioridad de mejora» de TSMAI V9. Conviene contrastar sus componentes y la robustez ante cambios de pesos antes de decidir cualquier actuación."
            elif "desconectados" in prompt_lower or "aislados" in prompt_lower or "brecha" in prompt_lower or "parada" in prompt_lower:
                brechas = accommodations[accommodations["distance_to_nearest_stop_euclidean_m"] > 1200]
                response = f"Hay **{len(brechas):,} alojamientos** a más de 1.200 m en línea recta de la parada GTFS más cercana. Es una brecha de proximidad que debe validarse con red peatonal y servicio horario; por sí sola no demuestra el modo de viaje utilizado."

            elif "extendido" in prompt_lower or "accesibilidad universal" in prompt_lower:
                if tsmai_extended.empty:
                    response = "El índice TSMAI extendido no está cargado en esta vista. Actívalo marcando «Mostrar análisis técnico e histórico» en la parte superior del dashboard."
                else:
                    changed = tsmai_extended_report.get("level_changed_vs_v9", 0)
                    records = tsmai_extended_report.get("records", len(tsmai_extended))
                    delta = tsmai_extended_report.get("mean_delta_vs_v9", 0)
                    response = f"El **TSMAI extendido** (experimental, no oficial) combina el TSMAI V9 con evidencia de accesibilidad universal OSM/GTFS. De {records:,} alojamientos, **{changed:,} cambian de nivel** frente al TSMAI V9 oficial (delta medio {delta:+.4f}). No sustituye al índice oficial ni incorpora seguridad vial."

            elif "anomal" in prompt_lower:
                if demand_accessibility_anomalies.empty:
                    response = "La detección de anomalías de demanda y accesibilidad no está cargada en esta vista. Actívala marcando «Mostrar análisis técnico e histórico» en la parte superior del dashboard."
                else:
                    count = demand_accessibility_anomalies_report.get("anomalies_detected", 0)
                    compared = demand_accessibility_anomalies_report.get("municipalities_compared", len(demand_accessibility_anomalies))
                    names = demand_accessibility_anomalies_report.get("anomalous_municipalities", [])
                    if count:
                        response = f"Se detectaron **{count} municipio(s)** con demanda turística alta y accesibilidad TSMAI baja simultáneamente (umbral z-score ≥1σ): {', '.join(names)}. Es un umbral estadístico simple sobre {compared} municipios comparables, no un modelo entrenado."
                    else:
                        response = f"No se detectó ningún municipio con demanda alta y accesibilidad baja a la vez, sobre una comparación de {compared} municipios con oferta turística oficial registrada. Es un umbral estadístico simple; no garantiza la ausencia de brechas reales."

        except Exception as exc:
            logger.exception("Error al procesar la pregunta de consulta guiada: %r", prompt)
            response = "Ha ocurrido un error al procesar los datos."
            
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

with explorer_tab:
    st.subheader("Casos de validación técnica")
    st.caption("Muestra histórica de pares origen–destino para explicar la metodología. No forma parte del ranking TSMAI V9 ni representa una recomendación de ruta para el cliente final.")
    if len(priorities):
        validity_columns = st.columns(3)
        if "walk_status" in priorities.columns:
            valid_walk_cases = int(priorities["walk_status"].eq("ok").sum())
            validity_columns[0].metric(
                "Ruta peatonal OTP válida",
                f"{valid_walk_cases} de {len(priorities)}",
                help="Resultado del barrido original sobre la muestra de validación; no es una consulta en vivo.",
            )
        if not bicycle_route_validation.empty:
            valid_bicycle_cases = int(bicycle_route_validation["bike_status"].eq("ok").sum())
            validity_columns[1].metric(
                "Ruta ciclista OTP válida",
                f"{valid_bicycle_cases} de {len(bicycle_route_validation)}",
                help="Resultado del barrido original sobre la muestra de validación; no es una consulta en vivo.",
            )
        if "transit_status" in priorities.columns:
            valid_transit_cases = int(priorities["transit_status"].eq("ok").sum())
            validity_columns[2].metric(
                "Ruta multimodal OTP válida",
                f"{valid_transit_cases} de {len(priorities)}",
                help="Casos con itinerario de transporte público resuelto en el barrido original; no es una consulta en vivo.",
            )
    available_cases = priorities.loc[priorities["robust_priority"]].sort_values("priority_index_score", ascending=False).copy()
    if available_cases.empty:
        available_cases = priorities.sort_values("priority_index_score", ascending=False).copy()
    available_cases["case_label"] = available_cases.apply(lambda row: f"{row.origin_name} → {row.destination_name}", axis=1)
    selected_label = st.selectbox("Selecciona un caso de validación", available_cases["case_label"], key="assistant_case")
    selected_case = available_cases.loc[available_cases["case_label"].eq(selected_label)].iloc[0]
    st.markdown(explain_case(selected_case))
    st.badge("Prioridad robusta" if selected_case["robust_priority"] else "Caso exploratorio", icon=":material/verified:" if selected_case["robust_priority"] else ":material/manage_search:", color="green" if selected_case["robust_priority"] else "blue")
    if not sustainable_mode_recommendations.empty:
        selected_mode = sustainable_mode_recommendations.loc[sustainable_mode_recommendations["od_id"].eq(selected_case["od_id"])]
        if not selected_mode.empty:
            mode = selected_mode.iloc[0]
            st.info(f"**Modo sostenible sugerido: {mode['recommendation_label']}.** {mode['recommendation_rule']} La decisión no certifica seguridad ni disponibilidad de bicicleta.", icon=":material/eco:")
    if not route_infrastructure_profiles.empty:
        selected_profiles = route_infrastructure_profiles.loc[route_infrastructure_profiles["od_id"].eq(selected_case["od_id"])].copy()
        if not selected_profiles.empty:
            with st.expander("Contexto OSM de las rutas activa y peatonal"):
                st.caption("Porcentaje de puntos muestreados cada 100 m a =30 m de infraestructura documentada. Es contexto cartográfico: no mide accidentes, tráfico, continuidad ni seguridad percibida.")
                profile_display = selected_profiles[["mode", "route_status", "duration_min", "near_documented_cycle_infrastructure_pct", "near_documented_pedestrian_infrastructure_pct", "active_infrastructure_context_score"]].rename(columns={"mode": "Modo", "route_status": "Estado OTP", "duration_min": "Duración (min)", "near_documented_cycle_infrastructure_pct": "Cerca de ciclovía OSM (%)", "near_documented_pedestrian_infrastructure_pct": "Cerca de infraestructura peatonal OSM (%)", "active_infrastructure_context_score": "Índice de contexto OSM (0–100)"})
                profile_display["Modo"] = profile_display["Modo"].map({"WALK": "A pie", "BICYCLE": "Bicicleta", "TRANSIT": "Transporte p\u00FAblico", "CAR": "Coche"}).fillna(profile_display["Modo"])
                profile_display["Estado OTP"] = profile_display["Estado OTP"].map({"ok": "Ruta v\u00E1lida", "no_route": "Sin ruta", "service_unavailable": "Servicio ca\u00EDdo", "no_transit_leg": "Sin red p\u00FAblica", "internal_error": "Error interno"}).fillna(profile_display["Estado OTP"])
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(profile_display, width="stretch", hide_index=True, column_config={"Duración (min)": st.column_config.NumberColumn(format="%.1f"), "Cerca de ciclovía OSM (%)": st.column_config.NumberColumn(format="%.1f %%"), "Cerca de infraestructura peatonal OSM (%)": st.column_config.NumberColumn(format="%.1f %%"), "Índice de contexto OSM (0–100)": st.column_config.NumberColumn(format="%.1f")})
    st.info(
        "Esta consulta en vivo sirve para verificar que el motor de rutas responde correctamente sobre este caso de la muestra de validación; "
        "no es la herramienta de planificación del cliente. Para planificar una ruta entre cualquier alojamiento y destino, usa la pestaña **Planificador**.",
        icon=":material/science:",
    )
    with st.form("otp_case_form", border=False):
        date_col, time_col, steps_col, bicycle_col, geometry_col = st.columns([1, 1, 1, 1, 1.35], vertical_alignment="bottom")
        with date_col:
            routing_date = st.date_input("Fecha GTFS", value=pd.Timestamp("2026-09-03").date())
        with time_col:
            routing_time = st.time_input("Hora de salida", value=pd.Timestamp("12:00").time())
        with steps_col:
            request_steps = st.form_submit_button("Indicaciones a pie", icon=":material/directions_walk:")
        with bicycle_col:
            request_bicycle = st.form_submit_button("Ver ruta en bicicleta", icon=":material/directions_bike:")
        with geometry_col:
            request_geometry = st.form_submit_button("Ver ruta multimodal (a pie + autobús)", icon=":material/directions_bus:", type="primary")
    case_coordinates = (float(selected_case.origin_lat), float(selected_case.origin_lon), float(selected_case.destination_lat), float(selected_case.destination_lon))
    if request_steps:
        result = get_walk_steps(*case_coordinates, routing_date.isoformat(), routing_time.strftime("%H:%M"))
        st.session_state["otp_walk_result"] = result
        st.session_state["otp_walk_case"] = selected_case["od_id"]
    if st.session_state.get("otp_walk_case") == selected_case["od_id"] and st.session_state.get("otp_walk_result"):
        result = st.session_state["otp_walk_result"]
        if result["status"] == "ok":
            st.success(f"Ruta a pie OTP: {result['distance_m']:.0f} m · {result['duration_min']:.1f} min. La polilínea verde representa el recorrido real sobre la red.", icon=":material/check_circle:")
            st_folium(build_route_map(selected_case, result["itinerary"]), height=500, width=None, returned_objects=[])
            if result["steps"]:
                st.markdown("**Indicaciones de recorrido**")
                for number, step in enumerate(result["steps"], start=1):
                    st.markdown(format_walk_step(step, number))
            else:
                st.info("OTP devolvió una ruta, pero no expuso giros detallados en esta consulta.")
        else:
            st.warning(result["message"], icon=":material/warning:")
    if request_bicycle:
        bicycle_result = get_bicycle_geometry(*case_coordinates, routing_date.isoformat(), routing_time.strftime("%H:%M"))
        st.session_state["otp_bicycle_result"] = bicycle_result
        st.session_state["otp_bicycle_case"] = selected_case["od_id"]
    if st.session_state.get("otp_bicycle_case") == selected_case["od_id"] and st.session_state.get("otp_bicycle_result"):
        bicycle_result = st.session_state["otp_bicycle_result"]
        if bicycle_result["status"] == "ok":
            itinerary = bicycle_result["itinerary"]
            distance = sum(leg["distance"] for leg in itinerary["legs"])
            st.success(f"Ruta ciclista OTP: {distance:.0f} m · {itinerary['duration'] / 60:.1f} min. Naranja: bicicleta; verde: tramos a pie, si existen.")
            st_folium(build_route_map(selected_case, itinerary), height=560, width=None, returned_objects=[])
        else:
            st.warning(bicycle_result["message"], icon=":material/warning:")
    if request_geometry:
        geometry_result = get_multimodal_geometry(*case_coordinates, routing_date.isoformat(), routing_time.strftime("%H:%M"))
        st.session_state["otp_route_result"] = geometry_result
        st.session_state["otp_route_case"] = selected_case["od_id"]
    if st.session_state.get("otp_route_case") == selected_case["od_id"] and st.session_state.get("otp_route_result"):
        geometry_result = st.session_state["otp_route_result"]
        if geometry_result["status"] == "ok":
            itinerary = geometry_result["itinerary"]
            st.success(f"Ruta multimodal OTP: {itinerary['duration'] / 60:.1f} min · caminata total {itinerary['walkDistance']:.0f} m. Verde: a pie; azul: transporte público.")
            st_folium(build_route_map(selected_case, itinerary), height=560, width=None, returned_objects=[])
            leg_table = pd.DataFrame([{"Modo": "A pie" if leg["mode"] == "WALK" else "Transporte público", "Línea": ((leg.get("route") or {}).get("shortName") or (leg.get("route") or {}).get("longName") or "—"), "Distancia (m)": round(leg["distance"], 0), "Duración (min)": round(leg["duration"] / 60, 1)} for leg in itinerary["legs"]])
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(leg_table, width="stretch", hide_index=True)
        else:
            st.warning(geometry_result["message"], icon=":material/warning:")

    active_route_result = None
    if st.session_state.get("otp_route_case") == selected_case["od_id"]:
        active_route_result = st.session_state.get("otp_route_result")
    elif st.session_state.get("otp_bicycle_case") == selected_case["od_id"]:
        active_route_result = st.session_state.get("otp_bicycle_result")
    elif st.session_state.get("otp_walk_case") == selected_case["od_id"]:
        active_route_result = st.session_state.get("otp_walk_result")
    with st.container(border=True):
        st.subheader("Ficha descargable del caso")
        st.caption("Incluye evidencia, recomendación y, si se ha consultado en esta sesión, los tramos reales de OTP. La ficha no sustituye la validación de campo.")
        export_columns = st.columns(2)
        with export_columns[0]:
            st.download_button("Descargar ficha HTML", data=build_case_html(selected_case, active_route_result, quality_context), file_name=f"ficha_{selected_case['od_id'].lower()}.html", mime="text/html", icon=":material/html:")
        with export_columns[1]:
            st.download_button("Descargar ficha PDF", data=build_case_pdf(selected_case, active_route_result, quality_context), file_name=f"ficha_{selected_case['od_id'].lower()}.pdf", mime="application/pdf", icon=":material/picture_as_pdf:", type="primary")

    robust_priorities = filtered_priorities.sort_values("priority_index_score", ascending=False)
    with st.container(border=True):
        st.subheader("Casos OD históricos con prioridad robusta")
        st.caption("Muestra histórica de pares origen-destino (no alojamientos individuales del TSMAI V9) que permanecen en el top 5 en al menos tres de cuatro escenarios de pesos. Son prioridades de revisión, no decisiones automáticas de obra.")
        priority_table = robust_priorities[["od_id", "origin_name", "destination_name", "priority_index_score", "priority_level", "top5_scenarios", "recommendation_code"]].rename(columns={"od_id": "Caso", "origin_name": "Alojamiento", "destination_name": "Destino", "priority_index_score": "Índice de prioridad", "priority_level": "Nivel", "top5_scenarios": "Escenarios top 5", "recommendation_code": "Acción propuesta"})
        priority_table["Acción propuesta"] = priority_table["Acción propuesta"].map(RECOMMENDATION_LABELS)
        with st.expander("📊 Ver datos detallados", expanded=False):
            st.dataframe(priority_table, width="stretch", hide_index=True, column_config={"Índice de prioridad": st.column_config.NumberColumn(format="%.3f"), "Escenarios top 5": st.column_config.NumberColumn(format="%d")})

    with st.container(border=True):
        st.subheader("Recomendaciones trazables")
        recommendation_table = robust_priorities[["od_id", "origin_name", "destination_name", "recommendation_code", "recommendation", "evidence_summary"]].rename(columns={"od_id": "Caso", "origin_name": "Alojamiento", "destination_name": "Destino", "recommendation_code": "Acción", "recommendation": "Propuesta de revisión", "evidence_summary": "Evidencia resumida"})
        recommendation_table["Acción"] = recommendation_table["Acción"].map(RECOMMENDATION_LABELS)
        with st.expander("📊 Ver datos detallados", expanded=False):
            st.dataframe(recommendation_table, width="stretch", hide_index=True, column_config={"Propuesta de revisión": st.column_config.TextColumn(width="large"), "Evidencia resumida": st.column_config.TextColumn(width="large")})

    if not sustainable_mode_recommendations.empty:
        with st.container(border=True):
            st.subheader("Recomendación de modo sostenible")
            st.caption("Reglas deterministas basadas en rutas OTP reales de la muestra: caminar hasta 20 min; bicicleta hasta 30 min y sin penalización relevante frente al transporte público; después, transporte público si existe. No son preferencias observadas ni un juicio de seguridad.")
            mode_table = sustainable_mode_recommendations[["od_id", "origin_name", "destination_name", "recommendation_label", "walk_only_duration_min", "bike_duration_min", "transit_duration_min", "recommendation_rule"]].rename(columns={"od_id": "Caso", "origin_name": "Alojamiento", "destination_name": "Destino", "recommendation_label": "Modo sugerido", "walk_only_duration_min": "A pie (min)", "bike_duration_min": "Bicicleta (min)", "transit_duration_min": "Transporte público (min)", "recommendation_rule": "Regla aplicada"})
            mode_table["Caso"] = mode_table["Caso"].map(format_case_id)
            mode_table["Caso"] = mode_table["Caso"].map(format_case_id)
            mode_table["Modo sugerido"] = mode_table["Modo sugerido"].map({"walk_only": "Solo a pie", "bike": "Bicicleta", "transit": "Transporte p\u00FAblico"}).fillna(mode_table["Modo sugerido"])
            mode_table["Regla aplicada"] = mode_table["Regla aplicada"].map({"walk_under_20min": "Caminata < 20 min", "bike_competitive_under_30min": "Bicicleta < 30 min (competitiva)", "transit_fallback": "Red p\u00FAblica prioritaria", "no_transit_and_bike_too_long": "Bicicleta larga (sin T. P\u00FAblico)", "no_route_available": "Sin alternativas"}).fillna(mode_table["Regla aplicada"])
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(mode_table, width="stretch", hide_index=True, column_config={"A pie (min)": st.column_config.NumberColumn(format="%.1f"), "Bicicleta (min)": st.column_config.NumberColumn(format="%.1f"), "Transporte público (min)": st.column_config.NumberColumn(format="%.1f"), "Regla aplicada": st.column_config.TextColumn(width="large")})

    if not slope_profiles.empty:
        with st.container(border=True):
            st.subheader("Dificultad por pendiente en rutas prioritarias")
            st.caption("Muestra de rutas WALK reales de OTP (hasta 20 casos priorizados). La pendiente procede del MDP05 del IGN/CNIG (celda de 5 m, grados) y se muestrea cada 1.000 m. No evalúa aceras, pavimento, cruces ni accesibilidad universal.")
            slope_table = slope_profiles.rename(columns={"od_id": "Caso", "origin_name": "Alojamiento", "destination_name": "Destino", "route_status": "Estado de ruta", "samples_requested": "Muestras solicitadas", "samples_valid": "Muestras válidas", "mean_slope_degrees": "Pendiente media (°)", "p95_slope_degrees": "Pendiente p95 (°)", "max_slope_degrees": "Pendiente máxima (°)", "slope_difficulty": "Dificultad"})
            slope_table["Caso"] = slope_table["Caso"].map(format_case_id)
            slope_table["Estado de ruta"] = slope_table["Estado de ruta"].map({"ok": "V\u00E1lida", "no_route": "Sin ruta", "service_unavailable": "Servicio ca\u00EDdo"}).fillna(slope_table["Estado de ruta"])
            slope_table["Dificultad"] = slope_table["Dificultad"].map({"baja_0_3_grados": "Baja: p95 =3°", "moderada_3_6_grados": "Moderada: p95 3–6°", "exigente_mas_6_grados": "Exigente: p95 >6°", "sin_dato": "Sin dato"})
            with st.expander("📊 Ver datos detallados", expanded=False):
                st.dataframe(slope_table, width="stretch", hide_index=True, column_config={"Pendiente media (°)": st.column_config.NumberColumn(format="%.2f"), "Pendiente p95 (°)": st.column_config.NumberColumn(format="%.2f"), "Pendiente máxima (°)": st.column_config.NumberColumn(format="%.2f")})

    if not current_sample_slope_profiles.empty:
        with st.container(border=True):
            st.subheader("Pendiente de la muestra multimodal actual")
            st.caption(
                "Doce pares reales y estratificados (3 bandas TIB × 4 temas de destino), "
                f"consultados en OTP el {current_sample_slope_report.get('routing_date', '—')} "
                f"a las {current_sample_slope_report.get('routing_time', '—')}. "
                "La pendiente procede del MDP05 de IGN/CNIG y se mantiene fuera de TSMAI."
            )
            current_valid = current_sample_slope_profiles.loc[
                current_sample_slope_profiles["samples_valid"].gt(0)
            ].copy()
            current_metrics = st.columns(4)
            current_metrics[0].metric("Pares con pendiente válida", f"{len(current_valid):,} de {len(current_sample_slope_profiles):,}")
            current_metrics[1].metric("Muestras MDP05 válidas", f"{int(current_valid['samples_valid'].sum()):,}")
            current_metrics[2].metric("Pendiente p95 mediana", f"{current_valid['p95_slope_degrees'].median():.2f}°" if not current_valid.empty else "—")
            current_metrics[3].metric("Pares exigentes (p95 >6°)", f"{int(current_valid['slope_difficulty'].eq('exigente_mas_6_grados').sum()):,}")
            difficulty_labels = {
                "baja_0_3_grados": "Baja: p95 =3°",
                "moderada_3_6_grados": "Moderada: p95 3–6°",
                "exigente_mas_6_grados": "Exigente: p95 >6°",
                "sin_dato": "Sin dato",
            }
            slope_display = current_sample_slope_profiles[
                [
                    "od_id", "origin_name", "origin_municipality", "origin_tib_access_band",
                    "destination_name", "destination_theme", "samples_requested", "samples_valid",
                    "mean_slope_degrees", "p95_slope_degrees", "max_slope_degrees", "slope_difficulty",
                ]
            ].rename(columns={
                "od_id": "Caso", "origin_name": "Alojamiento", "origin_municipality": "Municipio",
                "origin_tib_access_band": "Banda TIB", "destination_name": "Destino",
                "destination_theme": "Tema", "samples_requested": "Muestras solicitadas",
                "samples_valid": "Muestras válidas", "mean_slope_degrees": "Pendiente media (°)",
                "p95_slope_degrees": "Pendiente p95 (°)", "max_slope_degrees": "Pendiente máxima (°)",
                "slope_difficulty": "Dificultad",
            })
            sample_band_labels = {
                "alta_0_400m": "Alta: 0–400 m",
                "media_400_800m": "Media: 400–800 m",
                "brecha_mas_800m": "Brecha: más de 800 m",
            }
            slope_display["Caso"] = slope_display["Caso"].map(format_case_id)
            slope_display["Banda TIB"] = slope_display["Banda TIB"].map(sample_band_labels).fillna(slope_display["Banda TIB"])
            slope_display["Tema"] = slope_display["Tema"].map(DESTINATION_LABELS).fillna(slope_display["Tema"])
            slope_display["Dificultad"] = slope_display["Dificultad"].map(difficulty_labels).fillna(slope_display["Dificultad"])
            selected_slope_difficulty = st.multiselect(
                "Filtrar por dificultad de pendiente",
                list(difficulty_labels.values()),
                default=list(difficulty_labels.values()),
                key="slope_difficulty_filter",
            )
            slope_display = slope_display.loc[slope_display["Dificultad"].isin(selected_slope_difficulty)].copy()
            if slope_display.empty:
                st.info("Ningún caso coincide con la dificultad de pendiente seleccionada.", icon=":material/info:")
            else:
                chart = px.bar(
                    slope_display.sort_values("Pendiente p95 (°)", ascending=True),
                    x="Pendiente p95 (°)", y="Caso", color="Dificultad", orientation="h",
                    color_discrete_map={
                        "Baja: p95 =3°": "#22c55e", "Moderada: p95 3–6°": "#f59e0b",
                        "Exigente: p95 >6°": "#dc2626", "Sin dato": "#94a3b8",
                    },
                    hover_data=["Alojamiento", "Destino", "Banda TIB", "Tema", "Muestras válidas"],
                )
                chart.update_layout(margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
                st.plotly_chart(chart, width="stretch")
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(
                        slope_display.sort_values("Pendiente p95 (°)", ascending=False),
                        width="stretch", hide_index=True,
                        column_config={
                            "Pendiente media (°)": st.column_config.NumberColumn(format="%.2f"),
                            "Pendiente p95 (°)": st.column_config.NumberColumn(format="%.2f"),
                            "Pendiente máxima (°)": st.column_config.NumberColumn(format="%.2f"),
                        },
                    )
            st.info(
                "La pendiente es una señal topográfica de una muestra, no una auditoría de itinerario. "
                "No mide aceras, pavimento, cruces, continuidad, iluminación ni accesibilidad universal.",
                icon=":material/info:",
            )

    emissions_comparable = emissions.loc[emissions["car_status"].eq("ok")].copy()
    estimated_co2_avoided = emissions_comparable["estimated_avoided_kg_co2eq"].sum()
    estimated_co2_reduction_pct = 100 * estimated_co2_avoided / emissions_comparable["estimated_car_kg_co2eq"].sum() if not emissions_comparable.empty else 0
    with st.container(border=True):
        st.subheader("Impacto ambiental de la muestra multimodal")
        st.caption("Contrafactual por viajero: coche OTP frente a autobús OTP. Factores MITECO 2024: 0,095 kg CO2eq/km para coche y 0,065 para autobús. No se extrapola la muestra a demanda turística sin datos de ocupación y elección modal.")
        co2_columns = st.columns(3)
        co2_columns[0].metric("Rutas comparables", f"{len(emissions_comparable):,} de {len(emissions):,}")
        co2_columns[1].metric("CO2eq evitado estimado", f"{estimated_co2_avoided:.3f} kg")
        co2_columns[2].metric("Reducción estimada", f"{estimated_co2_reduction_pct:.1f} %")
        emissions_table = emissions_comparable[["od_id", "origin_name", "destination_name", "transit_routes", "car_distance_km", "bus_distance_km", "estimated_avoided_kg_co2eq", "estimated_reduction_pct"]].rename(columns={"od_id": "Caso", "origin_name": "Alojamiento", "destination_name": "Destino", "transit_routes": "Línea", "car_distance_km": "Coche (km)", "bus_distance_km": "Autobús (km)", "estimated_avoided_kg_co2eq": "CO2eq evitado (kg)", "estimated_reduction_pct": "Reducción (%)"}).sort_values("CO2eq evitado (kg)", ascending=False)
        emissions_table["Caso"] = emissions_table["Caso"].map(format_case_id)
        emissions_table["Caso"] = emissions_table["Caso"].map(format_case_id)
        with st.expander("📊 Ver datos detallados", expanded=False):
            st.dataframe(emissions_table, width="stretch", hide_index=True, column_config={"Coche (km)": st.column_config.NumberColumn(format="%.3f"), "Autobús (km)": st.column_config.NumberColumn(format="%.3f"), "CO2eq evitado (kg)": st.column_config.NumberColumn(format="%.3f"), "Reducción (%)": st.column_config.NumberColumn(format="%.1f %%")})

with planner_tab:
    st.subheader("Planificador multimodal para cualquier alojamiento y destino")
    st.caption("Consulta rutas WALK, BICYCLE, TRANSIT y CAR para el par seleccionado. La recomendación es explicable: pondera duración, emisiones estimadas, caminata y transbordos de la consulta actual.")
    planner_filters = st.columns(3)
    with planner_filters[0]:
        planner_municipality = st.selectbox("Municipio del alojamiento", ["Todos"] + sorted(accommodations["municipality_raw"].dropna().astype(str).unique().tolist()), key="planner_municipality")
    with planner_filters[1]:
        planner_group_options = ["Todos"] + sorted(accommodations["group_raw"].dropna().astype(str).unique().tolist()) if "group_raw" in accommodations else ["Todos"]
        planner_group = st.selectbox("Tipo de alojamiento", planner_group_options, key="planner_group")
    with planner_filters[2]:
        planner_category = st.selectbox("Tipo de destino", ["Todos"] + list(DESTINATION_LABELS), format_func=lambda value: "Todos" if value == "Todos" else DESTINATION_LABELS[value], key="planner_category")

    planner_accommodations = accommodations.copy()
    if planner_municipality != "Todos":
        planner_accommodations = planner_accommodations.loc[planner_accommodations["municipality_raw"].astype(str).eq(planner_municipality)]
    if planner_group != "Todos" and "group_raw" in planner_accommodations:
        planner_accommodations = planner_accommodations.loc[planner_accommodations["group_raw"].astype(str).eq(planner_group)]
    planner_destinations = destinations.copy()
    if planner_category != "Todos":
        planner_destinations = planner_destinations.loc[planner_destinations["destination_theme"].astype(str).eq(planner_category)]
    # --- LIMPIEZA DE NOMBRES Y DUPLICADOS ---
    planner_accommodations = planner_accommodations.drop_duplicates(subset=["commercial_name", "municipality_raw"])
    planner_destinations = planner_destinations.drop_duplicates(subset=["name"])
    
    planner_accommodations = planner_accommodations.sort_values(["commercial_name"])
    planner_destinations = planner_destinations.sort_values(["name"])
    
    planner_accommodations["planner_label"] = planner_accommodations.apply(lambda row: f"{row['commercial_name']} ({row['municipality_raw']})", axis=1)
    planner_destinations["planner_label"] = planner_destinations.apply(lambda row: f"{row['name']} ({DESTINATION_LABELS.get(row['destination_theme'], row['destination_theme'])})", axis=1)
    # ------------------------------------------

    if planner_accommodations.empty or planner_destinations.empty:
        st.warning("No hay combinaciones disponibles con los filtros del planificador.")
    else:
        planner_selection = st.columns(2)
        with planner_selection[0]:
            selected_origin_label = st.selectbox("Alojamiento de origen", planner_accommodations["planner_label"].tolist(), key="planner_origin")
        with planner_selection[1]:
            selected_destination_label = st.selectbox("Destino", planner_destinations["planner_label"].tolist(), key="planner_destination")
        origin = planner_accommodations.loc[planner_accommodations["planner_label"].eq(selected_origin_label)].iloc[0]
        destination = planner_destinations.loc[planner_destinations["planner_label"].eq(selected_destination_label)].iloc[0]
        with st.form("dynamic_planner_form", border=False):
            planning_inputs = st.columns(3)
            with planning_inputs[0]:
                planner_date = st.date_input("Fecha de salida", value=pd.Timestamp("2026-09-15").date(), key="planner_date")
            with planning_inputs[1]:
                planner_time = st.time_input("Hora de salida", value=pd.Timestamp("12:00").time(), key="planner_time")
            with planning_inputs[2]:
                planner_profile = st.selectbox("Prioridad", list(PROFILES), format_func={"balanced": "Equilibrada", "low_carbon": "Menor huella de carbono", "low_walking": "Menor caminata", "fastest": "Más rápida"}.get, key="planner_profile")
            run_dynamic_planner = st.form_submit_button("Comparar rutas", type="primary", icon=":material/alt_route:")
        signature = f"{origin.accommodation_id}|{destination.poi_id}|{planner_date}|{planner_time}|{planner_profile}"
        if run_dynamic_planner:
            st.session_state["dynamic_planner_signature"] = signature
            with st.spinner("Consultando cuatro alternativas en OTP; puede tardar hasta 25 segundos…"):
                st.session_state["dynamic_planner_results"] = get_dynamic_comparison(
                    str(origin.accommodation_id), str(origin.commercial_name), float(origin.geometry.y), float(origin.geometry.x),
                    str(destination.poi_id), str(destination.name), float(destination.geometry.y), float(destination.geometry.x),
                    planner_date.isoformat(), planner_time.strftime("%H:%M"),
                )
        if st.session_state.get("dynamic_planner_signature") == signature:
            dynamic_results = st.session_state.get("dynamic_planner_results", ())
            ranked_results = rank_alternatives(dynamic_results, PROFILES[planner_profile])
            service_unavailable = dynamic_results and all(item.status == "service_unavailable" for item in dynamic_results)
            if service_unavailable:
                st.warning("OTP no respondió en 25 segundos. No se ha calculado una comparación; prueba de nuevo más tarde o cambia el par origen–destino.", icon=":material/cloud_off:")
            if ranked_results:
                suggested_mode_label = {"WALK": "A pie", "BICYCLE": "Bicicleta", "TRANSIT": "Transporte público", "CAR": "Coche"}.get(ranked_results[0]["mode"], ranked_results[0]["mode"])
                planner_profile_label = {"balanced": "Equilibrada", "low_carbon": "Menor huella de carbono", "low_walking": "Menor caminata", "fastest": "Más rápida"}.get(planner_profile, planner_profile)
                st.success(f"Alternativa sugerida: {suggested_mode_label}. La puntuación es relativa a las alternativas de este origen-destino, refleja el perfil «{planner_profile_label}» y no certifica seguridad ni accesibilidad universal.", icon=":material/recommend:")
                comparison_table = pd.DataFrame([
                    {
                        "Modo": {"WALK": "A pie", "BICYCLE": "Bicicleta", "TRANSIT": "Transporte p\u00FAblico", "CAR": "Coche"}.get(item["mode"], item["mode"]),
                        "Duración (min)": item["duration_min"],
                        "Caminata (m)": item["walk_distance_m"],
                        "Distancia (m)": item["distance_m"],
                        "Transbordos": item["transfers"],
                        "CO2eq estimado (kg)": item["estimated_kg_co2eq"],
                        "Puntuación relativa (0–100)": item["sustainability_score"],
                    }
                    for item in ranked_results
                ])
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(comparison_table, width="stretch", hide_index=True, column_config={"Duración (min)": st.column_config.NumberColumn(format="%.1f"), "Caminata (m)": st.column_config.NumberColumn(format="%.0f"), "Distancia (m)": st.column_config.NumberColumn(format="%.0f"), "CO2eq estimado (kg)": st.column_config.NumberColumn(format="%.4f"), "Puntuación relativa (0–100)": st.column_config.NumberColumn(format="%.1f")})
                selected_alternative = next(item for item in dynamic_results if item.mode == ranked_results[0]["mode"] and item.status == "ok")
                dynamic_case = pd.Series({"origin_name": origin.commercial_name, "destination_name": destination.name, "origin_lat": origin.geometry.y, "origin_lon": origin.geometry.x, "destination_lat": destination.geometry.y, "destination_lon": destination.geometry.x})
                st_folium(build_route_map(dynamic_case, itinerary_from_alternative(selected_alternative)), height=520, width=None, returned_objects=[])
            unavailable = [item for item in dynamic_results if item.status != "ok"]
            if unavailable:
                st.caption("Resultados no disponibles para esta fecha/hora")
                
                def translate_mode(m):
                    return {"WALK": "A pie", "BICYCLE": "Bicicleta", "TRANSIT": "Transporte público", "CAR": "Coche"}.get(m, m)
                
                def translate_status(s):
                    return {"no_route": "Sin ruta", "service_unavailable": "Servicio caído", "no_transit_leg": "Sin red pública"}.get(s, s)
                
                def translate_message(msg):
                    if msg and "No route found" in msg:
                        return "No se ha encontrado ruta directa. El origen y destino están demasiado alejados o desconectados en este modo."
                    if msg and "Location is not accessible" in msg:
                        return "La ubicación de origen o destino no es accesible por la red."
                    return msg
                
                with st.expander("📊 Ver datos detallados", expanded=False):
                    st.dataframe(pd.DataFrame([{"Modo": translate_mode(item.mode), "Estado": translate_status(item.status), "Detalle": translate_message(item.message)} for item in unavailable]), width="stretch", hide_index=True)
            st.info("Factores de emisión orientativos: coche 0,095 y transporte público 0,065 kg CO2eq/km. No se incluye tráfico en tiempo real, disponibilidad de bicicletas, continuidad de carril ni auditoría de accesibilidad.", icon=":material/info:")
with st.expander("Limitaciones y uso responsable"):
    st.caption("Antes de usar estos resultados para decidir algo, ten en cuenta:")
    st.markdown(
        "- **Distancias del mapa vs. rutas reales**: el mapa principal mide distancia en línea recta a la parada; solo las rutas que consultas una a una usan calles y horarios reales.\n"
        "- **Transporte público, solo una muestra**: el análisis de transporte público se hizo sobre 20 casos y una fecha/hora concretas, no sobre todo el año.\n"
        "- **Las rutas pueden cambiar**: las rutas que ves se calculan en el momento con el motor de rutas real; si cambias la fecha o la hora, el resultado puede variar.\n"
        "- **Carriles bici y aceras, según el mapa colaborativo OpenStreetMap**: si algo no aparece, no significa que no exista en la realidad; esto no sustituye una inspección sobre el terreno.\n"
        "- **Tiempos a pie, aproximados**: se calculan sobre una cuadrícula de 750 m, no calle a calle; la pendiente solo se calculó para una muestra reducida de rutas prioritarias.\n"
        "- **Accesibilidad, solo lo que consta documentado**: la información sobre rampas, avisos sonoros, etc. viene de etiquetas de mapas abiertos; no certifica que una ruta sea accesible en la práctica.\n"
        "- **Versiones anteriores del índice (V1 a V8)**: son herramientas de trabajo que ya no están vigentes, se conservan solo para explicar cómo evolucionó la metodología. Ninguna versión del índice mide la opinión de los usuarios, la sensación de seguridad, el tráfico real ni la demanda turística observada.\n"
        "- **Agrupaciones de zonas, prioridades y recomendaciones**: son una ayuda para decidir qué revisar primero, no una fórmula automática de inversión ni una relación de causa y efecto demostrada.\n"
        "- **Emisiones evitadas**: es una estimación teórica sobre solo 6 casos comparables (coche frente a autobús); no son emisiones medidas realmente ni una proyección para todo el turismo de Mallorca."
    )

    st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1], vertical_alignment="center")
with footer_col1:
    st.markdown("**© 2026 Proyecto TFM - Accesibilidad Turística y Movilidad Sostenible en Mallorca**")
with footer_col2:
    col_text, col_img = st.columns([1, 1], vertical_alignment="center")
    with col_text:
        st.markdown("<p style='text-align: right; margin-top: 10px;'>En colaboración con</p>", unsafe_allow_html=True)
    with col_img:
        st.image("tui_logo.svg", width=80)










