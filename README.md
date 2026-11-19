# Phishing Awareness Training Generator

Generates realistic phishing email templates for authorized cybersecurity awareness training. Built with Python, LangGraph, and Claude (Anthropic).

> **For authorized use only.** This tool is intended for security teams running sanctioned employee phishing simulations and awareness programs.

---

## How It Works

```
Wizard → Scenario → Org Data → Brand Assets → Logo Analysis → Landing Page* → HTML Email → Browser Preview
```
<sub>*Landing page stage runs only if you opt in (wizard step 9).</sub>

1. You fill in a short wizard describing the target and scenario
2. Claude generates a plausible phishing scenario from your inputs
3. Company data is extracted (name, domain, description)
4. Brand assets are fetched via BrandFetch API *(optional)*
5. Logos are analyzed for email suitability via Claude Vision *(if brand data available)*
6. *(Optional)* Claude generates a matching standalone **landing page** — the page the email's CTA links to
7. Claude generates a polished HTML phishing email (its CTA links to the landing page, if one was generated)
8. The result(s) open in your browser and are saved to your current directory

### The landing page

When enabled, the tool also produces a brand-matched landing page (e.g. a spoofed sign-in portal) that the email's call-to-action links to, saved as a second file. The page is **deliberately inert and safe for training**: the form submits nowhere, makes no network requests, and stores nothing — on submit it reveals a "Security Awareness Training" message explaining that a real attacker would now have the victim's credentials. Entered values are never captured, echoed, or logged.

---

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- *(Optional)* A [BrandFetch API key](https://brandfetch.com/developers) for accurate brand colors and logos

---

## Installation

```bash
# 1. Clone the repo
git clone <repo-url>
cd phish_craft

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install the package
pip install -e .

# 4. Configure credentials
cp .env.example .env   # macOS / Linux
copy .env.example .env # Windows
```

Edit `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=sk-ant-...

# Optional — omit to let Claude use built-in brand knowledge
BRANDFETCH_API_KEY=...

# Optional — override the email generation model (code default: claude-sonnet-4-6)
PHISHING_EMAIL_MODEL=claude-opus-4-6

# Optional — override the landing-page model (defaults to PHISHING_EMAIL_MODEL)
# PHISHING_LANDING_MODEL=claude-opus-4-6
```

> **Model note:** Newer Claude models (the 5-family, and Opus 4.7/4.8) removed the
> `temperature` sampling parameter and run with thinking on by default. The tool
> handles this automatically — `temperature` is passed only to models that still
> accept it (4.6 and older), and response text is read in a way that works whether
> thinking is on or off. Any valid Claude model id works in the overrides above.

---

## Usage

Run the tool from any directory:

```bash
phishcraft
```

The wizard will walk you through 9 steps:

```
─────────────── Phishing Email Generator ───────────────
Press Enter to accept defaults or skip optional fields.

1. Target company:          The organization being impersonated (e.g. Microsoft, Acme Corp)
2. Company domain:          Optional — supply the exact domain for better branding (e.g. acmecorp.com)
3. Target persona:          Who receives the email (e.g. HR employees, finance team)
4. Sender identity:         Who the email appears to be from (e.g. IT Helpdesk, HR Department)
5. Pretext:                 The reason for the email (e.g. MFA re-enrollment, password expiry)
6. Internal systems:        Optional — systems to name-drop for realism (e.g. Workday, ServiceNow)
7. Urgency level:           1 = Low / 2 = Medium / 3 = High
8. Include training banner: Appends a watermark explaining this is a simulation
9. Landing page:            Optional — also generate a matching standalone landing page (default: No)
```

The generated HTML file(s) are saved to the directory where you ran `phishcraft` and open automatically in your browser. If you enable the landing page (step 9), a second `CompanyName_landing.html` file is created alongside the email.

---

## Tips for Better Results

- **Supply the domain** (step 2) whenever possible. The LLM will guess if you skip it, but the exact domain ensures BrandFetch returns correct colors and logos.
- **Name internal systems** (step 6) — referencing tools like Workday, SAP, or ServiceNow adds significant realism.
- **Match urgency to pretext** — high urgency works well for account suspension, IT alerts, and MFA prompts; low urgency suits HR benefit notices or survey requests.
- **Set `PHISHING_EMAIL_MODEL=claude-opus-4-6`** in `.env` for higher-quality output on complex or niche targets.

---

## Scenario Examples

### IT / Helpdesk

| Field | Value |
|---|---|
| Company | GitHub |
| Domain | github.com |
| Persona | Software engineers |
| Sender | IT Helpdesk |
| Pretext | MFA re-enrollment required, account suspended in 24 hours |
| Systems | GitHub Enterprise, Okta, VPN |
| Urgency | High |

### HR / Finance

| Field | Value |
|---|---|
| Company | Salesforce |
| Domain | salesforce.com |
| Persona | Marketing managers |
| Sender | HR Department |
| Pretext | Open enrollment for benefits closes this Friday |
| Systems | Workday, employee portal |
| Urgency | Medium |

### Executive / Business

| Field | Value |
|---|---|
| Company | JPMorgan Chase |
| Domain | jpmorganchase.com |
| Persona | Finance directors |
| Sender | DocuSign via Legal |
| Pretext | Contract awaiting signature — partner agreement |
| Systems | DocuSign, SharePoint |
| Urgency | Medium |

### Package / Delivery

| Field | Value |
|---|---|
| Company | Amazon |
| Domain | amazon.com |
| Persona | Remote employees |
| Sender | FedEx |
| Pretext | Delivery failed — confirm address to reschedule |
| Systems | — |
| Urgency | Low |

---

## Models Used

| Stage | Model | Notes |
|---|---|---|
| Scenario generation | `claude-sonnet-4-6` | Creative, contextual |
| Org data extraction | `claude-haiku-4-5-20251001` | Fast structured output |
| Logo analysis | `claude-sonnet-4-6` | Vision — skipped if no brand data |
| Landing page | `PHISHING_EMAIL_MODEL` | Only if opted in; override via `PHISHING_LANDING_MODEL` |
| Email generation | `claude-sonnet-4-6` | Override via `PHISHING_EMAIL_MODEL` |

The shipped `.env` sets `PHISHING_EMAIL_MODEL=claude-opus-4-6`, so by default the email and landing page are generated with Opus 4.6.

---

## BrandFetch: On vs Off

| | With BrandFetch | Without BrandFetch |
|---|---|---|
| Logo source | Fetched from CDN, vision-analyzed | Claude's training knowledge |
| Colors/fonts | Exact brand values | Approximated by Claude |
| Cost | BrandFetch API credits | None (Anthropic only) |
| Best for | Known brands with public assets | Quick runs, lesser-known orgs |

If BrandFetch returns sparse data for a domain (no logos, fewer than 3 colors), the tool automatically falls back to Claude's built-in brand knowledge.

---

## Output

- **Browser**: Opens automatically from your current directory
- **Email file**: Saved as `CompanyName.html` in the directory where `phishcraft` was run
- **Landing page file** *(if enabled)*: Saved as `CompanyName_landing.html` in the same directory; the email's CTA links to it
