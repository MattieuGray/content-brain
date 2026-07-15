# Phase 7: Voice DNA

Purpose: distill how this person actually sounds into a small set of durable notes, so every future word can be checked against their real voice instead of a generic one. This is the centerpiece of the whole build.

This phase is done in two stages, on purpose. First a machine pass reads every piece one at a time and writes down the measurable voice features of each, one row per piece, reconciled against the folder. Then you synthesize the Voice DNA notes from that complete feature table. You never form the voice from a skim of a handful of pieces. Never invent a trait, phrase, or example the corpus does not actually show.

You are producing up to four cross-linked notes in `wiki/voice/`:

1. Brand Voice DNA, how the business sounds
2. Personal Voice DNA, how the person sounds as themselves (only if they told you these differ)
3. Written Voice, how they write (mined from their text)
4. Spoken Voice, how they talk (mined from their transcripts), a genuinely different instrument

Written and spoken are kept separate on purpose. People do not write the way they talk.

Tell them up front, warmly: "This is the part that makes everything sound like you and not like a robot. I am going to go through everything you have made, piece by piece, pull out how you actually write and how you actually talk, and then check it with you."

---

## Stage A: extract voice features from every piece (one reconciled pass)

The engine writes one row per piece: deterministic stats (word count, sentence count, average sentence length, exclamation and question counts, capitalized-word count) computed in code, plus model-extracted features (candidate signature phrases with counts, quotable verbatim lines, punctuation habits, register). The numbers are computed, not guessed, so word counts and sentence stats are exact.

Run it twice into the same table, once over their writing and once over their transcripts, tagging each row with its medium.

Written sources:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/corpus_pass.py" \
  --input "<vault>/wiki/sources/articles/**/*.md,<vault>/wiki/sources/books/**/*.md" \
  --spec "${CLAUDE_PLUGIN_ROOT}/scripts/specs/voice_feature_spec.json" \
  --out "<vault>/.content-brain/voice_features.csv" \
  --const medium=written \
  --model haiku
```

Spoken sources (the transcript notes):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/corpus_pass.py" \
  --input "<vault>/wiki/sources/transcripts/**/*.md" \
  --spec "${CLAUDE_PLUGIN_ROOT}/scripts/specs/voice_feature_spec.json" \
  --out "<vault>/.content-brain/voice_features.csv" \
  --const medium=spoken \
  --model haiku \
  --audit 10
```

Both runs append to the same `voice_features.csv` and skip rows already present, so they are resumable and safe to re-run.

**Reconcile gate.** After both runs, confirm coverage over everything that should have a voice row:

```
python3 - <<'PY'
import glob, csv, os
vault = "<vault>"
globs = [f"{vault}/wiki/sources/articles/**/*.md",
         f"{vault}/wiki/sources/books/**/*.md",
         f"{vault}/wiki/sources/transcripts/**/*.md"]
files = sorted({p for g in globs for p in glob.glob(g, recursive=True) if os.path.isfile(p)})
rows = {r["note_id"] for r in csv.DictReader(open(f"{vault}/.content-brain/voice_features.csv"))}
print("files:", len(files), "rows:", len(rows), "reconciled:", len(files) == len(rows))
PY
```

If it does not reconcile, check `voice_features.csv.errors.log`, re-run the matching command (resumable), and only continue once files equals rows. If there is no written content, say so plainly and note Written Voice is light for now; if there are no transcripts, skip Spoken Voice and say so. Honest gaps are fine; a false claim of coverage is not.

**Audit.** Open a few of the rows the `--audit 10` flag printed and check the quotable lines are really verbatim in the source note and the register reads right. Fix the spec wording and re-run if a pattern is clearly wrong.

---

## Stage B: synthesize the four notes from the complete table

Now build the voice notes from `voice_features.csv`, the full feature set, never from a re-read of a few pieces. Quotes you cite must come from the `quotable_lines` and `signature_phrases` of real rows, with a `[[wikilink]]` to that row's source note.

