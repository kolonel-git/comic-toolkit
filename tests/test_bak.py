import sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import archive_tools as at
from comic_core import find_comics, COMIC_EXT

def mk(p, n=3):
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n):
            z.writestr(f"{i:03d}.jpg", b"x" * 10)

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    f = d / "Batman 01.cbz"
    mk(f)
    # swap_in with backup, twice (collision)
    for _ in range(2):
        part = d / "Batman 01.cbz.part"
        mk(part)
        at.swap_in(part, f, True)
    names = sorted(p.name for p in (d / "Archive").iterdir())
    print("archive:", names)
    assert names == ["Batman 01.cbz (1).bak", "Batman 01.cbz.bak"], names
    assert not any(Path(n).suffix.lower() in COMIC_EXT for n in names)
    assert f.exists()
    # dispose_original MOVE
    g = d / "X 01.cbr"
    g.write_bytes(b"r")
    at.dispose_original(g, at.MOVE)
    assert (d / "Archive" / "X 01.cbr.bak").exists() and not g.exists()
    # restore = drop .bak
    b = d / "Archive" / "Batman 01.cbz.bak"
    assert zipfile.is_zipfile(b)
    print("scan:", [p.name for p in find_comics(d, False)] if find_comics.__code__.co_argcount == 2 else "skip")
print("OK")
