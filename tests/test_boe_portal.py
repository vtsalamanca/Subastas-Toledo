import unittest
from bs4 import BeautifulSoup

from src.boe_portal import CoverageError, parse_search_page, parse_goods, table_rows


class PortalSearchTests(unittest.TestCase):
    def test_parses_declared_total_and_unique_result(self):
        html = '''<html><body><p>Resultados 1 a 1 de 1</p><ul>
        <li class="resultado-busqueda"><a href="./detalleSubasta.php?idSub=SUB-JA-2026-1">Ficha</a>
        SUBASTA SUB-JA-2026-1 Toledo</li></ul></body></html>'''
        page = parse_search_page(html)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["referencia"], "SUB-JA-2026-1")

    def test_missing_counter_is_coverage_error(self):
        with self.assertRaises(CoverageError):
            parse_search_page("<html><body>Respuesta cambiada</body></html>")

    def test_parses_structured_good(self):
        html = '''<div><h3>Datos del bien subastado</h3><div><h4>Bien 1 - Inmueble (Vivienda)</h4>
        <table><tr><th>Localidad</th><td>TOLEDO</td></tr>
        <tr><th>Dirección</th><td>Calle Mayor 1</td></tr></table></div></div>'''
        goods = parse_goods(BeautifulSoup(html, "html.parser"))
        self.assertEqual(goods[0]["campos"]["Localidad"], ["TOLEDO"])

    def test_preserves_repeated_table_labels(self):
        html = '''<table><tr><th>Documento</th><td>Uno</td></tr>
        <tr><th>Documento</th><td>Dos</td></tr></table>'''
        self.assertEqual(table_rows(BeautifulSoup(html, "html.parser"))["Documento"], ["Uno", "Dos"])


if __name__ == "__main__":
    unittest.main()
