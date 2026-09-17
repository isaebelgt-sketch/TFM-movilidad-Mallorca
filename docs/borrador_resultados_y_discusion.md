# Borrador — Resultados y discusión

> Documento de trabajo para la memoria. Los valores proceden de las capas `curated` y de la validación final reproducible. Debe adaptarse al estilo de citación, extensión y normativa del máster antes de incorporarlo al TFM.

## 7. Resultados

### 7.1. Calidad y cobertura de los datos

El inventario inicial de alojamientos turísticos contenía 1.877 registros. Tras el control de geometrías, se identificaron 1.463 alojamientos con puntos válidos y plausibles dentro del ámbito de estudio de Mallorca. Estos constituyen la población analizada en las métricas espaciales posteriores. Los registros sin geometría o fuera del ámbito se conservaron documentados en la capa *unified*, pero no se utilizaron para calcular accesibilidad; esta decisión evita asignar una localización no verificable a un establecimiento.

El conjunto GTFS se sometió a controles de integridad referencial entre paradas, rutas, viajes y horarios. No se detectaron identificadores duplicados ni referencias rotas. Para la visualización y los cálculos de acceso se emplearon 772 paradas de embarque. Por otra parte, se extrajeron 2.507 POI turísticos desde OpenStreetMap y se seleccionaron 1.423 destinos con nombre, evitando presentar elementos sin denominación como destinos turísticos comparables.

### 7.2. Accesibilidad preliminar de los alojamientos al transporte público

La línea base calcula la distancia euclídea entre cada alojamiento y la parada GTFS de embarque más próxima. El 78,88 % de los 1.463 alojamientos se encuentra a 800 metros o menos de una parada. La distribución por bandas fue la siguiente:

| Banda de distancia | Alojamientos | Porcentaje |
|---|---:|---:|
| 0–400 m | 884 | 60,42 % |
| 400–800 m | 270 | 18,46 % |
| 800–1.200 m | 42 | 2,87 % |
| Más de 1.200 m | 267 | 18,25 % |

Este resultado indica que la proximidad espacial a una parada es relativamente elevada en el conjunto de alojamientos georreferenciados, pero también revela una bolsa de 267 establecimientos con una brecha preliminar superior a 1.200 metros. La medida no equivale a distancia caminable ni a tiempo de acceso, por lo que se utiliza como indicador de cribado espacial y no como evidencia directa de calidad peatonal.

### 7.3. Validación de la distancia por red peatonal

Para contrastar el indicador euclídeo, se configuró OpenTripPlanner sobre datos OSM y GTFS locales. Una validación inicial de cuatro rutas, una por banda, obtuvo solución peatonal en los cuatro casos. La distancia por red fue siempre superior a la euclídea: los cocientes oscilaron entre 1,305 y 2,161.

La muestra estratificada de 80 rutas peatonales confirmó el patrón. En la banda de brecha superior a 1.200 metros, la distancia media por red alcanzó 5.644,11 m frente a 2.908,88 m de distancia euclídea y una mediana de 47,50 minutos. Así, la aproximación euclídea tiende a infravalorar de forma relevante el esfuerzo de acceso, especialmente en contextos de menor conectividad territorial.

### 7.4. Accesibilidad de destinos turísticos

La cobertura de los destinos turísticos fue inferior a la de los alojamientos: el 65,50 % de los 1.423 destinos nombrados quedó a 800 metros o menos de una parada. La diferencia de 13,38 puntos porcentuales respecto a la cobertura de los alojamientos sugiere que la accesibilidad al transporte debe evaluarse en ambos extremos del viaje turístico, no únicamente en el punto de alojamiento.

Por categoría, el patrimonio histórico concentró el mayor número de destinos con brecha superior a 1.200 metros (234), seguido de los destinos turísticos etiquetados como `tourism` en OSM (121). Este hallazgo identifica ámbitos prioritarios para examinar conexiones de última milla y condiciones de acceso peatonal.

### 7.5. Resultados de la muestra multimodal

Se evaluaron 20 pares origen-destino mediante OTP en una fecha y franja horaria concreta del GTFS. En siete casos (35 %) se obtuvo una alternativa con transporte público; cuatro casos (20 %) fueron resueltos preferentemente a pie por el motor; cinco (25 %) no tenían una parada dentro del radio de búsqueda en al menos un extremo; un caso no presentó conexión planificada en la ventana temporal; dos solo devolvieron alternativas peatonales y uno no obtuvo conexión peatonal directa en el grafo.

