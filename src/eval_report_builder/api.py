"""High-level API: load, build, and write evaluation reports."""

from pathlib import Path

from .html import render_html
from .markdown import render_markdown
from .schema import load_results

_FORMATS = ("markdown", "html")


class Report:
    """In-memory report builder around a validated results document.

    >>> r = Report({"title": "demo", "splits": [
    ...     {"name": "test", "metrics": {"accuracy": 0.9}}]})
    >>> "## Metrics by Split" in r.to_markdown()
    True
    """

    def __init__(self, results, lower_is_better=()):
        from .schema import validate_results
        self.results = validate_results(results)
        self.lower_is_better = tuple(lower_is_better)

    @classmethod
    def from_file(cls, path, lower_is_better=()):
        return cls(load_results(path), lower_is_better=lower_is_better)

    def to_markdown(self):
        return render_markdown(self.results, self.lower_is_better)

    def to_html(self):
        return render_html(self.results, self.lower_is_better)

    def render(self, fmt):
        fmt = _normalize_format(fmt)
        return self.to_html() if fmt == "html" else self.to_markdown()


def _normalize_format(fmt):
    fmt = (fmt or "markdown").lower()
    if fmt in ("md", "markdown"):
        return "markdown"
    if fmt in ("html", "htm"):
        return "html"
    raise ValueError(f"format must be one of {_FORMATS}, got {fmt!r}")


def build_report(results, fmt="markdown", lower_is_better=()):
    """Render a report string from a results dict (or Report)."""
    if not isinstance(results, Report):
        results = Report(results, lower_is_better=lower_is_better)
    return results.render(fmt)


def write_report(results, out, fmt="markdown", lower_is_better=()):
    """Render and write a report file. Returns the Path written."""
    if not isinstance(results, Report):
        results = Report(results, lower_is_better=lower_is_better)
    fmt = _normalize_format(fmt)
    text = results.render(fmt)
    path = Path(out)
    if not path.suffix:
        path = path.with_suffix(".html" if fmt == "html" else ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
