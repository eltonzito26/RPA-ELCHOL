# Contexto

## Organización

El proyecto se desarrolla en el contexto del Ministerio de Agricultura, Ganadería y Alimentación (MAGA) de Guatemala, para el municipio de El Chol, Baja Verapaz. El MAGA es una institución pública vinculada al desarrollo agropecuario y rural, y opera distintos sistemas de información para apoyar su gestión administrativa y regional.

El proceso que se automatiza maneja fotografías de DPI y un control de avance asociado a las personas incluidas en listados CADER.

## Proceso actual

Una persona realiza hoy estos pasos:

1. Recibe las fotos de anverso y reverso, organizadas por comunidad.
2. Revisa la calidad y que estén completas.
3. Edita las imágenes para mejorar la lectura.
4. Identifica los datos y a la persona.
5. Contrasta con el listado CADER.
6. Une las dos caras y guarda un PDF con el nombre de la persona.
7. Actualiza el Excel de control.

Son tareas repetitivas y estructuradas, con riesgo de errores de transcripción. Por eso son buenas candidatas para RPA.

## Objetivo

Construir un robot local que prepare y lea las imágenes, busque por CUI exacto, valide ambas caras entre sí, evite reprocesar registros completos, verifique la vigencia del DPI, genere los PDF y actualice el libro de seguimiento de forma trazable. El Excel debe mostrar el avance por comunidad y el total municipal para los supervisores, que lo consultan en modo solo lectura.

## Alcance de la primera fase

- Leer las fotos nuevas de las carpetas por comunidad. Si falta una cara o hay un error, las fotos se conservan.
- Preprocesar las imágenes, clasificar anverso y reverso, ejecutar OCR local y validar los datos, incluidos los dígitos de verificación de la zona inferior del reverso.
- Consultar el listado CADER por CUI y distinguir los casos: CADER, pendiente, incompleto, vencido, duplicado, revisión manual y error técnico.
- Generar un PDF por persona en una página vertical tamaño carta, con el anverso arriba y el reverso abajo.
- Publicar el libro actualizado en Google Drive y, si se habilita, enviar un resumen numérico sin imágenes ni datos personales.

### Fuera de la primera fase

No se usa similitud de nombre para declarar identidad. Si el CUI no aparece en el listado CADER, el operador elige manualmente la opción **NO CADER** y la comunidad; el robot no toma esa decisión.

## El libro de seguimiento

El libro de Excel tiene 24 hojas: un **Panel Interactivo**, un **Reporte General** y una hoja por cada una de las 22 comunidades. Cada hoja de comunidad contiene la lista de personas con su número, nombre, CUI y estado (VA o FALTA), un resumen y un bloque con los pendientes.

El robot actualiza las celdas existentes sin reconstruir el libro, para conservar sus fórmulas y su formato.

## Roles

| Rol | Responsabilidad |
| --- | --- |
| Responsable / dueño del Drive | Administra permisos y carpetas, autoriza copias de PDF y revisa los accesos. |
| Robot | Único escritor del libro maestro. Crea los PDF y traslada las fotos al respaldo. |
| Operador del lote | Único editor humano. Resuelve los casos de excepción en un libro de decisiones aparte. |
| Supervisor lector | Consulta el Excel y los PDF en pantalla, sin descargar ni editar. |

## Retorno de la inversión (estimación)

Con un volumen estimado de 50 DPI por semana, el ahorro depende del tiempo manual real por persona. Los tiempos de la tabla son supuestos de planificación, que se reemplazarán por mediciones durante la prueba de concepto.

| Tiempo manual por persona | Ahorro semanal | Ahorro anual (50 semanas) | Recuperación con 120 h de desarrollo |
| --- | --- | --- | --- |
| 4 min | 2,5 h | ~125 h | ~48 semanas |
| 6 min | 4,2 h | ~210 h | ~29 semanas |
| 8 min | 5,8 h | ~290 h | ~21 semanas |

Fórmula: ahorro semanal = personas por semana × (tiempo manual − tiempo humano restante con el robot). Se supone 1 minuto humano por persona con el robot.

El valor del proyecto no se apoya solo en las horas: también cuentan la reducción de errores de transcripción, la trazabilidad de cada decisión y el avance siempre actualizado para los supervisores.

## Decisiones abiertas

- Licencia de UiPath para uso institucional: pendiente de confirmar.
- Tiempos manuales y tiempos con robot: se miden en la prueba de concepto.
- Marca opcional "por vencer" (por ejemplo, 60 días): por decidir.
