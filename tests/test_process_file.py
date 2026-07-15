import corpus_pass as cp

SPEC = {
    "system_prompt": "Extract stuff.",
    "columns": ["pillars", "summary"],
    "list_fields": ["pillars"],
    "computed_fields": {"word_count": "words"},
    "allowed_values": {"pillars": ["A", "B"]},
    "id_field": "note_id",
}


def test_build_prompt_includes_content_and_keys():
    p = cp.build_prompt(SPEC, "hello world", stricter=False)
    assert "hello world" in p
    assert "pillars, summary" in p
    assert "STRICT" not in p


def test_build_prompt_stricter_lists_allowed():
    p = cp.build_prompt(SPEC, "x", stricter=True)
    assert "STRICT" in p
    assert "A, B" in p


def test_file_id_is_stem(tmp_path):
    f = tmp_path / "My Note.md"
    f.write_text("x")
    assert cp.file_id(str(f)) == "My Note"


def test_process_file_happy_path(tmp_path):
    f = tmp_path / "note1.md"
    f.write_text("one two three four")
    calls = []

    def fake_runner(prompt, model):
        calls.append((prompt, model))
        return '{"pillars": ["A"], "summary": "ok"}'

    row = cp.process_file(str(f), SPEC, "haiku", const={"medium": "written"}, runner=fake_runner)
    assert row["note_id"] == "note1"
    assert row["pillars"] == ["A"]
    assert row["summary"] == "ok"
    assert row["word_count"] == 4
    assert row["medium"] == "written"
    assert row["schema_violations"] == ""
    assert len(calls) == 1


def test_process_file_retries_once_on_violation(tmp_path):
    f = tmp_path / "note2.md"
    f.write_text("hello")
    outputs = iter([
        '{"pillars": ["Bogus"], "summary": "s"}',
        '{"pillars": ["B"], "summary": "s"}',
    ])
    prompts = []

    def fake_runner(prompt, model):
        prompts.append(prompt)
        return next(outputs)

    row = cp.process_file(str(f), SPEC, "haiku", runner=fake_runner)
    assert row["pillars"] == ["B"]
    assert row["schema_violations"] == ""
    assert len(prompts) == 2
    assert "STRICT" in prompts[1]


def test_process_file_coerces_after_failed_retry(tmp_path):
    f = tmp_path / "note3.md"
    f.write_text("hello")

    def fake_runner(prompt, model):
        return '{"pillars": ["Nope"], "summary": "s"}'

    row = cp.process_file(str(f), SPEC, "haiku", runner=fake_runner)
    assert row["pillars"] == ["other"]
    assert row["schema_violations"] == "pillars=Nope"


def test_call_model_invokes_claude(monkeypatch):
    captured = {}

    class FakeCompleted:
        returncode = 0
        stdout = '{"ok": 1}'
        stderr = ""

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None):
        captured["cmd"] = cmd
        captured["input"] = input
        return FakeCompleted()

    monkeypatch.setattr(cp.subprocess, "run", fake_run)
    out = cp.call_model("my prompt", "haiku")
    assert out == '{"ok": 1}'
    assert captured["cmd"] == ["claude", "-p", "--model", "haiku"]
    assert captured["input"] == "my prompt"


def test_call_model_raises_on_nonzero(monkeypatch):
    import pytest

    class FakeCompleted:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(cp.subprocess, "run", lambda *a, **k: FakeCompleted())
    with pytest.raises(RuntimeError):
        cp.call_model("p", "haiku")
