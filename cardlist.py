"""A list of cards you pick up and move: each item is one card, and the cards can be put in any order by dragging.

`CardList(parent, render, ...)` draws one card per item on a canvas (only the ones in view, so a long list stays quick). It is
for lists whose order matters: Reading order today, the ACEO cover list next.

- Press a card and drag it anywhere to move it. Select first with a click, Ctrl+click (add or remove one), Shift+click (a
  range) or by dragging a box over several from the space between or under the cards; then dragging any selected card moves
  all of them. The selected cards collapse into one stacked card with a count ("5 issues"), a thick line shows the gap they
  will land in, the list scrolls itself near its top and bottom edge, and on release the cards arrive together in their old
  order and flash for a moment. Escape cancels.
- Never drag-only: Alt+Up / Alt+Down move the selection, Up / Down / Shift+Up / Shift+Down and Ctrl+A select, Space ticks the
  card, Ctrl+Z undoes a move (`move_selected`, `to_edge` and `undo` are methods for the page's buttons).

`render(id)` returns what to draw: {"num", "title", "sub", "status", "tone" ("", "dim" or "bad"), "checked" (None for no tick
box)}, and optionally "images" (a list of small PIL pictures drawn at the left of the card; "image_on" is the index of the one
that is in use and gets a thick outline) and "buttons" (a list of (key, text) drawn at the right of the card; a key of None is
a plain label, any other makes a small button that calls `on_button(id, key)`). The page owns what the ids mean; this list owns their order, the selection and the undo history, and calls
`on_reorder()` after the order changed by a move or an undo.
"""
from __future__ import annotations

import math
import tkinter as tk
import tkinter.font as tkfont
import time

import customtkinter as ctk
from PIL import ImageTk

import blocks
from ui_kit import (ACCENT, BG, BORDER, DANGER, EDGE, FOCUS, FONT, HOVER, INK, MUTED, ON_ACCENT, PINK, RAISED, SCROLL,
                    SELECT_BG, TEXT, pick)

CARD_H, GAP, PAD = 54, 6, 8      # in pixels at 96 dpi; scaled with the screen
DRAG_PX = 5                      # movement before a press counts as a drag
EDGE_PX = 26                     # how close to the top or bottom edge the list starts scrolling
STEP_PX = 20                     # how far it scrolls each tick
TICK_MS = 50
FLASH_MS = 700                   # how long the cards that just moved stay highlighted
KEEP = 50                        # moves that can be undone
WHEEL_PX = 60


