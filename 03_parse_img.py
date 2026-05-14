#!/usr/bin/env python3
"""Parse manually-downloaded IMG/JGI metadata CSV and normalize to the same
field schema used by ENA/NCBI candidates.

=== MANUAL DOWNLOAD INSTRUCTIONS ===
1. Go to https://img.jgi.doe.gov (log in with JGI account)
2. Click 'Find Genomes' → 'Metagenomes'
3. Apply filters:
     Ecosystem → Terrestrial → Soil → Rhizosphere
     Sequencing Status → Complete  (or include Permanent Draft)
4. Select all results
5. Click 'Export' → 'Metadata' → CSV
6. Save the file as:
     <this_script_dir>/data/img_metadata_raw.csv
7. Then run this script.
=====================================

Input:  data/img_metadata_raw.csv
Output: data/img_candidates.json
"""

import csv, json, os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IN_FILE  = os.path.join(BASE_DIR, "data", "img_metadata_raw.csv")
OUT_FILE = os.path.join(BASE_DIR, "data", "img_candidates.json")

# Map IMG column names → our normalized field names
# (IMG column names vary by export version; add more here as needed)
FIELD_MAP = {
    "Genome ID":                "img_genome_id",
    "Taxon Object ID":          "img_genome_id",
    "Study Name":               "study_title",
    "Proposal Name":            "study_title",
    "Taxon Name":               "scientific_name",
    "Domain":                   "domain",
    "Ecosystem":                "ecosystem",
    "Ecosystem Category":       "ecosystem_category",
    "Ecosystem Type":           "ecosystem_type",
    "Ecosystem Subtype":        "ecosystem_subtype",
    "Specific Ecosystem":       "isolation_source",
    "Isolation":                "isolation_source_detail",
    "Geographic Location":      "geo_loc_name",
    "Latitude":                 "lat",
    "Longitude":                "lon",
    "Host Name":                "host",
    "Sequencing Depth":         "base_count",
    "Assembly Status":          "assembly_status",
    "Genome Size":              "genome_size",
    "Add Date":                 "submission_date",
    "Is Public":                "is_public",
    "NCBI Taxon ID":            "tax_id",
    "BioProject Accession":     "bioproject",
    "BioSample Accession":      "sample_accession",
    "IMG Sample ID":            "img_sample_id",
    "Sequencing Center":        "sequencing_center",
    "Number of Genes":          "gene_count",
    "Publication(s)":           "publications",
}

if not os.path.exists(IN_FILE):
    print(f"ERROR: {IN_FILE} not found.")
    print("Please follow the manual download instructions at the top of this script.")
    sys.exit(1)

records = []
skipped_private = 0

with open(IN_FILE, newline="", encoding="utf-8-sig") as fh:
    # Handle both comma and tab-separated IMG exports
    sample = fh.read(4096)
    fh.seek(0)
    dialect = "excel-tab" if sample.count("\t") > sample.count(",") else "excel"
    reader = csv.DictReader(fh, dialect=dialect)

    for row in reader:
        rec: dict = {}
        for img_col, norm_col in FIELD_MAP.items():
            val = row.get(img_col, "")
            if val and norm_col not in rec:
                rec[norm_col] = val.strip()

        # Skip private records
        is_pub = rec.get("is_public", "").lower()
        if is_pub and is_pub not in ("yes", "1", "true", "public", ""):
            skipped_private += 1
            continue

        rec["_source_db"] = "IMG/JGI"
        # Use genome ID as the run_accession key (IMG has no SRA run IDs directly)
        rec["run_accession"] = rec.get("img_genome_id", "")
        # Mark isolation_source if not present but ecosystem info is
        if not rec.get("isolation_source") and rec.get("ecosystem_type"):
            rec["isolation_source"] = " > ".join(filter(None, [
                rec.get("ecosystem"), rec.get("ecosystem_category"),
                rec.get("ecosystem_type"), rec.get("ecosystem_subtype"),
            ]))

        records.append(rec)

with open(OUT_FILE, "w") as fh:
    json.dump(records, fh, indent=2)

print(f"Parsed {len(records)} IMG candidates → {OUT_FILE}")
if skipped_private:
    print(f"  (skipped {skipped_private} private/non-public records)")
