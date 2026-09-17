# Protocolo de validación de campo y revisión experta TSMAI V9

## Propósito

Contrastar si las prioridades generadas por TSMAI V9 se corresponden con condiciones observables de primera y última milla. El protocolo evalúa rutas y entornos; no certifica accesibilidad universal ni seguridad vial.

## Diseño de muestra

Seleccionar 36 alojamientos: 12 de prioridad de mejora, 12 intermedios y 12 favorables. En cada nivel, estratificar por municipio y por banda de distancia euclídea a parada (0–400, 400–800, 800–1.200 y más de 1.200 m). Añadir hasta 6 casos de reserva si no es posible acceder de forma segura.

Para cada alojamiento se audita el itinerario peatonal hacia la parada o destino recomendado por el análisis. Se realizan dos franjas horarias, una diurna y una nocturna cuando la seguridad operativa lo permita. Registrar fecha, hora, persona observadora, condiciones meteorológicas y versión de datos usada.

## Ficha de observación

La plantilla `data/templates/ficha_validacion_campo_v9.csv` contiene los campos mínimos. El equipo debe registrar observaciones separadas de interpretaciones. Fotografías o coordenadas sensibles requieren autorización y una política de custodia específica.

| Dimensión | Escala | Criterio observable |
|---|---|---|
| Continuidad peatonal | 0–2 | 0: interrupción crítica; 1: discontinuidad o desvío relevante; 2: continuo. |
| Cruces | 0–2 | 0: cruce inseguro/no resuelto; 1: cruce con fricción; 2: cruce claro y legible. |
| Pendiente y esfuerzo | 0–2 | 0: barrera probable; 1: esfuerzo moderado; 2: sin barrera apreciable. |
| Iluminación y orientación | 0–2 | 0: insuficiente; 1: parcial; 2: adecuada. |
| Accesibilidad física observable | 0–2 | 0: barrera clara; 1: evidencia ambigua; 2: paso observable sin barrera clara. |
| Conexión ciclista | 0–2 | 0: no apta o discontinua; 1: compartida o ambigua; 2: conexión funcional observable. |
| Servicio programado | Sí/No/No verificable | Contrastar con GTFS y señalización; no inferir puntualidad. |

## Revisión experta

Dos personas con perfil de movilidad accesible o ingeniería de transporte revisarán una submuestra común de al menos 12 itinerarios. Antes de la visita recibirán una guía común y una sesión de calibración de 30 minutos. Se calcula el acuerdo por dimensión (porcentaje de acuerdo y, si la escala lo permite, kappa ponderado). Las discrepancias se resuelven conservando ambos registros y documentando el criterio final.

## Criterios de análisis

- Comparar el nivel V9 con la puntuación de campo sin convertir la segunda en una nueva versión del índice.
- Marcar como `revisión prioritaria` cualquier caso V9 favorable con una barrera crítica observada, y cualquier caso de prioridad de mejora sin barrera observable para revisión de datos o fecha.
- Informar por separado la no accesibilidad, la ausencia de observación y la evidencia ambigua.
- Publicar únicamente agregados y rutas anonimizadas si hay información sensible.

## Seguridad y ética

No auditar calzadas o entornos peligrosos sin evaluación previa. No recoger identificadores de huéspedes ni opiniones personales sin consentimiento. El protocolo no sustituye una auditoría reglada de accesibilidad ni una evaluación de riesgos laborales.
