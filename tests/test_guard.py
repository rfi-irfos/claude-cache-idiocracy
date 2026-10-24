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
from hache_guard.indexer import SessionIndexer
from hache_guard.doctor import report
from hache_guard.lifecycle import rollback, uninstall
from hache_guard.proxy import Budget
from hache_guard.agent_guard import admit, release


def test_policy_is_ten_tools_three_agents():
    env = Policy().environment()
    assert env["CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"] == "10"
    assert env["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "3"
    assert env["CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS"] == "3"
    assert env["CLAUDE_CODE_PROMPT_CACHE_TTL"] == "1h"
    assert env["CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL"] == "1h"


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
        {"type":"api-request", "id":"new", "timestamp":"2020-01-01T00:20:00Z", "error":"502 timeout"},
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
    project_name = str(cwd.resolve()).replace("\\", "-").replace("/", "-").replace(":", "")
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
    assert sum(item["matcher"] == "Read" for item in data["hooks"]["PreToolUse"]) == 1
    assert sum(item["matcher"] == "Read" for item in data["hooks"]["PostToolUse"]) == 1

def test_installer_wires_existing_rtk_without_requiring_it(tmp_path, monkeypatch):
    monkeypatch.setattr("hache_guard.installer.shutil.which", lambda name: "/usr/bin/rtk" if name == "rtk" else None)
    target = tmp_path / "settings.json"; install_settings(target)
    data = json.loads(target.read_text())
    assert any(h["command"] == "rtk hook claude" for item in data["hooks"]["PreToolUse"] for h in item["hooks"])

def test_indexer_is_incremental_and_deduplicates(tmp_path):
    transcript = tmp_path / "s.jsonl"; transcript.write_text(json.dumps({"id":"a","type":"assistant"}) + "\n")
    index = SessionIndexer(tmp_path / "index.sqlite")
    assert index.index(transcript)["new_events"] == 1
    assert index.index(transcript)["new_events"] == 0
    transcript.write_text(transcript.read_text() + json.dumps({"id":"b","type":"assistant"}) + "\n")
    assert index.index(transcript)["new_events"] == 1
    index.close()

def test_doctor_reports_policy_and_valid_settings(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks":{"PreToolUse":[{"hooks":[{"command":"hache_guard"}]}]}}))
    result = report(settings)
    assert result["settings_valid"] and result["hooks_installed"] and result["policy"]["CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"] == "10"

def test_installer_creates_backup_and_uninstall_preserves_other_settings(tmp_path):
    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"custom": True}))
    install_settings(target)
    assert list(tmp_path.glob("settings.json.hache-backup-*"))
    uninstall(target)
    data = json.loads(target.read_text())
    assert data["custom"] is True and not any("hache_guard" in json.dumps(x) for x in data.get("hooks", {}).values())

def test_proxy_budget_is_local_and_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("HACHE_PROXY_STATE", str(tmp_path / "proxy.sqlite"))
    monkeypatch.setenv("HACHE_PROXY_INPUT_BUDGET", "10")
    budget = Budget()
    assert budget.charge(10)
    assert not budget.charge(1)

def test_proxy_records_usage_metadata_without_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("HACHE_PROXY_STATE", str(tmp_path / "proxy.sqlite"))
    budget = Budget(); assert budget.charge(20); budget.record("req", 20, 12, 200, 4.5); budget.close()
    raw = (tmp_path / "proxy.sqlite").read_bytes()
    assert b"req" in raw and b"prompt" not in raw

def test_doctor_strict_rejects_invalid_settings(tmp_path):
    target = tmp_path / "bad.json"; target.write_text("not-json")
    result = report(target)
    assert not result["settings_valid"] and not result["strict_ok"]

def test_indexer_recovers_after_transcript_truncation(tmp_path):
    transcript = tmp_path / "s.jsonl"; transcript.write_text(json.dumps({"id":"a"}) + "\n")
    index = SessionIndexer(tmp_path / "i.sqlite"); index.index(transcript)
    transcript.write_text(json.dumps({"id":"b"}) + "\n")
    assert index.index(transcript)["new_events"] == 1
    index.close()

def test_indexer_does_not_store_message_body(tmp_path):
    transcript = tmp_path / "s.jsonl"; transcript.write_text(json.dumps({"id":"a","message":"SECRET"}) + "\n")
    database = tmp_path / "i.sqlite"; index = SessionIndexer(database); index.index(transcript); index.close()
    assert b"SECRET" not in database.read_bytes()

def test_uninstall_removes_only_hache_hooks(tmp_path):
    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"hooks":{"PreToolUse":[{"hooks":[{"command":"hache_guard pre"}]},{"hooks":[{"command":"custom"}]}]}}))
    uninstall(target)
    data = json.loads(target.read_text())
    assert "hache_guard" not in json.dumps(data) and "custom" in json.dumps(data)

def test_rollback_restores_latest_backup(tmp_path):
    target = tmp_path / "settings.json"; target.write_text(json.dumps({"before": True}))
    install_settings(target); target.write_text(json.dumps({"after": True}))
    assert rollback(target) is not None
    assert json.loads(target.read_text())["before"] is True

def test_compact_list_content_is_preserved(tmp_path):
    target = tmp_path / "s.jsonl"
    target.write_text(json.dumps({"type":"user","message":{"role":"user","content":[{"type":"text","text":"important task"}]}}) + "\n")
    compact(target, replace=True)
    assert "important task" in json.loads(target.read_text())["message"]["content"]

def test_policy_env_override_for_concurrency(monkeypatch):
    monkeypatch.setenv("HACHE_MAX_TOOLS", "7")
    assert Policy.from_env().max_tools == 7

def test_breaker_error_threshold_is_hard():
    assert evaluate({"errors":{"502":50}})["state"] == "break"

def test_agent_guard_enforces_three_and_releases(tmp_path, monkeypatch):
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    assert admit("s")[0] and admit("s")[0] and admit("s")[0]
    assert not admit("s")[0]
    release("s")
    assert admit("s")[0]

def test_agent_guard_isolated_by_session(tmp_path, monkeypatch):
    monkeypatch.setenv("HACHE_STATE", str(tmp_path / "state.json"))
    for _ in range(3): assert admit("a")[0]
    assert admit("b")[0]
