import json, sys, tempfile, time, warnings, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.simplefilter("error", SyntaxWarning)
import library_scan as ls, page_audit as pa
import customtkinter as ctk

def mk(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z: z.writestr("0.jpg", b"x")

with tempfile.TemporaryDirectory() as d:
    d = Path(d); cache = d / "c.json"
    mk(d / "Comics" / "A 01.cbz"); mk(d / "Comics Old" / "B 01.cbz")
    ls.scan_library(d / "Comics Old", cache_path=cache)
    ls.scan_library(d / "Comics", cache_path=cache)  # must NOT prune the sibling's entry
    keys = list(json.loads(cache.read_text())["entries"])
    print(keys)
    assert any("comics old" in k for k in keys) and any(k.endswith("a 01.cbz") for k in keys)
    (d / "Comics" / "A 01.cbz").unlink()
    ls.scan_library(d / "Comics", cache_path=cache)
    keys = list(json.loads(cache.read_text())["entries"])
    assert not any(k.endswith("a 01.cbz") for k in keys) and any("comics old" in k for k in keys)

    root = ctk.CTk(); page = pa.AuditPage(root); page.pack(fill="both", expand=True); root.update()
    def wait():
        t = time.time()
        while page.q and time.time() - t < 20: root.update(); time.sleep(0.01)
        root.update(); assert not page.q
    # nothing checked
    mk(d / "Lib" / "X 01.cbz"); page.set_folder(d / "Lib")
    page.vars["deep"].set(False); page.vars["integrity"].set(False)
    ls_orig = pa.scan_library
    pa.scan_library = lambda *a, **k: ls_orig(*a, cache_path=cache, **k)
    page.scan(); wait()
    print("meta:", page.meta.cget("text"), "| hint:", page.hint.cget("text"))
    assert page.meta.cget("text") == "Nothing was checked."
    page.vars["deep"].set(True); page.scan(); wait()
    assert page.meta.cget("text") == "1 file with problems"  # fixture cover bytes are junk
    # worker failure must release the page
    def boom(*a, **k): raise RuntimeError("disk exploded")
    pa.scan_library = boom
    page.scan(); wait()
    print("status:", page.status.cget("text"))
    assert page.q is None and "disk exploded" in page.status.cget("text") and page.btn_scan.cget("state") == "normal"
    root.destroy()
print("FIXES OK")
