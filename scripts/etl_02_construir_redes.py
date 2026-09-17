from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *


import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
QUERY = """
query BicycleNetworkAccess($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: [{mode: BICYCLE}], numItineraries: 1) {
    itineraries { duration walkDistance legs { mode distance duration } }
    routingErrors { code description }
  }
}
"""


def atomic_parquet(frame, path):
    # Escribe el parquet de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def atomic_json(payload, path):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


async def health_check(session, endpoint):
    # Comprueba que OTP este activo
    try:
        async with session.post(endpoint, json={"query": "{ __typename }"}) as response:
            response.raise_for_status()
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"OTP no está disponible en {endpoint}. Inícialo antes de ejecutar el barrido. Detalle: {exc}") from exc


async def fetch_bicycle_route(session, endpoint, semaphore, row, date, clock, retries):
    # Prepara las coordenadas para OTP
    variables = {
        "from": {"lat": row.origin_lat, "lon": row.origin_lon},
        "to": {"lat": row.destination_lat, "lon": row.destination_lon},
        "date": date,
        "time": clock,
    }
    async with semaphore:
        for attempt in range(retries + 1):
            # Reintenta la consulta si falla
            try:
                async with session.post(endpoint, json={"query": QUERY, "variables": variables}) as response:
                    response.raise_for_status()
                    payload = await response.json()
                if payload.get("errors"):
                    return {"screening_id": row.screening_id, "route_status": "graphql_error", "route_error": json.dumps(payload["errors"], ensure_ascii=False)}
                plan = payload.get("data", {}).get("plan") or {}
                itineraries = plan.get("itineraries") or []
                if not itineraries:
                    return {"screening_id": row.screening_id, "route_status": "no_route", "route_error": json.dumps(plan.get("routingErrors", []), ensure_ascii=False)}
                itinerary = min(itineraries, key=lambda item: item["duration"])
                legs = itinerary.get("legs") or []
                bicycle_legs = [leg for leg in legs if leg.get("mode") == "BICYCLE"]
                if not bicycle_legs:
                    return {"screening_id": row.screening_id, "route_status": "no_bicycle_leg", "route_error": "OTP devolvió un itinerario sin tramo BICYCLE."}
                return {
                    "screening_id": row.screening_id,
                    "route_status": "ok",
                    "route_duration_min": round(float(itinerary["duration"]) / 60, 2),
                    "route_bicycle_distance_m": round(sum(float(leg.get("distance") or 0) for leg in bicycle_legs), 2),
                    "route_walk_distance_m": round(float(itinerary.get("walkDistance") or 0), 2),
                    "route_leg_count": len(legs),
                }
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                if attempt == retries:
                    return {"screening_id": row.screening_id, "route_status": "request_error", "route_error": str(exc)}
                await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Estado de reintento no alcanzable.")


