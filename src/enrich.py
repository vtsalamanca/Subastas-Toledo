"""Extrae campos preliminares de las fichas oficiales, sin certificar inmuebles."""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

MUNICIPIOS = ("Toledo", "Nambroca", "Burguillos de Toledo", "Cobisa", "Argés", "Olías del Rey", "Bargas", "Azucaica")
LOCATION_RE = re.compile(r"(?:situad[oa]s?\s+en|ubicad[oa]s?\s+en|localidad\s*[:：]|municipio\s*[:：]|t[ée]rmino municipal\s+de|domicilio\s*[:：]|direcci[oó]n\s*[:：])\s*([^.;\n]{3,170})", re.I)
PROPERTY_RE = re.compile(r"\b(vivienda|piso|apartamento|chalet|casa\s+(?:unifamiliar|adosada|pareada)|finca\s+urbana\s+destinada\s+a\s+vivienda)\b", re.I)
DATE_RE = re.compile(r"(?:fecha\s+(?:de\s+)?(?:inicio|fin|apertura|cierre)|inicio|fin\s+de\s+la\s+subasta)\s*[:：]?\s*([^\n]{4,90})", re.I)
AMOUNT_RE = re.compile(r"(?:valor\s+(?:de\s+)?subasta|tipo\s+de\s+subasta|valoraci[oó]n)\s*[:：]?\s*([\d.,]+\s*€?)", re.I)

def clean(value):
    return re.sub(r"\s+", " ", value).strip()

def parse_detail(html, url):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    locations = []
    for match in LOCATION_RE.finditer(text):
        fragment = clean(match.group(1))
        for city in MUNICIPIOS:
            if re.search(r"(?<!\w)" + re.escape(city) + r"(?!\w)", fragment, re.I):
                locations.append({"municipio": city, "evidencia": clean(match.group(0))[:220]})
    kinds = sorted({clean(m.group(0)).lower() for m in PROPERTY_RE.finditer(text)})
    dates = [clean(m.group(0))[:140] for m in list(DATE_RE.finditer(text))[:6]]
    amounts = [clean(m.group(0))[:120] for m in list(AMOUNT_RE.finditer(text))[:4]]
    return {"ficha_url": url, "ficha_consultada": True,
            "municipios_mencionados_en_direccion": locations[:8],
            "tipos_mencionados": kinds[:10], "fechas_texto": dates,
            "valores_texto": amounts,
            "advertencia": "Extracción preliminar. Comprobar lotes, cargas, posesión y documentos antes de pujar."}

def enrich(candidate, session=None):
    result = dict(candidate)
    url = result.get("subasta_url", "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "subastas.boe.es" or parsed.path != "/ds.php":
        result.update(detalle_estado="error", detalle_error="URL de ficha no admitida")
        return result
    session = session or requests.Session()
    try:
        response = session.get(url, timeout=22, headers={"User-Agent": "Subastas-Toledo/0.3 (consulta pública)"})
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "text/html").lower():
            raise ValueError("Respuesta no HTML")
        if len(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)) < 100:
            raise ValueError("Ficha sin contenido legible suficiente")
        result.update(parse_detail(response.text, url))
        result["detalle_estado"] = "consultado_sin_verificacion_integral"
        result.pop("detalle_error", None)
    except (requests.RequestException, ValueError) as exc:
        result.update(detalle_estado="error", detalle_error=str(exc)[:250])
    result["detalle_ultima_consulta"] = datetime.now(timezone.utc).isoformat()
    return result
