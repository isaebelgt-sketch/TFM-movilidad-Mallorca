from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
UNIFIED = ROOT / "data" / "unified" / "aemet"
CURATED = ROOT / "data" / "curated"
LATEST_INPUT = UNIFIED / "latest_aemet_weather.json"
LATEST = CURATED / "latest_aemet_weather_context.json"
REPORT = ROOT / "docs" / "aemet_mallorca_weather_context_report.json"
MALLORCA_BBOX = {"west": 2.20, "south": 39.15, "east": 3.55, "north": 40.20}
NUMERIC_COLUMNS = {
    "tmed": "tmed_c", "tmin": "tmin_c", "tmax": "tmax_c", "prec": "prec_mm",
    "velmedia": "wind_mean_ms", "racha": "wind_gust_ms", "hrMedia": "relative_humidity_mean_pct",
    "hrMax": "relative_humidity_max_pct", "hrMin": "relative_humidity_min_pct", "sol": "sunshine_hours",
}
DMS_PATTERN = re.compile(r"^(?P<degrees>\d{2,3})(?P<minutes>\d{2})(?P<seconds>\d{2})(?P<hemisphere>[NSEW])$")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(payload, path):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def atomic_parquet(frame, path):
    # Escribe el parquet de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def dms_to_decimal(value):
    # Convierte coordenadas DMS a decimal
    match = DMS_PATTERN.fullmatch(str(value).strip())
    if not match:
        return None
    degrees = float(match.group("degrees"))
    minutes = float(match.group("minutes"))
    seconds = float(match.group("seconds"))
    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if match.group("hemisphere") in {"S", "W"} else decimal

def aemet_number(value):
    # Convierte texto AEMET a numero
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def main_aemet_mallorca_weather_context():
    # Carga el contexto AEMET vigente
    if not LATEST_INPUT.is_file():
        raise FileNotFoundError("Ejecuta primero build_aemet_weather_context.py --execute.")
    metadata = json.loads(LATEST_INPUT.read_text(encoding="utf-8"))
    if metadata.get("status") != "passed":
        raise ValueError("El último contexto AEMET no es válido.")
    stations_path = ROOT / metadata["stations_output"]
    daily_path = ROOT / metadata["daily_output"]
    if not stations_path.is_file() or not daily_path.is_file():
        raise FileNotFoundError("Las salidas AEMET declaradas no existen.")
    stations = pd.read_parquet(stations_path).copy()
    daily = pd.read_parquet(daily_path).copy()
    required_stations = {"indicativo", "latitud", "longitud", "nombre"}
    required_daily = {"indicativo", "fecha"}
    if missing := required_stations.difference(stations.columns):
        raise ValueError(f"Faltan columnas de estaciones AEMET: {sorted(missing)}")
    if missing := required_daily.difference(daily.columns):
        raise ValueError(f"Faltan columnas diarios AEMET: {sorted(missing)}")
    stations["latitude"] = stations["latitud"].map(dms_to_decimal)
    stations["longitude"] = stations["longitud"].map(dms_to_decimal)
    stations = stations.dropna(subset=["latitude", "longitude"])
    mallorca = stations.loc[
        stations["longitude"].between(MALLORCA_BBOX["west"], MALLORCA_BBOX["east"])
        & stations["latitude"].between(MALLORCA_BBOX["south"], MALLORCA_BBOX["north"])
    ].copy()
    if mallorca.empty:
        raise ValueError("No hay estaciones AEMET dentro de la envolvente de Mallorca.")
    context = mallorca.merge(daily, on="indicativo", how="inner", suffixes=("_station", ""), validate="one_to_many")
    if context.empty:
        raise ValueError("No hay observaciones AEMET para las estaciones de Mallorca en el periodo solicitado.")
    for raw_name, normalized_name in NUMERIC_COLUMNS.items():
        if raw_name in context.columns:
            context[normalized_name] = context[raw_name].map(aemet_number)
    context["observation_date"] = pd.to_datetime(context["fecha"], errors="coerce").dt.date.astype("string")
    if context["observation_date"].isna().any():
        raise ValueError("AEMET devolvió observaciones sin fecha válida.")
    context["weather_data_contract"] = "AEMET observed daily station context; Mallorca bbox only"
    output = gpd.GeoDataFrame(context, geometry=gpd.points_from_xy(context["longitude"], context["latitude"]), crs="EPSG:4326")
    run_id = metadata["run_id"]
    output_path = CURATED / f"aemet_weather_context_mallorca_{run_id}.parquet"
    atomic_parquet(output, output_path)
    report = {
        "status": "passed",
        "source_id": "aemet_weather",
        "source_run_id": run_id,
        "period": metadata["period"],
        "attribution": metadata["attribution"],
        "inputs": {
            "stations": str(stations_path.relative_to(ROOT)), "stations_sha256": sha256(stations_path),
            "daily": str(daily_path.relative_to(ROOT)), "daily_sha256": sha256(daily_path),
        },
        "output": str(output_path.relative_to(ROOT)),
        "records": int(len(output)),
        "mallorca_stations": int(output["indicativo"].nunique()),
        "observation_dates": sorted(output["observation_date"].dropna().unique().tolist()),
        "numeric_coverage": {column: int(output[column].notna().sum()) for column in NUMERIC_COLUMNS.values() if column in output.columns},
        "bbox_wgs84": MALLORCA_BBOX,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "El filtrado por envolvente selecciona estaciones localizadas en Mallorca; no interpola microclima.",
            "Las observaciones diarias históricas no describen condiciones de rutas de otra fecha.",
            "Los valores cualitativos AEMET no se convierten en números ni se imputan.",
            "El contexto no forma parte de TSMAI ni del ranking o recomendación de rutas.",
        ],
    }
    atomic_json(report, LATEST)
    atomic_json(report, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))






