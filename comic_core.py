"""Archive reading, cover rendering and output-path planning. No UI code here."""
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
COMIC_EXT = {".cbz", ".cbr"}
ARCHIVE_DIR = "Archive"  # where backups and converted originals are parked; scans skip it

# option labels, shared by the UI and the planner
FORMATS = ["Original", "JPG", "PNG", "WebP"]
HEIGHTS = {"Original size": None, "1600 px tall": 1600, "1200 px tall": 1200,
           "800 px tall": 800, "400 px tall": 400}
WHERE_SUB, WHERE_CUSTOM, WHERE_BESIDE = "Subfolder of the source", "A folder I choose", "Beside each comic"
WHERES = [WHERE_SUB, WHERE_CUSTOM, WHERE_BESIDE]
ORG_FLAT, ORG_MIRROR, ORG_SERIES = "All in one folder", "Mirror folder structure", "Group by series"
ORGS = [ORG_FLAT, ORG_MIRROR, ORG_SERIES]
NAMES = ["Comic name", "Comic name - cover"]
CONFLICTS = ["Keep both", "Overwrite", "Skip"]


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


def is_page(name):
    p = Path(name)
    return p.suffix.lower() in IMG_EXT and "__MACOSX" not in name and not p.name.startswith(".")


# ---------- archives ----------

def find_extractor():
    for exe in ("7z", "7za", "unrar"):
        if shutil.which(exe):
            return exe
    for p in (r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"):
        if Path(p).exists():
            return p
    return shutil.which("tar")  # bsdtar on Windows 10/11 reads RAR


def extract_rar(src, dest):
    exe = find_extractor()
    if not exe:
        raise RuntimeError("No RAR extractor found. Install 7-Zip.")
    name = Path(exe).stem.lower()
    if name.startswith("7z"):
        cmd = [exe, "x", "-y", f"-o{dest}", str(src)]
    elif name == "unrar":
        cmd = [exe, "x", "-y", str(src), str(dest) + "\\"]
    else:
        cmd = [exe, "-xf", str(src), "-C", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"Extraction failed: {r.stderr.strip() or r.stdout.strip()}")


class Comic:
    """Uniform view over a cbz/cbr: sorted page names + byte reader."""

    def __init__(self, path):
        self.path = Path(path)
        self.tmp = None
        if zipfile.is_zipfile(self.path):  # also covers .cbr files that are really zips
            self.zip = zipfile.ZipFile(self.path)
            self.pages = sorted((n for n in self.zip.namelist() if is_page(n)), key=natural_key)
        else:
            self.zip = None
            self.tmp = Path(tempfile.mkdtemp(prefix="comic_"))
            try:
                extract_rar(self.path, self.tmp)
            except RuntimeError:
                self.close()
                raise
            files = (p for p in self.tmp.rglob("*") if p.is_file())
            rel = (str(p.relative_to(self.tmp)).replace("\\", "/") for p in files)
            self.pages = sorted((n for n in rel if is_page(n)), key=natural_key)
        if not self.pages:
            self.close()
            raise RuntimeError("No images found in archive.")

    def read(self, name):
        return self.zip.read(name) if self.zip else (self.tmp / name).read_bytes()

    def to_zip(self, out):
        if self.zip:
            shutil.copyfile(self.path, out)
            return
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:  # images are already compressed
            for p in sorted(self.tmp.rglob("*"), key=natural_key):
                if p.is_file():
                    z.write(p, p.relative_to(self.tmp).as_posix())

    def close(self):
        if self.zip:
            self.zip.close()
        if self.tmp:
            shutil.rmtree(self.tmp, ignore_errors=True)


# ---------- cover rendering ----------

def render_cover(data, src_ext, fmt="Original", quality=90, max_h=None):
    """Return (bytes, extension) for the cover, re-encoding only when asked to."""
    src_ext = src_ext.lower()
    if fmt == "Original" and not max_h:
        return data, src_ext
    img = Image.open(io.BytesIO(data))
    if max_h and img.height > max_h:  # only ever shrink
        img = img.resize((max(1, round(img.width * max_h / img.height)), max_h), Image.LANCZOS)
    if fmt == "Original":
        fmt = {".jpg": "JPG", ".jpeg": "JPG", ".webp": "WebP"}.get(src_ext, "PNG")  # gif/bmp -> PNG
    buf = io.BytesIO()
    if fmt == "JPG":
        img.convert("RGB").save(buf, "JPEG", quality=int(quality), optimize=True)
        return buf.getvalue(), ".jpg"
    if fmt == "WebP":
        img.save(buf, "WEBP", quality=int(quality))
        return buf.getvalue(), ".webp"
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue(), ".png"


# ---------- naming / paths ----------

def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "Untitled"


_ISSUE = re.compile(r"[\s_\-–#.]*(?:(?:issue|vol(?:ume)?|v|no|ch(?:apter)?)\.?\s*)?\d+(?:\.\d+)?\s*$", re.I)
_VOLUME = re.compile(r"[\s_\-–#.]*(?:vol(?:ume)?\.?|v)\s*\d+\s*$", re.I)


def series_name(stem):
    """'Batman #12 (2016)' -> 'Batman'. Falls back to the full stem."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", stem)
    s = re.sub(r"\s+", " ", s).strip()
    s = _VOLUME.sub("", _ISSUE.sub("", s, count=1), count=1).strip(" -–_.#")
    return s or stem


def plan_dest(src, root, o, ext):
    """Where the cover for `src` goes. `o` is the options dict; `root` is the scanned folder."""
    src, root = Path(src), Path(root)
    name = sanitize(src.stem + (" - cover" if o["name"] == NAMES[1] else ""))
    if o["where"] == WHERE_BESIDE:
        base = src.parent
    else:
        base = Path(o["custom"]) if o["where"] == WHERE_CUSTOM else root / sanitize(o["subfolder"])
        if o["organize"] == ORG_MIRROR:
            try:
                base = base / src.parent.relative_to(root)
            except ValueError:
                pass
        elif o["organize"] == ORG_SERIES:
            base = base / sanitize(series_name(src.stem))
    return base / f"{name}{ext}"


def unique(path, used=()):
    """First free variant of `path`: not on disk and not already claimed in this run."""
    path, n = Path(path), 1
    while path.exists() or str(path).lower() in used:
        path = path.with_name(f"{path.stem} ({n}){path.suffix}")
        n += 1
    return path


def in_archive(path, root):
    """True if `path` sits inside an Archive folder below `root`."""
    try:
        return ARCHIVE_DIR.lower() in (part.lower() for part in Path(path).relative_to(root).parts[:-1])
    except ValueError:
        return False


def find_comics(folder, recursive):
    it = Path(folder).rglob("*") if recursive else Path(folder).iterdir()
    files = [p for p in it if p.is_file() and p.suffix.lower() in COMIC_EXT and not in_archive(p, folder)]
    return sorted(files, key=lambda p: natural_key(p.relative_to(folder)))


def export_cover(comic, root, o, used):
    """Write the first page of `comic` as a cover. Returns ('saved' | 'skipped', dest)."""
    page = comic.pages[0]
    data, ext = render_cover(comic.read(page), Path(page).suffix, o["format"], o["quality"],
                             HEIGHTS[o["height"]])
    dest = plan_dest(comic.path, root, o, ext)
    if str(dest).lower() in used:  # two comics map to one name in this run: never clobber
        dest = unique(dest, used)
    elif dest.exists():
        if o["conflict"] == "Skip":
            return "skipped", dest
        if o["conflict"] == "Keep both":
            dest = unique(dest, used)
    used.add(str(dest).lower())
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return "saved", dest
