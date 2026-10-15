"""Pick pages window: every page of an issue as a thumbnail, choose some, save them as JPGs."""
import io
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

import picker_core as pc
from ui_kit import slider, ACCENT, BG, BORDER, FONT, MUTED, PANEL, SELECT_BG, TEXT, button, pick

THUMB_MAX = 360          # longest side of the cached thumbnail
SIZE_MIN, SIZE_MAX, SIZE_START = 70, 260, 130
DRAG_PX = 5              # movement before a press counts as a rubber-band drag instead of a click
COVER = "#E5A100"        # outline colour of pages that look like covers


class PickerWindow(ctk.CTkToplevel):
    """`order` starts the picks (a list of page indexes) and `on_change(order)` is told whenever the picks change, so the
    page that opened this window can share one selection with it; `set_order` is the way back."""

    def __init__(self, parent, comic, order=None, on_change=None):
        super().__init__(parent)
        self.on_change = on_change
        self.comic = comic
        self.n = len(comic.pages)
        self.title(f"Pick pages - {comic.path.name}")
        self.geometry("1100x760")
        self.minsize(640, 420)
        self.configure(fg_color=BG)

        self._order = list(order or [])    # picked page indexes, in the order they will be numbered
        self.anchor = None                 # last clicked page, for shift-click ranges
        self.thumbs = [None] * self.n      # PIL thumbnails as they load
        self.sizes = [None] * self.n       # original (w, h) of each page
        self.covers = set()
        self._photos = {}                  # (index, size) -> PhotoImage for what is on screen
        self._want = []                    # page indexes on screen, loaded first
        self._lock = threading.Lock()
        self._results = queue.Queue()
        self._stop = False
        self._done = set()
        self._drag = None
        self._redraw_id = None
        self._full = None
        self._saved_dir = None

        self._build()
        self._worker = threading.Thread(target=self._load_all, daemon=True)
        self._worker.start()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(60, self._poll)
        self.after(100, self.focus_force)

    @property
    def order(self):
        return self._order

    @order.setter
    def order(self, value):
        self._order = value
        if self.on_change:
            self.on_change(list(value))

    def set_order(self, order):
        """The page changed the picks (without telling it back)."""
        self._order = list(order)
        self._changed()

    # ------------------------------------------------------------------ layout
    def _build(self):
        bar = ctk.CTkFrame(self, fg_color=PANEL)
        bar.pack(fill="x")
        inner = ctk.CTkFrame(bar, fg_color=PANEL)
        inner.pack(fill="x", padx=14, pady=10)
        for text, fn in (("Select all", self.select_all), ("Clear", self.clear), ("Invert", self.invert)):
            button(inner, text, fn, width=84).pack(side="left", padx=(0, 6))
        self.lbl_count = ctk.CTkLabel(inner, text="", font=(FONT, 13), text_color=TEXT, width=150, anchor="w")
        self.lbl_count.pack(side="left", padx=(10, 0))
        self.btn_extract = button(inner, "Extract as JPG…", self.extract, primary=True, width=150)
        self.btn_extract.pack(side="right")
        self.btn_reorder = button(inner, "Reorder…", self.reorder, width=96)
        self.btn_reorder.pack(side="right", padx=(0, 8))
        self.size = tk.IntVar(value=SIZE_START)
        slider(inner, from_=SIZE_MIN, to=SIZE_MAX, variable=self.size, width=140,
               command=lambda _: self._schedule()).pack(side="right", padx=(0, 16))
        ctk.CTkLabel(inner, text="Size", font=(FONT, 12), text_color=MUTED).pack(side="right", padx=(0, 6))

        self.lbl_status = ctk.CTkLabel(self, text="", font=(FONT, 12), text_color=MUTED, anchor="w")
        self.lbl_status.pack(side="bottom", fill="x", padx=14, pady=(4, 8))
        self.btn_open = button(self, "Open folder", self._open_folder, width=110)  # shown after an extract

        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=pick(BG), highlightthickness=0, bd=0)
        self.scroll = ctk.CTkScrollbar(body, command=self.canvas.yview)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.bind("<Configure>", lambda _: self._schedule())
        self.canvas.bind("<MouseWheel>", lambda e: self._wheel(-1 if e.delta > 0 else 1))
        self.canvas.bind("<Button-4>", lambda _: self._wheel(-1))
        self.canvas.bind("<Button-5>", lambda _: self._wheel(1))
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Double-Button-1>", self._double)
        self._update_count()

    def _geometry(self):
        return pc.layout(max(1, self.canvas.winfo_width() - 4), int(self.size.get()))

    def _wheel(self, d):
        self.canvas.yview_scroll(d * 3, "units")

    def _on_scroll(self, a, b):
        self.scroll.set(a, b)
        self._schedule()

    def _schedule(self):
        if self._redraw_id is None:
            self._redraw_id = self.after(15, self.redraw)

    # ------------------------------------------------------------------ drawing
    def redraw(self):
        self._redraw_id = None
        if not self.winfo_exists():
            return
        cols, cw, ch = self._geometry()
        size = int(self.size.get())
        self.canvas.configure(scrollregion=(0, 0, 1, pc.total_height(self.n, cols, ch)))
        top, bottom = self.canvas.canvasy(0), self.canvas.canvasy(self.canvas.winfo_height())
        first = max(0, int((top - pc.GAP) // ch)) * cols
        last = min(self.n, (int((bottom - pc.GAP) // ch) + 1) * cols)
        shown = list(range(first, last))
        with self._lock:
            self._want = shown
        self.canvas.delete("all")
        if len(self._photos) > 400:
            self._photos.clear()
        picked = {i: k for k, i in enumerate(self.order, 1)}
        for i in shown:
            x0, y0, x1, y1 = pc.cell_rect(i, cols, cw, ch)
            sel = i in picked
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=pick(SELECT_BG) if sel else pick(BG),
                                         outline=pick(ACCENT) if sel else (COVER if i in self.covers else pick(BORDER)),
                                         width=3 if sel or i in self.covers else 1)
            img = self.thumbs[i]
            if img is not None:
                photo = self._photos.get((i, size))
                if photo is None:
                    s = min(size / img.width, (size * pc.ASPECT) / img.height)
                    photo = ImageTk.PhotoImage(img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))),
                                                          Image.LANCZOS))
                    self._photos[(i, size)] = photo
                cx = (x0 + x1) // 2
                self.canvas.create_image(cx, y0 + 4 + round(size * pc.ASPECT) // 2, image=photo)
            else:
                self.canvas.create_text((x0 + x1) // 2, y0 + round(size * pc.ASPECT) // 2, text="…", fill=pick(MUTED))
            tag = f"{i + 1}" + ("  cover?" if i in self.covers else "")
            if sel:
                tag += f"   #{picked[i]}"
            self.canvas.create_text((x0 + x1) // 2, y1 - pc.LABEL_H // 2 - 2, text=tag, font=(FONT, 10),
                                    fill=pick(TEXT) if sel else pick(MUTED))
        if self._drag and self._drag["moved"]:
            d = self._drag
            self.canvas.create_rectangle(d["x"], d["y"], d["cx"], d["cy"], outline=pick(ACCENT), width=1, dash=(3, 2))

    def _update_count(self):
        k = len(self.order)
        self.lbl_count.configure(text=f"{k} of {self.n} selected")
        for b in (self.btn_extract, self.btn_reorder):
            b.configure(state="normal" if k else "disabled")

    def _changed(self):
        self._update_count()
        self._schedule()

    # ------------------------------------------------------------------ loading
    def _load_all(self):
        """Background thread: thumbnails for the pages on screen first, then the rest in order."""
        while not self._stop:
            with self._lock:
                todo = [i for i in self._want if i not in self._done]
            if not todo:
                todo = [i for i in range(self.n) if i not in self._done][:1]
            if not todo:
                return
            i = todo[0]
            self._done.add(i)
            try:
                img = Image.open(io.BytesIO(self.comic.read(self.comic.pages[i])))
                size = img.size
                img.draft("RGB", (THUMB_MAX * 2, THUMB_MAX * 2))  # JPEGs decode far faster at reduced size
                img = img.convert("RGB")
                img.thumbnail((THUMB_MAX, THUMB_MAX))
                self._results.put((i, size, img))
            except Exception:  # noqa: BLE001 - one unreadable page must not stop the rest
                self._results.put((i, None, None))

    def _poll(self):
        if self._stop or not self.winfo_exists():
            return
        got = 0
        while got < 12:
            try:
                i, size, img = self._results.get_nowait()
            except queue.Empty:
                break
            self.thumbs[i], self.sizes[i] = img, size
            got += 1
        if got:
            self.covers = pc.likely_covers(self.sizes)
            self._schedule()
        loaded = len(self._done)
        if loaded < self.n:
            self.lbl_status.configure(text=f"Loading thumbnails… {loaded} of {self.n}", text_color=MUTED)
        elif not self.btn_open.winfo_ismapped() and not self._saved_dir:
            self.lbl_status.configure(text="Click to pick, shift-click for a range, drag to box-select, "
                                           "double-click to view. Orange outline = looks like a cover.",
                                      text_color=MUTED)
        self.after(60, self._poll)

    # ------------------------------------------------------------------ mouse
    def _hit(self, x, y):
        cols, cw, ch = self._geometry()
        hits = pc.cells_in((x, y, x, y), self.n, cols, cw, ch)
        return hits[0] if hits else None

    def _press(self, e):
        self.canvas.focus_set()
        x, y = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        self._drag = {"x": x, "y": y, "cx": x, "cy": y, "px": e.x, "py": e.y, "moved": False, "shift": bool(e.state & 0x1),
                      "ctrl": bool(e.state & 0x4), "base": list(self.order), "hit": self._hit(x, y)}

    def _motion(self, e):
        d = self._drag
        if not d:
            return
        d["cx"], d["cy"] = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        if not d["moved"] and abs(e.x - d["px"]) + abs(e.y - d["py"]) < DRAG_PX:
            return
        d["moved"] = True
        cols, cw, ch = self._geometry()
        inside = pc.cells_in((d["x"], d["y"], d["cx"], d["cy"]), self.n, cols, cw, ch)
        base = d["base"] if (d["ctrl"] or d["shift"]) else []
        self.order = pc.add_all(base, inside)
        self._changed()

    def _release(self, e):
        d, self._drag = self._drag, None
        if d and not d["moved"] and d["hit"] is not None:
            i = d["hit"]
            if d["shift"] and self.anchor is not None:
                self.order = pc.add_all(self.order, pc.range_between(self.anchor, i))
            else:
                self.order = pc.toggle(self.order, i)
            self.anchor = i
        elif d and d["moved"]:
            self.anchor = self.order[-1] if self.order else None
        self._changed()

    def _double(self, e):
        i = self._hit(self.canvas.canvasx(e.x), self.canvas.canvasy(e.y))
        if i is not None:
            self.open_full(i)

    # ------------------------------------------------------------------ selection buttons
    def select_all(self):
        self.order = pc.add_all(self.order, range(self.n))
        self._changed()

    def clear(self):
        self.order = []
        self._changed()

    def invert(self):
        self.order = pc.invert(self.order, self.n)
        self._changed()

    def reorder(self):
        """Dialog to set the numbering order of the picked pages."""
        if not self.order:
            return
        win = ctk.CTkToplevel(self)
        win.title("Order of picked pages")
        win.geometry("340x460")
        win.configure(fg_color=BG)
        win.transient(self)
        ctk.CTkLabel(win, text="Files are numbered in this order.", font=(FONT, 12), text_color=MUTED,
                     anchor="w").pack(fill="x", padx=14, pady=(12, 6))
        box = tk.Listbox(win, activestyle="none", exportselection=False, font=(FONT, 11), bd=0, highlightthickness=1,
                         bg=pick(BG), fg=pick(TEXT), selectbackground=pick(ACCENT), highlightbackground=pick(BORDER))
        box.pack(fill="both", expand=True, padx=14)
        order = list(self.order)

        def fill(sel=None):
            box.delete(0, "end")
            for k, i in enumerate(order, 1):
                box.insert("end", f"{k}.  page {i + 1}")
            if sel is not None:
                box.selection_set(sel)
                box.see(sel)

        def shift(delta):
            cur = box.curselection()
            if cur:
                new, pos = pc.move(order, cur[0], delta)
                order[:] = new
                fill(pos)

        def by_page():
            order.sort()
            fill()

        row = ctk.CTkFrame(win, fg_color=BG)
        row.pack(fill="x", padx=14, pady=8)
        button(row, "Up", lambda: shift(-1), width=60).pack(side="left")
        button(row, "Down", lambda: shift(1), width=60).pack(side="left", padx=6)
        button(row, "By page", by_page, width=80).pack(side="left")

        def ok():
            self.order = list(order)
            win.destroy()
            self._changed()

        foot = ctk.CTkFrame(win, fg_color=BG)
        foot.pack(fill="x", padx=14, pady=(0, 12))
        button(foot, "Done", ok, primary=True, width=100).pack(side="right")
        button(foot, "Cancel", win.destroy, width=90).pack(side="right", padx=(0, 8))
        fill()
        win.after(150, win.grab_set)

    # ------------------------------------------------------------------ extract
    def extract(self):
        if not self.order:
            return
        folder = filedialog.askdirectory(title="Save the picked pages to", parent=self,
                                         initialdir=str(self.comic.path.parent))
        if not folder:
            return
        try:
            saved = pc.extract_pages(self.comic, self.order, folder)
        except Exception as e:  # noqa: BLE001
            self.lbl_status.configure(text=str(e), text_color="#E03E3E")
            return
        self._saved_dir = folder
        self.lbl_status.configure(text=f"Saved {len(saved)} JPG{'s' if len(saved) != 1 else ''} to {folder}",
                                  text_color=TEXT)
        self.btn_open.pack(side="bottom", anchor="w", padx=14, pady=(0, 2))

    def _open_folder(self):
        if self._saved_dir:
            try:
                os.startfile(self._saved_dir)
            except (AttributeError, OSError):
                pass

    # ------------------------------------------------------------------ full view
    def open_full(self, i):
        """One page at screen size. Arrows move, Space picks, Esc closes."""
        if self._full is not None and self._full.winfo_exists():
            self._full.destroy()
        win = self._full = ctk.CTkToplevel(self)
        win.title("Page view")
        win.configure(fg_color="#151515")
        self._fi = i
        bar = ctk.CTkFrame(win, fg_color="#151515")
        bar.pack(fill="x", padx=16, pady=(10, 0))
        button(bar, "◀", lambda: self._fgo(-1), width=44).pack(side="left")
        self._f_label = ctk.CTkLabel(bar, text="", font=(FONT, 14), text_color="#EEEEEE", width=220)
        self._f_label.pack(side="left", padx=8)
        button(bar, "▶", lambda: self._fgo(1), width=44).pack(side="left")
        button(bar, "Close  (Esc)", win.destroy, width=110).pack(side="right")
        self._f_pick = button(bar, "", lambda: self._fpick(), width=120)
        self._f_pick.pack(side="right", padx=8)
        button(bar, "Fit", lambda: self._fzoom_to(1.0), width=60).pack(side="right")
        button(bar, "+", lambda: self._fzoom_by(1.25), width=44).pack(side="right", padx=(0, 6))
        button(bar, "−", lambda: self._fzoom_by(0.8), width=44).pack(side="right", padx=(0, 6))
        self._f_hint = ctk.CTkLabel(win, text="Click the page to pick or unpick it · wheel: next page, or scroll when zoomed · "
                                              "Ctrl+wheel or +/−: zoom · drag: move · Left/Right: page · Space: pick · Esc: close",
                                    font=(FONT, 11), text_color="#AAAAAA")
        self._f_hint.pack(side="bottom", pady=(0, 8))
        self._f_canvas = tk.Canvas(win, bg="#151515", highlightthickness=0, bd=0)
        self._f_canvas.pack(fill="both", expand=True, padx=12, pady=10)
        self._fz, self._fpan, self._fsrc, self._fdrag = 1.0, [0, 0], (None, None), None
        self._f_photo = None
        c = self._f_canvas
        c.bind("<MouseWheel>", lambda e: self._fwheel(1 if e.delta < 0 else -1, bool(e.state & 0x4)))
        c.bind("<Button-4>", lambda e: self._fwheel(-1, bool(e.state & 0x4)))
        c.bind("<Button-5>", lambda e: self._fwheel(1, bool(e.state & 0x4)))
        c.bind("<ButtonPress-1>", self._fpress)
        c.bind("<B1-Motion>", self._fmotion)
        c.bind("<ButtonRelease-1>", self._frelease)
        for key, fn in (("<Escape>", lambda _: win.destroy()), ("<Left>", lambda _: self._fgo(-1)),
                        ("<Right>", lambda _: self._fgo(1)), ("<space>", lambda _: self._fpick()),
                        ("<plus>", lambda _: self._fzoom_by(1.25)), ("<equal>", lambda _: self._fzoom_by(1.25)),
                        ("<minus>", lambda _: self._fzoom_by(0.8)), ("<Key-0>", lambda _: self._fzoom_to(1.0)),
                        ("<Up>", lambda _: self._fscroll(120)), ("<Down>", lambda _: self._fscroll(-120))):
            win.bind(key, fn)
        self._f_after = None
        win.bind("<Configure>", lambda _: self._flater())
        win.after(150, lambda: self._fstart(win))

    def _fstart(self, win):
        if not win.winfo_exists():
            return
        try:
            win.attributes("-fullscreen", True)
        except Exception:  # noqa: BLE001
            win.geometry("1100x900")
        win.focus_force()
        self._flater()

    def _fgo(self, d):
        self._fi = min(self.n - 1, max(0, self._fi + d))
        self._fz, self._fpan = 1.0, [0, 0]
        self._flater()

    def _fpick(self):
        self.order = pc.toggle(self.order, self._fi)
        self.anchor = self._fi
        self._changed()
        self._flater()

    def _fzoom_by(self, k):
        self._fzoom_to(self._fz * k)

    def _fzoom_to(self, z):
        z = min(8.0, max(1.0, z))
        if z == 1.0:
            self._fpan = [0, 0]
        else:  # keep the same point in the middle
            k = z / self._fz
            self._fpan = [self._fpan[0] * k, self._fpan[1] * k]
        self._fz = z
        self._flater()

    def _fwheel(self, d, ctrl):
        if ctrl:
            self._fzoom_by(1.25 if d < 0 else 0.8)
        elif self._fz > 1.0:
            self._fscroll(-d * 120)
        else:
            self._fgo(d)

    def _fscroll(self, dy):
        self._fpan[1] += dy
        self._fclamp()
        self._fmove()

    def _fpress(self, e):
        self._fdrag = {"x": e.x, "y": e.y, "pan": list(self._fpan), "moved": False}

    def _fmotion(self, e):
        d = self._fdrag
        if not d:
            return
        if abs(e.x - d["x"]) + abs(e.y - d["y"]) >= DRAG_PX:
            d["moved"] = True
        if d["moved"]:
            self._fpan = [d["pan"][0] + e.x - d["x"], d["pan"][1] + e.y - d["y"]]
            self._fclamp()
            self._fmove()

    def _frelease(self, e):
        d, self._fdrag = self._fdrag, None
        if d and not d["moved"]:
            self._fpick()

    def _fclamp(self):
        """Keep the zoomed page from being dragged out of view."""
        ph = self._f_photo
        if ph is None:
            return
        c = self._f_canvas
        for k, (have, need) in enumerate(((ph.width(), c.winfo_width()), (ph.height(), c.winfo_height()))):
            lim = max(0, (have - need) / 2)
            self._fpan[k] = max(-lim, min(lim, self._fpan[k]))

    def _fmove(self):
        c = self._f_canvas
        c.coords("page", c.winfo_width() / 2 + self._fpan[0], c.winfo_height() / 2 + self._fpan[1])

    def _flater(self):
        win = self._full
        if win is None or not win.winfo_exists():
            return
        if self._f_after:
            win.after_cancel(self._f_after)
        self._f_after = win.after(60, self._fdraw)

    def _fdraw(self):
        win = self._full
        if win is None or not win.winfo_exists():
            return
        self._f_after = None
        i = self._fi
        on = i in self.order
        self._f_label.configure(text=f"Page {i + 1} of {self.n}" + (f"  (picked #{self.order.index(i) + 1})" if on else ""))
        self._f_pick.configure(text="Unpick" if on else "Pick")
        c = self._f_canvas
        c.configure(highlightthickness=4 if on else 0, highlightbackground=pick(ACCENT), highlightcolor=pick(ACCENT))
        if self._fsrc[0] != i:
            try:
                self._fsrc = (i, Image.open(io.BytesIO(self.comic.read(self.comic.pages[i]))).convert("RGB"))
            except Exception:  # noqa: BLE001
                self._fsrc = (i, None)
        img = self._fsrc[1]
        c.delete("all")
        if img is None:
            c.create_text(c.winfo_width() / 2, c.winfo_height() / 2, text="Can't read this page", fill="#EEEEEE")
            self._f_photo = None
            return
        w, h = max(200, c.winfo_width() - 8), max(200, c.winfo_height() - 8)
        s = min(w / img.width, h / img.height) * self._fz
        size = (max(1, round(img.width * s)), max(1, round(img.height * s)))
        self._f_photo = ImageTk.PhotoImage(img.resize(size, Image.LANCZOS))
        c.create_image(0, 0, image=self._f_photo, tags="page")
        self._fclamp()
        self._fmove()

    # ------------------------------------------------------------------ closing
    def close(self):
        self._stop = True
        if self._full is not None and self._full.winfo_exists():
            self._full.destroy()
        self.destroy()
