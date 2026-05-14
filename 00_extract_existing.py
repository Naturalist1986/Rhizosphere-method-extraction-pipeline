#!/usr/bin/env python3
"""Extract run accessions, BioProjects, and BioSamples from metadata_unified.xlsx
for use as a deduplication set in subsequent search steps."""

import argparse, os
import pandas as pd

DEFAULT_XLSX = os.environ.get("METADATA_XLSX", "")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--metadata", default=DEFAULT_XLSX,
                help="Path to metadata_unified.xlsx (or set METADATA_XLSX env var)")
args = ap.parse_args()

if not args.metadata:
    ap.error("provide --metadata or set METADATA_XLSX")

df = pd.read_excel(args.metadata)
print(f"Loaded {len(df)} samples, {len(df.columns)} columns")

run_acc = set(df["run_accession"].dropna().astype(str))
bioproj = set(df["bioproject"].dropna().astype(str))
biosamp = set(df["BioSample"].dropna().astype(str))

for name, s in [
    ("existing_run_accessions.txt", run_acc),
    ("existing_bioprojects.txt",    bioproj),
    ("existing_biosamples.txt",     biosamp),
]:
    with open(os.path.join(OUT, name), "w") as fh:
        fh.write("\n".join(sorted(s)))

print(f"Saved: {len(run_acc)} run accessions, {len(bioproj)} bioprojects, {len(biosamp)} BioSamples")
