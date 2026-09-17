from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
OUT = CURATED / "accommodations_tourism_sustainable_mobility_index_v3.parquet"
REPORT = ROOT / "docs" / "accommodation_tourism_sustainable_mobility_index_v3_report.json"

def inverse_distance_score(values, threshold_m):
    # Convierte distancia en puntuacion inversa
    numeric = pd.to_numeric(values, errors="coerce")
    return (1 - numeric.clip(lower=0, upper=threshold_m) / threshold_m).where(numeric.notna())


def main_accommodation_accessibility_index_v3():
    # Carga capas base del alojamiento
    baseline = pd.read_parquet(CURATED / "accommodations_transport_access_baseline.parquet")
    active = pd.read_parquet(CURATED / "accommodations_active_mobility_access.parquet")
    tourism = pd.read_parquet(CURATED / "accommodations_tourism_proximity.parquet")
    universal = pd.read_parquet(CURATED / "accommodations_documented_accessibility_evidence.parquet")
    required = {"accommodation_id", "commercial_name", "municipality_raw", "distance_to_nearest_stop_euclidean_m"}
    missing = required.difference(baseline.columns)
    if missing:
        raise ValueError(f"Contrato incumplido en línea base: {sorted(missing)}")

    data = (
        baseline[["accommodation_id", "commercial_name", "municipality_raw", "group_raw", "subgroup_raw", "places", "distance_to_nearest_stop_euclidean_m"]]
        .merge(active[["accommodation_id", "distance_to_cycle_infrastructure_m", "distance_to_pedestrian_infrastructure_m"]], on="accommodation_id", how="left", validate="one_to_one")
        .merge(tourism[["accommodation_id", "distance_to_nearest_tourism_destination_m"]], on="accommodation_id", how="left", validate="one_to_one")
        .merge(universal[["accommodation_id", "osm_evidence_within_400m", "gtfs_wheelchair_stop_within_800m"]], on="accommodation_id", how="left", validate="one_to_one")
    )
    data["public_transport_proximity_score"] = inverse_distance_score(data["distance_to_nearest_stop_euclidean_m"], 1200)
    data["cycling_proximity_score"] = inverse_distance_score(data["distance_to_cycle_infrastructure_m"], 800)
    data["pedestrian_evidence_score"] = inverse_distance_score(data["distance_to_pedestrian_infrastructure_m"], 800)
    data["tourism_proximity_score"] = inverse_distance_score(data["distance_to_nearest_tourism_destination_m"], 3000)
    data["documented_accessibility_evidence_score"] = (
        0.7 * data["osm_evidence_within_400m"].fillna(False).astype(float)
        + 0.3 * data["gtfs_wheelchair_stop_within_800m"].fillna(False).astype(float)
    )
    weights = {
        "public_transport_proximity_score": 0.34,
        "cycling_proximity_score": 0.22,
        "pedestrian_evidence_score": 0.20,
        "tourism_proximity_score": 0.18,
        "documented_accessibility_evidence_score": 0.06,
    }
    available_columns = list(weights)
    data["evidence_coverage_pct"] = 100 * data[available_columns].notna().mean(axis=1)

    weighted_values = sum(data[column].fillna(0) * weight for column, weight in weights.items())
    available_weight = sum(data[column].notna().astype(float) * weight for column, weight in weights.items())
    data["tsmai_v3_accommodation_score"] = (weighted_values / available_weight.where(available_weight.gt(0))).round(3)
    data["tsmai_v3_accommodation_level"] = pd.cut(
        data["tsmai_v3_accommodation_score"],
        bins=[-0.01, 0.40, 0.67, 1.01],
        labels=["prioridad de mejora", "intermedio", "favorable"],
    ).astype("string")
    data["index_version"] = "TSMAI-v3-accommodation"
    data["interpretation_scope"] = "cribado individual basado en proximidad y evidencia documental; no es tiempo de red ni certificación"
    data.to_parquet(OUT, index=False)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "name": "Tourism Sustainable Mobility and Accessibility idx v3 Accommodation",
        "unit_of_analysis": "alojamiento turístico con geometría validada",
        "records": int(len(data)),
        "weights": weights,
        "missing_data_rule": "Un dato ausente se excluye del denominador de ese alojamiento y evidence_coverage_pct permite detectarlo; no se convierte en una barrera física.",
        "limitations": [
            "Las distancias de entrada son euclídeas a la infraestructura o POI más próximo, no recorridos sobre red.",
            "La evidencia OSM y GTFS es documental y no acredita una ruta universalmente accesible.",
            "No incluye sentimiento, seguridad percibida, tráfico, pendiente de cada trayecto ni demanda observada.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK TSMAI v3 individual: {len(data):,} alojamientos")






