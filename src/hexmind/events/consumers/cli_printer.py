"""CLIPrinter: Rich-powered terminal output consumer."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from hexmind.events.types import Event, EventType

# Hat → color mapping for Rich
_HAT_STYLES: dict[str, str] = {
    "white": "bold white",
    "red": "bold red",
    "black": "bold bright_black",
    "yellow": "bold yellow",
    "green": "bold green",
}


class CLIPrinter:
    """Listens to events and prints formatted output to the terminal."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self.console = Console()

    async def on_event(self, event: Event) -> None:
        handler = getattr(self, f"_on_{event.type.value}", None)
        if handler:
            handler(event)
        elif self.verbose:
            self.console.print(f"[dim]Event: {event.type.value}[/dim]")

    # ── Lifecycle ──────────────────────────────────────────────

    def _on_discussion_started(self, event: Event) -> None:
        question = event.data.get("question", "")
        personas = event.data.get("personas", [])
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]{question}[/bold]\n参与者: {', '.join(personas)}",
                title="[bold blue]HexMind Discussion[/bold blue]",
                border_style="blue",
            )
        )

    def _on_conclusion(self, event: Event) -> None:
        summary = event.data.get("summary", "")
        confidence = event.data.get("confidence", "")
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]{summary}[/bold]\n置信度: {confidence}",
                title="[bold green]结论[/bold green]",
                border_style="green",
            )
        )

    def _on_discussion_cancelled(self, event: Event) -> None:
        reason = event.data.get("reason", "用户取消")
        self.console.print(f"\n[bold red]讨论已取消: {reason}[/bold red]")

    # ── Round-level ────────────────────────────────────────────

    def _on_blue_hat_decision(self, event: Event) -> None:
        hat = event.data.get("hat") or "unknown"
        reasoning = event.data.get("reasoning", "")
        round_num = event.data.get("round", "?")
        style = _HAT_STYLES.get(hat, "bold")
        self.console.print()
        self.console.rule(f"[{style}]Round {round_num} — {hat.title()} Hat[/{style}]")
        if self.verbose and reasoning:
            self.console.print(f"  [dim]Blue Hat: {reasoning}[/dim]")

    def _on_round_started(self, event: Event) -> None:
        if self.verbose:
            self.console.print(f"  [dim]Round {event.data.get('round', '?')} 开始...[/dim]")

    def _on_round_completed(self, event: Event) -> None:
        if self.verbose:
            self.console.print(f"  [dim]Round {event.data.get('round', '?')} 完成[/dim]")

    def _on_panelist_output(self, event: Event) -> None:
        persona = event.data.get("persona_id", "unknown")
        hat = event.data.get("hat", "unknown")
        content = event.data.get("content", "")
        style = _HAT_STYLES.get(hat, "bold")

        header = Text(f"  {persona}", style=style)
        self.console.print(header)
        self.console.print(f"    {content}")

    # ── Validation ─────────────────────────────────────────────

    def _on_validation_result(self, event: Event) -> None:
        if self.verbose:
            passed = event.data.get("passed", True)
            persona = event.data.get("persona_id", "")
            if not passed:
                violations = event.data.get("violations", [])
                self.console.print(
                    f"  [yellow]⚠ {persona} 验证失败: {violations}[/yellow]"
                )

    # ── Tree ───────────────────────────────────────────────────

    def _on_fork_created(self, event: Event) -> None:
        question = event.data.get("question", "")
        self.console.print(f"\n  [bold cyan]↳ FORK: {question}[/bold cyan]")

    def _on_sub_conclusion(self, event: Event) -> None:
        summary = event.data.get("summary", "")
        self.console.print(f"  [cyan]子结论: {summary}[/cyan]")

    # ── Budget / compression ───────────────────────────────────

    def _on_budget_warning(self, event: Event) -> None:
        pct = event.data.get("used_pct", 0)
        level = event.data.get("level", "warning")
        self.console.print(f"  [yellow]⚠ 预算已用 {pct:.0%} — {level}[/yellow]")

    def _on_degradation_changed(self, event: Event) -> None:
        new_level = event.data.get("new_level", "")
        self.console.print(f"  [yellow]降级: {new_level}[/yellow]")

    def _on_context_compressed(self, event: Event) -> None:
        if self.verbose:
            ratio = event.data.get("ratio", 0)
            self.console.print(f"  [dim]上下文已压缩 (ratio={ratio:.2f})[/dim]")

    # ── Error ──────────────────────────────────────────────────

    def _on_error(self, event: Event) -> None:
        msg = event.data.get("message", "未知错误")
        self.console.print(f"  [bold red]✖ 错误: {msg}[/bold red]")
