"""Model-vs-baseline comparison logic.

For every (split, metric) shared between the model and a baseline, compute
the absolute and relative delta. Delta direction matters for readability:
higher-is-better is the default assumption, but callers can pass a
``lower_is_better`` set (e.g. latency_ms, error_rate) so deltas are
interpreted correctly in reports.
"""

from dataclasses import dataclass, field


@dataclass
class Comparison:
    baseline_name: str
    split: str
    metric: str
    model_value: float
    baseline_value: float
    delta: float            # model - baseline
    rel_delta_pct: float    # (model - baseline) / |baseline| * 100
    lower_is_better: bool = False

    @property
    def improved(self):
        return self.delta < 0 if self.lower_is_better else self.delta > 0


def compare_to_baselines(results, lower_is_better=()):
    """Return a list of Comparison rows across all baselines/splits/metrics."""
    lower = set(lower_is_better)
    rows = []
    model_splits = {s["name"]: s["metrics"] for s in results["splits"]}
    for baseline in results.get("baselines", []):
        b_splits = {s["name"]: s["metrics"] for s in baseline["splits"]}
        for split, b_metrics in b_splits.items():
            m_metrics = model_splits.get(split)
            if not m_metrics:
                continue
            for metric, b_val in b_metrics.items():
                if metric not in m_metrics:
                    continue
                m_val = m_metrics[metric]
                delta = m_val - b_val
                rel = (delta / abs(b_val) * 100.0) if b_val != 0 else float("inf")
                rows.append(Comparison(
                    baseline_name=baseline["name"],
                    split=split,
                    metric=metric,
                    model_value=m_val,
                    baseline_value=b_val,
                    delta=delta,
                    rel_delta_pct=rel,
                    lower_is_better=metric in lower,
                ))
    return rows


def best_and_worst_split(results, metric):
    """Return (best_split_name, worst_split_name, values) for a metric."""
    pairs = [(s["name"], s["metrics"][metric])
             for s in results["splits"] if metric in s["metrics"]]
    if not pairs:
        return None, None, []
    best = max(pairs, key=lambda p: p[1])
    worst = min(pairs, key=lambda p: p[1])
    return best[0], worst[0], pairs


def metric_union(results):
    """All metric names across splits and baselines, in first-seen order."""
    seen, out = set(), []
    def add(metrics):
        for key in metrics:
            if key not in seen:
                seen.add(key)
                out.append(key)
    for s in results["splits"]:
        add(s["metrics"])
    for b in results.get("baselines", []):
        for s in b["splits"]:
            add(s["metrics"])
    return out
