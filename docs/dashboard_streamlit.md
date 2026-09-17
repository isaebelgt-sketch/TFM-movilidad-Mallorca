# Dashboard Ejecutivo Streamlit

## Finalidad

El dashboard transforma los artefactos `curated` en una interfaz de exploración
trazable y de **apoyo a la decisión**. No recalcula indicadores pesados: expone
el resultado vigente **TSMAI V9 por alojamiento**, permite consultar rutas OTP
reales bajo una fecha y hora elegidas y conserva los resultados anteriores como
referencias metodológicas.

## Alcance visible

| Tipo de resultado | Elementos | Cómo interpretarlo |
|---|---|---|
| Vigente | TSMAI V9, capas territoriales P7, paradas GTFS, destinos OSM y rutas OTP | Evidencia individual de acceso sostenible, no una certificación ni un promedio anual. |
| Contexto o muestra | Pendiente, estaciones CAIB/AEMET, siniestralidad DGT, oferta turística y emisiones | No alimenta TSMAI ni se extrapola a rutas o alojamientos no medidos. |
| Histórico | TSMAI V1–V8, clústeres, casos OD y recomendaciones anteriores | Trazabilidad y comparación metodológica; no es el resultado final. |

## Vistas disponibles

### 📊 Síntesis ejecutiva
- Visión general del proyecto y objetivo del sistema.
- Resumen orientado a stakeholders no técnicos, con límites explícitos de interpretación.

### 🗺️ Análisis territorial interactivo
- Diseño 7:3 (Filtros a la izquierda, Mapa principal a la derecha).
- **KPIs dinámicos:** recálculo en tiempo real de alojamientos, cobertura, TSMAI V9 medio y distancia mediana a parada según los filtros aplicados.
- **Interactividad Folium:** Al hacer clic en un hotel del mapa, se despliega instantáneamente una ficha resumen en un panel destacado inferior.
- Alojamientos por banda de proximidad a parada GTFS, filtros por municipio y perfiles K-Means interpretables.

### 🧭 Explorador de casos y asistente explicable
- Diagnóstico y recomendación trazable de cada caso alojamiento-destino.
- Geometrías OTP reales: verde para caminar, naranja para bicicleta y azul para transporte público; tabla de tramos e indicaciones a pie traducidas.
- Perfil OSM de infraestructura activa de cada ruta y evidencia documental asociada.

## Arranque

Con el entorno `tfm-mallorca` activo:

```powershell
docker compose -f docker/otp/docker-compose.yml up -d otp-server
streamlit run app/streamlit_app.py
```

Para los comandos de validación y regeneración, consulta
[REPRODUCIBILIDAD_OPERATIVA.md](REPRODUCIBILIDAD_OPERATIVA.md).
