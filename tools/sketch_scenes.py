"""Animated pencil-sketch scenes for the "Beyond the code" card.

Each scene draws a small world as SVG line art. A camera (one CSS transform on
the whole world) pans and zooms across it while people and objects move inside
it. Limbs bend at their joints, balls fly along sampled curves, and the card
applies a "line boil" filter so the pencil lines shimmer like hand-drawn
animation. It is all CSS keyframes, because GitHub shows these files as <img>.

Times are seconds from the moment the hobby appears on screen. Angles are
degrees; 0 means a limb hangs straight down and positive turns it clockwise.
"""

import math

RX, RY = 585, 182  # where the camera's look-at point lands on the card


def tf(x=0, y=0, r=0, sx=1, sy=None, px=0, py=0):
    """A transform with an explicit pivot. The function list never changes, so keyframes interpolate."""
    sy = sx if sy is None else sy
    return (f"translate({x:.2f}px,{y:.2f}px) translate({px:.2f}px,{py:.2f}px) rotate({r:.2f}deg) "
            f"scale({sx:.4f},{sy:.4f}) translate({-px:.2f}px,{-py:.2f}px)")


def cam(cx, cy, z):
    """Camera looking at world point (cx, cy) with zoom z."""
    return f"translate({RX}px,{RY}px) scale({z:.4f}) translate({-cx:.2f}px,{-cy:.2f}px)"


def rnd(i):
    """Deterministic 0..1 noise, so every build draws the same crowd, grass and clouds."""
    return (math.sin(i * 12.9898 + 78.233) * 43758.5453) % 1


def ell(cx, cy, rx, ry):
    return f"M{cx - rx:.2f} {cy:.2f}a{rx:.2f} {ry:.2f} 0 1 0 {2 * rx:.2f} 0a{rx:.2f} {ry:.2f} 0 1 0 {-2 * rx:.2f} 0Z"


def arc_path(t0, t1, p0, p1, lift, s0=1.0, s1=1.0, steps=12, ease=lambda u: u):
    """Sample a flight from p0 to p1 that bulges `lift` units upward; returns (t, x, y, scale) points."""
    pts = []
    for i in range(steps + 1):
        u = i / steps
        e = ease(u)
        x = p0[0] + (p1[0] - p0[0]) * e
        y = p0[1] + (p1[1] - p0[1]) * e - lift * 4 * e * (1 - e)
        pts.append((t0 + (t1 - t0) * u, x, y, s0 + (s1 - s0) * e))
    return pts


class Sketch:
    """Drawing and timing helpers bound to one hobby's slot in the card's cycle."""

    def __init__(self, svg, theme, start, dur, cycle, kf):
        self.svg, self.t, self.kf = svg, theme, kf
        self.start, self.dur, self.cycle = start, dur, cycle
        self.ink, self.bg, self.pop, self.faint = theme["ink"], theme["bg"], theme["pop"], theme["faint"]
        self._ids = 0

    # ---- timing --------------------------------------------------------

    def _pct(self, t):
        return 100.0 * (self.start + min(max(t, 0.0), self.dur)) / self.cycle

    def keys(self, prop, frames, ease="ease-in-out"):
        """Keyframes on the card's full cycle; holds the first value before and the last value after."""
        frames = sorted(frames, key=lambda f: f[0])
        rows = {0.0: (frames[0][1], "linear")}
        for f in frames:
            rows[round(self._pct(f[0]), 3)] = (f[1], f[2] if len(f) > 2 else ease)
        rows[100.0] = (frames[-1][1], "linear")
        body = "".join(f"{k:.3f}%{{{prop}:{v};animation-timing-function:{e}}}" for k, (v, e) in sorted(rows.items()))
        return f"{self.kf(self.svg, body)} {self.cycle}s linear infinite"

    def windows(self, wins):
        """Opacity that is 1 inside the (t0, t1) windows and 0 elsewhere."""
        cuts = sorted({0.0, *(a for a, _ in wins), *(b for _, b in wins)})
        frames = [(c, 1 if any(a <= c < b for a, b in wins) else 0, "step-end") for c in cuts]
        return self.keys("opacity", frames, "step-end")

    def loop(self, prop, frames, period, ease="linear", delay=0.0):
        """A short animation that repeats on its own clock (spinning wheels, dribbles, waving flags)."""
        body = "".join(f"{100 * t / period:.3f}%{{{prop}:{v};animation-timing-function:{ease}}}" for t, v in frames)
        return f"{self.kf(self.svg, body)} {period}s linear {-delay:.2f}s infinite"

    def g(self, *content, tr=None, show=None, loops=(), ease="ease-in-out", attrs=""):
        anims = []
        if tr:
            anims.append(self.keys("transform", tr, ease))
        if show is not None:
            anims.append(self.windows(show))
        anims += list(loops)
        style = "transform-origin:0 0;transform-box:view-box"
        if show is not None:
            style += ";opacity:0"
        if anims:
            style += ";animation:" + ",".join(anims)
        return f'<g style="{style}"{attrs}>' + "".join(content) + "</g>"

    def place(self, x, y, s, *content):
        """Static placement (an SVG attribute, so it never fights a CSS animation)."""
        return f'<g transform="translate({x} {y}) scale({s})">' + "".join(content) + "</g>"

    # ---- marks -----------------------------------------------------------

    def line(self, d, w=1.6, color=None, op=None, dash=None, fill="none"):
        out = f'<path d="{d}" fill="{fill}" stroke="{color or self.ink}" stroke-width="{w}"'
        if op is not None:
            out += f' opacity="{op}"'
        if dash:
            out += f' stroke-dasharray="{dash}"'
        return out + "/>"

    def shape(self, d, fill=None, w=1.7, op=None):
        return self.line(d, w, fill=fill or self.bg, op=op)

    def hatch(self, d, s=4.0, op=None, color=None):
        pid = f"h{int(s * 100)}{'p' if color else ''}"
        if pid not in self.svg.__dict__.setdefault("hatches", set()):
            self.svg.hatches.add(pid)
            self.svg.defs.append(
                f'<pattern id="{pid}" width="{s}" height="{s}" patternUnits="userSpaceOnUse" patternTransform="rotate(40)">'
                f'<line x1="0" y1="0" x2="0" y2="{s}" stroke="{color or self.ink}" stroke-width="{s * 0.22:.3f}" opacity="0.55"/>'
                f"</pattern>")
        return f'<path d="{d}" fill="url(#{pid})" stroke="none"' + (f' opacity="{op}"' if op is not None else "") + "/>"

    def tube(self, d, w, k=1.0, fill=None):
        """A limb: a fat stroke outlined in ink (two strokes), scaled with the world."""
        return (f'<path class="tb" d="{d}" fill="none" stroke="{self.ink}" stroke-width="{w + 2.4 * k:.2f}"/>'
                f'<path class="tb" d="{d}" fill="none" stroke="{fill or self.bg}" stroke-width="{w:.2f}"/>')

    def circ(self, cx, cy, r, fill=None, w=1.6, color=None):
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill or self.bg}" stroke="{color or self.ink}" stroke-width="{w}"/>'

    def text(self, x, y, s, size, weight=700, fill=None, outline=False, anchor="middle", fam="G", ls=None):
        if outline:
            return self.svg.text(x, y, s, fam, weight, size, fill="none", anchor=anchor, ls=ls,
                                 extra=f'stroke="{self.ink}" stroke-width="{size * 0.035:.2f}"')
        return self.svg.text(x, y, s, fam, weight, size, fill=fill or self.ink, anchor=anchor, ls=ls)

    def arc_text(self, d, s, size, ls=0.08):
        self._ids += 1
        pid = f"tp{int(self.start)}_{self._ids}"
        self.svg.used.setdefault(("G", 700), set()).update(s)
        return (f'<path id="{pid}" d="{d}" fill="none" stroke="none"/>'
                f'<text font-family="G" font-weight="700" font-size="{size}" fill="{self.ink}" letter-spacing="{ls}em">'
                f'<textPath href="#{pid}" startOffset="50%" text-anchor="middle">{s}</textPath></text>')

    # ---- rigs ------------------------------------------------------------

    def limb(self, base, l1, l2, w1, w2, ang, end="", k=1.0, ease="ease-in-out"):
        """Two-segment limb hanging from `base`. ang = [(t, upper, lower[, ease])]; `end` sits at the tip."""
        bx, by = base
        ex, ey = bx, by + l1
        lower = self.g(self.tube(f"M{ex} {ey}L{ex} {ey + l2}", w2, k), end,
                       tr=[(a[0], tf(r=a[2], px=ex, py=ey), *a[3:]) for a in ang], ease=ease)
        return self.g(self.tube(f"M{bx} {by}L{ex} {ey}", w1, k), lower,
                      tr=[(a[0], tf(r=a[1], px=bx, py=by), *a[3:]) for a in ang], ease=ease)

    def mover(self, pts, *content, show=None, ease="linear", rot=None):
        """Move content drawn around (0, 0) through (t, x, y, scale) points."""
        tr = [(p[0], tf(p[1], p[2], r=(rot(p[0]) if rot else 0), sx=p[3])) for p in pts]
        return self.g(*content, tr=tr, show=show, ease=ease)


