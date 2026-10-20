"""The card list (cardlist.py) on its own, and the block-moving maths behind it (blocks.py): selecting with click, Ctrl and
Shift, dragging one card or a whole selection, the stacked card and the drop line, scrolling near the edges, the selection
box, the keys, undo, and every no-op."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

import blocks as b
from cardlist import CardList

# ---- the maths
order = list("abcdefgh")
assert b.insert_block(order, "bc", 5) == list("adebcfgh"), "a gap after e"
assert b.insert_block(order, "bc", 0) == list("bcadefgh") and b.insert_block(order, "bc", 8) == list("adefghbc")
assert b.insert_block(order, "bc", 1) == order and b.insert_block(order, "bc", 2) == order and b.insert_block(order, "bc", 3) == order, "next to or inside the block: unchanged"
assert b.insert_block(order, "ce", 8) == list("abdfghce"), "a block of two apart keeps its order and comes together"
assert b.insert_block(order, "", 3) == order and b.insert_block(order, "a", 99) == list("bcdefgha")
assert not hasattr(b, "place_block"), "Move to position is gone"
assert b.move_block(order, "bc", 1) == list("adbcefgh") and b.send_to_edge(order, "gh", True) == list("ghabcdef")
import reading_order as ro
assert ro.move_block is b.move_block and ro.drop_block is b.drop_block, "reading_order keeps using the same functions"

# ---- the widget
root = ctk.CTk(); root.geometry("620x520")
data = {f"c{i:02d}": {"num": str(i + 1), "title": f"Comic {i + 1:02d}.cbz", "sub": "→ 01 - Comic.cbz", "status": "Add", "tone": "",
                      "checked": True} for i in range(40)}
data["c01"]["tone"] = "dim"; data["c02"]["tone"] = "bad"; data["c03"]["checked"] = None
ticks, stacks, moved = [], [], []
cl = CardList(root, lambda i: data[i], on_reorder=lambda: moved.append(list(cl.order)), on_tick=ticks.append, noun="issue",
              empty="Nothing here yet.", on_stack=stacks.append)
cl.pack(fill="both", expand=True)
root.update()
cv = cl.canvas


def texts(tag=None):
    items = cv.find_withtag(tag) if tag else cv.find_all()
    return [cv.itemcget(i, "text") for i in items if cv.type(i) == "text"]


class E: pass


def ev(iid, dx=200, dy=0, state=0):
    x0, y0, x1, y1 = cl.card_box(iid); e = E(); e.x, e.y, e.state = x0 + dx, (y0 + y1) // 2 + dy, state; return e


def at(x, y, state=0):
    e = E(); e.x, e.y, e.state = x, y, state; return e


def tick_at(iid):
    x0, y0, x1, y1 = cl.card_box(iid); e = E(); e.x, e.y, e.state = x0 + cl.u(26), (y0 + y1) // 2, 0; return e


def drag(src, target, low=False, state=0, steps=2):
    """Press a card, move to a card (its top or bottom half) and release: a drag."""
    cl._press(ev(src, state=state))
    cl._motion(ev(src, dx=210, dy=cl.u(8)))
    t = ev(target, dy=cl.u(18) if low else -cl.u(18))
    cl._motion(t); root.update()
    cl._release(t)


# empty
assert texts() == ["Nothing here yet."] and cl.order == [], texts()

# a long list: only the cards in view are drawn
ids = list(data)
cl.set_order(ids); root.update()
assert "Comic 01.cbz" in texts() and "Comic 40.cbz" not in texts(), "only the visible cards are drawn"
assert cl.sb.get()[0] == 0 and cl.sb.get()[1] < 1
import cardlist as cardmod
assert cl.card_box("c00")[3] - cl.card_box("c00")[1] == cl.u(cardmod.CARD_H) and cl.card_box("c01")[1] - cl.card_box("c00")[1] == cl.u(cardmod.CARD_H + cardmod.GAP)

# click, Ctrl+click, Shift+click
cl._press(ev("c02")); cl._release(ev("c02")); assert cl.sel == {"c02"} and cl.anchor == "c02"
cl._press(ev("c05", state=4)); cl._release(ev("c05")); assert cl.sel == {"c02", "c05"}, "Ctrl adds one"
cl._press(ev("c02", state=4)); cl._release(ev("c02")); assert cl.sel == {"c05"}, "Ctrl on a selected card removes it"
cl._press(ev("c05")); cl._release(ev("c05")); cl._press(ev("c08", state=1)); cl._release(ev("c08"))
assert cl.sel == {"c05", "c06", "c07", "c08"} and cl.anchor == "c05", "Shift selects a range from the anchor"
cl._press(ev("c03", state=1)); cl._release(ev("c03")); assert cl.sel == {"c03", "c04", "c05"}, "and a range upwards"
cl._press(ev("c10", state=5)); cl._release(ev("c10")); assert cl.sel == {"c03", "c04", "c05", "c06", "c07", "c08", "c09", "c10"}, "Ctrl+Shift adds the range"
cl.select(["c01"]); assert cl.selected() == ["c01"]
# a click on one of several selected cards selects just it, once the button is up
cl.select(["c04", "c05", "c06"])
cl._press(ev("c05")); assert cl.sel == {"c04", "c05", "c06"}, "pressing keeps the selection, so it can be dragged"
cl._release(ev("c05")); assert cl.sel == {"c05"}
cl.select(["c04", "c05", "c06"]); cl._press(ev("c05", state=4)); cl._release(ev("c05")); assert cl.sel == {"c04", "c06"}

# dragging one card: it is picked up wherever you hold it, and it lands where the line was
cl.select([]); before = len(moved); cl.offset = 0
cl._press(ev("c02", dx=120)); assert cl.sel == {"c02"}
cl._motion(ev("c02", dx=122, dy=1)); assert cl._d["moved"] is False and not cv.find_withtag("overlay"), "a small movement is still a click"
cl._motion(ev("c02", dx=150, dy=cl.u(20)))
cl._motion(ev("c06", dy=cl.u(18))); root.update()
assert cl._d["boundary"] == 7 and cv.find_withtag("overlay") and "Comic 03.cbz" in texts("overlay") and not any("issues" in t for t in texts("overlay"))
cl._release(ev("c06", dy=cl.u(18))); root.update()
assert cl.order[:8] == ["c00", "c01", "c03", "c04", "c05", "c06", "c02", "c07"] and len(moved) == before + 1 and moved[-1] == cl.order
assert not cv.find_withtag("overlay") and str(cv.cget("cursor")) in ("", "{}")
assert "c02" in cl.flash and cl.can_undo and stacks[-1] is True
t0 = time.time()
while time.time() - t0 < 0.9: root.update()
assert cl.flash == {}, "the highlight fades"

# several cards: one stacked card with a count, and they land together in their old order
cl.select(["c04", "c05", "c06"]); order0 = list(cl.order); cl.offset = 0
cl._press(ev("c05")); cl._motion(ev("c05", dy=cl.u(10))); cl._motion(ev("c11", dy=cl.u(18))); root.update()
assert "3 issues" in texts("overlay") and "Comic 05.cbz" in texts("overlay") and cl._d["boundary"] == 12
cl._release(ev("c11", dy=cl.u(18)))
assert cl.order == [i for i in order0 if i not in ("c04", "c05", "c06")][:9] + ["c04", "c05", "c06"] + [i for i in order0 if i not in ("c04", "c05", "c06")][9:]
assert cl.sel == {"c04", "c05", "c06"}, "the selection survives"
# undo puts them back, one move at a time
assert cl.undo() and cl.order == order0 and moved[-1] == order0

# dropping next to or inside the block changes nothing
cl.select(["c04", "c05", "c06"]); n = len(moved); depth = len(cl.stack); cur = list(cl.order)
cl._press(ev("c05")); cl._motion(ev("c05", dy=cl.u(10))); cl._motion(ev("c05", dy=cl.u(-3))); cl._release(ev("c05"))
assert cl.order == cur and len(moved) == n and len(cl.stack) == depth
# Escape takes the drag back
cl._press(ev("c05")); cl._motion(ev("c05", dy=cl.u(10))); cl._motion(ev("c12")); assert cv.find_withtag("overlay")
assert cl._escape(None) == "break" and cl._d is None and not cv.find_withtag("overlay")
cl._release(ev("c12")); assert cl.order == cur

# scrolling by itself near the bottom edge
cl.offset = 0; cl.select(["c00"]); root.update()
cl._press(ev("c00")); cl._motion(ev("c00", dy=cl.u(10))); h = cl._view_h()
cl._motion(at(200, h - 6)); root.update()
t0 = time.time()
while cl.offset == 0 and time.time() - t0 < 3: root.update()
assert cl.offset > 0, "it scrolled by itself"
first = cl.offset
t0 = time.time()
while time.time() - t0 < 0.4: root.update()
assert cl.offset > first and cl._d["boundary"] > 8, "and keeps going while the pointer stays at the edge"
cl._release(at(200, h - 6)); assert cl._auto is None
stopped = cl.offset; t0 = time.time()
while time.time() - t0 < 0.3: root.update()
assert cl.offset == stopped, "it stops when released"
cl.undo(); cl.offset = 0

# the wheel and the scrollbar
cl._wheel(60); assert cl.offset == cl.u(60); cl._wheel(-600); assert cl.offset == 0
cl._yview("moveto", 0.5); assert cl.offset == int(0.5 * cl._content()) or cl.offset == cl._content() - cl._view_h()
cl._yview("scroll", -1, "pages"); assert cl.offset >= 0
cl._yview("moveto", 5); assert cl.offset == cl._content() - cl._view_h(), "clamped to the end"
cl.see("c00"); assert cl.card_box("c00")[1] >= 0
cl.offset = 0

# a box: from the empty space beside a card in a short list, and Ctrl keeps what was selected
short = ["c10", "c11", "c12", "c13"]
cl.set_order(short); root.update()
x0, y0, x1, y1 = cl.card_box("c13"); under = y1 + cl.u(40)
cl.select(["c10"])
cl._press(at(80, under)); assert cl.sel == set() and cl._d["kind"] == "box"
cl._motion(at(82, under + 1)); assert cl._d["moved"] is False
cl._motion(at(100, cl.card_box("c11")[1] + cl.u(10))); root.update()
assert cl.sel == {"c11", "c12", "c13"} and cv.find_withtag("overlay"), cl.sel
cl._release(at(100, cl.card_box("c11")[1] + cl.u(10))); assert not cv.find_withtag("overlay") and cl.sel == {"c11", "c12", "c13"}
cl.select(["c10"]); cl._press(at(80, under, 4)); cl._motion(at(100, cl.card_box("c13")[1] + cl.u(10))); assert cl.sel == {"c10", "c13"}
cl._release(at(100, under))
# the gap between two cards starts a box as well
cl.select(["c10"]); gap_y = cl.card_box("c11")[1] - cl.u(3)
cl._press(at(80, gap_y)); assert cl._d["kind"] == "box"; cl._release(at(80, gap_y))

# keys
for seq in ("<Alt-Up>", "<Alt-Down>", "<Control-z>", "<Control-a>", "<Up>", "<Down>", "<Shift-Up>", "<Shift-Down>", "<space>", "<Escape>"):
    assert cv.bind(seq), seq
cl.set_order(short); cl.select(["c11"])
cl._arrow(1, False); assert cl.sel == {"c12"} and cl.cursor == "c12"
cl._arrow(1, True); assert cl.sel == {"c12", "c13"}, "Shift extends from the anchor"
cl._arrow(-1, True); assert cl.sel == {"c12"}
cl._arrow(10 ** 9, False); assert cl.sel == {"c13"}; cl._arrow(-10 ** 9, False); assert cl.sel == {"c10"}
cl.select_all(); assert cl.sel == set(short)
cl.select(["c12"]); assert cl.move_selected(-1) and cl.order == ["c10", "c12", "c11", "c13"]
assert cl.to_edge(True) and cl.order[0] == "c12" and cl.to_edge(False) and cl.order[-1] == "c12"
assert cl.move_selected(1) is False or cl.order[-1] == "c12"
cl.select([]); assert not cl.move_selected(1) and not cl.to_edge(True)
cl.select(["c13"]); cl.cursor = "c13"; ticks.clear(); cl._space(); assert ticks == ["c13"]
cl.cursor = "c03"; ticks.clear(); cl._space(); assert ticks == [], "a card without a tick box ignores Space"
assert cl._key(lambda: None) == "break"
# a press on a tick box goes to the page and changes no selection
cl.set_order(short); cl.select(["c12"]); ticks.clear()
assert cl._press(tick_at("c11")) == "break" and ticks == ["c11"] and cl.sel == {"c12"} and cl._d is None
data["c03"]["checked"] = None; cl.set_order(["c03", "c10"]); cl.select([])
cl._press(tick_at("c03")); cl._release(tick_at("c03")); assert cl.sel == {"c03"} and ticks == ["c11"], "no tick box: a plain click"

# undo: one move at a time, and forgotten when cards come or go
cl.set_order(ids); cl.select(["c05"]); cl.offset = 0
for _ in range(3): cl.move_selected(1)
assert len(cl.stack) == 3
for _ in range(3): assert cl.undo()
assert not cl.undo() and not cl.can_undo and cl.order == ids
cl.move_selected(1); assert cl.can_undo
cl.append(["late"]) if False else None
data["late"] = dict(data["c00"]); cl.append(["late"]); assert not cl.can_undo and stacks[-1] is False and cl.order[-1] == "late"
cl.move_selected(1); cl.remove(["late"]); assert not cl.can_undo and "late" not in cl.order and len(cl.order) == len(ids)
cl.select(["c05"]); cl.move_selected(1); cl.stack.append(["x", "y"]); assert cl.undo() is False and not cl.stack, "a history that no longer fits is dropped"
cl.set_order(ids); cl.remove(["c05"]); assert "c05" not in cl.order and cl.sel == set() and cl.cursor != "c05"

# busy: nothing starts, nothing moves
cl.set_order(ids); cl.select(["c03"]); cl.busy = lambda: True
assert cl._press(ev("c03")) == "break" and cl._d is None
assert not cl.move_selected(1) and not cl.to_edge(True) and not cl.undo()
cl.busy = lambda: False

# pictures and buttons on a card (the ACEO cover list): drawn, hit-tested, and a button press is not a click on the card
from PIL import Image
pics = [Image.new("RGB", (60, 90), (200, 40, 40)), Image.new("RGB", (60, 90), (40, 40, 200))]
pressed = []
cl.cards = None
pl = CardList(root, lambda i: {"num": "1", "title": "Cover", "sub": "Sheet 1 · card 1", "images": pics, "image_on": 1,
                               "buttons": [("back", "Front"), ("less", "−"), (None, "×2"), ("more", "+")]},
              on_button=lambda i, k: pressed.append((i, k)), card_h=76, noun="cover")
cl.pack_forget(); pl.pack(fill="both", expand=True); pl.set_order(["a", "b"]); root.update()
assert pl.card_box("a")[3] - pl.card_box("a")[1] == pl.u(76)
boxes = {k: bb for k, _t, bb in pl._button_boxes(pl.render("a"), pl.card_box("a")) if k}
assert set(boxes) == {"back", "less", "more"} and boxes["back"][0] < boxes["less"][0] < boxes["more"][0], "left to right, as given"
pic_boxes = pl._picture_boxes(pl.render("a"), pl.card_box("a")[0] + 100, (pl.card_box("a")[1] + pl.card_box("a")[3]) / 2)
assert len(pic_boxes) == 2 and pic_boxes[0][1][2] < pic_boxes[1][1][0], "two pictures side by side"
assert any(pl.canvas.type(i) == "image" for i in pl.canvas.find_all()), "the pictures are drawn"
def over(key):
    x0, y0, x1, y1 = boxes[key]; e = E(); e.x, e.y, e.state = int((x0 + x1) / 2), int((y0 + y1) / 2), 0; return e
assert pl._press(over("more")) == "break" and pressed == [("a", "more")] and pl.sel == set() and pl._d is None, "a button is not a click on the card"
pl._press(over("back")); pl._press(over("less")); assert pressed[-2:] == [("a", "back"), ("a", "less")]
e = ev_card = E(); x0, y0, x1, y1 = pl.card_box("b"); e.x, e.y, e.state = int(x0 + 160), int((y0 + y1) / 2), 0
pl._press(e); pl._release(e); assert pl.sel == {"b"} and len(pressed) == 3, "the rest of the card selects it"
pl.pack_forget(); cl.pack(fill="both", expand=True); root.update()

# the look: every tone and the dark theme draw without trouble
ctk.set_appearance_mode("dark"); cl.apply_theme(); root.update(); assert cv.find_all()
ctk.set_appearance_mode("light"); cl.apply_theme(); root.update()
cl.clear(); root.update(); assert cl.order == [] and texts() == ["Nothing here yet."]
root.destroy()
print("cardlist OK")
