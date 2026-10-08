# Intake

Run this before touching footage. Ask in these six rounds, in order: each round
tells you what to ask in the next. Use multiple choice wherever the answer is a
pick from a short list, and put the recommended option first.

Record every answer in `project.json` (see `scripts/project.example.json`).
Anything still unknown goes in the **Open items** list at the end of the file
with who is chasing it. Do not start rendering while a blocker is open.

Legend: **[blocker]** stops the build. **[default]** proceed on the bracketed
value if the client does not care.

---

## Round 1: the job

1. **Client and event name, as they should appear on screen.** Exact casing and
   spacing ("ExampleON Sydney 2026", not "exampleon sydney"). [blocker]
2. **What is this for?** Client channels, your own channels, both, or an
   on-site screen loop. Sets safe areas and whether the producer outro belongs
   on the end.
3. **Delivery date, and is there an embargo** before which nothing may be
   published.
4. **Who approves the cut**, and do they want a still mock-up before the first
   render. [default: yes, one mock-up of a question card and one captioned
   frame]
5. **Where do the finished files go?** Full output path, and whether anything
   should also land on a shared drive. [blocker]
6. **File naming.** The house pattern is
   `<Event>-VoxPop-<ratio>-<Programme><-TREATMENTS>.mp4`. Confirm or replace.
   Ask whether a version prefix or suffix is wanted this time, and agree it
   stays off the delivered name once approved.

## Round 2: footage and audio

7. **Source folder(s), and the camera format.** Resolution, frame rate, codec.
   The pipeline assumes one consistent format; mixed formats need a conform
   pass first. [blocker]
8. **Which clips are b-roll** rather than interviews, or permission to sort
   that by scanning. `scan_broll.py` does the scan.
9. **Is the interviewer audible on the clips?** Normally yes, and their
   questions get replaced by splash cards.
10. **Separate audio?** Lapel or recorder files to use instead of camera audio,
    and whether they are already synced.
11. **Anything that must not appear.** Faces without releases, competitor
    branding, a speaker who has since withdrawn, a stat that was pulled after
    the event. Ask directly: this is the single most expensive thing to find
    out late. [blocker]
12. **Consent and releases.** Confirm every on-camera participant signed, and
    whether any of them were promised a review before publication.

## Round 3: brand

13. **Logo, vector (SVG or PDF), in positive and reverse/white cuts.** The
    reverse cut is mandatory over the brand colour and is the most common thing
    to be missing. [blocker]
14. **Brand colours as hex**, plus the brand guide. Which logo variant sits on
    which ground, and the minimum clear space.
15. **The licensed desktop font family, full set.** Trial cuts routinely drop
    the question mark and apostrophe, which wrecks question cards. The build
    reports any glyph that falls through to the fallback: never sign off a
    build that reports one. [blocker]
16. **Caption font and size.** [default: the brand font, SemiBold, white on a
    black plate at 80% opacity] If the client wants their own caption styling,
    get it as a spec, not as a screenshot.
17. **Animated background loop** for title, end and opener slates. If there is
    none, ask whether a flat brand-colour card is acceptable. [blocker unless
    flat is agreed]
18. **Watermark or bug.** Which logo file, which corner, what size and opacity,
    and whether it stays up for the whole programme or only under speech.
    [default: none]
19. **Secondary brand device** (a mark used oversized and faded behind question
    cards). Optional.
20. **Splash and end card design.** What the title card says beyond the event
    name, what the end card says, and whether a call to action, URL or hashtag
    belongs on it. Ask for a reference still from any previous campaign.
21. **Producer outro.** The producer's logo reveal; confirm the file and
    whether this client's cut carries it at all.
22. **Music bed**, or permission to source one. Confirm the licence covers
    paid social if the client will boost the posts.

## Round 4: editorial

23. **The questions as they should read on the cards.** Usually a tidied
    version of what was asked on the day. [blocker]
24. **Every speaker's name, exact job title and company.** Chase this from day
    one. Plates cannot be built without it, and the client will correct
    spelling you were confident about. [blocker for any clip that needs a
    plate]
25. **Name plate rule.** House rule is one plate per person per programme, on
    their first appearance. Confirm, and ask whether titles are wanted at all
    (some clients want name and company only).
26. **Which programmes they want.** Long cut, short teaser, per-speaker solo
    cuts, themed cuts grouping one question across speakers. Each renders in
    every treatment, so confirm the list before rendering. [blocker]
27. **Ratios.** [default: 9:16 only] 1:1 or 16:9 as well doubles or triples the
    render.
28. **Treatments.** [default: four — clean, `-LOWERTHIRDS`, `-CAPTIONS`,
    `-LOWERTHIRDS-CAPTIONS`]
29. **Target runtime per programme**, if the client has a platform limit in
    mind.
30. **Spelling convention.** [default: Australian] Also collect the product and
    company names that must be spelled a particular way: these go straight into
    the caption fix list.

## Round 5: captions

31. **Captions burned in, sidecar SRT, or both.** [default: both]
32. **Third transcript source.** The cross-check needs a source that is not
    Whisper: Descript (upload, the default), a client-supplied reference
    transcript, or a platform export. Confirm the client is comfortable with
    audio going to that service, and which account or drive it lands in.
    [blocker: see `reference/captions.md`]
33. **Verbatim or tidied.** [default: tidied — fillers, stutters and false
    starts dropped, wording otherwise untouched]
34. **Who resolves wording the engines disagree on?** [default: you send the
    list with timecodes and the client decides] Agreed wording gets locked in
    the project's fix list so a later rebuild cannot revert it.

## Round 6: technical

35. **Loudness target.** [default: -16 LUFS for social, flat per-clip gain, not
    dynamic normalisation]
36. **Where the work files live.** A fast local drive with room; budget roughly
    10x the source footage size.
37. **Tool paths**, if this machine differs from the last: ffmpeg, ffprobe,
    Whisper.

---

## What to hand back before building

A short brief the client can approve in one read:

- programme list with runtimes and ratios
- the questions as they will appear on cards
- the speaker list with names and titles exactly as they will appear
- anything still blocked, and who owns it
- the mock-up stills, if they asked for them
