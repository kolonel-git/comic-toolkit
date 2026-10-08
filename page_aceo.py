"""ACEO sheets page: pick comics or cover images, see the sheets of 8 cards they fill, and save a print-ready PDF made
from the blank template."""
import os
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

import aceo_core as ac
import reading_order as ro
from ui_kit import (ACCENT, BG, BORDER, DANGER, FONT, MUTED, PANEL, TEXT, DropZone, Page, apply_tree_theme, build_tree,
                    button, entry, menu, switch_style, title_block, Splitter, toolbar)

THUMB = 900  # longest side of the in-memory preview copy of a cover
PREVIEW_W = 300  # width of the preview column; the sheet is as tall as the space allows


@dataclass
class Cover:
    path: Path
    data: bytes  # the cover as found (kept so the PDF is made from the original pixels)
    thumb: Image.Image  # a smaller copy for the preview
    iid: str = ""


def _load(q, paths, source):
    files = ac.find_sources(paths)
    if not files:
        q.put(("none",))
    for k, p in enumerate(files):
        try:
            data = ac.load_cover(p, source)
            thumb = ac.decode(data, max_side=THUMB)
            thumb.thumbnail((THUMB, THUMB))
            q.put(("cover", Cover(p, data, thumb), k + 1, len(files)))
        except Exception as e:  # noqa: BLE001 - a corrupt comic must not stop the rest
            q.put(("skip", p.name, str(e) or type(e).__name__))
    q.put(("loaded",))


def _render(q, tpl, cards, o, out, stop):
    try:
        n = ac.render_pdf(tpl, cards, o, out, progress=lambda k, t: q.put(("page", k, t)), stop=stop)
        q.put(("saved", out, n))
    except InterruptedError:
        q.put(("stopped",))
    except Exception as e:  # noqa: BLE001 - report instead of leaving the page waiting
        q.put(("failed", f"{type(e).__name__}: {e}"))


