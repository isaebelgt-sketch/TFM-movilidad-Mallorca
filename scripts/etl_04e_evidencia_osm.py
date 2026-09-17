from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OSM_DIR = ROOT / "data" / "unified" / "osm"
UNIFIED = ROOT / "data" / "unified"
CURATED = ROOT / "data" / "curated"
TMP = ROOT / "tmp" / "active_mobility_evidence"
REPORT = ROOT / "docs" / "active_mobility_evidence_report.json"
accs = UNIFIED / "accommodations_official_normalized.geojson"
METRIC_CRS = "EPSG:25831"


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


def resolve_network():
    latest = OSM_DIR / "latest_mallorca_network.json"
    if not latest.exists():
        raise FileNotFoundError("No hay red OSM preparada. Ejecuta scripts/prepare_osm_mobility_network.py.")
    metadata = json.loads(latest.read_text(encoding="utf-8"))
    network = ROOT / metadata["network_file"]
    if not network.is_file() or network.stat().st_size == 0:
        raise FileNotFoundError(f"La red OSM indicada en el manifiesto no existe: {network}")
    return network, metadata


def osmium_command():
    if os.name == "nt":
        conda_bat = Path(sys.prefix).parents[1] / "condabin" / "conda.bat"
        if conda_bat.exists():
            return [str(conda_bat), "run", "--no-capture-output", "-p", sys.prefix, "osmium"]
    executable = shutil.which("osmium")
    if executable:
        return [executable]
    raise RuntimeError("No se encontró osmium. Activa el entorno del proyecto o instala osmium-tool desde conda-forge.")


def run_osmium(arguments):
    subprocess.run(osmium_command() + arguments, check=True, text=True)


def extract_candidates(network, name, filters):
    TMP.mkdir(parents=True, exist_ok=True)
    pbf = TMP / f"{name}.osm.pbf"
    geojson = TMP / f"{name}.geojson"
    run_osmium(["tags-filter", str(network), *filters, "-o", str(pbf), "--overwrite"])
    run_osmium(["export", str(pbf), "-o", str(geojson), "--overwrite"])
    payload = json.loads(geojson.read_text(encoding="utf-8"))
    layer = gpd.GeoDataFrame.from_features(payload.get("features", []), crs="EPSG:4326")
    return layer.loc[layer.geom.type.isin(["LineString", "MultiLineString", "Polygon", "MultiPolygon"])].copy()


def first_existing(frame, names):
    # Busca la primera columna disponible
    for name in names:
        if name in frame.columns:
            return frame[name].astype("string")
    return pd.Series(pd.NA, index=frame.index, dtype="string")


def as_lines(layer):
    result = layer.copy()
    polygons = result.geom.type.isin(["Polygon", "MultiPolygon"])
    result.loc[polygons, "geom"] = result.loc[polygons, "geom"].boundary
    return result.loc[result.geom.notna() & ~result.geom.is_empty].copy()


def classify_cycleways(candidates):
    highway = first_existing(candidates, ["highway"])
    cycleway = first_existing(candidates, ["cycleway"])
    left = first_existing(candidates, ["cycleway:left"])
    right = first_existing(candidates, ["cycleway:right"])
    bicycle = first_existing(candidates, ["bicycle"])
    no_value = lambda series: series.str.lower().isin(["no", "none"])
    keep = highway.eq("cycleway") | (cycleway.notna() & ~no_value(cycleway)) | (left.notna() & ~no_value(left)) | (right.notna() & ~no_value(right)) | bicycle.str.lower().isin(["designated"])
    result = candidates.loc[keep].copy()
    result["osm_mobility_evidence"] = "infraestructura ciclista etiquetada"
    result.loc[first_existing(result, ["highway"]).eq("cycleway"), "osm_mobility_evidence"] = "vía ciclista dedicada"
    return as_lines(result)


