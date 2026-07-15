import csv as _csv
import corpus_pass as cp

SPEC = {
    "columns": ["pillars", "summary"],
    "list_fields": ["pillars"],
    "computed_fields": {"word_count": "words"},
    "allowed_values": {"pillars": ["A", "B"]},
    "id_field": "note_id",
}


def test_build_fieldnames_order():
    fn = cp.build_fieldnames(SPEC, {"medium": "written"})
    assert fn == ["note_id", "pillars", "summary", "word_count", "medium", "schema_violations"]


def test_serialize_row_joins_list_fields():
    fn = cp.build_fieldnames(SPEC, {"medium": "written"})
    row = {
        "note_id": "n1", "pillars": ["A", "B"], "summary": "hi",
        "word_count": 3, "medium": "written", "schema_violations": "",
    }
    out = cp.serialize_row(row, SPEC, fn)
    assert out["pillars"] == "A; B"
    assert out["word_count"] == 3


def test_append_row_writes_header_once(tmp_path):
    csv_path = str(tmp_path / "out.csv")
    fn = cp.build_fieldnames(SPEC, {})
    cp.append_row(csv_path, {"note_id": "n1", "pillars": "A", "summary": "x", "word_count": 2, "schema_violations": ""}, fn)
    cp.append_row(csv_path, {"note_id": "n2", "pillars": "B", "summary": "y", "word_count": 4, "schema_violations": ""}, fn)
    with open(csv_path, newline="") as fh:
        rows = list(_csv.DictReader(fh))
    assert [r["note_id"] for r in rows] == ["n1", "n2"]
    assert open(csv_path).read().count("note_id") == 1


def test_reconcile_counts(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for name in ["a", "b", "c"]:
        (src / f"{name}.md").write_text("x")
    csv_path = str(tmp_path / "out.csv")
    cp.append_row(csv_path, {"note_id": "a"}, ["note_id"])
    cp.append_row(csv_path, {"note_id": "b"}, ["note_id"])
    errors_path = str(tmp_path / "err.log")
    open(errors_path, "w").write("c\tValueError: bad\n")
    summary = cp.reconcile(f"{src}/*.md", csv_path, errors_path, "note_id")
    assert summary["files"] == 3
    assert summary["rows"] == 2
    assert summary["errors"] == 1
    # 'c' has no row, so it is missing; accounted/reconciled must both be False
    # under the file-set contract (accounted = not missing and not duplicates).
    assert summary["missing"] == ["c"]
    assert summary["accounted"] is False
    assert summary["reconciled"] is False


def test_reconcile_clean(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("x")
    csv_path = str(tmp_path / "out.csv")
    cp.append_row(csv_path, {"note_id": "a"}, ["note_id"])
    summary = cp.reconcile(f"{src}/*.md", csv_path, str(tmp_path / "err.log"), "note_id")
    assert summary["reconciled"] is True


def test_reconcile_counts_only_current_glob(tmp_path):
    # Two passes share one CSV (Phase 7: written-pass + spoken-pass -> one file).
    # reconcile must count only the CURRENT glob's files, not every CSV row. (bug #2)
    src = tmp_path / "src"
    src.mkdir()
    for name in ["C", "D"]:
        (src / f"{name}.md").write_text("x")
    csv_path = str(tmp_path / "out.csv")
    for nid in ["A", "B", "C", "D"]:  # A,B belong to the OTHER pass
        cp.append_row(csv_path, {"note_id": nid}, ["note_id"])
    summary = cp.reconcile(f"{src}/*.md", csv_path, str(tmp_path / "err.log"), "note_id")
    assert summary["files"] == 2
    assert summary["rows"] == 2
    assert summary["missing"] == []
    assert summary["reconciled"] is True


def test_reconcile_flags_missing_file(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("x")
    (src / "b.md").write_text("x")
    csv_path = str(tmp_path / "out.csv")
    cp.append_row(csv_path, {"note_id": "a"}, ["note_id"])  # 'b' never got a row
    summary = cp.reconcile(f"{src}/*.md", csv_path, str(tmp_path / "err.log"), "note_id")
    assert summary["missing"] == ["b"]
    assert summary["reconciled"] is False


def test_reconcile_flags_duplicate_stems(tmp_path):
    # Two real files in different subdirs collide on the same filename stem.
    # The gate must fail loud, not silently accept one row covering both. (bug #4)
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    (tmp_path / "x" / "dup.md").write_text("x")
    (tmp_path / "y" / "dup.md").write_text("y")
    csv_path = str(tmp_path / "out.csv")
    cp.append_row(csv_path, {"note_id": "dup"}, ["note_id"])
    summary = cp.reconcile(f"{tmp_path}/**/*.md", csv_path, str(tmp_path / "err.log"), "note_id")
    assert summary["duplicate_ids"] == ["dup"]
    assert summary["reconciled"] is False


def test_audit_sample_size_and_determinism(tmp_path):
    csv_path = str(tmp_path / "out.csv")
    for i in range(10):
        cp.append_row(csv_path, {"note_id": f"n{i}"}, ["note_id"])
    sample = cp.audit_sample(csv_path, 3, "note_id", seed=1)
    assert len(sample) == 3
    assert cp.audit_sample(csv_path, 3, "note_id", seed=1) == sample
