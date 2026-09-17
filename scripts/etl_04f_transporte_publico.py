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


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
V9_V8_INPUT = CURATED / "accommodations_tsmai_v8_temporal_transit.parquet"
V9_SUMMER_INPUT = CURATED / "transit_temporal_weekday_am_peak_weekday_midday_weekday_evening_weekend_midday.parquet"
V9_WINTER_INPUT = CURATED / "transit_temporal_winter_2027_winter_weekday_am_peak_winter_weekday_midday_winter_weekday_evening_winter_weekend_midday.parquet"
V9_SEASONAL_COMPARISON = CURATED / "transit_seasonal_comparison_sep2026_vs_winter2027.parquet"
V9_OUTPUT = CURATED / "accommodations_tsmai_v9_seasonal_transit.parquet"
V9_REPORT = ROOT / "docs" / "tsmai_v9_seasonal_transit_report.json"
WEIGHTS = {
    "public_transport_proximity_score": 0.12,
    "public_transport_service_score": 0.08,
    "temporal_transit_destination_score": 0.20,
    "cycling_evidence_proximity_score": 0.10,
    "bicycle_network_destination_score": 0.10,
    "pedestrian_evidence_proximity_score": 0.20,
    "walk_network_destination_score": 0.20,
}

def temporal_transit_score(status, duration_min):
    # Puntua duracion de transporte publico
    score = pd.Series(0.0, index=duration_min.index, dtype="float64")
    minutes = pd.to_numeric(duration_min, errors="coerce")
    valid = status.astype("string").eq("ok") & minutes.notna()
    score.loc[valid & minutes.le(60)] = 1.0
    score.loc[valid & minutes.gt(60) & minutes.le(90)] = 0.70
    score.loc[valid & minutes.gt(90) & minutes.le(120)] = 0.40
    return score


