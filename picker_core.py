"""Page picker logic (no UI): grid layout, cover guessing, selection helpers and JPG extraction."""
import io
from pathlib import Path

from PIL import Image

from comic_core import sanitize, unique

GAP = 12
LABEL_H = 22
ASPECT = 1.45  # cell image height / width
JPG_QUALITY = 95
SIZE_TOLERANCE = 0.04  # a page this much bigger or smaller than the one before it starts a new "section"


def layout(width, size):
    """Cell geometry for a canvas `width` px wide and thumbnails `size` px wide: (cols, cell_w, cell_h)."""
    cell_w = size + GAP
    cols = max(1, (max(width, cell_w) - GAP) // cell_w)
    return cols, cell_w, round(size * ASPECT) + LABEL_H + GAP


def cell_rect(i, cols, cell_w, cell_h):
    """(x0, y0, x1, y1) of the whole cell (thumbnail plus label) for page index `i`."""
    r, c = divmod(i, cols)
    x, y = GAP + c * cell_w, GAP + r * cell_h
    return x, y, x + cell_w - GAP, y + cell_h - GAP


def total_height(n, cols, cell_h):
    return GAP + -(-n // cols) * cell_h


def cells_in(rect, n, cols, cell_w, cell_h):
    """Indexes of pages whose cell overlaps `rect` (x0, y0, x1, y1), in page order."""
    x0, y0, x1, y1 = rect
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    c0, c1 = max(0, int((x0 - GAP) // cell_w)), min(cols - 1, int((x1 - GAP) // cell_w))
    r0, r1 = max(0, int((y0 - GAP) // cell_h)), int((y1 - GAP) // cell_h)
    out = []
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            i = r * cols + c
            if i < n:
                ax0, ay0, ax1, ay1 = cell_rect(i, cols, cell_w, cell_h)
                if ax1 >= x0 and ax0 <= x1 and ay1 >= y0 and ay0 <= y1:
                    out.append(i)
    return out


def likely_covers(sizes):
    """Pages that look like a cover: portrait, and the first page, the page after a double-page spread, or one whose
    size differs from both neighbours (covers are usually a different size to the interior).

    `sizes` is a list of (w, h) or None for pages not read yet; a page is only judged once its neighbour is known.
    """
    out = set()
    for i, s in enumerate(sizes):
        if not s or s[1] <= s[0]:  # unknown, or a landscape double-page spread
            continue
        if i == 0:
            out.add(i)
            continue
        p = sizes[i - 1]
        if not p:
            continue
        if p[1] <= p[0]:
            out.add(i)
        elif differs(s, p) and (i + 1 == len(sizes) or sizes[i + 1] is None or differs(s, sizes[i + 1])):
            out.add(i)  # odd one out against both neighbours: a cover among interior pages
    return out


def differs(a, b):
    return abs(a[0] - b[0]) > b[0] * SIZE_TOLERANCE or abs(a[1] - b[1]) > b[1] * SIZE_TOLERANCE


def range_between(a, b):
    lo, hi = sorted((a, b))
    return list(range(lo, hi + 1))


def toggle(order, i):
    """New pick order with page `i` added at the end, or removed if it was picked."""
    return [x for x in order if x != i] if i in order else [*order, i]


def add_all(order, idxs):
    seen = set(order)
    return [*order, *(i for i in idxs if i not in seen)]


def invert(order, n):
    return [i for i in range(n) if i not in set(order)]


def move(order, pos, delta):
    """Move the entry at `pos` by `delta` places; returns (new order, new position)."""
    new = pos + delta
    if not 0 <= new < len(order):
        return list(order), pos
    out = list(order)
    out[pos], out[new] = out[new], out[pos]
    return out, new


def to_jpg(data, ext):
    """Page bytes as JPG: a JPG page is copied untouched, anything else is re-encoded."""
    if ext.lower() in (".jpg", ".jpeg"):
        return data
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        flat = Image.new("RGB", img.size, (255, 255, 255))
        flat.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = flat
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=JPG_QUALITY, optimize=True)
    return buf.getvalue()


def extract_pages(comic, order, folder):
    """Write the pages in `order` (indexes) to `folder` as '<comic name> <n>.jpg'. Returns the paths written."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stem = sanitize(comic.path.stem)
    width = len(str(len(order)))
    saved, used = [], set()
    for n, i in enumerate(order, 1):
        name = comic.pages[i]
        dest = unique(folder / f"{stem} {n:0{width}d}.jpg", used)
        dest.write_bytes(to_jpg(comic.read(name), Path(name).suffix))
        used.add(str(dest).lower())
        saved.append(dest)
    return saved
