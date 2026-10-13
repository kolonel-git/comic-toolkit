"""The app shell: the sidebar can be resized within limits."""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def ev(x): return types.SimpleNamespace(x_root=x)


# the app: the sidebar can be resized and its width is kept
import comic_tool as ct
app = ct.App(); app.update()
w = app.splitter.target.winfo_width() / app.splitter._scale()  # may start from a width saved in settings.json
app.splitter._press(ev(100)); app.splitter._drag(ev(160)); app.splitter._release(None); app.update()
k = app.splitter._scale()
assert abs(app.sidebar_width - (w + 60 / k)) <= 2 and abs(app.splitter.target.winfo_width() - app.sidebar_width * k) <= 3, app.sidebar_width
app.splitter._press(ev(0)); app.splitter._drag(ev(-900)); app.splitter._release(None); assert app.sidebar_width == 150
app.splitter._press(ev(0)); app.splitter._drag(ev(900)); app.splitter._release(None); assert app.sidebar_width == 360

# Home: every tool on one screen with no scrolling, cards the same width in every row, bigger gaps between groups
def cards(w, out):
    for c in w.winfo_children():
        (out.append(c) if isinstance(c, ct.Card) else cards(c, out))
    return out
def check_home(width):
    app.splitter.set_width(width); app.show("home"); app.update(); app.update()
    home = app.pages["home"]
    cs = cards(home, [])
    assert len(cs) == len(ct.TOOLS) == 10, len(cs)
    ws = {c.winfo_width() for c in cs}
    assert max(ws) - min(ws) <= 2, ("cards differ in width", ws)
    assert all(c.winfo_height() > 60 for c in cs)
    bottom = max(c.winfo_rooty() + c.winfo_height() for c in cs)
    assert bottom <= home.winfo_rooty() + home.winfo_height() - 20, ("cards must fit without scrolling", bottom, home.winfo_height())
    assert all(c.winfo_rootx() >= home.winfo_rootx() and c.winfo_rootx() + c.winfo_width() <= home.winfo_rootx() + home.winfo_width() for c in cs), "inside the page"
    byrow = {}
    for c in cs: byrow.setdefault(c.winfo_rooty(), []).append(c)
    gaps = []
    for row in byrow.values():
        row.sort(key=lambda c: c.winfo_rootx())
        gaps += [b.winfo_rootx() - (a.winfo_rootx() + a.winfo_width()) for a, b in zip(row, row[1:])]
    assert max(gaps) > min(gaps) + 10, ("groups need a wider gap than cards inside a group", sorted(gaps))
    first = next(c for c in cs if c.desc.cget("text").startswith("Preview"))
    first._command()  # a card opens its tool
    assert app.current == "single"
    app.show("home")


def header_order():
    """The group headings as laid out on Home, left to right, top to bottom."""
    labels = []
    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, ct.ctk.CTkLabel) and c.cget("text") in {h.upper() for h, _ in ct.GROUPS}:
                labels.append(c)
            walk(c)
    walk(app.pages["home"])
    labels.sort(key=lambda c: (c.winfo_rooty() // 20, c.winfo_rootx()))
    return [c.cget("text") for c in labels]


for width in (190, 360):
    check_home(width)

# the sidebar scrolls, the dark-mode switch and Reorder button stay pinned under it
assert isinstance(app.nav_scroll, ct.ctk.CTkScrollableFrame)
app.show("home"); app.update()
by_text = {h: b for h, b in app.group_heads.items()}
assert all(b.winfo_ismapped() for b in by_text.values())
canvas = app.nav_scroll._parent_canvas
app.geometry("1200x720"); app.update()
y0 = by_text["ACEO Cards"].winfo_rooty()
canvas.yview_moveto(1.0); app.update()
assert canvas.yview()[0] >= 0 and by_text["ACEO Cards"].winfo_rooty() <= y0, "scrolling moves the list"

# headings fold and unfold, and the state is remembered
assert "metadata" in app.nav
by_text["Metadata"].invoke(); app.update()
assert "metadata" not in app.nav and "Metadata" in app.collapsed and "aceo" in app.nav
assert app.group_heads["Metadata"].cget("text").startswith("▸")
app.group_heads["Metadata"].invoke(); app.update()
assert "metadata" in app.nav and not app.collapsed and app.group_heads["Metadata"].cget("text").startswith("▾")
app.show("metadata"); app.group_heads["Comic Renamer"].invoke(); app.update()   # folding another group keeps the highlight
assert app.nav["metadata"].cget("fg_color") == ct.BORDER
app.group_heads["Comic Renamer"].invoke()

# reordering moves a group in the sidebar and on Home, and Home still fits
default = [h for h, _ in ct.GROUPS]
assert [h.upper() for h in default][:2] == header_order()[:2]
app.move_group("ACEO Cards", -2); app.update()
order = [h for h, _ in ct.ordered_groups(app.group_order)]
assert order.index("ACEO Cards") == default.index("ACEO Cards") - 2
ys = [app.group_heads[h].winfo_rooty() for h in order]
assert ys == sorted(ys), "sidebar follows the order"
assert header_order().index("ACEO CARDS") < header_order().index("READING ORDERS")
for width in (190, 360):
    check_home(width)
app.move_group("Comic Cover Extractor", 99)              # past the end does nothing
app.set_group_order(list(reversed(default))); app.update()
for width in (190, 360):
    check_home(width)
rows = ct.home_rows(ct.ordered_groups(app.group_order))
assert all(sum(len(k) for _, k in r) <= ct.HOME_COLS and len(r) <= ct.HOME_GAPS + 1 for r in rows)
assert sorted(h for r in rows for h, _ in r) == sorted(default)
# the dialog's buttons, and Reset
app.reorder_dialog(); app.update()
ui = app._reorder_ui
ui["box"].selection_set(0); ui["shift"](1); app.update()
assert ui["box"].curselection() == (1,)
ui["reset"](); app.update(); assert app.group_order == [] and [h for h, _ in ct.ordered_groups(app.group_order)] == default
app._reorder_win.destroy()
# unknown and missing headings in a saved order are tolerated
assert [h for h, _ in ct.ordered_groups(["Nope", "ACEO Cards"])][0] == "ACEO Cards" and len(ct.ordered_groups(["Nope"])) == len(ct.GROUPS)
assert ct.home_rows([]) == []
check_home(190)
app.destroy()
print("layout app OK")
