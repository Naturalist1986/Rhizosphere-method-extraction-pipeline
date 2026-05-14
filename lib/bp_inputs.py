from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


_BP_KEY_CANDIDATES = ("bioproject", "study_accession", "secondary_study_accession")


def _list_to_bp_dict(records: list[dict]) -> dict[str, dict]:
    """Convert a list of records to {bioproject: first_record} using the first recognised BP key."""
    bp_key = next((k for k in _BP_KEY_CANDIDATES if k in (records[0] if records else {})), None)
    if bp_key is None:
        return {}
    result: dict[str, dict] = {}
    for r in records:
        bp = r.get(bp_key)
        if bp and bp not in result:
            result[bp] = r
    return result


def load_bioprojects(csv_path: Path, enrichment_paths: list[Path]) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    df = df.drop_duplicates(subset=["bioproject"]).set_index("bioproject", drop=False)
    for ep in enrichment_paths:
        if not Path(ep).exists():
            continue
        raw = json.loads(Path(ep).read_text())
        rec: dict[str, dict] = raw if isinstance(raw, dict) else _list_to_bp_dict(raw)
        for bp, fields in rec.items():
            if bp not in df.index:
                continue
            for k, v in fields.items():
                col = f"enrich_{k}"
                if col not in df.columns:
                    df[col] = ""
                if not df.at[bp, col]:
                    df.at[bp, col] = str(v) if v is not None else ""
    return df
