# Guía de capturas para la defensa

Ejecuta primero las tareas de validación indicadas en `VALIDACION_FINAL_ENTREGA_V9.md`. Todas las capturas deben conservar visible el título del panel, la fecha de generación y, cuando exista, el filtro aplicado. No mezcles en una misma diapositiva las capas históricas con las actuales P7.

| Nº | Captura | Evidencia que debe verse | Mensaje oral recomendado |
|---:|---|---|---|
| 1 | Portada del dashboard | Título y filtros globales | El producto es una interfaz de exploración, no una caja negra. |
| 2 | Mapa P7 | Alojamientos V9, paradas, destinos y leyenda | Se analizan 1.461 alojamientos en el universo actual. |
| 3 | Filtro por nivel V9 | Prioridad de mejora seleccionada | Los 172 casos son candidatos para contraste, no prescripciones de obra. |
| 4 | Panel TRANSIT estacional | Verano, invierno y alcance temporal | La caída invernal describe el calendario consultado, no demanda observada. |
| 5 | Comparador de rutas | WALK, BICYCLE y TRANSIT, con fecha/hora | La red se usa para itinerarios; la distancia radial sólo sirve de cribado. |
| 6 | Tabla o gráfico de sensibilidad | 625 estables, 836 variables, 110 robustos | Los pesos son una decisión explícita y se someten a estrés. |
| 7 | Ficha de un alojamiento | Componentes, nivel y geometría | La prioridad es explicable componente a componente. |
| 8 | Documentación de límites | Alcance y limitaciones | Seguridad por tramo, tráfico y accesibilidad universal requieren validación externa. |

## Secuencia sugerida

1. Abre el dashboard local con el manifiesto P7 vigente.
2. Restablece filtros y toma las capturas 1 y 2.
3. Filtra `prioridad de mejora`, registra el número mostrado y toma la captura 3.
4. Selecciona un alojamiento que permita explicar la diferencia entre proximidad y ruta por red.
5. Acompaña las capturas 4 y 6 con las figuras reproducibles de `figuras_defensa/`.

## Reglas de calidad

- Exporta a 1920 × 1080 o superior y elimina datos personales, rutas locales y tokens visibles.
- Añade un pie de figura: fuente, snapshot, fecha de captura y limitación principal.
- Si un filtro modifica el total, indícalo en el título de la diapositiva.
- No uses capturas de un servidor distinto al validado ni de una versión V1–V8 como resultado final.