async def execute(args, pairs, lineage, run_id):
    # Define las rutas de salida
    output = CURATED / f"accommodations_bicycle_network_access_{run_id}.parquet"
    checkpoint = CURATED / f"accommodations_bicycle_network_access_{run_id}_checkpoint.parquet"
    report_path = ROOT / "docs" / f"bicycle_network_access_{run_id}_report.json"
    if (output.exists() or checkpoint.exists()) and not args.resume:
        raise FileExistsError("Ya existe una ejecución para esta fecha/hora. Usa --resume para continuarla, sin sobrescribirla.")
    completed = pd.read_parquet(checkpoint) if args.resume and checkpoint.exists() else pd.DataFrame()
    if not completed.empty:
        completed = completed.drop_duplicates("screening_id", keep="last")
    pending = pairs.loc[~pairs["screening_id"].isin(completed.get("screening_id", pd.Series(dtype="string")))].copy()
    if args.limit is not None:
        pending = pending.head(args.limit).copy()
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        endpoint = args.otp_url.rstrip("/")
        await health_check(session, endpoint)
        semaphore = asyncio.Semaphore(args.concurrency)
        new_results = []
        for offset in range(0, len(pending), args.batch_size):
            batch = pending.iloc[offset: offset + args.batch_size]
            new_results.extend(await asyncio.gather(*(fetch_bicycle_route(session, endpoint, semaphore, row, args.date, args.time, args.retries) for row in batch.itertuples())))
            partial = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("screening_id", keep="last")
            atomic_parquet(partial, checkpoint)
            print(f"{min(offset + len(batch), len(pending))}/{len(pending)} consultas nuevas completadas", flush=True)
    res = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("screening_id", keep="last")
    final = pairs.merge(res, on="screening_id", how="left", validate="one_to_one")
    complete = final["route_status"].notna().all()
    if complete:
        final["bicycle_10min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(10)
        final["bicycle_20min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(20)
        final["bicycle_30min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(30)
        final["bicycle_45min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(45)
        atomic_parquet(final, output)
    elapsed = time.perf_counter() - started
    report = {
        "status": "passed" if complete else "partial",
        "run_id": run_id,
        "routing_date": args.date,
        "routing_time": args.time,
        "otp_endpoint": args.otp_url,
        "method": "Un destino elegible real más próximo por alojamiento; duración y distancia obtenidas mediante ruta BICYCLE de OTP.",
        "eligible_destination_categories": sorted(ELIGIBLE_DESTINATION_CATEGORIES),
        "pairs_total": int(len(pairs)),
        "pairs_completed": int(final["route_status"].notna().sum()),
        "status_counts": final["route_status"].fillna("not_completed").value_counts().to_dict(),
        "threshold_coverage_pct": {threshold: round(100 * final[threshold].mean(), 2) for threshold in ("bicycle_10min", "bicycle_20min", "bicycle_30min", "bicycle_45min")} if complete else {},
        "inputs": lineage,
        "checkpoint": str(checkpoint.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)) if complete else None,
        "elapsed_seconds": round(elapsed, 2),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La selección del destino por proximidad geométrica no representa demanda, preferencia ni itinerario turístico observado.",
            "La ruta BICYCLE no prueba infraestructura segregada, continuidad, iluminación, seguridad vial ni ciclabilidad percibida.",
            "La ruta se interpreta con la red y configuración OTP documentadas; la evidencia de ciclovías OSM se mantiene como componente separado.",
        ],
    }
    atomic_json(report, report_path)
    if complete:
        atomic_json(report, CURATED / "latest_bicycle_network_access.json")
    return report


def main_current_bicycle_network_access():
    parser = argparse.ArgumentParser(description="Construye cobertura BICYCLE por red para las capas actuales.")
    parser.add_argument("--date", required=True, help="Fecha GTFS en formato YYYY-MM-DD.")
    parser.add_argument("--time", required=True, help="Hora GTFS en formato HH:MM.")
    parser.add_argument("--otp-url", default="http://localhost:8080/otp/gtfs/v1")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, help="Sólo para piloto: número determinista de consultas nuevas.")
    parser.add_argument("--resume", action="store_true", help="Continúa el checkpoint de la misma fecha/hora.")
    parser.add_argument("--execute", action="store_true", help="Autoriza consultas OTP y escrituras de resultados.")
    args = parser.parse_args()
    if args.concurrency < 1 or args.batch_size < 1 or args.timeout < 1 or args.retries < 0 or (args.limit is not None and args.limit < 1):
        raise ValueError("concurrency, batch-size, timeout y limit deben ser positivos; retries no puede ser negativo.")
    pd.Timestamp(args.date).date()
    pd.Timestamp(f"1970-01-01 {args.time}").time()
    accs, dests, lineage = current_inputs()
    pairs = build_pairs(accs, dests)
    run_id = f"bicycle_{lineage['tourism_source_run_id']}_{args.date.replace('-', '')}_{args.time.replace(':', '')}"
    plan = {
        "status": "dry_run" if not args.execute else "ready",
        "run_id": run_id,
        "accs": int(len(accs)),
        "eligible_destinations": int(len(dests)),
        "pairs_planned": int(len(pairs)),
        "date": args.date,
        "time": args.time,
        "limit": args.limit,
        "inputs": lineage,
        "message": "No se ha consultado OTP ni escrito ningún resultado. Añade --execute para iniciar el piloto o el barrido." if not args.execute else "Iniciando consultas OTP.",
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=True, indent=2))
        return
    print(json.dumps(asyncio.run(execute(args, pairs, lineage, run_id)), ensure_ascii=True, indent=2))






import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
MIN_DESTINATION_DISTANCE_M = 8_000
MAX_DESTINATION_DISTANCE_M = 20_000
QUERY = """
query TransitNetworkAccess($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: [{mode: TRANSIT}], numItineraries: 1) {
    itineraries { duration walkDistance legs { mode distance duration route { shortName longName } } }
    routingErrors { code description }
  }
}
"""

def build_transit_pairs(accs, dests):
    # Empareja cada alojamiento con destino
    origins = accs.to_crs(METRIC_CRS).reset_index(drop=True)
    targets = dests.to_crs(METRIC_CRS).reset_index(drop=True)
    spatial_index = targets.sindex
    rows = []
    for origin_position, origin in origins.iterrows():
        candidate_positions = list(spatial_index.query(origin.geom.buffer(MAX_DESTINATION_DISTANCE_M), predicate="intersects"))
        candidates = targets.iloc[candidate_positions].copy()
        candidates["screening_distance_m"] = candidates.geom.distance(origin.geom)
        candidates = candidates.loc[candidates["screening_distance_m"].between(MIN_DESTINATION_DISTANCE_M, MAX_DESTINATION_DISTANCE_M)]
        if candidates.empty:
            raise ValueError(f"No hay un destino elegible entre 2 y 20 km para {origin['accommodation_id']}.")
        selected = candidates.sort_values(["screening_distance_m", "poi_id"], kind="stable").iloc[0]
        source = accs.iloc[origin_position]
        target = dests.iloc[selected.name]
        rows.append({
            "screening_id": f"transit_current_{source['accommodation_id']}",
            "accommodation_id": str(source["accommodation_id"]),
            "commercial_name": str(source["commercial_name"]),
            "municipality": str(source["municipality"]),
            "origin_lat": float(source.geom.y),
            "origin_lon": float(source.geom.x),
            "destination_poi_id": str(target["poi_id"]),
            "destination_name": str(target["name"]),
            "destination_category": str(target["destination_category"]),
            "destination_lat": float(target.geom.y),
            "destination_lon": float(target.geom.x),
            "screening_euclidean_distance_m": round(float(selected["screening_distance_m"]), 2),
        })
    result = pd.DataFrame(rows).sort_values("accommodation_id", kind="stable").reset_index(drop=True)
    if len(result) != len(accs) or result["screening_id"].duplicated().any():
        raise ValueError("Los pares TRANSIT deben ser únicos y cubrir todos los alojamientos.")
    return result


