from __future__ import annotations
import json, os, re, time
from typing import Optional
import litellm

DEFAULT_MODEL = "openrouter/perplexity/sonar-pro-search"

PROMPT = """You are a biomedical literature locator.
Given the following NCBI BioProject metadata, identify the single most likely primary publication (peer-reviewed paper OR bioRxiv/medRxiv preprint) that produced the deposited data.

BioProject: {bioproject}
Study title: {study_title}
Organism: {organism}
Sample count: {n_samples}
Center / submitter: {center}
Additional context: {extra}

Return ONLY a fenced ```json block with these fields:
  doi          - DOI string, no URL prefix, or null
  pmid         - PubMed ID as string, or null
  title        - paper title, or null
  abstract     - first 400 chars of the paper abstract, or null
  confidence   - one of "high" | "medium" | "low"
  reasoning    - one sentence explaining your match (cite where the BioProject appears)
If no candidate is found, set all fields except confidence (which must be "low") to null."""

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_sonar_paper_response(raw: dict) -> dict:
    content = raw["choices"][0]["message"]["content"]
    m = _JSON_BLOCK.search(content)
    payload = m.group(1) if m else content
    return json.loads(payload)


def search_paper_for_bp(bioproject: str, study_title: str, organism: str,
                        n_samples: str, center: str, extra: str,
                        model: str = DEFAULT_MODEL, max_retries: int = 3) -> dict:
    prompt = PROMPT.format(bioproject=bioproject, study_title=study_title,
                           organism=organism, n_samples=n_samples,
                           center=center, extra=extra)
    last = None
    for attempt in range(max_retries):
        try:
            resp = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                api_key=os.environ["OPENROUTER_API_KEY"],
                temperature=0,
            )
            return parse_sonar_paper_response(resp.model_dump())
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"sonar search failed for {bioproject}: {last}")
