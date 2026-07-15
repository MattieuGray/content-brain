# Phase 7: Voice DNA

**Purpose:** distill how this person actually sounds into a small set of durable notes, so every future word can be checked against their real voice instead of a generic one. This is the centerpiece of the whole build.

You now have their corpus ingested, transcribed, and tagged. That corpus is the evidence. **Never invent a trait, phrase, or example that the corpus does not actually show.** If the evidence is thin somewhere, say so and build only what's supported.

## Why this phase fans out too

Voice is different from tagging. Tagging is per-file. Voice is a **pattern across the whole corpus**, a recurring phrase, a typical sentence length, a real words-per-minute number. You cannot see those patterns by reading a sample, and you cannot honestly read every transcript into one conversation. So this phase runs in two stages:

1. **Extract (fan out).** A subagent reads each piece in full and returns a small, structured *evidence digest*, counts, quotable lines, sentence stats, WPM inputs. Every file is genuinely read, by a worker with a fresh context.
2. **Synthesize (you).** You read the digests, not the raw corpus, and draft the voice notes from them. The digests are small, so you can hold **all** of them at once and actually see the cross-corpus patterns.

This is what keeps the voice honest: it's built from evidence extracted out of every file, not from an impression of the few you happened to read.

> Same doctrine as Phase 6 (see `SKILL.md`): count the corpus from disk, extract a digest per file, and don't synthesize until the digest count matches the file count. Store digests under `<vault>/.content-brain/voice-evidence/` so the extract stage is resumable, skip any file that already has a digest.

You are producing up to **four** cross-linked notes in `wiki/voice/`:

1. **Brand Voice DNA**, how the business sounds
2. **Personal Voice DNA**, how the person sounds as themselves (only if they told you these differ)
3. **Written Voice**, how they write (mined from their text)
4. **Spoken Voice**, how they talk (mined from their transcripts), a genuinely different instrument

Written and spoken are kept separate on purpose. People do not write the way they talk. Capture both truthfully.

Tell them up front, warmly: *"This is the part that makes everything sound like you and not like a robot. I'm going to read back through everything you've made, pull out how you actually write and how you actually talk, and then check it with you."*

---

## Step 1: Written Voice

**Enumerate the text corpus** from disk: everything under `wiki/sources/articles/`, `wiki/sources/books/`, and any extracted documents (their real, self-written prose, not transcripts). Count the files.

**Extract (fan out).** Batch the files (5–10 per worker) and launch a subagent per batch. Skip any file that already has a digest in `.content-brain/voice-evidence/written/`. Give each worker this job:

> Read each file below **in full**. For each, write a JSON digest to `<vault>/.content-brain/voice-evidence/written/<stem>.json` capturing, **only from the actual text**:
> - typical sentence length and how much it varies (a rough word count per sentence is fine);
> - how pieces open, build, and close (story / claim / question / number?);
> - punctuation habits actually observed (lists, dashes, parentheticals, one-line paragraphs, ALL CAPS emphasis);
> - transition words they reach for ("Here's the thing", "But", "So", "Look");
> - vocabulary register (plain vs technical, formal vs casual);
> - recurring rhetorical moves (the reveal, the contrast, the confession, direct address, rule-of-three);
> - **6–10 verbatim quoted lines** pulled exactly from the text, each with the source note's `[[wikilink]]`.
> Never invent. If the file is thin, return a thin digest. Reply only with the path you wrote.

**Synthesize (you).** Read **all** the written digests. Now the patterns are visible across the whole body of writing. Draft `wiki/voice/Written Voice.md` with frontmatter `type: voice` and a section per trait above, each backed by **8–12 real quoted lines** carried straight from the digests (keep the `[[wikilink]]` citations). The quotes are the proof, they matter more than your adjectives.

**Walk them through it.** Show the headline findings and 3–4 example quotes. Ask: *"Does this feel like how you write? Anything I've overstated or missed?"* Fold in their corrections.

If there is little or no written content, say so plainly, Written Voice is light for now and will grow as they add writing.

---

## Step 2: Spoken Voice

**Enumerate the transcripts** under `wiki/sources/transcripts/` from disk. Count them.

**Extract (fan out).** Batch and dispatch as above, skipping any transcript that already has a digest in `.content-brain/voice-evidence/spoken/`. Each worker, for each transcript:

