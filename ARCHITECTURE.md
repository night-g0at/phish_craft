# Pipeline Architecture

This document explains how the phishing email generator works end-to-end — what happens at each stage, which models are involved, and how data flows through the pipeline.

---

## Overview

The tool is built on **LangGraph**, a framework for orchestrating multi-step AI pipelines as a directed graph. Each stage is a node that receives the current state, does its work, and returns updates to that state. Nodes run sequentially, each building on the output of the previous one.

```
┌─────────────┐
│    Wizard   │  User fills in target, domain, persona, sender, pretext,
│   (CLI)     │  systems, urgency, training banner, landing-page toggle
└──────┬──────┘
       │ user_input + override_domain + include_training_banner + include_landing_page
       ▼
┌─────────────────┐
│ 1. Generate     │  claude-sonnet-4-6
│    Scenario     │  Expands user inputs into a coherent phishing scenario
└──────┬──────────┘
       │ scenario
       ▼
┌─────────────────┐
│ 2. Extract      │  claude-haiku-4-5
│    Org Data     │  Pulls company name, domain, description from scenario
└──────┬──────────┘
       │ org_data (company_name, company_url, description)
       ▼
┌─────────────────┐
│ 3. Fetch        │  BrandFetch API
│    Brand Data   │  Retrieves logos, colors, and fonts for the domain
└──────┬──────────┘
       │ brand_data (logos, colors, fonts)
       ▼
┌─────────────────┐
│ 4. Analyze      │  claude-sonnet-4-6 (Vision)
│    Logos        │  Evaluates each logo for email rendering suitability
└──────┬──────────┘
       │ brand_data (logos with usability flags)
       ▼
┌─────────────────┐
│ 5. Build        │  claude model (opt-in; skipped if not requested)
│    Landing Page │  Generates a brand-matched, inert landing page
└──────┬──────────┘
       │ landing_page_html + landing_page_filename
       ▼
┌─────────────────┐
│ 6. Build        │  claude-sonnet-4-6 (or override model)
│    Email        │  Generates the HTML email; CTA links to the landing page
└──────┬──────────┘
       │ html_email
       ▼
┌─────────────────┐
│ 7. Save         │  Writes email (+ landing page) to disk, opens in browser
│    Output       │
└─────────────────┘
```

The landing-page stage runs **before** the email so the email's CTA can point at the
landing page's local filename. When the user does not opt in, the stage is a no-op
(returns immediately) and the email falls back to a believable fake spoof URL.

---

## Stage-by-Stage Breakdown

### Stage 1 — Generate Scenario
**File:** `phishing/nodes/scenario.py`
**Model:** `claude-sonnet-4-6` (temperature 0.7)

Takes the enriched user input from the wizard and generates a concise 2–3 sentence phishing scenario. This frames the social engineering angle — who the target is, why they would act, and what the email will ask them to do.

**Input:**
```
Target company: FirstEnergy
Target persona: HR employees
Sender: IT Helpdesk
Pretext: MFA re-enrollment, account suspended in 24 hours
Urgency: high
Internal systems to mention: Workday, Active Directory
```

**Output (example):**
```
FirstEnergy HR employees are being targeted with a fraudulent IT Helpdesk
alert claiming their domain accounts require mandatory MFA re-enrollment.
The email threatens account suspension within 24 hours to create urgency,
directing victims to a credential-harvesting portal.
```

---

### Stage 2 — Extract Org Data
**File:** `phishing/nodes/org_data.py`
**Model:** `claude-haiku-4-5-20251001` (temperature 0, structured output)

Parses the scenario and original user input to extract structured company information. Output is validated against a Pydantic model.

If the user supplied a domain in the wizard (step 2), that domain is stored separately as `override_domain` and passed directly to BrandFetch in the next stage — it does not go through LLM extraction.

**Extracts:**
| Field | Example |
|---|---|
| `company_name` | FirstEnergy |
| `company_url` | firstenergycorp.com |
| `company_description` | A regulated electric utility serving the northeastern US |
| `other_information` | Targeting HR employees, high urgency |

---

### Stage 3 — Fetch Brand Data
**File:** `phishing/nodes/brand_fetch.py`
**API:** BrandFetch v2 (`https://api.brandfetch.io/v2/brands/{domain}`)

