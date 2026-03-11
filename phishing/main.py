import asyncio
import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule

load_dotenv()

console = Console()
app = typer.Typer(add_completion=False)


def _check_env():
    missing = [k for k in ("ANTHROPIC_API_KEY",) if not os.environ.get(k)]
    if missing:
        console.print(f"[red]Missing environment variables: {', '.join(missing)}[/red]")
        console.print("Copy .env.example to .env and fill in your keys.")
        raise typer.Exit(1)


def _run_wizard() -> tuple[str, str | None, bool]:
    """Interactive wizard. Returns (enriched_prompt, override_domain, include_banner)."""
    console.print(Rule("[bold cyan]Phishing Email Generator[/bold cyan]"))
    console.print("[dim]Press Enter to accept defaults or skip optional fields.[/dim]\n")

    # 1. Target company
    company = Prompt.ask("[bold]1. Target company[/bold]")

    # 2. Domain
    domain_raw = Prompt.ask(
        "[bold]2. Company domain[/bold] [dim](optional — e.g. acmecorp.com)[/dim]",
        default="",
    )
    override_domain = domain_raw.strip() or None

    # 3. Target persona
    persona = Prompt.ask(
        "[bold]3. Target persona[/bold] [dim](e.g. HR employees, software engineers)[/dim]",
        default="",
    )

    # 4. Sender identity
    sender = Prompt.ask(
        "[bold]4. Sender identity[/bold] [dim](e.g. IT Helpdesk, HR Department, FedEx)[/dim]",
        default="IT Helpdesk",
    )

    # 5. Pretext
    pretext = Prompt.ask(
        "[bold]5. Pretext[/bold] [dim](e.g. MFA re-enrollment, password expiry, invoice approval)[/dim]",
        default="",
    )

    # 6. Internal systems
    systems = Prompt.ask(
        "[bold]6. Internal systems to reference[/bold] [dim](optional — comma-separated, e.g. Workday, SAP, ServiceNow)[/dim]",
        default="",
    )

    # 7. Urgency
    console.print("\n[bold]7. Urgency level[/bold]")
    console.print("   [dim]1[/dim]  Low    — informational, no hard deadline")
    console.print("   [dim]2[/dim]  Medium — action required, soft deadline")
    console.print("   [dim]3[/dim]  High   — immediate action, account/access at risk")
    urgency_choice = Prompt.ask("   Choose", choices=["1", "2", "3"], default="2")
    urgency = {"1": "low", "2": "medium", "3": "high"}[urgency_choice]

    # 8. Training banner
    include_banner = Confirm.ask("\n[bold]8. Include training banner?[/bold]", default=True)

    # Build enriched prompt
    parts = [f"Target company: {company}"]
    if persona:
        parts.append(f"Target persona: {persona}")
    parts.append(f"Sender: {sender}")
    if pretext:
        parts.append(f"Pretext / scenario: {pretext}")
    parts.append(f"Urgency: {urgency}")
    if systems:
        parts.append(f"Internal systems to mention: {systems}")

    enriched_prompt = "\n".join(parts)
    return enriched_prompt, override_domain, include_banner


@app.command()
def run():
    """Generate a phishing awareness training email."""
    _check_env()

    enriched_prompt, override_domain, include_banner = _run_wizard()

    console.print()
    console.print(Panel(enriched_prompt, title="[cyan]Simulation Brief[/cyan]", border_style="cyan"))
    asyncio.run(_run_graph(enriched_prompt, override_domain, include_banner))


async def _run_graph(user_input: str, override_domain: str | None, include_banner: bool):
    # Import here so load_dotenv() runs before LangChain imports (which read env at import time)
    from phishing.graph import build_graph

    graph = build_graph()

    node_labels = {
        "generate_scenario": "Generating scenario",
        "extract_org_data":  "Extracting org data",
        "fetch_brand_data":  "Fetching brand assets",
        "analyze_logos":     "Analyzing logos",
        "build_email":       "Building email",
        "save_output":       "Saving output",
    }

    merged_state: dict = {"errors": []}

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Starting...", total=None)

        async for event in graph.astream(
            {
                "user_input": user_input,
                "override_domain": override_domain,
                "include_training_banner": include_banner,
                "errors": [],
            },
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                label = node_labels.get(node_name, node_name)
                progress.update(task, description=f"[bold]{label}[/bold] ✓")
                # Merge node output into running state
                for k, v in (node_output or {}).items():
                    if k == "errors":
                        merged_state["errors"].extend(v)
                    else:
                        merged_state[k] = v

    _print_summary(merged_state)


def _print_summary(state: dict):
    org = state.get("org_data")
    brand = state.get("brand_data")
    errors = state.get("errors", [])
    output_path = state.get("output_path", "unknown")

    lines = []
    if org:
        lines.append(f"[cyan]Company:[/cyan]  {org.company_name} ({org.company_url})")
    if brand:
        colors = [c.get("hex", c) for c in brand.colors[:5]] if brand.colors else []
        lines.append(f"[cyan]Brand colors:[/cyan] {', '.join(str(c) for c in colors) or 'none'}")
        lines.append(f"[cyan]Logos:[/cyan]    {sum(len(l.formats) for l in brand.logos)} format(s)")
    else:
        lines.append("[yellow]Brand:[/yellow]    no data (using Claude knowledge)")
    lines.append(f"[green]Saved:[/green]    {output_path}")
    lines.append(f"[yellow]Warnings:[/yellow] {len(errors)}")

    console.print(Panel("\n".join(lines), title="[green]Done[/green]", border_style="green"))

    for err in errors:
        console.print(f"  [yellow]![/yellow] {err}")


if __name__ == "__main__":
    app()
