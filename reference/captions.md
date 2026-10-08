# Captions: three reads, cross-checked

Captions are the most-read thing you deliver and the easiest to get quietly
wrong. One transcription engine is not enough: Whisper invents phrases, drops
sentences, and is confidently wrong on product names.

## The three reads

| read | role |
|---|---|
| Faster-Whisper **large-v2** | timing backbone: its word times overlap least |
| Faster-Whisper **large-v3** | second opinion; better wording, looser timing |
| **Descript** (or a client reference transcript) | the independent read |

```bash
<whisper> <clip>.wav --model large-v2 -wt True --output_format json \
    --output_dir asr/v2 --device cuda --compute_type float16 --language en
<whisper> <clip>.wav --model large-v3 ... --output_dir asr/v3
# Descript: import_media (direct upload), then export_transcript as txt with
# paragraph timecodes, saved to asr/descript/<clip>.txt
python transcripts_merge.py <clip> asr/v2/<clip>.json asr/v3/<clip>.json \
    asr/descript/<clip>.txt merged/
```

`transcripts_merge.py` anchors on words all three agree on, then takes a
majority vote on each disputed window, flagging windows with no majority into
`<clip>.review.tsv`. Pass **v2 first**: that slot is the timing backbone.

## The rule that matters

**Two Whisper models agreeing with each other is worth nothing.** They share
failure modes and will agree confidently on SIEM as "SIM", Claude as "cloud",
AppSec as "app", SOC as "sock". Treat a reading as settled only when the
non-Whisper source agrees with at least one Whisper pass. On one delivery that
rule rejected 132 candidates and kept 48.

## After the merge, always

1. **Read every `no majority` row** and decide it yourself from context. Never
   let the vote pick silently in these.
2. **Run `caption_crosscheck.py`.** It aligns the final caption words against
   all three sources and lists any run of words that none of them contains.
   That is what catches a splice or an invented phrase. It also lists words
   both Whisper models marked low confidence, which is the "to confirm" list.
3. **Send the user the list with timecodes** before rendering the captioned
   files, as the intake agreed. Lock the answers into the project's fix list.

## Things that have actually gone wrong

- **An invented phrase spliced mid-sentence.** large-v3 heard "token spend is
  important. So, I think the value is" inside "token spend is increasing". The
  vote took it because it was the medoid of three disagreeing readings. Only
  the cross-check against all three sources caught it.
- **Word order shuffled.** A reading timed by spreading it across a gap, then
  sorted by time, interleaved with its neighbours: "say yes you when know the
  CRO". Keep the vote's emission order; clamp timings forward instead of
  re-sorting. Fixed in `transcripts_merge.py`.
- **Product names.** Both Whispers heard "cloud" three times where the speaker
  said "Claude", next to ChatGPT and Perplexity in the same sentence. Only the
  third source had it right.
- **Never swap one word inside a multi-word difference.** "If you send" against
  "need to send" gives If→Need on its own, which produces "Need you send". Fix
  the whole phrase or leave it for review.
- **A cut mid-sentence leaves a lowercase opening word.** Capitalise the first
  word of a bite's first cue.
- **Caption plate height must come from the font's ink bounds**, not fixed
  offsets around the text origin. PIL's default anchor is the ascender, so
  fixed offsets leave a gap above and clip descenders below. See
  `gotchas.md`.
- **Cue overlap.** Clamp each cue's end against the next cue's displayed start,
  or two plates stack on screen.

## Spelling and equivalences

realise/realize, colour/color, OK/Okay are style, not errors: set the
convention once in `project.json` and let the build apply it. Keep a per-client
list of product names and agreed wording; the automated rules will happily
revert a decision the client already made.
