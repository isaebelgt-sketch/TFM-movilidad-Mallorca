from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *




import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
URL = "https://intranet.caib.es/opendatacataleg/files/dataset/estacions-qualitat-aire/estacions-qualitat-aire.geojson"
RAW = ROOT / "data" / "raw" / "caib_air_quality_stations.geojson"
accs = ROOT / "data" / "curated" / "accommodations_transport_access_baseline.parquet"
OUT_STATIONS = ROOT / "data" / "unified" / "caib_air_quality_stations.parquet"
OUT_ACCOMMODATIONS = ROOT / "data" / "curated" / "accommodations_air_quality_station_context.parquet"
REPORT = ROOT / "docs" / "air_quality_context_report.json"
METRIC_CRS = "EPSG:25831"


def normalized(name):
    # Normaliza el nombre de columna
    return "".join(character for character in name.lower() if character.isalnum())


def pollutant_columns(frame):
    # Detecta columnas de contaminantes CAIB
    tokens = ("so2", "no2", "co", "o3", "pm10", "pm25", "benzene", "benze")
    return [column for column in frame.columns if any(token in normalized(column) for token in tokens)]


def main_air_quality_context():
    parser = argparse.ArgumentParser(description="Descarga estaciones CAIB como contexto de calidad del aire.")
    parser.add_argument("--execute", action="store_true", help="Autoriza la descarga remota y la escritura de artefactos de contexto.")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({
            "status": "dry_run",
            "source_url": URL,
            "message": "No se ha descargado ninguna fuente ni escrito resultados. Añade --execute para actualizar el contexto.",
        }, ensure_ascii=False, indent=2))
        return
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    RAW.write_bytes(response.content)
    stations = gpd.read_file(RAW)
    stations = stations.loc[stations.geometry.notna() & ~stations.geometry.is_empty].copy()
    stations.to_parquet(OUT_STATIONS, index=False)

    accs = gpd.read_parquet(accs)
    sources = accs.to_crs(METRIC_CRS)
    targets = stations.to_crs(METRIC_CRS)
    pairs, distances = targets.sindex.nearest(sources.geometry, return_distance=True)
    nearest = sources.iloc[pairs[0]][["accommodation_id"]].copy()
    nearest["distance_to_air_quality_station_m"] = distances
    nearest["nearest_air_quality_station_index"] = pairs[1]
    nearest = nearest.loc[~nearest["accommodation_id"].duplicated(keep="first")]
    context = accs[["accommodation_id", "municipality_raw", "geom"]].merge(nearest, on="accommodation_id", how="left", validate="one_to_one")
    context.to_parquet(OUT_ACCOMMODATIONS, index=False)

    pollutants = pollutant_columns(stations)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Govern de les Illes Balears, Estacions de mesura de la qualitat de l'aire (CC-BY).",
        "source_url": URL,
        "raw_sha256": hashlib.sha256(response.content).hexdigest(),
        "stations": int(len(stations)), "pollutant_columns_detected": pollutants,
        "method": "Asignación de la estación CAIB más próxima en CRS métrico a cada alojamiento.",
        "limitations": ["La proximidad a una estación no estima exposición ni calidad del aire de un alojamiento o ruta.", "Las observaciones son puntuales y pueden cambiar con el tiempo; no se integran en TSMAI.", "Para una evaluación de exposición se requeriría una serie temporal validada y un modelo espacial de interpolación."],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Estaciones CAIB: {len(stations)}; contaminantes detectados: {len(pollutants)}")







if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_air_quality_context":
        main_air_quality_context()
        sys.exit(0)
    print(f"Task {task_name} not found.")
