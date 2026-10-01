"""Minimal chat clients for the Blue scanner.

The local contract comes from measurements on the target Mac (see docs/HARDWARE.md):
- JSON-schema constrained output works through Ollama's native /api/chat `format`;
- a prompt longer than num_ctx is truncated SILENTLY, so `prompt_tokens >= num_ctx` is an error;
- thinking models must run with thinking off, otherwise they reason inside the answer until the cap;
- temperature 0 makes seeds meaningless, so runs use T > 0 and an explicit seed.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


class LLMError(Exception):
    pass


class ContextTruncated(LLMError):
    """The server cut the prompt to fit num_ctx; the answer would be based on partial input."""


@dataclass
class Reply:
    text: str
    prompt_tokens: int | None = None
    gen_tokens: int | None = None
    wall_s: float = 0.0
    done_reason: str | None = None
    cached: bool = False


class ChatClient(Protocol):
    model: str

    def chat(self, prompt: str, schema: dict) -> Reply: ...


def check_context(prompt_tokens: int | None, num_ctx: int) -> None:
    if prompt_tokens is not None and prompt_tokens >= num_ctx:
        raise ContextTruncated(f"prompt used {prompt_tokens} tokens of a {num_ctx}-token context; input was truncated")


class OllamaClient:
    def __init__(self, model: str, host: str = "http://127.0.0.1:11434", num_ctx: int = 8192,
                 num_predict: int = 1500, temperature: float = 0.7, seed: int = 1,
                 think: bool | None = False, timeout: int = 900):
        self.model, self.host, self.timeout = model, host.rstrip("/"), timeout
        self.num_ctx, self.num_predict, self.temperature, self.seed, self.think = num_ctx, num_predict, temperature, seed, think

    def options(self) -> dict:
        return {"temperature": self.temperature, "seed": self.seed, "num_ctx": self.num_ctx,
                "num_predict": self.num_predict, "think": self.think}

    def chat(self, prompt: str, schema: dict) -> Reply:
        body = {"model": self.model, "stream": False, "format": schema,
                "messages": [{"role": "user", "content": prompt}],
                "options": {k: v for k, v in self.options().items() if k != "think"}}
        if self.think is not None:
            body["think"] = self.think
        req = urllib.request.Request(f"{self.host}/api/chat", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                d = json.load(resp)
        except OSError as exc:
            raise LLMError(f"cannot reach {self.host}: {exc}") from exc
        reply = Reply(d["message"]["content"], d.get("prompt_eval_count"), d.get("eval_count"),
                      time.time() - t0, d.get("done_reason"))
        check_context(reply.prompt_tokens, self.num_ctx)
        return reply


class CachedClient:
    """Disk cache keyed by (model, options, prompt, schema): re-running an evaluation is free and replayable."""

    def __init__(self, inner, directory: Path):
        self.inner, self.dir = inner, Path(directory)
        self.model = inner.model

    def _key(self, prompt: str, schema: dict) -> str:
        opts = self.inner.options() if hasattr(self.inner, "options") else {}
        blob = json.dumps([self.inner.model, opts, prompt, schema], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def chat(self, prompt: str, schema: dict) -> Reply:
        path = self.dir / f"{self._key(prompt, schema)}.json"
        if path.exists():
            data = json.loads(path.read_text())
            return Reply(**{**data, "cached": True})
        reply = self.inner.chat(prompt, schema)
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(reply.__dict__))
        return reply


class FakeClient:
    """Scripted client for tests: `responder(prompt) -> str` returns the raw model text."""

    def __init__(self, responder: Callable[[str], str], model: str = "fake"):
        self.model, self.responder, self.calls = model, responder, []

    def chat(self, prompt: str, schema: dict) -> Reply:
        self.calls.append(prompt)
        return Reply(self.responder(prompt), prompt_tokens=len(prompt) // 4, gen_tokens=50)
