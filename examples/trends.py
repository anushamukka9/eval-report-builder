#!/usr/bin/env python3
"""Trends example: history snapshots, highlight sections, and dark theme.

Generates sample results with 8 synthetic history snapshots, then builds:
- report.md      (Markdown: Summary, Highlights, Metrics, Trends table, Gates, Comparison)
- report.html    (HTML, light theme, with per-metric trend line charts)
- report-dark.html (HTML, dark theme)

Run from the repo root (after `pip install -e .`):

    python examples/trends.py

Outputs land in examples/output/.
"""

from pathlib import Path

from eval_report_builder import make_sample_results, write_report
from eval_report_builder.schema import validate_results

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"


def main():
    OUT.mkdir(exist_ok=True)
    lower = ("latency_ms",)

    results = validate_results(
        make_sample_results(seed=42, jitter=0.002, history_points=8)
    )
    print(f"model: {results['model']['name']}")
    print(f"history snapshots: {[h['label'] for h in results['history']]}")

    md_path = write_report(results, OUT / "trends-report", fmt="markdown",
                           lower_is_better=lower)
    html_path = write_report(results, OUT / "trends-report", fmt="html",
                             lower_is_better=lower)
    dark_path = write_report(results, OUT / "trends-report-dark", fmt="html",
                             lower_is_better=lower, theme="dark")
    for p in (md_path, html_path, dark_path):
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
