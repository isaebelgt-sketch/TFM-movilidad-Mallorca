"""Utilidades trazables para escenarios y fichas descargables del dashboard."""

from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

import pandas as pd


MODE_LABELS = {
    "WALK": "A pie",
    "BICYCLE": "Bicicleta",
    "CAR": "Coche",
}
MODE_COLORS = {
    "WALK": "#22c55e",
    "BICYCLE": "#f97316",
    "CAR": "#64748b",
}


def route_mode_label(mode: object) -> str:
    """Devuelve una etiqueta fiel al modo devuelto por OTP."""
    return MODE_LABELS.get(str(mode).upper(), "Transporte público")


def route_mode_color(mode: object) -> str:
    """Mantiene un color consistente para cada modo en fichas HTML y PDF."""
    return MODE_COLORS.get(str(mode).upper(), "#2563eb")


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decodifica una polilínea OTP (formato Google) a pares latitud/longitud."""
    index = latitude = longitude = 0
    coordinates: list[tuple[float, float]] = []
    while index < len(encoded):
        values = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += values[0]
        longitude += values[1]
        coordinates.append((latitude / 1e5, longitude / 1e5))
    return coordinates


def route_legs(route_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Normaliza una respuesta OTP guardada en sesión, si existe."""
    if not route_result or route_result.get("status") != "ok":
        return []
    itinerary = route_result.get("itinerary", {})
    legs = []
    for leg in itinerary.get("legs", []):
        route = leg.get("route") or {}
        legs.append(
            {
                "mode": leg.get("mode", "UNKNOWN"),
                "line": route.get("shortName") or route.get("longName") or "-",
                "distance_m": float(leg.get("distance", 0)),
                "duration_min": float(leg.get("duration", 0)) / 60,
                "points": decode_polyline((leg.get("legGeometry") or {}).get("points", ""))
                if (leg.get("legGeometry") or {}).get("points")
                else [],
            }
        )
    return legs


def _route_svg(legs: list[dict[str, Any]], width: int = 720, height: int = 280) -> str:
    """Esquema geográfico de la ruta basado en sus polilíneas, sin teselas externas."""
    points = [point for leg in legs for point in leg["points"]]
    if not points:
        return "<p><em>No hay geometría OTP almacenada para este caso.</em></p>"
    latitudes, longitudes = zip(*points)
    lat_range = max(max(latitudes) - min(latitudes), 0.00001)
    lon_range = max(max(longitudes) - min(longitudes), 0.00001)

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        latitude, longitude = point
        x = 30 + (longitude - min(longitudes)) / lon_range * (width - 60)
        y = height - 30 - (latitude - min(latitudes)) / lat_range * (height - 60)
        return x, y

    paths = []
    for leg in legs:
        if len(leg["points"]) < 2:
            continue
        values = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(transform, leg["points"]))
        color = route_mode_color(leg["mode"])
        dash = ' stroke-dasharray="8 8"' if str(leg["mode"]).upper() == "WALK" else ""
        paths.append(f'<polyline points="{values}" fill="none" stroke="{color}" stroke-width="5"{dash} />')
    start_x, start_y = transform(points[0])
    end_x, end_y = transform(points[-1])
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Trazado OTP de la ruta" '
        'style="max-width:100%;height:auto;background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px">'
        + "".join(paths)
        + f'<circle cx="{start_x:.1f}" cy="{start_y:.1f}" r="8" fill="#16a34a" />'
        + f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="8" fill="#dc2626" />'
        + '<text x="18" y="22" font-size="14" fill="#334155">Los colores distinguen los modos OTP; verde discontinuo: a pie.</text>'
        + "</svg>"
    )


