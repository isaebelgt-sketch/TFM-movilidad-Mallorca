# Desafío 4: Generador de Mapas de Accesibilidad y Movilidad Sostenible

Este proyecto responde al **Desafío 4** mediante un prototipo reproducible de análisis territorial y enrutamiento multimodal para destinos turísticos, utilizando Mallorca como laboratorio de pruebas.

La entrega actual integra datos geoespaciales, alojamiento turístico, puntos de interés, transporte público, movilidad activa, rutas OTP y un índice TSMAI por alojamiento. Las partes de sentimiento de usuarios y generación LLM quedan preparadas técnicamente, pero no se presentan como resultados finales si no existe corpus licenciado o API configurada.

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

### 3. Sentimiento de Usuarios (Preparado, No Ejecutado)
- **Preparado:** Pipeline BERT multilingüe para reseñas con licencia o consentimiento explícito.
- **Estado actual:** No se publican resultados de sentimiento porque no hay corpus lícito incorporado.
- **Límite:** El sentimiento general no debe llamarse "seguridad percibida" sin anotación manual, protocolo de evaluación y validación temática.

### 4. Narrativas Explicativas
- **Implementado:** Generación de textos explicativos a partir de reglas y evidencias de ruta.
- **Estado actual:** Si no hay API key configurada, el sistema lo etiqueta como **mock heurístico**, no como LLM real.

### 5. Tourism Sustainable Mobility & Accessibility Index (TSMAI)
- **Implementado:** TSMAI V9 por alojamiento, con rutas OTP, evidencia OSM, GTFS TIB y comparación estacional dentro del feed disponible.
- **Límite:** No incorpora sentimiento, seguridad percibida, tráfico por tramo, accesibilidad universal certificada ni demanda turística observada.

## Tecnologías Empleadas
- **Backend & Data:** Python, Pandas, GeoPandas, PyArrow (GeoParquet).
- **Routing & Maps:** OpenTripPlanner (OTP), OpenStreetMap, GTFS.
- **Frontend:** Streamlit, Folium, Plotly.
- **IA / Analítica:** Clustering, scoring explicable, pipeline BERT opcional y narrativas heurísticas/LLM condicionadas a configuración.

## Impacto Esperado
1. **Gestores de Destino (Ayuntamientos):** Identificar "islas" de alojamientos desconectados del transporte público para trazar nuevas líneas de bus o crear corredores verdes peatonales.
2. **Alojamientos y cadenas hoteleras:** Comparar la conectividad sostenible de sus ubicaciones con criterios transparentes.
3. **Turistas:** Consultar alternativas de movilidad sostenible, entendiendo que las recomendaciones no sustituyen validación de seguridad, accesibilidad o disponibilidad real.
