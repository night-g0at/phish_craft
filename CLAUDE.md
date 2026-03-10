# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **n8n workflow project** for generating phishing email templates for cybersecurity awareness training. The entire project is a single n8n workflow definition: `Phishing_Email.json`.

## Workflow Architecture

The workflow is a multi-stage LLM pipeline triggered via n8n's chat interface:

1. **Scenario Generation** — User input describing a target persona is processed by GPT-4O (`4o Scenario Builder`) to generate a phishing scenario.
2. **Brand Data Gathering** — `GatherOrgData` LLM chain extracts the target company's URL/description; `Get Brand Info` fetches brand assets (logos, colors, fonts) from the BrandFetch API (`https://api.brandfetch.io/v2/brands/{domain}`).
3. **Logo Analysis** — A LangChain agent (`AI Agent`) invokes an external `ImageAnalysis` sub-workflow tool to evaluate brand logo effectiveness.
4. **Email Generation** — `PhishBuilder` chain (powered by o3-mini) generates a realistic HTML phishing email using the gathered brand data.
5. **Output** — A `Code` node base64-encodes the HTML; an HTML preview node renders it; `Read/Write Files from Disk1` saves the result as an `.html` file.

## Required Credentials

To run this workflow in n8n, configure these credentials:
- **OpenAI API key** — used by multiple nodes (gpt-4o, gpt-4o-mini, o3-mini)
- **BrandFetch API key** — used by the `Get Brand Info` HTTP node

## Managing the Workflow

This project has no build/test/lint tooling. All changes are made directly to `Phishing_Email.json` or via the n8n web UI:

- **Import**: In n8n, go to Workflows → Import → select `Phishing_Email.json`
- **Export**: After editing in the UI, export and overwrite `Phishing_Email.json`
- **Run**: Activate the workflow and send a chat message via the n8n chat trigger

## JSON Structure Notes

The workflow JSON uses n8n's standard schema: top-level `nodes` array and `connections` object. Each node has a `type` (e.g., `@n8n/n8n-nodes-langchain.lmChatOpenAi`), `parameters`, and a unique `id`. The `connections` object maps node output ports to downstream node inputs by name.

When editing the JSON directly, preserve node `id` values — they are referenced in `connections`.
