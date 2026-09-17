# Accesibilidad de destinos turísticos

La capa tourism_destinations_transport_access_baseline.parquet añade a cada POI turístico la parada GTFS de embarque más próxima y su distancia euclídea en metros.

- stop_id y stop_name: parada GTFS más próxima.
- wheelchair_boarding: atributo GTFS original de la parada.
- distance_to_nearest_stop_euclidean_m: distancia en línea recta, en EPSG:25831.
- destination_access_band_euclidean: banda 0–400 m, 400–800 m, 800–1.200 m o más de 1.200 m.

La métrica sirve para preseleccionar destinos con potencial de acceso en transporte público. Las rutas completas se calcularán con OpenTripPlanner.
