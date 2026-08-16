# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Geometry and type for the Patent 1024 'Claim Tree' identity.

The tree is defined once here in a 64x64 unit square and reused by every
output (SVG, PNG raster, animated GIF), so the drawings cannot drift apart.
See README.md in this directory for how to regenerate the assets.
"""

import glob
import math
import os

import numpy as np
import uharfbuzz as hb
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

# Decompressed woff2 files are cached here; the directory is gitignored.
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fontcache")
os.makedirs(FONTS, exist_ok=True)

NAVY = "#283E53"
SLATE = "#3A5A7E"
CYAN = "#00A8E8"
WHITE = "#FFFFFF"
SKY = "#7FC9EC"  # mid tone for branches on a dark ground


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


# --------------------------------------------------------------------------
# Geometry: the claim tree, 1 -> 2 -> 4 -> 8, in a 64x64 box.
# Each entry is (x0, y0, x1, y1, stroke_width, level).
# --------------------------------------------------------------------------


def build_tree(levels=4):
    """Root at bottom centre, branching upward. Returns segments by level."""
    if levels == 4:
        # Even rises and halving spreads: the canonical dendrogram, which also
        # lands the eight tips at near-uniform spacing.
        ys = [58, 48, 34, 21, 9]
        widths = [6.0, 5.0, 3.6, 2.4]
        spreads = [0, 15, 7.5, 4]
    elif levels == 3:  # compact 1 -> 2 -> 4, for roughly 20-40px
        ys = [58, 45, 28, 11]
        widths = [8.5, 7.0, 5.0]
        spreads = [0, 16, 8]
    else:  # mini 1 -> 2, the last reduction that still reads at 16px
        ys = [58, 40, 12]
        widths = [11.0, 9.0]
        spreads = [0, 19]

    segs = []
    # level 0: the trunk, a vertical stem
    nodes = [32.0]
    segs.append((32.0, ys[0], 32.0, ys[1], widths[0], 0))
    for lv in range(1, len(widths)):
        nxt = []
        for x in nodes:
            for sign in (-1, 1):
                x2 = x + sign * spreads[lv]
                segs.append((x, ys[lv], x2, ys[lv + 1], widths[lv], lv))
                nxt.append(x2)
        nodes = nxt
    return segs


TREE_FULL = build_tree(4)
TREE_COMPACT = build_tree(3)
TREE_MINI = build_tree(2)

# Each generation steps toward the accent, so the doubling is legible as colour
# as well as geometry.
LEVEL_COLORS_LIGHT = [NAVY, "#2E5273", "#2A7CAC", CYAN]
LEVEL_COLORS_DARK = [WHITE, "#D3E4F0", SKY, CYAN]
LEVEL_COLORS_COMPACT_LIGHT = [NAVY, NAVY, CYAN]
LEVEL_COLORS_COMPACT_DARK = [WHITE, WHITE, CYAN]
LEVEL_COLORS_MINI_DARK = [WHITE, CYAN]


def tree_svg(segs, colors, dx=0.0, dy=0.0, scale=1.0, indent="  "):
    """Emit the tree as grouped <path> elements, one group per stroke weight."""
    by_key = {}
    for x0, y0, x1, y1, w, lv in segs:
        by_key.setdefault((round(w, 2), colors[lv]), []).append((x0, y0, x1, y1))
    out = []
    for (w, col), items in by_key.items():
        d = " ".join(
            "M%s %s L%s %s"
            % (
                fmt(x0 * scale + dx),
                fmt(y0 * scale + dy),
                fmt(x1 * scale + dx),
                fmt(y1 * scale + dy),
            )
            for x0, y0, x1, y1 in items
        )
        out.append(
            f'{indent}<path d="{d}" fill="none" stroke="{col}" '
            f'stroke-width="{fmt(w * scale)}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
        )
    return "\n".join(out)


def fmt(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


# --------------------------------------------------------------------------
# Type: pull Inter SemiBold and IBM Plex Mono Medium out of the bundled
# woff2 subsets, convert to ttf, shape with HarfBuzz, emit outlines.
# --------------------------------------------------------------------------

# Both faces are already dependencies of the frontend (@fontsource/inter and
# @fontsource/ibm-plex-mono) and both are SIL Open Font License 1.1, so their
# outlines can be embedded in the logo. They are looked up by family name
# rather than by path: webpack rehashes the built filenames on every build.
SEARCH_GLOBS = [
    "superset/static/assets/*.woff2",
    "superset-frontend/node_modules/@fontsource/*/files/*.woff2",
]
NEEDED = set("PATEN1024")


def find_face(family):
    """Locate a woff2 for `family` that has every glyph the logo needs."""
    for pattern in SEARCH_GLOBS:
        for path in sorted(glob.glob(pattern)):
            try:
                f = TTFont(path, lazy=True)
                if f["name"].getDebugName(1) != family:
                    continue
                if NEEDED <= {chr(c) for c in f.getBestCmap()}:
                    return path
            except Exception:  # noqa: S112 - unreadable/!woff2 files are skipped
                continue
    raise SystemExit(
        f"Could not find a {family!r} woff2 containing "
        f"{''.join(sorted(NEEDED))}.\n"
        "Build the frontend (npm run build) or install its node_modules first."
    )


def woff2_to_ttf(family, name):
    """Cache a decompressed ttf: HarfBuzz and Pillow both need a real file."""
    dst = os.path.join(FONTS, name)
    if not os.path.exists(dst):
        f = TTFont(find_face(family))
        f.flavor = None
        f.save(dst)
    return dst


class Face:
    def __init__(self, path):
        self.file = path
        self.tt = TTFont(path)
        self.upem = self.tt["head"].unitsPerEm
        self.cap = self.tt["OS/2"].sCapHeight
        self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        blob = hb.Blob.from_file_path(path)
        face = hb.Face(blob)
        self.hbfont = hb.Font(face)
        self.hbfont.scale = (self.upem, self.upem)

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf)
        return list(zip(buf.glyph_infos, buf.glyph_positions, strict=False))

    def layout(self, text, cap_height, tracking_px=0.0):
        """Return [(glyph_name, x_px, y_px)], total advance width in px."""
        scale = cap_height / self.cap
        runs = self.shape(text)
        placed = []
        x = 0.0
        for info, pos in runs:
            gname = self.order[info.codepoint]
            placed.append((gname, x + pos.x_offset * scale, -pos.y_offset * scale))
            x += pos.x_advance * scale + tracking_px
        width = x - tracking_px if runs else 0.0
        return placed, width, scale

    def path(self, text, cap_height, tracking_px, ox, oy):
        placed, width, scale = self.layout(text, cap_height, tracking_px)
        pen = SVGPathPen(self.gs, ntos=fmt)
        for gname, gx, gy in placed:
            t = Transform(scale, 0, 0, -scale, ox + gx, oy + gy)
            self.gs[gname].draw(TransformPen(pen, t))
        return pen.getCommands(), width


INTER = Face(woff2_to_ttf("Inter SemiBold", "inter-semibold.ttf"))
MONO = Face(woff2_to_ttf("IBM Plex Mono Medium", "plexmono-medium.ttf"))

# --------------------------------------------------------------------------
# Lockup metrics
# --------------------------------------------------------------------------


def tree_ink_bbox(segs):
    """Outer bounds of the drawn strokes, round caps included."""
    x0 = min(min(s[0], s[2]) - s[4] / 2 for s in segs)
    x1 = max(max(s[0], s[2]) + s[4] / 2 for s in segs)
    y0 = min(min(s[1], s[3]) - s[4] / 2 for s in segs)
    y1 = max(max(s[1], s[3]) + s[4] / 2 for s in segs)
    return x0, y0, x1, y1


# Shift the tree so its ink starts at the origin: logo files carry no baked-in
# padding, so layout is controlled by whatever places them.
_bx0, _by0, _bx1, _by1 = tree_ink_bbox(TREE_FULL)
TREE_DX, TREE_DY = -_bx0, -_by0
TREE_W, TREE_H = _bx1 - _bx0, _by1 - _by0

CAP_WORD = 21.0  # cap height of PATENT
CAP_NUM = 11.5  # cap height of 1024
TRACK_WORD = 0.5
TRACK_NUM = 0.42 * CAP_NUM  # letterspaced, drafting-label style
GAP_LINES = 12.0  # PATENT baseline down to the 1024 cap line

# Centre the two-line text block on the mark's optical centre.
_block_h = CAP_WORD + GAP_LINES + CAP_NUM
_top = TREE_H / 2 - _block_h / 2
BASE_WORD = _top + CAP_WORD
BASE_NUM = _top + _block_h

GAP = 13.0
RULE_X = TREE_W + GAP
TEXT_X = RULE_X + GAP
RULE_Y0, RULE_Y1 = _top - 1.5, BASE_NUM + 1.5

_, W_WORD = INTER.path("PATENT", CAP_WORD, TRACK_WORD, 0, 0)
_, W_NUM = MONO.path("1024", CAP_NUM, TRACK_NUM, 0, 0)
TOTAL_W = TEXT_X + W_WORD
TOTAL_H = TREE_H

D_WORD, _ = INTER.path("PATENT", CAP_WORD, TRACK_WORD, TEXT_X, BASE_WORD)
D_NUM, _ = MONO.path("1024", CAP_NUM, TRACK_NUM, TEXT_X, BASE_NUM)

LICENSE = """<!--
  Patent 1024 - primary logo. Type is converted to outlines: Inter SemiBold and
  IBM Plex Mono Medium, both SIL Open Font License 1.1.
