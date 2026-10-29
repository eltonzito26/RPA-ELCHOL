import os
import re
import json
from PIL import Image
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import win32com.client as win32

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# Expresiones regulares para detectar si el nombre indica reverso o anverso al final
PATRON_REVERSO = re.compile(
    r"[\s_\-\(\[]*(reverso|atras|atrás|dorso|cara\s*2|lado\s*b)[\s_\-\)\]]*$",
    re.IGNORECASE
)
PATRON_ANVERSO = re.compile(
    r"[\s_\-\(\[]*(anverso|frente|frontal|adelante|cara\s*1|lado\s*a)[\s_\-\)\]]*$",
    re.IGNORECASE
)


def analizar_nombre_imagen(nombre_archivo: str) -> tuple[str, str]:
    """Separa el nombre completo de la persona y detecta la cara."""
    base, _ = os.path.splitext(nombre_archivo)
    base_limpia = base.replace("_", " ").strip()

    if PATRON_REVERSO.search(base_limpia):
        nombre_persona = PATRON_REVERSO.sub("", base_limpia).strip(" -_()[]")
        cara = "reverso"
    elif PATRON_ANVERSO.search(base_limpia):
        nombre_persona = PATRON_ANVERSO.sub("", base_limpia).strip(" -_()[]")
        cara = "anverso"
    else:
        nombre_persona = base_limpia.strip(" -_()[]")
        cara = "sin_etiqueta"

    nombre_persona = " ".join(nombre_persona.split())
    if nombre_persona.isupper() or nombre_persona.islower():
        nombre_persona = nombre_persona.title()

    return nombre_persona, cara


def calcular_dimensiones_carta(ruta_imagen: str, max_ancho_pulg=5.4, max_alto_pulg=4.3) -> tuple[float, float]:
    """Ajusta proporción para que ambas caras quepan holgadamente en 1 página tamaño carta."""
    with Image.open(ruta_imagen) as img:
        ancho_px, alto_px = img.size

    proporcion = ancho_px / alto_px
    ancho_pulg = max_ancho_pulg
    alto_pulg = ancho_pulg / proporcion

    if alto_pulg > max_alto_pulg:
        alto_pulg = max_alto_pulg
        ancho_pulg = alto_pulg * proporcion

    return ancho_pulg, alto_pulg


def crear_docx_dpi(ruta_anverso: str, ruta_reverso: str, ruta_salida_docx: str):
    """Crea el Word vertical tamaño Carta con anverso arriba y reverso abajo."""
    doc = Document()

    seccion = doc.sections[0]
    seccion.page_width = Inches(8.5)
    seccion.page_height = Inches(11.0)
    seccion.top_margin = Inches(0.65)
    seccion.bottom_margin = Inches(0.65)
    seccion.left_margin = Inches(0.75)
    seccion.right_margin = Inches(0.75)

    # Insertar ANVERSO (Arriba)
    ancho_anv, alto_anv = calcular_dimensiones_carta(ruta_anverso)
    p_anverso = doc.add_paragraph()
    p_anverso.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_anverso.paragraph_format.space_before = Pt(6)
    p_anverso.paragraph_format.space_after = Pt(24)
    p_anverso.add_run().add_picture(ruta_anverso, width=Inches(ancho_anv), height=Inches(alto_anv))

    # Insertar REVERSO (Abajo)
    ancho_rev, alto_rev = calcular_dimensiones_carta(ruta_reverso)
    p_reverso = doc.add_paragraph()
    p_reverso.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_reverso.paragraph_format.space_before = Pt(0)
    p_reverso.paragraph_format.space_after = Pt(0)
    p_reverso.add_run().add_picture(ruta_reverso, width=Inches(ancho_rev), height=Inches(alto_rev))

    doc.save(ruta_salida_docx)


