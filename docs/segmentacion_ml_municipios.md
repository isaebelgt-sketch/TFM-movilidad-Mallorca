# Segmentación ML de municipios

## Objetivo

Agrupar los 51 municipios con alojamientos turísticos geolocalizados en perfiles de accesibilidad y capacidad turística. El algoritmo K-Means es no supervisado: no predice demanda de movilidad ni etiqueta municipios como buenos o malos.

## Variables

- Número de alojamientos, transformado con log(1+x).
- Número de plazas turísticas, transformado con log(1+x).
- Mediana de distancia euclídea a la parada GTFS más próxima.
- Porcentaje de alojamientos con parada a 800 m o menos.
- Porcentaje de alojamientos a más de 1.200 m.

Las cinco variables se estandarizan antes de aplicar K-Means. Se comparan de 2 a 5 grupos mediante silhouette y se selecciona K=3.

## Limitaciones

Los clusters describen similitud relativa en estas variables, no causalidad ni calidad absoluta de transporte. El número reducido de municipios y la dependencia de la distancia euclídea obligan a interpretar los perfiles junto con los resultados de rutas OTP y no de forma aislada.
