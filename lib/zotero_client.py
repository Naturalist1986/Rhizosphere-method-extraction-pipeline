from __future__ import annotations
import os
from typing import Optional
from pyzotero import zotero

LIBRARY_ID = os.environ.get("ZOTERO_LIBRARY_ID", "")
LIBRARY_TYPE = "user"
COLLECTION_NAME = "Soil_Rhizosphere_sampling_methods_candidates"


def get_client(api_key: str | None = None) -> zotero.Zotero:
    api_key = api_key or os.environ["ZOTERO_API_KEY"]
    return zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, api_key)


def get_collection_key(z) -> str:
    for c in z.collections():
        if c["data"]["name"] == COLLECTION_NAME:
            return c["key"]
    raise RuntimeError(f"collection {COLLECTION_NAME!r} not found")


def find_by_doi(z, doi: str) -> Optional[dict]:
    hits = z.items(q=doi, qmode="everything", limit=20)
    for h in hits:
        if (h.get("data", {}).get("DOI", "") or "").lower() == doi.lower():
            return h
    return None


def upsert_paper(z, collection_key: str, doi: Optional[str], pmid: Optional[str],
                 title: str, abstract: str) -> dict:
    if doi:
        existing = find_by_doi(z, doi)
        if existing:
            return {"action": "exists", "zotero_item_key": existing["key"]}
    template = z.item_template("journalArticle")
    template.update({
        "title": title or "Untitled",
        "DOI": doi or "",
        "abstractNote": abstract or "",
        "extra": f"PMID: {pmid}" if pmid else "",
        "collections": [collection_key],
    })
    res = z.create_items([template])
    new = res["successful"]["0"]
    return {"action": "created", "zotero_item_key": new["key"]}
