import io, shutil, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
import archive_tools as a
from comic_core import find_comics

d = Path(tempfile.mkdtemp())
def img():
    b = io.BytesIO(); Image.new("RGB", (30, 40)).save(b, "JPEG"); return b.getvalue()

def mk(path, names, extra=None):
    with zipfile.ZipFile(path, "w") as z:
        for n in names: z.writestr(n, img() if n.lower().endswith((".jpg", ".png")) else b"junk")
        for n, data in (extra or {}).items(): z.writestr(n, data)

messy = d / "Messy 01.cbz"
mk(messy, ["Messy 01/p10.jpg", "Messy 01/p2.JPG", "Messy 01/p1.jpg", "Messy 01/Thumbs.db", "__MACOSX/._p1.jpg",
           "readme.nfo", "Messy 01/zzz-ad.jpg"], {"Messy 01/ComicInfo.xml": "<ComicInfo><Series>Old</Series></ComicInfo>"})

print("--- cleanup plan (sequential, junk, pattern zzz*)")
plan = a.plan_cleanup(messy, True, "zzz*", a.SEQUENTIAL)
print(a.describe_cleanup(plan)); print(plan["order"])
a.apply_cleanup(messy, plan, backup=True)
print(sorted(zipfile.ZipFile(messy).namelist()), "| archive:", sorted(p.name for p in (d / "Archive").iterdir()))
print("again:", a.describe_cleanup(a.plan_cleanup(messy, True, "zzz*", a.SEQUENTIAL)))
print("find_comics skips Archive:", [p.name for p in find_comics(d, True)])

print("--- keep names, junk off")
k = d / "Keep.cbz"; mk(k, ["b.jpg", "a.jpg", "x.txt"])
print(a.describe_cleanup(a.plan_cleanup(k, False, "", a.KEEP_NAMES)))
print(a.describe_cleanup(a.plan_cleanup(k, True, "", a.KEEP_NAMES)))
try: a.plan_cleanup(k, True, "*.jpg", a.KEEP_NAMES)
except ValueError as e: print("expected error:", e)

print("--- metadata")
raw_name, raw = a.read_comicinfo_raw(messy); print(raw_name)
a.apply_metadata(messy, {"series": "Messy", "issue": "1", "year": "2020"}, backup=False)
print(a.read_comicinfo_raw(messy)[1].decode())
print(len([n for n in zipfile.ZipFile(messy).namelist()]), "entries,", "pages ok")
fresh = d / "Fresh.cbz"; mk(fresh, ["1.jpg"])
a.apply_metadata(fresh, {"series": "Fresh & New", "issue": "7"}, backup=True)
print(a.read_comicinfo_raw(fresh)[1].decode())
bad = d / "Bad.cbz"; mk(bad, ["1.jpg"], {"ComicInfo.xml": "<broken"})
try: a.apply_metadata(bad, {"series": "x"}, False)
except ValueError as e: print("expected error:", e)
print("no .part left:", not list(d.rglob("*.part")))

print("--- convert (zip-backed cbr)")
cbr = d / "Old 01.cbr"; mk(cbr, ["1.jpg", "2.jpg", "ComicInfo.xml"])
n = a.convert_to_cbz(cbr, cbr.with_suffix(".cbz")); print("pages", n)
a.dispose_original(cbr, a.MOVE); print(sorted(p.name for p in d.iterdir()), sorted(p.name for p in (d / "Archive").iterdir()))
shutil.rmtree(d)
