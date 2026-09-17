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






import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TSMAI_V2_SENSITIVITY_INPUT = ROOT / "data" / "curated" / "municipality_tourism_sustainable_mobility_index_v2.parquet"
TSMAI_V2_SENSITIVITY_OUT = ROOT / "data" / "curated" / "municipality_tsmai_v2_sensitivity.parquet"
TSMAI_V2_SENSITIVITY_REPORT = ROOT / "docs" / "tsmai_v2_sensitivity_report.json"

TSMAI_V2_COMPONENTS = [
    "coverage_score", "gap_score", "proximity_score", "routing_score",
    "transit_score", "cycling_score", "pedestrian_evidence_score",
    "tourism_proximity_score",
]

TSMAI_V2_SCENARIOS = {
    "balanced": {"coverage_score": .18, "gap_score": .12, "proximity_score": .10, "routing_score": .15, "transit_score": .10, "cycling_score": .14, "pedestrian_evidence_score": .10, "tourism_proximity_score": .11},
    "public_transport_focus": {"coverage_score": .25, "gap_score": .20, "proximity_score": .10, "routing_score": .15, "transit_score": .15, "cycling_score": .05, "pedestrian_evidence_score": .05, "tourism_proximity_score": .05},
    "active_mobility_focus": {"coverage_score": .10, "gap_score": .10, "proximity_score": .05, "routing_score": .10, "transit_score": .10, "cycling_score": .25, "pedestrian_evidence_score": .15, "tourism_proximity_score": .15},
    "tourism_proximity_focus": {"coverage_score": .12, "gap_score": .10, "proximity_score": .08, "routing_score": .12, "transit_score": .10, "cycling_score": .12, "pedestrian_evidence_score": .11, "tourism_proximity_score": .25},
}


def main_analyze_tsmai_v2_sensitivity():
    # Carga el TSMAI v2 municipal
    data = pd.read_parquet(TSMAI_V2_SENSITIVITY_INPUT).copy()
    missing = set(TSMAI_V2_COMPONENTS).difference(data.columns)
    if missing:
        raise ValueError(f"Faltan componentes TSMAI v2: {sorted(missing)}")

    rankings = data[["municipality"]].copy()
    for name, weights in TSMAI_V2_SCENARIOS.items():
        if round(sum(weights.values()), 8) != 1:
            raise ValueError(f"Los pesos de {name} no suman uno")
        score = sum(data[column].fillna(0) * weight for column, weight in weights.items())
        rankings[f"{name}_score"] = score.round(3)
        rankings[f"{name}_rank"] = score.rank(method="min", ascending=False).astype(int)

    rank_columns = [f"{name}_rank" for name in TSMAI_V2_SCENARIOS]
        # Correlaciona los rankings entre escenarios
    correlations = rankings[rank_columns].corr(method="spearman").round(3)
    rankings["top10_scenarios"] = rankings[rank_columns].le(10).sum(axis=1)
    rankings["robust_top10"] = rankings["top10_scenarios"].ge(3)
    rankings.to_parquet(TSMAI_V2_SENSITIVITY_OUT, index=False)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Análisis de sensibilidad de pesos del TSMAI v2; no validación causal.",
        "scenarios": TSMAI_V2_SCENARIOS,
        "rank_spearman_correlation": correlations.to_dict(),
        "robust_top10_municipalities": rankings.loc[rankings["robust_top10"], "municipality"].tolist(),
        "limitations": [
            "Los escenarios expresan prioridades analíticas plausibles, no preferencias observadas.",
            "Una correlación alta no valida el índice frente a resultados de movilidad reales.",
        ],
    }
    TSMAI_V2_SENSITIVITY_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Sensibilidad TSMAI: {len(rankings)} municipios; robustos top 10: {int(rankings['robust_top10'].sum())}")






import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
TSMAI_V9_SENSITIVITY_INPUT = CURATED / "accommodations_tsmai_v9_seasonal_transit.parquet"
ACCOMMODATION_OUT = CURATED / "accommodations_tsmai_v9_sensitivity.parquet"
MUNICIPALITY_OUT = CURATED / "municipality_tsmai_v9_sensitivity.parquet"
LATEST = CURATED / "latest_tsmai_v9_sensitivity.json"
TSMAI_V9_SENSITIVITY_REPORT = ROOT / "docs" / "tsmai_v9_sensitivity_report.json"

TSMAI_V9_COMPONENTS = [
    "public_transport_proximity_score",
    "public_transport_service_score",
    "temporal_transit_destination_score",
    "cycling_evidence_proximity_score",
    "bicycle_network_destination_score",
    "pedestrian_evidence_proximity_score",
    "walk_network_destination_score",
]



TSMAI_V9_SCENARIOS = {
    "balanced": {
        "public_transport_proximity_score": 0.12,
        "public_transport_service_score": 0.08,
        "temporal_transit_destination_score": 0.20,
        "cycling_evidence_proximity_score": 0.10,
        "bicycle_network_destination_score": 0.10,
        "pedestrian_evidence_proximity_score": 0.20,
        "walk_network_destination_score": 0.20,
    },
    "seasonal_public_transport_focus": {
        "public_transport_proximity_score": 0.12,
        "public_transport_service_score": 0.08,
        "temporal_transit_destination_score": 0.36,
        "cycling_evidence_proximity_score": 0.08,
        "bicycle_network_destination_score": 0.08,
        "pedestrian_evidence_proximity_score": 0.14,
        "walk_network_destination_score": 0.14,
    },
    "active_mobility_focus": {
        "public_transport_proximity_score": 0.06,
        "public_transport_service_score": 0.04,
        "temporal_transit_destination_score": 0.08,
        "cycling_evidence_proximity_score": 0.18,
        "bicycle_network_destination_score": 0.18,
        "pedestrian_evidence_proximity_score": 0.23,
        "walk_network_destination_score": 0.23,
    },
    "walkability_focus": {
        "public_transport_proximity_score": 0.10,
        "public_transport_service_score": 0.05,
        "temporal_transit_destination_score": 0.10,
        "cycling_evidence_proximity_score": 0.10,
        "bicycle_network_destination_score": 0.10,
        "pedestrian_evidence_proximity_score": 0.25,
        "walk_network_destination_score": 0.30,
    },
    "balanced_non_transit_focus": {
        "public_transport_proximity_score": 0.10,
        "public_transport_service_score": 0.05,
        "temporal_transit_destination_score": 0.05,
        "cycling_evidence_proximity_score": 0.16,
        "bicycle_network_destination_score": 0.16,
        "pedestrian_evidence_proximity_score": 0.24,
        "walk_network_destination_score": 0.24,
    },
}

