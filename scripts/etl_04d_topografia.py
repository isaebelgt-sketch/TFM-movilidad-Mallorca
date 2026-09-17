from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
if _gdal_data.exists():
    os.environ.setdefault("GDAL_DATA", str(_gdal_data))

import numpy as np
import pandas as pd
import requests
from pyproj import Transformer
from rasterio.io import MemoryFile
from shapely.geometry import LineString, Point


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
RAW = ROOT / "data" / "raw" / "ign_cnig_mdp05"
DOCS = ROOT / "docs"
LATEST_SAMPLE = CURATED / "latest_multimodal_route_sample.json"
LATEST_OUTPUT = CURATED / "latest_current_sample_slope_profiles.json"
REPORT = DOCS / "current_sample_slope_profiles_ign_mdp05_report.json"
OTP_URL = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
WCS_URL = "https://wcs-pendientes.idee.es/pendientes"
METRIC_TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:25831", always_xy=True)
WCS_TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
TO_WGS84 = Transformer.from_crs("EPSG:25831", "EPSG:4326", always_xy=True)

WALK_QUERY = """
query CurrentSampleWalk($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: [{mode: WALK}], numItineraries: 1) {
    itineraries { duration walkDistance legs { legGeometry { points } } }
    routingErrors { code description }
  }
}
"""


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, payload):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def atomic_parquet(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def decode_polyline(encoded):
    # Decodifica la geometria codificada OTP
    idx = latitude = longitude = 0
    coords: list[tuple[float, float]] = []
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
        coords.append((longitude / 1e5, latitude / 1e5))
    return coords


def classify_slope(mean_slope, p95_slope):
    if mean_slope is None or p95_slope is None:
        return "sin_dato"
    if p95_slope <= 3:
        return "baja_0_3_grados"
    if p95_slope <= 6:
        return "moderada_3_6_grados"
    return "exigente_mas_6_grados"


def load_sample():
    if not LATEST_SAMPLE.exists():
        raise FileNotFoundError("Falta data/curated/latest_multimodal_route_sample.json. Ejecuta primero la muestra multimodal.")
    metadata = json.loads(LATEST_SAMPLE.read_text(encoding="utf-8"))
    sample_path = ROOT / metadata["sample_output"]
    sample = pd.read_parquet(sample_path)
    required = {
        "od_id", "origin_accommodation_id", "origin_name", "origin_municipality",
        "origin_tib_access_band", "origin_latitude", "origin_longitude",
        "destination_poi_id", "destination_name", "destination_category",
        "destination_theme", "destination_latitude", "destination_longitude",
    }
    missing = required.difference(sample.columns)
    if missing:
        raise ValueError(f"La muestra multimodal no contiene los campos requeridos: {sorted(missing)}")
    if sample.empty or sample["od_id"].duplicated().any():
        raise ValueError("La muestra multimodal debe contener pares no vacíos y únicos.")
    if not {"routing_date", "routing_time"}.issubset(metadata):
        raise ValueError("El manifiesto de la muestra no documenta fecha y hora de enrutamiento.")
    return sample.sort_values("od_id", kind="stable").reset_index(drop=True), metadata, sample_path


def plan():
    sample, metadata, sample_path = load_sample()
    return {
        "status": "dry_run",
        "purpose": "Perfilar pendiente sobre los pares actuales y reales de la muestra multimodal OTP.",
        "sample_pairs": int(len(sample)),
        "sample_output": str(sample_path.relative_to(ROOT)),
        "sample_sha256": sha256(sample_path),
        "routing_date": metadata["routing_date"],
        "routing_time": metadata["routing_time"],
        "sampling_rule": metadata.get("sampling_rule"),
        "source": "IGN/CNIG MDP05 mediante WCS; pendiente observada en grados.",
        "next_action": "Añade --execute con OTP activo para consultar geometrías WALK y el WCS de IGN/CNIG.",
        "limitations": [
            "La muestra de 12 pares es estratificada, no representa demanda ni todos los desplazamientos turísticos.",
            "La pendiente no mide anchura, pavimento, cruces, iluminación, continuidad ni accesibilidad universal.",
        ],
    }


def fetch_walk_geometry(row, routing_date, routing_time, timeout):
    # Consulta la ruta a pie
    variables = {
        "from": {"lat": float(row.origin_latitude), "lon": float(row.origin_longitude)},
        "to": {"lat": float(row.destination_latitude), "lon": float(row.destination_longitude)},
        "date": routing_date,
        "time": routing_time,
    }
    response = requests.post(OTP_URL, json={"query": WALK_QUERY, "variables": variables}, timeout=timeout)
    response.raise_for_status()
    plan_response = response.json().get("data", {}).get("plan", {})
    itineraries = plan_response.get("itineraries") or []
    if not itineraries:
        errors = plan_response.get("routingErrors") or []
        message = "; ".join(str(error.get("description") or error.get("code")) for error in errors) or "OTP no devolvió itinerario WALK"
        return None, message
    coords: list[tuple[float, float]] = []
    for leg in itineraries[0].get("legs", []):
        encoded = (leg.get("legGeometry") or {}).get("points")
        if encoded:
            coords.extend(decode_polyline(encoded))
    return (coords if len(coords) >= 2 else None), None


def sample_line(coords, spacing_m):
    projected = [Point(*METRIC_TRANSFORMER.transform(lon, lat)) for lon, lat in coords]
    line = LineString(projected)
    count = max(2, int(line.length // spacing_m) + 1)
    return [line.interpolate(distance) for distance in np.linspace(0, line.length, count)]


def query_wcs(payload):
    od_id, sample_index, point, timeout = payload
    longitude, latitude = TO_WGS84.transform(point.x, point.y)
    x, y = WCS_TRANSFORMER.transform(longitude, latitude)
    params = {
        "service": "WCS", "version": "1.0.0", "request": "GetCoverage", "coverage": "mdp05",
        "crs": "EPSG:25830", "bbox": f"{x - 2.5},{y - 2.5},{x + 2.5},{y + 2.5}",
        "width": 2, "height": 2, "format": "GEOTIFFINT16",
    }
    result = {
        "od_id": od_id,
        "sample_index": sample_index,
        "longitude": longitude,
        "latitude": latitude,
        "wcs_x_25830": x,
        "wcs_y_25830": y,
        "query_status": "unknown",
        "slope_degrees": None,
        "http_status": None,
        "error": None,
    }
    try:
        response = requests.get(WCS_URL, params=params, timeout=timeout)
        result["http_status"] = response.status_code
        response.raise_for_status()
    except requests.RequestException as exc:
        result.update(
            query_status="http_error",
            error=type(exc).__name__,
            error_detail=str(exc)[:300],
        )
        return result
    if not response.content.startswith((b"II*", b"MM\x00*")):
        result.update(query_status="unexpected_content", error="WCS_no_devolvio_GeoTIFF")
        return result
    try:
        with MemoryFile(response.content) as memory_file:
            with memory_file.open() as dataset:
                values = dataset.read(1, masked=True).compressed().astype(float)
    except Exception as exc:
        result.update(query_status="invalid_raster", error=type(exc).__name__)
        return result
    valid = values[(values >= 0) & (values < 90)]
    if not len(valid):
        result.update(query_status="no_valid_value", error="sin_valor_mdp05")
        return result
    result.update(query_status="ok", slope_degrees=float(np.median(valid)))
    return result


def execute(spacing_m, workers, timeout):
    sample, metadata, sample_path = load_sample()
    routing_date, routing_time = metadata["routing_date"], metadata["routing_time"]
    profiles = []
    raw_routes = []
    raw_wcs = []
    for position, (_, row) in enumerate(sample.iterrows(), start=1):
        print(f"{position}/{len(sample)} — pendiente actual de {row.od_id}", flush=True)
        try:
            coords, route_message = fetch_walk_geometry(row, routing_date, routing_time, timeout)
        except requests.RequestException as exc:
            coords, route_message = None, f"OTP_{type(exc).__name__}"
        route_record = {
            "od_id": row.od_id,
            "routing_date": routing_date,
            "routing_time": routing_time,
            "route_status": "ok" if coords else "no_walk_route",
            "route_message": route_message,
            "route_geometry_wkt": LineString(coords).wkt if coords else None,
        }
        raw_routes.append(route_record)
        profile = {
            **row.to_dict(),
            "routing_date": routing_date,
            "routing_time": routing_time,
            "route_status": route_record["route_status"],
            "samples_requested": 0,
            "samples_valid": 0,
            "mean_slope_degrees": None,
            "p95_slope_degrees": None,
            "max_slope_degrees": None,
            "slope_difficulty": "sin_dato",
        }
        if coords:
            sample_points = sample_line(coords, spacing_m)
            payloads = [(str(row.od_id), idx, point, timeout) for idx, point in enumerate(sample_points)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                evidence = list(pool.map(query_wcs, payloads))
            raw_wcs.extend(evidence)
            values = [item["slope_degrees"] for item in evidence if item["slope_degrees"] is not None]
                # Calcula estadisticos de pendiente validos
            profile.update(
                samples_requested=len(evidence),
                samples_valid=len(values),
                mean_slope_degrees=float(np.mean(values)) if values else None,
                p95_slope_degrees=float(np.percentile(values, 95)) if values else None,
                max_slope_degrees=float(max(values)) if values else None,
            )
            profile["slope_difficulty"] = classify_slope(profile["mean_slope_degrees"], profile["p95_slope_degrees"])
        profiles.append(profile)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = RAW / run_id
    raw_sample_path = raw_dir / "sample_pairs.parquet"
    raw_routes_path = raw_dir / "otp_walk_responses.parquet"
    raw_wcs_path = raw_dir / "wcs_mdp05_samples.parquet"
    profile_path = CURATED / f"current_sample_slope_profiles_ign_mdp05_{run_id}.parquet"
    result = pd.DataFrame(profiles)
    atomic_parquet(sample, raw_sample_path)
    atomic_parquet(pd.DataFrame(raw_routes), raw_routes_path)
    atomic_parquet(pd.DataFrame(raw_wcs), raw_wcs_path)
    atomic_parquet(result, profile_path)
    manifest = {
        "source_id": "ign_cnig_mdp05",
        "run_id": run_id,
        "source_url": WCS_URL,
        "license": "CC-BY-4.0",
        "attribution": "Obra derivada de MDP05, IGN/CNIG, CC-BY 4.0.",
        "input_sample": str(sample_path.relative_to(ROOT)),
        "input_sample_sha256": sha256(sample_path),
        "raw_outputs": {
            "sample_pairs": str(raw_sample_path.relative_to(ROOT)),
            "otp_walk_responses": str(raw_routes_path.relative_to(ROOT)),
            "wcs_mdp05_samples": str(raw_wcs_path.relative_to(ROOT)),
        },
        "sha256": {
            "sample_pairs": sha256(raw_sample_path),
            "otp_walk_responses": sha256(raw_routes_path),
            "wcs_mdp05_samples": sha256(raw_wcs_path),
        },
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(raw_dir / "manifest.json", manifest)
    routes_with_slope = int(result["samples_valid"].gt(0).sum())
    status = "passed" if routes_with_slope == len(sample) else "partial"
    if routes_with_slope == 0:
        status = "blocked_external_source"
    report = {
        "status": status,
        "run_id": run_id,
        "purpose": "Perfiles actuales de pendiente sobre la muestra multimodal OTP real y estratificada.",
        "routing_date": routing_date,
        "routing_time": routing_time,
        "otp_endpoint": OTP_URL,
        "source": manifest["attribution"],
        "source_sample": str(sample_path.relative_to(ROOT)),
        "source_sample_sha256": manifest["input_sample_sha256"],
        "sample_pairs": int(len(sample)),
        "routes_with_geometry": int(result["route_status"].eq("ok").sum()),
        "routes_with_slope": routes_with_slope,
        "wcs_queries": int(len(raw_wcs)),
        "wcs_status_counts": pd.DataFrame(raw_wcs)["query_status"].value_counts().to_dict() if raw_wcs else {},
        "profile_output": str(profile_path.relative_to(ROOT)),
        "raw_manifest": str((raw_dir / "manifest.json").relative_to(ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": f"Geometría WALK actual de OTP; muestreo cada {spacing_m} m; WCS MDP05 de IGN/CNIG con celdas 5 m y valores en grados.",
        "next_action": (
            "Perfil completo disponible."
            if status == "passed"
            else "Reintenta con conectividad al WCS de IGN/CNIG; las rutas y respuestas fallidas quedan trazadas en raw."
        ),
        "limitations": [
            "La muestra de 12 pares sigue siendo estratificada y no representa demanda ni todos los desplazamientos turísticos.",
            "No se imputan valores WCS ni rutas ausentes.",
            "La pendiente no mide anchura, pavimento, cruces, iluminación, continuidad ni accesibilidad universal.",
            "No se incorpora al TSMAI V9 sin cobertura por alojamiento y validación metodológica específica.",
        ],
    }
    atomic_json(LATEST_OUTPUT, report)
    atomic_json(REPORT, report)
    return report


def main_current_sample_slope_profiles():
    # Define los argumentos del comando
    parser = argparse.ArgumentParser(description="Construye perfiles actuales de pendiente sobre la muestra multimodal real.")
    parser.add_argument("--execute", action="store_true", help="Consulta OTP e IGN/CNIG y publica snapshots reales.")
    parser.add_argument("--spacing-m", type=int, default=1000, help="Separación entre puntos de muestreo WCS (por defecto: 1000 m).")
    parser.add_argument("--workers", type=int, default=4, help="Máximo de consultas WCS simultáneas (por defecto: 4).")
    parser.add_argument("--timeout", type=int, default=45, help="Tiempo máximo por consulta remota en segundos.")
    args = parser.parse_args()
    if args.spacing_m < 100 or args.workers < 1 or args.timeout < 1:
        parser.error("--spacing-m debe ser ≥100; --workers y --timeout deben ser positivos.")
    report = execute(args.spacing_m, args.workers, args.timeout) if args.execute else plan()
    print(json.dumps(report, ensure_ascii=False, indent=2))





if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_current_sample_slope_profiles":
        main_current_sample_slope_profiles()
        sys.exit(0)
    print(f"Task {task_name} not found.")

