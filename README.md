# Rhizosphere Method Extraction Pipeline

An end-to-end pipeline that takes a list of NCBI BioProject IDs, discovers their associated publications via ENA, NCBI elink, and Perplexity Sonar, syncs candidate papers into a Zotero collection, and then uses an LLM to extract rhizosphere soil sampling methods from full-text PDFs into a master XLSX.

---

## Pipeline overview

```
00_extract_existing.py   → extract known run/BioProject/BioSample IDs from existing dataset
01_search_ena.py         → search ENA API for rhizosphere/root metagenome runs
02_search_ncbi.py        → search NCBI SRA (supplementary, US-specific submissions)
03_parse_img.py          → parse manually-downloaded IMG/JGI metadata CSV
04_merge_dedupe.py       → merge ENA + NCBI + IMG; remove already-known accessions
05_quality_filter.py     → keyword-based ACCEPT/FLAG/REJECT quality filter
06_fetch_papers.py       → NCBI elink: BioProject → PubMed paper
07_build_xlsx.py         → build review XLSX from filtered candidates
08_perplexity_paper_search.py  → Perplexity Sonar: fill paper gaps for unresolved BPs
09_zotero_sync.py        → push candidate papers into Zotero collection
09b_verify_dois.py       → verify each DOI resolves; flag broken ones for correction [RECOMMENDED]
10_pdf_download_report.py      → report which Zotero items still need PDFs [HUMAN STEP]
11_extract_methods.py    → LLM-based method extraction from PDFs
12_merge_into_master.py  → merge extracted methods into master XLSX
```

---

## Quickstart

### Prerequisites

- Python ≥ 3.12
- `pip install -r requirements.txt`
- Copy `.env.example` → `.env` and fill in API keys

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Running the full pipeline

Run each stage in order. Each script is self-contained and resumable.

```bash
# Stage 00: extract existing accessions for deduplication
python 00_extract_existing.py --metadata /path/to/metadata_unified.xlsx

# Stage 01: ENA search (writes data/ena_candidates.json)
python 01_search_ena.py

# Stage 02: NCBI SRA search (writes data/ncbi_candidates.json)
python 02_search_ncbi.py

# Stage 03: IMG/JGI parse (requires manual CSV download from img.jgi.doe.gov)
python 03_parse_img.py

# Stage 04: merge and deduplicate (writes data/merged_candidates.csv)
python 04_merge_dedupe.py

# Stage 05: quality filter (writes data/filtered_candidates.csv)
python 05_quality_filter.py

# Stage 06: fetch PubMed papers via NCBI elink (writes data/filtered_with_papers.csv)
python 06_fetch_papers.py

# Stage 07: build review XLSX (writes data/candidates_review.xlsx)
python 07_build_xlsx.py

# Stage 08: Perplexity Sonar for remaining unresolved BioProjects
python 08_perplexity_paper_search.py --batch 100 --sleep 1.5

# Stage 09: sync candidate papers to Zotero
python 09_zotero_sync.py --min-conf medium

# Stage 09b: verify DOIs resolve (recommended before downloading PDFs)
# Reviews data/doi_failures.csv and correct any broken DOIs in Zotero first
python 09b_verify_dois.py

# Stage 10: generate PDF download report [HUMAN STEP — see below]
python 10_pdf_download_report.py

# Stage 11: extract sampling methods from PDFs
python 11_extract_methods.py

# Stage 12: merge methods into master XLSX
python 12_merge_into_master.py --master /path/to/rhizosphere_combined.xlsx
```

---

## Stage reference

