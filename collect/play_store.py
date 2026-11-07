"""Collect Google Play reviews for INDmoney with resumable multi-pass pulls.

Only text, rating and date are stored. Usernames and other personal fields are
dropped before anything is written to disk or printed.

Passes (up to 3,000 reviews each):
  1. newest
  2. most relevant
  3. 1-3 star (split evenly across ratings 1, 2 and 3)

Progress is appended to JSONL in batches and saved to a state file after every
batch, so an interrupted run resumes from the last saved position.
"""
import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

import yaml
from google_play_scraper import Sort, reviews
from google_play_scraper.features.reviews import _ContinuationToken

APP_ID = "in.indwealth"  # INDmoney
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT_ROOT / "data" / "raw" / "play_store_reviews.jsonl"
DEFAULT_STATE = PROJECT_ROOT / "data" / "raw" / "play_store_reviews.state.json"

PASSES = [
    {"key": "newest", "label": "newest", "sort": Sort.NEWEST, "scores": [None]},
    {"key": "most_relevant", "label": "most relevant", "sort": Sort.MOST_RELEVANT, "scores": [None]},
    {"key": "low_ratings", "label": "1-3 star", "sort": Sort.NEWEST, "scores": [1, 2, 3]},
]


def force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def load_keywords(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keywords = [str(k).strip().lower() for k in data.get("keywords", []) if str(k).strip()]
    if not keywords:
        raise SystemExit(f"No keywords found in {path}")
    return keywords


def build_matchers(keywords: list[str]) -> list[tuple[str, re.Pattern]]:
    """Whole-word matchers with simple plural/past suffixes.

    "sip" matches "SIPs" but not "gossip"; "nav value" does not match
    "navigation". Devanagari keywords are matched as whole words too.
    """
    matchers = []
    for keyword in keywords:
        body = r"\s+".join(re.escape(part) for part in keyword.split())
        pattern = re.compile(
            r"(?<!\w)" + body + r"(?:s|es|ed|d|ing)?(?!\w)",
            re.IGNORECASE,
        )
        matchers.append((keyword, pattern))
    return matchers


def is_sip_related(text: str, matchers: list[tuple[str, re.Pattern]]) -> bool:
    text = text or ""
    return any(pattern.search(text) for _, pattern in matchers)


def dedupe_key(record: dict) -> str:
    raw = f"{record.get('text', '')}\x1f{record.get('date', '')}\x1f{record.get('rating', '')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def load_existing(path: Path) -> tuple[list[dict], set[str]]:
    rows: list[dict] = []
    seen: set[str] = set()
    if not path.exists():
        return rows, seen
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(row)
            seen.add(dedupe_key(row))
    return rows, seen


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"app_id": APP_ID, "passes": {}}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def review_record(review: dict) -> dict | None:
    text = (review.get("content") or "").strip()
    if not text:
        return None
    at = review.get("at")
    return {
        "text": text,
        "rating": review.get("score"),
        "date": at.isoformat() if hasattr(at, "isoformat") else str(at),
    }


def token_to_state(token: _ContinuationToken | None) -> dict | None:
    if token is None:
        return None
    return {
        "token": token.token,
        "lang": token.lang,
        "country": token.country,
        "sort": token.sort,
        "filter_score_with": token.filter_score_with,
        "filter_device_with": token.filter_device_with,
    }


def token_from_state(info: dict | None, count: int) -> _ContinuationToken | None:
    if not info or info.get("token") is None:
        return None
    return _ContinuationToken(
        info["token"],
        info.get("lang", "en"),
        info.get("country", "in"),
        info.get("sort", Sort.NEWEST.value),
        count,
        info.get("filter_score_with"),
        info.get("filter_device_with"),
    )


def sub_targets(pass_def: dict, target: int) -> list[tuple[int | None, int]]:
    scores = pass_def["scores"]
    base = target // len(scores)
    out = []
    for index, score in enumerate(scores):
        amount = base + (target - base * len(scores) if index == len(scores) - 1 else 0)
        out.append((score, amount))
    return out


