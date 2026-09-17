# Validación final de entrega — TSMAI V9

Fecha de validación: 17-09-2026. Esta hoja registra la comprobación de la
cadena final ya construida; no sustituye los informes de cada fuente ni implica
que se hayan vuelto a consultar los 1.461 pares de routing.

## Cadena validada

| Control | Resultado | Evidencia |
|---|---|---|
| Puntos de entrada publicados | 43/43 tareas importan sin ejecutarse | `python scripts/run_task.py --check` |
| Índice final | Correcto: 1.461 alojamientos, media 0,625 | `docs/tsmai_v9_seasonal_transit_report.json` |
| Sensibilidad | Correcta: cinco escenarios sobre los mismos siete componentes | `docs/tsmai_v9_sensitivity_report.json` |
| Capas del dashboard P7 | Correctas: 1.461 alojamientos, 772 paradas, 4.487 destinos y 1.421 evidencias ciclistas | `docs/dashboard_current_layers_report.json` |
| Interfaz Streamlit | Contrato de datos verificado | `python scripts/run_task.py validate_streamlit_app` |
| Pruebas automatizadas | Suite completa superada | `python -m pytest -q` |

## Regeneración controlada aplicada

Se ejecutaron las tres fases derivadas que no consultan OTP ni descargan datos
externos:

```powershell
python scripts/run_task.py build_current_tsmai_v9_seasonal_transit
python scripts/run_task.py analyze_tsmai_v9_sensitivity
python scripts/run_task.py build_current_dashboard_layers
```

El índice se reconstruyó desde V8, las dos campañas TRANSIT ya versionadas y
la comparación estacional. La sensibilidad sólo modifica pesos; la publicación
P7 sólo transforma artefactos existentes. Por tanto, esta validación verifica
la coherencia de la entrega sin presentar una nueva consulta como evidencia
observada.

## Controles que requieren una ejecución distinta

- El rebarrido WALK, BICYCLE o TRANSIT con OTP requiere fecha, hora, servicio
  activo y `--execute`; no se incluyó porque modificaría el experimento de
  referencia.
- AEMET, calidad del aire y sentimiento requieren respectivamente credencial,
  actualización remota o corpus autorizado. No son condición para TSMAI V9.
- Seguridad, continuidad física y accesibilidad universal requieren auditoría
  de campo o una fuente de resolución adecuada.

## Criterio para la defensa

El resultado vigente es TSMAI V9 por alojamiento. Las cifras de V1–V8, casos
OD, emisiones y clústeres sirven para explicar la evolución del prototipo, no
como una segunda estimación del resultado final.
