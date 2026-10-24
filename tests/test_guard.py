import json
from pathlib import Path

from hache_guard.policy import Policy
from hache_guard.read_guard import check, record


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
