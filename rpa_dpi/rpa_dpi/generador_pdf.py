import os
import json
import docx
from docx.shared import Cm
import win32com.client

def analizar_nombre_imagen(nombre_archivo):
    # Le quitamos la extensión al archivo (.jpg, .png)
    nombre_sin_extension = os.path.splitext(nombre_archivo)[0]

    # Pasamos todo a minúsculas para que sea más fácil buscar
    texto_minusculas = nombre_sin_extension.lower()

    # Buscamos si es anverso o reverso con un if normal
    cara = ""
    if "anverso" in texto_minusculas:
        cara = "anverso"
    elif "reverso" in texto_minusculas:
        cara = "reverso"
    else:
        cara = "desconocido"

    # Sacamos el nombre de la persona (quitando la palabra anverso/reverso y los guiones)
    # Por ejemplo, pasa de "carlos eduardo gomez - anverso" a "carlos eduardo gomez"
    nombre_limpio = texto_minusculas.replace("anverso", "").replace("reverso", "")
    nombre_limpio = nombre_limpio.replace("-", " ").replace("_", " ").strip()

    # Ponemos la primera letra de cada palabra en mayúscula (Carlos Eduardo Gomez)
    nombre_final = nombre_limpio.title()

    return nombre_final, cara

def generar_pdfs_desde_carpeta(carpeta_entrada, carpeta_salida):
    # Diccionarios y listas para guardar los datos
    personas = {}
    pdfs_creados = []
    incompletos = []

    # 1. Leer todos los archivos de la carpeta de entrada
    for archivo in os.listdir(carpeta_entrada):
        if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
            nombre_persona, cara = analizar_nombre_imagen(archivo)

            # Si la persona no está en el diccionario, la agregamos vacía
            if nombre_persona not in personas:
                personas[nombre_persona] = {"anverso": None, "reverso": None}

            # Guardamos la ruta de la imagen donde corresponde
            ruta_completa = os.path.join(carpeta_entrada, archivo)
            if cara == "anverso":
                personas[nombre_persona]["anverso"] = ruta_completa
            elif cara == "reverso":
                personas[nombre_persona]["reverso"] = ruta_completa

    # 2. Revisar quién tiene las dos caras y armar el PDF
    for persona, imagenes in personas.items():
        foto_anverso = imagenes["anverso"]
        foto_reverso = imagenes["reverso"]

        # Si tiene ambas fotos, armamos el documento Word
        if foto_anverso is not None and foto_reverso is not None:
            documento = docx.Document()
            
            # Ajustamos los márgenes de la hoja a 2 cm
            seccion = documento.sections[0]
            seccion.left_margin = Cm(2)
            seccion.right_margin = Cm(2)
            seccion.top_margin = Cm(2)
            seccion.bottom_margin = Cm(2)

            # Metemos las imágenes al documento con un ancho de 15 cm para que quepan bien
            documento.add_picture(foto_anverso, width=Cm(15))
            documento.add_picture(foto_reverso, width=Cm(15))

            # Guardamos el Word temporalmente
            ruta_word = os.path.join(carpeta_salida, f"{persona}.docx")
            documento.save(ruta_word)

            # Convertimos el Word a PDF usando win32com (simula que abrimos Word en la compu)
            ruta_pdf = os.path.join(carpeta_salida, f"{persona}.pdf")
            word_app = win32com.client.Dispatch("Word.Application")
            word_app.Visible = False # Que no se abra la ventana molestando al usuario
            
            try:
                # Formato 17 es el código interno de Word para exportar a PDF
                doc_abierto = word_app.Documents.Open(ruta_word)
                doc_abierto.SaveAs(ruta_pdf, FileFormat=17)
                doc_abierto.Close()
            except Exception as error:
                print(f"Ocurrió un error con {persona}: {error}")
            finally:
                word_app.Quit()

            # Borramos el archivo Word porque el robot solo necesita el PDF
            if os.path.exists(ruta_word):
                os.remove(ruta_word)

            # Lo agregamos a la lista de PDFs creados exitosamente
            pdfs_creados.append({
                "persona": persona,
                "ruta_pdf": ruta_pdf
            })

        else:
            # Le falta una cara, identificamos cuál es y lo mandamos a la lista de errores
            cara_que_falta = ""
            if foto_anverso is None:
                cara_que_falta = "ANVERSO"
            elif foto_reverso is None:
                cara_que_falta = "REVERSO"

            incompletos.append({
                "persona": persona,
                "cara_faltante": cara_que_falta
            })

    # 3. Armar la respuesta final en formato JSON para que UiPath la entienda
    resultado = {
        "ok": True,
        "pdfs_creados": pdfs_creados,
        "incompletos": incompletos
    }
    
    return json.dumps(resultado, indent=4)