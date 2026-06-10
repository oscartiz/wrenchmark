"""Sweep models × tasks × repetitions, writing one JSONL record per episode."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from rich.console import Console

from .agent import run_episode
from .mocktools import registry_for
from .providers import Provider, ScriptedProvider
from .tasks import Task, grade

console = Console()


def run_task(provider: Provider, task: Task) -> dict:
    schemas, dispatch = registry_for(task.tools)
    ep = run_episode(provider, task.prompt, schemas, dispatch, max_turns=task.max_turns)
    g = grade(task, ep)
    return {
        "model": provider.name,
        "task_id": task.id,
        "tier": task.tier,
        "success": g.success,
        "failed_checks": g.failed_checks,
        "n_tool_calls": len(ep.calls),
        "malformed_calls": ep.malformed_calls,
        "hit_max_turns": ep.hit_max_turns,
        "latency_s": round(ep.latency_s, 3),
        "final_answer": ep.final_answer,
        "calls": [asdict(c) for c in ep.calls],
        "error": ep.error,
    }


def run_sweep(provider_factory: Callable[[], Provider], tasks: list[Task],
              reps: int, out_path: Path, quiet: bool = False) -> list[dict]:
    """provider_factory is called once per episode so provider state never leaks."""
    records = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        for task in tasks:
            for rep in range(reps):
                provider = provider_factory()
                record = run_task(provider, task)
                record["rep"] = rep
                records.append(record)
                f.write(json.dumps(record) + "\n")
                if not quiet:
                    mark = "[green]✓[/]" if record["success"] else "[red]✗[/]"
                    console.print(
                        f"{mark} {record['model']}  {task.id}  rep {rep + 1}/{reps}"
                        f"  ({record['n_tool_calls']} calls, {record['latency_s']}s)"
                    )
    return records


def reference_provider(task: Task) -> ScriptedProvider:
    return ScriptedProvider(task.reference, name="reference")
