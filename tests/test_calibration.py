"""Harness calibration: the instrument must be validated before it measures.

1. Every task's reference solution, replayed through the *full* pipeline
   (provider → agent loop → mock tools → checkers), must pass its own checks.
2. The null baseline (never calls tools, answers unhelpfully) must fail
   nearly everything — if it passes, the checks are too loose.
"""

from pathlib import Path

import pytest

from wrenchmark.providers import NullProvider
from wrenchmark.runner import reference_provider, run_task
from wrenchmark.tasks import load_tasks

TASKS = load_tasks(Path(__file__).resolve().parents[1] / "tasks")


@pytest.mark.parametrize("task", TASKS, ids=[t.id for t in TASKS])
def test_reference_solution_passes(task):
    record = run_task(reference_provider(task), task)
    assert record["success"], f"{task.id} failed checks: {record['failed_checks']}"


def test_null_baseline_fails_almost_everything():
    passes = sum(run_task(NullProvider(), t)["success"] for t in TASKS)
    assert passes <= len(TASKS) * 0.15, (
        f"Null baseline passed {passes}/{len(TASKS)} tasks — checks are too loose"
    )
