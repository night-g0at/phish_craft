import re
import tempfile
import webbrowser
from pathlib import Path
from phishing.state import PhishingState


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name or "phishing_email"


async def save_output(state: PhishingState) -> dict:
    company_name = state["org_data"].company_name if state.get("org_data") else "output"
    filename = f"{_safe_filename(company_name)}.html"
    output_path = Path(tempfile.gettempdir()) / filename

    output_path.write_text(state["html_email"], encoding="utf-8")
    webbrowser.open(output_path.as_uri())

    return {"output_path": str(output_path)}