LEVEL_LABELS = ["prioridad de mejora", "intermedio", "favorable"]
LEVEL_BINS = [-0.01, 0.40, 0.67, 1.01]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_parquet(frame, path):
    # Escribe el parquet de forma atomica
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


def validate_scenarios():
    # Valida pesos y componentes declarados
    for name, weights in TSMAI_V9_SCENARIOS.items():
        if set(weights) != set(TSMAI_V9_COMPONENTS):
            raise ValueError(f"Los componentes de {name} no coinciden con TSMAI V9.")
        if round(sum(weights.values()), 10) != 1:
            raise ValueError(f"Los pesos de {name} no suman uno.")
        if any(weight < 0 for weight in weights.values()):
            raise ValueError(f"Los pesos de {name} no pueden ser negativos.")


def score_with_weights(data, weights):
    weighted_total = sum(data[column].fillna(0) * weight for column, weight in weights.items())
    available_weight = sum(data[column].notna().astype(float) * weight for column, weight in weights.items())
    return (weighted_total / available_weight.where(available_weight.gt(0))).round(3)


def classify_scores(scores):
    return pd.cut(scores, LEVEL_BINS, labels=LEVEL_LABELS).astype("string")


def top_count(record_count):
    return max(1, math.ceil(record_count * 0.10))


def append_scenarios(data, identifier_columns):
    res = data.loc[:, identifier_columns].copy()
    for name, weights in TSMAI_V9_SCENARIOS.items():
        scores = score_with_weights(data, weights)
        res[f"{name}_score"] = scores
        res[f"{name}_level"] = classify_scores(scores)
        res[f"{name}_rank"] = scores.rank(method="min", ascending=False).astype("Int64")
    rank_columns = [f"{name}_rank" for name in TSMAI_V9_SCENARIOS]
    level_columns = [f"{name}_level" for name in TSMAI_V9_SCENARIOS]
        # Calcula dispersion entre los escenarios
    res["rank_spread"] = res[rank_columns].max(axis=1) - res[rank_columns].min(axis=1)
    res["level_changes_vs_balanced"] = res[level_columns].ne(res["balanced_level"], axis=0).sum(axis=1)
    res["level_stable_all_scenarios"] = res["level_changes_vs_balanced"].eq(0)
    threshold = top_count(len(res))
    res["top_decile_scenarios"] = res[rank_columns].le(threshold).sum(axis=1)
    res["robust_top_decile"] = res["top_decile_scenarios"].ge(len(TSMAI_V9_SCENARIOS) - 1)
    return res


def municipality_results(data):
    grouped = data.groupby("municipality", dropna=False).agg(
        accommodations=("accommodation_id", "size"),
        **{component: (component, "mean") for component in TSMAI_V9_COMPONENTS},
    ).reset_index()
    identifier_columns = ["municipality", "accommodations"]
    result = append_scenarios(grouped, identifier_columns)
    return result


def main_analyze_tsmai_v9_sensitivity():
    # Valida y calcula sensibilidad TSMAI
    validate_scenarios()
    if not TSMAI_V9_SENSITIVITY_INPUT.is_file():
        raise FileNotFoundError("Ejecuta primero build_current_tsmai_v9_seasonal_transit.py.")
    data = pd.read_parquet(TSMAI_V9_SENSITIVITY_INPUT)
    required = {
        "accommodation_id",
        "commercial_name",
        "municipality",
        "tsmai_v9_score",
        "tsmai_v9_level",
        "seasonal_transit_destination_score",
        *TSMAI_V9_COMPONENTS,
    }
    if missing := required.difference(data.columns):
        raise ValueError(f"TSMAI V9 no contiene: {sorted(missing)}")
    if data["accommodation_id"].isna().any() or data["accommodation_id"].duplicated().any():
        raise ValueError("TSMAI V9 debe contener un accommodation_id único y no nulo.")

    score_data = data.copy()
    score_data["temporal_transit_destination_score"] = score_data["seasonal_transit_destination_score"]
    accommodation_columns = ["accommodation_id", "commercial_name", "municipality", "group", "subgroup", "tsmai_v9_score", "tsmai_v9_level"]
    accommodation_columns = [column for column in accommodation_columns if column in data.columns]
    accs = append_scenarios(score_data, accommodation_columns)
    if not accs["balanced_score"].eq(data["tsmai_v9_score"]).all():
        raise ValueError("El escenario balanced debe reproducir exactamente el TSMAI V9 publicado.")
    municipalities = municipality_results(score_data)

    rank_columns = [f"{name}_rank" for name in TSMAI_V9_SCENARIOS]
    accommodation_correlations = accs[rank_columns].corr(method="spearman").round(3)
    municipality_correlations = municipalities[rank_columns].corr(method="spearman").round(3)
    atomic_parquet(accs, ACCOMMODATION_OUT)
    atomic_parquet(municipalities, MUNICIPALITY_OUT)
    report = {
        "status": "passed",
        "index_version": "TSMAI-v9-seasonal-transit",
        "purpose": "Análisis determinista de sensibilidad de pesos del TSMAI V9; no validación causal ni simulación de datos.",
        "input": {"path": str(TSMAI_V9_SENSITIVITY_INPUT.relative_to(ROOT)), "sha256": sha256(TSMAI_V9_SENSITIVITY_INPUT), "records": int(len(data))},
        "scenarios": TSMAI_V9_SCENARIOS,
        "top_decile_definition": f"top {top_count(len(accs))} de {len(accs)} alojamientos; prioridad robusta si aparece en al menos {len(TSMAI_V9_SCENARIOS) - 1} de {len(TSMAI_V9_SCENARIOS)} escenarios.",
        "accommodation_results": {
            "records": int(len(accs)),
            "level_stable_all_scenarios": int(accs["level_stable_all_scenarios"].sum()),
            "level_changed_in_any_scenario": int((~accs["level_stable_all_scenarios"]).sum()),
            "robust_top_decile": int(accs["robust_top_decile"].sum()),
            "mean_rank_spread": round(float(accs["rank_spread"].mean()), 2),
            "rank_spearman_correlation": accommodation_correlations.to_dict(),
            "output": str(ACCOMMODATION_OUT.relative_to(ROOT)),
        },
        "municipality_results": {
            "records": int(len(municipalities)),
            "level_stable_all_scenarios": int(municipalities["level_stable_all_scenarios"].sum()),
            "robust_top_decile": int(municipalities["robust_top_decile"].sum()),
            "mean_rank_spread": round(float(municipalities["rank_spread"].mean()), 2),
            "rank_spearman_correlation": municipality_correlations.to_dict(),
            "robust_top10_municipalities": municipalities.loc[
                municipalities[[f"{name}_rank" for name in TSMAI_V9_SCENARIOS]].le(10).sum(axis=1).ge(len(TSMAI_V9_SCENARIOS) - 1),
                    # Filtra municipios robustos en ranking
                "municipality",
            ].tolist(),
            "output": str(MUNICIPALITY_OUT.relative_to(ROOT)),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Los escenarios modifican pesos, no los componentes ni las fuentes reales de TSMAI V9.",
            "La estabilidad de ranking no valida causalmente el índice ni demuestra preferencias de visitantes o gestores.",
            "Los resultados mantienen las limitaciones de OSM, GTFS y OTP, incluida la estacionalidad calculada dentro de un único feed GTFS versionado.",
        ],
    }
    atomic_json(report, LATEST)
    atomic_json(report, TSMAI_V9_SENSITIVITY_REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))


