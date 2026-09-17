from __future__ import annotations
import sys
import argparse
from math import *
from os import *
from datetime import *


from pathlib import Path
from copy import deepcopy

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.shared import Pt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "Memoria_TFM_Movilidad_Sostenible_Mallorca.docx"
OUTPUT = ROOT / "docs" / "Memoria_TFM_Movilidad_Sostenible_Mallorca_actualizada.docx"


def find_paragraph(document, prefix):
    # Busca el parrafo por prefijo
    for paragraph in document.paragraphs:
        if paragraph.text.startswith(prefix):
            return paragraph
    raise ValueError(f"No se encontró el párrafo: {prefix}")

def find_heading(document, text):
    # Busca el encabezado por texto
    for paragraph in document.paragraphs:
        if paragraph.text == text and paragraph.style.name.startswith("Heading"):
            return paragraph
    raise ValueError(f"No se encontró el encabezado: {text}")


def replace_text(paragraph, text):
    # Reemplaza el texto del parrafo
    paragraph.clear()
    run = paragraph.add_run(text)
    run.font.size = Pt(10.5)


def insert_after(paragraph, text, style="normal"):
    new_paragraph = deepcopy(paragraph._p)
    paragraph._p.addnext(new_paragraph)
    new_paragraph.clear_content()
    wrapper = paragraph._parent.add_paragraph()
    wrapper._p.getparent().remove(wrapper._p)
    wrapper._p = new_paragraph
    wrapper._element = new_paragraph
    wrapper.style = style
    wrapper.add_run(text)
    return wrapper


def add_before(paragraph, text, style="normal"):
    new = paragraph.insert_paragraph_before(text, style=style)
    return new

def mark_first_row_as_header(table):
    properties = table.rows[0]._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "true")
    properties.append(header)


