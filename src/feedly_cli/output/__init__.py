"""Public presentation API; no HTTP requests are made by this package."""

from .markdown import add_markdown, write_markdown
from .render import render, render_error

__all__ = ["add_markdown", "render", "render_error", "write_markdown"]
