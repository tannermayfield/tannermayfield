"""Builds the SVG cards and README.md for github.com/tannermayfield.

Every card is rendered twice (dark + light) and README.md swaps them with
<picture> + prefers-color-scheme. GitHub shows SVGs through <img>, so fonts are
subset and embedded as base64 WOFF and all motion is plain CSS keyframes.

    python tools/build_profile.py      # rewrites assets/*.svg and README.md
"""

import base64
import hashlib
import html
import io
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from sketch_scenes import SCENES, Sketch

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
ASSETS = ROOT / "assets"

# --------------------------------------------------------------------------
# Content. Everything below comes from tech-portfolio/data/*.ts; edit freely.
# --------------------------------------------------------------------------

USER = "tannermayfield"
SITE = "https://tannermayfield.dev"
EMAIL = "tannerjamesmayfield@gmail.com"

HERO = {
    "location": "PROVO, UTAH",
    "name": ["TANNER", "MAYFIELD"],
    "tagline": ["Information Systems student using", "data, software, and AI tools", "to meet business needs."],
}

# now.txt rows: (key, value). An empty key continues the row above.
NOW = [
    ("scheming", "BravOS"),
    ("", "Sandbox for AI tools"),
    ("building", "Polybot"),
    ("", "AI language learning"),
    ("dabbling", "Airline Intelligence"),
    ("", "ETL + delay-risk models"),
    ("studying", "IS at BYU, class of '28"),
    ("", "+ Spanish minor"),
    ("teaching", "Spanish at the MTC"),
]

# Optional line of Markdown under the buttons. Leave empty to skip it.
INTRO = ""

BUTTONS = [
    ("site", "Portfolio", SITE),
    ("resume", "Résumé", f"{SITE}/resume/"),
    ("linkedin", "LinkedIn", "https://www.linkedin.com/in/tanner-mayfield"),
    ("email", "Email", f"mailto:{EMAIL}"),
]

WORK_HEAD = ("SELECTED WORK", "Four things I'm building")

# Each terminal is (command, progress label, (result key, result value)).
# Taglines wrap onto a second line when they need to.
WORK = [
    {
        "slug": "polybot",
        "title": "Polybot",
        "pill": "IN DEVELOPMENT",
        "tagline": "A personalized language-learning app, with a Chrome extension that turns the web into language practice",
        "stack": ["JavaScript", "Chrome MV3", "Python"],
        "url": f"https://github.com/{USER}/PolyBot",
        "term": ('$ select "¿qué tal?"', "saving", ("added", "My Path · Spanish")),
    },
    {
        "slug": "bravos",
        "title": "BravOS",
        "pill": "IN DEVELOPMENT",
        "tagline": "An adaptive AI workspace built around what you're doing that automates daily organizational tasks",
        "stack": ["Claude Code", "Codex", "Spec-driven"],
        "url": f"{SITE}/projects/bravos/",
        "term": ("$ focus today", "assembling", ("open", "calendar + tasks")),
    },
    {
        "slug": "airline",
        "title": "Airline Intelligence",
        "pill": "TINKERING",
        "tagline": "Turning 631,970 messy flight records into data people trust, while I play with ETL and other tools for my own growth",
        "stack": ["Python", "PostgreSQL", "AWS", "Tableau"],
        "url": f"https://github.com/{USER}/airlines-operations-intelligence-platform",
        "term": ("$ load bts_jul_2026", "validating", ("airports", "352 · 12 airlines")),
    },
    {
        "slug": "portfolio",
        "title": "tannermayfield.dev",
        "pill": "LIVE",
        "tagline": "My portfolio, soon with live previews so you can try my apps without leaving the page",
        "stack": ["Next.js", "TypeScript", "Tailwind"],
        "url": SITE,
        "term": ("$ preview polybot", "embedding", ("status", "coming soon")),
    },
]