def atomic_parquet(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def atomic_json(payload, path):
    # Escribe el JSON de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


async def health_check(session, endpoint):
    # Comprueba que OTP este activo
    try:
        async with session.post(endpoint, json={"query": "{ __typename }"}) as response:
            response.raise_for_status()
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"OTP no está disponible en {endpoint}. Inícialo antes de ejecutar el barrido. Detalle: {exc}") from exc


async def fetch_transit_route(session, endpoint, semaphore, row, date, clock, retries):
    variables = {
        "from": {"lat": row.origin_lat, "lon": row.origin_lon},
        "to": {"lat": row.destination_lat, "lon": row.destination_lon},
        "date": date,
        "time": clock,
    }
    async with semaphore:
        for attempt in range(retries + 1):
            try:
                async with session.post(endpoint, json={"query": QUERY, "variables": variables}) as response:
                    response.raise_for_status()
                    payload = await response.json()
                if payload.get("errors"):
                    return {"screening_id": row.screening_id, "route_status": "graphql_error", "route_error": json.dumps(payload["errors"], ensure_ascii=False)}
                plan = payload.get("data", {}).get("plan") or {}
                itineraries = plan.get("itineraries") or []
                if not itineraries:
                    return {"screening_id": row.screening_id, "route_status": "no_route", "route_error": json.dumps(plan.get("routingErrors", []), ensure_ascii=False)}
                itinerary = min(itineraries, key=lambda item: item["duration"])
                legs = itinerary.get("legs") or []
                transit_legs = [leg for leg in legs if leg.get("mode") not in {"WALK"}]
                    # Filtra los tramos de transporte
                if not transit_legs:
                    return {"screening_id": row.screening_id, "route_status": "no_transit_leg", "route_error": "OTP devolvió un itinerario sin tramo de transporte público."}
                lines = []
                for leg in transit_legs:
                    route = leg.get("route") or {}
                    line = route.get("shortName") or route.get("longName")
                    if line:
                        lines.append(str(line))
                return {
                    "screening_id": row.screening_id,
                    "route_status": "ok",
                    "route_duration_min": round(float(itinerary["duration"]) / 60, 2),
                    "route_walk_distance_m": round(float(itinerary.get("walkDistance") or 0), 2),
                    "transit_leg_count": len(transit_legs),
                    "transfers": max(0, len(transit_legs) - 1),
                    "transit_lines": ",".join(lines),
                }
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                if attempt == retries:
                    return {"screening_id": row.screening_id, "route_status": "request_error", "route_error": str(exc)}
                await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Estado de reintento no alcanzable.")


