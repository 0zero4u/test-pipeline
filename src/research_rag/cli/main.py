"""CLI entry point for Research RAG."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from research_rag import __version__
from research_rag.config import load_settings
from research_rag.logging import setup_logging

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="research-rag")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def main(ctx: click.Context, config: str | None, debug: bool) -> None:
    """Research RAG - Citation-grounded research assistance."""
    ctx.ensure_object(dict)

    # Load settings
    config_path = Path(config) if config else None
    settings = load_settings(config_path)

    if debug:
        settings.debug = True
        settings.log_level = "DEBUG"

    # Setup logging
    setup_logging(level=settings.log_level)

    # Store in context
    ctx.obj["settings"] = settings


@main.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="./data", help="Output directory")
@click.pass_context
def ingest(ctx: click.Context, input_dir: str, output: str) -> None:
    """Ingest PDFs from directory."""
    settings = ctx.obj["settings"]
    console.print(f"[bold green]Ingesting PDFs from {input_dir}[/]")

    # TODO: Implement ingestion pipeline
    console.print("[yellow]Ingestion pipeline not yet implemented[/]")


@main.command()
@click.argument("query")
@click.option("--top-k", "-k", type=int, default=5, help="Number of results")
@click.pass_context
def query(ctx: click.Context, query: str, top_k: int) -> None:
    """Query the research database."""
    settings = ctx.obj["settings"]
    console.print(f"[bold blue]Query: {query}[/]")

    # TODO: Implement query pipeline
    console.print("[yellow]Query pipeline not yet implemented[/]")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status."""
    settings = ctx.obj["settings"]

    table = Table(title="Research RAG Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row("Config", "OK", f"Log level: {settings.log_level}")
    table.add_row("Storage", "OK", f"Chroma: {settings.storage.chroma_path}")
    table.add_row("API Keys", "Check", "Set OPENROUTER_API_KEY and EMBEDDING_API_KEY")

    console.print(table)


if __name__ == "__main__":
    main()
