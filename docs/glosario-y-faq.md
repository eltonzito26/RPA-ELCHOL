# Glosario y preguntas frecuentes

## Glosario

| Término | Significado |
| --- | --- |
| **CADER** | Programa y listado de personas beneficiarias que sirve de base para el seguimiento. El proyecto lleva el avance del escaneo de sus DPI. |
| **CUI** | Código Único de Identificación: número de 13 dígitos del DPI. Es la llave para identificar a una persona. |
| **DPI** | Documento Personal de Identificación. |
| **Anverso / reverso** | Cara frontal y cara posterior del DPI. |
| **Zona inferior del reverso (MRZ)** | Franja de texto en la parte baja del reverso, pensada para lectura automática. Contiene el CUI, la fecha de nacimiento, el sexo y la fecha de vencimiento, con dígitos de verificación. |
| **Dígito de verificación** | Dígito calculado a partir de otros para detectar errores de lectura o captura. |
| **7-3-1** | Método de cálculo del dígito de verificación: se multiplican los dígitos por los pesos 7, 3, 1 (repetidos) y se toma el último dígito de la suma. |
| **OCR** | Reconocimiento óptico de caracteres: convierte el texto de una imagen en texto digital. |
| **RPA** | Automatización robótica de procesos. |
| **VA** | Estado de una persona cuyo PDF fue creado, verificado y registrado como completo. |
| **FALTA** | Estado de una persona que aún no tiene PDF. |
| **NO CADER** | Clasificación manual de un DPI cuyo CUI no aparece en el listado CADER. |
| **Vigente / Vencido / Pendiente** | Estados de vigencia de un DPI. Pendiente significa que la fecha no se pudo leer o validar. |
| **Lote** | Ejecución semanal del robot sobre las fotos nuevas. |
| **Operador del lote** | Persona que resuelve los casos de excepción y registra las decisiones. |
| **Libro maestro** | Excel con las 24 hojas de seguimiento. |
| **Libro de decisiones** | Archivo aparte donde el operador registra sus decisiones para que el robot las aplique. |
| **Hoja Revisión** | Hoja del libro maestro con la cola de casos pendientes de revisión. |
| **Hash** | Huella numérica de un archivo. Si dos archivos tienen el mismo hash, son copias exactas. |
| **Orquestador** | Herramienta (UiPath) que coordina los pasos del flujo. |

## Preguntas frecuentes

### ¿El robot puede equivocarse al identificar a una persona?

El diseño busca que **no asocie a una persona equivocada**: solo avanza cuando el CUI del anverso coincide con el del reverso, los dígitos de verificación son válidos y existe una única coincidencia en el listado. Todo lo demás pasa a una persona. Una asociación equivocada es un bloqueador del piloto.

### ¿Qué pasa si una foto está borrosa?

El caso va a revisión con el motivo registrado, y las fotos se conservan. Nunca se adivina un dato dudoso.

### ¿Por qué no se compara el nombre?

Los nombres se repiten y se escriben de formas distintas (con o sin "de", con tildes). El CUI es único. El nombre solo sirve de apoyo.

### ¿Qué pasa con un DPI vencido?

Sí se genera el PDF y la persona queda en VA, con la marca VENCIDO en la hoja Revisión. El vencimiento se cuenta aparte y no cambia el porcentaje de avance. Si la fecha no se puede leer, el caso queda pendiente y nunca se asume vigente.

### ¿Qué pasa si una persona ya tiene PDF?

Si el PDF anterior sigue vigente, se comparan las dos versiones y decide una persona. Si venció, se propone la versión nueva y el operador confirma. El PDF anterior nunca se sobrescribe sin esa decisión.

### ¿Qué pasa si el CUI no está en el listado CADER?

El robot no decide. El operador elige NO CADER y la comunidad, o NO CADER sin comunidad si no se conoce.

### ¿Cuánto tiempo se guardan las fotos?

Las fotos de los casos completos se trasladan a un respaldo y se eliminan a los 30 días. Las de casos incompletos o con error se conservan hasta resolverlos. El PDF final no se borra automáticamente.

### ¿Quién puede ver los DPI?

El responsable, el operador y el robot. Los supervisores ven los PDF y el Excel solo en pantalla, sin descargar. Ver [Privacidad](privacidad.md).

### ¿Se envían los DPI a la nube?

No. El OCR y el procesamiento son locales. Solo el Excel y los PDF se publican en una carpeta de Drive con acceso restringido.

### ¿El correo de resumen incluye datos personales?

No. Es una plantilla con solo números, y si el cuerpo contiene algo ajeno a la plantilla, no se envía.

### ¿Puedo subir una foto de DPI al repositorio para probar?

No. Para pruebas se usan imágenes sintéticas o anonimizadas. Las pruebas con documentos reales se hacen solo en una estación autorizada, fuera del repositorio.

### ¿Por qué falla la instalación en mi computadora?

Revisa la tabla de problemas frecuentes de [Instalación](instalacion.md). Los casos más comunes son Tesseract sin el idioma español, el PATH sin actualizar y el paquete `tzdata` faltante.

### ¿Qué falta para tener el flujo completo?

Integrar las tres partes (recorte, OCR y validación), confirmar el formato real de la zona inferior del reverso, generar el PDF, escribir el estado en el libro, publicar en Drive y orquestarlo con UiPath. El detalle está en [Backlog y planificación](backlog-y-sprints.md).