CLASSIFIED_ROUTES = CURATED / "od_multimodal_routes_classified.parquet"
ACCOMMODATIONS_BASELINE = CURATED / "accommodations_transport_access_baseline.parquet"
DESTINATIONS_BASELINE = CURATED / "tourism_destinations_transport_access_baseline.parquet"
PRIORITY_INDEX_OUT = CURATED / "od_multimodal_priority_index.parquet"
PRIORITY_SENSITIVITY_OUT = CURATED / "od_multimodal_priority_sensitivity.parquet"
PRIORITY_REPORT = ROOT / "docs" / "od_multimodal_priority_index_report.json"
PRIORITY_METHOD_DOC = ROOT / "docs" / "indice_prioridad_multimodal.md"

PRIORITY_WEIGHTS_BALANCED = {
    "origin_access_gap_score": 0.30,
    "destination_access_gap_score": 0.30,
    "route_outcome_constraint_score": 0.25,
    "transit_walk_burden_score": 0.15,
}

PRIORITY_SCENARIOS = {
    "balanced": PRIORITY_WEIGHTS_BALANCED,
    "origin_focus": {
        "origin_access_gap_score": 0.50, "destination_access_gap_score": 0.15,
        "route_outcome_constraint_score": 0.25, "transit_walk_burden_score": 0.10,
    },
    "destination_focus": {
        "origin_access_gap_score": 0.15, "destination_access_gap_score": 0.50,
        "route_outcome_constraint_score": 0.25, "transit_walk_burden_score": 0.10,
    },
    "route_focus": {
        "origin_access_gap_score": 0.20, "destination_access_gap_score": 0.20,
        "route_outcome_constraint_score": 0.45, "transit_walk_burden_score": 0.15,
    },
}

PRIORITY_OUTCOME_CONSTRAINT = {
    "transit_available": 0.00,
    "walking_preferable_by_otp": 0.10,
    "no_scheduled_connection_at_time": 0.50,
    "walk_only_itineraries": 0.50,
    "endpoint_without_stop_in_range": 0.90,
    "direct_walk_network_disconnect": 0.90,
    "other_routing_outcome": 0.60,
}


def priority_gap_score(distance, low=400, high=1200):
    return ((distance - low) / (high - low)).clip(lower=0, upper=1)


