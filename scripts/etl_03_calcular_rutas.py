import sys
import argparse
from math import *
from datetime import *
from os import *
import argparse
from math import *
from datetime import *
from os import *
import json
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
import geopandas as gpd
import pandas as pd
from src.mobility.catalog import Place
from src.mobility.routing import OtpClient
from src.mobility.scoring import PROFILES, rank_alternatives, recommend_sustainable_mode
import concurrent.futures
import math
import os
from datetime import datetime, timezone
import numpy as np
import requests
from shapely.geometry import LineString, Point, mapping
from shapely.ops import unary_union
import re
from rasterio.io import MemoryFile
from pyproj import Transformer
import shutil
import subprocess

"""Genera una muestra estratificada de rutas OTP entre alojamientos y destinos reales.

La muestra es un instrumento de validación y recomendación explicable. No
representa toda la demanda turística ni permite inferir reparto modal observado.
"""

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CURATED = ROOT / "data" / "curated"
METRIC_CRS = "EPSG:25831"
ACCESS_BANDS = ("alta_0_400m", "media_400_800m", "brecha_mas_800m")
THEMES = ("cultural", "nature", "coastal", "leisure")

def atomic_json_write(path, payload):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

def atomic_parquet_write(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)

def latest_path(filename, field):
    # Resuelve la ruta desde el manifiesto
    metadata = json.loads((CURATED / filename).read_text(encoding="utf-8"))
    return ROOT / metadata[field]

def destination_theme(categories):
    values = categories.astype("string")
    result = pd.Series(pd.NA, index=values.index, dtype="string")
    result.loc[values.str.startswith("natural:beach", na=False)] = "coastal"
    result.loc[values.str.startswith("natural:", na=False) & result.isna()] = "nature"
    cultural = values.str.startswith("historic:", na=False) | values.isin(["tourism:museum", "tourism:gallery", "tourism:artwork"])
    result.loc[cultural & result.isna()] = "cultural"
    leisure = values.str.startswith("leisure:", na=False) | values.isin(["tourism:attraction", "tourism:theme_park", "tourism:zoo", "tourism:aquarium", "tourism:picnic_site"])
    result.loc[leisure & result.isna()] = "leisure"
    return result

def load_inputs():
    # Carga las fuentes de entrada
    public_path = latest_path("latest_public_transport_access.json", "accommodation_access_output")
    active_path = latest_path("latest_active_mobility_access.json", "accommodation_access")
    destination_path = latest_path("latest_tourism_destinations.json", "parquet_output")
    public = gpd.read_parquet(public_path)
    active = gpd.read_parquet(active_path)[["accommodation_id", "distance_to_cycle_evidence_m", "distance_to_pedestrian_evidence_m"]]
    accs = public.merge(active, on="accommodation_id", how="inner", validate="one_to_one")
    accs = accs.loc[accs.geom.notna()].copy()
    dests = gpd.read_parquet(destination_path)
    dests["destination_theme"] = destination_theme(dests["destination_category"])
    dests = dests.loc[dests["destination_theme"].isin(THEMES) & dests.geom.notna()].copy()
    if dests.empty:
        raise ValueError("No hay destinos con categorías aptas para la muestra.")
    provenance = {
        "public_transport_access": str(public_path.relative_to(ROOT)),
        "active_mobility_access": str(active_path.relative_to(ROOT)),
        "tourism_destinations": str(destination_path.relative_to(ROOT)),
    }
    return accs, dests, provenance

def representative_accommodations(accs):
    selected = []
    for band in ACCESS_BANDS:
        subset = accs.loc[accs["tib_stop_access_band"].eq(band)].copy()
        if subset.empty:
            raise ValueError(f"No hay alojamientos en la banda TIB {band}.")
        median = subset["distance_to_nearest_tib_stop_m"].median()
        subset["selection_deviation"] = (subset["distance_to_nearest_tib_stop_m"] - median).abs()
        selected.append(subset.sort_values(["selection_deviation", "accommodation_id"]).iloc[0])
    return gpd.GeoDataFrame(selected, geometry="geom", crs=accs.crs).reset_index(drop=True)

def near_dest(origin, dests, theme):
    # Busca el destino mas cercano
    candidates = dests.loc[dests["destination_theme"].eq(theme)].copy()
    if candidates.empty:
        raise ValueError(f"No hay destinos para el tema {theme}.")
    projected = candidates.to_crs(METRIC_CRS)
    origin_projected = gpd.GeoSeries([origin.geom], crs=dests.crs).to_crs(METRIC_CRS).iloc[0]
    distances = projected.geom.distance(origin_projected)
    position = distances.idxmin()
    return candidates.loc[position], float(distances.loc[position])

def build_sample(accs, dests):
    rows = []
    for origin in representative_accommodations(accs).itertuples():
        for theme in THEMES:
            # Busca destino real por tema
            destination, euc_dist = near_dest(origin, dests, theme)
            rows.append({
                "od_id": "%s_%s" % (origin.tib_stop_access_band, theme),
                "origin_accommodation_id": origin.accommodation_id,
                "origin_name": origin.commercial_name,
                "origin_municipality": origin.municipality,
                "origin_tib_access_band": origin.tib_stop_access_band,
                "origin_distance_to_stop_m": float(origin.distance_to_nearest_tib_stop_m),
                "origin_latitude": float(origin.geom.y),
                "origin_longitude": float(origin.geom.x),
                "destination_poi_id": destination.poi_id,
                "destination_name": destination.name,
                "destination_category": destination.destination_category,
                "destination_theme": theme,
                "destination_latitude": float(destination.geom.y),
                "destination_longitude": float(destination.geom.x),
                "selection_euclidean_distance_m": round(euc_dist, 1),
                "selection_rule": "alojamiento representativo por mediana de banda TIB + destino real más próximo de cada tema",
            })
    return pd.DataFrame(rows)