def walk_frames(t0, t1, step, a, offset=0):
    """Alternating swing angles for a walk or shuffle."""
    out, k = [], offset
    t = t0
    while t <= t1:
        out.append((t, a if k % 2 == 0 else -a))
        t += step
        k += 1
    return out


# =============================================================================
# 1. Baseball: from behind the pitcher (#22 Mayfield), curveball, swing and a miss.
# =============================================================================

def _baseball_ball(S, r):
    seams = (f"M{-r * 0.55:.2f} {-r * 0.8:.2f}C{-r * 0.15:.2f} {-r * 0.3:.2f} {-r * 0.15:.2f} {r * 0.3:.2f} {-r * 0.55:.2f} {r * 0.8:.2f}"
             f"M{r * 0.55:.2f} {-r * 0.8:.2f}C{r * 0.15:.2f} {-r * 0.3:.2f} {r * 0.15:.2f} {r * 0.3:.2f} {r * 0.55:.2f} {r * 0.8:.2f}")
    return S.circ(0, 0, r) + S.line(seams, 1.3, color=S.pop)


def _umpire(S, k):
    arm = S.limb((-18, -78), 17, 17, 7, 6, [(0, 24, -46), (8.85, 24, -46), (9.1, 100, -6, "ease-out"),
                                             (10.2, 100, -6), (10.7, 24, -46)], end=S.circ(-18, -40, 3.4), k=k)
    body = [
        S.tube("M-12 -42L-22 -20L-17 0", 12, k), S.tube("M12 -42L22 -20L17 0", 12, k),
        S.shape("M-24 -44C-28 -62 -24 -76 -18 -82L18 -82C24 -76 28 -62 24 -44Z"),
        S.hatch("M-24 -44C-28 -62 -24 -76 -18 -82L18 -82C24 -76 28 -62 24 -44Z", 2.2),
        S.tube("M18 -78L28 -60L20 -44", 6.5, k), arm,
        S.circ(0, -92, 9.5), S.line("M-6 -98V-86M0 -99V-85M6 -98V-86M-8 -93H8M-7 -88H7", 0.9),
    ]
    call = S.g(S.text(-46, -112, "STRIKE!", 15, fill=S.pop), show=[(8.95, 10.4)])
    return S.g(*body, tr=[(0, tf()), (8.85, tf()), (9.05, tf(y=-6)), (10.6, tf())]) + call


def _catcher(S, k):
    mitt_ball = S.g(S.circ(6, -48, 2.6, fill=S.pop, w=0.8), show=[(8.72, 9.85)])
    mitt = S.g(S.tube("M13 -64L19 -54L9 -48", 6, k), S.shape(ell(6, -48, 8, 9)), S.line("M1 -53Q6 -57 11 -53M2 -44Q6 -41 10 -44", 0.9),
               mitt_ball, tr=[(8.7, tf()), (8.76, tf(y=2.5)), (8.95, tf())])
    throw_ball = S.g(S.circ(-13, -38, 2.6, fill=S.pop, w=0.8), show=[(9.85, 10.28)])
    arm = S.limb((-13, -64), 13, 13, 6, 5.5, [(0, 12, -24), (9.5, 12, -24), (9.8, 140, 40), (10.15, 150, 50),
                                              (10.3, -70, -10, "ease-in"), (10.7, -30, -20)],
                 end=S.circ(-13, -38, 3) + throw_ball, k=k)
    crouch = S.g(S.tube("M-10 -36L-26 -26L-18 0", 11, k), S.tube("M10 -36L26 -26L18 0", 11, k),
                 S.line("M-24 -20L-19 -4M24 -20L19 -4", 0.8), show=[(0, 9.7)])
    stand = S.g(S.tube("M-9 -36L-11 -12L-12 14", 11, k), S.tube("M9 -36L12 -12L13 14", 11, k), show=[(9.7, 99)])
    torso = [S.shape("M-16 -36C-19 -52 -17 -64 -12 -68L12 -68C17 -64 19 -52 16 -36Z"),
             S.line("M-14 -46H14M-15 -56H15M0 -68V-36", 0.8),
             S.circ(0, -77, 9), S.line("M-5 -82V-71M0 -83V-70M5 -82V-71M-7 -77H7", 0.9)]
    return S.g(crouch, stand, *torso, arm, mitt, tr=[(0, tf()), (9.55, tf()), (9.85, tf(y=-14, r=6, py=-36))])


def _batter(S, k):
    bat = S.g(S.tube("M14 -88L14 -112", 3.6, k), S.tube("M14 -112L14 -140", 5.4, k), S.circ(14, -86, 2.4),
              tr=[(0, tf(r=22, px=14, py=-88)), (8.45, tf(r=22, px=14, py=-88)),
                  (8.58, tf(r=95, sy=0.9, px=14, py=-88), "ease-in"), (8.66, tf(r=178, sy=0.12, px=14, py=-88), "linear"),
                  (8.73, tf(r=270, sy=1, px=14, py=-88), "linear"), (8.9, tf(r=330, sy=0.85, px=14, py=-88)),
                  (9.4, tf(r=340, px=14, py=-88)), (9.9, tf(r=520, px=14, py=-88))])
    arms = S.tube("M-6 -84L4 -74L14 -86", 6, k) + S.tube("M4 -84L11 -78L15 -88", 5.5, k)
    head = S.g(S.circ(-3, -98, 9), S.shape("M-13 -99C-13 -112 7 -113 7 -100Z"), S.hatch("M-13 -99C-13 -112 7 -113 7 -100Z", 1.8),
               S.line("M-13 -99L-20 -98", 1.4), tr=[(0, tf()), (9.4, tf()), (9.8, tf(r=-16, y=2, px=0, py=-90))])
    upper = S.g(S.shape("M-10 -50C-14 -64 -14 -78 -8 -88L10 -86C14 -74 13 -60 9 -50Z"), S.line("M-10 -54H9", 1.0),
                arms, head, bat,
                tr=[(0, tf()), (8.5, tf()), (8.7, tf(r=-12, px=0, py=-50)), (9.1, tf(r=-5, px=0, py=-50)),
                    (9.6, tf(r=8, px=0, py=-50))])
    walk = walk_frames(9.9, 16, 0.42, 16)
    legs = (S.g(S.tube("M-4 -50L-16 -26L-20 0", 10, k),
                tr=[(0, tf())] + [(t, tf(r=a, px=-4, py=-50)) for t, a in walk]) +
            S.g(S.tube("M6 -50L16 -28L20 0", 10, k),
                tr=[(0, tf())] + [(t, tf(r=-a, px=6, py=-50)) for t, a in walk]))
    body = S.g(legs, upper, tr=[(0, tf()), (9.4, tf()), (9.9, tf(x=6, sx=-1, sy=1)), (16, tf(x=150, sx=-1, sy=1), "linear")])
    grawlix = S.g(S.text(0, -124, "#@%&!", 16, fill=S.pop), tr=[(9.4, tf()), (16, tf(x=144), "linear")], show=[(9.8, 12.2)])
    return body + grawlix


