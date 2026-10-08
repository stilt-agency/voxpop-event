---
name: voxpop-event
description: Build branded vertical vox pop compilations for any client from a folder of event interview clips - intake questionnaire, question splash cards instead of the interviewer's audible lead-in, grouped soundbites, b-roll, name plates, cross-checked burned-in captions, music bed and outro, delivered as several programmes in four overlay treatments. Use when the user has event or on-the-floor interview footage to cut into social videos for a client, mentions vox pops, event interview compilations, 9:16 soundbite reels, or asks to set up a new vox pop job for a new client.
---

# Event vox pops, client by client

A repeatable pipeline: a folder of on-the-floor interviews becomes a set of
branded vertical programmes with question cards, grouped soundbites, b-roll,
name plates, captions and a music bed.

The method is fixed. Everything that changes between clients lives in one
`project.json`, written by the intake. Proven across multiple events; the
traps in `reference/gotchas.md` each cost a rebuild to find.

## 1. Intake first, always

**Do not open the footage before this.** Work through
`reference/intake.md` with the user: six rounds, in order. Ask the
multiple-choice ones as multiple choice with the recommended option first, and
ask in batches rather than one at a time.

Two rules while you do it:

- **Write every answer into `project.json` as you go**, including the ones
  that only confirm a default. The next job for this client starts from this
  file.
- **Anything unanswered becomes an `open_items` entry** with an owner and what
  it blocks. Never guess a speaker's job title, a hex value, or whether a
  clip has a release.

Blockers that genuinely stop a build: output path, source footage, the logo's
reverse cut, the licensed font, the question wording, the programme list, the
speaker names and titles for any clip that needs a plate, and the exclusion
list.

```bash
mkdir <project> && cd <project>
cp <skill>/scripts/*.py .
cp <skill>/scripts/project.example.json project.json   # then fill it in
python brandkit.py            # resolves every asset, lists open items
```

`python brandkit.py` is the gate: it prints MISSING against anything that does
not resolve and repeats the open items. Clear it before step 2.

## 2. Pipeline

```bash
python -m pip install pillow fonttools pymupdf numpy    # once

python scan_broll.py              # sort interviews from b-roll, contact sheets
python transcripts_build.py asr   # Whisper large-v2 + large-v3 on every clip
python transcripts_build.py prep  # mono mp3s for the third read
#   upload those, export txt with paragraph timecodes -> asr/descript/<clip>.txt
python transcripts_build.py merge # anchor-and-vote; writes transcripts/*.json
#   read every "no majority" row it prints and decide each one yourself

python make_castsheet.py          # who is in which clip, for the names chase
python dump_segments.py           # read transcripts, choose the soundbites
#   hand-build bites.json and speakers.json from that (reference/method.md)

python make_cards.py              # question, title and end cards
python make_opener.py             # animated logo opener frames
python make_overlays.py           # name plates and caption PNGs
python caption_crosscheck.py      # unsupported runs + the "to confirm" list
#   send that list to the user with timecodes, lock the answers into
#   captions.fixes in project.json, re-run make_overlays.py

python build.py                   # every programme x every treatment
```

`programmes.py` defines what gets built. Budget a few minutes per programme
per treatment, and remember each programme is four files.

## 3. The shape

```
opener        animated client logo over their backdrop
title card    event name, strapline, logo
  question card    flat brand colour, eyebrow, the question
  soundbites       grouped answers from several speakers
  b-roll           between chapters
  ... repeat per question
end card      logo over the backdrop
outro         producer logo reveal
```

## 4. Rules that are not negotiable

**Captions get three reads, cross-checked.** Two Whisper models plus one
independent source, and two Whisper models agreeing with each other counts for
nothing: they share failure modes. `reference/captions.md` has the method and
the failures it has caught.

**One name plate per person per programme**, on their first appearance. Not
once per clip. This was a client correction, stated as a hard rule.

**The eyebrow reads "Question", never "Question Two".** Numbering implies an
order the viewer cannot see once a clip is reshared alone.

**Reverse logo on the brand colour, positive on black or white.** The code
asserts clear space but cannot know the client's variant rules.

**Captions sit at one height for a whole programme.** That is what the
`caphigh` burn is for: captions at the with-plate height on shots carrying no
plate. Without it the caption line jumps whenever a plate appears.

**Lower thirds go below captions, never above.**

**Flat per-clip gain to the target LUFS**, not dynamic normalisation, so
delivery stays natural. The music bed is sidechain-ducked under speech.

**Never sign off a build that reports a font fallback.** It means the supplied
cut is missing glyphs, usually the question mark or apostrophe.

**Version suffixes come off the delivered name.** Keep superseded copies in
`out/_superseded/`, and never delete anything from `out/` without asking.

## 5. Delivery

Each programme in each ratio in each treatment, into `output.dir`. Alongside
them: the SRTs if the intake asked for them, and a short note listing
programmes with runtimes, the speakers and plates used, any wording the client
decided, and anything still open.

When the client comes back with changes, re-cut from `bites.json` and
`programmes.py` rather than trimming the rendered file, and move the files
being replaced into `out/_superseded/` first.

## Reference

- `reference/intake.md` — the question set, in the order to ask it.
- `reference/captions.md` — the three-read cross-check and what it has caught.
- `reference/gotchas.md` — the traps, each with the measurement that proves it.
- `reference/method.md` — bite selection, treatments, audio chain, scripts.