def main_memoria_tfm():
    document = Document(SOURCE)

    replace_text(
        find_paragraph(document, "Este trabajo desarrolla un sistema reproducible"),
        "Este trabajo desarrolla un sistema reproducible de análisis espacial para evaluar la accesibilidad turística y la movilidad sostenible en Mallorca. Integra registros públicos de alojamientos, GTFS, OpenStreetMap, puntos de interés turísticos y fuentes institucionales complementarias. La propuesta organiza los datos en capas raw, unified y curated; contrasta distancia euclídea y rutas reales de red; consulta itinerarios a pie, bicicleta y transporte público con OpenTripPlanner; y presenta los hallazgos en un dashboard interactivo. La línea base analiza 1.463 alojamientos georreferenciados y 1.423 destinos turísticos nombrados: el 78,88 % de los alojamientos y el 65,50 % de los destinos se sitúan a 800 m o menos de una parada. Se validaron 80 rutas peatonales y se estudiaron 20 pares origen-destino multimodales. El sistema identifica cinco casos robustos de revisión, calcula perfiles de pendiente para 19 de los 20 casos y estima una reducción contrafactual del 69,81 % de CO2eq en seis comparaciones coche-autobús. El trabajo amplía el análisis con infraestructura activa OSM, evidencia documental de accesibilidad universal, calidad del aire, estacionalidad de la oferta e índices territoriales explicables, manteniendo sus límites de interpretación.",
    )
    replace_text(
        find_paragraph(document, "This project develops a reproducible"),
        "This project develops a reproducible spatial analysis system to assess tourist accessibility and sustainable mobility in Mallorca. It integrates public accommodation records, GTFS, OpenStreetMap, tourist points of interest and complementary institutional sources. The workflow uses raw, unified and curated data layers; compares Euclidean and network distances; queries walking, cycling and public-transport itineraries with OpenTripPlanner; and presents findings in an interactive dashboard. The baseline covers 1,463 georeferenced accs and 1,423 named tourist dests. It validates 80 walking routes and evaluates 20 multimodal origin-dest pairs. res support evidence-based diagnostic prioritisation while preserving methodological limitations and avoiding unsupported claims about route safety, universal accessibility or real modal shift.",
    )

    objectives = find_paragraph(document, "• Comunicar los resultados")
    add_before(objectives, "• Incorporar de forma trazable evidencia de movilidad activa, pendiente y accesibilidad universal documental, sin confundirla con una certificación.")

    replace_text(
        find_paragraph(document, "El ámbito es Mallorca."),
        "El ámbito es Mallorca. El estudio usa una instantánea de fuentes abiertas y una muestra de 20 pares en una fecha y hora concretas. La escala territorial, la disponibilidad de datos y la posibilidad de construir un grafo local justifican la elección. Como contexto se incorporan estaciones CAIB de calidad del aire, oferta turística reglada de Ibestat y siniestralidad DGT agregada para Baleares; ninguna de estas capas se interpreta como exposición individual, demanda observada o riesgo por tramo. Quedan fuera la predicción de demanda, la observación de trayectorias individuales, la valoración económica de inversiones y la declaración de causalidad.",
    )

    replace_text(
        find_paragraph(document, "Los datos se procesan principalmente"),
        "Los datos se procesan principalmente con Python, GeoPandas, PyArrow, OSMium y OpenTripPlanner en Docker. Parquet y GeoParquet permiten almacenamiento columnar y trazable. Se añaden capas institucionales de calidad del aire CAIB, plazas turísticas de Ibestat, pendientes MDP05 del IGN/CNIG y siniestralidad DGT como contexto sujeto a limitaciones explícitas. PySpark se contempla como capacidad de escalado para volúmenes superiores, pero no se utiliza de forma artificial cuando el tamaño de Mallorca permite un procesamiento local reproducible.",
    )
    replace_text(
        find_paragraph(document, "Se extrajo una red de movilidad"),
        "Se extrajo una red de movilidad desde un PBF de OpenStreetMap con OSMium y se construyó un grafo OTP local junto con el feed GTFS. El grafo resultante incluyó 162.998 vértices, 417.112 aristas, 772 paradas y 311 patrones. Las consultas se realizaron mediante la API GraphQL de OTP. Además de itinerarios WALK y TRANSIT, se validaron rutas BICYCLE y se perfilaron las geometrías con etiquetas OSM de movilidad activa y con la pendiente MDP05. Los datos y el software se ejecutaron localmente con Anaconda, Jupyter Notebook y Docker Desktop, evitando APIs de pago.",
    )

    table = document.tables[1]
    for values in [
        ("IGN/CNIG MDP05", "Pendiente en rutas OTP", "Muestreo WCS y perfil reproducible"),
        ("CAIB", "Estaciones de calidad del aire", "Uso sólo como contexto puntual"),
        ("Ibestat", "Oferta turística reglada", "No equivale a demanda ni ocupación"),
        ("DGT", "Siniestralidad vial de Baleares", "Sin riesgo por tramo ni routing"),
    ]:
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = value

    for table_item in document.tables:
        mark_first_row_as_header(table_item)

    discussion_heading = find_heading(document, "8. Discusión")
    new_sections = [
        ("7.9. Movilidad activa, pendiente y accesibilidad universal documental", "Heading 2"),
        ("La extensión de movilidad activa valida rutas BICYCLE para los 20 casos de la muestra y perfila rutas WALK y BICYCLE mediante etiquetas de infraestructura activa de OpenStreetMap. La recomendación modal es transparente: 12 casos se clasifican como bicicleta, seis como bicicleta con revisión de confort y dos como transporte público. Estas etiquetas no certifican seguridad vial, disponibilidad de bicicletas ni calidad física de la infraestructura." , "normal"),
        ("Para la pendiente se procesaron hasta 20 rutas WALK priorizadas mediante el MDP05 del IGN/CNIG; 19 devolvieron valores válidos. La pendiente aporta una señal topográfica de apoyo, pero no mide anchura, continuidad, pavimento, iluminación, cruces ni barreras. Por esa razón no se incorpora al índice municipal TSMAI v2." , "normal"),
        ("La evidencia de accesibilidad universal se trata de forma conservadora. Se distinguieron 1.626 elementos OSM con señal positiva fuerte, como etiquetas de silla de ruedas, pavimento táctil o bordillo rebajado, de 6.952 cruces que sólo aportan contexto peatonal. Un total de 821 alojamientos se encuentra a 400 m o menos de evidencia fuerte y dos paradas GTFS declaran embarque accesible. Estos datos no acreditan una ruta universalmente accesible y su ausencia no prueba la existencia de una barrera." , "normal"),
        ("7.10. Índice territorial y contextos institucionales", "Heading 2"),
        ("El TSMAI v2 amplía el índice territorial con cobertura GTFS, éxito de enrutamiento, proximidad a infraestructura ciclista y peatonal OSM y proximidad a destinos turísticos. Se compararon cuatro escenarios de pesos y ocho municipios permanecieron entre los diez primeros en al menos tres escenarios. El análisis expresa robustez relativa a los pesos, no causalidad ni una clasificación administrativa definitiva." , "normal"),
        ("Como contexto ambiental y turístico, el dashboard incorpora 22 estaciones oficiales CAIB de calidad del aire y una serie de plazas turísticas regladas de Ibestat disponible para 15 municipios. Los microdatos DGT de 2024 se agregan únicamente como contexto provincial de Baleares: al no disponer de geometría de tramo ni de una delimitación insular plenamente verificada para todos los registros, no se integran en el enrutamiento, el TSMAI ni las recomendaciones." , "normal"),
    ]

    for text, style in new_sections:
        add_before(discussion_heading, text, style)

    discussion = find_paragraph(document, "La muestra multimodal y el cálculo de emisiones")
    replace_text(
        discussion,
        "La muestra multimodal y el cálculo de emisiones sugieren que, cuando existe una alternativa de autobús funcional, el potencial de reducción frente al coche individual es relevante. La infraestructura activa, la pendiente y los contextos ambientales enriquecen el diagnóstico, pero no permiten estimar comportamiento real, exposición ni seguridad de cada trayecto. Para generalizar a todos los viajes turísticos de Mallorca serían necesarios datos de demanda, ocupación, estacionalidad, preferencias modales y observación de viajes reales.",
    )

    limitations_heading = find_paragraph(document, "## Figuras y tablas")
    new_limits = [
        "• Las etiquetas OSM de infraestructura activa y accesibilidad universal son evidencia documental; no certifican seguridad, continuidad o accesibilidad física.",
        "• La pendiente se calcula sobre 19 rutas válidas de una muestra de 20; no representa todos los desplazamientos del territorio.",
        "• La estación CAIB más próxima no permite inferir exposición ambiental de una persona ni de una ruta.",
        "• La siniestralidad DGT se mantiene como contexto provincial de Baleares y no como riesgo georreferenciado por tramo en Mallorca.",
        "• El análisis de sentimiento y la meteorología dinámica quedan preparados, pero no se ejecutan sin un corpus con licencia y una clave AEMET, respectivamente.",
    ]
    for item in reversed(new_limits):
        add_before(limitations_heading, item)

    figures_heading = find_paragraph(document, "## Figuras y tablas")
    replace_text(figures_heading, "Figuras y tablas recomendadas para la versión final")
    figure_last = find_paragraph(document, "8. Tabla de comparación de emisiones")
    add_before(figure_last, "8. Mapa de rutas WALK, BICYCLE y multimodales con sus geometrías OTP.")
    replace_text(figure_last, "9. Tabla de comparación de emisiones coche-autobús y escenario potencial.")
    add_before(figure_last, "10. Tabla de evidencia universal documental, pendientes y límites de interpretación.")

    replace_text(
        find_paragraph(document, "El TFM demuestra la viabilidad"),
        "El TFM demuestra la viabilidad de construir con herramientas abiertas un sistema de análisis de accesibilidad turística y movilidad sostenible en Mallorca. La integración de alojamiento, GTFS y OSM produce una línea base auditable; el enrutamiento muestra que la proximidad euclídea infravalora el esfuerzo peatonal; y el análisis multimodal permite diferenciar problemas de parada, red, horario y preferencia de modo. Las extensiones de bicicleta, pendiente, infraestructura activa, accesibilidad documental y contexto institucional refuerzan el valor diagnóstico del sistema sin ocultar los límites de las fuentes.",
    )
    replace_text(
        find_paragraph(document, "El resultado principal no es una lista"),
        "El resultado principal no es una lista de obras, sino un método reproducible para priorizar revisión. Los cinco casos robustos y los perfiles territoriales deben contrastarse con inspección de campo, demanda, estacionalidad, seguridad vial y coordinación institucional antes de proponer inversiones. La estimación ambiental refuerza que, donde existe una alternativa de autobús viable, puede haber reducción frente al coche individual, aunque no permite inferir cambio modal real.",
    )
    future = find_paragraph(document, "• Incorporar pendientes")
    replace_text(future, "• Completar la accesibilidad universal con inventario municipal y auditoría de campo de itinerarios.")
    add_before(future, "• Añadir aforos de tráfico georreferenciados y series temporales ambientales con resolución adecuada para modelar exposición por ruta.")
    add_before(future, "• Ejecutar sentimiento multilingüe exclusivamente con reseñas reutilizables y evaluar el modelo con un protocolo explícito.")

    references = find_paragraph(document, "Anexos")
    new_references = [
        "Dirección General de Tráfico. (2024). Ficheros de microdatos de accidentes con víctimas 2024. Datos.gob.es. https://datos.gob.es/es/catalogo/e00130502-ficheros-de-microdatos-de-accidentes-con-victimas-2024",
        "Govern de les Illes Balears. (2026). Estacions de mesura de la qualitat de l'aire. Portal de Dades Obertes. https://intranet.caib.es/opendatacataleg/es/dataset/estacions-qualitat-aire",
        "Institut d'Estadística de les Illes Balears. (2026). Plaza turística. https://ibestat.caib.es/",
        "Instituto Geográfico Nacional y Centro Nacional de Información Geográfica. (2026). Modelo Digital de Pendientes MDP05. https://centrodedescargas.cnig.es/",
    ]
    for reference in reversed(new_references):
        # Inserta cada referencia en orden
        add_before(references, reference)

    replace_text(
        find_paragraph(document, "Anexo A."),
        "Anexo A. Inventario y diccionarios de datos. Anexo B. Manifiestos de descargas y de grafo OTP. Anexo C. Cuadernos y scripts reproducibles. Anexo D. Dashboard Streamlit y API local. Anexo E. Informes de validación, sensibilidad, emisiones, pendiente, evidencia universal y contextos institucionales. Los artefactos se encuentran en las carpetas data, docs, notebooks, docker, scripts y app del repositorio del proyecto.",
    )

    document.core_properties.title = "Memoria TFM Movilidad Sostenible Mallorca"
    document.core_properties.subject = "Actualización técnica y metodológica del prototipo"
    document.save(OUTPUT)
    print(OUTPUT)




"""Legacy dispatcher retained as non-executable history; use scripts/run_task.py.
parser = argparse.ArgumentParser(description="Consolidated ETL runner")
parser.add_argument("task", choices=["publish_current_layers_postgis", "build_memoria_tfm", "update_tfm_memory", "all"], help="Task to run")
args = parser.parse_args()

if args.task in ("all", "publish_current_layers_postgis"):
    print(f"\n=== Running run_publish_current_layers_postgis ===")
    run_publish_current_layers_postgis()
if args.task in ("all", "build_memoria_tfm"):
    print(f"\n=== Running run_build_memoria_tfm ===")
    run_build_memoria_tfm()
if args.task in ("all", "update_tfm_memory"):
    print(f"\n=== Running run_update_tfm_memory ===")
    run_update_tfm_memory()



"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Task to run")
    args = parser.parse_args()
    task_name = args.task if args.task.startswith("run_") else "run_" + args.task

    if task_name in ("run_update_tfm_memory", "run_memoria_tfm"):
        main_memoria_tfm()
        sys.exit(0)
    print(f"Task {task_name} not found.")
