"""ACEO sheets page: lay comic covers out as trading cards on printable sheets and save a print-ready PDF made from the blank
template. On the shared page shell in two columns with a divider you can drag. Left: Covers, a list of cards (one per cover,
with its picture, a copies stepper and a front / back switch) you can reorder. Right, scrolling on its own: Preview and print
(the sheet as it will print, a strip of every sheet, swapping cards by dragging them, the print quality) and Cards (how each
cover fits, turns and sits on its card, shown as pictures)."""
import os
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

import aceo_core as ac
from cardlist import CardList
from flow_kit import Advanced, ChoiceCards, SegmentPage, labelled, section
from ui_kit import (ACCENT, BG, BORDER, DANGER, FOCUS, FONT, MUTED, PINK, TEXT, TYPE_BODY, TYPE_HINT, DropZone,
                    FlowRow, Toggle, button, divider, entry, menu, pick, switch_style, tool_button, tooltip)

THUMB = 900        # longest side of the in-memory preview copy of a cover
BACK_THUMB = 360   # ... and of a back cover (only the preview needs it)
SMALL = 140        # longest side of the picture on a card in the list
STRIP_W = 70       # width of a sheet in the strip, in pixels at 96 dpi
FIT_TITLES = ["Fill and crop", "Fit inside", "Stretch"]
TURN_TITLES = ["Turn, top left", "Turn, top right", "Never turn"]
MARGINS = [("0", "No margin"), ("4", "4 pt"), ("8", "8 pt"), ("12", "12 pt")]
DRAG_PX = 5


@dataclass
class Cover:
    path: Path
    data: bytes             # the front as found (kept so the PDF is made from the original pixels)
    thumb: Image.Image      # a smaller copy of the front for the preview
    small: Image.Image      # the picture on the card in the list
    back_thumb: Image.Image = None   # the same for the last page, when the comic has one
    back_small: Image.Image = None
    iid: str = ""
    copies: int = 1
    use_back: bool = False
    back_data: bytes = None  # the last page's original, read when it is first needed

    @property
    def can_back(self):
        return self.back_thumb is not None

    def shown(self):
        """The picture the preview uses."""
        return self.back_thumb if self.use_back and self.back_thumb is not None else self.thumb

    def original(self):
        """The cover's own pixels for the PDF (the last page is read from the comic the first time it is wanted)."""
        if self.use_back and self.can_back:
            if self.back_data is None:
                self.back_data = ac.load_cover(self.path, ac.SOURCES[1])
            return self.back_data
        return self.data


def _small(img):
    img = img.copy()
    img.thumbnail((SMALL, SMALL))
    return img


def _load(q, paths, source):
    files = ac.find_sources(paths)
    if not files:
        q.put(("none",))
    for k, p in enumerate(files):
        try:
            front, back = ac.load_pair(p)
            thumb = ac.decode(front, max_side=THUMB)
            thumb.thumbnail((THUMB, THUMB))
            cover = Cover(p, front, thumb, _small(thumb))
            if back is not None:
                bt = ac.decode(back, max_side=BACK_THUMB)
                bt.thumbnail((BACK_THUMB, BACK_THUMB))
                cover.back_thumb, cover.back_small = bt, _small(bt)
                cover.use_back = source == ac.SOURCES[1]
            q.put(("cover", cover, k + 1, len(files)))
        except Exception as e:  # noqa: BLE001 - a corrupt comic must not stop the rest
            q.put(("skip", p.name, str(e) or type(e).__name__))
    q.put(("loaded",))


def _render(q, tpl, entries, counts, o, out, stop):
    """`entries` is [(path, front bytes, use the last page?)]; the last pages are read here, off the screen's thread."""
    try:
        covers = []
        for path, data, back in entries:
            covers.append(ac.load_cover(path, ac.SOURCES[1]) if back else data)
        n = ac.render_pdf(tpl, ac.expand(covers, counts), o, out, progress=lambda k, t: q.put(("page", k, t)), stop=stop)
        q.put(("saved", out, n))
    except InterruptedError:
        q.put(("stopped",))
    except Exception as e:  # noqa: BLE001 - report instead of leaving the page waiting
        q.put(("failed", f"{type(e).__name__}: {e}"))


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