Estos resultados no deben interpretarse como ausencia permanente de servicio. Expresan el resultado del enrutamiento bajo una configuración, una fecha, una hora y una cobertura cartográfica determinadas. Sin embargo, permiten distinguir causas operativas y espaciales: disponibilidad de línea, primera o última milla, preferencia peatonal, calendario o conectividad de red.

En los siete itinerarios con transporte público, la mediana de tiempo ahorrado frente a caminar fue de 16,72 minutos. Todas las alternativas encontradas presentaron una única etapa de autobús y cero transbordos. La distancia caminada asociada a la alternativa multimodal tuvo una mediana de 1.950,42 m, lo que muestra que disponer de línea no elimina necesariamente la carga de acceso a pie.

### 7.6. Priorización y recomendaciones trazables

Se construyó un índice de prioridad que combina brecha de acceso en origen, brecha en destino, restricción observada por el enrutamiento y carga peatonal multimodal. El análisis de sensibilidad contrastó cuatro escenarios de pesos. Cinco pares se mantuvieron en el *top 5* de al menos tres escenarios y se clasificaron como prioridades robustas:

| Caso | Alojamiento | Destino | Índice | Recomendación de revisión |
|---|---|---|---:|---|
| OD16 | SA BOLEDA | Son Real | 0,825 | Auditar conectividad peatonal |
| OD18 | INDICO ROCK-HOTEL MALLORCA | Convair CV-990 EC-BZO | 0,825 | Evaluar primera/última milla |
| OD13 | L’HERMITAGE | Torre de sa Cova | 0,739 | Evaluar primera/última milla |
| OD15 | Salino Port | sa Falconera | 0,610 | Preservar calidad peatonal |
| OD19 | SHERATON MALLORCA ARABELLA GOLF HOTEL | Plaza de Toros Son Puigdorfila Nou | 0,592 | Evaluar primera/última milla |

Las recomendaciones no equivalen a decisiones automáticas de inversión. Constituyen propuestas de revisión que conservan la evidencia de origen: la causa devuelta por OTP, las brechas de accesibilidad y la estabilidad del caso ante cambios de pesos.

### 7.7. Segmentación municipal exploratoria

El algoritmo K-Means agrupó los 51 municipios según volumen turístico, cobertura a 800 m, proporción de brechas y distancia mediana a parada. La solución de tres perfiles obtuvo el mayor valor *silhouette* entre las alternativas evaluadas (0,502).

El perfil C1 reúne 16 municipios con alta intensidad turística y cobertura media del 85,80 %. El perfil C2 agrupa 24 municipios de menor escala, con cobertura media del 77,90 %. El perfil C3 concentra 11 municipios con una cobertura media del 12,79 %, una brecha media superior a 1.200 m del 85,70 % y una distancia mediana de 2.127,68 m. Esta segmentación es descriptiva y exploratoria: no identifica causas ni determina por sí misma dónde construir infraestructura.

### 7.8. Estimación ambiental en la muestra con alternativa de autobús

Se compararon las rutas OTP en coche y en autobús para los siete casos con alternativa de tránsito. Seis pares pudieron compararse; OD10 se excluyó porque OTP no localizó el destino en modo coche. Con los factores de emisión adoptados, la alternativa de autobús evitó de forma estimada 2,844 kg de CO₂eq para el conjunto de los seis desplazamientos y representó una reducción del 69,81 % frente al contrafactual de realizar esos viajes individualmente en coche.

La estimación se interpreta como un contrafactual por viajero, no como una medición observada, una evaluación de ciclo de vida ni una estimación de emisiones marginales del servicio. La geometría del caso OD09, que mostró la mayor diferencia, se validó visualmente a partir de las geometrías de ruta devueltas por OTP.

### 7.9. Movilidad activa, pendiente y accesibilidad universal documental

Las 20 observaciones multimodales disponen de una consulta BICYCLE en OTP. Aplicando reglas explícitas de duración, competitividad frente al transporte público y contexto OSM próximo a la geometría, se clasificaron 12 casos como **Bicicleta**, 6 como **Bicicleta: revisar confort** y 2 como **Transporte público**. Esta clasificación no acredita seguridad vial, disponibilidad de bicicleta, segregación, iluminación o estado del firme.

Se calcularon perfiles de pendiente para los 20 casos priorizados mediante la geometría WALK de OTP y el MDP05 del IGN/CNIG; 19 devolvieron valores válidos. La pendiente complementa la lectura de una ruta, pero no mide aceras, cruces, pavimento, continuidad ni accesibilidad universal.