def collect(args: argparse.Namespace) -> None:
    keywords = load_keywords(PROJECT_ROOT / "config.yaml")
    rows, seen = load_existing(args.out)
    state = load_state(args.state)
    state["app_id"] = args.app_id

    print(f"Resuming with {len(rows)} unique reviews already saved.")
    print(f"Output: {args.out}")
    print(f"State:  {args.state}\n")

    for pass_def in PASSES:
        for score, target in sub_targets(pass_def, args.target):
            subkey = f"{pass_def['key']}:{score if score is not None else 'all'}"
            progress = state["passes"].setdefault(
                subkey,
                {"token_info": None, "fetched": 0, "saved": 0, "done": False},
            )
            label = pass_def["label"] if score is None else f"{score} star"
            if progress.get("done"):
                print(f"[{label}] already complete ({progress.get('fetched', 0)} fetched)")
                continue

            print(f"[{label}] starting at {progress.get('fetched', 0)}/{target}")
            stalls = 0
            while progress.get("fetched", 0) < target:
                remaining = target - progress["fetched"]
                need = min(args.batch_size, remaining)
                token = token_from_state(progress.get("token_info"), need)

                try:
                    batch, next_token = reviews(
                        args.app_id,
                        lang=args.lang,
                        country=args.country,
                        sort=pass_def["sort"],
                        count=need,
                        filter_score_with=score,
                        continuation_token=token,
                    )
                except Exception as exc:  # noqa: BLE001 - readable message for a collector
                    print(f"[{label}] request failed: {exc}")
                    print("Progress is saved. Re-run the same command to resume.")
                    return

                if not batch:
                    progress["done"] = True
                    save_state(args.state, state)
                    print(f"[{label}] no more reviews returned; marked complete.")
                    break

                new_rows = []
                for review in batch:
                    record = review_record(review)
                    if record is None:
                        continue
                    key = dedupe_key(record)
                    if key in seen:
                        continue
                    seen.add(key)
                    new_rows.append(record)

                if new_rows:
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    with args.out.open("a", encoding="utf-8") as handle:
                        for record in new_rows:
                            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    rows.extend(new_rows)

                progress["fetched"] = progress.get("fetched", 0) + len(batch)
                progress["saved"] = progress.get("saved", 0) + len(new_rows)
                progress["token_info"] = token_to_state(next_token)
                if next_token is None:
                    progress["done"] = True
                save_state(args.state, state)

                print(
                    f"[{label}] fetched {progress['fetched']}/{target}, "
                    f"saved {progress['saved']} new (total {len(rows)})"
                )

                if progress["done"]:
                    break

                if not new_rows:
                    stalls += 1
                    if stalls >= 3:
                        progress["done"] = True
                        save_state(args.state, state)
                        print(f"[{label}] no new unique reviews; marked complete.")
                        break
                else:
                    stalls = 0

                if args.pause > 0:
                    time.sleep(args.pause)

    report(rows, keywords, args.show)


def report(rows: list[dict], keywords: list[str], show: int) -> None:
    total = len(rows)
    matchers = build_matchers(keywords)
    kept = [row for row in rows if is_sip_related(row["text"], matchers)]
    share = len(kept) / total if total else 0.0

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total pulled (unique): {total}")
    print(f"Kept after keyword filter: {len(kept)}")
    print(f"Share kept: {share:.1%}")

    print("\nHits per keyword (reviews containing it):")
    for keyword, pattern in matchers:
        hits = sum(1 for row in rows if pattern.search(row["text"]))
        print(f"  {keyword}: {hits}")

    dates = sorted(row["date"][:10] for row in rows if row.get("date"))
    if dates:
        print(f"\nDate range: {dates[0]} to {dates[-1]}")
    else:
        print("\nDate range: n/a")

    if not kept:
        print("\nNo keyword matches to sample.")
        return

    random.seed(7)
    sample = random.sample(kept, min(show, len(kept)))
    print(f"\n{len(sample)} random kept reviews:\n")
    for index, row in enumerate(sample, start=1):
        print(f"[{index}] rating={row['rating']}")
        print(row["text"])
        print("verdict: ____")
        print()


def main() -> None:
    force_utf8()
    parser = argparse.ArgumentParser(description="Resumable multi-pass Play Store review collector.")
    parser.add_argument("--target", type=int, default=3000, help="Max reviews per pass (default: 3000).")
    parser.add_argument("--batch-size", type=int, default=200, help="Reviews per saved batch (default: 200).")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds between requests (default: 2).")
    parser.add_argument("--app-id", default=APP_ID, help=f"Play Store app id (default: {APP_ID}).")
    parser.add_argument("--lang", default="en", help="Language code (default: en).")
    parser.add_argument("--country", default="in", help="Country code (default: in).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output JSONL (default: {DEFAULT_OUT}).")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help=f"Resume state (default: {DEFAULT_STATE}).")
    parser.add_argument("--show", type=int, default=10, help="How many kept reviews to print (default: 10).")
    parser.add_argument("--report-only", action="store_true", help="Only report on the existing output; do not pull.")
    args = parser.parse_args()

    if args.report_only:
        key_words = load_keywords(PROJECT_ROOT / "config.yaml")
        rows, _ = load_existing(args.out)
        report(rows, key_words, args.show)
        return

    collect(args)


if __name__ == "__main__":
    main()
