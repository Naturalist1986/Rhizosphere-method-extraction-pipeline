#!/usr/bin/env python3
"""Merge candidates from ENA, NCBI, and IMG; remove runs and BioSamples
already present in metadata_unified.xlsx.

BioProject-level duplicates are flagged but NOT removed — a study already in
the dataset may contain additional biological samples.

Input:  data/ena_candidates.json
        data/ncbi_candidates.json
        data/img_candidates.json         (optional)
        data/existing_run_accessions.txt
        data/existing_bioprojects.txt
        data/existing_biosamples.txt
Output: data/merged_raw.csv
"""

import json, os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA     = os.path.join(BASE_DIR, "data")


def load_set(fname: str) -> set[str]:
    p = os.path.join(DATA, fname)
    if not os.path.exists(p):
        return set()
    with open(p) as fh:
        return {line.strip() for line in fh if line.strip()}


def load_json(fname: str) -> list[dict]:
    p = os.path.join(DATA, fname)
    if not os.path.exists(p):
        print(f"  (skipping {fname} — not found)")
        return []
    with open(p) as fh:
        data = json.load(fh)
    print(f"  Loaded {len(data):,} records from {fname}")
    return data


existing_runs    = load_set("existing_run_accessions.txt")
existing_projs   = load_set("existing_bioprojects.txt")
existing_samples = load_set("existing_biosamples.txt")

print(
    f"Existing dataset: {len(existing_runs):,} run accessions, "
    f"{len(existing_projs):,} bioprojects, {len(existing_samples):,} BioSamples"
)

all_recs: list[dict] = []
for src in ["ena_candidates.json", "ncbi_candidates.json", "img_candidates.json"]:
    all_recs.extend(load_json(src))

print(f"Total records before dedup: {len(all_recs):,}")

df = pd.DataFrame(all_recs)

# Normalize key columns to string, strip whitespace
for col in ["run_accession", "sample_accession", "secondary_sample_accession",
            "bioproject", "secondary_study_accession", "study_accession"]:
    if col not in df.columns:
        df[col] = ""
    df[col] = df[col].fillna("").astype(str).str.strip()

# Drop rows with no run_accession
df = df[df["run_accession"] != ""]

# Deduplicate within candidates (same run from multiple queries/sources)
before_internal = len(df)
df = df.drop_duplicates(subset=["run_accession"])
print(f"After internal dedup: {len(df):,} unique run accessions "
      f"(removed {before_internal - len(df):,} intra-source duplicates)")

# Mark exact duplicates against existing dataset
df["_already_run"]     = df["run_accession"].isin(existing_runs)
df["_already_biosamp"] = (
    df["sample_accession"].isin(existing_samples) |
    df["secondary_sample_accession"].isin(existing_samples)
)
df["_bioproject_already"] = (
    df["bioproject"].isin(existing_projs) |
    df["secondary_study_accession"].isin(existing_projs)
)

# Hard-remove exact run or BioSample duplicates
before_dedup = len(df)
df = df[~df["_already_run"] & ~df["_already_biosamp"]]
removed = before_dedup - len(df)
shared_bp = int(df["_bioproject_already"].sum())

print(f"Removed {removed:,} exact run/BioSample duplicates")
print(f"Remaining: {len(df):,} candidates "
      f"({shared_bp:,} share a BioProject with existing data — flagged, not removed)")

out_path = os.path.join(DATA, "merged_raw.csv")
df.to_csv(out_path, index=False)
print(f"Saved {out_path}")
