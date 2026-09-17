# Alcance extendido y límites de evidencia

Este documento distingue lo que el prototipo calcula con datos observados de lo que únicamente puede usar como contexto o requiere una fuente adicional. La distinción evita convertir una ausencia de dato en una conclusión sobre el territorio.

| Área del desafío | Estado | Evidencia disponible | Uso en el producto |
| --- | --- | --- | --- |
| Alojamiento, destinos y transporte público | Completada | Registro turístico, POI de OpenStreetMap, GTFS y rutas OTP | Métricas, mapas, rutas y TSMAI V9 individual. |
| Caminabilidad y bicicleta | Completada con contexto OSM | Rutas OTP y etiquetas OSM próximas a las geometrías | Recomendación modal y perfil de infraestructura; no certifica seguridad vial. |
| Accesibilidad universal | Completada como evidencia parcial | `wheelchair`, pavimento táctil y bordillos rebajados de OSM; atributos GTFS | Señales positivas y ausencia de evidencia; no certificación de accesibilidad. |
| Emisiones evitadas | Completada para la muestra comparable | Distancias OTP, factores documentados y escenarios de demanda | Comparación coche-autobús y escenarios, no inventario de emisiones real. |
| TSMAI V9 y sensibilidad | Completada | Siete componentes por alojamiento, rutas OTP y cinco escenarios de pesos | Resultado individual vigente y comprobación de robustez relativa a los pesos. |
| Clustering y prioridades territoriales | Histórico exploratorio | Indicadores municipales y K-Means de versiones anteriores | Perfilado y casos de referencia; no alimentan TSMAI V9. |
| Calidad del aire | Completada como contexto territorial | Estaciones oficiales CAIB | Mapa y proximidad a estación; no se interpreta como exposición individual o por ruta. |
| Estacionalidad de la oferta | Completada como contexto | Serie oficial Ibestat de plazas turísticas | Oferta reglada por municipio; no equivale a ocupación ni demanda observada. |
| Siniestralidad vial | Completada como contexto provincial | Microdatos DGT 2024 para Baleares | Indicador agregado para contextualizar; no se usa para recomendar rutas ni se presenta como Mallorca si no hay isla identificada. |
| Meteorología | Preparada, pendiente de credencial | Conector AEMET OpenData | Se ejecuta únicamente con una clave personal de AEMET. |
| Sentimiento de usuarios | Preparada, pendiente de corpus lícito | Pipeline BERT multilingüe y validador de licencia | Se ejecuta sólo con textos licenciados o consentidos; no se hace scraping de plataformas. |
| Tráfico por segmento, calidad física y auditoría universal | Pendiente de fuente o campo | No hay capa abierta homogénea incorporada | Requiere aforos/sensores con licencia, inventario municipal o validación de campo. |

## Regla de interpretación

Una etiqueta OSM ausente significa **"sin evidencia registrada en la fuente"**, no **"infraestructura inexistente"**. Las prioridades generadas son candidatas a revisión técnica o de campo, nunca órdenes automáticas de intervención.

La puntuación vigente es TSMAI V9 por alojamiento. Emisiones, perfiles de
pendiente, calidad del aire, siniestralidad, meteorología, oferta turística y
sentimiento se muestran como contexto o muestras independientes: no se agregan
al índice ni prueban por sí solos la calidad de una ruta. Las versiones V1–V8,
clústeres y casos OD se mantienen para trazabilidad, no como resultado vigente.

## Reproducibilidad

Los scripts de adquisición y transformación producen sus tablas en `data/raw`, `data/unified` y `data/curated`; los informes JSON documentan conteos, fechas y límites. La operación completa está descrita en `OPERACION_PRODUCTO.md`.
