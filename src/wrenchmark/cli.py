"""CLI: wrenchmark list | selftest | run | report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from .providers import NullProvider, make_provider
from .runner import reference_provider, run_sweep, run_task
from .scoring import load_records, score
from .tasks import load_tasks

console = Console()
DEFAULT_TASKS = Path(__file__).resolve().parents[2] / "tasks"


def cmd_list(args) -> int:
    for task in load_tasks(args.tasks):
        console.print(f"[bold]{task.id}[/] (tier {task.tier}, tools: {', '.join(task.tools)})")
        console.print(f"  [dim]{task.prompt}[/]")
    return 0


def cmd_selftest(args) -> int:
    """Calibrate the harness: every reference solution must pass its own checks,
    and the null baseline (no tools, unhelpful answer) must fail almost all."""
    tasks = load_tasks(args.tasks)
    failures = []
    for task in tasks:
        record = run_task(reference_provider(task), task)
        mark = "[green]✓[/]" if record["success"] else "[red]✗[/]"
        console.print(f"{mark} reference  {task.id}")
        if not record["success"]:
            failures.append((task.id, record["failed_checks"]))

    null_passes = sum(run_task(NullProvider(), t)["success"] for t in tasks)
    console.print(f"\nreference solutions: {len(tasks) - len(failures)}/{len(tasks)} pass")
    console.print(f"null baseline passes: {null_passes}/{len(tasks)} (lower is better)")

    if failures:
        console.print("\n[red]Self-test FAILED:[/]")
        for task_id, checks in failures:
            console.print(f"  {task_id}: {checks}")
        return 1
    if null_passes > len(tasks) * 0.15:
        console.print("[red]Self-test FAILED: null baseline passes too many tasks.[/]")
        return 1
    console.print("[green]Harness calibrated.[/]")
    return 0


def cmd_run(args) -> int:
    tasks = load_tasks(args.tasks)
    for model in args.models.split(","):
        model = model.strip()
        console.rule(f"[bold]{model}[/]")
        run_sweep(
            lambda m=model: make_provider(args.provider, m, args.base_url),
            tasks, reps=args.reps, out_path=args.out,
        )
    console.print(f"\nRecords appended to [bold]{args.out}[/] — run: wrenchmark report {args.out}")
    return 0


def cmd_report(args) -> int:
    from .report import terminal_table, write_report

    records = load_records(args.results)
    if not records:
        console.print("[red]No records found.[/]")
        return 1
    scores = score(records)
    terminal_table(scores)
    report = write_report(scores, args.out_dir)
    console.print(f"\nWrote [bold]{report}[/] and chart.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="wrenchmark",
                                     description="A verifiable tool-calling benchmark for local LLMs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List all tasks")
    p_list.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    p_list.set_defaults(fn=cmd_list)

    p_self = sub.add_parser("selftest", help="Validate harness with reference solutions + null baseline")
    p_self.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    p_self.set_defaults(fn=cmd_selftest)

    p_run = sub.add_parser("run", help="Benchmark one or more models")
    p_run.add_argument("--models", required=True, help="Comma-separated model names, e.g. hermes3,qwen2.5:7b")
    p_run.add_argument("--provider", default="ollama", choices=["ollama", "openai", "null"])
    p_run.add_argument("--base-url", default=None, help="Override endpoint URL")
    p_run.add_argument("--reps", type=int, default=3)
    p_run.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    p_run.add_argument("--out", type=Path, default=Path("results/results.jsonl"))
    p_run.set_defaults(fn=cmd_run)

    p_rep = sub.add_parser("report", help="Score results and write leaderboard + chart")
    p_rep.add_argument("results", type=Path)
    p_rep.add_argument("--out-dir", type=Path, default=Path("results"))
    p_rep.set_defaults(fn=cmd_report)

    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
