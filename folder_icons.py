"""Windows folder icons from cover images: folder.ico + desktop.ini (+ optional folder.jpg).
No UI code. Explorer only honours an icon when desktop.ini is hidden+system and the folder is
read-only/system flagged, so those attributes are handled here."""
import configparser
import ctypes
import io
import os
from pathlib import Path

from PIL import Image

from comic_core import ARCHIVE_DIR, COMIC_EXT, natural_key

ICO, INI, JPG = "folder.ico", "desktop.ini", "folder.jpg"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
SECTION = ".ShellClassInfo"
READONLY, HIDDEN, SYSTEM = 0x1, 0x2, 0x4
SKIP_DIRS = {ARCHIVE_DIR.lower()}


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


def make_ico(image_bytes, dest):
    """Letterbox the cover onto a transparent square so a portrait cover reads as a book icon."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    side = 256
    scale = min(side / img.width, side / img.height)
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    canvas.save(dest, format="ICO", sizes=SIZES)


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


def write_icon(folder, image_bytes, ico_on=True, save_jpg=True, replace=True):
    """Give `folder` an icon (folder.ico + desktop.ini) and/or a folder.jpg made from `image_bytes`.
    With replace=False an existing folder.jpg is kept. Returns the file names written."""
    if not supported():
        raise RuntimeError("Folder icons only work on Windows")
    folder = Path(folder)
    ico, ini, jpg = folder / ICO, folder / INI, folder / JPG
    written = []
    if ico_on:
        _writable(ico)
        make_ico(image_bytes, ico)
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


def comics_in(folder):
    return sorted((p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in COMIC_EXT),
                  key=lambda p: natural_key(p.name))


def plan_folders(root, which_issue="First issue"):
    """[(folder, comic)] for every folder under `root` that directly holds comics."""
    root = Path(root)
    dirs = sorted((p for p in root.rglob("*") if p.is_dir() and p.name.lower() not in SKIP_DIRS
                   and not any(part.lower() in SKIP_DIRS for part in p.relative_to(root).parts)),
                  key=lambda p: natural_key(p.relative_to(root)))
    out = []
    for d in dirs:
        comics = comics_in(d)
        if comics:
            out.append((d, comics[0] if which_issue == "First issue" else comics[-1]))
    return out
