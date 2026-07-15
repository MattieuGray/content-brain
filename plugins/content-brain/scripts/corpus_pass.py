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
