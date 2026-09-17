# Motor multimodal local — OpenTripPlanner

## Finalidad

OpenTripPlanner (OTP) construye un grafo multimodal a partir de:

- `mallorca_mobility_network.osm.pbf`: red viaria y restricciones de giro de OpenStreetMap.
- `gtfs_tib_mallorca.zip`: líneas, expediciones, paradas y calendarios de TIB.

El motor se ejecuta localmente en Docker Desktop. No utiliza APIs comerciales, ni transmite los datos a un servicio externo.

## Flujo de ejecución

1. El cuaderno 08 copia los dos insumos inmutables a `data/otp/` y registra sus hashes.
2. `docker compose run --rm otp-build` crea `data/otp/graph.obj`.
3. `docker compose up -d otp-server` carga el grafo y publica la interfaz local en `http://localhost:8080`.

## Recursos y reproducibilidad

- Imagen anclada: `opentripplanner/opentripplanner:2.10.0_2026-09-01T15-06`.
- Memoria máxima Java: 2 GB; es suficiente para el PBF filtrado de Mallorca. Si Docker informa de falta de memoria, se aumentará a 4 GB de forma explícita.
- El contenedor recibe los datos exclusivamente mediante el volumen local `data/otp`.

## Calendario del GTFS

El análisis de los archivos `calendar.txt` y `calendar_dates.txt` permite conocer el rango de fechas declarado por cada servicio y sus excepciones. Las fechas mínima y máxima agregadas no demuestran, por sí solas, que no haya servicio entre dos valores: la disponibilidad efectiva se validará con consultas de ruta para fechas concretas. Las consultas del TFM deberán indicar una fecha de servicio válida y conservar la versión del GTFS utilizada.
