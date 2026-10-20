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

# ---- the three styles, removing icons, and what the page needs
from PIL import ImageChops
cov = Image.new("RGB", (300, 450), (200, 40, 40)); cov.paste(Image.new("RGB", (300, 150), (40, 40, 200)), (0, 0))
buf = io.BytesIO(); cov.save(buf, "JPEG"); data = buf.getvalue()
tiles = {s: fi.render_icon(data, s, "Blue", "Medium", "") for s in fi.STYLES}
assert all(t.size == (256, 256) and t.mode == "RGBA" for t in tiles.values()) and len({t.tobytes() for t in tiles.values()}) == 3
assert tiles[fi.STYLE_FLAT].getpixel((5, 128))[3] == 0 and tiles[fi.STYLE_POCKET].getpixel((128, 128))[3] == 255, "flat has bare sides, a folder fills the middle"
assert fi.render_icon(cov, fi.STYLE_POCKET, side=64).size == (64, 64), "a picture is as good as bytes"
assert fi.render_icon(data, fi.STYLE_POCKET, "Red").tobytes() != fi.render_icon(data, fi.STYLE_POCKET, "Green").tobytes()
assert fi.render_icon(data, fi.STYLE_POCKET, size="Small").tobytes() != fi.render_icon(data, fi.STYLE_POCKET, size="Large").tobytes()
for style in (fi.STYLE_POCKET, fi.STYLE_TAB):
    plain, named = fi.render_icon(data, style, badge=""), fi.render_icon(data, style, badge="Batman: The Long Halloween")
    assert ImageChops.difference(plain, named).getbbox(), "the series name is printed on the folder"
assert fi.render_icon(data, "no such style").tobytes() == fi.render_icon(data, fi.STYLE_FLAT).tobytes(), "an unknown style is flat"
assert fi.render_icon(data, fi.STYLE_FLAT).tobytes() == fi.render_icon(data).tobytes()

d2 = Path(tempfile.mkdtemp())
(d2 / "A").mkdir(); (d2 / "B").mkdir(); (d2 / "C").mkdir()
a, b2, c2 = d2 / "A", d2 / "B", d2 / "C"
fi.write_icon(a, data, style=fi.STYLE_POCKET, color="Blue", badge="A")
fi.write_icon(b2, data)    # flat, as before
with Image.open(a / "folder.ico") as ia, Image.open(b2 / "folder.ico") as ib:
    assert ia.size == ib.size == (256, 256) and ia.convert("RGBA").tobytes() != ib.convert("RGBA").tobytes(), "the style reaches the .ico"
assert fi.has_icon(a) and fi.has_icon(b2) and not fi.has_icon(c2)
# remove: the file, the icon line and the folder's read-only flag go; folder.jpg and other lines stay
fi._writable(a / "desktop.ini")
(a / "desktop.ini").write_bytes(("[.ShellClassInfo]\r\nInfoTip=My A\r\nIconResource=folder.ico,0\r\n").encode("utf-16"))
fi._set_attrs(a / "desktop.ini", fi.HIDDEN | fi.SYSTEM)
assert fi.remove_icon(a) == [fi.ICO] and not (a / "folder.ico").exists() and (a / "folder.jpg").exists()
assert not fi.has_icon(a) and "InfoTip=My A" in (a / "desktop.ini").read_text(encoding="utf-16") and "IconResource" not in (a / "desktop.ini").read_text(encoding="utf-16")
assert not fi._get_attrs(a) & fi.READONLY
assert sorted(fi.remove_icon(b2)) == sorted([fi.ICO, fi.INI]) and not (b2 / "desktop.ini").exists() and not fi._get_attrs(b2) & fi.READONLY and (b2 / "folder.jpg").exists()
assert fi.remove_icon(b2) == [] and fi.remove_icon(c2) == [], "nothing to take away"
# an icon some other program set is not ours to remove
fi._writable(c2 / "desktop.ini") if (c2 / "desktop.ini").exists() else None
(c2 / "desktop.ini").write_bytes(("[.ShellClassInfo]\r\nIconResource=C:/Other/thing.dll,3\r\n").encode("utf-16"))
assert fi.remove_icon(c2) == [] and "thing.dll" in (c2 / "desktop.ini").read_text(encoding="utf-16")
# planning: the folder itself counts, and subfolders only when asked
(d2 / "A" / "Sub").mkdir()
for p in (d2 / "A" / "A 01.cbz", d2 / "A" / "Sub" / "S 01.cbz"):
    with zipfile.ZipFile(p, "w") as z: z.writestr("1.jpg", data)
assert [f.name for f, _ in fi.plan_folders(a)] == ["A", "Sub"] and [f.name for f, _ in fi.plan_folders(a, recursive=False)] == ["A"]
# Refresh Explorer asks Windows and tells whether it could (the cache tool itself is not run here)
import subprocess
calls = []
real = subprocess.run
subprocess.run = lambda *a, **k: calls.append(a[0]) or None
try:
    assert fi.refresh_explorer() is True and calls == [["ie4uinit.exe", "-show"]]
finally:
    subprocess.run = real
for p in (a, b2, c2):
    for n in ("desktop.ini", "folder.ico"):
        if (p / n).exists(): fi._set_attrs(p / n, 0x80)
    fi._set_attrs(p, 0x10)
shutil.rmtree(d2)
print("ICONS OK")
