# Privacidad

El proyecto maneja documentos de identidad. Estas reglas aplican a las personas, al código, a los registros y al repositorio.

## Principios

- **Procesamiento local.** Ninguna imagen de DPI se envía a servicios en la nube.
- **Mínimo necesario.** Los registros técnicos y los correos no contienen nombres, CUI ni fechas.
- **Trazabilidad sin exposición.** Cada caso se identifica con un ID interno, no con datos personales.
- **Autorización.** Se requiere autorización institucional escrita del MAGA para usar Drive como repositorio de DPI, y del responsable de los datos para operar con datos reales.

## Quién ve qué

| Rol | Libro maestro | PDF de DPI | Fotos y respaldo | Registros técnicos |
| --- | --- | --- | --- | --- |
| Dueño / responsable | Administra; no edita durante el lote | Administra | Administra | Ver |
| Robot | Editar | Crear | Leer, mover y borrar tras el plazo | Escribir |
| Operador del lote | Ver (edita el libro de decisiones) | Ver | Ver | Ver |
| Supervisor lector | Ver en pantalla | Ver en pantalla | Sin acceso | Sin acceso |
| Correo resumen | Solo cantidades | Nada | Nada | Nada |

### Acceso de supervisores

- Acceso por **correo individual**, nunca por "cualquier persona con el enlace".
- Solo lectura en pantalla: sin descargar, imprimir, copiar ni compartir. Las copias se piden al responsable, que deja registro.
- Esto no impide las capturas de pantalla, por eso se mantiene una lista nominal de supervisores con fecha de alta y baja, que se revisa cada trimestre.
- Cuentas institucionales con verificación en dos pasos, si es posible.

## Retención

| Elemento | Regla |
| --- | --- |
| Fotos de entrada | Se trasladan a una carpeta de respaldo cuando el PDF está verificado, el estado VA confirmado y el libro actualizado. Se eliminan a los 30 días. |
| Fotos incompletas o con error | No pasan al respaldo; permanecen en la carpeta de entrada hasta recibir la cara faltante. |
| PDF final | Nunca se borra automáticamente. |
| Bitácora de lotes | 12 meses. |
| Historial de reemplazos de una persona | Mientras exista su PDF, más 12 meses. |

El respaldo de fotos solo es accesible para el dueño y el robot, no para los supervisores.

## Correo resumen

- Plantilla fija **con solo números**: fecha del lote y, por comunidad, procesados, pendientes, en revisión, vencidos y errores técnicos.
- Sin texto libre, mensajes de excepción ni nombres de archivo.
- Control previo al envío: si el cuerpo contiene una secuencia de 13 dígitos u otro texto que no provenga de la plantilla, no se envía y se registra una alerta.
- Lista fija de destinatarios institucionales y credenciales en un almacén seguro.

## Registros técnicos

- Cada caso se identifica con un **ID interno** (lote más número de orden), nunca con nombre ni CUI. La correspondencia ID–persona vive solo en la hoja Revisión.
- Al capturar una excepción se registra el tipo de error y el paso, no el mensaje original.
- De las rutas solo se registra la carpeta de la comunidad, nunca el nombre del archivo.
- No se registra el texto leído por el OCR ni variables con datos de la persona.
- Se desactivan las capturas automáticas de pantalla en los pasos donde hay un DPI visible.
- Los registros locales quedan en una carpeta accesible solo para el dueño y el robot.
- La carpeta de trabajo del OCR se vacía al terminar cada caso.

## Reglas para el repositorio y la documentación

- **Nunca** se suben al repositorio: el libro Excel real, fotos de DPI, PDF generados, registros ni credenciales. El archivo `.gitignore` bloquea los tipos de archivo más comunes (`*.xlsx`, `*.pdf`, imágenes, `*.log`), pero la responsabilidad es de cada integrante.
- Las pruebas usan **datos sintéticos** o anonimizados; los ejemplos de CUI y fechas de este proyecto son ficticios.
- Las pruebas con documentos reales se hacen solo en una estación autorizada y solo con el consentimiento de la persona dueña del DPI.
- Los scripts de prueba manual que lean fotos reales no deben imprimir ni guardar CUI, nombres ni fechas, y no se suben al repositorio.
- La documentación publicada en GitBook debe mantenerse **privada o con acceso restringido**.

## Pruebas de privacidad

- Provocar errores con un archivo ficticio de nombre reconocible y comprobar, con una búsqueda de texto, que ese nombre y su CUI no aparecen en el correo, en los registros ni en las capturas.
- Comprobar que un supervisor lector no puede descargar ni editar, y que una persona fuera de la lista no tiene acceso.
