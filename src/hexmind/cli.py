"""HexMind CLI: Six Hats Multi-Expert Decision Engine."""

from __future__ import annotations

import asyncio
import sys

import click
from dotenv import load_dotenv

load_dotenv()  # Load .env before any LLM/config imports

from hexmind.config import load_config
from hexmind.archive.reader import ArchiveReader
from hexmind.archive.search import ArchiveSearch
from hexmind.engine.orchestrator import Orchestrator
from hexmind.events.bus import EventBus
from hexmind.events.consumers.archive_writer import ArchiveWriter
from hexmind.events.consumers.cli_printer import CLIPrinter
from hexmind.llm.litellm_wrapper import LiteLLMWrapper
from hexmind.model_catalog import load_model_catalog
from hexmind.models.config import DiscussionConfig
from hexmind.personas.loader import PersonaLoader
from hexmind.prompt_library.loader import PromptLibraryLoader


@click.group()
@click.version_option(package_name="hexmind")
def cli():
    """HexMind — Six Hats Multi-Expert Decision Engine"""


@cli.command()
@click.argument("question")
@click.option("--persona", "-p", multiple=True, help="Persona ID (repeatable)")
@click.option("--model", "-m", default=None, help="LLM model name (defaults to env config)")
@click.option("--budget", "-b", default=50000, type=int, help="Token budget")
@click.option(
    "--discussion-locale",
    "--locale",
    "-l",
    default="zh",
    type=click.Choice(["zh", "en"]),
)
@click.option("--archive/--no-archive", default=True, help="Enable/disable archiving")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def discuss(question, persona, model, budget, discussion_locale, archive, verbose):
    """Start a Six Hats discussion."""
    asyncio.run(
        _discuss(
            question,
            persona,
            model,
            budget,
            discussion_locale,
            archive,
            verbose,
        )
    )


async def _discuss(
    question: str,
    persona_ids: tuple[str, ...],
    model: str | None,
    budget: int,
    discussion_locale: str,
    archive_flag: bool,
    verbose: bool,
) -> None:
    config_defaults = load_config()
    catalog = load_model_catalog()
    selected_id = model or catalog.default_model_id
    try:
        selected_model = catalog.resolve(selected_id)
    except KeyError as exc:
        raise click.ClickException(f"Unknown model alias: {selected_id}") from exc
    fallback_model = catalog.fallback_for(selected_model.id)
    config = DiscussionConfig(
        execution_token_cap=budget,
        resolved_model_slug=selected_model.slug,
        resolved_fallback_model_slug=fallback_model.slug,
        selected_model_id=selected_model.id,
        fallback_model_id=fallback_model.id,
        discussion_locale=discussion_locale,
        archive_dir=config_defaults.archive_dir,
    )

    loader = PersonaLoader()
    if persona_ids:
        personas = [loader.load(pid) for pid in persona_ids]
    else:
        # Zero-config: auto-select 3 diverse personas
        all_personas = loader.load_all()
        personas = _auto_select_personas(all_personas, count=3)

    llm = LiteLLMWrapper(model=selected_model.slug)

    bus = EventBus()
    printer = CLIPrinter(verbose=verbose)
    bus.subscribe(printer)

    if archive_flag:
        writer = ArchiveWriter(config.archive_dir)
        bus.subscribe(writer)

    orch = Orchestrator(llm, personas, config, bus)
    await orch.run(question)


def _auto_select_personas(
    personas: list, count: int = 3
) -> list:
    """Pick personas ensuring domain diversity."""
    by_domain: dict[str, list] = {}
    for p in personas:
        by_domain.setdefault(p.domain, []).append(p)

    selected: list = []
    for domain in sorted(by_domain):
        if len(selected) >= count:
            break
        selected.append(by_domain[domain][0])

    remaining = [p for p in personas if p not in selected]
    for p in remaining:
        if len(selected) >= count:
            break
        selected.append(p)

    return selected


@cli.command("personas")
def list_personas():
    """List all available personas."""
    loader = PersonaLoader()
    personas = loader.load_all()
    if not personas:
        click.echo("No personas found.")
        return
    for p in sorted(personas, key=lambda x: x.id):
        click.echo(f"  {p.id:30s} {p.name} ({p.domain})")


