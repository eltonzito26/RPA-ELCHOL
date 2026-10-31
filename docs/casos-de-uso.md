# Casos de uso

## CU-01: Procesar un lote de fotografías de DPI y actualizar el seguimiento

| Campo | Descripción |
| --- | --- |
| **ID** | CU-01 |
| **Nombre** | Procesar lote de fotografías de DPI y actualizar seguimiento |
| **Objetivo** | Procesar de forma supervisada las fotografías de DPI, asociarlas correctamente, generar el PDF cuando corresponda y actualizar el libro maestro de forma trazable. |
| **Actor principal** | Operador del lote |
| **Actores secundarios** | Supervisor lector, responsable del Drive y el robot RPA como sistema automatizado |
| **Disparador** | Inicio del lote programado (lunes 6:00 a. m.) o ejecución autorizada del proceso |
| **Precondiciones** | La estación autorizada está disponible. Existe acceso a la carpeta de entrada, al libro maestro y al libro de decisiones. No hay otra ejecución activa. Las fotografías están organizadas por comunidad. |
| **Postcondición de éxito** | El PDF válido queda archivado cuando aplica. El estado VA se actualiza solo después de la verificación. El libro conserva sus fórmulas y totales. Las fotos completas pasan al respaldo y la publicación queda registrada. |
| **Postcondición alternativa** | Los casos incompletos, dudosos, discrepantes o con error permanecen sin marcar VA y quedan registrados para revisión, sin perder los archivos originales. |

### Flujo principal

1. El robot lee la configuración, el libro maestro y las decisiones pendientes, y confirma que no existe otra ejecución activa.
2. Detecta los archivos nuevos por comunidad y compara su hash con el historial para evitar copias exactas.
3. Prepara cada imagen, clasifica anverso o reverso y ejecuta el OCR local.
4. Valida los formatos, los dígitos de verificación y la coherencia entre ambas caras.
5. Empareja anverso y reverso y busca una coincidencia exacta del CUI en CADER.
6. Comprueba que el par esté completo y consulta el estado VA/FALTA y la existencia de un PDF previo.
7. Evalúa la vigencia del DPI nuevo y, cuando corresponde, la del PDF previo.
8. Aplica las reglas de decisión. Si se requiere una elección humana, el caso pasa al operador.
9. Genera y verifica el PDF de una página, con el anverso arriba y el reverso abajo, y lo archiva en la carpeta correspondiente.
10. Actualiza el libro sobre una copia local, valida los totales y publica solo si la consistencia es correcta.
11. Confirma la sincronización, mueve al respaldo las fotos de los casos completos y registra el resultado del lote.

### Flujos alternativos y excepciones

| Situación | Resultado |
| --- | --- |
| Imagen ilegible, OCR dudoso o dígito de verificación inválido | El caso va a revisión y no continúa automáticamente. |
| Falta el anverso o el reverso | Se registra como incompleto, se conservan las fotos y no se genera PDF final. |
| CUI distinto entre caras, cero coincidencias o varias coincidencias | Revisión manual. No se decide por similitud de nombre. |
| Existe un PDF previo vigente | Se comparan las versiones y el operador registra la decisión indicada por el supervisor. |
| Estado VA sin PDF, archivo dañado o que no corresponde | Se registra una discrepancia y no se sobrescribe. |
| Fecha de vencimiento ilegible o discordante | Vigencia pendiente. No se asume que el DPI está vigente. |
| Fallo de Excel, Drive, OCR o generación del PDF | Se conserva la entrada, no se marca VA y se deja traza del error. |
| El CUI no está en el listado CADER | El operador elige NO CADER y la comunidad. |

## CU-02: Resolver casos de excepción

Caso de uso derivado de las reglas de decisión. Describe la intervención del operador entre dos lotes.

| Campo | Descripción |
| --- | --- |
| **Actor principal** | Operador del lote |
| **Precondición** | El último lote dejó casos en la hoja Revisión. |
| **Flujo principal** | 1. El operador filtra la hoja Revisión por comunidad y tipo de caso. 2. Revisa cada caso con el motivo registrado. 3. En el libro de decisiones elige, con listas desplegables, la versión elegida, CADER o NO CADER y la comunidad. 4. En el siguiente lote, el robot lee esas decisiones y las aplica. |
| **Postcondición** | Los casos resueltos salen de la cola; los que siguen dudosos permanecen. |
| **Excepción** | Si una fila del libro de decisiones está incompleta, el robot la ignora y la deja pendiente. |

## CU-03: Consultar el avance

| Campo | Descripción |
| --- | --- |
| **Actor principal** | Supervisor lector |
| **Precondición** | El supervisor está en la lista nominal de accesos autorizados. |
| **Flujo principal** | 1. Abre el libro en Drive. 2. Elige una comunidad o el total municipal en el Panel Interactivo. 3. Revisa el avance y, si lo necesita, abre el PDF de una persona en pantalla. 4. Si hay dos versiones de un DPI, indica su preferencia al operador. |
| **Restricciones** | No puede descargar, imprimir, copiar, editar ni compartir. No ve las fotos de entrada ni los registros técnicos. |
