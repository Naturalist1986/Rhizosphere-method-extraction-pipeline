from pathlib import Path
from lib.methods_extract import extract_rhizosphere_method

FIX = Path(__file__).parent / "fixtures"


def test_good_passage_high_confidence():
    txt = (FIX / "methods_pdf_text_good.txt").read_text()
    out = extract_rhizosphere_method(txt)
    assert out["confidence"] in {"high", "medium"}
    assert out["sampling_depth_cm"] is not None
    assert "rhizosphere" in out["verbatim_excerpt"].lower()


def test_minimal_passage_low_confidence():
    txt = (FIX / "methods_pdf_text_minimal.txt").read_text()
    out = extract_rhizosphere_method(txt)
    assert out["confidence"] == "low"


def test_no_header_still_finds_protocol():
    txt = (FIX / "methods_pdf_text_noheader.txt").read_text()
    out = extract_rhizosphere_method(txt)
    assert out["verbatim_excerpt"]
