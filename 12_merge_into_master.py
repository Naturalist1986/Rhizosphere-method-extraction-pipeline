#!/usr/bin/env python3
"""Stage 12 — merge stage-11 methods into the master rhizosphere_combined xlsx.

Rows whose bioproject has no PDF-backed method extraction (i.e. not present in
the latest bp_methods JSON) are dropped from the output entirely.

For each surviving row, populate:
  Rhizosphere_Method      (one-word label derived from confidence)
  sampling_method         (verbatim_excerpt)
  paper_pmid, paper_doi, paper_title    (from manifest)
  _zotero_item_key        (from manifest)
  pdf_available           (always True for emitted rows)
  notes                   (depth + root_processing + manifest source)

Output: rhizosphere_combined_<today>.xlsx in cwd (or alongside --master input)
"""
from __future__ import annotations
import argparse, json, os
from datetime import date
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MANIFEST = DATA / "candidates_zotero_manifest.json"

CONF_TO_LABEL = {"high": "Good", "medium": "Acceptable", "low": "Weak"}


def latest_methods_file() -> Path:
    files = sorted(DATA.glob("bp_methods_*.json"))
    if not files:
        raise SystemExit("no bp_methods_*.json found — run stage 11 first")
    return files[-1]


def main() -> None:
    default_master = os.environ.get("MASTER_XLSX", "rhizosphere_combined_latest.xlsx")
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=default_master,
                    help="Path to input master xlsx (or set MASTER_XLSX env var)")
    args = ap.parse_args()

    master_in = Path(args.master)
    master_out = master_in.parent / f"rhizosphere_combined_{date.today().isoformat()}.xlsx"

    df = pd.read_excel(master_in)
    methods = json.loads(latest_methods_file().read_text())
    manifest = {m["bioproject"]: m for m in json.loads(MANIFEST.read_text())}

    n_before = len(df)
    df = df[df["bioproject"].astype(str).isin(methods)].reset_index(drop=True)
    n_dropped = n_before - len(df)
    print(f"dropped {n_dropped} rows with no PDF-backed method extraction")

    new_rhizo, new_sm, new_pmid, new_doi, new_ptitle, new_zkey, new_pdf, new_notes = (
        [], [], [], [], [], [], [], [])
    for bp in df["bioproject"].astype(str):
        m = methods[bp]
        man = manifest.get(bp, {})
        new_rhizo.append(CONF_TO_LABEL.get(m["confidence"]))
        new_sm.append(m.get("verbatim_excerpt") or None)
        new_pmid.append(man.get("pmid"))
        new_doi.append(man.get("doi"))
        new_ptitle.append(man.get("title"))
        new_zkey.append(m.get("zotero_item_key"))
        new_pdf.append(True)
        notes_bits = []
        if m.get("sampling_depth_cm"): notes_bits.append(f"depth={m['sampling_depth_cm']}cm")
        if m.get("root_processing"):   notes_bits.append(f"processing={m['root_processing']}")
        if man.get("search_method"):   notes_bits.append(f"source={man['search_method']}")
        new_notes.append("; ".join(notes_bits) or None)

    def fill_col(col_name, new_vals):
        if col_name in df.columns:
            df[col_name] = df[col_name].where(df[col_name].notna(), new_vals)
        else:
            df[col_name] = new_vals

    fill_col("Rhizosphere_Method", new_rhizo)
    fill_col("sampling_method", new_sm)
    fill_col("paper_pmid", new_pmid)
    fill_col("paper_doi", new_doi)
    fill_col("paper_title", new_ptitle)
    fill_col("_zotero_item_key", new_zkey)
    fill_col("pdf_available", new_pdf)
    fill_col("notes", new_notes)

    df.to_excel(master_out, index=False)
    n_filled = df["sampling_method"].notna().sum()
    print(f"wrote {master_out} — {n_filled}/{len(df)} rows have sampling_method")


if __name__ == "__main__":
    main()