def _pitcher(S):
    px = -90
    k = 1.0
    hand_ball = S.g(S.g(_baseball_ball(S, 9),
                        tr=[(0, tf(x=px + 50, y=-158)), (1.0, tf(x=px + 50, y=-158)), (1.5, tf(x=px + 50, y=-158, r=-18)),
                            (2.3, tf(x=px + 50, y=-158, r=4)), (2.8, tf(x=px + 50, y=-158))]),
                    show=[(0, 7.95)])
    fingers = S.tube(f"M{px + 41} -167L{px + 52} -160L{px + 60} -150", 5.5, 0.6) + \
        S.tube(f"M{px + 44} -170L{px + 56} -164L{px + 64} -156", 5.5, 0.6) + \
        S.tube(f"M{px + 44} -150L{px + 54} -146", 5, 0.6)
    r_hand = S.circ(px + 50, -168, 10) + hand_ball + S.g(fingers, show=[(0, 7.95)])
    glove = S.shape(f"M{px - 62} -176C{px - 74} -168 {px - 70} -134 {px - 52} -128C{px - 36} -126 {px - 34} -150 {px - 40} -166Z") + \
        S.line(f"M{px - 60} -162L{px - 44} -142M{px - 56} -168L{px - 42} -152", 1.1) + \
        S.hatch(f"M{px - 62} -176C{px - 74} -168 {px - 70} -134 {px - 52} -128C{px - 36} -126 {px - 34} -150 {px - 40} -166Z", 3)

    r_ang = [(0, -14, 84), (3.6, -14, 84), (4.3, -30, 120), (6.1, -30, 120), (6.5, -60, 30), (7.0, -150, 40),
             (7.6, -165, 70), (7.9, -190, 10, "ease-in"), (8.35, -320, 10), (16, -320, 12)]
    l_ang = [(0, 10, -6), (3.6, 10, -6), (4.3, -35, -55), (6.1, -35, -55), (6.6, 150, -10), (7.6, 125, -30),
             (8.1, 30, -60), (8.6, 20, -70), (16, 20, -70)]
    r_arm = S.limb((px + 50, -284), 62, 56, 24, 21, r_ang, end=r_hand, k=k)
    l_arm = S.limb((px - 50, -284), 62, 56, 24, 21, l_ang, end=glove, k=k)
    behind = [(3.6, 6.3), (8.1, 99)]
    front = [(0, 3.6), (6.3, 8.1)]

    shoe = lambda x: S.shape(f"M{x - 15} -14C{x - 16} -2 {x - 8} 2 {x} 2C{x + 8} 2 {x + 16} -2 {x + 15} -14Z") + \
        S.line(f"M{x - 13} -4H{x + 13}", 1.0)
    l_leg = S.limb((px - 20, -168), 80, 76, 32, 28,
                   [(0, 3, 0), (4.6, 3, 0), (5.4, 42, -78), (6.4, 46, -84), (7.0, 8, -5), (16, 6, -4)],
                   end=shoe(px - 20), k=k)
    r_leg = S.limb((px + 20, -168), 80, 76, 32, 28,
                   [(0, -3, 0), (7.0, -3, 0), (7.6, -14, 12), (8.3, -30, 40), (16, -30, 40)], end=shoe(px + 20), k=k)

    torso_d = (f"M{px - 38} -166C{px - 42} -205 {px - 58} -250 {px - 54} -288Q{px} -306 {px + 54} -288"
               f"C{px + 58} -250 {px + 42} -205 {px + 38} -166Z")
    head = S.g(S.tube(f"M{px} -300L{px} -312", 22, k),
               S.circ(px, -332, 25), S.hatch(f"M{px - 24} -326Q{px} -300 {px + 24} -326L{px + 24} -316Q{px} -304 {px - 24} -316Z", 2.5),
               S.line(f"M{px - 25} -336q-6 4 0 10M{px + 25} -336q6 4 0 10", 1.4),
               S.shape(f"M{px - 27} -334C{px - 27} -364 {px + 27} -364 {px + 27} -334Z"),
               S.hatch(f"M{px - 27} -334C{px - 27} -364 {px + 27} -364 {px + 27} -334Z", 3.5, op=0.6),
               S.line(f"M{px} -359V-336M{px - 14} -356Q{px - 10} -345 {px - 12} -334M{px + 14} -356Q{px + 10} -345 {px + 12} -334", 1.0),
               S.line(f"M{px - 9} -334Q{px} -346 {px + 9} -334", 1.4), S.circ(px, -360, 2.6),
               tr=[(0, tf()), (1.2, tf()), (1.8, tf(r=4, px=px, py=-306)), (2.8, tf(r=4, px=px, py=-306)), (3.4, tf())])
    jersey = [S.shape(torso_d), S.hatch(f"M{px - 38} -166C{px - 42} -205 {px - 50} -230 {px - 52} -250L{px - 40} -250L{px - 30} -166Z", 3),
              S.line(f"M{px - 14} -300L{px - 46} -252M{px + 14} -300L{px + 46} -252", 1.1),
              S.line(f"M{px - 14} -300Q{px} -292 {px + 14} -300", 1.3),
              S.arc_text(f"M{px - 44} -258Q{px} -282 {px + 44} -258", "MAYFIELD", 15),
              S.text(px, -194, "22", 58, outline=True),
              S.shape(f"M{px - 41} -174H{px + 41}V-160H{px - 41}Z"), S.line(f"M{px - 20} -174V-160M{px + 20} -174V-160", 1.0)]
    upper = S.g(S.g(l_arm, show=behind), S.g(r_arm, show=behind), *jersey, head,
                S.g(l_arm, show=front), S.g(r_arm, show=front),
                tr=[(0, tf()), (4.8, tf(r=-4, px=px, py=-168)), (6.2, tf(r=-7, px=px, py=-168)),
                    (7.4, tf(r=3, px=px, py=-168)), (8.0, tf(r=8, sy=0.93, px=px, py=-168)),
                    (8.5, tf(r=14, sy=0.86, px=px, py=-168)), (16, tf(r=14, sy=0.86, px=px, py=-168))])
    shadow = S.hatch(ell(px, -4, 70, 10), 3)
    return S.g(shadow, l_leg, r_leg, upper,
               tr=[(0, tf()), (7.0, tf()), (7.7, tf(y=-14, sx=0.97, px=px)), (8.4, tf(x=8, y=-22, sx=0.95, px=px))])


