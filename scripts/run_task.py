"""Punto de entrada único para las tareas ETL y de validación vigentes.

Evita los nombres históricos de scripts que ya no existen y delega en la
función ``main_*`` que conserva los argumentos y controles de cada tarea.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TASKS: dict[str, tuple[str, str]] = {
    "prepare_official_accommodations": ("scripts.etl_01_preparacion", "main_prepare_official_accommodations"),
    "prepare_osm_mobility_network": ("scripts.etl_01_preparacion", "main_prepare_osm_mobility_network"),
    "prepare_otp_inputs": ("scripts.etl_01_preparacion", "main_prepare_otp_inputs"),
    "prepare_tib_gtfs": ("scripts.etl_01_preparacion", "main_prepare_tib_gtfs"),
    "ingest_licensed_mobility_survey": ("scripts.etl_01_preparacion", "main_ingest_licensed_mobility_survey"),
    "prepare_inside_airbnb_reviews": ("scripts.etl_01_preparacion", "main_prepare_inside_airbnb_reviews"),
    "build_current_bicycle_network_access": ("scripts.etl_02_construir_redes", "main_current_bicycle_network_access"),
    "build_current_transit_network_access": ("scripts.etl_02_construir_redes", "main_current_transit_network_access"),
    "build_current_walk_network_access": ("scripts.etl_02_construir_redes", "main_current_walk_network_access"),
    "build_tib_public_transport_access": ("scripts.etl_02_construir_redes", "main_tib_public_transport_access"),
    "build_multimodal_route_sample": ("scripts.etl_03_calcular_rutas", "main_build_multimodal_route_sample"),
    "build_otp_walk_isochrones": ("scripts.etl_03_calcular_rutas", "main_build_otp_walk_isochrones"),
    "build_route_infrastructure_profiles": ("scripts.etl_03_calcular_rutas", "main_build_route_infrastructure_profiles"),
    "build_route_slope_profiles": ("scripts.etl_03_calcular_rutas", "main_build_route_slope_profiles"),
    "build_sustainable_route_recommendations": ("scripts.etl_03_calcular_rutas", "main_build_sustainable_route_recommendations"),
    "build_active_mobility_layers": ("scripts.etl_03_calcular_rutas", "main_build_active_mobility_layers"),
    "build_aemet_weather_context": ("scripts.etl_04a_clima_aemet", "main_aemet_weather_context"),
    "build_current_sample_aemet_route_context": ("scripts.etl_04a_clima_aemet", "main_current_sample_aemet_route_context"),
    "build_air_quality_context": ("scripts.etl_04b_calidad_aire", "main_air_quality_context"),
    "build_road_safety_context": ("scripts.etl_04c_seguridad_vial", "main_road_safety_context"),
    "build_current_sample_slope_profiles": ("scripts.etl_04d_topografia", "main_current_sample_slope_profiles"),
    "build_osm_active_mobility_evidence": ("scripts.etl_04e_evidencia_osm", "main_osm_active_mobility_evidence"),
    "build_osm_tourism_destinations": ("scripts.etl_04e_evidencia_osm", "main_osm_tourism_destinations"),
    "build_tourism_proximity": ("scripts.etl_04e_evidencia_osm", "main_tourism_proximity"),
    "build_universal_access_evidence": ("scripts.etl_04e_evidencia_osm", "main_universal_access_evidence"),
    "build_current_tsmai_v9_seasonal_transit": ("scripts.etl_04f_transporte_publico", "main_current_tsmai_v9_seasonal_transit"),
    "build_tourist_offer_seasonality": ("scripts.etl_04f_transporte_publico", "main_tourist_offer_seasonality"),
    "build_transit_temporal_robustness": ("scripts.etl_04f_transporte_publico", "main_transit_temporal_robustness"),
    "build_accommodation_accessibility_index_v3": ("scripts.etl_04g_capas_dashboard", "main_accommodation_accessibility_index_v3"),
    "build_current_dashboard_layers": ("scripts.etl_04g_capas_dashboard", "main_current_dashboard_layers"),
    "build_current_sample_route_documentary_evidence": ("scripts.etl_04g_capas_dashboard", "main_current_sample_route_documentary_evidence"),
    "aggregate_mobility_sentiment": ("scripts.etl_05_analizar_datos", "main_aggregate_mobility_sentiment"),
    "analyze_multilingual_sentiment": ("scripts.etl_05_analizar_datos", "main_analyze_multilingual_sentiment"),
    "analyze_tsmai_v9_sensitivity": ("scripts.etl_05_analizar_datos", "main_analyze_tsmai_v9_sensitivity"),
    "analyze_od_priority_sensitivity": ("scripts.etl_05_analizar_datos", "main_analyze_od_priority_sensitivity"),
    "compare_transit_seasonal_runs": ("scripts.etl_05_analizar_datos", "main_compare_transit_seasonal_runs"),
    "generate_ai_route_narratives": ("scripts.etl_05_analizar_datos", "main_generate_ai_route_narratives"),
    "generate_destination_clusters": ("scripts.etl_05_analizar_datos", "main_generate_destination_clusters"),
    "simulate_access_interventions": ("scripts.etl_05_analizar_datos", "main_simulate_access_interventions"),
    "prioritize_access_interventions": ("scripts.etl_05_analizar_datos", "main_prioritize_access_interventions"),
    "detect_demand_accessibility_anomalies": ("scripts.etl_05_analizar_datos", "main_detect_demand_accessibility_anomalies"),
    "calculate_tsmai_extended": ("scripts.etl_05_analizar_datos", "main_calculate_tsmai_extended"),
    "validate_bicycle_routes": ("scripts.etl_07_validar_calidad", "main_validate_bicycle_routes"),
    "validate_licensed_reviews": ("scripts.etl_07_validar_calidad", "main_validate_licensed_reviews"),
    "validate_massive_routes": ("scripts.etl_07_validar_calidad", "main_validate_massive_routes"),
    "validate_otp_service": ("scripts.etl_07_validar_calidad", "main_validate_otp_service"),
    "validate_pdf_export": ("scripts.etl_07_validar_calidad", "main_validate_pdf_export"),
    "validate_source_registry": ("scripts.etl_07_validar_calidad", "main_validate_source_registry"),
    "validate_streamlit_app": ("scripts.etl_07_validar_calidad", "main_validate_streamlit_app"),
    "build_memoria_tfm": ("scripts.etl_06_publicar_resultados", "main_memoria_tfm"),
}


def usage() -> None:
    print("Uso: python scripts/run_task.py <tarea> [argumentos de la tarea]")
    print("     python scripts/run_task.py --check")
    print("\nTareas disponibles:")
    for task in sorted(TASKS):
        print(f"  - {task}")


def check_tasks() -> None:
    """Comprueba que cada tarea publicada puede cargarse sin ejecutarla."""
    failures: list[tuple[str, str]] = []
    for task, (module_name, function_name) in sorted(TASKS.items()):
        try:
            module = importlib.import_module(module_name)
            entrypoint = getattr(module, function_name)
            if not callable(entrypoint):
                raise TypeError(f"{module_name}.{function_name} no es invocable")
        except (ImportError, AttributeError, TypeError, SyntaxError) as exc:
            failures.append((task, f"{type(exc).__name__}: {exc}"))

    checked = len(TASKS) - len(failures)
    print(f"Comprobadas {checked}/{len(TASKS)} tareas sin ejecutarlas.")
    if failures:
        for task, detail in failures:
            print(f"  - {task}: {detail}", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "--list"}:
        usage()
        return

    if sys.argv[1] == "--check":
        check_tasks()
        return

    task, *task_args = sys.argv[1:]
    target = TASKS.get(task)
    if target is None:
        print(f"Tarea desconocida: {task}", file=sys.stderr)
        usage()
        raise SystemExit(2)

    module_name, function_name = target
    sys.argv = [f"{Path(__file__).name} {task}", *task_args]
    module = importlib.import_module(module_name)
    getattr(module, function_name)()


if __name__ == "__main__":
    main()
