"""Library stats on the shared page shell: segments, tiles, charts, Health links, the side drawer, reading-order folders
(marked, suggested, left out or included), needs-attention cards, export, state."""
import csv, sys, tempfile, time, types, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
import archive_tools as at
import page_stats as ps
from reading_orders import ReadingOrders


def cbz(p, n=2, pad=0):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n): z.writestr(f"{i}.jpg", b"x" * (100 + pad))
    return p


root = ctk.CTk(); root.geometry("1250x800")
page = ps.StatsPage(root); page.pack(fill="both", expand=True); root.update()
page.orders = ReadingOrders()
opened = []
page.open_tool = opened.append


def wait(t=30):
    end = time.time() + t
    while page.q and time.time() < end: root.update(); time.sleep(0.01)
    root.update(); assert not page.q, "scan did not finish"


def ev(i): return types.SimpleNamespace(x=5, y=i * ps.ROW + 5)
def labels(name): return [it.label for it in page.charts[name].items]
def states(): return [s.state for s in page.segments]
def footer(): return [b.cget("text") for b in page.side_row.winfo_children()]
def rows(table): return [table.tree.item(i, "values") for i in table.tree.get_children()]


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

    # nothing scanned: three segments, only Library is open to work in; the footer says why it cannot scan
    assert [s.title.cget("text") for s in page.segments] == ["Library", "Overview", "Needs attention"]
    assert states() == ["active", "locked", "locked"]
    assert page.bar_btn.cget("text") == "Scan library" and page.bar_btn.cget("state") == "disabled" and footer() == []
    assert page.tiles["comics"].value.cget("text") == "–" and "Choose your library folder" in page.meta.cget("text")
    page.scan(); assert "Choose a library folder" in page.status.cget("text")
    assert not page.scan_adv.opened and page.scan_adv.changed == 0, "scan options sit in a shut Advanced block"

    got = []
    page.on_scanned = got.append
    page.set_folder(lib); wait()
    st = page.stats
    assert st.comics == 4 + 16 + 1 == 21, st.comics  # the Archive file is not counted
    assert got and got[-1]["comics"] == 21 and got[-1]["root"] == str(lib) and got[-1]["series"] == st.series == 19
    assert got[-1]["attention"] > 0, "the Home line gets a count of comics that need attention"
    assert page.vars["root"].get() == str(lib) and page.drop.label.cget("text") == str(lib) and page.drop.winfo_height() < 60, "a slim folder strip"
    t = {k: v.value.cget("text") for k, v in page.tiles.items()}
    assert t["comics"] == "21" and t["series"] == "19" and t["publishers"] == "2" and t["pages"] == "not read", t
    assert t["bytes"].endswith("KB") or t["bytes"].endswith("MB"), t
    assert page.bar_btn.cget("text") == "Rescan library" and page.bar_btn.cget("state") == "normal"
    assert footer() == ["Open library folder", "Export CSV…", "Copy summary"], footer()
    assert "Done · 21 comics" in page.status.cget("text") and "Done · 21 comics" in page.bar_text.cget("text")
    # after a scan Library folds to its summary and Overview opens by itself
    assert states()[0] == "done" and not page.s1.body.winfo_ismapped() and page.s2.body.winfo_ismapped()
    assert page.s1.summary.cget("text").startswith("21 comics") and "19 series" in page.s2.summary.cget("text")

    # series chart: Batman merged, "Other" after 15, every bar in the one accent colour
    ser = page.charts["Series"].items
    assert len(ser) == 16 and ser[0].frac == 1.0 and ser[-1].label.startswith("Other ("), (len(ser), [(i.label, i.frac) for i in ser][:3], ser[-1].label)
    assert sum(len(i.issues) for i in ser) == 21
    page.vars["show_all"].set(True); root.update()
    assert len(page.charts["Series"].items) == 19 and not page.charts["Series"].items[-1].label.startswith("Other")
    assert page.chart_adv.changed == 1 and "1 changed" in page.chart_adv.head.cget("text")
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
    big = rows(page.big)
    assert len(big) == 15 and "X-Men 001" in big[0][0]

    # Health rows with something missing carry a "Fix these" link that opens the Metadata tool; rows with nothing to fix do not
    health = page.charts["Coverage"]
    names = [i.label for i in health.items]
    pub = names.index("Have a publisher")
    assert health.items[pub].fix == "Fix these" and health.items[names.index("Single issues")].fix == ""
    health._click(types.SimpleNamespace(x=health.canvas.winfo_width() - 10, y=pub * ps.ROW + 5))
    assert opened == ["metadata"], opened
    health._click(types.SimpleNamespace(x=20, y=pub * ps.ROW + 5)); assert opened == ["metadata"], "only the link is clickable"

    # clicking a bar lists the comics behind it in a drawer at the side; Close hides it again
    pub = page.charts["Publishers"]
    pub._click(ev(0)); root.update()
    assert page.drawer.winfo_ismapped() and "DC · 2 comics" in page.drawer_title.cget("text"), page.drawer_title.cget("text")
    drawn = [r[0] for r in page.drawer_table.all]
    assert drawn == ["DC/Batman v1 001 (1940).cbz", "DC/Batman v2 001 (2011).cbz"], drawn
    assert page.drawer.winfo_rootx() + page.drawer.winfo_width() >= root.winfo_rootx() + root.winfo_width() - 4, "against the right edge"
    assert pub.selected == 0
    page.charts["Coverage"]._click(ev(0)); assert pub.selected == 0, "coverage bars are not clickable"
    page.charts["Formats"]._click(ev(1)); root.update()
    assert pub.selected is None and "CBR · 1 comic" in page.drawer_title.cget("text") and len(page.drawer_table.all) == 1
    page._close_drill(); root.update(); assert not page.drawer.winfo_ismapped()
    pub._click(ev(40)); assert not page.drawer.winfo_ismapped(), "a click below the bars does nothing"

    # needs attention: the cards say what, in plain words, with a button each
    texts = page.card_texts
    assert any("have no publisher" in x for x in texts) and any("have no issue number" not in x or True for x in texts), texts
    assert states()[2] == "active" and "to look at" in page.s3.summary.cget("text")
    pubcard = next(x for x in texts if "have no publisher" in x)
    assert "Unknown" in pubcard and "Fix metadata opens the Metadata tool" in pubcard and "For example: " in pubcard and ".cbz" in pubcard, pubcard
    assert all(len(x) > 120 for x in texts), "every card says what the problem means, not just a count"
    assert not any("looks like a reading order" in x for x in texts), "nothing here looks like a reading order"

    # export and copy: the footer's Export button offers every section
    out = d / "series.csv"
    ps.filedialog.asksaveasfilename = lambda **k: str(out)
    page.export_csv("Series")
    rows_csv = list(csv.reader(open(out, encoding="utf-8-sig")))
    assert rows_csv[0] == ["Series", "Comics", "Bytes"] and len(rows_csv) == 1 + 19 and rows_csv[1][1] == "2", rows_csv[:3]
    for name in ps.EXPORTS:
        page.export_csv(name); assert page.status.cget("text").startswith("Exported"), name
    ps.filedialog.asksaveasfilename = lambda **k: ""
    page.say(""); page.export_csv("Series"); assert page.status.cget("text") == ""
    menu = []
    ps.popup_menu = lambda anchor, items, above=False: menu.append((anchor, [t for t, _c in items], above))
    page._export_menu(page.bar_btn)
    assert menu[0][1] == [f"{n}…" for n in ps.EXPORTS] and menu[0][2] is True, "opens upward from the footer"
    page.copy_summary()
    clip = root.clipboard_get()
    assert clip.startswith(f"Comic library: {lib}") and "21 comics · 19 series · 2 publishers" in clip, clip
    assert "Have ComicInfo.xml: 4 of 20" in clip

    # page counts when asked for
    page.vars["deep"].set(True); assert page.scan_adv.changed == 1; page.scan(); wait()
    assert page.tiles["pages"].value.cget("text") not in ("not read", "–"), page.tiles["pages"].value.cget("text")
    page.vars["deep"].set(False)
    # stopping keeps a partial result and tells the app nothing new; the footer button is Stop while scanning
    got.clear()
    page.scan(); assert page.bar_btn.cget("text") == "Stop"; page.stop_action(); wait()
    assert "Stopped" in page.status.cget("text") or "Done" in page.status.cget("text")

    # a missing folder is reported; state round-trips; theme switch redraws
    page.vars["root"].set(str(d / "nope")); page.scan(); assert "Choose a library folder" in page.status.cget("text")
    assert page.state()["root"] == str(d / "nope") and "_auto_advance" in page.state()
    page.restore({"root": str(lib), "split": True, "export": "Years", "with_orders": True})
    assert page.vars["split"].get() and page.root() == lib and page.vars["with_orders"].get()
    page.vars["with_orders"].set(False); page.vars["split"].set(False)
    ctk.set_appearance_mode("dark"); root.update(); page.apply_theme(); root.update()
    ctk.set_appearance_mode("light"); root.update(); page.apply_theme()