async def execute(args, pairs, lineage, run_id):
    output = CURATED / f"accommodations_transit_network_access_{run_id}.parquet"
    checkpoint = CURATED / f"accommodations_transit_network_access_{run_id}_checkpoint.parquet"
    report_path = ROOT / "docs" / f"transit_network_access_{run_id}_report.json"
    if (output.exists() or checkpoint.exists()) and not args.resume:
        raise FileExistsError("Ya existe una ejecución para esta fecha/hora. Usa --resume para continuarla, sin sobrescribirla.")
    completed = pd.read_parquet(checkpoint) if args.resume and checkpoint.exists() else pd.DataFrame()
    if not completed.empty:
        completed = completed.drop_duplicates("screening_id", keep="last")
    pending = pairs.loc[~pairs["screening_id"].isin(completed.get("screening_id", pd.Series(dtype="string")))].copy()
    if args.limit is not None:
        pending = pending.head(args.limit).copy()
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        endpoint = args.otp_url.rstrip("/")
        await health_check(session, endpoint)
        semaphore = asyncio.Semaphore(args.concurrency)
        new_results = []
        for offset in range(0, len(pending), args.batch_size):
            batch = pending.iloc[offset: offset + args.batch_size]
            new_results.extend(await asyncio.gather(*(fetch_transit_route(session, endpoint, semaphore, row, args.date, args.time, args.retries) for row in batch.itertuples())))
            partial = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("screening_id", keep="last")
            atomic_parquet(partial, checkpoint)
            print(f"{min(offset + len(batch), len(pending))}/{len(pending)} consultas nuevas completadas", flush=True)
    res = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("screening_id", keep="last")
    final = pairs.merge(res, on="screening_id", how="left", validate="one_to_one")
    complete = final["route_status"].notna().all()
    if complete:
        final["transit_30min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(30)
        final["transit_60min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(60)
        final["transit_90min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(90)
        final["transit_120min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(120)
        atomic_parquet(final, output)
    elapsed = time.perf_counter() - started
    report = {
        "status": "passed" if complete else "partial",
        "run_id": run_id,
        "routing_date": args.date,
        "routing_time": args.time,
        "otp_endpoint": args.otp_url,
        "method": "Un destino elegible real más próximo entre 8 y 20 km por alojamiento; itinerario TRANSIT de OTP con al menos un tramo no WALK.",
        "distance_window_m": [MIN_DESTINATION_DISTANCE_M, MAX_DESTINATION_DISTANCE_M],
        "eligible_destination_categories": sorted(ELIGIBLE_DESTINATION_CATEGORIES),
        "pairs_total": int(len(pairs)),
        "pairs_completed": int(final["route_status"].notna().sum()),
        "status_counts": final["route_status"].fillna("not_completed").value_counts().to_dict(),
        "threshold_coverage_pct": {threshold: round(100 * final[threshold].mean(), 2) for threshold in ("transit_30min", "transit_60min", "transit_90min", "transit_120min")} if complete else {},
        "inputs": lineage,
        "checkpoint": str(checkpoint.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)) if complete else None,
        "elapsed_seconds": round(elapsed, 2),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La selección del destino por proximidad geométrica dentro de una ventana no representa demanda, preferencia ni itinerario turístico observado.",
            "El resultado depende del horario GTFS y la fecha/hora documentadas; no mide puntualidad, ocupación, tarifa ni accesibilidad física certificada.",
            "Un itinerario TRANSIT encontrado no certifica seguridad, continuidad de la primera/última milla ni accesibilidad universal.",
        ],
    }
    atomic_json(report, report_path)
    if complete:
        atomic_json(report, CURATED / "latest_transit_network_access.json")
    return report


def main_current_transit_network_access():
    parser = argparse.ArgumentParser(description="Construye cobertura TRANSIT por red para las capas actuales.")
    parser.add_argument("--date", required=True, help="Fecha GTFS en formato YYYY-MM-DD.")
    parser.add_argument("--time", required=True, help="Hora GTFS en formato HH:MM.")
    parser.add_argument("--otp-url", default="http://localhost:8080/otp/gtfs/v1")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, help="Sólo para piloto: número determinista de consultas nuevas.")
    parser.add_argument("--resume", action="store_true", help="Continúa el checkpoint de la misma fecha/hora.")
    parser.add_argument("--execute", action="store_true", help="Autoriza consultas OTP y escrituras de resultados.")
    args = parser.parse_args()
    if args.concurrency < 1 or args.batch_size < 1 or args.timeout < 1 or args.retries < 0 or (args.limit is not None and args.limit < 1):
        raise ValueError("concurrency, batch-size, timeout y limit deben ser positivos; retries no puede ser negativo.")
    pd.Timestamp(args.date).date()
    pd.Timestamp(f"1970-01-01 {args.time}").time()
    accs, dests, lineage = current_inputs()
    pairs = build_transit_pairs(accs, dests)
    run_id = f"transit_{lineage['tourism_source_run_id']}_{args.date.replace('-', '')}_{args.time.replace(':', '')}_{MIN_DESTINATION_DISTANCE_M // 1000}to{MAX_DESTINATION_DISTANCE_M // 1000}km"
    plan = {
        "status": "dry_run" if not args.execute else "ready",
        "run_id": run_id,
        "accs": int(len(accs)),
        "eligible_destinations": int(len(dests)),
        "pairs_planned": int(len(pairs)),
        "distance_window_m": [MIN_DESTINATION_DISTANCE_M, MAX_DESTINATION_DISTANCE_M],
        "date": args.date,
        "time": args.time,
        "limit": args.limit,
        "inputs": lineage,
        "message": "No se ha consultado OTP ni escrito ningún resultado. Añade --execute para iniciar el piloto o el barrido." if not args.execute else "Iniciando consultas OTP.",
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=True, indent=2))
        return
    print(json.dumps(asyncio.run(execute(args, pairs, lineage, run_id)), ensure_ascii=True, indent=2))






import argparse
import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
UNIFIED = ROOT / "data" / "unified"
METRIC_CRS = "EPSG:25831"
ELIGIBLE_DESTINATION_CATEGORIES = {
    "natural:beach", "leisure:park", "leisure:garden", "leisure:nature_reserve",
    "tourism:attraction", "tourism:museum", "tourism:gallery", "tourism:viewpoint",
    "tourism:theme_park", "tourism:zoo", "tourism:aquarium", "tourism:spa_resort",
    "historic:archaeological_site", "historic:castle", "historic:fort", "historic:city_gate",
    "historic:monastery", "historic:ruins", "historic:monument", "man_made:lighthouse",
}
QUERY = """
query WalkNetworkAccess($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: [{mode: WALK}], numItineraries: 1) {
    itineraries { duration walkDistance legs { mode distance duration } }
    routingErrors { code description }
  }
}
"""


