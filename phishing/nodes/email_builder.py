import os
import json
from datetime import date
from phishing.llm import make_chat
from phishing.state import PhishingState, LogoFormat

_SYSTEM = """You are assisting a cybersecurity team building phishing awareness training materials.
Your task is to generate a highly realistic phishing email in raw HTML — no markdown, no code fences.

Requirements:
- Personalize using the target's name or job title if available (prefer name)
- If brand colors/fonts/logos are provided, use them exactly
- If use_built_in_knowledge is true, use your training knowledge of the company's real visual identity: their primary brand colors, logo style, typography, and email design patterns — make it look like a real email from that company. Apply the brand color palette consistently across ALL elements (header, buttons, banners, accents) — do NOT substitute generic red for urgency if red is not part of the company's actual brand colors
- Include a logo (use a provided URL, or render a text-based logo block in the company's brand colors if no URL is available)
- Use today's date for realism
- Do NOT use emoji or emoji-style pictographs anywhere — not next to bullet points or list items, nor in headings, labels, or buttons. Emoji bullets read as obviously AI-generated and look unprofessional. Use plain text with standard typographic bullets (or no bullet glyph at all). If iconography genuinely helps, use a tasteful inline SVG or simple CSS shape in the brand style (e.g. a clean leaf motif) — never an emoji character.
- The phishing pretext must closely follow the user_input and scenario — preserve the specific angle, urgency, and framing described
- Always include a prominent, clearly styled CTA button (e.g. "Verify Now", "Re-enroll Now", "Complete Review") — it must be a full-width or centred button block in the company's primary brand color. If landing_page_url is provided in the data, use that value EXACTLY as the button's href and as the plain-text fallback URL (it is the matching training landing page). Otherwise use a believable but obviously fake href URL that matches the scenario (e.g. a spoofed internal portal domain). Also include a plain-text fallback URL below the button
- Match the layout, tone, and UX patterns a real attacker would use for this scenario
- If include_training_banner is true, append a clearly styled training watermark section at the bottom of the email explaining it is a simulation and listing the social engineering tactics used. If false, omit it entirely.
- Output ONLY the raw HTML document, starting with <!DOCTYPE html>

This is strictly for authorized employee security awareness training."""


def _pick_best_logos(brand_data) -> list[str]:
    usable_urls = []
    for logo in brand_data.logos:
        for fmt in logo.formats:
            if fmt.usable and fmt.format.lower() in {"png", "jpg", "jpeg", "webp"}:
                usable_urls.append(fmt.src)
    # Fall back to any format if nothing passed vision analysis
    if not usable_urls:
        for logo in brand_data.logos:
            for fmt in logo.formats:
                if fmt.src and fmt.format.lower() in {"png", "jpg", "jpeg", "webp", "svg"}:
                    usable_urls.append(fmt.src)
    return usable_urls[:3]  # top 3 to avoid prompt bloat


async def build_email(state: PhishingState) -> dict:
    model_name = os.environ.get("PHISHING_EMAIL_MODEL", "claude-sonnet-4-6")
    # A full branded HTML email can exceed 4096 tokens; give it headroom so the
    # output is never truncated (and isn't starved by thinking on 5-family models).
    llm = make_chat(model=model_name, temperature=0.4, max_tokens=8192)

    org = state["org_data"]
    brand = state["brand_data"]

    # Treat brand data as absent if it has no logos and fewer than 3 colors — it's too sparse to be useful
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
        # When a landing page was generated, point the CTA at its local file.
        "landing_page_url": state.get("landing_page_filename"),
    }

    prompt = f"Build the phishing training email using this data:\n\n{json.dumps(context, indent=2)}"

    response = await llm.ainvoke([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ])

    # On models with thinking enabled (e.g. the Claude 5 family), response
    # content is a list of blocks; `.text` concatenates just the text blocks.
    html = str(response.text).strip()
    # Strip accidental markdown fences if the model disobeys
    if html.startswith("```"):
        html = html.split("```", 2)[-1] if html.count("```") >= 2 else html.lstrip("`\n")
        if html.lower().startswith("html\n"):
            html = html[5:]

    return {"html_email": html}
