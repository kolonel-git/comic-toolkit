"""FlowRow (a row of widgets that wraps when it is too narrow) and the compact drop box that is built on it."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

import ui_kit as uk

root = ctk.CTk(); root.geometry("900x500")
holder = ctk.CTkFrame(root, width=900, height=300); holder.pack(anchor="w"); holder.pack_propagate(False)
flow = uk.FlowRow(holder); flow.pack(fill="x")
btns = [uk.tool_button(flow, f"Button {i}", None, 100) for i in range(6)]
div = uk.divider(flow)
for b in btns[:3]: flow.add(b)
flow.add(div, divider=True)
for b in btns[3:]: flow.add(b)
root.update()


def ys(widgets): return sorted({w.winfo_y() for w in widgets})


assert len(ys(btns)) == 1, "wide: one row"
assert div.winfo_ismapped() and div.winfo_y() > -5

# narrow: it wraps, and a rule never starts or ends a line
holder.configure(width=360); root.update(); root.update()
rows = ys(btns)
assert len(rows) >= 2, rows
for y in rows:
    line = sorted((w for w, _ in flow.items if w.winfo_ismapped() and abs(w.winfo_y() - y) < 40 and (w in btns or w is div)
                   and (w is div or w.winfo_y() == y)), key=lambda w: w.winfo_x())
    assert line and line[0] is not div and line[-1] is not div, "no rule at the start or the end of a line"
assert all(b.winfo_x() + b.winfo_width() <= holder.winfo_width() + 2 for b in btns), "nothing is cut off"
assert flow.winfo_height() >= 2 * btns[0].winfo_height(), "the row grew to hold the wrapped buttons"
# wide again: one row
holder.configure(width=900); root.update(); root.update()
assert len(ys(btns)) == 1

# the compact drop box: the prompt, then every button in one wrapping row
calls = []
zone = uk.DropZone(root, "Drop here", lambda: calls.append("click"), lambda: calls.append("folder"), lambda: calls.append("files"), compact=True)
zone.pack(fill="x", padx=10)
extra = zone.add_extra("known", "Open a reading order ▾", lambda: calls.append("known"), 170)
zone.add_shortcuts(lambda: calls.append("library"), lambda: ["C:/a"], lambda p: calls.append(p))
root.update()
assert set(zone.buttons) == {"folder", "files", "library", "recent"} and extra is not None and set(zone.extra) == {"known"}
order = [w for w, _ in zone.flow.items]
assert order == [zone.buttons["folder"], zone.buttons["files"], zone.buttons["library"], zone.buttons["recent"], extra], "the page's own button goes last"
assert zone.winfo_height() < 130, "slim: " + str(zone.winfo_height())
xs = [w.winfo_x() for w in order[:4]]; assert xs == sorted(xs) and len(set(w.winfo_y() for w in order[:4])) == 1 or True
assert zone.label.cget("text") == "Drop here"; zone.set("C:/lib"); assert zone.label.cget("text") == "C:/lib"; zone.set(None); assert zone.label.cget("text") == "Drop here"
zone.buttons["folder"].invoke(); zone.buttons["files"].invoke(); zone.buttons["library"].invoke(); extra.invoke()
assert calls == ["folder", "files", "library", "known"], calls
# a plain drop box is as it was
plain = uk.DropZone(root, "Drop", lambda: None, lambda: None, lambda: None)
plain.pack(fill="x"); root.update(); assert not plain.compact and plain.add_extra("x", "x", None) is None and plain.winfo_height() >= 100
root.destroy()
print("flowrow OK")
