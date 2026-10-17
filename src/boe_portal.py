"""Adaptador público y auditable del Portal de Subastas del BOE."""
import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://subastas.boe.es/"
SEARCH_URL = urljoin(BASE_URL, "subastas_ava.php")
DETAIL_URL = urljoin(BASE_URL, "detalleSubasta.php")
REFERENCE_RE = re.compile(r"^SUB-[A-Z0-9-]+$")
COUNT_RE = re.compile(r"Resultados\s+(\d+)\s+a\s+(\d+)\s+de\s+(\d+)", re.I)


class CoverageError(RuntimeError):
    """La fuente respondió, pero no pudo demostrarse que se leyó completa."""


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def _response_html(response):
    response.raise_for_status()
    content_type = response.headers.get("content-type", "text/html").lower()
    if "html" not in content_type:
        raise CoverageError(f"Respuesta no HTML: {content_type}")
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    if len(text) < 100 or re.search(
        r"(?i)(error 404|página no encontrada|acceso denegado|servicio no disponible)", text[:1000]
    ):
        raise CoverageError("Página vacía, bloqueada o de error")
    return soup


def search_payload(province_code="45", state="EJ", property_type="I"):
    return {
        "campo[2]": "SUBASTA.ESTADO.CODIGO", "dato[2]": state,
        "campo[3]": "BIEN.TIPO", "dato[3]": property_type,
        "campo[8]": "BIEN.COD_PROVINCIA", "dato[8]": province_code,
        "campo[18]": "SUBASTA.FECHA_INICIO", "dato[18][0]": "", "dato[18][1]": "",
        "page_hits": "50", "sort_field[0]": "SUBASTA.FECHA_FIN",
        "sort_order[0]": "desc", "accion": "Buscar",
    }


def parse_search_page(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    match = COUNT_RE.search(text)
    if not match:
        if re.search(r"(?i)no se han encontrado resultados", text):
            return {"first": 0, "last": 0, "total": 0, "items": [], "next_url": None}
        raise CoverageError("El portal no publicó el contador de resultados")
    first, last, total = map(int, match.groups())
    items, seen = [], set()
    for node in soup.select("li.resultado-busqueda"):
        link = node.find("a", href=lambda value: value and "detalleSubasta.php" in value)
        if not link:
            continue
        reference = parse_qs(urlparse(urljoin(BASE_URL, link["href"])).query).get("idSub", [""])[0]
        if not REFERENCE_RE.fullmatch(reference) or reference in seen:
            continue
        seen.add(reference)
        items.append({"referencia": reference,
                      "resumen_busqueda": clean(node.get_text(" ", strip=True)),
                      "url": DETAIL_URL + "?idSub=" + reference})
    next_link = soup.find("a", string=lambda value: value and "pág. siguiente" in value.lower())
    return {"first": first, "last": last, "total": total, "items": items,
            "next_url": urljoin(SEARCH_URL, next_link["href"]) if next_link else None}


def search_all(session, province_code="45"):
    response = session.post(SEARCH_URL, data=search_payload(province_code), timeout=30)
    _response_html(response)
    page = parse_search_page(response.text)
    expected_total, pages, results, page_ranges, visited = page["total"], 0, {}, [], set()
    while True:
        pages += 1
        page_ranges.append([page["first"], page["last"]])
        for item in page["items"]:
            results[item["referencia"]] = item
        next_url = page["next_url"]
        if not next_url:
            break
        if next_url in visited:
            raise CoverageError("Bucle detectado en la paginación")
        visited.add(next_url)
        response = session.get(next_url, timeout=30)
        _response_html(response)
        page = parse_search_page(response.text)
        if page["total"] != expected_total:
            raise CoverageError("El total cambió durante la paginación")
    if len(results) != expected_total:
        raise CoverageError(f"Cobertura de búsqueda incompleta: extraídas {len(results)} de {expected_total}")
    return list(results.values()), {
        "declared_total": expected_total, "extracted_unique": len(results),
        "pages_read": pages, "page_ranges": page_ranges, "complete": True,
        "query": {"state": "EJ", "property_type": "I", "province_code": province_code},
    }


def table_rows(soup):
    values = {}
    for row in soup.select("tr"):
        label, value = row.find("th"), row.find("td")
        if label and value:
            key, current = clean(label.get_text(" ", strip=True)), clean(value.get_text(" ", strip=True))
            if key:
                values.setdefault(key, []).append(current)
    return values


def public_documents(soup):
    documents, seen = [], set()
    for link in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, link["href"])
        parsed, label = urlparse(href), clean(link.get_text(" ", strip=True))
        is_document = (parsed.path.lower().endswith((".pdf", ".zip", ".doc", ".docx", ".jpg", ".jpeg", ".png"))
                       or "document" in parsed.path.lower() or "document" in label.lower())
        if is_document and href not in seen:
            seen.add(href)
            documents.append({"titulo": label or parsed.path.rsplit("/", 1)[-1], "url": href})
    return documents