def classify_pedestrian(candidates):
    highway = first_existing(candidates, ["highway"])
    sidewalk = first_existing(candidates, ["sidewalk"])
    foot = first_existing(candidates, ["foot"])
    wheelchair = first_existing(candidates, ["wheelchair"])
    lit = first_existing(candidates, ["lit"])
    keep = highway.isin(["footway", "pedestrian", "path", "steps"]) | sidewalk.notna() | foot.str.lower().isin(["designated"])
    result = candidates.loc[keep].copy()
    result["osm_mobility_evidence"] = "infraestructura peatonal etiquetada"
    result.loc[wheelchair.str.lower().isin(["yes", "designated"]), "osm_mobility_evidence"] = "evidencia OSM de accesibilidad universal"
    result.loc[lit.str.lower().eq("yes"), "osm_mobility_evidence"] = "infraestructura peatonal etiquetada e iluminada"
    return as_lines(result)


def nearest_distance(points, lines, column, bands):
    if lines.empty:
        raise ValueError(f"No se extrajo evidencia OSM para {column}.")
    left = points.to_crs(METRIC_CRS).copy()
    right = lines.to_crs(METRIC_CRS)[["geom"]].copy()
    index_pairs, distances = right.sindex.nearest(left.geom, return_distance=True)
    left_positions = index_pairs[0]
    result = left.iloc[left_positions].copy()
    result[column] = distances
    result = result.loc[~result.index.duplicated(keep="first")].reindex(left.index).to_crs(points.crs)
    result[f"{column}_band"] = pd.cut(result[column], bins=[-1, bands[0], bands[1], float("inf")], labels=[f"alta_0_{bands[0]}m", f"media_{bands[0]}_{bands[1]}m", f"brecha_mas_{bands[1]}m"]).astype("string")
    return result


def main_osm_active_mobility_evidence():
    if not accs.exists():
        raise FileNotFoundError(f"No existe {accs}. Ejecuta primero prepare_official_accommodations.py.")
    network, network_metadata = resolve_network()
    run_id = network_metadata["source_run_id"]
    print("[1/4] Extrayendo etiquetas OSM de movilidad activa…", flush=True)
    cycleways = classify_cycleways(extract_candidates(network, f"cycle_{run_id}", ["w/highway=cycleway", "w/cycleway", "w/cycleway:left", "w/cycleway:right", "w/bicycle=designated"]))
    pedestrian = classify_pedestrian(extract_candidates(network, f"pedestrian_{run_id}", ["w/highway=footway", "w/highway=pedestrian", "w/highway=path", "w/highway=steps", "w/sidewalk", "w/foot=designated", "w/wheelchair"]))

    print("[2/4] Publicando capas de evidencia OSM…", flush=True)
    cycle_path = OSM_DIR / f"mallorca_cycling_evidence_{run_id}.parquet"
    pedestrian_path = OSM_DIR / f"mallorca_pedestrian_evidence_{run_id}.parquet"
    atomic_parquet_write(cycleways, cycle_path)
    atomic_parquet_write(pedestrian, pedestrian_path)

    print("[3/4] Midiendo proximidad para alojamientos oficiales…", flush=True)
    accs = gpd.read_file(accs)
    with_cycle = nearest_distance(accs, cycleways, "distance_to_cycle_evidence_m", (400, 800))
    access = nearest_distance(with_cycle, pedestrian, "distance_to_pedestrian_evidence_m", (400, 800))
    access["analysis_source_run_id"] = run_id
    access["analysis_scope"] = "proximidad geométrica a evidencia OSM; no es distancia ni tiempo de red"
    access_path = CURATED / f"accommodations_active_mobility_access_{run_id}.parquet"
    atomic_parquet_write(access, access_path)

    print("[4/4] Registrando trazabilidad y controles de calidad…", flush=True)
    latest = {
        "status": "passed",
        "source_network": network_metadata["network_file"],
        "source_network_sha256": network_metadata["network_sha256"],
        "source_run_id": run_id,
        "accommodations_source": str(accs.relative_to(ROOT)),
        "cycling_evidence": str(cycle_path.relative_to(ROOT)),
        "pedestrian_evidence": str(pedestrian_path.relative_to(ROOT)),
        "accommodation_access": str(access_path.relative_to(ROOT)),
        "accommodations_evaluated": int(len(access)),
        "cycling_features": int(len(cycleways)),
        "pedestrian_features": int(len(pedestrian)),
        "cycle_access_bands": access["distance_to_cycle_evidence_m_band"].value_counts(dropna=False).to_dict(),
        "pedestrian_access_bands": access["distance_to_pedestrian_evidence_m_band"].value_counts(dropna=False).to_dict(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La ausencia de etiqueta OSM no prueba ausencia de infraestructura.",
            "La proximidad geométrica no acredita continuidad, seguridad, pendiente, iluminación ni ciclabilidad de una ruta.",
            "Las etiquetas wheelchair y sidewalk son evidencia cartográfica, no una auditoría de accesibilidad universal.",
        ],
    }
    atomic_json_write(CURATED / "latest_active_mobility_access.json", latest)
    atomic_json_write(REPORT, latest)
    print(json.dumps(latest, ensure_ascii=False, indent=2))






