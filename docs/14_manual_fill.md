# Stage 14 — Manual fill-in of missing methods [HUMAN STEP]

After stage 13, two failure modes remain in `Rhizosphere_extraction_summary`:

1. **Empty / "Not described"** — the paper itself did not write out a
   protocol in the Methods section that NotebookLM picked up.
2. **Reference-only** — the paper says something like *"rhizosphere
   sampling was performed as described in Edwards et al. 2015"* or *"see
   Supplementary Methods"* without restating the protocol.

Stage 14 closes those gaps by chasing the citation chain or the
supplementary file by hand. The outputs land in a separate column,
`Rhizosphere_extraction_method`, so the provenance (NotebookLM vs human
curator) stays distinct.

## Procedure

For each row where `Rhizosphere_extraction_summary` is blank or reads
`Not described`:

1. Open the PDF in Zotero (or `relevant_papers/<zotero_item_key>.pdf`).
2. If the Methods section refers to a **cited study**, fetch that paper
   from Zotero (or via DOI), find the cited protocol, and copy the
   relevant paragraph verbatim into `Rhizosphere_extraction_method`. Add
   a parenthetical note such as `(method per Edwards et al. 2015,
   doi:10.1073/pnas.1414592112)` so future readers can trace it.
3. If the paper says **"see Supplementary"**, download the supplementary
   PDF/DOCX from the publisher and paste the rhizosphere passage into
   `Rhizosphere_extraction_method`.
4. If the paper genuinely never describes any extraction step — only
   defines what "rhizosphere" means, or only mentions the depth/distance —
   leave the cell blank. Stage 15 will pick this up as
   `bucket = "Not described"`.
5. If both `Rhizosphere_extraction_summary` and
   `Rhizosphere_extraction_method` end up populated for the same row
   (e.g. NotebookLM gave a vague paragraph and the curator added the
   verbatim text), keep both. Stage 15 prefers `*_method` because the
   verbatim text is less likely to drop reagent names like Silwet L-77 or
   Tween 20.

## Output

The master XLSX gains a second method column:

| Column | Description |
|---|---|
| `Rhizosphere_extraction_method` | Verbatim Methods-section text (from the paper itself, a cited paper, or supplementary), added by human curator |

After stages 13 and 14, every row that had a PDF should have at least one
of `Rhizosphere_extraction_summary` or `Rhizosphere_extraction_method`
populated, or be explicitly marked `Not described`.

## Result XLSX

The combined output of stages 11–14 is the manual-review workbook
`rhizosphere_methods_review_manual.xlsx`, with one row per BioProject
and these key columns:

- `bioproject`, `paper_title`, `paper_doi`, `paper_pmid`,
  `zotero_item_key`, `pdf_available`
- `Rhizosphere_extraction_summary` (from stage 13)
- `Rhizosphere_extraction_method` (from stage 14)

This is the direct input to stage 15.
