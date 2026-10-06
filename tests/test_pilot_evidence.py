"""Check published claims against the recorded evidence, without provider calls."""

import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    data = json.loads((ROOT / "evidence/provider-pilot/data.json").read_text())
    logs = {record["path"]: read_eval_log(ROOT / record["path"]) for record in data["files"]}
    return data, logs


def test_published_sample_counts_and_timings_match_traces(evidence):
    data, logs = evidence
    assert len(data["samples"]) == sum(len(log.samples) for log in logs.values()) == 24
    assert len(logs) == 12
    assert sum(row["correct"] == 1 for row in data["samples"]) == 17
    assert Counter(row["failure"] for row in data["samples"] if row["failure"]) == {
        "rate_limit": 5,
        "tool_protocol_error": 1,
        "output_truncated": 1,
    }
    for row in data["samples"]:
        sample = next(
            sample
            for sample in logs[row["trace"]].samples
            if (sample.id, sample.epoch) == (row["sample_id"], row["epoch"])
        )
        assert row["agent_seconds"] == sample.store["agent_seconds"]
        if sample.error:
            assert row["correct"] is None
            assert row["failure"] == sample.error.message
        else:
            assert row["correct"] == next(iter(sample.scores.values())).value

    actual_requests = [
        event
        for log in logs.values()
        for sample in log.samples
        for event in sample.events
        if event.event == "model"
    ]
    assert len(data["requests"]) == len(actual_requests) == 43
    assert sum(row["error"] for row in data["requests"]) == 6
    assert all(not event.retries for event in actual_requests)


def test_reviewed_artifacts_and_source_snapshots_match_recorded_hashes(evidence):
    data, _ = evidence
    for record in data["files"]:
        assert (
            hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest()
            == record["reviewed_sha256"]
        )
    for batch in data["batches"]:
        archive = ROOT / batch["source_archive"]["path"]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == batch["source_archive"]["sha256"]
        with zipfile.ZipFile(archive) as source:
            assert set(source.namelist()) == set(batch["source_hashes"]["files"])
            for path, digest in batch["source_hashes"]["files"].items():
                assert hashlib.sha256(source.read(path)).hexdigest() == digest


def test_recorded_openrouter_requests_used_zero_price_routing(evidence):
    data, logs = evidence
    observed = 0
    for log in logs.values():
        if not log.eval.model.startswith("free_openrouter/"):
            continue
        for sample in log.samples:
            for event in sample.events:
                if event.event != "model" or not event.call:
                    continue
                request = event.call.request
                assert request["model"].endswith(":free")
                routing = request["extra_body"]["provider"]
                assert routing["allow_fallbacks"] is False
                assert routing["max_price"] == {"prompt": 0, "completion": 0}
                assert routing["require_parameters"] is True
                assert "models" not in request["extra_body"]
                observed += 1
    assert observed > 0
    assert all(batch["openrouter_usage_delta_usd"] == 0 for batch in data["batches"])