def baseball(S):
    w = []
    crowd = "".join(f"M{-380 + i * 10 + (row % 2) * 5 + rnd(i * 7 + row) * 3:.1f} {-306 + row * 11 + rnd(i + row * 13) * 2:.1f}"
                    f"a3 3 0 1 0 6 0a3 3 0 1 0 -6 0" for row in range(4) for i in range(86))
    w += [S.hatch("M-400 -330H480V-262H-400Z", 3, op=0.55), S.line(crowd, 0.9, op=0.75),
          S.shape("M-400 -264H480V-252H-400Z"), S.hatch("M-400 -264H480V-252H-400Z", 2)]
    w += [S.line("".join(f"M-400 {y}H480" for y in range(-240, -30, 16)), 1, op=0.18, dash="10 8")]
    w += [S.hatch(ell(40, -206, 125, 22), 3.2, op=0.7), S.line(ell(40, -206, 125, 22), 1, op=0.5),
          S.line("M40 -207L-360 -130M40 -207L440 -130", 1.2, op=0.6),
          S.shape("M380 -144L392 -140L380 -136L368 -140Z"),
          S.line("M6 -213H28V-200H4ZM52 -213H74L76 -200H54Z", 0.9, op=0.7),
          S.shape("M33 -208H47L48 -206L40 -203L32 -206Z", w=1.0),
          S.line(ell(-90, 0, 210, 36), 1.2, op=0.5, dash="6 6"), S.shape("M-112 -6H-68V-1H-112Z")]
    w += [S.place(46, -210, 0.45, _umpire(S, 0.5)), S.place(40, -203, 0.42, _catcher(S, 0.5)),
          S.place(80, -205, 0.5, _batter(S, 0.5))]
    w.append(_pitcher(S))

    spin = S.g(_baseball_ball(S, 7), loops=[S.loop("transform", [(0, "rotate(0deg)"), (0.12, "rotate(360deg)")], 0.12)])
    pitch = [(7.95, -36, -382, 1.0), (8.15, -6, -332, 0.62), (8.35, 19, -287, 0.42), (8.5, 33, -255, 0.33),
             (8.62, 40, -238, 0.28), (8.72, 42.5, -224, 0.24)]
    w.append(S.mover(pitch, spin, show=[(7.95, 8.72)]))
    throw = arc_path(10.28, 10.9, (31, -243), (330, -150), 70, 0.24, 0.5)
    w.append(S.mover(throw, _baseball_ball(S, 7), show=[(10.28, 10.9)]))

    camera = [(0, cam(-88, -215, 1.9)), (3.4, cam(-86, -212, 1.96)), (6.4, cam(-60, -190, 0.95)),
              (7.5, cam(-50, -200, 1.0)), (8.45, cam(58, -226, 3.2), "ease-in"), (16, cam(58, -226, 3.25))]
    return S.g(*w, tr=camera)


# =============================================================================
# 2. Basketball: jersey, crossover, step-back three at the buzzer.
# =============================================================================

def _player_back(S, num_side=True):
    k = 1.0
    shoe = lambda x: S.shape(f"M{x - 17} -26C{x - 19} -6 {x - 10} 0 {x} 0C{x + 10} 0 {x + 19} -6 {x + 17} -26Z") + \
        S.line(f"M{x - 15} -8H{x + 15}M{x - 10} -18Q{x} -12 {x + 12} -20", 1.0)
    shuffle = walk_frames(3.8, 7.3, 0.3, 7)
    jump_l = [(8.3, 6, 18), (8.7, 0, 0), (9.1, 4, 12), (9.7, 6, 20), (10.3, 2, 4)]
    jump_r = [(8.3, -6, -18), (8.7, 0, 0), (9.1, -4, -12), (9.7, -6, -20), (10.3, -2, -4)]
    l_leg = S.limb((-24, -195), 88, 82, 30, 26, [(0, 3, 0)] + [(t, 3 + a, max(a, 0) * 1.5) for t, a in shuffle] + jump_l,
                   end=shoe(-24), k=k)
    r_leg = S.limb((24, -195), 88, 82, 30, 26, [(0, -3, 0)] + [(t, -3 - a, min(a, 0) * -1.5) for t, a in shuffle] + jump_r,
                   end=shoe(24), k=k)
    shorts = "M-58 -212L58 -212L64 -118L8 -112L0 -136L-8 -112L-64 -118Z"
    tank = "M-46 -205C-50 -250 -54 -292 -40 -322L-26 -330C-14 -316 14 -316 26 -330L40 -322C54 -292 50 -250 46 -205Z"

    pump = []
    t = 0.0
    while t < 8.0:
        pump.append((t, -18, 34))
        pump.append((t + 0.275, -22, 8))
        t += 0.55
    r_arm = S.limb((48, -312), 58, 54, 20, 18, pump + [(8.0, -18, 30), (8.7, -168, 28), (9.0, -175, 20), (9.4, -150, 30),
                                                         (10.2, -20, 20), (15, -12, 14)],
                   end=S.circ(48, -194, 9), k=k)
    l_arm = S.limb((-48, -312), 58, 54, 20, 18, [(0, 28, -20), (3.8, 28, -20), (4.5, 40, -30), (6.0, 20, -10),
                                                 (8.0, 18, -30), (8.7, 165, -36), (9.0, 172, -20), (9.4, 150, -30),
                                                 (10.2, 20, -10), (15, 12, -8)],
                   end=S.circ(-48, -194, 9), k=k)
    head = [S.tube("M0 -318L0 -338", 22, k), S.circ(0, -360, 24), S.hatch("M-24 -362C-24 -392 24 -392 24 -362Q0 -372 -24 -362Z", 2.4),
            S.line("M-24 -364q-6 4 0 10M24 -364q6 4 0 10", 1.4)]
    torso = [S.shape(tank), S.line("M-26 -330Q0 -306 26 -330", 1.2),
             S.arc_text("M-36 -284Q0 -302 36 -284", "MAYFIELD", 14), S.text(0, -228, "22", 52, outline=True),
             S.line("M-46 -214H46", 1.2)]
    return [l_leg, r_leg, S.shape(shorts), S.line("M-56 -200L-62 -122M56 -200L62 -122", 1.0, op=0.7),
            S.hatch("M-58 -212L-48 -212L-54 -116L-64 -118Z", 2.5), *torso, *head, l_arm, r_arm]


def _defender(S):
    k = 1.0
    shoe = lambda x: S.shape(f"M{x - 16} -24C{x - 18} -6 {x - 9} 0 {x} 0C{x + 9} 0 {x + 18} -6 {x + 16} -24Z")
    legs = [S.limb((-26, -195), 88, 82, 30, 26, [(0, 14, -14)], end=shoe(-26), k=k),
            S.limb((26, -195), 88, 82, 30, 26, [(0, -14, 14)], end=shoe(26), k=k)]
    arms = [S.limb((-48, -310), 58, 54, 20, 18, [(0, 62, -10), (8.4, 62, -10), (8.8, 168, -10), (9.6, 62, -10)],
                   end=S.circ(-48, -192, 9), k=k),
            S.limb((48, -310), 58, 54, 20, 18, [(0, -62, 10)], end=S.circ(48, -192, 9), k=k)]
    body = [S.shape("M-58 -212L58 -212L64 -120L8 -114L0 -136L-8 -114L-64 -120Z"),
            S.hatch("M-58 -212L58 -212L64 -120L8 -114L0 -136L-8 -114L-64 -120Z", 3.4),
            S.shape("M-46 -205C-50 -250 -54 -292 -40 -322L-26 -330L0 -300L26 -330L40 -322C54 -292 50 -250 46 -205Z"),
            S.hatch("M-46 -205C-50 -250 -54 -292 -40 -322L-26 -330L0 -300L26 -330L40 -322C54 -292 50 -250 46 -205Z", 3.4),
            S.text(0, -240, "4", 40, outline=True),
            S.tube("M0 -318L0 -338", 22, k), S.circ(0, -360, 24), S.hatch("M-24 -366C-22 -392 22 -392 24 -366Z", 2.2),
            S.line("M-10 -362h5M5 -362h5M-6 -347q6 -3 12 0M-13 -370l8 3M13 -370l-8 3", 1.4)]
    return S.g(*legs, *body, *arms,
               tr=[(0, tf()), (4.0, tf()), (4.6, tf(x=-42, r=-6)), (5.6, tf(x=-28, r=-3)), (6.4, tf(x=10)),
                   (7.4, tf(x=40)), (8.5, tf(x=58)), (8.9, tf(x=58, y=-46)), (9.5, tf(x=58)), (15, tf(x=58))])


