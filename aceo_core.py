"""ACEO card sheets: put comic covers into the card slots of a blank PDF template and write a PDF. No UI code.

The template is a PDF page whose card outlines are drawn as rectangles (the bundled "ACEO - Full Page BLANK.pdf" has
eight 3.5" x 2.5" slots on a Letter page). The slots are read from the page itself, covers are fitted into them, each
page is rendered as a picture, and the template's outlines are laid back on top as crisp vector lines.
"""
from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from comic_core import COMIC_EXT, IMG_EXT, Comic, natural_key

TEMPLATE_NAME = "ACEO - Full Page BLANK.pdf"
FITS = ["Fill the card (crop edges)", "Fit inside (show the whole cover)", "Stretch to the card"]
ROTATIONS = ["Turn to fit, top of cover on the left", "Turn to fit, top of cover on the right", "Never turn"]
BACKGROUNDS = {"White": (255, 255, 255), "Black": (0, 0, 0), "Light grey": (225, 225, 225)}
SOURCES = ["First page (the cover)", "Last page (the back cover)"]
QUALITIES = {"Draft (150 dpi)": 150, "Standard (300 dpi)": 300, "High (600 dpi)": 600}
AUTO_COLOR, CUSTOM_COLOR = "Automatic (contrasts with the background)", "Custom (hex below)"
OUTLINE_COLORS = {AUTO_COLOR: None, "Black": (0, 0, 0), "White": (255, 255, 255), "Light grey": (200, 200, 200),
                  "Grey": (128, 128, 128), "Red": (220, 30, 30), "Gold": (212, 175, 55), CUSTOM_COLOR: None}
DEFAULT_OPTIONS = {"fit": FITS[0], "rotate": ROTATIONS[0], "background": "White", "dpi": "Standard (300 dpi)",
                   "inset": 0.0, "outlines": True, "copies": 1, "outline_color": AUTO_COLOR, "outline_hex": "#FFFFFF",
                   "outline_width": 0.0}


@dataclass
class Slot:
    x: float  # points, from the top-left corner of the page
    y: float
    w: float
    h: float


@dataclass
class Template:
    path: Path
    width: float  # points
    height: float
    slots: list
    line_width: float = 1.0  # the template's own outline thickness, in points


def _pypdf():
    """pypdf is imported on first use so the rest of the app starts without it."""
    try:
        import pypdf
    except ImportError as e:
        raise RuntimeError("The ACEO sheets tool needs pypdf: run  pip install pypdf") from e
    return pypdf


def default_template():
    return Path(__file__).with_name(TEMPLATE_NAME)


# ---------- reading the template ----------

_NUM = rb"(-?\d+(?:\.\d+)?)"
_OPS = re.compile(rb"(?:" + b"\\s+".join([_NUM] * 6) + rb"\s+cm)|(?:" + b"\\s+".join([_NUM] * 4) + rb"\s+re)")


def read_template(path):
    """Find the card slots in a template PDF: every `x y w h re` rectangle on its first page, placed through the page's
    `cm` transforms. Slots are returned in reading order (rows top to bottom, left to right)."""
    path = Path(path)
    page = _pypdf().PdfReader(str(path)).pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    contents = page.get_contents()  # compare with None: an empty stream object is falsy
    data = contents.get_data() if contents is not None else b""
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # a b c d e f
    lw = re.search(rb"(\d+(?:\.\d+)?)\s+w\b", data)
    slots = []
    for m in _OPS.finditer(data):
        v = [float(g) for g in m.groups() if g is not None]
        if len(v) == 6:  # cm: the new matrix applies before the current one
            a, b, c, d, e, f = v
            A, B, C, D, E, F = ctm
            ctm = (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)
        else:
            x, y, w, h = v
            A, B, C, D, E, F = ctm
            xs = [A * px + C * py + E for px, py in ((x, y), (x + w, y + h))]
            ys = [B * px + D * py + F for px, py in ((x, y), (x + w, y + h))]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            if x1 - x0 > 10 and y1 - y0 > 10:  # ignore specks
                slots.append(Slot(x0, height - y1, x1 - x0, y1 - y0))
    if not slots:
        raise ValueError("No card outlines (rectangles) were found on the first page of this template")
    tol = min(s.h for s in slots) / 2
    slots.sort(key=lambda s: (round(s.y / tol), s.x))
    return Template(path, width, height, slots, float(lw.group(1)) if lw else 1.0)


