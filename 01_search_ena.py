#!/usr/bin/env python3
"""Search ENA portal API for rhizosphere metagenomic run accessions.

Queries:
  1. tax_tree(<rhizo_taxid>)  — rhizosphere metagenome (TaxID resolved at runtime)
  2. tax_tree(<root_taxid>)   — root metagenome
  3. isolation_source wildcard text searches

Writes: data/ena_candidates.json  (list of dicts with run metadata)
"""

import json, os, time, requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE_DIR, "data", "ena_candidates.json")
BASE_URL = "https://www.ebi.ac.uk/ena/portal/api/search"

FIELDS = ",".join([
    "run_accession", "sample_accession", "secondary_sample_accession",
    "study_accession", "secondary_study_accession", "experiment_accession",
    "scientific_name", "tax_id",
    "sample_title", "sample_description", "isolation_source",
    "host", "country", "lat", "lon", "collection_date",
    "instrument_platform", "instrument_model",
    "library_strategy", "library_source", "library_selection",
    "base_count", "read_count",
    "study_title", "first_created", "first_public",
])


def resolve_taxid(name: str) -> str | None:
    """Look up an NCBI/ENA TaxID by scientific name via ENA taxonomy REST API."""
    try:
        r = requests.get(
            "https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/"
            + requests.utils.quote(name),
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            if data:
                return str(data[0].get("taxId"))
    except Exception as e:
        print(f"  TaxID lookup error for '{name}': {e}")
    return None


rhizo_taxid = resolve_taxid("rhizosphere metagenome")
root_taxid  = resolve_taxid("root metagenome")
print(f"TaxIDs: rhizosphere metagenome={rhizo_taxid}, root metagenome={root_taxid}")

QUERIES = [
    # ENA only supports trailing wildcards — use multiple prefix variants to maximise recall
    'isolation_source="rhizosphere*" AND library_strategy="WGS" AND library_source="METAGENOMIC"',
    'isolation_source="root zone*" AND library_strategy="WGS" AND library_source="METAGENOMIC"',
    'isolation_source="root-attached*" AND library_strategy="WGS" AND library_source="METAGENOMIC"',
    'isolation_source="rhizoplane*" AND library_strategy="WGS" AND library_source="METAGENOMIC"',
    'isolation_source="ectorhizosphere*" AND library_strategy="WGS" AND library_source="METAGENOMIC"',
    'isolation_source="soil attached to root*" AND library_strategy="WGS" AND library_source="METAGENOMIC"',
]

# Add taxonomy queries only if TaxIDs resolved
if rhizo_taxid and rhizo_taxid != "None":
    QUERIES.insert(0, f'tax_tree({rhizo_taxid}) AND library_strategy="WGS" AND library_source="METAGENOMIC"')
if root_taxid and root_taxid != "None":
    QUERIES.insert(1, f'tax_tree({root_taxid}) AND library_strategy="WGS" AND library_source="METAGENOMIC"')

all_records: list[dict] = []
seen_runs: set[str] = set()

for q in QUERIES:
    print(f"\nQuerying: {q[:90]}...")
    try:
        r = requests.get(
            BASE_URL,
            params={
                "result":  "read_run",
                "query":   q,
                "fields":  FIELDS,
                "format":  "json",
                "limit":   50000,
            },
            timeout=300,
        )
        r.raise_for_status()
        hits = r.json()
        new = 0
        for rec in hits:
            run = rec.get("run_accession", "")
            if run and run not in seen_runs:
                seen_runs.add(run)
                rec["_source_db"] = "ENA"
                rec["_ena_query"] = q[:80]
                all_records.append(rec)
                new += 1
        print(f"  → {len(hits)} hits, {new} new unique runs (total: {len(all_records)})")
    except Exception as e:
        print(f"  ERROR: {e}")
    time.sleep(2)

with open(OUT_FILE, "w") as fh:
    json.dump(all_records, fh, indent=2)

print(f"\nSaved {len(all_records)} unique ENA candidates to {OUT_FILE}")
