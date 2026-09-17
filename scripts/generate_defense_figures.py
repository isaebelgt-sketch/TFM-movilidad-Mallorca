"""Genera figuras PNG reproducibles para la defensa de TSMAI V9.

Las figuras se derivan exclusivamente de los informes JSON versionados. No
recalculan rutas ni consultan servicios externos.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "figuras_defensa"
WIDTH, HEIGHT = 1600, 900
BG, INK, GRID = "#FFFFFF", "#1F2937", "#D1D5DB"


def read_json(name: str) -> dict:
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(Path("C:/Windows/Fonts") / name, size=size)


def text_center(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], text: str, face: ImageFont.FreeTypeFont, fill: str = INK) -> None:
    left, top, right, bottom = box
    bbox = draw.multiline_textbbox((0, 0), text, font=face, align="center", spacing=6)
    x = left + (right - left - (bbox[2] - bbox[0])) / 2
    y = top + (bottom - top - (bbox[3] - bbox[1])) / 2
    draw.multiline_text((x, y), text, font=face, fill=fill, align="center", spacing=6)


def bar_chart(title: str, ylabel: str, names: list[str], values: list[float], colors: list[str], filename: str, decimals: int = 0) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    title_font, label_font, value_font = font(42, True), font(26), font(28, True)
    text_center(draw, (70, 35, WIDTH - 70, 105), title, title_font)
    draw.text((75, 135), ylabel, font=label_font, fill=INK)
    plot_left, plot_right, plot_top, plot_bottom = 180, 1490, 200, 720
    maximum = max(values) * 1.18 if max(values) else 1
    for step in range(5):
        y = plot_bottom - (plot_bottom - plot_top) * step / 4
        draw.line((plot_left, y, plot_right, y), fill=GRID, width=2)
    count = len(values)
    slot = (plot_right - plot_left) / count
    bar_width = slot * 0.52
    for index, (name, value, color) in enumerate(zip(names, values, colors)):
        center = plot_left + slot * (index + 0.5)
        height = (plot_bottom - plot_top) * value / maximum
        left, right, top = center - bar_width / 2, center + bar_width / 2, plot_bottom - height
        draw.rounded_rectangle((left, top, right, plot_bottom), radius=8, fill=color)
        display = f"{value:.{decimals}f}".replace(".", ",")
        text_center(draw, (left - 50, top - 54, right + 50, top - 8), display, value_font)
        text_center(draw, (left - 80, 745, right + 80, 845), name, label_font)
    image.save(OUT / filename)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    v9 = read_json("tsmai_v9_seasonal_transit_report.json")
    sensitivity = read_json("tsmai_v9_sensitivity_report.json")
    levels = v9["levels"]
    bar_chart(
        "Distribución de niveles TSMAI V9",
        "Número de alojamientos",
        ["Favorable", "Intermedio", "Prioridad\nde mejora"],
        [levels["favorable"], levels["intermedio"], levels["prioridad de mejora"]],
        ["#2E7D32", "#F9A825", "#C62828"],
        "01_niveles_tsmai_v9.png",
    )
    seasonal = v9["seasonal_transit_component"]
    bar_chart(
        "Componente TRANSIT por campaña",
        "Puntuación media normalizada",
        ["Verano", "Invierno", "Media\nestacional"],
        [seasonal["summer_score_mean"], seasonal["winter_score_mean"], seasonal["seasonal_score_mean"]],
        ["#1565C0", "#7B1FA2", "#455A64"],
        "02_transit_estacional_v9.png",
        decimals=4,
    )
    results = sensitivity["accommodation_results"]
    bar_chart(
        "Sensibilidad de ponderaciones TSMAI V9",
        "Número de alojamientos",
        ["Nivel estable\nen 5 escenarios", "Nivel cambia en\nalgún escenario", "Prioridad robusta\ndel decil superior"],
        [results["level_stable_all_scenarios"], results["level_changed_in_any_scenario"], results["robust_top_decile"]],
        ["#00838F", "#EF6C00", "#6A1B9A"],
        "03_sensibilidad_tsmai_v9.png",
    )
    print(f"Figuras generadas en {OUT}")


if __name__ == "__main__":
    main()