La evidencia de accesibilidad universal se interpretó de forma conservadora. Se separaron 1.626 elementos OSM de evidencia fuerte (`wheelchair`, pavimento táctil o bordillo rebajado) de 6.952 cruces que solo aportan contexto peatonal. Hay 821 alojamientos a 400 m o menos de alguna evidencia fuerte y 2 paradas GTFS con `wheelchair_boarding=1`. Estos campos no constituyen certificación de un itinerario accesible; la falta de etiqueta tampoco demuestra una barrera.

### 7.10. Índice TSMAI v9 y contextos institucionales

El TSMAI v9 incorpora cobertura GTFS, éxito de enrutamiento, proximidad a infraestructura ciclista y peatonal OSM y proximidad a destinos turísticos. Su sensibilidad se contrastó en cuatro escenarios de pesos; 8 municipios permanecieron entre los diez primeros en al menos tres escenarios. Este resultado expresa estabilidad relativa del orden, no causalidad ni una evaluación administrativa definitiva.

El prototipo añade 22 estaciones oficiales CAIB de calidad del aire y una serie oficial de plazas turísticas regladas de Ibestat disponible para 15 municipios. Se incorporaron también microdatos DGT de 2024 como contexto provincial de Baleares. Ninguna de estas capas se usa para inferir exposición individual, ocupación turística, riesgo por tramo o recomendación automática de ruta.

## 8. Discusión

Los resultados respaldan la conveniencia de evaluar la movilidad turística como un sistema origen-destino. Aunque la proximidad de los alojamientos a paradas es elevada en términos generales, los destinos presentan menor cobertura y el análisis por red muestra que la distancia euclídea oculta barreras y rodeos reales. Por ello, una estrategia basada solo en añadir paradas o en medir radios rectos resultaría incompleta.

La combinación de OSM, GTFS y OTP permite diferenciar problemas de infraestructura peatonal, ausencia de parada cercana y restricciones temporales de servicio. Esta diferenciación es útil para no recomendar la misma intervención en todos los casos: un resultado sin parada cercana requiere revisar primera o última milla; un resultado sin conexión en una hora específica requiere examinar calendario y frecuencia; y un fallo de conexión peatonal exige primero validar la cartografía y el terreno.

La muestra multimodal y el cálculo de emisiones sugieren que, cuando existe una alternativa de autobús funcional, el potencial de reducción frente al coche individual es relevante. La infraestructura activa, la pendiente y los contextos institucionales enriquecen el diagnóstico, pero no permiten estimar exposición, seguridad por tramo ni cambio modal observado. Para generalizar a todos los viajes turísticos de Mallorca serían necesarios datos de demanda, ocupación, estacionalidad, preferencias modales y observación de viajes reales.

## 9. Limitaciones que deben conservarse en la memoria

- La línea base usa distancia euclídea; solo las rutas OTP representan una red caminable.
- Los datos OSM y GTFS corresponden a una instantánea y pueden cambiar.
- La muestra multimodal contiene 20 pares y una fecha/hora de consulta; no describe todo el año.
- Los POI turísticos OSM no constituyen un inventario administrativo exhaustivo.
- K-Means y el índice de prioridad son herramientas de apoyo descriptivo, no modelos causales.
- Las emisiones son una aproximación contrafactual por viajero con factores de emisión explícitos.
- Las etiquetas OSM de infraestructura activa y accesibilidad universal son evidencia documental, no certificación de seguridad o accesibilidad física.
- La estación CAIB más próxima no mide la exposición ambiental de un viajero o una ruta.
- La siniestralidad DGT disponible se conserva como contexto provincial de Baleares, no como riesgo georreferenciado por tramo en Mallorca.
- El sentimiento y la meteorología dinámica solo se ejecutarán con un corpus autorizado y una clave AEMET, respectivamente.
- Las intervenciones propuestas requieren contraste en campo, participación institucional, análisis de demanda y evaluación de viabilidad.

## Figuras y tablas que conviene incluir

1. Arquitectura de datos desde *raw* hasta el dashboard.
2. Mapa de alojamientos, paradas y bandas de accesibilidad.
3. Cobertura de destinos turísticos por categoría.
4. Comparación de distancia euclídea y por red en la muestra estratificada.
5. Perfil municipal C1–C3 y su interpretación descriptiva.
6. Tabla de prioridades robustas y recomendaciones trazables.
7. Mapa de validación geométrica del caso OD09.
8. Tabla de comparación de emisiones coche-autobús.
