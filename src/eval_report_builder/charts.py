"""Inline-SVG chart builders — zero dependencies, embeddable in HTML reports.

bar_chart(series, labels, ...)   -> vertical bar chart SVG string
line_chart(series_map, labels)   -> multi-line chart SVG string
comparison_chart(...)            -> grouped bar chart: model vs baselines

All charts are hand-rolled SVG: a single self-contained ``<svg>`` element
with inline styles, safe to paste into an HTML report or email.
"""

import html as _html
from math import floor, log10


def _esc(text):
    return _html.escape(str(text), quote=True)


def _nice_step(span, target_ticks=5):
    """Pick a human-friendly tick step for an axis spanning `span`."""
    if span <= 0:
        return 1.0
    raw = span / target_ticks
    mag = 10 ** floor(log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        if raw <= mult * mag:
            return mult * mag
    return 10 * mag


def bar_chart(labels, values, title="", value_fmt=".3f", color="#2563eb",
              width=560, height=300, y_label=""):
    """Vertical bar chart for one metric across splits (or models)."""
    labels = list(labels)
    values = list(values)
    n = len(values)
    margin = dict(top=38, right=16, bottom=46, left=64)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    vmax = max(values) if values else 1.0
    vmin = min(0.0, min(values)) if values else 0.0
    span = vmax - vmin or 1.0
    pad = span * 0.08
    top = vmax + pad
    bottom = vmin - pad if vmin < 0 else 0.0
    span = top - bottom or 1.0

    def y_of(v):
        return margin["top"] + plot_h * (1 - (v - bottom) / span)

    slot = plot_w / max(n, 1)
    bar_w = min(slot * 0.62, 72)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'role="img" aria-label="{_esc(title or "bar chart")}" '
             f'style="font-family:system-ui,sans-serif">']
    if title:
        parts.append(f'<text x="{width/2}" y="20" text-anchor="middle" font-size="14" '
                     f'font-weight="600">{_esc(title)}</text>')

    step = _nice_step(top - bottom)
    tick = bottom
    while tick <= top + 1e-9:
        y = y_of(tick)
        if margin["top"] - 4 <= y <= margin["top"] + plot_h + 4:
            parts.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" '
                         f'x2="{width - margin["right"]}" y2="{y:.1f}" stroke="#e5e7eb"/>')
            parts.append(f'<text x="{margin["left"] - 8}" y="{y + 4:.1f}" text-anchor="end" '
                         f'font-size="11" fill="#6b7280">{tick:.{3}g}</text>')
        tick += step
    if y_label:
        parts.append(f'<text x="14" y="{margin["top"] + plot_h/2}" text-anchor="middle" '
                     f'font-size="11" fill="#6b7280" transform="rotate(-90 14 '
                     f'{margin["top"] + plot_h/2})">{_esc(y_label)}</text>')

    for i, (lab, val) in enumerate(zip(labels, values)):
        x = margin["left"] + i * slot + (slot - bar_w) / 2
        y = y_of(max(val, bottom))
        h = max(y_of(bottom) - y, 1.0)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                     f'fill="{color}" rx="3"/>')
        parts.append(f'<text x="{x + bar_w/2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
                     f'font-size="11" font-weight="600">{val:{value_fmt}}</text>')
        parts.append(f'<text x="{x + bar_w/2:.1f}" y="{height - 24}" text-anchor="middle" '
                     f'font-size="11" fill="#374151">{_esc(lab)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def line_chart(series, x_labels, title="", color_palette=None, width=560, height=300):
    """Multi-series line chart. `series` is {name: [values]} aligned to x_labels."""
    x_labels = list(x_labels)
    series = {k: list(v) for k, v in series.items()}
    palette = color_palette or ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed"]
    margin = dict(top=38, right=16, bottom=46, left=64)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    all_vals = [v for vals in series.values() for v in vals]
    vmax = max(all_vals) if all_vals else 1.0
    vmin = min(all_vals) if all_vals else 0.0
    pad = (vmax - vmin) * 0.08 or 0.05
    top, bottom = vmax + pad, vmin - pad
    n = max(len(x_labels), 2)

    def xy(i, v):
        x = margin["left"] + plot_w * i / (n - 1)
        y = margin["top"] + plot_h * (1 - (v - bottom) / (top - bottom))
        return x, y

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'role="img" aria-label="{_esc(title or "line chart")}" '
             f'style="font-family:system-ui,sans-serif">']
    if title:
        parts.append(f'<text x="{width/2}" y="20" text-anchor="middle" font-size="14" '
                     f'font-weight="600">{_esc(title)}</text>')

    step = _nice_step(top - bottom)
    tick = bottom
    while tick <= top + 1e-9:
        _, y = xy(0, tick)
        if margin["top"] - 4 <= y <= margin["top"] + plot_h + 4:
            parts.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" '
                         f'x2="{width - margin["right"]}" y2="{y:.1f}" stroke="#e5e7eb"/>')
            parts.append(f'<text x="{margin["left"] - 8}" y="{y + 4:.1f}" text-anchor="end" '
                         f'font-size="11" fill="#6b7280">{tick:.{3}g}</text>')
        tick += step

    for i, lab in enumerate(x_labels):
        x = margin["left"] + plot_w * i / (n - 1)
        parts.append(f'<text x="{x:.1f}" y="{height - 24}" text-anchor="middle" '
                     f'font-size="11" fill="#374151">{_esc(lab)}</text>')

    lx = width - margin["right"] - 4
    for j, (name, vals) in enumerate(series.items()):
        color = palette[j % len(palette)]
        d = " ".join(f"{'M' if i == 0 else 'L'}{xy(i, v)[0]:.1f},{xy(i, v)[1]:.1f}"
                     for i, v in enumerate(vals))
        parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for i, v in enumerate(vals):
            x, y = xy(i, v)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"/>')
        ly = margin["top"] + j * 18
        parts.append(f'<rect x="{lx - 120}" y="{ly - 10}" width="12" height="12" fill="{color}" rx="2"/>')
        parts.append(f'<text x="{lx - 102}" y="{ly}" font-size="11" fill="#374151">{_esc(name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def comparison_chart(groups, series_names, series_values, title=""):
    """Grouped bar chart: rows per group (split), one bar per series (model/baseline)."""
    groups = list(groups)
    series_names = list(series_names)
    palette = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed"]
    width, height = 640, 320
    margin = dict(top=38, right=16, bottom=46, left=64)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    flat = [v for vals in series_values for v in vals]
    vmax = max(flat) if flat else 1.0
    vmin = min(0.0, min(flat)) if flat else 0.0
    top = vmax * 1.10
    span = top - vmin or 1.0

    def y_of(v):
        return margin["top"] + plot_h * (1 - (v - vmin) / span)

    slot = plot_w / max(len(groups), 1)
    m = len(series_names)
    bar_w = min(slot * 0.7 / max(m, 1), 44)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'role="img" aria-label="{_esc(title or "comparison chart")}" '
             f'style="font-family:system-ui,sans-serif">']
    if title:
        parts.append(f'<text x="{width/2}" y="20" text-anchor="middle" font-size="14" '
                     f'font-weight="600">{_esc(title)}</text>')

    step = _nice_step(top - vmin)
    tick = vmin
    while tick <= top + 1e-9:
        y = y_of(tick)
        parts.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" '
                     f'x2="{width - margin["right"]}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{margin["left"] - 8}" y="{y + 4:.1f}" text-anchor="end" '
                     f'font-size="11" fill="#6b7280">{tick:.{3}g}</text>')
        tick += step

    for gi, group in enumerate(groups):
        gx = margin["left"] + gi * slot
        for si, (name, vals) in enumerate(zip(series_names, series_values)):
            v = vals[gi]
            x = gx + (slot - bar_w * m) / 2 + si * bar_w
            y = y_of(v)
            h = max(y_of(vmin) - y, 1.0)
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                         f'fill="{palette[si % len(palette)]}" rx="3"/>')
        parts.append(f'<text x="{gx + slot/2:.1f}" y="{height - 24}" text-anchor="middle" '
                     f'font-size="11" fill="#374151">{_esc(group)}</text>')

    for si, name in enumerate(series_names):
        lx, ly = margin["left"] + si * 150, margin["top"] - 22
        parts.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" '
                     f'fill="{palette[si % len(palette)]}" rx="2"/>')
        parts.append(f'<text x="{lx + 16}" y="{ly}" font-size="11" fill="#374151">{_esc(name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)