def read_json(path):
    if not path.exists():
        raise FileNotFoundError(f"No existe el metadato requerido: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def current_inputs():
    # Carga alojamientos y destinos vigentes
    accommodations_path = UNIFIED / "accommodations_official_normalized.geojson"
    destinations_metadata = read_json(CURATED / "latest_tourism_destinations.json")
    destinations_path = ROOT / destinations_metadata["parquet_output"]
    accs = gpd.read_file(accommodations_path).reset_index(drop=True)
    dests = gpd.read_parquet(destinations_path).reset_index(drop=True)
    if accs.empty or dests.empty:
        raise ValueError("Las capas actuales de alojamientos y destinos no pueden estar vacías.")
    required_accommodations = {"accommodation_id", "commercial_name", "municipality", "geom"}
    required_destinations = {"poi_id", "name", "destination_category", "geom"}
    if missing := required_accommodations.difference(accs.columns):
        raise ValueError(f"Faltan campos de alojamiento: {sorted(missing)}")
    if missing := required_destinations.difference(dests.columns):
        raise ValueError(f"Faltan campos de destino: {sorted(missing)}")
    if accs.geom.isna().any() or not accs.geom.is_valid.all():
        raise ValueError("La capa de alojamientos contiene geometrías no válidas.")
    eligible = dests.loc[dests["destination_category"].isin(ELIGIBLE_DESTINATION_CATEGORIES)].copy()
    if eligible.empty:
        raise ValueError("No hay destinos elegibles tras aplicar la taxonomía declarada.")
    lineage = {
        "accs": str(accommodations_path.relative_to(ROOT)),
        "accommodations_sha256": sha256(accommodations_path),
        "tourism_destinations": str(destinations_path.relative_to(ROOT)),
        "tourism_destinations_sha256": sha256(destinations_path),
        "tourism_source_run_id": destinations_metadata["source_run_id"],
    }
    return accs, eligible, lineage

def build_pairs(accs, dests):
    origins = accs.to_crs(METRIC_CRS).reset_index(drop=True)
    targets = dests.to_crs(METRIC_CRS).reset_index(drop=True)
    pairs, distances = targets.sindex.nearest(origins.geom, return_distance=True)
    matches = {int(origin): (int(target), float(distance)) for origin, target, distance in zip(pairs[0], pairs[1], distances)}
    if len(matches) != len(origins):
        raise ValueError("No se ha encontrado un destino elegible para todos los alojamientos.")
    rows = []
    for origin_position in range(len(origins)):
        # Asocia origen con destino cercano
        target_position, distance = matches[origin_position]
        origin = accs.iloc[origin_position]
        target = dests.iloc[target_position]
        rows.append({
            "screening_id": f"walk_current_{origin['accommodation_id']}",
            "accommodation_id": str(origin["accommodation_id"]),
            "commercial_name": str(origin["commercial_name"]),
            "municipality": str(origin["municipality"]),
            "origin_lat": float(origin.geom.y),
            "origin_lon": float(origin.geom.x),
            "destination_poi_id": str(target["poi_id"]),
            "destination_name": str(target["name"]),
            "destination_category": str(target["destination_category"]),
            "destination_lat": float(target.geom.y),
            "destination_lon": float(target.geom.x),
            "screening_euclidean_distance_m": round(distance, 2),
        })
    result = pd.DataFrame(rows).sort_values("accommodation_id", kind="stable").reset_index(drop=True)
    if result["screening_id"].duplicated().any():
        raise ValueError("Los pares de screening deben ser únicos por alojamiento.")
    return result


async def health_check(session, endpoint):
    try:
        async with session.post(endpoint, json={"query": "{ __typename }"}) as response:
            response.raise_for_status()
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"OTP no está disponible en {endpoint}. Inícialo antes de ejecutar el barrido. Detalle: {exc}") from exc


async def fetch_walk_route(session, endpoint, semaphore, row, date, clock, retries):
    variables = {
        "from": {"lat": row.origin_lat, "lon": row.origin_lon},
        "to": {"lat": row.destination_lat, "lon": row.destination_lon},
        "date": date,
        "time": clock,
    }
    async with semaphore:
        for attempt in range(retries + 1):
            # Reintenta la consulta si falla
            try:
                async with session.post(endpoint, json={"query": QUERY, "variables": variables}) as response:
                    response.raise_for_status()
                    payload = await response.json()
                if payload.get("errors"):
                    return {"screening_id": row.screening_id, "route_status": "graphql_error", "route_error": json.dumps(payload["errors"], ensure_ascii=False)}
                plan = payload.get("data", {}).get("plan") or {}
                itineraries = plan.get("itineraries") or []
                if not itineraries:
                    return {"screening_id": row.screening_id, "route_status": "no_route", "route_error": json.dumps(plan.get("routingErrors", []), ensure_ascii=False)}
                itinerary = min(itineraries, key=lambda item: item["duration"])
                return {
                    "screening_id": row.screening_id,
                    "route_status": "ok",
                    "route_duration_min": round(float(itinerary["duration"]) / 60, 2),
                    "route_walk_distance_m": round(float(itinerary.get("walkDistance") or 0), 2),
                    "route_leg_count": len(itinerary.get("legs") or []),
                }
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                if attempt == retries:
                    return {"screening_id": row.screening_id, "route_status": "request_error", "route_error": str(exc)}
                await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Estado de reintento no alcanzable.")


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


