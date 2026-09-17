# Construcción trazable de rutas multimodales

OpenTripPlanner se construye con una red OSM de Mallorca y un ZIP GTFS TIB ya
validados. Cada construcción usa una carpeta propia para impedir que un
`graph.obj` previo se confunda con los datos actuales.

## Preparar entradas

```powershell
python scripts/prepare_otp_inputs.py
```

El comando crea `data/otp/builds/otp_<run_osm>_<run_gtfs>/` e imprime su ruta.
No descarga datos ni elimina el grafo anterior.

## Construir y servir

En PowerShell, sustituye la ruta por la que imprimió el paso anterior:

```powershell
$env:OTP_DATA_DIR = (Resolve-Path "data\otp\builds\otp_<run_osm>_<run_gtfs>").Path
docker compose -f docker/otp/docker-compose.yml run --rm otp-build
docker compose -f docker/otp/docker-compose.yml up -d otp-server
```

En Anaconda Prompt o `cmd.exe`, cuyo prompt termina en `>`, utiliza esta
variante equivalente (no uses la sintaxis `$env:`):

```bat
set "OTP_DATA_DIR=%CD%\data\otp\builds\otp_<run_osm>_<run_gtfs>"
docker compose -f docker/otp/docker-compose.yml run --rm otp-build
docker compose -f docker/otp/docker-compose.yml up -d otp-server
```

El servicio queda disponible en `http://localhost:8080/otp/gtfs/v1`. La ruta
depende del feed GTFS, la fecha, la hora y la red OSM cargada; no implica que la
infraestructura sea segura o universalmente accesible.

La configuración conserva servicios desde un año antes hasta tres años después
de la fecha de construcción del grafo. Documenta siempre la fecha y hora de
cualquier consulta para que los resultados sean reproducibles.

## Validación en vivo

Con `otp-server` iniciado y la misma variable `OTP_DATA_DIR` definida, ejecuta:

```powershell
python scripts/validate_otp_service.py
```

El validador usa alojamientos reales con parada TIB próxima, prueba una ruta
WALK local y una consulta TRANSIT de mayor separación, y registra el endpoint,
fecha, hora, entradas y respuestas en `docs/otp_service_validation_report.json`.