> Read the transcript **in full**. Compute its word count (`wc -w`) and find its media duration (the YouTube `.info.json` `duration` field, or `ffprobe -v quiet -show_entries format=duration -of csv=p=0 "<media>"` in seconds). Write a JSON digest to `<vault>/.content-brain/voice-evidence/spoken/<stem>.json` with:
> - `words`, `duration_seconds`, and `wpm` = words ÷ (seconds ÷ 60) when duration is known;
> - signature openers (how they start an answer);
> - recurring phrases and verbal tics with a **count** of how often each appears in this transcript;
> - natural filler words and rhythm notes;
> - how they walk to a point (set up a number and pay it off? mini-story then lesson? ask then answer?);
> - **6–10 verbatim quoted phrases**, each with the source `[[wikilink]]`.
> Never invent phrases or counts. Reply only with the path you wrote.

**Synthesize (you).** Read all the spoken digests.
- **WPM**: average the real `wpm` values across the pieces that had a duration, and report a typical **range** (e.g. "about 165–180 wpm"). Never guess a number, if no durations were available, say WPM couldn't be measured.
- **Recurring phrases**: sum each phrase's counts **across** digests, so "'ask me how I know' appears 14 times" is a real corpus-wide total, not one transcript's.
- Draft `wiki/voice/Spoken Voice.md` (`type: voice`) with the WPM figure up top, then each section backed by verbatim phrases from the digests, noting which are frequent vs one-offs.

**Walk them through it.** Play back the standout findings, the WPM number and their top signature phrases usually land well. *"These are the phrases you actually reach for out loud, sound right? Any you'd never want in your name?"* Fold in corrections.

If there is no audio/video, say so and skip Spoken Voice for now, it can be built later once they have recordings.

---

## Step 3: Brand Voice DNA

This is how the **business** sounds in public. This one is a synthesis, not a fan-out, build it from the written and spoken digests you already gathered plus the interview profile (`interview.profile`, `interview.pillars` in state.json).

**Draft** `wiki/voice/Brand Voice DNA.md` (`type: voice`) covering:
- **Positioning**, who they help and what they stand for, in a line.
- **Audience**, who they're talking to.
- **Core messages**, the handful of things the brand says over and over (tie each to a [[pillar]] concept note where relevant).
- **Signature vocabulary**, the words and phrases that are theirs; the words they avoid.
- **Tone**, 3–5 adjectives, each with a real example from the digests.
- **Do / Don't**, concrete guardrails drawn from how they actually show up (e.g. "Do lead with a real number. Don't use hype adjectives.").

Keep every claim grounded in real examples. **Walk them through it** and let them sharpen the do/don't list, that's the part they'll have the strongest opinions on.

---

## Step 4: Personal Voice DNA (conditional)

**Only build this if** `interview.personal_voice_differs` is true. If their personal and brand voice are the same, skip it and say so, one honest Brand Voice note is better than two padded ones.

If they differ, draft `wiki/voice/Personal Voice DNA.md` (`type: voice`) describing how they sound as *themselves*, the looser, off-brand, this-is-just-me register, drawn mostly from casual spoken moments and any personal writing in the digests. Contrast it explicitly with the brand voice ("Brand is X; personally they're more Y"). Walk them through it.

---

## Step 5: Wire it together

- Cross-link the four notes to each other and link each from `index.md` under the Voice section (the starter `index.md` already lists them).
- Add a one-line pointer in `Home.md` to the Voice set.
- Make sure every voice trait that cites the corpus uses a real [[wikilink]] to the source note, so a reader can click straight to the evidence.

---

## When this phase is done

1. Confirm coverage: the number of digests in each `voice-evidence/` folder matches the number of files in the corresponding corpus folder. If they don't match, some files went unread, extract the stragglers before finalizing. State how many pieces the voice was built from.
2. Update `<vault>/.content-brain/state.json`: set `phases.voice_dna` to `{ "done": true, "at": "<ISO>", "notes": "built: written, spoken, brand[, personal]; from <n> written + <m> spoken pieces; wpm ~<range>" }`. Note which of the four you built and which you skipped and why.
3. Then load `references/08-handoff.md` and begin the final phase.
