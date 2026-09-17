# Diccionario de datos — Capa unified de alojamientos

| Campo | Tipo | Descripción |
|---|---|---|
| `accommodation_id` | texto | Identificador oficial `Signatura` del registro de origen. Clave única. |
| `commercial_name` | texto | Denominación comercial declarada. |
| `group_raw`, `subgroup_raw`, `category_raw` | texto | Clasificación original del registro turístico. |
| `activity_start_date_raw` | texto | Fecha original, conservada para trazabilidad. |
| `activity_start_date` | fecha | Fecha convertida con formato día/mes/año; valores no convertibles pasan a nulo. |
| `status_raw` | texto | Estado administrativo original. No se infiere actividad ni vigencia a partir de él. |
| `municipality_raw`, `locality_raw`, `address_raw` | texto | Localización textual original. |
| `places`, `surface_m2`, `units` | numérico | Capacidad, superficie y unidades, convertidas a número cuando es posible. |
| `city_hotel_raw`, `operator_raw` | texto | Atributos originales del establecimiento. |
| `geometry` | Point / nulo | Geometría original en EPSG:4326; nunca se modifica en esta capa. |
| `geometry_quality` | categoría | `valid_point_in_study_bbox`, `missing_geometry`, `outside_study_bbox` o `unsupported_geometry_type`. |
| `is_spatial_candidate` | booleano | Verdadero solo cuando la geometría es un punto dentro de la envolvente provisional del estudio. |
| `source_file` | texto | Nombre del fichero raw que generó el registro. |
| `ingested_at_utc` | fecha-hora | Momento UTC de ejecución de la transformación. |

## Artefactos resultantes

- `data/unified/accommodations_unified.parquet`: los 1.877 registros estandarizados, incluidos los no espaciales.
- `data/unified/accommodations_spatial_candidates.parquet`: subconjunto apto para análisis espacial inicial.
- `docs/data_quality_accommodations.json`: métricas reproducibles de calidad y trazabilidad.

La envolvente empleada es un filtro provisional de plausibilidad de coordenadas, no un contorno exacto de Mallorca. Se reemplazará por un límite administrativo antes de calcular indicadores territoriales.