def sha256(path):
    # Calcula el hash SHA-256 del archivo
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_parquet(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    if isinstance(frame, gpd.GeoDataFrame):
        frame.to_parquet(temporary, index=False)
    else:
        frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def atomic_json(payload, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def campaign_score(frame, campaign):
    required = {"accommodation_id", "scenario_id", "route_status", "route_duration_min"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"La campaña {campaign} no contiene: {sorted(missing)}")
    if frame["accommodation_id"].isna().any():
        raise ValueError(f"La campaña {campaign} contiene alojamientos sin identificador.")
    scored = frame.copy()
    scored["scenario_score"] = temporal_transit_score(scored["route_status"], scored["route_duration_min"])
    result = scored.groupby("accommodation_id", dropna=False).agg(
        **{
            f"{campaign}_transit_score": ("scenario_score", "mean"),
            f"{campaign}_transit_scenarios": ("scenario_id", "size"),
            f"{campaign}_transit_ok_scenarios": ("route_status", lambda values: int(values.eq("ok").sum())),
        }
    ).reset_index()
    if not result[f"{campaign}_transit_scenarios"].eq(4).all():
        raise ValueError(f"Cada alojamiento debe tener cuatro escenarios {campaign}.")
    return result


def main_current_tsmai_v9_seasonal_transit():
    # Verifica que existan los insumos
    required_files = [V9_V8_INPUT, V9_SUMMER_INPUT, V9_WINTER_INPUT, V9_SEASONAL_COMPARISON]
    missing_files = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
        # Aborta si falta algun insumo
    if missing_files:
        raise FileNotFoundError(f"Faltan artefactos P2 requeridos: {missing_files}")
    v8 = gpd.read_parquet(V9_V8_INPUT)
    summer = campaign_score(pd.read_parquet(V9_SUMMER_INPUT), "summer")
    winter = campaign_score(pd.read_parquet(V9_WINTER_INPUT), "winter")
    comparison = pd.read_parquet(V9_SEASONAL_COMPARISON)
    geometry_column = v8.geometry.name
    required_v8 = {"accommodation_id", geometry_column, *WEIGHTS}
    required_comparison = {"accommodation_id", "seasonal_change", "transit_ok_share_delta_pp", "temporal_transit_level_baseline", "temporal_transit_level_seasonal"}
    if missing := required_v8.difference(v8.columns):
        raise ValueError(f"TSMAI v8 no contiene: {sorted(missing)}")
    if missing := required_comparison.difference(comparison.columns):
        raise ValueError(f"La comparación P2 no contiene: {sorted(missing)}")
    if any(frame["accommodation_id"].duplicated().any() for frame in [v8, summer, winter, comparison]):
        # Aborta si hay ids duplicados
        raise ValueError("Todos los insumos de V9 deben tener un accommodation_id único.")
    data = v8.merge(summer, on="accommodation_id", how="left", validate="one_to_one")
    data = data.merge(winter, on="accommodation_id", how="left", validate="one_to_one")
    data = data.merge(comparison[list(required_comparison)], on="accommodation_id", how="left", validate="one_to_one")
    seasonal_columns = ["summer_transit_score", "winter_transit_score", "seasonal_change"]
    if len(data) != len(v8) or data[seasonal_columns].isna().any().any():
        raise ValueError("La evidencia P2 debe cubrir exactamente todos los alojamientos de V8.")
    data["seasonal_transit_destination_score"] = data[["summer_transit_score", "winter_transit_score"]].mean(axis=1)
    components = list(WEIGHTS)
    score_inputs = data.copy()
    score_inputs["temporal_transit_destination_score"] = data["seasonal_transit_destination_score"]
    weighted_total = sum(score_inputs[column].fillna(0) * weight for column, weight in WEIGHTS.items())
    available_weight = sum(score_inputs[column].notna().astype(float) * weight for column, weight in WEIGHTS.items())
        # Calcula cobertura y puntuacion final
    data["tsmai_v9_evidence_coverage_pct"] = 100 * score_inputs[components].notna().mean(axis=1)
    data["tsmai_v9_score"] = (weighted_total / available_weight.where(available_weight.gt(0))).round(3)
    data["tsmai_v9_level"] = pd.cut(data["tsmai_v9_score"], [-0.01, 0.40, 0.67, 1.01], labels=["prioridad de mejora", "intermedio", "favorable"]).astype("string")
    data["tsmai_v8_to_v9_delta"] = (data["tsmai_v9_score"] - data["tsmai_v8_score"]).round(3)
    data["index_version"] = "TSMAI-v9-seasonal-transit"
    data["interpretation_scope"] = (
        "índice individual multimodal; el componente TRANSIT es la media de cuatro escenarios de verano y cuatro de invierno "
        "del mismo GTFS versionado, no un promedio anual ni una medida de puntualidad, seguridad o accesibilidad universal"
    )
    output = gpd.GeoDataFrame(data, geometry=geometry_column, crs=v8.crs)
    atomic_parquet(output, V9_OUTPUT)
    report = {
        "status": "passed",
        "index_version": "TSMAI-v9-seasonal-transit",
        "records": int(len(output)),
        "weights": WEIGHTS,
        "seasonal_transit_component": {
            "aggregation": "media simple, por alojamiento, de dos campañas reales de cuatro escenarios cada una",
            "summer_score_mean": round(float(output["summer_transit_score"].mean()), 4),
            "winter_score_mean": round(float(output["winter_transit_score"].mean()), 4),
            "seasonal_score_mean": round(float(output["seasonal_transit_destination_score"].mean()), 4),
            "seasonal_change_counts": output["seasonal_change"].value_counts().to_dict(),
        },
        "inputs": {
            "tsmai_v8": str(V9_V8_INPUT.relative_to(ROOT)),
            "tsmai_v8_sha256": sha256(V9_V8_INPUT),
            "summer_transit_long": str(V9_SUMMER_INPUT.relative_to(ROOT)),
            "summer_transit_long_sha256": sha256(V9_SUMMER_INPUT),
            "winter_transit_long": str(V9_WINTER_INPUT.relative_to(ROOT)),
            "winter_transit_long_sha256": sha256(V9_WINTER_INPUT),
            "seasonal_comparison": str(V9_SEASONAL_COMPARISON.relative_to(ROOT)),
            "seasonal_comparison_sha256": sha256(V9_SEASONAL_COMPARISON),
        },
        "levels": output["tsmai_v9_level"].value_counts().to_dict(),
        "score_summary": output["tsmai_v9_score"].describe().round(3).to_dict(),
        "v8_to_v9_delta_summary": output["tsmai_v8_to_v9_delta"].describe().round(3).to_dict(),
        "output": str(V9_OUTPUT.relative_to(ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La media de verano e invierno no representa un promedio anual ni pondera demanda, ocupación o frecuencias observadas.",
            "La variación estacional procede del calendario del mismo GTFS versionado; no mide cambios entre publicaciones del proveedor.",
            "Los estados no_transit_leg y no_route reciben 0 en el escenario correspondiente, sin imputación.",
        ],
    }
    atomic_json(report, CURATED / "latest_tsmai_v9.json")
    atomic_json(report, V9_REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))






import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ibestat_000060A_000004.csv"
TOURIST_OFFER_OUTPUT = ROOT / "data" / "curated" / "municipality_tourist_offer_seasonality.parquet"
TOURIST_OFFER_REPORT = ROOT / "docs" / "tourist_offer_seasonality_report.json"


def main_tourist_offer_seasonality():
    data = pd.read_csv(RAW)
    places = data.loc[data["MEDIDAS_CODE"].eq("PLAZA_TURISTICA")].copy()
    places["period"] = pd.to_datetime(places["TIME_PERIOD#es"], format="%m/%Y", errors="coerce")
    places["places"] = pd.to_numeric(places["OBS_VALUE"], errors="coerce")
    places = places.dropna(subset=["period", "places", "TERRITORIO#es"])
    summary = places.groupby("TERRITORIO#es", dropna=False).agg(
        periods=("period", "nunique"), first_period=("period", "min"), latest_period=("period", "max"),
        minimum_official_places=("places", "min"), maximum_official_places=("places", "max"),
        mean_official_places=("places", "mean"),
    ).reset_index().rename(columns={"TERRITORIO#es": "municipality"})
    latest = places.sort_values("period").groupby("TERRITORIO#es", as_index=False).tail(1)[["TERRITORIO#es", "places"]].rename(columns={"TERRITORIO#es": "municipality", "places": "latest_official_places"})
    summary = summary.merge(latest, on="municipality", how="left", validate="one_to_one")
    summary["seasonal_offer_range_pct"] = ((summary["maximum_official_places"] - summary["minimum_official_places"]) / summary["maximum_official_places"].replace(0, pd.NA) * 100).fillna(0).round(1)
    summary["mean_official_places"] = summary["mean_official_places"].round(1)
    summary.to_parquet(TOURIST_OFFER_OUTPUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "IBESTAT 000060A_000004; medida PLAZA_TURISTICA.",
        "municipalities": int(len(summary)), "period_start": str(places["period"].min().date()), "period_end": str(places["period"].max().date()),
        "limitations": ["Las plazas oficiales son capacidad de oferta, no ocupación, llegadas ni viajes observados.", "No se incorporan al TSMAI como demanda ni se usan para validar emisiones."],
    }
    TOURIST_OFFER_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Estacionalidad de oferta: {len(summary)} municipios")






import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
SCENARIOS_FILE = ROOT / "config" / "transit_temporal_scenarios.json"
QUERY = """
query TransitTemporal($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: [{mode: TRANSIT}], numItineraries: 1) {
    itineraries { duration walkDistance legs { mode distance duration route { shortName longName } } }
    routingErrors { code description }
  }
}
"""


def atomic_parquet(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def atomic_json(payload, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

def load_gtfs_lineage(run_id):
    raw_root = ROOT / "data" / "raw" / "tib_gtfs_supply"
    if run_id is None:
        latest = json.loads((raw_root / "latest.json").read_text(encoding="utf-8"))
        run_id = latest["run_id"]
        manifest_path = ROOT / latest["manifest"]
    else:
        manifest_path = raw_root / run_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No existe el manifiesto GTFS para el run_id {run_id!r}.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "tib_gtfs_supply" or manifest.get("run_id") != run_id:
        raise ValueError("El manifiesto GTFS no coincide con el snapshot declarado.")
    return {
        "gtfs_source_run_id": run_id,
        "gtfs_source_snapshot": str(manifest_path.parent.relative_to(ROOT)),
        "gtfs_source_sha256": manifest["payload_sha256"],
    }


def load_inputs(gtfs_run_id: str | None = None, scenarios_file: Path = SCENARIOS_FILE):
    # Carga pares base y escenarios
    metadata = json.loads((CURATED / "latest_transit_network_access.json").read_text(encoding="utf-8"))
    pairs_path = ROOT / metadata["output"]
    if not scenarios_file.is_file():
        raise FileNotFoundError(f"No existe el fichero de escenarios: {scenarios_file}")
    scenarios_payload = json.loads(scenarios_file.read_text(encoding="utf-8"))
    scenarios = scenarios_payload["scenarios"]
    required = {"screening_id", "accommodation_id", "origin_lat", "origin_lon", "destination_lat", "destination_lon"}
    pairs = pd.read_parquet(pairs_path)
    if missing := required.difference(pairs.columns):
        raise ValueError(f"El barrido base TRANSIT no contiene: {sorted(missing)}")
    if pairs["screening_id"].duplicated().any() or len(pairs) != 1461:
        raise ValueError("El barrido base debe contener un par único para cada alojamiento oficial.")
    scenario_ids = [scenario["scenario_id"] for scenario in scenarios]
    if len(scenario_ids) < 2 or len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Se requieren al menos dos escenarios con identificadores únicos.")
    for scenario in scenarios:
        # Valida fecha y hora declaradas
        pd.Timestamp(scenario["date"]).date()
        pd.Timestamp(f"1970-01-01 {scenario['time']}").time()
    return pairs, scenarios, {
        "base_transit_output": str(pairs_path.relative_to(ROOT)),
        "scenario_set": scenarios_payload["scenario_set"],
        "scenario_config": str(scenarios_file.relative_to(ROOT)),
        **load_gtfs_lineage(gtfs_run_id),
    }


def build_queries(pairs, scenarios):
    rows = []
    for scenario in scenarios:
        scoped = pairs[["screening_id", "accommodation_id", "origin_lat", "origin_lon", "destination_lat", "destination_lon"]].copy()
        scoped["scenario_id"] = scenario["scenario_id"]
        scoped["scenario_label"] = scenario["label"]
        scoped["routing_date"] = scenario["date"]
        scoped["routing_time"] = scenario["time"]
        scoped["temporal_id"] = scoped["scenario_id"] + "::" + scoped["screening_id"]
        rows.append(scoped)
    queries = pd.concat(rows, ignore_index=True)
    if queries["temporal_id"].duplicated().any():
        raise ValueError("Cada consulta temporal debe ser única.")
    return queries


async def health_check(session, endpoint):
    try:
        async with session.post(endpoint, json={"query": "{ __typename }"}) as response:
            response.raise_for_status()
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"OTP no está disponible en {endpoint}. Inícialo antes de ejecutar el barrido. Detalle: {exc}") from exc


async def fetch(session, endpoint, semaphore, row, retries):
    variables = {
        "from": {"lat": row.origin_lat, "lon": row.origin_lon},
        "to": {"lat": row.destination_lat, "lon": row.destination_lon},
        "date": row.routing_date,
        "time": row.routing_time,
    }
    async with semaphore:
        for attempt in range(retries + 1):
            try:
                async with session.post(endpoint, json={"query": QUERY, "variables": variables}) as response:
                    response.raise_for_status()
                    payload = await response.json()
                if payload.get("errors"):
                    return {"temporal_id": row.temporal_id, "route_status": "graphql_error", "route_error": json.dumps(payload["errors"], ensure_ascii=False)}
                plan = payload.get("data", {}).get("plan") or {}
                itineraries = plan.get("itineraries") or []
                if not itineraries:
                    return {"temporal_id": row.temporal_id, "route_status": "no_route", "route_error": json.dumps(plan.get("routingErrors", []), ensure_ascii=False)}
                itinerary = min(itineraries, key=lambda item: item["duration"])
                legs = itinerary.get("legs") or []
                transit_legs = [leg for leg in legs if leg.get("mode") != "WALK"]
                if not transit_legs:
                    return {"temporal_id": row.temporal_id, "route_status": "no_transit_leg", "route_error": "OTP devolvió un itinerario sin tramo TRANSIT."}
                return {
                    "temporal_id": row.temporal_id,
                    "route_status": "ok",
                    "route_duration_min": round(float(itinerary["duration"]) / 60, 2),
                    "route_walk_distance_m": round(float(itinerary.get("walkDistance") or 0), 2),
                    "transit_leg_count": len(transit_legs),
                    "transfers": max(0, len(transit_legs) - 1),
                }
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                if attempt == retries:
                    return {"temporal_id": row.temporal_id, "route_status": "request_error", "route_error": str(exc)}
                await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Estado de reintento no alcanzable.")


def summarize(final):
    # Resume resultados por alojamiento TRANSIT
    result = final.copy()
    result["transit_ok"] = result["route_status"].eq("ok")
    result["transit_60min"] = result["transit_ok"] & result["route_duration_min"].le(60)
    result["transit_90min"] = result["transit_ok"] & result["route_duration_min"].le(90)
    result["transit_120min"] = result["transit_ok"] & result["route_duration_min"].le(120)
    grouped = result.groupby("accommodation_id", dropna=False)
    summary = grouped.agg(
        scenarios_evaluated=("scenario_id", "size"),
        transit_ok_scenarios=("transit_ok", "sum"),
        transit_60min_scenarios=("transit_60min", "sum"),
        transit_90min_scenarios=("transit_90min", "sum"),
        transit_120min_scenarios=("transit_120min", "sum"),
        transit_duration_median_min=("route_duration_min", "median"),
        transit_duration_max_min=("route_duration_min", "max"),
        transit_walk_distance_median_m=("route_walk_distance_m", "median"),
    ).reset_index()
    for column in ["transit_ok", "transit_60min", "transit_90min", "transit_120min"]:
        summary[f"{column}_share_pct"] = (100 * summary[f"{column}_scenarios"] / summary["scenarios_evaluated"]).round(2)
    summary["temporal_transit_level"] = pd.cut(
        summary["transit_ok_share_pct"], [-0.01, 0, 50, 100],
        labels=["sin_servicio_en_escenarios", "servicio_inestable", "servicio_consistente"],
    ).astype("string")
    return summary


async def execute(args, queries, scenarios, lineage):
    # Define rutas de la ejecucion
    scenario_suffix = "_".join(scenario["scenario_id"] for scenario in scenarios)
    run_id = "transit_temporal_" + (f"{args.analysis_id}_" if args.analysis_id else "") + scenario_suffix
    checkpoint = CURATED / f"{run_id}_checkpoint.parquet"
    long_output = CURATED / f"{run_id}.parquet"
    summary_output = CURATED / f"{run_id}_summary.parquet"
    report_path = ROOT / "docs" / f"{run_id}_report.json"
    if (checkpoint.exists() or long_output.exists() or summary_output.exists()) and not args.resume:
        raise FileExistsError("Ya existe esta ejecución temporal. Usa --resume para continuarla, sin sobrescribirla.")
    completed = pd.read_parquet(checkpoint) if args.resume and checkpoint.exists() else pd.DataFrame()
    if not completed.empty:
        completed = completed.drop_duplicates("temporal_id", keep="last")
    pending = queries.loc[~queries["temporal_id"].isin(completed.get("temporal_id", pd.Series(dtype="string")))].copy()
    if args.limit_per_scenario is not None:
        pending = pending.groupby("scenario_id", group_keys=False, sort=False).head(args.limit_per_scenario).copy()
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        endpoint = args.otp_url.rstrip("/")
        await health_check(session, endpoint)
        semaphore = asyncio.Semaphore(args.concurrency)
        new_results = []
        for offset in range(0, len(pending), args.batch_size):
            # Consulta OTP en lotes sucesivos
            batch = pending.iloc[offset: offset + args.batch_size]
            new_results.extend(await asyncio.gather(*(fetch(session, endpoint, semaphore, row, args.retries) for row in batch.itertuples())))
            partial = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("temporal_id", keep="last")
            atomic_parquet(partial, checkpoint)
            print(f"{min(offset + len(batch), len(pending))}/{len(pending)} consultas nuevas completadas", flush=True)
    res = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("temporal_id", keep="last")
    final = queries.merge(res, on="temporal_id", how="left", validate="one_to_one")
    complete = final["route_status"].notna().all()
    report = {
        "status": "passed" if complete else "partial",
        "scenario_set": lineage["scenario_set"],
        "scenarios": scenarios,
        "queries_total": int(len(queries)),
        "queries_completed": int(final["route_status"].notna().sum()),
        "status_by_scenario": {scenario: frame["route_status"].fillna("not_completed").value_counts().to_dict() for scenario, frame in final.groupby("scenario_id")},
        "inputs": lineage,
        "checkpoint": str(checkpoint.relative_to(ROOT)),
        "long_output": str(long_output.relative_to(ROOT)) if complete else None,
        "summary_output": str(summary_output.relative_to(ROOT)) if complete else None,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La robustez se refiere sólo a las cuatro fecha/horas del GTFS versionado; no representa todo el año ni puntualidad observada.",
            "Los pares TRANSIT se heredan del barrido de destinos OSM a 8–20 km y no representan demanda turística observada.",
            "No se imputan rutas: no_transit_leg, no_route y errores se mantienen como estados diferenciados.",
        ],
    }
    if complete:
        final["transit_ok"] = final["route_status"].eq("ok")
        final["transit_60min"] = final["transit_ok"] & final["route_duration_min"].le(60)
        final["transit_90min"] = final["transit_ok"] & final["route_duration_min"].le(90)
        final["transit_120min"] = final["transit_ok"] & final["route_duration_min"].le(120)
        summary = summarize(final)
        atomic_parquet(final, long_output)
        atomic_parquet(summary, summary_output)
        report["summary_levels"] = summary["temporal_transit_level"].value_counts().to_dict()
        report["network_coverage_by_scenario_pct"] = {
            scenario: {column: round(100 * float(frame[column].mean()), 2) for column in ["transit_ok", "transit_60min", "transit_90min", "transit_120min"]}
            for scenario, frame in final.groupby("scenario_id")
        }
        atomic_json(report, CURATED / "latest_transit_temporal_robustness.json")
    atomic_json(report, report_path)
    return report


def main_transit_temporal_robustness():
    parser = argparse.ArgumentParser(description="Evalúa robustez temporal TRANSIT sobre pares OTP reales.")
    parser.add_argument("--otp-url", default="http://localhost:8080/otp/gtfs/v1")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit-per-scenario", type=int, help="Sólo para piloto: consultas nuevas deterministas por escenario.")
    parser.add_argument("--analysis-id", help="Identificador seguro de una campaña independiente, por ejemplo winter_2027.")
    parser.add_argument("--gtfs-run-id", help="Run ID del snapshot GTFS que carga el OTP consultado; por defecto, el snapshot GTFS latest.")
    parser.add_argument("--scenarios-file", type=Path, default=SCENARIOS_FILE, help="JSON de escenarios GTFS reales; por defecto usa la campaña P1.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.concurrency < 1 or args.batch_size < 1 or args.timeout < 1 or args.retries < 0 or (args.limit_per_scenario is not None and args.limit_per_scenario < 1):
        raise ValueError("Los parámetros numéricos deben ser positivos; retries no puede ser negativo.")
    if args.analysis_id and not re.fullmatch(r"[A-Za-z0-9_-]+", args.analysis_id):
        raise ValueError("analysis-id sólo puede contener letras, números, guiones y guiones bajos.")
    scenarios_file = args.scenarios_file if args.scenarios_file.is_absolute() else ROOT / args.scenarios_file
    pairs, scenarios, lineage = load_inputs(args.gtfs_run_id, scenarios_file)
    queries = build_queries(pairs, scenarios)
    plan = {
        "status": "dry_run" if not args.execute else "ready",
        "scenario_set": lineage["scenario_set"],
        "scenarios": scenarios,
        "pairs_per_scenario": int(len(pairs)),
        "queries_planned": int(len(queries)),
        "limit_per_scenario": args.limit_per_scenario,
        "inputs": lineage,
        "message": "No se ha consultado OTP ni escrito ningún resultado. Añade --execute para el piloto o el barrido." if not args.execute else "Iniciando consultas OTP.",
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=True, indent=2))
        return
    print(json.dumps(asyncio.run(execute(args, queries, scenarios, lineage)), ensure_ascii=True, indent=2))







if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_current_tsmai_v9_seasonal_transit":
        main_current_tsmai_v9_seasonal_transit()
        sys.exit(0)
    if task_name == "run_build_tourist_offer_seasonality":
        main_tourist_offer_seasonality()
        sys.exit(0)
    if task_name == "run_build_transit_temporal_robustness":
        main_transit_temporal_robustness()
        sys.exit(0)
    print(f"Task {task_name} not found.")
