#!/usr/bin/env python3
"""Stage 15 — classify each BioProject's rhizosphere extraction method into
one of seven mutually-exclusive buckets, and populate auxiliary flag columns.

Input: a manual-review XLSX (typically the output of stages 13 + 14) with two
free-text source columns:

  - `Rhizosphere_extraction_summary` — NotebookLM-generated per-paper paragraph
                                       (stage 13)
  - `Rhizosphere_extraction_method`  — verbatim Methods text (stage 14)

Per-row source rule: prefer `Rhizosphere_extraction_method` when both are
populated (less likely to have dropped reagent names like Silwet/Tween).

Decision tree (apply strictly in order; the first YES terminates):

  1. Is the method described at all?
     NO  → "Not described"
  2. Was there a root/soil separation step?
     NO  → "Bulk-near-root coring"  (coring/augering/depth-based sampling)
  3. Was a liquid buffer used in the separation?
     NO  → "Dry separation"  (shake/brush/scrape/sieve)
  4. Was sonication applied?
     YES → "Sonication-based"
  5. Was a surfactant added (Tween 20, Silwet L-77, sodium pyrophosphate)?
     YES → "Surfactant-assisted"
  6. Was the extraction performed in a preservation buffer
     (RNAlater, LifeGuard, glycerol, SM buffer)?
     YES → "Preservation-embedded"
  7. Default → "Buffer wash + vortex"

Output: a coded XLSX with all original columns preserved and 14 new columns
appended (bucket + auxiliary flags + coder notes + confidence).

Usage:
    python 15_classify_buckets.py \
        --input  data/rhizosphere_methods_review_manual.xlsx \
        --output data/rhizosphere_methods_review_coded.xlsx

The bucket assignments encoded in BUCKETS{} below are hand-curated against
the 183-row dataset used to develop this stage. To re-use this script on a
new manual-review XLSX, re-curate BUCKETS{} (and OVERRIDES{}) row-by-row;
the regex helpers for auxiliary columns are dataset-agnostic.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

DEFAULT_INPUT = Path("data/rhizosphere_methods_review_manual.xlsx")
DEFAULT_OUTPUT = Path("data/rhizosphere_methods_review_coded.xlsx")

# ---------------------------------------------------------------------------
# Hand-coded bucket per row index (0-based). Built by reading every row's text
# against the decision tree (see classify_rhizosphere_README.md if generated).
# ---------------------------------------------------------------------------
BUCKETS = {
    0: "Dry separation",
    1: "Bulk-near-root coring",
    2: "Bulk-near-root coring",
    3: "Dry separation",
    4: "Dry separation",
    5: "Bulk-near-root coring",
    6: "Bulk-near-root coring",
    7: "Dry separation",
    8: "Buffer wash + vortex",
    9: "Bulk-near-root coring",
    10: "Dry separation",
    11: "Dry separation",
    12: "Bulk-near-root coring",
    13: "Buffer wash + vortex",
    14: "Bulk-near-root coring",
    15: "Bulk-near-root coring",
    16: "Dry separation",
    17: "Dry separation",
    18: "Surfactant-assisted",
    19: "Buffer wash + vortex",
    20: "Sonication-based",
    21: "Buffer wash + vortex",
    22: "Sonication-based",
    23: "Preservation-embedded",
    24: "Preservation-embedded",
    25: "Buffer wash + vortex",
    26: "Buffer wash + vortex",
    27: "Dry separation",
    28: "Dry separation",
    29: "Dry separation",
    30: "Sonication-based",
    31: "Dry separation",
    32: "Buffer wash + vortex",
    33: "Buffer wash + vortex",
    34: "Dry separation",
    35: "Preservation-embedded",
    36: "Dry separation",
    37: "Buffer wash + vortex",
    38: "Buffer wash + vortex",
    39: "Buffer wash + vortex",
    40: "Buffer wash + vortex",
    41: "Dry separation",
    42: "Buffer wash + vortex",
    43: "Buffer wash + vortex",
    44: "Buffer wash + vortex",
    45: "Buffer wash + vortex",
    46: "Buffer wash + vortex",
    47: "Buffer wash + vortex",
    48: "Sonication-based",
    49: "Surfactant-assisted",
    50: "Surfactant-assisted",
    51: "Surfactant-assisted",
    52: "Surfactant-assisted",
    53: "Surfactant-assisted",
    54: "Surfactant-assisted",
    55: "Surfactant-assisted",
    56: "Surfactant-assisted",
    57: "Surfactant-assisted",
    58: "Buffer wash + vortex",
    59: "Sonication-based",
    60: "Buffer wash + vortex",
    61: "Buffer wash + vortex",
    62: "Bulk-near-root coring",
    63: "Dry separation",
    64: "Buffer wash + vortex",
    65: "Bulk-near-root coring",
    66: "Bulk-near-root coring",
    67: "Dry separation",
    68: "Not described",
    69: "Bulk-near-root coring",
    70: "Not described",
    71: "Bulk-near-root coring",
    72: "Dry separation",
    73: "Dry separation",
    74: "Buffer wash + vortex",
    75: "Dry separation",
    76: "Buffer wash + vortex",
    77: "Dry separation",
    78: "Dry separation",
    79: "Sonication-based",
    80: "Dry separation",
    81: "Dry separation",
    82: "Dry separation",
    83: "Sonication-based",
    84: "Buffer wash + vortex",
    85: "Buffer wash + vortex",
    86: "Surfactant-assisted",
    87: "Buffer wash + vortex",
    88: "Dry separation",
    89: "Buffer wash + vortex",
    90: "Buffer wash + vortex",
    91: "Dry separation",
    92: "Dry separation",
    93: "Dry separation",
    94: "Buffer wash + vortex",
    95: "Buffer wash + vortex",
    96: "Surfactant-assisted",
    97: "Dry separation",
    98: "Dry separation",
    99: "Dry separation",
    100: "Dry separation",
    101: "Buffer wash + vortex",
    102: "Buffer wash + vortex",
    103: "Buffer wash + vortex",
    104: "Buffer wash + vortex",
    105: "Dry separation",
    106: "Buffer wash + vortex",
    107: "Buffer wash + vortex",
    108: "Dry separation",
    109: "Not described",
    110: "Buffer wash + vortex",
    111: "Dry separation",
    112: "Dry separation",
    113: "Bulk-near-root coring",
    114: "Bulk-near-root coring",
    115: "Bulk-near-root coring",
    116: "Bulk-near-root coring",
    117: "Bulk-near-root coring",
    118: "Bulk-near-root coring",
    119: "Bulk-near-root coring",
    120: "Buffer wash + vortex",
    121: "Buffer wash + vortex",
    122: "Surfactant-assisted",
    123: "Bulk-near-root coring",
    124: "Bulk-near-root coring",
    125: "Buffer wash + vortex",
    126: "Preservation-embedded",
    127: "Sonication-based",
    128: "Buffer wash + vortex",
    129: "Not described",
    130: "Not described",
    131: "Buffer wash + vortex",
    132: "Not described",
    133: "Not described",
    134: "Not described",
    135: "Dry separation",
    136: "Bulk-near-root coring",
    137: "Not described",
    138: "Bulk-near-root coring",
    139: "Surfactant-assisted",
    140: "Not described",
    141: "Dry separation",
    142: "Buffer wash + vortex",
    143: "Dry separation",
    144: "Dry separation",
    145: "Dry separation",
    146: "Dry separation",
    147: "Bulk-near-root coring",
    148: "Buffer wash + vortex",
    149: "Buffer wash + vortex",
    150: "Bulk-near-root coring",
    151: "Dry separation",
    152: "Buffer wash + vortex",
    153: "Buffer wash + vortex",
    154: "Not described",
    155: "Buffer wash + vortex",
    156: "Not described",
    157: "Not described",
    158: "Not described",
    159: "Surfactant-assisted",
    160: "Not described",
    161: "Buffer wash + vortex",
    162: "Buffer wash + vortex",
    163: "Dry separation",
    164: "Not described",
    165: "Surfactant-assisted",
    166: "Not described",
    167: "Dry separation",
    168: "Not described",
    169: "Dry separation",
    170: "Not described",
    171: "Bulk-near-root coring",
    172: "Bulk-near-root coring",
    173: "Buffer wash + vortex",
    174: "Buffer wash + vortex",
    175: "Not described",
    176: "Buffer wash + vortex",
    177: "Not described",
    178: "Buffer wash + vortex",
    179: "Sonication-based",
    180: "Buffer wash + vortex",
    181: "Dry separation",
    182: "Bulk-near-root coring",
}

# Rows where I want to override or refine auto-derived fields.
# Each entry may set any of: confidence, coder_notes, buffer_identity,
# distance_threshold_mm, definition_type, definition_explicit, dry_subtype,
# bulk_soil_control_collected, sieving_used, sieve_mesh,
# subsequent_root_sterilization, wash_time_min, centrifugation_g_force.
OVERRIDES = {
    23: dict(confidence="low",
             coder_notes="Roots submerged in 'sterile water OR RNAlater'; "
                         "preservation present in some samples → preservation-embedded"),
    24: dict(confidence="low",
             coder_notes="Same as PRJNA710504; water-or-RNAlater"),
    66: dict(confidence="low",
             coder_notes="Only proximity definition (0-3 mm); no extraction step described"),
    68: dict(confidence="high",
             coder_notes="Authors explicitly state 'no mechanical extraction method was described'"),
    69: dict(confidence="low",
             coder_notes="Only 'collected from most adjacent soil surrounding the roots'; no separation step"),
    70: dict(confidence="medium",
             coder_notes="Only a rhizosphere definition (1 mm region); no extraction protocol given"),
    71: dict(confidence="medium",
             coder_notes="PVC pipe core 20 cm; rhizosphere=adhering to mangrove roots, no separation step"),
    78: dict(confidence="low",
             coder_notes="Sparse: 'manually extricated gently'; no explicit action described"),
    88: dict(confidence="high",
             coder_notes="Rhizosphere = brushing; sonication step is for rhizoplane (separate fraction)"),
    96: dict(buffer_identity="PBS"),
    109: dict(confidence="high",
              coder_notes="Authors state root-separation technique 'is not detailed'"),
    121: dict(confidence="low",
              coder_notes="'Epiphyte removal buffer' often contains Triton (surfactant) "
                          "but not stated in text → defaulted to Buffer wash + vortex"),
    123: dict(confidence="medium",
              coder_notes="Soil <2 mm from root collected with roots; no explicit separation step"),
    133: dict(confidence="medium",
              coder_notes="Only rhizosphere definition ('closely adhering to roots'); no method"),
    155: dict(confidence="low",
              coder_notes="Creek-water wash, rhizosphere+root pooled as one compartment"),
    161: dict(confidence="high",
              coder_notes="Tween 20 is for downstream root surface sterilization, not extraction"),
    165: dict(distance_threshold_mm=1.0,
              definition_type="distance",
              definition_explicit=True,
              buffer_identity="PBS",
              wash_time_min=0.25,  # 15 s vortex
              centrifugation_g_force=3200,
              sieving_used=True,
              sieve_mesh="100 µm"),
    179: dict(coder_notes="Tween 20 + sonication → sonication takes precedence per Q4"),
    182: dict(confidence="high",
              coder_notes="Authors explicitly state no rhizosphere/bulk separation"),
}


# ---------------------------------------------------------------------------
# Regex-based auxiliary feature detection
# ---------------------------------------------------------------------------
def pick_text(row: pd.Series) -> str:
    m = row.get("Rhizosphere_extraction_method")
    s = row.get("Rhizosphere_extraction_summary")
    if pd.notna(m) and str(m).strip():
        return str(m)
    if pd.notna(s) and str(s).strip():
        return str(s)
    return ""


def detect_buffer(text: str) -> str:
    t = text.lower()
    if re.search(r"\bsodium\s+pyrophosphate|napp[ii]\b", t):
        return "Na-pyrophosphate"
    if re.search(r"rnalater|lifeguard|glycerol\b|sm buffer\b", t):
        return "preservation"
    if re.search(r"mineral\s+medium", t):
        return "mineral-medium"
    if re.search(r"\bp(b|hosphate[- ]buffered)\s*s(aline|\b)|phosphate buffer|pbs\b", t):
        return "PBS"
    if re.search(r"\bnacl\b|saline|normal saline|0\.\d+\s*%\s*nacl|0\.9%\s*na", t):
        return "saline"
    if re.search(r"\b(sterile\s+)?(distilled\s+)?(deionized\s+)?(ultra-?pure\s+)?(nano-?pure\s+)?water\b"
                 r"|\bdi\s+water\b|creek water", t):
        return "water"
    if re.search(r"potassium\s+sulfate|k2so4|epiphyte\s+removal", t):
        return "other"
    return "none"


def detect_definition(text: str):
    """Return (definition_explicit, definition_type, distance_threshold_mm)."""
    t = text.lower()

    # Distance language
    m = re.search(r"(?:within|up to|approx(?:imately|\.)?|approximately|about|~|<)\s*"
                  r"(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?)\s*)?(mm|cm)\b"
                  r"[^.]*?(?:from|of|surround|adher|attach|thick|away from)\s+(?:the\s+)?(?:root|bulb|plant)",
                  t)
    if m:
        lo = float(m.group(1))
        hi = float(m.group(2)) if m.group(2) else lo
        val = max(lo, hi)  # upper bound when range
        unit = m.group(3)
        if unit == "cm":
            val *= 10
        return True, "distance", val

    # Pattern "X mm thick" or "X mm of soil"
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?)\s*)?mm\s+(?:thick|of\s+soil|of\s+attached|"
                   r"of\s+still\s+attached|attached|still\s+attached)", t)
    if m2:
        lo = float(m2.group(1))
        hi = float(m2.group(2)) if m2.group(2) else lo
        return True, "distance", max(lo, hi)

    # "X cm from root surface" without explicit "within"
    m3 = re.search(r"(\d+(?:\.\d+)?)\s*mm\s+(?:from|surround)", t)
    if m3:
        return True, "distance", float(m3.group(1))

    # Depth + radius pattern (depth and radius/diameter together)
    has_depth = re.search(r"\bdepth\s+of\s+\d+|\d+\s*cm\s+depth|at\s+a\s+depth|"
                          r"\d+\s*cm\s+under\s+the\s+ground|\b\d+[-–]\d+\s*cm\s+depth", t)
    has_radius = re.search(r"radius\s+of\s+\d+|diameter\s+of\s+\d+|\d+\s*cm\s+diameter|"
                           r"\d+\s*cm\s+(?:away\s+)?from\s+the\s+(?:trunk|plant|tree|stem|maize)", t)
    if has_depth and has_radius:
        return True, "depth-radius", None
    if has_depth:
        return True, "depth-radius", None

    # tight-vs-loose
    if re.search(r"tightly\s+adher|loosely\s+adher|tightly\s+attach|loosely\s+attach|"
                 r"firmly\s+attach|closely\s+adher|loosely[- ]bound|tightly\s+bound|"
                 r"loose\s+soil|loosely[- ]knitted|closely\s+knit", t):
        return True, "tight-vs-loose", None

    # Container/compartment (mesh bag, root mesh, rhizocompartment, root ball)
    if re.search(r"mesh\s+bag|rhizocompartment|root\s+mesh|root\s+ball|compartment", t):
        return True, "compartment-explicit", None

    return False, "none", None


def detect_wash_time(text: str) -> float | None:
    """Total wash/agitation time in minutes."""
    t = text.lower()
    total = 0.0
    found_any = False
    # minutes
    for m in re.finditer(
            r"(?:for|at\s+\d+\s*rpm\s+for)?\s*(\d+(?:\.\d+)?)\s*"
            r"(?:[-–]\s*\d+(?:\.\d+)?\s*)?\s*min(?:ute|s)?\b", t):
        try:
            total += float(m.group(1))
            found_any = True
        except ValueError:
            pass
    # seconds → minutes
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?\b(?!.*g)", t):
        try:
            total += float(m.group(1)) / 60.0
            found_any = True
        except ValueError:
            pass
    return round(total, 2) if found_any else None


def detect_centrifuge_g(text: str) -> float | None:
    t = text.lower()
    # Patterns: 10,000 g; 10000 × g; 3,200g; 3000 x g; 4000 rcf
    m = re.search(r"(\d{1,3}(?:[,]\d{3})*|\d+)\s*(?:×|x)?\s*(?:g\b|rcf\b)", t)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    # rpm not converted (varies with rotor)
    return None


def detect_sieving(text: str):
    """Detect a real sieve/strainer/mesh-filter step.

    Avoid 'filtered water' (filtered = adjective), 'root mesh' (the rhizosphere
    fraction name), 'mesh bag' (microcosm container).
    """
    t = text.lower()
    # Hard exclusions: phrases where 'mesh' is not a sieving step
    has_root_mesh_only = (
        re.search(r"\b(?:root\s+mesh|mesh\s+bag|24[- ]?µm\s+mesh\s+bag)\b", t)
        and not re.search(r"\bsieve|sieved|sieving|strainer|"
                          r"(?:sieved|filtered)\s+(?:with|through|using)\s+a?\s*\d|"
                          r"\d+[- ]?(?:mm|µm|um|micron|mesh)\s+(?:sieve|screen|strainer|mesh\s+filter|"
                          r"nylon\s+mesh|cell\s+strainer)", t)
    )
    if has_root_mesh_only:
        return False, None

    # Real sieving signals:
    sig = (
        re.search(r"\bsieve|sieved|sieving|sieves\b", t)
        or re.search(r"\bstrainer\b", t)
        or re.search(r"\b\d+[- ]?(?:mm|µm|um|micron)\s+(?:mesh|screen|nylon\s+mesh|cell\s+strainer|"
                     r"mesh\s+filter)\b", t)
        or re.search(r"\b\d+[- ]mesh\b", t)
        or re.search(r"filtered\s+through\b", t)
        or re.search(r"filtered\s*\(\s*\d+\s*(?:µm|um|mm)", t)
        or re.search(r"poured\s+through\s+a?\s*\d", t)
    )
    if not sig:
        return False, None

    mesh = None
    # "filtered (100 µm)" / "filtered through a 100 µm strainer"
    m_paren = re.search(r"filtered\s*\(\s*(\d+(?:\.\d+)?)\s*(?:µm|um|mm)\s*\)", t)
    if m_paren:
        mesh = f"{m_paren.group(1)} µm"
    # explicit mesh sizes
    m4 = re.search(r"(\d+(?:\.\d+)?)[- ]?(?:µm|um|micron)\s*(?:strainer|nylon|cell\s+strainer|"
                   r"mesh\s+filter|mesh|sieve|screen|filter)", t)
    if m4 and not mesh:
        mesh = f"{m4.group(1)} µm"
    if mesh is None:
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*mm\s+(?:mesh|sieve|screen|strainer|nylon\s+mesh)", t)
        if m2:
            mesh = f"{m2.group(1)} mm"
        else:
            m3 = re.search(r"(\d+)[- ]mesh", t)
            if m3:
                mesh = f"{m3.group(1)}-mesh"
            else:
                # "100-mm nylon mesh" likely a typo for µm; capture as-is
                m5 = re.search(r"(\d+)[- ]?mm\s+nylon\s+mesh", t)
                if m5:
                    mesh = f"{m5.group(1)} mm (likely typo for µm)"
    return True, mesh


def detect_bulk_control(text: str) -> bool:
    t = text.lower()
    # Positive signals: bulk soil collected/sampled as control
    if re.search(
            r"bulk\s+soil\s+(?:was\s+)?(?:sampled|collected|controls?|samples\s+were\s+collected|"
            r"obtained|labelled|labeled)",
            t):
        return True
    if re.search(r"bulk\s+soil\s+from\s+(?:the\s+same|nearby|the\s+edge|the\s+periphery)", t):
        return True
    if re.search(r"bare\s+soil\s+(?:from|samples|was)", t):
        return True
    if re.search(r"background\s+soil|non-root(?:ed|-free)\s+(?:soil|sediment)\s+(?:was|samples|"
                 r"were)", t):
        return True
    if re.search(r"five\s+bulk\s+soil|three\s+bulk\s+soil|paired\s+sample\s+of\s+sediment", t):
        return True
    # Negative: 'bulk soil was removed' (removed during processing, not collected)
    if re.search(r"bulk\s+soil\s+was\s+(?:manually\s+)?removed\b", t) and not re.search(
            r"bulk\s+soil\s+(?:sampled|collected|frozen)", t):
        return False
    return False


def detect_dry_subtype(text: str) -> str | None:
    t = text.lower()
    has_shake = bool(re.search(r"shak|slapped|dropped|drag|kneading|patting", t))
    has_brush = bool(re.search(r"brush|scrape|scrap|spatula|knife|spoon|tweezer|scoopula|sterile\s+fork", t))
    if has_shake and has_brush:
        return "both"
    if has_brush:
        return "brush_or_scrape"
    if has_shake:
        return "shake_only"
    return "shake_only"  # default for dry without explicit cue


def detect_root_sterilization(text: str) -> bool:
    t = text.lower()
    return bool(re.search(r"surface[- ]steril|sodium\s+hypochlorite|bleach|"
                          r"75%\s+alcohol|70%\s+ethanol\s+(?:rinse|wash)|naclo", t))


def default_confidence(text: str, bucket: str) -> str:
    n = len(text)
    if bucket == "Not described":
        return "high"
    if n < 80:
        return "medium"
    if n < 50:
        return "low"
    return "high"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"input XLSX (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"output XLSX (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--expect-rows", type=int, default=None,
                        help="if given, assert input row count matches "
                             "(catches accidental sheet drift)")
    args = parser.parse_args()

    df = pd.read_excel(args.input, engine="openpyxl")
    if args.expect_rows is not None:
        assert len(df) == args.expect_rows, \
            f"Expected {args.expect_rows} rows, got {len(df)}"
    if len(df) != len(BUCKETS):
        print(f"WARNING: input has {len(df)} rows but BUCKETS{{}} covers "
              f"{len(BUCKETS)} indices. Any uncovered indices will raise KeyError.")

    new_cols = {
        "bucket": [],
        "definition_explicit": [],
        "definition_type": [],
        "distance_threshold_mm": [],
        "buffer_identity": [],
        "wash_time_min": [],
        "centrifugation_g_force": [],
        "bulk_soil_control_collected": [],
        "dry_subtype": [],
        "sieving_used": [],
        "sieve_mesh": [],
        "subsequent_root_sterilization": [],
        "coder_notes": [],
        "confidence": [],
    }

    for i, row in df.iterrows():
        text = pick_text(row)
        bucket = BUCKETS[i]

        def_explicit, def_type, dist_mm = detect_definition(text)
        buffer_id = detect_buffer(text) if bucket not in ("Not described",
                                                          "Bulk-near-root coring",
                                                          "Dry separation") else (
            "none" if bucket != "Dry separation" else detect_buffer(text) if False else "none"
        )
        # Buffer identity: for Dry / Bulk-near-root / Not described, default 'none'
        # unless surfactant / preservation present (then it would be a different bucket).
        if bucket in ("Not described", "Bulk-near-root coring", "Dry separation"):
            buffer_id = "none"
        else:
            buffer_id = detect_buffer(text)

        wash_min = detect_wash_time(text) if bucket not in ("Not described",
                                                            "Bulk-near-root coring",
                                                            "Dry separation") else None
        cent_g = detect_centrifuge_g(text)
        siev, mesh = detect_sieving(text)
        bulk_ctl = detect_bulk_control(text)
        dry_st = detect_dry_subtype(text) if bucket == "Dry separation" else None
        root_steril = detect_root_sterilization(text)
        conf = default_confidence(text, bucket)

        # Apply per-row overrides
        ov = OVERRIDES.get(i, {})
        if "buffer_identity" in ov:
            buffer_id = ov["buffer_identity"]
        if "distance_threshold_mm" in ov:
            dist_mm = ov["distance_threshold_mm"]
        if "definition_type" in ov:
            def_type = ov["definition_type"]
        if "definition_explicit" in ov:
            def_explicit = ov["definition_explicit"]
        if "dry_subtype" in ov:
            dry_st = ov["dry_subtype"]
        if "bulk_soil_control_collected" in ov:
            bulk_ctl = ov["bulk_soil_control_collected"]
        if "sieving_used" in ov:
            siev = ov["sieving_used"]
        if "sieve_mesh" in ov:
            mesh = ov["sieve_mesh"]
        if "subsequent_root_sterilization" in ov:
            root_steril = ov["subsequent_root_sterilization"]
        if "wash_time_min" in ov:
            wash_min = ov["wash_time_min"]
        if "centrifugation_g_force" in ov:
            cent_g = ov["centrifugation_g_force"]
        if "confidence" in ov:
            conf = ov["confidence"]
        notes = ov.get("coder_notes", "")

        new_cols["bucket"].append(bucket)
        new_cols["definition_explicit"].append(def_explicit)
        new_cols["definition_type"].append(def_type)
        new_cols["distance_threshold_mm"].append(dist_mm)
        new_cols["buffer_identity"].append(buffer_id)
        new_cols["wash_time_min"].append(wash_min)
        new_cols["centrifugation_g_force"].append(cent_g)
        new_cols["bulk_soil_control_collected"].append(bulk_ctl)
        new_cols["dry_subtype"].append(dry_st)
        new_cols["sieving_used"].append(siev)
        new_cols["sieve_mesh"].append(mesh)
        new_cols["subsequent_root_sterilization"].append(root_steril)
        new_cols["coder_notes"].append(notes)
        new_cols["confidence"].append(conf)

    out = df.copy()
    for k, v in new_cols.items():
        out[k] = v

    # ---- Validation ----
    assert len(out) == 183
    assert out["bucket"].notna().all()
    print("=" * 70)
    print("BUCKET COUNTS:")
    counts = out["bucket"].value_counts()
    expected = {
        "Not described": (18, 22),
        "Bulk-near-root coring": (20, 25),
        "Dry separation": (40, 50),
        "Buffer wash + vortex": (60, 70),
        "Sonication-based": (6, 10),
        "Surfactant-assisted": (4, 8),
        "Preservation-embedded": (3, 5),
    }
    for b, (lo, hi) in expected.items():
        n = int(counts.get(b, 0))
        flag = ""
        if n < lo * 0.5 or n > hi * 1.5:
            flag = "  <-- MORE THAN 50% OFF expected range"
        elif n < lo or n > hi:
            flag = f"  (outside expected [{lo}, {hi}])"
        print(f"  {b:<28s} {n:>3d}{flag}")
    print(f"  TOTAL                          {len(out)}")

    # Low-confidence rows
    print()
    print("=" * 70)
    print("LOW-CONFIDENCE ROWS (for human review):")
    low = out[out["confidence"] == "low"]
    print(f"({len(low)} rows)")
    for _, r in low.iterrows():
        txt = pick_text(r).replace("\n", " ")
        print(f"  [{r['bioproject']}] bucket={r['bucket']}: {txt[:160]}")
        if r["coder_notes"]:
            print(f"    note: {r['coder_notes']}")

    # 5-row sample per bucket
    print()
    print("=" * 70)
    print("5-ROW SAMPLE PER BUCKET:")
    for b in expected:
        print(f"\n--- {b} ---")
        sub = out[out["bucket"] == b].head(5)
        for _, r in sub.iterrows():
            txt = pick_text(r).replace("\n", " ")
            print(f"  [{r['bioproject']}] {txt[:140]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(args.output, index=False, engine="openpyxl")
    print()
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
