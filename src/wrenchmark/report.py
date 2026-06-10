"""Render scores as a terminal table, a markdown leaderboard, and a chart."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .scoring import TIERS, ModelScore

TIER_NAMES = {1: "T1 single call", 2: "T2 judgment", 3: "T3 chains"}


def terminal_table(scores: list[ModelScore]) -> None:
    console = Console()
    table = Table(title="wrenchmark leaderboard")
    table.add_column("model", style="bold")
    table.add_column("overall", justify="right")
    for t in TIERS:
        table.add_column(TIER_NAMES[t], justify="right")
    table.add_column("malformed", justify="right")
    table.add_column("avg latency", justify="right")
    for s in scores:
        row = [s.model, f"{100 * s.success_rate:.0f}% ± {100 * s.stderr:.0f}"]
        for t in TIERS:
            p, err = s.tier_rate(t)
            row.append(f"{100 * p:.0f}%")
        row += [f"{100 * s.malformed_rate:.1f}%", f"{s.mean_latency:.1f}s"]
        table.add_row(*row)
    console.print(table)


def markdown_leaderboard(scores: list[ModelScore]) -> str:
    lines = [
        "| Model | Overall | T1 single call | T2 judgment | T3 chains | Malformed calls | Avg latency |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in scores:
        cells = [s.model, f"{100 * s.success_rate:.0f}% ± {100 * s.stderr:.0f}"]
        for t in TIERS:
            p, err = s.tier_rate(t)
            cells.append(f"{100 * p:.0f}% ± {100 * err:.0f}")
        cells += [f"{100 * s.malformed_rate:.1f}%", f"{s.mean_latency:.1f}s"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def chart(scores: list[ModelScore], out_path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    models = [s.model for s in scores]
    x = np.arange(len(TIERS))
    width = 0.8 / max(len(models), 1)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    for i, s in enumerate(scores):
        rates, errs = zip(*(s.tier_rate(t) for t in TIERS))
        ax.bar(x + i * width, [100 * r for r in rates], width,
               yerr=[100 * e for e in errs], capsize=3, label=s.model)
    ax.set_xticks(x + width * (len(models) - 1) / 2)
    ax.set_xticklabels([TIER_NAMES[t] for t in TIERS])
    ax.set_ylabel("success rate (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Tool-calling success by task tier (±1σ binomial)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def write_report(scores: list[ModelScore], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_path = chart(scores, out_dir / "success_by_tier.png")
    report = out_dir / "REPORT.md"
    report.write_text(
        "# wrenchmark results\n\n"
        + markdown_leaderboard(scores)
        + f"\n\n![success by tier]({chart_path.name})\n"
    )
    return report
