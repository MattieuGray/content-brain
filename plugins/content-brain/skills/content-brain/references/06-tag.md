# Phase 6: Tag

Purpose: connect every piece of content to the member's own frameworks, so the vault becomes one navigable graph instead of a pile of files. When this is done, they can click a pillar and see everything they've ever made about it.

This phase touches **every** source and transcript note, and a real library can be hundreds or thousands of them. That is far more than you can honestly hold in one conversation. So you do **not** read them all yourself and tag from memory. You build a work-list on disk, fan the reading out to subagents, and then **recount from disk** to prove nothing was skipped.

> Read the "Completeness doctrine" section in `SKILL.md` before you start. The one rule that matters: coverage is counted from disk, never claimed from memory. A file is done only when its note carries the `cb_tagged: true` marker, and this phase is done only when the PENDING count is zero.

## 1. Load their pillars and concept notes

Read the member's pillars from `state.json` (`interview.pillars`), and open their concept notes in `wiki/concepts/`. These pillars are the tag vocabulary, the whole point is to connect content back to *their* frameworks, not any generic scheme. This vocabulary is small; keep it in hand to pass to every worker.

## 2. Build the deterministic work-list

Enumerate every note and its tag status straight from disk:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/list_notes.sh "<vault>/wiki/sources" cb_tagged
```

Each line is `DONE\t<path>` or `PENDING\t<path>`. Count them. Tell the member the real numbers before you start, e.g. *"You've got 214 notes to tag. Let's get through them."* The `DONE` lines are already tagged from a previous run, skip them, this is what makes the phase resumable.

## 3. Fan the tagging out to subagents

Split the PENDING list into **batches of 5–10 notes** (fewer if the transcripts are very long). Launch a subagent per batch (the Task tool). Do several in parallel, but keep batches small enough that each worker reads every file in its batch **in full** without straining its own context, that is the whole point of fanning out.

Give each worker exactly this job, with the pillar list and its batch of file paths spelled out:

> You are tagging a batch of content notes against a fixed set of pillars: **[paste the pillar names + a one-line gloss each]**. For **each** file path below, do all of this:
> 1. **Read the entire note.** Never skim, never sample, never tag from the title alone.
> 2. Decide which **1 to 3 pillars** it genuinely belongs to. Add them to the note's frontmatter as `tags: [pillar-a, pillar-b]`. If it fits **no** pillar cleanly, assign none, an honest empty is better than a forced tag.
> 3. Add a **few free keywords** drawn from the actual content, real topics, names, and terms that appear in the piece.
> 4. Add a **wikilink** in the body to each pillar you assigned, e.g. `[[<Pillar>]]`, so Obsidian's graph draws the connection.
> 5. Whatever you decided, write `cb_tagged: true` into the note's frontmatter. Write it **even when you assigned zero pillars**, so this note is never re-processed.
> 6. **Never invent.** Only tag what the text actually supports. Do not fabricate topics or names.
>
> Return one compact line per file: `<filename> -> [pillars]` (or `-> none`). Nothing else, do not paste the transcripts back.

The worker edits the files itself. You only collect its short report.

## 4. Recount, and loop until zero PENDING

When a wave of workers returns, **run the work-list again**:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/list_notes.sh "<vault>/wiki/sources" cb_tagged
```

- If any `PENDING` remain, dispatch another wave over just those. Repeat.
- If a specific note fails twice (a worker errors or can't write it), stop retrying it, set it aside, and **list it by name** for the member. A named failure is honest; a silent skip is not.

Do not move on until PENDING is zero or every remaining PENDING is a named, reported failure. **This recount is the guarantee.** Never tell the member "everything's tagged" off your own sense of having done a lot, only off a real zero from `list_notes.sh`.

## 5. Mark notable moments in long transcripts (optional)

You can fold this into the same workers if you like: for a long transcript, the worker may add a short list of **3 to 6 notable moments**, a rough timestamp and a one-line description each, but only where the transcript clearly supports it. **Do not fabricate** moments, quotes, or timestamps. If the transcript doesn't clearly show it, leave it out.

## 6. Update the concept notes

For each concept note in `wiki/concepts/`, add a short summary or a backlinks-style list of what content now supports it, which videos, articles, and episodes touch that pillar. You can build this from the tags you just wrote (grep the frontmatter, or read Obsidian's backlinks) rather than re-reading every transcript, a short human summary at the top makes each pillar note a real hub.

## 7. Refresh the index and log

- Update `index.md` so it maps their sources by pillar, a reader should be able to scan it and see what they've made under each theme.
- Append a short progress line to `log.md`.

## When this phase is done

1. Confirm the final counts from a clean `list_notes.sh` run: total notes, how many carry pillars, how many were honestly left untagged, and any named failures.
2. Update `<vault>/.content-brain/state.json`: set `phases.tag` to
   `{ "done": true, "at": "<ISO timestamp now>", "notes": "<counts from the recount, e.g. '214 notes, 198 tagged across 5 pillars, 16 left untagged, 0 failed'>" }`.
   The counts must be the ones the recount actually produced, not an estimate.
3. Load `references/07-voice-dna.md` and begin Phase 7.
