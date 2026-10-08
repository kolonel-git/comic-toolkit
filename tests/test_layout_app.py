"""The app shell: the sidebar can be resized within limits."""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def ev(x): return types.SimpleNamespace(x_root=x)


# the app: the sidebar can be resized and its width is kept
import comic_tool as ct
app = ct.App(); app.update()
w = app.splitter.target.winfo_width()
app.splitter._press(ev(100)); app.splitter._drag(ev(160)); app.splitter._release(None); app.update()
k = app.splitter._scale()
assert abs(app.sidebar_width - (190 + 60 / k)) <= 2 and abs(app.splitter.target.winfo_width() - app.sidebar_width * k) <= 3, app.sidebar_width
app.splitter._press(ev(0)); app.splitter._drag(ev(-900)); app.splitter._release(None); assert app.sidebar_width == 150
app.splitter._press(ev(0)); app.splitter._drag(ev(900)); app.splitter._release(None); assert app.sidebar_width == 360

# Home: every tool on one screen with no scrolling, cards the same width in every row, bigger gaps between groups
def cards(w, out):
    for c in w.winfo_children():
        (out.append(c) if isinstance(c, ct.Card) else cards(c, out))
    return out
for width in (190, 360):
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
app.destroy()
print("layout app OK")
