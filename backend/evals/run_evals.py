#!/usr/bin/env python3
"""Eval harness for Veritas fact-check accuracy.

Submits every video in `dataset.json` to the public demo endpoint, waits for
each job to finish, and scores the result against the human-curated ground
truth. Produces a JSON report + a CSV row-level detail file.

Two metrics:
  1. Verdict accuracy   — does the overall_verdict match the expected one?
     Partial credit for adjacent labels (true <-> mostly true counts as 0.5).
  2. Source quality     — does the result cite at least one domain from the
     expected_source_domains list? Binary 0 or 1 per item.

Usage:
  # Run against production Render backend (default):
  python run_evals.py

  # Run against a local backend:
  python run_evals.py --base-url http://localhost:8000

  # Limit to a single item for quick debugging:
  python run_evals.py --only control-moon-landing

Notes:
  - This hits the PUBLIC /api/fact-check/demo endpoint, which is rate-limited
    to 3 per day per IP. If you need to run the full 15-item eval, do it from
    a machine on a different IP each day or temporarily loosen the limit on
    the backend.
  - Demo endpoint caps videos at 5 minutes.
  - Any item with video_url == "TODO" is skipped and counted as 'unfilled'.
"""

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

HERE = Path(__file__).parent
DATASET_PATH = HERE / "dataset.json"
REPORT_JSON = HERE / "report.json"
REPORT_CSV = HERE / "report.csv"

DEFAULT_BASE = "https://veritas-backend-5l6r.onrender.com"
POLL_INTERVAL = 4   # seconds between status checks
MAX_WAIT = 60 * 6   # 6 minutes per item; fail open after that


# --- Verdict normalization ---------------------------------------------------
# The LLM produces free-form verdict strings; we map them to a small canonical
# set so we can compare against ground truth without string-matching headaches.

VERDICT_ORDER = [
    "false", "mostly false", "partially true", "mostly true", "true", "unverified",
]

def normalize_verdict(v: Optional[str]) -> str:
    if not v:
        return "unverified"
    s = v.lower().strip()
    if "inconclusive" in s or "unverif" in s or "not a factual" in s:
        return "unverified"
    if "mostly true" in s: return "mostly true"
    if "mostly false" in s: return "mostly false"
    if "partially" in s or "partial" in s or "mixed" in s: return "partially true"
    if s == "true" or s.startswith("true"): return "true"
    if s == "false" or s.startswith("false"): return "false"
    return "unverified"


def verdict_score(predicted: str, expected: str) -> float:
    """1.0 exact match, 0.5 adjacent, 0.0 otherwise. 'unverified' only matches itself."""
    p, e = normalize_verdict(predicted), normalize_verdict(expected)
    if p == e:
        return 1.0
    if p == "unverified" or e == "unverified":
        return 0.0
    try:
        return 0.5 if abs(VERDICT_ORDER.index(p) - VERDICT_ORDER.index(e)) == 1 else 0.0
    except ValueError:
        return 0.0


def source_quality_score(sources: list, expected_domains: list) -> int:
    """1 if any cited source URL contains an expected domain, 0 otherwise.

    If `expected_domains` is empty (e.g. for opinion claims), we give credit
    automatically — we're not testing source quality on non-factual items."""
    if not expected_domains:
        return 1
    urls = " ".join((s.get("url") or "") for s in (sources or [])).lower()
    return int(any(dom.lower() in urls for dom in expected_domains))


# --- Runner ------------------------------------------------------------------

@dataclass
class ItemResult:
    id: str
    status: str              # "scored" | "skipped_unfilled" | "submit_failed" | "timeout" | "backend_failed"
    expected_verdict: str = ""
    predicted_verdict: str = ""
    verdict_score: float = 0.0
    source_score: int = 0
    error: str = ""
    raw_confidence: Optional[int] = None
    job_id: str = ""
    elapsed_s: float = 0.0
    sources_cited: list = field(default_factory=list)


