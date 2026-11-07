# AGENTS.md

## Project

An AI-powered discovery engine for the Growth team at INDmoney.

**Goal:** Discover why first-time mutual fund investors pause or stop their SIPs.

**Business metric:** % of first-time investors who still have an active SIP 12 months after starting.
Active = at least one successful instalment in the last 30 days.

## Rules (non-negotiable)

- Never recommend specific funds or stocks.
- No fear, FOMO, or urgency-based nudges.
- Free tools only.
- Anonymise usernames and personal numbers.
- Keys live only in `.env` and are never printed or committed.
- Test every AI step on 50 to 100 items and stop for approval before any full run.
- Log every decision and correction in `docs/evidence_log_notes.md`.

## Sources

- Play Store reviews
- App Store reviews
- Indian investing subreddits
- An investing forum
- YouTube comments on SIP and personal finance videos

## Questions the engine must help answer

- Why do people start a SIP, and what do they expect?
- How does behaviour change in the months after starting?
- What leads to pausing, reducing, or stopping?
- What do they check, and how often?
- What confuses or worries them in the app?
- What do they do outside the app when unsure?
- What separates continuers from drop-offs?
- How do patterns differ by segment (income stability, age, source of money, who influenced them)?
- What unmet needs recur?

## Pipeline

`collect -> clean -> filter (SIP-related?) -> tag with codebook.yaml -> export data/export/tagged.csv -> Streamlit app in app/streamlit_app.py`

- Keep the existing `tagged.csv` column names.

## Working agreements

- Do not change code outside the requested scope without explicit approval.
- Record decisions and corrections in `docs/evidence_log_notes.md`.
- Ask before any full AI run; only run on 50 to 100 items for testing.
