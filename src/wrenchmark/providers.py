"""Model providers, all normalized to one response shape:

    {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}

`ScriptedProvider` replays a fixed action sequence — it's how reference
solutions and baselines run through the exact same pipeline as real models,
which is what lets the harness be calibrated and CI-tested without a GPU.
"""

from __future__ import annotations

import json
import os
from typing import Protocol


class Provider(Protocol):
    name: str

    def chat(self, messages: list[dict], tools: list[dict]) -> dict: ...


class ScriptedProvider:
    """Replays a list of steps: {"tool": name, "args": {...}} or {"answer": str}."""

    def __init__(self, steps: list[dict], name: str = "scripted"):
        self.name = name
        self._steps = list(steps)
        self._i = 0

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        if self._i >= len(self._steps):
            return {"content": "", "tool_calls": []}
        step = self._steps[self._i]
        self._i += 1
        if "tool" in step:
            return {
                "content": "",
                "tool_calls": [{"name": step["tool"], "arguments": dict(step.get("args", {}))}],
            }
        return {"content": str(step.get("answer", "")), "tool_calls": []}


class NullProvider:
    """Baseline that never uses tools and answers unhelpfully. Should score ~0."""

    name = "null-baseline"

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        return {"content": "I don't have enough information to answer that.", "tool_calls": []}


class OllamaProvider:
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        import ollama

        self.name = model
        self._client = ollama.Client(host=base_url)
        self._model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        response = self._client.chat(model=self._model, messages=messages, tools=tools or None)
        msg = response.message
        calls = []
        for tc in msg.tool_calls or []:
            args = tc.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_malformed": args}
            calls.append({"name": tc.function.name, "arguments": args or {}})
        return {"content": msg.content or "", "tool_calls": calls}


class OpenAICompatProvider:
    """Together AI, OpenRouter, llama.cpp server — anything OpenAI-compatible."""

    def __init__(self, model: str, base_url: str, api_key: str | None = None):
        from openai import OpenAI

        self.name = model
        key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("TOGETHER_API_KEY") or "none"
        self._client = OpenAI(base_url=base_url, api_key=key)
        self._model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        kwargs = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        choice = self._client.chat.completions.create(**kwargs).choices[0].message
        calls = []
        for tc in choice.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {"_malformed": tc.function.arguments}
            calls.append({"name": tc.function.name, "arguments": args})
        return {"content": choice.content or "", "tool_calls": calls}


def make_provider(kind: str, model: str, base_url: str | None = None) -> Provider:
    if kind == "ollama":
        return OllamaProvider(model, base_url or "http://localhost:11434")
    if kind == "openai":
        if not base_url:
            raise ValueError("--base-url is required for the openai provider")
        return OpenAICompatProvider(model, base_url)
    if kind == "null":
        return NullProvider()
    raise ValueError(f"Unknown provider kind: {kind!r}")
