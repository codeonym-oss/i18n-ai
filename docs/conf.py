"""Sphinx configuration: MyST pages, Shibuya theme."""

from importlib.metadata import version as _version

project = "i18n-ai"
author = "codeonym-oss"
copyright = "codeonym-oss — MIT License"
release = _version("i18n-ai")
version = ".".join(release.split(".")[:2])

extensions = ["myst_parser"]
exclude_patterns = ["_build"]

# Pages: Markdown, with ```{directive} blocks and `#heading` anchors for links.
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

html_theme = "shibuya"
html_title = "i18n-ai"
html_baseurl = "https://docs.codeonym.work/projects/i18n-ai/"
html_context = {
    "source_type": "github",
    "source_user": "codeonym-oss",
    "source_repo": "i18n-ai",
    "source_version": "main",
    "source_docs_path": "/docs/",
}
html_theme_options = {
    "accent_color": "teal",
    "github_url": "https://github.com/codeonym-oss/i18n-ai",
    "nav_links": [
        {"title": "Guide", "url": "guide/getting-started"},
        {"title": "Commands", "url": "reference/commands"},
    ],
}
