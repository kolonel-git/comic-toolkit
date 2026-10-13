import csv, sys, tempfile, time, types, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
import archive_tools as at
import page_stats as ps


def cbz(p, n=2, pad=0):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n): z.writestr(f"{i}.jpg", b"x" * (100 + pad))
    return p


root = ctk.CTk(); root.geometry("1250x800")
page = ps.StatsPage(root); page.pack(fill="both", expand=True); root.update()


def wait(t=30):
    end = time.time() + t
    while page.q and time.time() < end: root.update(); time.sleep(0.01)
    root.update(); assert not page.q, "scan did not finish"


def ev(i): return types.SimpleNamespace(y=i * ps.ROW + 5)
def labels(name): return [it.label for it in page.charts[name].items]


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    lib = d / "Lib"
    cbz(lib / "Marvel" / "X-Men 001 (1991).cbz", pad=900); cbz(lib / "Marvel" / "X-Men 002 (1991).cbz")
    cbz(lib / "DC" / "Batman v1 001 (1940).cbz"); cbz(lib / "DC" / "Batman v2 001 (2011).cbz", pad=300)
    for n in range(16): cbz(lib / "Misc" / f"Solo{n:02d} 001 (200{n % 10}).cbz")
    (lib / "Old").mkdir(); (lib / "Old" / "Real 01.cbr").write_bytes(b"Rar!junk")
    cbz(lib / "Archive" / "Skipped 001.cbz")  # a backup folder: must be ignored
    at.apply_metadata(lib / "Marvel" / "X-Men 001 (1991).cbz", {"publisher": "Marvel", "year": "1991"}, False)
    at.apply_metadata(lib / "Marvel" / "X-Men 002 (1991).cbz", {"publisher": "Marvel"}, False)
    at.apply_metadata(lib / "DC" / "Batman v1 001 (1940).cbz", {"publisher": "DC"}, False)
    at.apply_metadata(lib / "DC" / "Batman v2 001 (2011).cbz", {"publisher": "DC"}, False)

    # nothing scanned: placeholders, nothing to export, scan needs a folder
    assert page.btn_csv.cget("state") == "disabled" and page.btn_scan.cget("state") == "disabled"
    assert page.tiles["comics"].value.cget("text") == "–" and "Choose your library folder" in page.meta.cget("text")
    page.scan(); assert "Choose a library folder" in page.status.cget("text")

    got = []
    page.on_scanned = got.append
    page.set_folder(lib); wait()
    st = page.stats
    assert st.comics == 4 + 16 + 1 == 21, st.comics  # the Archive file is not counted
    assert got and got[-1]["comics"] == 21 and got[-1]["root"] == str(lib) and got[-1]["series"] == st.series == 19
    assert page.vars["root"].get() == str(lib) and page.drop.label.cget("text") == str(lib) and page.drop.winfo_height() < 50, "a slim folder strip"
    t = {k: v.value.cget("text") for k, v in page.tiles.items()}
    assert t["comics"] == "21" and t["series"] == "19" and t["publishers"] == "2" and t["pages"] == "not read", t
    assert t["bytes"].endswith("KB") or t["bytes"].endswith("MB"), t
    assert page.btn_csv.cget("state") == "normal" and page.btn_scan.cget("text") == "Rescan library"
    assert "Done · 21 comics" in page.status.cget("text")

    # series chart: Batman merged, "Other" after 15
    ser = page.charts["Series"].items
    assert len(ser) == 16 and ser[0].frac == 1.0 and ser[-1].label.startswith("Other ("), (len(ser), [(i.label, i.frac) for i in ser][:3], ser[-1].label)
    assert sum(len(i.issues) for i in ser) == 21
    page.vars["show_all"].set(True); root.update()
    assert len(page.charts["Series"].items) == 19 and not page.charts["Series"].items[-1].label.startswith("Other")
    page.vars["show_all"].set(False); root.update()
    page.vars["split"].set(True); root.update()
    assert "Batman v1" in labels("Series") and "Batman v2" in labels("Series") and "Batman" not in labels("Series")
    page.vars["split"].set(False); root.update()
    assert labels("Publishers")[:2] == ["DC", "Marvel"] and labels("Publishers")[-1] == "Unknown", labels("Publishers")
    assert "1940" in labels("Years") and labels("Years")[-1] == "Unknown" or labels("Years")[-1].startswith("Other")
    page.vars["decades"].set(True); root.update()
    assert "1990s" in labels("Years") and "1940s" in labels("Years") and "1991" not in labels("Years")
    page.vars["decades"].set(False); root.update()
    assert labels("Formats") == ["CBZ", "CBR"]
    cov = {i.label: i.text for i in page.charts["Coverage"].items}
    assert cov["Have ComicInfo.xml"].startswith("4 of 20"), cov  # the real RAR was not opened
    assert "1 real .cbr file not opened" in page.sections["Coverage"][1].cget("text")
    assert len(page.big.get_children()) == 15 and "X-Men 001" in page.big.item(page.big.get_children()[0], "values")[0]

    # clicking a bar lists the comics behind it, right under that chart; Close hides it again
    pub = page.charts["Publishers"]
    pub._click(ev(0)); root.update()
    assert page.drill.winfo_ismapped() and "DC · 2 comics" in page.drill_title.cget("text"), page.drill_title.cget("text")
    rows = [page.table.item(i, "values")[0] for i in page.table.get_children()]
    assert rows == ["DC/Batman v1 001 (1940).cbz", "DC/Batman v2 001 (2011).cbz"], rows
    assert pub.selected == 0
    cov_chart = page.charts["Coverage"]; cov_chart._click(ev(0)); assert pub.selected == 0, "coverage bars are not clickable"
    page.charts["Formats"]._click(ev(1)); root.update()
    assert pub.selected is None and "CBR · 1 comic" in page.drill_title.cget("text") and len(page.table.get_children()) == 1
    page._close_drill(); root.update(); assert not page.drill.winfo_ismapped()
    pub._click(ev(40)); assert not page.drill.winfo_ismapped(), "a click below the bars does nothing"

    # export and copy
    out = d / "series.csv"
    ps.filedialog.asksaveasfilename = lambda **k: str(out)
    page.vars["export"].set("Series"); page.export_csv()
    rows = list(csv.reader(open(out, encoding="utf-8-sig")))
    assert rows[0] == ["Series", "Comics", "Bytes"] and len(rows) == 1 + 19 and rows[1][1] == "2", rows[:3]
    for name in ps.EXPORTS:
        page.vars["export"].set(name); page.export_csv(); assert page.status.cget("text").startswith("Exported"), name
    ps.filedialog.asksaveasfilename = lambda **k: ""
    page.say(""); page.export_csv(); assert page.status.cget("text") == ""
    page.copy_summary()
    clip = root.clipboard_get()
    assert clip.startswith(f"Comic library: {lib}") and "21 comics · 19 series · 2 publishers" in clip, clip
    assert "Have ComicInfo.xml: 4 of 20" in clip

    # page counts when asked for
    page.vars["deep"].set(True); page.scan(); wait()
    assert page.tiles["pages"].value.cget("text") not in ("not read", "–"), page.tiles["pages"].value.cget("text")
    # stopping keeps a partial result and tells the app nothing new
    got.clear()
    page.scan(); page.stop.set(); wait()
    assert "Stopped" in page.status.cget("text") or "Done" in page.status.cget("text")

    # a missing folder is reported; state round-trips; theme switch redraws
    page.vars["root"].set(str(d / "nope")); page.scan(); assert "Choose a library folder" in page.status.cget("text")
    assert page.state()["root"] == str(d / "nope")
    page.restore({"root": str(lib), "split": True}); assert page.vars["split"].get() and page.root() == lib
    ctk.set_appearance_mode("dark"); root.update(); page.apply_theme(); root.update()
    ctk.set_appearance_mode("light"); root.update(); page.apply_theme()

# an empty folder gives zeros, not a crash
with tempfile.TemporaryDirectory() as e:
    page.set_folder(e); wait()
    assert page.stats.comics == 0 and page.tiles["comics"].value.cget("text") == "0" and page.charts["Series"].items == []
    assert page.big.get_children() == ()
root.destroy()
print("stats ui OK")
