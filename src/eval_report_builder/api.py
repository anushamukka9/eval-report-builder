"""High-level API: load, build, and write evaluation reports."""

from pathlib import Path

from .html import render_html
from .markdown import render_markdown
from .schema import load_results

_FORMATS = ("markdown", "html")
_THEMES = ("light", "dark")


class Report:
    """In-memory report builder around a validated results document.

    >>> r = Report({"title": "demo", "splits": [
    ...     {"name": "test", "metrics": {"accuracy": 0.9}}]})
    >>> "## Metrics by Split" in r.to_markdown()
    True
    """

    def __init__(self, results, lower_is_better=(), theme="light"):
        from .schema import validate_results
        self.results = validate_results(results)
        self.lower_is_better = tuple(lower_is_better)
        self.theme = _normalize_theme(theme)

    @classmethod
    def from_file(cls, path, lower_is_better=(), theme="light"):
        return cls(load_results(path), lower_is_better=lower_is_better, theme=theme)

    def to_markdown(self):
        return render_markdown(self.results, self.lower_is_better)

    def to_html(self):
        return render_html(self.results, self.lower_is_better, theme=self.theme)

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


def _normalize_theme(theme):
    theme = (theme or "light").lower()
    if theme not in _THEMES:
        raise ValueError(f"theme must be one of {_THEMES}, got {theme!r}")
    return theme


def build_report(results, fmt="markdown", lower_is_better=(), theme=None):
    """Render a report string from a results dict (or Report).

    ``theme`` defaults to the Report's own theme (or "light" for a dict).
    """
    if not isinstance(results, Report):
        results = Report(results, lower_is_better=lower_is_better,
                         theme=theme or "light")
    elif theme is not None and theme != results.theme:
        results = Report(results.results, lower_is_better=results.lower_is_better,
                         theme=theme)
    return results.render(fmt)


def write_report(results, out, fmt="markdown", lower_is_better=(), theme=None):
    """Render and write a report file. Returns the Path written.

    ``theme`` defaults to the Report's own theme (or "light" for a dict).
    """
    if not isinstance(results, Report):
        results = Report(results, lower_is_better=lower_is_better,
                         theme=theme or "light")
    elif theme is not None and theme != results.theme:
        results = Report(results.results, lower_is_better=results.lower_is_better,
                         theme=theme)
    fmt = _normalize_format(fmt)
    text = results.render(fmt)
    path = Path(out)
    if not path.suffix:
        path = path.with_suffix(".html" if fmt == "html" else ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
