#!/usr/bin/env python3
"""corpus_pass.py - reusable per-file corpus processor for Content Brain.

Enumerate every file matching one or more globs, process each file in ONE
isolated `claude -p` call against an extraction spec, write one structured CSV
row per file, and reconcile (files-in equals rows-out). Resumable: skips ids
already in the output CSV. Never halts on a single failure; writes failures to
an errors log and continues.

No Anthropic API key needed: the transport is the `claude` CLI already present
on a Content Brain member's Mac.
"""

import argparse
import csv
import glob
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path


def enumerate_files(input_globs):
    """Return a sorted, de-duplicated list of files matching a comma-separated
    string of globs (or a list of globs). Recursive `**` is honored."""
    if isinstance(input_globs, str):
        input_globs = [g.strip() for g in input_globs.split(",") if g.strip()]
    out = set()
    for g in input_globs:
        for p in glob.glob(g, recursive=True):
            if os.path.isfile(p):
                out.add(p)
    return sorted(out)


def load_done_ids(csv_path, id_field):
    """Return the set of id values already present in the output CSV, so reruns
    skip finished files. Empty set if the CSV does not exist yet."""
    if not os.path.exists(csv_path):
        return set()
    done = set()
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get(id_field):
                done.add(r[id_field])
    return done


def extract_json(text):
    """Pull a JSON object out of model output: strip a code fence if present,
    then take the substring from the first '{' to the last '}'."""
    if text is None:
        raise ValueError("empty model output")
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"no JSON object found in model output: {text[:200]!r}")
    return json.loads(s[start:end + 1])


def validate_row(row, spec):
    """Coerce out-of-list categorical values to 'other' and record each as a
    violation. Only fields that appear in spec['allowed_values'] are checked.
    A list field is validated element by element; a bare string in a list field
    is normalized to a one-element list first."""
    allowed = spec.get("allowed_values", {})
    list_fields = set(spec.get("list_fields", []))
    violations = []
    for field, allowed_list in allowed.items():
        allowed_set = set(allowed_list)
        val = row.get(field)
        if field in list_fields:
            if isinstance(val, list):
                items = val
            elif val in (None, ""):
                items = []
            else:
                items = [val]
            coerced = []
            for item in items:
                if item in allowed_set:
                    coerced.append(item)
                else:
                    coerced.append("other")
                    violations.append(f"{field}={item}")
            row[field] = coerced
        else:
            if val not in allowed_set:
                violations.append(f"{field}={val}")
                row[field] = "other"
    return row, violations


def count_words(text):
    return len(text.split())


def count_sentences(text):
    return len([s for s in re.split(r"[.!?]+", text) if s.strip()])


def avg_sentence_len(text):
    s = count_sentences(text)
    w = count_words(text)
    return round(w / s, 1) if s else 0.0


def count_exclaims(text):
    return text.count("!")


def count_questions(text):
    return text.count("?")


def count_caps_words(text):
    return len(re.findall(r"\b[A-Z]{2,}\b", text))


# Registry of deterministic, text-derived fields. Specs reference these by name
# so word counts and sentence stats are computed, never guessed by the model.
COMPUTERS = {
    "words": count_words,
    "sentences": count_sentences,
    "avg_sentence_len": avg_sentence_len,
    "exclaims": count_exclaims,
    "questions": count_questions,
    "caps_words": count_caps_words,
}


def build_fieldnames(spec, const):
    """Column order for the output CSV: id, model columns, computed fields,
    constant columns (sorted for determinism), then schema_violations."""
    fields = [spec["id_field"]]
    fields += list(spec.get("columns", []))
    fields += list(spec.get("computed_fields", {}).keys())
    fields += sorted(const.keys())
    fields += ["schema_violations"]
    return fields


def serialize_row(row, spec, fieldnames):
    """Turn a row dict into CSV-ready values: list fields are joined with '; '."""
    list_fields = set(spec.get("list_fields", []))
    out = {}
    for k in fieldnames:
        v = row.get(k, "")
        if k in list_fields and isinstance(v, list):
            out[k] = "; ".join(str(x) for x in v)
        elif v is None:
            out[k] = ""
        else:
            out[k] = v
    return out


