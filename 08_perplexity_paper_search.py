#!/usr/bin/env python3
"""Stage 08 — for each BP in bioprojects_to_search.csv not yet resolved by
elink (stage 06) or a prior perplexity run, query Perplexity Sonar Pro Search
for a candidate paper and cache the result.

Input:  sample_search/bioprojects_to_search.csv
        sample_search/data/candidates_bp_papers.json  (elink hits, 121 BPs)
        sample_search/data/perplexity_paper_cache.json (this stage's cache, if resuming)
Output: sample_search/data/perplexity_paper_cache.json
        sample_search/data/perplexity_run.log

Resumable: every successful call is immediately flushed to the cache.
"""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
from lib.bp_inputs import load_bioprojects
from lib.perplexity import search_paper_for_bp

DATA = ROOT / "data"
ELINK = DATA / "candidates_bp_papers.json"
PCACHE = DATA / "perplexity_paper_cache.json"
LOG = DATA / "perplexity_run.log"
INPUT_CSV = ROOT / "bioprojects_to_search.csv"


def main(batch: int, sleep_s: float, dry_run: bool) -> None:
    df = load_bioprojects(INPUT_CSV, enrichment_paths=[
        DATA / "ncbi_candidates.json", DATA / "ena_candidates.json"])
    elink = json.loads(ELINK.read_text()) if ELINK.exists() else {}
    cache = json.loads(PCACHE.read_text()) if PCACHE.exists() else {}

    todo = [bp for bp in df.index if bp not in elink and bp not in cache]
    print(f"{len(todo)} BPs to resolve (skipping {len(elink)} elink, {len(cache)} cached)")
    todo = todo[:batch] if batch else todo

    with LOG.open("a") as logf:
        for i, bp in enumerate(todo, 1):
            row = df.loc[bp]
            if dry_run:
                print(f"[dry] {bp} {row.get('study_title', '')[:60]}")
                continue
            try:
                result = search_paper_for_bp(
                    bioproject=bp,
                    study_title=row.get("study_title", ""),
                    organism=row.get("enrich_organism", ""),
                    n_samples=row.get("n_samples", ""),
                    center=row.get("enrich_center_name", ""),
                    extra=row.get("paper_abstract_excerpt", ""),
                )
                cache[bp] = result
                PCACHE.write_text(json.dumps(cache, indent=2))
                logf.write(f"{bp}\tOK\t{result.get('confidence')}\t{result.get('doi')}\n")
                print(f"[{i}/{len(todo)}] {bp} → {result.get('confidence')} {result.get('doi')}")
            except Exception as e:
                logf.write(f"{bp}\tERR\t{e}\n")
                print(f"[{i}/{len(todo)}] {bp} ERROR {e}", file=sys.stderr)
            time.sleep(sleep_s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=50, help="Max BPs this run (0 = all)")
    ap.add_argument("--sleep", type=float, default=1.5, help="Seconds between requests")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    main(a.batch, a.sleep, a.dry_run)
