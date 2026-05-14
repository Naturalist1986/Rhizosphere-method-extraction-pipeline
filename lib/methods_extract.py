from __future__ import annotations
import re

METHODS_START = re.compile(
    r'\n[ \t]*(?:\d[\d.]*[ \t]+)?(?:Materials?\s+and\s+)?Methods?\s*\n',
    re.IGNORECASE)
METHODS_END = re.compile(
    r'\n[ \t]*(?:\d[\d.]*[ \t]+)?(?:Results?|Discussion|Conclusions?|'
    r'Acknowledgements?|Funding|Author\s+contributions?|Data\s+availability)\s*\n',
    re.IGNORECASE)
DEPTH_RE = re.compile(r'(\d+\s*[–-]\s*\d+)\s*cm', re.IGNORECASE)
RHIZO_KEYWORDS = ("rhizosphere", "root-adhering", "tightly adhering", "shaken from roots",
                  "rhizoplane", "root system", "loosely adhering soil", "root-adhering soil")


def _methods_slice(text: str) -> str:
    m = METHODS_START.search(text)
    if not m:
        return text
    start = m.end()
    end = METHODS_END.search(text, pos=start)
    return text[start: end.start() if end else min(len(text), start + 20000)]


def _score_sentences(slab: str) -> list[tuple[float, str]]:
    sents = re.split(r'(?<=[.!?])\s+', slab)
    scored = []
    for s in sents:
        low = s.lower()
        hits = sum(k in low for k in RHIZO_KEYWORDS)
        if hits:
            scored.append((hits + 0.1 * ("soil" in low) + 0.1 * ("dna" in low), s.strip()))
    scored.sort(reverse=True)
    return scored


def extract_rhizosphere_method(full_text: str) -> dict:
    slab = _methods_slice(full_text)
    scored = _score_sentences(slab)
    verbatim = " ".join(s for _, s in scored[:4])
    depth = None
    m = DEPTH_RE.search(slab)  # search full methods section, not just rhizo sentences
    if m:
        depth = m.group(1).replace(" ", "")
    top_score = scored[0][0] if scored else 0
    if top_score >= 2:
        conf = "high"
    elif top_score >= 1:
        conf = "medium"
    else:
        conf = "low"
    return {
        "verbatim_excerpt": verbatim[:1500],
        "summary_one_sentence": scored[0][1] if scored else "",
        "sampling_depth_cm": depth,
        "root_processing": "shaken" if any("shak" in s.lower() for _, s in scored[:3]) else
                           ("washed" if any("wash" in s.lower() for _, s in scored[:3]) else None),
        "sieve_or_fraction": None,
        "replication": None,
        "confidence": conf,
    }
