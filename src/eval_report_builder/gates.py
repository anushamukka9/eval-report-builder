"""Pass/fail quality gates over evaluation metrics.

A gate names a metric (optionally scoped to one split) and a comparison
against a threshold::

    {"metric": "f1", "split": "test", "op": ">=", "threshold": 0.90,
     "severity": "error", "description": "F1 must stay above 0.90 on test"}

evaluate_gates(results) returns a list of GateResult objects plus a summary
of whether any gate failed. Severity "error" gates flip the overall verdict;
"warn" gates are reported but do not fail the build — handy for CI usage.
"""

from dataclasses import dataclass

_OPS = {
    ">=": lambda v, t: v >= t,
    ">": lambda v, t: v > t,
    "<=": lambda v, t: v <= t,
    "<": lambda v, t: v < t,
    "==": lambda v, t: v == t,
}


@dataclass
class Gate:
    metric: str
    op: str
    threshold: float
    split: str | None = None
    severity: str = "error"
    description: str = ""

    @classmethod
    def from_dict(cls, data):
        return cls(
            metric=data["metric"],
            op=data["op"],
            threshold=data["threshold"],
            split=data.get("split"),
            severity=data.get("severity", "error"),
            description=data.get("description", ""),
        )


@dataclass
class GateResult:
    gate: Gate
    value: float | None
    passed: bool
    message: str

    @property
    def severity(self):
        return self.gate.severity


def _metric_value(results, metric, split):
    """Find the metric value; if split is None, use the first split that has it."""
    splits = results["splits"]
    if split is not None:
        for s in splits:
            if s["name"] == split:
                return s["metrics"].get(metric)
        return None
    for s in splits:
        if metric in s["metrics"]:
            return s["metrics"][metric]
    return None


def evaluate_gates(results):
    """Evaluate every gate. Returns (results_list, overall_passed).

    overall_passed is False only when an "error" gate fails; unknown metric
    values fail the gate with a clear message.
    """
    out = []
    for raw in results.get("gates", []):
        gate = Gate.from_dict(raw)
        value = _metric_value(results, gate.metric, gate.split)
        if value is None:
            where = f" on split '{gate.split}'" if gate.split else ""
            out.append(GateResult(gate, None, False,
                                 f"metric '{gate.metric}'{where} not found in results"))
            continue
        ok = _OPS[gate.op](value, gate.threshold)
        label = f"{gate.metric} {gate.op} {gate.threshold}"
        where = f" [{gate.split}]" if gate.split else ""
        if ok:
            message = f"PASS{where}: {label} (value {value})"
        else:
            message = f"FAIL{where}: {label} (value {value})"
        out.append(GateResult(gate, value, ok, message))
    overall = all(r.passed or r.severity == "warn" for r in out)
    return out, overall
