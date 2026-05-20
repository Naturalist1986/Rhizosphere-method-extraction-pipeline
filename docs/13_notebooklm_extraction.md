# Stage 13 — NotebookLM-assisted method extraction [HUMAN STEP]

After stage 12, the master XLSX has one row per BioProject with a paper, a
Zotero key, and a PDF either attached in Zotero or stored locally under
`relevant_papers/<zotero_item_key>.pdf`. The LLM extraction in stage 11
captures a verbatim slice of the paper, but for many papers the rhizosphere
sampling protocol is split across multiple paragraphs, hidden in a "Materials
and Methods" subsection, or simply paraphrased awkwardly. Stage 13 uses
[NotebookLM](https://notebooklm.google.com) as a higher-recall second-pass
summarizer.

## Why NotebookLM, not another LLM call

- NotebookLM cites every source paragraph it summarizes, which makes it easy
  to verify each per-paper summary against the actual PDF.
- It handles large multi-PDF source sets (≥ 100 PDFs per notebook) without
  context-window juggling.
- It is run interactively, so we can iterate on the prompt if the first
  output is too vague.

## Procedure

1. Collect every PDF the pipeline successfully placed in Zotero or in
   `relevant_papers/`. Name each PDF with the BioProject accession or the
   Zotero item key so the output rows are traceable.
2. Create a new NotebookLM notebook called
   `Rhizosphere methods — <YYYY-MM-DD>` and upload all PDFs as sources.
3. Run the following prompt verbatim:

   > For each source paper, write one short paragraph (1–3 sentences) that
   > describes exactly how the authors collected and separated the
   > rhizosphere soil from roots. Mention any buffers, surfactants,
   > sonication, sieving, centrifugation, and how the rhizosphere was
   > defined (e.g. "tightly adhering", "within 1 mm", "0–15 cm depth").
   > Quote the paper's own wording where useful. Label each paragraph with
   > the source PDF filename. If a paper does not describe the method,
   > write "Not described" for that source.

4. Save the resulting answer as a `.docx` file (NotebookLM's "Save to
   Notes" → export). The file in this repository's parent project is
   `Here is a summary of the rhizosphere extraction sampling methods for
   each source provided.docx`.
5. Run `merge_docx_summaries.py` (kept in the parent project, not in this
   repo because it is a one-off transform) to push each labelled paragraph
   into the `Rhizosphere_extraction_summary` column of the master XLSX,
   keyed by BioProject. Empty paragraphs and `Not described` rows are
   preserved as-is so stage 14 can find them.

## Output

The master XLSX gains a new column:

| Column | Description |
|---|---|
| `Rhizosphere_extraction_summary` | NotebookLM's per-paper paragraph, or `Not described` |

This column will be filled for most rows that had a PDF. Rows where the
paper cited a different study, where the protocol was in a supplementary
file NotebookLM did not see, or where the wording was "as described
previously" remain blank or `Not described` — those are the input to
stage 14.
