from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *


from pathlib import Path
import os

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data" / "curated" / "od_multimodal_priority_index.parquet"
OTP_URL = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
QUERY = """
query BicycleRoute($from: InputCoordinates!, $to: InputCoordinates!) {
  plan(from: $from, to: $to, date: "2026-09-03", time: "12:00",
       transportModes: [{mode: BICYCLE}], numItineraries: 1) {
    itineraries { duration legs { mode distance } }
    routingErrors { code description }
  }
}
"""


def main_validate_bicycle_routes():
    cases = pd.read_parquet(CASES).sort_values("priority_index_score", ascending=False)
    res = []
    for _, row in cases.iterrows():
        # Consulta ruta en bicicleta OTP
        payload = {"query": QUERY, "variables": {"from": {"lat": float(row.origin_lat), "lon": float(row.origin_lon)}, "to": {"lat": float(row.destination_lat), "lon": float(row.destination_lon)}}}
        response = requests.post(OTP_URL, json=payload, timeout=60)
        data = response.json()
        plan = data.get("data", {}).get("plan", {})
        itinerary = (plan.get("itineraries") or [None])[0]
        res.append({"od_id": row.od_id, "origin": row.origin_name, "dest": row.destination_name, "bike_status": "ok" if itinerary else "no_route", "duration_min": round(itinerary["duration"] / 60, 1) if itinerary else None, "distance_m": round(sum(leg["distance"] for leg in itinerary["legs"]), 0) if itinerary else None})
    result = pd.DataFrame(res)
    print(result.to_string(index=False))
    output = ROOT / "data" / "curated" / "otp_bicycle_route_validation.parquet"
    result.to_parquet(output, index=False)
    print(f"OK Validacion guardada: {output}")






import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "reviews_licensed.csv"
SURVEY_RAW = ROOT / "data" / "raw" / "licensed_mobility_survey"
OUT = ROOT / "data" / "unified" / "reviews_licensed_validated.parquet"
REPORT = ROOT / "docs" / "reviews_licensing_validation_report.json"
ALLOWED_LICENSES = {"CC-BY", "CC-BY-4.0", "CC0", "CC0-1.0", "CONSENT"}


