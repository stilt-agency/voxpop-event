"""
Check the caption text that will be burned in against all three reads.

For every caption cue, the words are aligned against Whisper large-v2,
Whisper large-v3 and the third source separately. Any run of words that none
of the three contains in that place is printed: that is a splice, an invented
phrase, or a fix list entry gone wrong. Also prints the words both Whisper
models marked low confidence, which is the list to send the client.

  python caption_crosscheck.py            # every clip in overlays.json
  python caption_crosscheck.py b03 b07    # named bites only

Run it after make_overlays.py and before build.py.
"""
import difflib
import json
import os
import re
import sys

import brandkit as BK
import transcripts_merge as TM

ROOT = BK.PROJECT
ASR = os.path.join(ROOT, "asr")


def norm(text):
    out = []
    for t in TM.norm_tokens(text):
        # captions carry the project's spelling convention; compare in one form
        out.append(re.sub(r"(\w{3,}?)is(e|ed|es|ing|ation|ations|er|ers)$", r"\1iz\2", t))
    return out


def source_tokens(clip):
    srcs = {}
    for name, path, reader in (
            ("v2", os.path.join(ASR, "v2", clip + ".json"), TM.whisper_words),
            ("v3", os.path.join(ASR, "v3", clip + ".json"), TM.whisper_words),
            ("third", os.path.join(ASR, "descript", clip + ".txt"), TM.descript_words)):
        if os.path.exists(path):
            srcs[name] = [t for w in reader(path) for t in norm(w["text"])]
    return srcs


def main():
    overlays = json.load(open(os.path.join(ROOT, "overlays.json"), encoding="utf-8"))
    bites = {b["id"]: b for b in json.load(open(os.path.join(ROOT, "bites.json"),
                                               encoding="utf-8"))["bites"]}
    only = sys.argv[1:]
    bad = 0
    for bid, cues in sorted(overlays["cap"].items()):
        if only and bid not in only:
            continue
        clip = bites[bid]["clip"]
        srcs = source_tokens(clip)
        if len(srcs) < 3:
            print("%-5s %s: only %d reads available" % (bid, clip, len(srcs)))
        cap, where = [], []
        for c in cues:
            for t in norm(c["text"]):
                cap.append(t)
                where.append(c["start"])
        ok = [False] * len(cap)
        for toks in srcs.values():
            for b in difflib.SequenceMatcher(None, cap, toks, autojunk=False).get_matching_blocks():
                for k in range(b.size):
                    ok[b.a + k] = True
        i = 0
        while i < len(ok):
            if not ok[i]:
                j = i
                while j < len(ok) and not ok[j]:
                    j += 1
                if j - i >= 2 or len(cap[i]) > 3:
                    bad += 1
                    print("   %-5s %6.2fs  [%s]  ...%s..."
                          % (bid, where[i], " ".join(cap[i:j]),
                             " ".join(cap[max(0, i - 4):j + 4])))
                i = j
            else:
                i += 1
    print("\n%d unsupported run%s" % (bad, "" if bad == 1 else "s"))

    # the "to confirm" list: low confidence in both Whisper models at once
    print("\nTo confirm (low confidence in both Whisper passes):")
    for bid, cues in sorted(overlays["cap"].items()):
        if only and bid not in only:
            continue
        clip = bites[bid]["clip"]
        p2, p3 = (os.path.join(ASR, s, clip + ".json") for s in ("v2", "v3"))
        if not (os.path.exists(p2) and os.path.exists(p3)):
            continue
        w2, w3 = TM.whisper_words(p2), TM.whisper_words(p3)
        lo = [w for w in w3 if w["p"] < 0.5 and len(w["text"].strip(".,?!")) > 2]
        for w in lo:
            m = [x for x in w2 if abs(x["start"] - w["start"]) < 0.4 and x["p"] < 0.5]
            if m:
                print("   %-5s %s %7.2fs  %s" % (bid, clip, w["start"], w["text"]))


if __name__ == "__main__":
    main()
