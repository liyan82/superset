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
"""Regenerate every Patent 1024 brand asset. See README.md in this directory.

Run from the repository root:

    python superset/patent1024/brand/generate.py

Invoked as a plain script rather than a module: this is a design-time tool with
no relationship to the Flask app, and importing the ``superset`` package would
drag in the whole runtime just to draw a logo.
"""

import io
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from geometry import (  # noqa: E402  (path set above)
    BASE_NUM,
    BASE_WORD,
    CAP_NUM,
    CAP_WORD,
    CYAN,
    draw_text,
    hex2rgb,
    INTER,
    LEVEL_COLORS_COMPACT_DARK,
    LEVEL_COLORS_DARK,
    LEVEL_COLORS_LIGHT,
    LEVEL_COLORS_MINI_DARK,
    lockup_svg,
    mark_svg,
    MONO,
    NAVY,
    raster_tree,
    rgba,
    rounded_tile,
    RULE_X,
    RULE_Y0,
    RULE_Y1,
    SKY,
    TEXT_X,
    TOTAL_H,
    TOTAL_W,
    TRACK_NUM,
    TRACK_WORD,
    TREE_COMPACT,
    TREE_DX,
    TREE_DY,
    tree_field,
    TREE_FULL,
    TREE_MINI,
    tree_rgb,
    WHITE,
)

# Source of truth for images; webpack copies this whole directory to
# superset/static/assets/images at build time. We mirror there too so a running
# instance picks the assets up without a rebuild.
SRC = "superset-frontend/src/assets/images"
STATIC = "superset/static/assets/images"

# The email header is a gradient from NAVY to #3A5A7E; this is its midpoint.
EMAIL_BG = "#31496A"


def emit(name, data):
    for d in (SRC, STATIC):
        if not os.path.isdir(d):
            continue
        p = os.path.join(d, name)
        if isinstance(data, str):
            open(p, "w").write(data)
        elif isinstance(data, bytes):
            open(p, "wb").write(data)
        else:
            data.save(p, optimize=True)
    print(f"  {name}")


def raster_lockup(scale, dark=False, bg=None):
    """The full lockup as an RGBA image at `scale` px per design unit."""
    w = int(round(TOTAL_W * scale))
    h = int(round(TOTAL_H * scale))
    colors = LEVEL_COLORS_DARK if dark else LEVEL_COLORS_LIGHT

    rgb, a = raster_tree(TREE_FULL, colors, w, h, scale, TREE_DX, TREE_DY, ss=3)
    img = rgba(rgb, a)

    rule = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(rule).rectangle(
        [
            RULE_X * scale,
            RULE_Y0 * scale,
            RULE_X * scale + max(1, round(scale)),
            RULE_Y1 * scale,
        ],
        fill=hex2rgb("#3B546B" if dark else "#C6D2DE") + (255,),
    )
    img.alpha_composite(rule)

    draw_text(
        img,
        INTER,
        "PATENT",
        CAP_WORD * scale,
        TRACK_WORD * scale,
        TEXT_X * scale,
        BASE_WORD * scale,
        hex2rgb(WHITE if dark else NAVY) + (255,),
    )
    draw_text(
        img,
        MONO,
        "1024",
        CAP_NUM * scale,
        TRACK_NUM * scale,
        TEXT_X * scale,
        BASE_NUM * scale,
        hex2rgb(CYAN) + (255,),
    )

    if bg:
        flat = Image.new("RGBA", img.size, hex2rgb(bg) + (255,))
        flat.alpha_composite(img)
        return flat.convert("RGB")
    return img


def favicon(size):
    """Navy rounded tile with the mark knocked out.

    Inset, corner radius and the drawing itself all step down with size, so the
    mark still reads at 16px instead of drowning in its own tile.
    """
    if size >= 48:
        inset_r, radius_r = 0.17, 14 / 64
        segs, cols = TREE_COMPACT, LEVEL_COLORS_COMPACT_DARK
    elif size >= 24:
        inset_r, radius_r = 0.13, 0.19
        segs, cols = TREE_COMPACT, LEVEL_COLORS_COMPACT_DARK
    else:
        # at 16px only the fork survives; the four-tip crown turns to mush
        inset_r, radius_r = 0.07, 0.16
        segs, cols = TREE_MINI, LEVEL_COLORS_MINI_DARK

    rgb, a = tree_rgb(segs, cols, size, pad=size * inset_r, ss=3)
    base = np.zeros((size, size, 3), dtype=np.float32)
    base[:] = hex2rgb(NAVY)
    base = base * (1 - a[..., None]) + rgb * a[..., None]
    return rgba(base, rounded_tile(size, radius_ratio=radius_r))


def build_ico(sizes=(16, 24, 32, 48, 64, 128, 256)):
    """Hand-assemble the .ico so every entry is its own tuned drawing.

    Pillow's ICO writer resizes a single source image, which would throw the
    small-size reductions away.
    """
    payloads = []
    for s in sizes:
        buf = io.BytesIO()
        favicon(s).save(buf, format="PNG", optimize=True)
        payloads.append(buf.getvalue())

    offset = 6 + 16 * len(sizes)
    entries, blobs = b"", b""
    for s, data in zip(sizes, payloads, strict=False):
        dim = s if s < 256 else 0
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    return struct.pack("<HHH", 0, 1, len(sizes)) + entries + blobs


