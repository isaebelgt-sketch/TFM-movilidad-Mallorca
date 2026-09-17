# Gobierno de datos para el planificador multimodal

## Principios aplicados

El planificador sólo expone puntos procedentes de las capas `curated` con
geometría válida. No geocodifica direcciones de usuarios, no conserva sus
consultas y no modifica la zona `raw`. Cada resultado dinámico se asocia a la
fecha, hora, versión de GTFS cargada y endpoint OTP utilizados en la consulta.

El registro ejecutable `config/source_registry.json` es la fuente de verdad de
admisión. Antes de una descarga se ejecuta `python
scripts/validate_source_registry.py`: sólo una fuente con estado `approved`,
licencia admitida y metadatos completos puede entrar en `data/raw/`.

## Fuentes y límites

| Componente | Fuente permitida | Regla de uso |
| --- | --- | --- |
| Alojamientos | Registro público oficial | Conservar identificador, fecha y control de geometría. |
| Transporte | GTFS TIB descargado con licencia aplicable | Mostrar fecha/hora de consulta; no presentar horario como tiempo real. |
| Red, POI e infraestructura | OpenStreetMap con atribución ODbL | Tratar etiquetas ausentes como dato desconocido, no como infraestructura inexistente. |
| Pendiente | IGN CNIG MDP05 | Asociar a ruta y fecha de proceso; no deducir estado de aceras. |
| Sentimiento | Corpus CC0, CC-BY o consentimiento explícito | Validar licencia, vínculo geográfico y minimización de datos antes de NLP. |

## Contratos de publicación

- `reviews_licensed.csv` no se descarga ni se versiona. Debe incluir texto,
  licencia, URL de origen y `accommodation_id` o coordenadas.
- El sentimiento municipal sólo se publica a partir de diez menciones de
  movilidad vinculadas; las muestras menores se marcan como insuficientes.
- Una puntuación de ruta no certifica accesibilidad universal, seguridad vial,
  demanda observada ni reducción real de emisiones.
- Los factores de emisión, pesos y estados de ruta se devuelven junto a cada
  recomendación para permitir auditoría y réplica.
- Las fuentes con `pending_permission` o `disabled` no se descargan ni se
  transforman. Una excepción requiere actualizar el registro y conservar la
  evidencia de la licencia o del consentimiento.