def generar_pdfs_desde_carpeta(
    carpeta_imagenes: str,
    carpeta_salida_pdf: str,
    conservar_word: bool = False
) -> str:
    """Agrupa imágenes por persona, genera Word y exporta PDF de 1 página."""
    os.makedirs(carpeta_salida_pdf, exist_ok=True)
    carpeta_temp_word = os.path.join(carpeta_salida_pdf, "_temp_word")
    os.makedirs(carpeta_temp_word, exist_ok=True)

    personas = {}

    for archivo in os.listdir(carpeta_imagenes):
        ruta_completa = os.path.join(carpeta_imagenes, archivo)
        if not os.path.isfile(ruta_completa):
            continue

        _, ext = os.path.splitext(archivo)
        if ext.lower() not in EXTENSIONES_VALIDAS:
            continue

        nombre_limpio, cara = analizar_nombre_imagen(archivo)
        if not nombre_limpio:
            continue

        clave = nombre_limpio.lower()
        if clave not in personas:
            personas[clave] = {
                "nombre_oficial": nombre_limpio,
                "anverso": [],
                "reverso": [],
                "sin_etiqueta": []
            }
        personas[clave][cara].append(ruta_completa)

    resultados = {
        "ok": True,
        "pdfs_creados": [],
        "incompletos": [],
        "errores_o_duplicados": []
    }

    pares_listos = []

    for clave, info in personas.items():
        nombre = info["nombre_oficial"]

        if len(info["anverso"]) == 0 and len(info["sin_etiqueta"]) == 1:
            info["anverso"].append(info["sin_etiqueta"].pop(0))

        if len(info["anverso"]) > 1 or len(info["reverso"]) > 1 or len(info["sin_etiqueta"]) > 0:
            resultados["errores_o_duplicados"].append({
                "persona": nombre,
                "motivo": "MULTIPLES_ARCHIVOS_PARA_MISMA_PERSONA"
            })
            continue

        tiene_anverso = len(info["anverso"]) == 1
        tiene_reverso = len(info["reverso"]) == 1

        if not tiene_anverso or not tiene_reverso:
            cara_faltante = "REVERSO" if tiene_anverso else "ANVERSO"
            resultados["incompletos"].append({
                "persona": nombre,
                "tiene_anverso": tiene_anverso,
                "tiene_reverso": tiene_reverso,
                "cara_faltante": cara_faltante
            })
            continue

        pares_listos.append({
            "nombre": nombre,
            "ruta_anverso": info["anverso"][0],
            "ruta_reverso": info["reverso"][0]
        })

    word_app = None
    if pares_listos:
        try:
            word_app = win32.DispatchEx("Word.Application")
            word_app.Visible = False
            word_app.DisplayAlerts = 0

            for item in pares_listos:
                nombre = item["nombre"]
                ruta_docx = os.path.abspath(os.path.join(carpeta_temp_word, f"{nombre}.docx"))
                ruta_pdf = os.path.abspath(os.path.join(carpeta_salida_pdf, f"{nombre}.pdf"))

                if os.path.exists(ruta_pdf):
                    resultados["errores_o_duplicados"].append({
                        "persona": nombre,
                        "motivo": "PDF_PREVIAMENTE_EXISTENTE"
                    })
                    continue

                doc_word = None
                try:
                    crear_docx_dpi(item["ruta_anverso"], item["ruta_reverso"], ruta_docx)

                    doc_word = word_app.Documents.Open(ruta_docx, ReadOnly=True)
                    doc_word.Repaginate()
                    total_paginas = doc_word.ComputeStatistics(2)

                    if total_paginas != 1:
                        resultados["errores_o_duplicados"].append({
                            "persona": nombre,
                            "motivo": f"PAGINACION_INVALIDA_{total_paginas}_PAGINAS"
                        })
                        continue

                    doc_word.ExportAsFixedFormat(
                        OutputFileName=ruta_pdf,
                        ExportFormat=17,
                        OpenAfterExport=False,
                        OptimizeFor=0
                    )

                    doc_word.Close(SaveChanges=False)
                    doc_word = None

                    if os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 10240:
                        resultados["pdfs_creados"].append({
                            "persona": nombre,
                            "archivo_pdf": f"{nombre}.pdf",
                            "ruta_pdf": ruta_pdf,
                            "pdf_verificado": True
                        })
                    else:
                        resultados["errores_o_duplicados"].append({
                            "persona": nombre,
                            "motivo": "PDF_VACIO_O_CORRUPTO"
                        })

                except Exception as ex:
                    resultados["errores_o_duplicados"].append({
                        "motivo": f"ERROR_TECNICO_{type(ex).__name__}"
                    })
                finally:
                    if doc_word is not None:
                        doc_word.Close(SaveChanges=False)
                    if not conservar_word and os.path.exists(ruta_docx):
                        os.remove(ruta_docx)

        finally:
            if word_app is not None:
                word_app.Quit()

    if not conservar_word and os.path.exists(carpeta_temp_word) and not os.listdir(carpeta_temp_word):
        os.rmdir(carpeta_temp_word)

    return json.dumps(resultados, ensure_ascii=False, indent=2)