class CardList(ctk.CTkFrame):
    def __init__(self, parent, render, on_reorder=None, on_tick=None, noun="item", empty="", busy=None, on_stack=None,
                 card_h=CARD_H, on_button=None):
        """`on_tick(id)` is called for a press on a card's tick box; `busy()` returns True while nothing may be moved;
        `on_stack(can_undo)` is told when undo becomes available or not; `noun` is the word after the count."""
        super().__init__(parent, fg_color=BG, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.render = render
        self.on_reorder = on_reorder
        self.on_tick = on_tick
        self.on_button = on_button
        self.card_h = card_h        # the height of a card in pixels at 96 dpi (a list with pictures wants taller cards)
        self._photos = {}
        self.noun = noun
        self.empty = empty
        self.busy = busy or (lambda: False)
        self.on_stack = on_stack
        self.order = []
        self.sel = set()
        self.anchor = None          # where a Shift range starts
        self.cursor = None          # the card the keys work from
        self.stack = []
        self.flash = {}             # id -> time it stops being highlighted
        self.offset = 0             # how far the list is scrolled, in pixels
        self._d = None              # the gesture in progress
        self._redraw_id = None
        self._auto = None
        self.k = 1.0
        self.canvas = tk.Canvas(self, bg=pick(BG), highlightthickness=0, bd=0, takefocus=1, height=120)
        self.sb = ctk.CTkScrollbar(self, command=self._yview, button_color=SCROLL, corner_radius=0)
        self.sb.pack(side="right", fill="y", padx=(0, 2), pady=4)
        self.canvas.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.k = max(1.0, self.winfo_fpixels("1i") / 96)
        self.f_title = tkfont.Font(root=self, family=FONT, size=11, weight="bold")
        self.f_sub = tkfont.Font(root=self, family=FONT, size=10)
        self.f_num = tkfont.Font(root=self, family=FONT, size=11, weight="bold")
        c = self.canvas
        c.bind("<Configure>", lambda _: self._configured())
        c.bind("<MouseWheel>", lambda e: self._wheel(-WHEEL_PX if e.delta > 0 else WHEEL_PX))
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._motion)
        c.bind("<ButtonRelease-1>", self._release)
        for seq, fn in (("<Alt-Up>", lambda: self.move_selected(-1)), ("<Alt-Down>", lambda: self.move_selected(1)),
                        ("<Control-z>", self.undo), ("<Control-a>", self.select_all), ("<space>", self._space),
                        ("<Up>", lambda: self._arrow(-1, False)), ("<Down>", lambda: self._arrow(1, False)),
                        ("<Shift-Up>", lambda: self._arrow(-1, True)), ("<Shift-Down>", lambda: self._arrow(1, True)),
                        ("<Home>", lambda: self._arrow(-10 ** 9, False)), ("<End>", lambda: self._arrow(10 ** 9, False))):
            c.bind(seq, lambda _, fn=fn: self._key(fn))
        c.bind("<Escape>", self._escape)
        c.bind("<FocusIn>", lambda _: self._schedule())
        c.bind("<FocusOut>", lambda _: self._schedule())

    def u(self, n):
        """A length in pixels, scaled to the screen."""
        return round(n * self.k)

    # ------------------------------------------------------------------ the items
    def set_order(self, ids):
        """Replace the items (no undo; the history is dropped)."""
        self.order = list(ids)
        self.sel &= set(self.order)
        self.stack.clear()
        self._notify()
        self._clamp()
        self._schedule()

    def append(self, ids):
        self.order += [i for i in ids if i not in self.order]
        self.forget()
        self._schedule()

    def remove(self, ids):
        gone = set(ids)
        self.order = [i for i in self.order if i not in gone]
        self.sel -= gone
        if self.anchor in gone:
            self.anchor = None
        if self.cursor in gone:
            self.cursor = None
        self.forget()
        self._clamp()
        self._schedule()

    def clear(self):
        self.set_order([])

    def selected(self):
        """The selected cards, top to bottom."""
        return [i for i in self.order if i in self.sel]

    def select(self, ids):
        self.sel = set(ids) & set(self.order)
        sel = self.selected()
        self.anchor = self.cursor = sel[-1] if sel else None
        self._schedule()

    def select_all(self):
        self.sel = set(self.order)
        self.anchor = self.order[0] if self.order else None
        self._schedule()

    def refresh(self):
        """The page changed what the cards say."""
        self._schedule()

    def apply_theme(self):
        self.canvas.configure(bg=pick(BG))
        self._schedule()

    # ------------------------------------------------------------------ the order
    def apply(self, new, flash=None):
        """Put the cards in `new` order (undoable). Returns False when that is the order they already have."""
        if list(new) == self.order:
            return False
        self.stack.append(list(self.order))
        del self.stack[:-KEEP]
        self.order = list(new)
        self._flash(flash if flash is not None else self.selected())
        self._notify()
        self._schedule()
        if self.on_reorder:
            self.on_reorder()
        return True

    def move_selected(self, delta):
        sel = self.selected()
        if self.busy() or not sel:
            return False
        done = self.apply(blocks.move_block(self.order, sel, delta), sel)
        self.see(sel[0] if delta < 0 else sel[-1])
        return done

    def to_edge(self, top):
        sel = self.selected()
        if self.busy() or not sel:
            return False
        done = self.apply(blocks.send_to_edge(self.order, sel, top), sel)
        self.see(sel[0] if top else sel[-1])
        return done

    def undo(self):
        """Take back the last move. Returns False when there is nothing to take back (or cards were added or removed
        since, which forgets the history)."""
        if self.busy() or not self.stack:
            return False
        prev = self.stack.pop()
        if set(prev) != set(self.order):
            self.stack.clear()
            self._notify()
            return False
        self.order = prev
        self._flash(self.selected())
        self._notify()
        self._schedule()
        if self.on_reorder:
            self.on_reorder()
        return True

    def forget(self):
        """Cards were added or removed: the history no longer fits."""
        if self.stack:
            self.stack.clear()
            self._notify()

    @property
    def can_undo(self):
        return bool(self.stack)

    def _notify(self):
        if self.on_stack:
            self.on_stack(bool(self.stack))

    def _flash(self, ids):
        now = time.time()
        for i in ids:
            self.flash[i] = now + FLASH_MS / 1000
        self.after(FLASH_MS + 30, self._schedule)

    # ------------------------------------------------------------------ geometry
    def _pitch(self):
        return self.u(self.card_h + GAP)

    def _content(self):
        return self.u(PAD) * 2 + len(self.order) * self._pitch() - self.u(GAP)

    def _view_h(self):
        return max(1, self.canvas.winfo_height())

    def _clamp(self):
        self.offset = max(0, min(self.offset, max(0, self._content() - self._view_h())))

    def card_box(self, iid):
        """(x0, y0, x1, y1) of a card in the canvas, or None when it is not in the list."""
        if iid not in self.order:
            return None
        i = self.order.index(iid)
        y0 = self.u(PAD) + i * self._pitch() - self.offset
        return self.u(6), y0, max(self.u(60), self.canvas.winfo_width() - self.u(10)), y0 + self.u(self.card_h)

    def _hit(self, x, y):
        """(the index of the card at this point, True if the point is on the card itself and not in the gap beside it)."""
        ay = y + self.offset - self.u(PAD)
        if ay < 0:
            return None, False
        i = ay // self._pitch()
        if i >= len(self.order):
            return None, False
        x0, _, x1, _ = self.card_box(self.order[i])
        return int(i), (ay % self._pitch()) < self.u(self.card_h) and x0 <= x <= x1

    def _boundary(self, y):
        """The gap in the list the pointer is at: 0 is above the first card, len(order) below the last."""
        ay = y + self.offset - self.u(PAD)
        if ay <= 0 or not self.order:
            return 0
        return max(0, min(len(self.order), math.ceil((ay - self.u(self.card_h) / 2) / self._pitch())))

    def _line_y(self, boundary):
        return self.u(PAD) + boundary * self._pitch() - self.u(GAP) // 2 - self.offset

    def see(self, iid):
        """Scroll so the card is in view."""
        box = self.card_box(iid)
        if not box:
            return
        h = self._view_h()
        if box[1] < 0:
            self.offset += box[1] - self.u(PAD)
        elif box[3] > h:
            self.offset += box[3] - h + self.u(PAD)
        self._clamp()
        self._schedule()

    # ------------------------------------------------------------------ scrolling
    def _yview(self, *args):
        total = max(1, self._content())
        if args[0] == "moveto":
            self.offset = int(float(args[1]) * total)
        elif args[0] == "scroll":
            step = self._view_h() if args[2] == "pages" else self.u(self.card_h)
            self.offset += int(args[1]) * step
        self._clamp()
        self._schedule()

    def _wheel(self, dy):
        self.offset += self.u(dy)
        self._clamp()
        self._schedule()

    def _configured(self):
        self._clamp()
        self._schedule()

    # ------------------------------------------------------------------ drawing
    def _schedule(self):
        if self._redraw_id is None:
            self._redraw_id = self.after_idle(self.redraw)

    def _fit(self, text, font, width):
        text = str(text or "")
        if width <= 0:
            return ""
        if font.measure(text) <= width:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + "…"

    def redraw(self):
        self._redraw_id = None
        try:
            c = self.canvas
            if not c.winfo_exists():
                return
        except tk.TclError:
            return
        c.delete("all")
        w, h = max(1, c.winfo_width()), self._view_h()
        total = max(1, self._content())
        self.sb.set(self.offset / total, min(1.0, (self.offset + h) / total))
        now = time.time()
        self.flash = {i: t for i, t in self.flash.items() if t > now}
        if not self.order:
            c.create_text(w / 2, h * 0.42, text=self.empty, fill=pick(MUTED), font=(FONT, 12, "bold"), width=w - self.u(60),
                          justify="center")
        else:
            pitch = self._pitch()
            first = max(0, (self.offset - self.u(PAD)) // pitch)
            last = min(len(self.order), (self.offset + h - self.u(PAD)) // pitch + 1)
            for i in range(first, last):
                self._draw_card(self.order[i], w)
        self._draw_overlay()

    def _draw_card(self, iid, w):
        c, u = self.canvas, self.u
        x0, y0, x1, y1 = self.card_box(iid)
        v = self.render(iid)
        ink = pick(INK)
        selected = iid in self.sel
        fill = pick(SELECT_BG) if selected else pick(HOVER) if iid in self.flash else pick(RAISED)
        sh = u(3)
        c.create_rectangle(x0 + sh, y0 + sh, x1 + sh, y1 + sh, fill=ink, outline=ink)
        c.create_rectangle(x0, y0, x1, y1, fill=fill, outline=pick(FOCUS) if iid == self.cursor and self.canvas.focus_get() is self.canvas
                           else ink, width=u(3))
        tone = v.get("tone", "")
        if tone == "bad":
            c.create_rectangle(x0 + u(2), y0 + u(2), x0 + u(8), y1 - u(2), fill=pick(DANGER), outline="")
        elif selected:
            c.create_rectangle(x0 + u(2), y0 + u(2), x0 + u(8), y1 - u(2), fill=pick(PINK), outline="")
        cy = (y0 + y1) / 2
        text_color = pick(MUTED) if tone == "dim" else pick(TEXT)
        left = x0 + u(16)
        if v.get("checked") is not None:
            t = u(20)
            c.create_rectangle(left, cy - t / 2, left + t, cy + t / 2, fill=pick(RAISED), outline=ink, width=u(2))
            if v["checked"]:
                c.create_text(left + t / 2, cy, text="✓", fill=ink, font=(FONT, 13, "bold"))
            left += u(30)
        c.create_rectangle(left, cy - u(15), left + u(40), cy + u(15), fill=pick(ACCENT), outline=ink, width=u(2))
        c.create_text(left + u(20), cy, text=self._fit(v.get("num", ""), self.f_num, u(36)), fill=ON_ACCENT, font=self.f_num)
        left += u(52)
        for k, (img, box) in enumerate(self._picture_boxes(v, left, cy)):
            c.create_image(box[0], box[1], image=self._photo(img, box[2] - box[0], box[3] - box[1]), anchor="nw")
            on = v.get("image_on") == k
            c.create_rectangle(box[0] - 1, box[1] - 1, box[2], box[3], outline=pick(FOCUS) if on else ink, width=u(3) if on else u(1))
            left = box[2] + u(8)
        tx0 = left + u(2)
        tx1 = x1 - u(14)
        for key, text, bb in self._button_boxes(v, (x0, y0, x1, y1)):
            if key is None:
                c.create_text((bb[0] + bb[2]) / 2, cy, text=text, fill=text_color, font=self.f_title)
            else:
                c.create_rectangle(bb[0] + u(2), bb[1] + u(2), bb[2] + u(2), bb[3] + u(2), fill=ink, outline=ink)
                c.create_rectangle(*bb, fill=pick(RAISED), outline=ink, width=u(2))
                c.create_text((bb[0] + bb[2]) / 2, cy, text=text, fill=pick(TEXT), font=self.f_num)
            tx1 = min(tx1, bb[0] - u(10))
        status = self._fit(v.get("status", ""), self.f_sub, int((tx1 - tx0) * 0.42))
        sw = self.f_sub.measure(status) if status else 0
        sub = self._fit(v.get("sub", ""), self.f_sub, tx1 - tx0)
        ty = cy - u(9) if sub else cy   # a card with nothing to add under its name centres the name
        c.create_text(tx0, ty, text=self._fit(v.get("title", ""), self.f_title, tx1 - tx0 - sw - u(10)), anchor="w",
                      fill=text_color, font=self.f_title)
        if status:
            c.create_text(tx1, ty, text=status, anchor="e", font=self.f_sub, fill=pick(DANGER) if tone == "bad" else pick(MUTED))
        if sub:
            c.create_text(tx0, cy + u(11), text=sub, anchor="w", fill=pick(MUTED), font=self.f_sub)

    def _picture_boxes(self, v, left, cy):
        """[(picture, (x0, y0, x1, y1))] for the small pictures at the left of a card, each scaled to fit the card's height."""
        out = []
        h = self.u(self.card_h) - self.u(14)
        for img in v.get("images") or []:
            w = max(1, round(h * img.width / img.height))
            out.append((img, (left, cy - h / 2, left + w, cy + h / 2)))
            left += w + self.u(8)
        return out

    def _photo(self, img, w, h):
        """A picture as the canvas wants it (kept, so it is made once)."""
        key = (id(img), int(w), int(h))
        photo = self._photos.get(key)
        if photo is None:
            if len(self._photos) > 400:
                self._photos.clear()
            photo = self._photos[key] = ImageTk.PhotoImage(img.resize((max(1, int(w)), max(1, int(h)))), master=self.canvas)
            self._photo_owner = getattr(self, "_photo_owner", {})
            self._photo_owner[key] = img   # (so the id() of a picture cannot be reused while its photo is kept)
        return photo

    def _button_boxes(self, v, box):
        """[(key, text, (x0, y0, x1, y1))] for the buttons and labels at the right of a card, drawn right to left."""
        u = self.u
        x0, y0, x1, y1 = box
        cy = (y0 + y1) / 2
        out, right = [], x1 - u(14)
        for key, text in reversed(v.get("buttons") or []):
            w = max(u(26) if key else u(8), self.f_num.measure(text) + (u(16) if key else u(6)))
            h = u(24) if key else u(20)
            out.append((key, text, (right - w, cy - h / 2, right, cy + h / 2)))
            right -= w + u(6)
        return out[::-1]

    def _draw_overlay(self):
        """The line, the stacked card and the selection box: drawn over the cards, from the gesture in progress."""
        c, u = self.canvas, self.u
        c.delete("overlay")
        d = self._d
        if not d or not d.get("moved"):
            return
        w = max(1, c.winfo_width())
        if d["kind"] == "box":
            c.create_rectangle(d["x0"], d["y0"] - self.offset, d["x"], d["y"], outline=pick(FOCUS), width=2, dash=(4, 3),
                               tags="overlay")
            return
        ly = self._line_y(d["boundary"])
        c.create_rectangle(u(6), ly - u(2), w - u(10), ly + u(2), fill=pick(FOCUS), outline="", tags="overlay")
        ids = d["ids"]
        n = len(ids)
        gw, gh = min(u(240), w - u(30)), u(34)
        px, py = d["x"], d["y"]
        left = max(u(6), min(px + u(14), w - gw - u(14)))
        top = max(u(4), min(py + u(8), self._view_h() - gh - u(14)))
        ink = pick(INK)
        for depth in range(min(n, 3) - 1, 0, -1):
            o = depth * u(6)
            c.create_rectangle(left + o, top + o, left + gw + o, top + gh + o, fill=pick(RAISED), outline=ink, width=u(2),
                               tags="overlay")
        c.create_rectangle(left, top, left + gw, top + gh, fill=pick(RAISED), outline=ink, width=u(2), tags="overlay")
        badge = f"{n} {self.noun}s" if n > 1 else ""
        bw = self.f_sub.measure(badge) + u(16) if badge else 0
        name = self._fit(self.render(ids[0]).get("title", ""), self.f_title, gw - bw - u(26))
        c.create_text(left + u(10), top + gh / 2, text=name, anchor="w", fill=pick(TEXT), font=self.f_title, tags="overlay")
        if badge:
            c.create_rectangle(left + gw - bw - u(6), top + u(6), left + gw - u(6), top + gh - u(6), fill=pick(PINK), outline="",
                               tags="overlay")
            c.create_text(left + gw - bw / 2 - u(6), top + gh / 2, text=badge, fill="#111111", font=(FONT, 10, "bold"),
                          tags="overlay")

    # ------------------------------------------------------------------ the mouse
    def _set_sel(self, ids):
        self.sel = set(ids)
        self._schedule()

    def _press(self, e):
        self.canvas.focus_set()
        self._cancel()
        if self.busy():
            return "break"
        i, on_card = self._hit(e.x, e.y)
        ctrl, shift = bool(e.state & 0x4), bool(e.state & 0x1)
        if i is None or not on_card:   # the space between and under the cards: a box can start here
            base = set(self.sel) if ctrl else set()
            if not ctrl:
                self._set_sel(set())
            self._d = {"kind": "box", "x0": e.x, "y0": e.y + self.offset, "x": e.x, "y": e.y, "base": base, "moved": False}
            return "break"
        iid = self.order[i]
        x0, y0, x1, y1 = self.card_box(iid)
        if self.on_button:
            for key, _text, bb in self._button_boxes(self.render(iid), (x0, y0, x1, y1)):
                if key and bb[0] <= e.x <= bb[2] and bb[1] <= e.y <= bb[3]:
                    self.on_button(iid, key)
                    return "break"
        t = self.u(20)
        if self.on_tick and v_checked(self.render(iid)) and x0 + self.u(10) <= e.x <= x0 + self.u(16) + t + self.u(6):
            self.on_tick(iid)
            return "break"
        pending = False
        if shift and self.anchor in self.order:
            a = self.order.index(self.anchor)
            rng = set(self.order[min(a, i):max(a, i) + 1])
            self._set_sel((self.sel if ctrl else set()) | rng)
        elif ctrl:
            self._set_sel(self.sel ^ {iid})
            self.anchor = iid
        elif iid in self.sel:
            pending = len(self.sel) > 1   # a click on one of several selected cards selects just it, on release
            if not pending:
                self.anchor = iid
        else:
            self._set_sel({iid})
            self.anchor = iid
        self.cursor = iid
        if iid not in self.sel:
            return "break"
        self._d = {"kind": "move", "ids": self.selected(), "iid": iid, "x": e.x, "y": e.y, "x_press": e.x, "y_press": e.y,
                   "moved": False, "pending": pending, "boundary": 0}
        return "break"

    def _motion(self, e):
        d = self._d
        if not d:
            return None
        if d["kind"] == "move":
            if not d["moved"]:
                if abs(e.x - d["x_press"]) + abs(e.y - d["y_press"]) < DRAG_PX:
                    return "break"
                d["moved"] = True
                self.canvas.configure(cursor="fleur")
            d["x"], d["y"] = e.x, e.y
            d["boundary"] = self._boundary(e.y)
        else:
            if not d["moved"]:
                if abs(e.y - (d["y0"] - self.offset)) < DRAG_PX and abs(e.x - d["x0"]) < DRAG_PX:
                    return "break"
                d["moved"] = True
            d["x"], d["y"] = e.x, e.y
            self._box_select(d)
        if self._auto is None:
            self._auto = self.after(TICK_MS, self._scroll_tick)
        self._draw_overlay()
        return "break"

    def _box_select(self, d):
        y0, y1 = sorted((d["y0"], d["y"] + self.offset))
        top = self.u(PAD)
        pitch = self._pitch()
        hit = []
        for i, iid in enumerate(self.order):
            cy0 = top + i * pitch
            if cy0 + self.u(self.card_h) > y0 and cy0 < y1:
                hit.append(iid)
        self._set_sel(set(d["base"]) | set(hit))

    def _release(self, e):
        d, self._d = self._d, None
        was_moving = bool(d and d["moved"])
        self._stop()
        if not d:
            return "break"
        if d["kind"] == "move":
            if was_moving:
                self.apply(blocks.insert_block(self.order, d["ids"], d["boundary"]), d["ids"])
            elif d["pending"]:
                self._set_sel({d["iid"]})
                self.anchor = d["iid"]
        self._schedule()
        return "break"

    def _escape(self, _):
        if self._d:
            self._cancel()
            self._schedule()
        return "break"

    def _cancel(self):
        self._d = None
        self._stop()

    def _stop(self):
        if self._auto is not None:
            try:
                self.after_cancel(self._auto)
            except tk.TclError:
                pass
            self._auto = None
        try:
            self.canvas.configure(cursor="")
            self.canvas.delete("overlay")
        except tk.TclError:
            pass

    def _scroll_tick(self):
        """While dragging near the top or bottom edge the list scrolls by itself."""
        self._auto = None
        d = self._d
        if not d or not d["moved"]:
            return
        y = d["y"]
        before = self.offset
        if y < self.u(EDGE_PX):
            self.offset -= self.u(STEP_PX)
        elif y > self._view_h() - self.u(EDGE_PX):
            self.offset += self.u(STEP_PX)
        self._clamp()
        if self.offset != before:
            if d["kind"] == "move":
                d["boundary"] = self._boundary(y)
            else:
                self._box_select(d)
            self.redraw()
        self._auto = self.after(TICK_MS, self._scroll_tick)

    # ------------------------------------------------------------------ the keys
    def _key(self, fn):
        fn()
        return "break"

    def _arrow(self, delta, extend):
        if not self.order or self.busy():
            return
        cur = self.order.index(self.cursor) if self.cursor in self.order else (-1 if delta > 0 else len(self.order))
        new = max(0, min(len(self.order) - 1, cur + delta))
        iid = self.order[new]
        if extend and self.anchor in self.order:
            a = self.order.index(self.anchor)
            self._set_sel(set(self.order[min(a, new):max(a, new) + 1]))
        else:
            self._set_sel({iid})
            self.anchor = iid
        self.cursor = iid
        self.see(iid)

    def _space(self):
        if self.cursor in self.order and self.on_tick and v_checked(self.render(self.cursor)) and not self.busy():
            self.on_tick(self.cursor)


def v_checked(view):
    """True when a card has a tick box."""
    return view.get("checked") is not None
