# Phishing Awareness Training Generator

Generates realistic phishing email templates for authorized cybersecurity awareness training. Built with Python, LangGraph, and Claude (Anthropic).

> **For authorized use only.** This tool is intended for security teams running sanctioned employee phishing simulations and awareness programs.

---

## How It Works

```
User Input → Scenario → Org Data → Brand Assets → Logo Analysis → HTML Email → Browser Preview
```

1. You describe a target company and persona
2. Claude generates a plausible phishing scenario
3. Structured company data is extracted (name, domain, description)
4. Brand assets are fetched via BrandFetch API *(optional)*
5. Logos are analyzed for email suitability via Claude Vision *(if brand data available)*
6. Claude generates a polished HTML phishing email
7. The result opens in your browser and is saved to your temp folder

---

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- *(Optional)* A [BrandFetch API key](https://brandfetch.com/developers) for fetched brand assets

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
copy .env.example .env       # Windows
cp .env.example .env         # macOS / Linux
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

```bash
# Pass the target description directly
phishing "Target description here"

# Or run interactively — it will prompt you
phishing
```

The generated HTML file is saved to your system temp folder and opens automatically in your browser.

---

## Example Prompts

### IT / Helpdesk

```
IT helpdesk alert targeting a software engineer at GitHub. Their account requires MFA re-enrollment within 24 hours or access will be suspended.
```

```
Password expiry notice for an employee at Cloudflare. They need to reset their credentials through the internal portal.
```

### HR / Finance

```
HR benefits enrollment reminder for a marketing manager at Salesforce. Open enrollment closes this Friday.
```

```
Payroll direct deposit update required for an accountant at Deloitte. Action needed before next pay cycle.
```

### Executive / Business

```
DocuSign contract signature request for a VP of Sales at Oracle. A partner agreement is awaiting their signature.
```

```
Invoice approval request for a finance director at JPMorgan Chase. An overdue vendor payment needs authorization.
```

### Package / Delivery

```
FedEx delivery failure notice targeting a remote employee at Amazon. They need to confirm their address to reschedule delivery.
```

### Energy & Electric Services

```
Smart meter upgrade notification targeting a residential customer service rep at Duke Energy. They need to schedule a technician visit through the internal portal before the grid modernization deadline.
```

```
Outage management system alert for a field engineer at Pacific Gas & Electric. Their SCADA dashboard credentials need to be reverified following a cybersecurity audit.
```

```
Billing system migration notice for an accounts manager at Constellation Energy. They must log in to validate customer account transfers before the system cutover window closes.
```

### Industry-Specific

```
Security alert for a nurse at Kaiser Permanente — their Epic Systems login was accessed from an unrecognized device.
```

```
Microsoft Teams meeting invite from "IT Security" for an analyst at Goldman Sachs regarding a compliance review.
```

---

## Models Used

| Stage | Model | Notes |
|---|---|---|
| Scenario generation | `claude-sonnet-4-6` | Creative, contextual |
| Org data extraction | `claude-haiku-4-5-20251001` | Fast structured output |
| Logo analysis | `claude-sonnet-4-6` | Vision — skipped if no brand data |
| Email generation | `claude-sonnet-4-6` | Override via `PHISHING_EMAIL_MODEL` |

Set `PHISHING_EMAIL_MODEL=claude-opus-4-6` for maximum output quality on complex targets.

---

## BrandFetch: On vs Off

| | With BrandFetch | Without BrandFetch |
|---|---|---|
| Logo source | Fetched from CDN, vision-analyzed | Claude's training knowledge |
| Colors/fonts | Exact brand values | Approximated by Claude |
| Cost | BrandFetch API credits | None (Anthropic only) |
| Best for | Known brands with public assets | Quick runs, lesser-known orgs |

---

## Output

- **Browser**: Opens automatically at `file:///tmp/CompanyName.html`
- **File**: Saved to your system temp directory (`%TEMP%` on Windows, `/tmp` on macOS/Linux)
