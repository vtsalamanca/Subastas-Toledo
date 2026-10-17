"""Prueba real y acotada de fuentes. No altera resultados públicos."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

OUT = Path("probe-report.json")
S = requests.Session()
S.headers.update({"User-Agent": "Subastas-Toledo/diagnostic-0.1", "Accept": "application/json"})
report = {"time": datetime.now(timezone.utc).isoformat(), "checks": []}

def check(name, url, kind):
    row = {"name": name, "url": url, "result": "error"}
    try:
        response = S.get(url, timeout=15)
        row["http_status"] = response.status_code
        row["content_type"] = response.headers.get("content-type", "")
        row["bytes"] = len(response.content)
        response.raise_for_status()
        if kind == "json":
            obj = response.json()
            row["result"] = "readable_json" if isinstance(obj, (dict, list)) else "unexpected_json"
            row["root_keys"] = list(obj)[:12] if isinstance(obj, dict) else []
        else:
            text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
            row["result"] = "readable_html" if len(text) >= 100 else "short_html"
            row["text_length"] = len(text)
            row["possible_block"] = any(x in text.lower()[:800] for x in ("acceso denegado", "error 404", "página no encontrada", "captcha"))
    except (requests.RequestException, ValueError) as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:250]
    report["checks"].append(row)

yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
check("boe_api", "https://www.boe.es/datosabiertos/api/boe/sumario/" + yesterday, "json")
for ident in ("SUB-JA-2026-267377", "SUB-JA-2026-260645", "SUB-JA-2026-263668"):
    check("portal_detail", "https://subastas.boe.es/ds.php?id=" + ident, "html")
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))

accepted_results = {"readable_json", "readable_html"}
failed_checks = [row for row in report["checks"] if row["result"] not in accepted_results]
if failed_checks:
    print(
        json.dumps(
            {
                "result": "failed",
                "failed_checks": [row["name"] for row in failed_checks],
                "report": str(OUT),
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    raise SystemExit(1)
