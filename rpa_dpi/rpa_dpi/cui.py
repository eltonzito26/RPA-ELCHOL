"""Validaciones de CUI y de la zona de lectura del reverso del DPI.

Todas las funciones trabajan con datos ya extraídos por el OCR (texto), no con
imágenes. Así Emilio (OCR) y quien arme el flujo comparten un contrato simple.

Nota sobre dos dígitos de verificación distintos:
  * Posición 9 del CUI (en el anverso y en el listado): módulo 11 sobre los
    8 primeros dígitos con pesos 2..9. Comprobado contra el listado CADER:
    631 de 638 CUI cumplen (los 7 que no cumplen son filas FALTA, probables
    errores de captura).
  * Dígito extra de la posición 10 en la zona inferior del reverso y dígitos
    de los grupos de fecha: método 7-3-1 (sección 4 del documento).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

GT_TZ = ZoneInfo("America/Guatemala")
_PESOS_731 = (7, 3, 1)


# --------------------------------------------------------------------------
# CUI
# --------------------------------------------------------------------------
def normalize_cui(value) -> tuple[str | None, bool]:
    """Devuelve (cui_de_13_digitos | None, fue_corregido).

    Acepta texto, enteros y flotantes de Excel. Corrige espacios y sufijos
    decimales como '1918624361509,00'. Si no resultan exactamente 13 dígitos
    devuelve None: no se adivina.
    """
    if value is None:
        return None, False
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    raw = str(value).strip()
    corregido = False
    m = re.fullmatch(r"(\d[\d\s]*)[.,]0+", raw)
    if m:
        raw, corregido = m.group(1), True
    digitos = re.sub(r"\D", "", raw)
    if digitos != raw:
        corregido = True
    if len(digitos) == 13:
        return digitos, corregido
    return None, corregido


def check_digit_cui(cui13: str) -> int:
    """Residuo módulo 11 de los 8 primeros dígitos (pesos 2..9).

    Debe ser igual al dígito de la posición 9 del CUI.
    """
    return sum(int(d) * w for d, w in zip(cui13[:8], range(2, 10))) % 11


def cui_mod11_ok(cui13: str) -> bool:
    return len(cui13) == 13 and check_digit_cui(cui13) == int(cui13[8])


# --------------------------------------------------------------------------
# Método 7-3-1 (zona de lectura del reverso)
# --------------------------------------------------------------------------
def check_digit_731(digitos: str) -> int:
    """Último dígito de la suma ponderada con pesos 7, 3, 1 repetidos."""
    return sum(int(d) * _PESOS_731[i % 3] for i, d in enumerate(digitos)) % 10


def verify_group(grupo: str) -> bool:
    """Grupo = dígitos + su dígito de verificación al final (p. ej. AAMMDD + 1)."""
    return bool(re.fullmatch(r"\d{2,}", grupo)) and check_digit_731(grupo[:-1]) == int(grupo[-1])


def reconstruct_cui(cui14: str) -> tuple[str | None, bool]:
    """CUI del reverso: 13 dígitos con un dígito extra en la posición 10.

    Devuelve (cui_de_13 | None, digito_extra_valido). Si la cadena no tiene
    14 dígitos devuelve (None, False).
    """
    d = re.sub(r"\D", "", cui14 or "")
    if len(d) != 14:
        return None, False
    base9, extra, resto = d[:9], d[9], d[10:]
    return base9 + resto, check_digit_731(base9) == int(extra)


# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------
def parse_aammdd(texto: str, siglo: int = 2000) -> date | None:
    """AAMMDD -> date (año = siglo + AA). None si no es una fecha real."""
    if not re.fullmatch(r"\d{6}", texto or ""):
        return None
    try:
        return date(siglo + int(texto[:2]), int(texto[2:4]), int(texto[4:6]))
    except ValueError:
        return None


def birth_matches(nacimiento_anverso: date | None, aammdd_reverso: str) -> bool:
    """Compara la fecha completa del anverso con AAMMDD del reverso.

    El reverso solo trae dos dígitos de año, así que se compara AA, MM y DD.
    """
    if nacimiento_anverso is None or not re.fullmatch(r"\d{6}", aammdd_reverso or ""):
        return False
    return (
        nacimiento_anverso.year % 100 == int(aammdd_reverso[:2])
        and nacimiento_anverso.month == int(aammdd_reverso[2:4])
        and nacimiento_anverso.day == int(aammdd_reverso[4:6])
    )


def hoy_guatemala() -> date:
    return datetime.now(GT_TZ).date()


def estado_vigencia(vencimiento: date | None, hoy: date | None = None) -> str:
    """VIGENTE | VENCIDO | PENDIENTE (sección 7). Vigente hasta el último día, inclusive."""
    if vencimiento is None:
        return "PENDIENTE"
    hoy = hoy or hoy_guatemala()
    return "VIGENTE" if vencimiento >= hoy else "VENCIDO"


def por_vencer(vencimiento: date | None, dias: int = 60, hoy: date | None = None) -> bool:
    """Aviso informativo opcional; no cambia el estado."""
    if vencimiento is None:
        return False
    hoy = hoy or hoy_guatemala()
    return 0 <= (vencimiento - hoy).days <= dias


# --------------------------------------------------------------------------
# Emparejamiento de ambas caras (sección 4)
# --------------------------------------------------------------------------
@dataclass
class ParResultado:
    ok: bool
    cui: str | None = None
    vencimiento: date | None = None
    vigencia_confiable: bool = False
    motivos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def validar_par(
    anverso_cui: str | None,
    anverso_nacimiento: date | None,
    reverso_cui14: str | None,
    reverso_nacimiento: str | None,
    reverso_vencimiento: str | None,
) -> ParResultado:
    """Aplica la regla de emparejamiento. Entradas = texto leído por el OCR.

    reverso_nacimiento / reverso_vencimiento: 7 dígitos (AAMMDD + dígito).
    El par es válido solo si: el dígito extra del CUI y el del grupo de
    nacimiento son válidos, los dos CUI son iguales y el nacimiento coincide.
    Una falla en el grupo de vencimiento NO invalida el par: deja la
    vigencia en PENDIENTE (sección 7).
    """
    r = ParResultado(ok=False)

    cui_a, _ = normalize_cui(anverso_cui)
    if cui_a is None:
        r.motivos.append("ANVERSO_CUI_FORMATO")
    elif not cui_mod11_ok(cui_a):
        r.avisos.append("ANVERSO_CUI_MOD11")  # aviso: puede ser OCR dudoso

    cui_r, dv_ok = reconstruct_cui(reverso_cui14 or "")
    if cui_r is None:
        r.motivos.append("REVERSO_CUI_FORMATO")
    elif not dv_ok:
        r.motivos.append("REVERSO_CUI_DV_INVALIDO")

    if cui_a and cui_r and cui_a != cui_r:
        r.motivos.append("CUI_DISTINTO_ENTRE_CARAS")

    nac = re.sub(r"\D", "", reverso_nacimiento or "")
    if len(nac) != 7 or not verify_group(nac):
        r.motivos.append("NACIMIENTO_DV_INVALIDO")
    elif not birth_matches(anverso_nacimiento, nac[:6]):
        r.motivos.append("NACIMIENTO_DISTINTO")

    ven = re.sub(r"\D", "", reverso_vencimiento or "")
    if len(ven) == 7 and verify_group(ven):
        r.vencimiento = parse_aammdd(ven[:6])
        r.vigencia_confiable = r.vencimiento is not None
    if not r.vigencia_confiable:
        r.avisos.append("VIGENCIA_PENDIENTE")

    r.ok = not r.motivos
    if r.ok:
        r.cui = cui_a
    return r