import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_pipeline.source_registry import require_approved_source


RAW = ROOT / "data" / "raw"
UNIFIED = ROOT / "data" / "unified" / "aemet"
SNAPSHOT_DOCS = ROOT / "docs" / "source_snapshots"
REPORT = ROOT / "docs" / "aemet_weather_context_report.json"
LATEST = UNIFIED / "latest_aemet_weather.json"
BASE_URL = "https://opendata.aemet.es/opendata/api"
SOURCE_ID = "aemet_weather"
CHUNK_SIZE = 1024 * 1024


def utc_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path):
    # Calcula el hash SHA-256 del archivo
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            # Actualiza el hash por bloques
            digest.update(block)
    return digest.hexdigest()


def atomic_json(payload, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def atomic_parquet(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def local_env_value(name, env_path: Path = ROOT / ".env"):
    # Lee la clave desde entorno
    value = os.getenv(name)
    if value:
        return value.strip()
    if not env_path.is_file():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, candidate = stripped.split("=", 1)
        if key.strip() == name:
            return candidate.strip().strip('"').strip("'") or None
    return None


def parse_date(value):
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("La fecha debe tener formato YYYY-MM-DD.") from exc
    if parsed > datetime.now(timezone.utc).date():
        raise argparse.ArgumentTypeError("AEMET de observaciones no admite fechas futuras.")
    return parsed

def get_aemet_json(path, api_key):
    response = requests.get(f"{BASE_URL}/{path.lstrip('/')}", params={"api_key": api_key}, timeout=60)
    response.raise_for_status()
    envelope = response.json()
    if int(envelope.get("estado", 200)) >= 400 or not envelope.get("datos"):
        raise RuntimeError(f"AEMET no devolvió datos: {envelope.get('descripcion', envelope)}")
    payload_url = str(envelope["datos"])
    payload = requests.get(payload_url, timeout=60)
    payload.raise_for_status()
    records = payload.json()
    if not isinstance(records, list):
        raise ValueError("La carga de AEMET no tiene el formato de lista esperado.")
    return records, payload_url


def balearic_stations(frame):
    # Filtra las estaciones de Baleares
    if frame.empty:
        return frame.copy()
    matches = frame.astype("string").apply(
        lambda column: column.str.contains("BALEARES|MALLORCA", case=False, na=False)
    )
    return frame.loc[matches.any(axis=1)].copy()


def plan(start, end):
    # Valida el rango de fechas
    if end < start:
        raise ValueError("--end no puede ser anterior a --start.")
    source = require_approved_source(SOURCE_ID)
    return {
        "status": "dry_run",
        "source_id": SOURCE_ID,
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "source_url": source["source_url"],
        "attribution": source["attribution"],
        "message": "No se ha consultado AEMET ni escrito datos. Añade --execute con AEMET_API_KEY sólo en .env local.",
    }


def execute(start, end):
    # Ejecuta la descarga real AEMET
    source = require_approved_source(SOURCE_ID)
    api_key = local_env_value("AEMET_API_KEY")
    if not api_key or api_key == "PEGA_AQUI_TU_CLAVE_NUEVA":
        raise RuntimeError("Falta una AEMET_API_KEY válida. Copia .env.example a .env, añade una clave nueva y no la subas a Git.")
    run_id = utc_run_id()
    temporary_snapshot = RAW / SOURCE_ID / f"{run_id}.part"
    snapshot = RAW / SOURCE_ID / run_id
    if temporary_snapshot.exists() or snapshot.exists():
        raise FileExistsError(f"Ya existe el identificador de ejecución {run_id}.")
    temporary_snapshot.mkdir(parents=True)
    try:
        inventory, _ = get_aemet_json("valores/climatologicos/inventarioestaciones/todasestaciones/", api_key)
        daily_path = (
            "valores/climatologicos/diarios/datos/"
            f"fechaini/{start.isoformat()}T00:00:00UTC/"
            f"fechafin/{end.isoformat()}T23:59:59UTC/todasestaciones/"
        )
        daily, _ = get_aemet_json(daily_path, api_key)
        stations = pd.DataFrame(inventory)
        baleares = balearic_stations(stations)
        daily_frame = pd.DataFrame(daily)
        if "indicativo" not in daily_frame.columns or "indicativo" not in baleares.columns:
            raise ValueError("AEMET no devolvió el identificador de estación requerido para el filtrado.")
        daily_baleares = daily_frame.loc[daily_frame["indicativo"].isin(baleares["indicativo"])].copy()
        stations_payload = temporary_snapshot / "stations_inventory.json"
        daily_payload = temporary_snapshot / f"daily_{start.isoformat()}_{end.isoformat()}.json"
        atomic_json(inventory, stations_payload)
        atomic_json(daily, daily_payload)
        manifest = {
            "source_id": SOURCE_ID, "provider": source["provider"], "source_url": source["source_url"],
            "license": source["license"], "attribution": source["attribution"], "coverage": source["coverage"],
            "status_at_ingestion": source["status"], "run_id": run_id,
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "acquisition": {
                "inventory_request": "valores/climatologicos/inventarioestaciones/todasestaciones/",
                "daily_request": daily_path,
                "payload_delivery": "URL temporal de AEMET consultada durante la ejecución y no persistida",
                "authentication": "AEMET_API_KEY local; valor no registrado",
            },
            "payloads": [
                {"file": stations_payload.name, "bytes": stations_payload.stat().st_size, "sha256": sha256(stations_payload)},
                {"file": daily_payload.name, "bytes": daily_payload.stat().st_size, "sha256": sha256(daily_payload)},
            ],
        }
        atomic_json(manifest, temporary_snapshot / "manifest.json")
        temporary_snapshot.replace(snapshot)
    except Exception:
        shutil.rmtree(temporary_snapshot, ignore_errors=True)
        raise

    SNAPSHOT_DOCS.mkdir(parents=True, exist_ok=True)
    atomic_json(manifest, SNAPSHOT_DOCS / f"{SOURCE_ID}_{run_id}.json")
    atomic_json(
        {"run_id": run_id, "manifest": str((snapshot / "manifest.json").relative_to(ROOT))},
        snapshot.parent / "latest.json",
    )
    stations_out = UNIFIED / f"aemet_weather_stations_{run_id}.parquet"
    daily_out = UNIFIED / f"aemet_weather_daily_baleares_{run_id}.parquet"
    atomic_parquet(baleares, stations_out)
    atomic_parquet(daily_baleares, daily_out)
    latest = {
        "status": "passed", "source_id": SOURCE_ID, "run_id": run_id,
        "raw_manifest": str((snapshot / "manifest.json").relative_to(ROOT)),
        "stations_output": str(stations_out.relative_to(ROOT)), "daily_output": str(daily_out.relative_to(ROOT)),
        "period": {"start": start.isoformat(), "end": end.isoformat()}, "attribution": source["attribution"],
    }
    atomic_json(latest, LATEST)
    report = {
        **latest, "station_inventory_records": int(len(stations)), "balearic_stations": int(len(baleares)),
        "daily_records_baleares": int(len(daily_baleares)), "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Es contexto meteorológico de estaciones; no interpola microclima a cada ruta.",
            "Las condiciones deben corresponder a la fecha y hora de la ruta antes de interpretarlas.",
            "No se incorpora al TSMAI sin una validación metodológica específica.",
        ],
    }
    atomic_json(report, REPORT)
    return report


def main_aemet_weather_context():
    # Define los argumentos del comando
    default_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    parser = argparse.ArgumentParser(description="Ingiere observaciones AEMET reales como contexto trazable.")
    parser.add_argument("--start", type=parse_date, default=default_date, help="Fecha inicial YYYY-MM-DD; por defecto, ayer UTC.")
    parser.add_argument("--end", type=parse_date, default=default_date, help="Fecha final YYYY-MM-DD; por defecto, ayer UTC.")
    parser.add_argument("--execute", action="store_true", help="Autoriza la consulta remota y la escritura de snapshots raw/unified.")
    args = parser.parse_args()
    result = execute(args.start, args.end) if args.execute else plan(args.start, args.end)
    print(json.dumps(result, ensure_ascii=False, indent=2))




import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
SAMPLE_LATEST = CURATED / "latest_multimodal_route_sample.json"
WEATHER_LATEST = CURATED / "latest_aemet_weather_context.json"
LATEST_OUTPUT = CURATED / "latest_current_sample_aemet_route_context.json"
REPORT = ROOT / "docs" / "current_sample_aemet_route_context_report.json"
METRIC_CRS = "EPSG:25831"
WEATHER_COLUMNS = ["indicativo", "nombre_station", "observation_date", "tmed_c", "tmin_c", "tmax_c", "prec_mm", "wind_mean_ms", "wind_gust_ms"]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def inputs():
    sample_meta = json.loads(SAMPLE_LATEST.read_text(encoding="utf-8"))
    weather_meta = json.loads(WEATHER_LATEST.read_text(encoding="utf-8"))
    sample_path = ROOT / sample_meta["sample_output"]
    weather_path = ROOT / weather_meta["output"]
    sample = pd.read_parquet(sample_path).sort_values("od_id", kind="stable").reset_index(drop=True)
    weather = gpd.read_parquet(weather_path)
    required_sample = {"od_id", "origin_latitude", "origin_longitude", "destination_latitude", "destination_longitude"}
    required_weather = {"indicativo", "observation_date", "geom"}
    if missing := required_sample.difference(sample.columns):
        raise ValueError(f"La muestra OTP no contiene: {sorted(missing)}")
    if missing := required_weather.difference(weather.columns):
        raise ValueError(f"El contexto AEMET no contiene: {sorted(missing)}")
    if weather.empty or weather.geom.isna().any():
        raise ValueError("No hay estaciones AEMET válidas para construir contexto.")
    return sample, weather, {
        "sample": str(sample_path.relative_to(ROOT)),
        "routing_date": sample_meta["routing_date"],
        "routing_time": sample_meta["routing_time"],
        "aemet_context": str(weather_path.relative_to(ROOT)),
        "aemet_source_run_id": weather_meta["source_run_id"],
        "aemet_observation_dates": sorted(weather["observation_date"].dropna().astype(str).unique().tolist()),
    }


def readiness():
    sample, weather, provenance = inputs()
    route_date = provenance["routing_date"]
    matching = weather.loc[weather["observation_date"].astype(str).eq(route_date)].copy()
    status = "ready" if not matching.empty else "blocked_date_mismatch"
    report = {
        "status": status,
        "sample_pairs": int(len(sample)),
        "routing_date": route_date,
        "routing_time": provenance["routing_time"],
        "aemet_observation_dates": provenance["aemet_observation_dates"],
        "matching_aemet_stations": int(len(matching)),
        "provenance": provenance,
        "message": (
            "La fecha AEMET coincide; añade --execute para publicar contexto de estaciones cercano a cada extremo."
            if status == "ready"
            else "No se publica contexto: las observaciones AEMET no corresponden a la fecha documentada de las rutas OTP."
        ),
        "limitations": [
            "La estación más cercana es contexto puntual diario, no meteorología interpolada de la ruta.",
            "El resultado no se incorpora a TSMAI ni modifica recomendaciones de ruta.",
        ],
    }
    return report, sample, matching, provenance


def nearest_context(points, stations, prefix):
    # Busca la estacion mas cercana
    points_metric = points.to_crs(METRIC_CRS)
    stations_metric = stations.to_crs(METRIC_CRS)
    pairs, distances = stations_metric.sindex.nearest(points_metric.geom, return_distance=True)
    matched = {int(origin): (int(station), float(distance)) for origin, station, distance in zip(pairs[0], pairs[1], distances)}
    rows = []
    available = [column for column in WEATHER_COLUMNS if column in stations.columns]
        # Recorre cada punto de ruta
    for position in range(len(points)):
        station_position, distance = matched[position]
        station = stations.iloc[station_position]
        row = {f"{prefix}_station_distance_m": round(distance, 1)}
        for column in available:
            row[f"{prefix}_{column}"] = station[column]
        rows.append(row)
    return pd.DataFrame(rows, index=points.index)


def execute():
    # Publica el contexto AEMET vigente
    report, sample, stations, provenance = readiness()
    if report["status"] != "ready":
        return report
    origins = gpd.GeoDataFrame(sample[["od_id"]].copy(), geometry=gpd.points_from_xy(sample["origin_longitude"], sample["origin_latitude"]), crs="EPSG:4326")
    dests = gpd.GeoDataFrame(sample[["od_id"]].copy(), geometry=gpd.points_from_xy(sample["destination_longitude"], sample["destination_latitude"]), crs="EPSG:4326")
    result = sample.copy()
    result = result.join(nearest_context(origins, stations, "origin"))
    result = result.join(nearest_context(dests, stations, "dest"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = CURATED / f"current_sample_aemet_route_context_{run_id}.parquet"
    temporary = output.with_suffix(".part.parquet")
    result.to_parquet(temporary, index=False)
    temporary.replace(output)
    report.update({
        "status": "passed", "run_id": run_id,
        "output": str(output.relative_to(ROOT)), "records": int(len(result)),
        "method": "Estación AEMET diaria observada más cercana a origen y destino; sin interpolación de ruta.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    write_json(LATEST_OUTPUT, report)
    write_json(REPORT, report)
    return report


def main_current_sample_aemet_route_context():
    parser = argparse.ArgumentParser(description="Construye contexto AEMET de rutas sólo para fechas coincidentes.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    report = execute() if args.execute else readiness()[0]
    print(json.dumps(report, ensure_ascii=False, indent=2))




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_aemet_mallorca_weather_context":
        main_aemet_mallorca_weather_context()
        sys.exit(0)
    if task_name == "run_build_aemet_weather_context":
        main_aemet_weather_context()
        sys.exit(0)
    if task_name == "run_build_current_sample_aemet_route_context":
        main_current_sample_aemet_route_context()
        sys.exit(0)
    print(f"Task {task_name} not found.")

