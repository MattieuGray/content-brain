import json
import corpus_pass as cp

SPEC = {
    "system_prompt": "Extract.",
    "columns": ["pillars", "summary"],
    "list_fields": ["pillars"],
    "allowed_values": {"pillars": ["A", "B"]},
    "id_field": "note_id",
}


def _mk_notes(tmp_path, n):
    src = tmp_path / "src"
    src.mkdir()
    for i in range(n):
        (src / f"n{i}.md").write_text(f"content {i}")
    return src


def test_run_processes_all_and_reconciles(tmp_path):
    src = _mk_notes(tmp_path, 4)
    summary = cp.run(
        f"{src}/*.md", SPEC, str(tmp_path / "out.csv"), str(tmp_path / "err.log"),
        "haiku", runner=lambda p, m: '{"pillars": ["A"], "summary": "s"}',
        progress=lambda *a: None,
    )
    assert summary["files"] == 4
    assert summary["rows"] == 4
    assert summary["errors"] == 0
    assert summary["reconciled"] is True


def test_run_is_resumable(tmp_path):
    src = _mk_notes(tmp_path, 3)
    csv_path = str(tmp_path / "out.csv")
    errors_path = str(tmp_path / "err.log")
    calls = {"n": 0}

    def fake_runner(prompt, model):
        calls["n"] += 1
        return '{"pillars": ["A"], "summary": "s"}'

    cp.run(f"{src}/*.md", SPEC, csv_path, errors_path, "haiku", runner=fake_runner, progress=lambda *a: None)
    assert calls["n"] == 3
    cp.run(f"{src}/*.md", SPEC, csv_path, errors_path, "haiku", runner=fake_runner, progress=lambda *a: None)
    assert calls["n"] == 3


def test_run_logs_errors_and_continues(tmp_path):
    src = _mk_notes(tmp_path, 3)
    summary = cp.run(
        f"{src}/*.md", SPEC, str(tmp_path / "out.csv"), str(tmp_path / "err.log"),
        "haiku", runner=lambda p, m: "not json at all", progress=lambda *a: None,
    )
    assert summary["rows"] == 0
    assert summary["errors"] == 3
    assert summary["accounted"] is True


def test_load_spec_sets_defaults(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({"system_prompt": "x", "columns": ["a"]}))
    spec = cp.load_spec(str(spec_path))
    assert spec["id_field"] == "id"
    assert spec["allowed_values"] == {}
    assert spec["list_fields"] == []
    assert spec["computed_fields"] == {}


def test_load_spec_rejects_unknown_computer(tmp_path):
    import pytest
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({"system_prompt": "x", "columns": ["a"], "computed_fields": {"a": "nope"}}))
    with pytest.raises(ValueError):
        cp.load_spec(str(spec_path))


def test_main_end_to_end_with_monkeypatched_model(tmp_path, monkeypatch, capsys):
    src = _mk_notes(tmp_path, 2)
    spec = {
        "system_prompt": "x", "columns": ["pillars", "summary"], "list_fields": ["pillars"],
        "allowed_values": {"pillars": ["A"]}, "id_field": "note_id",
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    csv_path = tmp_path / "out.csv"
    monkeypatch.setattr(cp, "call_model", lambda prompt, model: '{"pillars": ["A"], "summary": "s"}')
    rc = cp.main([
        "--input", f"{src}/*.md", "--spec", str(spec_path),
        "--out", str(csv_path), "--model", "haiku", "--audit", "1",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COVERAGE:" in out
    assert csv_path.exists()
