"""HTML report renderer: self-contained single file with inline SVG charts."""

import html as _html
from datetime import datetime, timezone

from .charts import bar_chart, comparison_chart
from .compare import compare_to_baselines, metric_union
from .gates import evaluate_gates

_CSS = """
body { font-family: system-ui, -apple-system, sans-serif; color: #111827;
       max-width: 960px; margin: 0 auto; padding: 32px 20px; line-height: 1.5; }
h1 { font-size: 1.9rem; border-bottom: 3px solid #2563eb; padding-bottom: 8px; }
h2 { font-size: 1.35rem; margin-top: 2rem; color: #1f2937; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.92rem; }
th, td { border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; }
th { background: #f3f4f6; font-weight: 600; }
tr:nth-child(even) td { background: #f9fafb; }
.meta { color: #4b5563; margin-bottom: 4px; }
.notes { background: #eff6ff; border-left: 4px solid #2563eb; padding: 10px 14px;
         margin: 16px 0; border-radius: 4px; }
.gate-pass { color: #059669; font-weight: 600; }
.gate-fail { color: #dc2626; font-weight: 600; }
.gate-warn { color: #d97706; font-weight: 600; }
.verdict { font-size: 1.1rem; padding: 10px 14px; border-radius: 6px; margin: 12px 0; }
.verdict.pass { background: #ecfdf5; border: 1px solid #059669; }
.verdict.fail { background: #fef2f2; border: 1px solid #dc2626; }
.improved { color: #059669; font-weight: 600; }
.regressed { color: #dc2626; font-weight: 600; }
.chart { margin: 16px 0; overflow-x: auto; }
.footer { margin-top: 3rem; font-size: 0.8rem; color: #9ca3af;
          border-top: 1px solid #e5e7eb; padding-top: 12px; }
"""


def _esc(v):
    return _html.escape(str(v), quote=True)


def _fmt(v):
    return f"{v:.4f}" if isinstance(v, float) else str(v)


def render_html(results, lower_is_better=()):
    """Render the full HTML report as a single self-contained document."""
    title = results["title"]
    model = results.get("model", {})
    parts = ["<!DOCTYPE html>", "<html lang=\"en\">", "<head>",
             '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1">',
             f"<title>{_esc(title)}</title>", f"<style>{_CSS}</style>", "</head>", "<body>"]
    parts.append(f"<h1>{_esc(title)}</h1>")

    if model.get("name"):
        name = model["name"] + (f" ({_esc(model['version'])})" if model.get("version") else "")
        parts.append(f'<p class="meta"><strong>Model:</strong> {_esc(name)}</p>')
    if results.get("generated_at"):
        parts.append(f'<p class="meta"><strong>Generated:</strong> {_esc(results["generated_at"])}</p>')
    if results.get("notes"):
        parts.append(f'<div class="notes">{_esc(results["notes"])}</div>')

    total = sum(s.get("samples") or 0 for s in results["splits"])
    parts.append("<h2>Summary</h2><ul>")
    parts.append(f"<li>Splits evaluated: {len(results['splits'])}</li>")
    if total:
        parts.append(f"<li>Total samples: {total}</li>")
    parts.append(f"<li>Metrics reported: {len(metric_union(results))}</li>")
    if results.get("baselines"):
        names = ", ".join(_esc(b["name"]) for b in results["baselines"])
        parts.append(f"<li>Baselines compared: {names}</li>")
    parts.append("</ul>")

    # Metrics table
    metrics = metric_union(results)
    parts.append("<h2>Metrics by Split</h2><table><thead><tr><th>Metric</th>")
    parts.extend(f"<th>{_esc(s['name'])}</th>" for s in results["splits"])
    parts.append("</tr></thead><tbody>")
    for metric in metrics:
        parts.append("<tr>" + f"<td><strong>{_esc(metric)}</strong></td>" +
                     "".join(f"<td>{_esc(_fmt(s['metrics'][metric])) if metric in s['metrics'] else '—'}</td>"
                             for s in results["splits"]) + "</tr>")
    parts.append("</tbody></table>")

    # Charts: bar chart per metric across splits
    parts.append("<h2>Charts</h2>")
    for metric in metrics:
        labels, values = [], []
        for s in results["splits"]:
            if metric in s["metrics"]:
                labels.append(s["name"])
                values.append(s["metrics"][metric])
        if values:
            parts.append('<div class="chart">' +
                         bar_chart(labels, values, title=f"{metric} by split") + "</div>")

    # Quality gates
    gate_results, overall = evaluate_gates(results)
    parts.append("<h2>Quality Gates</h2>")
    if gate_results:
        cls = "pass" if overall else "fail"
        parts.append(f'<div class="verdict {cls}">Overall verdict: {"PASS" if overall else "FAIL"}</div><ul>')
        for r in gate_results:
            gcls = "gate-pass" if r.passed else ("gate-warn" if r.severity == "warn" else "gate-fail")
            parts.append(f'<li class="{gcls}">{_esc(r.message)}</li>')
        parts.append("</ul>")
    else:
        parts.append("<p><em>No gates defined.</em></p>")

    # Model vs baseline comparisons
    comparisons = compare_to_baselines(results, lower_is_better)
    parts.append("<h2>Model vs Baseline</h2>")
    if comparisons:
        baselines = sorted({c.baseline_name for c in comparisons})
        # grouped chart for the first metric shared across everything
        chart_metrics = [m for m in metrics if any(
            c.metric == m and c.baseline_name == baselines[0] for c in comparisons)]
        if chart_metrics:
            metric = chart_metrics[0]
            groups = sorted({c.split for c in comparisons
                             if c.baseline_name == baselines[0] and c.metric == metric})
            names = ["model"] + baselines
            series_values = []
            for name in names:
                vals = []
                for g in groups:
                    if name == "model":
                        vals.append(next(s["metrics"][metric]
                                        for s in results["splits"] if s["name"] == g))
                    else:
                        c = next(c for c in comparisons
                                 if c.baseline_name == name and c.split == g and c.metric == metric)
                        vals.append(c.baseline_value)
                series_values.append(vals)
            parts.append('<div class="chart">' +
                         comparison_chart(groups, names, series_values,
                                          title=f"{metric}: model vs baselines") + "</div>")
        for baseline in baselines:
            parts.append(f"<h3>Baseline: {_esc(baseline)}</h3>")
            parts.append("<table><thead><tr><th>Split</th><th>Metric</th><th>Model</th>"
                         "<th>Baseline</th><th>Δ</th></tr></thead><tbody>")
            for c in comparisons:
                if c.baseline_name != baseline:
                    continue
                rel = f"{c.rel_delta_pct:+.2f}%" if c.rel_delta_pct != float("inf") else "n/a"
                arrow = "▲" if c.improved else ("▼" if c.delta != 0 else "■")
                dcls = "improved" if c.improved else ("regressed" if c.delta != 0 else "")
                parts.append("<tr>" + "".join(
                    f"<td>{_esc(x)}</td>" for x in
                    (c.split, c.metric, _fmt(c.model_value), _fmt(c.baseline_value))) +
                    f'<td class="{dcls}">{arrow} {c.delta:+.4f} ({rel})</td></tr>')
            parts.append("</tbody></table>")
    else:
        parts.append("<p><em>No baselines defined.</em></p>")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts.append(f'<div class="footer">Generated by <strong>eval-report-builder</strong> '
                 f'<a href="https://anushamukka.com">anushamukka.com</a> · {now}</div>')
    parts.extend(["</body>", "</html>"])
    return "\n".join(parts)
