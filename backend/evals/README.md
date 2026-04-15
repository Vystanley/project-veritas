# Veritas accuracy evals

A small, honest evaluation harness for the fact-check pipeline. It runs Veritas against a fixed set of videos with known-truth labels, then reports how often the model's verdicts and cited sources match the ground truth.

This is not a benchmark. It's a sanity check that catches regressions and gives a defensible number to put in the README instead of vibes.

## What's in here

- `dataset.json` — 15 items. Each is a short video URL paired with the claim it makes, the verdict a competent human fact-checker would give, and the source domains we'd expect a credible answer to cite.
- `run_evals.py` — submits every item to the `/api/fact-check/demo` endpoint, polls until each job finishes, and scores the result.
- `report.json` / `report.csv` — generated output. Overwritten on each run.

## How items are scored

Two metrics, both per-item:

**Verdict accuracy (0.0 to 1.0).** We normalize both the predicted and expected verdict into a small canonical set (`false`, `mostly false`, `partially true`, `mostly true`, `true`, `unverified`). Exact match is 1.0. One step off is 0.5. Anything further, or a flip to/from `unverified`, is 0.0.

**Source quality (0 or 1).** 1 if the result cites at least one URL containing any of the expected source domains; 0 otherwise. For items where no specific sources are expected (pure opinion claims) we auto-credit 1.

The aggregate report gives the mean verdict score and the source-quality rate across all successfully-scored items.

## Known limitations, stated honestly

- **Small dataset.** 15 items is enough to catch obvious regressions, not enough to make statistical claims.
- **Ground truth is judgmental.** A human curator (you) decided each expected verdict. Disagreement with the model doesn't automatically mean the model is wrong. Read the cited sources before concluding anything.
- **LLM non-determinism.** Two runs on the same video can produce slightly different verdicts. Run the harness more than once if a number looks off.
- **Rate limits.** The demo endpoint is capped at 3 scans per day per IP, so running the full 15-item eval in one sitting either needs a temporary backend adjustment or needs to be spread across days.
- **Platform coverage is skewed.** YouTube is unreliable from Render's IP (see the main README). TikTok/Instagram/X are the platforms with working coverage, so the dataset leans that way too.
- **Only tests the demo endpoint.** The authenticated endpoint has the same fact-check logic but is unmeasured here.

## How to fill in the dataset

Items are seeded as templates. Every `video_url` is `TODO` and some `expected_verdict` / `claim` fields are placeholders too. To run real evals, you need to:

1. Find a short (<5 min) TikTok, Instagram, or X video that makes the listed claim.
2. Replace the `TODO` in `video_url` with the real URL.
3. For the `TODO` items that don't yet have a specific claim, pick one and fill in `claim`, `expected_verdict`, and `notes`.
4. Prefer claims with a canonical fact-check already published (Snopes, PolitiFact, Reuters Fact Check, APFactCheck) — link that ruling in the `notes` field so anyone auditing the eval can verify your ground truth.

The dataset is deliberately small and hand-curated. Don't scale it up without also scaling up your curation effort.

## How to run

```bash
cd backend/evals
pip install requests --break-system-packages
python run_evals.py                    # hits production Render by default
python run_evals.py --only control-moon-landing    # smoke test one item
python run_evals.py --base-url http://localhost:8000    # local backend
```

Each item takes 1 to 3 minutes. A full 15-item run is therefore 20 to 45 minutes wall clock.

## Interpreting the output

After a run, open `report.json` for the summary block, for example:

```json
"summary": {
  "total_items": 15,
  "scored": 14,
  "skipped_unfilled": 0,
  "submit_failed": 0,
  "backend_failed": 1,
  "timeout": 0,
  "avg_verdict_accuracy": 0.714,
  "source_quality_rate": 0.857
}
```

Rough reading: on 14 items that completed end-to-end, the mean verdict score was 0.71 (so verdicts are usually right or one-step-off, rarely a full flip), and 86% of verdicts cited at least one expected source.

The CSV is per-item, useful for spotting patterns (e.g. "it systematically misreads partial-true claims as mostly-true").

## Suggested workflow

1. Fill in 3 or 4 control items first (moon landing, flat earth, water boils). Run the harness. You should see near-1.0 scores and good sources. If you don't, the pipeline has a regression.
2. Once controls pass, fill in the rest over a few sessions.
3. Re-run the full harness whenever you change prompts, swap models, or touch the search code. Compare to the previous `report.json`.
4. Commit a `report.json` snapshot you're proud of so there's a baseline to point reviewers at.
