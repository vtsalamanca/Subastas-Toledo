import unittest

from src.segipsa import normalize_item, query_params


class SegipsaTests(unittest.TestCase):
    def test_normalizes_documents_and_html(self):
        item = {"ID": 1, "post_title": "Subasta", "link": "https://example.test/subasta/1",
                "acf": {"informacion": {"contenido": "<p>Dos lotes</p>", "fecha": "18/11/2026",
                                         "hora_inicio": "10:00", "btn_subasta_online": None},
                        "documentacion": {"docs": [{"nombre": "Pliego", "doc": {
                            "url": "https://example.test/pliego.pdf", "mime_type": "application/pdf",
                            "filesize": 123}}]}}}
        result = normalize_item(item)
        self.assertEqual(result["contenido"], "Dos lotes")
        self.assertEqual(result["modalidad"], "presencial")
        self.assertEqual(result["documentos_publicos"][0]["bytes"], 123)

    def test_query_is_for_active_auctions(self):
        params = dict(query_params())
        self.assertEqual(params["post_type"], "subasta")
        self.assertEqual(params["meta_query[2][compare]"], ">")


if __name__ == "__main__":
    unittest.main()
