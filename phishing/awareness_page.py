"""Deterministic (non-LLM) renderer for the post-submission security-awareness page.

In GoPhish mode the landing-page form submits to GoPhish, which captures the data and
then redirects the target. This page is what you host at GoPhish's *Redirect URL* so the
target sees a clear security-awareness message after they submit. It is a plain, branded
static page — no form, no scripts, nothing captured here.
"""

import html as _html
from datetime import date

# Default message shown to a target after they submit (used for the inline reveal on a
# standalone landing page, and as the body of this awareness page in GoPhish mode).
DEFAULT_DEBRIEF = (
    "This was an authorized security awareness test run by your organization. "
    "No credentials were captured, stored, or used, and no further action is taken "
    "with anything you entered. Please treat this as a reminder to check links and "
    "sender addresses carefully before signing in."
)

# A few static, emoji-free reminders shown beneath the message.
_TIPS = [
    "Check the sender's address and hover over links before clicking.",
    "Look for urgency, threats, or unexpected requests — common phishing tells.",
    "When in doubt, navigate to the site directly instead of using an emailed link.",
    "Report suspicious messages to your security team.",
]

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Security Awareness Training</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f3f4f6; color: #111827;
         font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  .bar {{ height: 6px; background: {color}; }}
  .wrap {{ max-width: 620px; margin: 48px auto; padding: 0 20px; }}
  .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
          box-shadow: 0 1px 3px rgba(0,0,0,.08); overflow: hidden; }}
  .head {{ padding: 24px 28px; border-bottom: 1px solid #f0f0f0;
          display: flex; align-items: center; gap: 12px; }}
  .head .brand {{ font-weight: 700; color: {color}; font-size: 18px; }}
  .body {{ padding: 28px; }}
  .shield {{ width: 28px; height: 28px; flex: none; }}
  h1 {{ font-size: 22px; margin: 0 0 16px; color: {color}; }}
  p {{ line-height: 1.6; margin: 0 0 14px; }}
  ul {{ line-height: 1.7; padding-left: 20px; margin: 8px 0 0; }}
  .note {{ margin-top: 24px; padding: 14px 16px; background: #f9fafb;
          border-left: 4px solid {color}; border-radius: 4px; font-size: 14px; color: #374151; }}
  .foot {{ padding: 16px 28px; border-top: 1px solid #f0f0f0; font-size: 12px; color: #6b7280; }}
</style>
</head>
<body>
<div class="bar"></div>
<div class="wrap">
  <div class="card">
    <div class="head">
      <svg class="shield" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 2l8 3v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5l8-3z"></path>
        <path d="M9 12l2 2 4-4"></path>
      </svg>
      {brand}
    </div>
    <div class="body">
      <h1>Security Awareness Training</h1>
      {message}
      <p>If you entered any information, in a real attack it would now be in the hands of an attacker.</p>
      <div class="note">
        <strong>How to spot the next one:</strong>
        <ul>{tips}</ul>
      </div>
    </div>
    <div class="foot">Authorized security awareness simulation &middot; {today}</div>
  </div>
</div>
</body>
</html>
"""


def render_awareness_page(
    company_name: str,
    message: str | None = None,
    primary_color: str | None = None,
    logo_url: str | None = None,
) -> str:
    """Render a standalone, branded security-awareness page (no form, no scripts)."""
    color = _sanitize_color(primary_color) or "#1f2937"
    text = message or DEFAULT_DEBRIEF

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    message_html = "\n      ".join(f"<p>{_html.escape(p)}</p>" for p in paragraphs) or (
        f"<p>{_html.escape(DEFAULT_DEBRIEF)}</p>"
    )

    if logo_url:
        brand_html = (
            f'<img src="{_html.escape(logo_url, quote=True)}" alt="" '
            f'style="max-height:36px;max-width:160px;">'
        )
    else:
        brand_html = f'<span class="brand">{_html.escape(company_name or "Security Team")}</span>'

    tips_html = "".join(f"<li>{_html.escape(t)}</li>" for t in _TIPS)

    return _TEMPLATE.format(
        color=color,
        brand=brand_html,
        message=message_html,
        tips=tips_html,
        today=date.today().strftime("%B %d, %Y"),
    )


def _sanitize_color(value: str | None) -> str | None:
    """Only allow a simple #hex color into the inline CSS."""
    if not value:
        return None
    v = value.strip()
    if v.startswith("#") and len(v) in (4, 7) and all(c in "0123456789abcdefABCDEF" for c in v[1:]):
        return v
    return None