def place(identifier, name, latitude, longitude, kind):
    # Construye el objeto Place OTP
    return Place(id=str(identifier), name=str(name), latitude=float(latitude), longitude=float(longitude), kind=kind)

def route_pair(row, client, routing_date, routing_time):
    # Consulta OTP para este par
    origin = place(row.origin_accommodation_id, row.origin_name, row.origin_latitude, row.origin_longitude, "accommodation")
    destination = place(row.destination_poi_id, row.destination_name, row.destination_latitude, row.destination_longitude, "destination")
    alternatives = client.compare(origin, destination, routing_date, routing_time)
    ranked = {item["mode"]: item for item in rank_alternatives(alternatives, PROFILES["balanced"])}
    recommendation = recommend_sustainable_mode(alternatives)
    output = []
    for alternative in alternatives:
        # Convierte la alternativa a diccionario
        value = alternative.as_dict()
        legs = [{key: item for key, item in leg.items() if key != "geom"} for leg in value.pop("legs")]
            # Descarta la geometria de tramos
        output.append({
            **row.to_dict(),
            "routing_date": routing_date.isoformat(),
            "routing_time": routing_time.strftime("%H:%M"),
            "mode": alternative.mode,
            "r_stat": alternative.status,
            "duration_min": value["duration_min"],
            "route_distance_m": value["distance_m"],
            "walk_distance_m": value["walk_distance_m"],
            "transfers": value["transfers"],
            "estimated_kg_co2eq": value["estimated_kg_co2eq"],
            "router_message": value["message"],
            "route_legs_json": json.dumps(legs, ensure_ascii=False),
            "balanced_sustainability_score": ranked.get(alternative.mode, {}).get("sustainability_score"),
            "recommended_mode": recommendation["recommended_mode"],
            "recommendation_code": recommendation["recommendation_code"],
            "recommendation_reason": recommendation["recommendation_reason"],
        })
    return output

