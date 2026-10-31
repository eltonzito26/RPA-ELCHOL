# Recorte automático por lote de DPI

Procesa las fotos localmente en tu computadora. Conserva los originales y crea un recorte PNG por cada foto con un DPI detectado. Los casos dudosos se conservan en `revision`; no se anuncian como recortes finales.

## Instalación

1. Descomprime este ZIP en una carpeta nueva.
2. Ejecuta `instalar_y_abrir.bat`. Instala las dependencias y abre la aplicación.
3. Selecciona la carpeta de fotos y una carpeta distinta para los resultados. Pulsa **Procesar carpeta**.

Se recomienda Python 3.14, 3.13 o 3.12 de 64 bits. Si el programa muestra que `pyclipper` no se puede cargar, instala el runtime de Visual C++ 2015–2022 x64 desde PowerShell con `winget install --id Microsoft.VCRedist.2015+.x64 --exact` y vuelve a ejecutar el `.bat`. No hace falta instalar una extensión de Kiro ni Tesseract.

## Qué cambió

- Busca candidatos con bordes y, por separado, por la gama azul/celeste/verde habitual del DPI. Así puede detectar el marco de la tarjeta cuando la hoja o tela del fondo tiene bordes más fuertes.
- Afina cada uno de los cuatro lados con transiciones de color y luminancia. Prolonga las líneas rectas hasta sus intersecciones para no confundir el comienzo de una esquina redondeada con la esquina geométrica; ayuda especialmente en los bordes superior e izquierdo.
- Penaliza cuadros demasiado grandes y los que llegan al borde de la foto; ese borde suele ser la hoja o una tarjeta parcialmente cortada.
- Corrige perspectiva y deja el lado largo en horizontal. Para decidir entre 0° y 180°, compara texto OCR y la posición del encabezado, la firma y las líneas MRZ. No publica una orientación sin señales de texto ubicadas en sentido coherente.
- Guarda una vista con 8 puntos (esquinas y puntos medios) en `marcas_8_puntos`, para comprobar qué borde detectó.
- Guarda a 85.60 × 53.98 mm, 300 DPI fijos, esquinas redondeadas y fondo transparente. El selector de DPI se quitó porque cambia metadatos/tamaño de impresión, no recupera detalle que no exista en la foto.

Los resultados se guardan en `informe_procesamiento.csv`, `marcas_8_puntos` y `revision`. Revisa siempre los elementos de `revision` y confirma el encuadre final antes de usarlo; reflejos, fondos azulados, desenfoque o bordes tapados pueden confundir cualquier detector automático.