def basketball(S):
    w = []
    w.append(S.line("".join(f"M{i * 60} 140L{40 + i * 12} -560" for i in range(-14, 16)), 1, op=0.16))
    w.append(S.hatch("M-700 -660H800V-560H-700Z", 3.2, op=0.55))
    w.append(S.line("".join(f"M{-690 + i * 11 + rnd(i) * 4:.1f} {-640 + rnd(i * 3) * 30:.1f}a3.4 3.4 0 1 0 6.8 0a3.4 3.4 0 1 0 -6.8 0"
                            for i in range(135)), 0.9, op=0.6))
    w.append(S.line("M-700 -560H800", 1.6))
    w.append(S.line("M-14 -560L-60 -270L140 -270L94 -560", 1.4, op=0.8))
    w.append(S.line(ell(40, -270, 100, 22), 1.2, op=0.6, dash="8 8"))
    w.append(S.line("M-600 -10Q40 -112 680 -10", 2.4))
    w.append(S.tube("M40 -570L40 -790", 14))
    w.append(S.line("M40 -760L40 -790M40 -775H70", 2))

    # Shot clock, buzzer and backboard.
    flash = [(10.3 + i * 0.3, 10.45 + i * 0.3) for i in range(8)]
    w += [S.shape("M-20 -800H100V-725H-20Z"), S.line("M22 -760H58V-728H22Z", 1.4),
          S.shape("M8 -850H72V-810H8Z"), S.hatch("M8 -850H72V-810H8Z", 2, op=0.5),
          S.g(S.text(40, -822, "0:01", 20, 700, fam="M"), show=[(0, 10.3)]),
          S.g(S.text(40, -822, "0:00", 20, 700, fill=S.pop, fam="M"), show=[(10.3, 99)]),
          S.g(S.shape("M-20 -805H100V-799H-20Z", fill=S.pop), S.line("M-2 -860L-24 -880M82 -860L104 -880M40 -862V-892M-8 -830H-34M88 -830H114", 2.2, color=S.pop),
              show=flash),
          S.g(S.text(150, -860, "BZZZZT!", 24, fill=S.pop), tr=[(10.3, tf()), (10.5, tf(r=-6, px=150, py=-860)),
                                                               (10.7, tf(r=4, px=150, py=-860)), (11, tf())], show=[(10.3, 12.6)])]
    w.append(S.line("M6 -705A34 6.5 0 0 1 74 -705", 2.4))  # back of the rim

    k = 1.0
    body_tr = [(0, tf()), (3.8, tf()), (4.5, tf(x=-30, r=-6)), (5.0, tf(x=-18)), (5.9, tf(x=75, r=4)), (6.6, tf(x=95)),
               (7.3, tf(x=80, y=45, sx=1.1)), (8.0, tf(x=80, y=45, sx=1.1)), (8.6, tf(x=80, y=-25, sx=1.1), "ease-out"),
               (9.1, tf(x=80, y=-45, sx=1.1)), (9.7, tf(x=80, y=45, sx=1.1), "ease-in"), (15, tf(x=80, y=45, sx=1.1))]
    w.append(S.place(70, -75, 0.85, _defender(S)))

    bounce = []
    t = 0.0
    while t < 8.0:
        bounce.append((t, 64, -190, 1))
        bounce.append((t + 0.275, 64, -16, 1))
        t += 0.55
    ball_art = S.circ(0, 0, 15, fill=S.bg) + S.line("M-15 0H15M0 -15V15M-10 -11Q-4 0 -10 11M10 -11Q4 0 10 11", 1.1, color=S.pop)
    dribble = S.mover(bounce + [(8.0, 64, -190, 1)], ball_art, show=[(0, 8.0)], ease="ease-in-out")
    held = S.mover([(8.0, 64, -190, 1), (8.7, 4, -440, 1), (9.0, 2, -456, 1)], ball_art, show=[(8.0, 9.0)], ease="ease-out")
    w.append(S.g(*_player_back(S), dribble, held, tr=body_tr))

    flight = arc_path(9.0, 10.9, (82, -456), (40, -712), 320, 1.0, 0.5, steps=16, ease=lambda u: u)
    flight += [(11.2, 40, -665, 0.5), (11.6, 40, -600, 0.5)]
    w.append(S.mover(flight, ball_art, show=[(9.0, 11.6)]))

    strands = "".join(f"M{40 + 34 * math.cos(a):.1f} {-705 + 6.5 * math.sin(a):.1f}L{40 + 20 * math.cos(a):.1f} -655"
                      for a in [math.pi * i / 7 for i in range(8)])
    zig = "M8 -700L18 -685L26 -700L34 -684L44 -700L52 -684L60 -700L70 -686M20 -676L30 -664L40 -676L50 -664L60 -676"
    net = S.g(S.line(strands, 1.2), S.line(zig, 1.0), S.line("M6 -705A34 6.5 0 0 0 74 -705", 2.6),
              tr=[(0, tf()), (10.95, tf()), (11.15, tf(sy=1.28, px=40, py=-705)), (11.35, tf(sy=0.9, r=3, px=40, py=-705)),
                  (11.6, tf(sy=1.06, r=-2, px=40, py=-705)), (12.0, tf())])
    w.append(net)
    w.append(S.g(S.text(-30, -640, "swish.", 20, 500, fill=S.pop, anchor="end"), show=[(11.2, 13.5)]))

    camera = [(0, cam(0, -300, 1.7)), (2.3, cam(4, -296, 1.72)), (3.6, cam(15, -112, 1.35)), (6.0, cam(55, -110, 1.35)),
              (6.6, cam(70, -120, 1.3)), (8.0, cam(40, -330, 0.56)), (8.7, cam(40, -360, 0.6)),
              (10.4, cam(40, -730, 1.05), "ease-in-out"), (12, cam(40, -716, 1.15)), (15, cam(40, -712, 1.2))]
    return S.g(*w, tr=camera)


# =============================================================================
# 3. Travel: spinning tire, the car drives off, up through the clouds, a jet.
# =============================================================================

def _cloud(S, x, y, s):
    d = (f"M{x - 60 * s:.1f} {y:.1f}a{20 * s:.1f} {20 * s:.1f} 0 0 1 {24 * s:.1f} {-22 * s:.1f}"
         f"a{26 * s:.1f} {26 * s:.1f} 0 0 1 {44 * s:.1f} {-8 * s:.1f}a{22 * s:.1f} {22 * s:.1f} 0 0 1 {34 * s:.1f} {14 * s:.1f}"
         f"a{16 * s:.1f} {16 * s:.1f} 0 0 1 {18 * s:.1f} {16 * s:.1f}Z")
    return S.shape(d) + S.hatch(f"M{x - 56 * s:.1f} {y:.1f}H{x + 56 * s:.1f}V{y - 9 * s:.1f}H{x - 56 * s:.1f}Z", 3, op=0.6)


