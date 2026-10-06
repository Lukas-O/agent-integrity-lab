"""Conservative request pacing shared by the sequential Hawk worker processes."""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path


async def reserve(model: str, prompt_chars: int, max_tokens: int = 2048) -> tuple[str, float]:
    path = os.environ.get("SHOWCASE_RATE_STATE")
    if not path or model.startswith("mockllm/"):
        return "", 0.0
    state_path = Path(path)
    started = time.perf_counter()
    reservation = min(7800, prompt_chars // 3 + max_tokens + 700)
    while True:
        history = json.loads(state_path.read_text()) if state_path.exists() else []
        now = time.time()
        history = [r for r in history if now - r["at"] < 86400]
        same = [r for r in history if r["model"] == model]
        is_groq = model.startswith("groq/")
        if is_groq and sum(r["tokens"] for r in same) + reservation > 175000:
            raise RuntimeError(
                "Local conservative daily token budget reached; no provider call made"
            )
        if (
            not is_groq
            and len([r for r in history if r["model"].startswith("free_openrouter/")]) >= 850
        ):
            raise RuntimeError("Local conservative daily free-request budget reached")
        recent = [r for r in same if now - r["at"] < 65]
        spacing = 3.2 if model.startswith("free_openrouter/") else 2.2
        wait = max(0, spacing - (now - same[-1]["at"])) if same else 0
        if is_groq and recent and sum(r["tokens"] for r in recent) + reservation > 7500:
            wait = max(wait, 65 - (now - recent[0]["at"]))
        if wait > 0:
            await asyncio.sleep(min(wait, 30))
            continue
        identifier = uuid.uuid4().hex
        history.append({"id": identifier, "model": model, "at": now, "tokens": reservation})
        state_path.write_text(json.dumps(history))
        return identifier, time.perf_counter() - started


def complete(identifier: str, tokens: int | None):
    if not identifier or tokens is None:
        return
    path = Path(os.environ["SHOWCASE_RATE_STATE"])
    history = json.loads(path.read_text())
    for row in history:
        if row["id"] == identifier:
            row["tokens"] = tokens
    path.write_text(json.dumps(history))
