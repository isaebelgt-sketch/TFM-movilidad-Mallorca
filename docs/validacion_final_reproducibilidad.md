# Validación final y reproducibilidad

**Estado:** superado.  
**Generado:** 2026-09-04T01:10:22.487402+00:00

## Indicadores comprobados

| Indicador | Valor |
|---|---:|
| Alojamientos con coordenadas plausibles | 1463.0 |
| Cobertura de alojamientos a ≤800 m (%) | 78.88 |
| Destinos turísticos nombrados | 1423.0 |
| Cobertura de destinos a ≤800 m (%) | 65.5 |
| Pares OD multimodales analizados | 20.0 |
| Casos prioritarios robustos | 5.0 |
| Pares coche-autobús comparables | 6.0 |
| CO₂eq evitado estimado (kg) | 2.844 |
| Reducción estimada (%) | 69.81 |

## Casos robustos

- OD16: audit_pedestrian_network (índice 0.825)
- OD18: first_last_mile_assessment (índice 0.825)
- OD13: first_last_mile_assessment (índice 0.739)
- OD15: walking_quality_preservation (índice 0.610)
- OD19: first_last_mile_assessment (índice 0.592)

## Límites de interpretación

- La accesibilidad inicial usa distancia euclídea a la parada GTFS más cercana.
- La muestra multimodal contiene 20 pares y una única fecha/hora del GTFS.
- Las emisiones son un contrafactual por viajero; no son emisiones observadas ni marginales.
- Las recomendaciones requieren validación de campo y análisis de viabilidad.
