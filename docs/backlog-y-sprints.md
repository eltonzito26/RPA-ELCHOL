# Backlog y planificación

## Product backlog inicial

El backlog traduce el alcance a historias de usuario organizadas en épicas. Las prioridades pueden ajustarse en la planificación sin cambiar las reglas funcionales.

| Épica | Característica | Historia | Historia de usuario | Prioridad |
| --- | --- | --- | --- | --- |
| EP-01 | Entrada y preparación | HU-01 | Como operador, quiero que el robot detecte archivos nuevos por comunidad para procesar únicamente las entradas pendientes. | Alta |
| EP-01 | Entrada y preparación | HU-02 | Como operador, quiero que las imágenes se orienten, recorten y mejoren conservando el original, para facilitar la lectura sin perder evidencia. | Alta |
| EP-02 | OCR e identidad | HU-03 | Como operador, quiero extraer CUI, nacimiento y vencimiento mediante OCR local para evitar la transcripción manual. | Alta |
| EP-02 | OCR e identidad | HU-04 | Como responsable, quiero validar los dígitos de verificación y la coincidencia entre ambas caras para impedir asociaciones incorrectas. | Alta |
| EP-02 | OCR e identidad | HU-05 | Como operador, quiero buscar el CUI exacto en CADER y enviar las ambigüedades a revisión para no decidir por similitud de nombre. | Alta |
| EP-03 | PDF, vigencia y duplicados | HU-06 | Como operador, quiero detectar copias y PDF previos para evitar reprocesamientos y sobrescrituras. | Alta |
| EP-03 | PDF, vigencia y duplicados | HU-07 | Como supervisor, quiero conocer si un DPI está vigente, vencido o pendiente para revisar versiones de forma informada. | Media |
| EP-03 | PDF, vigencia y duplicados | HU-08 | Como operador, quiero generar y verificar un PDF de una página con ambas caras para marcar VA únicamente cuando la salida sea válida. | Alta |
| EP-04 | Excel y publicación | HU-09 | Como responsable, quiero que el robot actualice el libro maestro sin alterar fórmulas ni formatos para mantener los indicadores existentes. | Alta |
| EP-04 | Excel y publicación | HU-10 | Como responsable, quiero publicar el libro de forma segura en Drive y detectar conflictos de sincronización para evitar la pérdida de cambios. | Alta |
| EP-05 | Supervisión y seguridad | HU-11 | Como operador, quiero registrar excepciones y decisiones en una cola de revisión para dar seguimiento a los casos manuales. | Alta |
| EP-05 | Supervisión y seguridad | HU-12 | Como responsable, quiero controlar el acceso, los registros y el respaldo de fotos para proteger la información y conservar la trazabilidad. | Alta |
| EP-06 | Pruebas y despliegue | HU-13 | Como equipo de desarrollo, queremos probar OCR, emparejamiento, Excel, Drive y la recuperación ante fallos para validar la prueba de concepto antes del piloto. | Alta |

## Avance por historia

Estado según lo que existe hoy en el repositorio. Debe confirmarse con el equipo en cada revisión.

| Historia | Estado | Dónde |
| --- | --- | --- |
| HU-01 | Pendiente | Flujo de orquestación |
| HU-02 | En progreso | `recorte_tarjetas` |
| HU-03 | En progreso | `ocr_dpi_guatemala` |
| HU-04 | Implementada con pruebas sintéticas; falta integrarla con la salida real del OCR | `rpa_dpi/cui.py`, `rpa_dpi/mrz.py` |
| HU-05 | Búsqueda por CUI exacto implementada; falta integrarla al flujo | `rpa_dpi/listado.py` |
| HU-06 | Pendiente (hash y PDF previo) | Flujo de orquestación |
| HU-07 | Parcial: cálculo de vigencia implementado | `rpa_dpi/cui.py` |
| HU-08 | Pendiente | Generación de PDF |
| HU-09 | Pendiente. La lectura del libro está hecha; falta la escritura | `rpa_dpi/listado.py` |
| HU-10 | Pendiente | Publicación en Drive |
| HU-11 | Pendiente | Hoja Revisión y libro de decisiones |
| HU-12 | Parcial: reglas de privacidad documentadas y `.gitignore` | [Privacidad](privacidad.md) |
| HU-13 | En progreso | Pruebas de `rpa_dpi` |