import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OSM_DIR = ROOT / "data" / "unified" / "osm"
CURATED = ROOT / "data" / "curated"
TMP = ROOT / "tmp" / "tourism_destinations"
REPORT = ROOT / "docs" / "tourism_destinations_osm_report.json"
METRIC_CRS = "EPSG:25831"
EXCLUDED_TOURISM_VALUES = {
    "hotel", "apartment", "guest_house", "hostel", "motel", "camp_site",
    "caravan_site", "alpine_hut", "chalet", "wilderness_hut", "camp_pitch",
    "building", "yes",
}
ALLOWED_LEISURE_VALUES = {"park", "garden", "nature_reserve"}
ALLOWED_NATURAL_VALUES = {"beach", "peak", "cave_entrance", "waterfall"}


def sha256(path):
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


def atomic_parquet_write(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def osmium_command():
    if os.name == "nt":
        conda_bat = Path(sys.prefix).parents[1] / "condabin" / "conda.bat"
        if conda_bat.exists():
            return [str(conda_bat), "run", "--no-capture-output", "-p", sys.prefix, "osmium"]
    executable = shutil.which("osmium")
    if executable:
        return [executable]
    raise RuntimeError("No se encontró osmium. Activa el entorno del proyecto o instala osmium-tool.")


def run_osmium(arguments):
    subprocess.run(osmium_command() + arguments, check=True, text=True)


def resolve_network():
    latest = OSM_DIR / "latest_mallorca_network.json"
    if not latest.exists():
        raise FileNotFoundError("No existe la red OSM de Mallorca preparada.")
    metadata = json.loads(latest.read_text(encoding="utf-8"))
    network = ROOT / metadata["network_file"]
    if not network.exists() or sha256(network) != metadata["network_sha256"]:
        raise ValueError("La red OSM no coincide con el hash registrado.")
    return network, metadata


def first_existing(frame, name):
    # Devuelve la columna si existe
    return frame[name].astype("string") if name in frame.columns else pd.Series(pd.NA, index=frame.index, dtype="string")


def extract_candidates(network, run_id):
    TMP.mkdir(parents=True, exist_ok=True)
    pbf = TMP / f"tourism_candidates_{run_id}.osm.pbf"
    geojson = TMP / f"tourism_candidates_{run_id}.geojson"
    filters = [
        "nwr/tourism",
        "nwr/historic",
        "nwr/leisure=park",
        "nwr/leisure=garden",
        "nwr/leisure=nature_reserve",
        "nwr/natural=beach",
        "nwr/natural=peak",
        "nwr/natural=cave_entrance",
        "nwr/natural=waterfall",
        "nwr/man_made=lighthouse",
    ]
    run_osmium(["tags-filter", str(network), *filters, "-o", str(pbf), "--overwrite"])
    run_osmium(["export", str(pbf), "-o", str(geojson), "--overwrite"])
    payload = json.loads(geojson.read_text(encoding="utf-8"))
    return gpd.GeoDataFrame.from_features(payload.get("features", []), crs="EPSG:4326")

def classify_category(frame):
    tourism = first_existing(frame, "tourism").str.lower()
    historic = first_existing(frame, "historic").str.lower()
    leisure = first_existing(frame, "leisure").str.lower()
    natural = first_existing(frame, "natural").str.lower()
    man_made = first_existing(frame, "man_made").str.lower()
    accommodation_like = tourism.isin(EXCLUDED_TOURISM_VALUES)
    is_tourism = tourism.notna() & ~accommodation_like
    is_historic = historic.notna()
    is_leisure = leisure.isin(ALLOWED_LEISURE_VALUES)
    is_natural = natural.isin(ALLOWED_NATURAL_VALUES)
    is_lighthouse = man_made.eq("lighthouse")
    accepted = (is_tourism | is_historic | is_leisure | is_natural | is_lighthouse) & ~accommodation_like
    result = pd.Series(pd.NA, index=frame.index, dtype="string")

    result.loc[is_tourism & accepted] = "tourism:" + tourism.loc[is_tourism & accepted]
    result.loc[result.isna() & is_historic & accepted] = "historic:" + historic.loc[result.isna() & is_historic & accepted]
    result.loc[result.isna() & is_leisure & accepted] = "leisure:" + leisure.loc[result.isna() & is_leisure & accepted]
    result.loc[result.isna() & is_natural & accepted] = "natural:" + natural.loc[result.isna() & is_natural & accepted]
    result.loc[result.isna() & is_lighthouse & accepted] = "man_made:lighthouse"
    return result, accepted, accommodation_like


def destination_id(name, destination_category, geom):
    # Genera un identificador unico OSM
    payload = f"{name}|{destination_category}|{geom.x:.7f}|{geom.y:.7f}".encode("utf-8")
    return "osm_" + hashlib.sha256(payload).hexdigest()[:20]


def normalize(candidates):
    source_geometry = candidates.geom.geom_type.astype("string")
    valid_geometry = candidates.geom.notna() & ~candidates.geom.is_empty
    layer = candidates.loc[valid_geometry].copy()
    source_geometry = source_geometry.loc[valid_geometry]
    layer["name"] = first_existing(layer, "name").str.strip()
    layer["destination_category"], accepted_category, accommodation_like = classify_category(layer)
    named = layer["name"].notna() & layer["name"].ne("")
    result = layer.loc[named & accepted_category].copy()
    source_geometry = source_geometry.loc[result.index]
    projected = result.to_crs(METRIC_CRS)
    result["geom"] = projected.geom.representative_point().to_crs("EPSG:4326")
    result["source_geometry_type"] = source_geometry.astype("string")
    result["poi_id"] = [destination_id(name, kind, geom) for name, kind, geom in zip(result["name"], result["destination_category"], result.geom)]
    result = result.loc[~result["poi_id"].duplicated(keep="first")].copy()
    result["source_dataset"] = "osm_mallorca_network"
    result["analysis_scope"] = "POI OSM nombrado convertido a punto representativo para cálculo de destinos"
    keep_columns = ["poi_id", "name", "destination_category", "source_geometry_type", "source_dataset", "analysis_scope", "geom"]
    return result.loc[:, keep_columns], {
        "candidate_features": int(len(candidates)),
        "invalid_geometry_excluded": int((~valid_geometry).sum()),
        "unnamed_excluded": int((valid_geometry & ~named.reindex(candidates.index, fill_value=False)).sum()),
        "accommodation_like_tourism_excluded": int((valid_geometry & accommodation_like.reindex(candidates.index, fill_value=False)).sum()),
        "unqualified_tag_excluded": int((valid_geometry & ~accepted_category.reindex(candidates.index, fill_value=False)).sum()),
    }


def main_osm_tourism_destinations():
    network, metadata = resolve_network()
    run_id = metadata["source_run_id"]
    print("[1/3] Extrayendo candidatos turísticos y naturales OSM…", flush=True)
    dests, quality = normalize(extract_candidates(network, run_id))
    if dests.empty:
        raise ValueError("No se publicaron destinos OSM nombrados tras el control de calidad.")
    print("[2/3] Publicando destinos versionados…", flush=True)
    geojson_path = OSM_DIR / f"mallorca_tourism_destinations_{run_id}.geojson"
    parquet_path = CURATED / f"tourism_destinations_osm_{run_id}.parquet"
    feature_collection = json.loads(dests.to_json())
    feature_collection["metadata"] = {
        "source_network": metadata["network_file"],
        "source_network_sha256": metadata["network_sha256"],
        "source_run_id": run_id,
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json_write(geojson_path, feature_collection)
    atomic_parquet_write(dests, parquet_path)
    print("[3/3] Registrando calidad y trazabilidad…", flush=True)
    report = {
        "status": "passed",
        "source_network": metadata["network_file"],
        "source_network_sha256": metadata["network_sha256"],
        "source_run_id": run_id,
        "destinations_published": int(len(dests)),
        "categories": dests["destination_category"].value_counts().to_dict(),
        "quality": quality,
        "geojson_output": str(geojson_path.relative_to(ROOT)),
        "parquet_output": str(parquet_path.relative_to(ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Los POI dependen de la cobertura y clasificación colaborativa de OpenStreetMap.",
            "Un punto representativo de un polígono no equivale a la entrada física del lugar.",
            "La capa no mide horarios, capacidad, coste ni accesibilidad universal de cada destino.",
        ],
    }
    atomic_json_write(CURATED / "latest_tourism_destinations.json", report)
    atomic_json_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))






import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
accs = ROOT / "data" / "curated" / "accommodations_transport_access_baseline.parquet"
dests = ROOT / "data" / "curated" / "tourism_destinations_named.parquet"
OUT = ROOT / "data" / "curated" / "accommodations_tourism_proximity.parquet"
REPORT = ROOT / "docs" / "tourism_proximity_report.json"
METRIC_CRS = "EPSG:25831"


def main_tourism_proximity():
    accs = gpd.read_parquet(accs)
    dests = gpd.read_parquet(dests)
    left = accs.to_crs(METRIC_CRS)
    right = dests.to_crs(METRIC_CRS)[["poi_id", "name", "destination_category", "geom"]]
    pairs, distances = right.sindex.nearest(left.geom, return_distance=True)
    result = left.iloc[pairs[0]][["accommodation_id", "municipality_raw"]].copy()
    selected_destinations = right.iloc[pairs[1]][["poi_id", "name", "destination_category"]].reset_index(drop=True)
    result = result.reset_index(drop=True).join(selected_destinations)
    result["distance_to_nearest_tourism_destination_m"] = distances
    result = result.loc[~result["accommodation_id"].duplicated(keep="first")]
    result["tourism_destination_proximity_band"] = pd.cut(result["distance_to_nearest_tourism_destination_m"], bins=[-1, 1000, 3000, float("inf")], labels=["alta_menos_1km", "media_1_3km", "baja_mas_3km"]).astype("string")
    result.to_parquet(OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Destinos turísticos nombrados extraídos de OpenStreetMap.",
        "method": "Distancia euclídea de cada alojamiento al centroide o punto de destino nombrado más próximo, EPSG:25831.",
        "accs": int(len(result)), "dests": int(len(dests)),
        "bands": result["tourism_destination_proximity_band"].value_counts().to_dict(),
        "limitations": ["No es tiempo ni distancia por red.", "La ausencia o clasificación de POI en OSM condiciona la métrica."],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Proximidad turística calculada para {len(result):,} alojamientos")






import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OSM_DIR = ROOT / "data" / "unified" / "osm"
GTFS_DIR = ROOT / "data" / "unified" / "gtfs"
CURATED_DIR = ROOT / "data" / "curated"
accs = ROOT / "data" / "unified" / "accommodations_official_normalized.geojson"
TMP = ROOT / "tmp" / "universal_access"
REPORT = ROOT / "docs" / "universal_access_evidence_report.json"
METRIC_CRS = "EPSG:25831"


def atomic_json(payload, path):
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


def resolve_osmium():
    # Localiza el ejecutable de osmium
    if os.name == "nt":
        conda_bat = Path(sys.prefix).parents[1] / "condabin" / "conda.bat"
        if conda_bat.exists():
            return [str(conda_bat), "run", "--no-capture-output", "-p", sys.prefix, "osmium"]
    if executable := shutil.which("osmium"):
        return [executable]
    raise RuntimeError("No se encontró osmium. Activa el entorno del proyecto o instala osmium-tool desde conda-forge.")


def run_osmium(arguments):
    subprocess.run(resolve_osmium() + arguments, check=True, text=True)


def resolve_network():
    latest_path = OSM_DIR / "latest_mallorca_network.json"
    if not latest_path.is_file():
        raise FileNotFoundError("No existe una red OSM actual. Ejecuta prepare_osm_mobility_network.py.")
    metadata = json.loads(latest_path.read_text(encoding="utf-8"))
    network = ROOT / metadata["network_file"]
    if not network.is_file() or network.stat().st_size == 0:
        raise FileNotFoundError(f"No existe la red OSM registrada: {network}")
    return network, metadata


def resolve_stops():
    # Localiza las paradas GTFS vigentes
    latest_path = GTFS_DIR / "latest_tib_gtfs.json"
    if not latest_path.is_file():
        raise FileNotFoundError("No existe un GTFS actual preparado. Ejecuta prepare_tib_gtfs.py.")
    metadata = json.loads(latest_path.read_text(encoding="utf-8"))
    stops = ROOT / metadata["stops_output"]
    if not stops.is_file():
        raise FileNotFoundError(f"No existe la capa de paradas registrada: {stops}")
    return stops, metadata


def extract_evidence(network, run_id):
    # Extrae evidencia de accesibilidad OSM
    TMP.mkdir(parents=True, exist_ok=True)
    extracted = TMP / f"universal_evidence_{run_id}.osm.pbf"
    geojson = TMP / f"universal_evidence_{run_id}.geojson"
    filters = [
        "nwr/wheelchair=yes", "nwr/wheelchair=designated", "nwr/tactile_paving=yes",
        "nwr/kerb=lowered", "nwr/crossing",
    ]
    run_osmium(["tags-filter", str(network), *filters, "-o", str(extracted), "--overwrite"])
    run_osmium(["export", str(extracted), "-o", str(geojson), "--overwrite"])
    payload = json.loads(geojson.read_text(encoding="utf-8"))
    evidence = gpd.GeoDataFrame.from_features(payload.get("features", []), crs="EPSG:4326")
    for column in ["wheelchair", "tactile_paving", "kerb", "crossing"]:
        # Asegura que existan las columnas
        if column not in evidence.columns:
            evidence[column] = pd.NA
    strong = evidence["wheelchair"].astype("string").str.lower().isin(["yes", "designated"])
    strong |= evidence["tactile_paving"].astype("string").str.lower().eq("yes")
    strong |= evidence["kerb"].astype("string").str.lower().eq("lowered")
    contextual = evidence["crossing"].notna() & ~strong
    evidence = evidence.loc[(strong | contextual) & evidence.geom.notna() & ~evidence.geom.is_empty].copy()
    evidence["accessibility_evidence_strength"] = "contextual"
    evidence.loc[strong.loc[evidence.index], "accessibility_evidence_strength"] = "strong"
    evidence["accessibility_evidence_type"] = "cruce peatonal documentado (contextual)"
    evidence.loc[evidence["tactile_paving"].astype("string").str.lower().eq("yes"), "accessibility_evidence_type"] = "pavimento táctil documentado"
    evidence.loc[evidence["kerb"].astype("string").str.lower().eq("lowered"), "accessibility_evidence_type"] = "bordillo rebajado documentado"
    evidence.loc[evidence["wheelchair"].astype("string").str.lower().isin(["yes", "designated"]), "accessibility_evidence_type"] = "accesibilidad de silla de ruedas documentada"
    return evidence


def nearest_distance(points, targets, column):
    # Calcula distancia a evidencia cercana
    if targets.empty:
        return pd.DataFrame({"accommodation_id": points["accommodation_id"], column: pd.NA})
    left = points.to_crs(METRIC_CRS)
    right = targets.to_crs(METRIC_CRS)
    pairs, distances = right.sindex.nearest(left.geom, return_distance=True)
    result = left.iloc[pairs[0]][["accommodation_id"]].copy()
    result[column] = distances
    return result.loc[~result["accommodation_id"].duplicated(keep="first")]


def main_universal_access_evidence():
    if not accs.is_file():
        raise FileNotFoundError("No existe el registro oficial actual de alojamientos.")
    network, network_metadata = resolve_network()
    stops_path, gtfs_metadata = resolve_stops()
    osm_run_id = network_metadata["source_run_id"]
    gtfs_run_id = gtfs_metadata["source_run_id"]
    print("[1/4] Extrayendo evidencia positiva y contexto peatonal OSM…", flush=True)
    evidence = extract_evidence(network, osm_run_id)
    strong = evidence.loc[evidence["accessibility_evidence_strength"].eq("strong")].copy()
    contextual = evidence.loc[evidence["accessibility_evidence_strength"].eq("contextual")].copy()
    evidence_output = OSM_DIR / f"mallorca_universal_access_evidence_{osm_run_id}.parquet"
    atomic_parquet(evidence, evidence_output)

    print("[2/4] Leyendo alojamientos oficiales y paradas GTFS versionadas…", flush=True)
    accs = gpd.read_file(accs)
    stops = gpd.read_file(stops_path)
    if accs["accommodation_id"].duplicated().any() or accs.geom.isna().any():
        raise ValueError("El registro oficial debe tener accommodation_id y geometría válidos únicos.")
    normal_stops = stops.loc[stops["location_type"].fillna("0").astype("string").str.strip().isin(["0", ""])].copy()
    wheelchair_stops = normal_stops.loc[normal_stops["wheelchair_boarding"].astype("string").str.strip().eq("1")].copy()

    print("[3/4] Midiendo proximidad geométrica a evidencia documentada…", flush=True)
    result = accs[["accommodation_id", "commercial_name", "municipality", "geom"]].copy()
    result = result.merge(nearest_distance(accs, strong, "distance_to_osm_accessibility_evidence_m"), on="accommodation_id", how="left", validate="one_to_one")
    result = result.merge(nearest_distance(accs, contextual, "distance_to_osm_pedestrian_context_m"), on="accommodation_id", how="left", validate="one_to_one")
    result = result.merge(nearest_distance(accs, wheelchair_stops, "distance_to_gtfs_wheelchair_stop_m"), on="accommodation_id", how="left", validate="one_to_one")
    result["osm_evidence_within_400m"] = result["distance_to_osm_accessibility_evidence_m"].le(400)
    result["osm_pedestrian_context_within_400m"] = result["distance_to_osm_pedestrian_context_m"].le(400)
    result["gtfs_wheelchair_stop_within_800m"] = result["distance_to_gtfs_wheelchair_stop_m"].le(800)
    result["documented_accessibility_evidence_level"] = "sin evidencia positiva cercana"
    result.loc[result["osm_evidence_within_400m"], "documented_accessibility_evidence_level"] = "evidencia OSM cercana"
    result.loc[result["gtfs_wheelchair_stop_within_800m"], "documented_accessibility_evidence_level"] = "parada GTFS etiquetada cercana"
    result["analysis_scope"] = "proximidad geométrica a etiquetas positivas OSM y GTFS; no es auditoría ni ruta accesible certificada"
    output = CURATED_DIR / f"accommodations_documented_accessibility_evidence_{osm_run_id}_{gtfs_run_id}.parquet"
    atomic_parquet(gpd.GeoDataFrame(result, geometry="geom", crs=accs.crs), output)

    print("[4/4] Publicando trazabilidad y controles de calidad…", flush=True)
    report = {
        "status": "passed",
        "source_network": network_metadata["network_file"],
        "source_network_sha256": network_metadata["network_sha256"],
        "osm_source_run_id": osm_run_id,
        "gtfs_stops_source": gtfs_metadata["stops_output"],
        "gtfs_source_run_id": gtfs_run_id,
        "gtfs_source_sha256": gtfs_metadata["source_sha256_verified"] and json.loads((ROOT / "data" / "raw" / "tib_gtfs_supply" / gtfs_run_id / "manifest.json").read_text(encoding="utf-8"))["payload_sha256"],
        "accommodations_source": str(accs.relative_to(ROOT)),
        "evidence_output": str(evidence_output.relative_to(ROOT)),
        "accommodation_evidence_output": str(output.relative_to(ROOT)),
        "osm_features": int(len(evidence)),
        "osm_strong_features": int(len(strong)),
        "osm_contextual_crossings": int(len(contextual)),
        "gtfs_wheelchair_boarding_stops": int(len(wheelchair_stops)),
        "accommodations_evaluated": int(len(result)),
        "accommodations_osm_evidence_within_400m": int(result["osm_evidence_within_400m"].sum()),
        "accommodations_gtfs_wheelchair_stop_within_800m": int(result["gtfs_wheelchair_stop_within_800m"].sum()),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La ausencia de una etiqueta OSM o GTFS no demuestra una barrera ni ausencia física de accesibilidad.",
            "Los cruces OSM se conservan como contexto, no como evidencia positiva fuerte.",
            "La proximidad geométrica no certifica una ruta accesible, cumplimiento normativo ni ausencia de barreras.",
        ],
    }
    atomic_json(report, CURATED_DIR / "latest_universal_access_evidence.json")
    atomic_json(report, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))




