# Usage Guide

## Install

```bash
pip install eval-report-builder        # once published
# or, from a checkout:
pip install -e .
```

No runtime dependencies — charts are hand-rolled SVG, so the package works
anywhere Python 3.10+ runs.

## The results document

Everything starts from a JSON results file. A minimal document needs a title
and one split with numeric metrics:

```json
{
  "title": "Sentiment classifier eval",
  "model": {"name": "sent-xgb", "version": "2026.09"},
  "splits": [
    {"name": "test", "samples": 5000,
     "metrics": {"accuracy": 0.931, "f1": 0.912, "latency_ms": 13.2}}
  ]
}
```

Full schema (all optional keys included):

```json
{
  "title": "Report title",                       // required
  "model": {"name": "...", "version": "..."},    // optional
  "generated_at": "2026-09-17T12:00:00Z",        // optional ISO-8601
  "notes": "Free text shown in the report",      // optional
  "splits": [                                    // required, >= 1
    {"name": "dev", "samples": 1200, "metrics": {"f1": 0.90}}
  ],
  "baselines": [                                 // optional
    {"name": "production-v42",
     "splits": [{"name": "dev", "metrics": {"f1": 0.87}}]}
  ],
  "gates": [                                     // optional
    {"metric": "f1", "split": "test", "op": ">=",
     "threshold": 0.90, "severity": "error",
     "description": "F1 must stay above 0.90 on test"}
  ]
}
```

Validation rules (`schema.py`): metric values must be numbers (int/float),
`op` must be one of `>= > <= < ==`, `severity` is `error` (fails the build)
or `warn` (reported only), and each split needs a non-empty name.

## CLI

```bash
# Build a Markdown report
eval-report-builder build results.json -o report.md

# Build HTML (self-contained: inline CSS + inline SVG, no external assets)
eval-report-builder build results.json -o report.html --format html

# Generate a synthetic demo file to try the tool
eval-report-builder sample -o demo.json --seed 42 --jitter 0.01

# Fail CI when an error-severity gate fails (exit code 1)
eval-report-builder build results.json --format markdown --check-gates

# Mark latency-like metrics as lower-is-better for comparison tables
eval-report-builder build results.json --lower-is-better latency_ms,error_rate
```

`python -m eval_report_builder` works identically if you prefer not to use
the installed script.

## Python API

```python
from eval_report_builder import Report, write_report, make_sample_results

report = Report(make_sample_results(), lower_is_better=("latency_ms",))
print(report.to_markdown())   # or report.to_html(), or report.render("html")
write_report(report, "report.html", fmt="html")
```

## What the report contains

1. **Summary** — model name, split count, total samples, baselines.
2. **Metrics by split** — one table, all metrics across splits.
3. **Charts (HTML)** — a bar chart per metric across splits, plus a
   grouped model-vs-baseline chart for the first shared metric.
4. **Quality gates** — per-gate PASS/FAIL/WARN lines and an overall verdict.
5. **Model vs baseline** — per-baseline tables with absolute and relative
   deltas and improvement indicators (▲/▼), honoring `lower_is_better`.

## CI pattern

```yaml
- run: eval-report-builder build eval/results.json -o report.md --check-gates
```

`--check-gates` exits non-zero only on `error`-severity failures; `warn`
gates are informational. Archive the generated `report.md`/`report.html` as
a build artifact for audit trails.
