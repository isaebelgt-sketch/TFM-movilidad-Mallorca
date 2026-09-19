# Operación del prototipo

> **Referencia de ejecución:** usa el lanzador único
> `python scripts/run_task.py <tarea>`. La guía de fases y la reconciliación de
> universos están en
> [REPRODUCIBILIDAD_OPERATIVA.md](REPRODUCIBILIDAD_OPERATIVA.md).

Desde la carpeta raíz `TFM_Movilidad_Mallorca_v2`, activar el entorno:

```powershell
conda activate tfm-mallorca-v2
```

Antes de regenerar una fase, comprueba que el lanzador puede cargar sus 43
tareas publicadas sin ejecutarlas:

```powershell
python scripts/run_task.py --check
```

Antes de descargar o sustituir cualquier fuente, valida el registro de
licencias y trazabilidad:

```powershell
python scripts/run_task.py validate_source_registry
```

Iniciar el motor de rutas cuando se vayan a consultar indicaciones o geometrías OTP:

```powershell
docker compose -f docker/otp/docker-compose.yml up -d otp-server
```

Iniciar el dashboard:

```powershell
streamlit run app/streamlit_app.py
```

La API local es opcional para integrar el prototipo con otro cliente. Se documenta automáticamente en `http://localhost:8000/docs`:

```powershell
uvicorn api.main:app --reload --port 8000
```

Endpoints principales:

- `GET /health`: estado de TSMAI V9 y referencia al motor OTP.
- `GET /municipalities`: agregación municipal de TSMAI V9.
- `GET /accommodations/tsmai`: evidencia TSMAI V9 por alojamiento, con filtros de municipio y nivel.
- `GET /sensitivity/tsmai-v9`: pesos, métricas y limitaciones del análisis P6.
- `GET /sensitivity/tsmai-v9/municipalities?robust_only=true`: municipios robustos en el top decil de P6.
- `GET /legacy/municipalities-v1`: línea base histórica, no resultado vigente.
- `GET /cases/{od_id}`: evidencia y recomendación de un caso histórico, por ejemplo `OD03`.
- `GET /routes/walk`: proxy de una ruta peatonal OTP. Requiere que OTP esté activo.

Si cambian datos de entrada o resultados del barrido, regenerar los artefactos
en este orden:

```powershell
python scripts/run_task.py prepare_official_accommodations
python scripts/run_task.py prepare_osm_mobility_network
python scripts/run_task.py prepare_tib_gtfs
python scripts/run_task.py prepare_otp_inputs
python scripts/run_task.py build_tib_public_transport_access
python scripts/run_task.py build_active_mobility_layers
python scripts/run_task.py build_current_walk_network_access --date 2026-09-15 --time 10:00 --execute --resume
python scripts/run_task.py build_current_bicycle_network_access --date 2026-09-15 --time 10:00 --execute --resume
python scripts/run_task.py build_current_transit_network_access --date 2026-09-15 --time 10:00 --execute --resume
python scripts/run_task.py build_current_tsmai_v9_seasonal_transit
python scripts/run_task.py analyze_tsmai_v9_sensitivity
python scripts/run_task.py build_current_dashboard_layers
python scripts/run_task.py validate_streamlit_app
python -m pytest -q
```

## Capas de movilidad activa y pendiente

Estas extensiones usan exclusivamente las fuentes abiertas ya documentadas: red
OpenStreetMap, rutas locales OTP y el MDP05 del IGN/CNIG (CC-BY 4.0). Con OTP
activo, se pueden regenerar así:

```powershell
python scripts/run_task.py build_osm_active_mobility_evidence
python scripts/run_task.py build_otp_walk_isochrones --execute
python scripts/run_task.py build_route_slope_profiles --execute
```

- La capa ciclista y la evidencia peatonal son etiquetas OSM y proximidad; no son una auditoría de campo.
- Las isócronas proceden de una cuadrícula de 750 m que consulta rutas WALK reales de OTP; se presentan como aproximación de red.
- La pendiente se calcula para los 20 casos priorizados, con muestreo cada 1.000 m sobre la malla MDP05 de 5 m. No mide estado del pavimento, aceras o cruces.

Como complemento actual de esa muestra histórica, P10 perfila los 12 pares
reales de la muestra multimodal actual (3 bandas de acceso TIB × 4 temas de
destino). Primero se puede comprobar el plan sin hacer peticiones:

```powershell
python scripts/run_task.py build_multimodal_route_sample
```

Con OTP activo, la ejecución real conserva la geometría WALK devuelta por OTP
y cada observación MDP05 del WCS IGN/CNIG en un snapshot `raw` antes de publicar
el perfil curado:

```powershell
python scripts/run_task.py build_current_sample_slope_profiles --execute --spacing-m 1000 --workers 4
```

