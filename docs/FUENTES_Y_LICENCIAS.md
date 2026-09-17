# Fuentes y derechos de uso

## Modelo Digital de Pendientes MDP05

- Fuente: Instituto Geográfico Nacional / Centro Nacional de Información Geográfica (IGN/CNIG), servicio WCS y descarga MDP05.
- Uso en el proyecto: cálculo derivado de pendiente para los 20 casos WALK prioritarios de OpenTripPlanner; 19 perfiles devolvieron valores válidos. No se redistribuye el raster fuente.
- Licencia declarada por la fuente: CC-BY 4.0 compatible con SCNE.
- Atribución que figurará en la memoria, dashboard y vídeo: **"Obra derivada de MDP05 2008-2015 CC-BY 4.0 scne.es"**.
- URL de consulta: <https://centrodedescargas.cnig.es/CentroDescargas/modelo-digital-pendientes-mdp05-primera-cobertura>.

## Estaciones de calidad del aire CAIB

- Fuente: Govern de les Illes Balears, "Estacions de mesura de la qualitat de l'aire".
- Licencia declarada por el catálogo: Creative Commons Attribution (CC-BY).
- Uso en el proyecto: localización de estaciones y contexto ambiental; no se infiere exposición de rutas ni se incorpora al TSMAI.
- URL: <https://intranet.caib.es/opendatacataleg/es/dataset/estacions-qualitat-aire>.

## Contexto meteorológico AEMET

- Fuente: AEMET OpenData. La reutilización exige citar a AEMET como autora.
- Uso previsto: observaciones meteorológicas por estación y fecha, siempre separadas de la estimación de ruta.
- Requisito técnico: una API key personal gratuita en `AEMET_API_KEY`; no se almacena ni distribuye en el repositorio.
- URL: <https://opendata.aemet.es/>.

## Siniestralidad vial DGT

- Fuente: Dirección General de Tráfico, ficheros de microdatos de accidentes con víctimas de 2024.
- Licencia declarada por el catálogo Datos.gob.es: CC-BY 4.0.
- Uso en el proyecto: contexto anual agregado de Baleares. Los registros no incluyen geometría de tramo utilizable en el prototipo, por lo que no se deduce seguridad de una ruta ni se añade al índice TSMAI.
- URL: <https://datos.gob.es/es/catalogo/e00130502-ficheros-de-microdatos-de-accidentes-con-victimas-2024>.

## Oferta turística reglada Ibestat

- Fuente: Instituto de Estadística de las Illes Balears, serie `000060A_000004` de plazas turísticas.
- Uso en el proyecto: contexto de capacidad reglada y rango estacional para los municipios con series disponibles.
- Límite: las plazas no miden ocupación, pernoctaciones, demanda de movilidad ni comportamiento observado.
- URL: <https://ibestat.caib.es/>.

## Sentimiento de reseñas

- No se descargan ni raspan reseñas de plataformas de terceros sin licencia o consentimiento explícito.
- Sólo se aceptan corpus CC0, CC-BY o con consentimiento explícito y evidencia de reutilización.
- Modelo opcional documentado en el proyecto de desarrollo: `nlptown/bert-base-multilingual-uncased-sentiment` (licencia MIT). **Esta copia de presentación no incluye el script que lo invoca** (`analyze_multilingual_sentiment`), retirado junto con el resto de componentes de IA generativa/preentrenada.

Las condiciones de reutilización dependen de cada fuente. Cuando una fuente
declara una licencia CC-BY, se mantiene su atribución; en todos los casos se
conservan este documento, la URL y el informe de ejecución como evidencia de
trazabilidad.

## Criterio aplicado

La guía del TFM exige al alumno comprobar que tiene licencia para los datos y revisar sus derechos de uso. Por tanto, cada fuente del proyecto debe mantenerse documentada con proveedor, URL, fecha de consulta, licencia y atribución aplicable.
