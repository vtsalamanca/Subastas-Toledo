import unittest
from unittest.mock import Mock
from src.enrich import parse_detail, enrich

URL = "https://subastas.boe.es/ds.php?id=SUB-JA-2026-267377"

class DetailTests(unittest.TestCase):
    def test_extracts_explicit_location(self):
        html = "<html><body><h1>Subasta judicial</h1><p>Municipio: Nambroca</p><p>Vivienda</p></body></html>"
        result = parse_detail(html, URL)
        self.assertEqual(result["municipios_mencionados_en_direccion"][0]["municipio"], "Nambroca")
        self.assertIn("vivienda", result["tipos_mencionados"])

    def test_no_location_from_court_alone(self):
        result = parse_detail("<html><body>Juzgado de Toledo. Subasta judicial.</body></html>", URL)
        self.assertEqual(result["municipios_mencionados_en_direccion"], [])

    def test_invalid_url_rejected(self):
        result = enrich({"subasta_url": "https://example.org/redirect"})
        self.assertEqual(result["detalle_estado"], "error")

    def test_404_page_rejected(self):
        session = Mock()
        response = Mock()
        response.headers = {"content-type": "text/html"}
        response.text = "<html><body>Error 404 página no encontrada. " + "Contenido " * 25 + "</body></html>"
        session.get.return_value = response
        result = enrich({"subasta_url": URL}, session)
        self.assertEqual(result["detalle_estado"], "error")

if __name__ == "__main__":
    unittest.main()