# Toolbox rows: (label, [(chip text, icon file or None)]).
STACK = [
    ("DATA", [("PostgreSQL", "postgresql-original"), ("pandas", "pandas-original"), ("scikit-learn", "scikitlearn-original"),
              ("Jupyter", "jupyter-original"), ("Tableau", "si-tableau")]),
    ("DEV LANGUAGES", [("Python", "python-original"), ("JavaScript", "javascript-original"),
                       ("TypeScript", "typescript-original"), ("HTML", "html5-original"), ("CSS", "css3-original")]),
    ("FULL-STACKS", [("React", "react-original"), ("Next.js", "si-nextdotjs"), ("Tailwind CSS", "tailwindcss-original"),
                     ("Node.js", "nodejs-original"), ("Supabase", "supabase-original")]),
    ("CLOUD & TOOLS", [("AWS", "amazonwebservices-original-wordmark"), ("Git", "git-original"),
                       ("GitHub", "github-original"), ("Microsoft Office Suite", "si-microsoftoffice")]),
]

ABOUT_HEAD = ("ABOUT ME", "Beyond the code")

# Hobbies cycle in this order: (scene key, title, description, seconds on screen).
# Each scene is drawn in tools/sketch_scenes.py under the same key.
HOBBIES = [
    ("baseball", "Baseball",
     "I played throughout high school on a travel team, and I am a die-hard Atlanta Braves fan.", 16),
    ("basketball", "Basketball",
     "This always has and will always be my favorite activity to do with my friends. I am always down to ball!", 15),
    ("travel", "Travel",
     "As a kid, my favorite memories have come while traveling the world with my family. Now, my wife and I travel as "
     "much as our schedules allow.", 13),
    ("bowling", "Bowling",
     "I am humbly a part of the 200-club at the BYU bowling alley. I got it first try, and now I am going for 300!", 16),
    ("golf", "Golf",
     "Growing up, I thought golf was boring. Now that I am older... it is slightly less boring. That still never stops "
     "me from playing a round of 18 with my family.", 15),
]

FOOTER = {
    "label": "CONTACT",
    "title": "Let’s build something.",
    "sub": "Looking for internships in data, full-stack development, and AI automation. Email is fastest.",
}

# --------------------------------------------------------------------------
# Themes (Tokyo Night for dark, cream + yellow for light, as in the reference)
# --------------------------------------------------------------------------

THEMES = {
    "dark": dict(bg="#1A1B26", ink="#C0CAF5", muted="#A9B1D6", faint="#949EC8", accent="#E0AF68",
                 panel="#16161E", head="#24283B", alt="#292B39", onacc="#1A1B26", key="#E0AF68", pop="#E0AF68",
                 grid="rgba(192,202,245,0.07)", glow="rgba(192,202,245,0.05)"),
    "light": dict(bg="#F7F5EE", ink="#161616", muted="rgba(22,22,22,0.62)", faint="rgba(22,22,22,0.45)",
                  accent="#FACC00", panel="#FFFFFF", head="#FDF7C4", alt="#FDF7C4", onacc="#161616", key="#161616", pop="#E4572E",
                  grid="rgba(22,22,22,0.07)", glow="rgba(255,255,255,0.8)"),
}

# Icons that are black/monochrome and need recoloring on dark backgrounds.
DARK_ON_DARK = {"si-nextdotjs", "github-original", "pandas-original"}
BRAND_FILL = {"si-tableau": "#E97627", "si-nextdotjs": "#161616", "si-microsoftoffice": "#D83B01"}

# --------------------------------------------------------------------------
# Fonts: instance the variable fonts per weight, measure, subset, embed.
# --------------------------------------------------------------------------

FONT_FILES = {"G": TOOLS / "fonts" / "SpaceGrotesk.ttf", "M": TOOLS / "fonts" / "JetBrainsMono.ttf",
              "S": TOOLS / "fonts" / "Yellowtail.ttf"}  # S: script, for the ballpark wordmark
_instances: dict = {}


def _instance(fam, weight):
    key = (fam, weight)
    if key not in _instances:
        font = TTFont(FONT_FILES[fam])
        if "fvar" in font:
            font = instancer.instantiateVariableFont(font, {"wght": weight})
        buf = io.BytesIO()
        font.save(buf)
        _instances[key] = (buf.getvalue(), font)
    return _instances[key]


def measure(text, fam="G", weight=500, size=14, ls=0.0):
    """Advance width in px (kerning ignored; letter-spacing in em, applied per char like SVG)."""
    _, font = _instance(fam, weight)
    cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    units = sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in text)
    return units * size / upm + ls * size * len(text)