def main_analyze_od_priority_sensitivity():
    """Reconstruye el índice de prioridad OD y su sensibilidad de pesos.

    Migrado de notebooks/15_indice_prioridad_multimodal.ipynb para que sea
    reproducible con ``python scripts/run_task.py analyze_od_priority_sensitivity``
    en vez de depender de una ejecución manual del cuaderno.
    """
    for path in (CLASSIFIED_ROUTES, ACCOMMODATIONS_BASELINE, DESTINATIONS_BASELINE):
        if not path.exists():
            raise FileNotFoundError(f"Falta el archivo requerido: {path.name}")
    for name, weights in PRIORITY_SCENARIOS.items():
        if round(sum(weights.values()), 10) != 1:
            raise ValueError(f"Los pesos de {name} no suman uno.")

    classified = pd.read_parquet(CLASSIFIED_ROUTES)
    accommodations = pd.read_parquet(ACCOMMODATIONS_BASELINE)
    destinations = pd.read_parquet(DESTINATIONS_BASELINE)

    origin_access = accommodations[["accommodation_id", "distance_to_nearest_stop_euclidean_m"]].rename(
        columns={"distance_to_nearest_stop_euclidean_m": "origin_nearest_stop_m"}
    )
    destination_access = destinations[["poi_id", "distance_to_nearest_stop_euclidean_m"]].rename(
        columns={"distance_to_nearest_stop_euclidean_m": "destination_nearest_stop_m"}
    )
    index_data = (
        classified
        .merge(origin_access, left_on="origin_accommodation_id", right_on="accommodation_id", how="left", validate="many_to_one")
        .merge(destination_access, left_on="destination_poi_id", right_on="poi_id", how="left", validate="many_to_one")
        .drop(columns=["accommodation_id", "poi_id"])
    )
    if len(index_data) != len(classified):
        raise ValueError("La unión de accesos de origen/destino generó duplicados inesperados.")
    if index_data[["origin_nearest_stop_m", "destination_nearest_stop_m"]].isna().any().any():
        raise ValueError("Faltan distancias de acceso para algún caso OD; revisa las líneas base.")

    index_data["origin_access_gap_score"] = priority_gap_score(index_data["origin_nearest_stop_m"])
    index_data["destination_access_gap_score"] = priority_gap_score(index_data["destination_nearest_stop_m"])
    index_data["route_outcome_constraint_score"] = index_data["analysis_outcome_code"].map(PRIORITY_OUTCOME_CONSTRAINT)
    if index_data["route_outcome_constraint_score"].isna().any():
        unknown = sorted(index_data.loc[index_data["route_outcome_constraint_score"].isna(), "analysis_outcome_code"].unique())
        raise ValueError(f"analysis_outcome_code sin score de restricción declarado: {unknown}")
    index_data["transit_walk_burden_score"] = 0.0
    transit_mask = index_data["analysis_outcome_code"].eq("transit_available")
    index_data.loc[transit_mask, "transit_walk_burden_score"] = priority_gap_score(
        index_data.loc[transit_mask, "transit_walk_distance_m"], low=1600, high=2400
    )
    index_data["priority_index_score"] = sum(
        index_data[component] * weight for component, weight in PRIORITY_WEIGHTS_BALANCED.items()
    )
    index_data["priority_level"] = pd.cut(
        index_data["priority_index_score"], bins=[-0.001, 0.33, 0.66, 1.0], labels=["baja", "media", "alta"]
    ).astype("string")
    index_data["priority_rank_balanced"] = index_data["priority_index_score"].rank(ascending=False, method="min").astype(int)
    atomic_parquet(index_data, PRIORITY_INDEX_OUT)

    sensitivity = index_data[["od_id", "origin_name", "destination_name", "priority_index_score"]].copy()
    for scenario_name, weights in PRIORITY_SCENARIOS.items():
        score = sum(index_data[component] * weight for component, weight in weights.items())
        sensitivity[f"{scenario_name}_score"] = score
        sensitivity[f"{scenario_name}_rank"] = score.rank(ascending=False, method="min").astype(int)
    rank_columns = [f"{name}_rank" for name in PRIORITY_SCENARIOS]
    sensitivity["top5_scenarios"] = (sensitivity[rank_columns] <= 5).sum(axis=1)
    sensitivity["robust_priority"] = sensitivity["top5_scenarios"].ge(3)
    atomic_parquet(sensitivity, PRIORITY_SENSITIVITY_OUT)

    rank_correlations = sensitivity[rank_columns].corr(method="spearman").round(3)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_size": int(len(index_data)),
        "index_type": "Índice multicriterio auditable para priorizar revisiones; no es predictivo ni causal.",
        "balanced_weights": PRIORITY_WEIGHTS_BALANCED,
        "distance_normalization": {
            "origin_and_destination_gap": "0 a <=400 m; 1 a >=1.200 m.",
            "transit_walk_burden": "0 a <=1.600 m; 1 a >=2.400 m.",
        },
        "outcome_constraint_scores": PRIORITY_OUTCOME_CONSTRAINT,
        "sensitivity_scenarios": PRIORITY_SCENARIOS,
        "rank_spearman_correlation": rank_correlations.to_dict(),
        "robust_priorities_top5_in_at_least_3_scenarios": [
            {"od_id": row.od_id, "top5_scenarios": int(row.top5_scenarios)}
            for row in sensitivity.loc[sensitivity["robust_priority"]].itertuples()
        ],
        "output_files": {
            "index": str(PRIORITY_INDEX_OUT.relative_to(ROOT)),
            "sensitivity": str(PRIORITY_SENSITIVITY_OUT.relative_to(ROOT)),
        },
        "limitations": [
            "Los pesos y la codificación de resultados son decisiones explícitas del estudio, no preferencias observadas.",
            "El índice se limita a la muestra de validación y a las condiciones temporales del experimento OTP.",
        ],
    }
    atomic_json(report, PRIORITY_REPORT)

    method_text = f"""# Índice de prioridad de intervención multimodal

## Propósito

Ordenar los {len(index_data)} pares alojamiento-destino de la muestra para identificar casos que requieren revisión de accesibilidad o de servicio. No estima demanda, emisiones, causalidad ni calidad global de cada municipio.

## Componentes y pesos del escenario equilibrado

- Brecha de acceso a parada desde el alojamiento: 0,30.
- Brecha de acceso a parada desde el destino: 0,30.
- Restricción observada en el resultado OTP: 0,25.
- Carga de caminata de la alternativa multimodal, si existe: 0,15.

Las brechas de origen y destino se normalizan entre 400 y 1.200 m, límites utilizados ya en la línea base. La caminata multimodal se normaliza entre 1.600 y 2.400 m, equivalentes a dos accesos de 800 y 1.200 m.

## Robustez

Se recalcula el rango con cuatro conjuntos de pesos: equilibrado, foco en origen, foco en destino y foco en resultado de ruta. Un caso se considera robustamente prioritario si permanece entre los cinco primeros en al menos tres escenarios.

## Limitaciones

Los pesos y la codificación de resultados son decisiones explícitas del estudio y deben discutirse; por eso se entrega el análisis de sensibilidad. El índice se limita a la muestra y a las condiciones temporales del experimento OTP.
"""
    PRIORITY_METHOD_DOC.write_text(method_text, encoding="utf-8")
    print(f"OK Índice de prioridad OD: {len(index_data)} casos; robustos: {int(sensitivity['robust_priority'].sum())} de {len(sensitivity)}")






import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
REQUIRED = {
    "accommodation_id",
    "scenarios_evaluated",
    "transit_ok_share_pct",
    "transit_60min_share_pct",
    "transit_90min_share_pct",
    "transit_120min_share_pct",
    "temporal_transit_level",
}
LEVEL_SCORE = {
    "sin_servicio_en_escenarios": 0,
    "servicio_inestable": 1,
    "servicio_consistente": 2,
}


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


