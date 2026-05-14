#!/usr/bin/env python3
"""Stage 10 — list which Zotero items still lack a PDF attachment so the user
can manually download them. Pipeline pauses here.

Output: sample_search/data/pdfs_needed.csv
"""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from lib.zotero_client import get_client

DATA = ROOT / "data"
MANIFEST = DATA / "candidates_zotero_manifest.json"
OUT = DATA / "pdfs_needed.csv"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    z = get_client()

    rows = []
    for entry in manifest:
        key = entry["zotero_item_key"]
        children = z.children(key)
        has_pdf = any(c["data"].get("contentType") == "application/pdf" for c in children)
        entry["pdf_attached"] = has_pdf
        if not has_pdf:
            rows.append({
                "bioproject": entry["bioproject"],
                "doi": entry.get("doi", ""),
                "pmid": entry.get("pmid", ""),
                "zotero_item_key": key,
                "title": (entry.get("title") or "")[:120],
                "open_url": f"https://doi.org/{entry['doi']}" if entry.get("doi") else "",
            })

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bioproject", "doi", "pmid", "zotero_item_key", "title", "open_url"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} items need PDFs → {OUT}")
    print("HUMAN STEP: download each PDF and attach it to the Zotero item, or drop it in")
    print("  relevant_papers/<zotero_item_key>.pdf")
    print("Then re-run stage 11.")


if __name__ == "__main__":
    main()
