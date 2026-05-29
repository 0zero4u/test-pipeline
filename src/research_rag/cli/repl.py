"""Interactive REPL for Research RAG CLI."""

import atexit
import json
import os
import readline
import shlex
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from research_rag.config import Settings
from research_rag.embeddings import EmbeddingService
from research_rag.ingestion.pipeline import IngestionPipeline
from research_rag.models import Chunk, DocumentMetadata, ChunkFlags
from research_rag.retrieval import Retriever
from research_rag.storage.chroma import ChromaStore
from research_rag.synthesis import AnswerGenerator
from research_rag.utils import ResearchRAGError
from research_rag.writing import ChapterWriter, ChapterOutline, DissertationState

console = Console()

HISTORY_FILE = Path.home() / ".research_rag_history"
COMMANDS = ["ask", "ingest", "query", "write", "status", "help", "history", "exit", "quit"]


class ReplCompleter:
    """Tab completion for REPL commands."""

    def __init__(self, commands: list[str]) -> None:
        self.commands = commands
        self.matches: list[str] = []

    def complete(self, text: str, state: int) -> str | None:
        if state == 0:
            if text:
                self.matches = [c for c in self.commands if c.startswith(text)]
            else:
                self.matches = self.commands[:]
        try:
            return self.matches[state]
        except IndexError:
            return None


def _setup_readline() -> None:
    """Configure readline with history and tab completion."""
    readline.set_completer(ReplCompleter(COMMANDS).complete)
    readline.parse_and_bind("tab: complete")

    if HISTORY_FILE.exists():
        try:
            readline.read_history_file(str(HISTORY_FILE))
        except Exception:
            pass

    atexit.register(lambda: readline.write_history_file(str(HISTORY_FILE)))


def _parse_command(line: str) -> tuple[str, list[str], dict[str, Any]]:
    """Parse a REPL command line into command, args, and kwargs.

    Supports quoted arguments via shlex.
    """
    parts = shlex.split(line)
    if not parts:
        return "", [], {}

    command = parts[0].lower()
    args: list[str] = []
    kwargs: dict[str, Any] = {}

    i = 1
    while i < len(parts):
        part = parts[i]
        if part.startswith("-"):
            key = part.lstrip("-")
            if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                kwargs[key] = parts[i + 1]
                i += 2
            else:
                kwargs[key] = True
                i += 1
        else:
            args.append(part)
            i += 1

    return command, args, kwargs


def _print_welcome() -> None:
    """Display REPL welcome banner."""
    console.print(
        Panel.fit(
            "[bold cyan]Research RAG Interactive REPL[/]\n"
            "Type [bold]help[/] for available commands or [bold]exit[/] to quit.",
            title="Welcome",
            border_style="cyan",
        )
    )


def _print_help() -> None:
    """Display available commands."""
    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    table.add_column("Example", style="dim")

    table.add_row("ask", "Ask a research question", 'ask "What is X?" -k 5')
    table.add_row("ingest", "Ingest PDFs from a directory", "ingest ./pdfs/")
    table.add_row("query", "Semantic search", 'query "machine learning" -k 5')
    table.add_row("write", "Write a chapter from outline", 'write 3 "Chapter Title" --context "arg"')
    table.add_row("status", "Show system status", "status")
    table.add_row("history", "Show query history", "history")
    table.add_row("help / ?", "Show this help message", "help")
    table.add_row("exit / quit", "Exit the REPL", "exit")

    console.print(table)


