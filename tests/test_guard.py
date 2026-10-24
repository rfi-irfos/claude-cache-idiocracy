import json
from pathlib import Path

from hache_guard.policy import Policy
from hache_guard.read_guard import check, record
from hache_guard.breaker import evaluate
from hache_guard.metrics import transcript_usage


def test_policy_is_ten_tools_three_agents():
    env = Policy().environment()
    assert env["CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"] == "10"
    assert env["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "3"
    assert env["CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS"] == "3"


def test_unchanged_full_read_is_blocked(tmp_path, monkeypatch):
    target = tmp_path / "skill.md"
    target.write_text("hello\nworld\n", encoding="utf-8")
    state = tmp_path / "state.json"
    monkeypatch.setenv("HACHE_STATE", str(state))
    assert check(str(target)).allowed

def test_breaker_warns_and_breaks():
    assert evaluate({"cache_read_input_tokens": 100_000_000})["state"] == "warn"
    assert evaluate({"cache_read_input_tokens": 250_000_000})["state"] == "break"

def test_transcript_usage_deduplicates_request_ids(tmp_path):
    target = tmp_path / "session.jsonl"
    row = {"type": "api-request", "id": "r1", "message": {"usage": {"cache_read_input_tokens": 10}}}
    target.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    assert transcript_usage(target)["cache_read_input_tokens"] == 10
    record(str(target))
    decision = check(str(target))
    assert not decision.allowed


def test_changed_file_is_allowed(tmp_path, monkeypatch):
    target = tmp_path / "skill.py"
    target.write_text("one\n", encoding="utf-8")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target))
    target.write_text("two\n", encoding="utf-8")
    assert check(str(target)).allowed