Queries the BrandFetch API using the domain — preferring the user-supplied `override_domain` over the LLM-extracted one. Returns brand assets that make the email visually convincing.

**Returns:**
- **Logos** — CDN URLs with format (PNG, SVG, etc.), dimensions, and background type
- **Colors** — hex values with type tags (primary, accent, etc.)
- **Fonts** — font family names used in the brand

**Fallback behaviour:**
- No `BRANDFETCH_API_KEY` → skipped entirely; email builder uses Claude's built-in knowledge
- API error → minimal brand object logged as a warning; email builder uses Claude's knowledge
- Sparse response (0 logos, fewer than 3 colors) → treated as no data; Claude uses built-in knowledge

---

### Stage 4 — Analyze Logos
**File:** `phishing/nodes/logo_analysis.py`
**Model:** `claude-sonnet-4-6` (Vision, max 5 concurrent requests)

For each raster-format logo (PNG, JPG, WEBP), sends the image to Claude Vision for evaluation. The model assesses:

1. Clarity at small sizes
2. Rendering quality on a white email background
3. Overall visual recognizability

Each logo format is tagged `usable: true/false`. The email builder uses only usable logos; if none pass, it falls back to any available format.

**Skipped entirely** if BrandFetch returned no logos.

---

### Stage 5 — Build Landing Page *(optional)*
**File:** `phishing/nodes/landing_page.py`
**Model:** `PHISHING_LANDING_MODEL` → `PHISHING_EMAIL_MODEL` → `claude-opus-4-6` (temperature 0.4 where supported, max 8192 tokens)

Runs **only** when the user opts in at wizard step 9 (`include_landing_page`); otherwise it returns immediately and changes nothing. When enabled, it builds a brand-matched standalone HTML landing page — typically a spoofed sign-in portal or document/review page matching the email's pretext — using the same brand context (colors, fonts, usable logos) as the email.

The generated page is **deliberately inert and safe for authorized training**. The system prompt hard-requires:

- The form submits nowhere — no posting `action`, no `fetch`/`XMLHttpRequest`/`sendBeacon`, no external requests, no `localStorage`/cookies.
- A small inline `<script>` intercepts submit, calls `preventDefault()`, and reveals a clearly styled **"Security Awareness Training"** message explaining the page was simulated and that a real attacker would now have the victim's credentials.
- Entered values are never echoed, stored, logged, or transmitted; no tracking pixels or data-carrying outbound links.

The persistent visible training banner follows the same `include_training_banner` toggle as the email, but the inert form and the post-submit training reveal are required regardless of that setting.

**Output:** `landing_page_html` plus `landing_page_filename` (`{CompanyName}_landing.html`), which the next stage uses as the email's CTA target. On failure it appends to `errors` and the pipeline continues (the email simply uses a fake spoof URL).

---

### Stage 6 — Build Email
**File:** `phishing/nodes/email_builder.py`
**Model:** `claude-sonnet-4-6` (or `PHISHING_EMAIL_MODEL` env override, temperature 0.4 where supported, max 8192 tokens)

The core generation step. Assembles all collected data into a JSON context block and instructs Claude to produce a complete, self-contained HTML email.

**Context passed to the model:**
```json
{
  "user_input": "...",
  "scenario": "...",
  "company_name": "FirstEnergy",
  "company_url": "firstenergycorp.com",
  "company_description": "...",
  "target_info": "...",
  "today": "2026-03-10",
  "brand": {
    "colors": [{"hex": "#004B87", "type": "brand"}, ...],
    "fonts": [{"name": "Helvetica Neue"}],
    "logo_urls": ["https://cdn.brandfetch.io/..."],
    "use_built_in_knowledge": false
  },
  "include_training_banner": true,
  "landing_page_url": "FirstEnergy_landing.html"
}
```

When `landing_page_url` is present (a landing page was generated), the model uses it exactly as the CTA button's `href` and plain-text fallback URL, so the email links to the local landing-page file. When it is `null`, the model falls back to a believable-but-fake spoof URL.

**Branding logic:**
- If `use_built_in_knowledge` is `false` — uses exact colors, fonts, and logos from BrandFetch
- If `use_built_in_knowledge` is `true` — uses Claude's training knowledge of the company's visual identity (colors, logo style, typography)

**Training banner:**
If `include_training_banner` is `true`, a clearly styled watermark section is appended to the bottom of the email, listing the social engineering tactics used.

