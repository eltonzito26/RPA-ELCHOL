# rpa_dpi — capa de datos y validaciones

Lógica de negocio en Python (independiente de UiPath).

El paquete vive en `rpa_dpi/`. Ejecuta todo desde la raíz del repositorio:

    pip install -r rpa_dpi/requirements.txt
    python -m unittest discover -s rpa_dpi/tests -t . -v      # pruebas (datos sintéticos)
    CADER_XLSX=<libro.xlsx> python -m unittest discover -s rpa_dpi/tests -t .   # + libro real
    python -m rpa_dpi.listado <libro.xlsx>                    # informe de calidad (sin nombres ni CUI)

- `cui.py`: normalizar CUI, dígito de la posición 9 (mod 11), 7-3-1 de la zona del reverso,
  reconstrucción del CUI del reverso, vigencia (VIGENTE/VENCIDO/PENDIENTE) y `validar_par()`
  (regla de emparejamiento de la sección 4). Recibe texto ya leído por el OCR.
- `listado.py`: carga el libro maestro (solo lectura) y busca por CUI exacto
  (UNICA / SIN_COINCIDENCIA / MULTIPLE / CUI_INVALIDO).

Pendiente de confirmar con la salida real del OCR (Sprint 1, T3): el formato exacto de la
zona inferior del reverso (separadores, relleno '<') para armar los argumentos de `validar_par()`.