El resultado no sustituye los 20 casos históricos ni se incorpora a TSMAI V9:
la cobertura es una muestra estratificada, no una medición por alojamiento.

Cuando el manifiesto `latest_current_sample_slope_profiles.json` tenga estado
`passed`, el dashboard muestra la distribución, tabla y dificultad P95 de estos
12 pares en un bloque independiente. No se muestran perfiles bloqueados o
incompletos como si fueran pendientes observadas.

P13 perfila, por separado, la documentación ciclista y peatonal OSM a lo largo
de esos mismos 12 pares actuales. Con OTP activo:

```powershell
python scripts/run_task.py build_current_sample_route_documentary_evidence
python scripts/run_task.py build_current_sample_route_documentary_evidence --execute --spacing-m 100 --radius-m 30 --workers 4
```

Los porcentajes resultantes son proximidad a etiquetas OSM, nunca una medida de
seguridad, iluminación, tráfico, continuidad física o accesibilidad universal.

## Alcance de los índices TSMAI

El producto vigente es **TSMAI V9 por alojamiento**. Combina datos oficiales de
alojamientos, evidencia OSM, GTFS TIB y rutas OTP WALK, BICYCLE y TRANSIT. El
componente TRANSIT es la media simple de cuatro escenarios de verano y cuatro
de invierno del mismo GTFS versionado; no es un promedio anual, una frecuencia
observada ni una medida de puntualidad. El archivo principal es
`data/curated/accommodations_tsmai_v9_seasonal_transit.parquet`.

La estabilidad de sus pesos se reproduce sin añadir ni simular observaciones:

```powershell
python scripts/run_task.py analyze_tsmai_v9_sensitivity
```

Este paso publica resultados por alojamiento y municipio, junto con
`docs/tsmai_v9_sensitivity_report.json`. El escenario `balanced` debe
reproducir exactamente TSMAI V9; los otros cuatro escenarios sólo cambian las
ponderaciones de los mismos componentes reales. Una prioridad robusta aparece
en el top decil en al menos cuatro de los cinco escenarios.

TSMAI V1–V8 se conservan exclusivamente para reproducibilidad histórica. El
resultado final del desafío es TSMAI V9 por alojamiento.

## Capas actuales del mapa territorial (P7)

El mapa territorial usa exclusivamente cuatro capas P7 versionadas: alojamientos
oficiales enriquecidos con TSMAI V9, paradas del GTFS TIB, destinos turísticos
OSM y evidencia ciclista OSM. Se publican con su manifiesto y hashes en
`data/curated/latest_dashboard_current_layers.json`.

Después de regenerar TSMAI V9, el GTFS o el recorte OSM, ejecutar:

```powershell
python scripts/run_task.py build_current_dashboard_layers
python scripts/run_task.py validate_streamlit_app
```

Los casos OD, perfiles K-Means y simulaciones de emisiones que aún aparecen en
la interfaz están señalados como referencias históricas: no alimentan el mapa
ni el índice TSMAI V9 actual.

Los índices municipales V1 y V2 usan cobertura GTFS a 800 m, brechas superiores a 1.200 m, proximidad mediana a parada, éxito de routing OTP y disponibilidad de tránsito en el cribado exploratorio; V2 añade proximidad a ciclovías, evidencia peatonal OSM y destinos turísticos. TSMAI V9 es individual y utiliza siete componentes de proximidad, servicio y rutas OTP. Ninguna versión incorpora pendiente, sentimiento, seguridad percibida, accesibilidad universal certificada, tráfico por tramo ni calidad del aire como componente del índice.

El campo GTFS `wheelchair_boarding` se entrega en una capa separada como proxy documental. No constituye una certificación de accesibilidad universal.

El dashboard conserva **TSMAI V1–V8** como referencias históricas. La versión
vigente, TSMAI V9, culmina la evolución iniciada en V1 e incorpora:

- proximidad de los alojamientos a infraestructura ciclista OSM;
- evidencia peatonal OSM;
- proximidad a destinos turísticos OSM.

Los ocho pesos, variables de entrada y exclusiones de V2 se guardan en
`docs/tourism_sustainable_mobility_index_v2_report.json`; la metodología
vigente se centraliza en `docs/TSMAI_METODOLOGIA_VERSIONADA.md`. La pendiente está
calculada sobre una muestra de 20 rutas, no sobre cada trayecto municipal, y la
evidencia universal es escasa y documental; por ello ambas se excluyen del
índice para no inducir una precisión inexistente.

## Evidencia universal, modos sostenibles y escenarios

- `build_universal_access_evidence.py` separa evidencia positiva OSM
  (`wheelchair`, pavimento táctil y bordillos rebajados) de los cruces OSM que
  sólo son contexto peatonal. También conserva paradas GTFS con
  `wheelchair_boarding=1`. Proximidad a una etiqueta no acredita que un
  itinerario sea universalmente accesible; tampoco la ausencia de etiqueta
  demuestra una barrera.
