# Metodología versionada del TSMAI

Este documento fija la interpretación académica del **Tourism Sustainable
Mobility & Accessibility Index (TSMAI)**. La versión vigente es **TSMAI V9 por
alojamiento**. Las versiones V1–V8 se conservan para poder reproducir la
evolución metodológica, pero no deben presentarse como resultados finales ni
compararse directamente como si midieran exactamente lo mismo.

## Unidad, universo y lectura correcta

El resultado vigente analiza **1.461 alojamientos turísticos oficiales con
geometría válida** de la capa P7 (snapshot CAIB `20260912T224211Z`). Los
1.463 alojamientos y 1.423 destinos OSM citados en la línea base pertenecen a
un snapshot y una taxonomía históricos distintos. La reconciliación completa
está en [REPRODUCIBILIDAD_OPERATIVA.md](REPRODUCIBILIDAD_OPERATIVA.md).

Cada puntuación es un indicador compuesto entre 0 y 1 de evidencia de
accesibilidad sostenible disponible para un alojamiento. No es una medición de
viajes realizados, calidad experimentada, demanda turística, cumplimiento
normativo ni causalidad de una inversión.

## Línea de versiones

| Versión | Unidad y cambio metodológico principal | Estado |
|---|---|---|
| V1 | Cribado municipal (51 municipios): cobertura y brechas GTFS, proximidad a parada, éxito de routing exploratorio y disponibilidad TRANSIT. | Histórico |
| V2 | Cribado municipal: añade proximidad a evidencia ciclista y peatonal OSM y a destinos turísticos OSM; incluye análisis de sensibilidad de pesos. | Histórico |
| V3 | Índice individual por alojamiento con proximidad euclídea a transporte, ciclovía, evidencia peatonal y destino, más evidencia documental de accesibilidad. | Histórico |
| V4 | Índice individual reproducible de 1.461 alojamientos; consolida cinco señales de proximidad y servicio de las capas actuales. | Histórico |
| V5 | Sustituye la proximidad al destino por una ruta WALK real de OTP. | Histórico |
| V6 | Añade rutas BICYCLE reales de OTP y separa evidencia ciclista de capacidad de enrutamiento. | Histórico |
| V7 / P0 | Añade un itinerario TRANSIT real hacia un POI OSM elegible situado entre 8 y 20 km. | Histórico |
| V8 / P1 | Sustituye el TRANSIT puntual de V7 por la media de cuatro escenarios de verano del GTFS. | Histórico |
| **V9 / P2** | Sustituye el componente TRANSIT de V8 por la media simple de campañas reales de verano e invierno (cuatro escenarios cada una) del mismo GTFS versionado. | **Vigente** |

La cronología no expresa nueve mediciones independientes: documenta cómo se
reemplazaron aproximaciones geométricas por evidencia de red y se amplió la
robustez temporal del transporte público.

## Fórmula vigente: TSMAI V9

TSMAI V9 utiliza siete componentes, todos normalizados de 0 a 1. La puntuación
es la media ponderada de los componentes disponibles; la cobertura de evidencia
se publica por alojamiento para evitar ocultar datos ausentes.

| Componente | Peso | Evidencia usada |
|---|---:|---|
| Proximidad a parada TIB | 12 % | Distancia a la parada GTFS más cercana. |
| Servicio GTFS TIB | 8 % | Evidencia de servicio del GTFS versionado. |
| TRANSIT estacional por red | 20 % | OTP: media de verano e invierno. |
| Proximidad a evidencia ciclista | 10 % | Etiquetas OSM de infraestructura ciclista. |
| BICYCLE por red | 10 % | Ruta BICYCLE de OTP al POI elegible. |
| Proximidad a evidencia peatonal | 20 % | Etiquetas OSM peatonales. |
| WALK por red | 20 % | Ruta WALK de OTP al POI elegible. |

Para el componente TRANSIT se emplea el snapshot GTFS
`20260912T231840Z`. Cada campaña incluye cuatro escenarios: laborable a las
08:00, 10:00 y 18:00, y sábado a las 10:00. Verano corresponde al 15/19 de
septiembre de 2026 e invierno al 15/16 de enero de 2027. Un itinerario válido
recibe 1,0 hasta 60 minutos; 0,70 entre más de 60 y 90; 0,40 entre más de 90 y
120; y 0 por encima de 120 minutos o ante `no_transit_leg`/`no_route`. No se
imputan rutas ausentes.

El POI de WALK/BICYCLE es el elegible más próximo por geometría. El de TRANSIT
se selecciona entre 8 y 20 km. Estas reglas fijan pares de análisis
reproducibles, pero no representan una preferencia ni una demanda observada.

## Resultado vigente y límites

El artefacto vigente es
`data/curated/accommodations_tsmai_v9_seasonal_transit.parquet`, generado el
13-09-2026. Resume 719 alojamientos favorables, 570 intermedios y 172 de
prioridad de mejora; su puntuación media es 0,625. El informe verificable es
`docs/tsmai_v9_seasonal_transit_report.json`.

La media simple de verano e invierno **no** es un promedio anual y no pondera
demanda, ocupación, tarifas, frecuencias observadas ni puntualidad. Tampoco
certifica seguridad vial, continuidad de la red, estado del pavimento,
iluminación, pendiente de cada itinerario o accesibilidad universal. Las
etiquetas OSM y `wheelchair_boarding` de GTFS son evidencia documental; su
ausencia cartográfica no prueba una barrera física.

Pendiente, calidad del aire, siniestralidad, emisiones, reseñas y sentimiento
pueden servir como contexto o muestras exploratorias, pero no forman parte de
TSMAI V9. Deben mantenerse separados hasta contar con cobertura, licencia y
validación compatibles con un indicador por alojamiento.

## Trazabilidad y regeneración

Los informes de cada etapa son `docs/tourism_sustainable_mobility_index_v1_report.json`,
`docs/tourism_sustainable_mobility_index_v2_report.json`,
`docs/tsmai_v4_current_report.json` hasta
`docs/tsmai_v9_seasonal_transit_report.json`. V3 publica además su informe al
regenerarse desde el artefacto correspondiente.

La entrada de ejecución vigente es `python scripts/run_task.py`; consulta
`python scripts/run_task.py --list` y la guía de reproducibilidad antes de
regenerar una campaña. No se deben ejecutar literalmente los nombres
históricos de scripts aislados que aparecen en documentación heredada.
