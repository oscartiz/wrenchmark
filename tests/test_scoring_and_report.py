import json
from pathlib import Path

from wrenchmark.report import markdown_leaderboard, write_report
from wrenchmark.runner import reference_provider, run_sweep
from wrenchmark.scoring import load_records, score
from wrenchmark.tasks import load_tasks

TASKS = load_tasks(Path(__file__).resolve().parents[1] / "tasks")


def test_end_to_end_sweep_score_report(tmp_path):
    """Full pipeline offline: sweep references on a task subset, score, report."""
    subset = TASKS[:4]
    out = tmp_path / "results.jsonl"

    # run_sweep calls the factory per episode; rotate reference scripts per task
    for task in subset:
        run_sweep(lambda t=task: reference_provider(t), [task],
                  reps=2, out_path=out, quiet=True)

    records = load_records(out)
    assert len(records) == len(subset) * 2
    assert all(r["success"] for r in records)

    scores = score(records)
    assert len(scores) == 1
    s = scores[0]
    assert s.model == "reference"
    assert s.success_rate == 1.0
    assert s.stderr == 0.0

    md = markdown_leaderboard(scores)
    assert "reference" in md and "100%" in md

    report = write_report(scores, tmp_path / "out")
    assert report.exists()
    assert (tmp_path / "out" / "success_by_tier.png").exists()


def test_records_are_valid_jsonl(tmp_path):
    out = tmp_path / "r.jsonl"
    task = TASKS[0]
    run_sweep(lambda: reference_provider(task), [task], reps=1, out_path=out, quiet=True)
    for line in out.read_text().splitlines():
        record = json.loads(line)
        assert {"model", "task_id", "tier", "success", "latency_s"} <= set(record)