async def execute(args, pairs, lineage, run_id):
    output = CURATED / f"accommodations_walk_network_access_{run_id}.parquet"
    checkpoint = CURATED / f"accommodations_walk_network_access_{run_id}_checkpoint.parquet"
    report_path = ROOT / "docs" / f"walk_network_access_{run_id}_report.json"
    if (output.exists() or checkpoint.exists()) and not args.resume:
        raise FileExistsError("Ya existe una ejecución para esta fecha/hora. Usa --resume para continuarla, sin sobrescribirla.")
    completed = pd.read_parquet(checkpoint) if args.resume and checkpoint.exists() else pd.DataFrame()
    if not completed.empty:
        completed = completed.drop_duplicates("screening_id", keep="last")
    pending = pairs.loc[~pairs["screening_id"].isin(completed.get("screening_id", pd.Series(dtype="string")))].copy()
    if args.limit is not None:
        pending = pending.head(args.limit).copy()
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        endpoint = args.otp_url.rstrip("/")
        await health_check(session, endpoint)
        semaphore = asyncio.Semaphore(args.concurrency)
        new_results = []
        for offset in range(0, len(pending), args.batch_size):
            batch = pending.iloc[offset: offset + args.batch_size]
            new_results.extend(await asyncio.gather(*(fetch_walk_route(session, endpoint, semaphore, row, args.date, args.time, args.retries) for row in batch.itertuples())))
                # Guarda el progreso en checkpoint
            partial = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("screening_id", keep="last")
            atomic_parquet(partial, checkpoint)
            print(f"{min(offset + len(batch), len(pending))}/{len(pending)} consultas nuevas completadas", flush=True)
    res = pd.concat([completed, pd.DataFrame(new_results)], ignore_index=True).drop_duplicates("screening_id", keep="last")
    final = pairs.merge(res, on="screening_id", how="left", validate="one_to_one")
    complete = final["route_status"].notna().all()
    if complete:
        final["walk_5min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(5)
        final["walk_10min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(10)
        final["walk_15min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(15)
        final["walk_30min"] = final["route_status"].eq("ok") & final["route_duration_min"].le(30)
        atomic_parquet(final, output)
    elapsed = time.perf_counter() - started
    report = {
        "status": "passed" if complete else "partial",
        "run_id": run_id,
        "routing_date": args.date,
        "routing_time": args.time,
        "otp_endpoint": args.otp_url,
        "method": "Un destino elegible real más próximo por alojamiento; duración y distancia obtenidas mediante ruta WALK de OTP.",
        "eligible_destination_categories": sorted(ELIGIBLE_DESTINATION_CATEGORIES),
        "pairs_total": int(len(pairs)),
        "pairs_completed": int(final["route_status"].notna().sum()),
        "status_counts": final["route_status"].fillna("not_completed").value_counts().to_dict(),
        "threshold_coverage_pct": {threshold: round(100 * final[threshold].mean(), 2) for threshold in ("walk_5min", "walk_10min", "walk_15min", "walk_30min")} if complete else {},
        "inputs": lineage,
        "checkpoint": str(checkpoint.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)) if complete else None,
        "elapsed_seconds": round(elapsed, 2),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La selección del destino por proximidad geométrica no representa demanda, preferencia ni itinerario turístico observado.",
            "Los POI OSM son puntos representativos; no garantizan la entrada física ni horario de apertura.",
            "La ruta WALK se interpreta con la red y configuración OTP de la fecha documentada; no certifica seguridad, pendiente ni accesibilidad universal.",
        ],
    }
    atomic_json(report, report_path)
    if complete:
        atomic_json(report, CURATED / "latest_walk_network_access.json")
    return report


def main_current_walk_network_access():
    # Define los argumentos del comando
    parser = argparse.ArgumentParser(description="Construye cobertura WALK por red para las capas actuales.")
    parser.add_argument("--date", required=True, help="Fecha GTFS en formato YYYY-MM-DD.")
    parser.add_argument("--time", required=True, help="Hora GTFS en formato HH:MM.")
    parser.add_argument("--otp-url", default="http://localhost:8080/otp/gtfs/v1")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, help="Sólo para piloto: número determinista de consultas nuevas.")
    parser.add_argument("--resume", action="store_true", help="Continúa el checkpoint de la misma fecha/hora.")
    parser.add_argument("--execute", action="store_true", help="Autoriza consultas OTP y escrituras de resultados.")
    args = parser.parse_args()
    if args.concurrency < 1 or args.batch_size < 1 or args.timeout < 1 or args.retries < 0 or (args.limit is not None and args.limit < 1):
        raise ValueError("concurrency, batch-size, timeout y limit deben ser positivos; retries no puede ser negativo.")
    pd.Timestamp(args.date).date()
    pd.Timestamp(f"1970-01-01 {args.time}").time()
    accs, dests, lineage = current_inputs()
    pairs = build_pairs(accs, dests)
    run_id = f"walk_{lineage['tourism_source_run_id']}_{args.date.replace('-', '')}_{args.time.replace(':', '')}"
    plan = {
        "status": "dry_run" if not args.execute else "ready",
        "run_id": run_id,
        "accs": int(len(accs)),
        "eligible_destinations": int(len(dests)),
        "pairs_planned": int(len(pairs)),
        "date": args.date,
        "time": args.time,
        "limit": args.limit,
        "inputs": lineage,
        "message": "No se ha consultado OTP ni escrito ningún resultado. Añade --execute para iniciar el piloto o el barrido." if not args.execute else "Iniciando consultas OTP.",
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    report = asyncio.run(execute(args, pairs, lineage, run_id))
    print(json.dumps(report, ensure_ascii=False, indent=2))






import csv
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_GTFS = ROOT / "data" / "raw" / "tib_gtfs_supply"
UNIFIED = ROOT / "data" / "unified"
GTFS = UNIFIED / "gtfs"
CURATED = ROOT / "data" / "curated"
accs = UNIFIED / "accommodations_official_normalized.geojson"
METRIC_CRS = "EPSG:25831"


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


def atomic_parquet_write(frame, path):
    # Escribe el parquet de forma atomica
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def csv_rows(archive, filename):
    with archive.open(filename) as binary:
        with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
            yield from csv.DictReader(text)


def load_sources():
    latest_gtfs = GTFS / "latest_tib_gtfs.json"
    if not latest_gtfs.exists():
        raise FileNotFoundError("No existe GTFS normalizado. Ejecuta scripts/prepare_tib_gtfs.py.")
    gtfs_metadata = json.loads(latest_gtfs.read_text(encoding="utf-8"))
    stops_path = ROOT / gtfs_metadata["stops_output"]
    if not stops_path.exists():
        raise FileNotFoundError(f"No existe la capa de paradas: {stops_path}")
    raw_latest = RAW_GTFS / "latest.json"
    if not raw_latest.exists():
        raise FileNotFoundError("No existe el snapshot raw de TIB GTFS.")
    latest_raw = json.loads(raw_latest.read_text(encoding="utf-8"))
    manifest_path = ROOT / latest_raw["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_path = manifest_path.parent / manifest["payload_file"]
    if sha256(archive_path) != manifest["payload_sha256"]:
        raise ValueError("El hash del ZIP GTFS no coincide con su manifiesto.")
    if manifest["run_id"] != gtfs_metadata["source_run_id"]:
        raise ValueError("La capa de paradas no corresponde al snapshot GTFS más reciente.")
    return manifest, archive_path, stops_path


def service_by_stop(archive_path):
    # Cuenta servicios programados por parada
    with zipfile.ZipFile(archive_path) as archive:
        names = {Path(item.filename).name.lower(): item.filename for item in archive.infolist() if not item.is_dir()}
        if not {"trips.txt", "stop_times.txt"}.issubset(names):
            raise ValueError("El ZIP GTFS no contiene trips.txt y stop_times.txt.")
        trip_route = {
            (row.get("trip_id") or "").strip(): (row.get("route_id") or "").strip()
            for row in csv_rows(archive, names["trips.txt"])
            if (row.get("trip_id") or "").strip()
        }
        routes_by_stop: dict[str, set[str]] = defaultdict(set)
        stop_time_count = Counter()
        for row in csv_rows(archive, names["stop_times.txt"]):
            stop_id = (row.get("stop_id") or "").strip()
            route_id = trip_route.get((row.get("trip_id") or "").strip())
            if stop_id and route_id:
                routes_by_stop[stop_id].add(route_id)
                stop_time_count[stop_id] += 1
    return routes_by_stop, stop_time_count


def enrich_stops(stops, routes_by_stop, stop_time_count):
    # Añade metricas de servicio GTFS
    result = stops.copy()
    result["served_route_count"] = result["stop_id"].map(lambda value: len(routes_by_stop.get(value, set()))).astype("int64")
    result["scheduled_stop_time_records"] = result["stop_id"].map(lambda value: int(stop_time_count.get(value, 0))).astype("int64")
    return result


def nearest_access(accs, stops):
    # Busca la parada mas cercana
    points = accs.to_crs(METRIC_CRS).copy()
    transport = stops.to_crs(METRIC_CRS)[["stop_id", "stop_name", "served_route_count", "scheduled_stop_time_records", "geom"]].copy()
    pairs, distances = transport.sindex.nearest(points.geom, return_distance=True)
    accommodation_positions, stop_positions = pairs
    chosen: dict[int, tuple[int, float]] = {}
    for accommodation_position, stop_position, distance in zip(accommodation_positions, stop_positions, distances):
        chosen.setdefault(int(accommodation_position), (int(stop_position), float(distance)))
    if len(chosen) != len(points):
        raise ValueError("No se encontró una parada TIB para todos los alojamientos.")
    ordered_positions = range(len(points))
    result = points.iloc[list(ordered_positions)].reset_index(drop=True)
    nearest = transport.iloc[[chosen[position][0] for position in ordered_positions]].drop(columns="geom").reset_index(drop=True)
        # Copia los atributos de parada
    result["nearest_tib_stop_id"] = nearest["stop_id"]
    result["nearest_tib_stop_name"] = nearest["stop_name"]
    result["nearest_tib_stop_route_count"] = nearest["served_route_count"]
    result["nearest_tib_stop_scheduled_records"] = nearest["scheduled_stop_time_records"]
    result["distance_to_nearest_tib_stop_m"] = [chosen[position][1] for position in ordered_positions]
    result["tib_stop_access_band"] = pd.cut(result["distance_to_nearest_tib_stop_m"], [-1, 400, 800, float("inf")], labels=["alta_0_400m", "media_400_800m", "brecha_mas_800m"]).astype("string")
    return result.to_crs(accs.crs)


def nearby_counts(accs, stops, radius_m):
    points = accs.to_crs(METRIC_CRS)
    transport = stops.to_crs(METRIC_CRS)
    idx = transport.sindex
    output = []
    for accommodation_id, geom in zip(points["accommodation_id"], points.geom):
        matches = list(idx.query(geom.buffer(radius_m), predicate="intersects"))
        selected = transport.iloc[matches]
        output.append({"accommodation_id": accommodation_id, f"tib_stops_within_{radius_m}m": len(selected), f"tib_route_stop_evidence_within_{radius_m}m": int(selected["served_route_count"].sum())})
    return pd.DataFrame(output)


def main_tib_public_transport_access():
    if not accs.exists():
        raise FileNotFoundError("No existe la capa oficial normalizada de alojamientos.")
    manifest, archive_path, stops_path = load_sources()
    run_id = manifest["run_id"]
    print("[1/4] Leyendo servicio programado del GTFS…", flush=True)
    routes_by_stop, stop_time_count = service_by_stop(archive_path)
    stops = enrich_stops(gpd.read_file(stops_path), routes_by_stop, stop_time_count)
    print("[2/4] Publicando paradas enriquecidas…", flush=True)
    enriched_stops = GTFS / f"tib_gtfs_stops_service_{run_id}.parquet"
    atomic_parquet_write(stops, enriched_stops)
    print("[3/4] Calculando acceso desde alojamientos oficiales…", flush=True)
    access = nearest_access(gpd.read_file(accs), stops)
    access = access.merge(nearby_counts(access, stops, 400), on="accommodation_id", how="left", validate="one_to_one")
    access = access.merge(nearby_counts(access, stops, 800), on="accommodation_id", how="left", validate="one_to_one")
    access["analysis_source_run_id"] = run_id
    access["analysis_scope"] = "proximidad geométrica a paradas y oferta GTFS; no es itinerario ni tiempo de viaje"
    access_path = CURATED / f"accommodations_public_transport_access_{run_id}.parquet"
    atomic_parquet_write(access, access_path)
    print("[4/4] Registrando controles de calidad…", flush=True)
    report = {
        "status": "passed",
        "source_gtfs_snapshot": str(archive_path.relative_to(ROOT)),
        "source_run_id": run_id,
        "source_sha256_verified": True,
        "source_license": manifest["license"],
        "stops_enriched": int(len(stops)),
        "stops_with_at_least_one_route": int(stops["served_route_count"].gt(0).sum()),
        "accommodations_evaluated": int(len(access)),
        "access_bands": access["tib_stop_access_band"].value_counts(dropna=False).to_dict(),
        "enriched_stops_output": str(enriched_stops.relative_to(ROOT)),
        "accommodation_access_output": str(access_path.relative_to(ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La distancia a la parada es euclídea; no es distancia caminable por red ni tiempo de viaje.",
            "scheduled_stop_time_records cuenta filas del feed y no representa frecuencia diaria sin fijar fecha y servicio.",
            "La evidencia de rutas dentro de un radio suma paradas servidas; no es número de líneas únicas del área.",
        ],
    }
    atomic_json_write(CURATED / "latest_public_transport_access.json", report)
    atomic_json_write(ROOT / "docs" / "public_transport_access_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_current_bicycle_network_access":
        main_current_bicycle_network_access()
        sys.exit(0)
    if task_name == "run_build_current_transit_network_access":
        main_current_transit_network_access()
        sys.exit(0)
    if task_name == "run_build_current_walk_network_access":
        main_current_walk_network_access()
        sys.exit(0)
    if task_name == "run_build_tib_public_transport_access":
        main_tib_public_transport_access()
        sys.exit(0)
    print(f"Task {task_name} not found.")

