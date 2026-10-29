"""Lectura del libro maestro CADER y búsqueda por CUI exacto.

Solo LEE. La escritura del libro (Estado, relleno de color, resumen, bloque de
faltantes) debe hacerse en otro módulo, sobre una copia local.

Estructura esperada de cada hoja de comunidad (verificada en el libro real):
  fila de encabezado con 'No.' en la columna A; B=Nombre, C=CUI, D=Estado
  (VA/FALTA); resumen en F:G; bloque 'PERSONAS QUE FALTAN POR PROCESAR DPI (n)'
  debajo de la lista.

Los informes de problemas NO incluyen nombres ni CUI: solo comunidad, número
de fila y tipo, para poder compartirlos sin exponer datos personales.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from .cui import cui_mod11_ok, normalize_cui

HOJAS_NO_COMUNIDAD = ("Panel Interactivo", "Reporte General")
ESTADOS = ("VA", "FALTA")


@dataclass(frozen=True)
class Registro:
    comunidad: str
    no: int
    fila_excel: int
    nombre: str
    cui: str | None  # 13 dígitos normalizados, None si no se pudo normalizar
    cui_original: str
    estado: str


@dataclass(frozen=True)
class Problema:
    tipo: str
    comunidad: str
    no: int | None
    detalle: str = ""


class Listado:
    def __init__(self, registros: list[Registro], problemas: list[Problema]):
        self.registros = registros
        self.problemas = problemas
        self._por_cui: dict[str, list[Registro]] = defaultdict(list)
        for r in registros:
            if r.cui:
                self._por_cui[r.cui].append(r)

    # -- búsqueda --------------------------------------------------------
    def buscar(self, cui) -> tuple[str, list[Registro]]:
        """Coincidencia exacta. Devuelve (UNICA | SIN_COINCIDENCIA | MULTIPLE, registros)."""
        n, _ = normalize_cui(cui)
        if n is None:
            return "CUI_INVALIDO", []
        hallados = self._por_cui.get(n, [])
        if not hallados:
            return "SIN_COINCIDENCIA", []
        return ("UNICA" if len(hallados) == 1 else "MULTIPLE"), list(hallados)

    # -- conteos ---------------------------------------------------------
    def conteos(self) -> dict[str, dict[str, int]]:
        c: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "VA": 0, "FALTA": 0})
        for r in self.registros:
            c[r.comunidad]["total"] += 1
            if r.estado in ESTADOS:
                c[r.comunidad][r.estado] += 1
        return dict(c)


def _valor_resumen(ws, hdr: int, etiqueta: str):
    for r in range(hdr, hdr + 6):
        if str(ws.cell(r, 6).value or "").strip().lower() == etiqueta.lower():
            return ws.cell(r, 7).value
    return None


def cargar_listado(ruta: str | Path) -> Listado:
    wb = openpyxl.load_workbook(ruta, data_only=True)
    registros: list[Registro] = []
    problemas: list[Problema] = []

    for hoja in wb.sheetnames:
        if hoja in HOJAS_NO_COMUNIDAD:
            continue
        ws = wb[hoja]
        hdr = next((r for r in range(1, 30) if ws.cell(r, 1).value == "No."), None)
        if hdr is None:
            problemas.append(Problema("HOJA_SIN_ENCABEZADO", hoja, None))
            continue

        # lista principal
        fila = hdr + 1
        propios: list[Registro] = []
        while isinstance(ws.cell(fila, 1).value, (int, float)):
            no = int(ws.cell(fila, 1).value)
            crudo = ws.cell(fila, 3).value
            cui, corregido = normalize_cui(crudo)
            estado = str(ws.cell(fila, 4).value or "").strip().upper()
            reg = Registro(hoja, no, fila, str(ws.cell(fila, 2).value or "").strip(),
                           cui, "" if crudo is None else str(crudo), estado)
            propios.append(reg)
            if cui is None:
                problemas.append(Problema("CUI_FORMATO", hoja, no, "no se pudo normalizar a 13 dígitos"))
            else:
                if corregido:
                    problemas.append(Problema("CUI_CORREGIDO", hoja, no, "se limpió formato (p. ej. ',00')"))
                if not cui_mod11_ok(cui):
                    problemas.append(Problema("CUI_MOD11", hoja, no, "no cumple dígito de verificación de la posición 9"))
            if estado not in ESTADOS:
                problemas.append(Problema("ESTADO_INVALIDO", hoja, no, "distinto de VA/FALTA"))
            fila += 1
        registros.extend(propios)

        va = sum(1 for r in propios if r.estado == "VA")
        faltan = sum(1 for r in propios if r.estado == "FALTA")

        # resumen estático de la hoja (en el libro real son valores, no fórmulas)
        for etiqueta, esperado in (("Total integrantes", len(propios)),
                                   ("DPI escaneado (Van)", va),
                                   ("Pendientes (Faltan)", faltan)):
            v = _valor_resumen(ws, hdr, etiqueta)
            if v is not None and v != esperado:
                problemas.append(Problema("RESUMEN_DESFASADO", hoja, None, f"{etiqueta}: hoja={v}, real={esperado}"))

        # bloque de faltantes
        titulo = None
        for r in range(fila, ws.max_row + 1):
            v = ws.cell(r, 1).value
            if v and "PERSONAS QUE FALTAN" in str(v):
                titulo = r
                break
        if titulo is not None:
            m = re.search(r"\((\d+)\)", str(ws.cell(titulo, 1).value))
            n_titulo = int(m.group(1)) if m else None
            bloque: list[str | None] = []
            r = titulo + 2
            while isinstance(ws.cell(r, 1).value, (int, float)):
                bloque.append(normalize_cui(ws.cell(r, 3).value)[0])
                r += 1
            falta_cui = {x.cui for x in propios if x.estado == "FALTA"}
            if n_titulo != len(bloque):
                problemas.append(Problema("BLOQUE_TITULO_DESFASADO", hoja, None,
                                          f"título={n_titulo}, filas={len(bloque)}"))
            if set(bloque) != falta_cui:
                sobran = len(set(bloque) - falta_cui)
                faltan_b = len(falta_cui - set(bloque))
                problemas.append(Problema("BLOQUE_DISTINTO_DE_ESTADO", hoja, None,
                                          f"en bloque pero no FALTA={sobran}; FALTA ausentes del bloque={faltan_b}"))

    # CUI duplicados
    por_cui: dict[str, list[Registro]] = defaultdict(list)
    for r in registros:
        if r.cui:
            por_cui[r.cui].append(r)
    for rs in por_cui.values():
        if len(rs) > 1:
            for r in rs:
                otros = ", ".join(f"{o.comunidad} No.{o.no}" for o in rs if o is not r)
                problemas.append(Problema("CUI_DUPLICADO", r.comunidad, r.no, f"también en: {otros}"))

    # Mismos 9 primeros dígitos (número + verificador) pero CUI completo distinto:
    # casi seguro la misma persona con el código de municipio mal digitado.
    por_prefijo: dict[str, list[Registro]] = defaultdict(list)
    for r in registros:
        if r.cui:
            por_prefijo[r.cui[:9]].append(r)
    for rs in por_prefijo.values():
        if len({r.cui for r in rs}) > 1:
            for r in rs:
                otros = ", ".join(f"{o.comunidad} No.{o.no}" for o in rs if o is not r)
                problemas.append(Problema("CUI_PREFIJO_REPETIDO", r.comunidad, r.no,
                                          f"mismos 9 primeros dígitos que: {otros}"))

    return Listado(registros, problemas)


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: python -m rpa_dpi.listado <libro.xlsx>")
        return 2
    lst = cargar_listado(argv[1])
    va = sum(1 for r in lst.registros if r.estado == "VA")
    fa = sum(1 for r in lst.registros if r.estado == "FALTA")
    print(f"Registros: {len(lst.registros)}  VA: {va}  FALTA: {fa}")
    print(f"Problemas: {len(lst.problemas)}")
    for p in sorted(lst.problemas, key=lambda p: (p.tipo, p.comunidad, p.no or 0)):
        print(f"  {p.tipo:26s} {p.comunidad:26s} No.{p.no if p.no is not None else '-':<4} {p.detalle}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
