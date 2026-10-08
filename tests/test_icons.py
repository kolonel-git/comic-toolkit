import io, shutil, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
import folder_icons as fi

d = Path(tempfile.mkdtemp())
(d / "DC" / "Batman").mkdir(parents=True); (d / "DC" / "Superman").mkdir(); (d / "Archive").mkdir()
b = io.BytesIO(); Image.new("RGB", (300, 450), (200, 40, 40)).save(b, "JPEG"); cover = b.getvalue()
for p in (d / "DC" / "Batman" / "Batman 02.cbz", d / "DC" / "Batman" / "Batman 01.cbz", d / "DC" / "Superman" / "S 1.cbz", d / "Archive" / "Old.cbz"):
    with zipfile.ZipFile(p, "w") as z: z.writestr("1.jpg", cover)
print([(str(f.relative_to(d)), c.name) for f, c in fi.plan_folders(d)])
print([(str(f.relative_to(d)), c.name) for f, c in fi.plan_folders(d, "Last issue")][:1])

f = d / "DC" / "Batman"
(f / "desktop.ini").write_text("[.ShellClassInfo]\nInfoTip=My Batman\n", encoding="utf-8")
print("written:", fi.write_icon(f, cover))
print("ini:", (f / "desktop.ini").read_bytes()[:2], (f / "desktop.ini").read_text(encoding="utf-16"))
print("attrs ini/ico/folder:", [hex(fi._get_attrs(p)) for p in (f / "desktop.ini", f / "folder.ico", f)])
print("has_icon:", fi.has_icon(f), fi.has_icon(d / "DC" / "Superman"))
with Image.open(f / "folder.ico") as im: print("ico sizes:", sorted(im.info.get("sizes", [])))
print("rewrite works:", fi.write_icon(f, cover, save_jpg=True, replace=True))
# cleanup: clear flags so rmtree works
for p in [f / "desktop.ini", f / "folder.ico"]: fi._set_attrs(p, 0x80)
fi._set_attrs(f, 0x10)
shutil.rmtree(d)
