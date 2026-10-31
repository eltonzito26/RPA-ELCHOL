# Pruebas y criterios de aceptación

## Estrategia

La prueba de concepto usa un conjunto representativo de casos, **separado** del que se usa para ajustar las reglas. Se mide la lectura del OCR, las decisiones correctas, los casos derivados a revisión, la creación del PDF y la consistencia del libro. No se fija un umbral de precisión del OCR antes de medir resultados reales.

Las pruebas automáticas usan **datos sintéticos**. Las pruebas con documentos reales se hacen solo en una estación autorizada y con el consentimiento de la persona dueña del DPI (ver [Privacidad](privacidad.md)).

## Estado actual de las pruebas automáticas

| Módulo | Pruebas | Qué cubren |
| --- | --- | --- |
| `rpa_dpi` | 42 pruebas; una se omite a propósito | Normalización del CUI, dígitos de verificación, reconstrucción del CUI del reverso, vigencia, emparejamiento de las dos caras, lectura de la zona inferior y lectura del libro CADER con informe de calidad. |
| `ocr_dpi_guatemala` | Sin pruebas automáticas | Se verifica a mano con imágenes de prueba. |
| `recorte_tarjetas` | Sin pruebas automáticas | Se verifica a mano con imágenes de prueba. |

La prueba omitida es la de integración con el libro CADER real, que solo corre si se define la variable de entorno `CADER_XLSX`. Está omitida a propósito para no manejar datos reales en el entorno de desarrollo.

Para ejecutarlas, ver [Instalación](instalacion.md).

## Criterios de aceptación

| Prueba | Qué comprobar | Criterio de aceptación |
| --- | --- | --- |
| **OCR del CUI** | Lecturas exactas por tipo de degradación (desenfoque, reflejo, rotación, poca luz) en anverso y reverso, y formato inválido. | No se asocia a una persona equivocada. Una lectura de baja confianza va a revisión. Se mide cuántos errores detecta el dígito de verificación. |
| **Zona inferior y emparejamiento** | Dígito válido e inválido, CUI distinto entre caras, nacimiento distinto, formatos de distintos modelos de DPI. | Solo un par con las tres coincidencias y dígitos válidos produce PDF. |
| **Fecha de vencimiento** | Vigente, vencido, ilegible, último día de vigencia y discrepancia entre fuentes. | Estado trazable según las reglas de vigencia. |
| **Emparejamiento de caras** | Dos caras, cara faltante, duplicadas, más de dos entradas. | Solo una pareja inequívoca y completa produce el PDF final. |
| **No reprocesar** | PDF=VA con archivo, PDF=VA sin archivo, PDF=FALTA con salida previa. | No se duplica ni se sobrescribe; las discrepancias se registran. |
| **Excel y Drive** | Permisos, bloqueo, sincronización lenta, desconexión, libro modificado durante el lote, libro de decisiones con filas incompletas. | Solo se declara publicado si el cambio está confirmado y el resumen cuadra. |
| **Respaldo de fotos** | Traslado solo con PDF verificado, VA y libro actualizado; borrado definitivo tras el plazo. | Ninguna foto se pierde antes de 30 días. |
| **Indicadores** | Dos o más comunidades y el consolidado municipal. | Totales y porcentajes coinciden con el listado maestro. |
| **Recuperación** | Fallo en OCR, Python o Drive durante un lote. | No se pierde el original; se reanuda sin duplicar la salida ni el estado. |
| **Privacidad** | Supervisor sin descarga ni edición, persona fuera de la lista sin acceso, correo, registros, repositorio y video. | Solo los usuarios autorizados ven datos identificadores. Ningún nombre ni CUI de prueba aparece en el correo ni en los registros. |

## Bloqueadores del piloto

El piloto no puede iniciar mientras ocurra cualquiera de estos casos:

- Una asociación a la persona equivocada.
- Generar un PDF final incompleto.
- Sobrescribir o perder originales.
- Marcar VA sin un archivo verificado.
- No detectar duplicados.
- Dar acceso a CUI o DPI a personas fuera de la lista de supervisores autorizados, o dar a un supervisor más permisos que los de lector.
- Operar con datos reales sin la autorización del responsable de esos datos.

## Hallazgos de las pruebas preliminares

| Hallazgo | Consecuencia |
| --- | --- |
| El OCR confunde la letra I del marcador `IDGTM` con el número 1. | El lector de la zona inferior tolera esa variante. Se propuso el mismo cambio en el módulo de OCR. |
| En una foto real comprimida por WhatsApp, el OCR leyó el nombre de la zona inferior pero no sus dos líneas numéricas. | Se repetirá la prueba con fotos originales sin comprimir antes de ajustar el código. |
| El libro CADER tiene CUI que no cumplen el dígito de la posición 9, CUI repetidos entre personas y bloques de pendientes con títulos desfasados. | Se preparó una lista para el responsable del listado, solo por comunidad y número de fila, sin nombres ni CUI. Debe corregirse antes del piloto. |
