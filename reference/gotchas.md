# Traps, and the measurements that caught them

From a large event build. Each cost a rebuild.

---

## Trial font cuts are not the font

The client's trial release of ES Build mapped **68 glyphs**. No question mark,
no apostrophe, no colon — on a deliverable whose entire premise is question
cards. The licensed desktop family has 477.

`brandtext.py` draws text as runs, choosing the brand face or a fallback per
character, and `report()` says which characters fell through. **Do not sign off
a build that reports any fallback.** Ask for the full licensed desktop family
by name and check what you were sent.

Where a family ships several cuts, match the one the client's own title cards
use rather than assuming the default.

---

## Lower thirds repeating on every cut

The plate is per *person per programme*, not per clip. The first build inserted
one every time a speaker reappeared after a cut, which the client called out as
a hard rule.

A hand-written exception for the one speaker who obviously repeated did not
scale — it broke the moment the programme list grew. `badged_bites()` computes
first-appearance per programme instead.

Knock-on: once some shots carry a plate and some do not, the caption line jumps
height whenever a plate appears. Hence the fourth burn, `caphigh` — captions at
the with-plate height, no plate. Four burns, not three.

---

## A 16:9 logo reveal will not survive a 9:16 crop

The producer's reveal has the logo plus tagline spanning 1578px against a
1215px crop window. Cropping cuts the tagline off.

Scale to fit and pad instead. And if the source blacks are a textured grid
rather than true black, crush them or the padded area reads as a lighter band:

```
lutyuv=y='if(lt(val,48),16,val)'
```

`colorlevels` produced an all-black frame here, and `lumakey`/overlay failed on
a timestamp mismatch. `lutyuv` is the one that worked.

---

## Rasterise vector logos at final size

At 1080 wide, a supplied PNG is usually too small and the wordmark goes soft.
Render the PDF or SVG at the exact pixel width with PyMuPDF. `make_cards.logo()`
accepts a raster if that is all you have, but say so in the README.

---

## Clear space

Guides express the minimum as a fraction of the logo plate height — one client's is
the height of the "e", about 0.48 of the plate. `logo.clear_space_ratio` in
`brand.json` defaults to 0.55 and `place_logo()` asserts it against both edges.

Keep the bottom margin generous regardless, so the logo clears platform UI
overlays on social.

---

## Cut points and joins

Whisper snaps word times to segment edges, so a cut on a raw word boundary
lands exactly on the speech onset and clips the attack. Handles give delivery
room; short edge fades kill the join clicks:

```
HEAD_HANDLE 0.12   TAIL_HANDLE 0.15   EDGE_FADE 0.05
```

Caption cues must never overlap: clamp each cue's end against the next cue's
start, or two PNGs stack on screen.

---

## Don't repeat the backdrop

Every card composited from the same animated loop at offset zero shows the same
frames. Sample a different offset per card — `backdrop_offsets` in
`brand.json`.

---

## Render each element once

Cards, b-roll, opener and outro are shared across programmes. Render each into
`segs/` once and concat; do not re-decode 4K source per programme. Burn the
overlay treatments onto the finished 1080×1920 segment rather than re-cropping
from source, so framing is identical across treatments and it is cheap.

---

## Editorial notes worth carrying forward

**B-roll choice matters more than it looks.** An escalator shot was rejected as
filler; snap shots of keynote presenters on stage and pans across the crowd
were what the client wanted. Show stills and get them confirmed before
committing.

**Show stills for anything ambiguous.** Speaker identification, b-roll picks,
crop centring. Cheaper than a rebuild, and the client can only react to what
they can see.

**Names and titles are the long pole.** Start the chase on day one. The plates
cannot be generated without exact wording, and the client will correct spelling
you were confident about.

**Version suffixes come off before handover.** Keep them on superseded copies
in `out/_superseded/`, and ask before deleting anything from `out/`.

## Caption plate padding must come from font ink bounds

Do not size the plate behind a caption line with fixed pixel offsets around the
text origin (the `y - 8 … y + line_h - 2` pattern one build shipped with).
PIL's default text anchor is the font's *ascender* line, not the top of the
glyphs, so those offsets leave a large gap above the letters and none below —
measured on Poppins Medium 56px it was 23px above and **-6px below**, i.e. the
descenders on g/j/p/q/y and the comma physically overhang the bottom edge.

Derive the box from the rendered ink instead:

```python
ink  = font.getbbox("ABCdfghjklpqty0123456789,'")   # constant per font+size
top    = y_text + ink[1] - padv
bottom = y_text + ink[3] + padv
```

Anchor the *last* line's plate bottom to the target baseline so the block grows
upward and the clearance to any lower third underneath stays fixed. Keep the
reference string constant so every plate is the same height and stacked lines
still merge into one block. Scale `padv` with the font size, since the fitting
loop shrinks the size on long cues.

Verify by measuring the rendered PNG, not by eye: alpha rows give the plate
extent, near-white pixels give the ink extent, and the two gaps should match.

## Re-cuts after client feedback

**Client timecodes are against the delivered file, not the source.** Map each
one through the programme's element list before cutting: an opener and a title
card mean a note at 0:26 is nowhere near 26s of source. Confirm the mapping on
one note ("the 82 stat at 3:44") before acting on the rest.

**A cut sentence usually appears twice.** When a client pulls a statistic,
search every programme's transcript for it: the interviewer often quotes the
figure back a minute later, and a solo cut or a long cut may carry it too. A
plain phrase search misses the paraphrase; search the number.

**Trimming one programme changes the others.** A bite used in three programmes
cannot be edited in place. Make a new bite id for the trimmed version and point
only the programme that needs it at the new id, or you silently re-cut the
others.

**Capitalise the first word of a bite cut mid-sentence**, or the caption opens
lowercase.

**Keep the end card and producer outro unless the client says otherwise.**
"Delete from 26 seconds onwards" means the content, not the branding. Ask once.

**Deleting delivered files from a shared drive is the client's call.** Replace
by writing the new file beside the old one, and say which files you would
remove rather than removing them.
