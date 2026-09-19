from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *




import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "mallorca_tourist_accommodations"
UNIFIED = ROOT / "data" / "unified"
REPORT = ROOT / "docs" / "accommodations_preparation_report.json"
OUTPUT = UNIFIED / "accommodations_official_normalized.geojson"

MALLORCA_BOUNDS = {"min_lon": 2.20, "max_lon": 3.55, "min_lat": 39.15, "max_lat": 40.20}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_text(value):
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def normalized_key(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", value)


def property_value(properties, *prefixes):
    normalized = {normalized_key(key): value for key, value in properties.items()}
        # Busca la clave normalizada correspondiente
    for prefix in prefixes:
        # Normaliza el prefijo para comparar
        candidate = normalized_key(prefix)
        for key, value in normalized.items():
            if key.startswith(candidate):
                return value
    return None


def as_int(value):
    text = clean_text(value)
    if text is None:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        numeric = float(text)
    except ValueError:
        return None
    if not math.isfinite(numeric) or numeric < 0 or not numeric.is_integer():
        return None
    return int(numeric)


def load_snapshot():
    latest_file = RAW_ROOT / "latest.json"
    if not latest_file.exists():
        raise FileNotFoundError(f"No existe {latest_file}. Ejecuta primero el extractor de alojamientos.")
    latest = json.loads(latest_file.read_text(encoding="utf-8"))
    manifest_path = ROOT / latest["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = manifest_path.parent / manifest["payload_file"]
    if not payload.is_file():
        raise FileNotFoundError(f"No existe el payload indicado en el manifiesto: {payload}")
    actual_hash = sha256(payload)
    if actual_hash != manifest["payload_sha256"]:
        raise ValueError("El hash del payload no coincide con el manifiesto; se cancela la normalización.")
    return manifest, payload


def point_coordinates(feature):
    geom = feature.get("geom") or {}
    if not geom:
        return None, "missing_geometry"
    if geom.get("type") != "Point":
        return None, "non_point_geometry"
    coords = geom.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
        return None, "invalid_point_coordinates"
    try:
        lon, lat = float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return None, "invalid_point_coordinates"
    if not (MALLORCA_BOUNDS["min_lon"] <= lon <= MALLORCA_BOUNDS["max_lon"] and MALLORCA_BOUNDS["min_lat"] <= lat <= MALLORCA_BOUNDS["max_lat"]):
        return None, "out_of_scope_coordinates"
    return (lon, lat), None


def normalize_feature(feature):
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None, "missing_properties"
    coords, geometry_error = point_coordinates(feature)
    if geometry_error:
        return None, geometry_error
    identifier = clean_text(property_value(properties, "Signatura"))
    if identifier is None:
        return None, "missing_accommodation_id"
    normalized = {
        "accommodation_id": identifier,
        "commercial_name": clean_text(property_value(properties, "Denominaci")),
        "municipality": clean_text(property_value(properties, "Municipi")),
        "locality": clean_text(property_value(properties, "Localitat")),
        "address": clean_text(property_value(properties, "Direcci")),
        "group": clean_text(property_value(properties, "Grup")),
        "subgroup": clean_text(property_value(properties, "Subgrup")),
        "category": clean_text(property_value(properties, "Categoria")),
        "status": clean_text(property_value(properties, "Estat")),
        "activity_start_date_raw": clean_text(property_value(properties, "Inici d'activitat", "Inici dactivitat")),
        "places": as_int(property_value(properties, "Places")),
        "units": as_int(property_value(properties, "Unitats")),
        "source_dataset": "mallorca_tourist_accommodations",
        "source_record_id": identifier,
    }
    return {"type": "Feature", "properties": normalized, "geom": {"type": "Point", "coords": list(coords)}}, None


def atomic_json_write(dest, payload):
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(dest.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(dest)


def main_prepare_official_accommodations():
    manifest, source_file = load_snapshot()
    source = json.loads(source_file.read_text(encoding="utf-8"))
    if source.get("type") != "FeatureCollection" or not isinstance(source.get("features"), list):
        raise ValueError("El payload no es un GeoJSON FeatureCollection válido.")

    rejected = Counter()
    duplicate_ids = Counter()
    normalized_features: list[dict[str, Any]] = []
    seen_ids = set()
    for feature in source["features"]:
        # Normaliza y valida cada alojamiento
        normalized, reason = normalize_feature(feature)
        if reason:
            rejected[reason] += 1
            continue
        identifier = normalized["properties"]["accommodation_id"]
        if identifier in seen_ids:
            duplicate_ids[identifier] += 1
            rejected["duplicate_accommodation_id"] += 1
            continue
        seen_ids.add(identifier)
        normalized_features.append(normalized)

    if not normalized_features:
        raise ValueError("No quedaron alojamientos válidos tras los controles de calidad.")

    output = {
        "type": "FeatureCollection",
        "name": "accommodations_official_normalized",
        "metadata": {
            "source_id": manifest["source_id"],
            "source_run_id": manifest["run_id"],
            "source_payload_sha256": manifest["payload_sha256"],
            "license": manifest["license"],
            "attribution": manifest["attribution"],
            "crs": "EPSG:4326",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "features": normalized_features,
    }
    atomic_json_write(OUTPUT, output)
    report = {
        "status": "passed",
        "source_snapshot": str(source_file.relative_to(ROOT)),
        "source_run_id": manifest["run_id"],
        "source_sha256_verified": True,
        "input_features": len(source["features"]),
        "published_features": len(normalized_features),
        "rejected_features": int(sum(rejected.values())),
        "rejected_by_reason": dict(rejected),
        "duplicated_ids_discarded": int(sum(duplicate_ids.values())),
        "active_status_count": sum(item["properties"]["status"] == "Alta" for item in normalized_features),
        "output": str(OUTPUT.relative_to(ROOT)),
        "limitations": [
            "Los valores vacíos se conservan como nulos; no se imputan datos turísticos.",
            "La validación espacial comprueba pertenencia a la envolvente de Mallorca, no la parcela exacta.",
            "La capa representa registros administrativos, no una auditoría de accesibilidad del establecimiento.",
        ],
    }
    atomic_json_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))






import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "osm_mallorca_network"
OSM_UNIFIED = ROOT / "data" / "unified" / "osm"
LATEST = OSM_UNIFIED / "latest_mallorca_network.json"
REPORT = ROOT / "docs" / "osm_network_preparation_report.json"

MALLORCA_BBOX = "2.20,39.15,3.55,40.20"


def sha256(path):
    # Calcula el hash SHA-256 del archivo
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json_write(path, payload):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_source():
    # Carga el ultimo snapshot OSM
    latest_path = RAW_ROOT / "latest.json"
    if not latest_path.exists():
        raise FileNotFoundError(f"No existe {latest_path}. Ejecuta primero el extractor OSM.")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    manifest_path = ROOT / latest["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "osm_mallorca_network":
        raise ValueError("El manifiesto no corresponde a la fuente OSM registrada.")
    payload = manifest_path.parent / manifest["payload_file"]
    if not payload.exists():
        raise FileNotFoundError(f"No existe el PBF indicado en el manifiesto: {payload}")
    if sha256(payload) != manifest.get("payload_sha256"):
        raise ValueError("El hash del PBF no coincide con su manifiesto; se cancela el procesamiento.")
    return manifest, payload

def osmium_command():
    # Localiza el ejecutable de osmium
    if os.name == "nt":
        conda_bat = Path(sys.prefix).parents[1] / "condabin" / "conda.bat"
        if conda_bat.exists():
            return [str(conda_bat), "run", "--no-capture-output", "-p", sys.prefix, "osmium"]
    executable = shutil.which("osmium")
    if executable:
        return [executable]
    raise RuntimeError(
        "No se encontró 'osmium'. Activa el entorno del proyecto y ejecuta "
        "conda install -c conda-forge osmium-tool si aún no está instalado."
    )


def main_prepare_osm_mobility_network():
    manifest, source = load_source()
    osmium = osmium_command()
    run_id = manifest["run_id"]
    output = OSM_UNIFIED / f"mallorca_mobility_network_{run_id}.osm.pbf"
    temporary = OSM_UNIFIED / f"mallorca_mobility_network_{run_id}.part.osm.pbf"
    OSM_UNIFIED.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Ya existe una red para este snapshot: {output}. No se sobrescribe.")

    command = osmium + ["extract", "-b", MALLORCA_BBOX, str(source), "-o", str(temporary), "--overwrite"]
    try:
        subprocess.run(command, check=True, text=True)
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise ValueError("Osmium no produjo una red PBF con contenido.")
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    report = {
        "status": "passed",
        "source_snapshot": str(source.relative_to(ROOT)),
        "source_run_id": run_id,
        "source_sha256_verified": True,
        "source_license": manifest["license"],
        "source_attribution": manifest["attribution"],
        "bbox_wgs84": MALLORCA_BBOX,
        "network_file": str(output.relative_to(ROOT)),
        "network_bytes": output.stat().st_size,
        "network_sha256": sha256(output),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "El recorte por envolvente puede incluir segmentos próximos al litoral; no es un límite administrativo exacto.",
            "Este paso prepara la red OSM; la clasificación por modo y las restricciones de accesibilidad se calculan en etapas posteriores.",
        ],
    }
    atomic_json_write(LATEST, report)
    atomic_json_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))






