import os
import sys
import json
import random
import tempfile
import unittest
from PIL import Image, ImageDraw

RUTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if RUTA_BASE not in sys.path:
    sys.path.insert(0, RUTA_BASE)

from rpa_dpi.generador_pdf import analizar_nombre_imagen, generar_pdfs_desde_carpeta


def crear_dpi_sintetico(ruta_archivo: str, texto_cara: str, color_fondo: tuple[int, int, int]):
    """Crea una imagen sintetica con proporcion de DPI y peso realista."""
    ancho, alto = 856, 540
    img = Image.new("RGB", (ancho, alto), color_fondo)
    draw = ImageDraw.Draw(img)

    generador = random.Random(42)
    foto_simulada = Image.frombytes("RGB", (200, 260), generador.randbytes(200 * 260 * 3))
    img.paste(foto_simulada, (50, 140))

    draw.rectangle([20, 20, ancho - 20, alto - 20], outline=(25, 45, 85), width=6)
    draw.text((290, 180), texto_cara, fill=(10, 20, 40))
    draw.text((290, 230), "NOMBRE: CARLOS EDUARDO GOMEZ", fill=(30, 30, 30))
    draw.text((290, 270), "PRUEBA SINTETICA LOCAL - RPA DPI", fill=(60, 60, 60))

    img.save(ruta_archivo, format="JPEG", quality=92)


class TestGeneradorPDF(unittest.TestCase):
    def test_analizar_nombre_imagen(self):
        nombre, cara = analizar_nombre_imagen("carlos_eduardo_gomez_anverso.jpg")
        self.assertEqual(nombre, "Carlos Eduardo Gomez")
        self.assertEqual(cara, "anverso")

        nombre_rev, cara_rev = analizar_nombre_imagen("Carlos Eduardo Gomez - Reverso.png")
        self.assertEqual(nombre_rev, "Carlos Eduardo Gomez")
        self.assertEqual(cara_rev, "reverso")

    def test_generacion_pdf_y_deteccion_incompletos(self):
        with (
            tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as dir_entrada,
            tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as dir_salida,
        ):
            crear_dpi_sintetico(
                os.path.join(dir_entrada, "Carlos Eduardo Gomez - anverso.jpg"),
                "DPI ANVERSO (FRENTE)",
                (225, 238, 250)
            )
            crear_dpi_sintetico(
                os.path.join(dir_entrada, "Carlos Eduardo Gomez - reverso.jpg"),
                "DPI REVERSO (DORSO)",
                (230, 245, 230)
            )

            crear_dpi_sintetico(
                os.path.join(dir_entrada, "Ana Lucia Morales - anverso.jpg"),
                "DPI ANVERSO INCOMPLETO",
                (250, 235, 225)
            )

            respuesta_json = generar_pdfs_desde_carpeta(dir_entrada, dir_salida)
            datos = json.loads(respuesta_json)

            self.assertTrue(datos["ok"])
            self.assertEqual(len(datos["pdfs_creados"]), 1)
            self.assertEqual(datos["pdfs_creados"][0]["persona"], "Carlos Eduardo Gomez")
            self.assertTrue(os.path.exists(datos["pdfs_creados"][0]["ruta_pdf"]))

            self.assertEqual(len(datos["incompletos"]), 1)
            self.assertEqual(datos["incompletos"][0]["persona"], "Ana Lucia Morales")
            self.assertEqual(datos["incompletos"][0]["cara_faltante"], "REVERSO")


if __name__ == "__main__":
    print("1. Ejecutando pruebas automaticas del modulo generador_pdf...")
    programa = unittest.main(exit=False, verbosity=2)

    if programa.result.wasSuccessful():
        carpeta_muestra = os.path.join(tempfile.gettempdir(), "muestra_rpa_dpi")
        dir_imgs = os.path.join(carpeta_muestra, "entrada")
        dir_pdfs = os.path.join(carpeta_muestra, "salida")
        os.makedirs(dir_imgs, exist_ok=True)
        os.makedirs(dir_pdfs, exist_ok=True)

        pdf_previo = os.path.join(dir_pdfs, "Carlos Eduardo Gomez.pdf")
        if os.path.exists(pdf_previo):
            os.remove(pdf_previo)

        crear_dpi_sintetico(
            os.path.join(dir_imgs, "Carlos Eduardo Gomez - anverso.jpg"),
            "DPI ANVERSO (ARRIBA)",
            (225, 238, 250)
        )
        crear_dpi_sintetico(
            os.path.join(dir_imgs, "Carlos Eduardo Gomez - reverso.jpg"),
            "DPI REVERSO (ABAJO)",
            (230, 245, 230)
        )

        resultado = generar_pdfs_desde_carpeta(dir_imgs, dir_pdfs)
        print("\n2. Reporte JSON generado:")
        print(resultado)

        if os.path.exists(pdf_previo):
            print(f"\n3. Abriendo PDF de muestra en pantalla: {pdf_previo}")
            os.startfile(pdf_previo)
