"""eval-report-builder: turn model evaluation results into polished reports.

Given a JSON results file (metrics, per-split scores, optional baselines,
pass/fail gates), build Markdown and HTML evaluation reports with summary
tables, inline-SVG charts (no heavy dependencies), gate verdicts, and
model-vs-baseline comparison sections.

Public API
----------
load_results(path)      -> dict      validated results document
Report                  -> class     in-memory report builder
build_report(results, format) -> str rendered report ("markdown" | "html")
write_report(results, out, format) -> pathlib.Path

CLI
---
python -m eval_report_builder build results.json -o report.html --format html
python -m eval_report_builder sample -o demo-results.json --seed 42
"""

from .api import Report, build_report, load_results, write_report
from .gates import Gate, GateResult, evaluate_gates
from .sample import make_sample_results

__all__ = [
    "Report",
    "Gate",
    "GateResult",
    "build_report",
    "evaluate_gates",
    "load_results",
    "make_sample_results",
    "write_report",
]

__version__ = "0.1.0"
__author__ = "Anusha Mukka"
__author_url__ = "https://anushamukka.com"
