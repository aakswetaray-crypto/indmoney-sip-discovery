# Evidence Log Notes

## 2026-11-06 — Play Store collection (INDmoney, `in.indwealth`)

### Funnel

- Fetched: **9,000** reviews
  - Newest: 3,000
  - Most relevant: 3,000
  - 1–3 star: 3,000 (1,000 each for 1★, 2★, 3★)
- After de-duplication: **7,290**
- Kept by keyword filter: **468**
- Keep rate: **6.4%**

### Date range

**2019-06-27 to 2026-11-04**

### Top 10 keyword hits

| Keyword | Hits |
|---|---:|
| mutual fund | 246 |
| sip | 123 |
| stopped | 48 |
| returns | 36 |
| redeem | 24 |
| xirr | 23 |
| mandate | 14 |
| pause | 9 |
| autopay | 7 |
| auto pay | 7 |

### Limitations

- The sample deliberately over-represents 1 to 3 star reviews.
- Keyword hits overlap: one review can match multiple keywords, so hits do not sum to the kept total.
- "stopped" can mean the app rather than the SIP.

### Language coverage and keep rates

- **English-only limitation:** the first pass used `--lang en`, so it under-represents Hindi and Hinglish reviews. It contained 32 Devanagari reviews but none were kept, and every Hinglish/Hindi keyword scored 0 hits.
- A second pass used `--lang hi` (country `in`) into `data/raw/play_store_reviews_hi.jsonl`: **462** unique reviews pulled, **4** kept.
- The Hindi pass returned 100 Devanagari reviews, but none mentioned SIP or mutual fund terms; the 4 kept reviews were English/Hinglish.
- **English pass keep rate:** 468 / 7,290 = **6.4%**
- **Hindi pass keep rate:** 4 / 462 = **0.9%**
- **Merged (`data/raw/play_store_all.jsonl`):** 7,752 unique reviews, 472 kept = **6.1%**

## Research question → tag mapping

`unmet_need` below is the existing free-text field already exported in `data/export/tagged.csv`; keep its column name.

| # | Research question | Fields that answer it |
|---:|---|---|
| 1 | Why do people start a SIP, and what do they expect? | `start_reason`, `expectation`, `influencer`, `money_source`, `age_band`, `income_stability` |
| 2 | How does behaviour change in the months after starting? | `stage`, `action`, `check_behaviour`, `continued_reason`, `trigger`, `lapse_type`, `emotion` |
| 3 | What leads to pausing, reducing, or stopping? | `trigger`, `lapse_type`, `action`, `stage`, `app_confusion`, `income_stability`, `money_source` |
| 4 | What do they check, and how often? | `check_behaviour`, `app_confusion`, `action` |
| 5 | What confuses or worries them in the app? | `app_confusion`, `emotion`, `trigger`, `unmet_need` |
| 6 | What do they do outside the app when unsure? | `outside_app_action`, `influencer`, `app_confusion` |
| 7 | What separates continuers from drop-offs? | `action`, `continued_reason`, `start_reason`, `expectation`, `check_behaviour`, `trigger`, `lapse_type`, `stage`, `emotion` |
| 8 | How do patterns differ by segment (income stability, age, source of money, who influenced them)? | `income_stability`, `age_band`, `money_source`, `influencer` |
| 9 | What unmet needs recur? | `unmet_need`, `app_confusion`, `trigger`, `expectation`, `outside_app_action` |

## 2026-11-06 — Tagging engine (`app/engine_app.py`)

### Model

- The Groq key can access 11 models. After checking JSON mode, the engine uses **`openai/gpt-oss-120b`**.
- Comparison on three sample reviews: `openai/gpt-oss-20b` marked a loan-against-mutual-funds review as SIP-related, and with a stricter prompt marked clear SIP posts as not SIP-related. `openai/gpt-oss-120b` classified all three correctly, so it is the preferred model. Fallbacks: `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`.
- The app lists the models available to the key and shows the chosen model name.

### Tagging rules

