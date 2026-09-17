# Validación inicial de rutas peatonales con OTP

## Objetivo

Validar que las capas generadas (alojamientos, paradas GTFS, PBF OSM y `graph.obj`) funcionan conjuntamente para generar itinerarios a pie por la red real.

## Diseño de prueba

Se selecciona un alojamiento por cada banda de accesibilidad euclídea. La selección es determinista: el menor `accommodation_id` de cada banda. Para cada caso se solicita a OTP una ruta exclusivamente peatonal hacia la parada GTFS más cercana, a fecha y hora explícitas.

## Métricas

- Distancia euclídea previa a la parada (m).
- Distancia por red OSM calculada por OTP (m).
- Duración estimada de la ruta peatonal (min).
- Cociente `distancia_red / distancia_euclídea`.

## Interpretación

Las cuatro rutas demuestran la viabilidad técnica y permiten verificar la diferencia entre proximidad geométrica y distancia caminable. No representan una muestra estadística de Mallorca ni sustituyen el cálculo masivo posterior para los 1.463 alojamientos.