def calculate_emissions_scenarios(
    places: pd.Series,
    mean_avoided_kg_per_shift: float,
    scenarios: list[dict[str, float | str]],
) -> pd.DataFrame:
    """Calcula escenarios, no predicciones, a partir de supuestos visibles."""
    total_places = float(pd.to_numeric(places, errors="coerce").fillna(0).clip(lower=0).sum())
    rows = []
    for scenario in scenarios:
        occupied_person_nights = total_places * float(scenario["occupancy_rate"]) * 365
        stays = occupied_person_nights / float(scenario["average_stay_nights"])
        shifted_trips = stays * float(scenario["modal_shift_rate"])
        rows.append(
            {
                "Escenario": scenario["name"],
                "Ocupación (%)": 100 * float(scenario["occupancy_rate"]),
                "Estancia media (noches)": float(scenario["average_stay_nights"]),
                "Adopción modal (%)": 100 * float(scenario["modal_shift_rate"]),
                "Viajes con cambio modal/año": round(shifted_trips),
                "CO2eq evitado estimado (kg/año)": round(shifted_trips * mean_avoided_kg_per_shift, 1),
            }
        )
    return pd.DataFrame(rows)


def build_case_html(case: pd.Series, route_result: dict[str, Any] | None, quality_context: dict[str, Any]) -> bytes:
    """Ficha HTML autónoma, imprimible y descargable, sin dependencias externas."""
    legs = route_legs(route_result)
    case_id = escape(str(case["od_id"]))
    rows = [
        ("Alojamiento", case["origin_name"]),
        ("Destino", case["destination_name"]),
        ("Municipio de origen", case["origin_municipality"]),
        ("Prioridad", f"{case['priority_level']} ({case['priority_index_score']:.3f})"),
        ("Resultado OTP de la muestra", case["analysis_outcome"]),
        ("Recomendación", case["recommendation"]),
        ("Evidencia", case["evidence"]),
        ("Fecha de generación", quality_context.get("generated_at", "No disponible")),
    ]
    facts = "".join(f"<tr><th>{escape(str(label))}</th><td>{escape(str(value))}</td></tr>" for label, value in rows)
    legs_html = "".join(
        f"<tr><td>{route_mode_label(leg['mode'])}</td>"
        f"<td>{escape(str(leg['line']))}</td><td>{leg['distance_m']:.0f}</td><td>{leg['duration_min']:.1f}</td></tr>"
        for leg in legs
    ) or '<tr><td colspan="4">No se ha consultado todavía una ruta OTP en esta sesión.</td></tr>'
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Ficha {case_id}</title>
    <style>body{{font-family:Arial,sans-serif;color:#0f172a;margin:36px;line-height:1.45}}h1{{color:#14532d}}h2{{margin-top:30px;color:#166534}}table{{border-collapse:collapse;width:100%;margin:14px 0}}th,td{{text-align:left;padding:9px;border:1px solid #cbd5e1}}th{{background:#ecfdf5;width:30%}}.note{{padding:14px;background:#fefce8;border-left:4px solid #ca8a04}}footer{{margin-top:30px;font-size:12px;color:#475569}}</style>
    </head><body><h1>Ficha de caso {case_id}</h1><p>Accesibilidad turística y movilidad sostenible - Mallorca</p>
    <table>{facts}</table><h2>Ruta OTP consultada</h2>{_route_svg(legs)}<table><thead><tr><th>Modo</th><th>Línea</th><th>Distancia (m)</th><th>Duración (min)</th></tr></thead><tbody>{legs_html}</tbody></table>
    <p class="note">Esta ficha apoya la revisión técnica. Las recomendaciones requieren validación de campo, viabilidad operativa y contraste con datos actualizados.</p>
    <footer>Fuente: capas curated del TFM, GTFS TIB y OpenTripPlanner. El trazado incluido procede de la respuesta OTP mostrada en la aplicación.</footer></body></html>"""
    return html.encode("utf-8")


def build_case_pdf(case: pd.Series, route_result: dict[str, Any] | None, quality_context: dict[str, Any]) -> bytes:
    """Genera una ficha PDF estática y autocontenida para descarga desde Streamlit."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    class RouteSketch(Flowable):
        """Esquema vectorial de las polilíneas OTP para una ficha PDF autónoma."""

        def __init__(self, route_legs_data: list[dict[str, Any]]):
            super().__init__()
            self.legs = route_legs_data
            self.width = 17.3 * cm
            self.height = 5.4 * cm

        def draw(self) -> None:
            points = [point for leg in self.legs for point in leg["points"]]
            if not points:
                return
            latitudes, longitudes = zip(*points)
            lat_range = max(max(latitudes) - min(latitudes), 0.00001)
            lon_range = max(max(longitudes) - min(longitudes), 0.00001)

            def transform(point: tuple[float, float]) -> tuple[float, float]:
                latitude, longitude = point
                return (
                    12 + (longitude - min(longitudes)) / lon_range * (self.width - 24),
                    12 + (latitude - min(latitudes)) / lat_range * (self.height - 24),
                )

            self.canv.setFillColor(colors.HexColor("#f8fafc"))
            self.canv.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)
            for leg in self.legs:
                if len(leg["points"]) < 2:
                    continue
                self.canv.setStrokeColor(colors.HexColor(route_mode_color(leg["mode"])))
                self.canv.setLineWidth(3.5)
                self.canv.setDash(5, 4) if str(leg["mode"]).upper() == "WALK" else self.canv.setDash()
                route_path = self.canv.beginPath()
                first_x, first_y = transform(leg["points"][0])
                route_path.moveTo(first_x, first_y)
                for point in leg["points"][1:]:
                    x, y = transform(point)
                    route_path.lineTo(x, y)
                self.canv.drawPath(route_path, stroke=1, fill=0)
            self.canv.setDash()
            start_x, start_y = transform(points[0])
            end_x, end_y = transform(points[-1])
            self.canv.setFillColor(colors.HexColor("#16a34a")); self.canv.circle(start_x, start_y, 5, fill=1, stroke=0)
            self.canv.setFillColor(colors.HexColor("#dc2626")); self.canv.circle(end_x, end_y, 5, fill=1, stroke=0)
            self.canv.setFillColor(colors.HexColor("#334155")); self.canv.setFont("Helvetica", 8); self.canv.drawString(10, self.height - 12, "Los colores distinguen los modos OTP; verde discontinuo: a pie.")

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Ficha de caso {escape(str(case['od_id']))}", styles["Title"]), Spacer(1, 0.25 * cm)]
    story.append(Paragraph("Accesibilidad turística y movilidad sostenible - Mallorca", styles["Heading2"]))
    info = [
        ["Alojamiento", str(case["origin_name"])], ["Destino", str(case["destination_name"])],
        ["Municipio de origen", str(case["origin_municipality"])], ["Prioridad", f"{case['priority_level']} ({case['priority_index_score']:.3f})"],
        ["Resultado OTP de la muestra", str(case["analysis_outcome"])], ["Recomendación", str(case["recommendation"])],
        ["Evidencia", str(case["evidence"])], ["Generación", str(quality_context.get("generated_at", "No disponible"))],
    ]
    table = Table([[Paragraph(escape(label), styles["BodyText"]), Paragraph(escape(value), styles["BodyText"])] for label, value in info], colWidths=[4.3 * cm, 13.0 * cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecfdf5")), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.extend([table, Spacer(1, 0.3 * cm), Paragraph("Ruta OTP consultada", styles["Heading2"])])
    legs = route_legs(route_result)
    if legs:
        story.extend([RouteSketch(legs), Spacer(1, 0.18 * cm)])
        route_data = [["Modo", "Línea", "Distancia (m)", "Duración (min)"]] + [[route_mode_label(leg["mode"]), str(leg["line"]), f"{leg['distance_m']:.0f}", f"{leg['duration_min']:.1f}"] for leg in legs]
        route_table = Table(route_data, colWidths=[4.1 * cm, 4.1 * cm, 4.3 * cm, 4.3 * cm])
        route_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14532d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 1), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(route_table)
    else:
        story.append(Paragraph("No se ha consultado una geometría OTP durante esta sesión. La ficha conserva la evidencia del caso y puede regenerarse tras consultar una ruta.", styles["BodyText"]))
    story.extend([Spacer(1, 0.35 * cm), Paragraph("Limitación de uso", styles["Heading2"]), Paragraph("Esta ficha es una ayuda a la revisión técnica. No prueba causalidad, no equivale a una decisión de obra y requiere validación de campo y viabilidad operativa.", styles["BodyText"])])
    document.build(story)
    return buffer.getvalue()
