# Reproducibilidad operativa y universos de análisis

Este documento es la referencia de ejecución vigente. Los nombres históricos como `prepare_tib_gtfs.py`, `validate_streamlit_app.py` o `etl_*.py` no son archivos ejecutables de esta versión. Usa siempre el lanzador único:

```powershell
python scripts/run_task.py --list
python scripts/run_task.py --check
python scripts/run_task.py <tarea> [argumentos de la tarea]
```

No existe una tarea `all`: las fases consumen artefactos de la fase anterior y las consultas OTP, AEMET o la publicación PostGIS pueden requerir servicios, credenciales o autorización explícita. Ejecutarlas como un bloque opaco haría menos trazable el TFM.

`--check` importa y comprueba los puntos de entrada de todas las tareas
publicadas sin consultar servicios ni escribir artefactos. Debe ejecutarse tras
cambiar el lanzador, una dependencia o un módulo ETL.

## Reconciliación de cifras

| Universo | Snapshot y regla | Registros |
|---|---|---:|
| Auditoría histórica de línea base | Snapshot CAIB del 03-09-2026; puntos plausibles dentro de Mallorca | 1.463 alojamientos |
| Línea base histórica | Destinos OSM nombrados con la taxonomía inicial | 1.423 destinos |
| Capa oficial actual P7 | Snapshot CAIB `20260912T224211Z`; 1.876 entradas, menos 399 sin geometría y 16 fuera de alcance | 1.461 alojamientos |
| TSMAI V9 y dashboard actual | Capa oficial actual P7 y sus entradas analíticas versionadas | 1.461 alojamientos |
| Mapa territorial actual P7 | Destinos OSM temáticos, no limitados a la taxonomía histórica de POI nombrados | 4.487 destinos |

No se debe atribuir la diferencia 1.463 → 1.461 a una unión analítica: procede de un snapshot oficial posterior y de sus controles de calidad espacial. Los informes de evidencia son `docs/data_quality_accommodations.json`, `docs/accommodations_preparation_report.json` y `docs/dashboard_current_layers_report.json`.

## Preparación y validación mínima

```powershell
conda env create -f environment-dev.yml
conda activate tfm-mallorca
python scripts/run_task.py validate_source_registry
python -m pytest -q
```

Para la demostración con rutas en vivo, inicia OTP antes del dashboard:

```powershell
docker compose -f docker/otp/docker-compose.yml up -d otp-server
streamlit run app/streamlit_app.py
```

## Flujo por fases

1. Ingesta autorizada de datos: `scripts/extract/ingest_source.py` mantiene su interfaz propia con `--source-id` y, para escribir, `--execute`.
2. Preparación: `prepare_official_accommodations`, `prepare_osm_mobility_network`, `prepare_tib_gtfs` y `prepare_otp_inputs`.
3. Red y cobertura: `build_tib_public_transport_access`, `build_active_mobility_layers`, `build_current_walk_network_access`, `build_current_bicycle_network_access` y `build_current_transit_network_access`.
4. Rutas y evidencia: `build_multimodal_route_sample`, `build_route_infrastructure_profiles`, `build_route_slope_profiles` y `build_sustainable_route_recommendations`.
5. Índice y publicación: `build_current_tsmai_v9_seasonal_transit`, `build_current_dashboard_layers`, `analyze_tsmai_v9_sensitivity` y las tareas de validación correspondientes.

Ejemplo de consulta OTP explícita, que escribe resultados sólo con `--execute`:

```powershell
python scripts/run_task.py build_current_walk_network_access --date 2026-09-15 --time 10:00 --execute --resume
```

La publicación PostGIS no se incluye en el lanzador porque la función de publicación no está presente en el código actual. Debe volver a incorporarse y probarse antes de documentarla como una capacidad ejecutable.

## Credencial AEMET

La clave expuesta previamente debe ser revocada por el titular en el portal de AEMET y sustituida sólo en el archivo local `.env`. Nunca se debe copiar a `.env.example`, documentación, notebooks, commits o capturas de pantalla.
