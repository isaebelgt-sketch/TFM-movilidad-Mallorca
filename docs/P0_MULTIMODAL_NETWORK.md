# P0 — Evidencia multimodal completa

## Alcance cerrado

La prioridad P0 evalúa los 1.461 alojamientos turísticos oficiales de Mallorca
con rutas reales de OpenTripPlanner (OTP) en tres modos. La fecha y hora
experimental son **2026-09-15, 10:00**, sobre el mismo grafo construido con la
red OSM y el GTFS TIB versionados en el proyecto.

| Componente | Pares | Resultado útil | Resultado no imputado |
|---|---:|---:|---:|
| WALK a POI elegible más próximo | 1.461 | 1.454 rutas | 7 `no_route` |
| BICYCLE a POI elegible más próximo | 1.461 | 1.460 rutas | 1 `no_route` |
| TRANSIT a POI elegible entre 8 y 20 km | 1.461 | 756 rutas con tramo TRANSIT | 644 `no_transit_leg`; 61 `no_route` |

Los destinos son POI nombrados de OpenStreetMap pertenecientes a una taxonomía
explícita de turismo, patrimonio, naturaleza y ocio. La selección determinista
del POI fija el par de análisis, pero no representa una observación de demanda,
preferencia ni itinerario turístico real.

## Índice publicado

`data/curated/accommodations_tsmai_v7_complete_multimodal.parquet` contiene el
**TSMAI V7 — multimodal completo**. Es un hito histórico de la metodología;
el resultado vigente del proyecto es TSMAI V9. Sus pesos son:

| Evidencia | Peso |
|---|---:|
| Proximidad a parada TIB | 12 % |
| Evidencia de servicio GTFS TIB | 8 % |
| TRANSIT efectivo OTP | 20 % |
| Proximidad a evidencia ciclista OSM | 10 % |
| BICYCLE efectivo OTP | 10 % |
| Evidencia peatonal OSM | 20 % |
| WALK efectivo OTP | 20 % |

Las puntuaciones TRANSIT se asignan únicamente a itinerarios con tramo no
WALK: 1,0 para hasta 30 minutos; 0,8 hasta 60; 0,6 hasta 90; 0,3 hasta 120;
0 para más de 120 minutos, `no_transit_leg` o `no_route`. Se conserva el
estado original para distinguir falta de conexión de una alternativa sólo a
pie.

## Resultados reproducibles

El índice clasifica 765 alojamientos como favorables, 522 como intermedios y
174 como prioridad de mejora. Los manifiestos `latest_walk_network_access.json`,
`latest_bicycle_network_access.json`, `latest_transit_network_access.json` y
`latest_tsmai_v7.json` registran entradas, hashes, fecha/hora, reglas y
salidas.

## Límites

P0 no certifica seguridad vial, continuidad física, pendiente, iluminación,
frecuencia observada, puntualidad, ocupación, precio ni accesibilidad universal.
La ausencia de una etiqueta OSM no demuestra ausencia de infraestructura. Estos
aspectos se mantienen fuera del índice hasta disponer de una fuente con la
resolución y licencia adecuadas o de una auditoría de campo.
