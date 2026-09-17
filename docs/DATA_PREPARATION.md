# Preparación de datos reales

> Los comandos vigentes usan `python scripts/run_task.py <tarea>`. Las formas
> históricas `python scripts/<nombre>.py` y `python scripts/etl_*.py` de este
> documento no deben ejecutarse literalmente; consulta
> [REPRODUCIBILIDAD_OPERATIVA.md](REPRODUCIBILIDAD_OPERATIVA.md).

Los ficheros de `data/raw` son snapshots inmutables. Las transformaciones sólo
leen de esa zona y publican nuevas capas en `data/unified` o `data/curated`.

## Registro oficial de alojamientos

```powershell
python scripts/run_task.py prepare_official_accommodations
```

El proceso valida el SHA-256 del snapshot descargado, exige identificador único
y geometría Point dentro de la envolvente de Mallorca, estandariza los campos y
publica:

- `data/unified/accommodations_official_normalized.geojson`
- `docs/accommodations_preparation_report.json`

No sustituye los campos ausentes, no geocodifica direcciones y no modifica el
GeoJSON original. Los rechazos se registran por motivo en el informe.

## Red de movilidad

La red OSM requiere `osmium` (incluido en el entorno conda definido por
`environment.yml`). Genera primero el recorte reproducible desde el snapshot:

```powershell
python scripts/run_task.py prepare_osm_mobility_network
```

El proceso no descarga nada: verifica el SHA-256 del PBF original, recorta la
envolvente de Mallorca y publica una red con hash en
`data/unified/osm/latest_mallorca_network.json`. Después, con GeoPandas y
Osmium disponibles, construye las capas de evidencia activa y la proximidad de
los alojamientos oficiales:

```powershell
python scripts/run_task.py build_active_mobility_layers
```

El proceso publica capas versionadas de evidencia ciclista y peatonal, más la
tabla de proximidad de alojamientos. La ausencia de etiquetas OSM no se
interpreta como ausencia de infraestructura.

## Transporte público TIB (GTFS)

Descarga el ZIP GTFS desde el portal oficial de datos abiertos de TIB. No lo
descomprimas ni lo renombres antes de importarlo:

```powershell
python scripts/extract/ingest_source.py --source-id tib_gtfs_supply --input "C:\ruta\ctm-mallorca-es.zip" --execute
python scripts/run_task.py prepare_tib_gtfs
```

El segundo comando verifica el hash del ZIP, exige las tablas GTFS obligatorias
(`stops`, `routes`, `trips`, `stop_times`), valida paradas y publica una capa
de paradas versionada en `data/unified/gtfs` junto a un informe de calidad.

Para integrar esa oferta de transporte con los alojamientos oficiales:

```powershell
python scripts/run_task.py build_tib_public_transport_access
```

El resultado identifica la parada TIB más próxima, la banda de distancia, el
número de paradas cercanas y los registros de servicio GTFS disponibles. No
presenta esos valores como tiempo de viaje ni frecuencia diaria.

Para calcular tiempos e itinerarios reales sobre red, continúa con la
construcción OTP documentada en `docs/OTP_ROUTING.md`.

## Destinos turísticos y naturales OSM

Con la red OSM preparada, publica POI turísticos y naturales nombrados desde el
snapshot actual:

```powershell
python scripts/run_task.py build_osm_tourism_destinations
```

Se excluyen las etiquetas OSM de alojamiento y los POI sin nombre. Los
polígonos se convierten en puntos representativos sólo para análisis espacial;
no se interpretan como accesos físicos.

## Muestra de rutas multimodales OTP

Con el servidor OTP activo, genera 12 pares reales: tres bandas de acceso TIB
por cuatro tipos de destino (cultural, naturaleza, costa y ocio).

```powershell
python scripts/run_task.py build_multimodal_route_sample --date 2026-09-15 --time 10:00
```

Se consultan los modos WALK, BICYCLE, TRANSIT y CAR. El resultado almacena
duración, distancia, caminata, transbordos, estimación de emisiones y un ranking
multiobjetivo explicable; no representa demanda turística observada.

## Índice individual actualizado

Para construir el TSMAI v9 por alojamiento con las capas actuales:

```powershell
python scripts/run_task.py build_current_tsmai_v9_seasonal_transit
```

El índice pondera proximidad a paradas TIB, evidencia de servicio, proximidad a
evidencia ciclista y peatonal OSM, y proximidad a destinos actuales. Conserva
los datos ausentes como ausencia de evidencia y no los presenta como barreras
físicas verificadas.
