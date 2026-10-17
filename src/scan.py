"""Ejecuta una extracción completa y medible del ámbito público definido."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from boe_portal import crawl_active_toledo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WEB = ROOT / "docs" / "data"
DATA.mkdir(exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)


def main():
    auctions, coverage = crawl_active_toledo()
    generated_at = datetime.now(timezone.utc).isoformat()
    status = {
        "last_run": generated_at,
        "scope": coverage["scope"],
        "sources": [
            {"id": "boe_subastas", "status": "checked" if coverage["complete"] else "error",
             "reason": "Búsqueda oficial, paginación y fichas públicas"},
            {"id": "hacienda", "status": "covered_by_boe_portal",
             "reason": "Las subastas electrónicas AEAT se publican y celebran en el Portal BOE",
             "references_found": sum(row["referencia"].startswith("SUB-AT-") for row in auctions)},
            {"id": "segipsa", "status": "covered_by_boe_portal",
             "reason": "Las subastas electrónicas SEGIPSA del ámbito se celebran en el Portal BOE; no cubre ventas presenciales"},
        ],
        "coverage": coverage,
        "verified_public_auctions": len(auctions),
        "verified_public_goods": coverage["goods_extracted"],
        "complete": coverage["complete"],
    }
    diagnostics = {
        "generated_at": generated_at, "complete": coverage["complete"],
        "issues": coverage["errors"],
        "proof": {key: coverage[key] for key in (
            "declared_total", "extracted_unique", "pages_read", "details_attempted",
            "details_readable", "goods_extracted", "documents_linked")},
    }
    payloads = {"results.json": auctions, "candidates.json": auctions,
                "status.json": status, "diagnostics.json": diagnostics}
    for name, payload in payloads.items():
        (DATA / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copyfile(DATA / name, WEB / name)
    print(json.dumps(status, ensure_ascii=False))
    if not coverage["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
