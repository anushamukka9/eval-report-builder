"""Validation for the evaluation-results document.

Expected JSON shape (all keys are documented in docs/usage.md):

{
  "title": "Report title",
  "model": {"name": "model-name", "version": "v1.0"},
  "generated_at": "2026-09-17T12:00:00Z",          # optional ISO-8601 string
  "notes": "Free text about the run",               # optional
  "splits": [
    {"name": "dev", "samples": 1200,
     "metrics": {"accuracy": 0.93, "f1": 0.90, "latency_ms": 12.4}}
  ],
  "baselines": [                                     # optional
    {"name": "previous", "splits": [
       {"name": "dev", "samples": 1200, "metrics": {"accuracy": 0.91, ...}}]}
  ],
  "gates": [                                         # optional
    {"metric": "f1", "split": "test", "op": ">=",
     "threshold": 0.90, "severity": "error",
     "description": "F1 must stay above 0.90 on test"}
  ]
}
"""

import json
from pathlib import Path

_METRIC_TYPES = (int, float)
_GATE_OPS = {">=", ">", "<=", "<", "=="}


def _err(msg):
    raise ValueError(f"invalid results document: {msg}")


def _req_mapping(obj, name):
    if not isinstance(obj, dict):
        _err(f"'{name}' must be an object")
    return obj


def _req_list(obj, name):
    if not isinstance(obj, list):
        _err(f"'{name}' must be a list")
    return obj


def validate_split(split, *, where):
    _req_mapping(split, f"{where} split")
    name = split.get("name")
    if not isinstance(name, str) or not name:
        _err(f"{where} split must have a non-empty string 'name'")
    metrics = split.get("metrics")
    _req_mapping(metrics, f"{where} split '{name}' metrics")
    if not metrics:
        _err(f"{where} split '{name}' has no metrics")
    for key, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, _METRIC_TYPES):
            _err(f"metric '{key}' in {where} split '{name}' must be a number")
    samples = split.get("samples")
    if samples is not None and (isinstance(samples, bool) or not isinstance(samples, int) or samples < 0):
        _err(f"'samples' in {where} split '{name}' must be a non-negative int")
    return split


def validate_gate(gate, index):
    _req_mapping(gate, f"gates[{index}]")
    for field in ("metric", "op"):
        if not isinstance(gate.get(field), str) or not gate.get(field):
            _err(f"gates[{index}] must have a non-empty string '{field}'")
    if gate["op"] not in _GATE_OPS:
        _err(f"gates[{index}].op must be one of {sorted(_GATE_OPS)}")
    threshold = gate.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, _METRIC_TYPES):
        _err(f"gates[{index}].threshold must be a number")
    if "split" in gate and (not isinstance(gate["split"], str) or not gate["split"]):
        _err(f"gates[{index}].split must be a non-empty string if given")
    severity = gate.get("severity", "error")
    if severity not in ("error", "warn"):
        _err(f"gates[{index}].severity must be 'error' or 'warn'")
    gate.setdefault("severity", "error")
    return gate


def validate_results(doc):
    """Validate a decoded results document; return the normalized document."""
    _req_mapping(doc, "results")
    doc = dict(doc)
    if not isinstance(doc.get("title"), str) or not doc["title"]:
        _err("'title' must be a non-empty string")
    model = doc.get("model", {})
    _req_mapping(model, "model")
    if "name" in model and (not isinstance(model["name"], str) or not model["name"]):
        _err("'model.name' must be a non-empty string if given")
    doc["model"] = model

    splits = _req_list(doc.get("splits"), "splits")
    if not splits:
        _err("'splits' must contain at least one split")
    doc["splits"] = [validate_split(s, where="model") for s in splits]

    baselines = doc.get("baselines", [])
    norm_baselines = []
    for b in _req_list(baselines, "baselines"):
        _req_mapping(b, "baseline")
        name = b.get("name")
        if not isinstance(name, str) or not name:
            _err("each baseline must have a non-empty string 'name'")
        bsplits = _req_list(b.get("splits"), f"baseline '{name}' splits")
        if not bsplits:
            _err(f"baseline '{name}' must contain at least one split")
        norm_baselines.append(
            {"name": name, "splits": [validate_split(s, where=f"baseline '{name}'") for s in bsplits]}
        )
    doc["baselines"] = norm_baselines

    gates = doc.get("gates", [])
    doc["gates"] = [validate_gate(g, i) for i, g in enumerate(_req_list(gates, "gates"))]
    return doc


def load_results(path):
    """Load and validate a results JSON file. Raises ValueError on bad input."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"results file not found: {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid results document: not valid JSON: {exc}") from exc
    return validate_results(doc)
