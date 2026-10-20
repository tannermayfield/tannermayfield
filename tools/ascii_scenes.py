"""ASCII scenes for the "Beyond the code" card.

Each scene loops every `period` seconds on a 48 x 11 character grid (col 0-47, row 0-10).
Items:
  static(col, row, lines)                      never changes
  frames((col, row, lines, t0, t1), ...)       pose swaps: each frame shows during [t0, t1)
  mover(lines, path, show)                     slides along path [(t, col, row), ...] (fractional ok),
                                               visible during the `show` windows
Colors: "ink" (default), "faint", or "pop" (the bright accent).
"""

BALL = "●"


def static(col, row, lines, color="ink"):
    return {"kind": "static", "col": col, "row": row, "lines": lines, "color": color}


def frames(*fs, color="ink"):
    return {"kind": "frames", "frames": list(fs), "color": color}


def mover(lines, path, show=None, color="ink"):
    return {"kind": "mover", "lines": lines, "path": path, "show": show, "color": color}


def arc(t0, t1, start, end, height, steps=10):
    """Parabolic flight from start to end (col, row), peaking `height` rows above the straight line."""
    pts = []
    for i in range(steps + 1):
        u = i / steps
        col = start[0] + (end[0] - start[0]) * u
        row = start[1] + (end[1] - start[1]) * u - height * 4 * u * (1 - u)
        pts.append((t0 + (t1 - t0) * u, col, row))
    return pts


def blink(period, on, off, start=0.0, until=None):
    """Repeating visible windows: `on` seconds visible, `off` hidden, from start to until."""
    until = period if until is None else until
    out, t = [], start
    while t < until:
        out.append((t, min(t + on, until)))
        t += on + off
    return out


# --------------------------------------------------------------------------
# Baseball: pitch, swing, crack, and the ball sails out.
# --------------------------------------------------------------------------

_stance = ["   o /", "  /|/", "   |", "  / \\"]
_swing = ["   o", "  /|\\____", "   |", "  / \\"]
_follow = ["\\  o", " \\/|\\", "   |", "  / \\"]
_set = ["  o", " /|\\", "  |", " / \\"]
_kick = ["  o", " /|\\", "  |__", " /"]
_throw = ["\\_o", "   \\", "  |", " / \\"]

BASEBALL = {
    "period": 3.0,
    "label": "baseball.ascii",
    "items": [
        static(0, 10, ["_" * 48], "faint"),
        static(29, 0, [".--------------.", "|              |", "'--------------'"], "faint"),
        frames((32, 1, ["GO BRAVES!"], 0, 1.5), (32, 1, ["CHOP ON! "], 1.5, 3.0), color="pop"),
        frames((3, 6, _stance, 0, 1.3), (3, 6, _swing, 1.3, 1.55), (3, 6, _follow, 1.55, 2.5), (3, 6, _stance, 2.5, 3.0)),
        frames((40, 6, _set, 0, 0.5), (40, 6, _kick, 0.5, 0.85), (40, 6, _throw, 0.85, 1.25), (40, 6, _set, 1.25, 3.0)),
        frames((12, 3, ["CRACK!"], 1.42, 1.95), (12, 6, ["*"], 1.42, 1.6), color="pop"),
        mover([BALL], [(0.9, 39, 6), (1.42, 11, 7)] + arc(1.42, 2.4, (11, 7), (52, -1), 6), show=[(0.9, 2.4)], color="pop"),
    ],
}

# --------------------------------------------------------------------------
# Basketball: dribble, jump shot, swish.
# --------------------------------------------------------------------------

_dribble = ["  o", " /|\\", "  | \\", " / \\"]
_jump = ["  o/", " /|", "  |", " / \\"]
_cheer = [" \\o/", "  |", "  |", " / \\"]

_bounces = []
for k in range(4):
    _bounces += [(k * 0.4, 9, 8.2), (k * 0.4 + 0.2, 9, 9.6)]

BASKETBALL = {
    "period": 3.2,
    "label": "basketball.ascii",
    "items": [
        static(0, 10, ["_" * 45], "faint"),
        static(45, 0, ["|"] * 11),
        static(38, 3, ["-------"]),
        frames((38, 4, ["\\\\||//", " \\||/"], 0, 2.45), (38, 4, ["|\\||/|", " |\\/|"], 2.45, 2.85),
               (38, 4, ["\\\\||//", " \\||/"], 2.85, 3.2)),
        frames((24, 1, ["SWISH!"], 2.5, 3.1), color="pop"),
        frames((5, 6, _dribble, 0, 1.6), (5, 5, _jump, 1.6, 2.3), (5, 6, _cheer, 2.3, 3.2)),
        mover([BALL], _bounces + [(1.6, 9, 8.2), (1.85, 8, 4.2)] + arc(1.85, 2.45, (8, 4.2), (40.5, 2.6), 3.2)
              + [(2.75, 40.5, 6), (2.95, 40.5, 9.6), (3.1, 37, 8.6)], show=[(0, 3.12)], color="pop"),
    ],
}

# --------------------------------------------------------------------------
# Travel: a plane crosses over mountains while clouds drift; the two of us watch.
# --------------------------------------------------------------------------

_sun1 = [" \\ | /", "-  O  -", " / | \\"]
_sun2 = ["  \\|/", " - O -", "  /|\\"]

