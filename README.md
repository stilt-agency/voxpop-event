# voxpop-event

A Claude Code skill for building branded vertical vox pop compilations from a
folder of event interview footage, for any client.

A folder of on-the-floor interviews becomes a set of 9:16 programmes with
question splash cards in place of the interviewer's audible lead-in, grouped
soundbites, b-roll between chapters, name plates, burned-in captions, a music
bed and an outro. Each programme is delivered in four overlay treatments.

The pipeline is fixed. Everything that changes between clients lives in one
`project.json`, written by the intake at the start of a job.

## Install

Put the `voxpop-event` folder inside your skills directory:

| | |
|---|---|
| Windows | `C:\Users\<you>\.claude\skills\voxpop-event` |
| macOS, Linux | `~/.claude/skills/voxpop-event` |

```bash
git clone https://github.com/stilt-agency/voxpop-event.git ~/.claude/skills/voxpop-event
```

Skills hot-reload, so it is available straight away. Ask Claude Code to start
a vox pop job and it will run the intake first.

## Requirements

- ffmpeg and ffprobe
- [Faster-Whisper-XXL](https://github.com/Purfview/whisper-standalone-win)
  with the `large-v2` and `large-v3` models
- Python 3.10+ with `pillow`, `fonttools`, `pymupdf`, `numpy`
- A third transcript source for the caption cross-check: Descript, or a
  client-supplied reference transcript
- Per client: the licensed font family, logo in positive and reverse vector
  cuts, an animated background loop, and a music bed

Tool paths are set per machine in `project.json`.

## How a job runs

1. **Intake.** `reference/intake.md`, six rounds of questions. Answers go into
   `project.json`; anything unanswered becomes an open item with an owner.
   `python brandkit.py` is the gate: it reports missing assets and open items.
2. **Transcripts.** Whisper large-v2 and large-v3 on every clip, plus one
   independent read, merged by anchor-and-vote. Two Whisper models agreeing
   with each other counts for nothing: they share failure modes.
3. **Selection.** Read the transcripts, choose the soundbites, build
   `bites.json` and `speakers.json`. This is the editorial work and is not
   automated.
4. **Cards and overlays.** Question, title and end cards, the animated opener,
   name plates and caption PNGs.
5. **Check.** `caption_crosscheck.py` aligns every caption word back against
   all three reads and lists anything none of them supports, plus the words to
   confirm with the client.
6. **Build.** Every programme in every treatment.

## What is in here

| path | |
|---|---|
| `SKILL.md` | the workflow and the non-negotiable rules |
| `reference/intake.md` | the question set, in the order to ask it |
| `reference/captions.md` | the three-read cross-check, and what it has caught |
| `reference/gotchas.md` | traps, each with the measurement that proves it |
| `reference/method.md` | bite selection, treatments, audio chain |
| `scripts/` | the pipeline |
| `scripts/project.example.json` | the config the intake fills in |

Built and proven on live event deliveries. The gotchas each cost a rebuild to
find, which is why they are written down.
