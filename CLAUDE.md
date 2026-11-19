# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PhishCraft** is a Python CLI tool that generates realistic phishing email templates — and optionally matching landing pages — for **authorized** cybersecurity awareness training. It is built on **LangGraph** (pipeline orchestration) and **Claude** via `langchain-anthropic`.

> For authorized security-awareness training only. Generated landing pages are deliberately inert — their forms capture nothing, make no network requests, and store nothing.

## Architecture

The tool is a LangGraph pipeline (`phishing/graph.py`) of sequential nodes, each reading and updating a shared `PhishingState` (`phishing/state.py`). An interactive wizard (`phishing/main.py`) collects inputs, then the graph runs:

1. **Generate Scenario** (`nodes/scenario.py`) — expands wizard input into a phishing scenario.
2. **Extract Org Data** (`nodes/org_data.py`) — structured extraction of company name/domain/description (Pydantic `OrgData`).
3. **Fetch Brand Data** (`nodes/brand_fetch.py`) — pulls logos/colors/fonts from the BrandFetch API (`https://api.brandfetch.io/v2/brands/{domain}`); optional.
4. **Analyze Logos** (`nodes/logo_analysis.py`) — Claude Vision rates each logo's email suitability.
5. **Build Landing Page** (`nodes/landing_page.py`) — *optional*; generates a brand-matched, inert standalone landing page. Runs before the email so the email CTA can link to it.
6. **Build Email** (`nodes/email_builder.py`) — generates the HTML phishing email.
7. **Save Output** (`nodes/output.py`) — writes the email (and landing page, if any) to `Path.cwd()` and opens them in the browser.

See `ARCHITECTURE.md` for the full stage-by-stage breakdown and the state schema.

## Key Conventions

- **Build LLM clients through `phishing/llm.py` → `make_chat()`, never `ChatAnthropic(...)` directly.** It handles two cross-model concerns centrally:
  - `temperature` is passed only to models that still accept it (Claude 4.6 and older); it is omitted for the 5-family and Opus 4.7/4.8, which removed sampling params (passing it 400s).
  - Callers express intent with `temperature=`; the factory decides whether to forward it.
- **Read model text with `str(response.text)`, not `response.content`.** Models with thinking enabled (the 5-family, on by default) return content as a list of blocks; `.text` concatenates the text blocks and also works for plain-string responses.
- **Filenames come from `phishing/naming.py`** (`safe_filename`, `landing_page_filename`) so the email's CTA target and the file written to disk always match.
- **Errors are non-fatal.** Nodes append to `state["errors"]` (an `operator.add`-reduced list) instead of raising, so the pipeline always completes; warnings are shown in the final summary.
- **Landing page safety is enforced in the prompt** (`nodes/landing_page.py`): no form submission, no `fetch`/`XMLHttpRequest`/`sendBeacon`, no storage; submit triggers a "Security Awareness Training" reveal whose text comes from `landing_debrief_message` (wizard-supplied; `DEFAULT_DEBRIEF` in `main.py`). Preserve these guarantees in the default (non-GoPhish) path when editing that node.
- **GoPhish mode (`gophish_mode`, wizard step 10)** appends a system-prompt addendum in both `email_builder.py` and `landing_page.py`. In this mode the email uses GoPhish template vars (`{{.URL}}`, `{{.FirstName}}`, `{{.Tracking}}`) and the landing page emits a real submitting `<form method="post" action="">` with named inputs (no inert JS, no inline debrief) so GoPhish captures submissions. Capture is done by the authorized GoPhish framework, not the page. Keep the inert behavior as the default when `gophish_mode` is false.

## Environment / Credentials

Configured via `.env` (loaded with `python-dotenv` in `main.py`):

- `ANTHROPIC_API_KEY` — **required**.
- `BRANDFETCH_API_KEY` — optional; without it, Claude uses built-in brand knowledge.
- `PHISHING_EMAIL_MODEL` — optional; overrides the email model (code default `claude-sonnet-4-6`; the shipped `.env` sets `claude-opus-4-6`).
- `PHISHING_LANDING_MODEL` — optional; overrides the landing-page model (defaults to `PHISHING_EMAIL_MODEL`).

Any valid Claude model id works in the overrides thanks to the `make_chat()` / `.text` handling above.

## Development

This project has no build/test/lint tooling. It is a standard editable Python package.

- **Install:** `python -m venv .venv && source .venv/bin/activate && pip install -e .`
- **Run:** `phishcraft` (entry point `phishing.main:app`, a Typer CLI). The tool writes output files to the directory it is run from.
- **Dependencies:** `langgraph`, `langchain-anthropic`, `httpx`, `pydantic`, `python-dotenv`, `rich`, `typer` (see `pyproject.toml`).
- Because it's an editable install, source edits take effect without reinstalling. Reinstall only when dependencies or entry points in `pyproject.toml` change.

## Adding a Pipeline Stage

1. Add a node function `async def my_node(state: PhishingState) -> dict` in `phishing/nodes/`.
2. Add any new fields to `PhishingState` in `phishing/state.py`.
3. Register the node and wire its edges in `phishing/graph.py`.
4. If the stage is optional, gate it on a state flag and return `{}` early when disabled (see `build_landing_page`).
5. Build any LLM client via `make_chat()` and read responses via `str(response.text)`.
