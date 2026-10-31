# Arquitectura

## Visión general

El sistema es un robot local que se ejecuta por lote en una estación de trabajo autorizada. Un orquestador (UiPath) coordina el flujo y llama a scripts de Python que contienen la lógica de negocio. El resultado se escribe en un libro de Excel y se publica en una carpeta sincronizada de Google Drive, donde los supervisores lo consultan en modo solo lectura.

Los diagramas de contexto y de contenedores están en la página [Diagramas](diagramas.md).

## Componentes

| Componente | Responsabilidad | Observaciones |
| --- | --- | --- |
| **UiPath Studio** | Orquestar carpetas, Excel, reglas, llamadas a Python, excepciones, bitácora, programación y resumen. | Orquestador sustituible: la lógica de negocio vive en Python. Flujos modulares con control de errores por archivo y por lote. |
| **OCR local** | Tesseract invocado desde Python. Lectura restringida de la zona inferior del reverso (dígitos, mayúsculas y el símbolo `<`) y lectura general del anverso. | Debe verificarse el idioma español, la confianza y el comportamiento con reflejos. Se mide una alternativa local. Ningún DPI se envía a la nube. |
| **Python y OpenCV** | Orientación, recorte, mejora de imagen y recorte de la franja inferior del reverso. | Se preserva el original. Se registran las versiones de las dependencias. |
| **Python PDF** | Crear un PDF por persona en página carta vertical. | Anverso arriba y reverso abajo, en una sola página. |
| **Excel de seguimiento** | Fuente del estado y de las métricas. | Un solo escritor: el robot. Se escribe con Excel instalado en la estación para que las fórmulas se recalculen. |
| **Libro de decisiones** | Registro de las decisiones del operador. | Archivo aparte del maestro. El robot lo lee al iniciar el lote. |
| **Google Drive** | Compartir el libro y las carpetas de PDF con los supervisores en modo lector. | Carpeta sincronizada autorizada en la estación. Supervisores por correo individual, sin enlace público. |
| **Programador de Windows** | Iniciar el lote una vez por semana. | Hora configurable. La estación debe estar encendida, conectada a Drive y autorizada. |

## Decisiones de diseño

| Decisión | Motivo |
| --- | --- |
| La lógica de negocio vive en Python y no en UiPath | Permite probar las reglas de forma automática y reemplazar el orquestador sin reescribirlas. |
| Identificación por CUI exacto, nunca por nombre | Evita asociar a la persona equivocada, que es un bloqueador del piloto. |
| Validación cruzada de ambas caras con la zona inferior del reverso | Dos fuentes independientes reducen el riesgo de un error de lectura del OCR. |
| El robot es el único escritor del libro maestro | Evita conflictos de edición entre personas y robot. |
| El operador registra sus decisiones en un libro aparte | Separa lo que decide una persona de lo que escribe el robot y deja trazabilidad. |
| OCR local, sin servicios en la nube | Protege los datos personales de los beneficiarios. |
| Trabajar sobre una copia local y publicar al final | Permite verificar los totales antes de que los supervisores vean un libro incompleto. |
| Un PDF previo nunca se sobrescribe sin decisión humana | Evita perder una versión correcta por una nueva de peor calidad. |
| El estado VA solo se marca después de verificar el PDF | VA significa "PDF creado y verificado", no "foto recibida". |

## Publicación en Drive

1. El robot trabaja durante todo el lote sobre una copia local, fuera de la carpeta sincronizada.
2. Antes de publicar comprueba que el libro en Drive no cambió desde que empezó (fecha de modificación o hash). Si cambió, no lo sobrescribe: guarda el resultado con otro nombre y avisa.
3. Antes de reemplazar guarda una copia del libro anterior en una carpeta de versiones (últimas 8 semanas).
4. Verifica los totales del Panel, del Reporte General y de cada resumen por comunidad en la copia.
5. Publica y confirma que la sincronización terminó antes de registrar el éxito.
6. Si Drive deja una copia temporal o en conflicto, el robot registra el fallo y no afirma que el libro publicado está al día.

> Confirmar la sincronización por la API de Drive (fecha de modificación y suma de verificación) se evalúa en la prueba de concepto. Si no es posible, queda como comprobación manual durante el piloto.

## Requisitos de operación

| Requisito | Uso |
| --- | --- |
| Windows 10 u 11 | Estación autorizada y disponible durante la ejecución. |
| UiPath Studio Community | Diseño, desarrollo y pruebas. La licencia para uso institucional está pendiente de confirmar. |
| Python 3 de 64 bits | OpenCV, OCR y creación de PDF. |
| Tesseract OCR con español | Motor de OCR local. |
| Microsoft Excel | Recalcular fórmulas al actualizar el libro. |
| Google Drive | Cuenta con edición en la carpeta sincronizada; supervisores invitados con acceso de lector. |
| Azure DevOps y Git | Backlog, sprints y código, sin datos reales ni credenciales. |

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| El OCR no lee bien la zona inferior del reverso (reflejos, compresión de la imagen) | Medir con fotos originales sin comprimir; ajustar el preprocesamiento; derivar a revisión lo que no cuadre. |
| El formato real de la zona inferior difiere del supuesto | El lector de esa zona no adivina: devuelve vacío y el caso va a revisión. Se confirma con una muestra real. |
| Datos del listado CADER con errores (CUI mal digitados o repetidos) | Informe de calidad del libro antes de la puesta en marcha; corrección por el responsable del listado. |
| Los resúmenes por comunidad y los bloques de pendientes están escritos como valores fijos y se desfasan | El robot los actualiza en cada lote, o se convierten en fórmulas. Decisión pendiente. |
| Sincronización de Drive lenta o con conflictos | Publicación verificada, copia previa y no declarar éxito sin confirmación. |
| Licencia de UiPath no confirmada | La lógica en Python permite cambiar de orquestador. |
| Acceso a datos personales por personas no autorizadas | Matriz de acceso, lista nominal de supervisores y revisión trimestral. Ver [Privacidad](privacidad.md). |