def _car(S):
    spokes = "".join(f"M0 0L{20 * math.cos(a):.2f} {20 * math.sin(a):.2f}" for a in [i * 2 * math.pi / 5 for i in range(5)])
    spin = S.loop("transform", [(0, "rotate(0deg)"), (0.16, "rotate(360deg)")], 0.16)
    wheel = (S.shape(ell(172, -40, 20, 40)) + S.line(ell(172, -40, 17, 36), 3.2, dash="5 6") +
             f'<g transform="translate(172 -40) scale(0.5 1)">' +
             S.g(S.circ(0, 0, 21), S.line(spokes, 2.2), S.circ(0, 0, 5), loops=[spin]) + "</g>")
    tread = S.g(S.line(ell(172, -40, 17, 36), 3.2, dash="5 6"),
                loops=[S.loop("stroke-dashoffset", [(0, "0"), (0.12, "-22")], 0.12)])
    left_tire = S.shape("M-142 -46H-100V2H-142Z") + S.hatch("M-142 -46H-100V2H-142Z", 2.2) + \
        S.g(S.line("M-142 -40H-100M-142 -28H-100M-142 -16H-100M-142 -4H-100", 1.2),
            loops=[S.loop("transform", [(0, "translateY(-12px)"), (0.1, "translateY(0px)")], 0.1)])
    puff = S.g(S.line(ell(-112, -30, 7, 5), 1.0, op=0.6),
               loops=[S.loop("transform", [(0, "translate(0px,0px) scale(1)"), (0.9, "translate(-14px,22px) scale(2.4)")], 0.9),
                      S.loop("opacity", [(0, "0.9"), (0.9, "0")], 0.9)])
    body = [
        S.shape("M150 -120L192 -110L194 -40L150 -38Z"), S.hatch("M150 -120L192 -110L194 -40L150 -38Z", 3),
        S.line("M150 -72Q172 -104 196 -70", 1.6),
        S.shape("M-110 -152L-84 -216L84 -216L110 -152Z"), S.hatch("M-96 -160L-76 -208L-40 -208L-70 -160Z", 3),
        S.line("M84 -216L120 -208L150 -152", 1.6),
        S.shape("M-150 -40L-150 -122C-150 -142 -140 -152 -120 -152L120 -152C140 -152 150 -142 150 -122L150 -40Z"),
        S.line("M-140 -132H140", 1.0, op=0.7),
        S.shape("M-146 -142H-96V-118H-146Z", fill=S.pop, op=0.85), S.shape("M96 -142H146V-118H96Z", fill=S.pop, op=0.85),
        S.shape("M-34 -104H34V-76H-34Z"), S.text(0, -84, "TM 22", 15, 700, fam="M"),
        S.shape("M-156 -62H156V-36H-156Z"), S.line("M-150 -50H150", 0.9, op=0.6),
    ]
    return [left_tire, S.shape(ell(-112, -38, 5, 4)), puff, *body, wheel, tread]


def _plane(S):
    contrails = S.line("M-112 44L-150 320M-104 44L-136 320M112 44L150 320M104 44L136 320M-282 -16L-334 220M282 -16L334 220", 1.2, op=0.45, dash="3 7")
    parts = [
        S.shape("M-30 4L-282 -28L-286 -16L-28 24Z"), S.shape("M30 4L282 -28L286 -16L28 24Z"),
        S.shape("M-28 -16L-150 -36L-150 -26L-26 -4Z"), S.shape("M28 -16L150 -36L150 -26L26 -4Z"),
        S.shape("M-7 -24L-14 -150L10 -150L8 -24Z"), S.hatch("M-7 -24L-14 -150L-2 -150L0 -24Z", 3),
        S.shape(ell(0, 0, 34, 30)), S.line(ell(0, 0, 22, 19), 1.2, op=0.7),
        S.shape(ell(-112, 26, 18, 18)), S.line(ell(-112, 26, 10, 10), 1.2), S.hatch(ell(-112, 26, 10, 10), 2),
        S.shape(ell(112, 26, 18, 18)), S.line(ell(112, 26, 10, 10), 1.2), S.hatch(ell(112, 26, 10, 10), 2),
    ]
    return [contrails, *parts]


def travel(S):
    w = []
    # Sky above the clouds (drawn first; the camera only gets here at the end).
    rays = S.g(S.line("".join(f"M{230 + 44 * math.cos(a):.1f} {-1080 + 44 * math.sin(a):.1f}L{230 + 62 * math.cos(a):.1f} {-1080 + 62 * math.sin(a):.1f}"
                              for a in [i * math.pi / 6 for i in range(12)]), 1.8, color=S.pop),
               loops=[S.loop("transform", [(0, "translate(230px,-1080px) rotate(0deg) translate(-230px,1080px)"),
                                           (12, "translate(230px,-1080px) rotate(360deg) translate(-230px,1080px)")], 12)])
    w += [S.circ(230, -1080, 32, fill=S.bg, color=S.pop, w=2), rays,
          S.line("M-300 -1150q40 -10 80 0M-120 -1190q30 -8 60 0M90 -1210q40 -10 80 0", 1.2, op=0.5)]
    tops = "M-800 -860" + "".join(f"q{30 + rnd(i) * 20:.0f} {-26 - rnd(i * 5) * 18:.0f} {60 + rnd(i) * 30:.0f} 0" for i in range(26)) + \
        "L1200 -700L-800 -700Z"
    w += [S.shape(tops), S.hatch("M-800 -840H1200V-700H-800Z", 3.5, op=0.45)]
    # Cloud band the camera rises through.
    clouds = []
    for row, (y, s) in enumerate([(-770, 1.5), (-700, 1.3), (-630, 1.15), (-560, 1.0)]):
        for i in range(9):
            x = -560 + i * 150 + (row % 2) * 70 + rnd(i * 11 + row) * 30
            clouds.append(_cloud(S, x, y, s))
    w.append(S.g(*clouds, loops=[S.loop("transform", [(0, "translateX(0px)"), (9, "translateX(-40px)"), (18, "translateX(0px)")],
                                        18, "ease-in-out")]))
    # Ground: hills, road, guardrail.
    w += [S.line("M-800 -300Q-600 -360 -420 -310T-60 -318T280 -312T620 -320T900 -300", 1.4),
          S.hatch("M-800 -300Q-600 -360 -420 -310T-60 -318T280 -312T620 -320T900 -300V-292H-800Z", 3, op=0.6),
          S.line("".join(f"M{x} -300v-14m-6 0a6 7 0 1 1 12 0a6 7 0 1 1 -12 0" for x in range(-640, 700, 47)), 1.0, op=0.7),
          S.hatch("M-900 80L-8 -300L-900 -300Z", 4, op=0.35), S.hatch("M900 80L8 -300L900 -300Z", 4, op=0.35),
          S.shape("M-700 80L-6 -300L6 -300L700 80Z"),
          S.line("M300 -16L12 -296M320 -6L14 -290", 1.4),
          S.line("".join(f"M{300 - i * 30:.0f} {-16 - i * 29.4:.0f}v14" for i in range(9)), 1.2)]
    lanes = "".join(S.g(S.line(d, 3, dash="34 26"),
                        loops=[S.loop("stroke-dashoffset", [(0, "0"), (0.45, "60")], 0.45)])
                    for d in ["M0 80L0 -300", "M-250 80L-3 -300", "M250 80L3 -300"])
    w.append(lanes)
    streaks = S.g(S.line("M-60 10v24M40 30v26M120 4v20M-130 36v22", 1.2, op=0.6),
                  loops=[S.loop("transform", [(0, "translateY(-30px)"), (0.3, "translateY(40px)")], 0.3),
                         S.loop("opacity", [(0, "1"), (0.3, "0")], 0.3)])
    w.append(streaks)
    w.append(S.g(*_car(S), tr=[(0, tf()), (4.9, tf()), (6.0, tf(y=-60, sx=0.72), "ease-in"), (7.5, tf(y=-212, sx=0.22)),
                               (9.0, tf(y=-286, sx=0.06)), (9.6, tf(y=-293, sx=0.03))], ease="linear"))
    w.append(S.g(*_plane(S), tr=[(10.3, tf(0, -690, sx=3.4)), (11.3, tf(-10, -960, sx=1.15), "ease-out"),
                                 (12.5, tf(40, -1088, sx=0.44)), (13, tf(54, -1118, sx=0.32))],
                 show=[(10.3, 99)], ease="linear"))
    camera = [(0, cam(172, -40, 3.4)), (2.6, cam(172, -42, 3.5)), (4.8, cam(0, -130, 1.05)), (7.2, cam(0, -160, 1.05)),
              (9.6, cam(0, -660, 1.0)), (10.8, cam(0, -1000, 1.0)), (13, cam(10, -1010, 1.02))]
    return S.g(*w, tr=camera)


# =============================================================================
# 4. Bowling: a scrapbook collage of strikes, every panel on its own loop.
# =============================================================================

