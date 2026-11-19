"""Shared output-filename helpers so nodes agree on file names."""

import re


def safe_filename(name: str, fallback: str = "phishing_email") -> str:
    """Slugify a company name into a filesystem-safe base (no extension)."""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name or fallback


def landing_page_filename(company_name: str) -> str:
    """Relative filename for the landing page that the email CTA links to."""
    return f"{safe_filename(company_name, 'phishing')}_landing.html"