def resolve_workspace_path(value):
    path = value if value.is_absolute() else ROOT / value
    if path.suffix.lower() != ".parquet":
        raise ValueError(f"Se esperaba un fichero Parquet: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"No existe el fichero de campaña: {path}")
    return path


def load_summary(path, label):
    frame = pd.read_parquet(path)
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"La salida {label} no contiene columnas requeridas: {sorted(missing)}")
    if frame["accommodation_id"].isna().any() or frame["accommodation_id"].duplicated().any():
        raise ValueError(f"La salida {label} debe tener un accommodation_id único y no nulo.")
    unknown = set(frame["temporal_transit_level"].dropna().astype(str)).difference(LEVEL_SCORE)
    if unknown:
        raise ValueError(f"La salida {label} contiene niveles temporales desconocidos: {sorted(unknown)}")
    return frame.loc[:, sorted(REQUIRED)].copy()


def manifest_for(run_id):
    manifest_path = ROOT / "data" / "raw" / "tib_gtfs_supply" / run_id / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No existe el snapshot GTFS declarado: {run_id}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "tib_gtfs_supply" or manifest.get("run_id") != run_id:
        raise ValueError(f"El snapshot {run_id} no es un GTFS TIB válido.")
    return manifest


def compare(baseline, seasonal):
    # Compara campanas base y estacional
    joined = baseline.merge(
        seasonal,
        on="accommodation_id",
        how="outer",
        suffixes=("_baseline", "_seasonal"),
        indicator=True,
        validate="one_to_one",
    )
    if not joined["_merge"].eq("both").all():
        missing = joined.loc[~joined["_merge"].eq("both"), "accommodation_id"].tolist()
        raise ValueError(f"Las campañas no cubren el mismo universo de alojamientos; ejemplos: {missing[:10]}")
    joined = joined.drop(columns="_merge")
    joined["temporal_level_score_baseline"] = joined["temporal_transit_level_baseline"].map(LEVEL_SCORE)
    joined["temporal_level_score_seasonal"] = joined["temporal_transit_level_seasonal"].map(LEVEL_SCORE)
    joined["temporal_level_delta"] = joined["temporal_level_score_seasonal"] - joined["temporal_level_score_baseline"]
    joined["transit_ok_share_delta_pp"] = (joined["transit_ok_share_pct_seasonal"] - joined["transit_ok_share_pct_baseline"]).round(2)
    joined["seasonal_change"] = joined["temporal_level_delta"].map({-2: "worsens", -1: "worsens", 0: "unchanged", 1: "improves", 2: "improves"})
    return joined.sort_values("accommodation_id").reset_index(drop=True)


def summary_metrics(result):
    return {
        "accommodations_compared": int(len(result)),
        "seasonal_change_counts": result["seasonal_change"].value_counts().to_dict(),
        "baseline_level_counts": result["temporal_transit_level_baseline"].value_counts().to_dict(),
        "seasonal_level_counts": result["temporal_transit_level_seasonal"].value_counts().to_dict(),
        "mean_transit_ok_share_delta_pp": round(float(result["transit_ok_share_delta_pp"].mean()), 2),
        "median_transit_ok_share_delta_pp": round(float(result["transit_ok_share_delta_pp"].median()), 2),
    }


