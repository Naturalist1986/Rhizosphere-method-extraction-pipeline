#!/usr/bin/env python3
"""For each unique BioProject in filtered_candidates.csv, retrieve the linked
PubMed paper via NCBI elink. Adds columns:
  paper_pmid, paper_title, paper_abstract_excerpt (first 400 chars)

Results are cached in data/paper_cache.json to allow resuming interrupted runs.

Input:  data/filtered_candidates.csv
Output: data/filtered_with_papers.csv
Cache:  data/paper_cache.json

Rate: ~3 req/sec (NCBI free tier; stays within 10 req/sec limit).
"""

import os, time, json
import pandas as pd
from Bio import Entrez, Medline

Entrez.email = os.environ.get("ENTREZ_EMAIL", "")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA       = os.path.join(BASE_DIR, "data")
IN_FILE    = os.path.join(DATA, "filtered_candidates.csv")
OUT_FILE   = os.path.join(DATA, "filtered_with_papers.csv")
CACHE_FILE = os.path.join(DATA, "paper_cache.json")


def load_cache() -> dict[str, dict]:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as fh:
            return json.load(fh)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w") as fh:
        json.dump(cache, fh, indent=2)


def _strip_prefix(bp: str) -> str:
    """NCBI elink expects numeric BioProject IDs, not PRJNA/PRJEB prefixes."""
    for prefix in ("PRJNA", "PRJEB", "PRJDB", "PRJDA", "PRJ"):
        if bp.upper().startswith(prefix):
            numeric = bp[len(prefix):]
            if numeric.isdigit():
                return numeric
    return bp


def fetch_paper(bioproject: str, cache: dict) -> dict:
    """Return paper dict {pmid, title, abstract_excerpt}; empty if not found."""
    bp = bioproject.strip()
    if not bp or bp in ("", "nan", "None"):
        return {}
    if bp in cache:
        return cache[bp]

    result: dict = {}
    try:
        numeric_id = _strip_prefix(bp)
        link_handle = Entrez.elink(dbfrom="bioproject", db="pubmed", id=numeric_id)
        link_data   = Entrez.read(link_handle)
        link_handle.close()

        pmids = []
        for rec in link_data:
            for linkset in rec.get("LinkSetDb", []):
                pmids += [lnk["Id"] for lnk in linkset.get("Link", [])]

        if pmids:
            pmid = pmids[0]
            fh   = Entrez.efetch(db="pubmed", id=pmid, rettype="medline", retmode="text")
            recs = list(Medline.parse(fh))
            fh.close()
            if recs:
                r = recs[0]
                abstract = r.get("AB", "")
                result = {
                    "paper_pmid":             pmid,
                    "paper_title":            r.get("TI", ""),
                    "paper_abstract_excerpt": abstract[:400],
                }
    except Exception as e:
        result = {
            "paper_pmid":             "",
            "paper_title":            "",
            "paper_abstract_excerpt": f"LOOKUP_ERROR: {e}",
        }

    cache[bp] = result
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

df    = pd.read_csv(IN_FILE, low_memory=False)
cache = load_cache()
print(f"Loaded {len(df):,} candidates; cache has {len(cache):,} entries")

# Determine which column holds BioProject IDs
bp_col = "bioproject" if "bioproject" in df.columns else "secondary_study_accession"

unique_bps = [
    bp for bp in df[bp_col].dropna().unique()
    if str(bp).strip() not in ("", "nan", "None")
]
uncached   = [bp for bp in unique_bps if str(bp).strip() not in cache]
print(f"{len(unique_bps):,} unique BioProjects; {len(uncached):,} need fetching")

bp_to_paper: dict[str, dict] = {}

for i, bp in enumerate(unique_bps):
    bp_to_paper[str(bp)] = fetch_paper(str(bp), cache)

    if str(bp) in uncached:
        time.sleep(0.35)  # rate limit

    if i > 0 and i % 100 == 0:
        save_cache(cache)
        found_so_far = sum(1 for v in bp_to_paper.values() if v.get("paper_pmid"))
        print(f"  {i}/{len(unique_bps)} BioProjects processed; "
              f"{found_so_far} papers found so far")

save_cache(cache)

df["paper_pmid"]             = df[bp_col].map(
    lambda x: bp_to_paper.get(str(x), {}).get("paper_pmid", ""))
df["paper_title"]            = df[bp_col].map(
    lambda x: bp_to_paper.get(str(x), {}).get("paper_title", ""))
df["paper_abstract_excerpt"] = df[bp_col].map(
    lambda x: bp_to_paper.get(str(x), {}).get("paper_abstract_excerpt", ""))

found = df["paper_pmid"].astype(bool).sum()
print(f"\nPapers found for {found:,}/{len(df):,} candidates ({100*found//len(df)}%)")

df.to_csv(OUT_FILE, index=False)
print(f"Saved {OUT_FILE}")
