# Tablas de defensa TSMAI V9

Estas tablas se derivan de los informes versionados de la entrega vigente. La línea base histórica se mantiene separada y no debe sumarse ni compararse como si fuera el mismo universo.

## Resultado principal

| Métrica | Resultado | Interpretación para la defensa |
|---|---:|---|
| Alojamientos del universo actual | 1.461 | Snapshot oficial CAIB con geometría válida. |
| Puntuación media TSMAI V9 | 0,625 | Índice normalizado y explicable, no una certificación. |
| Desviación estándar | 0,179 | Existe heterogeneidad territorial entre alojamientos. |
| Nivel favorable | 719 | Resultado relativo al modelo y pesos V9. |
| Nivel intermedio | 570 | Resultado relativo al modelo y pesos V9. |
| Prioridad de mejora | 172 | Cartera de contraste técnico, no lista automática de obras. |

## Componente TRANSIT estacional

| Campaña o agregado | Puntuación media | Alcance |
|---|---:|---|
| Verano | 0,4291 | Cuatro escenarios temporales del GTFS versionado. |
| Invierno | 0,0137 | Cuatro escenarios temporales del mismo GTFS versionado. |
| Media estacional | 0,2214 | Media simple de ambas campañas. |
| Alojamientos que empeoran | 793 | Cambio según la regla configurada. |
| Alojamientos sin cambio | 668 | Cambio según la regla configurada. |

## Pesos de referencia V9

| Familia | Componentes | Peso total |
|---|---|---:|
| Transporte público | Proximidad 12 %, servicio GTFS 8 %, TRANSIT 20 % | 40 % |
| Caminabilidad | Evidencia OSM 20 %, ruta WALK OTP 20 % | 40 % |
| Bicicleta | Evidencia OSM 10 %, ruta BICYCLE OTP 10 % | 20 % |

## Sensibilidad de ponderaciones

| Indicador | Resultado | Lectura correcta |
|---|---:|---|
| Escenarios | 5 | Cambian pesos; no se generan observaciones sintéticas. |
| Nivel estable en los 5 escenarios | 625 alojamientos | Estabilidad categórica completa. |
| Cambio de nivel en algún escenario | 836 alojamientos | Incertidumbre normativa relevante. |
| Prioridad robusta del decil superior | 110 alojamientos | En el decil superior al menos en 4 de 5 escenarios. |
| Spearman alojamientos | 0,855–0,995 | Estabilidad relativa del ranking. |
| Spearman municipios | 0,916–0,996 | Estabilidad relativa agregada. |

## Capas actuales P7

| Capa | Registros |
|---|---:|
| Alojamientos TSMAI V9 | 1.461 |
| Paradas GTFS TIB | 772 |
| Destinos OSM temáticos | 4.487 |
| Evidencias ciclistas OSM | 1.421 |

La distancia de alojamientos a parada es una medida euclídea de cribado: 885 están en 0–400 m, 267 en 400–800 m, 42 en 800–1.200 m y 267 a más de 1.200 m. No equivale a un itinerario a pie por red.
