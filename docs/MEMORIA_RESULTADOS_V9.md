# Resultados, discusión y conclusiones — TSMAI V9

> Texto base para integrar en la memoria. Debe adaptarse a la plantilla,
> extensión y sistema de citas del máster. Las fuentes, versiones y límites se
> documentan en `REPRODUCIBILIDAD_OPERATIVA.md` y
> `TSMAI_METODOLOGIA_VERSIONADA.md`.

## Resultados

### Universo y capas analíticas

El resultado vigente analiza 1.461 alojamientos turísticos oficiales con
geometría válida del snapshot CAIB `20260912T224211Z`. El mapa territorial P7
asocia este universo con 772 paradas de embarque del GTFS TIB, 4.487 destinos
OSM temáticos y 1.421 elementos de evidencia ciclista OSM. Estas cifras no se
deben mezclar con la línea base histórica de 1.463 alojamientos y 1.423
destinos OSM nombrados, ya que proceden de snapshots y reglas de selección
distintos.

La capa P7 permite explorar la proximidad euclídea a parada: 885 alojamientos
se sitúan en la banda 0–400 m, 267 entre 400–800 m, 42 entre 800–1.200 m y 267
a más de 1.200 m. Esta medida sólo se usa como cribado territorial; no sustituye
un itinerario a pie por red.

### Índice TSMAI V9

TSMAI V9 integra siete componentes de transporte público, movilidad ciclista y
movilidad peatonal. El componente TRANSIT es la media simple de cuatro
escenarios de verano y cuatro de invierno del mismo GTFS versionado. La
puntuación media obtenida es 0,625 (desviación estándar 0,179): 719 alojamientos
quedan en nivel favorable, 570 en nivel intermedio y 172 en prioridad de mejora.

La comparación estacional muestra una media TRANSIT de 0,4291 en verano y
0,0137 en invierno; 793 alojamientos empeoran y 668 permanecen sin cambio con
la regla configurada. El resultado describe la disponibilidad programada en las
fechas seleccionadas dentro de un mismo feed GTFS, no un promedio anual ni la
puntualidad, ocupación o demanda observada.

### Sensibilidad de las ponderaciones

Se recalculó el índice con cinco escenarios de pesos y los mismos componentes
reales. En 625 alojamientos el nivel se mantuvo en los cinco escenarios; 836
cambiaron de nivel en alguno de ellos. De los 147 alojamientos que aproximadamente
forman cada decil, 110 aparecen en el decil superior al menos en cuatro de los
cinco escenarios y pueden tratarse como candidatos de prioridad robusta para
revisión posterior.

Las correlaciones de Spearman entre los rankings de alojamientos oscilan entre
0,855 y 0,995; para municipios, entre 0,916 y 0,996. Estas cifras muestran una
estabilidad relativa razonable del orden agregado, pero no validan causalmente
el índice ni convierten una prioridad en una decisión automática de inversión.

## Discusión

El principal valor del prototipo es reemplazar una lectura exclusivamente radial
por una evidencia multimodal y trazable: la proximidad a una parada se combina
con servicio GTFS, rutas OTP WALK/BICYCLE y disponibilidad TRANSIT en escenarios
temporales. Separar la evidencia OSM de la capacidad de enrutamiento evita
afirmar que una etiqueta cartográfica certifica una infraestructura segura o
continua.

La marcada reducción del componente TRANSIT en los escenarios invernales es un
resultado útil para plantear preguntas de planificación, especialmente sobre
primera y última milla. Sin embargo, no permite afirmar que los turistas dejan
de viajar, que un servicio sea puntual o que una intervención reduzca emisiones:
para ello se necesitarían aforos, ocupación, comportamiento modal y evaluación
antes/después.

Los 172 alojamientos de prioridad de mejora deben entenderse como una cartera
para contraste técnico. Una revisión posterior puede diferenciar si la causa es
la distancia a parada, el calendario del servicio, la conectividad de la red o
una limitación cartográfica. El dashboard y la API permiten inspeccionar esta
evidencia, pero no prescriben obras.

## Limitaciones

- Los POI OSM son elementos representativos y no garantizan entrada física,
  horario de apertura ni demanda turística.
- OSM y GTFS son snapshots versionados; cambian con el tiempo y la ausencia de
  etiqueta no demuestra ausencia de infraestructura.
- Las campañas TRANSIT no son un promedio anual y no incluyen puntualidad,
  tarifa, ocupación o preferencia modal.
- El índice no incorpora seguridad vial por tramo, tráfico, continuidad,
  iluminación, pendiente de cada itinerario ni accesibilidad universal
  certificada.
- Calidad del aire, AEMET, siniestralidad, plazas turísticas, emisiones y
  sentimiento son contexto o muestras separadas; no alimentan TSMAI V9.

## Conclusión

El TFM entrega un prototipo reproducible de análisis de movilidad turística que
combina datos abiertos, GIS, GTFS y routing OTP en un índice individual
explicable. Su uso adecuado es priorizar investigación y validación de campo,
no certificar accesibilidad ni sustituir la decisión pública. La trazabilidad de
fuentes, pesos, escenarios y resultados permite actualizar el análisis cuando
se disponga de nuevas publicaciones GTFS, cartografía OSM o datos de demanda.

## Figuras y tablas recomendadas

1. Arquitectura `raw → unified → curated → OTP → TSMAI V9 → dashboard`.
2. Mapa P7 con alojamientos, paradas, destinos y niveles TSMAI V9.
3. Distribución de puntuaciones y niveles TSMAI V9.
4. Comparación de la puntuación TRANSIT de verano, invierno y estacional.
5. Tabla de escenarios de sensibilidad y correlaciones de ranking.
6. Tabla de límites, fuentes y evidencia que no se incorpora al índice.
