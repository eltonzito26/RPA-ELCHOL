"""Lectura de la zona MRZ del reverso del DPI a partir de las líneas que entrega el OCR.

Entrada: la lista ``mrz`` que devuelve ``ocr_dpi_guatemala/ocr_dpi.py::extract``
(líneas sin espacios, en mayúsculas, con '<').

Se supone un diseño tipo ICAO de tres líneas, pero NO se adivina nada:

    IDGTM<13 o 14 dígitos><<<<...          línea 1
    AAMMDDd S AAMMDDd GTM <<<<... d        línea 2  (d = dígito de verificación 7-3-1)
    APELLIDO<APELLIDO<<NOMBRE<NOMBRE<<<<   línea 3

Cada línea se identifica por su contenido, no por su posición (puede faltar una).
Si una línea no coincide exactamente con lo esperado, sus campos quedan en None.
Las confusiones del OCR (O,Q→0; I,L,|→1) se corrigen SOLO en campos numéricos.

Este módulo no valida dígitos de verificación: eso lo hace ``rpa_dpi.cui``
(``verify_group``, ``reconstruct_cui``) sobre los valores devueltos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_OCR_DIGITOS = str.maketrans({"O": "0", "Q": "0", "I": "1", "L": "1", "|": "1"})
_NUM = r"[0-9OQIL|]"

_MARCADOR = re.compile(r"[I1Ll|][D0][OGQE6]TM")
_LINEA2 = re.compile(rf"({_NUM}{{7}})([MF<])({_NUM}{{7}})GTM")
_SOLO_NOMBRE = re.compile(r"[A-Z<]+")


@dataclass(frozen=True)
class DatosMrz:
    cui14: str | None = None          # 13 o 14 dígitos tras IDGTM
    nacimiento7: str | None = None    # AAMMDD + dígito de verificación
    vencimiento7: str | None = None   # AAMMDD + dígito de verificación
    sexo: str | None = None           # 'M' o 'F' (None si '<' o ilegible)
    nombres: str | None = None
    apellidos: str | None = None

    @property
    def nombre(self) -> str | None:
        """Nombres seguidos de apellidos (None si falta alguno)."""
        if self.nombres and self.apellidos:
            return f"{self.nombres} {self.apellidos}"
        return None


def _num(texto: str) -> str:
    return texto.translate(_OCR_DIGITOS)


def _unico(valores: list):
    """El valor si todas las coincidencias coinciden entre sí; None si hay 0 o conflicto."""
    distintos = list(dict.fromkeys(valores))
    return distintos[0] if len(distintos) == 1 else None


def _cui14(linea: str) -> str | None:
    m = _MARCADOR.match(linea)
    if not m:
        return None
    resto = linea[m.end():]
    digitos = resto.split("<", 1)[0]
    if not re.fullmatch(rf"{_NUM}{{13,14}}", digitos):
        return None
    # lo que sigue debe ser solo relleno '<' (o nada); si no, la línea está dañada
    if resto[len(digitos):].strip("<"):
        return None
    return _num(digitos)


def _fechas_sexo(linea: str) -> tuple[str, str, str] | None:
    m = _LINEA2.match(linea)
    if not m:
        return None
    return _num(m.group(1)), m.group(2), _num(m.group(3))


def _nombres(linea: str) -> tuple[str, str] | None:
    """(nombres, apellidos) de 'APE<APE<<NOM<NOM<<<<'; None si no encaja o es ambiguo."""
    if not _SOLO_NOMBRE.fullmatch(linea) or "<<" not in linea:
        return None
    ape, nom = linea.split("<<", 1)
    apellidos = [t for t in ape.split("<") if t]
    nombres = [t for t in nom.split("<") if t]
    if not apellidos or not nombres:
        return None
    # un token de una sola letra suele ser relleno '<' mal leído: no se adivina
    if any(len(t) < 2 for t in apellidos + nombres):
        return None
    return " ".join(nombres), " ".join(apellidos)


def parse_mrz(lines: list[str]) -> DatosMrz:
    limpias = [re.sub(r"\s+", "", x or "").upper() for x in (lines or [])]

    cui = _unico([c for c in map(_cui14, limpias) if c])
    f2 = [r for r in map(_fechas_sexo, limpias) if r]
    nom = [r for r in map(_nombres, limpias) if r]

    nac = venc = sexo = None
    if len(set(f2)) == 1:
        nac, s, venc = f2[0]
        sexo = s if s in ("M", "F") else None
    nombres = apellidos = None
    if len(set(nom)) == 1:
        nombres, apellidos = nom[0]

    return DatosMrz(cui, nac, venc, sexo, nombres, apellidos)
