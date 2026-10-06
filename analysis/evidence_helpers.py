"""Shared review transformations for exported Inspect evidence."""

import re
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET = re.compile(
    r"(?:sk-or-v1-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]{20,})"
)


def clean(value):
    """Remove transport headers and local identities, preserving behavioral data."""
    if isinstance(value, dict):
        result = {
            k: clean(v)
            for k, v in value.items()
            if k.lower()
            not in {"authorization", "api_key", "headers", "extra_headers", "signature"}
        }
        if value.get("redacted") is True and "reasoning" in result:
            result["reasoning"] = "[opaque reasoning omitted]"
        if value.get("type") == "reasoning.encrypted" and "data" in result:
            result["data"] = "[opaque reasoning omitted]"
        return result
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, str):
        if SECRET.search(value):
            raise ValueError("Credential-like content detected; publication stopped")
        for original, replacement in [
            (str(ROOT), "${PROJECT_ROOT}"),
            (str(Path.home()), "${RUNNER_HOME}"),
            (socket.gethostname(), "${RUNNER_HOST}"),
        ]:
            value = value.replace(original, replacement)
        return re.sub(r"0x[0-9a-f]{8,}", "<memory-address>", value)
    return value


def failure_kind(sample):
    message = sample.error.message if sample.error else ""
    if "RateLimitError" in message:
        return "rate_limit"
    if "tool_use_failed" in message:
        return "tool_protocol_error"
    if sample.error:
        return "execution_error"
    if sample.output.choices and sample.output.stop_reason == "max_tokens":
        return "output_truncated"
    return ""
