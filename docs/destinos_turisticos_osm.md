# Destinos turísticos candidatos desde OpenStreetMap

## Justificación

La fuente oficial `centres_turistics_mallorca.geojson` contiene 51 registros, pero solo dos geometrías. Para poder evaluar rutas a destinos georreferenciados se complementa con datos OSM extraídos localmente del PBF ya versionado.

## Selección de POI

- `tourism=attraction,museum,viewpoint,zoo,aquarium,theme_park,gallery`
- `historic=*`
- `amenity=arts_centre,theatre,cinema,marketplace,exhibition_centre`

Los valores turísticos asociados a alojamiento no se incluyen en esta capa de destinos.

## Tratamiento espacial

Los nodos OSM se conservan como puntos. Las líneas y polígonos se transforman a un punto representativo interior, calculado en EPSG:25831 y devuelto a EPSG:4326. Solo los POI con `name` entran en la capa curated de destinos recomendables.

## Limitaciones

OpenStreetMap es una fuente colaborativa; ofrece cobertura práctica para generar destinos candidatos, pero no sustituye un inventario turístico oficial completo. La procedencia, filtros y hash del PBF quedan registrados en `docs/data_quality_tourism_pois_osm.json`.
