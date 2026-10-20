"""Windows folder icons from cover images: folder.ico + desktop.ini (+ optional folder.jpg).
No UI code. Explorer only honours an icon when desktop.ini is hidden+system and the folder is
read-only/system flagged, so those attributes are handled here.

The icon can be a flat cover, a folder with the cover sticking out of its pocket, or a folder whose front face is the
cover; the folder shapes are drawn here (no template files), in a few colours."""
import configparser
import ctypes
import io
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from comic_core import ARCHIVE_DIR, COMIC_EXT, natural_key

ICO, INI, JPG = "folder.ico", "desktop.ini", "folder.jpg"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
SECTION = ".ShellClassInfo"
READONLY, HIDDEN, SYSTEM = 0x1, 0x2, 0x4
SKIP_DIRS = {ARCHIVE_DIR.lower()}

STYLE_POCKET, STYLE_TAB, STYLE_FLAT = "Folder with cover", "Folder tab", "Cover only"
STYLES = [STYLE_POCKET, STYLE_TAB, STYLE_FLAT]
FOLDER_COLORS = {   # name: (the back of the folder, the front, the edge line)
    "Manila": ((214, 164, 62), (244, 205, 98), (140, 100, 30)),
    "Blue": ((52, 98, 190), (92, 146, 236), (24, 52, 120)),
    "Red": ((190, 50, 56), (236, 98, 100), (116, 24, 30)),
    "Green": ((52, 142, 84), (96, 192, 128), (24, 90, 48)),
    "Purple": ((110, 70, 180), (158, 120, 226), (64, 36, 120)),
    "Grey": ((110, 114, 128), (170, 174, 188), (62, 64, 76)),
}
COVER_SIZES = {"Small": 250, "Medium": 300, "Large": 350}   # how tall the cover is, out of 512


def supported():
    return os.name == "nt"


def _get_attrs(p):
    return ctypes.windll.kernel32.GetFileAttributesW(str(p))


def _set_attrs(p, attrs):
    ctypes.windll.kernel32.SetFileAttributesW(str(p), attrs)


def _writable(p):
    """Clear hidden/system/readonly on a file we're about to overwrite."""
    if Path(p).exists():
        _set_attrs(p, 0x80)  # FILE_ATTRIBUTE_NORMAL


def _refresh_shell(folder):
    try:
        ctypes.windll.shell32.SHChangeNotify(0x00002000, 0x1005, ctypes.c_wchar_p(str(folder)), None)
    except OSError:
        pass


