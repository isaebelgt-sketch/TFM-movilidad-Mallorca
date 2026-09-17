# Diccionario de datos — GTFS TIB Mallorca

Las tablas se extraen del fichero `gtfs_tib_mallorca.zip` y se guardan en `data/unified/gtfs_tib_mallorca/`. Los identificadores se mantienen como texto para no perder ceros iniciales ni alterar claves.

| Tabla | Clave / relación | Uso previsto |
|---|---|---|
| `stops.parquet` | `stop_id` | Paradas de transporte público, con geometría EPSG:4326 y etiqueta `spatial_quality`. |
| `routes.parquet` | `route_id` | Líneas comerciales y tipo de transporte. |
| `trips.parquet` | `trip_id`; referencia a `route_id` | Expediciones programadas de cada línea. |
| `stop_times.parquet` | referencia a `trip_id` y `stop_id` | Horarios y secuencia de paradas. Las horas se mantienen en formato GTFS. |
| `calendar.parquet` | `service_id` | Días ordinarios en los que opera cada servicio. |
| `calendar_dates.parquet` | `service_id` y fecha | Excepciones al calendario ordinario. |
| `agency.parquet` | `agency_id` | Operadores y datos de contacto. |

## Reglas de tratamiento

- `arrival_time` y `departure_time` no se convierten a fecha-hora porque GTFS permite horas posteriores a `24:00:00`.
- La envolvente de Mallorca solo etiqueta la plausibilidad espacial de las paradas; no elimina registros.
- Las relaciones `trips → routes` y `stop_times → trips/stops` se validan antes de persistir datos.
