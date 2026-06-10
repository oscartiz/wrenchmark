"""Task definitions and programmatic checkers.

Every task is verifiable: its checks are evaluated against the episode
transcript (tool calls + final answer), never by another LLM. Every task
also ships a `reference` solution — the scripted action sequence a perfect
agent would take — used to calibrate the harness (see `selftest`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .agent import Episode


@dataclass
class Task:
    id: str
    tier: int
    prompt: str
    tools: list[str]
    checks: list[dict]
    reference: list[dict]
    max_turns: int = 8
    notes: str = ""

    @property
    def source_file(self) -> str:
        return getattr(self, "_source", "")


def load_tasks(tasks_dir: Path) -> list[Task]:
    tasks: list[Task] = []
    seen: set[str] = set()
    for path in sorted(tasks_dir.glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text()) or []:
            task = Task(**raw)
            if task.id in seen:
                raise ValueError(f"Duplicate task id: {task.id}")
            seen.add(task.id)
            task._source = path.name
            tasks.append(task)
    if not tasks:
        raise ValueError(f"No tasks found in {tasks_dir}")
    return tasks


# ── Checkers ─────────────────────────────────────────────────────────────────

def _values_match(expected, actual) -> bool:
    """Tolerant compare: numeric within 1e-6 relative; strings by casefolded
    substring (expected within actual or vice versa)."""
    if isinstance(expected, (int, float)) or isinstance(actual, (int, float)):
        try:
            a, b = float(expected), float(actual)
            return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))
        except (TypeError, ValueError):
            return False
    e, a = str(expected).casefold().strip(), str(actual).casefold().strip()
    return e in a or a in e


def _check_tool_called(check: dict, ep: Episode) -> bool:
    for call in ep.calls:
        if call.name != check["tool"]:
            continue
        subset = check.get("args_subset", {})
        if not all(k in call.arguments and _values_match(v, call.arguments[k])
                   for k, v in subset.items()):
            continue
        contains = check.get("args_contains", {})
        ok = True
        for k, needles in contains.items():
            actual = str(call.arguments.get(k, "")).casefold()
            if not any(str(n).casefold() in actual for n in needles):
                ok = False
                break
        if ok:
            return True
    return False


def _check_tool_not_called(check: dict, ep: Episode) -> bool:
    tool = check["tool"]
    if tool == "*":
        return len(ep.calls) == 0
    return all(c.name != tool for c in ep.calls)


def _check_final_answer_contains(check: dict, ep: Episode) -> bool:
    answer = ep.final_answer.casefold()
    if "any" in check:
        return any(str(n).casefold() in answer for n in check["any"])
    return all(str(n).casefold() in answer for n in check.get("all", []))


def _check_max_tool_calls(check: dict, ep: Episode) -> bool:
    return len(ep.calls) <= int(check["n"])


CHECKERS = {
    "tool_called": _check_tool_called,
    "tool_not_called": _check_tool_not_called,
    "final_answer_contains": _check_final_answer_contains,
    "max_tool_calls": _check_max_tool_calls,
}


@dataclass
class Grade:
    success: bool
    failed_checks: list[str] = field(default_factory=list)


def grade(task: Task, ep: Episode) -> Grade:
    if ep.error:
        return Grade(success=False, failed_checks=[f"episode error: {ep.error}"])
    failed = []
    for check in task.checks:
        kind = check["type"]
        if kind not in CHECKERS:
            raise ValueError(f"Task {task.id}: unknown check type {kind!r}")
        if not CHECKERS[kind](check, ep):
            failed.append(_describe(check))
    return Grade(success=not failed, failed_checks=failed)


def _describe(check: dict) -> str:
    parts = [check["type"]]
    for key in ("tool", "args_subset", "args_contains", "any", "all", "n"):
        if key in check:
            parts.append(f"{key}={check[key]}")
    return " ".join(parts)
