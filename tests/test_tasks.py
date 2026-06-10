from pathlib import Path

from wrenchmark.mocktools import TOOLS
from wrenchmark.tasks import CHECKERS, load_tasks

TASKS_DIR = Path(__file__).resolve().parents[1] / "tasks"


def test_tasks_load_and_are_well_formed():
    tasks = load_tasks(TASKS_DIR)
    assert len(tasks) >= 20
    for task in tasks:
        assert task.tier in (1, 2, 3), task.id
        assert task.prompt and task.tools and task.checks, task.id
        assert task.reference, f"{task.id} is missing a reference solution"
        for tool in task.tools:
            assert tool in TOOLS, f"{task.id} references unknown tool {tool}"
        for check in task.checks:
            assert check["type"] in CHECKERS, f"{task.id} has unknown check {check['type']}"
        # reference steps must use tools available to the task
        for step in task.reference:
            if "tool" in step:
                assert step["tool"] in task.tools, (
                    f"{task.id} reference uses {step['tool']} not in its tool list"
                )


def test_all_tiers_represented():
    tiers = {t.tier for t in load_tasks(TASKS_DIR)}
    assert tiers == {1, 2, 3}