def _woff(fam, weight, chars):
    raw, _ = _instance(fam, weight)
    font = TTFont(io.BytesIO(raw))
    opts = subset.Options()
    opts.layout_features = ["kern"]
    opts.name_IDs = []
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)))
    sub.subset(font)
    font.flavor = "woff"
    out = io.BytesIO()
    font.save(out)
    return base64.b64encode(out.getvalue()).decode()


# --------------------------------------------------------------------------
# A tiny SVG builder that tracks which glyphs each font weight needs.
# --------------------------------------------------------------------------


def esc(s):
    return html.escape(s, quote=True)


class Svg:
    def __init__(self, w, h, title, t):
        self.w, self.h, self.title, self.t = w, h, title, t
        self.defs, self.css, self.body = [], [], []
        self.used: dict = {}
        self._k = 0

    def text(self, x, y, s, fam="G", weight=500, size=14, fill=None, ls=None, anchor=None, extra=""):
        self.used.setdefault((fam, weight), set()).update(s)
        attrs = f'x="{x:.2f}" y="{y:.2f}" font-family="{fam}" font-weight="{weight}" font-size="{size}" ' \
                f'fill="{fill or self.t["ink"]}" xml:space="preserve"'
        if ls:
            attrs += f' letter-spacing="{ls}em"'
        if anchor:
            attrs += f' text-anchor="{anchor}"'
        return f"<text {attrs} {extra}>{esc(s)}</text>"

    def spans(self, x, y, parts, fam="M", weight=400, size=12, extra=""):
        """One <text> with differently-colored tspans: parts = [(string, fill)]."""
        for s, _ in parts:
            self.used.setdefault((fam, weight), set()).update(s)
        inner = "".join(f'<tspan fill="{f}">{esc(s)}</tspan>' for s, f in parts)
        return f'<text x="{x:.2f}" y="{y:.2f}" font-family="{fam}" font-weight="{weight}" font-size="{size}" ' \
               f'xml:space="preserve" {extra}>{inner}</text>'

    def reveal(self, cycle, on, off=None, loop=False):
        """Style for a step-end opacity reveal; returns the inline style and registers keyframes."""
        self._k += 1
        name = f"k{self._k}"
        on_pct = 100 * on / cycle
        frames = f"0%{{opacity:0}}{on_pct:.3f}%{{opacity:1}}"
        if off is not None:
            frames += f"{100 * off / cycle:.3f}%{{opacity:0}}"
        frames += "100%{opacity:" + ("0" if off is not None else "1") + "}"
        self.css.append(f"@keyframes {name}{{{frames}}}")
        count = "infinite" if loop else "1"
        return f'style="opacity:0;animation:{name} {cycle}s step-end {count} forwards"'

    def render(self):
        faces = "".join(
            f"@font-face{{font-family:{fam};font-weight:{w};src:url(data:font/woff;base64,{_woff(fam, w, chars)}) format('woff')}}\n"
            for (fam, w), chars in sorted(self.used.items())
        )
        css = faces + "\n".join(dict.fromkeys(self.css)) + \
            "\n@media (prefers-reduced-motion: reduce){*{animation:none!important}.fin{opacity:1!important}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'role="img" aria-labelledby="t">\n<title id="t">{esc(self.title)}</title>\n'
            f'<defs>{"".join(self.defs)}</defs>\n<style>\n{css}\n</style>\n' + "\n".join(self.body) + "\n</svg>\n"
        )


