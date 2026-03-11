# Phishing Awareness Training Generator

Generates realistic phishing email templates for authorized cybersecurity awareness training. Built with Python, LangGraph, and Claude (Anthropic).

> **For authorized use only.** This tool is intended for security teams running sanctioned employee phishing simulations and awareness programs.

---

## How It Works

```
Wizard → Scenario → Org Data → Brand Assets → Logo Analysis → HTML Email → Browser Preview
```

1. You fill in a short wizard describing the target and scenario
2. Claude generates a plausible phishing scenario from your inputs
3. Company data is extracted (name, domain, description)
4. Brand assets are fetched via BrandFetch API *(optional)*
5. Logos are analyzed for email suitability via Claude Vision *(if brand data available)*
6. Claude generates a polished HTML phishing email
7. The result opens in your browser and is saved to your current directory

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
cd phishing

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

# Optional — override the email generation model (default: claude-sonnet-4-6)
# PHISHING_EMAIL_MODEL=claude-opus-4-6
```

---

## Usage

Run the tool from any directory:

```bash
phishing
```

The wizard will walk you through 8 steps:

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
```

The generated HTML file is saved to the directory where you ran `phishing` and opens automatically in your browser.

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
| Email generation | `claude-sonnet-4-6` | Override via `PHISHING_EMAIL_MODEL` |

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
- **File**: Saved as `CompanyName.html` in the directory where `phishing` was run