def append_row(csv_path, row, fieldnames):
    """Append one row, writing the header first if the file is new."""
    exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def reconcile(input_globs, csv_path, errors_path, id_field):
    """Coverage check computed from the CURRENT file set (not a raw row count),
    so it is correct even when several passes share one CSV. reconciled=True
    means: every file in this run's globs has a row, no two files collide on the
    same id, and this run logged no errors.

    Caveat (known, low probability): ids are filename stems. A file deleted and
    later replaced across separate runs by a DIFFERENT file that reuses the same
    stem can be skipped (its stem is already in the CSV) and still reconcile
    true. Future hardening: path-relative or content-hash ids."""
    files = enumerate_files(input_globs)
    expected_ids = [file_id(p) for p in files]
    unique_expected = set(expected_ids)
    covered = load_done_ids(csv_path, id_field)      # all ids present in the CSV
    covered_here = covered & unique_expected          # rows for THIS run's files
    missing = sorted(unique_expected - covered)
    seen, dupes = set(), set()
    for i in expected_ids:
        if i in seen:
            dupes.add(i)
        seen.add(i)
    duplicate_ids = sorted(dupes)
    n_errors = 0
    if os.path.exists(errors_path):
        with open(errors_path, encoding="utf-8") as fh:
            n_errors = sum(1 for line in fh if line.strip())
    return {
        "files": len(files),
        "rows": len(covered_here),
        "errors": n_errors,
        "missing": missing,
        "duplicate_ids": duplicate_ids,
        "accounted": not missing and not duplicate_ids,
        "reconciled": not missing and not duplicate_ids and n_errors == 0,
    }


def audit_sample(csv_path, n, id_field, seed=None):
    """Return up to n random rows for a human or second-pass spot-check."""
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if seed is not None:
        random.seed(seed)
    return random.sample(rows, min(n, len(rows)))


def build_prompt(spec, file_text, stricter=False):
    """Assemble the per-file extraction prompt. In stricter mode (the retry),
    the allowed values are spelled out so the model stops going out of list."""
    parts = [spec["system_prompt"]]
    if stricter and spec.get("allowed_values"):
        parts.append(
            "STRICT: for the fields below, choose ONLY from the allowed values. "
            "Any value not in the list is invalid and will be rejected:"
        )
        for field, allowed_list in spec["allowed_values"].items():
            parts.append(f"- {field}: {', '.join(allowed_list)}")
    parts.append(
        "Return ONLY a JSON object with exactly these keys: "
        + ", ".join(spec["columns"])
        + ". No prose, no markdown fence."
    )
    parts.append("---- CONTENT START ----")
    parts.append(file_text)
    parts.append("---- CONTENT END ----")
    return "\n\n".join(parts)


def file_id(path):
    return os.path.splitext(os.path.basename(path))[0]


def read_file_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def call_model(prompt, model):
    """Transport: one `claude -p --model <model>` call, prompt on stdin."""
    result = subprocess.run(
        ["claude", "-p", "--model", model],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr.strip()[:500]}")
    return result.stdout


def _extract_once(text, spec, model, runner, stricter):
    raw = runner(build_prompt(spec, text, stricter=stricter), model)
    data = extract_json(raw)
    row = {c: data.get(c) for c in spec["columns"]}
    return validate_row(row, spec)


def process_file(path, spec, model, const=None, runner=None):
    """Process one file into one row: model-extract the columns (retry once with
    a stricter prompt if the first result violates the allowed lists), coerce
    leftover violations, add deterministic computed fields and constant columns,
    and stamp the id from the filename stem."""
    const = const or {}
    runner = runner or call_model
    text = read_file_text(path)
    row, violations = _extract_once(text, spec, model, runner, stricter=False)
    if violations:
        row, violations = _extract_once(text, spec, model, runner, stricter=True)
    row["schema_violations"] = "; ".join(violations)
    for field, fn_name in spec.get("computed_fields", {}).items():
        row[field] = COMPUTERS[fn_name](text)
    for k, v in const.items():
        row[k] = v
    row[spec["id_field"]] = file_id(path)
    return row


