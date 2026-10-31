# Módulos

El código vive en tres carpetas independientes en la raíz del repositorio. Cada una resuelve una parte del flujo y puede probarse por separado.

| Carpeta | Responsabilidad | Pasos del flujo |
| --- | --- | --- |
| `recorte_tarjetas` | Recortar cada tarjeta a partir de las fotografías. | 3 |
| `ocr_dpi_guatemala` | Leer los datos de cada cara con OCR local. | 5 |
| `rpa_dpi` | Validar lo leído, leer el listado CADER y decidir el emparejamiento. | 6, 7, 10 |

La lógica de negocio está en Python para que el orquestador (UiPath) pueda sustituirse sin reescribir las reglas.

## recorte_tarjetas

Recorta las tarjetas de las fotos por lote. Usa RapidOCR sobre `onnxruntime` (con `pyclipper` y `Shapely`).

- Dependencias: `recorte_tarjetas/requirements.txt`.
- Todavía no tiene pruebas automáticas; se verifica a mano con imágenes de prueba.

## ocr_dpi_guatemala

Lee los datos de cada cara con Tesseract (idioma español) y OpenCV. La función `extract()` del archivo `ocr_dpi.py` devuelve un diccionario con el CUI, los candidatos a CUI, el nombre y las líneas crudas de la zona inferior del reverso.

- Dependencias: `ocr_dpi_guatemala/requirements.txt`. Requiere **Tesseract OCR** con el idioma `spa`, que se instala aparte (ver [Instalación](instalacion.md)).
- No separa los campos de la zona inferior: entrega las líneas como texto. De ahí parte `rpa_dpi/mrz.py`.
- Las fechas de nacimiento y vencimiento se leen hoy del texto impreso del reverso, no de la zona inferior.
- Todavía no tiene pruebas automáticas.

## rpa_dpi

Capa de datos y validaciones. Recibe texto ya leído por el OCR; no procesa imágenes. Se ejecuta siempre desde la raíz del repositorio.

### `cui.py`

| Función | Para qué sirve |
| --- | --- |
| `normalize_cui` | Normaliza el CUI a 13 dígitos. Limpia espacios y sufijos como `,00`. Si no resultan 13 dígitos, devuelve `None` en lugar de adivinar. |
| `cui_mod11_ok` | Comprueba el dígito de la posición 9 del CUI. |
| `check_digit_731`, `verify_group` | Dígitos de verificación del método 7-3-1 de la zona inferior del reverso. |
| `reconstruct_cui` | Reconstruye el CUI de 13 dígitos desde el CUI de 14 del reverso, quitando el dígito extra de la posición 10. |
| `estado_vigencia` | Devuelve VIGENTE, VENCIDO o PENDIENTE. El último día de vigencia cuenta como vigente. |
| `validar_par` | Aplica la regla de emparejamiento de las dos caras y devuelve si el par es válido, con los motivos y avisos. |

La zona horaria usada es `America/Guatemala`. En Windows requiere el paquete `tzdata`, que está en `rpa_dpi/requirements.txt`.

### `mrz.py`

`parse_mrz(lines)` recibe la lista de líneas de la zona inferior que entrega `ocr_dpi.py` y devuelve el CUI de 13 o 14 dígitos, el nacimiento y el vencimiento (con su dígito), el sexo y el nombre.

- Supone un diseño de tres líneas tipo ICAO. **Ese formato está pendiente de confirmar con fotos reales.**
- Reconoce cada línea por su contenido, no por su posición.
- No adivina: si una línea no coincide con lo esperado, deja en `None` los campos de esa línea.
- Corrige confusiones típicas del OCR (O y Q por 0; I, L y | por 1) solo en los campos numéricos. Tolera que el marcador `IDGTM` se lea como `1DGTM`.
- No valida los dígitos de verificación; eso lo hace `cui.py`.

### `listado.py`

Lee el libro maestro CADER en modo solo lectura y busca a una persona por CUI exacto. El resultado de la búsqueda es uno de:

| Resultado | Significado |
| --- | --- |
| `UNICA` | Una sola coincidencia. |
| `SIN_COINCIDENCIA` | El CUI no está en el listado. |
| `MULTIPLE` | Más de una fila con ese CUI. |
| `CUI_INVALIDO` | El CUI de entrada no tiene 13 dígitos. |

Además genera un **informe de calidad del libro** (CUI con formato dudoso, repetidos, resúmenes desfasados) que no incluye nombres ni CUI, solo la comunidad, el número de fila y el tipo de problema.

```
python -m rpa_dpi.listado <libro.xlsx>
```

## Cómo se conectan

```
foto -> recorte_tarjetas -> ocr_dpi_guatemala -> rpa_dpi (mrz -> cui -> listado) -> decisión
```

**Estado de la integración:** las tres partes todavía no se llaman entre sí. Falta un paso que tome la salida del OCR de cada cara, la pase por `parse_mrz`, llame a `validar_par` y consulte el listado. Es el siguiente trabajo del proyecto.

## Hallazgo de la prueba preliminar

En una prueba con una foto real comprimida por WhatsApp, el OCR leyó el nombre de la zona inferior pero no sus dos líneas numéricas (CUI, nacimiento y vencimiento). La causa más probable es la calidad de la imagen en esa franja. Conviene probar con fotos originales sin comprimir antes de ajustar el código.

## Pruebas

Las pruebas de `rpa_dpi` usan solo datos sintéticos y cubren la normalización del CUI, los dígitos de verificación, la vigencia, el emparejamiento, la lectura de la zona inferior y la lectura del libro. Ver [Instalación](instalacion.md) para ejecutarlas.