def social_card(lines, kicker):
    """1200x630 Open Graph card."""
    w, h, margin = 1200, 630, 88
    bg = np.zeros((h, w, 3), dtype=np.float32)
    bg[:] = hex2rgb("#16242F")

    # oversized tree as a watermark, bleeding off the right edge
    big = 900
    rgb, a = raster_tree(TREE_FULL, [SKY] * 4, big, big, big / 56.0, dx=-4, dy=-4, ss=2)
    a = a * 0.075
    x0, y0 = 700, -110
    xs = slice(max(0, x0), min(w, x0 + big))
    ys = slice(max(0, y0), min(h, y0 + big))
    sa = a[ys.start - y0 : ys.stop - y0, xs.start - x0 : xs.stop - x0]
    sc = rgb[ys.start - y0 : ys.stop - y0, xs.start - x0 : xs.stop - x0]
    bg[ys, xs] = bg[ys, xs] * (1 - sa[..., None]) + sc * sa[..., None]

    img = Image.fromarray(bg.astype(np.uint8), "RGB").convert("RGBA")
    img.alpha_composite(raster_lockup(1.75, dark=True), (margin, 78))

    cap = 54 if len(lines) < 2 or max(len(x) for x in lines) < 22 else 46
    y = 330
    for line in lines:
        draw_text(img, INTER, line, cap, 0.0, margin, y, hex2rgb(WHITE) + (255,))
        y += round(cap * 1.44)  # clears the descenders of the line above
    draw_text(img, MONO, kicker, 14, 3.6, margin + 2, 506, hex2rgb(CYAN) + (255,))
    ImageDraw.Draw(img).rectangle(
        [margin, 540, margin + 116, 544], fill=hex2rgb(CYAN) + (255,)
    )
    return img.convert("RGB")


def loading_gif(size=88, frames=60, duration=20):
    """A charge travelling root to tips, looping.

    Matches the cadence of Superset's own spinner (60 frames at 20ms, 1.2s,
    transparent ground) so it drops in without feeling different.
    """
    alpha, along = tree_field(TREE_FULL, size, pad=3.0, ss=3)

    base = np.array(hex2rgb("#AFC0CE"), dtype=np.float32)  # resting tree
    hot = np.array(hex2rgb(CYAN), dtype=np.float32)
    warm = np.array(hex2rgb(NAVY), dtype=np.float32)

    imgs = []
    for f in range(frames):
        # the pulse re-enters at the root as the previous one leaves the tips,
        # so the loop has no dead frame at the seam
        phase = (f / frames) * 1.20 - 0.05
        d = along - phase
        # sharp leading edge, long trailing tail: reads as flow, not a blink
        head = np.exp(-(np.clip(d, 0, None) ** 2) / (2 * 0.045**2))
        tail = np.exp(np.clip(d, None, 0) / 0.26)
        e = np.clip(np.where(d >= 0, head, tail), 0, 1) * (alpha > 0.02)

        col = (
            base[None, None, :] * (1 - e[..., None])
            + (warm[None, None, :] * 0.35 + hot[None, None, :] * 0.65) * e[..., None]
        )
        col = col * (1 - (e**3)[..., None]) + hot[None, None, :] * (e**3)[..., None]

        # GIF alpha is 1-bit, so cut low to keep the thin outer branches solid
        opaque = alpha > 0.35
        q = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGB").convert(
            "P", palette=Image.ADAPTIVE, colors=255
        )
        pal = q.getpalette()[: 255 * 3] + [0, 0, 0]  # reserve 255 as transparent
        arr = np.array(q)
        arr[~opaque] = 255
        q = Image.fromarray(arr, "P")
        q.putpalette(pal)
        imgs.append(q)

    buf = io.BytesIO()
    imgs[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=imgs[1:],
        duration=duration,
        loop=0,
        transparency=255,
        disposal=2,
    )
    return buf.getvalue()


def main():
    if not os.path.isdir(SRC):
        raise SystemExit(f"Run this from the repository root ({SRC} not found).")

    print(f"lockup {TOTAL_W:.2f} x {TOTAL_H:.2f} ({TOTAL_W / TOTAL_H:.2f}:1)")

    emit("patent-1024.svg", lockup_svg(dark=False))
    emit("patent-1024-inverse.svg", lockup_svg(dark=True))
    emit("patent-1024-mark.svg", mark_svg())
    emit("patent-1024-mark-inverse.svg", mark_svg(dark=True))

    # raster lockups: the email body and the schema.org publisher logo both
    # need a bitmap, and the email header band is dark
    emit("patent-1024.png", raster_lockup(3.0))
    emit("patent-1024-email.png", raster_lockup(3.0, dark=True, bg=EMAIL_BG))

    emit("p4-favicon.png", favicon(512))
    emit("p4-apple-touch-icon.png", favicon(180))
    emit("p4-favicon.ico", build_ico())

    emit(
        "patent-1024-og.png",
        social_card(
            ["Dangerously Addictive", "Patent Insights"],
            "USPTO ANALYTICS   ·   PATENT1024.COM",
        ),
    )
    emit(
        "blog-og.png",
        social_card(
            ["Patent Analytics Blog", "Expert USPTO Insights"],
            "PATENT1024.COM   ·   BLOG",
        ),
    )
    emit(
        "blog-patent-trends-og.png",
        social_card(
            ["USPTO Patent Filing", "Trends & Statistics 2024"],
            "PATENT1024.COM   ·   BLOG",
        ),
    )

    emit("patent-1024-loading.gif", loading_gif())
    print("done")


if __name__ == "__main__":
    main()
