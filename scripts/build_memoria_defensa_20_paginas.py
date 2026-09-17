"""Genera una memoria de defensa clara y visual del TFM de movilidad sostenible."""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Memoria_y_Defensa_TFM_Movilidad_Sostenible_Mallorca_20_paginas.docx"
FIG = ROOT / "docs" / "figuras_defensa"

NAVY = "17365D"
BLUE = "DCE6F1"
PALE = "F4F7FA"
GREY = "D9E1F2"
TEXT = RGBColor(0, 0, 0)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tcMar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tcMar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def add_field(run, field):
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


def set_run(run, size=10.5, bold=False, italic=False, color=TEXT):
    run.font.name = "Aptos"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def add_text(doc, text, style=None, after=5, before=0, align=None, italic=False, bold=False):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.08
    if align is not None:
        p.alignment = align
    r = p.add_run(text)
    set_run(r, bold=bold, italic=italic)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.space_before = Pt(5 if level == 1 else 3)
    p.paragraph_format.space_after = Pt(7 if level == 1 else 4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run(r, size=16 if level == 1 else 12, bold=True)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(item)
        set_run(r)


def add_table(doc, headers, rows, widths=None):
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.autofit = False
    tbl.style = "Table Grid"
    hdr = tbl.rows[0]
    set_repeat_table_header(hdr)
    for i, value in enumerate(headers):
        cell = hdr.cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shade(cell, NAVY)
        set_cell_margins(cell)
        if widths:
            cell.width = Cm(widths[i])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(value)
        set_run(r, size=9, bold=True, color=RGBColor(255, 255, 255))
    for ri, row in enumerate(rows):
        cells = tbl.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)
            if ri % 2 == 1:
                shade(cell, PALE)
            if widths:
                cell.width = Cm(widths[i])
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 and len(row) > 2 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(str(value))
            set_run(r, size=8.5)
    return tbl


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run(r, size=8.5, italic=True)


