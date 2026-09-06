# Agent brief — the vendor documentation audit (read fully)

You are collecting one slice of **SafeLegalAI's `legal-ai-vendor-facts` dataset**: what each legal-AI vendor *documents on its own public pages* about pricing, contract terms, security and accuracy. The output feeds the facts registry at safelegalai.com/tools and side-by-side fact comparisons. **It is a record of what vendors say, never a judgement of them.**

## Rules (non-negotiable)
1. **Facts only.** Record what the page states. Never infer quality, never rank, never use "best", "leading", "secure". A vendor that does not publish a price gets `pricing.published = "no"`, `status: not-found`, with `pages_checked` listing what you read — that absence is a fact we publish.
2. **Public pages only, no accounts, no forms, no chat widgets.** Pricing pages, security/trust pages, terms of service, privacy policy, DPA, sub-processor lists, "legal" hubs, documentation, official blog posts about certifications. Never log in, never request a demo, never scrape behind click-wrap or a paywall. Do not use Crunchbase, G2, Capterra, LinkedIn, review sites or competitor comparisons as sources of facts (you may use web_search to *find* the vendor's own page).
3. **Quotes ≤ 25 words, verbatim, in quotation marks**, one per fact, for identification only. Do not copy paragraphs.
4. **Provenance on every row**: `source_url` (the vendor page), `fetched_at` (today: 2026-09-06), `page_dated` (the "last updated" date printed on the page, if any). Request an archive snapshot for each *distinct* page you rely on: `curl -sI -A "SafeLegalAI-Bot/1.0 (+https://safelegalai.com/datasets; hello@safelegalai.com)" "https://web.archive.org/save/<url>"` and read the `Location`/`Content-Location` header for the `https://web.archive.org/web/<timestamp>/<url>`; put it in `archive_url`. If Wayback declines or is slow (>30 s), try the availability API once (`https://archive.org/wayback/available?url=<url>`) for an existing snapshot; else null. Never retry more than once per page.
5. **Politeness**: identify yourself with the User-Agent above; ≤ 1 request per second per host; `curl -sL --max-time 45`; fetch each page once. Many vendor pages are JavaScript-rendered — if curl returns a shell, try `web_fetch` on the URL (it renders), and if still empty, record `not-found` with a note "page did not render".
6. **Exclusions**: do not audit `legalai-space` (an affiliated product; excluded by policy). Skip it if it appears anywhere.

## The fields, and how to code them
Read `schema/fact.schema.json` (`cat schema/fact.schema.json`) — the `field` enum is the checklist. For every tool, produce a row for AT LEAST these fields (stated, implied or not-found):
`pricing.published`, `pricing.model`, `pricing.list_price`, `pricing.seat_minimum`, `pricing.minimum_term`, `pricing.free_trial`,
`security.soc2`, `security.iso27001`, `security.iso42001`, `security.no_training_on_customer_data`, `security.zero_retention`, `security.private_deployment`, `security.data_residency`, `security.encryption_at_rest`, `security.sso_saml`,
`contract.dpa_available`, `contract.subprocessors_published`, `contract.model_providers`, `contract.terms_last_updated`, `contract.privacy_last_updated`,
`accuracy.claim`, `accuracy.method_published`.
Add the other enum fields when the page states them (HIPAA, FedRAMP, breach notification hours, audit rights, liability cap, governing law, pen test, retention period, product markets/languages, Word integration, on-premise option).

Value conventions: tri-state fields → `"yes"` / `"no"` (only when the page says so) — never guess; `pricing.published` → `"yes"` if any concrete price appears, `"no"` otherwise; `pricing.model` → one of `per-seat | enterprise | usage | freemium | free | tiered | not-published`; `pricing.list_price` → the price string as printed (e.g. `"$99 per user per month, billed annually"`); `security.data_residency` → list of region/country codes or names as stated (`["US","EU"]`); `contract.model_providers` → list of named model providers (`["OpenAI","Anthropic"]`); `accuracy.claim` → the claim as a short string with its number if given; `accuracy.method_published` → `"yes"` if the vendor links a methodology/benchmark description, else `"no"`.

`status`: `stated` when a sentence says it; `implied` when only a badge/logo/list implies it (e.g. a SOC 2 logo with no sentence); `not-found` when you read the relevant pages and none addresses it; `contradictory` when two vendor pages disagree — explain in `note`.

## Where to look, per tool
Start from the `website` in your batch file; then find: `/pricing`, `/plans`; `/security`, `/trust`, `trust.<domain>`, `/legal`, `/terms`, `/privacy`, `/dpa`, `/subprocessors` or `/sub-processors`; `/docs` security pages; the vendor blog for certification announcements (SOC 2, ISO 27001, ISO 42001). Use `web_search` with `site:<domain> pricing`, `site:<domain> SOC 2`, `site:<domain> sub-processors` when navigation hides them. Budget ~6–10 page fetches per tool.

## Output
Append rows to **`work/agents/<your-batch>.jsonl`** (path given in your task), one JSON object per line conforming to the schema. `fact_id` = `<tool_id>.<field>`. Validate as you go: `python3 -c "import json;[json.loads(l) for l in open('work/agents/<batch>.jsonl')]"`. Expect 22–35 rows per tool.

## When done
Reply ONLY with: tools completed; rows written; rows by status; tools whose pages would not render or whose site is down; anything that needs a human (e.g. a claim that looks like a hallucination-rate figure). Do not paste rows.
