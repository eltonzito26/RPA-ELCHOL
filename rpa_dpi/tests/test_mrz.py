"""Pruebas de rpa_dpi.mrz. Líneas sintéticas; los dígitos de verificación se calculan, no se escriben."""
import unittest

from rpa_dpi.cui import check_digit_731, verify_group
from rpa_dpi.mrz import DatosMrz, parse_mrz


def grupo(aammdd: str) -> str:
    return aammdd + str(check_digit_731(aammdd))


def linea1(digitos="1234567890123", largo=30):
    return ("IDGTM" + digitos).ljust(largo, "<")


def linea2(nac="800101", sexo="M", venc="300101"):
    return (grupo(nac) + sexo + grupo(venc) + "GTM").ljust(29, "<") + "4"


def linea3(texto="PEREZ<LOPEZ<<JUAN<CARLOS"):
    return texto.ljust(30, "<")


class TestParseMrz(unittest.TestCase):
    def test_tres_lineas_completas(self):
        d = parse_mrz([linea1(), linea2(), linea3()])
        self.assertEqual(d.cui14, "1234567890123")
        self.assertEqual(d.nacimiento7, grupo("800101"))
        self.assertEqual(d.vencimiento7, grupo("300101"))
        self.assertTrue(verify_group(d.nacimiento7) and verify_group(d.vencimiento7))
        self.assertEqual(d.sexo, "M")
        self.assertEqual(d.nombres, "JUAN CARLOS")
        self.assertEqual(d.apellidos, "PEREZ LOPEZ")
        self.assertEqual(d.nombre, "JUAN CARLOS PEREZ LOPEZ")

    def test_cui_de_14_digitos(self):
        d = parse_mrz([linea1("12345678901234")])
        self.assertEqual(d.cui14, "12345678901234")

    def test_correccion_ocr_solo_en_numeros(self):
        n, v = grupo("800101"), grupo("300101")
        l1 = linea1("12345678QO1L3")                       # Q,O→0  L→1
        l2 = (n.replace("0", "O").replace("1", "|") + "F" + v.replace("1", "I") + "GTM").ljust(30, "<")
        d = parse_mrz([l1, l2, linea3("OROZCO<LOPEZ<<LIDIA")])
        self.assertEqual(d.cui14, "1234567800113")
        self.assertEqual(d.nacimiento7, n)
        self.assertEqual(d.vencimiento7, v)
        self.assertEqual(d.sexo, "F")
        # las letras del nombre NO se tocan (O, I, L siguen siendo letras)
        self.assertEqual(d.nombres, "LIDIA")
        self.assertEqual(d.apellidos, "OROZCO LOPEZ")

    def test_marcador_con_error_ocr(self):
        self.assertEqual(parse_mrz([linea1().replace("IDGTM", "I0QTM")]).cui14, "1234567890123")

    def test_sexo_no_especificado(self):
        d = parse_mrz([linea2(sexo="<")])
        self.assertIsNone(d.sexo)
        self.assertEqual(d.nacimiento7, grupo("800101"))

    # ---- línea faltante -------------------------------------------------
    def test_falta_linea1(self):
        d = parse_mrz([linea2(), linea3()])
        self.assertEqual(d, DatosMrz(None, grupo("800101"), grupo("300101"), "M", "JUAN CARLOS", "PEREZ LOPEZ"))

    def test_falta_linea2(self):
        d = parse_mrz([linea1(), linea3()])
        self.assertEqual((d.cui14, d.nacimiento7, d.vencimiento7, d.sexo), ("1234567890123", None, None, None))
        self.assertEqual(d.nombre, "JUAN CARLOS PEREZ LOPEZ")

    def test_falta_linea3(self):
        d = parse_mrz([linea1(), linea2()])
        self.assertIsNone(d.nombre)
        self.assertIsNone(d.nombres)
        self.assertEqual(d.sexo, "M")

    def test_orden_no_importa(self):
        self.assertEqual(parse_mrz([linea3(), linea1(), linea2()]), parse_mrz([linea1(), linea2(), linea3()]))

    def test_vacio_o_basura(self):
        self.assertEqual(parse_mrz([]), DatosMrz())
        self.assertEqual(parse_mrz(None), DatosMrz())
        self.assertEqual(parse_mrz(["<<<<<<<<<<<<<<<<<<<<<<", "ABC"]), DatosMrz())

    # ---- relleno '<' dañado ---------------------------------------------
    def test_relleno_linea1_danado(self):
        self.assertIsNone(parse_mrz([linea1()[:18] + "K" + linea1()[19:]]).cui14)   # '<' leído como letra
        self.assertIsNone(parse_mrz(["IDGTM1234567890123<<<<<<<<<<1"]).cui14)      # '<' leído como dígito al final

    def test_relleno_linea1_totalmente_perdido(self):
        self.assertEqual(parse_mrz(["IDGTM1234567890123"]).cui14, "1234567890123")  # solo dígitos: sigue siendo válido
        self.assertIsNone(parse_mrz(["IDGTM12345678901234567"]).cui14)              # largo imposible

    def test_cui_con_digitos_insuficientes(self):
        self.assertIsNone(parse_mrz([linea1("123456789012")]).cui14)

    def test_relleno_nombre_danado(self):
        self.assertIsNone(parse_mrz([linea3("PEREZ<LOPEZ<<JUAN<CARLOS")[:-3] + "KK(" ]).nombre)  # símbolo ajeno
        self.assertIsNone(parse_mrz([linea3("PEREZ<LOPEZ<<JUAN<CARLOS<<<<<<<<K<<<<")]).nombres)  # letra suelta
        self.assertIsNone(parse_mrz([linea3("PEREZ<LOPEZ<JUAN<CARLOS")]).nombres)               # falta '<<'

    def test_separador_dañado_en_linea2(self):
        l = linea2()
        self.assertIsNone(parse_mrz([l.replace("GTM", "G1M")]).nacimiento7)         # nacionalidad ilegible
        self.assertIsNone(parse_mrz([l[:7] + "X" + l[8:]]).sexo)                    # sexo ilegible → línea no coincide
        self.assertIsNone(parse_mrz([l[:7] + "X" + l[8:]]).vencimiento7)

    def test_lineas_contradictorias_no_se_adivinan(self):
        d = parse_mrz([linea1(), linea1("9999999999999"), linea2(), linea2(nac="900202"), linea3()])
        self.assertIsNone(d.cui14)
        self.assertIsNone(d.nacimiento7)
        self.assertEqual(d.nombre, "JUAN CARLOS PEREZ LOPEZ")

    def test_acepta_lineas_repetidas_iguales(self):
        self.assertEqual(parse_mrz([linea1(), linea1()]).cui14, "1234567890123")


if __name__ == "__main__":
    unittest.main()