def main_build_multimodal_route_sample():
    parser = argparse.ArgumentParser(description="Construye una muestra de rutas OTP reales y estratificadas.")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today() + timedelta(days=2))
    parser.add_argument("--time", type=time.fromisoformat, default=time(10, 0))
    parser.add_argument("--otp-url", default="http://localhost:8080/otp/gtfs/v1")
    args = parser.parse_args()
    accs, dests, provenance = load_inputs()
    sample = build_sample(accs, dests)
    route_rows = []
    client = OtpClient(args.otp_url)
    for index, (_, row) in enumerate(sample.iterrows(), start=1):
        print(f"[{index}/{len(sample)}] Consultando {row['od_id']}…", flush=True)
        route_rows.extend(route_pair(row, client, args.date, args.time))
    routes = pd.DataFrame(route_rows)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sample_path = CURATED / f"multimodal_route_sample_{run_id}.parquet"
    routes_path = CURATED / f"multimodal_route_results_{run_id}.parquet"
    atomic_parquet_write(sample, sample_path)
    atomic_parquet_write(routes, routes_path)
    report = {
        "status": "passed",
        "sample_pairs": int(len(sample)),
        "route_queries": int(len(routes)),
        "routing_date": args.date.isoformat(),
        "routing_time": args.time.strftime("%H:%M"),
        "otp_endpoint": args.otp_url,
        "sampling_rule": "3 bandas de acceso TIB × 4 temas de destino; sin muestreo sintético ni selección aleatoria.",
        "route_status_by_mode": {
            mode: counts.droplevel(0).to_dict()
            for mode, counts in routes.groupby("mode")["r_stat"].value_counts().groupby(level=0)
        },
        "recommendations": routes.loc[routes["mode"].eq("WALK"), "recommended_mode"].value_counts(dropna=False).to_dict(),
        "recommendation_codes": routes.loc[routes["mode"].eq("WALK"), "recommendation_code"].value_counts(dropna=False).to_dict(),
        "sample_output": str(sample_path.relative_to(ROOT)),
        "routes_output": str(routes_path.relative_to(ROOT)),
        "provenance": provenance,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La muestra no representa la demanda turística ni el reparto modal observado.",
            "Los destinos se seleccionan por proximidad geométrica temática; el resultado de ruta procede de OTP.",
            "Las recomendaciones aplican umbrales explícitos de caminata, bicicleta y transporte; no certifican seguridad o accesibilidad universal.",
        ],
    }
    atomic_json_write(CURATED / "latest_multimodal_route_sample.json", report)
    atomic_json_write(ROOT / "docs" / "multimodal_route_sample_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

"""Isócronas peatonales aproximadas mediante consultas reales a OTP.

Cada celda se consulta sobre la red peatonal del grafo OTP. El borde resultante
no es una distancia euclídea: es una agregación de celdas alcanzables. La
resolución se conserva como metadato para no sobreinterpretar el contorno.
"""

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "curated" / "accommodations_transport_access_baseline.parquet"
OUT_DIR = ROOT / "data" / "curated" / "isochrones"
DOC = ROOT / "docs" / "otp_walk_isochrones_report.json"
OTP_URL = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
METRIC_CRS = "EPSG:25831"
DATE = "2026-09-03"
TIME = "12:00"
THRESHOLDS = [5, 10, 15, 30]
GRID_SPACING_M = 750
RADIUS_M = 3_000
WORKERS = 8

QUERY = """
query WalkIsochrone($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: [{mode: WALK}], numItineraries: 1) {
    itineraries { duration walkDistance }
    routingErrors { code description }
  }
}
"""

def choose_origins():
    data = gpd.read_parquet(BASELINE)
    selected = []
    for band in ["alta_0_400m", "media_400_800m", "baja_800_1200m", "brecha_mas_1200m"]:
        group = data.loc[data["walk_access_band_euclidean"].eq(band)].copy()
        if group.empty:
            continue
        median_distance = group["distance_to_nearest_stop_euclidean_m"].median()
        selected.append(group.iloc[(group["distance_to_nearest_stop_euclidean_m"] - median_distance).abs().argsort().iloc[0]])
    result = gpd.GeoDataFrame(selected, geometry="geom", crs=data.crs).reset_index(drop=True)
    result["isochrone_origin_id"] = [f"ISO{index:02d}" for index in range(1, len(result) + 1)]
    return result

def make_grid(origin):
    projected = gpd.GeoSeries([origin.geom], crs="EPSG:4326").to_crs(METRIC_CRS).iloc[0]
    offsets = np.arange(-RADIUS_M, RADIUS_M + GRID_SPACING_M, GRID_SPACING_M)
    points = [Point(projected.x + dx, projected.y + dy) for dx in offsets for dy in offsets if math.hypot(dx, dy) <= RADIUS_M]
    return gpd.GeoDataFrame({"geom": points}, crs=METRIC_CRS).to_crs("EPSG:4326")

def route_duration(origin, point):
    variables = {
        "from": {"lat": float(origin.geom.y), "lon": float(origin.geom.x)},
        "to": {"lat": float(point.y), "lon": float(point.x)},
        "date": DATE,
        "time": TIME,
    }
    try:
        response = requests.post(OTP_URL, json={"query": QUERY, "variables": variables}, timeout=45)
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            return {"status": "graphql_error", "duration_min": None, "walk_distance_m": None}
        plan = payload.get("data", {}).get("plan", {})
        itineraries = plan.get("itineraries") or []
        if not itineraries:
            return {"status": "no_route", "duration_min": None, "walk_distance_m": None}
        best = min(itineraries, key=lambda item: item["duration"])
        return {"status": "ok", "duration_min": best["duration"] / 60, "walk_distance_m": best["walkDistance"]}
    except requests.RequestException:
        return {"status": "request_error", "duration_min": None, "walk_distance_m": None}

def build_origin(origin):
    # Genera la malla de puntos
    grid = make_grid(origin)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        # Lanza consultas OTP en paralelo
        mapping = {pool.submit(route_duration, origin, point): index for index, point in enumerate(grid.geom)}
        ordered = [None] * len(grid)
        for future in concurrent.futures.as_completed(mapping):
            ordered[mapping[future]] = future.result()
    values = pd.DataFrame(ordered)
    grid = pd.concat([grid.reset_index(drop=True), values], axis=1)
    grid["isochrone_origin_id"] = origin.isochrone_origin_id
    grid["origin_name"] = origin.commercial_name
    grid["origin_access_band"] = origin.walk_access_band_euclidean
    return gpd.GeoDataFrame(grid, geometry="geom", crs="EPSG:4326")

def build_polygons(points):
    # Construye poligonos por tiempo alcanzable
    projected = points.to_crs(METRIC_CRS)
    records = []
    for origin_id, group in projected.groupby("isochrone_origin_id"):
        for threshold in THRESHOLDS:
            reachable = group.loc[group["duration_min"].le(threshold) & group["status"].eq("ok")]
            if reachable.empty:
                continue
            geom = unary_union([item.buffer(GRID_SPACING_M / 2) for item in reachable.geom]).buffer(0)
            records.append({
                "isochrone_origin_id": origin_id,
                "origin_name": group["origin_name"].iloc[0],
                "origin_access_band": group["origin_access_band"].iloc[0],
                "threshold_min": threshold,
                "grid_sp": GRID_SPACING_M,
                "reachable_grid_cells": int(len(reachable)),
                "geom": geom,
            })
    return gpd.GeoDataFrame(records, geometry="geom", crs=METRIC_CRS).to_crs("EPSG:4326")

def main_build_otp_walk_isochrones():
    parser = argparse.ArgumentParser(description="Construye isócronas WALK de OTP sobre una cuadrícula reproducible.")
    parser.add_argument("--execute", action="store_true", help="Autoriza consultas OTP y la publicación de las capas de isócronas.")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({
            "status": "dry_run",
            "origins": "un origen representativo por banda de accesibilidad disponible",
            "date": DATE,
            "time": TIME,
            "message": "No se han consultado rutas ni escrito resultados. Añade --execute para ejecutar la campaña.",
        }, ensure_ascii=False, indent=2))
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    origins = choose_origins()
    print(f"OK Origenes estratificados: {len(origins)}", flush=True)
    point_layers = []
    for index, origin in origins.iterrows():
        print(f"{index + 1}/{len(origins)} — {origin.isochrone_origin_id} {origin.commercial_name}", flush=True)
        point_layers.append(build_origin(origin))
    points = gpd.GeoDataFrame(pd.concat(point_layers, ignore_index=True), geometry="geom", crs="EPSG:4326")
    polygons = build_polygons(points)
    points.to_parquet(OUT_DIR / "otp_walk_isochrones_grid.parquet", index=False)
    polygons.to_parquet(OUT_DIR / "otp_walk_isochrones.parquet", index=False)
    features = []
    for _, row in polygons.iterrows():
        # Convierte cada poligono a GeoJSON
        features.append({"type": "Feature", "geom": mapping(row.geom), "properties": {
            "isochrone_origin_id": str(row.isochrone_origin_id), "origin_name": str(row.origin_name),
            "origin_access_band": str(row.origin_access_band), "threshold_min": int(row.threshold_min),
            "grid_sp": int(row.grid_sp), "reachable_grid_cells": int(row.reachable_grid_cells),
        }})
    (OUT_DIR / "otp_walk_isochrones.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Malla de puntos consultada contra itinerarios WALK reales de OpenTripPlanner; polígonos formados por unión de celdas alcanzables.",
        "otp_endpoint": OTP_URL,
        "date": DATE,
        "time": TIME,
        "origins": origins[["isochrone_origin_id", "commercial_name", "walk_access_band_euclidean"]].to_dict(orient="records"),
        "grid_sp": GRID_SPACING_M,
        "radius_m": RADIUS_M,
        "th_min": THRESHOLDS,
        "grid_points": int(len(points)),
        "successful_routes": int(points["status"].eq("ok").sum()),
        "limitations": [
            "El contorno está aproximado a una cuadrícula de 750 m; no debe interpretarse como límite submétrico.",
            "Representa la red, datos GTFS y fecha/hora documentados, no condiciones de tráfico ni accesibilidad certificada.",
        ],
    }
    DOC.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Malla de rutas: {len(points):,}; rutas OTP validas: {report['successful_routes']:,}")
    print(f"OK Poligonos de isocrona: {len(polygons):,}; informe: {DOC}")

