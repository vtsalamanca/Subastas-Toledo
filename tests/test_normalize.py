import unittest
from src.normalize import auction_key, normalize, coverage

class NormalizeTests(unittest.TestCase):
    def test_deduplicates_same_auction(self):
        url = "https://subastas.boe.es/ds.php?id=SUB-JA-2026-123"
        items = [{"id": "BOE-B-2026-1", "subasta_url": url},
                 {"id": "BOE-B-2026-2", "subasta_url": url}]
        rows = normalize(items)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["anuncios_boe"]), 2)
        self.assertEqual(rows[0]["clasificacion"], "candidato_sin_verificar")

    def test_no_merge_different_auctions(self):
        a = {"id": "A", "subasta_url": "https://subastas.boe.es/ds.php?id=SUB-JA-2026-1"}
        b = {"id": "B", "subasta_url": "https://subastas.boe.es/ds.php?id=SUB-JA-2026-2"}
        self.assertEqual(len(normalize([a, b])), 2)

    def test_unchecked_source_blocks_completeness(self):
        report = coverage([{"id": "boe", "status": "checked"},
                           {"id": "segipsa", "status": "not_checked"}],
                          {"attempted": 1, "readable": 1, "failed": 0})
        self.assertFalse(report["consulta_completa"])
        self.assertEqual(report["fuentes_no_comprobadas"], ["segipsa"])

    def test_failed_detail_blocks_completeness(self):
        report = coverage([{"id": "boe", "status": "checked"}],
                          {"attempted": 2, "readable": 1, "failed": 1})
        self.assertFalse(report["consulta_completa"])

if __name__ == "__main__":
    unittest.main()
