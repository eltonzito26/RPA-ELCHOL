# Flujo del proceso

El proceso corre por lote, una vez por semana (por defecto, los **lunes a las 6:00 a. m.**, hora de Guatemala; el horario es configurable). Cada archivo se procesa de forma aislada, de modo que un fallo individual no detiene el lote.

## Los 14 pasos

| Paso | Acción del robot | Si algo falla |
| --- | --- | --- |
| 1. Iniciar lote | Lee la configuración, comprueba el acceso a las carpetas y al libro, y verifica que no haya otra ejecución activa. Aplica las decisiones que el operador dejó en el libro de decisiones. | Si hay bloqueo o no se puede leer el Excel, no inicia ninguna escritura. |
| 2. Detectar entradas | Identifica los archivos nuevos y su comunidad. Calcula el hash de cada archivo y lo compara con el historial. | Una copia exacta se omite y se registra. |
| 3. Preparar la imagen | Orienta, recorta y mejora el contraste, conservando el original. | Imagen ilegible: revisión. |
| 4. Clasificar la cara | Detecta si es anverso o reverso. | Baja confianza: revisión manual. |
| 5. Leer con OCR | OCR local. Anverso: CUI, nombre y fecha de nacimiento. Reverso: zona inferior (CUI, nacimiento, vencimiento y dígitos de verificación). | Dato faltante o dudoso: no continúa automáticamente. |
| 6. Validar las lecturas | Comprueba los formatos y los dígitos de verificación. | Falla: revisión, con el motivo registrado. |
| 7. Emparejar y buscar en CADER | Agrupa anverso y reverso, y busca el CUI exacto en el listado. | Par dudoso, cero coincidencias o varias: revisión manual. |
| 8. Comprobar el par completo | Verifica que estén las dos caras. | Falta una: estado *Incompleto*; se indica ANVERSO o REVERSO y se retienen las fotos. |
| 9. Consultar estado y PDF previo | Por CUI: estado VA/FALTA y existencia de un PDF anterior. | VA sin archivo, archivo dañado o que no corresponde: *Discrepancia*, a revisión. |
| 10. Evaluar vigencia | Lee el vencimiento de la entrada y del PDF previo y lo compara con la fecha local. | Fecha ilegible o fuentes distintas: PENDIENTE. |
| 11. Decidir | Aplica las [reglas de decisión](reglas-de-decision.md). | Con un PDF previo vigente, pasa al operador para elegir. |
| 12. Crear y verificar el PDF | PDF de una página carta: anverso arriba, reverso abajo. Nombre: *Nombre Completo*.pdf. Lo archiva en la carpeta de la comunidad (CADER o NO CADER). | Nunca sobrescribe: si el nombre choca, agrega un sufijo. Un fallo es un error técnico. |
| 13. Actualizar el libro | Trabaja sobre una copia local. Marca VA solo tras verificar el PDF y registra faltantes, vigencias y versiones en la hoja Revisión. Comprueba que los totales cuadren. | Si los totales no cuadran, no publica. |
| 14. Publicar y limpiar | Confirma la sincronización con Drive, traslada al respaldo las fotos de los casos completos y borra del respaldo lo que superó 30 días. | Con una cara faltante o un error, las fotos se retienen en la carpeta de entrada. |

## Dónde interviene una persona

El robot automatiza lo mecánico. Una persona decide en estos casos:

- **Casos dudosos:** OCR dudoso, dígito de verificación inválido, CUI distinto entre las dos caras, cero o varias coincidencias.
- **Elección de versión:** cuando ya existe un PDF vigente de la persona, el supervisor indica su preferencia y el operador la registra.
- **NO CADER:** cuando el CUI no está en el listado, el operador elige la opción y la comunidad.
- **Discrepancias:** estado VA sin archivo, o archivo dañado.

El operador registra sus decisiones en un **libro de decisiones** aparte, que el robot lee al iniciar el siguiente lote. Por eso cada decisión se aplica, como mínimo, en el lote siguiente.

## Estados de un caso

| Estado | Significado |
| --- | --- |
| **VA** | El PDF quedó creado, verificado y registrado como completo. Un DPI vencido también puede quedar en VA, con la marca VENCIDO en la hoja Revisión. |
| **FALTA** | Sin PDF todavía. |
| **Incompleto** | Solo llegó una de las dos caras. |
| **Revisión manual** | Hay un dato dudoso o una excepción. |
| **Discrepancia** | El Excel y los archivos no coinciden. |
| **Error técnico** | Falló Excel, Drive, OCR o la generación del PDF. |

## Seguridad al escribir

- El robot trabaja siempre sobre una copia local del libro y solo publica si los totales cuadran.
- Antes de reemplazar el libro en Drive, guarda una copia del anterior (últimas 8 semanas).
- Si el libro en Drive cambió durante el lote, no lo sobrescribe: guarda el resultado con otro nombre y avisa.
- El PDF final nunca se borra automáticamente.
