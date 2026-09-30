"""Tests for eval-report-builder."""

import json
import re

import pytest

from eval_report_builder import (
    Report,
    build_report,
    evaluate_gates,
    load_results,
    make_sample_results,
    write_report,
)
from eval_report_builder.charts import bar_chart, comparison_chart, line_chart
from eval_report_builder.compare import compare_to_baselines
from eval_report_builder.schema import validate_results


def sample():
    return make_sample_results()


def test_sample_results_validate():
    doc = validate_results(sample())
    assert len(doc["splits"]) == 3
    assert len(doc["baselines"]) == 1
    assert len(doc["gates"]) == 3


def test_load_results_roundtrip(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(sample()), encoding="utf-8")
    doc = load_results(path)
    assert doc["title"].startswith("Q3 Model Evaluation")


def test_load_results_rejects_bad_input(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"title": "x"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_results(path)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_results(path)


def test_schema_rejects_non_numeric_metric():
    doc = sample()
    doc["splits"][0]["metrics"]["accuracy"] = "high"
    with pytest.raises(ValueError, match="must be a number"):
        validate_results(doc)


def test_gates_all_pass_on_sample():
    gate_results, overall = evaluate_gates(sample())
    assert overall is True
    assert all(r.passed for r in gate_results)


def test_gates_fail_when_threshold_violated():
    doc = sample()
    doc["splits"][1]["metrics"]["f1"] = 0.5  # test split F1 gate is >= 0.88
    gate_results, overall = evaluate_gates(doc)
    assert overall is False
    failed = [r for r in gate_results if not r.passed]
    assert failed and failed[0].severity == "error"


def test_warn_gate_does_not_fail_overall():
    doc = sample()
    doc["splits"][2]["metrics"]["f1"] = 0.5  # canary warn gate only
    _, overall = evaluate_gates(doc)
    assert overall is True


def test_gate_missing_metric_fails():
    doc = sample()
    doc["gates"] = [{"metric": "nope", "op": ">=", "threshold": 1.0}]
    gate_results, overall = evaluate_gates(doc)
    assert overall is False
    assert gate_results[0].value is None


def test_comparison_deltas():
    rows = compare_to_baselines(sample(), lower_is_better=("latency_ms",))
    test_f1 = [r for r in rows if r.split == "test" and r.metric == "f1"][0]
    assert test_f1.delta == pytest.approx(0.8855 - 0.8629)
    assert test_f1.improved is True
    latency = [r for r in rows if r.split == "test" and r.metric == "latency_ms"][0]
    assert latency.improved is True  # lower latency is better
    assert latency.delta < 0


def test_bar_chart_is_valid_svg():
    svg = bar_chart(["a", "b"], [0.9, 0.8], title="demo")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert svg.count("<rect") == 2
    assert "demo" in svg


def test_line_chart_multiple_series():
    svg = line_chart({"m1": [1, 2, 3], "m2": [3, 2, 1]}, ["x", "y", "z"])
    assert svg.count("<circle") == 6
    assert "m1" in svg and "m2" in svg


def test_comparison_chart_groups():
    svg = comparison_chart(["dev", "test"], ["model", "base"], [[0.9, 0.85], [0.8, 0.8]])
    assert svg.count("<rect") == 4 + 2  # 4 bars + 2 legend swatches


def test_markdown_report_sections():
    text = build_report(sample(), "markdown")
    for section in ("## Summary", "## Metrics by Split", "## Quality Gates",
                    "## Model vs Baseline", "### Baseline: production-v42"):
        assert section in text
    assert "PASS" in text


def test_html_report_is_self_contained():
    html_text = build_report(sample(), "html")
    assert html_text.startswith("<!DOCTYPE html>")
    assert "<svg" in html_text  # inline charts
    assert "anushamukka.com" in html_text


def test_write_report_creates_files(tmp_path):
    md = write_report(sample(), tmp_path / "r" / "report", fmt="markdown")
    assert md.suffix == ".md" and md.exists()
    html_path = write_report(sample(), tmp_path / "report.html", fmt="html")
    assert html_path.exists() and "<svg" in html_path.read_text()


def test_report_class_render_both_formats():
    report = Report(sample(), lower_is_better=("latency_ms",))
    md = report.render("md")
    html_text = report.render("html")
    assert md.startswith("# Q3")
    assert "<table>" in html_text


def test_report_rejects_unknown_format():
    report = Report(sample())
    with pytest.raises(ValueError):
        report.render("pdf")


def test_sample_generator_is_deterministic_with_seed():
    a = make_sample_results(seed=7, jitter=0.01)
    b = make_sample_results(seed=7, jitter=0.01)
    c = make_sample_results(seed=8, jitter=0.01)
    assert a == b
    assert a != c


def test_html_escapes_malicious_content():
    doc = sample()
    doc["title"] = "<script>alert(1)</script>"
    doc["notes"] = "x <img src=x onerror=alert(1)>"
    html_text = build_report(doc, "html")
    assert "<script>" not in html_text
    assert "&lt;script&gt;" in html_text


# ---------------------------------------------------------------------------
# New features: themes, highlights, history/trends
# ---------------------------------------------------------------------------

from eval_report_builder.charts import bar_chart as _bc  # noqa: E402
from eval_report_builder.compare import metric_highlights  # noqa: E402
from eval_report_builder.cli import main as cli_main  # noqa: E402


def _sample_with_history():
    return make_sample_results(seed=42, jitter=0.001, history_points=5)


def test_metric_highlights_honors_lower_is_better():
    hl = {h["metric"]: h for h in metric_highlights(sample(), lower_is_better=("latency_ms",))}
    # dev has the lowest latency in the sample fixture
    assert hl["latency_ms"]["best_split"] == "dev"
    assert hl["latency_ms"]["worst_split"] == "canary"
    # accuracy is higher-is-better: dev (0.9521) beats canary (0.9380)
    assert hl["accuracy"]["best_split"] == "dev"
    assert hl["accuracy"]["worst_split"] == "canary"


def test_markdown_has_highlights_section():
    text = build_report(sample(), "markdown", lower_is_better=("latency_ms",))
    assert "## Highlights" in text
    assert "| Metric | Best split | Worst split |" in text


def test_html_has_highlights_section():
    html_text = build_report(sample(), "html", lower_is_better=("latency_ms",))
    assert "<h2>Highlights</h2>" in html_text
    assert "Best split" in html_text


def test_dark_theme_html_uses_dark_palette():
    html_text = build_report(sample(), "html", theme="dark")
    assert "background: #111827" in html_text
    assert "background: #ffffff" not in html_text


def test_light_theme_is_default_and_explicit():
    default = build_report(sample(), "html")
    explicit = build_report(sample(), "html", theme="light")
    assert "background: #ffffff" in default
    assert default == explicit


def test_unknown_theme_rejected():
    with pytest.raises(ValueError, match="theme"):
        Report(sample(), theme="neon")
    with pytest.raises(ValueError, match="theme"):
        build_report(sample(), "html", theme="neon")


def test_dark_charts_use_dark_tick_colors():
    svg = _bc(["a", "b"], [0.9, 0.8], title="demo", dark=True)
    assert "#9ca3af" in svg  # dark tick color
    svg_light = _bc(["a", "b"], [0.9, 0.8], title="demo")
    assert "#6b7280" in svg_light


def test_history_validation_rejects_bad_entries():
    doc = sample()
    doc["history"] = [{"label": "", "metrics": {"f1": 0.9}}]
    with pytest.raises(ValueError, match="label"):
        validate_results(doc)
    doc["history"] = [{"label": "r1", "metrics": {"f1": "high"}}]
    with pytest.raises(ValueError, match="must be a number"):
        validate_results(doc)
    doc["history"] = [{"metrics": {"f1": 0.9}}]
    with pytest.raises(ValueError, match="label"):
        validate_results(doc)


def test_history_renders_trends_sections():
    doc = _sample_with_history()
    md = build_report(doc, "markdown")
    assert "## Trends" in md
    assert "run-01" in md and "run-05" in md
    html_text = build_report(doc, "html")
    assert "<h2>Trends</h2>" in html_text
    assert "over time" in html_text  # line charts per metric
    # summary mentions the snapshot count
    assert "History snapshots: 5" in md


def test_no_history_shows_placeholder():
    md = build_report(sample(), "markdown")
    assert "_No history recorded._" in md
    html_text = build_report(sample(), "html")
    assert "<h2>Trends</h2>" not in html_text


def test_sample_history_is_deterministic_with_seed():
    a = make_sample_results(seed=7, jitter=0.01, history_points=4)
    b = make_sample_results(seed=7, jitter=0.01, history_points=4)
    assert a == b
    assert len(a["history"]) == 4
    assert [h["label"] for h in a["history"]] == ["run-01", "run-02", "run-03", "run-04"]
    validate_results(a)


def test_cli_build_with_dark_theme(tmp_path):
    src = tmp_path / "results.json"
    src.write_text(json.dumps(_sample_with_history()), encoding="utf-8")
    out = tmp_path / "report.html"
    rc = cli_main(["build", str(src), "-o", str(out), "--format", "html",
                   "--theme", "dark"])
    assert rc == 0
    content = out.read_text(encoding="utf-8")
    assert "background: #111827" in content
    assert "<h2>Trends</h2>" in content


def test_cli_sample_with_history_points(tmp_path):
    out = tmp_path / "demo.json"
    rc = cli_main(["sample", "-o", str(out), "--seed", "3", "--history-points", "3"])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc["history"]) == 3
    validate_results(doc)
