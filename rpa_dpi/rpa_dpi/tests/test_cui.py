"""Pruebas de rpa_dpi.cui. Solo datos ficticios (los del documento del proyecto)."""
import unittest
from datetime import date

from rpa_dpi import cui as c


def construir_cui(ocho: str, muni: str = "1506") -> str:
    """CUI sintético válido: 8 dígitos + dígito mod 11 + código de municipio."""
    r = c.check_digit_cui(ocho + "0" * 5)
    assert r != 10, "usar otra semilla"
    return f"{ocho}{r}{muni}"


class TestNormalizar(unittest.TestCase):
    def test_limpia_decimales_y_espacios(self):
        self.assertEqual(c.normalize_cui("1918624361509,00"), ("1918624361509", True))
        self.assertEqual(c.normalize_cui("3158 03305 5170"), ("3158033055170", True))
        self.assertEqual(c.normalize_cui(3158033055170), ("3158033055170", False))
        self.assertEqual(c.normalize_cui(3158033055170.0), ("3158033055170", False))

    def test_no_adivina(self):
        self.assertEqual(c.normalize_cui("31580330551")[0], None)
        self.assertEqual(c.normalize_cui(None), (None, False))


class TestDigitos(unittest.TestCase):
    def test_731_ejemplo_del_documento(self):
        # 3 1 5 8 0 3 3 0 5 -> suma 114 -> dígito 4
        self.assertEqual(c.check_digit_731("315803305"), 4)

    def test_reconstruir_cui_del_reverso(self):
        self.assertEqual(c.reconstruct_cui("3158 03305 4 5170"), ("3158033055170", True))
        self.assertEqual(c.reconstruct_cui("3158 03305 7 5170"), ("3158033055170", False))
        self.assertEqual(c.reconstruct_cui("12345"), (None, False))

    def test_grupo_fecha(self):
        g = "300415"
        self.assertTrue(c.verify_group(g + str(c.check_digit_731(g))))
        self.assertFalse(c.verify_group(g + str((c.check_digit_731(g) + 1) % 10)))

    def test_731_detecta_error_de_un_digito(self):
        base = "315803305"
        dv = c.check_digit_731(base)
        for i in range(len(base)):
            for d in "0123456789":
                if d != base[i]:
                    mal = base[:i] + d + base[i + 1:]
                    self.assertNotEqual(c.check_digit_731(mal), dv)

    def test_mod11_cui_sintetico(self):
        v = construir_cui("31580330")
        self.assertTrue(c.cui_mod11_ok(v))
        mal = v[:8] + str((int(v[8]) + 1) % 10) + v[9:]
        self.assertFalse(c.cui_mod11_ok(mal))


class TestVigencia(unittest.TestCase):
    def test_ultimo_dia_inclusive(self):
        hoy = date(2026, 10, 28)
        self.assertEqual(c.estado_vigencia(date(2026, 10, 28), hoy), "VIGENTE")
        self.assertEqual(c.estado_vigencia(date(2026, 10, 27), hoy), "VENCIDO")
        self.assertEqual(c.estado_vigencia(None, hoy), "PENDIENTE")

    def test_por_vencer(self):
        hoy = date(2026, 10, 28)
        self.assertTrue(c.por_vencer(date(2026, 12, 27), 60, hoy))
        self.assertFalse(c.por_vencer(date(2027, 1, 30), 60, hoy))
        self.assertFalse(c.por_vencer(date(2026, 10, 1), 60, hoy))

    def test_fechas_invalidas(self):
        self.assertIsNone(c.parse_aammdd("301340"))
        self.assertEqual(c.parse_aammdd("360630"), date(2036, 6, 30))


def zona(cui13, nacimiento, vencimiento):
    """Arma las lecturas del reverso (CUI14, nac7, venc7) para pruebas."""
    cui14 = cui13[:9] + str(c.check_digit_731(cui13[:9])) + cui13[9:]
    return (cui14,
            nacimiento + str(c.check_digit_731(nacimiento)),
            vencimiento + str(c.check_digit_731(vencimiento)))


class TestPar(unittest.TestCase):
    def setUp(self):
        self.cui = construir_cui("31580330")
        self.nac = date(1990, 4, 15)

    def test_par_valido(self):
        r = c.validar_par(self.cui, self.nac, *zona(self.cui, "900415", "360630"))
        self.assertTrue(r.ok, r.motivos)
        self.assertEqual(r.cui, self.cui)
        self.assertEqual(r.vencimiento, date(2036, 6, 30))
        self.assertTrue(r.vigencia_confiable)

    def test_cui_distinto_entre_caras(self):
        otro = construir_cui("31580331")
        r = c.validar_par(otro, self.nac, *zona(self.cui, "900415", "360630"))
        self.assertFalse(r.ok)
        self.assertIn("CUI_DISTINTO_ENTRE_CARAS", r.motivos)
        self.assertIsNone(r.cui)

    def test_nacimiento_distinto(self):
        r = c.validar_par(self.cui, date(1991, 4, 15), *zona(self.cui, "900415", "360630"))
        self.assertIn("NACIMIENTO_DISTINTO", r.motivos)

    def test_digito_invalido_en_cui_del_reverso(self):
        cui14, nac7, ven7 = zona(self.cui, "900415", "360630")
        malo = cui14[:9] + str((int(cui14[9]) + 1) % 10) + cui14[10:]
        r = c.validar_par(self.cui, self.nac, malo, nac7, ven7)
        self.assertIn("REVERSO_CUI_DV_INVALIDO", r.motivos)
        self.assertFalse(r.ok)

    def test_vencimiento_ilegible_no_invalida_el_par(self):
        cui14, nac7, _ = zona(self.cui, "900415", "360630")
        r = c.validar_par(self.cui, self.nac, cui14, nac7, "3606301")  # dígito incorrecto
        self.assertTrue(r.ok)
        self.assertFalse(r.vigencia_confiable)
        self.assertIn("VIGENCIA_PENDIENTE", r.avisos)
        self.assertEqual(c.estado_vigencia(r.vencimiento), "PENDIENTE")

    def test_falta_el_reverso(self):
        r = c.validar_par(self.cui, self.nac, None, None, None)
        self.assertFalse(r.ok)


if __name__ == "__main__":
    unittest.main()