def run(input_globs, spec, csv_path, errors_path, model, const=None, runner=None, progress=print):
    """Process every not-yet-done file, append one row each, log failures, and
    return the reconcile summary. Resumable and failure-tolerant by design."""
    const = const or {}
    runner = runner or call_model
    files = enumerate_files(input_globs)
    done = load_done_ids(csv_path, spec["id_field"])
    fieldnames = build_fieldnames(spec, const)
    # Fresh error log each run: a file that failed before but now succeeds (has a
    # row) must be able to reach reconciled=True. The skip set comes from the CSV,
    # never from this log, so clearing it loses no state.
    open(errors_path, "w", encoding="utf-8").close()
    for path in files:
        fid = file_id(path)
        if fid in done:
            progress(f"skip   {fid} (already done)")
            continue
        try:
            row = process_file(path, spec, model, const=const, runner=runner)
            append_row(csv_path, serialize_row(row, spec, fieldnames), fieldnames)
            v = row.get("schema_violations", "")
            progress(f"ok     {fid}" + (f"  [violations: {v}]" if v else ""))
        except Exception as e:
            with open(errors_path, "a", encoding="utf-8") as fh:
                fh.write(f"{fid}\t{type(e).__name__}: {str(e)[:300]}\n")
            progress(f"ERROR  {fid}: {type(e).__name__}: {str(e)[:120]}")
    summary = reconcile(input_globs, csv_path, errors_path, spec["id_field"])
    progress(
        f"RECONCILE files={summary['files']} rows={summary['rows']} "
        f"errors={summary['errors']} reconciled={summary['reconciled']}"
    )
    return summary


def load_spec(spec_path):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    spec.setdefault("id_field", "id")
    spec.setdefault("allowed_values", {})
    spec.setdefault("list_fields", [])
    spec.setdefault("computed_fields", {})
    for fn_name in spec["computed_fields"].values():
        if fn_name not in COMPUTERS:
            raise ValueError(f"unknown computed field function: {fn_name}")
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description="Per-file corpus processor for Content Brain.")
    ap.add_argument("--input", required=True,
                    help="comma-separated globs, e.g. '<vault>/wiki/sources/**/*.md'")
    ap.add_argument("--spec", required=True, help="path to the extraction spec JSON")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--errors", default=None, help="errors log path (default: <out>.errors.log)")
    ap.add_argument("--model", default="haiku",
                    help="model alias/id for `claude -p --model` (default: haiku)")
    ap.add_argument("--const", action="append", default=[], metavar="KEY=VALUE",
                    help="constant column added to every row; repeatable")
    ap.add_argument("--audit", type=int, default=0,
                    help="print N random rows after the run for a human spot-check")
    args = ap.parse_args(argv)

    spec = load_spec(args.spec)
    errors_path = args.errors or (args.out + ".errors.log")
    const = {}
    for item in args.const:
        if "=" not in item:
            ap.error(f"--const must be KEY=VALUE, got: {item}")
        k, v = item.split("=", 1)
        const[k] = v

    summary = run(args.input, spec, args.out, errors_path, args.model, const=const)

    audited = 0
    if args.audit > 0:
        sample = audit_sample(args.out, args.audit, spec["id_field"])
        audited = len(sample)
        print("\nAUDIT SAMPLE (verify these rows against their source files):")
        for r in sample:
            print(json.dumps(r, ensure_ascii=False))

    pct = round(100 * audited / summary["files"]) if summary["files"] else 0
    print(
        f"\nCOVERAGE: {summary['rows']}/{summary['files']} files processed, "
        f"{summary['errors']} errors, audited {audited} ({pct}%)."
    )
    return 0 if summary["reconciled"] else 1


if __name__ == "__main__":
    sys.exit(main())
