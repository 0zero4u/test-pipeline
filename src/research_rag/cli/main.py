"""CLI entry point for Research RAG."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from research_rag import __version__
from research_rag.config import load_settings
from research_rag.embeddings import EmbeddingService
from research_rag.ingestion.pipeline import IngestionPipeline
from research_rag.logging import setup_logging
from research_rag.models import Chunk, DocumentMetadata, ChunkFlags
from research_rag.retrieval import Retriever
from research_rag.storage.chroma import ChromaStore
from research_rag.synthesis import AnswerGenerator
from research_rag.cli.repl import repl

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="research-rag")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def main(ctx: click.Context, config: str | None, debug: bool) -> None:
    """Research RAG - Citation-grounded research assistance."""
    ctx.ensure_object(dict)

    config_path = Path(config) if config else None
    settings = load_settings(config_path)

    if debug:
        settings.debug = True
        settings.log_level = "DEBUG"

    setup_logging(level=settings.log_level)
    ctx.obj["settings"] = settings


@main.command(help="Ingest PDFs from a directory.")
@click.argument("input_dir", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="./data", help="Output directory")
@click.pass_context
def ingest(ctx: click.Context, input_dir: str, output: str) -> None:
    """Ingest PDFs from directory."""
    settings = ctx.obj["settings"]
    input_path = Path(input_dir)
    output_path = Path(output)

    console.print(f"[bold green]Ingesting PDFs from {input_dir}[/]")
    console.print(f"[bold]Config:[/] chunk_size={settings.ingestion.chunk_size_min}-{settings.ingestion.chunk_size_max}, overlap={settings.ingestion.chunk_overlap}")

    pipeline = IngestionPipeline(
        config=settings.ingestion,
        output_dir=output_path,
    )

    results = pipeline.process_directory(input_path)

    success = sum(1 for r in results if r.success)
    total_chunks = sum(r.chunks_created for r in results)

    table = Table(title="Ingestion Results")
    table.add_column("Document", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Chunks", justify="right")
    table.add_column("Confidence", justify="right")

    for r in results:
        status = "[green]OK[/]" if r.success else "[red]FAIL[/]"
        table.add_row(
            r.title[:50],
            status,
            str(r.chunks_created),
            f"{r.metadata_confidence:.2f}",
        )

    console.print(table)
    console.print(f"\n[bold]Summary:[/] {success}/{len(results)} PDFs processed, {total_chunks} chunks created")


@main.command(help="Semantic search across ingested documents.")
@click.argument("query_str")
@click.option("--top-k", "-k", type=int, default=5, help="Number of results")
@click.option("--where", "-w", type=str, default=None, help="Metadata filter as JSON (e.g. '{\"year\": 2024}')")
@click.pass_context
def query(ctx: click.Context, query_str: str, top_k: int, where: str | None) -> None:
    """Semantic search across ingested documents."""
    settings = ctx.obj["settings"]
    console.print(f"[bold blue]Query:[/] {query_str}")

    where_filter = None
    if where:
        try:
            where_filter = json.loads(where)
        except json.JSONDecodeError:
            console.print("[red]Invalid --where JSON. Use format: '{\"key\": \"value\"}'[/]")
            sys.exit(1)

    embed_service = EmbeddingService(
        api_key=settings.openrouter_api_key,
    )
    store = ChromaStore(
        persist_directory=settings.storage.chroma_path,
        embedding_service=embed_service,
    )
    retriever = Retriever(
        store=store,
        top_k=top_k,
    )

    results = retriever.search(query=query_str, where=where_filter)

    if not results:
        console.print("[yellow]No results found. Try a different query.[/]")
        return

    console.print(f"\n[bold]Top {len(results)} results:[/]\n")

    for i, r in enumerate(results, 1):
        title_display = r.title[:60] if r.title else r.document_id[:60]
        console.print(f"[cyan][{i}][/] [bold]{title_display}[/]")
        console.print(f"    [dim]Section:[/] {r.section_title or '(unknown)'}")
        console.print(
            f"    [dim]Pages:[/] {r.page_start}-{r.page_end}  "
            f"[dim]Relevance:[/] {r.score:.3f}"
        )
        if r.text:
            excerpt = r.text[:250].replace("\n", " ")
            if len(r.text) > 250:
                excerpt += "..."
            console.print(f"    [dim]Excerpt:[/] {excerpt}")
        console.print("")


@main.command(help="Ask a research question and get a citation-grounded answer.")
@click.argument("question")
@click.option("--top-k", "-k", type=int, default=5, help="Number of evidence chunks")
@click.option("--reasoning", is_flag=True, help="Show reasoning trace")
@click.pass_context
def ask(ctx: click.Context, question: str, top_k: int, reasoning: bool) -> None:
    """Ask a research question and get a citation-grounded answer."""
    settings = ctx.obj["settings"]
    console.print(f"[bold blue]Question:[/] {question}")
    console.print("[dim]Searching knowledge base...[/]")

    embed_service = EmbeddingService(
        api_key=settings.openrouter_api_key,
    )
    store = ChromaStore(
        persist_directory=settings.storage.chroma_path,
        embedding_service=embed_service,
    )
    retriever = Retriever(
        store=store,
        top_k=top_k,
    )

    if not settings.openrouter_api_key:
        console.print("[yellow]OPENROUTER_API_KEY not set. Showing retrieval results only.[/]")
        results = retriever.search(query=question, top_k=top_k)
        if results:
            for i, r in enumerate(results, 1):
                console.print(f"  [cyan][{i}][/] {r.title[:60]} (score: {r.score:.3f})")
        else:
            console.print("[yellow]No relevant evidence found.[/]")
        return

    generator = AnswerGenerator(
        retriever=retriever,
        top_k=top_k,
    )

    with console.status("[bold green]Generating answer...[/]"):
        response = generator.answer(
            query=question,
            include_reasoning=reasoning,
        )

    console.print(f"\n[bold]Answer:[/] (confidence: {response['confidence']:.2f})\n")
    console.print(response["answer"])
    console.print("")

    if response["citations"]:
        console.print("[bold]Sources:[/]")
        table = Table(show_header=False)
        table.add_column("#", style="cyan")
        table.add_column("Source", style="green")
        table.add_column("Page", style="dim")
        table.add_column("Relevance", style="dim")

        for i, c in enumerate(response["citations"], 1):
            title_short = c["title"][:40] if c["title"] else c["document_id"][:40]
            table.add_row(
                str(i),
                title_short,
                str(c["page"]),
                f"{c['relevance_score']:.3f}",
            )
        console.print(table)
    else:
        console.print("[yellow]No citations extracted.[/]")

    if reasoning and "reasoning_trace" in response:
        console.print(f"\n[dim]Evidence count: {response['reasoning_trace']['evidence_count']}[/]")


@main.command(help="Ingest PDFs and store chunks in Chroma.")
@click.argument("input_dir", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="./data", help="Ingestion output directory")
@click.pass_context
def ingest_and_store(ctx: click.Context, input_dir: str, output: str) -> None:
    """Ingest PDFs and store chunks in Chroma."""
    settings = ctx.obj["settings"]
    input_path = Path(input_dir)
    output_path = Path(output)

    console.print(f"[bold green]Ingesting PDFs from {input_dir}[/]")

    # Step 1: Run ingestion pipeline
    pipeline = IngestionPipeline(
        config=settings.ingestion,
        output_dir=output_path,
    )
    results = pipeline.process_directory(input_path)

    success = sum(1 for r in results if r.success)
    total_chunks = sum(r.chunks_created for r in results)

    table = Table(title="Ingestion Results")
    table.add_column("Document", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Chunks", justify="right")
    table.add_column("Confidence", justify="right")

    for r in results:
        status = "[green]OK[/]" if r.success else "[red]FAIL[/]"
        table.add_row(
            r.title[:50],
            status,
            str(r.chunks_created),
            f"{r.metadata_confidence:.2f}",
        )

    console.print(table)

    if success == 0:
        console.print("[red]No PDFs were successfully ingested. Aborting.[/]")
        return

    # Step 2: Load chunks from output and store in Chroma
    chunks_dir = output_path / "chunks"
    metadata_dir = output_path / "metadata"

    if not chunks_dir.exists():
        console.print(f"[red]No chunks directory found at {chunks_dir}[/]")
        return

    embed_service = EmbeddingService(
        api_key=settings.openrouter_api_key,
    )
    store = ChromaStore(
        persist_directory=settings.storage.chroma_path,
        embedding_service=embed_service,
    )

    all_chunks: list[Chunk] = []
    for chunk_file in sorted(chunks_dir.glob("*.json")):
        doc_id = chunk_file.stem
        meta_file = metadata_dir / f"{doc_id}.json"

        doc_meta = None
        if meta_file.exists():
            with open(meta_file) as f:
                doc_meta = DocumentMetadata(**json.load(f))

        with open(chunk_file) as f:
            chunk_data_list = json.load(f)

        for cd in chunk_data_list:
            chunk = Chunk(
                chunk_id=cd["chunk_id"],
                document_id=cd.get("document_id", doc_id),
                section_title=cd.get("section_title", ""),
                page_start=cd.get("page_start", 1),
                page_end=cd.get("page_end", 1),
                text=cd.get("text", ""),
                token_count=cd.get("token_count", 0),
                metadata=doc_meta,
                flags=ChunkFlags(
                    quoted_text=cd.get("flags", {}).get("quoted_text", False),
                    has_citations=cd.get("flags", {}).get("has_citations", False),
                ),
            )
            all_chunks.append(chunk)

    stored = store.upsert_chunks(all_chunks)
    console.print(f"\n[bold green]Stored {stored} chunks in Chroma ({store.count()} total)[/]")


@main.command(help="Show system status.")
@click.option("--reset", is_flag=True, help="Reset the vector store")
@click.pass_context
def status(ctx: click.Context, reset: bool) -> None:
    """Show system status."""
    settings = ctx.obj["settings"]

    table = Table(title="Research RAG Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row("Config", "OK", f"Log level: {settings.log_level}")
    table.add_row("Storage", "OK", f"Chroma: {settings.storage.chroma_path}")

    api_status = "[green]Set[/]" if settings.openrouter_api_key else "[yellow]Not set[/]"
    table.add_row("API Key (OpenRouter)", api_status,
                  "Set OPENROUTER_API_KEY env var" if not settings.openrouter_api_key else "Configured")

    try:
        embed_service = EmbeddingService(
            api_key=settings.openrouter_api_key,
        )
        store = ChromaStore(
            persist_directory=settings.storage.chroma_path,
            embedding_service=embed_service,
        )
        chunk_count = store.count()
        doc_count = len(store.list_documents())
        table.add_row("Chroma Collection", "[green]OK[/]",
                      f"{chunk_count} chunks from {doc_count} documents")

        if reset and chunk_count > 0:
            store.reset()
            console.print("[yellow]Vector store reset.[/]")
    except Exception as e:
        table.add_row("Chroma Collection", "[red]Error[/]", str(e)[:50])

    console.print(table)


@main.command(help="Start the interactive Research RAG REPL.")
@click.pass_context
def repl_cmd(ctx: click.Context) -> None:
    """Start the interactive Research RAG REPL."""
    settings = ctx.obj["settings"]
    repl(settings)


if __name__ == "__main__":
    main()
