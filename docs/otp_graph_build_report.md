# Informe de construcción del grafo OpenTripPlanner

## Ejecución

- Motor: OpenTripPlanner `2.10.0-SNAPSHOT` (imagen anclada `2.10.0_2026-09-01T15-06`).
- Tiempo total de construcción: 54,884 s.
- Grafo persistido: `data/otp/graph.obj`.
- Tamaño registrado durante la escritura: 30,9 MB.

## Grafo resultante

| Métrica | Valor |
|---|---:|
| Vértices del grafo | 162.998 |
| Aristas del grafo | 417.112 |
| Paradas de transporte integradas | 772 |
| Patrones de servicio | 311 |
| Transferencias peatonales directas creadas | 1.835 |
| Paradas con transferencias conectadas | 699 |

## Calidad y limitaciones detectadas por OTP

La construcción terminó correctamente. Las advertencias siguientes no invalidan el grafo, pero deben quedar documentadas y condicionan la interpretación de rutas concretas:

- 73 paradas no quedaron enlazadas para transferencias peatonales.
- 2 islas de paradas se podaron durante el análisis de conectividad.
- Se detectaron 287 restricciones de giro OSM con incidencias de calidad.
- OTP detectó componentes aislados de las redes a pie, bicicleta y automóvil; aplicó su poda y etiquetado de conectividad.

Estas incidencias reflejan las limitaciones de la cartografía colaborativa OSM y/o la posición de paradas en el GTFS respecto de la red viaria. En la fase de resultados se seleccionarán rutas de muestra y se verificará visualmente que sus orígenes, destinos y accesos a parada sean plausibles.

## Implicación metodológica

Las consultas posteriores usarán este motor para medir rutas y tiempos de red. Los resultados conservarán la versión del PBF, GTFS, configuración y grafo empleada; no se extrapolarán a zonas donde las advertencias de conectividad impidan obtener una ruta válida.
