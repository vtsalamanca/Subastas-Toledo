import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
now = datetime.now(timezone.utc).isoformat()
sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
# No se inventan anuncios: los adaptadores pendientes no se consideran consultados.
status = {"last_run": now, "sources": [{"id": s["id"], "status": "not_checked", "reason": "Adaptador de extracción y validación pendiente"} for s in sources], "verified_listings": 0}
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data/status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
(ROOT / "docs/data/status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "docs/data/results.json").write_text((ROOT / "data/results.json").read_text(encoding="utf-8"), encoding="utf-8")
print(json.dumps(status, ensure_ascii=False))