import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OSM_UNIFIED = ROOT / "data" / "unified" / "osm"
RAW_GTFS = ROOT / "data" / "raw" / "tib_gtfs_supply"
OTP_ROOT = ROOT / "data" / "otp"
BUILDS = OTP_ROOT / "builds"
REPORT = ROOT / "docs" / "otp_input_preparation_report.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_network():
    latest_path = OSM_UNIFIED / "latest_mallorca_network.json"
    if not latest_path.exists():
        raise FileNotFoundError("No existe una red OSM preparada para Mallorca.")
    metadata = json.loads(latest_path.read_text(encoding="utf-8"))
    network = ROOT / metadata["network_file"]
    if not network.exists() or sha256(network) != metadata["network_sha256"]:
        raise ValueError("La red OSM no existe o no coincide con el hash registrado.")
    return metadata, network


def load_gtfs():
    # Carga el ultimo snapshot GTFS
    latest_path = RAW_GTFS / "latest.json"
    if not latest_path.exists():
        raise FileNotFoundError("No existe un snapshot GTFS TIB importado.")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    manifest_path = ROOT / latest["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = manifest_path.parent / manifest["payload_file"]
    if not archive.exists() or sha256(archive) != manifest["payload_sha256"]:
        raise ValueError("El archivo GTFS no existe o no coincide con el hash registrado.")
    return manifest, archive


def main_prepare_otp_inputs():
    network_metadata, network = load_network()
    gtfs_manifest, archive = load_gtfs()
    build_id = f"otp_{network_metadata['source_run_id']}_{gtfs_manifest['run_id']}"
    build_dir = BUILDS / build_id
    if build_dir.exists():
        raise FileExistsError(f"La construcción OTP ya existe: {build_dir}. Usa ese directorio para Docker; no se sobrescribe.")
    build_dir.mkdir(parents=True, exist_ok=False)
    try:
        osm_input = build_dir / "mallorca_network.osm.pbf"
        gtfs_input = build_dir / "tib_gtfs.zip"
        shutil.copy2(network, osm_input)
        shutil.copy2(archive, gtfs_input)
        build_config = {
            "transitServiceStart": "-P1Y",
            "transitServiceEnd": "P3Y",
            "osmDefaults": {"timeZone": "Europe/Madrid", "osmTagMapping": "default"},
        }
        atomic_json_write(build_dir / "build-config.json", build_config)
        report = {
            "status": "ready_for_otp_build",
            "build_id": build_id,
            "build_directory": str(build_dir.relative_to(ROOT)),
            "osm_source": network_metadata["network_file"],
            "osm_source_sha256": network_metadata["network_sha256"],
            "gtfs_source": str(archive.relative_to(ROOT)),
            "gtfs_source_sha256": gtfs_manifest["payload_sha256"],
            "osm_input": str(osm_input.relative_to(ROOT)),
            "gtfs_input": str(gtfs_input.relative_to(ROOT)),
            "timezone": "Europe/Madrid",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "next_command": "docker compose -f docker/otp/docker-compose.yml run --rm otp-build",
        }
        atomic_json_write(build_dir / "input_manifest.json", report)
        atomic_json_write(OTP_ROOT / "latest_otp_inputs.json", report)
        atomic_json_write(REPORT, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception:

        raise






import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "tib_gtfs_supply"
GTFS_UNIFIED = ROOT / "data" / "unified" / "gtfs"
REPORT = ROOT / "docs" / "tib_gtfs_preparation_report.json"
MALLORCA_BOUNDS = {"min_lon": 2.20, "max_lon": 3.55, "min_lat": 39.15, "max_lat": 40.20}
REQUIRED_TABLES = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            # Actualiza el hash por bloques
            digest.update(block)
    return digest.hexdigest()


def atomic_json_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_snapshot():
    # Verifica que exista el snapshot
    latest_path = RAW_ROOT / "latest.json"
    if not latest_path.exists():
        raise FileNotFoundError(
            "No hay un snapshot TIB GTFS. Descarga el ZIP oficial e impórtalo con "
            "scripts/extract/ingest_source.py --source-id tib_gtfs_supply --input RUTA --execute."
        )
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    manifest_path = ROOT / latest["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "tib_gtfs_supply":
        raise ValueError("El manifiesto no corresponde a la fuente GTFS de TIB.")
    payload = manifest_path.parent / manifest["payload_file"]
    if payload.suffix.lower() != ".zip" or not payload.exists():
        raise ValueError("El snapshot GTFS debe ser un archivo ZIP existente.")
    if sha256(payload) != manifest.get("payload_sha256"):
        raise ValueError("El hash del ZIP no coincide con su manifiesto; se cancela el procesamiento.")
    return manifest, payload


def table_index(archive):
    result: dict[str, str] = {}
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        if entry.filename.startswith("/") or ".." in Path(entry.filename).parts:
            raise ValueError("El ZIP contiene una ruta insegura.")
        basename = Path(entry.filename).name.lower()
        if basename in result:
            raise ValueError(f"El ZIP contiene más de una tabla llamada {basename}.")
        result[basename] = entry.filename
    return result


def rows(archive, filename):
    with archive.open(filename) as binary:
        with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
            yield from csv.DictReader(text)


def as_float(value):
    try:
        number = float(value or "")
    except ValueError:
        return None
    return number if number == number and abs(number) != float("inf") else None


def valid_mallorca_point(lat, lon):
    return lat is not None and lon is not None and MALLORCA_BOUNDS["min_lon"] <= lon <= MALLORCA_BOUNDS["max_lon"] and MALLORCA_BOUNDS["min_lat"] <= lat <= MALLORCA_BOUNDS["max_lat"]


def normalize_stops(archive, filename):
    # Filtra y normaliza las paradas
    rejected = Counter()
    seen = set()
    features = []
    for row in rows(archive, filename):
        stop_id = (row.get("stop_id") or "").strip()
        if not stop_id:
            rejected["missing_stop_id"] += 1
            continue
        if stop_id in seen:
            rejected["duplicate_stop_id"] += 1
            continue
        seen.add(stop_id)
        lat, lon = as_float(row.get("stop_lat")), as_float(row.get("stop_lon"))
        if not valid_mallorca_point(lat, lon):
            rejected["invalid_or_out_of_scope_coordinates"] += 1
            continue
        properties = {
            "stop_id": stop_id,
            "stop_name": (row.get("stop_name") or "").strip() or None,
            "stop_code": (row.get("stop_code") or "").strip() or None,
            "location_type": (row.get("location_type") or "0").strip(),
            "parent_station": (row.get("parent_station") or "").strip() or None,
            "wheelchair_boarding": (row.get("wheelchair_boarding") or "").strip() or None,
            "zone_id": (row.get("zone_id") or "").strip() or None,
            "source_dataset": "tib_gtfs_supply",
        }
        features.append({"type": "Feature", "properties": properties, "geom": {"type": "Point", "coords": [lon, lat]}})
    return features, rejected


def main_prepare_tib_gtfs():
    manifest, payload = load_snapshot()
    with zipfile.ZipFile(payload) as archive:
        if any(item.flag_bits & 0x1 for item in archive.infolist()):
            raise ValueError("El ZIP GTFS está cifrado y no se puede validar de forma reproducible.")
        tables = table_index(archive)
        missing = REQUIRED_TABLES.difference(tables)
        if missing:
            raise ValueError(f"GTFS incompleto; faltan tablas obligatorias: {sorted(missing)}")
        stops, stop_rejections = normalize_stops(archive, tables["stops.txt"])
        if not stops:
            raise ValueError("No hay paradas GTFS válidas en Mallorca tras la validación.")
        route_ids = {(row.get("route_id") or "").strip() for row in rows(archive, tables["routes.txt"])}
        route_ids.discard("")
        trip_rows = 0
        trip_route_ids = set()
        for row in rows(archive, tables["trips.txt"]):
            trip_rows += 1
            route_id = (row.get("route_id") or "").strip()
            if route_id:
                trip_route_ids.add(route_id)
        stop_time_rows = sum(1 for _ in rows(archive, tables["stop_times.txt"]))
            # Cierra la lectura del ZIP

    run_id = manifest["run_id"]
    stops_output = GTFS_UNIFIED / f"tib_gtfs_stops_{run_id}.geojson"
    geojson = {
        "type": "FeatureCollection",
        "name": "tib_gtfs_stops",
        "metadata": {
            "source_id": manifest["source_id"],
            "source_run_id": run_id,
            "source_payload_sha256": manifest["payload_sha256"],
            "license": manifest["license"],
            "attribution": manifest["attribution"],
            "crs": "EPSG:4326",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "features": stops,
    }
    atomic_json_write(stops_output, geojson)
    report = {
        "status": "passed",
        "source_snapshot": str(payload.relative_to(ROOT)),
        "source_run_id": run_id,
        "source_sha256_verified": True,
        "source_license": manifest["license"],
        "tables_detected": sorted(tables),
        "stops_published": len(stops),
        "stops_rejected_by_reason": dict(stop_rejections),
        "routes_declared": len(route_ids),
        "trips_declared": trip_rows,
        "routes_referenced_by_trips": len(trip_route_ids),
        "unknown_route_ids_in_trips": len(trip_route_ids.difference(route_ids)),
        "stop_time_rows": stop_time_rows,
        "calendar_table_present": "calendar.txt" in tables,
        "calendar_dates_table_present": "calendar_dates.txt" in tables,
        "stops_output": str(stops_output.relative_to(ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La posición de una parada no demuestra frecuencia, puntualidad ni accesibilidad física de la misma.",
            "La validación comprueba la estructura del feed; el cálculo de itinerarios y tiempo de espera se realizará sobre horario GTFS en una etapa posterior.",
        ],
    }
    atomic_json_write(GTFS_UNIFIED / "latest_tib_gtfs.json", report)
    atomic_json_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))





import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
DOCS = ROOT / "docs"
OTP_ENDPOINT = "http://localhost:8080/otp/gtfs/v1"
QUERY = """query Route($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
 plan(from:$from,to:$to,date:$date,time:$time,transportModes:[{mode:WALK},{mode:TRANSIT}],numItineraries:1) {
  itineraries { duration walkDistance legs { mode distance duration route { shortName } } }
  routingErrors { code description }
 }}"""


def build_pairs():
    lodgings = gpd.read_parquet(CURATED / "accommodations_transport_access_baseline.parquet")
    dests = gpd.read_parquet(CURATED / "tourism_destinations_transport_access_baseline.parquet")
    targets = dests.loc[dests.destination_category.astype("string").isin(["tourism", "historic"])].copy()
    l_utm, t_utm = lodgings.to_crs(25831), targets.to_crs(25831)
    spatial_index = t_utm.sindex
    rows = []
    for source_idx, origin in l_utm.iterrows():
        candidates_idx = list(spatial_index.query(origin.geom.buffer(20_000), predicate="intersects"))
        if not candidates_idx:
            continue
        candidates = t_utm.iloc[candidates_idx].copy()
        candidates["distance_m"] = candidates.geom.distance(origin.geom)
        candidates = candidates.loc[candidates.distance_m.between(2_000, 20_000)]
        if candidates.empty:
            continue
        target_idx = candidates.distance_m.idxmin()
        source, target = lodgings.loc[source_idx], targets.loc[target_idx]
        rows.append({"od_id": f"M_OD{source_idx:04d}", "origin_name": source.commercial_name,
                     "origin_municipality": source.municipality_raw, "origin_access_band": source.walk_access_band_euclidean,
                     "destination_name": target["name"], "destination_category": target.destination_category,
                     "origin_lat": float(source.geom.y), "origin_lon": float(source.geom.x),
                     "destination_lat": float(target.geom.y), "destination_lon": float(target.geom.x),
                     "screening_distance_m": float(candidates.loc[target_idx, "distance_m"])})
    return pd.DataFrame(rows)


async def health_check(session, endpoint):
    try:
        async with session.post(endpoint, json={"query": "{ __typename }"}) as response:
            response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"OTP no está disponible en {endpoint}. Inícialo con Docker antes de ejecutar el barrido. Detalle: {exc}") from exc


async def fetch_route(session, semaphore, row, date, clock, retries=2):
    variables = {"from": {"lat": row.origin_lat, "lon": row.origin_lon}, "to": {"lat": row.destination_lat, "lon": row.destination_lon}, "date": date, "time": clock}
    async with semaphore:
        for attempt in range(retries + 1):
            try:
                async with session.post(OTP_ENDPOINT, json={"query": QUERY, "variables": variables}) as response:
                    response.raise_for_status(); payload = await response.json()
                if payload.get("errors"):
                    return {"od_id": row.od_id, "query_status": "graphql_error", "error": json.dumps(payload["errors"], ensure_ascii=False)}
                plan = payload["data"]["plan"]
                if not plan.get("itineraries"):
                    return {"od_id": row.od_id, "query_status": "no_itinerary", "error": json.dumps(plan.get("routingErrors", []), ensure_ascii=False)}
                itinerary = plan["itineraries"][0]
                transit = [leg for leg in itinerary["legs"] if leg["mode"] not in {"WALK"}]
                    # Calcula transbordos y lineas usadas
                return {"od_id": row.od_id, "query_status": "ok", "route_found": True,
                        "total_duration_min": round(itinerary["duration"] / 60, 2), "walk_distance_m": round(itinerary["walkDistance"], 2),
                        "has_transit": bool(transit), "transfers": max(0, len(transit) - 1),
                        "transit_routes": ",".join(str(leg.get("route", {}).get("shortName", "")) for leg in transit)}
                            # Reintenta la consulta si falla
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt == retries:
                    return {"od_id": row.od_id, "query_status": "http_error", "error": str(exc)}
                await asyncio.sleep(2 ** attempt)


async def run(args):
    output = CURATED / "od_multimodal_routes_massive_exploratory.parquet"
    checkpoint = CURATED / "od_multimodal_routes_massive_checkpoint.parquet"
    pairs = build_pairs()
    completed = pd.read_parquet(checkpoint) if args.resume and checkpoint.exists() else pd.DataFrame()
    pending = pairs.loc[~pairs.od_id.isin(completed.get("od_id", pd.Series(dtype="string")))].copy()
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    start = time.perf_counter()
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await health_check(session, OTP_ENDPOINT)
        semaphore = asyncio.Semaphore(args.concurrency)
        res = []
        for offset in range(0, len(pending), args.batch_size):
            batch = pending.iloc[offset:offset + args.batch_size]
            res.extend(await asyncio.gather(*(fetch_route(session, semaphore, row, args.date, args.time) for row in batch.itertuples())))
            partial = pd.concat([completed, pd.DataFrame(res)], ignore_index=True)
            partial.to_parquet(checkpoint, index=False)
            print(f"{min(offset + len(batch), len(pending))}/{len(pending)} consultas nuevas completadas")
    result_df = pd.concat([completed, pd.DataFrame(res)], ignore_index=True)
    final = pairs.merge(result_df, on="od_id", how="left", validate="one_to_one")
    final.to_parquet(output, index=False)
    seconds = time.perf_counter() - start
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "exploratory nearest eligible dest screening", "date": args.date, "time": args.time, "concurrency": args.concurrency, "batch_size": args.batch_size, "pairs": len(final), "ok": int(final.query_status.eq("ok").sum()), "seconds": round(seconds, 2), "requests_per_second": round(len(pending) / seconds, 2)}
    (DOCS / "async_massive_processing_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Resultado: {output}\nInforme: {DOCS / 'async_massive_processing_report.json'}")




import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "licensed_mobility_survey"
PRIVATE = ROOT / "data" / "private"
DOCS = ROOT / "docs" / "source_snapshots"
SOURCE_ID = "licensed_mobility_survey"
ALLOWED_LICENSES = {"CC-BY", "CC-BY-4.0", "CC0", "CC0-1.0", "CONSENT"}
REQUIRED_PURPOSES = {"academic_analysis", "machine_learning_inference", "aggregated_publication"}
FORBIDDEN_COLUMNS = {"author", "author_name", "email", "user_id", "profile_url", "phone", "telephone"}


def sha256(path):
    # Calcula el hash del archivo
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_consent(path):
    # Valida el manifiesto de consentimiento
    if not path.is_file():
        raise FileNotFoundError(f"No existe el manifiesto de consentimiento: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "source_id", "consent_obtained", "consent_notice_version", "collection_start",
        "collection_end", "approved_purposes", "personal_data_removed", "retention_policy",
    }
    missing = required.difference(manifest)
    if missing:
        raise ValueError(f"El manifiesto de consentimiento no contiene: {sorted(missing)}")
    if manifest["source_id"] != SOURCE_ID or manifest["consent_obtained"] is not True:
        raise ValueError("La atestación debe declarar source_id correcto y consent_obtained=true.")
    if manifest["personal_data_removed"] is not True:
        raise ValueError("No se ingieren datos hasta confirmar la eliminación de datos personales.")
    purposes = set(manifest["approved_purposes"])
    if not REQUIRED_PURPOSES.issubset(purposes):
        raise ValueError(f"Faltan usos autorizados: {sorted(REQUIRED_PURPOSES.difference(purposes))}")
    return manifest


def validate_survey(path):
    # Valida el CSV de encuesta
    if not path.is_file():
        raise FileNotFoundError(f"No existe el CSV de encuesta: {path}")
    data = pd.read_csv(path)
    required = {"review_id", "text", "license", "source_url"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"El CSV no contiene las columnas obligatorias: {sorted(missing)}")
    if "accommodation_id" not in data.columns and "municipality" not in data.columns:
        raise ValueError("Cada respuesta debe vincularse a accommodation_id o municipality, nunca a la identidad del participante.")
    forbidden = sorted(FORBIDDEN_COLUMNS.intersection(data.columns))
    if forbidden:
        raise ValueError(f"El CSV incluye columnas personales prohibidas: {forbidden}. Elimínalas antes de ingerir.")
    ids = data["review_id"].astype("string").str.strip()
    if ids.isna().any() or ids.eq("").any() or ids.duplicated().any():
        raise ValueError("review_id debe ser no vacío y único; usa un identificador pseudónimo estable.")
    licenses = data["license"].astype("string").str.upper().str.strip()
    invalid_licenses = sorted(set(licenses.dropna()) - ALLOWED_LICENSES)
    if invalid_licenses:
        raise ValueError(f"Licencias no permitidas: {invalid_licenses}")
    if data["text"].astype("string").str.strip().str.len().lt(15).any():
        raise ValueError("Cada texto debe tener al menos 15 caracteres; no se aceptan respuestas vacías o triviales.")
    return {"records": int(len(data)), "columns": sorted(data.columns.tolist()), "licenses": sorted(licenses.dropna().unique().tolist())}


def write_json(path, payload):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main_ingest_licensed_mobility_survey():
    parser = argparse.ArgumentParser(description="Ingiere una encuesta de movilidad autorizada, sin PII ni scraping.")
    parser.add_argument("--input", type=Path, required=True, help="CSV local exportado de la encuesta, sin identificadores personales.")
    parser.add_argument("--consent-manifest", type=Path, default=PRIVATE / "licensed_mobility_survey_consent.json")
    parser.add_argument("--execute", action="store_true", help="Copia el CSV y la atestación a un snapshot raw inmutable.")
    args = parser.parse_args()
    consent = read_consent(args.consent_manifest)
    survey = validate_survey(args.input)
    if not args.execute:
        print(json.dumps({
            "status": "dry_run", "source_id": SOURCE_ID, "input": str(args.input),
            "records": survey["records"], "licenses": survey["licenses"],
            "message": "La estructura y la atestación son válidas; añade --execute para crear el snapshot raw.",
        }, ensure_ascii=False, indent=2))
        return
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = RAW / run_id
    snapshot.mkdir(parents=True, exist_ok=False)
    payload = snapshot / "payload.csv"
    attestation = snapshot / "consent_attestation.json"
    shutil.copy2(args.input, payload)
    shutil.copy2(args.consent_manifest, attestation)
    manifest = {
        "source_id": SOURCE_ID,
        "run_id": run_id,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "acquisition_mode": "local_collection_with_informed_consent",
        "payload_file": payload.name,
        "payload_sha256": sha256(payload),
        "consent_attestation_file": attestation.name,
        "consent_attestation_sha256": sha256(attestation),
        "records_declared": survey["records"],
        "licenses_declared": survey["licenses"],
        "approved_purposes": consent["approved_purposes"],
        "personal_data_removed": True,
    }
    write_json(snapshot / "manifest.json", manifest)
    write_json(RAW / "latest.json", {"run_id": run_id, "manifest": str((snapshot / "manifest.json").relative_to(ROOT))})
    write_json(DOCS / f"{SOURCE_ID}_{run_id}.json", manifest)
    print(json.dumps({"status": "ingested", "source_id": SOURCE_ID, "payload": str(payload.relative_to(ROOT)), "manifest": str((snapshot / "manifest.json").relative_to(ROOT))}, ensure_ascii=False, indent=2))


INSIDE_AIRBNB_ROOT = ROOT / "data" / "raw" / "inside_airnb"
INSIDE_AIRBNB_LISTINGS = INSIDE_AIRBNB_ROOT / "listings.csv"
INSIDE_AIRBNB_REVIEWS = INSIDE_AIRBNB_ROOT / "reviews.csv.gz"
REVIEWS_LICENSED_OUT = ROOT / "data" / "raw" / "reviews_licensed.csv"
INSIDE_AIRBNB_REPORT = ROOT / "docs" / "inside_airbnb_reviews_preparation_report.json"
INSIDE_AIRBNB_LICENSE = "CC-BY-4.0"
INSIDE_AIRBNB_SOURCE_URL = "https://insideairbnb.com/get-the-data/"

# Diferencias de grafía entre el "neighbourhood" de Inside Airbnb y el municipality_raw
# del proyecto (mayúsculas resuelven el resto); comprobado contra el registro de
# alojamientos vigente. Los municipios de Inside Airbnb sin alojamientos en el
# proyecto (p. ej. "Mancor de la Vall", "Sant Joan") se descartan, no se inventan.
INSIDE_AIRBNB_NEIGHBOURHOOD_OVERRIDES = {
    "Palma de Mallorca": "PALMA",
    "Deyá": "DEIÀ",
    "Vilafranc de Bonany": "VILAFRANCA DE BONANY",
    "Santa María del Camí": "SANTA MARIA DEL CAMÍ",
}


def clean_inside_airbnb_text(value):
    # Quita marcado HTML y saltos de línea crudos del scrape, sin tocar el contenido
    if not isinstance(value, str):
        return ""
    text = value.replace("<br/>", " ").replace("<br />", " ").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def main_prepare_inside_airbnb_reviews():
    """Transforma el export de Inside Airbnb (Mallorca) al contrato de validate_licensed_reviews.

    Inside Airbnb publica sus datos bajo Creative Commons Attribution 4.0
    (ver https://insideairbnb.com/get-the-data/); "reviews.csv.gz" es la única
    de las dos exportaciones de reseñas que trae el texto ("reviews.csv" es
    sólo un resumen de fechas, sin comentarios, y no sirve para sentimiento).
    Sólo se publica un agregado por municipio aguas abajo: nunca el texto en
    bruto, en línea con la política de la fuente de no republicar el dataset.
    """
    parser = argparse.ArgumentParser(description="Prepara las reseñas de Inside Airbnb (Mallorca) para el pipeline de sentimiento de movilidad.")
    parser.add_argument("--max-per-municipality", type=int, default=200, help="Límite de reseñas por municipio para acotar el tiempo de inferencia BERT posterior; 0 = sin límite.")
    args = parser.parse_args()

    if not INSIDE_AIRBNB_LISTINGS.is_file() or not INSIDE_AIRBNB_REVIEWS.is_file():
        raise FileNotFoundError("Faltan listings.csv o reviews.csv.gz en data/raw/inside_airnb/.")
    if not OUTPUT.is_file():
        raise FileNotFoundError("Falta el registro de alojamientos del proyecto; ejecuta prepare_official_accommodations primero.")
    project_municipalities = set(gpd.read_file(OUTPUT)["municipality"].dropna().unique())

    listings = pd.read_csv(INSIDE_AIRBNB_LISTINGS, usecols=["id", "neighbourhood"], low_memory=False)
    listings["municipality"] = listings["neighbourhood"].map(
        lambda value: INSIDE_AIRBNB_NEIGHBOURHOOD_OVERRIDES.get(value, str(value).upper()) if pd.notna(value) else None
    )
    unmatched_neighbourhoods = sorted(set(
        listings.loc[listings["municipality"].notna() & ~listings["municipality"].isin(project_municipalities), "neighbourhood"].dropna()
    ))
    listings.loc[~listings["municipality"].isin(project_municipalities), "municipality"] = None

    reviews = pd.read_csv(INSIDE_AIRBNB_REVIEWS, compression="gzip", usecols=["listing_id", "id", "comments"])
    reviews_total = int(len(reviews))
    reviews = reviews.merge(listings[["id", "municipality"]], left_on="listing_id", right_on="id", how="left", suffixes=("", "_listing"))

    reviews["text"] = reviews["comments"].map(clean_inside_airbnb_text)
    with_text = reviews.loc[reviews["text"].str.len().ge(15)].copy()
    with_municipality = with_text.loc[with_text["municipality"].notna()].copy()

    sampled = with_municipality
    if args.max_per_municipality > 0:
        sampled_parts = [
            group.sample(n=min(len(group), args.max_per_municipality), random_state=42)
            for _, group in with_municipality.groupby("municipality")
        ]
        sampled = pd.concat(sampled_parts, ignore_index=True) if sampled_parts else with_municipality.iloc[0:0].copy()

    output = pd.DataFrame({
        "review_id": "airbnb_" + sampled["id"].astype(str),
        "text": sampled["text"],
        "license": INSIDE_AIRBNB_LICENSE,
        "source_url": INSIDE_AIRBNB_SOURCE_URL,
        "municipality": sampled["municipality"],
    }).drop_duplicates(subset="review_id")
    REVIEWS_LICENSED_OUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(REVIEWS_LICENSED_OUT, index=False)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Inside Airbnb (Mallorca): listings.csv + reviews.csv.gz",
        "source_license": INSIDE_AIRBNB_LICENSE,
        "source_policy_note": "Inside Airbnb pide no republicar el dataset en bruto y citar la fuente; este pipeline sólo agrega por municipio, nunca publica el texto de las reseñas.",
        "reviews_in_source": reviews_total,
        "reviews_with_usable_text": int(len(with_text)),
        "reviews_matched_to_project_municipality": int(len(with_municipality)),
        "reviews_written": int(len(output)),
        "max_per_municipality": args.max_per_municipality or None,
        "municipalities_covered": sorted(output["municipality"].unique().tolist()),
        "neighbourhoods_without_project_municipality": unmatched_neighbourhoods,
        "output": str(REVIEWS_LICENSED_OUT.relative_to(ROOT)),
        "next_steps": [
            "python scripts/run_task.py validate_licensed_reviews",
            "python scripts/run_task.py analyze_multilingual_sentiment  (requiere pip install -r requirements-nlp.txt)",
            "python scripts/run_task.py aggregate_mobility_sentiment",
        ],
        "limitations": [
            "El municipio se asigna por el 'neighbourhood' del alojamiento en Inside Airbnb, no por el alojamiento real del proyecto: es contexto territorial, no un vínculo a un accommodation_id.",
            "El muestreo por municipio (si --max-per-municipality > 0) no es aleatorio simple sobre toda Mallorca, sino estratificado por municipio con semilla fija (42) para reproducibilidad.",
        ],
    }
    write_json(INSIDE_AIRBNB_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_") else "run_" + args.task

    if task_name == "run_prepare_official_accommodations":
        main_prepare_official_accommodations()
        sys.exit(0)
    if task_name == "run_prepare_osm_mobility_network":
        main_prepare_osm_mobility_network()
        sys.exit(0)
    if task_name == "run_prepare_otp_inputs":
        main_prepare_otp_inputs()
        sys.exit(0)
    if task_name == "run_prepare_tib_gtfs":
        main_prepare_tib_gtfs()
        sys.exit(0)
    if task_name == "run_process_od_async":
        main_process_od_async()
        sys.exit(0)
    if task_name == "run_ingest_licensed_mobility_survey":
        main_ingest_licensed_mobility_survey()
        sys.exit(0)
    print(f"Task {task_name} not found.")




