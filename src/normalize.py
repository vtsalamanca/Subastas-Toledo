"""Normalización conservadora: una referencia de subasta puede tener varios anuncios."""
import re
from urllib.parse import parse_qs, urlparse

REF_RE = re.compile(r"^SUB-[A-Z0-9-]+$")

def auction_key(item):
    url = item.get("subasta_url") or ""
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc == "subastas.boe.es" and parsed.path == "/ds.php":
        value = parse_qs(parsed.query).get("id", [""])[0]
        if REF_RE.fullmatch(value):
            return "portal:" + value
    return "anuncio:" + str(item.get("id", "")).strip()

def normalize(items):
    """Agrupa anuncios por referencia oficial; conserva procedencias y evidencia."""
    groups = {}
    for item in items:
        key = auction_key(item)
        if key == "anuncio:":
            continue
        if key not in groups:
            groups[key] = {**item, "referencia_unica": key, "anuncios_boe": []}
        row = groups[key]
        announcement = item.get("id")
        if announcement and announcement not in row["anuncios_boe"]:
            row["anuncios_boe"].append(announcement)
        for field in ("detalle_estado", "detalle_error", "detalle_ultima_consulta",
                      "municipios_mencionados_en_direccion", "tipos_mencionados",
                      "fechas_texto", "valores_texto"):
            if item.get(field) and not row.get(field):
                row[field] = item[field]
        row["clasificacion"] = "candidato_sin_verificar"
    return sorted(groups.values(), key=lambda x: x["referencia_unica"])

def coverage(sources, details):
    statuses = [s.get("status") for s in sources]
    complete = bool(statuses) and all(s == "checked" for s in statuses)
    if details.get("failed", 0) or details.get("attempted", 0) != details.get("readable", 0):
        complete = False
    return {
        "consulta_completa": complete,
        "fuentes_no_comprobadas": [s["id"] for s in sources if s.get("status") not in ("checked",)],
        "fichas_con_error": details.get("failed", 0),
        "advertencia": "Sin resultados no significa que no existan subastas.",
    }