"""Perfila rutas WALK y BICYCLE con infraestructura activa ya extraída de OSM.

El cálculo usa las capas OSM reproducibles de ciclovías y elementos peatonales;
no trata una etiqueta cartográfica como una certificación de seguridad.
"""

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data" / "curated" / "od_multimodal_priority_index.parquet"
CYCLEWAYS = ROOT / "data" / "unified" / "osm" / "mallorca_cycling_infrastructure.parquet"
PEDESTRIAN = ROOT / "data" / "unified" / "osm" / "mallorca_pedestrian_infrastructure.parquet"
OUT = ROOT / "data" / "curated" / "route_osm_infrastructure_profiles.parquet"
REPORT = ROOT / "docs" / "route_osm_infrastructure_profiles_report.json"
OTP_URL = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
METRIC_CRS = "EPSG:25831"

QUERY = """
query RouteProfile($from: InputCoordinates!, $to: InputCoordinates!, $modes: [TransportMode]!) {
  plan(from: $from, to: $to, date: "2026-09-03", time: "12:00",
       transportModes: $modes, numItineraries: 1) {
    itineraries { duration legs { mode distance legGeometry { points } } }
    routingErrors { code description }
  }
}
"""

def dec_poly(encoded):
    index = latitude = longitude = 0
    output: list[tuple[float, float]] = []
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
        output.append((longitude / 1e5, latitude / 1e5))
    return output

def itinerary_geometry(row, mode):
    # Consulta la geometria de ruta
    variables = {
        "from": {"lat": float(row.origin_lat), "lon": float(row.origin_lon)},
        "to": {"lat": float(row.destination_lat), "lon": float(row.destination_lon)},
        "modes": [{"mode": mode}],
    }
    try:
        response = requests.post(OTP_URL, json={"query": QUERY, "variables": variables}, timeout=60)
        response.raise_for_status()
        itinerary = ((response.json().get("data", {}).get("plan", {}) or {}).get("itineraries") or [None])[0]
    except (requests.RequestException, ValueError):
        return "routing_error", None, None
    if not itinerary:
        return "no_route", None, None
    points = [point for leg in itinerary["legs"] for point in dec_poly((leg.get("legGeometry") or {}).get("points", ""))]
        # Valida que haya suficientes puntos
    if len(points) < 2:
        return "no_geometry", None, None
    return "ok", LineString(points), float(itinerary["duration"]) / 60

def share_near(points, infra, radius_m = 30):
    # Calcula porcentaje de puntos cercanos
    if points.empty or infra.empty:
        return 0.0
    matches, distances = infra.sindex.nearest(points, return_distance=True)
    matched_positions = set(matches[0][distances <= radius_m])
    return round(100 * len(matched_positions) / len(points), 1)

def profile_route(route, cycleways, ped):
    # Muestrea la ruta cada 100m
    metric_route = gpd.GeoSeries([route], crs="EPSG:4326").to_crs(METRIC_CRS).iloc[0]
    sample_distances = list(range(0, int(metric_route.length) + 1, 100)) or [0]
    points = gpd.GeoSeries([metric_route.interpolate(distance) for distance in sample_distances], crs=METRIC_CRS)
        # Calcula cercania a infraestructura activa
    cycle_share = share_near(points, cycleways)
    pedestrian_share = share_near(points, ped)
    return {
        "sample_points": int(len(points)),
        "near_documented_cycle_infrastructure_pct": cycle_share,
        "near_documented_pedestrian_infrastructure_pct": pedestrian_share,
        "active_infrastructure_context_score": round(.55 * cycle_share + .45 * pedestrian_share, 1),
    }