def _font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _badge(canvas, text, box):
    """The series name on a pale label inside `box` (x0, y0, x1, y1), the text as large as fits."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=(255, 255, 255, 235), outline=(30, 30, 30, 255), width=5)
    size = max(14, y1 - y0 - 26)
    font = _font(size)
    while size > 14 and d.textlength(text, font=font) > (x1 - x0) - 36:
        size -= 3
        font = _font(size)
    while len(text) > 3 and d.textlength(text, font=font) > (x1 - x0) - 36:
        text = text[:-2].rstrip() + "…" if not text.endswith("…") else text[:-2] + "…"
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), text, font=font, fill=(25, 25, 25, 255), anchor="mm")


def _flat(cover, side):
    """The cover letterboxed onto a transparent square, so a portrait cover reads as a book."""
    scale = min(side / cover.width, side / cover.height)
    img = cover.resize((max(1, round(cover.width * scale)), max(1, round(cover.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return canvas


def render_icon(image, style=STYLE_FLAT, color="Manila", size="Medium", badge="", side=256):
    """The icon as a transparent `side` x `side` picture. `image` is the cover (bytes or a PIL image); `style` is one of
    STYLES; `color` a name of FOLDER_COLORS; `size` how big the cover is on the pocket style; `badge` a series name to
    print on the folder ('' for none). Drawn at twice the size and scaled down so the edges are smooth."""
    cover = image if isinstance(image, Image.Image) else Image.open(io.BytesIO(image))
    cover = cover.convert("RGBA")
    S = 512
    if style == STYLE_FLAT or style not in STYLES:
        return _flat(cover, 512).resize((side, side), Image.LANCZOS)
    back, front, edge = FOLDER_COLORS.get(color, FOLDER_COLORS["Manila"])
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    if style == STYLE_POCKET:
        d.rounded_rectangle((28, 56, 210, 140), radius=30, fill=back + (255,), outline=edge + (255,), width=6)   # the tab
        d.rounded_rectangle((28, 92, 484, 448), radius=40, fill=back + (255,), outline=edge + (255,), width=6)    # the back
        h = COVER_SIZES.get(size, 300)
        w = min(380, round(h * cover.width / cover.height))
        art = cover.resize((w, h), Image.LANCZOS)
        framed = Image.new("RGBA", (w + 12, h + 12), (30, 30, 30, 255))
        framed.paste(art, (6, 6), art)
        framed = framed.rotate(-7, resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(framed, ((S - framed.width) // 2, 232 - framed.height // 2 + 8))
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle((28, 252, 484, 448), radius=40, fill=front + (255,), outline=edge + (255,), width=6)   # the pocket
        d.line((64, 264, 448, 264), fill=tuple(min(255, c + 40) for c in front) + (255,), width=6)
        if badge:
            _badge(canvas, badge, (64, 330, 448, 408))
    else:
        d.rounded_rectangle((28, 56, 210, 140), radius=30, fill=edge + (255,))                                    # the tab
        d.rounded_rectangle((28, 92, 484, 456), radius=40, fill=edge + (255,))                                    # the folder
        face = (46, 112, 466, 438)
        fw, fh = face[2] - face[0], face[3] - face[1]
        art = ImageOps.fit(cover, (fw, fh), Image.LANCZOS)
        mask = Image.new("L", (fw, fh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw - 1, fh - 1), radius=28, fill=255)
        canvas.paste(art, (face[0], face[1]), mask)
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle(face, radius=28, outline=back + (255,), width=8)
        d.rounded_rectangle((28, 56, 210, 112), radius=30, outline=None, fill=back + (255,))
        if badge:
            _badge(canvas, badge, (70, 346, 442, 418))
    return canvas.resize((side, side), Image.LANCZOS)


def make_ico(image_bytes, dest, style=STYLE_FLAT, color="Manila", size="Medium", badge=""):
    """Write the icon in `style` (see `render_icon`) as a multi-size .ico."""
    render_icon(image_bytes, style, color, size, badge, side=256).save(dest, format="ICO", sizes=SIZES)


def _read_ini(path):
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str  # desktop.ini keys are case-sensitive in spirit; keep them as written
    if path.exists():
        raw = path.read_bytes()
        for enc in ("utf-16", "utf-8-sig", "cp1252"):
            try:
                cp.read_string(raw.decode(enc))
                break
            except (UnicodeError, configparser.Error):
                cp = configparser.ConfigParser(interpolation=None, strict=False)
                cp.optionxform = str
    return cp


def has_icon(folder):
    cp = _read_ini(Path(folder) / INI)
    return cp.has_option(SECTION, "IconResource") and ICO in cp.get(SECTION, "IconResource").lower()


def write_icon(folder, image_bytes, ico_on=True, save_jpg=True, replace=True, style=STYLE_FLAT, color="Manila",
               size="Medium", badge=""):
    """Give `folder` an icon (folder.ico + desktop.ini) and/or a folder.jpg made from `image_bytes`.
    With replace=False an existing folder.jpg is kept. `style`, `color`, `size` and `badge` shape the icon (see
    `render_icon`); folder.jpg is always the cover as it is. Returns the file names written."""
    if not supported():
        raise RuntimeError("Folder icons only work on Windows")
    folder = Path(folder)
    ico, ini, jpg = folder / ICO, folder / INI, folder / JPG
    written = []
    if ico_on:
        _writable(ico)
        make_ico(image_bytes, ico, style, color, size, badge)
        written.append(ICO)

        cp = _read_ini(ini)
        if not cp.has_section(SECTION):
            cp.add_section(SECTION)
        cp.set(SECTION, "IconResource", f"{ICO},0")
        _writable(ini)
        with open(ini, "w", encoding="utf-16") as f:
            cp.write(f, space_around_delimiters=False)
        written.append(INI)
        for p in (ico, ini):
            _set_attrs(p, HIDDEN | SYSTEM)
        _set_attrs(folder, (_get_attrs(folder) & ~0x80) | READONLY)  # Explorer needs this flag on the folder

    if save_jpg and (replace or not jpg.exists()):
        buf = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        _writable(jpg)
        buf.save(jpg, "JPEG", quality=90)
        written.append(JPG)
    _refresh_shell(folder)
    return written


def remove_icon(folder):
    """Take a folder's icon away again: folder.ico, the icon line of desktop.ini (the file goes when nothing else is in it)
    and the read-only flag Explorer needed. A desktop.ini that points at some other icon is left alone, and folder.jpg
    stays. Returns the file names removed."""
    folder = Path(folder)
    if not supported():
        raise RuntimeError("Folder icons only work on Windows")
    ini, ico = folder / INI, folder / ICO
    removed = []
    if has_icon(folder):
        cp = _read_ini(ini)
        cp.remove_option(SECTION, "IconResource")
        left = [sec for sec in cp.sections() if cp.options(sec)]
        _writable(ini)
        if left:
            with open(ini, "w", encoding="utf-16") as f:
                cp.write(f, space_around_delimiters=False)
            _set_attrs(ini, HIDDEN | SYSTEM)
        else:
            ini.unlink()
            removed.append(INI)
        if ico.exists():
            _writable(ico)
            ico.unlink()
            removed.append(ICO)
        attrs = _get_attrs(folder)
        if attrs != -1 and attrs & READONLY:
            _set_attrs(folder, attrs & ~READONLY)
        _refresh_shell(folder)
    return removed


def refresh_explorer():
    """Ask Windows to redraw its icons (a change of file associations makes Explorer drop what it remembered); on a
    Windows that has `ie4uinit` it also asks for the icon cache to be shown again. Safe to call at any time."""
    if not supported():
        return False
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)   # SHCNE_ASSOCCHANGED
    except OSError:
        return False
    try:
        subprocess.run(["ie4uinit.exe", "-show"], timeout=15, capture_output=True, creationflags=0x08000000)
    except (OSError, subprocess.SubprocessError):
        pass
    return True


def comics_in(folder):
    return sorted((p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in COMIC_EXT),
                  key=lambda p: natural_key(p.name))


def plan_folders(root, which_issue="First issue", recursive=True):
    """[(folder, comic)] for `root` itself and, with `recursive`, every folder under it that directly holds comics."""
    root = Path(root)
    subs = (sorted((p for p in root.rglob("*") if p.is_dir() and p.name.lower() not in SKIP_DIRS
                    and not any(part.lower() in SKIP_DIRS for part in p.relative_to(root).parts)),
                   key=lambda p: natural_key(p.relative_to(root))) if recursive else [])
    out = []
    for d in [root] + subs:
        comics = comics_in(d)
        if comics:
            out.append((d, comics[0] if which_issue == "First issue" else comics[-1]))
    return out
