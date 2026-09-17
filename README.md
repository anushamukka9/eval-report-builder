# eval-report-builder

Turn model evaluation results into polished, shareable reports. Feed it a
JSON file with metrics, per-split scores, and optional baselines; get back a
Markdown or self-contained HTML report with summary tables, inline-SVG
charts (zero charting dependencies), pass/fail quality gates, and
model-vs-baseline comparison sections.

Built by [Anusha Mukka](https://anushamukka.com).

## Why

Evaluation numbers usually die in a notebook cell or a CI log. This tool
gives them a durable, readable home: a Markdown report you can paste into a
PR or wiki, and a single-file HTML report (inline CSS + inline SVG, no
external assets) you can attach to an email, archive as a build artifact, or
host as a static page. The `--check-gates` mode plugs straight into CI so a
metric regression fails the build before it ships.

## Install

```bash
pip install -e .        # from a checkout; no runtime dependencies
```

Python 3.10+. No matplotlib, no pandas — charts are hand-rolled SVG.

## Quickstart

```bash
# 1. Make a demo results file
eval-report-builder sample -o demo.json --seed 42

# 2. Build both report formats
eval-report-builder build demo.json -o report.md
eval-report-builder build demo.json -o report.html --format html

# 3. Gate the build on quality thresholds (exit 1 on failure — CI friendly)
eval-report-builder build demo.json --check-gates --lower-is-better latency_ms
```

Or in Python (`examples/quickstart.py` is a runnable version of this):

```python
from eval_report_builder import Report, write_report, make_sample_results

results = make_sample_results(seed=42)
report = Report(results, lower_is_better=("latency_ms",))
write_report(report, "report.html", fmt="html")
```

## Results JSON

```json
{
  "title": "Fraud model eval",
  "model": {"name": "fraud-xgb", "version": "2026.09.17"},
  "splits": [
    {"name": "dev", "samples": 2400,
     "metrics": {"accuracy": 0.9521, "f1": 0.8922, "latency_ms": 11.7}}
  ],
  "baselines": [
    {"name": "production-v42",
     "splits": [{"name": "dev", "metrics": {"accuracy": 0.9388, "f1": 0.87}}]}
  ],
  "gates": [
    {"metric": "f1", "split": "dev", "op": ">=", "threshold": 0.88,
     "severity": "error", "description": "F1 must not regress"}
  ]
}
```

Full schema, CLI flags, the Python API, and the CI pattern are documented
in [docs/usage.md](docs/usage.md).

## Architecture

```
src/eval_report_builder/
├── __init__.py    public API surface
├── api.py         Report class, build_report(), write_report()
├── schema.py      results-document validation (fail fast, clear errors)
├── gates.py       pass/fail gate evaluation (error vs warn severity)
├── compare.py     model-vs-baseline deltas, lower_is_better handling
├── charts.py      dependency-free inline-SVG bar/line/grouped charts
├── markdown.py    Markdown renderer
├── html.py        self-contained HTML renderer
├── sample.py      synthetic demo-results generator
└── cli.py         `eval-report-builder` console script
```

The pipeline is deliberately linear: **validate → evaluate gates →
compare → render**. Rendering is a pure function of the validated document,
so reports are reproducible byte-for-byte from the same JSON.

## Development

```bash
pip install -e .
pip install pytest
python -m pytest -q
python examples/quickstart.py   # writes examples/output/report.{md,html}
```

## License

MIT — Copyright 2026 Anusha Mukka. See [LICENSE](LICENSE).