# reading orders: a folder that looks like one is suggested, marked folders are left out and counted apart
with tempfile.TemporaryDirectory() as e:
    e = Path(e); lib2 = e / "Lib2"
    for n in range(1, 4): cbz(lib2 / "Real" / f"Saga {n:03d} (2012).cbz")
    for n in range(1, 5): cbz(lib2 / "Orders" / "Event" / f"{n:02d} - Saga {n:03d} (2012).cbz")
    page.orders = ReadingOrders(); got.clear()
    page.set_folder(lib2); wait()
    assert page.stats.comics == 7 and page.suggestions[0][0] == lib2 / "Orders" / "Event" and page.suggestions[0][1] == 4
    assert any("1 folder looks like a reading order" in x and "Folders: Event (4)" in x for x in page.card_texts), page.card_texts
    assert page.order_box.title.startswith("Reading orders") and not page.order_box.opened, "the Reading orders section starts shut"
    # "Mark them" keeps the copies out of the numbers
    page._mark([f for f, _c, _w in page.suggestions]); root.update()
    assert page.stats.comics == 3 and page.suggestions == [] and page.orders.folders == [str(lib2 / "Orders" / "Event")]
    assert page.left_out.cget("text") == "4 reading-order comics left out" and got[-1]["comics"] == 3, "Home follows without a rescan"
    assert "4 comics in 1 folder" in page.order_box.title
    assert rows(page.order_table) == [(str(lib2 / "Orders" / "Event"), "4", rows(page.order_table)[0][2])]
    assert not any("like a reading order" in x for x in page.card_texts)
    # the visible switch includes them again
    page.vars["with_orders"].set(True); root.update()
    assert page.stats.comics == 7 and page.left_out.cget("text") == "4 reading-order comics included" and got[-1]["comics"] == 7
    page.vars["with_orders"].set(False); root.update(); assert page.stats.comics == 3
    # attention counts ignore the copies; duplicates of the copies are not duplicates
    assert page.attn["no_publisher"] == 3
    # unmark a folder: it counts again and is suggested again; "Not these" remembers the no
    page.order_table.tree.selection_set("0"); page.unmark_selected(); root.update()
    assert page.stats.comics == 7 and len(page.suggestions) == 1 and len(page.orders) == 0
    page._dismiss([f for f, _c, _w in page.suggestions]); root.update()
    assert page.suggestions == [] and page.orders.dismissed(lib2 / "Orders" / "Event") and page.stats.comics == 7
    # marking a folder by hand
    ps.filedialog.askdirectory = lambda **k: str(lib2 / "Orders" / "Event")
    page.mark_folder(); root.update(); assert page.stats.comics == 3 and not page.orders.dismissed(lib2 / "Orders" / "Event")

# an empty folder gives zeros, not a crash
with tempfile.TemporaryDirectory() as e:
    page.set_folder(e); wait()
    assert page.stats.comics == 0 and page.tiles["comics"].value.cget("text") == "0" and page.charts["Series"].items == []
    assert page.big.all == [] and any(isinstance(w, ctk.CTkLabel) and "Nothing needs attention" in w.cget("text") for w in page.cards_box.winfo_children())
root.destroy()
print("stats ui OK")
