from pathlib import Path
import pandas as pd
from lib.bp_inputs import load_bioprojects


def test_load_bioprojects_has_one_row_per_bp(tmp_path):
    csv = tmp_path / "bps.csv"
    csv.write_text(
        "bioproject,study_title,n_samples,paper_pmid,paper_doi,paper_title,paper_abstract_excerpt,search_status\n"
        "PRJNA1,Test rhizo,5,,,,,pending\n"
        "PRJNA2,Other,3,,,,,pending\n"
    )
    df = load_bioprojects(csv, enrichment_paths=[])
    assert list(df["bioproject"]) == ["PRJNA1", "PRJNA2"]
    assert df.index.is_unique
