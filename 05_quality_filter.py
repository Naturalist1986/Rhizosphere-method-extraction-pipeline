#!/usr/bin/env python3
"""Apply keyword-based quality assessment to merged candidates.

Each row receives:
  auto_quality  : ACCEPT | FLAG | REJECT
  quality_flags : pipe-separated list of reasons

Hard-reject criteria (per user specification):
  - isolation_source matches a bulk-soil pattern
  - Any text field mentions rhizobox/rhizotron/artificial root systems
  - Any text field mentions hydroponic or agar/liquid culture (no soil)

Flag criteria (needs Moshe's manual review):
  - No isolation_source provided
  - isolation_source is generic "soil" without "rhizosphere" qualifier
  - Description mentions mesocosm / microcosm / growth chamber
  - Read count < 500,000
  - Study BioProject already in the existing dataset

Positive boost:
  - Text explicitly mentions tightly-attached / adhering-soil collection
    → overrides minor flags (only no_isolation_source) → ACCEPT

Input:  data/merged_raw.csv
Output: data/filtered_candidates.csv
"""

import os, re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA     = os.path.join(BASE_DIR, "data")
IN_FILE  = os.path.join(DATA, "merged_raw.csv")
OUT_FILE = os.path.join(DATA, "filtered_candidates.csv")

# ── Pattern definitions ────────────────────────────────────────────────────────

BULK_SOURCES = re.compile(
    r"^(bulk[\s_-]?soil|non[\s_-]?rhizosphere[\s_-]?soil|control[\s_-]?soil|"
    r"bare[\s_-]?soil|non[\s_-]?vegetated[\s_-]?soil|bulk[\s_-]?agricultural[\s_-]?soil|"
    r"bulk[\s_-]?forest[\s_-]?soil|bulk[\s_-]?grassland[\s_-]?soil|"
    r"non[\s_-]?rhizosphere|unplanted[\s_-]?soil|vegetated[\s_-]?bulk[\s_-]?soil)$",
    re.IGNORECASE,
)

ARTIFICIAL_SYSTEMS = re.compile(
    r"rhizotron|rhizobox|rhizotube|mini[\s_-]?rhizotron|"
    r"\broot[\s_-]?window\b|\broot[\s_-]?box\b|\broot[\s_-]?chamber\b",
    re.IGNORECASE,
)

NO_ATTACHMENT = re.compile(
    r"\bhydroponic\b|agar[\s_-]?plate|liquid[\s_-]?culture|"
    r"\bsterile[\s_-]?sand\b|\bsterile[\s_-]?glass[\s_-]?bead",
    re.IGNORECASE,
)

POSITIVE = re.compile(
    r"tightly[\s_-]?attached|adhering[\s_-]?soil|root[\s_-]?attached[\s_-]?soil|"
    r"soil[\s_-]?attached[\s_-]?to[\s_-]?root|vigorous[\s_-]?shak|"
    r"\brhizoplane\b|\bectorhizosphere\b|soil[\s_-]?clinging[\s_-]?to[\s_-]?root|"
    r"washed[\s_-]?root[\s_-]?surface",
    re.IGNORECASE,
)

FLAG_TERMS = re.compile(
    r"\bmesocosm\b|\bmicrocosm\b|\bgrowth[\s_-]?chamber\b",
    re.IGNORECASE,
)


def _combined_text(row: pd.Series, *cols: str) -> str:
    parts = []
    for c in cols:
        v = row.get(c, "")
        if isinstance(v, str) and v:
            parts.append(v)
    return " | ".join(parts)


def classify(row: pd.Series) -> tuple[str, list[str]]:
    iso      = str(row.get("isolation_source", "") or "").strip()
    combined = _combined_text(
        row, "isolation_source", "sample_description", "sample_title", "study_title"
    )

    flags: list[str] = []

    # ── Hard rejects ──────────────────────────────────────────────────────────
    if BULK_SOURCES.match(iso):
        return "REJECT", ["isolation_source=bulk_soil"]

    if ARTIFICIAL_SYSTEMS.search(combined):
        return "REJECT", ["artificial_root_system"]

    if NO_ATTACHMENT.search(combined):
        return "REJECT", ["no_soil_attachment"]

    # ── Flags ─────────────────────────────────────────────────────────────────
    iso_lower = iso.lower()
    if not iso or iso_lower in ("", "na", "n/a", "not provided", "not collected",
                                "missing", "unknown", "not applicable"):
        flags.append("no_isolation_source")
    elif iso_lower == "soil":
        flags.append("isolation_source=generic_soil")

    # Read depth check
    read_count = 0
    for col in ("read_count", "base_count", "spots", "run_total_spots"):
        try:
            v = row.get(col, 0)
            parsed = int(float(str(v or 0)))
            if parsed > 0:
                # base_count is bases, not reads — rough conversion: /150
                read_count = parsed // 150 if col == "base_count" else parsed
                break
        except (ValueError, TypeError):
            pass
    if 0 < read_count < 500_000:
        flags.append(f"low_reads(~{read_count:,})")

    if FLAG_TERMS.search(combined):
        flags.append("controlled_environment")

    if row.get("_bioproject_already", False):
        flags.append("bioproject_already_in_dataset")

    # ── Positive boost ────────────────────────────────────────────────────────
    positive = bool(POSITIVE.search(combined))
    if positive:
        flags.append("positive_method_indicator")

    if not flags:
        return "ACCEPT", []

    # Positive indicator overrides the single "no_isolation_source" flag
    if positive and flags == ["no_isolation_source", "positive_method_indicator"]:
        return "ACCEPT", flags

    return "FLAG", flags


# ── Main ──────────────────────────────────────────────────────────────────────

df = pd.read_csv(IN_FILE, low_memory=False)
print(f"Loaded {len(df):,} candidates")

results = df.apply(classify, axis=1, result_type="expand")
df["auto_quality"]  = results[0]
df["quality_flags"] = results[1].apply(lambda x: " | ".join(x) if x else "")

counts = df["auto_quality"].value_counts()
print(f"\nQuality breakdown:")
for q, n in counts.items():
    print(f"  {q:8s}: {n:,}")

df.to_csv(OUT_FILE, index=False)
print(f"\nSaved {len(df):,} rows to {OUT_FILE}")