def _cmd_ask(
    args: list[str],
    kwargs: dict[str, Any],
    generator: AnswerGenerator,
    history: list[dict[str, Any]],
) -> None:
    """Handle the 'ask' command."""
    if not args:
        console.print("[red]Usage: ask \"<question>\" [-k <top_k>] [--reasoning][/red]")
        return

    question = args[0]
    top_k = int(kwargs.get("k", kwargs.get("top-k", 5)))
    reasoning = bool(kwargs.get("reasoning", False))

    console.print(f"[bold blue]Question:[/] {question}")
    console.print("[dim]Searching knowledge base...[/]")

    with console.status("[bold green]Generating answer...[/]"):
        response = generator.answer(
            query=question,
            top_k=top_k,
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
        console.print(
            f"\n[dim]Evidence count: {response['reasoning_trace']['evidence_count']}[/]"
        )

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": response["answer"]})


def _cmd_ingest(
    args: list[str],
    kwargs: dict[str, Any],
    settings: Settings,
    store: ChromaStore,
) -> None:
    """Handle the 'ingest' command (pipeline + chroma store)."""
    if not args:
        console.print("[red]Usage: ingest <directory>[/red]")
        return

    input_dir = Path(args[0])
    if not input_dir.exists():
        console.print(f"[red]Directory not found: {input_dir}[/]")
        return

    output_path = Path(kwargs.get("output", "./data"))

    console.print(f"[bold green]Ingesting PDFs from {input_dir}[/]")
    console.print(
        f"[bold]Config:[/] chunk_size={settings.ingestion.chunk_size_min}-"
        f"{settings.ingestion.chunk_size_max}, overlap={settings.ingestion.chunk_overlap}"
    )

    pipeline = IngestionPipeline(
        config=settings.ingestion,
        output_dir=output_path,
    )
    results = pipeline.process_directory(input_dir)

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
    console.print(
        f"\n[bold]Summary:[/] {success}/{len(results)} PDFs processed, "
        f"{total_chunks} chunks created"
    )

    if success == 0:
        console.print("[red]No PDFs were successfully ingested.[/]")
        return

    # Store in Chroma
    chunks_dir = output_path / "chunks"
    metadata_dir = output_path / "metadata"

    if not chunks_dir.exists():
        console.print(f"[red]No chunks directory found at {chunks_dir}[/]")
        return

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
    console.print(
        f"\n[bold green]Stored {stored} chunks in Chroma ({store.count()} total)[/]"
    )


def _cmd_query(
    args: list[str],
    kwargs: dict[str, Any],
    retriever: Retriever,
) -> None:
    """Handle the 'query' command."""
    if not args:
        console.print("[red]Usage: query \"<search>\" [-k <top_k>][/red]")
        return

    query_str = args[0]
    top_k = int(kwargs.get("k", kwargs.get("top-k", 5)))

    console.print(f"[bold blue]Query:[/] {query_str}")

    where_filter = None
    if "where" in kwargs:
        try:
            where_filter = json.loads(kwargs["where"])
        except json.JSONDecodeError:
            console.print("[red]Invalid --where JSON. Use format: '{\"key\": \"value\"}'[/]")
            return

    results = retriever.search(query=query_str, top_k=top_k, where=where_filter)

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


def _cmd_status(store: ChromaStore, settings: Settings) -> None:
    """Handle the 'status' command."""
    table = Table(title="Research RAG Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row("Config", "OK", f"Log level: {settings.log_level}")
    table.add_row("Storage", "OK", f"Chroma: {settings.storage.chroma_path}")

    api_status = "[green]Set[/]" if settings.openrouter_api_key else "[yellow]Not set[/]"
    table.add_row(
        "API Key (OpenRouter)",
        api_status,
        "Set OPENROUTER_API_KEY env var" if not settings.openrouter_api_key else "Configured",
    )

    try:
        chunk_count = store.count()
        doc_count = len(store.list_documents())
        table.add_row(
            "Chroma Collection",
            "[green]OK[/]",
            f"{chunk_count} chunks from {doc_count} documents",
        )
    except Exception as e:
        table.add_row("Chroma Collection", "[red]Error[/]", str(e)[:50])

    console.print(table)


def _cmd_write(
    args: list[str],
    kwargs: dict[str, Any],
    writer: ChapterWriter,
    state: DissertationState,
) -> None:
    """Handle the 'write' command — generate a chapter from outline."""
    if not args:
        console.print(
            "[red]Usage: write <chapter_number> \"<title>\" [--sections <json>] [--context <text>][/red]"
        )
        console.print("[dim]Example: write 3 \"Partition and Violence\" --context \"Comparative study\"[/]")
        return

    try:
        chapter_num = int(args[0])
    except ValueError:
        console.print("[red]Chapter number must be an integer.[/]")
        return

    title = args[1] if len(args) > 1 else f"Chapter {chapter_num}"
    context = kwargs.get("context", "")

    sections_raw = kwargs.get("sections", None)
    if sections_raw:
        import json as _json
        try:
            sections_data = _json.loads(sections_raw)
        except _json.JSONDecodeError:
            console.print("[red]Invalid --sections JSON.[/]")
            return
    else:
        sections_data = [
            {"title": f"{chapter_num}.1 Introduction", "description": "Introduce the chapter topic."},
            {"title": f"{chapter_num}.2 Main Analysis", "description": "Core analysis with evidence."},
            {"title": f"{chapter_num}.3 Conclusion", "description": "Summarize and transition."},
        ]

    outline = ChapterOutline(chapter_num, title)
    for sec in sections_data:
        outline.add_section(sec["title"], sec["description"])

    console.print(f"[bold blue]Writing Chapter {chapter_num}: {title}[/]")
    console.print(f"[dim]{outline.section_count} sections, ~{outline.total_target_words} words target[/]")

    with console.status("[bold green]Generating chapter (this may take a minute)...[/]"):
        result = writer.write_chapter(outline, chapter_context=context)

    console.print(f"\n[bold]Chapter {chapter_num} complete![/] ({result['word_count']} words)\n")
    console.print(result["chapter_text"][:2000])
    if result["word_count"] > 2000:
        console.print("[dim]... (truncated, full text in output)[/]")

    if result["citations"]:
        console.print(f"\n[bold]Citations used:[/] {len(result['citations'])}")
        for cit in result["citations"][:10]:
            console.print(f"  [{cit['number']}] {cit.get('author', '?')} ({cit.get('year', 'n.d.')})")


def _cmd_history(history: list[dict[str, Any]]) -> None:
    """Handle the 'history' command."""
    if not history:
        console.print("[yellow]No conversation history yet.[/]")
        return

    table = Table(title="Conversation History")
    table.add_column("Turn", style="cyan", justify="right")
    table.add_column("Role", style="green")
    table.add_column("Content")

    turn = 0
    for i, entry in enumerate(history):
        if entry["role"] == "user":
            turn += 1
        role_emoji = "[blue]You[/]" if entry["role"] == "user" else "[green]Assistant[/]"
        content = entry["content"][:100]
        if len(entry["content"]) > 100:
            content += "..."
        table.add_row(str(turn) if entry["role"] == "user" else "", role_emoji, content)

    console.print(table)


def repl(settings: Settings) -> None:
    """Run the interactive Research RAG REPL.

    Initializes heavy components once and reuses them across turns.
    """
    _setup_readline()

    # Initialize session state once
    console.print("[dim]Initializing session state...[/]")
    embed_service = EmbeddingService(api_key=settings.openrouter_api_key)
    store = ChromaStore(
        persist_directory=Path(settings.storage.chroma_path),
        embedding_service=embed_service,
    )
    retriever = Retriever(
        store=store,
        top_k=settings.retrieval.top_k,
    )
    generator = AnswerGenerator(
        retriever=retriever,
        top_k=settings.retrieval.top_k,
    )
    state = DissertationState()
    writer = ChapterWriter(retriever=retriever, state=state)

    conversation_history: list[dict[str, Any]] = []

    _print_welcome()

    while True:
        try:
            line = input("research-rag> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            break

        if not line:
            continue

        command, args, kwargs = _parse_command(line)

        if command in ("exit", "quit"):
            console.print("[dim]Goodbye![/]")
            break
        elif command in ("help", "?"):
            _print_help()
        elif command == "ask":
            try:
                _cmd_ask(args, kwargs, generator, conversation_history)
            except ResearchRAGError as e:
                console.print(f"[red]Error:[/] {e}", style="red")
        elif command == "ingest":
            try:
                _cmd_ingest(args, kwargs, settings, store)
            except ResearchRAGError as e:
                console.print(f"[red]Error:[/] {e}", style="red")
        elif command == "query":
            try:
                _cmd_query(args, kwargs, retriever)
            except ResearchRAGError as e:
                console.print(f"[red]Error:[/] {e}", style="red")
        elif command == "write":
            try:
                _cmd_write(args, kwargs, writer, state)
            except ResearchRAGError as e:
                console.print(f"[red]Error:[/] {e}", style="red")
        elif command == "status":
            _cmd_status(store, settings)
        elif command == "history":
            _cmd_history(conversation_history)
        else:
            console.print(f"[red]Unknown command: {command}[/]")
            console.print("Type [bold]help[/] for available commands.")
