# Phase 6: Tag

Purpose: connect every piece of content to the member's own frameworks, so the vault becomes one navigable graph instead of a pile of files. When this is done, they can click a pillar and see everything they have ever made about it.

This phase does NOT read the corpus in this session and generalize from a sample. It processes every note one at a time through a small engine, writes one row per note to a table, and refuses to move on until the table reconciles against the folder. That is what lets us honestly say "every note was tagged," not "a sample was."

## 1. Load their pillars and concept notes

Read the member's pillars from `<vault>/.content-brain/state.json` (`interview.pillars`), and open their concept notes in `wiki/concepts/`. These pillars are the tag vocabulary. The whole point is to connect content back to their frameworks, not any generic scheme.

## 2. Build the per-run tag spec

The engine reads a small JSON spec. A template ships with the skill; fill in this member's real pillars so the engine only ever tags with their vocabulary:

```
TEMPLATE="${CLAUDE_PLUGIN_ROOT}/scripts/specs/tag_spec.template.json"
STATE="<vault>/.content-brain/state.json"
SPEC="<vault>/.content-brain/tag_spec.json"
python3 -c "import json,sys; t=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2])); t['allowed_values']['pillars']=s['interview']['pillars']; json.dump(t, open(sys.argv[3],'w'), indent=2)" "$TEMPLATE" "$STATE" "$SPEC"
```

Open `$SPEC` and confirm `allowed_values.pillars` is exactly their pillar list.

## 3. Tag every source and transcript note (one reconciled pass)

Run the engine over every markdown note under `wiki/sources/` (this includes the transcript notes in `wiki/sources/transcripts/`). It processes one note per model call, skips notes already in the table (resumable), and writes one row per note:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/corpus_pass.py" \
  --input "<vault>/wiki/sources/**/*.md" \
  --spec "<vault>/.content-brain/tag_spec.json" \
  --out "<vault>/.content-brain/tags.csv" \
  --model haiku \
  --audit 10
```

`haiku` is the fast, cheap default and is the right model for this high-volume pass. The run prints one line per note, then a `RECONCILE` line and a `COVERAGE:` line. `--model` also accepts `sonnet`, `opus`, or a full model id if the member wants a stronger read.

**Reconcile gate (do not skip).** The run must end with `reconciled=True`: files processed equals rows written, zero errors. If it does not:
- Look at `<vault>/.content-brain/tags.csv.errors.log` for the notes that failed.
- Re-run the exact same command. It is resumable and only retries the missing notes.
- Only once `reconciled=True` do you continue. Never tell the member "everything is tagged" from a run that did not reconcile.

## 4. Audit a random sample

The `--audit 10` flag printed 10 random rows. Open the actual note for a few of them and check the row against the real content: are the pillars ones the note genuinely supports, are the keywords really in the text, is the summary accurate? If a couple are wrong in the same way, the spec wording is the likely cause. Tighten the `system_prompt` in `$SPEC`, delete `tags.csv`, and re-run step 3. Do not apply tags from a table you have not spot-checked.

## 5. Apply the tags to each note

Now the table is trustworthy. Work straight from `<vault>/.content-brain/tags.csv`, not from memory or a re-read. For each row (matched to its note by the `note_id` stem):

- Read the row's `pillars` (a `; `-separated list). Drop any entry equal to `other` or empty. What remains are the supported pillars.
- If one or more pillars remain, set the note's frontmatter `tags:` to those pillars in inline-list form, for example `tags: [Owner Financing, Exits]`, and add a `[[<Pillar>]]` wikilink near the top of the note body for each, so Obsidian's graph draws the connection.
- Fold the row's `keywords` into the frontmatter as a `keywords:` field.
- If no pillars remain, leave the note honestly untagged. Never force a pillar the content does not support.

Because you are driving this from the reconciled table, every note is accounted for: there is no note you "did not get to."

## 6. Mark notable moments in long transcripts (optional)

For long transcripts, you may add a short list of 3 to 6 notable moments, a rough timestamp and a one-line description each, but only where the transcript clearly supports it. Do not fabricate moments, quotes, or timestamps. If the transcript does not clearly show it, do not list it.

## 7. Update the concept notes, index, and log

- For each concept note in `wiki/concepts/`, add a short summary or backlinks-style list of the content that now supports it. A short human summary at the top makes each pillar note a real hub.
- Update `index.md` so it maps their sources by pillar.
- Append a short progress line to `log.md`.

## 8. Surface the coverage report

Show the member the honest coverage line, filled in with the real numbers, for example:
> "164 of 164 notes tagged across 5 pillars, 0 errors, audited 10. Every note was read individually, not skimmed."

This is the promise this phase now keeps: full coverage you can prove, not a sample you hope is representative.

## When this phase is done

1. Update `<vault>/.content-brain/state.json`: set `phases.tag` to `{ "done": true, "at": "<ISO timestamp now>", "notes": "<coverage line, e.g. '164/164 notes tagged, 0 errors, audited 10, 5 pillars'>" }`.
2. Load `references/07-voice-dna.md` and begin Phase 7.