### Written Voice

Filter the table to `medium == written`. From those rows:
- Sentence shape: report the real distribution of `avg_sentence_len` across their writing (typical value and spread), not an impression.
- Punctuation and formatting habits: aggregate the `punctuation_habits` across rows into the patterns that recur.
- Signature phrases and transitions: pull the `signature_phrases` that show up across many rows, with their counts.
- Register and rhetorical moves: summarize from the rows, grounded in examples.

Draft `wiki/voice/Written Voice.md` with frontmatter `type: voice` and a section for each of the above, each backed by 8 to 12 real quoted lines pulled from the `quotable_lines` of specific rows, each cited with a `[[wikilink]]` to its source note. The quotes are the proof.

Walk them through it: show the headline findings and 3 to 4 example quotes. Ask: "Does this feel like how you write? Anything I have overstated or missed?" Fold in corrections. If written content is thin, say so and note Written Voice will grow as they add writing.

### Spoken Voice

Filter the table to `medium == spoken`.

Compute words per minute from real numbers. The table already holds an exact `word_count` per transcript. Pair a handful of representative transcripts with the duration of their media to get a real WPM range:
- Duration: from the YouTube `.info.json` `duration` field, or `ffprobe -v quiet -show_entries format=duration -of csv=p=0 "<media-file>"` (seconds).
- WPM = word_count / (seconds / 60). Do this across several pieces and report the measured range, for example "about 165 to 180 wpm." Never state a WPM you did not compute.

Then, from the spoken rows:
- Signature openers and recurring phrases: the `signature_phrases` that recur across transcripts, with counts (for example "'ask me how I know' appears 14 times").
- Filler and rhythm: from `punctuation_habits` and the sentence stats, describe cadence.
- How they walk to a point, and their spoken register.

Draft `wiki/voice/Spoken Voice.md` (`type: voice`) with the WPM figure up top, then each section backed by verbatim quoted phrases from real transcript rows (`[[wikilink]]` the source). Note which phrases are frequent versus one-offs. Walk them through it and fold in corrections. If there is no audio or video, skip Spoken Voice for now and say it can be built later once they have recordings.

### Brand Voice DNA

This is how the business sounds in public. Synthesize from the feature table and the interview profile (`interview.profile`, `interview.pillars` in state.json). Draft `wiki/voice/Brand Voice DNA.md` (`type: voice`) covering positioning, audience, core messages (tie each to a `[[pillar]]` concept note where relevant), signature vocabulary, tone (3 to 5 adjectives, each with a real example), and a Do and Do-Not list drawn from how they actually show up. Keep every claim grounded in real rows. Walk them through it and let them sharpen the Do and Do-Not list.

### Personal Voice DNA (conditional)

Only build this if `interview.personal_voice_differs` is true. If personal and brand voice are the same, skip it and say so. If they differ, draft `wiki/voice/Personal Voice DNA.md` (`type: voice`) describing how they sound as themselves, drawn mostly from casual spoken rows and any personal writing, contrasted explicitly with the brand voice. Walk them through it.

---

## Wire it together

- Cross-link the four notes to each other and link each from `index.md` under the Voice section.
- Add a one-line pointer in `Home.md` to the Voice set.
- Every voice trait that cites the corpus uses a real `[[wikilink]]` to the source note, so a reader can click straight to the evidence.

## Surface the coverage report

Tell the member the honest coverage line, for example:
> "Read every one of your 164 pieces individually to build this, 118 written and 46 spoken, 0 errors. Your Voice DNA is drawn from all of it, not a sample."

## When this phase is done

Update `<vault>/.content-brain/state.json`: set `phases.voice_dna` to `{ "done": true, "at": "<ISO>", "notes": "built: written, spoken, brand[, personal]; wpm ~<n>; from <N> reconciled pieces" }`. Note which of the four you built and which you skipped and why.

Then load `references/08-handoff.md` and begin the final phase.
