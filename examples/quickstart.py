#!/usr/bin/env python3
"""Quickstart: generate sample results, then build Markdown and HTML reports.

Run from the repo root (after `pip install -e .`):

    python examples/quickstart.py

Outputs land in examples/output/.
"""

from pathlib import Path

from eval_report_builder import make_sample_results, write_report
from eval_report_builder.schema import validate_results

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"


def main():
    OUT.mkdir(exist_ok=True)

    # 1. Produce (or load) validated evaluation results.
    results = validate_results(make_sample_results(seed=42, jitter=0.005))
    print(f"model: {results['model']['name']}  splits: "
          f"{[s['name'] for s in results['splits']]}")

    # 2. Render both formats. latency_ms is lower-is-better so comparison
    #    deltas and charts read correctly.
    lower = ("latency_ms",)
    md_path = write_report(results, OUT / "report", fmt="markdown", lower_is_better=lower)
    html_path = write_report(results, OUT / "report", fmt="html", lower_is_better=lower)
    print(f"wrote {md_path}")
    print(f"wrote {html_path}")

    # 3. Evaluate the quality gates — the same check the CLI's --check-gates does.
    from eval_report_builder.gates import evaluate_gates
    gate_results, overall = evaluate_gates(results)
    for r in gate_results:
        print(("PASS " if r.passed else "FAIL ") + r.message)
    print("overall:", "PASS" if overall else "FAIL")


if __name__ == "__main__":
    main()
