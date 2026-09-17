# Interpretación de rutas multimodales

La muestra contiene 20 pares alojamiento-destino evaluados en el instante horario definido en el cuaderno 13. Se preserva el resultado bruto de OTP y se añade una clasificación analítica reproducible.

- **Transporte público disponible:** 7 rutas. Son las únicas que se usan para resumir tiempos, líneas y transbordos.
- **OTP prioriza caminar:** 4 rutas. No prueba ausencia de transporte público; el planificador considera que caminar es preferible según sus parámetros y el momento consultado.
- **Extremo sin parada en radio de búsqueda:** 5 rutas. Es un indicador de posible brecha de primera o última milla, pero debe interpretarse junto con el radio de búsqueda configurado en OTP.
- **Sin conexión en fecha/hora:** 1 ruta(s). Esta categoría se limita al horario GTFS y a la ventana temporal consultados; no se extrapola a todo el año.
- **Solo alternativa a pie:** 2 rutas. OTP resolvió el desplazamiento, pero no ofreció una alternativa con tránsito entre las opciones solicitadas.
- **Desconexión peatonal en grafo:** 1 ruta(s). Requiere revisión visual de los extremos y de la conectividad OSM antes de cualquier conclusión territorial.

## Regla de interpretación

No se debe escribir que las categorías sin alternativa de tránsito carecen de transporte público. Los resultados son condicionados por la fecha, hora, red OSM, GTFS, parámetros de búsqueda y posición representativa del POI. La conclusión defendible es que esas rutas no obtuvieron una alternativa multimodal adecuada bajo las condiciones reproducibles del experimento.
