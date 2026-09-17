# Resultados preliminares — Acceso a transporte público

## Cobertura de los alojamientos turísticos georreferenciados

La línea base evalúa 1.463 alojamientos turísticos con coordenadas plausibles en Mallorca. La métrica es la distancia euclídea a la parada GTFS de embarque más cercana, calculada en EPSG:25831.

| Banda de proximidad | Alojamientos | Porcentaje |
|---|---:|---:|
| 0–400 m | 884 | 60,42 % |
| 400–800 m | 270 | 18,46 % |
| 800–1.200 m | 42 | 2,87 % |
| Más de 1.200 m | 267 | 18,25 % |

En total, 1.154 alojamientos (78,88 %) se sitúan a 800 m o menos de la parada más cercana. Los 267 registros situados a más de 1.200 m constituyen candidatos iniciales a brecha de accesibilidad.

## Lectura territorial inicial

Los menores porcentajes de cobertura a 800 m aparecen, entre otros, en Vilafranca de Bonany, Escorca, Santa Maria del Camí, Campanet, Binissalem, Lloseta, Búger, Campos, Montuïri y Maria de la Salut. Esta clasificación debe interpretarse conjuntamente con el número de alojamientos de cada municipio: porcentajes basados en una o dos observaciones no tienen la misma robustez que los de Campos, que cuenta con 25 alojamientos y una cobertura del 4 %.

## Limitación que debe acompañar a toda visualización

Los resultados no representan todavía un itinerario caminable ni un tiempo de viaje. La distancia en línea recta no considera calles, aceras, cruces, pendientes, barreras, frecuencia de servicio o tiempos de espera. La siguiente fase calculará métricas de red con OpenStreetMap y comparará ambas aproximaciones.
