"""Markdown report renderer."""

from .compare import compare_to_baselines, metric_union
from .gates import evaluate_gates


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _gates_section(gate_results, overall):
    lines = ["## Quality Gates", ""]
    if not gate_results:
        lines.append("_No gates defined._")
        return "\n".join(lines)
    verdict = "PASS" if overall else "FAIL"
    lines.append(f"**Overall verdict: {verdict}**")
    lines.append("")
    for r in gate_results:
        icon = "✅" if r.passed else ("⚠️" if r.severity == "warn" else "❌")
        lines.append(f"- {icon} {r.message}")
    return "\n".join(lines)


def _metrics_table(results):
    metrics = metric_union(results)
    headers = ["Metric"] + [s["name"] for s in results["splits"]]
    rows = []
    for metric in metrics:
        row = [metric]
        for s in results["splits"]:
            v = s["metrics"].get(metric)
            row.append(_fmt(v) if v is not None else "—")
        rows.append(row)
    return _table(headers, rows)


def _comparison_section(results, lower_is_better):
    comparisons = compare_to_baselines(results, lower_is_better)
    lines = ["## Model vs Baseline", ""]
    if not comparisons:
        lines.append("_No baselines defined._")
        return "\n".join(lines)
    for baseline in sorted({c.baseline_name for c in comparisons}):
        lines.append(f"### Baseline: {baseline}")
        lines.append("")
        rows = []
        for c in comparisons:
            if c.baseline_name != baseline:
                continue
            arrow = "▲" if c.improved else ("▼" if c.delta != 0 else "■")
            sign = "+" if c.delta >= 0 else ""
            rel = f"{c.rel_delta_pct:+.2f}%" if c.rel_delta_pct != float("inf") else "n/a"
            rows.append([c.split, c.metric, _fmt(c.model_value),
                         _fmt(c.baseline_value), f"{arrow} {sign}{c.delta:.4f} ({rel})"])
        lines.append(_table(["Split", "Metric", "Model", "Baseline", "Δ"], rows))
        lines.append("")
    return "\n".join(lines)


def render_markdown(results, lower_is_better=()):
    """Render the full Markdown report for a validated results document."""
    title = results["title"]
    model = results.get("model", {})
    lines = [f"# {title}", ""]

    meta = []
    if model.get("name"):
        name = model["name"] + (f" ({model['version']})" if model.get("version") else "")
        meta.append(f"**Model:** {name}")
    if results.get("generated_at"):
        meta.append(f"**Generated:** {results['generated_at']}")
    if meta:
        lines.extend(meta + [""])
    if results.get("notes"):
        lines.append(f"> {results['notes']}")
        lines.append("")

    total = sum(s.get("samples") or 0 for s in results["splits"])
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Splits evaluated: {len(results['splits'])}")
    if total:
        lines.append(f"- Total samples: {total}")
    lines.append(f"- Metrics reported: {len(metric_union(results))}")
    if results.get("baselines"):
        lines.append(f"- Baselines compared: {', '.join(b['name'] for b in results['baselines'])}")
    lines.append("")

    lines.append("## Metrics by Split")
    lines.append("")
    lines.append(_metrics_table(results))
    lines.append("")

    gate_results, overall = evaluate_gates(results)
    lines.append(_gates_section(gate_results, overall))
    lines.append("")
    lines.append(_comparison_section(results, lower_is_better))
    return "\n".join(lines).rstrip() + "\n"