import hashlib
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
UNIFIED = ROOT / "data" / "unified"
OSM = UNIFIED / "osm"
GTFS = UNIFIED / "gtfs"
TSMAI_V9 = CURATED / "accommodations_tsmai_v9_seasonal_transit.parquet"
GTFS_LATEST = GTFS / "latest_tib_gtfs.json"
OSM_LATEST = OSM / "latest_mallorca_network.json"
ACCOMMODATIONS_OUT = CURATED / "dashboard_current_accommodations_tsmai_v9.parquet"
STOPS_OUT = CURATED / "dashboard_current_tib_gtfs_stops.parquet"
DESTINATIONS_OUT = CURATED / "dashboard_current_tourism_destinations_osm.parquet"
CYCLING_OUT = CURATED / "dashboard_current_cycling_evidence_osm.parquet"
LATEST = CURATED / "latest_dashboard_current_layers.json"
REPORT = ROOT / "docs" / "dashboard_current_layers_report.json"

BAND_ORDER = ["alta_0_400m", "media_400_800m", "baja_800_1200m", "brecha_mas_1200m"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_parquet(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def atomic_json(payload, path):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def destination_theme(category):
    # Clasifica el destino por tema
    value = str(category)
    if value in {"natural:beach", "man_made:lighthouse"}:
        return "coastal"
    if value.startswith("natural:") or value == "leisure:nature_reserve":
        return "nature"
    if value.startswith("historic:") or value in {"tourism:museum", "tourism:gallery", "tourism:artwork"}:
        return "cultural"
    if value.startswith("leisure:"):
        return "leisure"
    return "tourism"


def access_band(distance_m):
    return pd.cut(
        pd.to_numeric(distance_m, errors="coerce"),
        bins=[-float("inf"), 400, 800, 1200, float("inf")],
        labels=BAND_ORDER,
        include_lowest=True,
    ).astype("string")


def read_metadata(path):
    if not path.is_file():
        raise FileNotFoundError(f"Falta el manifiesto versionado: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_output(metadata, key):
    try:
        path = ROOT / metadata[key]
    except KeyError as exc:
        raise ValueError(f"El manifiesto no contiene '{key}'.") from exc
    if not path.is_file():
        raise FileNotFoundError(f"La capa declarada no existe: {path.relative_to(ROOT)}")
    return path


def main_current_dashboard_layers():
    # Verifica insumos y publica capas
    required = [TSMAI_V9, GTFS_LATEST, OSM_LATEST]
    if missing := [str(path.relative_to(ROOT)) for path in required if not path.is_file()]:
        raise FileNotFoundError(f"Faltan insumos actuales P7: {missing}")
    gtfs_metadata = read_metadata(GTFS_LATEST)
    osm_metadata = read_metadata(OSM_LATEST)
    stops_source = resolve_output(gtfs_metadata, "stops_output")
    source_run_id = osm_metadata["source_run_id"]
    destinations_source = OSM / f"mallorca_tourism_destinations_{source_run_id}.geojson"
    cycling_source = OSM / f"mallorca_cycling_evidence_{source_run_id}.parquet"
    if not destinations_source.is_file():
        raise FileNotFoundError(
            "No existe la capa de destinos OSM para la red declarada: "
            f"{destinations_source.relative_to(ROOT)}"
        )
    if not cycling_source.is_file():
        raise FileNotFoundError(
            "No existe la capa ciclista OSM para la red declarada: "
            f"{cycling_source.relative_to(ROOT)}"
        )

    accs = gpd.read_parquet(TSMAI_V9).copy()
    accommodations_geometry = accs.geometry.name
    required_accommodations = {
        "accommodation_id", "commercial_name", "municipality", "group", "subgroup", accommodations_geometry,
        "nearest_tib_stop_name", "distance_to_nearest_tib_stop_m", "tsmai_v9_score", "tsmai_v9_level",
        "evidence_coverage_pct",
    }
    if missing := required_accommodations.difference(accs.columns):
        raise ValueError(f"TSMAI V9 no contiene los campos de mapa requeridos: {sorted(missing)}")
    if accs["accommodation_id"].isna().any() or accs["accommodation_id"].duplicated().any():
        raise ValueError("La capa actual de alojamientos debe tener accommodation_id único y no nulo.")
    if accs.geometry.isna().any() or accs.geometry.is_empty.any():
        raise ValueError("La capa actual de alojamientos contiene geometrías inválidas.")
    accs["municipality_raw"] = accs["municipality"]
    accs["group_raw"] = accs["group"]
    accs["subgroup_raw"] = accs["subgroup"]
    accs["stop_name"] = accs["nearest_tib_stop_name"]
    accs["distance_to_nearest_stop_euclidean_m"] = pd.to_numeric(
        accs["distance_to_nearest_tib_stop_m"], errors="coerce"
    )
    accs["walk_access_band_euclidean"] = access_band(accs["distance_to_nearest_stop_euclidean_m"])
    if accs["walk_access_band_euclidean"].isna().any():
        raise ValueError("No se pudo clasificar la distancia a parada de todos los alojamientos actuales.")
    accs["map_data_contract"] = "TSMAI-v9 + GTFS TIB versionado"
    accs["tsmai_v4_evidence_coverage_pct"] = accs["evidence_coverage_pct"]

    stops = gpd.read_file(stops_source)
    stops_geometry = stops.geometry.name
    required_stops = {"stop_id", "stop_name", "location_type", stops_geometry}
    if missing := required_stops.difference(stops.columns):
        raise ValueError(f"GTFS actual no contiene: {sorted(missing)}")
    location_type = stops["location_type"].fillna("0").astype("string").str.strip()
    stops = stops.loc[location_type.isin(["0", ""])].copy()
    if stops.geometry.isna().any() or stops.geometry.is_empty.any():
        raise ValueError("Las paradas GTFS actuales contienen geometrías inválidas.")
    stops["map_data_contract"] = f"GTFS TIB {gtfs_metadata['source_run_id']}"

    dests = gpd.read_file(destinations_source)
    destinations_geometry = dests.geometry.name
    required_destinations = {"poi_id", "name", "destination_category", destinations_geometry}
    if missing := required_destinations.difference(dests.columns):
        raise ValueError(f"Destinos OSM actuales no contienen: {sorted(missing)}")
    if dests["poi_id"].isna().any() or dests["poi_id"].duplicated().any():
        raise ValueError("Los destinos OSM actuales deben tener poi_id único y no nulo.")
    if dests.geometry.isna().any() or dests.geometry.is_empty.any():
        raise ValueError("Los destinos OSM actuales contienen geometrías inválidas.")
    dests["destination_theme"] = dests["destination_category"].map(destination_theme)
    dests["map_data_contract"] = f"OSM mobility network {source_run_id}"

    cycling = gpd.read_parquet(cycling_source)
    if cycling.empty:
        raise ValueError("La evidencia ciclista OSM actual no contiene geometrías publicables.")
    cycling = cycling.loc[cycling.geometry.notna() & ~cycling.geometry.is_empty].copy()
    cycling["map_data_contract"] = f"OSM mobility network {source_run_id}"

    atomic_parquet(accs, ACCOMMODATIONS_OUT)
    atomic_parquet(stops, STOPS_OUT)
    atomic_parquet(dests, DESTINATIONS_OUT)
    atomic_parquet(cycling, CYCLING_OUT)
    report = {
        "status": "passed",
        "purpose": "Capas actuales del mapa territorial, sin dependencia de la línea base histórica.",
        "inputs": {
            "accommodations_tsmai_v9": str(TSMAI_V9.relative_to(ROOT)),
            "accommodations_tsmai_v9_sha256": sha256(TSMAI_V9),
            "gtfs_manifest": str(GTFS_LATEST.relative_to(ROOT)),
            "gtfs_source_run_id": gtfs_metadata["source_run_id"],
            "gtfs_stops": str(stops_source.relative_to(ROOT)),
            "gtfs_stops_sha256": sha256(stops_source),
            "osm_manifest": str(OSM_LATEST.relative_to(ROOT)),
            "osm_source_run_id": source_run_id,
            "destinations_osm": str(destinations_source.relative_to(ROOT)),
            "destinations_osm_sha256": sha256(destinations_source),
            "cycling_osm": str(cycling_source.relative_to(ROOT)),
            "cycling_osm_sha256": sha256(cycling_source),
        },
        "outputs": {
            "accommodations": str(ACCOMMODATIONS_OUT.relative_to(ROOT)),
            "stops": str(STOPS_OUT.relative_to(ROOT)),
            "destinations": str(DESTINATIONS_OUT.relative_to(ROOT)),
            "cycling": str(CYCLING_OUT.relative_to(ROOT)),
        },
        "counts": {
            "accommodations": int(len(accs)),
            "stops": int(len(stops)),
            "destinations": int(len(dests)),
            "cycling_evidence": int(len(cycling)),
            "destination_themes": dests["destination_theme"].value_counts().to_dict(),
            "accommodation_access_bands": accs["walk_access_band_euclidean"].value_counts().to_dict(),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La distancia a parada sigue siendo euclídea y no equivale a un itinerario a pie por red.",
            "Los destinos OSM son POI representativos; no garantizan entrada física, horario o accesibilidad universal.",
            "Las capas sustituyen la línea base del mapa, pero no convierten los casos OD históricos en resultados TSMAI V9.",
        ],
    }
    atomic_json(report, LATEST)
    atomic_json(report, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))



import argparse
import concurrent.futures
import os
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
RAW = ROOT / "data" / "raw" / "current_route_documentary_evidence"
LATEST_SAMPLE = CURATED / "latest_multimodal_route_sample.json"
LATEST_ACTIVE = CURATED / "latest_active_mobility_access.json"
LATEST_OUTPUT = CURATED / "latest_current_sample_route_documentary_evidence.json"
REPORT = ROOT / "docs" / "current_sample_route_documentary_evidence_report.json"
OTP_URL = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
METRIC_CRS = "EPSG:25831"

QUERY = """
query CurrentRouteEvidence($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!, $modes: [TransportMode]!) {
  plan(from: $from, to: $to, date: $date, time: $time, transportModes: $modes, numItineraries: 1) {
    itineraries { duration legs { legGeometry { points } } }
    routingErrors { code description }
  }
}
"""


def write_json(path, payload):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def write_parquet(frame, path):
    # Escribe el parquet de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def decode_polyline(encoded):
    idx = latitude = longitude = 0
    points: list[tuple[float, float]] = []
    while idx < len(encoded):
        values = []
        for _ in range(2):
            shift = value = 0
            while True:
                byte = ord(encoded[idx]) - 63
                idx += 1
                value |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(value >> 1) if value & 1 else value >> 1)
        latitude += values[0]
        longitude += values[1]
        points.append((longitude / 1e5, latitude / 1e5))
    return points


def inputs():
    # Carga muestra y evidencia activa
    sample_meta = json.loads(LATEST_SAMPLE.read_text(encoding="utf-8"))
    active_meta = json.loads(LATEST_ACTIVE.read_text(encoding="utf-8"))
    sample_path = ROOT / sample_meta["sample_output"]
    cycling_path = ROOT / active_meta["cycling_evidence"]
    pedestrian_path = ROOT / active_meta["pedestrian_evidence"]
    sample = pd.read_parquet(sample_path).sort_values("od_id", kind="stable").reset_index(drop=True)
    required = {"od_id", "origin_latitude", "origin_longitude", "destination_latitude", "destination_longitude"}
    if missing := required.difference(sample.columns):
        raise ValueError(f"La muestra no contiene: {sorted(missing)}")
    if len(sample) != 12 or sample["od_id"].duplicated().any():
        raise ValueError("P13 requiere los 12 pares únicos de la muestra multimodal actual.")
    return sample, gpd.read_parquet(cycling_path).to_crs(METRIC_CRS), gpd.read_parquet(pedestrian_path).to_crs(METRIC_CRS), {
        "sample": str(sample_path.relative_to(ROOT)),
        "routing_date": sample_meta["routing_date"], "routing_time": sample_meta["routing_time"],
        "cycling_evidence": str(cycling_path.relative_to(ROOT)),
        "pedestrian_evidence": str(pedestrian_path.relative_to(ROOT)),
        "osm_source_run_id": active_meta["source_run_id"],
    }


def plan():
    # Resume la ejecucion en dry-run
    sample, cycling, pedestrian, provenance = inputs()
    return {
        "status": "dry_run", "sample_pairs": int(len(sample)), "route_queries": int(len(sample) * 2),
        "sampling_method": "Puntos cada 100 m de las geometrías OTP; proximidad OSM ≤30 m.",
        "provenance": provenance,
        "cycling_features": int(len(cycling)), "pedestrian_features": int(len(pedestrian)),
        "message": "No se ha consultado OTP ni escrito datos. Añade --execute.",
    }


def request_route(row, mode, routing_date, routing_time, timeout):
    variables = {
        "from": {"lat": float(row.origin_latitude), "lon": float(row.origin_longitude)},
        "to": {"lat": float(row.destination_latitude), "lon": float(row.destination_longitude)},
        "date": routing_date, "time": routing_time, "modes": [{"mode": mode}],
    }
    result = {"od_id": row.od_id, "mode": mode, "route_status": "routing_error", "route_message": None, "duration_min": None, "route_geometry_wkt": None}
    try:
        response = requests.post(OTP_URL, json={"query": QUERY, "variables": variables}, timeout=timeout)
        response.raise_for_status()
        plan_response = response.json().get("data", {}).get("plan", {})
    except requests.RequestException as exc:
        result["route_message"] = type(exc).__name__
        return result
    itineraries = plan_response.get("itineraries") or []
    if not itineraries:
        result.update(route_status="no_route", route_message="; ".join(str(item.get("code")) for item in plan_response.get("routingErrors", [])))
        return result
    points = [point for leg in itineraries[0].get("legs", []) for point in decode_polyline((leg.get("legGeometry") or {}).get("points", ""))]
    if len(points) < 2:
        result.update(route_status="no_geometry")
        return result
    result.update(route_status="ok", duration_min=float(itineraries[0]["duration"]) / 60, route_geometry_wkt=LineString(points).wkt)
    return result


def documented_share(route_wkt, evidence, spacing_m, radius_m):
    # Calcula porcentaje de ruta documentada
    route = gpd.GeoSeries.from_wkt([route_wkt], crs="EPSG:4326").to_crs(METRIC_CRS).iloc[0]
    distances = list(range(0, int(route.length) + 1, spacing_m)) or [0]
    points = gpd.GeoSeries([route.interpolate(distance) for distance in distances], crs=METRIC_CRS)
    matches, near = evidence.sindex.nearest(points, return_distance=True)
    matched = set(matches[0][near <= radius_m])
    return len(points), round(100 * len(matched) / len(points), 1)


def execute(spacing_m, radius_m, workers, timeout):
    sample, cycling, pedestrian, provenance = inputs()
    jobs = [(row, mode, provenance["routing_date"], provenance["routing_time"], timeout) for _, row in sample.iterrows() for mode in ("WALK", "BICYCLE")]
        # Consulta rutas OTP en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        routes = list(pool.map(lambda job: request_route(*job), jobs))
    output = []
    for route in routes:
        # Une cada ruta con origen
        row = sample.loc[sample["od_id"].eq(route["od_id"])].iloc[0].to_dict()
        profile = {**row, **route, "sampling_spacing_m": spacing_m, "proximity_radius_m": radius_m}
        if route["route_status"] == "ok":
            points, cycle_share = documented_share(route["route_geometry_wkt"], cycling, spacing_m, radius_m)
            _, pedestrian_share = documented_share(route["route_geometry_wkt"], pedestrian, spacing_m, radius_m)
            profile.update(sample_points=points, near_documented_cycle_infrastructure_pct=cycle_share, near_documented_pedestrian_infrastructure_pct=pedestrian_share)
        else:
            profile.update(sample_points=0, near_documented_cycle_infrastructure_pct=None, near_documented_pedestrian_infrastructure_pct=None)
        output.append(profile)
    result = pd.DataFrame(output)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = RAW / run_id
    raw_routes = raw_dir / "otp_route_geometries.parquet"
    profile_path = CURATED / f"current_sample_route_documentary_evidence_{run_id}.parquet"
    write_parquet(result[["od_id", "mode", "route_status", "route_message", "duration_min", "route_geometry_wkt"]], raw_routes)
    write_parquet(result.drop(columns=["route_geometry_wkt"]), profile_path)
    report = {
        "status": "passed" if result["route_status"].eq("ok").all() else "partial",
        "run_id": run_id, "sample_pairs": int(len(sample)), "route_profiles": int(len(result)),
        "route_status_counts": result["route_status"].value_counts().to_dict(), "provenance": provenance,
        "profile_output": str(profile_path.relative_to(ROOT)), "raw_routes": str(raw_routes.relative_to(ROOT)),
        "method": f"Puntos cada {spacing_m} m de rutas OTP; proximidad ≤{radius_m} m a evidencia OSM.",
        "limitations": [
            "Mide documentación OSM próxima a la geometría, no seguridad vial, continuidad física, iluminación, tráfico ni siniestralidad.",
            "La ausencia de etiqueta OSM no demuestra ausencia de infraestructura.",
            "No es una auditoría de campo ni una certificación de accesibilidad universal.",
        ], "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(raw_dir / "manifest.json", report)
    write_json(LATEST_OUTPUT, report)
    write_json(REPORT, report)
    return report


def main_current_sample_route_documentary_evidence():
    # Define los argumentos del comando
    parser = argparse.ArgumentParser(description="Construye evidencia documental OSM para las rutas actuales de muestra.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--spacing-m", type=int, default=100)
    parser.add_argument("--radius-m", type=int, default=30)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    if min(args.spacing_m, args.radius_m, args.workers, args.timeout) < 1:
        parser.error("Los parámetros numéricos deben ser positivos.")
    report = execute(args.spacing_m, args.radius_m, args.workers, args.timeout) if args.execute else plan()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    try:
        print(rendered)
    except UnicodeEncodeError:
        print(json.dumps(report, ensure_ascii=True, indent=2))




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_accommodation_accessibility_index_v3":
        main_accommodation_accessibility_index_v3()
        sys.exit(0)
    if task_name == "run_build_current_dashboard_layers":
        main_current_dashboard_layers()
        sys.exit(0)
    if task_name == "run_build_current_sample_route_documentary_evidence":
        main_current_sample_route_documentary_evidence()
        sys.exit(0)
    print(f"Task {task_name} not found.")

