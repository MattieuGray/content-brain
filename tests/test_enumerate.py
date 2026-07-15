import os
import corpus_pass as cp


def test_enumerate_files_sorted_and_unique(tmp_path):
    (tmp_path / "b.md").write_text("b")
    (tmp_path / "a.md").write_text("a")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.md").write_text("c")
    result = cp.enumerate_files(f"{tmp_path}/**/*.md")
    assert result == sorted(result)
    assert len(result) == 3


def test_enumerate_files_multiple_globs_dedupe(tmp_path):
    (tmp_path / "a.md").write_text("a")
    result = cp.enumerate_files(f"{tmp_path}/*.md,{tmp_path}/*.md")
    assert len(result) == 1


def test_enumerate_files_skips_directories(tmp_path):
    (tmp_path / "d.md").mkdir()
    (tmp_path / "real.md").write_text("x")
    result = cp.enumerate_files(f"{tmp_path}/*.md")
    assert all(os.path.isfile(p) for p in result)
    assert len(result) == 1


def test_load_done_ids_missing_file(tmp_path):
    assert cp.load_done_ids(str(tmp_path / "nope.csv"), "note_id") == set()


def test_load_done_ids_reads_ids(tmp_path):
    csv_path = tmp_path / "out.csv"
    csv_path.write_text("note_id,summary\nalpha,hi\nbeta,yo\n")
    assert cp.load_done_ids(str(csv_path), "note_id") == {"alpha", "beta"}
