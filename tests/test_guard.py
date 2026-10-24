import json
from pathlib import Path

from hache_guard.policy import Policy
from hache_guard.read_guard import check, record
from hache_guard.breaker import evaluate
from hache_guard.metrics import transcript_usage
from hache_guard.supervisor import find_transcript
from hache_guard.offline_compact import compact
from hache_guard.handover import write
from hache_guard.installer import install_settings


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

def test_breaker_warns_and_breaks():
    assert evaluate({"cache_read_input_tokens": 100_000_000})["state"] == "warn"
    assert evaluate({"cache_read_input_tokens": 250_000_000})["state"] == "break"

def test_transcript_usage_deduplicates_request_ids(tmp_path):
    target = tmp_path / "session.jsonl"
    row = {"type": "api-request", "id": "r1", "message": {"usage": {"cache_read_input_tokens": 10}}}
    target.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    assert transcript_usage(target)["cache_read_input_tokens"] == 10

def test_breaker_compaction_threshold():
    assert evaluate({"compactions": 2})["state"] == "warn"
    assert evaluate({"compactions": 3})["state"] == "break"


def test_changed_file_is_allowed(tmp_path, monkeypatch):
    target = tmp_path / "skill.py"
    target.write_text("one\n", encoding="utf-8")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target))
    target.write_text("two\n", encoding="utf-8")
    assert check(str(target)).allowed

def test_full_read_covers_partial_without_type_error(tmp_path, monkeypatch):
    target = tmp_path / "full.txt"; target.write_text("0123456789")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target), session="s1")
    assert not check(str(target), 2, 3, session="s1").allowed

def test_partial_read_does_not_cover_full_read(tmp_path, monkeypatch):
    target = tmp_path / "partial.txt"; target.write_text("0123456789")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target), 0, 1, session="s1")
    assert check(str(target), session="s1").allowed

def test_read_dedup_is_scoped_to_session(tmp_path, monkeypatch):
    target = tmp_path / "session.txt"; target.write_text("hello")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target), session="a")
    assert check(str(target), session="b").allowed

def test_range_overlap_is_blocked(tmp_path, monkeypatch):
    target = tmp_path / "x.txt"; target.write_text("0123456789")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target), 2, 4)
    assert not check(str(target), 3, 2).allowed

def test_range_outside_is_allowed(tmp_path, monkeypatch):
    target = tmp_path / "x.txt"; target.write_text("0123456789")
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    record(str(target), 2, 2)
    assert check(str(target), 8, 2).allowed

def test_metrics_parse_assistant_usage(tmp_path):
    target = tmp_path / "s.jsonl"
    row = {"type":"assistant", "message":{"usage":{"input_tokens":4,"output_tokens":2,"cache_read_input_tokens":9}}}
    target.write_text(json.dumps(row) + "\n")
    metrics = transcript_usage(target)
    assert metrics["input_tokens"] == 4 and metrics["cache_read_input_tokens"] == 9

def test_metrics_counts_one_error_per_request_and_uses_window(tmp_path):
    target = tmp_path / "errors.jsonl"
    rows = [
        {"type":"api-request", "id":"old", "timestamp":"2020-01-01T00:00:00Z", "error":"502 timeout"},
        {"type":"api-request", "id":"new", "timestamp":"2020-01-01T00:10:00Z", "error":"502 timeout"},
    ]
    target.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert transcript_usage(target)["errors"] == {"502": 1}

def test_offline_replace_archives_and_leaves_summary(tmp_path):
    target = tmp_path / "session.jsonl"
    original = json.dumps({"type":"user","message":{"role":"user","content":"hello"}}) + "\n"
    target.write_text(original)
    compact(target, replace=True)
    archives = list(tmp_path.glob("session.full-*.jsonl"))
    current = json.loads(target.read_text().splitlines()[0])
    assert current["isCompactSummary"] and "hello" in current["message"]["content"] and len(archives) == 1 and archives[0].read_text() == original

def test_handover_names_are_unique(tmp_path, monkeypatch):
    assert write("a", {}, str(tmp_path)) != write("a", {}, str(tmp_path))

def test_find_transcript_returns_existing_file(tmp_path):
    p = tmp_path / "abc.jsonl"; p.write_text("{}\n")
    import os, time
    os.environ["CLAUDE_PROJECTS"] = str(tmp_path)
    assert find_transcript(str(tmp_path), time.time() - 10) == p

def test_find_transcript_scopes_to_working_project(tmp_path):
    import os, time
    cwd = tmp_path / "project"; cwd.mkdir()
    project_name = str(cwd).replace("/", "-")
    scoped = tmp_path / project_name; scoped.mkdir()
    wanted = scoped / "wanted.jsonl"; wanted.write_text("{}\n")
    other = tmp_path / "other.jsonl"; other.write_text("{}\n")
    os.environ["CLAUDE_PROJECTS"] = str(tmp_path)
    assert find_transcript(str(cwd), time.time() - 10) == wanted

def test_installer_is_idempotent_and_sets_model(tmp_path):
    target = tmp_path / "settings.json"
    install_settings(target); install_settings(target)
    data = json.loads(target.read_text())
    assert data["model"] == "claude-sonnet-5"
    assert len(data["hooks"]["PreToolUse"]) == 1
    assert len(data["hooks"]["PostToolUse"]) == 1