class AceoPage(SegmentPage):
    title = "ACEO sheets"
    subtitle = "Lay covers out as trading cards on printable sheets."
    defaults = {"fit": ac.FITS[0], "rotate": ac.ROTATIONS[0], "background": "White", "dpi": "Standard (300 dpi)",
                "source": ac.SOURCES[0], "inset": "0", "outlines": True, "open_after": True,
                "template": "", "out_dir": "", "outline_color": ac.AUTO_COLOR, "outline_hex": "#FFFFFF",
                "outline_width": ""}
    choices = {"fit": ac.FITS, "rotate": ac.ROTATIONS, "background": list(ac.BACKGROUNDS), "dpi": list(ac.QUALITIES),
               "source": ac.SOURCES, "outline_color": list(ac.OUTLINE_COLORS)}
    split = True
    show_auto = False
    max_width = 1600

    def __init__(self, parent):
        super().__init__(parent)
        self.items, self.by_iid = [], {}
        self.tpl, self.tpl_error = None, ""
        self.q = None
        self.busy = None  # 'load' | 'render'
        self.stop = threading.Event()
        self.sheet = 0
        self.out = None
        self.skipped = []
        self._ids = 0
        self._first = {}        # cover id -> the position of its first card
        self._sample = None     # the cover the option pictures were drawn from
        self._after = None
        self._sharp = None
        self._photo = None
        self._geom = None        # (x of the sheet on the canvas, y, pixels per point) of the sheet on show
        self._drag = None
        self._strip_photos = []
        self._strip_cache = {}
        self._pics_after = None
        self._full = None
        v = self.vars

        # ---- Covers
        self.make_panes(right_width=520, lo=400)
        self.s1 = self.add_block("Covers", side="left", grow=True)
        self.drop = DropZone(self.s1.body, "Drop comics, folders or cover images here", self.add_files, self.add_folder,
                             self.add_files, files_text="Choose comics or images…", compact=True)
        self.drop.pack(fill="x", padx=(0, 6))
        bar = FlowRow(self.s1.body)
        bar.pack(fill="x", pady=(0, 2))
        self.tools = {}
        groups = [[("top", "Top", 44, lambda: self.to_edge(True)), ("up", "▲", 30, lambda: self.shift(-1)),
                   ("down", "▼", 30, lambda: self.shift(1)), ("bottom", "Bottom", 58, lambda: self.to_edge(False))],
                  [("undo", "Undo", 50, lambda: self.undo())],
                  [("remove", "Remove", 64, self.remove), ("clear", "Clear", 52, self.clear)]]
        for g, group in enumerate(groups):
            if g:
                bar.add(divider(bar), divider=True)
            for key, text, width, cmd in group:
                self.tools[key] = tool_button(bar, text, cmd, width)
                bar.add(self.tools[key])
        for key, tip in (("up", "Move the selected covers up (Alt+Up)"), ("down", "Move the selected covers down (Alt+Down)"),
                         ("undo", "Take back the last move (Ctrl+Z)")):
            tooltip(self.tools[key], tip)
        self.hint = ctk.CTkLabel(self.s1.body, text="Hold a cover and drag it. Ctrl or Shift selects several. − and + set how many "
                                 "copies to print; Front or Back picks the page.", font=TYPE_HINT, text_color=MUTED, anchor="w",
                                 justify="left", wraplength=560)
        self.hint.pack(side="bottom", fill="x", pady=(2, 0))
        self.status = ctk.CTkLabel(self.s1.body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                   wraplength=560)
        self.cards = CardList(self.s1.body, self._render_cover, on_reorder=self._moved, noun="cover", card_h=76,
                              empty="Add comics or cover images above. Their covers are printed in this order.",
                              busy=lambda: bool(self.busy), on_stack=lambda _: self._refresh_buttons(), on_button=self._card_button)
        self.cards.pack(fill="both", expand=True, padx=(0, 6))
        self.s1.body.bind("<Configure>", lambda e: [w.configure(wraplength=max(200, int(e.width / self._get_widget_scaling()) - 20))
                                                    for w in (self.hint, self.status)], add="+")

        # ---- Preview and print
        self.s2 = self.add_block("Preview and print")
        body = self.s2.body
        self.note = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=480)
        self.note.pack(fill="x", pady=(0, 6))
        nav = ctk.CTkFrame(body, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 6))
        self.btn_prev = tool_button(nav, "◀", lambda: self._go(-1), 40)
        self.btn_prev.pack(side="left")
        self.lbl_sheet = ctk.CTkLabel(nav, text="", font=(FONT, 13, "bold"), text_color=TEXT, width=130)
        self.lbl_sheet.pack(side="left", padx=4)
        self.btn_next = tool_button(nav, "▶", lambda: self._go(1), 40)
        self.btn_next.pack(side="left")
        self.btn_full = tool_button(nav, "Full screen", self.open_full, 100)
        self.btn_full.pack(side="right")
        self.pane = ctk.CTkFrame(body, fg_color=("#FFFFFF", "#1E1E1E"), border_color=BORDER, border_width=3, corner_radius=0)
        self.pane.pack(fill="x")
        self.view = tk.Canvas(self.pane, height=430, highlightthickness=0, bd=0, bg=pick(("#FFFFFF", "#1E1E1E")), takefocus=1)
        self.view.pack(fill="x", padx=4, pady=4)
        self.preview = self.view
        self.view.bind("<Configure>", lambda _: self._schedule_preview())
        self.view.bind("<ButtonPress-1>", self._vpress)
        self.view.bind("<B1-Motion>", self._vmotion)
        self.view.bind("<ButtonRelease-1>", self._vrelease)
        self.view.bind("<Left>", lambda _: self._go(-1))
        self.view.bind("<Right>", lambda _: self._go(1))
        self.strip_box = ctk.CTkFrame(body, fg_color="transparent")
        self.strip_box.pack(fill="x", pady=(8, 0))
        self.strip = tk.Canvas(self.strip_box, height=108, highlightthickness=0, bd=0, bg=pick(BG))
        self.strip_sb = ctk.CTkScrollbar(self.strip_box, orientation="horizontal", command=self.strip.xview, height=12)
        self.strip.configure(xscrollcommand=self.strip_sb.set)
        self.strip.pack(fill="x")
        self.strip_sb.pack(fill="x")
        self.strip.bind("<Button-1>", self._strip_click)
        self.strip.bind("<MouseWheel>", lambda e: self.strip.xview_scroll(-1 if e.delta > 0 else 1, "units"))
        row = labelled(body, "Print quality")
        menu(row.cell, v["dpi"], list(ac.QUALITIES)).pack(fill="x")
        row.pack(fill="x", pady=(10, 6))
        Toggle(body, text="Open the PDF when it is done", variable=v["open_after"], **switch_style()).pack(anchor="w")
        self.print_hint = ctk.CTkLabel(body, text="Print at 100% scale (no \"fit to page\") so the cards come out at their true size.",
                                       font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=480)
        self.print_hint.pack(fill="x", pady=(6, 0))
        self.progress = ctk.CTkProgressBar(body, height=14, corner_radius=0, border_width=3, border_color=BORDER, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)

        # ---- Cards
        self.s3 = self.add_block("Cards")
        body = self.s3.body
        pic = (112, 80)
        section(body, "How the cover fits").pack(fill="x", pady=(0, 8))
        self.fit_cards = ChoiceCards(body, v["fit"], [(f, t, "") for f, t in zip(ac.FITS, FIT_TITLES)], columns=3, picture=pic)
        self.fit_cards.pack(fill="x")
        section(body, "Turning").pack(fill="x", pady=(8, 8))
        self.turn_cards = ChoiceCards(body, v["rotate"], [(r, t, "") for r, t in zip(ac.ROTATIONS, TURN_TITLES)], columns=3,
                                      picture=pic)
        self.turn_cards.pack(fill="x")
        section(body, "Behind the cover").pack(fill="x", pady=(8, 8))
        self.bg_cards = ChoiceCards(body, v["background"], [(b, b, "") for b in ac.BACKGROUNDS], columns=3, picture=pic)
        self.bg_cards.pack(fill="x")
        section(body, "Margin inside each card").pack(fill="x", pady=(8, 8))
        self.margin_cards = ChoiceCards(body, v["inset"], [(m, t, "") for m, t in MARGINS], columns=2, picture=pic)
        self.margin_cards.pack(fill="x")
        self.adv = Advanced(body)
        self.adv.pack(fill="x", pady=(10, 0))
        sw = switch_style()
        Toggle(self.adv.body, text="Draw the template's card outlines", variable=v["outlines"], **sw).pack(anchor="w", pady=(0, 10))
        row = labelled(self.adv.body, "Outline colour")
        menu(row.cell, v["outline_color"], list(ac.OUTLINE_COLORS)).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "Custom colour (#RRGGBB)")
        entry(row.cell, v["outline_hex"]).pack(fill="x")
        self.lbl_hex = ctk.CTkLabel(row.cell, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.lbl_hex.pack(fill="x", pady=(4, 0))
        row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "Outline thickness (points, empty = the template's)")
        entry(row.cell, v["outline_width"]).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "Margin in points (any number)")
        entry(row.cell, v["inset"]).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "Covers you add next come from")
        menu(row.cell, v["source"], ac.SOURCES).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "Blank card sheet (PDF)")
        self.lbl_tpl = ctk.CTkLabel(row.cell, text="", font=TYPE_HINT, text_color=TEXT, anchor="w", justify="left", wraplength=440)
        self.lbl_tpl.pack(fill="x")
        trow = ctk.CTkFrame(row.cell, fg_color="transparent")
        trow.pack(fill="x", pady=(8, 0))
        tool_button(trow, "Choose…", self.choose_template, 100).pack(side="left")
        tool_button(trow, "Use the bundled one", self.reset_template, 160).pack(side="left", padx=(8, 0))
        row.pack(fill="x")

        self.fit_right(self.note, self.print_hint, self.lbl_hex, self.lbl_tpl)
        self.watch("fit", "rotate", "background", "inset", "outlines", "dpi", "outline_color", "outline_hex", "outline_width",
                   callback=self._changed)
        self.watch("template", callback=self._load_template)
        self.watch("source", callback=self._source_changed)
        self._load_template()
        self._refresh()
        self._pictures_soon()

    # ------------------------------------------------------------------ theme
    def apply_theme(self):
        super().apply_theme()
        self.cards.apply_theme()
        self.view.configure(bg=pick(("#FFFFFF", "#1E1E1E")))
        self.strip.configure(bg=pick(BG))
        self._strip_cache.clear()
        self._schedule_preview()
        self._draw_strip()

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
            lw = max(0.0, float(str(o["outline_width"]).strip() or 0))
        except ValueError:
            lw = 0.0
        return {"fit": o["fit"], "rotate": o["rotate"], "background": o["background"], "dpi": o["dpi"], "inset": inset,
                "outlines": bool(o["outlines"]), "outline_color": o["outline_color"],
                "outline_hex": o["outline_hex"], "outline_width": lw}

    def _changed(self):
        o = self.state()
        custom = o["outline_color"] == ac.CUSTOM_COLOR
        ok = ac.parse_hex(o["outline_hex"]) is not None
        self.lbl_hex.configure(text=("Not a colour: use something like #FF8800. The automatic colour is used instead."
                                     if custom and not ok else "Used when the outline colour is “Custom”."),
                               text_color=DANGER if custom and not ok else MUTED)
        self._pictures_soon()
        self._refresh()

    def _source_changed(self):
        if self.items and not self.busy:
            self.say("Covers already in the list keep their page: use a cover's Front / Back switch to change it.")

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

    def set_folder(self, folder):
        self.add_paths([Path(folder)])

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
        self.s1.set_summary(f"Reading {_plural(len(new), 'cover')}…")
        threading.Thread(target=_load, args=(self.q, new, self.vars["source"].get()), daemon=True).start()
        self._poll()

    # ------------------------------------------------------------------ the list of covers
    def say(self, msg, err=False):
        super().say(msg, err)
        if msg:
            self.status.pack(side="bottom", fill="x", pady=(4, 0), after=self.hint)
        else:
            self.status.pack_forget()

    def _sync(self):
        self.items = [self.by_iid[i] for i in self.cards.order]

    def _moved(self):
        """The covers were put in another order (dragged, by the keys or buttons, or by an undo)."""
        self._sync()
        self._refresh()

    def shift(self, delta):
        self.cards.move_selected(delta)

    def to_edge(self, top):
        self.cards.to_edge(top)

    def undo(self):
        self.cards.undo()

    def remove(self):
        sel = self.cards.selected()
        if self.busy or not sel:
            return
        i = min(self.cards.order.index(x) for x in sel)
        for x in sel:
            self.by_iid.pop(x, None)
        self.cards.remove(sel)
        self._sync()
        if self.cards.order:
            self.cards.select([self.cards.order[min(i, len(self.cards.order) - 1)]])
        self._refresh()

    def clear(self):
        if self.busy:
            return
        self.cards.clear()
        self.items, self.by_iid = [], {}
        self.say("")
        self._refresh()

    def _card_button(self, iid, key):
        c = self.by_iid.get(iid)
        if c is None or self.busy:
            return
        if key == "less":
            c.copies = max(1, c.copies - 1)
        elif key == "more":
            c.copies = min(50, c.copies + 1)
        elif key == "back" and c.can_back:
            c.use_back = not c.use_back
        self._refresh()

    def _positions(self):
        """The first card position of each cover, in list order, and the total number of cards."""
        out, n = {}, 0
        for c in self.items:
            out[c.iid] = n
            n += c.copies
        return out, n

    def _render_cover(self, iid):
        c = self.by_iid.get(iid)
        if c is None:
            return {"title": str(iid)}
        per = len(self.tpl.slots) if self.tpl else 8
        first = self._first.get(iid, 0)
        last = first + c.copies - 1
        where = f"Sheet {first // per + 1} · card {first % per + 1}"
        if c.copies > 1:
            where = f"Sheet {first // per + 1} · card {first % per + 1}" + (f"–{last % per + 1}" if last // per == first // per
                                                                              else f" … sheet {last // per + 1} · card {last % per + 1}")
        buttons = ([("back", "Back" if c.use_back else "Front")] if c.can_back else []) + [("less", "−"), (None, f"×{c.copies}"), ("more", "+")]
        images = [c.small] + ([c.back_small] if c.can_back else [])
        return {"num": str(self.items.index(c) + 1 if c in self.items else ""), "title": c.path.name, "sub": where, "status": "",
                "tone": "", "checked": None, "images": images, "image_on": 1 if c.use_back and c.can_back else 0, "buttons": buttons}

    # ------------------------------------------------------------------ workers
    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "cover":
                    c = msg[1]
                    self._ids += 1
                    c.iid = f"c{self._ids}"
                    self.items.append(c)
                    self.by_iid[c.iid] = c
                    self.cards.append([c.iid])
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
                    self._pictures_soon()
                    return
                elif kind == "page":
                    self.progress.set(msg[1] / msg[2])
                    self.s2.set_summary(f"Rendering sheet {msg[1]} of {msg[2]}…")
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
        entries = [(c.path, c.data, c.use_back and c.can_back) for c in self.items]
        self.stop.clear()
        self.busy, self.q = "render", queue.Queue()
        self.out = Path(out)
        self.progress.pack(fill="x", pady=(10, 0))
        self._refresh()
        threading.Thread(target=_render, args=(self.q, self.tpl, entries, [c.copies for c in self.items], o, self.out, self.stop),
                         daemon=True).start()
        self._poll()

    def _finish(self, msg):
        self.busy = self.q = None
        self.progress.set(0)
        self.progress.pack_forget()
        if msg[0] == "saved":
            self.say(f"Saved {_plural(msg[2], 'sheet')}: {msg[1].name}")
        self._refresh()
        if msg[0] == "saved":
            if self.vars["open_after"].get():
                self.open_pdf()
        elif msg[0] == "stopped":
            self.say("Stopped. No file was written.")
        else:
            self.say(msg[1], err=True)

    def open_pdf(self):
        if self.out and Path(self.out).exists():
            try:
                os.startfile(self.out)  # Windows
            except OSError as e:
                self.say(f"Saved, but it could not be opened: {e}", err=True)

    def open_folder(self):
        if self.out and Path(self.out).parent.exists():
            os.startfile(Path(self.out).parent)  # Windows

    def stop_action(self):
        if self.busy == "render":
            self.stop.set()

    # ------------------------------------------------------------------ the sheets
    def _counts(self):
        return [c.copies for c in self.items]

    def _cards(self, original=False):
        """One entry per card in print order: the cover's preview picture, or its original bytes."""
        covers = [c.original() if original else c.shown() for c in self.items]
        return ac.expand(covers, self._counts())

    def _refresh(self):
        """Counts, the list's wording, the buttons, the preview and the strip."""
        self._sync()
        self._first, n_cards = self._positions()
        per = len(self.tpl.slots) if self.tpl else 8
        n_items = len(self.items)
        sheets = ac.sheet_count(n_cards, self.tpl) if self.tpl else 0
        blank = (sheets * per - n_cards) if sheets else 0
        if self.busy == "load":
            pass
        elif not n_items:
            self.s1.set_summary("Add comics or cover images to begin")
        else:
            copies = f" · {n_cards} cards" if n_cards != n_items else ""
            self.s1.set_summary(f"{_plural(n_items, 'cover')}{copies} on {_plural(sheets, 'sheet')}"
                                + (f" ({_plural(blank, 'empty slot')})" if blank else ""))
        self.meta = self.s1.summary
        self.sheet = max(0, min(self.sheet, sheets - 1))
        if self.busy != "render":
            self.s2.set_summary(f"Sheet {self.sheet + 1} of {sheets}" if sheets else "")
        o = self._opts()
        fit = FIT_TITLES[ac.FITS.index(o["fit"])] if o["fit"] in ac.FITS else o["fit"]
        self.s3.set_summary(f"{fit} · outlines {'on' if o['outlines'] else 'off'}")
        if not n_cards:
            self.note.configure(text="Add comics or cover images to see the sheets.", text_color=MUTED)
        elif blank:
            self.note.configure(text=f"The last sheet has {_plural(blank, 'empty slot')}. Add {blank} more "
                                f"cover{'s' if blank != 1 else ''} (or copies) to fill it.", text_color=TEXT)
        else:
            self.note.configure(text="Every slot on the last sheet is filled.", text_color=MUTED)
        self.cards.refresh()
        self._refresh_buttons()
        self.btn_full.configure(state="normal" if sheets and self.tpl else "disabled")
        self.btn_prev.configure(state="normal" if self.sheet > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.sheet < sheets - 1 else "disabled")
        self.lbl_sheet.configure(text=f"Sheet {self.sheet + 1} of {sheets}" if sheets else "No sheets yet")
        self._footer(n_items)
        self._schedule_preview()
        self._draw_strip()
        self._full_draw()
        first = self.items[0].iid if self.items else None
        if first != self._sample:
            self._sample = first
            self._pictures_soon()

    def _refresh_buttons(self):
        idle = not self.busy
        n = len(self.items)
        for key in ("top", "up", "down", "bottom", "remove", "clear"):
            self.tools[key].configure(state="normal" if idle and n else "disabled")
        self.tools["undo"].configure(state="normal" if idle and self.cards.can_undo else "disabled")

    def _footer(self, n_items):
        have_pdf = bool(self.out and Path(self.out).exists())
        side = [("Open PDF", self.open_pdf), ("Open folder", self.open_folder)] if have_pdf and not self.busy else []
        if self.busy == "render":
            self.set_footer(self.s2.summary.cget("text") or "Making the sheets…", "Stop", self.stop.set, secondary=[])
        elif self.busy == "load":
            self.set_footer("Reading the covers…", "Create PDF", self.create, enabled=False)
        elif not n_items:
            self.set_footer("Add comics or cover images to begin.", "Create PDF", self.create, enabled=False)
        elif self.tpl is None:
            self.set_footer("The template cannot be used.", "Create PDF", self.create, enabled=False)
        else:
            sheets = ac.sheet_count(sum(self._counts()), self.tpl)
            self.set_footer(f"{_plural(sheets, 'sheet')} ready.", "Create PDF", self.create, secondary=side)

    def _go(self, delta):
        self.sheet += delta
        self._refresh()

    def _goto(self, k):
        if k != self.sheet:
            self.sheet = k
            self._refresh()

    # ------------------------------------------------------------------ the sheet on show
    @staticmethod
    def _scaling(widget):
        """The display scaling CustomTkinter applies to images (1.25 on a 125% screen)."""
        try:
            return float(widget._get_widget_scaling())
        except Exception:  # noqa: BLE001 - fall back to no correction
            return 1.0

    def _marks(self):
        """The slots on the sheet on show whose card belongs to a selected cover."""
        if not self.tpl:
            return set()
        owners = ac.card_owners(self._counts())
        per = len(self.tpl.slots)
        sel = {self.items.index(self.by_iid[i]) for i in self.cards.sel if i in self.by_iid and self.by_iid[i] in self.items}
        return {k for k in range(per) if self.sheet * per + k < len(owners) and owners[self.sheet * per + k] in sel}

    def _sheet_image(self, size_px, use_originals=False, marks=(), dashed=True):
        """The current sheet as a picture no bigger than `size_px`, and the pixels per point it was drawn at."""
        o = self._opts()
        sheets = ac.chunk(self._cards(use_originals), self.tpl)
        group = sheets[self.sheet] if sheets else [None] * len(self.tpl.slots)
        w, h = size_px
        scale = min(w / self.tpl.width, h / self.tpl.height)  # pixels per point
        page = ac.compose_sheet(self.tpl, group, o, max(24, scale * 72), outlines_in_image=o["outlines"] or not sheets,
                                empty_style="dashed" if dashed else None, marks=marks)
        return page, scale

    def _schedule_preview(self):
        """A quick low-resolution sheet right away, the sharp one when nothing has changed for a moment."""
        if self.tpl is None:
            self._draw_preview(sharp=True)
            return
        self._draw_preview(sharp=False)
        if self._sharp:
            self.after_cancel(self._sharp)
        self._sharp = self.after(180, lambda: self._draw_preview(sharp=True))

    def _draw_preview(self, sharp=True):
        self._sharp = None if sharp else self._sharp
        v = self.view
        if not v.winfo_exists():
            return
        v.delete("all")
        w, h = max(120, v.winfo_width() - 8), max(160, v.winfo_height() - 8)
        if self.tpl is None:
            v.create_text(w / 2, h / 2, text="No usable template", fill=pick(MUTED), font=(FONT, 13, "bold"))
            return
        size = (w, h) if sharp else (max(60, w // 3), max(80, h // 3))
        shown, scale = self._sheet_image(size, marks=self._marks())
        if not sharp:
            shown = shown.resize((round(self.tpl.width * min(w / self.tpl.width, h / self.tpl.height)),
                                  round(self.tpl.height * min(w / self.tpl.width, h / self.tpl.height))), Image.BILINEAR)
            scale = min(w / self.tpl.width, h / self.tpl.height)
        self._photo = ImageTk.PhotoImage(shown, master=v)
        ox, oy = (v.winfo_width() - shown.width) // 2, (v.winfo_height() - shown.height) // 2
        v.create_image(ox, oy, image=self._photo, anchor="nw")
        self._geom = (ox, oy, scale)

    # ---- swapping cards in the preview
    def _slot_at(self, x, y):
        """The slot number on the sheet on show at a point of the preview, or None."""
        if not self._geom or not self.tpl:
            return None
        ox, oy, s = self._geom
        for k, slot in enumerate(self.tpl.slots):
            if ox + slot.x * s <= x <= ox + (slot.x + slot.w) * s and oy + slot.y * s <= y <= oy + (slot.y + slot.h) * s:
                return k
        return None

    def _cover_at_slot(self, k):
        """The cover printed in slot k of the sheet on show, or None for an empty slot."""
        owners = ac.card_owners(self._counts())
        pos = self.sheet * len(self.tpl.slots) + k
        return self.items[owners[pos]] if 0 <= pos < len(owners) else None

    def _vpress(self, e):
        self.view.focus_set()
        k = self._slot_at(e.x, e.y)
        cover = self._cover_at_slot(k) if k is not None else None
        self._drag = None
        if cover is None or self.busy:
            return
        self.cards.select([cover.iid])
        self.cards.see(cover.iid)
        self._drag = {"cover": cover, "x": e.x, "y": e.y, "moved": False}
        self._schedule_preview()

    def _vmotion(self, e):
        d = self._drag
        if not d:
            return
        if not d["moved"]:
            if abs(e.x - d["x"]) + abs(e.y - d["y"]) < DRAG_PX:
                return
            d["moved"] = True
            self.view.configure(cursor="fleur")
        # hold the card over a sheet in the strip to go to that sheet
        sx, sy = self.strip.winfo_rootx(), self.strip.winfo_rooty()
        if sx <= e.x_root <= sx + self.strip.winfo_width() and sy <= e.y_root <= sy + self.strip.winfo_height():
            k = self._strip_index(self.strip.canvasx(e.x_root - sx))
            if k is not None and k != self.sheet:
                self.sheet = k
                self._refresh()
            return
        self.view.delete("drag")
        k = self._slot_at(e.x, e.y)
        if k is not None and self._geom:
            ox, oy, s = self._geom
            slot = self.tpl.slots[k]
            target = self._cover_at_slot(k)
            color = pick(PINK) if target is not None and target is not d["cover"] else pick(MUTED)
            self.view.create_rectangle(ox + slot.x * s, oy + slot.y * s, ox + (slot.x + slot.w) * s, oy + (slot.y + slot.h) * s,
                                       outline=color, width=4, dash=(6, 3), tags="drag")
            d["target"] = target

    def _vrelease(self, e):
        d, self._drag = self._drag, None
        self.view.configure(cursor="")
        self.view.delete("drag")
        if not d or not d["moved"]:
            return
        k = self._slot_at(e.x, e.y)
        target = self._cover_at_slot(k) if k is not None else None
        if target is not None and target is not d["cover"]:
            self.swap(d["cover"], target)

    def swap(self, a, b):
        """Put two covers in each other's places (they keep their own copies)."""
        order = list(self.cards.order)
        i, j = order.index(a.iid), order.index(b.iid)
        order[i], order[j] = order[j], order[i]
        self.cards.apply(order, flash=[a.iid, b.iid])

    # ---- the strip of sheets
    def _strip_index(self, canvas_x):
        n = ac.sheet_count(sum(self._counts()), self.tpl) if self.tpl else 0
        step = self.strip_step()
        k = int(canvas_x // step)
        return k if 0 <= k < n else None

    def strip_step(self):
        return self.cards.u(STRIP_W + 10)

    def _strip_click(self, e):
        k = self._strip_index(self.strip.canvasx(e.x))
        if k is not None:
            self._goto(k)

    def _draw_strip(self):
        """A small picture of every sheet, in a row that scrolls; the one on show is outlined."""
        s = self.strip
        if not s.winfo_exists():
            return
        s.delete("all")
        self._strip_photos = []
        if not self.tpl or not self.items:
            s.configure(scrollregion=(0, 0, 1, 1))
            return
        n = ac.sheet_count(sum(self._counts()), self.tpl)
        u = self.cards.u
        tw = u(STRIP_W)
        th = round(tw * self.tpl.height / self.tpl.width)
        s.configure(height=th + u(30))
        groups = ac.chunk(self._cards(), self.tpl)
        o = self._opts()
        marks = [(c.iid, c.use_back and c.can_back) for c in self.items]
        sig = tuple(sorted((k, str(v)) for k, v in o.items() if k != "dpi"))
        per = len(self.tpl.slots)
        owners = ac.card_owners(self._counts())
        for k in range(n):
            key = (tuple(marks[owners[i]] for i in range(k * per, min(len(owners), (k + 1) * per))), sig)
            img = self._strip_cache.get(key)
            if img is None:
                if len(self._strip_cache) > 200:
                    self._strip_cache.clear()
                img = ac.compose_sheet(self.tpl, groups[k], o, 72 * tw / self.tpl.width, outlines_in_image=True,
                                       empty_style="dashed")
                self._strip_cache[key] = img
            photo = ImageTk.PhotoImage(img, master=s)
            self._strip_photos.append(photo)
            x = k * self.strip_step() + u(4)
            s.create_image(x, u(4), image=photo, anchor="nw")
            on = k == self.sheet
            s.create_rectangle(x - 2, u(4) - 2, x + img.width + 1, u(4) + img.height + 1, outline=pick(FOCUS) if on else pick(BORDER),
                               width=3 if on else 1)
            s.create_text(x + img.width / 2, u(4) + img.height + u(10), text=str(k + 1), fill=pick(TEXT), font=(FONT, 10, "bold"))
        s.configure(scrollregion=(0, 0, n * self.strip_step() + u(4), th + u(30)))

    # ------------------------------------------------------------------ the pictures on the option cards
    def _pictures_soon(self):
        if self._pics_after:
            self.after_cancel(self._pics_after)
        self._pics_after = self.after(120, self._pictures)

    def _pictures(self):
        """Redraw the small pictures on the option cards, using the first cover (or a made-up one) and the other options."""
        self._pics_after = None
        sample = self.items[0].shown() if self.items else ac.sample_cover()
        o = self._opts()
        for value in ac.FITS:
            self.fit_cards.set_picture(value, ac.card_picture(sample, {**o, "fit": value}, tpl=self.tpl))
        for value in ac.ROTATIONS:
            self.turn_cards.set_picture(value, ac.card_picture(sample, {**o, "rotate": value}, tpl=self.tpl))
        for value in ac.BACKGROUNDS:   # (shown with the cover fitted inside, so the colour round it can be seen)
            self.bg_cards.set_picture(value, ac.card_picture(sample, {**o, "background": value, "fit": ac.FITS[1]}, tpl=self.tpl))
        for value, _title in MARGINS:
            self.margin_cards.set_picture(value, ac.card_picture(sample, {**o, "inset": float(value)}, tpl=self.tpl))

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
        sheets = ac.sheet_count(sum(self._counts()), self.tpl)
        self._f_label.configure(text=f"Sheet {self.sheet + 1} of {sheets}")
        self._f_prev.configure(state="normal" if self.sheet > 0 else "disabled")
        self._f_next.configure(state="normal" if self.sheet < sheets - 1 else "disabled")
        k = self._scaling(self._f_image)
        w = max(200, self._f_image.winfo_width() - 8)
        h = max(200, self._f_image.winfo_height() - 8)
        shown, _ = self._sheet_image((w, h), use_originals=True, dashed=False)
        self._f_photo = ctk.CTkImage(light_image=shown, dark_image=shown, size=(shown.width / k, shown.height / k))
        self._f_image.configure(image=self._f_photo, text="")