-->"""


def lockup_svg(dark=False):
    colors = LEVEL_COLORS_DARK if dark else LEVEL_COLORS_LIGHT
    word_fill = WHITE if dark else NAVY
    rule = "#3B546B" if dark else "#C6D2DE"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(TOTAL_W)} \
{fmt(TOTAL_H)}" width="{fmt(TOTAL_W)}" height="{fmt(TOTAL_H)}" role="img" \
aria-label="Patent 1024">
{LICENSE}
  <title>Patent 1024</title>
{tree_svg(TREE_FULL, colors, dx=TREE_DX, dy=TREE_DY)}
  <line x1="{fmt(RULE_X)}" y1="{fmt(RULE_Y0)}" x2="{fmt(RULE_X)}" y2="{fmt(RULE_Y1)}" \
stroke="{rule}" stroke-width="1"/>
  <path d="{D_WORD}" fill="{word_fill}"/>
  <path d="{D_NUM}" fill="{CYAN}"/>
</svg>
"""


def mark_svg(compact=False, dark=False):
    """The mark alone, in a square box. Tiles are raster (see generate.favicon)."""
    if compact:
        segs, cols = (
            TREE_COMPACT,
            (LEVEL_COLORS_COMPACT_DARK if dark else LEVEL_COLORS_COMPACT_LIGHT),
        )
    else:
        segs, cols = TREE_FULL, (LEVEL_COLORS_DARK if dark else LEVEL_COLORS_LIGHT)

    # centre the ink in a square box so avatars and tiles crop predictably
    bx0, by0, bx1, by1 = tree_ink_bbox(segs)
    dx = (64 - (bx1 - bx0)) / 2 - bx0
    dy = (64 - (by1 - by0)) / 2 - by0
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" \
height="64" role="img" aria-label="Patent 1024">
  <title>Patent 1024</title>
{tree_svg(segs, cols, dx=dx, dy=dy)}
</svg>
"""


# --------------------------------------------------------------------------
# Raster: analytic distance-field rasteriser for the tree (round caps come
# free), so PNG and GIF output match the SVG exactly.
# --------------------------------------------------------------------------


def tree_field(segs, size, pad=0.0, ss=1):
    """Return (alpha, along) arrays. `along` is normalised distance from root."""
    n = size * ss
    bx0, by0, bx1, by1 = tree_ink_bbox(segs)
    iw, ih = bx1 - bx0, by1 - by0
    k = (size - 2 * pad) / max(iw, ih) * ss
    odx = ((size - iw * k / ss) / 2 - bx0 * k / ss) * ss
    ody = ((size - ih * k / ss) / 2 - by0 * k / ss) * ss

    xs = (np.arange(n) + 0.5).reshape(1, n)
    ys = (np.arange(n) + 0.5).reshape(n, 1)

    # cumulative distance from the root, walked by matching endpoints
    total = 0.0
    starts = {}
    for x0, y0, x1, y1, w, lv in segs:
        starts.setdefault((round(x0, 3), round(y0, 3)), []).append(
            (x0, y0, x1, y1, w, lv)
        )
    root = segs[0]
    order = []
    stack = [(root, 0.0)]
    while stack:
        seg, dist = stack.pop()
        x0, y0, x1, y1, w, lv = seg
        ln = math.hypot(x1 - x0, y1 - y0)
        order.append((seg, dist, ln))
        total = max(total, dist + ln)
        for child in starts.get((round(x1, 3), round(y1, 3)), []):
            stack.append((child, dist + ln))

    best = np.full((n, n), 1e9, dtype=np.float32)
    along = np.zeros((n, n), dtype=np.float32)
    alpha = np.zeros((n, n), dtype=np.float32)

    aa = 0.7 * ss
    for seg, dist, ln in order:
        x0, y0, x1, y1, w, lv = seg
        ax, ay = x0 * k + odx, y0 * k + ody
        bx, by = x1 * k + odx, y1 * k + ody
        vx, vy = bx - ax, by - ay
        seg_len_sq = vx * vx + vy * vy
        t = ((xs - ax) * vx + (ys - ay) * vy) / seg_len_sq
        t = np.clip(t, 0.0, 1.0)
        px, py = ax + t * vx, ay + t * vy
        d = np.hypot(xs - px, ys - py)
        r = w * k / 2.0
        a = np.clip((r + aa / 2 - d) / aa, 0.0, 1.0)
        alpha = np.maximum(alpha, a)
        upd = (d < best) & (a > 0)
        best = np.where(upd, d, best)
        along = np.where(upd, (dist + t * ln) / total, along)

    if ss > 1:
        alpha = alpha.reshape(size, ss, size, ss).mean(axis=(1, 3))
        along = along.reshape(size, ss, size, ss).mean(axis=(1, 3))
    return alpha, along


def raster_tree(segs, colors, w_px, h_px, k, dx=0.0, dy=0.0, ss=3):
    """Flat-coloured tree at `k` px per design unit, offset by (dx, dy) units.

    Returns (rgb float array h x w x 3, alpha h x w).
    """
    wide, high = w_px * ss, h_px * ss
    k = k * ss
    xs = (np.arange(wide) + 0.5).reshape(1, wide)
    ys = (np.arange(high) + 0.5).reshape(high, 1)

    acc_a = np.zeros((high, wide), dtype=np.float32)
    acc_c = np.zeros((high, wide, 3), dtype=np.float32)
    aa = 0.8 * ss

    # paint thinnest/outermost first so the trunk sits on top at the joins
    for x0, y0, x1, y1, w, lv in sorted(segs, key=lambda s: -s[5]):
        col = np.array(hex2rgb(colors[lv]), dtype=np.float32)
        ax, ay = (x0 + dx) * k, (y0 + dy) * k
        bx, by = (x1 + dx) * k, (y1 + dy) * k
        vx, vy = bx - ax, by - ay
        t = np.clip(((xs - ax) * vx + (ys - ay) * vy) / (vx * vx + vy * vy), 0, 1)
        d = np.hypot(xs - (ax + t * vx), ys - (ay + t * vy))
        a = np.clip((w * k / 2.0 + aa / 2 - d) / aa, 0.0, 1.0)
        acc_c = acc_c * (1 - a[..., None]) + col * a[..., None]
        acc_a = acc_a + a * (1 - acc_a)

    if ss > 1:
        acc_a = acc_a.reshape(h_px, ss, w_px, ss).mean(axis=(1, 3))
        acc_c = acc_c.reshape(h_px, ss, w_px, ss, 3).mean(axis=(1, 3))
    return acc_c, acc_a


def tree_rgb(segs, colors, size, pad=0.0, ss=3):
    """Square rendering: ink scaled to fill `size` px, inset by `pad`, centred."""
    bx0, by0, bx1, by1 = tree_ink_bbox(segs)
    iw, ih = bx1 - bx0, by1 - by0
    k = (size - 2 * pad) / max(iw, ih)
    dx = (size - iw * k) / 2 / k - bx0
    dy = (size - ih * k) / 2 / k - by0
    return raster_tree(segs, colors, size, size, k, dx, dy, ss=ss)


def compose(rgb, alpha, bg):
    bg = np.array(hex2rgb(bg), dtype=np.float32)
    out = rgb * alpha[..., None] + bg * (1 - alpha[..., None])
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def rgba(rgb, alpha):
    arr = np.concatenate(
        [np.clip(rgb, 0, 255), np.clip(alpha * 255, 0, 255)[..., None]], axis=2
    )
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def rounded_tile(size, radius_ratio=14 / 64.0, bg=NAVY):
    """Antialiased rounded square, returns alpha array."""
    ss = 3
    n = size * ss
    r = radius_ratio * n
    xs = (np.arange(n) + 0.5).reshape(1, n)
    ys = (np.arange(n) + 0.5).reshape(n, 1)
    dx = np.maximum(np.maximum(r - xs, xs - (n - r)), 0)
    dy = np.maximum(np.maximum(r - ys, ys - (n - r)), 0)
    d = np.hypot(dx, dy)
    a = np.clip((r + 0.5 - d) / 1.0, 0, 1)
    return a.reshape(size, ss, size, ss).mean(axis=(1, 3))


def draw_text(img, face, text, cap_height, tracking, ox, oy, fill):
    """Draw shaped text onto an RGBA image using per-glyph placement."""
    from PIL import ImageDraw, ImageFont

    placed, width, scale = face.layout(text, cap_height, tracking)
    px = int(round(face.upem * scale))
    font = ImageFont.truetype(face.file, px)
    d = ImageDraw.Draw(img)
    for gname, gx, gy in placed:
        ch = None
        for cp, gn in face.tt.getBestCmap().items():
            if gn == gname:
                ch = chr(cp)
                break
        if ch is None:
            continue
        d.text((ox + gx, oy + gy), ch, font=font, fill=fill, anchor="ls")
    return width