def main_build_route_infrastructure_profiles():
    cycleways = gpd.read_parquet(CYCLEWAYS).to_crs(METRIC_CRS)
    ped = gpd.read_parquet(PEDESTRIAN).to_crs(METRIC_CRS)
    cases = pd.read_parquet(CASES).sort_values("priority_index_score", ascending=False)
    rows = []
    for index, (_, case) in enumerate(cases.iterrows(), start=1):
        for mode in ["WALK", "BICYCLE"]:
            # Obtiene geometria para cada modo
            status, geom, duration = itinerary_geometry(case, mode)
            row = {"od_id": case.od_id, "origin_name": case.origin_name, "destination_name": case.destination_name, "mode": mode, "r_stat": status, "duration_min": duration}
            if geom is not None:
                row.update(profile_route(geom, cycleways, ped))
            rows.append(row)
        print(f"{index}/{len(cases)} — {case.od_id}", flush=True)
    result = pd.DataFrame(rows)
    result.to_parquet(OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "cases": int(len(cases)), "profiles": int(len(result)),
        "method": "Muestreo cada 100 m de geometrías OTP y proximidad <=30 m a capas de movilidad activa extraídas de OSM.",
        "limitations": ["El indicador mide documentación OSM, no siniestralidad, tráfico, continuidad física ni percepción de seguridad.", "Una vía no etiquetada no implica infraestructura ausente.", "No sustituye una auditoría de campo."],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Perfiles OSM: {len(result)} rutas")

"""Calcula perfiles de pendiente de rutas peatonales OTP con el MDP05 del IGN.

El servicio WCS abierto del IGN devuelve grados de pendiente. Se analizan los
20 casos multimodales priorizados para que la pendiente sea una evidencia
homogénea de la muestra, no una certificación de accesibilidad universal.
"""

_gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
if _gdal_data.exists():
    os.environ.setdefault("GDAL_DATA", str(_gdal_data))

ROOT = Path(__file__).resolve().parents[1]
PRIORITIES = ROOT / "data" / "curated" / "od_multimodal_priority_index.parquet"
SENSITIVITY = ROOT / "data" / "curated" / "od_multimodal_priority_sensitivity.parquet"
OUT = ROOT / "data" / "curated" / "route_slope_profiles_ign_mdp05.parquet"
DOC = ROOT / "docs" / "route_slope_profiles_ign_mdp05_report.json"
OTP_URL = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
WCS_URL = "https://wcs-pendientes.idee.es/pendientes"
DATE = "2026-09-03"
TIME = "12:00"
SAMPLE_SPACING_M = 1_000

CASE_COUNT = int(os.getenv("SLOPE_CASE_COUNT", "20"))
TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
METRIC_TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:25831", always_xy=True)

WALK_QUERY = """
query Walk($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
 plan(from: $from, to: $to, date: $date, time: $time,
      transportModes: [{mode: WALK}], numItineraries: 1) {
   itineraries { duration walkDistance legs { legGeometry { points } } }
   routingErrors { code description }
 }
}
"""

def dec_poly(encoded):
    index = lat = lon = 0
    coords: list[tuple[float, float]] = []
    while index < len(encoded):
        decoded = []
        for _ in range(2):
            shift = value = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                value |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            decoded.append(~(value >> 1) if value & 1 else value >> 1)
        lat += decoded[0]
        lon += decoded[1]
        coords.append((lon / 1e5, lat / 1e5))
    return coords

def fetch_walk_geometry(row):
    variables = {
        "from": {"lat": float(row.origin_lat), "lon": float(row.origin_lon)},
        "to": {"lat": float(row.destination_lat), "lon": float(row.destination_lon)},
        "date": DATE,
        "time": TIME,
    }
    response = requests.post(OTP_URL, json={"query": WALK_QUERY, "variables": variables}, timeout=60)
    response.raise_for_status()
    plan = response.json().get("data", {}).get("plan", {})
    itineraries = plan.get("itineraries") or []
    if not itineraries:
        return None
    coords = []
    for leg in itineraries[0]["legs"]:
        # Decodifica la geometria del tramo
        encoded = (leg.get("legGeometry") or {}).get("points")
        if encoded:
            coords.extend(dec_poly(encoded))
    return coords or None

def sample_line(coords):
    # Proyecta y muestrea la linea
    projected = [Point(*METRIC_TRANSFORMER.transform(lon, lat)) for lon, lat in coords]
    line = LineString(projected)
    count = max(2, int(line.length // SAMPLE_SPACING_M) + 1)
    return [line.interpolate(distance) for distance in np.linspace(0, line.length, count)]

def slope_at_point(point_25831):
    # Convierte coordenadas al sistema WCS

    lon, lat = Transformer.from_crs("EPSG:25831", "EPSG:4326", always_xy=True).transform(point_25831.x, point_25831.y)
    x, y = TRANSFORMER.transform(lon, lat)
    params = {

        "service": "WCS", "version": "1.0.0", "request": "GetCoverage", "coverage": "mdp05",
        "crs": "EPSG:25830", "bbox": f"{x - 2.5},{y - 2.5},{x + 2.5},{y + 2.5}",
        "width": 2, "height": 2, "format": "GEOTIFFINT16",
    }
    try:
        response = requests.get(WCS_URL, params=params, timeout=45)
        response.raise_for_status()
    except requests.RequestException:
        return None
    if not response.content.startswith((b"II*", b"MM\x00*")):
        return None
    try:
        with MemoryFile(response.content) as memory_file:
            with memory_file.open() as dataset:
                # Lee los valores del raster
                values = dataset.read(1, masked=True).compressed().astype(float)
    except Exception:
        return None
    valid = values[(values >= 0) & (values < 90)]
    return float(np.median(valid)) if len(valid) else None

def classify_slope(mean_slope, p95_slope):
    if mean_slope is None or p95_slope is None:
        return "sin_dato"
    if p95_slope <= 3:
        return "baja_0_3_grados"
    if p95_slope <= 6:
        return "moderada_3_6_grados"
    return "exigente_mas_6_grados"

def main_build_route_slope_profiles():
    parser = argparse.ArgumentParser(description="Construye perfiles de pendiente IGN/CNIG para la muestra histórica priorizada.")
    parser.add_argument("--execute", action="store_true", help="Autoriza consultas OTP y WCS IGN/CNIG y la publicación del resultado.")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({
            "status": "dry_run",
            "cases": CASE_COUNT,
            "date": DATE,
            "time": TIME,
            "message": "No se han consultado rutas ni pendiente. Añade --execute para ejecutar la campaña.",
        }, ensure_ascii=False, indent=2))
        return
    priorities = pd.read_parquet(PRIORITIES)
    sensitivity = pd.read_parquet(SENSITIVITY)
    priorities = priorities.merge(sensitivity[["od_id", "robust_priority"]], on="od_id", how="left", validate="one_to_one")
    cases = priorities.sort_values("priority_index_score", ascending=False).head(CASE_COUNT)
    records = []
    for index, row in cases.reset_index(drop=True).iterrows():
        # Recorre cada caso priorizado
        print("%s/%s — pendiente de %s" % (index + 1, len(cases), row.od_id), flush=True)
        try:
            coords = fetch_walk_geometry(row)
        except requests.RequestException:
            coords = None
        if not coords or len(coords) < 2:
            records.append({"od_id": row.od_id, "r_stat": "no_walk_route", "samples_requested": 0, "samples_valid": 0, "slope_difficulty": "sin_dato"})
            continue
        sample_points = sample_line(coords)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            # Calcula la pendiente en paralelo
            values = list(pool.map(slope_at_point, sample_points))
        valid = [value for value in values if value is not None]
        mean = float(np.mean(valid)) if valid else None
        p95 = float(np.percentile(valid, 95)) if valid else None
        records.append({
            "od_id": row.od_id, "origin_name": row.origin_name, "destination_name": row.destination_name,
            "r_stat": "ok", "samples_requested": len(values), "samples_valid": len(valid),
            "mean_slope_degrees": mean, "p95_slope_degrees": p95,
            "max_slope_degrees": float(max(valid)) if valid else None,
            "slope_difficulty": classify_slope(mean, p95),
        })
    result = pd.DataFrame(records)
    result.to_parquet(OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "IGN/CNIG MDP05, WCS abierto, CC-BY 4.0 scne.es; valor en grados sexagesimales.",
        "method": "Geometría WALK de OTP; se ordenan los casos por prioridad y se toman hasta 20. Muestreo cada 1.000 m y consulta WCS de una celda de pendiente de 5 m.",
        "date": DATE, "time": TIME, "sample_spacing_m": SAMPLE_SPACING_M,
        "cases": int(len(result)), "routes_with_slope": int(result.get("samples_valid", pd.Series()).gt(0).sum()),
        "profiles": json.loads(result[[column for column in ["od_id", "samples_valid", "mean_slope_degrees", "p95_slope_degrees", "max_slope_degrees", "slope_difficulty"] if column in result.columns]].to_json(orient="records")),
        "limitations": [
            "La pendiente no mide anchura de acera, pavimento, cruces, iluminación ni accesibilidad universal.",
            "El muestreo discreto no sustituye una auditoría de cada tramo ni observación en campo.",
        ],
    }
    DOC.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Perfiles de pendiente: {OUT}")
    print(f"OK Informe: {DOC}")

"""Recomienda modo sostenible con reglas explicables sobre rutas OTP reales."""

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
ROUTES = CURATED / "od_multimodal_routes.parquet"
BIKE = CURATED / "otp_bicycle_route_validation.parquet"
PROFILES = CURATED / "route_osm_infrastructure_profiles.parquet"
OUT = CURATED / "od_sustainable_route_recommendations.parquet"
REPORT = ROOT / "docs" / "sustainable_route_recommendations_report.json"

def choose_mode(row):
    # Extrae duraciones de cada modo
    walk = row.get("walk_only_duration_min")
    transit = row.get("transit_duration_min")
    bike = row.get("bike_duration_min")
    if pd.notna(walk) and walk <= 20:
        return "walk", "Caminar es una alternativa directa de hasta 20 minutos en la consulta OTP."
    bike_context = row.get("bike_active_infrastructure_context_score")
    if pd.notna(bike) and bike <= 30 and (pd.isna(transit) or bike <= transit + 10) and (pd.isna(bike_context) or bike_context >= 25):
        return "bicycle", "La bicicleta es viable en hasta 30 minutos, no penaliza más de 10 minutos frente al transporte público y la ruta tiene contexto de movilidad activa OSM documentado."
    if pd.notna(transit):
        if pd.notna(bike) and bike <= 30 and pd.notna(bike_context) and bike_context < 25:
            return "transit", "La bicicleta resuelve en OTP, pero la documentación OSM de infraestructura activa es limitada; se prioriza transporte público y se mantiene la bicicleta para revisión de campo."
        return "transit", "El transporte público es la alternativa motorizada de menor emisión disponible en la consulta OTP."
    if pd.notna(bike):
        if pd.notna(bike_context) and bike_context < 25:
            return "bicycle_review", "OTP resuelve bicicleta, pero la infraestructura activa documentada junto a la ruta es limitada; requiere revisión de campo."
        return "bicycle_review", "OTP resuelve bicicleta, pero el tiempo supera el umbral de confort de 30 minutos; requiere valoración del usuario."
    if pd.notna(walk):
        return "walk_review", "Sólo se resolvió caminata; conviene revisar una conexión sostenible adicional."
    return "connectivity_review", "OTP no resolvió alternativa activa o multimodal; requiere diagnóstico de conectividad."

def main_build_sustainable_route_recommendations():
    # Carga rutas y perfiles activos
    routes = pd.read_parquet(ROUTES)
    bicycle = pd.read_parquet(BIKE).rename(columns={"duration_min": "bike_duration_min", "distance_m": "bike_distance_m"})
    columns = [column for column in ["od_id", "bike_status", "bike_duration_min", "bike_distance_m"] if column in bicycle]
    result = routes.merge(bicycle[columns], on="od_id", how="left", validate="one_to_one")
    profiles = pd.read_parquet(PROFILES)
    bike_profiles = profiles.loc[profiles["mode"].eq("BICYCLE"), ["od_id", "active_infrastructure_context_score", "near_documented_cycle_infrastructure_pct", "near_documented_pedestrian_infrastructure_pct"]].rename(columns={
        "active_infrastructure_context_score": "bike_active_infrastructure_context_score",
        "near_documented_cycle_infrastructure_pct": "bike_near_cycle_infrastructure_pct",
        "near_documented_pedestrian_infrastructure_pct": "bike_near_pedestrian_infrastructure_pct",
    })
    result = result.merge(bike_profiles, on="od_id", how="left", validate="one_to_one")
    choices = result.apply(choose_mode, axis=1, result_type="expand")
    result["recommended_sustainable_mode"] = choices[0]
    result["recommendation_rule"] = choices[1]
    result["recommendation_label"] = result["recommended_sustainable_mode"].map({"walk": "Caminar", "bicycle": "Bicicleta", "transit": "Transporte público", "bicycle_review": "Bicicleta: revisar confort", "walk_review": "Caminata: revisar conexión", "connectivity_review": "Revisar conectividad"})
    result["decision_scope"] = "recomendación de modo; incorpora duración OTP y contexto OSM de movilidad activa, pero no certifica seguridad, ciclabilidad, accesibilidad universal ni disponibilidad de bicicleta"
    result.to_parquet(OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Reglas deterministas sobre duración de rutas OTP WALK, TRANSIT y BICYCLE, y contexto de infraestructura activa documentada en OSM; no se entrena un modelo predictivo.",
        "criteria": {"walk": "duración a pie <=20 min", "bicycle": "duración bicicleta <=30 min, no más de 10 min sobre tránsito y puntuación de contexto activo OSM >=25/100", "transit": "se selecciona si bicicleta no cumple el criterio y existe tránsito"},
        "cases": int(len(result)), "mode_distribution": result["recommendation_label"].value_counts().to_dict(),
        "limitations": ["La bicicleta en OTP modela red OSM; el contexto activo OSM no confirma carril segregado, tráfico, aparcamiento ni bicicleta disponible.", "Las reglas son explícitas y modificables, no preferencias observadas de visitantes.", "No incorpora sentimiento ni seguridad percibida."],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Recomendaciones sostenibles: {len(result)} casos")

"""Construye indicadores reproducibles de movilidad activa desde OpenStreetMap.

No convierte etiquetas OSM incompletas en una auditoría de seguridad. Las capas
resultantes miden *evidencia cartográfica disponible* y proximidad geométrica.
"""

ROOT = Path(__file__).resolve().parents[1]
OSM_DIR = ROOT / "data" / "unified" / "osm"
CURATED = ROOT / "data" / "curated"
TMP = ROOT / "tmp" / "active_mobility"
REPORT = ROOT / "docs" / "active_mobility_osm_report.json"
ACCOMMODATIONS = CURATED / "accommodations_transport_access_baseline.parquet"
DESTINATIONS = CURATED / "tourism_destinations_transport_access_baseline.parquet"
METRIC_CRS = "EPSG:25831"

def osmium_command():
    """Resuelve Osmium en el entorno que el usuario tenga activado."""
    if os.name == "nt":
        conda_bat = Path(sys.prefix).parents[1] / "condabin" / "conda.bat"
        if conda_bat.exists():
            return [str(conda_bat), "run", "--no-capture-output", "-p", sys.prefix, "osmium"]
    direct = shutil.which("osmium")
    if direct:
        return [direct]
    raise RuntimeError("No se encontró osmium. Activa el entorno del proyecto o instala osmium-tool desde conda-forge.")

def resolve_pbf():
    """Usa la red derivada del snapshot más reciente cuando está disponible."""
    latest = OSM_DIR / "latest_mallorca_network.json"
    if latest.exists():
        payload = json.loads(latest.read_text(encoding="utf-8"))
        pbf = ROOT / payload["network_file"]
        if pbf.exists() and pbf.stat().st_size > 0:
            return pbf
        raise FileNotFoundError("La red indicada en %s no existe: %s" % (latest, pbf))
    legacy = OSM_DIR / "mallorca_mobility_network.osm.pbf"
    if legacy.exists():
        return legacy
    raise FileNotFoundError("No hay red OSM preparada. Ejecuta scripts/prepare_osm_mobility_network.py.")

def run_osmium(arguments):
    subprocess.run(osmium_command() + arguments, check=True, capture_output=True, text=True)

def extract(source_pbf, name, filters):
    """Extrae vías candidatas y elimina nodos auxiliares que osmium conserva."""
    TMP.mkdir(parents=True, exist_ok=True)
    pbf = TMP / f"{name}.osm.pbf"
    geojson = TMP / f"{name}.geojson"
    run_osmium(["tags-filter", str(source_pbf), *filters, "-o", str(pbf), "--overwrite"])
    run_osmium(["export", str(pbf), "-o", str(geojson), "--overwrite"])

    payload = json.loads(geojson.read_text(encoding="utf-8"))
    layer = gpd.GeoDataFrame.from_features(payload["features"], crs="EPSG:4326")

    return layer.loc[layer.geom.type.isin(["LineString", "MultiLineString", "Polygon", "MultiPolygon"])].copy()

def as_lines(layer):
    """Convierte polígonos de infraestructura a su borde para medir proximidad."""
    result = layer.copy()
    polygon_mask = result.geom.type.isin(["Polygon", "MultiPolygon"])
    result.loc[polygon_mask, "geom"] = result.loc[polygon_mask, "geom"].boundary
    return result.loc[result.geom.notna() & ~result.geom.is_empty].copy()

def first_existing(frame, names):
    for name in names:
        if name in frame.columns:
            return frame[name].astype("string")
    return pd.Series(pd.NA, index=frame.index, dtype="string")

def cycle_evidence(frame):
    # Detecta etiquetas de ciclovia OSM
    value = first_existing(frame, ["cycleway"])
    highway = first_existing(frame, ["highway"])
    left = first_existing(frame, ["cycleway:left"])
    right = first_existing(frame, ["cycleway:right"])
    bicycle = first_existing(frame, ["bicycle"])
    is_no = lambda series: series.str.lower().isin(["no", "none"])
    keep = highway.eq("cycleway") | (value.notna() & ~is_no(value)) | (left.notna() & ~is_no(left)) | (right.notna() & ~is_no(right)) | bicycle.isin(["designated", "yes"])
    result = frame.loc[keep].copy()
    result["cycle_infrastructure_type"] = "ciclovía etiquetada"
    result.loc[first_existing(result, ["highway"]).eq("cycleway"), "cycle_infrastructure_type"] = "vía ciclista dedicada"
    return as_lines(result)

def pedestrian_evidence(frame):
    # Detecta etiquetas peatonales en OSM
    highway = first_existing(frame, ["highway"])
    sidewalk = first_existing(frame, ["sidewalk"])
    foot = first_existing(frame, ["foot"])
    wheelchair = first_existing(frame, ["wheelchair"])
    lit = first_existing(frame, ["lit"])
    ped = (highway.isin(["footway", "ped", "path", "steps"])) | sidewalk.notna() | foot.isin(["designated", "yes"])
    result = frame.loc[ped].copy()
    result["pedestrian_evidence"] = "infraestructura peatonal etiquetada"
    result.loc[first_existing(result, ["wheelchair"]).isin(["yes", "designated"]), "pedestrian_evidence"] = "evidencia OSM de accesibilidad universal"
    result.loc[first_existing(result, ["lit"]).eq("yes"), "pedestrian_evidence"] = "infraestructura peatonal etiquetada e iluminada"
    return as_lines(result)

def distance_table(points, lines, prefix):
    # Calcula distancia a la infraestructura
    if lines.empty:
        raise ValueError(f"No se extrajo infraestructura para {prefix}.")
    left = points.to_crs(METRIC_CRS).copy()
    right = lines.to_crs(METRIC_CRS)[["geom"]].copy()

    index_pairs, distances = right.sindex.nearest(left.geom, return_distance=True)
    left_positions = index_pairs[0]
    nearest = left.iloc[left_positions].copy()
    nearest[f"distance_to_{prefix}_m"] = distances

    nearest = nearest.loc[~nearest.index.duplicated(keep="first")]
    nearest = nearest.reindex(left.index).to_crs(points.crs)
    distance = nearest[f"distance_to_{prefix}_m"]
    nearest[f"{prefix}_access_band"] = pd.cut(
        distance,
        bins=[-1, 400, 800, float("inf")],
        labels=["alta_0_400m", "media_400_800m", "brecha_mas_800m"],
    ).astype("string")
    return nearest

def main_build_active_mobility_layers():
    # Extrae y publica movilidad activa
    pbf = resolve_pbf()

    print("[1/4] Extrayendo candidatos de movilidad activa…", flush=True)
    raw_cycle = extract(pbf, "cycle_candidates", ["w/highway=cycleway", "w/cycleway", "w/cycleway:left", "w/cycleway:right", "w/bicycle=designated"])
    raw_pedestrian = extract(pbf, "pedestrian_candidates", ["w/highway=footway", "w/highway=ped", "w/highway=path", "w/highway=steps", "w/sidewalk", "w/foot=designated", "w/wheelchair"])
    print("[2/4] Clasificando evidencia cartográfica…", flush=True)
    cycleways = cycle_evidence(raw_cycle)
    pedestrians = pedestrian_evidence(raw_pedestrian)
    cycle_file = OSM_DIR / "mallorca_cycling_infrastructure.parquet"
    pedestrian_file = OSM_DIR / "mallorca_pedestrian_infrastructure.parquet"
    cycleways.to_parquet(cycle_file, index=False)
    pedestrians.to_parquet(pedestrian_file, index=False)

    print("[3/4] Calculando proximidad de alojamientos y destinos…", flush=True)
    accs = gpd.read_parquet(ACCOMMODATIONS)
    dests = gpd.read_parquet(DESTINATIONS)
    print("  - proximidad ciclista de alojamientos", flush=True)
    accommodation_cycle = distance_table(accs, cycleways, "cycle_infrastructure")
    print("  - evidencia peatonal de alojamientos", flush=True)
    accommodation_active = distance_table(accommodation_cycle, pedestrians, "pedestrian_infrastructure")
    print("  - proximidad ciclista de destinos", flush=True)
    destination_cycle = distance_table(dests, cycleways, "cycle_infrastructure")
    print("  - evidencia peatonal de destinos", flush=True)
    destination_active = distance_table(destination_cycle, pedestrians, "pedestrian_infrastructure")
    accommodation_active.to_parquet(CURATED / "accommodations_active_mobility_access.parquet", index=False)
    destination_active.to_parquet(CURATED / "tourism_destinations_active_mobility_access.parquet", index=False)

    print("[4/4] Generando artefactos curated y control de calidad…", flush=True)
    report = {
        "scope": "Mallorca; red OSM contenida en %s" % (pbf.relative_to(ROOT)),
        "method": "Extracción OSM con Osmium y proximidad geométrica en EPSG:25831.",
        "cycling_features": int(len(cycleways)),
        "pedestrian_features": int(len(pedestrians)),
        "accommodations_evaluated": int(len(accommodation_active)),
        "destinations_evaluated": int(len(destination_active)),
        "accommodation_cycle_access": accommodation_active["cycle_infrastructure_access_band"].value_counts(dropna=False).to_dict(),
        "limitations": [
            "La ausencia de etiqueta OSM no prueba ausencia de infraestructura.",
            "La proximidad a infraestructura ciclista no certifica continuidad, seguridad ni ciclabilidad.",
            "La evidencia peatonal es documental y no una auditoría de accesibilidad universal ni de seguridad vial.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Ciclovías/infraestructura ciclista: {len(cycleways):,}")
    print(f"✓ Infraestructura peatonal con evidencia OSM: {len(pedestrians):,}")
    print(f"✓ Alojamientos con métricas activas: {len(accommodation_active):,}")
    print(f"✓ Informe: {REPORT}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    args = parser.parse_args()
    
    if args.task == "build_multimodal_route_sample":
        main_build_multimodal_route_sample()
    elif args.task == "build_otp_walk_isochrones":
        main_build_otp_walk_isochrones()
    elif args.task == "build_route_infrastructure_profiles":
        main_build_route_infrastructure_profiles()
    elif args.task == "build_route_slope_profiles":
        main_build_route_slope_profiles()
    elif args.task == "build_sustainable_route_recommendations":
        main_build_sustainable_route_recommendations()
    elif args.task == "build_active_mobility_layers":
        main_build_active_mobility_layers()

