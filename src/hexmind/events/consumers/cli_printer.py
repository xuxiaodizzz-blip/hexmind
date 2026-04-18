"""CLIPrinter: Rich-powered terminal output consumer."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from hexmind.events.types import (
    BlueHatDecisionPayload,
    BudgetWarningPayload,
    ConclusionPayload,
    ContextCompressedPayload,
    DegradationChangedPayload,
    DiscussionCancelledPayload,
    DiscussionStartedPayload,
    ErrorPayload,
    Event,
    EventType,
    ForkCreatedPayload,
    PanelistOutputPayload,
    RoundCompletedPayload,
    RoundStartedPayload,
    SubConclusionPayload,
    ValidationResultPayload,
)

# Hat -> color mapping for Rich
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

    # Lifecycle

    def _on_discussion_started(self, event: Event) -> None:
        payload = event.payload_as(DiscussionStartedPayload)
        if payload is None:
            return

        self.console.print()
        self.console.print(
            Panel(
                f"[bold]{payload.question}[/bold]\n参与者: {', '.join(payload.persona_ids)}",
                title="[bold blue]HexMind Discussion[/bold blue]",
                border_style="blue",
            )
        )

    def _on_conclusion(self, event: Event) -> None:
        payload = event.payload_as(ConclusionPayload)
        if payload is None:
            return

        self.console.print()
        self.console.print(
            Panel(
                f"[bold]{payload.summary}[/bold]\n置信度: {payload.confidence}",
                title="[bold green]结论[/bold green]",
                border_style="green",
            )
        )

    def _on_discussion_cancelled(self, event: Event) -> None:
        payload = event.payload_as(DiscussionCancelledPayload)
        if payload is None:
            return

        self.console.print(f"\n[bold red]讨论已取消: {payload.reason}[/bold red]")

    # Round-level

    def _on_blue_hat_decision(self, event: Event) -> None:
        payload = event.payload_as(BlueHatDecisionPayload)
        if payload is None:
            return

        hat = payload.hat.value if payload.hat else "unknown"
        style = _HAT_STYLES.get(hat, "bold")
        self.console.print()
        self.console.rule(f"[{style}]Round {payload.round} - {hat.title()} Hat[/{style}]")
        if self.verbose and payload.reasoning:
            self.console.print(f"  [dim]Blue Hat: {payload.reasoning}[/dim]")

    def _on_round_started(self, event: Event) -> None:
        payload = event.payload_as(RoundStartedPayload)
        if payload is None or not self.verbose:
            return
        self.console.print(f"  [dim]Round {payload.round} 开始...[/dim]")

    def _on_round_completed(self, event: Event) -> None:
        payload = event.payload_as(RoundCompletedPayload)
        if payload is None or not self.verbose:
            return
        self.console.print(f"  [dim]Round {payload.round} 完成[/dim]")

    def _on_panelist_output(self, event: Event) -> None:
        payload = event.payload_as(PanelistOutputPayload)
        if payload is None:
            return

        hat = payload.hat.value if payload.hat else "unknown"
        style = _HAT_STYLES.get(hat, "bold")
        header = Text(f"  {payload.persona_id or 'unknown'}", style=style)
        self.console.print(header)
        self.console.print(f"    {payload.content}")

    # Validation

    def _on_validation_result(self, event: Event) -> None:
        payload = event.payload_as(ValidationResultPayload)
        if payload is None or not self.verbose or payload.passed:
            return

        self.console.print(
            f"  [yellow]⚠ {payload.persona_id} 验证失败: {payload.violations}[/yellow]"
        )

    # Tree

    def _on_fork_created(self, event: Event) -> None:
        payload = event.payload_as(ForkCreatedPayload)
        if payload is None:
            return
        self.console.print(f"\n  [bold cyan]↳ FORK: {payload.question}[/bold cyan]")

    def _on_sub_conclusion(self, event: Event) -> None:
        payload = event.payload_as(SubConclusionPayload)
        if payload is None:
            return
        self.console.print(f"  [cyan]子结论: {payload.summary}[/cyan]")

    # Budget / compression

    def _on_budget_warning(self, event: Event) -> None:
        payload = event.payload_as(BudgetWarningPayload)
        if payload is None:
            return
        self.console.print(
            f"  [yellow]⚠ 预算已用 {payload.used_pct:.0%} - {payload.level}[/yellow]"
        )

    def _on_degradation_changed(self, event: Event) -> None:
        payload = event.payload_as(DegradationChangedPayload)
        if payload is None:
            return
        self.console.print(f"  [yellow]降级: {payload.new_level}[/yellow]")

    def _on_context_compressed(self, event: Event) -> None:
        payload = event.payload_as(ContextCompressedPayload)
        if payload is None or not self.verbose:
            return
        self.console.print(f"  [dim]上下文已压缩 (ratio={payload.ratio:.2f})[/dim]")

    # Error

    def _on_error(self, event: Event) -> None:
        payload = event.payload_as(ErrorPayload)
        if payload is None:
            return
        self.console.print(f"  [bold red]✖ 错误: {payload.message or '未知错误'}[/bold red]")