class AceoPage(Page):
    defaults = {"fit": ac.FITS[0], "rotate": ac.ROTATIONS[0], "background": "White", "dpi": "Standard (300 dpi)",
                "source": ac.SOURCES[0], "inset": "0", "outlines": True, "copies": "1", "open_after": True,
                "template": "", "out_dir": "", "outline_color": ac.AUTO_COLOR, "outline_hex": "#FFFFFF",
                "outline_width": ""}
    choices = {"fit": ac.FITS, "rotate": ac.ROTATIONS, "background": list(ac.BACKGROUNDS), "dpi": list(ac.QUALITIES),
               "source": ac.SOURCES, "outline_color": list(ac.OUTLINE_COLORS)}

    def __init__(self, parent):
        super().__init__(parent)
        self.items, self.by_iid = [], {}
        self.tpl, self.tpl_error = None, ""
        self.q = None
        self.busy = None  # 'load' | 'render'
        self.stop = threading.Event()
        self.sheet = 0
        self._after = None
        self._photo = None

        title_block(self.main, "ACEO sheets", "Fill full pages of ACEO cards with the covers you choose, as a PDF.")
        self.drop = DropZone(self.main, "Drop comics, folders or cover images here, or add them below", self.add_files,
                             self.add_folder, self.add_files, files_text="Choose comics or images…")
        self.drop.pack(fill="x")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(12, 6))
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(0, 8))
        self.tools = toolbar(
            bar, [("top", "Top", 48, lambda: self.to_edge(True)), ("up", "▲", 34, lambda: self.shift(-1)),
                  ("down", "▼", 34, lambda: self.shift(1)), ("bottom", "Bottom", 64, lambda: self.to_edge(False))],
            [("remove", "Remove", 72, self.remove), ("clear", "Clear", 60, self.clear)])
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))

        body = ctk.CTkFrame(self.main, fg_color=BG)
        body.pack(fill="both", expand=True)
        right = ctk.CTkFrame(body, fg_color=BG, width=PREVIEW_W)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        Splitter(body, right, side="right", lo=240, hi=700).pack(side="right", fill="y", padx=(6, 6))
        left = ctk.CTkFrame(body, fg_color=BG)
        left.pack(side="left", fill="both", expand=True)
        wrap, self.tree = build_tree(left, [("num", "#", 40, False), ("name", "Cover", 180, True),
                                            ("where", "Sheet · card", 110, False)], selectmode="extended")
        wrap.pack(fill="both", expand=True)

        nav = ctk.CTkFrame(right, fg_color=BG)
        nav.pack(fill="x")
        self.btn_prev = button(nav, "◀", lambda: self._go(-1), width=40)
        self.btn_prev.configure(height=26)
        self.btn_prev.pack(side="left")
        self.lbl_sheet = ctk.CTkLabel(nav, text="", font=(FONT, 13), text_color=TEXT, width=110)
        self.lbl_sheet.pack(side="left", padx=4)
        self.btn_next = button(nav, "▶", lambda: self._go(1), width=40)
        self.btn_next.configure(height=26)
        self.btn_next.pack(side="left")
        self.btn_full = button(nav, "Full screen", self.open_full, width=96)
        self.btn_full.configure(height=26)
        self.btn_full.pack(side="right")
        self.lbl_note = ctk.CTkLabel(right, text="", font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                                     wraplength=PREVIEW_W - 8)
        self.lbl_note.pack(side="bottom", fill="x", pady=(6, 0))
        self.pane = ctk.CTkFrame(right, fg_color=("#EDECE9", "#2C2C2B"), corner_radius=8)
        self.pane.pack(fill="both", expand=True, pady=(8, 0))
        self.pane.pack_propagate(False)
        self.preview = ctk.CTkLabel(self.pane, text="")
        self.preview.pack(expand=True)
        self.pane.bind("<Configure>", lambda _: self._schedule_preview())
        self._full = None

        v = self.vars
        sw = switch_style()
        self.form.heading("Template")
        box = self.form.add("Blank card sheet (PDF)")
        self.lbl_tpl = ctk.CTkLabel(box, text="", font=(FONT, 12), text_color=TEXT, anchor="w", justify="left",
                                    wraplength=260)
        self.lbl_tpl.pack(fill="x")
        row = ctk.CTkFrame(box, fg_color=PANEL)
        row.pack(fill="x", pady=(8, 0))
        button(row, "Choose…", self.choose_template, width=100).pack(side="left")
        button(row, "Use the bundled one", self.reset_template, width=150).pack(side="left", padx=(8, 0))
        self.form.heading("Covers")
        menu(self.form.add("Image from each comic"), v["source"], ac.SOURCES).pack(fill="x")
        menu(self.form.add("Fit the cover"), v["fit"], ac.FITS).pack(fill="x")
        menu(self.form.add("Turn the cover"), v["rotate"], ac.ROTATIONS).pack(fill="x")
        menu(self.form.add("Behind the cover"), v["background"], list(ac.BACKGROUNDS)).pack(fill="x")
        box = self.form.add("Margin inside each card (points)")
        entry(box, v["inset"]).pack(fill="x")
        self.form.heading("Cards")
        box = self.form.add("Copies of each cover")
        entry(box, v["copies"]).pack(fill="x")
        ctk.CTkLabel(box, text="Repeats every cover this many times in a row, to print several of each.",
                     font=(FONT, 11), text_color=MUTED, anchor="w", justify="left", wraplength=260).pack(
            fill="x", pady=(4, 0))
        ctk.CTkSwitch(self.form.add("Card outlines"), text="Draw the template's outlines", variable=v["outlines"],
                      **sw).pack(anchor="w")
        menu(self.form.add("Outline colour"), v["outline_color"], list(ac.OUTLINE_COLORS)).pack(fill="x")
        box = self.form.add("Custom colour (#RRGGBB)")
        entry(box, v["outline_hex"]).pack(fill="x")
        self.lbl_hex = ctk.CTkLabel(box, text="", font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                                    wraplength=260)
        self.lbl_hex.pack(fill="x", pady=(4, 0))
        box = self.form.add("Outline thickness (points, empty = template's)")
        entry(box, v["outline_width"]).pack(fill="x")
        self.form.heading("Output")
        menu(self.form.add("Print quality"), v["dpi"], list(ac.QUALITIES)).pack(fill="x")
        ctk.CTkSwitch(self.form.add("When finished"), text="Open the PDF", variable=v["open_after"], **sw).pack(anchor="w")

        self.btn_make = button(self.footer, "Create PDF…", self.create, primary=True)
        self.btn_make.pack(pady=(0, 8))
        self.btn_stop = button(self.footer, "Stop", self.stop.set)
        self.watch("fit", "rotate", "background", "inset", "outlines", "copies", "dpi", "outline_color", "outline_hex",
                   "outline_width", callback=self._changed)
        self.watch("template", callback=self._load_template)
        self.watch("source", callback=self._source_changed)
        self._load_template()
        self._refresh()

    # ------------------------------------------------------------------ theme
    def apply_theme(self):
        apply_tree_theme(self.tree)
        self._schedule_preview()

    # ------------------------------------------------------------------ template
    def _template_path(self):
        p = self.vars["template"].get().strip()
        return Path(p) if p and Path(p).exists() else ac.default_template()

    def _load_template(self):
        path = self._template_path()
        try:
            self.tpl, self.tpl_error = ac.read_template(path), ""
        except Exception as e:  # noqa: BLE001 - a missing or odd PDF is reported, not fatal
            self.tpl, self.tpl_error = None, f"{type(e).__name__}: {e}"
        if self.tpl:
            s = self.tpl.slots[0]
            self.lbl_tpl.configure(text=f"{path.name}\n{len(self.tpl.slots)} cards per sheet, {s.w / 72:.2f}\" × {s.h / 72:.2f}\" each",
                                   text_color=TEXT)
        else:
            self.lbl_tpl.configure(text=f"{path.name}\n{self.tpl_error}", text_color=DANGER)
        self._refresh()

    def choose_template(self):
        f = filedialog.askopenfilename(title="Blank card template (PDF)", filetypes=[("PDF", "*.pdf")])
        if f:
            self.vars["template"].set(f)

    def reset_template(self):
        self.vars["template"].set("")

    # ------------------------------------------------------------------ options
    def _opts(self):
        o = self.state()
        try:
            inset = max(0.0, float(str(o["inset"]).strip() or 0))
        except ValueError:
            inset = 0.0
        try:
            copies = min(50, max(1, int(str(o["copies"]).strip() or 1)))
        except ValueError:
            copies = 1
        try:
            lw = max(0.0, float(str(o["outline_width"]).strip() or 0))
        except ValueError:
            lw = 0.0
        return {"fit": o["fit"], "rotate": o["rotate"], "background": o["background"], "dpi": o["dpi"], "inset": inset,
                "outlines": bool(o["outlines"]), "copies": copies, "outline_color": o["outline_color"],
                "outline_hex": o["outline_hex"], "outline_width": lw}

    def _changed(self):
        o = self.state()
        custom = o["outline_color"] == ac.CUSTOM_COLOR
        ok = ac.parse_hex(o["outline_hex"]) is not None
        self.lbl_hex.configure(text=("Not a colour: use something like #FF8800. The automatic colour is used instead."
                                     if custom and not ok else "Used when the outline colour is “Custom”."),
                               text_color=DANGER if custom and not ok else MUTED)
        self._refresh()

    def _source_changed(self):
        if self.items and not self.busy:
            self.say("Covers already added keep the page they were read from. Clear and add them again to switch.")

    # ------------------------------------------------------------------ adding covers
    def add_files(self):
        files = filedialog.askopenfilenames(title="Choose comics or cover images", filetypes=[
            ("Comics and images", "*.cbz *.cbr *.jpg *.jpeg *.png *.webp *.bmp *.gif"), ("All", "*.*")])
        if files:
            self.add_paths([Path(f) for f in files])

    def add_folder(self):
        d = filedialog.askdirectory(title="Folder of comics or covers")
        if d:
            self.add_paths([Path(d)])

    def add_paths(self, paths):
        """Add comics and images from files and folders; anything already in the list is skipped."""
        if self.busy:
            return
        have = {str(c.path).lower() for c in self.items}
        new = [p for p in ac.find_sources(paths) if str(p).lower() not in have]
        if not new:
            self.say("Nothing new to add.")
            return
        self.say("")
        self.busy, self.q = "load", queue.Queue()
        self.skipped = []
        self.meta.configure(text=f"Reading {len(new)} cover{'s' if len(new) != 1 else ''}…")
        threading.Thread(target=_load, args=(self.q, new, self.vars["source"].get()), daemon=True).start()
        self._poll()

    # ------------------------------------------------------------------ list editing
    def _sync(self):
        self.items = [self.by_iid[i] for i in self.tree.get_children()]

    def _reorder(self, order):
        for i, iid in enumerate(order):
            self.tree.move(iid, "", i)
        self._sync()
        self._refresh()

    def shift(self, delta):
        sel = self.tree.selection()
        if self.busy or not sel:
            return
        order = list(self.tree.get_children())
        new = ro.move_block(order, sel, delta)
        if new != order:
            self._reorder(new)
        self.tree.see(sel[0] if delta < 0 else sel[-1])

    def to_edge(self, top):
        sel = self.tree.selection()
        if self.busy or not sel:
            return
        order = list(self.tree.get_children())
        new = ro.send_to_edge(order, sel, top)
        if new != order:
            self._reorder(new)
        self.tree.see(sel[0] if top else sel[-1])

    def remove(self):
        sel = self.tree.selection()
        if self.busy or not sel:
            return
        i = min(self.tree.index(s) for s in sel)
        for s in sel:
            self.by_iid.pop(s, None)
        self.tree.delete(*sel)
        self._sync()
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[min(i, len(kids) - 1)])
        self._refresh()

    def clear(self):
        if self.busy:
            return
        self.tree.delete(*self.tree.get_children())
        self.items, self.by_iid = [], {}
        self.say("")
        self._refresh()

    # ------------------------------------------------------------------ workers
    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "cover":
                    c = msg[1]
                    c.iid = self.tree.insert("", "end", values=("", c.path.name, ""))
                    self.items.append(c)
                    self.by_iid[c.iid] = c
                    self.progress.set(msg[2] / msg[3])
                elif kind == "skip":
                    self.skipped.append(f"{msg[1]}: {msg[2]}")
                elif kind == "none":
                    self.say("No comics or images found there.", err=True)
                elif kind == "loaded":
                    self.busy = self.q = None
                    self.progress.set(0)
                    if self.skipped:
                        self.say(f"{len(self.skipped)} skipped ({self.skipped[0]})", err=True)
                    self._refresh()
                    return
                elif kind == "page":
                    self.progress.set(msg[1] / msg[2])
                    self.meta.configure(text=f"Rendering sheet {msg[1]} of {msg[2]}…")
                elif kind in ("saved", "stopped", "failed"):
                    self._finish(msg)
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll)

    def create(self):
        if self.busy:
            return
        if self.tpl is None:
            self.say("The template can't be used: " + self.tpl_error, err=True)
            return
        if not self.items:
            self.say("Add some covers first.", err=True)
            return
        o = self._opts()
        out = filedialog.asksaveasfilename(title="Save the ACEO sheets", defaultextension=".pdf", initialfile="ACEO sheets.pdf",
                                           initialdir=self.vars["out_dir"].get() or None, filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        self.vars["out_dir"].set(str(Path(out).parent))
        cards = ac.expand([c.data for c in self.items], o["copies"])
        self.stop.clear()
        self.busy, self.q = "render", queue.Queue()
        self.out = Path(out)
        self._refresh()
        threading.Thread(target=_render, args=(self.q, self.tpl, cards, o, self.out, self.stop), daemon=True).start()
        self._poll()

    def _finish(self, msg):
        self.busy = self.q = None
        self.progress.set(0)
        self._refresh()
        if msg[0] == "saved":
            self.say(f"Saved {msg[2]} sheet{'s' if msg[2] != 1 else ''}: {msg[1].name}")
            if self.vars["open_after"].get():
                try:
                    os.startfile(msg[1])  # Windows
                except OSError as e:
                    self.say(f"Saved, but it could not be opened: {e}", err=True)
        elif msg[0] == "stopped":
            self.say("Stopped. No file was written.")
        else:
            self.say(msg[1], err=True)

    # ------------------------------------------------------------------ the sheets
    def _cards(self):
        return ac.expand(self.items, self._opts()["copies"])

    def _refresh(self):
        """Counts, positions in the list, buttons and the preview."""
        n_items = len(self.items)
        copies = self._opts()["copies"]
        per = len(self.tpl.slots) if self.tpl else 8
        for k, c in enumerate(self.items):
            first, last = k * copies, k * copies + copies - 1
            where = f"{first // per + 1} · {first % per + 1}" if copies == 1 else \
                f"{first // per + 1} · {first % per + 1}" + (f"–{last % per + 1}" if last // per == first // per else "…")
            self.tree.item(c.iid, values=(k + 1, c.path.name, where))
        cards = n_items * copies
        sheets = ac.sheet_count(cards, self.tpl) if self.tpl else 0
        if self.busy == "load":
            pass
        elif not n_items:
            self.meta.configure(text="Add comics or cover images to begin")
        else:
            blank = sheets * per - cards
            self.meta.configure(text=f"{n_items} cover{'s' if n_items != 1 else ''}"
                                + (f" × {copies}" if copies > 1 else "") + f" = {cards} card{'s' if cards != 1 else ''} on "
                                f"{sheets} sheet{'s' if sheets != 1 else ''}" + (f" ({blank} empty slot{'s' if blank != 1 else ''})" if blank else ""))
        self.sheet = max(0, min(self.sheet, sheets - 1))
        idle = not self.busy
        for key, b in self.tools.items():
            b.configure(state="normal" if idle and (n_items or key == "folder") else "disabled")
        self.btn_make.configure(state="normal" if idle and n_items and self.tpl else "disabled")
        self.btn_stop.pack_forget()
        if self.busy == "render":
            self.btn_stop.pack()
        self.btn_full.configure(state="normal" if sheets and self.tpl else "disabled")
        self.btn_prev.configure(state="normal" if self.sheet > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.sheet < sheets - 1 else "disabled")
        self.lbl_sheet.configure(text=f"Sheet {self.sheet + 1} of {sheets}" if sheets else "No sheets yet")
        self._schedule_preview()
        self._full_draw()

    def _go(self, delta):
        self.sheet += delta
        self._refresh()

    def _schedule_preview(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(120, self._draw_preview)

    @staticmethod
    def _scaling(widget):
        """The display scaling CustomTkinter applies to images (1.25 on a 125% screen)."""
        try:
            return float(widget._get_widget_scaling())
        except Exception:  # noqa: BLE001 - fall back to no correction
            return 1.0

    def _sheet_image(self, size_px, dpi=None, use_originals=False):
        """The current sheet as a picture no bigger than `size_px`, plus the dpi it was drawn at."""
        o = self._opts()
        covers = [c.data if use_originals else c.thumb for c in self._cards()]
        sheets = ac.chunk(covers, self.tpl)
        group = sheets[self.sheet] if sheets else [None] * len(self.tpl.slots)
        w, h = size_px
        scale = min(w / self.tpl.width, h / self.tpl.height)  # pixels per point
        page = ac.compose_sheet(self.tpl, group, o, max(24, scale * 72), outlines_in_image=o["outlines"] or not sheets)
        return page

    def _draw_preview(self):
        self._after = None
        if self.tpl is None:
            self.preview.configure(image=None, text="No usable template")
            return
        k = self._scaling(self.preview)  # winfo sizes are pixels; CTkImage sizes are scaled by k
        w = max(120, self.pane.winfo_width() - 16)
        h = max(160, self.pane.winfo_height() - 16)
        shown = self._sheet_image((w, h))
        self._photo = ctk.CTkImage(light_image=shown, dark_image=shown, size=(shown.width / k, shown.height / k))
        self.preview.configure(image=self._photo, text="")
        self.lbl_note.configure(text="Preview of the sheet. The PDF uses the full-resolution covers and the template's own outlines."
                                if self.items else "")

    # ------------------------------------------------------------------ full-screen preview
    def open_full(self):
        """The sheet at the size of the screen, with arrows to move between sheets. Esc closes it."""
        if self.tpl is None or not self.items:
            return
        if self._full is not None and self._full.winfo_exists():
            self._full.lift()
            return
        win = self._full = ctk.CTkToplevel(self)
        win.title("ACEO sheet preview")
        win.configure(fg_color="#151515")
        bar = ctk.CTkFrame(win, fg_color="#151515")
        bar.pack(fill="x", padx=16, pady=(10, 0))
        self._f_prev = button(bar, "◀", lambda: self._go(-1), width=44)
        self._f_prev.pack(side="left")
        self._f_label = ctk.CTkLabel(bar, text="", font=(FONT, 14), text_color="#EEEEEE", width=150)
        self._f_label.pack(side="left", padx=8)
        self._f_next = button(bar, "▶", lambda: self._go(1), width=44)
        self._f_next.pack(side="left")
        button(bar, "Close  (Esc)", self.close_full, width=110).pack(side="right")
        self._f_image = ctk.CTkLabel(win, text="")
        self._f_image.pack(fill="both", expand=True, padx=12, pady=10)
        for key, fn in (("<Escape>", lambda _: self.close_full()), ("<Left>", lambda _: self._go(-1)),
                        ("<Right>", lambda _: self._go(1))):
            win.bind(key, fn)
        self._f_after = None
        win.bind("<Configure>", lambda _: self._full_later())
        win.after(150, self._full_start)

    def _full_start(self):
        win = self._full
        if win is None or not win.winfo_exists():
            return
        try:
            win.attributes("-fullscreen", True)
        except Exception:  # noqa: BLE001 - a window manager without full screen: it stays a big window
            win.geometry("1100x900")
        win.focus_force()
        self._full_later()

    def close_full(self):
        win, self._full = self._full, None
        if win is not None and win.winfo_exists():
            win.destroy()

    def _full_later(self):
        if self._full is None or not self._full.winfo_exists():
            return
        if self._f_after:
            self._full.after_cancel(self._f_after)
        self._f_after = self._full.after(120, self._full_draw)

    def _full_draw(self):
        win = self._full
        if win is None or not win.winfo_exists() or self.tpl is None:
            return
        self._f_after = None
        sheets = ac.sheet_count(len(self._cards()), self.tpl)
        self._f_label.configure(text=f"Sheet {self.sheet + 1} of {sheets}")
        self._f_prev.configure(state="normal" if self.sheet > 0 else "disabled")
        self._f_next.configure(state="normal" if self.sheet < sheets - 1 else "disabled")
        k = self._scaling(self._f_image)
        w = max(200, self._f_image.winfo_width() - 8)
        h = max(200, self._f_image.winfo_height() - 8)
        shown = self._sheet_image((w, h), use_originals=True)
        self._f_photo = ctk.CTkImage(light_image=shown, dark_image=shown, size=(shown.width / k, shown.height / k))
        self._f_image.configure(image=self._f_photo, text="")