def latest_authorized_input():
    latest = SURVEY_RAW / "latest.json"
    if not latest.exists():
        if RAW.exists():
            return RAW, {"source": "legacy_local_file", "warning": "Migra el corpus a un snapshot con atestación P12 antes de publicar."}
        raise FileNotFoundError(
            "Falta un snapshot de encuesta autorizada. Ejecuta ingest_licensed_mobility_survey.py con CSV real y manifiesto de consentimiento."
        )
    pointer = json.loads(latest.read_text(encoding="utf-8"))
    manifest_path = ROOT / pointer["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"source_id", "payload_file", "consent_attestation_file", "approved_purposes", "personal_data_removed"}
    if missing := required.difference(manifest):
        raise ValueError(f"El manifest raw de encuesta no contiene: {sorted(missing)}")
    if manifest["source_id"] != "licensed_mobility_survey" or manifest["personal_data_removed"] is not True:
        raise ValueError("El snapshot no acredita la fuente P12 ni la minimización de datos.")
    expected_purposes = {"academic_analysis", "machine_learning_inference", "aggregated_publication"}
    if not expected_purposes.issubset(set(manifest["approved_purposes"])):
        raise ValueError("El consentimiento no autoriza todos los usos analíticos y de publicación agregada declarados.")
    return manifest_path.parent / manifest["payload_file"], {"source": "licensed_mobility_survey", "raw_manifest": str(manifest_path.relative_to(ROOT))}


def main_validate_licensed_reviews():
    parser = argparse.ArgumentParser(description="Valida textos de movilidad previamente autorizados.")
    parser.add_argument("--input", type=Path, help="Sólo para migrar un CSV autorizado ya existente; se recomienda el snapshot P12.")
    args = parser.parse_args()
    input_path, provenance = (args.input, {"source": "manual_migration"}) if args.input else latest_authorized_input()
    if not input_path or not input_path.exists():
        raise FileNotFoundError(f"No existe el CSV autorizado: {input_path}")
    reviews = pd.read_csv(input_path)
    required = {"text", "license", "source_url"}
    missing = required.difference(reviews.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {sorted(missing)}")
    if "accommodation_id" not in reviews.columns and "municipality" not in reviews.columns:
        raise ValueError("Cada reseña debe enlazarse a accommodation_id o municipality; no se agregan textos sin referencia territorial.")
    reviews["text"] = reviews["text"].astype("string").str.strip()
    reviews["license"] = reviews["license"].astype("string").str.upper().str.strip()
    source = reviews["source_url"].astype("string").str.strip()
    valid_source = source.str.startswith(("http://", "https://"), na=False) | source.eq("local_collection_with_informed_consent")
    valid = reviews["text"].notna() & reviews["text"].str.len().ge(15) & reviews["license"].isin(ALLOWED_LICENSES) & valid_source
    rejected = reviews.loc[~valid].copy()
    accepted = reviews.loc[valid].copy()
    accepted["review_id"] = accepted.get("review_id", pd.Series(index=accepted.index, dtype="string")).fillna(pd.Series([f"review_{idx:06d}" for idx in range(1, len(accepted) + 1)], index=accepted.index))
        # Elimina columnas con datos personales
    pii_columns = [column for column in ["author", "author_name", "email", "user_id", "profile_url"] if column in accepted.columns]
    accepted = accepted.drop(columns=pii_columns)
    accepted.to_parquet(OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "input_records": int(len(reviews)), "accepted_records": int(len(accepted)), "rejected_records": int(len(rejected)),
        "provenance": provenance,
        "accepted_licenses": sorted(accepted["license"].dropna().unique().tolist()), "removed_personal_data_columns": pii_columns,
        "limitations": ["La validación técnica de licencia no sustituye la comprobación jurídica del origen.", "El texto se pseudonimiza y no se redistribuyen identificadores personales."],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Reseñas autorizadas: {len(accepted)} de {len(reviews)}")






import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
DOCS = ROOT / "docs"
INPUT = CURATED / "od_multimodal_routes_massive_exploratory.parquet"
SUMMARY = CURATED / "od_multimodal_routes_massive_summary.parquet"
REPORT = DOCS / "async_massive_processing_validation_report.json"


def percent(value):
    # Calcula el porcentaje redondeado
    return round(100 * value.mean(), 2) if len(value) else 0.0


def main_validate_massive_routes():
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe el resultado masivo: {INPUT}")
    data = pd.read_parquet(INPUT)
    required = {"od_id", "origin_municipality", "origin_access_band", "query_status", "total_duration_min", "walk_distance_m", "has_transit"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")
    ok = data.loc[data["query_status"].eq("ok")].copy()
    issues = {
        "duplicate_od_id": int(data["od_id"].duplicated().sum()),
        "missing_od_id": int(data["od_id"].isna().sum()),
        "negative_duration_for_ok": int((ok["total_duration_min"] < 0).sum()),
        "negative_walk_distance_for_ok": int((ok["walk_distance_m"] < 0).sum()),
        "missing_duration_for_ok": int(ok["total_duration_min"].isna().sum()),
    }
    if any(issues.values()):
        raise ValueError(f"No se supera el contrato de calidad: {issues}")
    grouped = (
        data.groupby(["origin_municipality", "origin_access_band"], dropna=False)
        .agg(
            pares=("od_id", "size"),
            rutas_otp_ok=("query_status", lambda values: int((values == "ok").sum())),
            con_transporte_publico=("has_transit", lambda values: int(values.fillna(False).sum())),
            duracion_mediana_min=("total_duration_min", "median"),
            caminata_mediana_m=("walk_distance_m", "median"),
        )
        .reset_index()
    )
    grouped["tasa_ruta_otp_ok_pct"] = (100 * grouped["rutas_otp_ok"] / grouped["pares"]).round(2)
    grouped["tasa_transporte_publico_pct"] = (100 * grouped["con_transporte_publico"] / grouped["pares"]).round(2)
    grouped.to_parquet(SUMMARY, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_status": "passed",
        "scope": "Exploratory nearest eligible tourism/historic dest screening; it is not an observed demand model.",
        "source_artifact": INPUT.name,
        "summary_artifact": SUMMARY.name,
        "pairs_screened": int(len(data)),
        "routing": {
            "ok": int(len(ok)),
            "ok_rate_pct": percent(data["query_status"].eq("ok")),
            "no_itinerary": int(data["query_status"].eq("no_itinerary").sum()),
            "with_transit_among_ok_pct": percent(ok["has_transit"].fillna(False)) if len(ok) else 0.0,
            "median_duration_min_among_ok": round(float(ok["total_duration_min"].median()), 2),
            "p90_duration_min_among_ok": round(float(ok["total_duration_min"].quantile(0.90)), 2),
            "median_walk_distance_m_among_ok": round(float(ok["walk_distance_m"].median()), 2),
        },
        "quality_checks": issues,
        "interpretation": [
            "Every valid accommodation was paired with its nearest eligible named tourism/historic dest between 2 and 20 km.",
            "The result is a reproducible screening at the documented GTFS date/time, not a representative visitor-demand sample.",
            "No-itinerary outcomes are retained as analytical outcomes and are not imputed.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validation passed: {len(ok)}/{len(data)} OTP routes")
    print(f"Summary: {SUMMARY}")
    print(f"Report: {REPORT}")






import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
OTP_INPUTS = ROOT / "data" / "otp" / "latest_otp_inputs.json"
REPORT = ROOT / "docs" / "otp_service_validation_report.json"
ENDPOINT = os.getenv("OTP_URL", "http://localhost:8080/otp/gtfs/v1")
QUERY = """
query ValidateRoute($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!, $modes: [TransportMode]!) {
  plan(from: $from, to: $to, date: $date, time: $time, transportModes: $modes, numItineraries: 1) {
    itineraries { duration walkDistance legs { mode distance duration route { shortName } } }
    routingErrors { code description }
  }
}
"""


def atomic_json_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_access():
    import geopandas as gpd

    # Carga alojamientos con parada cercana
    latest = CURATED / "latest_public_transport_access.json"
    if not latest.exists():
        raise FileNotFoundError("No existe acceso TIB curado. Ejecuta build_tib_public_transport_access.py.")
    metadata = json.loads(latest.read_text(encoding="utf-8"))
    path = ROOT / metadata["accommodation_access_output"]
    data = gpd.read_parquet(path)
    eligible = data.loc[data["distance_to_nearest_tib_stop_m"].le(400) & data.geom.notna()].copy()
    if len(eligible) < 2:
        raise ValueError("No hay al menos dos alojamientos con parada TIB a 400 m para validar OTP.")
    return eligible

def choose_pairs(data):
    # Elige pares representativos para validar
    source = data.reset_index(drop=True)
    projected = source.to_crs("EPSG:25831")
    municipalities = projected.groupby("municipality", dropna=False)
    local_group = next((group for _, group in municipalities if len(group) >= 2), None)
    if local_group is None:
        raise ValueError("No hay dos alojamientos elegibles en el mismo municipio para validar WALK.")
    local = local_group.iloc[:2]
    origin_index = 0
    distances = projected.geom.distance(projected.geom.iloc[origin_index])
    transit_index = int(distances.idxmax())
    if transit_index == origin_index:
        raise ValueError("No se pudo seleccionar un destino TRANSIT distinto.")
    return (
        (source.iloc[int(local.index[0])].to_dict(), source.iloc[int(local.index[1])].to_dict()),
        (source.iloc[origin_index].to_dict(), source.iloc[transit_index].to_dict()),
    )


def coords(row):
    geom = row["geom"]
    return {"lat": float(geom.y), "lon": float(geom.x)}


def plan(origin, dest, mode, routing_date, routing_time):
    variables = {
        "from": coords(origin),
        "to": coords(dest),
        "date": routing_date.isoformat(),
        "time": routing_time.strftime("%H:%M"),
        "modes": [{"mode": mode}],
    }
    try:
        response = requests.post(ENDPOINT, json={"query": QUERY, "variables": variables}, timeout=60)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"status": "server_error", "message": str(exc), "variables": variables}
    except ValueError:
        return {"status": "invalid_json", "variables": variables}
    if payload.get("errors"):
        return {"status": "graphql_error", "errors": payload["errors"], "variables": variables}
    route = (payload.get("data") or {}).get("plan") or {}
    itineraries = route.get("itineraries") or []
    errors = route.get("routingErrors") or []
    if not itineraries:
        return {"status": "no_itinerary", "routing_errors": errors, "variables": variables}
    itinerary = itineraries[0]
    return {
        "status": "itinerary_found",
        "duration_min": round(float(itinerary["duration"]) / 60, 2),
        "walk_distance_m": round(float(itinerary.get("walkDistance", 0)), 1),
        "modes_returned": [leg.get("mode") for leg in itinerary.get("legs") or []],
            # Resume el itinerario devuelto OTP
        "variables": variables,
    }


def point_summary(row):
    # Resume datos clave del alojamiento
    return {
        "accommodation_id": str(row["accommodation_id"]),
        "commercial_name": row.get("commercial_name"),
        "municipality": row.get("municipality"),
        "distance_to_nearest_tib_stop_m": round(float(row["distance_to_nearest_tib_stop_m"]), 1),
    }


def main_validate_otp_service():
    # Valida que OTP responda correctamente
    if not OTP_INPUTS.exists():
        raise FileNotFoundError("No existe la preparación de entradas OTP.")
    otp_inputs = json.loads(OTP_INPUTS.read_text(encoding="utf-8"))
    graph = ROOT / otp_inputs["build_directory"] / "graph.obj"
    if not graph.exists() or graph.stat().st_size == 0:
        raise FileNotFoundError(f"No existe un graph.obj construido en {graph.parent}.")
    access = load_access()
    walk_pair, transit_pair = choose_pairs(access)
    routing_date = date.today() + timedelta(days=2)
    routing_time = time(10, 0)
    walk = plan(*walk_pair, "WALK", routing_date, routing_time)
    transit = plan(*transit_pair, "TRANSIT", routing_date, routing_time)
    hard_failures = [result for result in (walk, transit) if result["status"] in {"server_error", "invalid_json", "graphql_error"}]
    report = {
        "validation_status": "passed" if walk["status"] == "itinerary_found" and not hard_failures else "failed",
        "otp_endpoint": ENDPOINT,
        "otp_build_id": otp_inputs["build_id"],
        "graph_file": str(graph.relative_to(ROOT)),
        "graph_bytes": graph.stat().st_size,
        "routing_date": routing_date.isoformat(),
        "routing_time": routing_time.strftime("%H:%M"),
        "walk_pair": [point_summary(item) for item in walk_pair],
        "transit_pair": [point_summary(item) for item in transit_pair],
        "walk_result": walk,
        "transit_result": transit,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "interpretation": "La prueba confirma disponibilidad técnica del motor. La existencia o ausencia de un itinerario TRANSIT depende del horario GTFS para fecha y hora documentadas.",
    }
    atomic_json_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["validation_status"] != "passed":
        raise SystemExit(1)






import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from project_tools import build_case_pdf


def main_validate_pdf_export():
    from pypdf import PdfReader

    # Construye un caso de prueba
    case = pd.Series(
        {
            "od_id": "VALIDATION",
            "origin_name": "Origen de prueba",
            "destination_name": "Destino de prueba",
            "origin_municipality": "Mallorca",
            "priority_level": "alta",
            "priority_index_score": 0.825,
            "analysis_outcome": "Validación PDF",
            "recommendation": "Revisar en campo",
            "evidence": "Ficha de validación técnica.",
        }
    )
    output = ROOT / "output" / "pdf" / "validacion_ficha.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    route = {
        "status": "ok",
        "itinerary": {
            "legs": [
                {"mode": "WALK", "distance": 600, "duration": 480, "legGeometry": {"points": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"}},
                {"mode": "BUS", "distance": 1200, "duration": 600, "route": {"shortName": "122"}, "legGeometry": {"points": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"}},
            ]
        },
    }
    output.write_bytes(build_case_pdf(case, route, {"generated_at": "2026-09-10 20:00 UTC"}))
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 1
    assert "Ficha de caso VALIDATION" in text
    assert "Origen de prueba" in text
    assert "122" in text
    print(f"PDF export validation passed: {output}")






import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "source_registry.json"
DEFAULT_REPORT = ROOT / "docs" / "source_registry_validation_report.json"
REQUIRED_FIELDS = {
    "source_id", "layer", "provider", "source_url", "download_url", "license",
    "attribution", "coverage", "refresh_frequency", "data_kind", "status",
    "automated_download",
}


def is_url_or_local_collection(value):
    if value in {"not_applicable", "local_collection_with_informed_consent"}:
        return True
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_registry(registry):
    policy = registry.get("policy") or {}
    allowed_licenses = set(policy.get("allowed_licenses") or [])
    allowed_statuses = set(policy.get("allowed_statuses") or [])
    sources = registry.get("sources") or []
    errors = []
    warnings = []
    approved = []
    blocked = []
    seen_ids = set()

    if not sources:
        errors.append("El registro no contiene fuentes.")
    for source in sources:
        source_id = str(source.get("source_id", "<sin_id>"))
        missing = sorted(field for field in REQUIRED_FIELDS if field not in source or source[field] in (None, ""))
        if missing:
            errors.append(f"{source_id}: faltan campos obligatorios {missing}.")
            continue
        if source_id in seen_ids:
            errors.append(f"Identificador de fuente duplicado: {source_id}.")
        seen_ids.add(source_id)
        if source["status"] not in allowed_statuses:
            errors.append(f"{source_id}: estado no permitido {source['status']!r}.")
        if not is_url_or_local_collection(str(source["source_url"])):
            errors.append(f"{source_id}: source_url debe ser HTTPS o una colección primaria declarada.")
        if not is_url_or_local_collection(str(source["download_url"])):
            errors.append(f"{source_id}: download_url debe ser HTTPS, not_applicable o colección primaria declarada.")
        if source["status"] == "approved":
            if source["license"] not in allowed_licenses:
                errors.append(f"{source_id}: una fuente approved usa licencia no admitida: {source['license']}.")
            else:
                approved.append(source_id)
        else:
            blocked.append(source_id)
            warnings.append(f"{source_id}: bloqueada para ingesta ({source['status']}).")
            if source["status"] == "pending_permission" and source["license"] != "UNVERIFIED":
                warnings.append(f"{source_id}: permiso pendiente pero licencia no marcada como UNVERIFIED.")
    return {
        "validation_status": "passed" if not errors else "failed",
        "approved_sources": approved,
        "blocked_sources": blocked,
        "errors": errors,
        "warnings": warnings,
    }


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main_validate_source_registry():
    parser = argparse.ArgumentParser(description="Valida licencias y metadatos de las fuentes del proyecto.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = validate_registry(registry)
    result.update({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry": str(args.registry.relative_to(ROOT)),
        "registry_sha256": sha256(args.registry),
        "source_count": len(registry.get("sources") or []),
    })
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Registro de fuentes: {result['validation_status']}; aprobadas: {len(result['approved_sources'])}; bloqueadas: {len(result['blocked_sources'])}")
    if result["errors"]:
        for error in result["errors"]:
            print(f"ERROR: {error}")
        raise SystemExit(1)




def main_validate_streamlit_app():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(ROOT / "app" / "streamlit_app.py")
    app.run(timeout=180)
    assert not app.exception, [item.value for item in app.exception]
    print("Streamlit dashboard validation passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_") else "run_" + args.task

    if task_name == "run_validate_bicycle_routes":
        main_validate_bicycle_routes()
        sys.exit(0)
    if task_name == "run_validate_licensed_reviews":
        main_validate_licensed_reviews()
        sys.exit(0)
    if task_name == "run_validate_massive_routes":
        main_validate_massive_routes()
        sys.exit(0)
    if task_name == "run_validate_otp_service":
        main_validate_otp_service()
        sys.exit(0)
    if task_name == "run_validate_pdf_export":
        main_validate_pdf_export()
        sys.exit(0)
    if task_name == "run_validate_source_registry":
        main_validate_source_registry()
        sys.exit(0)
    if task_name == "run_validate_streamlit_app":
        main_validate_streamlit_app()
        sys.exit(0)
    print(f"Task {task_name} not found.")


