import sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reading_order as ro
o = list("abcdefgh")
assert ro.send_to_edge(o, ["d"], True) == list("dabcefgh") and ro.send_to_edge(o, ["d"], False) == list("abcefghd")
assert ro.send_to_edge(o, ["f", "c"], True) == list("cfabdegh")          # block keeps its list order, not click order
assert ro.send_to_edge(o, ["c", "f"], False) == list("abdeghcf")
assert ro.send_to_edge(o, ["a", "b"], True) == o and ro.send_to_edge(o, ["g", "h"], False) == o
assert ro.send_to_edge(o, [], True) == o and ro.send_to_edge(o, list(o), False) == o
import customtkinter as ctk
import page_order as po
root = ctk.CTk(); root.geometry("1200x780"); page = po.OrderPage(root); page.pack(fill="both", expand=True); root.update()
with tempfile.TemporaryDirectory() as d:
    d = Path(d); fs = []
    for i in range(1, 9):
        p = d / f"Saga {i:02d}.cbz"; fs.append(p)
        with zipfile.ZipFile(p, "w") as z: z.writestr("0.jpg", b"x")
    page.add_paths(fs)
    t = time.time()
    while page.busy and time.time() - t < 10: root.update(); time.sleep(0.01)
    page.arc.set("Run"); root.update()
    names = lambda: [r.path.name[5:7] for r in page.rows]
    ids = [r.iid for r in page.rows]
    assert page.tools["top"].cget("state") == "normal" and page.tools["bottom"].cget("state") == "normal"
    page.tree.selection_set(ids[4]); page.to_edge(True); assert names() == list("51234678".replace("5", "5")) or True
    print(names()); assert names() == ["05", "01", "02", "03", "04", "06", "07", "08"]
    page.tree.selection_set([ids[1], ids[6]]); page.to_edge(False)
    print(names()); assert names() == ["05", "01", "03", "04", "06", "08", "02", "07"]
    page.tree.selection_set([ids[2], ids[3], ids[7]]); page.to_edge(True)
    print(names()); assert names() == ["03", "04", "08", "05", "01", "06", "02", "07"]
    assert page.tree.selection() == tuple(ids[i] for i in (2, 3, 7)) or set(page.tree.selection()) == {ids[2], ids[3], ids[7]}
    assert [page.tree.item(i, "values")[1] for i in page.tree.get_children()] == [str(i) for i in range(1, 9)]
    page.tree.selection_set(()); page.to_edge(True); assert names()[0] == "03"        # nothing selected: no-op
    page.clear(); assert page.tools["top"].cget("state") == "disabled" and page.tools["bottom"].cget("state") == "disabled"
root.destroy()
print("EDGE OK")
