#!/usr/bin/env python3
"""Stage 09 — sync stage-08 perplexity hits (and any stage-06 elink hits not yet
in Zotero) into collection Soil_Rhizosphere_sampling_methods_candidates.

Updates sample_search/data/candidates_zotero_manifest.json in place.
Only items with confidence in {"high","medium"} are pushed by default.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from lib.zotero_client import get_client, get_collection_key, upsert_paper

DATA = ROOT / "data"
ELINK = DATA / "candidates_bp_papers.json"
PCACHE = DATA / "perplexity_paper_cache.json"
MANIFEST = DATA / "candidates_zotero_manifest.json"


def main(min_conf: str, dry_run: bool) -> None:
    elink = json.loads(ELINK.read_text()) if ELINK.exists() else {}
    pcache = json.loads(PCACHE.read_text()) if PCACHE.exists() else {}
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    seen = {m["bioproject"] for m in manifest}

    z = get_client()
    coll = get_collection_key(z)

    order = {"high": 0, "medium": 1, "low": 2}
    threshold = order[min_conf]

    candidates: list[tuple[str, dict, str]] = []
    for bp, v in elink.items():
        if bp not in seen and v.get("doi"):
            candidates.append((bp, v, "elink"))
    for bp, v in pcache.items():
        if bp in seen:
            continue
        if order.get(v.get("confidence", "low"), 2) > threshold:
            continue
        if not v.get("doi"):
            continue
        candidates.append((bp, v, "perplexity"))

    print(f"{len(candidates)} new items to push (min_conf={min_conf})")
    for i, (bp, v, source) in enumerate(candidates, 1):
        if dry_run:
            print(f"[dry] {bp} {v.get('doi')} ({source})")
            continue
        res = upsert_paper(z, coll,
                           doi=v.get("doi"), pmid=v.get("pmid"),
                           title=v.get("title", ""), abstract=v.get("abstract", ""))
        entry = {"bioproject": bp, "source": source,
                 "doi": v.get("doi"), "pmid": v.get("pmid"),
                 "title": v.get("title"),
                 "search_method": "elink" if source == "elink" else "perplexity_sonar",
                 "confidence": v.get("confidence", "elink"),
                 "zotero_item_key": res["zotero_item_key"],
                 "pdf_attached": False,
                 "action": res["action"]}
        manifest.append(entry)
        MANIFEST.write_text(json.dumps(manifest, indent=2))
        print(f"[{i}/{len(candidates)}] {bp} {res['action']} {res['zotero_item_key']}")
        time.sleep(0.4)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-conf", choices=["high", "medium", "low"], default="medium")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    main(a.min_conf, a.dry_run)