# ---------- covers ----------

def is_cover_source(path):
    return Path(path).suffix.lower() in COMIC_EXT | IMG_EXT


def load_cover(path, source=SOURCES[0]):
    """Image bytes for one cover: a comic's first (or last) page, or the image file itself."""
    path = Path(path)
    if path.suffix.lower() in IMG_EXT:
        return path.read_bytes()
    comic = Comic(path)
    try:
        return comic.read(comic.pages[-1] if source == SOURCES[1] else comic.pages[0])
    finally:
        comic.close()


def find_sources(paths):
    """Comics and images from files and folders, folders searched including subfolders. Archive folders are skipped."""
    from comic_core import in_archive
    out, seen = [], set()
    for p in map(Path, paths):
        found = [p] if p.is_file() else sorted((f for f in p.rglob("*") if f.is_file() and not in_archive(f, p)),
                                               key=lambda f: natural_key(f.relative_to(p))) if p.is_dir() else []
        for f in found:
            if is_cover_source(f) and str(f).lower() not in seen:
                seen.add(str(f).lower())
                out.append(f)
    return out


# ---------- one card, one sheet ----------

def decode(data, max_side=None):
    img = Image.open(io.BytesIO(data))
    if max_side and hasattr(img, "draft"):
        img.draft("RGB", (max_side, max_side))  # JPEG: decode smaller, much faster
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def fit_card(img, size, o):
    """The cover as an image exactly `size` (w, h) pixels, turned, scaled and cropped as the options say."""
    w, h = size
    o = {**DEFAULT_OPTIONS, **o}
    if o["rotate"] != ROTATIONS[2] and (img.height > img.width) != (h > w):
        img = img.rotate(90 if o["rotate"] == ROTATIONS[0] else -90, expand=True)
    bg = BACKGROUNDS.get(o["background"], (255, 255, 255))
    if o["fit"] == FITS[2]:
        return img.resize((w, h), Image.LANCZOS)
    if o["fit"] == FITS[1]:
        scale = min(w / img.width, h / img.height)
        small = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
        card = Image.new("RGB", (w, h), bg)
        card.paste(small, ((w - small.width) // 2, (h - small.height) // 2))
        return card
    return ImageOps.fit(img, (w, h), Image.LANCZOS)


def parse_hex(text):
    """'#RRGGBB', 'RRGGBB' or '#RGB' as an (r, g, b) tuple, or None when it is not a colour."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", (text or "").strip())
    if not m:
        return None
    h = m.group(1)
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def outline_rgb(o):
    """The outline colour as (r, g, b): the chosen one, a custom hex, or black/white to contrast with the background."""
    o = {**DEFAULT_OPTIONS, **o}
    chosen = OUTLINE_COLORS.get(o["outline_color"])
    if o["outline_color"] == CUSTOM_COLOR:
        chosen = parse_hex(o["outline_hex"])
    if chosen is not None:
        return chosen
    r, g, b = BACKGROUNDS.get(o["background"], (255, 255, 255))
    return (0, 0, 0) if 0.299 * r + 0.587 * g + 0.114 * b > 128 else (255, 255, 255)


def outline_width(tpl, o):
    try:
        w = float(o.get("outline_width") or 0)
    except (TypeError, ValueError):
        w = 0.0
    return w if w > 0 else tpl.line_width


def compose_sheet(tpl, covers, o, dpi, outlines_in_image=False):
    """One page as a picture. `covers` has one entry per slot: image bytes, a PIL image, or None for an empty slot."""
    o = {**DEFAULT_OPTIONS, **o}
    s = dpi / 72
    page = Image.new("RGB", (round(tpl.width * s), round(tpl.height * s)), (255, 255, 255))
    inset = float(o["inset"] or 0)
    for slot, cover in zip(tpl.slots, covers):
        if cover is None:
            continue
        x, y = slot.x + inset, slot.y + inset
        w, h = slot.w - 2 * inset, slot.h - 2 * inset
        if w <= 0 or h <= 0:
            continue
        box = (round(x * s), round(y * s), max(1, round(w * s)), max(1, round(h * s)))
        img = cover if isinstance(cover, Image.Image) else decode(cover, max_side=max(box[2], box[3]) * 2)
        page.paste(fit_card(img, (box[2], box[3]), o), (box[0], box[1]))
    if outlines_in_image:  # used for the on-screen preview; the PDF gets the template's own vector lines
        d = ImageDraw.Draw(page)
        rgb, lw = outline_rgb(o), max(1, round(outline_width(tpl, o) * s))
        for slot in tpl.slots:
            d.rectangle([slot.x * s, slot.y * s, (slot.x + slot.w) * s, (slot.y + slot.h) * s], outline=rgb, width=lw)
    return page


def sheet_count(n_cards, tpl):
    return max(1, math.ceil(n_cards / len(tpl.slots))) if n_cards else 0


def expand(covers, copies):
    """Each cover repeated `copies` times in a row (A A B B ...)."""
    return [c for c in covers for _ in range(max(1, int(copies or 1)))]


def chunk(cards, tpl):
    n = len(tpl.slots)
    return [cards[i:i + n] + [None] * (n - len(cards[i:i + n])) for i in range(0, len(cards), n)]


# ---------- the PDF ----------

def outline_overlay(tpl, o):
    """A transparent page carrying only the card outlines, in the chosen colour and thickness. It replaces the template
    page as the overlay so the colour can change; the rectangles are the template's own."""
    pypdf = _pypdf()
    from pypdf.generic import DecodedStreamObject, NameObject
    r, g, b = (c / 255 for c in outline_rgb(o))
    ops = [f"q {r:.4f} {g:.4f} {b:.4f} RG {outline_width(tpl, o):.3f} w"]
    ops += [f"{s.x:.3f} {tpl.height - s.y - s.h:.3f} {s.w:.3f} {s.h:.3f} re" for s in tpl.slots]
    ops += ["S", "Q", ""]
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(tpl.width, tpl.height)
    stream = DecodedStreamObject()
    stream.set_data("\n".join(ops).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    page._keep = writer  # the page's objects live in this writer
    return page


def render_pdf(tpl, cards, o, out_path, progress=None, stop=None):
    """Write the sheets to `out_path`. `cards` is a list of image bytes in card order. Returns the number of sheets.
    Pages are rendered one at a time so memory stays small even at 600 dpi."""
    pypdf = _pypdf()
    o = {**DEFAULT_OPTIONS, **o}
    dpi = QUALITIES.get(o["dpi"], 300) if isinstance(o["dpi"], str) else int(o["dpi"])
    sheets = chunk(cards, tpl)
    writer = pypdf.PdfWriter()
    overlay = outline_overlay(tpl, o) if o["outlines"] else None
    for k, group in enumerate(sheets, 1):
        if stop is not None and stop.is_set():
            raise InterruptedError("Stopped")
        if progress:
            progress(k, len(sheets))
        image = compose_sheet(tpl, group, o, dpi)
        buf = io.BytesIO()
        image.save(buf, "PDF", resolution=dpi, quality=95)
        del image
        page = pypdf.PdfReader(io.BytesIO(buf.getvalue())).pages[0]
        if overlay is not None:
            page.merge_page(overlay)
        writer.add_page(page)
    writer.add_metadata({"/Title": "ACEO card sheets", "/Producer": "Comic Toolkit"})
    out_path = Path(out_path)
    tmp = out_path.with_name(out_path.name + ".part")
    try:
        with open(tmp, "wb") as f:
            writer.write(f)
        tmp.replace(out_path)
    finally:
        tmp.unlink(missing_ok=True)
    return len(sheets)
