# Decisiones de diseño

| Fecha | Decisión | Motivo | Consecuencia |
|---|---|---|---|
| 2026-09-03 | Alcance inicial: Mallorca | Datos turísticos y GTFS oficiales disponibles; complejidad manejable | España completa queda como diseño escalable y trabajo futuro |
| 2026-09-03 | Ruta multimodal: OpenTripPlanner | OSMnx y NetworkX no modelan horarios, esperas y transbordos GTFS | Se incorporará Docker/Podman a partir de la semana 6 |
| 2026-09-03 | Capas Raw, Unified y Curated en Parquet | Trazabilidad, reproducibilidad y separación de responsabilidades | Los datos originales nunca se editan |
| 2026-09-03 | Índice IATS explicable | Las decisiones deben poder justificarse ante TUI y gestores | Se publicarán fórmula, pesos y análisis de sensibilidad |
| 2026-09-11 | TSMAI v9 con análisis de sensibilidad | La cobertura de parada no basta para describir movilidad sostenible | Se incorporan ocho componentes explicables y cuatro escenarios de pesos; la robustez no se interpreta como causalidad |
| 2026-09-11 | Evidencia universal conservadora | Un cruce OSM no certifica accesibilidad | Se separan señales fuertes (`wheelchair`, táctil, bordillo rebajado) de contexto peatonal y se exige validación de campo |
| 2026-09-11 | Rutas OTP visibles en el dashboard | El resultado del modelo debe ser verificable por el usuario | Se muestran geometrías reales WALK, BICYCLE y TRANSIT, además de instrucciones peatonales |
| 2026-09-11 | Calidad del aire, oferta y DGT como contexto | Las capas no tienen resolución suficiente para influir en una ruta individual | Se visualizan o documentan sin incorporarlas al routing ni al TSMAI |
| 2026-09-11 | No recopilar reseñas sin licencia | La disponibilidad pública no equivale a derecho de reutilización | El sentimiento queda preparado para un corpus CC0, CC-BY o consentido |
