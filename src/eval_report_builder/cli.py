"""Command-line interface for eval-report-builder.

Commands
--------
build    Build a Markdown/HTML report from a results JSON file.
sample   Write a synthetic demo results JSON file.

Examples
--------
$ eval-report-builder sample -o results.json --seed 42
$ eval-report-builder build results.json -o report.html --format html
$ eval-report-builder build results.json --format markdown --check-gates
"""

import argparse
import json
import sys

from .api import Report, write_report
from .gates import evaluate_gates
from .sample import write_sample


def _comma_list(value):
    return [v.strip() for v in value.split(",") if v.strip()]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="eval-report-builder",
        description="Build polished evaluation reports from model evaluation results.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Build a report from a results JSON file.")
    b.add_argument("results", help="Path to the results JSON file.")
    b.add_argument("-o", "--output", default=None,
                   help="Output path (default: report.<md|html> in cwd).")
    b.add_argument("-f", "--format", default="markdown", choices=["markdown", "md", "html"],
                   help="Report format (default: markdown).")
    b.add_argument("--lower-is-better", default="",
                   help="Comma-separated metrics where lower is better, e.g. latency_ms,error_rate.")
    b.add_argument("--check-gates", action="store_true",
                   help="Exit non-zero if any error-severity gate fails (for CI).")

    s = sub.add_parser("sample", help="Write a synthetic demo results JSON file.")
    s.add_argument("-o", "--output", default="sample-results.json",
                   help="Where to write the sample JSON (default: sample-results.json).")
    s.add_argument("--seed", type=int, default=None, help="Random seed for metric jitter.")
    s.add_argument("--jitter", type=float, default=0.0,
                   help="Max absolute jitter applied to float metrics (default: 0).")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "sample":
        path = write_sample(args.output, seed=args.seed, jitter=args.jitter)
        print(f"wrote sample results: {path}")
        return 0

    lower = _comma_list(args.lower_is_better)
    report = Report.from_file(args.results, lower_is_better=lower)
    out = args.output or ("report.html" if args.format == "html" else "report.md")
    path = write_report(report, out, fmt=args.format)
    print(f"wrote {args.format} report: {path}")

    if args.check_gates:
        gate_results, overall = evaluate_gates(report.results)
        for r in gate_results:
            print(("PASS " if r.passed else "FAIL ") + r.message)
        if not overall:
            print("quality gates FAILED", file=sys.stderr)
            return 1
        print("quality gates PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
