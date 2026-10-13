import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
import intake_core as ic
import page_intake as pi


def jpg():
    b = io.BytesIO(); Image.new("RGB", (60, 90), (9, 9, 9)).save(b, "JPEG"); return b.getvalue()


def cbz(p, junk=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(3): z.writestr(f"{i + 1:03d}.jpg", jpg())
        if junk: z.writestr("Thumbs.db", b"x")


root = ctk.CTk(); root.geometry("1200x780")
errors = []; root.report_callback_exception = lambda *a: errors.append(a)
page = pi.IntakePage(root); page.pack(fill="both", expand=True); root.update()
rows = lambda: [page.tree.item(r, "values") for r in page.tree.get_children()]


def wait():
    t = time.time()
    while page.busy and time.time() - t < 60: root.update(); time.sleep(0.01)
    root.update(); assert not page.busy


assert page.btn_apply.cget("state") == "disabled" and page.btn_open.cget("state") == "disabled"
with tempfile.TemporaryDirectory() as d:
    d = Path(d); inbox, ready = d / "in", d / "ready"
    cbz(inbox / "batman 12 (2016).cbz", junk=True); cbz(inbox / "Saga" / "saga 003.cbz"); cbz(inbox / "012.cbz")
    cbz(ready / "Batman" / "Batman 013 (2016).cbz")
    page.vars["inbox"].set(str(inbox))
    page.scan_inbox(); wait()
    assert len(rows()) == 3 and "3 comics" in page.meta.cget("text")
    assert all(r[4] == "" for r in rows())                          # no Ready folder yet: nothing planned
    page.apply(); assert "Ready folder" in page.status.cget("text")
    page.vars["ready"].set(str(ready)); page.recompute(); root.update()
    got = {r[1]: r for r in rows()}
    assert got["batman 12 (2016).cbz"][2].endswith("batman 012 (2016).cbz") and got["batman 12 (2016).cbz"][4] == "Ready"
    assert got["batman 12 (2016).cbz"][0] == "☑" and "clean" in got["batman 12 (2016).cbz"][3]
    assert got["012.cbz"][4] == "No series" and got["012.cbz"][0] == "☐"
    assert "2 to add" in page.meta.cget("text") and "need a look" in page.meta.cget("text") and page.btn_apply.cget("state") == "normal"
    assert page.add_paths([inbox]) == 0                              # nothing new the second time
    # untick Saga, tick the no-series one
    by_name = {page.by_iid[i].src.name: page.by_iid[i] for i in page.tree.get_children()}
    ev = lambda it: type("E", (), {"x": 10, "y": page.tree.bbox(it.iid)[1] + 5})()
    page.tree.update()
    page._click(ev(by_name["saga 003.cbz"])); assert not by_name["saga 003.cbz"].checked
    page._click(ev(by_name["saga 003.cbz"])); assert by_name["saga 003.cbz"].checked
    # run, declining first
    messagebox.askyesno = lambda *a, **k: False
    page.apply(); assert not page.busy and (inbox / "batman 12 (2016).cbz").exists()
    messagebox.askyesno = lambda *a, **k: True
    page.select_all(False); page._click(ev(by_name["batman 12 (2016).cbz"])); page._click(ev(by_name["saga 003.cbz"]))
    page.apply(); wait(); root.update()
    assert (ready / "batman" / "batman 012 (2016).cbz").exists() and (ready / "Saga" / "saga 003.cbz").exists()
    assert not (inbox / "batman 12 (2016).cbz").exists() and not (inbox / "Saga").exists() and (inbox / "012.cbz").exists()
    assert "Added 2 comics" in page.status.cget("text") and [r[1] for r in rows()] == ["012.cbz"]
    # a broken file reports its error and can be ticked to retry
    (inbox / "Broken 001.cbz").write_bytes(b"nope")
    page.scan_inbox(); wait()
    br = [page.by_iid[i] for i in page.tree.get_children() if page.by_iid[i].src.name == "Broken 001.cbz"][0]
    assert br.checked; page.apply(); wait(); root.update()
    br = [it for it in page.items if it.src.name == "Broken 001.cbz"][0]
    assert br.status == ic.FAILED and br.note and "1 failed" in page.status.cget("text") and (inbox / "Broken 001.cbz").exists()
    page.clear(); assert rows() == []
assert not errors, errors[:2]
root.destroy()
print("intake UI OK")
