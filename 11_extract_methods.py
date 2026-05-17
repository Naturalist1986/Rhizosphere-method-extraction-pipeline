#!/usr/bin/env python3
"""Stage 11 — for each manifest item with a PDF (Zotero attachment OR
relevant_papers/<zotero_item_key>.pdf), extract rhizosphere sampling method.

Output: sample_search/data/bp_methods_<date>.json
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from lib.zotero_client import get_client
from lib.methods_extract import extract_rhizosphere_method

DATA = ROOT / "data"
MANIFEST = DATA / "candidates_zotero_manifest.json"
OUT = DATA / f"bp_methods_{date.today().isoformat()}.json"
LOCAL_PDFS = ROOT.parent / "relevant_papers"


def _fulltext_zotero(z, item_key: str) -> str | None:
    children = z.children(item_key)
    for c in children:
        if c["data"].get("contentType") == "application/pdf":
            try:
                ft = z.fulltext_item(c["key"])
                return ft.get("content")
            except Exception:
                return None
    return None


def _fulltext_local(item_key: str) -> str | None:
    p = LOCAL_PDFS / f"{item_key}.pdf"
    if not p.exists():
        return None
    try:
        import pypdf
        reader = pypdf.PdfReader(str(p))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return None


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    z = get_client()
    results: dict[str, dict] = {}

    for entry in manifest:
        bp = entry["bioproject"]
        key = entry["zotero_item_key"]
        text = _fulltext_zotero(z, key) or _fulltext_local(key)
        if not text:
            print(f"  skip {bp}: no PDF")
            continue
        m = extract_rhizosphere_method(text)
        m["bioproject"] = bp
        m["zotero_item_key"] = key
        m["doi"] = entry.get("doi")
        results[bp] = m

    OUT.write_text(json.dumps(results, indent=2))
    by_conf: dict[str, int] = {}
    for v in results.values():
        by_conf[v["confidence"]] = by_conf.get(v["confidence"], 0) + 1
    print(f"{len(results)} BPs processed → {OUT}")
    print("by confidence:", by_conf)


if __name__ == "__main__":
    main()
