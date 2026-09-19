# Ingesta responsable de reseñas para sentimiento

> Los comandos vigentes son `python scripts/run_task.py
> ingest_licensed_mobility_survey`, `validate_licensed_reviews` y
> `aggregate_mobility_sentiment`. Los nombres históricos de scripts individuales
> que aparecen más abajo se conservan como contexto y no deben ejecutarse.

El proyecto no debe copiar reseñas de Google, Booking, TripAdvisor u otras
plataformas sin autorización expresa de reutilización. La disponibilidad en una
página web no equivale a una licencia para análisis o redistribución.

P12 admite trabajo de campo propio, anónimo y con consentimiento informado. No
actives `licensed_mobility_survey` en el registro de fuentes: la autorización
se aporta localmente, por cada campaña, mediante una atestación verificable.

El CSV de la encuesta debe contener este mínimo y no puede incluir nombre,
correo, teléfono, perfil, autor ni identificadores de participante:

```csv
review_id,accommodation_id,text,license,source_url
anon_0001,H/1234,"El trayecto a la parada fue cómodo y bien señalizado.",CONSENT,local_collection_with_informed_consent
```

También se admite `municipality` en lugar de `accommodation_id`. `review_id`
debe ser un seudónimo único y estable; no debe permitir reidentificar a una
persona. Crea, fuera de Git, `data/private/licensed_mobility_survey_consent.json`:

```json
{
  "source_id": "licensed_mobility_survey",
  "consent_obtained": true,
  "consent_notice_version": "v1.0",
  "collection_start": "2026-09-01",
  "collection_end": "2026-09-30",
  "approved_purposes": ["academic_analysis", "machine_learning_inference", "aggregated_publication"],
  "personal_data_removed": true,
  "retention_policy": "Eliminar la exportación identificable al finalizar el TFM."
}
```

Es una plantilla de estructura, no datos para copiar como observaciones. Debes
sustituir fechas, versión y política por las aprobadas para tu recogida real.

Primero valida y crea un snapshot inmutable, sin hacer ninguna descarga:

```powershell
python scripts/run_task.py ingest_licensed_mobility_survey --input "C:\ruta\encuesta_real.csv"
python scripts/run_task.py ingest_licensed_mobility_survey --input "C:\ruta\encuesta_real.csv" --execute
```

Validación y análisis, una vez instaladas las dependencias opcionales:

```powershell
python scripts/run_task.py validate_licensed_reviews
pip install -r requirements-nlp.txt
python scripts/run_task.py aggregate_mobility_sentiment
```

El modelo clasifica sentimiento general en positivo, neutral o negativo. No
debe llamarse "seguridad percibida" sin una anotación manual temática, acuerdo
entre anotadores y evaluación específica para movilidad turística.