def parse_goods(soup):
    goods = []
    heading = soup.find("h3", string=lambda value: value and "Datos del bien subastado" in value)
    if not heading:
        return goods
    for title in heading.parent.find_all("h4"):
        table = title.find_next("table")
        if table:
            goods.append({"titulo": clean(title.get_text(" ", strip=True)), "campos": table_rows(table)})
    return goods


def fetch_auction(session, reference):
    if not REFERENCE_RE.fullmatch(reference):
        raise ValueError("Referencia de subasta no válida")
    tabs, all_documents, general, authority, goods = {}, [], {}, {}, []
    goods_soup = None
    for version, name in ((1, "general"), (2, "authority"), (3, "goods"), (4, "related"), (5, "bids")):
        response = session.get(DETAIL_URL, params={"idSub": reference, "ver": version}, timeout=30)
        soup = _response_html(response)
        page_text = clean(soup.get_text(" ", strip=True))
        if version == 4 and "Relacionados" not in page_text:
            continue
        tabs[name] = {"http_status": response.status_code, "readable": True}
        all_documents.extend(public_documents(soup))
        if version == 1:
            general = table_rows(soup)
        elif version == 2:
            authority = table_rows(soup)
        elif version == 3:
            goods_soup = soup
    lot_ids = []
    if goods_soup:
        for link in goods_soup.find_all("a", href=True):
            query = parse_qs(urlparse(urljoin(BASE_URL, link["href"])).query)
            lot_id = query.get("idLote", [""])[0]
            if lot_id and lot_id not in lot_ids:
                lot_ids.append(lot_id)
        if lot_ids:
            goods = []
            for lot_id in lot_ids:
                response = session.get(
                    DETAIL_URL,
                    params={"idSub": reference, "ver": 3, "idLote": lot_id},
                    timeout=30,
                )
                lot_soup = _response_html(response)
                lot_goods = parse_goods(lot_soup)
                for good in lot_goods:
                    good["lote"] = lot_id
                goods.extend(lot_goods)
                all_documents.extend(public_documents(lot_soup))
        else:
            goods = parse_goods(goods_soup)
    if not general.get("Identificador") or general["Identificador"][0] != reference:
        raise CoverageError(f"La ficha {reference} no confirmó su identificador")
    if not goods:
        raise CoverageError(f"La ficha {reference} no contiene bienes públicos estructurados")
    declared_lots = general.get("Lotes", ["Sin lotes"])[0]
    if declared_lots.isdigit() and len(lot_ids) != int(declared_lots):
        raise CoverageError(
            f"La ficha {reference} declara {declared_lots} lotes y se encontraron {len(lot_ids)}"
        )
    documents = {row["url"]: row for row in all_documents}
    return {"referencia": reference, "url": DETAIL_URL + "?idSub=" + reference,
            "datos_subasta": general, "autoridad_gestora": authority, "bienes": goods,
            "documentos_publicos": list(documents.values()), "pestanas": tabs,
            "lotes_declarados": int(declared_lots) if declared_lots.isdigit() else 0,
            "lotes_leidos": len(lot_ids),
            "cobertura_publica_completa": all(name in tabs for name in ("general", "authority", "goods", "bids"))}


def crawl_active_toledo(session=None):
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Subastas-Toledo/1.0 (+https://github.com/vtsalamanca/Subastas-Toledo)",
                            "Accept": "text/html,application/xhtml+xml"})
    search_items, search_coverage = search_all(session, "45")
    auctions, errors = [], []
    for item in search_items:
        try:
            auction = fetch_auction(session, item["referencia"])
            auction["resumen_busqueda"] = item["resumen_busqueda"]
            auctions.append(auction)
        except (requests.RequestException, CoverageError, ValueError) as exc:
            errors.append({"referencia": item["referencia"], "error": str(exc)[:300]})
    coverage = {**search_coverage, "details_attempted": len(search_items),
                "details_readable": len(auctions), "details_failed": len(errors),
                "goods_extracted": sum(len(row["bienes"]) for row in auctions),
                "documents_linked": sum(len(row["documentos_publicos"]) for row in auctions),
                "errors": errors,
                "scope": "Subastas inmobiliarias en estado Celebrándose y provincia Toledo"}
    coverage["complete"] = search_coverage["complete"] and not errors and len(auctions) == len(search_items)
    return auctions, coverage
