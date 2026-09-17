# P1 — Robustez temporal del transporte público

P1 repite los mismos 1.461 pares TRANSIT de P0, con un destino OSM elegible
entre 8 y 20 km, en cuatro escenarios cubiertos por el GTFS TIB versionado:
martes 15/09/2026 a las 08:00, 10:00 y 18:00; sábado 19/09/2026 a las 10:00.

| Escenario | Itinerarios con TRANSIT | Sin tramo TRANSIT | Sin ruta |
|---|---:|---:|---:|
| Laborable, punta de mañana | 723 | 641 | 97 |
| Laborable, media mañana | 756 | 644 | 61 |
| Laborable, tarde | 776 | 639 | 46 |
| Sábado, media mañana | 742 | 652 | 67 |

De los 1.461 alojamientos, 747 tienen servicio TRANSIT en al menos tres de los
cuatro escenarios, 76 tienen servicio inestable y 638 no tienen un tramo
TRANSIT para el par seleccionado en ninguno de los escenarios.

El TSMAI V8 sustituye el componente TRANSIT puntual de V7 por una media de las
cuatro puntuaciones temporales: 1,0 hasta 60 minutos; 0,70 hasta 90; 0,40 hasta
120; 0 para más de 120 minutos, `no_transit_leg` o `no_route`. Esto no convierte
el resultado en una medida anual ni de puntualidad, ocupación, tarifas o demanda
observada. La fuente y los resultados permanecen versionados en
`latest_transit_temporal_robustness.json` y `latest_tsmai_v8.json`.

V8 se conserva como hito histórico: P2 construye el resultado vigente, TSMAI
V9, al combinar esta campaña de verano con una campaña equivalente de invierno.
