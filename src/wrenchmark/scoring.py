"""Aggregate episode records into per-model scores with binomial error bars."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

TIERS = (1, 2, 3)


@dataclass
class ModelScore:
    model: str
    n: int = 0
    successes: int = 0
    by_tier: dict = field(default_factory=lambda: {t: [0, 0] for t in TIERS})  # tier -> [ok, n]
    tool_calls: int = 0
    malformed: int = 0
    latency_total: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.n if self.n else 0.0

    @property
    def stderr(self) -> float:
        """Binomial standard error on the overall success rate."""
        if not self.n:
            return 0.0
        p = self.success_rate
        return math.sqrt(p * (1 - p) / self.n)

    def tier_rate(self, tier: int) -> tuple[float, float]:
        ok, n = self.by_tier[tier]
        if not n:
            return 0.0, 0.0
        p = ok / n
        return p, math.sqrt(p * (1 - p) / n)

    @property
    def mean_latency(self) -> float:
        return self.latency_total / self.n if self.n else 0.0

    @property
    def malformed_rate(self) -> float:
        return self.malformed / self.tool_calls if self.tool_calls else 0.0


def load_records(path: Path) -> list[dict]:
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def score(records: list[dict]) -> list[ModelScore]:
    scores: dict[str, ModelScore] = defaultdict(lambda: ModelScore(model=""))
    for r in records:
        s = scores[r["model"]]
        s.model = r["model"]
        s.n += 1
        s.successes += int(r["success"])
        tier = int(r["tier"])
        s.by_tier.setdefault(tier, [0, 0])
        s.by_tier[tier][0] += int(r["success"])
        s.by_tier[tier][1] += 1
        s.tool_calls += r["n_tool_calls"]
        s.malformed += r["malformed_calls"]
        s.latency_total += r["latency_s"]
    return sorted(scores.values(), key=lambda s: s.success_rate, reverse=True)
