#!/usr/bin/env python3
"""Stage 09b — verify that every DOI in the Zotero manifest actually resolves.

Sends an HTTP HEAD to https://doi.org/<doi> and marks each entry as:
  doi_verified: True   — resolves to a paper page (2xx or 3xx redirect)
  doi_verified: False  — 4xx/5xx or connection error

Entries with doi_verified=False are written to data/doi_failures.csv so you
can correct them before running stage 10 (PDF download) and stage 11 (extraction).

Updates data/candidates_zotero_manifest.json in place.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent / "data"
MANIFEST = DATA / "candidates_zotero_manifest.json"
FAILURES_OUT = DATA / "doi_failures.csv"

TIMEOUT = 10
SLEEP = 0.3
DOI_PREFIX = "https://doi.org/"

HEADERS = {
    "User-Agent": "rhizosphere-pipeline/1.0 (DOI verification; mailto:your@email.com)"
}


def check_doi(doi: str) -> tuple[bool, int | str]:
    """Return (ok, status_or_error) for a DOI string."""
    if not doi or doi.strip() in ("", "None", "nan"):
        return False, "empty"
    url = DOI_PREFIX + doi.strip()
    try:
        r = requests.head(url, allow_redirects=True, timeout=TIMEOUT, headers=HEADERS)
        ok = r.status_code < 400
        return ok, r.status_code
    except requests.exceptions.ConnectionError as e:
        return False, f"connection_error: {e}"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def main() -> None:
    if not MANIFEST.exists():
        sys.exit(f"manifest not found: {MANIFEST} — run stage 09 first")

    manifest: list[dict] = json.loads(MANIFEST.read_text())

    to_check = [m for m in manifest if m.get("doi")]
    no_doi   = [m for m in manifest if not m.get("doi")]
    print(f"{len(manifest)} manifest entries: {len(to_check)} have DOIs, "
          f"{len(no_doi)} have no DOI (skipped)")

    failures: list[dict] = []
    for i, entry in enumerate(to_check, 1):
        doi = entry["doi"]
        ok, status = check_doi(doi)
        entry["doi_verified"] = ok
        entry["doi_status"] = str(status)
        mark = "OK" if ok else "FAIL"
        print(f"[{i}/{len(to_check)}] {mark} {status:>5}  {doi}")
        if not ok:
            failures.append({
                "bioproject": entry.get("bioproject", ""),
                "doi": doi,
                "status": status,
                "title": (entry.get("title") or "")[:100],
                "zotero_item_key": entry.get("zotero_item_key", ""),
            })
        time.sleep(SLEEP)

    # entries with no DOI get a neutral marker
    for entry in no_doi:
        entry.setdefault("doi_verified", None)
        entry.setdefault("doi_status", "no_doi")

    MANIFEST.write_text(json.dumps(manifest, indent=2))

    with FAILURES_OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bioproject", "doi", "status", "title", "zotero_item_key"])
        w.writeheader()
        w.writerows(failures)

    n_ok   = sum(1 for m in to_check if m.get("doi_verified"))
    n_fail = len(failures)
    print(f"\n{n_ok}/{len(to_check)} DOIs verified OK, {n_fail} failed → {FAILURES_OUT}")
    if failures:
        print("Review doi_failures.csv, correct DOIs in Zotero, then re-run this stage "
              "before proceeding to stage 10.")


if __name__ == "__main__":
    main()
