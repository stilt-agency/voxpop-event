"""
Programme definitions: which bites, in what order, make each deliverable.

An element is one of:
  ("card", "<card file stem>", duration)
  ("bite", "<bite id>")            speech, gets lower thirds and captions
  ("broll", "<bite id>")           silent, no overlays
  ("opener",)                      animated client logo
  ("outro",)                       producer logo reveal

Everything is assembled from shared segment renders, so a clip used in more
than one programme is only decoded from the 4K source once.
"""

OPENER = ("opener",)
OUTRO = ("outro",)
END = ("card", "99_end", 3.5)
TITLE = ("card", "01_title", 2.6)
TITLE2 = ("card", "01_title2", 2.6)

# Keynote montage: three presenters, ~0.9s each
MONTAGE = [("broll", "m1"), ("broll", "m2"), ("broll", "m3")]

V1_LONG = [
    OPENER, TITLE,
    ("card", "q1", 2.6), ("bite", "b01"), ("bite", "b02"), ("bite", "b03"),
    ("broll", "r1"),
    ("card", "q2", 3.2), ("bite", "b04"), ("bite", "b05"),
    ("broll", "r2"),
    ("card", "q3", 2.8), ("bite", "b06"), ("bite", "b07"),
] + MONTAGE + [
    ("card", "q4", 2.6), ("bite", "b08"), ("bite", "b09"), ("bite", "b10"),
    ("broll", "r4"),
    ("card", "q5", 2.4), ("bite", "b13"), ("bite", "b14"), ("bite", "b15"),
    END, OUTRO,
]

V1_SHORT = [
    OPENER, TITLE,
    ("card", "q2", 3.2), ("bite", "b04"),
    ("broll", "r1"),
    ("card", "q4", 2.6), ("bite", "b08"), ("bite", "b10"),
    ("broll", "r4"),
    ("card", "q5", 2.4), ("bite", "b14"), ("bite", "b15"),
    END, OUTRO,
]

V2_LONG = [
    OPENER, TITLE2,
    ("card", "q4", 2.6), ("bite", "c11"), ("bite", "c03"), ("bite", "c05"),
    ("broll", "r3"),
    ("bite", "c09"), ("bite", "c01"), ("bite", "c07"),
] + MONTAGE + [
    ("card", "q5", 2.4), ("bite", "c12"), ("bite", "c04"), ("bite", "c06"),
    ("broll", "r1"),
    ("bite", "c10"), ("bite", "c02"), ("bite", "c08"),
    ("broll", "r4"),
    END, OUTRO,
]

V2_SHORT = [
    OPENER, TITLE2,
    ("card", "q4", 2.6), ("bite", "c11"), ("bite", "c05"),
    ("broll", "r4"),
    ("card", "q5", 2.4), ("bite", "c12"), ("bite", "c10"),
    END, OUTRO,
]

# One cut per new interviewee: their keynote answer and their what-next answer.
SOLO = {
    "William-Kusa": ("c01", "c02"),
    "Darren-Elsby": ("c03", "c04"),
    "Andrew-Panting": ("c05", "c06"),
    "Jordan-Xu": ("c07", "c08"),
    "Anthony-Spencer": ("c09", "c10"),
    "Behzaad-Habibi": ("c11", "c12"),
}


def solo(q4_bite, q5_bite):
    return [
        OPENER,
        ("card", "q4", 2.6), ("bite", q4_bite),
        ("card", "q5", 2.4), ("bite", q5_bite),
        END, OUTRO,
    ]


# Themed cuts, grouped by what people actually said rather than by person.
THEMED = {
    "Theme-One-Pane": [
        OPENER,
        ("card", "qA", 2.8), ("bite", "c05"), ("bite", "c09"),
        ("broll", "r4"),
        ("bite", "c06"),
        END, OUTRO,
    ],
    "Theme-Undo": [
        OPENER,
        ("card", "qB", 2.8), ("bite", "c01"), ("bite", "c02"),
        ("broll", "r2"),
        ("bite", "c10"),
        END, OUTRO,
    ],
    "Theme-Data-Work": [
        OPENER,
        ("card", "qC", 2.6), ("bite", "c03"), ("bite", "c04"),
        ("broll", "r3"),
        ("bite", "c07"), ("bite", "c08"),
        END, OUTRO,
    ],
}


def all_programmes():
    progs = {
        "VOL1-LONG": V1_LONG,
        "VOL1-SHORT": V1_SHORT,
        "VOL2-LONG": V2_LONG,
        "VOL2-SHORT": V2_SHORT,
    }
    for name, (a, b) in SOLO.items():
        progs["SOLO-" + name] = solo(a, b)
    progs.update(THEMED)
    return progs
