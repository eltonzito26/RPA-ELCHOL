# RPA DPI | MAGA El Chol

Documentación del proyecto de automatización (RPA) para la revisión supervisada de fotografías de DPI y el seguimiento del avance en el libro CADER del municipio de El Chol, Baja Verapaz.

> **Aviso de privacidad.** Esta documentación no contiene datos personales reales. Todos los ejemplos de CUI, nombres y fechas son ficticios.

## Qué hace el proyecto

Hoy una persona revisa las fotografías de DPI (anverso y reverso), identifica a cada beneficiario, lo contrasta con el listado CADER, prepara un PDF y actualiza el Excel de seguimiento. El proyecto automatiza los pasos mecánicos y deja a una persona la decisión cuando la información no es confiable.

En resumen, el robot:

1. Detecta las fotos nuevas por comunidad.
2. Prepara las imágenes y lee los datos con OCR local.
3. Valida el CUI y los dígitos de verificación, y comprueba que anverso y reverso correspondan a la misma persona.
4. Busca a la persona en el listado CADER por **CUI exacto**.
5. Revisa la vigencia del DPI y detecta duplicados.
6. Genera un PDF de una página (anverso arriba, reverso abajo).
7. Actualiza el Excel y deja en una cola de revisión todo lo dudoso.

## Principios

- **Supervisado.** El robot nunca decide un caso ambiguo: lo envía a revisión humana.
- **El CUI es la llave.** Nunca se identifica a una persona por similitud de nombre.
- **Todo local.** Ningún DPI se envía a servicios en la nube.
- **Trazable.** Cada decisión queda registrada, sin guardar datos personales en los registros técnicos.

## Estado actual

El proyecto está en la fase de análisis y prueba de concepto.

| Parte | Estado |
| --- | --- |
| Análisis, reglas de decisión y diseño del flujo | Documentado |
| Recorte de las tarjetas (`recorte_tarjetas`) | Primera versión en el repositorio |
| Lectura OCR (`ocr_dpi_guatemala`) | Primera versión en el repositorio |
| Validaciones, lectura del listado y lectura de la zona inferior del reverso (`rpa_dpi`) | Primera versión con pruebas |
| Conexión de las tres partes en un flujo único | Pendiente |
| Orquestación en UiPath, generación de PDF y escritura en el Excel | Pendiente |
| Formato real de la zona inferior del reverso | Pendiente de confirmar con fotos reales |

## Cómo está organizada esta documentación

- [Contexto](contexto.md): organización, problema, objetivo y alcance.
- [Flujo del proceso](flujo-del-proceso.md): los 14 pasos del flujo y dónde interviene una persona.
- [Módulos](modulos.md): qué hace cada parte del código y cómo se conectan.
- [Instalación](instalacion.md): cómo preparar el entorno en Windows y correr las pruebas.
- [Reglas de decisión](reglas-de-decision.md): identidad, emparejamiento, vigencia y estados.
- [Privacidad](privacidad.md): acceso, retención de datos y reglas para el repositorio.
