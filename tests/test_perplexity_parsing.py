import json
from pathlib import Path
from lib.perplexity import parse_sonar_paper_response

FIX = Path(__file__).parent / "fixtures" / "sonar_response_minimal.json"


def test_parse_sonar_paper_response_extracts_doi_and_confidence():
    raw = json.loads(FIX.read_text())
    parsed = parse_sonar_paper_response(raw)
    assert parsed["doi"] == "10.1038/s41586-024-08123-w"
    assert parsed["pmid"] == "39449039"
    assert parsed["confidence"] == "high"
    assert "rhizosphere" in parsed["abstract"]
