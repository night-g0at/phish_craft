# Pipeline Architecture

This document explains how the phishing email generator works end-to-end — what happens at each stage, which models are involved, and how data flows through the pipeline.

---

## Overview

The tool is built on **LangGraph**, a framework for orchestrating multi-step AI pipelines as a directed graph. Each stage is a node that receives the current state, does its work, and returns updates to that state. Nodes run sequentially, each building on the output of the previous one.

```
┌─────────────┐
│    Wizard   │  User fills in target, domain, persona, sender,
│   (CLI)     │  pretext, systems, urgency, training banner
└──────┬──────┘
       │ user_input + override_domain + include_training_banner
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
│ 5. Build        │  claude-sonnet-4-6 (or override model)
│    Email        │  Generates the full HTML phishing email
└──────┬──────────┘
       │ html_email
       ▼
┌─────────────────┐
│ 6. Save         │  Writes HTML to disk, opens in browser
│    Output       │
└─────────────────┘
```

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

### Stage 5 — Build Email
**File:** `phishing/nodes/email_builder.py`
**Model:** `claude-sonnet-4-6` (or `PHISHING_EMAIL_MODEL` env override, temperature 0.4, max 4096 tokens)

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
  "include_training_banner": true
}
```

**Branding logic:**
- If `use_built_in_knowledge` is `false` — uses exact colors, fonts, and logos from BrandFetch
- If `use_built_in_knowledge` is `true` — uses Claude's training knowledge of the company's visual identity (colors, logo style, typography)

**Training banner:**
If `include_training_banner` is `true`, a clearly styled watermark section is appended to the bottom of the email, listing the social engineering tactics used.

---

### Stage 6 — Save Output
**File:** `phishing/nodes/output.py`

Writes the generated HTML to disk and opens it in the default browser.

- **Filename:** `{CompanyName}.html` (special characters stripped)
- **Location:** The directory where `phishing` was run (`Path.cwd()`)

---

## State Object

All stages share a single typed state object (`PhishingState`) that is passed through the graph. Each node reads what it needs and returns only the fields it updates.

```
PhishingState
├── user_input              str       — enriched prompt from wizard
├── override_domain         str|None  — user-supplied domain (skips LLM extraction)
├── include_training_banner bool      — whether to append training watermark
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
├── html_email              str|None  — generated by stage 5
├── output_path             str|None  — set by stage 6
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

---

## File Structure

```
phishing/
├── main.py              — CLI entry point, wizard, progress display
├── graph.py             — LangGraph graph definition and node wiring
├── state.py             — Shared state schema (PhishingState, OrgData, BrandData)
└── nodes/
    ├── scenario.py      — Stage 1: scenario generation
    ├── org_data.py      — Stage 2: structured company data extraction
    ├── brand_fetch.py   — Stage 3: BrandFetch API integration
    ├── logo_analysis.py — Stage 4: Claude Vision logo evaluation
    ├── email_builder.py — Stage 5: HTML email generation
    └── output.py        — Stage 6: file save and browser open
```
