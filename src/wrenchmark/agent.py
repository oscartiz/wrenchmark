"""The system-under-test driver: a minimal, provider-agnostic tool-call loop.

Deliberately plain — the benchmark measures the *model's* tool-calling
ability, so the harness adds no retries, no prompt tricks, no parsing help
beyond feeding tool errors back as tool results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools. Use a tool when it is "
    "needed to answer correctly; answer directly when it is not. When you have "
    "the answer, state it clearly and concisely."
)


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: str


@dataclass
class Episode:
    final_answer: str = ""
    calls: list[ToolCall] = field(default_factory=list)
    turns: int = 0
    malformed_calls: int = 0
    hit_max_turns: bool = False
    error: str | None = None
    latency_s: float = 0.0


def run_episode(provider, prompt: str, schemas: list[dict], dispatch: dict,
                max_turns: int = 8) -> Episode:
    ep = Episode()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    start = time.perf_counter()
    try:
        for turn in range(max_turns):
            ep.turns = turn + 1
            response = provider.chat(messages, schemas)
            messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": [
                    {"function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in response["tool_calls"]
                ],
            })

            if not response["tool_calls"]:
                ep.final_answer = response["content"]
                return ep

            for call in response["tool_calls"]:
                name, args = call["name"], call["arguments"]
                if name not in dispatch or "_malformed" in args:
                    ep.malformed_calls += 1
                    result = f"Error: invalid tool call {name!r}"
                else:
                    try:
                        result = str(dispatch[name](**args))
                    except TypeError as e:
                        ep.malformed_calls += 1
                        result = f"Error: bad arguments for {name}: {e}"
                ep.calls.append(ToolCall(name, args if isinstance(args, dict) else {}, result))
                messages.append({"role": "tool", "name": name, "content": result})

        ep.hit_max_turns = True
    except Exception as e:
        ep.error = f"{type(e).__name__}: {e}"
    finally:
        ep.latency_s = time.perf_counter() - start
    return ep
