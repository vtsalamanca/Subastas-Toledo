"""Adaptador del catálogo público de subastas activas de SEGIPSA."""
from datetime import datetime

import requests
from bs4 import BeautifulSoup

AJAX_URL = "https://www.segipsa.es/wp-admin/admin-ajax.php"


class SegipsaCoverageError(RuntimeError):
    pass


def query_params(page=1, now=None):
    now = now or datetime.now()
    date, time = now.strftime("%Y%m%d"), now.strftime("%H%M%S")
    return [
        ("action", "veure_mes_extend"), ("posts_per_page", "100"),
        ("post_type", "subasta"), ("page", str(page)), ("order", "ASC"),
        ("orderby", "meta_value"), ("meta_key", "informacion_fecha"),
        ("meta_query_relation", "OR"),
        ("meta_query[0][key]", "informacion_fecha"), ("meta_query[0][compare]", "NOT EXISTS"),
        ("meta_query[1][key]", "informacion_fecha"), ("meta_query[1][value]", ""),
        ("meta_query[1][compare]", "="),
        ("meta_query[2][key]", "informacion_fecha"), ("meta_query[2][value]", date),
        ("meta_query[2][compare]", ">"), ("meta_query[2][type]", "NUMERIC"),
        ("meta_query[3][relation]", "AND"),
        ("meta_query[3][0][key]", "informacion_fecha"),
        ("meta_query[3][0][value]", date), ("meta_query[3][0][compare]", "="),
        ("meta_query[3][0][type]", "NUMERIC"),
        ("meta_query[3][1][relation]", "OR"),
        ("meta_query[3][1][0][key]", "informacion_hora_fin"),
        ("meta_query[3][1][0][value]", time), ("meta_query[3][1][0][compare]", ">="),
        ("meta_query[3][1][0][type]", "TIME"),
        ("meta_query[3][1][1][key]", "informacion_hora_fin"),
        ("meta_query[3][1][1][compare]", "NOT EXISTS"),
        ("meta_query[3][1][2][key]", "informacion_hora_fin"),
        ("meta_query[3][1][2][value]", ""), ("meta_query[3][1][2][compare]", "="),
    ]


def clean_html(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def normalize_item(item):
    acf = item.get("acf") or {}
    info = acf.get("informacion") or {}
    document_section = acf.get("documentacion") or {}
    documents = []
    for row in document_section.get("docs") or []:
        document = row.get("doc") or {}
        if document.get("url"):
            documents.append({
                "titulo": row.get("nombre") or document.get("title") or document.get("filename"),
                "url": document["url"], "mime_type": document.get("mime_type"),
                "bytes": document.get("filesize"),
            })
    return {
        "id": item.get("ID"), "titulo": item.get("post_title", ""),
        "url": item.get("link", ""), "fecha": info.get("fecha", ""),
        "hora_inicio": info.get("hora_inicio", ""), "hora_fin": info.get("hora_fin", ""),
        "modalidad": "electronica" if info.get("btn_subasta_online") else "presencial",
        "contenido": clean_html(info.get("contenido")), "documentos_publicos": documents,
    }


def crawl_active(session=None, now=None):
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Subastas-Toledo/1.0", "Referer": "https://www.segipsa.es/"})
    items, declared_total, max_pages = {}, None, 1
    for page in range(1, 101):
        response = session.post(AJAX_URL, data=query_params(page, now), timeout=30)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise SegipsaCoverageError("SEGIPSA no devolvió JSON") from exc
        if not payload.get("success") or not isinstance(payload.get("data"), dict):
            raise SegipsaCoverageError("Respuesta AJAX de SEGIPSA no válida")
        data = payload["data"]
        page_items = data.get("items") or []
        current_total = int(data.get("found_posts", len(page_items)))
        current_max_pages = int(data.get("max_num_pages", 1))
        if declared_total is None:
            declared_total, max_pages = current_total, current_max_pages
        elif current_total != declared_total or current_max_pages != max_pages:
            raise SegipsaCoverageError("El total de SEGIPSA cambió durante la paginación")
        for item in page_items:
            if item.get("ID") is not None:
                items[str(item["ID"])] = normalize_item(item)
        if page >= max_pages:
            break
    if len(items) != declared_total:
        raise SegipsaCoverageError(f"Cobertura SEGIPSA incompleta: {len(items)} de {declared_total}")
    result = list(items.values())
    coverage = {"declared_total": declared_total, "extracted_unique": len(result),
                "pages_read": max_pages,
                "documents_linked": sum(len(row["documentos_publicos"]) for row in result),
                "complete": True, "scope": "Catálogo de subastas activas publicado por SEGIPSA"}
    return result, coverage