@cli.command("persona-info")
@click.argument("persona_id")
def persona_info(persona_id: str):
    """Show persona details."""
    loader = PersonaLoader()
    try:
        p = loader.load(persona_id)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"Name: {p.name}")
    click.echo(f"Domain: {p.domain}")
    click.echo(f"Description: {p.description}")


@cli.command("prompts")
@click.option("--position", help="Filter by position label")
@click.option("--hat", type=click.Choice(["white", "red", "black", "yellow", "green"]))
@click.option("--status", help="Filter by status")
def list_prompts(position: str | None, hat: str | None, status: str | None):
    """List all prompt assets in the normalized prompt library."""
    loader = PromptLibraryLoader()
    prompts = loader.load_all()
    if position:
        prompts = [prompt for prompt in prompts if prompt.position == position]
    if hat:
        prompts = [prompt for prompt in prompts if hat in {item.value for item in prompt.applicable_hats}]
    if status:
        prompts = [prompt for prompt in prompts if prompt.status == status]
    if not prompts:
        click.echo("No prompt assets found.")
        return
    for prompt in prompts:
        hats = ",".join(h.value for h in prompt.applicable_hats) or "-"
        click.echo(
            f"  {prompt.id:35s} {prompt.position} [{prompt.source}/{prompt.status}] hats={hats}"
        )


@cli.command("prompt-info")
@click.argument("prompt_id")
def prompt_info(prompt_id: str):
    """Show prompt asset details."""
    loader = PromptLibraryLoader()
    try:
        prompt = loader.load(prompt_id)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Name: {prompt.name}")
    click.echo(f"Position: {prompt.position}")
    click.echo(f"Domain: {prompt.domain}")
    click.echo(f"Kind: {prompt.kind}")
    click.echo(f"Hat Context: {prompt.hat_context}")
    if prompt.hat is not None:
        click.echo(f"Hat: {prompt.hat.value}")
    if prompt.applicable_hats:
        click.echo(f"Applicable Hats: {', '.join(hat.value for hat in prompt.applicable_hats)}")
    click.echo(f"Status: {prompt.status}")
    click.echo(f"Source: {prompt.source}")
    if prompt.description:
        click.echo(f"Description: {prompt.description}")


@cli.command()
@click.argument("archive_id")
@click.option("--format", "-f", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(archive_id: str, fmt: str):
    """Show an archived discussion."""
    reader = ArchiveReader()
    entry = reader.get_entry(archive_id)
    if entry is None:
        click.echo(f"Archive not found: {archive_id}", err=True)
        sys.exit(1)

    if fmt == "json":
        summary = entry.summary
        if summary:
            click.echo(summary.model_dump_json(indent=2, ensure_ascii=False))
        else:
            click.echo("{}")
    else:
        click.echo(entry.discussion_md)


@cli.command()
@click.option("--query", "-q", required=True, help="Search keyword")
@click.option("--max-results", "-n", default=10, type=int)
def search(query: str, max_results: int):
    """Search discussion archives."""
    searcher = ArchiveSearch()
    result = searcher.search(query, max_results=max_results)
    if result.count == 0:
        click.echo("No results found.")
        return
    click.echo(f"Found {result.count} result(s):\n")
    for hit in result.hits:
        click.echo(f"  [{hit.entry.dir_name}] ({hit.field})")
        click.echo(f"    {hit.snippet}")
        click.echo()


@cli.command()
@click.argument("archive_id")
@click.option("--format", "-f", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export(archive_id: str, fmt: str, output: str | None):
    """Export an archived discussion."""
    reader = ArchiveReader()
    entry = reader.get_entry(archive_id)
    if entry is None:
        click.echo(f"Archive not found: {archive_id}", err=True)
        sys.exit(1)

    if fmt == "json":
        summary = entry.summary
        content = summary.model_dump_json(indent=2, ensure_ascii=False) if summary else "{}"
    else:
        content = entry.discussion_md

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"Exported to {output}")
    else:
        click.echo(content)