PIN = "M-9 0C-14 -20 -16 -40 -10 -58C-6 -66 -6 -72 -8 -80C-10 -92 -4 -100 0 -100C4 -100 10 -92 8 -80C6 -72 6 -66 10 -58C16 -40 14 -20 9 0Z"


def _strike_panel(S, x, y, w, h, period, delay, tilt, cid):
    loop = lambda frames, prop="transform", ease="linear": S.loop(prop, frames, period, ease, delay)
    T = lambda f: f * period
    unit = h * 0.3 / 100
    rows = [(1, h * 0.70, 1.0), (2, h * 0.655, 0.92), (3, h * 0.615, 0.85), (4, h * 0.58, 0.78)]
    cx = w / 2
    pins = []
    n = 0
    for count, py, sc in reversed(rows):
        for j in range(count):
            px = cx + (j - (count - 1) / 2) * w * 0.085 * sc
            n += 1
            ang = (rnd(n * 3 + cid) - 0.5) * 520
            dx = (px - cx) * 2.2 + (rnd(n + cid * 7) - 0.5) * w * 0.4
            dy = -h * (0.25 + rnd(n * 5 + cid) * 0.35)
            s = unit * sc
            art = f'<g transform="translate({px:.1f} {py:.1f}) scale({s:.4f})">' + S.shape(PIN, w=1.4) + \
                S.line("M-8 -74H8M-7 -70H7", 1.4, color=S.pop) + "</g>"
            fly = loop([(0, "translate(0px,0px) rotate(0deg)"), (T(0.45), "translate(0px,0px) rotate(0deg)"),
                        (T(0.62), f"translate({dx:.1f}px,{dy:.1f}px) rotate({ang:.0f}deg)"),
                        (T(0.8), f"translate({dx * 1.2:.1f}px,{dy * 0.2:.1f}px) rotate({ang * 1.3:.0f}deg)"),
                        (period, f"translate({dx * 1.2:.1f}px,{dy * 0.2:.1f}px) rotate({ang * 1.3:.0f}deg)")], "transform", "ease-out")
            fade = loop([(0, "1"), (T(0.8), "1"), (T(0.82), "0"), (T(0.96), "0"), (T(0.98), "1")], "opacity")
            pins.append(f'<g style="transform-box:fill-box;transform-origin:50% 100%;animation:{fly},{fade}">{art}</g>')
    ball = S.circ(0, 0, w * 0.07, fill=S.pop, w=1.6) + S.line(f"M{-w * 0.02:.1f} {-w * 0.025:.1f}h0.1M{w * 0.012:.1f} {-w * 0.03:.1f}h0.1M{-w * 0.002:.1f} {-w * 0.005:.1f}h0.1", 3.4)
    roll = loop([(0, f"translate({w * 0.66:.1f}px,{h * 1.08:.1f}px) scale(1.3)"),
                 (T(0.25), f"translate({w * 0.64:.1f}px,{h * 0.86:.1f}px) scale(0.95)"),
                 (T(0.45), f"translate({w * 0.54:.1f}px,{h * 0.66:.1f}px) scale(0.55)"),
                 (T(0.6), f"translate({w * 0.52:.1f}px,{h * 0.45:.1f}px) scale(0.4)"),
                 (period, f"translate({w * 0.52:.1f}px,{h * 0.45:.1f}px) scale(0.4)")])
    ball_show = loop([(0, "1"), (T(0.6), "0"), (T(0.97), "1")], "opacity")
    burst = S.g(S.line(f"M{w * 0.47:.1f} {h * 0.6:.1f}l-14 -8M{w * 0.6:.1f} {h * 0.6:.1f}l14 -8M{w * 0.535:.1f} {h * 0.5:.1f}v-14", 2,
                       color=S.pop), loops=[loop([(0, "0"), (T(0.45), "1"), (T(0.58), "0")], "opacity")])
    mark = S.g(S.line(f"M{w - 34} 12l20 20m0 -20l-20 20", 3, color=S.pop),
               loops=[loop([(0, "0"), (T(0.5), "1"), (T(0.9), "0")], "opacity")])
    sweep = S.g(S.shape(f"M{w * 0.15:.1f} {h * 0.2:.1f}H{w * 0.85:.1f}V{h * 0.27:.1f}H{w * 0.15:.1f}Z"),
                loops=[loop([(0, "translateY(-60px)"), (T(0.84), "translateY(-60px)"), (T(0.9), f"translateY({h * 0.42:.0f}px)"),
                             (T(0.96), "translateY(-60px)")], "transform", "ease-in-out")])
    lane = (S.hatch(f"M0 0H{w}V{h * 0.42:.1f}H0Z", 2.6, op=0.8) +
            S.line(f"M{w * 0.05:.1f} {h}L{w * 0.32:.1f} {h * 0.6:.1f}M{w * 0.95:.1f} {h}L{w * 0.68:.1f} {h * 0.6:.1f}"
                   f"M0 {h * 0.58:.1f}H{w}", 1.3) +
            S.line("".join(f"M{w * (0.12 + i * 0.076):.1f} {h}L{w * (0.34 + i * 0.032):.1f} {h * 0.6:.1f}" for i in range(11)), 0.8, op=0.3))
    clip = f"bc{cid}"
    S.svg.defs.append(f'<clipPath id="{clip}"><rect x="0" y="0" width="{w}" height="{h}"/></clipPath>')
    tape = S.shape(f"M{w * 0.42:.1f} -8H{w * 0.58:.1f}V8H{w * 0.42:.1f}Z", fill=S.pop, op=0.55)
    inner = (f'<g clip-path="url(#{clip})">' + lane + "".join(pins) +
             f'<g style="animation:{roll},{ball_show}">{ball}</g>' + burst + sweep + mark + "</g>")
    return (f'<g transform="translate({x} {y}) rotate({tilt} {w / 2} {h / 2})">' +
            S.shape(f"M3 3H{w + 3}V{h + 3}H3Z", fill=S.ink) + S.shape(f"M0 0H{w}V{h}H0Z") + inner + tape + "</g>")


def bowling(S):
    panels = [(298, 16, 262, 92, 2.6, 0.0, -1.2), (574, 12, 248, 124, 3.1, 1.1, 1.4),
              (402, 124, 204, 214, 2.9, 0.6, 0.8), (622, 148, 198, 188, 2.3, 1.7, -1.5)]
    return "".join(_strike_panel(S, *p, cid=i) for i, p in enumerate(panels))


# =============================================================================
# 5. Golf: the tee goes in, a smooth drive, and the camera rides it to an ace.
# =============================================================================

