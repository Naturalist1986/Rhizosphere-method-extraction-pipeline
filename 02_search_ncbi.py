#!/usr/bin/env python3
"""Supplementary NCBI SRA search to catch US-specific submissions not yet
mirrored to ENA. Uses Entrez esearch + efetch (RunInfo CSV format).

Writes: data/ncbi_candidates.json
"""

import json, os, time, csv, io
from Bio import Entrez

Entrez.email = os.environ.get("ENTREZ_EMAIL", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE_DIR, "data", "ncbi_candidates.json")

QUERIES = [
    '"rhizosphere metagenome"[Organism] AND "WGS"[Library Strategy]',
    '"root metagenome"[Organism] AND "WGS"[Library Strategy]',
    '"rhizosphere"[Isolation Source] AND "WGS"[Library Strategy] AND "metagenome"[Organism]',
    '"root zone soil"[Isolation Source] AND "WGS"[Library Strategy] AND "metagenome"[Organism]',
    '"root-attached"[Isolation Source] AND "WGS"[Library Strategy] AND "metagenome"[Organism]',
    '"rhizoplane"[Isolation Source] AND "WGS"[Library Strategy] AND "metagenome"[Organism]',
]


def esearch_all(query: str, retmax: int = 20000) -> list[str]:
    handle = Entrez.esearch(db="sra", term=query, retmax=retmax, usehistory="y")
    result = Entrez.read(handle)
    handle.close()
    ids = result.get("IdList", [])
    print(f"  '{query[:65]}' → {result['Count']} total, got {len(ids)}")
    return ids


def fetch_runinfo(uid_list: list[str], batch_size: int = 200) -> list[dict]:
    """Fetch SRA RunInfo CSV for a list of internal SRA UIDs."""
    records = []
    total_batches = (len(uid_list) + batch_size - 1) // batch_size
    for i in range(0, len(uid_list), batch_size):
        batch = uid_list[i: i + batch_size]
        batch_num = i // batch_size + 1
        try:
            handle = Entrez.efetch(
                db="sra", id=",".join(batch), rettype="runinfo", retmode="text"
            )
            raw = handle.read()
            handle.close()
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            reader = csv.DictReader(io.StringIO(text))
            batch_rows = [row for row in reader if row.get("Run")]
            records.extend(batch_rows)
            print(f"  batch {batch_num}/{total_batches}: +{len(batch_rows)} rows (total {len(records)})")
        except Exception as e:
            print(f"  batch {batch_num}: ERROR {e}")
        time.sleep(0.4)
    return records


all_uids: set[str] = set()
for q in QUERIES:
    ids = esearch_all(q)
    all_uids.update(ids)
    time.sleep(0.5)

print(f"\nTotal unique SRA UIDs: {len(all_uids)}")
print("Fetching RunInfo (may take several minutes)...")

records = fetch_runinfo(list(all_uids))

# Normalize keys to lowercase, mark source
normalized = []
for r in records:
    nr = {k.lower(): v for k, v in r.items()}
    nr["_source_db"] = "SRA/NCBI"
    normalized.append(nr)

# Rename NCBI RunInfo columns to match ENA field names where possible
NCBI_TO_ENA = {
    "run":           "run_accession",
    "biosample":     "sample_accession",
    "bioproject":    "bioproject",
    "spots":         "read_count",
    "bases":         "base_count",
    "organism":      "scientific_name",
    "samplename":    "sample_title",
    "librarysource": "library_source",
    "librarystrategy": "library_strategy",
    "libraryselection": "library_selection",
    "platform":      "instrument_platform",
    "model":         "instrument_model",
    "geo_loc_name_country_and_or_sea": "geo_loc_name",
    "lat_lon":       "lat_lon_combined",
}
for rec in normalized:
    for old, new in NCBI_TO_ENA.items():
        if old in rec and new not in rec:
            rec[new] = rec.pop(old)

with open(OUT_FILE, "w") as fh:
    json.dump(normalized, fh, indent=2)

print(f"Saved {len(normalized)} NCBI candidates to {OUT_FILE}")
