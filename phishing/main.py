import asyncio
import os
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

load_dotenv()

console = Console()
app = typer.Typer(add_completion=False)


def _check_env():
    missing = [k for k in ("ANTHROPIC_API_KEY",) if not os.environ.get(k)]
    if missing:
        console.print(f"[red]Missing environment variables: {', '.join(missing)}[/red]")
        console.print("Copy .env.example to .env and fill in your keys.")
        raise typer.Exit(1)


@app.command()
def run(
    prompt: str = typer.Argument(None, help="Describe the target company and persona"),
):
    """Generate a phishing awareness training email."""
    _check_env()

    if not prompt:
        prompt = typer.prompt("Describe the target (company, persona, context)")

    console.print(Panel(f"[bold]{prompt}[/bold]", title="Target", border_style="cyan"))
    asyncio.run(_run_graph(prompt))


async def _run_graph(user_input: str):
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
            {"user_input": user_input, "errors": []},
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
    errors = state.get("errors", [])
    output_path = state.get("output_path", "unknown")

    lines = []
    if org:
        lines.append(f"[cyan]Company:[/cyan]  {org.company_name} ({org.company_url})")
    lines.append(f"[green]Saved:[/green]    {output_path}")
    lines.append(f"[yellow]Warnings:[/yellow] {len(errors)}")

    console.print(Panel("\n".join(lines), title="[green]Done[/green]", border_style="green"))

    for err in errors:
        console.print(f"  [yellow]![/yellow] {err}")


if __name__ == "__main__":
    app()