def main_compare_transit_seasonal_runs():
    parser = argparse.ArgumentParser(description="Compara dos campañas TRANSIT de GTFS TIB reales.")
    parser.add_argument("--baseline-summary", type=Path, required=True)
    parser.add_argument("--seasonal-summary", type=Path, required=True)
    parser.add_argument("--baseline-gtfs-run-id", required=True)
    parser.add_argument("--seasonal-gtfs-run-id", required=True)
    parser.add_argument("--comparison-id", required=True)
    parser.add_argument(
        "--comparison-mode",
        choices=["different_gtfs_snapshots", "intra_feed_seasonal"],
        default="different_gtfs_snapshots",
        help="different_gtfs_snapshots exige dos ZIP distintos; intra_feed_seasonal compara fechas de calendario dentro del mismo ZIP.",
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.comparison_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("comparison-id sólo puede contener letras, números, guiones y guiones bajos.")
    baseline_path = resolve_workspace_path(args.baseline_summary)
    seasonal_path = resolve_workspace_path(args.seasonal_summary)
    baseline_manifest = manifest_for(args.baseline_gtfs_run_id)
    seasonal_manifest = manifest_for(args.seasonal_gtfs_run_id)
    same_run = args.baseline_gtfs_run_id == args.seasonal_gtfs_run_id
    same_payload = baseline_manifest["payload_sha256"] == seasonal_manifest["payload_sha256"]
    if args.comparison_mode == "different_gtfs_snapshots" and (same_run or same_payload):
        raise ValueError("Este modo exige dos snapshots GTFS con run_id y SHA-256 distintos.")
    if args.comparison_mode == "intra_feed_seasonal" and (not same_run or not same_payload):
        raise ValueError("El modo intra_feed_seasonal exige el mismo snapshot GTFS para ambas campañas.")
    plan = {
        "status": "dry_run",
        "comparison_id": args.comparison_id,
        "comparison_mode": args.comparison_mode,
        "baseline_summary": str(baseline_path.relative_to(ROOT)),
        "seasonal_summary": str(seasonal_path.relative_to(ROOT)),
        "baseline_gtfs": {"run_id": args.baseline_gtfs_run_id, "sha256": baseline_manifest["payload_sha256"]},
        "seasonal_gtfs": {"run_id": args.seasonal_gtfs_run_id, "sha256": seasonal_manifest["payload_sha256"]},
        "message": "No se ha escrito ningún resultado. Añade --execute para publicar la comparación P2.",
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    result = compare(load_summary(baseline_path, "base"), load_summary(seasonal_path, "estacional"))
    output = CURATED / f"transit_seasonal_comparison_{args.comparison_id}.parquet"
    report_path = ROOT / "docs" / f"transit_seasonal_comparison_{args.comparison_id}_report.json"
    if output.exists() or report_path.exists():
        raise FileExistsError("La comparación ya existe; usa un comparison-id nuevo para no sobrescribir evidencia.")
    report = {
        "status": "passed",
        "comparison_id": args.comparison_id,
        "comparison_mode": args.comparison_mode,
        "baseline_summary": str(baseline_path.relative_to(ROOT)),
        "seasonal_summary": str(seasonal_path.relative_to(ROOT)),
        "baseline_gtfs": {"run_id": args.baseline_gtfs_run_id, "sha256": baseline_manifest["payload_sha256"]},
        "seasonal_gtfs": {"run_id": args.seasonal_gtfs_run_id, "sha256": seasonal_manifest["payload_sha256"]},
        "output": str(output.relative_to(ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "La comparación mide diferencias entre campañas GTFS y las cuatro franjas declaradas, no puntualidad observada.",
            "En modo intra_feed_seasonal el resultado representa variación de calendario dentro de un único GTFS, no cambios entre publicaciones del proveedor.",
            "No se imputan itinerarios ausentes ni se interpretan como ausencia de infraestructura.",
            "Los pares origen-destino son los mismos del barrido P0 y no representan demanda turística observada.",
        ],
        **summary_metrics(result),
    }
    atomic_parquet(result, output)
    atomic_json(report, report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))






import json
from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"


def main_generate_destination_clusters():
    from sklearn.cluster import DBSCAN
    import geopandas as gpd
    import numpy as np

    input_path = ROOT / "data" / "curated" / "dashboard_current_tourism_destinations_osm.parquet"
    output_path = ROOT / "data" / "curated" / "destination_clusters_dbscan.parquet"

    print("Loading destinations...")
    df = gpd.read_parquet(input_path)
    geom_column = "geom" if "geom" in df.columns else df.geometry.name

    print("Extracting coordinates...")
    coords = np.radians(np.column_stack((df[geom_column].y, df[geom_column].x)))

    print("Running DBSCAN clustering...")
    db = DBSCAN(eps=0.5 / 6371, min_samples=3, algorithm="ball_tree", metric="haversine").fit(coords)
    df = df.assign(cluster_id=db.labels_)

    valid_clusters = df.loc[df["cluster_id"] != -1].copy()
    print(f"Encontrados {valid_clusters['cluster_id'].nunique()} clústeres válidos.")

    cluster_summary = valid_clusters.groupby("cluster_id").agg(
        poi_count=("poi_id", "count"),
        dominant_theme=("destination_theme", lambda x: x.mode()[0] if not x.mode().empty else "mixed"),
        lat_center=(geom_column, lambda geom: geom.y.mean()),
        lon_center=(geom_column, lambda geom: geom.x.mean()),
        top_name=("name", lambda x: x.value_counts().idxmax() if not x.empty and len(x.value_counts()) > 0 else "Unknown"),
    ).reset_index()
    cluster_summary["macro_destination_name"] = (
        "Zona " + cluster_summary["top_name"].astype(str) + " (" + cluster_summary["dominant_theme"] + ")"
    )

    print("Saving to parquet...")
    cluster_summary.to_parquet(output_path, index=False)
    print(f"OK Clústeres generados: {output_path}")




import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "curated" / "accommodations_transport_access_baseline.parquet"
ACTIVE = ROOT / "data" / "curated" / "accommodations_active_mobility_access.parquet"
ACCESS_INTERVENTION_SCENARIOS_OUT = ROOT / "data" / "curated" / "municipality_access_intervention_scenarios.parquet"
ACCESS_INTERVENTION_SCENARIOS_REPORT = ROOT / "docs" / "access_intervention_scenarios_report.json"


def main_simulate_access_interventions():
    import geopandas as gpd

    # Carga alojamientos y movilidad activa
    baseline = gpd.read_parquet(BASELINE)
    active = pd.read_parquet(ACTIVE)[["accommodation_id", "distance_to_cycle_infrastructure_m"]]
    data = baseline.merge(active, on="accommodation_id", how="left", validate="one_to_one")
    data["places"] = pd.to_numeric(data["places"], errors="coerce").fillna(0)
    distance = data["distance_to_nearest_stop_euclidean_m"]
    data["baseline_covered_800"] = distance.le(800)
    data["first_last_mile_candidate"] = distance.gt(800) & distance.le(1200)
    data["critical_gap_candidate"] = distance.gt(1200)
    data["cycle_gap_candidate"] = data["distance_to_cycle_infrastructure_m"].gt(800)
    rows = []
    for municipality, group in data.groupby("municipality_raw", dropna=False):
        total = len(group)
        base = 100 * group["baseline_covered_800"].mean()
        first_last = 100 * (group["baseline_covered_800"] | group["first_last_mile_candidate"]).mean()
        upper = 100 * (group["baseline_covered_800"] | group["first_last_mile_candidate"] | group["critical_gap_candidate"]).mean()
        rows.append({
            "municipality": municipality, "accs": total, "tourist_places": float(group["places"].sum()),
            "baseline_coverage_800m_pct": base,
            "scenario_first_last_mile_coverage_800m_pct": first_last,
            "scenario_upper_bound_connection_coverage_800m_pct": upper,
            "first_last_mile_candidates": int(group["first_last_mile_candidate"].sum()),
            "critical_gap_candidates": int(group["critical_gap_candidate"].sum()),
            "cycle_infrastructure_gap_candidates": int(group["cycle_gap_candidate"].sum()),
        })
    result = pd.DataFrame(rows)
    result["first_last_mile_gain_pp"] = result["scenario_first_last_mile_coverage_800m_pct"] - result["baseline_coverage_800m_pct"]
    result["upper_bound_gain_pp"] = result["scenario_upper_bound_connection_coverage_800m_pct"] - result["baseline_coverage_800m_pct"]

    result["review_priority_score"] = (result["critical_gap_candidates"] * 2 + result["first_last_mile_candidates"]) * (1 + result["tourist_places"] / max(result["tourist_places"].max(), 1))
    result = result.sort_values("review_priority_score", ascending=False)
    result.to_parquet(ACCESS_INTERVENTION_SCENARIOS_OUT, index=False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Simulación determinista de cobertura euclídea a parada GTFS para orientar revisión de intervenciones.",
        "scenario_first_last_mile": "Hipótesis: cada alojamiento entre 800 y 1.200 m consigue una conexión de última milla que lo sitúa dentro de 800 m.",
        "scenario_upper_bound_connection": "Límite teórico: todos los alojamientos sin cobertura obtienen conexión dentro de 800 m. No representa una ubicación, coste, demanda ni viabilidad de una parada/lanzadera.",
        "limitations": ["No se usa para recomendar obras automáticas.", "No incorpora red peatonal, orografía, presupuesto, demanda observada ni permisos.", "Los resultados son potenciales máximos bajo la hipótesis explícita."],
    }
    ACCESS_INTERVENTION_SCENARIOS_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK Escenarios generados para {len(result)} municipios")




import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
TSMAI_INPUT = CURATED / "municipality_tsmai_v9_sensitivity.parquet"
OFFER_INPUT = CURATED / "municipality_tourist_offer_seasonality.parquet"
DEMAND_ANOMALIES_OUT = CURATED / "municipality_demand_accessibility_anomalies.parquet"
DEMAND_ANOMALIES_REPORT = ROOT / "docs" / "demand_accessibility_anomalies_report.json"

Z_SCORE_THRESHOLD = 1.0


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


def normalized_municipality(value):
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def zscore(series):
    std = series.std(ddof=0)
    if not std or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def main_detect_demand_accessibility_anomalies():
    """Detección de anomalías por umbral de desviación típica (z-score).

    Cruza el TSMAI V9 municipal con la oferta turística oficial (Ibestat) para
    señalar municipios con demanda alta y accesibilidad sostenible baja. No es
    un modelo entrenado: es un umbral estadístico simple sobre datos ya
    calculados por el resto del pipeline.
    """
    if not TSMAI_INPUT.is_file():
        raise FileNotFoundError("Ejecuta primero analyze_tsmai_v9_sensitivity.")
    if not OFFER_INPUT.is_file():
        raise FileNotFoundError("Ejecuta primero build_tourist_offer_seasonality.")

    tsmai = pd.read_parquet(TSMAI_INPUT)[["municipality", "accommodations", "balanced_score"]].copy()
    offer = pd.read_parquet(OFFER_INPUT)[["municipality", "latest_official_places"]].copy()

    tsmai["join_key"] = tsmai["municipality"].map(normalized_municipality)
    offer["join_key"] = offer["municipality"].map(normalized_municipality)

    matched_keys = set(tsmai["join_key"]) & set(offer["join_key"])
    unmatched_tsmai = sorted(tsmai.loc[~tsmai["join_key"].isin(matched_keys), "municipality"])
    merged = tsmai.merge(
        offer.drop(columns="municipality"), on="join_key", how="inner", validate="one_to_one"
    ).drop(columns="join_key")

    merged["tourist_demand_zscore"] = zscore(merged["latest_official_places"].fillna(0)).round(2)
    merged["tsmai_zscore"] = zscore(merged["balanced_score"].fillna(0)).round(2)
    merged["demand_accessibility_gap"] = (merged["tourist_demand_zscore"] - merged["tsmai_zscore"]).round(2)
    merged["is_anomaly_high_demand_low_accessibility"] = merged["tourist_demand_zscore"].ge(Z_SCORE_THRESHOLD) & merged[
        "tsmai_zscore"
    ].le(-Z_SCORE_THRESHOLD)

    result = merged.sort_values("demand_accessibility_gap", ascending=False).reset_index(drop=True)
    atomic_parquet(result, DEMAND_ANOMALIES_OUT)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Umbral de desviación típica (z-score) sobre TSMAI V9 balanced y plazas turísticas oficiales Ibestat más recientes por municipio.",
        "z_score_threshold": Z_SCORE_THRESHOLD,
        "municipalities_compared": int(len(result)),
        "anomalies_detected": int(result["is_anomaly_high_demand_low_accessibility"].sum()),
        "anomalous_municipalities": result.loc[
            result["is_anomaly_high_demand_low_accessibility"], "municipality"
        ].tolist(),
        "municipalities_without_official_tourist_offer_match": unmatched_tsmai,
        "limitations": [
            "Es un umbral estadístico simple, no un modelo entrenado ni un test de significación.",
            "Las plazas turísticas oficiales son capacidad de oferta declarada, no ocupación, llegadas ni demanda observada.",
            "El emparejamiento de municipios usa normalización de texto; los municipios sin oferta turística oficial en Ibestat quedan excluidos del análisis, no clasificados como 'sin anomalía'.",
            "Un z-score alto de demanda y bajo de accesibilidad señala una brecha relativa entre municipios de Mallorca, no un umbral absoluto de calidad de servicio.",
        ],
    }
    atomic_json(report, DEMAND_ANOMALIES_REPORT)
    print(f"OK Anomalías demanda-accesibilidad: {report['anomalies_detected']} de {report['municipalities_compared']} municipios")




import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
TSMAI_V9_INPUT = CURATED / "accommodations_tsmai_v9_seasonal_transit.parquet"
UNIVERSAL_ACCESS_LATEST = CURATED / "latest_universal_access_evidence.json"
UNIVERSAL_ACCESS_FALLBACK = CURATED / "accommodations_documented_accessibility_evidence.parquet"
TSMAI_EXTENDED_OUT = CURATED / "accommodations_tsmai_extended.parquet"
TSMAI_EXTENDED_REPORT = ROOT / "docs" / "tsmai_extended_report.json"

CORE_WEIGHT = 0.75
UNIVERSAL_ACCESS_WEIGHT = 0.25
EVIDENCE_WEIGHTS = {
    "osm_evidence_within_400m": 0.5,
    "osm_pedestrian_context_within_400m": 0.2,
    "gtfs_wheelchair_stop_within_800m": 0.3,
}
LEVEL_LABELS = ["prioridad de mejora", "intermedio", "favorable"]
LEVEL_BINS = [-0.01, 0.40, 0.67, 1.01]


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


def resolve_universal_access_path():
    if UNIVERSAL_ACCESS_LATEST.is_file():
        latest = json.loads(UNIVERSAL_ACCESS_LATEST.read_text(encoding="utf-8"))
        path = ROOT / latest["accommodation_evidence_output"]
        if path.is_file():
            return path
    return UNIVERSAL_ACCESS_FALLBACK


def level_of(scores):
    return pd.cut(scores, LEVEL_BINS, labels=LEVEL_LABELS).astype("string")


def main_calculate_tsmai_extended():
    """Índice extendido OPCIONAL: TSMAI V9 + evidencia de accesibilidad universal.

    No sustituye ni modifica el TSMAI V9 oficial (scripts/etl_04f_transporte_publico.py)
    ni sus pesos publicados y justificados en docs/JUSTIFICACION_PESOS_TSMAI_V9.md. Es una
    combinación exploratoria aparte para estimar el efecto de sumar evidencia de
    accesibilidad universal documentada (OSM + parada GTFS con wheelchair_boarding), que
    el TSMAI V9 deja fuera por falta de cobertura y validación metodológica específica.
    No incorpora seguridad vial: los microdatos DGT sólo identifican con confianza 15 de
    43 municipios y no son atribuibles a un alojamiento o ruta concreta.
    """
    if not TSMAI_V9_INPUT.is_file():
        raise FileNotFoundError("Ejecuta primero build_current_tsmai_v9_seasonal_transit.")
    universal_path = resolve_universal_access_path()
    if not universal_path.is_file():
        raise FileNotFoundError("Ejecuta primero build_universal_access_evidence.")

    tsmai = pd.read_parquet(TSMAI_V9_INPUT)[
        ["accommodation_id", "commercial_name", "municipality", "tsmai_v9_score", "tsmai_v9_level"]
    ].copy()
    universal = pd.read_parquet(universal_path)[
        [
            "accommodation_id",
            "osm_evidence_within_400m",
            "osm_pedestrian_context_within_400m",
            "gtfs_wheelchair_stop_within_800m",
            "documented_accessibility_evidence_level",
        ]
    ].copy()

    data = tsmai.merge(universal, on="accommodation_id", how="left", validate="one_to_one")
    accommodations_without_evidence_match = int(data["documented_accessibility_evidence_level"].isna().sum())
    for column in EVIDENCE_WEIGHTS:
        data[column] = data[column].fillna(False)

    data["universal_access_evidence_score"] = sum(
        data[column].astype(float) * weight for column, weight in EVIDENCE_WEIGHTS.items()
    ).round(3)
    data["tsmai_extended_score"] = (
        CORE_WEIGHT * data["tsmai_v9_score"] + UNIVERSAL_ACCESS_WEIGHT * data["universal_access_evidence_score"]
    ).round(3)
    data["tsmai_extended_level"] = level_of(data["tsmai_extended_score"])
    data["tsmai_extended_delta_vs_v9"] = (data["tsmai_extended_score"] - data["tsmai_v9_score"]).round(3)
    data["level_changed_vs_v9"] = data["tsmai_extended_level"].ne(data["tsmai_v9_level"].astype("string"))

    atomic_parquet(data, TSMAI_EXTENDED_OUT)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "experimental_optional",
        "purpose": "Índice extendido opcional; no sustituye el TSMAI V9 oficial ni sus pesos publicados.",
        "core_weight": CORE_WEIGHT,
        "universal_access_weight": UNIVERSAL_ACCESS_WEIGHT,
        "evidence_weights": EVIDENCE_WEIGHTS,
        "records": int(len(data)),
        "accommodations_without_universal_access_match": accommodations_without_evidence_match,
        "level_changed_vs_v9": int(data["level_changed_vs_v9"].sum()),
        "mean_delta_vs_v9": round(float(data["tsmai_extended_delta_vs_v9"].mean()), 4),
        "limitations": [
            "No es el TSMAI V9 oficial: es una combinación exploratoria adicional que se publica aparte.",
            "Los pesos (0.75 índice oficial / 0.25 evidencia de accesibilidad universal) son una elección analítica declarada, no calibrada ni validada empíricamente, igual que el resto de escenarios de sensibilidad del proyecto.",
            "La evidencia de accesibilidad universal es proximidad geométrica a etiquetas OSM/GTFS, no una auditoría de campo ni una certificación de accesibilidad física.",
            "No incorpora seguridad vial: los microdatos DGT sólo identifican con confianza 15 de 43 municipios de la fuente local y no son atribuibles a un alojamiento o ruta concreta.",
        ],
    }
    atomic_json(report, TSMAI_EXTENDED_REPORT)
    print(
        f"OK TSMAI extendido calculado para {len(data)} alojamientos "
        f"({report['level_changed_vs_v9']} cambian de nivel frente al TSMAI V9 oficial)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_") else "run_" + args.task

    if task_name == "run_analyze_tsmai_v2_sensitivity":
        main_analyze_tsmai_v2_sensitivity()
        sys.exit(0)
    if task_name == "run_analyze_tsmai_v9_sensitivity":
        main_analyze_tsmai_v9_sensitivity()
        sys.exit(0)
    if task_name == "run_compare_transit_seasonal_runs":
        main_compare_transit_seasonal_runs()
        sys.exit(0)
    if task_name == "run_generate_destination_clusters":
        main_generate_destination_clusters()
        sys.exit(0)
    if task_name == "run_simulate_access_interventions":
        main_simulate_access_interventions()
        sys.exit(0)
    if task_name == "run_detect_demand_accessibility_anomalies":
        main_detect_demand_accessibility_anomalies()
        sys.exit(0)
    if task_name == "run_calculate_tsmai_extended":
        main_calculate_tsmai_extended()
        sys.exit(0)
    print(f"Task {task_name} not found.")


