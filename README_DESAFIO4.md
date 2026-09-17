# Desafío 4: Generador de Mapas de Accesibilidad y Movilidad Sostenible

Este proyecto responde al **Desafío 4** mediante un prototipo reproducible de análisis territorial y enrutamiento multimodal para destinos turísticos, utilizando Mallorca como laboratorio de pruebas.

La entrega actual integra datos geoespaciales, alojamiento turístico, puntos de interés, transporte público, movilidad activa, rutas OTP y un índice TSMAI por alojamiento.

> **Nota sobre esta copia de presentación:** los componentes de IA generativa o preentrenada del proyecto de desarrollo completo (análisis de sentimiento con BERT y generación de narrativas con un LLM) se han retirado deliberadamente de este paquete para dejar solo código propio. Las secciones 3 y 4 de más abajo describen el diseño original con esos componentes; en esta copia no están presentes.

## Propuesta de Valor
La solución permite diagnosticar la conectividad sostenible entre alojamientos y puntos de interés turísticos. El valor principal está en combinar datos abiertos, rutas reales de red y un índice explicable para localizar brechas de transporte, primera/última milla y movilidad activa.

El sistema no certifica seguridad vial, accesibilidad universal ni cambio modal observado. Sus resultados son evidencia de cribado para revisión técnica y planificación.

## Resolución de los Requisitos del Desafío

### 1. Integración de Datos Geoespaciales e Infraestructura
- **Implementado:** Registro de alojamientos turísticos, red OpenStreetMap, POIs turísticos, GTFS TIB, evidencia ciclista/peatonal OSM, capas de contexto y pendiente MDP05 en muestras documentadas.
- **Resultado:** Capas curadas y dashboard con 1.461 alojamientos y más de 4.000 destinos OSM en la capa territorial actual.

### 2. Rutas Multimodales Reales (Walk, Bicycle, Transit)
- El sistema no usa simples líneas rectas (distancia euclídea). Integra **OpenTripPlanner (OTP)** como motor enrutador de fondo.
- El **Planificador Multimodal** compara WALK, BICYCLE, TRANSIT y CAR para pares seleccionados, calculando duración, caminata, transbordos y emisiones estimadas bajo factores declarados.

### 3. Sentimiento de Usuarios (no incluido en esta copia)
- **Diseño original:** pipeline BERT multilingüe para reseñas con licencia o consentimiento explícito, documentado en `docs/RESEÑAS_LICENCIADAS.md` y `docs/FUENTES_Y_LICENCIAS.md`.
- **Esta copia:** el script que invoca el modelo (`analyze_multilingual_sentiment`) se ha retirado; no se publican resultados de sentimiento.
- **Límite (si se reincorpora):** el sentimiento general no debe llamarse "seguridad percibida" sin anotación manual, protocolo de evaluación y validación temática.

### 4. Narrativas Explicativas (no incluidas en esta copia)
- **Diseño original:** generación de textos explicativos a partir de reglas y evidencias de ruta, con una alternativa opcional vía LLM (Gemini) si había API key configurada.
- **Esta copia:** el generador (`generate_ai_route_narratives`) se ha retirado; las recomendaciones se explican solo con las reglas deterministas ya integradas en el índice de prioridad.

### 5. Tourism Sustainable Mobility & Accessibility Index (TSMAI)
- **Implementado:** TSMAI V9 por alojamiento, con rutas OTP, evidencia OSM, GTFS TIB y comparación estacional dentro del feed disponible.
- **Límite:** No incorpora sentimiento, seguridad percibida, tráfico por tramo, accesibilidad universal certificada ni demanda turística observada.

## Tecnologías Empleadas
- **Backend & Data:** Python, Pandas, GeoPandas, PyArrow (GeoParquet).
- **Routing & Maps:** OpenTripPlanner (OTP), OpenStreetMap, GTFS.
- **Frontend:** Streamlit, Folium, Plotly.
- **IA / Analítica:** Clustering (DBSCAN, K-Means) y scoring explicable. El pipeline BERT y las narrativas LLM del diseño original no están en esta copia (ver nota al inicio).

## Impacto Esperado
1. **Gestores de Destino (Ayuntamientos):** Identificar "islas" de alojamientos desconectados del transporte público para trazar nuevas líneas de bus o crear corredores verdes peatonales.
2. **Alojamientos y cadenas hoteleras:** Comparar la conectividad sostenible de sus ubicaciones con criterios transparentes.
3. **Turistas:** Consultar alternativas de movilidad sostenible, entendiendo que las recomendaciones no sustituyen validación de seguridad, accesibilidad o disponibilidad real.