"""Legacy dispatcher retained as non-executable history; use scripts/run_task.py.
parser = argparse.ArgumentParser(description="Consolidated ETL runner")
parser.add_argument("task", choices=["build_accommodation_accessibility_index_v3", "build_aemet_mallorca_weather_context", "build_aemet_weather_context", "build_air_quality_context", "build_current_dashboard_layers", "build_current_sample_aemet_route_context", "build_current_sample_route_documentary_evidence", "build_current_sample_slope_profiles", "build_current_tsmai_v9_seasonal_transit", "build_osm_active_mobility_evidence", "build_osm_tourism_destinations", "build_road_safety_context", "build_tourism_proximity", "build_tourist_offer_seasonality", "build_transit_temporal_robustness", "build_universal_access_evidence", "all"], help="Task to run")
args = parser.parse_args()

if args.task in ("all", "build_accommodation_accessibility_index_v3"):
    print(f"\n=== Running run_build_accommodation_accessibility_index_v3 ===")
    run_build_accommodation_accessibility_index_v3()
if args.task in ("all", "build_aemet_mallorca_weather_context"):
    print(f"\n=== Running run_build_aemet_mallorca_weather_context ===")
    run_build_aemet_mallorca_weather_context()
if args.task in ("all", "build_aemet_weather_context"):
    print(f"\n=== Running run_build_aemet_weather_context ===")
    run_build_aemet_weather_context()
if args.task in ("all", "build_air_quality_context"):
    print(f"\n=== Running run_build_air_quality_context ===")
    run_build_air_quality_context()
if args.task in ("all", "build_current_dashboard_layers"):
    print(f"\n=== Running run_build_current_dashboard_layers ===")
    run_build_current_dashboard_layers()
if args.task in ("all", "build_current_sample_aemet_route_context"):
    print(f"\n=== Running run_build_current_sample_aemet_route_context ===")
    run_build_current_sample_aemet_route_context()
if args.task in ("all", "build_current_sample_route_documentary_evidence"):
    print(f"\n=== Running run_build_current_sample_route_documentary_evidence ===")
    run_build_current_sample_route_documentary_evidence()
if args.task in ("all", "build_current_sample_slope_profiles"):
    print(f"\n=== Running run_build_current_sample_slope_profiles ===")
    run_build_current_sample_slope_profiles()
if args.task in ("all", "build_current_tsmai_v9_seasonal_transit"):
    print(f"\n=== Running run_build_current_tsmai_v9_seasonal_transit ===")
    run_build_current_tsmai_v9_seasonal_transit()
if args.task in ("all", "build_osm_active_mobility_evidence"):
    print(f"\n=== Running run_build_osm_active_mobility_evidence ===")
    run_build_osm_active_mobility_evidence()
if args.task in ("all", "build_osm_tourism_destinations"):
    print(f"\n=== Running run_build_osm_tourism_destinations ===")
    run_build_osm_tourism_destinations()
if args.task in ("all", "build_road_safety_context"):
    print(f"\n=== Running run_build_road_safety_context ===")
    run_build_road_safety_context()
if args.task in ("all", "build_tourism_proximity"):
    print(f"\n=== Running run_build_tourism_proximity ===")
    run_build_tourism_proximity()
if args.task in ("all", "build_tourist_offer_seasonality"):
    print(f"\n=== Running run_build_tourist_offer_seasonality ===")
    run_build_tourist_offer_seasonality()
if args.task in ("all", "build_transit_temporal_robustness"):
    print(f"\n=== Running run_build_transit_temporal_robustness ===")
    run_build_transit_temporal_robustness()
if args.task in ("all", "build_universal_access_evidence"):
    print(f"\n=== Running run_build_universal_access_evidence ===")
    run_build_universal_access_evidence()


"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_build_") else "run_build_" + args.task

    if task_name == "run_build_osm_active_mobility_evidence":
        main_osm_active_mobility_evidence()
        sys.exit(0)
    if task_name == "run_build_osm_tourism_destinations":
        main_osm_tourism_destinations()
        sys.exit(0)
    if task_name == "run_build_tourism_proximity":
        main_tourism_proximity()
        sys.exit(0)
    if task_name == "run_build_universal_access_evidence":
        main_universal_access_evidence()
        sys.exit(0)
    print(f"Task {task_name} not found.")

