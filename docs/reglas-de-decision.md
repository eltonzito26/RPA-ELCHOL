# Reglas de decisión

Estas reglas determinan qué hace el robot con cada caso. Si una regla no se cumple, el caso pasa a revisión humana; el robot nunca adivina.

## Identidad

- El **CUI** del DPI es la llave principal. Se busca una coincidencia **exacta y única** en el listado CADER.
- El nombre es solo un apoyo y **no sustituye** al CUI.
- Antes de emparejar, el CUI del anverso debe coincidir con el CUI reconstruido de la zona inferior del reverso.

## Dígitos de verificación

### Zona inferior del reverso (método 7-3-1)

Cada dígito se multiplica por los pesos 7, 3, 1 (repetidos) y el dígito de verificación es el último dígito de la suma. La zona inferior del reverso tiene:

- el CUI con un **dígito extra en la posición 10**;
- la fecha de nacimiento (AAMMDD) con su dígito;
- el sexo (M/F);
- la fecha de vencimiento (AAMMDD) con su dígito.

Ejemplo con datos ficticios: para los nueve primeros dígitos `3 1 5 8 0 3 3 0 5`, la suma es 21 + 3 + 5 + 56 + 0 + 3 + 21 + 0 + 5 = 114, y el dígito de verificación es 4. El CUI ficticio del anverso es `3158 03305 5170`; en el reverso aparece como `3158 03305 4 5170`.

> **Estado:** hipótesis respaldada por un ejemplo. Debe confirmarse con una muestra de 5 a 10 DPI que el método y el formato son los mismos en todos los modelos de documento.

### CUI (posición 9)

Al revisar el listado CADER se observó que, en 631 de 638 CUI, el dígito de la posición 9 coincide con el residuo módulo 11 de los ocho primeros dígitos, con pesos del 2 al 9. Se usa como **aviso** de posible error de captura, no como motivo de rechazo. Es una observación empírica, pendiente de confirmar con la fuente oficial.

### Correcciones del OCR

En los campos que deben ser numéricos se corrigen las confusiones típicas (O por 0, I por 1, B por 8). El dígito de verificación confirma si la lectura quedó bien; si no cuadra, el caso va a revisión.

## Regla de emparejamiento

Un par anverso–reverso es válido **solo si**:

1. los dígitos de verificación son válidos;
2. los dos CUI coinciden exactamente;
3. la fecha de nacimiento coincide;
4. hay una única coincidencia en el listado CADER.

En cualquier otro caso, el par pasa a revisión.

## Vigencia

| Resultado | Condición |
| --- | --- |
| **VIGENTE** | La fecha de vencimiento es igual o posterior a la fecha de ejecución del lote (hora de Guatemala). Es vigente hasta el último día indicado, inclusive. |
| **VENCIDO** | La fecha de vencimiento es anterior a la de ejecución. |
| **PENDIENTE** | No se pudo extraer o validar la fecha. Requiere revisión; **nunca se asume vigente**. |

- **Fuente principal:** la fecha de vencimiento de la zona inferior del reverso, válida solo si su dígito de verificación coincide. El año de dos dígitos se interpreta como 20AA.
- **Respaldo:** la fecha impresa en el documento. Si ambas fuentes difieren, el caso queda PENDIENTE.
- **Marca "por vencer"** (opcional): aviso informativo para DPI que vencen dentro de un plazo configurable. No cambia el estado.

Un DPI vencido **sí genera PDF y se marca VA**, con la marca VENCIDO en la hoja Revisión. El vencimiento se cuenta en su propio indicador y no se mezcla con el estado del PDF.

## Tabla de decisión

| Condición | Resultado | Acción |
| --- | --- | --- |
| CUI válido y una coincidencia exacta; par completo y coincidente; sin PDF previo; fecha legible. | Listo para PDF | Generar, verificar, archivar y marcar VA. Si está vencido, registrar VENCIDO en Revisión. |
| Existe un PDF anterior y está vigente. | Comparar versiones | Mostrar ambas versiones. El supervisor indica su preferencia y el operador registra la decisión. |
| PDF anterior vencido; la nueva pareja está completa y vigente. | Reemplazo propuesto | Priorizar la nueva versión; el operador confirma y se registra antes de reemplazar. |
| PDF anterior vencido y la entrada también vencida. | Comparar versiones | Proponer la de vencimiento más reciente; el operador confirma. |
| Estado VA, pero el PDF falta, está dañado o no corresponde. | Discrepancia | No sobrescribir; revisar y reconciliar Excel y archivos. |
| CUI inválido, OCR dudoso, dígito inválido, CUI distinto entre caras, cero coincidencias o más de una fila. | Revisión manual | Conservar el original, registrar el motivo y no decidir por similitud de nombre. |
| Falta el anverso o el reverso. | Incompleto | Dejar pendiente; no generar PDF ni cambiar a VA. |
| La fecha de vencimiento no se lee o las fuentes discrepan. | Vigencia pendiente | Revisión manual; no asumir vigente. |
| El CUI no aparece en el listado CADER. | Selección manual | El operador elige NO CADER y la comunidad conocida; si no se conoce, NO CADER sin comunidad. |
| Falla de Excel, Drive, OCR o generación. | Error técnico | Conservar la entrada, no marcar VA, reintentar solo lo transitorio y dejar traza. |

## Duplicados y nombres repetidos

La verificación de repetidos se hace en varios niveles:

- Se compara el **hash** de cada archivo contra el historial para detectar copias idénticas.
- Tras el OCR se busca el CUI exacto y se consulta el estado y el PDF previo.
- Se compara el vencimiento y la calidad de la versión existente con las imágenes nuevas.

**Nombre del PDF.** El archivo se llama *Nombre Completo*.pdf. Nunca se sobrescribe: si dos personas tienen el mismo nombre en la misma carpeta, el archivo lleva el sufijo `(XXXX)` con las posiciones 5 a 8 del CUI, por ejemplo `Nombre Completo (0330).pdf`. Si aun así chocara, se usa el número base completo.

## Verificación del PDF

Un PDF se considera válido cuando:

- abre sin error;
- tiene una sola página, tamaño carta, orientación vertical;
- contiene dos imágenes, ninguna en blanco y cada una con un tamaño mínimo razonable;
- su nombre coincide con el nombre completo del listado CADER;
- su tamaño está dentro de un rango esperado.

Esta verificación no garantiza la nitidez de la imagen; para eso existe la revisión semanal de los supervisores.