def wrap(text, width, fam="G", weight=400, size=14):
    """Greedy word wrap using real glyph widths."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and measure(trial, fam, weight, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def card(svg, w, h, fill, grid=True, r=14, off=6):
    """Bordered card with a solid offset shadow (the neo-brutalist look), optional grid texture."""
    t = svg.t
    out = f'<rect x="{2 + off}" y="{2 + off}" width="{w}" height="{h}" rx="{r}" fill="{t["ink"]}"/>' \
          f'<rect x="2" y="2" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{t["ink"]}" stroke-width="2"/>'
    if grid:
        svg.defs.append(
            f'<pattern id="gp" width="40" height="40" patternUnits="userSpaceOnUse" x="2" y="2">'
            f'<path d="M40 0V40H0" fill="none" stroke="{t["grid"]}"/></pattern>'
            f'<radialGradient id="gr" cx="0.5" cy="0" r="0.8"><stop offset="0" stop-color="{t["glow"]}"/>'
            f'<stop offset="1" stop-color="{t["glow"]}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="gc"><rect x="2" y="2" width="{w}" height="{h}" rx="{r}"/></clipPath>'
        )
        out += f'<g clip-path="url(#gc)"><rect x="2" y="2" width="{w}" height="{h}" fill="url(#gp)"/>' \
               f'<rect x="2" y="2" width="{w}" height="{h}" fill="url(#gr)"/></g>' \
               f'<rect x="2" y="2" width="{w}" height="{h}" rx="{r}" fill="none" stroke="{t["ink"]}" stroke-width="2"/>'
    svg.body.append(out)


def arrow_right(cx, cy, color, size=5):
    return f'<path d="M{cx - size} {cy}H{cx + size}M{cx + 1} {cy - 4}L{cx + size} {cy}L{cx + 1} {cy + 4}" ' \
           f'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'


def arrow_up_right(cx, cy, color, size=7):
    return f'<path d="M{cx - size} {cy + size}L{cx + size} {cy - size}M{cx - 3} {cy - size}H{cx + size}V{cy + 3}" ' \
           f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------


def hero(t):
    lines = [f"{k} {v}".strip() for k, v in NOW]
    title = f"Tanner Mayfield, Provo, Utah. {' '.join(HERO['tagline'])} A now.txt window: {'; '.join(lines)}."
    W, H = 840, 404
    svg = Svg(W, H, title, t)
    svg.css += ["@keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}",
                "@keyframes swipe{from{transform:scaleX(0)}to{transform:scaleX(1)}}"]
    card(svg, 830, 394, t["bg"])
    b = svg.body

    loc = HERO["location"]
    b.append(svg.text(40, 58, loc, weight=500, size=11, fill=t["muted"], ls=0.16))
    b.append(f'<line x1="{40 + measure(loc, size=11, ls=0.16) + 14:.1f}" y1="54" x2="460" y2="54" stroke="{t["faint"]}" stroke-width="1"/>')

    # Name: as large as possible (max 100px) while staying clear of the now.txt window.
    widest = max(measure(n, weight=700, size=1, ls=-0.03) for n in HERO["name"])
    size = min(100, int(430 / widest))
    for i, name in enumerate(HERO["name"]):
        y = 146 + i * 0.86 * size
        b.append(f'<g style="animation:rise .7s cubic-bezier(.16,1,.3,1) {0.1 + i * 0.12:.2f}s both">'
                 + svg.text(36, y, name, weight=700, size=size, ls=-0.03) + "</g>")

    first, bold, last = HERO["tagline"]
    b.append(svg.text(40, 294, first, weight=400, size=22))
    x = 40
    for i, word in enumerate(bold.split(" ")):
        b.append(svg.text(x, 324, word, weight=700, size=22, extra='class="fin" ' + svg.reveal(3, 0.6 + i * 0.14)))
        x += measure(word + " ", weight=700, size=22)
    b.append(svg.text(40, 354, last, weight=400, size=22))
    b.append(f'<rect x="40" y="329" width="{measure(bold, weight=700, size=22):.1f}" height="5" rx="1.5" fill="{t["accent"]}" '
             f'style="transform-box:fill-box;transform-origin:left;animation:swipe .6s cubic-bezier(.16,1,.3,1) 1.5s both"/>')

    # now.txt window, vertically centred now that nothing sits on top of it.
    ww, wh = 284, 58 + (len(NOW) - 1) * 19.5 + 39
    wx, wy = 496, round((H - wh) / 2 - 4)
    b.append(f'<rect x="{wx + 6}" y="{wy + 6}" width="{ww}" height="{wh}" rx="14" fill="{t["ink"]}"/>'
             f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="14" fill="{t["panel"]}" stroke="{t["ink"]}" stroke-width="2"/>'
             f'<path d="M{wx} {wy + 32}V{wy + 14}a14 14 0 0 1 14-14h{ww - 28}a14 14 0 0 1 14 14V{wy + 32}z" '
             f'fill="{t["head"]}" stroke="{t["ink"]}" stroke-width="2"/>'
             + "".join(f'<circle cx="{wx + 18 + i * 15}" cy="{wy + 16}" r="4.2" fill="none" stroke="{t["ink"]}" stroke-width="1.6"/>' for i in range(3)))
    b.append(svg.text(wx + 70, wy + 20.5, "now.txt", weight=500, size=12.5, fill=t["muted"]))
    for i, (k, v) in enumerate(NOW):
        parts = [(k.ljust(11), t["key"]), (v, t["ink"] if k else t["muted"])]
        b.append(svg.spans(wx + 20, wy + 58 + i * 19.5, parts, extra='class="fin" ' + svg.reveal(3, 1.0 + i * 0.09)))
    return svg


def button(t, label):
    tw = measure(label, size=15)
    w = 22 + tw + 16 + 30 + 4
    svg = Svg(round(w + 13), 56, label, t)
    svg.css.append("@keyframes go{0%,70%,100%{transform:translateX(0)}82%{transform:translateX(3px)}}")
    cx = w - 19
    svg.body.append(
        f'<rect x="6" y="8" width="{w:.1f}" height="44" rx="22" fill="{t["ink"]}"/>'
        f'<rect x="2" y="4" width="{w:.1f}" height="44" rx="22" fill="{t["panel"]}" stroke="{t["ink"]}" stroke-width="2"/>'
    )
    svg.body.append(svg.text(22, 31, label, size=15))
    svg.body.append(f'<circle cx="{cx:.1f}" cy="26" r="15" fill="{t["accent"]}" stroke="{t["ink"]}" stroke-width="1.5"/>'
                    f'<g style="animation:go 2.4s ease-in-out infinite">{arrow_right(round(cx, 1), 26, t["onacc"])}</g>')
    return svg


def work_head(t):
    label, title = WORK_HEAD
    svg = Svg(840, 96, f"{label.capitalize()}: {title}", t)
    svg.body += [svg.text(4, 30, label, size=11, fill=t["muted"], ls=0.16),
                 svg.text(4, 70, title, weight=700, size=30, ls=-0.015),
                 f'<line x1="4" y1="94" x2="836" y2="94" stroke="{t["ink"]}" stroke-width="2"/>']
    return svg


def work_row(t, i, p):
    cmd, label, (rk, rv) = p["term"]
    title = f"{i + 1:02d} {p['title']}: {p['tagline']}. {p['pill'].capitalize()}. Built with {', '.join(p['stack'])}."
    tag = wrap(p["tagline"], 428)
    extra_h = 19 * (len(tag) - 1)
    svg = Svg(840, 124 + extra_h, title, t)
    svg.css.append("@keyframes out{0%,72%,100%{transform:translate(0,0)}84%{transform:translate(3px,-3px)}}")
    b = svg.body
    b.append(svg.text(4, 76, f"{i + 1:02d}", weight=700, size=54, fill="none", extra=f'stroke="{t["ink"]}" stroke-width="1.3"'))
    b.append(svg.text(104, 48, p["title"], weight=700, size=27, ls=-0.01))
    px = 104 + measure(p["title"], weight=700, size=27, ls=-0.01) + 12
    pw = measure(p["pill"], weight=700, size=9.5, ls=0.08) + 20
    b.append(f'<rect x="{px:.1f}" y="30" width="{pw:.1f}" height="20" rx="10" fill="{t["accent"]}" stroke="{t["ink"]}" stroke-width="1.5"/>')
    b.append(svg.text(px + 10, 43.6, p["pill"], weight=700, size=9.5, fill=t["onacc"], ls=0.08))
    for j, line in enumerate(tag):
        b.append(svg.text(104, 74 + 19 * j, line, weight=400, size=14, fill=t["muted"]))
    b.append(svg.text(104, 100 + extra_h, "  ·  ".join(s.upper() for s in p["stack"]), size=10, fill=t["faint"], ls=0.08))
    b.append(f'<g style="animation:out 3s ease-in-out infinite">{arrow_up_right(822, 40, t["ink"])}</g>')
    b.append(f'<line x1="4" y1="{122.5 + extra_h}" x2="836" y2="{122.5 + extra_h}" stroke="{t["faint"]}" stroke-width="1" stroke-opacity="0.6"/>')

    # Looping mini-terminal: type the command, run a progress bar, print a result.
    cycle, cw, tx = 10, measure("a", "M", 400, 12), 548
    at = 0.2
    for j, ch in enumerate(cmd):
        if ch != " ":
            b.append(svg.text(tx + j * cw, 40, ch, "M", 400, 12, extra='class="fin" ' + svg.reveal(cycle, at, 9.5, True)))
        at += 0.12 if j == 0 else 0.055
    at += 0.25
    b.append(svg.text(tx, 62, label, "M", 400, 12, fill=t["faint"], extra='class="fin" ' + svg.reveal(cycle, at, 9.5, True)))
    bx = tx + (len(label) + 1) * cw
    frames = ["[      ]", "[##    ]", "[####  ]", "[######]"]
    for j, f in enumerate(frames):
        last = j == len(frames) - 1
        on, off = at + j * 0.5, 9.5 if last else at + (j + 1) * 0.5
        b.append(svg.text(bx, 62, f, "M", 400, 12, fill=t["muted"], extra=('class="fin" ' if last else "") + svg.reveal(cycle, on, off, True)))
    at += len(frames) * 0.5 + 0.2
    b.append(svg.spans(tx, 84, [(rk + " ", t["faint"]), (rv, t["accent"] if t["ink"] != "#161616" else t["ink"])],
                       extra='class="fin" ' + svg.reveal(cycle, at, 9.5, True)))
    return svg


def _icon(name, t):
    raw = (TOOLS / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    if name in BRAND_FILL:
        fill = t["ink"] if name in DARK_ON_DARK and t["ink"] != "#161616" else BRAND_FILL[name]
        raw = raw.replace("<svg ", f'<svg fill="{fill}" ', 1).replace("currentColor", fill)
    if "amazonwebservices" in name:
        raw = raw.replace("#252f3e", t["ink"] if t["ink"] != "#161616" else "#252f3e")
    return "data:image/svg+xml;base64," + base64.b64encode(raw.encode()).decode()


def stack(t):
    names = [c for _, chips in STACK for c, _ in chips]
    svg = Svg(840, 0, f"What I build with: {', '.join(names)}.", t)
    svg.css.append("@keyframes pop{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}")
    svg.defs.append('<filter id="inv"><feColorMatrix type="matrix" values="0 0 0 0 0.753 0 0 0 0 0.792 0 0 0 0 0.961 0 0 0 1 0"/></filter>')
    rows, y, delay = [], 121, 0.15
    for label, chips in STACK:
        rows.append(svg.text(40, y + 16, label, size=10.5, fill=t["muted"], ls=0.12))
        x = 172
        for text, icon in chips:
            w = measure(text, size=13) + (35 if icon else 14) + 13
            if x + w > 796:
                x, y = 172, y + 42
            g = f'<g style="animation:pop .45s cubic-bezier(.16,1,.3,1) {delay:.3f}s both">' \
                f'<rect x="{x + 3:.1f}" y="{y + 3}" width="{w:.1f}" height="30" rx="8" fill="{t["ink"]}"/>' \
                f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="30" rx="8" fill="{t["panel"]}" stroke="{t["ink"]}" stroke-width="1.8"/>'
            if icon:
                filt = ' filter="url(#inv)"' if icon in DARK_ON_DARK and icon not in BRAND_FILL and t["ink"] != "#161616" else ""
                g += f'<image x="{x + 11:.1f}" y="{y + 7}" width="16" height="16" href="{_icon(icon, t)}"{filt}/>'
            g += svg.text(x + (35 if icon else 14), y + 19.5, text, size=13) + "</g>"
            rows.append(g)
            x += w + 10
            delay += 0.035
        y += 48
    h = y + 10
    svg.h = h + 10
    card(svg, 830, h, t["bg"])
    svg.body += [svg.text(40, 54, "TOOLBOX", size=11, fill=t["muted"], ls=0.16),
                 svg.text(40, 88, "What I build with", weight=700, size=28, ls=-0.01)] + rows
    return svg


# --------------------------------------------------------------------------
# "Beyond the code": hobbies cycle on the left; a pencil-sketch "video" fills the
# open space to the right (wider at the top, where the heading is short).
# --------------------------------------------------------------------------

# The drawing area: everything right of the text column, plus the strip beside the heading.
# Extend beyond the face so the soft text-side mask stays opaque at the outer edges.
ART_AREA = "M296 -30H870V390H386V198H296Z"  # steps in only where the description paragraph starts


def _kf(svg, body):
    """Register a keyframes body once per SVG and return its name."""
    names = svg.__dict__.setdefault("kf_names", {})
    if body not in names:
        names[body] = f"a{len(names)}"
        svg.css.append(f"@keyframes {names[body]}{{{body}}}")
    return names[body]


def about(t):
    label, heading = ABOUT_HEAD
    n = len(HOBBIES)
    starts, cycle = [], 0
    for h in HOBBIES:
        starts.append(cycle)
        cycle += h[3]
    title = f"{heading}: " + " ".join(f"{name}: {desc}" for _, name, desc, _ in HOBBIES) + \
        " Each hobby plays as an animated pencil sketch."
    svg = Svg(840, 362, title, t)
    svg.css += [
        "@keyframes boil{0%{filter:url(#w0)}33.3%{filter:url(#w1)}66.6%{filter:url(#w2)}}",
        ".sk path,.sk circle,.sk line{vector-effect:non-scaling-stroke}.sk .tb{vector-effect:none}",
        "@media (prefers-reduced-motion: reduce){.hob{opacity:0!important}.h0{opacity:1!important}.sk{display:none}}",
    ]
    # Three slightly different wobble filters, swapped a few times a second: the "line boil" of hand-drawn animation.
    for i in range(3):
        svg.defs.append(
            f'<filter id="w{i}" filterUnits="userSpaceOnUse" x="290" y="0" width="550" height="362">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="2" seed="{i * 7 + 3}"/>'
            f'<feDisplacementMap in="SourceGraphic" scale="2.6" xChannelSelector="R" yChannelSelector="G"/></filter>')
    svg.defs.append('<filter id="mb" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="9"/></filter>'
                    f'<mask id="dm" maskUnits="userSpaceOnUse" x="0" y="0" width="840" height="362">'
                    f'<path d="{ART_AREA}" fill="#fff" filter="url(#mb)"/></mask>')
    # The face is x=2..832, y=2..352 with a 2px border and 14px corner radius.
    # Clip after the mask and wobble filter, at the border's inner edge; exclude the shadow.
    svg.defs.append('<clipPath id="sketch-clip" clipPathUnits="userSpaceOnUse">'
                    '<rect x="3" y="3" width="828" height="348" rx="13"/></clipPath>')
    card(svg, 830, 350, t["bg"])
    b = svg.body
    b += [svg.text(40, 54, label, size=11, fill=t["muted"], ls=0.16),
          svg.text(40, 88, heading, weight=700, size=28, ls=-0.01)]

    for i, (key, name, desc, dur) in enumerate(HOBBIES):
        p0, p1 = 100 * starts[i] / cycle, 100 * (starts[i] + dur) / cycle
        on = "opacity:1;visibility:visible"
        off = "opacity:0;visibility:hidden"
        vis = _kf(svg, f"0%{{{on if i == 0 else off}}}" + (f"{p0:.3f}%{{{on}}}" if i else "") +
                  f"{p1:.3f}%{{{off}}}100%{{{off}}}")
        bar = _kf(svg, f"0%{{transform:scaleX(0)}}{p0:.3f}%{{transform:scaleX(0)}}{p1:.3f}%{{transform:scaleX(1)}}"
                       f"100%{{transform:scaleX(1)}}")
        parts = [svg.text(40, 150, f"{i + 1:02d} / {n:02d}", size=11, fill=t["muted"], ls=0.16),
                 svg.text(40, 186, name, weight=700, size=26, ls=-0.01)]
        parts += [svg.text(40, 218 + 22 * j, line, weight=400, size=15, fill=t["muted"])
                  for j, line in enumerate(wrap(desc, 330, size=15))]
        parts += [f'<circle cx="{44 + 14 * k}" cy="314" r="4" fill="{t["accent"] if k == i else "none"}" '
                  f'stroke="{t["ink"]}" stroke-width="1.4"/>' for k in range(n)]
        parts.append(f'<rect x="120" y="311" width="252" height="6" rx="3" fill="{t["faint"]}" opacity="0.35"/>'
                     f'<rect x="120" y="311" width="252" height="6" rx="3" fill="{t["accent"]}" '
                     f'style="transform-box:fill-box;transform-origin:left;animation:{bar} {cycle}s linear infinite"/>')
        sk = Sketch(svg, t, starts[i], dur, cycle, _kf)
        parts.append(f'<g class="sk" clip-path="url(#sketch-clip)" mask="url(#dm)" fill="none" stroke-linecap="round" stroke-linejoin="round">'
                     f'<g style="animation:boil 0.42s step-end infinite">{SCENES[key](sk)}</g></g>')
        b.append(f'<g class="hob h{i}" style="opacity:0;visibility:hidden;animation:{vis} {cycle}s step-end infinite">'
                 f'{"".join(parts)}</g>')
    return svg


def footer(t):
    """Contact card; everything is centred on the card face (x 2..832, y 2..196), not counting the shadow."""
    f = FOOTER
    svg = Svg(840, 204, f"{f['title']} {f['sub']} Email {EMAIL}.", t)
    svg.css.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}")
    card(svg, 830, 194, t["alt"], grid=False)
    cx, b = 417, svg.body
    # Block from label cap-top (y 46) to mail baseline (y 162) is 116px tall; the face centre is y 99.
    top = 99 - 127 / 2  # block runs from the label's cap height (top) to the cursor's bottom (top + 127)
    b += [svg.text(cx, top + 8, f["label"], size=11, fill=t["muted"], ls=0.16, anchor="middle"),
          svg.text(cx, top + 50, f["title"], weight=700, size=34, ls=-0.02, anchor="middle"),
          svg.text(cx, top + 78, f["sub"], weight=400, size=14, fill=t["muted"], anchor="middle"),
          f'<line x1="{cx - 300}" y1="{top + 98}" x2="{cx + 300}" y2="{top + 98}" stroke="{t["faint"]}" stroke-width="1.5" '
          f'stroke-dasharray="2 7" stroke-linecap="round"/>']
    prompt = "$ mail "
    w = measure(prompt + EMAIL, "M", 400, 13) + 12
    x = cx - w / 2
    b.append(svg.spans(x, top + 124, [(prompt, t["faint"]), (EMAIL, t["ink"])], size=13))
    b.append(f'<rect x="{x + w - 8:.1f}" y="{top + 112}" width="8" height="15" fill="{t["accent"]}" stroke="{t["ink"]}" stroke-width="1" '
             f'style="animation:blink 1.1s step-end infinite"/>')
    return svg


# --------------------------------------------------------------------------
# README
# --------------------------------------------------------------------------


def _versioned(file):
    """assets/<file>?v=<content hash>: the link changes whenever the image does, so browsers never show a stale copy."""
    digest = hashlib.sha1((ASSETS / file).read_bytes()).hexdigest()[:8]
    return f"assets/{file}?v={digest}"


def pic(name, alt, width='width="100%"'):
    return f'<picture><source media="(prefers-color-scheme: dark)" srcset="{_versioned(name + "-dark.svg")}" />' \
           f'<img alt="{esc(alt)}" src="{_versioned(name + "-light.svg")}" {width} /></picture>'


def build():
    ASSETS.mkdir(exist_ok=True)
    cards = {"hero": hero, "work-head": work_head, "stack": stack, "about": about, "footer": footer}
    for i, p in enumerate(WORK):
        cards[f"work-{p['slug']}"] = lambda t, i=i, p=p: work_row(t, i, p)
    for slug, label, _ in BUTTONS:
        cards[f"btn-{slug}"] = lambda t, label=label: button(t, label)

    titles, widths = {}, {}
    for name, fn in cards.items():
        for mode, t in THEMES.items():
            svg = fn(t)
            (ASSETS / f"{name}-{mode}.svg").write_text(svg.render(), encoding="utf-8")
            titles[name], widths[name] = svg.title, svg.w

    btns = "\n".join(
        '<a href="{}">{}</a>'.format(url, pic(f"btn-{slug}", label, 'width="{}"'.format(widths[f"btn-{slug}"])))
        for slug, label, url in BUTTONS
    )
    work = "\n".join(
        '<a href="{}">{}</a>'.format(p["url"], pic(f"work-{p['slug']}", titles[f"work-{p['slug']}"])) for p in WORK
    )
    intro = f"\n{INTRO}\n" if INTRO else ""
    readme = f"""{pic("hero", titles["hero"])}

{btns}
{intro}
<br>

{pic("work-head", titles["work-head"])}
{work}

<br>

{pic("stack", titles["stack"])}

<br>

{pic("about", titles["about"])}

<br><br>

<a href="mailto:{EMAIL}">{pic("footer", titles["footer"])}</a>
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote README.md and {len(cards) * 2} SVGs to {ASSETS}")


if __name__ == "__main__":
    build()
