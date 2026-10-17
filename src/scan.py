import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from enrich import enrich

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WEB = ROOT / "docs" / "data"
DATA.mkdir(exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc)
SOURCES = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Subastas-Toledo/0.2 (+https://github.com/vtsalamanca/Subastas-Toledo)", "Accept": "application/json"})
PATTERN = re.compile(r"BOE-B-\d{4}-\d+")
AUCTION = re.compile(r"https://subastas\.boe\.es/ds\.php\?id=SUB-[A-Z0-9-]+")
LOCAL = re.compile(r"\b(?:TOLEDO|NAMBROCA|BURGUILLOS|BURGUILLOS DE TOLEDO|COBISA|ARG[EÉ]S|OL[IÍ]AS DEL REY|BARGAS|AZUCAICA)\b", re.I)

def crawl_ids(obj, out):
    """Solo anuncios de secciones IV y V-B, no todo el BOE."""
    def visit(node, eligible=False):
        if isinstance(node, dict):
            name = str(node.get("nombre", node.get("titulo", ""))).lower()
            code = str(node.get("codigo", "")).upper()
            if ("sección iv" in name or "sección cuarta" in name or "administración de justicia" in name or "otros anuncios oficiales" in name or code in ("4", "IV", "5B", "V-B")):
                eligible = True
            if "sección" in name and not any(x in name for x in ("iv", "cuarta", "administración de justicia", "otros anuncios oficiales")):
                eligible = False
            if eligible:
                for k in ("identificador", "id"):
                    v = node.get(k)
                    if isinstance(v, str) and PATTERN.fullmatch(v):
                        out.add(v)
            for value in node.values():
                visit(value, eligible)
        elif isinstance(node, list):
            for value in node:
                visit(value, eligible)
    visit(obj)

def collect_boe():
    ids = set()
    errors = []
    # Ventana solapada para cubrir festivos y fallos puntuales.
    for days in range(0, 8):
        date = (NOW - timedelta(days=days)).strftime("%Y%m%d")
        url = "https://www.boe.es/datosabiertos/api/boe/sumario/" + date
        try:
            res = SESSION.get(url, timeout=25, headers={"Accept": "application/json"})
            if res.status_code == 404:
                continue
            res.raise_for_status()
            crawl_ids(res.json(), ids)
        except (requests.RequestException, ValueError) as exc:
            errors.append(date + ": " + str(exc)[:150])
    if not ids:
        raise RuntimeError("Sin identificadores extraídos: comprobar estructura de la API. " + "; ".join(errors[:3]))
    candidates = []
    for boe_id in sorted(ids):
        try:
            r = SESSION.get("https://www.boe.es/diario_boe/txt.php", params={"id": boe_id}, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            links = AUCTION.findall(r.text.replace("&amp;", "&"))
            if not links:
                continue
            # El juzgado no acredita el municipio del inmueble.
            if not LOCAL.search(text[:1500]):
                continue
            candidates.append({
                "id": boe_id,
                "descripcion": "Anuncio judicial vinculado a Toledo; inmueble y ubicación sin confirmar",
                "municipio": "Por comprobar",
                "url": "https://www.boe.es/diario_boe/txt.php?id=" + boe_id,
                "subasta_url": links[0],
                "clasificacion": "candidato_sin_verificar"
            })
        except requests.RequestException as exc:
            errors.append(boe_id + ": " + str(exc)[:100])
    return candidates, len(ids), errors

status = {"last_run": NOW.isoformat(), "sources": [], "verified_listings": 0, "candidate_listings": 0}
old_path = DATA / "candidates.json"
old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else []
candidates = old
for source in SOURCES:
    if source["id"] != "boe_subastas":
        status["sources"].append({"id": source["id"], "status": "not_checked", "reason": "Adaptador pendiente"})
        continue
    try:
        found, scanned, errors = collect_boe()
        known = {x["id"]: x for x in old}
        for item in found:
            known[item["id"]] = item
        candidates = sorted(known.values(), key=lambda x: x["id"], reverse=True)[:500]
        status["sources"].append({"id": source["id"], "status": "partial" if errors else "checked_announcements", "reason": "Anuncios BOE, no viviendas verificadas", "documents_scanned": scanned, "errors": errors[:10]})
    except Exception as exc:
        status["sources"].append({"id": source["id"], "status": "error", "reason": str(exc)[:400]})
# Fichas oficiales: lectura preliminar, sin certificar viviendas.
for i, candidate in enumerate(candidates[:30]):
    candidates[i] = enrich(candidate, SESSION)
status["portal_details"] = {
    "attempted": min(30, len(candidates)),
    "readable": sum(x.get("detalle_estado") == "consultado_sin_verificacion_integral" for x in candidates[:30]),
    "failed": sum(x.get("detalle_estado") == "error" for x in candidates[:30]),
    "note": "La ficha legible no equivale a vivienda verificada",
}
status["candidate_listings"] = len(candidates)
(DATA / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
(DATA / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
for name in ("candidates.json", "status.json", "results.json"):
    shutil.copyfile(DATA / name, WEB / name)
print(json.dumps(status, ensure_ascii=False))