---

### Stage 7 — Save Output
**File:** `phishing/nodes/output.py`

Writes the generated HTML to disk and opens it in the default browser. If a landing page was generated, it is saved alongside the email and also opened.

- **Email filename:** `{CompanyName}.html` (special characters stripped)
- **Landing page filename:** `{CompanyName}_landing.html` (only when generated)
- **Location:** The directory where `phishcraft` was run (`Path.cwd()`)

Filenames are produced by the shared helpers in `phishing/naming.py`, so the landing-page name referenced by the email CTA and the name written to disk always match.

---

## State Object

All stages share a single typed state object (`PhishingState`) that is passed through the graph. Each node reads what it needs and returns only the fields it updates.

```
PhishingState
├── user_input              str       — enriched prompt from wizard
├── override_domain         str|None  — user-supplied domain (skips LLM extraction)
├── include_training_banner bool      — whether to append training watermark
├── include_landing_page    bool      — whether to also generate a landing page
├── scenario                str|None  — generated by stage 1
├── org_data                OrgData   — populated by stage 2
│   ├── company_name
│   ├── company_url
│   ├── company_description
│   └── other_information
├── brand_data              BrandData|None — populated by stage 3, updated by stage 4
│   ├── logos[]
│   │   └── formats[]
│   │       ├── src, format, width, height
│   │       ├── analysis    ← added by stage 4
│   │       └── usable      ← added by stage 4
│   ├── colors[]
│   └── fonts[]
├── landing_page_html       str|None  — generated by stage 5 (None if skipped)
├── landing_page_filename   str|None  — relative filename the email CTA links to
├── html_email              str|None  — generated by stage 6
├── output_path             str|None  — email path, set by stage 7
├── landing_page_path       str|None  — landing page path, set by stage 7 (if generated)
└── errors                  list[str] — accumulated across all stages (non-fatal warnings)
```

---

## Error Handling

Errors are non-fatal by design. Each node appends to the `errors` list rather than raising exceptions, so the pipeline always completes. Warnings are shown in the summary panel after the run.

| Situation | Behaviour |
|---|---|
| BrandFetch API key missing | Skip brand fetch; use Claude knowledge |
| BrandFetch HTTP error | Log warning; continue with no brand data |
| BrandFetch parse failure | Log warning; use partial data if available |
| Logo analysis failure (per logo) | Mark as `usable: false`; fall back to next best logo |
| Sparse brand data (<3 colors, 0 logos) | Treat as no data; use Claude knowledge |
| Landing page generation failure | Log warning; continue — email uses a fake spoof URL |

---

## File Structure

```
phishing/
├── main.py              — CLI entry point, wizard, progress display
├── graph.py             — LangGraph graph definition and node wiring
├── state.py             — Shared state schema (PhishingState, OrgData, BrandData)
├── llm.py               — ChatAnthropic factory (model-aware temperature handling)
├── naming.py            — Shared output-filename helpers
└── nodes/
    ├── scenario.py      — Stage 1: scenario generation
    ├── org_data.py      — Stage 2: structured company data extraction
    ├── brand_fetch.py   — Stage 3: BrandFetch API integration
    ├── logo_analysis.py — Stage 4: Claude Vision logo evaluation
    ├── landing_page.py  — Stage 5: standalone landing page (optional)
    ├── email_builder.py — Stage 6: HTML email generation
    └── output.py        — Stage 7: file save and browser open
```

---

## Model Compatibility

All nodes build their Claude client through `phishing/llm.py` → `make_chat()` rather than
constructing `ChatAnthropic` directly. This centralizes two cross-model concerns:

- **Sampling parameters** — `temperature` was removed on newer Claude models (the entire
  5-family, plus Opus 4.7/4.8). `make_chat()` passes `temperature` only to models that still
  accept it (4.6 and older); for newer models it is silently omitted, so the same code runs
  on any configured model without a 400 error.
- **Response text** — models with thinking enabled (the 5-family, on by default) return
  content as a list of blocks rather than a plain string. Nodes read model text via
  `str(response.text)`, which concatenates the text blocks and works whether thinking is on
  or off.

This is why `PHISHING_EMAIL_MODEL` / `PHISHING_LANDING_MODEL` can be set to any current
Claude model id without code changes.