def run_one(base_url: str, item: dict) -> ItemResult:
    iid = item["id"]
    if item.get("video_url") in (None, "", "TODO"):
        return ItemResult(id=iid, status="skipped_unfilled",
                          expected_verdict=item.get("expected_verdict", ""))

    started = time.time()
    try:
        # Render's free tier cold-starts in ~50s when the dyno is asleep, so
        # the very first POST of a run can take much longer than a warm one.
        r = requests.post(
            f"{base_url}/api/fact-check/demo",
            json={"video_url": item["video_url"]},
            timeout=120,
        )
    except requests.RequestException as e:
        return ItemResult(id=iid, status="submit_failed", error=f"network: {e}")

    if r.status_code != 202:
        return ItemResult(
            id=iid, status="submit_failed",
            error=f"HTTP {r.status_code}: {r.text[:300]}",
        )

    job_id = r.json().get("job_id", "")
    if not job_id:
        return ItemResult(id=iid, status="submit_failed", error="no job_id in response")

    # Poll for completion.
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            s = requests.get(
                f"{base_url}/api/fact-check/demo/{job_id}/status", timeout=30,
            )
        except requests.RequestException:
            continue
        if s.status_code != 200:
            continue
        data = s.json()
        status = data.get("status")
        if status == "completed":
            result = data.get("result") or {}
            exp = item.get("expected_verdict", "")
            pred = result.get("overall_verdict", "")
            v_score = verdict_score(pred, exp)
            s_score = source_quality_score(
                result.get("sources", []),
                item.get("expected_source_domains", []),
            )
            return ItemResult(
                id=iid, status="scored",
                expected_verdict=exp, predicted_verdict=pred,
                verdict_score=v_score, source_score=s_score,
                raw_confidence=result.get("confidence_score"),
                job_id=job_id, elapsed_s=round(time.time() - started, 1),
                sources_cited=[s.get("url", "") for s in (result.get("sources") or [])],
            )
        if status == "failed":
            return ItemResult(
                id=iid, status="backend_failed",
                error=data.get("error", "(no error message)"),
                job_id=job_id, elapsed_s=round(time.time() - started, 1),
            )

    return ItemResult(id=iid, status="timeout", job_id=job_id,
                      elapsed_s=round(time.time() - started, 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("VERITAS_BASE_URL", DEFAULT_BASE))
    ap.add_argument("--only", help="Run only the item with this id")
    args = ap.parse_args()

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    items = dataset["items"]
    if args.only:
        items = [i for i in items if i["id"] == args.only]
        if not items:
            print(f"No item with id '{args.only}'", file=sys.stderr)
            return 2

    results: list[ItemResult] = []
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item['id']}...", flush=True)
        res = run_one(args.base_url, item)
        results.append(res)
        print(f"    -> {res.status} "
              f"(verdict={res.verdict_score}, source={res.source_score})")

    # --- Aggregate ------------------------------------------------------------
    scored = [r for r in results if r.status == "scored"]
    summary = {
        "total_items": len(results),
        "scored": len(scored),
        "skipped_unfilled": sum(1 for r in results if r.status == "skipped_unfilled"),
        "submit_failed": sum(1 for r in results if r.status == "submit_failed"),
        "backend_failed": sum(1 for r in results if r.status == "backend_failed"),
        "timeout": sum(1 for r in results if r.status == "timeout"),
        "avg_verdict_accuracy": (
            round(sum(r.verdict_score for r in scored) / len(scored), 3)
            if scored else None
        ),
        "source_quality_rate": (
            round(sum(r.source_score for r in scored) / len(scored), 3)
            if scored else None
        ),
    }

    report = {
        "base_url": args.base_url,
        "summary": summary,
        "items": [r.__dict__ for r in results],
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "status", "expected_verdict", "predicted_verdict",
                    "verdict_score", "source_score", "raw_confidence",
                    "elapsed_s", "error"])
        for r in results:
            w.writerow([r.id, r.status, r.expected_verdict, r.predicted_verdict,
                        r.verdict_score, r.source_score, r.raw_confidence or "",
                        r.elapsed_s, r.error])

    print("\n--- Summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nWrote {REPORT_JSON} and {REPORT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