- The system prompt includes every `codebook.yaml` field and allowed value, plus `sip_related`, `evidence_quote`, and `unmet_need`.
- `sip_related` is false for loans, trading, IPOs, demat/KYC, and unrelated app issues. It is true only for mutual fund SIP decisions or instalments.
- Unstated fallbacks are field-specific: `none_stated` where allowed, `unclear` for `stage`, `not_applicable` or `unclear` for `lapse_type`, and `unknown` for segment fields.
- Requests contain 8 posts. Each run is capped at 40 posts; each browser session at 3 runs.
- Results are matched by item number, never response order.
- Every value is validated against the codebook. Invalid output is retried once; remaining failures are marked failed.
- `evidence_quote` is checked in code as an exact substring after normalising spaces and smart quotes.

### Decisions and corrections

- `unmet_need` is the existing free-text `tagged.csv` field. It is not in `codebook.yaml`, so it is validated as free text, not as an enum.
- Low confidence = quote not found, or fewer than two analysis fields (excluding severity) stated. `not_applicable` is not counted as a stated field.
- The terminal pilot paces batches by 15 seconds to stay inside the free-tier 8k tokens/minute window. The Streamlit app does not sleep; it shows a wait-and-retry message on rate limits.

### Pilot (20 reviews, terminal, no browser)

- Model: `openai/gpt-oss-120b`
- Posts sent: 20 (8 + 8 + 4)
- Tagged: 20
- SIP-related: 13
- Quotes verified: 20
- Low confidence: 13
- Failures: 0
- Pilot rows were spread across ratings (4 each for 1–5 stars), not the first 20 rows.

## 2026-11-06 — Correction: lapse scope and quote length

### What changed

- `trigger` and `lapse_type` are now filled **only** when the post describes pausing, reducing or stopping a SIP. Every other post gets `trigger = none_stated` and `lapse_type = not_applicable`.
- The system prompt now states this scope directly, and the earlier `lapse_type` guidance was rewritten so it no longer implies a lapse can be tagged without a pause, reduction or stop.
- `evidence_quote` must now be **one continuous exact span of at most 25 words**, chosen as the part that best supports the tags.
- The 25-word cap is enforced in code: a quote over the limit is invalid, the batch is retried once, and a record that still fails is marked failed. The prompt and the app's "How it works" text were updated to match.

### Why

- The study needs `trigger` and `lapse_type` to describe actual lapses. Filling them for posts that only mention a SIP, or only describe app use, made continuers and drop-offs look alike.
- Long quotes were harder to check exactly and often mixed several ideas. A short span of at most 25 words keeps the evidence tied to the tags and makes quote verification reliable.

### Pilot after the correction (same 20 reviews, terminal, no browser)

- Model: `openai/gpt-oss-120b`
- Posts sent: 20 (8 + 8 + 4)
- Tagged: 20
- Quotes verified: 18 (2 quotes were not exact spans; both records stayed tagged)
- Failures: 0 (no record failed validation or the retry)
- Records with `trigger` other than `none_stated`: 0
- SIP-related: 13
- Low confidence: 16
- The 20 reviews were the same rating-spread rows as the earlier pilot.
- One unverified quote inserted an ellipsis ("...") that was not in the post, so it was not an exact span. This is the failure mode the exact-span rule is meant to catch.
- No other code changed. `app/streamlit_app.py` was not touched.

## 2026-11-08 — Correction: research-panel quote selection

### What changed

- Each research-question panel now shows a verified quote only when the post states a value for that panel's own field. The own field is the first field listed for the question, so for Q5 it is `app_confusion`.
- A post whose own field is `none_stated`, `unknown`, `unclear`, `not_applicable`, empty or missing is skipped, even if the same post has other fields filled in.
- If no post qualifies, the panel now shows **"No verified quotes for this question."** instead of borrowing a quote from a post that does not speak to the panel's field.

### Why

- The previous selection accepted a quote when **any** field in the panel was stated. That let a quote appear under a question even when the question's own field was missing, so the evidence looked like it supported a tag it did not support.
- A panel quote should be evidence for the panel's field, not just evidence that the post carried some other tag.

### Tagging note

- One review described a SIP that was paused but was still debited afterwards. It was tagged with `trigger = failed_debit`, which is the correct trigger for that case.
- No other code changed.





