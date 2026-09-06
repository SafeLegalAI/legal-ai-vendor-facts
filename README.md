# Legal AI vendor facts

**What each legal-AI vendor documents on its own public pages — pricing, contract terms, security certifications, training and retention commitments, data residency, accuracy claims — one fact per row, with the quote that identifies it, the page it came from, an archived copy and the date we read it.** Facts, never a ranking.

Published by [SafeLegalAI](https://safelegalai.com) (Cognesio LLP). Canonical pages: [safelegalai.com/tools](https://safelegalai.com/tools) (one record per tool) and [safelegalai.com/tools/compare](https://safelegalai.com/tools/compare) (documented facts side by side). Mirror: [huggingface.co/datasets/safelegalaidata/legal-ai-vendor-facts](https://huggingface.co/datasets/safelegalaidata/legal-ai-vendor-facts).

## Files

| file | what |
|---|---|
| `data/facts.jsonl` · `.csv` · `.parquet` | every fact — `fact_id`, `tool_id`, `field`, `value`, `status` (`stated` · `implied` · `not-found` · `contradictory`), `quote` (≤ 25 words, verbatim), `source_url`, `pages_checked`, `archive_url`, `fetched_at`, `page_dated`, `note` |
| `data/by-tool/<tool_id>.json` | the same facts grouped per tool — the provenance object each SafeLegalAI tool record links to |
| `data/REVIEW-QUEUE.json` | rows the editor re-opens before anything is quoted on the site: every accuracy/hallucination claim, every contradiction, and every point where the audit disagrees with an existing record |
| `schema/fact.schema.json` | the row schema and the `field` checklist |
| `AGENT-BRIEF.md` | the collection rules (public pages only, no accounts, ≤ 25-word quotes, identified crawler, ≤ 1 req/s, archive every page) |
| `pipeline/merge.py` | merges collection output, writes the tables, and patches SafeLegalAI tool records — a documented yes/no only ever replaces "unknown"; existing values are never overwritten; disagreements are listed, not applied |

## How to read a row

- `status: stated` — a sentence on the page says it; the `quote` is that sentence's operative words.
- `status: implied` — a badge, logo or list implies it without a sentence (e.g. a SOC 2 logo).
- `status: not-found` — we read the pages in `pages_checked` on `fetched_at` and none addressed the point. **This is not an assertion that the vendor lacks the certification, term or price** — only that it was not published where we looked.
- `status: contradictory` — two vendor pages disagree; `note` says how.
- `pricing.published = "no"` means no concrete price appears on the vendor's public pages; that absence is itself a documented fact.
- Accuracy and hallucination figures are recorded as the vendor's own statements (`accuracy.claim`) with whether a method is published (`accuracy.method_published`); they are not endorsed, tested or compared.

## Method

128 tools from the SafeLegalAI legal-tech record (the affiliated product LegalAI Space is excluded by policy). Eight collection passes on 6 September 2026 read each vendor's pricing, security/trust, terms, privacy, DPA, sub-processor and certification pages (public pages only; identified `SafeLegalAI-Bot`; ≤ 1 request/s per host; no accounts, logins or paywalls) and wrote one row per checklist field, requesting a Wayback Machine snapshot for every page relied on (82% archived). `pipeline/merge.py` merged and de-duplicated the rows and patched the site records, filling only unknown values and appending a provenance source pointing at `data/by-tool/<tool_id>.json`. The editor works through `data/REVIEW-QUEUE.json` before any claim is quoted in prose.

## Licence, disclaimer and notices

Data: **CC BY 4.0** — attribute *SafeLegalAI (safelegalai.com), published by Cognesio LLP* and link here or to the tool record. Code: Apache-2.0. Both licences exclude warranties. Quotations are the vendors' words, used briefly for identification and verification. Product and company names and marks belong to their owners and identify their products; no affiliation or endorsement is implied. Vendors may correct a record with the public page that states the fact: https://safelegalai.com/report — we re-check within 7 working days and log the change. **Not legal advice; no warranty; see `DISCLAIMER.md` and https://safelegalai.com/disclaimer.**