- `validate_bicycle_routes.py` consulta geometrías reales de bicicleta en OTP.
  La recomendación resultante de `build_sustainable_route_recommendations.py`
  es una regla transparente basada en duración y disponibilidad de ruta. No
  conoce disponibilidad de bicicletas, preferencias, seguridad vial o estado
  de la infraestructura.
- `simulate_access_interventions.py` es un análisis de sensibilidad: el
  escenario de primera/última milla y el límite teórico no colocan paradas ni
  estiman coste, demanda, permisos u obras. Sirven para ordenar investigación
  posterior, no para prescribir inversiones.

Los tres módulos no usan sentimiento de usuarios. Ese componente permanece
expresamente fuera del alcance hasta disponer de reseñas con licencia, base
legal y un protocolo de anotación/evaluación.

## Planificador multimodal y sentimiento autorizado

La API incorpora `POST /routes/compare`, que resuelve en paralelo WALK,
BICYCLE, TRANSIT y CAR para un alojamiento/destino del catálogo validado o un
punto manual. La recomendación devuelve sus pesos y penalizaciones de tiempo,
emisiones estimadas, caminata y transbordos; no certifica seguridad o
accesibilidad universal. El dashboard expone el mismo flujo en la pestaña
**Planificador multimodal**.

El índice `TSMAI-v3-accommodation` puntúa cada alojamiento con sus propias
señales de proximidad y mantiene `evidence_coverage_pct`; no hereda la nota
municipal. Para activar sentimiento se requieren, en este orden:

```powershell
python scripts/extract/ingest_source.py --source-id licensed_mobility_survey --input "C:\ruta\encuesta_real.csv"
python scripts/extract/ingest_source.py --source-id licensed_mobility_survey --input "C:\ruta\encuesta_real.csv" --execute
python scripts/run_task.py validate_licensed_reviews
python scripts/run_task.py analyze_multilingual_sentiment
python scripts/run_task.py aggregate_mobility_sentiment
```

No se deben añadir reseñas de plataformas de terceros sin licencia o
consentimiento. El detalle de contratos y publicación está en
`docs/DATA_GOVERNANCE_V2.md`.

## Capas opcionales con requisitos externos

- La calidad del aire CAIB se descarga como contexto puntual con
  `python scripts/run_task.py build_air_quality_context --execute`. No convierte la estación más cercana en
  exposición de un alojamiento o ruta.
- `python scripts/run_task.py build_road_safety_context --execute` procesa microdatos DGT de 2024 como contexto
  provincial de Baleares. No es una capa de riesgo por tramo ni se usa para
  escoger rutas; hasta validar una delimitación insular completa no se etiqueta
  como resultado exclusivo de Mallorca.
- La tarea `python scripts/run_task.py build_aemet_weather_context` necesita una clave gratuita de
  AEMET en `AEMET_API_KEY` dentro de `.env`; no se debe guardar esa clave en el
  repositorio. Se ejecuta en modo informativo por defecto y sólo `--execute`
  consulta AEMET y crea snapshots versionados.
- Tras una descarga AEMET correcta, ejecutar
  `python scripts/run_task.py build_aemet_weather_context --execute` para publicar la
  capa curada de estaciones dentro de Mallorca. El dashboard la muestra sólo
  como contexto histórico y no la incorpora a TSMAI ni al routing.
- P15 exige coincidencia exacta entre la fecha de la muestra OTP y la fecha de
  observación AEMET. Comprueba el estado con
  `python scripts/run_task.py build_current_sample_aemet_route_context`; si AEMET ya
  dispone de esa fecha, publica sólo las estaciones diarias más cercanas a cada
  origen y destino con `--execute`. No interpola clima a lo largo de la ruta.
- La capa de evidencia universal se visualiza en el mapa mediante anillos para
  alojamientos con una etiqueta OSM positiva a ≤400 m o con una parada GTFS
  `wheelchair_boarding=1` a ≤800 m. Esta visualización conserva distancias y
  procedencia, pero no certifica el alojamiento, la parada ni la continuidad
  de un itinerario accesible.
- El sentimiento no se ejecuta sin un corpus autorizado. Consulta
  `docs/RESEÑAS_LICENCIADAS.md` antes de usar las tareas
  `validate_licensed_reviews` y `analyze_multilingual_sentiment`.

## P16 — publicación local PostGIS

La configuración de contenedor se conserva como trabajo futuro, pero la función
que publica las capas P7 en PostGIS no está presente en el código actual. Por
tanto, PostGIS **no es una capacidad ejecutable ni un entregable validado** de
esta versión. Los Parquet versionados y su manifiesto P7 son el contrato de
datos vigente. Antes de anunciar esta integración se debe implementar la
publicación, proteger el DSN local y añadir pruebas de conteos, geometrías,
hashes y permisos.
