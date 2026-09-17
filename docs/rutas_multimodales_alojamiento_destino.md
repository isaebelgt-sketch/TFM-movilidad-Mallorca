# Rutas multimodales alojamiento → destino

- **Fecha y hora de consulta:** 2026-09-03 12:00 (hora local de Mallorca).
- **Motor:** OpenTripPlanner local; red OSM y GTFS TIB integrados en `graph.obj`.
- **Muestra:** 20 pares, seleccionados con semilla 2026; cinco alojamientos por cada una de las cuatro bandas de acceso euclídeo a parada.
- **Destino:** POI OSM nombrado de categoría `tourism` o `historic` más cercano situado entre 2 y 20 km, calculados en EPSG:25831.
- **Comparación:** una ruta WALK-only frente a la alternativa más rápida con al menos un tramo de transporte público entre las cinco alternativas solicitadas a OTP.

## Interpretación

Los resultados describen la disponibilidad y coste temporal del horario GTFS cargado en un instante concreto. Una ausencia de itinerario no demuestra que no exista servicio en general: puede deberse al horario, la conectividad de la red o los límites del grafo. Los indicadores de emisiones no se calculan aún; requerirán hipótesis explícitas y una fuente oficial para los factores de emisión.

## Resultados de ejecución

- Rutas a pie resueltas: 19 de 20.
- Rutas con transporte público resueltas: 7 de 20.