TRAVEL = {
    "period": 8.0,
    "label": "travel.ascii",
    "items": [
        frames(*[(1, 0, _sun1 if k % 2 == 0 else _sun2, k * 0.5, k * 0.5 + 0.5) for k in range(16)], color="pop"),
        mover(["  .--.", " (    ).", "(___.__)"], [(0, 48, 0.4), (8, -12, 0.4)], color="faint"),
        mover([" .-.", "(___)"], [(0, 22, 4.2), (4.6, -8, 4.2), (4.61, 56, 4.2), (8, 22, 4.2)], color="faint"),
        mover(["     __", "     \\ \\_______", "~ ~ [==_______>", "     /_/"],
              [(0, -17, 2.4), (2, 4, 1.6), (4, 22, 2.4), (6, 40, 1.7), (8, 60, 2.3)]),
        static(0, 7, ["        /\\", "   /\\  /  \\      /\\", "  /  \\/    \\    /  \\  /\\",
                      "_/          \\__/    \\/  \\________________________"], "faint"),
        static(34, 7, ["o    o", "/|\\__/|\\", "/ \\  / \\"]),
        frames(*[(37, 5, ["<3"], t0, t1) for t0, t1 in blink(8.0, 0.6, 0.4)], color="pop"),
    ],
}

# --------------------------------------------------------------------------
# Bowling: approach, release, roll, strike.
# --------------------------------------------------------------------------

_hold = ["  o", " /|\\", "  |", " / \\"]
_slide = ["   o", "  /|\\_", "  /|", " /  \\_"]
_watch = ["  o", " /|\\", "  |", " / \\"]
_yes = [" \\o/", "  |", "  |", " / \\"]
_pins = ["      i", "    i", "  i   i", "i   i", "  i   i", "    i", "      i"]
_burst = ["   \\    '   /", " -     i", "  '  \\    / -", "    *   -   *", "  .  /   \\  '", " -     .", "   /    '   \\"]
_down = ["", "     _", "  .      -", "    __    .", "  -     _", "      .", ""]

BOWLING = {
    "period": 3.6,
    "label": "bowling.ascii",
    "items": [
        static(0, 2, ["=" * 48], "faint"),
        static(0, 10, ["=" * 48], "faint"),
        static(36, 0, ["next: 300"], "faint"),
        frames((1, 5, _hold, 0, 0.8), (1, 5, _slide, 0.8, 1.7), (1, 5, _watch, 1.7, 2.1), (1, 5, _yes, 2.1, 3.6)),
        frames((38, 3, _pins, 0, 2.05), (35, 3, _burst, 2.05, 2.45), (35, 3, _down, 2.45, 3.25), (38, 3, _pins, 3.25, 3.6)),
        frames(*[(17, 0, ["STRIKE!"], a, b) for a, b in [(2.1, 2.4), (2.55, 2.85), (3.0, 3.4)]], color="pop"),
        mover([BALL], [(0, 4, 7.2), (0.5, 4, 7.2), (0.75, 0.5, 7.6), (1.0, 7, 8), (1.25, 10, 6.2), (2.05, 37, 6),
                       (2.3, 52, 6)], show=[(0, 2.35)], color="pop"),
    ],
}

# --------------------------------------------------------------------------
# Golf: a slow, relaxing swing, a long drive, birds, and a yawn.
# --------------------------------------------------------------------------

_address = ["   o", "   |\\", "   | \\", "  / \\ \\"]
_back = ["\\__o", "   |\\", "   |", "  / \\"]
_through = ["   o__/", "   |/", "   |", "  /  \\"]
_bird1, _bird2 = ["\\v/"], ["-v-"]

GOLF = {
    "period": 6.0,
    "label": "golf.ascii",
    "items": [
        static(0, 10, ["_" * 41 + "\\_/" + "____"], "faint"),
        static(42, 7, ["|", "|", "|"]),
        frames(*[(42, 5, ["|\\", "|/"] if k % 2 == 0 else ["|-.", "|-'"], k * 0.6, k * 0.6 + 0.6) for k in range(10)],
               color="pop"),
        mover([" .--.", "(____)"], [(0, 26, 1.6), (3, 21, 1.6), (6, 26, 1.6)], color="faint"),
        # Two birds flap (frame swaps) while gliding across the sky.
        mover([(_bird1 if k % 2 == 0 else _bird2, k * 0.3, k * 0.3 + 0.3) for k in range(20)],
              [(0, 50, 0.6), (6, -6, 1.8)], color="faint"),
        mover([(_bird2 if k % 2 == 0 else _bird1, k * 0.3, k * 0.3 + 0.3) for k in range(20)],
              [(0, 56, 1.4), (6, 0, 2.4)], color="faint"),
        frames((2, 6, _address, 0, 1.3), (2, 6, _back, 1.3, 1.9), (2, 6, _address, 1.9, 2.05),
               (2, 6, _through, 2.05, 5.0), (2, 6, _address, 5.0, 6.0)),
        frames((8, 4, ["*yawn*"], 4.2, 5.3), (33, 7, ["nice."], 4.8, 5.8), color="faint"),
        mover([BALL], [(0, 9, 9), (1.95, 9, 9)] + arc(1.95, 3.6, (9, 9), (37, 9), 8.5)
              + [(4.5, 41.5, 9.2), (4.8, 42, 10), (4.81, 9, 9), (6, 9, 9)], show=[(0, 4.8), (5.2, 6.0)], color="pop"),
    ],
}

SCENES = {"baseball": BASEBALL, "basketball": BASKETBALL, "travel": TRAVEL, "bowling": BOWLING, "golf": GOLF}
