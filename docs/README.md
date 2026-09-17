# Guía de documentación del proyecto

Esta carpeta conserva tanto documentación vigente como informes históricos de cada ejecución. Los documentos de resultados de una fase no se reescriben cuando se incorpora una extensión posterior: así se preserva la trazabilidad de la evidencia original.

## Documentos vigentes

| Documento | Propósito |
| --- | --- |
| `Memoria_TFM_Movilidad_Sostenible_Mallorca_final_V9.docx` | Memoria académica final integrada con el resultado vigente TSMAI V9. |
| `OPERACION_PRODUCTO.md` | Arranque, regeneración y requisitos del prototipo. |
| `dashboard_streamlit.md` | Capacidades, rutas y límites de la interfaz. |
| `ALCANCE_EXTENDIDO.md` | Estado de cada componente y límites de evidencia. |
| `FUENTES_Y_LICENCIAS.md` | Proveedor, licencia, atribución y uso de fuentes externas. |
| `RESEÑAS_LICENCIADAS.md` | Requisitos legales y técnicos para sentimiento. |
| `TSMAI_METODOLOGIA_VERSIONADA.md` | Universo, versiones V1–V9, fórmula y límites del índice vigente. |
| `JUSTIFICACION_PESOS_TSMAI_V9.md` | Razonamiento de ponderaciones y lectura de sensibilidad. |
| `MEMORIA_RESULTADOS_V9.md` | Texto actualizado de resultados, discusión y conclusiones para la memoria. |
| `VALIDACION_FINAL_ENTREGA_V9.md` | Evidencia de la regeneración y validación final de la entrega. |
| `TABLAS_DEFENSA_V9.md` | Tablas listas para las diapositivas y la exposición oral. |
| `GUIA_CAPTURAS_DEFENSA.md` | Secuencia y criterios para capturas reproducibles del dashboard. |
| `PROTOCOLO_VALIDACION_CAMPO_V9.md` | Diseño de validación de campo y revisión experta posterior. |
| `borrador_resultados_y_discusion.md` | Texto base de resultados y discusión para la memoria. |
| `DECISIONES.md` | Decisiones de diseño y sus consecuencias. |

## Informes históricos y técnicos

- Los diccionarios `diccionario_datos_*.md` describen el esquema de cada capa estable.
- Los documentos `resultados_*`, `validacion_*`, `muestra_rutas_red.md` y `rutas_multimodales_alojamiento_destino.md` preservan el diseño y los resultados de las ejecuciones que los produjeron.
- Los informes JSON en `docs/` son artefactos de ejecución: incluyen conteos, fecha de generación, método, fuente y limitaciones.

## Regla de interpretación

Para el estado actual del sistema, usar la memoria final V9, `ALCANCE_EXTENDIDO.md` y los informes JSON más recientes. Las capas de calidad del aire, DGT, pendiente, infraestructura activa y accesibilidad universal son complementos con límites explícitos y no reemplazan las métricas de routing OTP.
