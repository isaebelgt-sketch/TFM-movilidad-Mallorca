# P2 — comparación estacional con el calendario GTFS real

## Alcance correcto

P2 mide la diferencia de accesibilidad por transporte público entre verano e
invierno declarada por el calendario del GTFS oficial de TIB. No se crean
horarios, paradas ni trayectos sintéticos y no es necesario descargar un
fichero llamado «programación de invierno».

El snapshot validado `20260912T231840Z` ya contiene ambos periodos. Para el 15
de septiembre de 2026 declara 2.865 expediciones en 78 líneas; para el 15 de
enero de 2027 declara 588 expediciones en 20 líneas. Por tanto, la comparación
se realiza con el mismo ZIP y fechas reales diferentes. El resultado representa
estacionalidad del servicio publicado, no diferencias entre actualizaciones del
proveedor.

## Ejecutar la campaña de invierno

Con el servidor OTP actual iniciado y validado, ejecuta en Anaconda Prompt:

```cmd
python scripts/run_task.py build_transit_temporal_robustness --gtfs-run-id 20260912T231840Z --analysis-id winter_2027 --scenarios-file config\transit_winter_scenarios.json --execute --resume --concurrency 4 --batch-size 25
```

Los cuatro escenarios se encuentran en
`config/transit_winter_scenarios.json`:

- Viernes 15 de enero de 2027: 08:00, 10:00 y 18:00.
- Sábado 16 de enero de 2027: 10:00.

La campaña genera 5.844 consultas OTP reales, los mismos 1.461 pares del P0 y
un resumen separado, sin sobrescribir P1.

## Comparar verano–invierno

Al terminar la campaña, ejecuta:

```cmd
python scripts/run_task.py compare_transit_seasonal_runs --baseline-summary "data\curated\transit_temporal_weekday_am_peak_weekday_midday_weekday_evening_weekend_midday_summary.parquet" --seasonal-summary "data\curated\transit_temporal_winter_2027_winter_weekday_am_peak_winter_weekday_midday_winter_weekday_evening_winter_weekend_midday_summary.parquet" --baseline-gtfs-run-id 20260912T231840Z --seasonal-gtfs-run-id 20260912T231840Z --comparison-id sep2026_vs_winter2027 --comparison-mode intra_feed_seasonal --execute
```

El comparador exige el mismo universo de alojamientos y registra el hash del
GTFS en ambas campañas. Sus deltas no se interpretan como puntualidad observada
ni como demanda turística.

## Extensión futura

Si TIB publica posteriormente un ZIP con SHA-256 distinto, se podrá evaluar el
efecto de la actualización con `--comparison-mode different_gtfs_snapshots`.
Eso será otro análisis, no sustituye P2.
