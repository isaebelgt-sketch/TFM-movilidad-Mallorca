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

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "dgt_accidents_2024.xlsx"
IBESTAT = ROOT / "data" / "raw" / "ibestat_000060A_000004.csv"
OUT = ROOT / "data" / "curated" / "municipality_road_safety_context_dgt_2024.parquet"
REPORT = ROOT / "docs" / "road_safety_context_dgt_2024_report.json"
URL = "https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/publicaciones/Ficheros_microdatos_de_accidentalidad_con_victimas/TABLA_ACCIDENTES_24.XLSX"


def main_road_safety_context():
    parser = argparse.ArgumentParser(description="Construye contexto agregado de siniestralidad DGT 2024.")
    parser.add_argument("--execute", action="store_true", help="Autoriza la escritura del artefacto curado de contexto.")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({
            "status": "dry_run",
            "input": str(RAW.relative_to(ROOT)),
            "message": "No se ha leído ni escrito ningún artefacto. Añade --execute para procesar el microdato local.",
        }, ensure_ascii=False, indent=2))
        return
    if not RAW.exists():
        raise FileNotFoundError("Falta el microdato DGT 2024. Descárgalo desde la URL documentada antes de ejecutar.")
    columns = ["COD_PROVINCIA", "COD_MUNICIPIO", "ISLA", "TOTAL_VICTIMAS_30DF", "TOTAL_MU30DF", "TOT_PEAT_MU30DF", "TOT_BICI_MU30DF", "TOTAL_VICTIMAS_24H"]

    accidents = pd.read_excel(RAW, sheet_name="ACCIDENTES_24", usecols=columns, engine="calamine")
    balearic = accidents.loc[accidents["COD_PROVINCIA"].eq(7)].copy()
    balearic["municipality_code"] = pd.to_numeric(balearic["COD_MUNICIPIO"], errors="coerce").astype("Int64").astype("string").str.zfill(5)
    summary = balearic.groupby("municipality_code", dropna=False).agg(
        accidents_with_victims_2024=("COD_MUNICIPIO", "size"),
        victims_30_days=("TOTAL_VICTIMAS_30DF", "sum"), deaths_30_days=("TOTAL_MU30DF", "sum"),
        pedestrian_deaths_30_days=("TOT_PEAT_MU30DF", "sum"), bicycle_deaths_30_days=("TOT_BICI_MU30DF", "sum"),
        victims_24h=("TOTAL_VICTIMAS_24H", "sum"),
    ).reset_index()
    ibestat = pd.read_csv(IBESTAT, usecols=["TERRITORIO_CODE", "TERRITORIO#es"])
    municipalities = ibestat.dropna().drop_duplicates("TERRITORIO_CODE").rename(columns={"TERRITORIO_CODE": "municipality_code", "TERRITORIO#es": "municipality"})
    municipalities["municipality_code"] = municipalities["municipality_code"].astype("string").str.zfill(5)
    result = summary.merge(municipalities, on="municipality_code", how="left", validate="one_to_one")
    result["municipality_name_available"] = result["municipality"].notna()
    result.to_parquet(OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "source": "DGT, Ficheros de microdatos de accidentes con víctimas 2024 (CC-BY 4.0).",
        "source_url": URL, "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "balearic_accident_records": int(len(balearic)), "municipal_codes": int(len(summary)), "municipalities_named_from_ibestat": int(result["municipality_name_available"].sum()),
        "method": "Agregación municipal de registros DGT con COD_PROVINCIA=7; unión nominal sólo cuando el código aparece en la fuente IBESTAT local.",
        "limitations": ["No hay coordenadas: no se puede calcular proximidad a una ruta, intersección vial ni riesgo por segmento.", "La siniestralidad observada no es percepción de seguridad ni una tasa ajustada por exposición.", "No se incorpora al TSMAI ni se usa para recomendar automáticamente una ruta."],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK DGT: {len(balearic)} siniestros Baleares; {len(summary)} códigos municipales")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_road_safety_context":
        main_road_safety_context()
        sys.exit(0)
    print(f"Task {task_name} not found.")
