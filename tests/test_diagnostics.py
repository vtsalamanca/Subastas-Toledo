import unittest
from src.diagnostics import diagnose

class DiagnosticsTests(unittest.TestCase):
    def test_unchecked_source_reported(self):
        status = {"sources": [{"id": "segipsa", "status": "not_checked", "reason": "Pendiente"}],
                  "portal_details": {"attempted": 0, "readable": 0, "failed": 0},
                  "verified_listings": 0}
        result = diagnose(status, [])
        self.assertFalse(result["complete"])
        self.assertIn("SOURCE_INCOMPLETE", [x["code"] for x in result["issues"]])

    def test_failure_counts(self):
        status = {"sources": [{"id": "boe", "status": "checked_announcements"}],
                  "portal_details": {"attempted": 2, "readable": 1, "failed": 1},
                  "verified_listings": 0}
        result = diagnose(status, [{"detalle_estado": "error"}, {"detalle_estado": "consultado_sin_verificacion_integral"}])
        self.assertEqual(result["detail_states"]["error"], 1)
        self.assertIn("DETAIL_FETCH_FAILURE", [x["code"] for x in result["issues"]])

if __name__ == "__main__":
    unittest.main()
