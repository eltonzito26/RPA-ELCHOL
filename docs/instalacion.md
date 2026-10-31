# Instalación

Guía para preparar el entorno de desarrollo en **Windows 10/11**.

> **Datos reales.** No se instalan ni se prueban fotos de DPI reales dentro del repositorio. Las pruebas con documentos reales se hacen solo en una estación autorizada, fuera de la carpeta del proyecto.

## Requisitos

| Requisito | Para qué |
| --- | --- |
| Git | Clonar el repositorio. |
| Python 3 de 64 bits | Código de las tres carpetas. Se verificó con Python 3.14. |
| Tesseract OCR con idioma español | Lectura OCR de `ocr_dpi_guatemala`. |
| Microsoft Excel | Recalcular fórmulas al actualizar el libro (fase de operación). |
| UiPath Studio | Orquestación del flujo (fase posterior; licencia por confirmar). |

## 1. Clonar el repositorio

```
cd $HOME\Documents
git clone https://github.com/eltonzito26/RPA-ELCHOL.git
cd RPA-ELCHOL
```

Al ser un repositorio privado, Git pide iniciar sesión en GitHub la primera vez.

## 2. Instalar Tesseract con español

1. Descarga el instalador de Windows de 64 bits desde la página de UB-Mannheim (wiki del proyecto *tesseract*).
2. En **Additional language data**, marca **Spanish**.
3. Instala en la ruta por defecto: `C:\Program Files\Tesseract-OCR`.
4. Cierra y vuelve a abrir la terminal (y VS Code, si lo usas) para que tome el PATH.
5. Comprueba:

```
tesseract --list-langs
```

Debe mostrar `eng`, `osd` y `spa`.

**Si falta `spa`:** descarga `spa.traineddata` (de `tessdata_fast`) a la carpeta `C:\Program Files\Tesseract-OCR\tessdata`. Esa carpeta requiere permisos de administrador.

**Si el comando `tesseract` no se reconoce:** la carpeta de instalación no está en el PATH. Agrégala a las variables de entorno del usuario y reinicia la terminal. Como alternativa, se puede indicar la ruta con la opción `--tesseract` de los scripts.

## 3. Crear el entorno virtual

```
python -m venv .venv
.venv\Scripts\activate
```

Si Windows bloquea la ejecución de scripts, ejecuta una vez:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 4. Instalar las dependencias

Con el entorno activo, desde la raíz del repositorio:

```
pip install -r rpa_dpi/requirements.txt
pip install -r ocr_dpi_guatemala/requirements.txt
pip install -r recorte_tarjetas/requirements.txt
```

Para evitar conflictos, se usa una sola variante de OpenCV (`opencv-python-headless`) en los tres módulos.

## 5. Ejecutar las pruebas

Siempre desde la raíz del repositorio:

```
python -m unittest discover -s rpa_dpi/tests -t . -v
```

El resultado esperado termina en `OK`. Una de las pruebas se omite a propósito: es la que usa el libro CADER real y solo corre si se define la variable `CADER_XLSX`.

## 6. Informe de calidad del libro (opcional)

Con una copia local del libro CADER, que **nunca** se sube al repositorio:

```
python -m rpa_dpi.listado <ruta-al-libro.xlsx>
```

El informe no imprime nombres ni CUI.

## Problemas frecuentes

| Síntoma | Causa y solución |
| --- | --- |
| `ZoneInfoNotFoundError` | Falta el paquete `tzdata`. Instala `rpa_dpi/requirements.txt`. |
| `tesseract` no se reconoce | Falta el PATH. Ver el paso 2. |
| Solo aparecen `eng` y `osd` | Falta el idioma español. Ver el paso 2. |
| `ModuleNotFoundError` | El entorno virtual no está activo o faltan dependencias. Repite los pasos 3 y 4. |
| Error al instalar una librería con una versión nueva de Python | Algunas librerías tardan en publicar compatibilidad. Usa una versión anterior de Python (por ejemplo, 3.12) para crear el entorno. |
| Los comandos de `unittest` no encuentran las pruebas | Ejecuta desde la raíz del repositorio, no desde dentro de `rpa_dpi`. |
