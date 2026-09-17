# Extracción reproducible de datos reales

> Para validaciones y transformaciones utiliza
> [REPRODUCIBILIDAD_OPERATIVA.md](REPRODUCIBILIDAD_OPERATIVA.md). El extractor
> `scripts/extract/ingest_source.py` sí mantiene su interfaz propia.

## Regla previa

Primero se valida la fuente:

```powershell
python scripts/run_task.py validate_source_registry
```

Los extractores se ejecutan en modo simulación por defecto: informan de la
operación y no escriben datos. Sólo `--execute` autoriza un snapshot en
`data/raw/<source_id>/<timestamp>/`. Cada snapshot contiene su `manifest.json`
con hash SHA-256, licencia, atribución, URL, tamaño, fecha y modo de adquisición.

## Fuentes automatizadas aprobadas

Revisar la operación antes de descargar:

```powershell
python scripts/extract/ingest_source.py --source-id mallorca_tourist_accommodations
python scripts/extract/ingest_source.py --source-id osm_mallorca_network
python scripts/extract/ingest_source.py --source-id ibestat_tourism_offer
```

Ejecutar sólo después de revisar licencia y conectividad:

```powershell
python scripts/extract/ingest_source.py --source-id mallorca_tourist_accommodations --execute
python scripts/extract/ingest_source.py --source-id osm_mallorca_network --execute
python scripts/extract/ingest_source.py --source-id ibestat_tourism_offer --execute
```

## GTFS TIB: importación manual trazable

El catálogo NAP/TIB puede requerir autenticación. Descarga el ZIP desde el
proveedor oficial, sin renombrar ni modificar el fichero. Después ejecútalo así:

```powershell
python scripts/extract/ingest_source.py --source-id tib_gtfs_supply --input C:\ruta\gtfs_tib.zip --execute
```

No copies el archivo manualmente a `data/raw`: el extractor debe crear el
snapshot y su manifiesto.

## Fuentes con requisito previo

Antes de ejecutar estas fuentes, comprueba su requisito registrado:

- AEMET: la fuente está aprobada, pero el extractor sólo ejecuta consultas si
  `AEMET_API_KEY` está en el archivo local `.env`. La ejecución crea snapshots
  raw con manifiesto y nunca registra la clave:

```powershell
python scripts/run_task.py build_aemet_weather_context --start 2026-09-12 --end 2026-09-12
python scripts/run_task.py build_aemet_weather_context --start 2026-09-12 --end 2026-09-12 --execute
```

- Mallorca Accesible: licencia o permiso escrito de reutilización.
- Encuesta: consentimiento, minimización de datos y exportación anónima.
