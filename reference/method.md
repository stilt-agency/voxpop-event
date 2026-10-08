# Method

## Data files you hand-build

Two JSON files drive everything. Neither can be generated reliably; they are
the editorial work.

**`bites.json`** — the soundbites, chosen by reading the transcripts.

```json
{"bites": [
  {"id": "b01", "clip": "P1022940", "q": "q1", "start": 31.2, "end": 44.8}
]}
```

One entry per usable answer: which clip, which question it answers, and the in
and out points in source seconds. `dump_segments.py` prints transcripts with
timings to choose from; `find_words.py` locates a phrase.

**`speakers.json`** — clip stem → `{name, title, company}`. Only clips with a
name get a lower third. Verify spelling against something authoritative, not
what you heard.

Also needed: a crop centre per bite (0–1 across the frame) so each speaker is
centred in the 9:16 slice. `make_castsheet.py` renders a sheet to set these by
eye.

## Programmes

`programmes.py` lists what gets built. Each is a sequence of elements:

```python
("opener",)            animated client logo
("card", stem, dur)    a still card held for dur seconds
("bite", id)           a soundbite
("broll", id)          a b-roll shot
("outro",)             producer logo reveal
```

Typical set: one long cut, a short teaser, per-speaker solo cuts, and themed
cuts grouping one question across speakers. Every programme renders in all four
treatments, so 13 programmes is 52 files.

## Treatments

| suffix | plates | captions |
|---|---|---|
| *(none)* | no | no |
| `-LOWERTHIRDS` | yes | no |
| `-CAPTIONS` | no | yes |
| `-LOWERTHIRDS-CAPTIONS` | yes | yes |

Four *burns* rather than three, because the with-both treatment needs captions
at a constant height even on shots carrying no plate. See `gotchas.md`.

Vertical placement:

```
captions only     caption block bottom at y 1450
plate only        plate at y 1400
both              captions bottom at y 1300, plate at y 1430
```

## Captions

Cues break on sentence punctuation, or 52 characters, or 9 words, or 3.2
seconds, or a clause break past 20 characters. Rounded black pills behind each
line for legibility over busy footage. A stray one-word tail folds into the
previous cue.

## Audio

- Flat per-clip gain to −16 LUFS. Not dynamic normalisation.
- Music bed looped to length, levelled to about −19 LUFS, then sidechain-ducked
  against the speech sum.
- Short edge fades on every speech segment to kill join clicks.
- AAC 192k 48 kHz stereo.

## Video

1080×1920. Crop a 1215px slice from a 3840×2160 frame and scale with Lanczos —
`crop_w` in `brand.json` if the camera differs. Keep the source frame rate.

H.264 High CRF 18, yuv420p, SAR 1:1 / DAR 9:16, faststart.

## Scripts

**Production**
`brandkit.py` brand config · `brandtext.py` type with glyph fallback ·
`make_cards.py` title, question, end cards · `make_opener.py` animated logo
opener · `make_overlays.py` plates and caption PNGs · `programmes.py` what to
build · `build.py` renderer

**Prep and inspection**
`scan_broll.py` sort interviews from b-roll · `make_castsheet.py` who is in
which clip, and crop centres · `make_brollsheet.py` b-roll contact sheets ·
`dump_segments.py` transcripts with timings · `find_words.py` locate a phrase ·
`check_edges.py` inspect cut boundaries

## Delivering

Filenames: `<Client>-<Event>-VoxPop-9x16-<PROGRAMME><-TREATMENT>.mp4`, no
spaces, no version suffix on the handover copies.

Write a README into the output folder: what was built, what the treatments
mean, the source and licence of the music bed, and anything the client
corrected along the way.