| Stage | Script | Input | Output | Description |
|---|---|---|---|---|
| 00 | `00_extract_existing.py` | `metadata_unified.xlsx` | `data/existing_*.txt` | Extract known IDs for deduplication |
| 01 | `01_search_ena.py` | ENA API | `data/ena_candidates.json` | Search ENA for rhizosphere runs |
| 02 | `02_search_ncbi.py` | NCBI SRA API | `data/ncbi_candidates.json` | Search NCBI SRA (US-specific) |
| 03 | `03_parse_img.py` | Manual IMG CSV | `data/img_candidates.json` | Parse IMG/JGI metadata |
| 04 | `04_merge_dedupe.py` | Stages 00–03 | `data/merged_candidates.csv` | Merge, deduplicate at run/BioSample level |
| 05 | `05_quality_filter.py` | Stage 04 | `data/filtered_candidates.csv` | Keyword ACCEPT/FLAG/REJECT filter |
| 06 | `06_fetch_papers.py` | Stage 05 | `data/filtered_with_papers.csv` | NCBI elink BioProject→PubMed lookup |
| 07 | `07_build_xlsx.py` | Stage 06 | `data/candidates_review.xlsx` | Build two-sheet review workbook |
| 08 | `08_perplexity_paper_search.py` | `bioprojects_to_search.csv` | `data/perplexity_paper_cache.json` | Perplexity Sonar paper search |
| 09 | `09_zotero_sync.py` | Stages 06+08 | `data/candidates_zotero_manifest.json` | Push papers to Zotero |
| 09b | `09b_verify_dois.py` | Stage 09 manifest | `data/doi_failures.csv` | HTTP-verify each DOI; flag broken ones |
| 10 | `10_pdf_download_report.py` | Stage 09 manifest | `data/pdfs_needed.csv` | Report missing PDFs **[HUMAN STEP]** |
| 11 | `11_extract_methods.py` | PDFs + Stage 09 | `data/bp_methods_<date>.json` | LLM method extraction |
| 12 | `12_merge_into_master.py` | Stage 11 + master xlsx | `rhizosphere_combined_<date>.xlsx` | Merge into master dataset |

---

## Input format

`bioprojects_to_search.csv` has one row per BioProject. Required columns:

| Column | Description |
|---|---|
| `bioproject` | NCBI BioProject accession (e.g. `PRJNA12345`) |
| `study_title` | Study title from ENA/NCBI |
| `n_samples` | Number of SRA run accessions in the study |
| `paper_pmid` | PubMed ID if already known (leave blank otherwise) |
| `paper_doi` | DOI if already known |
| `paper_title` | Paper title if already known |
| `paper_abstract_excerpt` | First ~400 chars of abstract (optional, improves Sonar queries) |
| `search_status` | `pending` \| `done` \| `skip` |

---

## Environment variables

Copy `.env.example` to `.env` and set:

| Variable | Required for | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Stages 08, 11 | OpenRouter key for Perplexity Sonar and LLM extraction |
| `ZOTERO_API_KEY` | Stages 09–11 | Zotero Web API key |
| `ZOTERO_LIBRARY_ID` | Stages 09–11 | Numeric Zotero library ID |
| `ENTREZ_EMAIL` | Stages 02, 06 | Email for NCBI Entrez (required by NCBI policy) |
| `METADATA_XLSX` | Stage 00 | Path to existing metadata xlsx (alternative to `--metadata`) |
| `MASTER_XLSX` | Stage 12 | Path to master xlsx (alternative to `--master`) |

---

## Zotero integration

Stages 09–11 use a dedicated Zotero collection named `Soil_Rhizosphere_sampling_methods_candidates` in your personal library. Create the collection in Zotero before running stage 09.

Stage 09 upserts papers (DOI-matched, no duplicates) and writes `data/candidates_zotero_manifest.json` tracking each BioProject → Zotero item key mapping.

Stage 11 reads PDF full-text from Zotero attachments via the API. If Zotero has not indexed a PDF, you can also place it as `relevant_papers/<zotero_item_key>.pdf` for local fallback.

---

## PDF download workflow (stage 10 pause)

Stage 10 prints a CSV of items that still need PDFs. The pipeline must pause here for manual action:

1. Download each PDF (use the `open_url` column, which is `https://doi.org/<doi>`)
2. Either attach it to the Zotero item directly, **or** drop it as `relevant_papers/<zotero_item_key>.pdf`
3. Re-run stage 11

---

## Output

`rhizosphere_combined_<date>.xlsx` adds these columns to the master dataset:

| Column | Values | Description |
|---|---|---|
| `Rhizosphere_Method` | `Good` / `Acceptable` / `Weak` / `NoPDF` | Confidence-derived label |
| `sampling_method` | free text | Verbatim excerpt from paper |
| `paper_pmid` | string | PubMed ID |
| `paper_doi` | string | DOI |
| `paper_title` | string | Paper title |
| `_zotero_item_key` | string | Zotero item key |
| `pdf_available` | bool | Whether a PDF was found |
| `notes` | string | Depth, root processing, source method |

---

## Tests

```bash
pytest tests/ -v
```

4 test modules covering: BioProject CSV loading, Perplexity response parsing, Zotero upsert logic, and methods extraction.

---

## License

MIT — see [LICENSE](LICENSE).
