"""Logo image helpers — clean up a photographed/scanned logo so it sits
nicely on the white order form (remove background, trim edges).

Uses an edge flood-fill: background regions that touch the image border are
made transparent (this clears uneven backgrounds, shadows and stray smudges),
while artwork in the middle of the image is preserved."""
import os
from PIL import Image, ImageDraw

_SENTINEL = (255, 0, 255)  # unlikely colour used to mark background


def process_logo(src_path: str, dest_png: str, remove_bg: bool = True,
                 tolerance: int = 50) -> str:
    img = Image.open(src_path).convert("RGBA")

    if remove_bg:
        rgb = img.convert("RGB")
        w, h = rgb.size
        px = rgb.load()

        # Background colour = average of the four corners (sampled before fill).
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        br = sum(c[0] for c in corners) // 4
        bg_ = sum(c[1] for c in corners) // 4
        bb = sum(c[2] for c in corners) // 4

        # Pass 1 — edge flood-fill: remove background regions (and smudges /
        # shadows) that touch the border, following gradients via many seeds.
        step = max(3, min(w, h) // 50)
        seeds = []
        for x in range(0, w, step):
            seeds += [(x, 0), (x, h - 1)]
        for y in range(0, h, step):
            seeds += [(0, y), (w - 1, y)]
        for sx, sy in seeds:
            if px[sx, sy] != _SENTINEL:
                ImageDraw.floodfill(rgb, (sx, sy), _SENTINEL, thresh=tolerance)

        # Pass 2 — colour key: also clear background trapped INSIDE the artwork
        # (e.g. the grey inside an oval logo outline) by matching the bg colour.
        mask = rgb.load()
        src = img.load()
        ctol = tolerance + 10
        out = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = src[x, y]
                if mask[x, y] == _SENTINEL:
                    out.append((r, g, b, 0))
                elif abs(r - br) <= ctol and abs(g - bg_) <= ctol and abs(b - bb) <= ctol:
                    out.append((r, g, b, 0))
                else:
                    out.append((r, g, b, a))
        img.putdata(out)

        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

    os.makedirs(os.path.dirname(dest_png), exist_ok=True)
    img.save(dest_png, "PNG")
    return dest_png
