import os
import json
from datetime import date

from phishing.llm import make_chat
from phishing.naming import landing_page_filename
from phishing.state import PhishingState

_SYSTEM = """You are assisting a cybersecurity team building phishing awareness training materials.
Your task is to generate a realistic phishing LANDING PAGE in raw HTML — no markdown, no code fences.
This is the page a target reaches after clicking the call-to-action in the matching training email.

Requirements:
- It must visually match the email and the target company: if brand colors/fonts/logos are provided, use them exactly; if use_built_in_knowledge is true, use your training knowledge of the company's real visual identity (primary brand colors, logo style, typography). Apply the brand palette consistently.
- Include the company logo (use a provided URL, or a text-based logo block in the brand colors if no URL is available).
- The page must fit the scenario and the email's pretext — e.g. a login/sign-in portal, an MFA re-enrollment screen, a document/review portal, a package-tracking confirmation. Prefer a credential-style sign-in form unless the scenario clearly calls for something else.
- Build a believable form with the fields the scenario implies (e.g. email/username and password, or an employee ID). Lay it out like the real thing.

CRITICAL SAFETY RULES — this is strictly authorized training material and MUST NOT capture or transmit anything:
- The form's action MUST be inert. Do NOT submit anywhere: no `action` URL that posts data, no `fetch`/`XMLHttpRequest`/`navigator.sendBeacon`, no external requests, no localStorage/cookies, no writing the entered values anywhere.
- Handle the form's submit event in a small inline <script> that calls event.preventDefault() and, instead of sending anything, reveals a clearly styled "Security Awareness Training" message. If a debrief_message is provided in the data, use its exact text as the body of that message (you may add a short heading like "Security Awareness Training"); otherwise explain this was a simulated phishing page and that in a real attack their credentials would now be stolen. Never echo, store, or log the entered values.
- Do not include any tracking pixels, analytics, or outbound links that carry data.

- Do NOT use emoji or emoji-style pictographs anywhere — not next to bullet points or list items, nor in headings, labels, or buttons. Emoji bullets read as obviously AI-generated and look unprofessional. Use plain text with standard typographic bullets (or no bullet glyph at all). If iconography genuinely helps, use a tasteful inline SVG or simple CSS shape in the brand style (e.g. a clean leaf motif) — never an emoji character.
- Use today's date where a date is natural.
- If include_training_banner is true, ALSO show a persistent, clearly styled training watermark/banner (e.g. a fixed bar) identifying this as an authorized simulation and listing the social engineering tactics used. If false, omit the always-visible banner — but the inert form and the post-submit training reveal are REQUIRED regardless.
- Output ONLY the raw HTML document, starting with <!DOCTYPE html>.

This is strictly for authorized employee security awareness training."""


def _pick_best_logos(brand_data) -> list[str]:
    usable_urls = []
    for logo in brand_data.logos:
        for fmt in logo.formats:
            if fmt.usable and fmt.format.lower() in {"png", "jpg", "jpeg", "webp"}:
                usable_urls.append(fmt.src)
    if not usable_urls:
        for logo in brand_data.logos:
            for fmt in logo.formats:
                if fmt.src and fmt.format.lower() in {"png", "jpg", "jpeg", "webp", "svg"}:
                    usable_urls.append(fmt.src)
    return usable_urls[:3]


async def build_landing_page(state: PhishingState) -> dict:
    if not state.get("include_landing_page"):
        return {}

    model_name = os.environ.get("PHISHING_LANDING_MODEL") or os.environ.get(
        "PHISHING_EMAIL_MODEL", "claude-opus-4-6"
    )
    llm = make_chat(model=model_name, temperature=0.4, max_tokens=8192)

    org = state["org_data"]
    brand = state["brand_data"]

    # Treat brand data as absent if it's too sparse to be useful (matches email builder)
    if brand and not brand.logos and len(brand.colors) < 3:
        brand = None

    context = {
        "user_input": state["user_input"],
        "scenario": state["scenario"],
        "company_name": org.company_name,
        "company_url": org.company_url,
        "company_description": org.company_description,
        "target_info": org.other_information,
        "today": str(date.today()),
        "brand": {
            "colors": brand.colors[:5] if brand else [],
            "fonts": brand.fonts[:3] if brand else [],
            "logo_urls": _pick_best_logos(brand) if brand else [],
            "use_built_in_knowledge": brand is None,
        },
        "include_training_banner": state.get("include_training_banner", True),
        "debrief_message": state.get("landing_debrief_message"),
    }

    prompt = f"Build the phishing training landing page using this data:\n\n{json.dumps(context, indent=2)}"

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        return {"errors": [f"Landing page generation failed: {e}"]}

    html = str(response.text).strip()
    # Strip accidental markdown fences if the model disobeys
    if html.startswith("```"):
        html = html.split("```", 2)[-1] if html.count("```") >= 2 else html.lstrip("`\n")
        if html.lower().startswith("html\n"):
            html = html[5:]

    if not html:
        return {"errors": ["Landing page generation returned empty output."]}

    return {
        "landing_page_html": html,
        "landing_page_filename": landing_page_filename(org.company_name),
    }
