# Muestra estratificada de rutas por red

## Diseño

La muestra contiene 80 alojamientos: 20 seleccionados aleatoriamente en cada una de las cuatro bandas de proximidad euclídea. Se fija la semilla `2026`, por lo que la selección es exactamente reproducible.

## Unidad de análisis

Cada observación calcula una ruta exclusivamente peatonal con OpenTripPlanner desde el alojamiento hasta la parada GTFS más próxima. La consulta se realiza con PBF OSM y GTFS versionados localmente.

## Salvaguardas

- Las respuestas se guardan como checkpoint cada 10 rutas para poder reanudar la ejecución.
- Se preservan fallos de ruta con su detalle; no se eliminan silenciosamente.
- Se exige al menos un 90 % de rutas exitosas. Un resultado inferior requerirá revisar conectividad OSM y enlaces de parada.

## Alcance

La muestra permite estimar la diferencia sistemática entre la distancia euclídea y la distancia de red. No pretende sustituir el cálculo exhaustivo ni producir inferencia estadística municipal sin ampliar el diseño muestral.