def golf(S):
    w = []
    w += [S.line("M-700 -305Q-500 -340 -300 -312T60 -320T420 -308T800 -312", 1.3),
          S.hatch("M-700 -305Q-500 -340 -300 -312T60 -320T420 -308T800 -312V-298H-700Z", 2.6, op=0.6)]
    trees = []
    for side in (-1, 1):
        for i in range(14):
            u = i / 13
            x = 40 + side * (300 - 270 * u ** 0.6) + rnd(i * 3 + side) * 10
            y = -40 - 260 * u ** 0.75
            s = 1.4 - 1.25 * u
            trees.append(S.line(f"M{x:.1f} {y:.1f}v{-14 * s:.1f}", 1.4) +
                         S.shape(ell(x, y - 30 * s, 16 * s, 20 * s)) + S.hatch(ell(x + 3 * s, y - 26 * s, 12 * s, 14 * s), 2.6))
    w += [S.line("M-260 -40L22 -300M300 -40L62 -300", 1.4), S.hatch("M-700 80L-260 -40L22 -300L-700 -300Z", 3.4, op=0.3),
          S.hatch("M800 80L300 -40L62 -300L800 -300Z", 3.4, op=0.3), *reversed(trees)]
    w += [S.line("".join(f"M{-150 + i * 34} -60L{24 + i * 1.2:.1f} -300" for i in range(10)), 0.8, op=0.2)]
    w += [S.hatch(ell(18, -289, 7, 1.6), 0.8), S.line(ell(18, -289, 7, 1.6), 0.9),
          S.shape(ell(44, -292, 30, 7)), S.line(ell(44, -292, 22, 4.6), 0.8, op=0.5, dash="3 3"),
          S.line(ell(44, -292, 13, 2.6), 0.8, op=0.4, dash="2 3"), S.shape(ell(45, -291.2, 1.5, 0.55), fill=S.ink, w=0.6)]
    flag = S.g(S.shape("M45 -312L54 -309L45 -306Z", fill=S.pop, w=0.8),
               loops=[S.loop("transform", [(0, "translate(45px,0px) scale(1,1) translate(-45px,0px)"),
                                           (0.6, "translate(45px,0px) scale(0.7,1) translate(-45px,0px)"),
                                           (1.2, "translate(45px,0px) scale(1,1) translate(-45px,0px)")], 1.2, "ease-in-out")])
    w.append(S.g(S.line("M45 -291.2V-312", 0.9), flag,
                 tr=[(0, tf()), (13.0, tf()), (13.15, tf(r=5, px=45, py=-291)), (13.35, tf(r=-4, px=45, py=-291)), (13.6, tf())]))

    # Tee box: everything here is drawn around the tee at (0, 0), then lifted TY so the
    # opening shot shows both the tee and the fairway out to the horizon.
    TY = -62
    tb = [S.hatch("M-500 -38H560V160H-500Z", 4.5, op=0.25),
          S.shape(ell(-180, 22, 20, 18)), S.hatch(ell(-180, 22, 20, 18), 2.6), S.shape(ell(190, 22, 20, 18)), S.hatch(ell(190, 22, 20, 18), 2.6)]
    tee_art = S.shape("M-1.6 -2L-1.2 14L1.2 14L1.6 -2Z", w=1.0) + S.shape("M-5 -4Q0 -1 5 -4L2 -1H-2Z", w=1.0)
    ball_art = S.circ(0, 0, 9) + S.line("M-4 -3h0.1M2 -5h0.1M4 1h0.1M-2 3h0.1M-6 2h0.1", 2)
    tb.append(S.g(tee_art, S.g(ball_art, attrs=' transform="translate(0 -13)"'), show=[(2.75, 6.38)]))
    tb.append(S.mover([(6.38, 0, 0, 1), (6.75, 34, -40, 0.8)], tee_art, show=[(6.38, 6.8)], rot=lambda t: (t - 6.38) * 900))
    grass = "".join(f"M{x:.1f} {y:.1f}l{-3 + rnd(i) * 2:.1f} {-8 - rnd(i * 2) * 6:.1f}M{x + 2:.1f} {y:.1f}l{2 + rnd(i * 3) * 2:.1f} {-7 - rnd(i * 4) * 6:.1f}"
                    for i, (x, y) in enumerate((-260 + (i % 40) * 13 + rnd(i) * 6, 6 + (i // 40) * 16 + rnd(i * 9) * 6) for i in range(240)))
    tb.append(S.line(grass, 1.1, op=0.8))

    # A hand brings the tee and ball in from the top left, presses the tee in, and lets go.
    hand = [S.tube("M-30 -52L-200 -250", 20), S.shape("M-46 -62C-62 -46 -54 -18 -32 -16C-16 -14 -6 -26 -10 -42C-14 -56 -30 -66 -46 -62Z"),
            S.line("M-40 -52Q-30 -48 -24 -40", 1.0, op=0.7),
            S.tube("M-30 -22L-14 -16L-6 -12", 7, 0.8), S.tube("M-18 -48L-4 -40L6 -30", 7, 0.8), S.tube("M-24 -36L-8 -28L2 -22", 6.5, 0.8)]
    carried = S.g(tee_art, S.g(ball_art, attrs=' transform="translate(0 -13)"'), show=[(0, 2.75)])
    tb.append(S.g(*hand, carried, tr=[(0, tf(-190, -230)), (1.2, tf(-190, -230)), (2.1, tf(0, -8), "ease-out"),
                                      (2.5, tf(0, 0)), (2.75, tf(0, 0)), (3.6, tf(-200, -240), "ease-in")]))

    # The driver sits between the ball and the camera, then one smooth swing.
    head_d = "M-66 18C-70 -6 -40 -22 -4 -22C34 -22 64 -8 60 14C56 30 -60 34 -66 18Z"
    club = [S.tube("M-56 -6L-240 -330", 7), S.shape(head_d), S.hatch("M-60 10C-60 -2 -40 -14 -6 -16C28 -16 50 -6 52 8Z", 3.2, op=0.7),
            S.line("M-4 -20V4", 1.6, color=S.pop), S.line("M-62 16C-30 26 30 26 58 12", 1.0, op=0.7)]
    tb.append(S.g(*club, tr=[(0, tf(-260, 120)), (3.6, tf(-260, 120)), (4.6, tf(-6, 10), "ease-out"), (4.9, tf(-12, 10)),
                             (5.15, tf(-2, 10)), (5.4, tf(-6, 10)), (6.15, tf(-230, -300, r=-28, px=-6, py=10), "ease-out"),
                             (6.38, tf(-6, 10), "ease-in"), (6.62, tf(70, -110, sx=0.55, r=26, px=-6, py=10)),
                             (15, tf(70, -110, sx=0.55, r=26, px=-6, py=10))],
                  show=[(3.6, 6.62)]))
    tb.append(S.g(S.line("M-10 -6l-10 -14M6 -8l8 -16M-2 -4l-2 -18M14 -4l14 -10", 1.4),
                  tr=[(6.38, tf()), (6.8, tf(0, -24, sx=1.4))], show=[(6.38, 6.85)]))
    w.append(S.place(0, TY, 1, *tb))

    # Ball flight to the green, then a breaking putt-like roll into the cup.
    flight = arc_path(6.38, 9.9, (0, TY - 13), (30, -292.6), 170, 1.0, 0.09, steps=18, ease=lambda u: 1 - (1 - u) ** 1.6)
    roll = [(10.1, 31.5, -294.6, 0.09), (10.3, 33, -292.6, 0.09), (11.2, 37.5, -291.4, 0.09), (12.0, 41.5, -292.3, 0.09),
            (12.7, 44.3, -291.6, 0.09), (13.0, 45, -291.3, 0.08)]
    w.append(S.mover(flight + roll, ball_art, show=[(6.38, 13.02)]))

    # The camera rides forward with the swing and tracks the ball all the way to the green.
    camera = [(0, cam(12, -160, 1.15)), (1.6, cam(6, -130, 1.25)), (5.4, cam(4, -128, 1.3)), (6.3, cam(4, -130, 1.32))]
    for t, x, y, sc in flight[2::2]:
        u = (t - 6.38) / (9.9 - 6.38)
        camera.append((t, cam(x * (1 - u) + 41 * u, y * (1 - u * 0.35) + (-292) * u * 0.35, 1.4 + 4.8 * u ** 2)))
    camera += [(10.4, cam(41, -292, 6.2)), (13.0, cam(44, -293, 6.8)), (15, cam(44, -293, 6.9))]
    world = S.g(*w, tr=camera, ease="linear")
    ace = S.g(S.text(440, 62, "HOLE IN ONE!", 30, fill=S.pop),
              S.line("M318 40l10 6M326 26l4 10M562 40l-10 6M554 26l-4 10M440 16v10", 2, color=S.pop),
              tr=[(13.05, tf(sx=0.6, px=440, py=52)), (13.35, tf(sx=1.08, px=440, py=52), "ease-out"), (13.6, tf(px=440, py=52))],
              show=[(13.05, 99)])
    return world + ace


SCENES = {"baseball": baseball, "basketball": basketball, "travel": travel, "bowling": bowling, "golf": golf}