def add_figure(doc, name, text, width=15.2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(0)
    shape = p.add_run().add_picture(str(FIG / name), width=Cm(width))
    shape._inline.docPr.set("descr", text)
    shape._inline.docPr.set("title", "Figura de resultados TSMAI V9")
    caption(doc, text)


def page(doc):
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def source_ref(doc, label):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(label)
    set_run(r, size=8.5, italic=True)


def prose_after(heading, text):
    """Inserta desarrollo narrativo justo después de un título de sección."""
    xml = OxmlElement("w:p")
    heading._p.addnext(xml)
    p = Paragraph(xml, heading._parent)
    p.style = "Normal"
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.08
    r = p.add_run(text)
    set_run(r)
    return p


def enrich_narrative(doc):
    """Añade explicación continua para que las tablas acompañen, no sustituyan, el relato."""
    extra = {
        "Resumen ejecutivo": [
            "La intención no es etiquetar alojamientos como buenos o malos, sino hacer visible una realidad que suele quedar repartida entre mapas, horarios y experiencias aisladas. La herramienta permite pasar de una impresión general a una revisión concreta: localizar un caso, entender qué parte de la conexión falla y decidir qué información adicional hace falta antes de actuar. Esa es la utilidad principal del proyecto para una defensa: demuestra un producto que puede sostener una conversación de planificación con evidencia comprobable.",
            "El índice final se acompaña de mapas, fichas y escenarios alternativos porque una sola cifra nunca explica un territorio. Si una puntuación cambia, el usuario puede volver a las capas de origen y revisar si el motivo es la distancia, el calendario de servicio, una ruta poco favorable o la ausencia de evidencia cartográfica. Esta capacidad de abrir el resultado es la diferencia entre un indicador útil y una etiqueta opaca.",
        ],
        "1. El problema que aborda el proyecto": [
            "La movilidad turística tiene una dificultad particular: las necesidades no son idénticas durante todo el año, ni todos los visitantes conocen el territorio, ni una conexión que parece cercana en un mapa se traduce necesariamente en un trayecto cómodo. La primera y la última parte del viaje suelen ser decisivas. Caminar hasta una parada, esperar un servicio o alcanzar un destino desde el alojamiento puede resultar sencillo en un caso y convertirse en una barrera en otro. El proyecto trata precisamente de hacer visible esa diferencia sin perder la escala individual del alojamiento.",
            "También era importante evitar una respuesta basada únicamente en la proximidad. Un radio de 800 metros puede ser una pista útil, pero no cuenta si existe un paso seguro, una acera continua, una pendiente pronunciada o una frecuencia compatible con la estancia. Por eso la plataforma combina medidas de cribado territorial con rutas por red y con escenarios temporales. La lectura final conserva esa prudencia: ofrece señales para mirar mejor, no afirmaciones que excedan los datos disponibles.",
        ],
        "2. Objetivos y personas a las que sirve": [
            "Los objetivos se han formulado pensando en una persona que debe justificar una prioridad sin ser especialista en sistemas de información geográfica. Un técnico municipal puede empezar por un municipio o una brecha concreta; un gestor de destino puede consultar cómo varía la conexión entre estaciones; y una persona que revisa el modelo puede entrar hasta los datos y reglas de cálculo. El mismo resultado se expresa a diferentes niveles de detalle, de forma que la interfaz no obligue al usuario a elegir entre simplificación excesiva y complejidad innecesaria.",
            "La palabra explicable es central. Cada componente del TSMAI está publicado, cada peso se declara y los resultados se someten a un análisis de sensibilidad. No se utiliza un modelo que entregue una prioridad sin explicar cómo ha llegado a ella. Esta decisión reduce la espectacularidad de la solución, pero aumenta su utilidad en un contexto donde las decisiones de movilidad afectan a residentes, visitantes y administraciones con intereses distintos.",
        ],
        "3. Datos y fuentes": [
            "Trabajar con fuentes distintas exige reconocer que sus calidades también son distintas. Un GTFS describe el servicio programado; no confirma que un vehículo haya circulado puntualmente. OpenStreetMap representa conocimiento cartográfico colaborativo; no equivale a una inspección del pavimento. El registro oficial identifica la oferta de alojamiento, pero no describe por sí mismo la experiencia de desplazamiento de cada visitante. La metodología respeta estas diferencias y evita usar una capa fuera del alcance para el que fue creada.",
            "La trazabilidad empieza antes de calcular. Cada fuente se conserva con su versión o snapshot, se somete a comprobaciones de estructura y se asocia a un uso concreto dentro del proyecto. Esta disciplina permite distinguir un dato que construye el índice de otro que solo aporta contexto. En términos de defensa, facilita responder a dos preguntas habituales: de dónde procede una cifra y qué parte de la realidad no está describiendo.",
        ],
        "4. Cómo se transforma un mapa en evidencia": [
            "La cadena de trabajo no es una sucesión automática de archivos. En cada fase se toma una decisión que puede afectar a la lectura posterior: qué geometrías se consideran válidas, cómo se enlaza un alojamiento con la red, qué destino se utiliza para un par reproducible o qué duración de trayecto se interpreta como viable. Por ello los pasos se documentan y los resultados intermedios se guardan. La reproducibilidad no significa que cualquier fuente cambie menos, sino que se sabe exactamente con qué versión se trabajó y cómo se llegó a cada salida.",
            "El motor de rutas aporta un cambio importante respecto a un mapa estático. No basta con tener calles dibujadas: hace falta recorrerlas con reglas de modo, red y tiempo. A pie, en bicicleta o en transporte público, la conexión depende del trazado real y de la disponibilidad programada. El proyecto traduce ese resultado técnico a una ficha legible, pero mantiene la posibilidad de revisar los itinerarios que hay detrás cuando el análisis lo requiere.",
        ],
        "5. El índice TSMAI V9": [
            "La evolución desde V1 hasta V9 no debe interpretarse como nueve notas distintas para el mismo fenómeno. Es la historia de cómo el proyecto sustituyó aproximaciones iniciales por evidencia más próxima al desplazamiento real. La proximidad geométrica sirvió para empezar a explorar el territorio, pero después se incorporaron rutas WALK y BICYCLE, escenarios TRANSIT y, finalmente, la comparación estacional. Mantener esa cronología visible ayuda a entender que la versión vigente es V9 y que las cifras anteriores se conservan como aprendizaje metodológico, no como resultados concurrentes.",
            "El índice calcula una media ponderada de componentes normalizados. Esa fórmula ordena información heterogénea, pero no elimina sus matices. Por ese motivo la cobertura de evidencia se publica por alojamiento y el dashboard no muestra solo el resultado agregado. Una puntuación baja puede deberse a varias combinaciones distintas de causas; tratar todas como un mismo problema de infraestructura sería una lectura incorrecta y poco útil para planificar.",
        ],
        "6. El dashboard y la experiencia de uso": [
            "La interfaz se diseñó como una secuencia de decisiones y no como un escaparate de gráficos. La pantalla inicial permite entender el tamaño del universo y las señales principales. Después, los filtros territoriales y la ficha individual reducen la escala hasta un caso concreto. Finalmente, el planificador permite comparar alternativas de desplazamiento cuando se necesita una conversación más operativa. El usuario puede detenerse en cualquiera de estos niveles sin perder el vínculo con la metodología.",
            "Los filtros tienen una función metodológica, no solo estética. Cuando se selecciona un municipio, una banda de distancia o un nivel de prioridad, el sistema debe dejar claro que el total mostrado ha cambiado. Las capas, las fechas y los criterios de consulta forman parte de la evidencia. Esta atención al contexto evita que una captura de pantalla se utilice fuera de la condición en la que fue calculada.",
        ],
        "7. Resultados que merece la pena explicar": [
            "La distribución de niveles muestra que la situación no es homogénea. Sin embargo, tampoco conviene convertir el grupo de prioridad de mejora en una lista de conclusiones cerradas. Los 172 casos indican dónde puede tener más sentido concentrar una revisión inicial, pero cada uno necesita ser interpretado con sus componentes. La diferencia entre un problema de cercanía, de servicio temporal o de ruta de acceso cambia el tipo de conversación que debe abrirse después con la administración competente o con una visita de campo.",
            "El resultado también confirma que una lectura territorial gana utilidad cuando puede alternar entre conjunto y detalle. La cifra media de 0,625 resume el universo, mientras que la clasificación y el mapa permiten reconocer su heterogeneidad. Esta doble escala es útil para defender el proyecto: el análisis produce una visión global, pero no obliga a aceptar la media como representación suficiente de todos los alojamientos.",
        ],
        "8. El hallazgo estacional": [
            "La estacionalidad es relevante porque un destino turístico no se comporta igual en septiembre que en enero. Si se utilizase un único día para puntuar la disponibilidad de transporte público, el resultado podría depender más de esa elección que de la conectividad real que se pretende estudiar. V9 utiliza cuatro situaciones horarias de verano y cuatro de invierno, siempre sobre el mismo feed versionado. Así, el cambio observado se atribuye al calendario consultado y no a una mezcla de fuentes incompatibles.",
            "La reducción del componente TRANSIT en los escenarios invernales debe comunicarse con cuidado. No demuestra que las personas no se desplacen ni que el sistema haya empeorado causalmente; describe las respuestas del experimento bajo unas fechas y reglas concretas. Su valor está en señalar una posible fragilidad estacional para revisar la primera y la última milla, las frecuencias y la adecuación de la oferta cuando el contexto turístico cambia.",
        ],
        "9. ¿Cambian las conclusiones si cambian los pesos?": [
            "La sensibilidad responde a una objeción legítima: los pesos de un índice compuesto siempre incorporan una decisión normativa. En vez de presentar una combinación como inevitable, el proyecto prueba cinco escenarios deterministas y observa qué ocurre con los niveles y rankings. Este ejercicio no convierte los pesos en una verdad científica, pero permite identificar dónde el resultado es estable y dónde depende con mayor intensidad de la preferencia analítica elegida.",
            "La lectura adecuada es gradual. Los 625 alojamientos que no cambian de nivel transmiten una señal categórica estable dentro de los escenarios definidos. Los 836 que sí cambian no son errores; muestran que conviene interpretar su prioridad con más matiz. Los 110 casos que aparecen en el decil superior en al menos cuatro escenarios ofrecen una cartera especialmente interesante para continuar con contraste técnico, siempre sin confundir robustez estadística relativa con una orden de inversión.",
        ],
        "10. Leer el territorio sin simplificarlo": [
            "Las capas del mapa permiten comprender la posición de cada alojamiento dentro de una red más amplia de paradas, destinos y evidencia de movilidad activa. Esta información resulta muy útil para descubrir patrones, pero exige distinguir lo que representa cada capa. Las distancias de la tabla son euclídeas y sirven para agrupar y explorar; no deben leerse como una distancia caminable certificada. Los itinerarios reales se obtienen en otra parte de la cadena, mediante el motor de rutas.",
            "La diferencia entre una medida de proximidad y una ruta calculada es más que un detalle técnico. Una línea recta no incorpora desvíos, pasos, discontinuidades ni la red de calles disponible. En una defensa conviene explicarlo de forma directa: el proyecto usa la proximidad para saber dónde mirar y el routing para entender cómo se llega. La combinación de ambas medidas mejora el diagnóstico sin prometer una precisión que los datos no pueden ofrecer.",
        ],
        "11. De los resultados a una decisión razonada": [
            "El paso desde una señal analítica a una intervención pública requiere información adicional. Por ejemplo, una brecha de proximidad puede sugerir que falta una conexión, pero antes de proponer una nueva parada habría que revisar la ruta peatonal existente, la demanda, la frecuencia del servicio, las restricciones operativas y la experiencia de residentes. La herramienta no elimina ese trabajo; lo ordena y ayuda a justificar por qué se empieza por un caso y no por otro.",
            "Esta es una de las decisiones de diseño más humanas del proyecto: dejar espacio para la revisión profesional. El dashboard puede proponer una acción de revisión en lenguaje llano, pero no presenta obras como consecuencia automática de una puntuación. La interpretación final necesita conocimiento local, contraste de campo y coordinación institucional. El sistema ofrece una base común para que esas conversaciones partan de la misma evidencia.",
        ],
        "12. Validación y reproducibilidad": [
            "La validación se plantea como una cadena. Primero se comprueba que las tareas publicadas se pueden cargar; después, que el índice y sus capas tienen las cifras esperadas; y, por último, que la interfaz recibe los datos que necesita. Esta estructura reduce el riesgo de una entrega que parezca correcta en el mapa pero contenga una incoherencia en la generación previa. Los informes dejan constancia de cada comprobación para que pueda revisarse de nuevo.",
            "La reproducibilidad también tiene una dimensión de comunicación. En una defensa, poder señalar el archivo, el snapshot y la fase que generó una cifra es más convincente que afirmar que el sistema funciona sin mostrar cómo se verificó. El proyecto separa los controles derivados de las consultas que requerirían volver a ejecutar el motor de rutas, evitando presentar una regeneración limitada como si fuese una campaña completamente nueva.",
        ],
        "13. Alcance ampliado y capacidades preparadas": [
            "Las capacidades ampliadas se mantienen fuera de TSMAI V9 porque responden a preguntas diferentes y necesitan evidencias con otra cobertura. El análisis de sentimiento puede aportar una lectura agregada de cómo se habla de la movilidad, pero no debe confundirse con una medida directa de accesibilidad de un alojamiento. De forma similar, la existencia de una etiqueta de accesibilidad es valiosa como señal, pero no sustituye una inspección física con criterios de diseño universal.",
            "Separar estas líneas no disminuye la ambición del proyecto; la hace más responsable. Permite seguir incorporando conocimiento sin inflar el índice con variables que no están alineadas en fecha, licencia, resolución o significado. Cuando una fuente cumpla las condiciones necesarias, podrá integrarse de manera explícita y versionada, igual que ocurrió con los componentes de ruteo y con la estacionalidad.",
        ],
        "14. Límites y consideraciones éticas": [
            "Toda herramienta de priorización puede influir en qué problemas se ven primero y cuáles quedan fuera del foco. Por eso es importante comunicar la incertidumbre de forma visible y no esconderla en una nota técnica. La ausencia de una etiqueta en un mapa no demuestra ausencia de infraestructura; un trayecto calculado no demuestra que sea cómodo o seguro; y un ranking no transforma una prioridad relativa en una decisión justa por sí misma.",
            "La dimensión ética también aparece al tratar reseñas y datos territoriales. El proyecto evita publicar textos individuales y plantea agregaciones con umbrales de tamaño de muestra, además de respetar las condiciones de licencia. La prudencia metodológica tiene consecuencias prácticas: ayuda a evitar que un dato incompleto se convierta en una afirmación sobre personas, barrios o establecimientos que no pueda sostenerse con la evidencia disponible.",
        ],
        "15. Trabajo futuro": [
            "La siguiente fase debería combinar el sistema de datos con observación directa. Una visita a una muestra de rutas y paradas permitiría contrastar elementos que el modelo no puede certificar, como continuidad, iluminación, comodidad, señalización y barreras físicas. No se trata de reemplazar la plataforma por trabajo de campo, sino de usar el análisis para seleccionar mejor qué situaciones merece la pena observar primero.",
            "También sería valioso incorporar información de uso real cuando exista una fuente adecuada: ocupación, puntualidad, demanda, cambios de servicio y, en su caso, datos de movilidad compartida. Estas ampliaciones permitirían pasar de la accesibilidad programada a una lectura más cercana al desempeño vivido. Cada incorporación debería mantener la misma disciplina de versión, licencia y alcance que organiza la entrega actual.",
        ],
        "16. Conclusión": [
            "En conjunto, el TFM demuestra que es posible construir una herramienta de movilidad turística que sea técnicamente sólida sin dejar de ser comprensible. El proyecto une datos abiertos, rutas reales y una interfaz orientada a preguntas prácticas. Su mayor fortaleza no es afirmar que conoce por completo la experiencia de moverse por Mallorca, sino hacer explícito qué se puede observar con los datos actuales y qué comprobaciones siguen pendientes.",
            "La memoria propone una forma de presentar resultados que invita a usarlos con cuidado. El TSMAI V9 ofrece un punto de partida para priorizar investigación; el análisis estacional y la sensibilidad impiden tratar ese punto de partida como una verdad única; y los anexos conservan la profundidad necesaria para auditar cada decisión. Esa combinación convierte el prototipo en una base realista para continuar el trabajo con instituciones y conocimiento local.",
        ],
    }
    headings = {p.text: p for p in doc.paragraphs if p.style.name == "Heading 1"}
    for title, paragraphs in extra.items():
        anchor = headings.get(title)
        if anchor is None:
            continue
        for text in paragraphs:
            anchor = prose_after(anchor, text)


def setup(doc):
    sec = doc.sections[0]
    sec.top_margin = Cm(1.75)
    sec.bottom_margin = Cm(1.55)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(10.5)
    for name, size in (("Title", 27), ("Heading 1", 16), ("Heading 2", 12)):
        s = styles[name]
        s.font.name = "Aptos Display" if name != "Normal" else "Aptos"
        s._element.rPr.rFonts.set(qn("w:ascii"), s.font.name)
        s._element.rPr.rFonts.set(qn("w:hAnsi"), s.font.name)
        s.font.size = Pt(size)
        s.font.color.rgb = TEXT
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(3)
    a = footer.add_run("Memoria y defensa | Movilidad sostenible en Mallorca | Página ")
    set_run(a, size=8, color=RGBColor(80, 80, 80))
    n = footer.add_run()
    set_run(n, size=8, color=RGBColor(80, 80, 80))
    add_field(n, "PAGE")


def main():
    doc = Document()
    setup(doc)
    props = doc.core_properties
    props.title = "Memoria y defensa de movilidad sostenible en Mallorca"
    props.subject = "Trabajo Fin de Máster sobre accesibilidad turística y movilidad sostenible"

    # 1 Portada
    doc.add_paragraph().paragraph_format.space_after = Pt(50)
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Movilidad turística sostenible en Mallorca")
    set_run(r, size=27, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    r = p.add_run("Memoria y defensa de un sistema de análisis de accesibilidad\npara alojamientos y destinos turísticos")
    set_run(r, size=15)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(38)
    r = p.add_run("Trabajo Fin de Máster\nData Science, Big Data e Inteligencia Artificial")
    set_run(r, size=12)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(80)
    r = p.add_run("Un proyecto para entender dónde la movilidad sostenible funciona\ny dónde conviene mirar con más detalle antes de intervenir.")
    set_run(r, size=12, italic=True)

    # 2 Resumen
    page(doc); add_heading(doc, "Resumen ejecutivo")
    add_text(doc, "Este proyecto convierte una pregunta cotidiana en una herramienta útil para la gestión turística: si una persona se aloja en Mallorca sin coche, ¿qué tan fácil es moverse de forma sostenible desde su alojamiento? La respuesta no se basa en una línea recta dibujada sobre un mapa, sino en datos abiertos, horarios oficiales y rutas calculadas sobre la red real.")
    add_text(doc, "El resultado es un panel de control que reúne evidencia sobre transporte público, trayectos a pie y bicicleta. Su pieza central es el TSMAI V9, una puntuación explicable entre 0 y 1 para cada alojamiento. No pretende certificar que una zona sea accesible ni decidir una obra por sí sola: ayuda a ordenar la revisión y a hacer buenas preguntas antes de invertir.")
    add_table(doc, ["Dato", "Resultado actual", "Qué nos dice"], [
        ["Universo", "1.461 alojamientos", "Registro oficial con geometría válida."],
        ["Índice TSMAI V9", "Media 0,625", "Existe diversidad territorial en la conectividad sostenible."],
        ["Nivel favorable", "719 alojamientos", "Evidencia disponible más sólida según el modelo."],
        ["Prioridad de mejora", "172 alojamientos", "Candidatos a revisión técnica; no una lista automática de obras."],
        ["Capas del mapa", "772 paradas y 4.487 destinos", "El análisis conecta oferta de transporte y lugares de interés."],
    ], [3.2, 4.0, 8.0])
    source_ref(doc, "Detalle metodológico: véanse Anexos A, B y H.")

    # 3 índice
    page(doc); add_heading(doc, "Índice de la memoria")
    for text in [
        "1. El problema que aborda el proyecto", "2. Objetivos y personas a las que sirve", "3. Datos y fuentes", "4. Cómo se transforma un mapa en evidencia", "5. El índice TSMAI V9", "6. El dashboard y la experiencia de uso", "7. Resultados que merece la pena explicar", "8. Estacionalidad y sensibilidad", "9. Cómo se traduce en decisiones", "10. Validación y reproducibilidad", "11. Alcance ampliado", "12. Límites, ética y trabajo futuro", "13. Conclusión", "Glosario y anexo técnico",
    ]:
        add_text(doc, text, after=7)
    add_text(doc, "La lectura está pensada para una defensa oral. Las referencias a anexos llevan a los documentos técnicos donde se pueden comprobar fuentes, supuestos, versiones y resultados completos.", italic=True)

    # 4 contexto
    page(doc); add_heading(doc, "1. El problema que aborda el proyecto")
    add_text(doc, "Mallorca concentra una oferta turística amplia y dispersa. Esa realidad hace que, para muchas estancias, el coche de alquiler parezca la única alternativa sencilla. El proyecto parte de una idea más práctica que grandilocuente: antes de pedir una infraestructura nueva, conviene saber con datos dónde están las brechas de movilidad y de qué tipo son.")
    add_text(doc, "No todos los problemas se explican por la misma causa. Un alojamiento puede estar cerca de una parada pero tener poca oferta en una fecha concreta. Otro puede disponer de servicio, pero estar mal conectado a pie. Y otro puede tener una buena ruta peatonal, aunque no una alternativa ciclista útil. Separar estas situaciones evita decisiones genéricas.")
    add_bullets(doc, [
        "Para administraciones: ayuda a priorizar comprobaciones de primera y última milla.",
        "Para gestores turísticos: facilita comparar la conectividad sostenible de distintos alojamientos.",
        "Para visitantes: deja preparada la base para recomendar rutas reales, no estimaciones abstractas.",
    ])
    source_ref(doc, "Contexto, fuentes y alcance: véanse Anexos B y J.")

    # 5 objetivos
    page(doc); add_heading(doc, "2. Objetivos y personas a las que sirve")
    add_text(doc, "El objetivo general es analizar la accesibilidad turística sostenible entre alojamientos, destinos y redes de movilidad de Mallorca de una forma actualizable y comprensible. El proyecto se diseñó para que la parte técnica quede detrás de una lectura clara, sin esconderla.")
    add_table(doc, ["Objetivo", "Cómo se resuelve"], [
        ["Integrar información dispersa", "Unifica alojamientos, destinos, red de calles, bicicleta, paradas y horarios en una misma cadena de datos."],
        ["Calcular accesibilidad real", "Usa OpenTripPlanner para recorrer la red a pie, en bicicleta y en transporte público."],
        ["Crear una lectura sencilla", "Resume siete señales de movilidad en el TSMAI V9, que conserva el detalle de cada componente."],
        ["Apoyar decisiones", "Presenta mapas, filtros y fichas para revisar casos antes de plantear una intervención."],
        ["Mantener trazabilidad", "Versiona las fuentes, los escenarios y los controles de calidad para poder regenerar el análisis."],
    ], [5.2, 10.0])
    add_text(doc, "La inteligencia artificial no se usa para inventar resultados. Cuando aparece, se limita a capacidades auxiliares y documentadas, como la futura interpretación de reseñas con licencia adecuada. El cálculo principal sigue reglas explícitas y verificables.")
    source_ref(doc, "Arquitectura y alcance: véanse Anexos C, H e I.")

    # 6 datos
    page(doc); add_heading(doc, "3. Datos y fuentes")
    add_text(doc, "La plataforma se apoya en datos abiertos, datos oficiales o fuentes con una licencia declarada. Cada conjunto tiene una función concreta: unos sitúan objetos en el mapa, otros describen horarios y otros aportan contexto. No se mezclan como si todos midieran lo mismo.")
    add_table(doc, ["Fuente", "Aporta", "Uso principal"], [
        ["Registro CAIB", "Alojamientos oficiales", "Unidad de análisis del índice."],
        ["GTFS TIB", "Paradas y calendarios", "Servicio de transporte público y escenarios temporales."],
        ["OpenStreetMap", "Red y destinos", "Evidencia peatonal, ciclista y puntos de interés."],
        ["OpenTripPlanner", "Rutas por red", "Itinerarios WALK, BICYCLE y TRANSIT."],
        ["IGN, AEMET, CAIB y DGT", "Capas de contexto", "Pendiente, clima, aire y seguridad; no entran en TSMAI V9."],
    ], [3.5, 5.0, 6.7])
    add_text(doc, "Una regla clave del proyecto es no convertir una etiqueta de mapa en una certeza física. Por ejemplo, una ciclovía en OpenStreetMap es evidencia cartográfica, pero no certifica continuidad, estado ni seguridad. Esa cautela es parte del resultado, no una nota al margen.")
    source_ref(doc, "Inventario, licencias y trazabilidad: véanse Anexo B y Anexo J.")

    # 7 proceso
    page(doc); add_heading(doc, "4. Cómo se transforma un mapa en evidencia")
    add_text(doc, "El proceso se puede resumir en ocho pasos. Aunque por dentro hay tareas de datos y cartografía, la lógica es bastante directa: reunir fuentes, limpiarlas, calcular opciones de desplazamiento y presentar lo que se ha encontrado sin perder el rastro de origen.")
    add_table(doc, ["Paso", "Qué ocurre", "Resultado"], [
        ["1", "Se recogen y auditan las fuentes.", "Datos con origen y fecha de referencia."],
        ["2", "Se validan geometrías y se normalizan campos.", "Alojamientos y destinos listos para análisis."],
        ["3", "Se prepara la red de movilidad.", "Base para itinerarios reales."],
        ["4", "Se ejecutan rutas por modo y escenario.", "Evidencia WALK, BICYCLE y TRANSIT."],
        ["5", "Se calculan las señales del índice.", "Puntuaciones explicables por alojamiento."],
        ["6", "Se prueban pesos alternativos.", "Sensibilidad de las prioridades."],
        ["7", "Se publican capas y fichas en el dashboard.", "Exploración para perfiles no técnicos."],
        ["8", "Se verifican contratos y resultados finales.", "Entrega reproducible y auditable."],
    ], [1.2, 7.2, 6.8])
    source_ref(doc, "Proceso reproducible y motor de rutas: véanse Anexos C, D y H.")

    # 8 índice
    page(doc); add_heading(doc, "5. El índice TSMAI V9")
    add_text(doc, "TSMAI significa Tourism Sustainable Mobility and Accessibility Index. En términos sencillos, es una forma de reunir siete señales de movilidad en una puntuación entre 0 y 1. Cuanto mayor es la puntuación, más favorable es la evidencia disponible para desplazarse de forma sostenible desde ese alojamiento.")
    add_table(doc, ["Familia", "Componentes", "Peso"], [
        ["Transporte público", "Proximidad a parada, servicio GTFS y ruta TRANSIT estacional", "40 %"],
        ["Caminabilidad", "Evidencia peatonal y ruta WALK calculada por red", "40 %"],
        ["Bicicleta", "Evidencia ciclista y ruta BICYCLE calculada por red", "20 %"],
    ], [3.6, 9.0, 2.6])
    add_text(doc, "El valor del índice no está en reducir un territorio a un número, sino en poder abrirlo. La ficha de un alojamiento muestra sus componentes, por lo que una puntuación baja puede revisarse: ¿falla la cercanía a la parada, el calendario, la ruta a pie o la evidencia ciclista?")
    add_bullets(doc, [
        "Favorable: evidencia más sólida de conectividad sostenible.",
        "Intermedio: situación aceptable, con espacio para mejorar o revisar.",
        "Prioridad de mejora: cartera de casos donde conviene mirar primero.",
    ])
    source_ref(doc, "Fórmula, pesos y versiones: véase Anexo A.")

    # 9 dashboard
    page(doc); add_heading(doc, "6. El dashboard y la experiencia de uso")
    add_text(doc, "La parte visible del proyecto está pensada como una conversación guiada con los datos. En vez de obligar a interpretar una tabla técnica, el usuario puede seguir una secuencia sencilla: localizar un caso, contrastarlo y revisar su evidencia.")
    add_table(doc, ["Pantalla", "Para qué sirve"], [
        ["Resumen de decisión", "Resume el universo, las prioridades y las brechas principales."],
        ["Ficha de intervención", "Explica un alojamiento concreto y sus componentes."],
        ["Análisis territorial", "Muestra el mapa, filtros y comparaciones por municipio."],
        ["Zonas de interés", "Agrupa destinos para facilitar la lectura territorial."],
        ["Consulta guiada", "Responde preguntas con reglas deterministas sobre datos publicados."],
        ["Validación técnica", "Permite comprobar casos de referencia del motor de rutas."],
        ["Planificador", "Compara alternativas reales a pie, bici, transporte público y coche."],
    ], [4.0, 11.2])
    add_text(doc, "La interfaz no es una caja negra. Conserva filtros, fechas y capas para que cada conclusión se pueda volver a situar en el mapa y verificar con mayor detalle.")
    source_ref(doc, "Uso de filtros y paneles: véase Anexo K.")

    # 10 resultados
    page(doc); add_heading(doc, "7. Resultados que merece la pena explicar")
    add_text(doc, "El universo actual del índice reúne 1.461 alojamientos oficiales con geometría válida. La puntuación media de TSMAI V9 es 0,625, pero la media no es el mensaje principal: lo interesante es que la conectividad no se distribuye de manera uniforme y el sistema permite localizar esa desigualdad.")
    add_figure(doc, "01_niveles_tsmai_v9.png", "Figura 1. Distribución de niveles TSMAI V9. Fuente: entrega validada del proyecto, 17-09-2026.", 15.0)
    add_text(doc, "719 alojamientos quedan en nivel favorable, 570 en nivel intermedio y 172 en prioridad de mejora. Esta última cifra debe leerse como un punto de partida para revisión técnica, no como un diagnóstico definitivo de mala accesibilidad.")
    source_ref(doc, "Resultado vigente y capas P7: véanse Anexos A y H.")

    # 11 seasonal
    page(doc); add_heading(doc, "8. El hallazgo estacional")
    add_text(doc, "La versión V9 introduce una mejora importante: el transporte público no se comprueba en una sola fecha. El componente TRANSIT combina cuatro escenarios de verano y cuatro de invierno dentro del mismo GTFS versionado. Así se evita presentar una fotografía puntual como si fuese la realidad de todo el año.")
    add_figure(doc, "02_transit_estacional_v9.png", "Figura 2. Comparación del componente TRANSIT en verano e invierno. Fuente: entrega validada del proyecto.", 15.0)
    add_text(doc, "La media del componente TRANSIT es 0,4291 en verano y 0,0137 en invierno. 793 alojamientos empeoran bajo la regla definida y 668 no cambian. El resultado describe disponibilidad programada para las fechas consultadas; no mide puntualidad, ocupación, tarifa ni demanda real.")
    source_ref(doc, "Escenarios y lectura correcta: véase Anexo A.")

    # 12 sensitivity
    page(doc); add_heading(doc, "9. ¿Cambian las conclusiones si cambian los pesos?")
    add_text(doc, "Un índice siempre obliga a tomar decisiones sobre qué pesa más. En lugar de ocultarlas, el proyecto las publica y las somete a estrés. La sensibilidad recalcula TSMAI V9 con cinco combinaciones de pesos, usando los mismos siete componentes reales.")
    add_figure(doc, "03_sensibilidad_tsmai_v9.png", "Figura 3. Sensibilidad de los niveles y estabilidad de los rankings. Fuente: entrega validada del proyecto.", 15.0)
    add_text(doc, "625 alojamientos mantienen su nivel en los cinco escenarios y 836 cambian al menos una vez. Entre las prioridades del decil superior, 110 aparecen en esa posición en cuatro de los cinco escenarios. Esto no prueba causalidad, pero ayuda a distinguir señales más estables de las que dependen mucho de una elección normativa.")
    source_ref(doc, "Detalle de escenarios y correlaciones: véase Anexo A.")

    # 13 territorial reading
    page(doc); add_heading(doc, "10. Leer el territorio sin simplificarlo")
    add_text(doc, "La capa territorial P7 reúne los 1.461 alojamientos del índice con 772 paradas GTFS, 4.487 destinos OSM temáticos y 1.421 evidencias ciclistas OSM. Este contexto permite pasar de una cifra global a una pregunta localizada: qué combina un alojamiento concreto, qué le falta y qué alternativas tienen sentido explorar.")
    add_table(doc, ["Distancia euclídea a la parada", "Alojamientos", "Uso correcto"], [
        ["0 a 400 m", "885", "Cribado territorial inicial."],
        ["400 a 800 m", "267", "Señal de accesibilidad cercana; no equivale a un itinerario real."],
        ["800 a 1.200 m", "42", "Casos donde conviene comprobar la red a pie."],
        ["Más de 1.200 m", "267", "Posible brecha de primera o última milla."],
    ], [4.5, 3.0, 7.7])
    add_text(doc, "La distancia a una parada es útil para explorar el mapa, pero no sustituye una ruta a pie por red. Por eso el proyecto separa la proximidad de los cálculos WALK, BICYCLE y TRANSIT de OpenTripPlanner.")
    source_ref(doc, "Capas actuales, rutas y criterios: véanse Anexos A, D y K.")

    # 14 decisions
    page(doc); add_heading(doc, "11. De los resultados a una decisión razonada")
    add_text(doc, "El proyecto no recomienda construir una parada, una acera o un carril bici de forma automática. Lo que hace es reducir una lista enorme de posibilidades a una cartera más manejable de casos que necesitan contraste técnico. Esa diferencia es importante: un mapa puede señalar dónde mirar; la decisión pública necesita más evidencia.")
    add_table(doc, ["Señal observada", "Pregunta que abre", "Siguiente comprobación"], [
        ["Prioridad de mejora", "¿Qué componente arrastra la puntuación?", "Abrir la ficha y revisar evidencia por componente."],
        ["Brecha a parada", "¿El problema es distancia o el camino?", "Comprobar ruta WALK y barreras de primera milla."],
        ["Caída invernal", "¿Se concentra en fechas o zonas?", "Contrastar calendarios, frecuencias y necesidad estacional."],
        ["Prioridad robusta", "¿La señal se mantiene con otros pesos?", "Programar validación de campo y consulta institucional."],
    ], [3.2, 6.2, 5.8])
    add_text(doc, "Esta forma de trabajar da un papel útil al análisis: no sustituye a la planificación, sino que la hace más transparente y más fácil de justificar.")
    source_ref(doc, "Recomendaciones y protocolo de contraste: véanse Anexos F y H.")

    # 15 validation
    page(doc); add_heading(doc, "12. Validación y reproducibilidad")
    add_text(doc, "En un proyecto de datos, una visualización atractiva no basta. Cada resultado debe poder localizarse en una fuente, repetirse con los mismos insumos y someterse a controles. Por eso la entrega guarda snapshots, informes de ejecución y pruebas automatizadas.")
    add_table(doc, ["Control", "Resultado comprobado"], [
        ["Puntos de entrada", "43 de 43 tareas importan sin ejecutarse."],
        ["Índice final", "1.461 alojamientos y puntuación media 0,625."],
        ["Sensibilidad", "Cinco escenarios sobre los mismos siete componentes."],
        ["Capas del dashboard", "Universo, paradas, destinos y evidencia ciclista coherentes."],
        ["Interfaz Streamlit", "Contrato de datos verificado."],
        ["Pruebas automatizadas", "Suite completa superada en la validación final."],
    ], [5.2, 10.0])
    add_text(doc, "La regeneración final se limitó a fases derivadas ya versionadas. No se presentó como una nueva observación el rebarrido de rutas que requeriría una fecha, servicio activo y ejecución específica. Esta distinción protege la honestidad del experimento.")
    source_ref(doc, "Evidencia de validación y guía de reproducción: véase Anexo H.")

    # 16 extended
    page(doc); add_heading(doc, "13. Alcance ampliado y capacidades preparadas")
    add_text(doc, "El proyecto también deja preparadas líneas de trabajo que pueden enriquecer el análisis, aunque no forman parte del resultado TSMAI V9. Se han mantenido separadas para no mezclar evidencia con niveles de cobertura distintos.")
    add_table(doc, ["Línea", "Aporta", "Estado y cautela"], [
        ["Sentimiento", "Lectura agregada de reseñas sobre movilidad.", "Requiere corpus autorizado; no identifica la experiencia de cada alojamiento oficial."],
        ["Accesibilidad universal", "Evidencia OSM y GTFS de elementos accesibles.", "Experimental; no sustituye una auditoría física certificada."],
        ["Emisiones", "Comparaciones orientativas de rutas de muestra.", "No estima demanda turística ni forma parte del índice vigente."],
        ["Clima y calidad del aire", "Contexto para interpretar trayectos.", "No se atribuyen a una ruta individual ni se incorporan a TSMAI V9."],
    ], [3.3, 5.4, 6.5])
    source_ref(doc, "Alcance extendido, datos y condiciones: véanse Anexos I y J.")

    # 17 limits
    page(doc); add_heading(doc, "14. Límites y consideraciones éticas")
    add_text(doc, "La principal garantía del proyecto es decir con claridad qué puede concluirse y qué no. El índice es una herramienta de apoyo; no representa viajes observados, calidad percibida, seguridad vial certificada ni impacto causal de una inversión.")
    add_bullets(doc, [
        "Los datos OSM y GTFS son snapshots: cambian con el tiempo y pueden estar incompletos.",
        "Los escenarios de transporte no son un promedio anual ni incluyen ocupación o puntualidad.",
        "No se certifican continuidad física, iluminación, firme, seguridad por tramo o accesibilidad universal.",
        "Las prioridades son una cartera de contraste, nunca una sustitución de la consulta pública o el análisis técnico de obra.",
        "El tratamiento de reseñas se plantea en agregado y con atención a licencia, privacidad y tamaño de muestra.",
    ])
    add_text(doc, "Convertir límites en parte visible de la interfaz ayuda a que el análisis se use con prudencia. También protege a los grupos afectados por decisiones apresuradas basadas solo en una puntuación.")
    source_ref(doc, "Límites metodológicos y gobernanza: véanse Anexos A, I y J.")

    # 18 future
    page(doc); add_heading(doc, "15. Trabajo futuro")
    add_text(doc, "El proyecto queda preparado para crecer sin perder coherencia. Las siguientes mejoras no son adornos: responden a las limitaciones que el propio análisis ha hecho visibles.")
    add_table(doc, ["Prioridad", "Siguiente paso", "Por qué importa"], [
        ["1", "Validación de campo de una muestra de casos.", "Contrasta la cartografía y las rutas con la experiencia de primera y última milla."],
        ["2", "Datos de demanda, ocupación y puntualidad.", "Permite pasar de servicio programado a desempeño observado."],
        ["3", "Auditoría de accesibilidad universal.", "Sustituye evidencia documental por condiciones físicas verificadas."],
        ["4", "Actualizaciones programadas de GTFS y OSM.", "Mantiene el sistema útil cuando cambia el territorio o el servicio."],
        ["5", "Ampliar el corpus autorizado de reseñas.", "Mejora la lectura agregada de la experiencia de movilidad."],
    ], [1.5, 7.2, 6.5])
    source_ref(doc, "Protocolo de validación y operación del producto: véanse Anexos F, H e I.")

    # 19 conclusion glossary
    page(doc); add_heading(doc, "16. Conclusión")
    add_text(doc, "La aportación del TFM no es solo un mapa ni una puntuación. Es una forma reproducible de convertir datos abiertos, rutas reales y horarios oficiales en una conversación más informada sobre movilidad turística. El resultado vigente, TSMAI V9, permite detectar dónde conviene revisar la conexión sostenible de los alojamientos y explicar por qué.")
    add_text(doc, "El proyecto funciona mejor cuando se utiliza como lo que es: una herramienta para priorizar investigación y abrir decisiones, no para cerrarlas. Su trazabilidad, la separación de resultados vigentes y exploratorios, y la explicitación de límites son tan importantes como la tecnología que hay detrás.")
    add_heading(doc, "Glosario breve", 2)
    add_table(doc, ["Término", "En palabras sencillas"], [
        ["TSMAI", "Puntuación explicable de accesibilidad sostenible por alojamiento."],
        ["GTFS", "Formato de datos con paradas y horarios oficiales de transporte público."],
        ["OpenTripPlanner", "Motor que calcula rutas reales sobre calles, red ciclista y servicios."],
        ["Sensibilidad", "Comprobación de si el resultado cambia cuando cambian los pesos."],
        ["Snapshot", "Versión fechada de una fuente de datos, útil para poder repetir el análisis."],
    ], [4.2, 11.0])

    # 20 Annex guide
    page(doc); add_heading(doc, "Anexo técnico de referencia")
    add_text(doc, "Las referencias del texto apuntan a la documentación técnica del repositorio. Esta relación facilita que el tribunal pueda profundizar en una decisión concreta sin sobrecargar la memoria de defensa.")
    add_table(doc, ["Anexo", "Contenido", "Documentos de referencia"], [
        ["A", "TSMAI V9, pesos y versiones", "TSMAI_METODOLOGIA_VERSIONADA.md; JUSTIFICACION_PESOS_TSMAI_V9.md"],
        ["B", "Fuentes y licencias", "FUENTES_Y_LICENCIAS.md; inventario_datos.csv"],
        ["C", "Preparación y extracción", "DATA_PREPARATION.md; DATA_EXTRACTION.md"],
        ["D", "Rutas y OpenTripPlanner", "OTP_ROUTING.md; opentripplanner_local.md"],
        ["E", "Prioridad multimodal histórica", "indice_prioridad_multimodal.md"],
        ["F", "Recomendaciones de intervención", "recomendaciones_intervencion.md"],
        ["G", "Impacto ambiental exploratorio", "impacto_ambiental_rutas_multimodales.md"],
        ["H", "Validación y reproducibilidad", "VALIDACION_FINAL_ENTREGA_V9.md; REPRODUCIBILIDAD_OPERATIVA.md"],
        ["I", "Alcance extendido", "ALCANCE_EXTENDIDO.md"],
        ["J", "Gobernanza de datos", "DATA_GOVERNANCE_V2.md"],
        ["K", "Uso del dashboard", "GUIA_FILTROS_USUARIO.md; dashboard_streamlit.md"],
    ], [1.2, 5.1, 9.0])
    add_text(doc, "Fin del documento.", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=10)

    enrich_narrative(doc)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
