# Preparación de la red OSM para movilidad

## Propósito

El fichero raw `islas-baleares-latest.osm.pbf` se conserva inalterado. El cuaderno 07 genera dos productos derivados:

1. `data/unified/osm/mallorca_bbox.osm.pbf`: extracto geográfico de la envolvente provisional de Mallorca.
2. `data/unified/osm/mallorca_mobility_network.osm.pbf`: vías con etiqueta `highway=*` y restricciones de giro, más los nodos necesarios para conservar la topología.

La etiqueta `highway=*` en OpenStreetMap incluye carreteras, calles, caminos, senderos y vías peatonales/ciclistas cuando están cartografiados de esa forma. No supone todavía que todos los segmentos sean accesibles a pie o en bicicleta: esa clasificación se aplicará al construir perfiles de red.

## Reproducibilidad y alcance

- Coordenadas de recorte provisional: longitud 2,20–3,60; latitud 39,10–40,20 (WGS84/EPSG:4326).
- El recorte por envolvente es un paso técnico de rendimiento, no la delimitación administrativa final de Mallorca.
- Cada salida queda registrada con tamaño y hash SHA-256 en `docs/osm_network_manifest.json`.
- El proceso nunca escribe en `data/raw`.

## Papel de Docker

La preparación PBF se ejecuta mediante Osmium Tool dentro del entorno Conda, que ofrece binarios para Windows. Docker Desktop despliega OpenTripPlanner y ya integra este PBF con el GTFS para generar rutas WALK, BICYCLE y multimodales con horarios.
