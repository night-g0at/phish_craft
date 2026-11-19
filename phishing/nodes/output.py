import webbrowser
from pathlib import Path

from phishing.naming import safe_filename
from phishing.state import PhishingState


async def save_output(state: PhishingState) -> dict:
    company_name = state["org_data"].company_name if state.get("org_data") else "output"
    filename = f"{safe_filename(company_name)}.html"
    output_path = Path.cwd() / filename

    output_path.write_text(state["html_email"], encoding="utf-8")

    result = {"output_path": str(output_path)}

    # Save the matching landing page alongside the email, if one was generated.
    landing_html = state.get("landing_page_html")
    if landing_html:
        landing_name = state.get("landing_page_filename") or f"{safe_filename(company_name)}_landing.html"
        landing_path = Path.cwd() / landing_name
        landing_path.write_text(landing_html, encoding="utf-8")
        result["landing_page_path"] = str(landing_path)

    webbrowser.open(output_path.as_uri())
    if result.get("landing_page_path"):
        webbrowser.open(Path(result["landing_page_path"]).as_uri())

    return result
