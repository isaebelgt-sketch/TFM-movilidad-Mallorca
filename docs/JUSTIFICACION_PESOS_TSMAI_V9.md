# Justificación de pesos y sensibilidad — TSMAI V9

## Criterio de diseño

Los pesos de TSMAI V9 son elecciones analíticas transparentes, no coeficientes
aprendidos ni preferencias observadas. Se definen para equilibrar tres familias
de movilidad sostenible y para no sustituir una evidencia de red por una mera
proximidad geométrica.

| Familia | Componentes | Peso total | Razonamiento |
|---|---|---:|---|
| Transporte público | Proximidad a parada (12 %), servicio GTFS (8 %) y TRANSIT estacional OTP (20 %) | 40 % | Separa acceso físico, oferta programada y posibilidad efectiva de viaje. |
| Caminabilidad | Evidencia peatonal OSM (20 %) y ruta WALK OTP (20 %) | 40 % | Equilibra la señal documental del entorno con el itinerario por red. |
| Bicicleta | Evidencia ciclista OSM (10 %) y ruta BICYCLE OTP (10 %) | 20 % | Reconoce la alternativa activa sin asumir que una ruta OTP equivale a carril segregado o bicicleta disponible. |

Dentro de cada familia, la evidencia documental y el comportamiento de red se
mantienen diferenciados. Por ejemplo, una ruta BICYCLE factible no demuestra
infraestructura ciclista de calidad, y una etiqueta OSM no garantiza que el
itinerario sea continuo. Esta separación reduce la doble interpretación de una
misma señal, aunque no elimina las limitaciones de cobertura de OSM.

El peso TRANSIT de 20 % hace que la disponibilidad temporal tenga el mismo peso
que cada dimensión peatonal, pero no domine el índice completo. El resto del
transporte público (20 %) conserva acceso y oferta GTFS, de modo que la ausencia
de una ruta en una ventana concreta no borra la evidencia espacial disponible.

## Escenarios de sensibilidad

La robustez se evalúa con cinco escenarios deterministas sobre los mismos 1.461
alojamientos y siete componentes. No se generan observaciones sintéticas.

| Escenario | Cambio principal |
|---|---|
| Equilibrado | Pesos de referencia V9: 40 % transporte público, 40 % caminabilidad, 20 % bicicleta. |
| Foco transporte público estacional | TRANSIT aumenta a 36 %; las dimensiones activas disminuyen de forma compensatoria. |
| Foco movilidad activa | Caminabilidad y bicicleta aumentan; TRANSIT baja a 8 %. |
| Foco caminabilidad | WALK por red y evidencia peatonal suman 55 %. |
| Equilibrado no TRANSIT | Reduce TRANSIT a 5 % y aumenta las componentes activas. |

El informe reproducible `tsmai_v9_sensitivity_report.json` muestra que 625
alojamientos mantienen nivel en los cinco escenarios, 110 pertenecen al decil
superior en al menos cuatro y las correlaciones de ranking de alojamientos son
0,855–0,995. Los municipios presentan correlaciones 0,916–0,996. Por tanto,
las prioridades robustas se pueden defender como candidatas consistentes frente
a cambios razonables de preferencias analíticas.

## Interpretación académica correcta

La sensibilidad prueba la estabilidad relativa ante cambios explícitos de pesos;
no demuestra que los pesos sean verdaderos, que los usuarios prefieran una
alternativa o que una mejora cause cambio modal. La memoria debe presentar el
escenario equilibrado como decisión de diseño y los escenarios alternativos como
análisis de incertidumbre normativa. Una calibración empírica futura requeriría
encuestas de preferencias, observación de viajes u otros datos con cobertura y
licencia adecuadas.
