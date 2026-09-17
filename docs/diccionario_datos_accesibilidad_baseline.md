# Diccionario de datos — Línea base de acceso a transporte

## Propósito

La capa cuantifica una aproximación inicial de proximidad entre alojamientos turísticos y paradas GTFS. No evalúa rutas peatonales, pendientes, barreras, frecuencias ni tiempos de espera.

## Capa `accommodations_transport_access_baseline.parquet`

Además de los campos heredados de `accommodations_spatial_candidates.parquet`, incorpora:

| Campo | Tipo | Descripción |
|---|---|---|
| `stop_id` | texto | Identificador GTFS de la parada de embarque más próxima. |
| `stop_name` | texto | Nombre GTFS de la parada asociada. |
| `wheelchair_boarding` | texto | Atributo GTFS original sobre accesibilidad de la parada; no debe interpretarse como accesibilidad garantizada de la ruta. |
| `distance_to_nearest_stop_euclidean_m` | decimal | Distancia en línea recta, calculada en ETRS89 / UTM 31N (EPSG:25831), en metros. |
| `walk_access_band_euclidean` | categoría | Banda de proximidad: 0–400 m, 400–800 m, 800–1.200 m o más de 1.200 m. |

## Capa `transport_access_by_municipality.parquet`

Resume número de alojamientos, distancia media y mediana a parada, y porcentaje dentro de 800 m por municipio.

## Limitación esencial

Las bandas no equivalen todavía a distancia o tiempo caminando: ignoran red viaria, pasos peatonales, pendientes y obstáculos. En el TFM se presentarán como una línea base que será reemplazada o comparada con las métricas de red derivadas de OpenStreetMap.