## Planificación del Sprint 1

**Objetivo.** Validar técnicamente las hipótesis críticas antes de construir el flujo completo, obtener tiempos base para el ROI y preparar un conjunto representativo de casos de prueba.

| ID | Tarea | Historia | Responsable |
| --- | --- | --- | --- |
| T1 | Preparar el entorno de desarrollo y las dependencias: UiPath, Python 3, OpenCV, Tesseract y librerías. | HU-13 | Por asignar |
| T2 | Preparar datos de prueba: reales solo en la estación autorizada y sintéticos o anonimizados para las evidencias. | HU-13 | Por asignar |
| T3 | Confirmar el formato de la zona inferior del reverso y el método de los dígitos de verificación con una muestra controlada. | HU-04 | Por asignar |
| T4 | Probar OCR con Tesseract y una alternativa local en imágenes con rotación, desenfoque, sombra y reflejo. | HU-03 | Por asignar |
| T5 | Cronometrar 10 casos manuales para reemplazar los supuestos del ROI. | HU-13 | Por asignar |
| T6 | Inspeccionar la estructura del Excel maestro y verificar el recálculo de fórmulas con una copia de prueba. | HU-09 | Por asignar |
| T7 | Comprobar la sincronización y el manejo de conflictos en Google Drive con datos no sensibles. | HU-10 | Por asignar |
| T8 | Documentar precisión, excepciones, decisiones técnicas y resultados de la prueba de concepto. | HU-13 | Por asignar |

## Plan de implementación

| Fase | Trabajo principal | Resultado demostrable |
| --- | --- | --- |
| **Sprint 1: prueba de concepto** | Datos de prueba, confirmación del dígito de verificación y del formato, medición del OCR, cronometraje de casos manuales, inspección del libro y de Drive. | Informe corto de precisión y decisiones técnicas; conjunto de casos de excepción; tiempos base para el ROI. |
| **Sprint 2: flujo supervisado** | Lote en UiPath, duplicados, emparejamiento por zona de lectura, PDF, estados de vigencia, actualización segura del Excel, libro de decisiones, respaldo, resumen numérico y manejo de fallos. | Demostración integral con CADER, FALTA/VA, vencidos, incompletos y revisión manual. |
| **Cierre académico** | Modelos BPMN, DFD, C4, backlog, repositorio y video. | Entregables trazables a las historias y a los criterios; datos protegidos en la evidencia. |
| **Piloto de operación** | Modo sombra, revisión humana, métricas, confirmación de permisos, política y licencia. | Aprobación del responsable antes de ampliar el volumen. |

## Parámetros de puesta en marcha

| Parámetro | Valor | Estado |
| --- | --- | --- |
| Hora del lote | Lunes a las 6:00 a. m., hora de Guatemala | Valor por defecto, configurable |
| Sufijo para nombres repetidos | `(XXXX)` con las posiciones 5 a 8 del CUI; si aún choca, el número base completo | Verificar con datos reales |
| Retención de la bitácora e historial | 12 meses | Valor por defecto |
| Retención de fotos de entrada | 30 días en la carpeta de respaldo | Decidido |
| Volumen | 50 DPI por semana (100 imágenes por lote) | Decidido |
| Marca "por vencer" | Opcional e informativa, por ejemplo 60 días | Por decidir |
| Licencia de UiPath | Pendiente de confirmar antes del uso institucional | Abierto |
| Tiempos manuales y con robot | Se miden en el Sprint 1 | Abierto |
