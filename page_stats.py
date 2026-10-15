"""Library stats page: scan a library once and see it as a dashboard (totals, bars per series, publisher, year and format,
metadata health, the biggest files), then a short list of what needs attention. Click a bar to list the comics behind it
in a side drawer. Folders marked as reading orders are counted apart. Nothing here changes a file."""
import csv
import os
import queue
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, font as tkfont

import customtkinter as ctk

import stats_core as sc
from flow_kit import Advanced, LazyTable, SegmentPage, section
from library_scan import scan_library
from reading_orders import ReadingOrders, suggest
from ui_kit import (ACCENT, ACCENT_TEXT, BG, BORDER, EDGE, FONT, MUTED, PANEL, RAISED, SELECT_BG, TEXT,
                    TYPE_BODY, TYPE_HINT, TYPE_SEGMENT, Toggle, pick, popup_menu, switch_style, tool_button)

EXPORTS = ["Series", "Publishers", "Years", "Formats", "Coverage", "Largest"]
ROW = 32  # height of one bar row, in pixels
FIX_W = 84  # width of the "Fix these" link at the end of a Health row
FIXABLE = {"Have ComicInfo.xml": "no_comicinfo", "Have a year": "no_year", "Have a publisher": "no_publisher",
           "Have an issue number": "no_issue"}  # Health row -> the Metadata view that lists what is missing


@dataclass
class Item:
    """One bar: its label, how long it is (0 to 1), the text at its end and the comics behind it. `fix` is the text of
    a link at the end of the row (Health rows that have something to fix)."""
    label: str
    frac: float
    text: str
    issues: list = field(default_factory=list)
    fix: str = ""


def row_items(rows):
    # an "Other (n more)" bar lumps many rows together, so it must not set the scale for the real ones
    top = max((r.count for r in rows if not r.label.startswith("Other (")), default=0) or max((r.count for r in rows), default=1)
    return [Item(r.label, min(1.0, r.count / top), f"{r.count:,}  ·  {sc.human_size(r.bytes)}", r.issues) for r in rows]


def _run(q, root, o, stop):
    """Worker: scan the library. No Tk calls; any failure is reported instead of leaving the page waiting."""
    try:
        res = scan_library(root, o["recursive"], deep=o["deep"], include_other=False,
                           progress=lambda d, t, i: q.put(("prog", d, t)), stop=stop)
        q.put(("result", res))
    except Exception as e:  # noqa: BLE001
        q.put(("error", f"{type(e).__name__}: {e}"))


class BarChart(ctk.CTkFrame):
    """Horizontal bars on a canvas: label, bar, value (and a "Fix these" link on rows that have one). Clicking a bar
    that has comics behind it calls on_pick(chart, item); clicking a link calls on_fix(item). Every bar uses the one
    accent colour."""

    def __init__(self, parent, on_pick=None, on_fix=None, bg=BG):
        super().__init__(parent, fg_color=bg)
        self._chart_bg = bg
        self.canvas = tk.Canvas(self, height=ROW, highlightthickness=0, bd=0, cursor="arrow")
        self.canvas.pack(fill="x")
        self.items, self.on_pick, self.on_fix, self.selected, self.hover = [], on_pick, on_fix, None, None
        self._job = None
        self._font = None
        self.canvas.bind("<Configure>", lambda _: self._schedule())
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda _: self._set_hover(None))
        self.canvas.bind("<Button-1>", self._click)

    def set_items(self, items, selected=None):
        self.items, self.selected = items, selected
        self.draw()

    def _schedule(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(60, self.draw)

    def _fit(self, text, width):
        if self._font is None:
            self._font = tkfont.Font(family=FONT, size=10)
        if self._font.measure(text) <= width:
            return text
        while text and self._font.measure(text + "…") > width:
            text = text[:-1]
        return text + "…"

    def draw(self):
        self._job = None
        c = self.canvas
        c.delete("all")
        c.configure(bg=pick(self._chart_bg), height=max(ROW, len(self.items) * ROW))
        w = max(c.winfo_width(), 320)
        label_w, value_w = min(240, int(w * 0.30)), min(190, int(w * 0.28))
        x0, x1 = label_w + 22, w - value_w - 12
        if not self.items:
            c.create_text(10, ROW // 2, text="Nothing to show.", anchor="w", fill=pick(MUTED), font=(FONT, 10))
            return
        for i, it in enumerate(self.items):
            y = i * ROW
            if i == self.selected:
                c.create_rectangle(0, y, w, y + ROW, fill=pick(SELECT_BG), outline="")
            elif i == self.hover:
                c.create_rectangle(0, y, w, y + ROW, fill=pick(PANEL), outline="")
            c.create_text(10, y + ROW // 2, text=self._fit(it.label, label_w - 10), anchor="w", fill=pick(TEXT),
                          font=(FONT, 10))
            c.create_rectangle(x0, y + 8, x0 + max(3, int((x1 - x0) * it.frac)), y + ROW - 8, fill=pick(ACCENT), outline="")
            right = w - 10
            if it.fix:
                c.create_text(right, y + ROW // 2, text=it.fix + " ›", anchor="e", fill=pick(ACCENT_TEXT),
                              font=(FONT, 10, "bold underline"))
                right -= FIX_W
            c.create_text(right, y + ROW // 2, text=it.text, anchor="e", fill=pick(MUTED), font=(FONT, 10))

    def _index(self, e):
        i = e.y // ROW
        return i if 0 <= i < len(self.items) else None

    def _clickable(self, i):
        return i is not None and self.on_pick is not None and bool(self.items[i].issues)

    def _over_fix(self, e):
        i = self._index(e)
        return i is not None and self.on_fix is not None and bool(self.items[i].fix) and e.x >= self.canvas.winfo_width() - FIX_W

    def _motion(self, e):
        i = self._index(e)
        self._set_hover(i if self._clickable(i) else None, hand=self._over_fix(e))

    def _set_hover(self, i, hand=False):
        if i != self.hover:
            self.hover = i
            self.draw()
        self.canvas.configure(cursor="hand2" if (i is not None or hand) else "arrow")

    def _click(self, e):
        i = self._index(e)
        if self._over_fix(e):
            self.on_fix(self.items[i])
        elif self._clickable(i):
            self.selected = i
            self.draw()
            self.on_pick(self, self.items[i])


class FolderBar(ctk.CTkFrame):
    """A slim one-line strip for the library folder: its path in small text, a Recent menu and a Change button.
    Dropping a folder on the page works too."""

    def __init__(self, parent, on_change, on_recent=None):
        super().__init__(parent, fg_color=PANEL, corner_radius=0, height=40)
        self.pack_propagate(False)
        self.prompt = "No library folder chosen"
        ctk.CTkLabel(self, text="Library folder", font=(FONT, 11, "bold"), text_color=MUTED).pack(side="left", padx=(12, 8))
        self.label = ctk.CTkLabel(self, text=self.prompt, font=(FONT, 12), text_color=MUTED, anchor="w")
        self.label.pack(side="left", fill="x", expand=True)
        self.button = tool_button(self, "Change…", on_change, 76)
        self.button.pack(side="right", padx=(0, 5))
        self.recent = None
        if on_recent:
            self.recent = tool_button(self, "Recent ▾", lambda: on_recent(self.recent), 88)
            self.recent.pack(side="right", padx=(0, 6))

    def set(self, text=None):
        if text and len(text) > 100:
            text = "…" + text[-99:]  # keep the end of a long path, which is the part that tells folders apart
        self.label.configure(text=text or self.prompt, text_color=TEXT if text else MUTED)


class Tile(ctk.CTkFrame):
    def __init__(self, parent, caption):
        super().__init__(parent, fg_color=RAISED, border_color=BORDER, border_width=3, corner_radius=0)
        self.value = ctk.CTkLabel(self, text="–", font=(FONT, 24, "bold"), text_color=TEXT, anchor="w")
        self.value.pack(fill="x", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text=caption, font=(FONT, 12), text_color=MUTED, anchor="w").pack(fill="x", padx=18, pady=(0, 16))

    def set(self, text):
        self.value.configure(text=text)


def _plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


class StatsPage(SegmentPage):
    title = "Library stats"
    subtitle = "See your whole collection at a glance. Nothing is changed."
    defaults = {"root": "", "recursive": True, "deep": False, "split": False, "decades": False, "show_all": False,
                "with_orders": False}
    max_width = 1180

    def __init__(self, parent):
        super().__init__(parent)
        self.orders = ReadingOrders()   # the app replaces this with the one it saves in settings.json
        self.recent_dirs = None         # the app gives a function returning the recent folders
        self.open_tool = None           # the app gives a function opening another tool on the library folder
        self.issues, self.stats, self.last = [], None, None
        self.real, self.order_issues, self.attn, self.suggestions = [], [], {}, []
        self.q = None
        self.stop = threading.Event()
        self.on_scanned = self.on_progress = self.on_error = None  # the app listens (Home summary line)
        self.charts, self.sections = {}, {}
        self.drill_from = None
        self.drawer_issues = []
        v = self.vars
        sw = switch_style()

        # ---- Library
        self.s1 = self.add_segment("Library")
        self.drop = FolderBar(self.s1.body, self.browse, self._recent_menu)
        self.drop.pack(fill="x", pady=(0, 10))
        self.meta = ctk.CTkLabel(self.s1.body, text="", font=TYPE_BODY, text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(0, 6))
        self.progress = ctk.CTkProgressBar(self.s1.body, height=14, corner_radius=0, border_width=3, border_color=BORDER,
                                           fg_color=BORDER, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.status = ctk.CTkLabel(self.s1.body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w")
        self.status.pack(fill="x", pady=(0, 8))
        self.scan_adv = Advanced(self.s1.body)
        self.scan_adv.pack(fill="x")
        Toggle(self.scan_adv.body, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        Toggle(self.scan_adv.body, text="Read page counts (slower)", variable=v["deep"], **sw).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(self.scan_adv.body, text="Adds total pages. Without it nothing inside an archive is opened except ComicInfo.xml.",
                     font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(4, 0))
        self.scan_adv.track(v, {"recursive": True, "deep": False})

        # ---- Overview
        self.s2 = self.add_segment("Overview")
        head = ctk.CTkFrame(self.s2.body, fg_color="transparent")
        head.pack(fill="x", pady=(0, 10))
        Toggle(head, text="Include reading orders in stats", variable=v["with_orders"], **sw).pack(side="left")
        self.left_out = ctk.CTkLabel(head, text="", font=TYPE_HINT, text_color=MUTED, anchor="w")
        self.left_out.pack(side="left", padx=(12, 0))
        self._build_dashboard()

        # ---- Needs attention
        self.s3 = self.add_segment("Needs attention")
        self.cards_box = ctk.CTkFrame(self.s3.body, fg_color="transparent")
        self.cards_box.pack(fill="x")
        self.card_texts = []

        # ---- the drawer a clicked bar opens at the right edge of the page
        self.drawer = ctk.CTkFrame(self, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0, width=470)
        bar = ctk.CTkFrame(self.drawer, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(14, 0))
        self.drawer_title = ctk.CTkLabel(bar, text="", font=TYPE_SEGMENT, text_color=TEXT, anchor="w", wraplength=240,
                                         justify="left")
        self.drawer_title.pack(side="left", fill="x", expand=True)
        tool_button(bar, "Close", self._close_drill, 64).pack(side="right")
        tool_button(bar, "Open folder", self._open_drilled, 100).pack(side="right", padx=(0, 6))
        self.drawer_table = LazyTable(self.drawer, [("file", "File", 220, True), ("series", "Series", 110, True),
                                                    ("year", "Year", 50, False), ("size", "Size", 70, False),
                                                    ("pages", "Pages", 52, False)], rows=17)
        self.drawer_table.pack(fill="both", expand=True, padx=14, pady=14)

        self.watch("split", "decades", callback=self._regroup)
        self.watch("show_all", callback=self.render)
        self.watch("with_orders", callback=self._regroup)
        self.watch("root", callback=self._root_changed)
        self._root_changed()
        self.render()

    # ------------------------------------------------------------------ dashboard
    def _build_dashboard(self):
        body = self.s2.body
        tiles = ctk.CTkFrame(body, fg_color=BG)
        tiles.pack(fill="x", pady=(4, 14))
        self.tiles = {}
        for i, (key, caption) in enumerate((("comics", "Comics"), ("series", "Series"), ("publishers", "Publishers"),
                                            ("bytes", "On disk"), ("average", "Average size"), ("pages", "Pages"))):
            tiles.columnconfigure(i, weight=1, uniform="tiles")
            t = Tile(tiles, caption)
            t.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 5 else 6))
            self.tiles[key] = t
        sw = switch_style()
        self.chart_adv = Advanced(body, "Chart options")
        self.chart_adv.pack(fill="x", pady=(0, 8))
        Toggle(self.chart_adv.body, text="Split series into volumes", variable=self.vars["split"], **sw).pack(anchor="w")
        Toggle(self.chart_adv.body, text="Group years into decades", variable=self.vars["decades"], **sw).pack(anchor="w", pady=(8, 0))
        Toggle(self.chart_adv.body, text="Show every bar (not just the top 15)", variable=self.vars["show_all"], **sw).pack(anchor="w", pady=(8, 0))
        self.chart_adv.track(self.vars, {"split": False, "decades": False, "show_all": False})

        section(body, "Collection").pack(fill="x", pady=(18, 0))
        for name, title in (("Series", "Comics per series"), ("Publishers", "Comics per publisher"),
                            ("Years", "Comics per year"), ("Formats", "File formats")):
            chart = BarChart(self._chart_box(body, title, name), self._pick, bg=RAISED)
            chart.pack(fill="x")
            self.charts[name] = chart
        section(body, "Health").pack(fill="x", pady=(30, 0))
        chart = BarChart(self._chart_box(body, "How complete the metadata is", "Coverage"), None, self._fix, bg=RAISED)
        chart.pack(fill="x")
        self.charts["Coverage"] = chart
        section(body, "Space").pack(fill="x", pady=(30, 0))
        box = self._chart_box(body, "Largest files", "Largest")
        self.big = LazyTable(box, [("file", "File", 460, True), ("size", "Size", 90, False), ("pages", "Pages", 70, False)],
                             rows=8, filterable=False)
        self.big.pack(fill="x")

        self.order_box = Advanced(body, "Reading orders")
        self.order_box.pack(fill="x", pady=(30, 0), padx=(0, 6))
        ctk.CTkLabel(self.order_box.body, text="Folders of reading-order copies. They are left out of the numbers above unless you "
                     "switch them in.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                     wraplength=680).pack(fill="x", pady=(0, 8))
        self.order_table = LazyTable(self.order_box.body, [("folder", "Folder", 420, True), ("comics", "Comics", 80, False),
                                                           ("size", "Size", 90, False)], rows=5, filterable=False)
        self.order_table.pack(fill="x")
        row = ctk.CTkFrame(self.order_box.body, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        tool_button(row, "Mark a folder…", self.mark_folder, 130).pack(side="left", padx=(0, 8))
        tool_button(row, "Unmark selected", self.unmark_selected, 140).pack(side="left")
        self.order_rows = []

    def _chart_box(self, parent, title, name):
        """A bordered card with room round its contents: a title, a small caption at the right, then the chart."""
        card = ctk.CTkFrame(parent, fg_color=RAISED, border_color=BORDER, border_width=EDGE, corner_radius=0)
        card.pack(fill="x", pady=(14, 0), padx=(0, 6))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(head, text=title, font=(FONT, 14, "bold"), text_color=TEXT, anchor="w").pack(side="left")
        cap = ctk.CTkLabel(head, text="", font=TYPE_HINT, text_color=MUTED, anchor="e")
        cap.pack(side="right")
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="x", padx=20, pady=(8, 18))
        self.sections[name] = (box, cap)
        return box

    def apply_theme(self):
        super().apply_theme()
        for chart in self.charts.values():
            chart.draw()
        for table in (self.big, self.drawer_table, self.order_table):
            table.apply_theme()

    # ------------------------------------------------------------------ folder and scan
    def browse(self):
        d = filedialog.askdirectory(title="Library folder")
        if d:
            self.set_folder(d)

    def _recent_menu(self, anchor):
        folders = self.recent_dirs() if self.recent_dirs else []
        items = [(f"{Path(p).name}    {str(Path(p).parent)[-40:]}", lambda p=p: self.set_folder(p)) for p in folders]
        popup_menu(anchor, items or [("No recent folders yet", None)])

    def set_folder(self, folder, scan=True):
        """Make this the library root (saved with the settings) and scan it."""
        if self.q:
            return
        self.vars["root"].set(str(folder))
        if scan:
            self.scan()

    def root(self):
        r = self.vars["root"].get().strip()
        return Path(r) if r and Path(r).is_dir() else None

    def _root_changed(self):
        r = self.vars["root"].get().strip()
        self.drop.set(r or None)
        self._sync()

    def scan(self):
        root = self.root()
        if self.q:
            return
        if not root:
            self.say("Choose a library folder first.", err=True)
            return
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self.say("")
        self.meta.configure(text="Scanning…")
        self._sync()
        threading.Thread(target=_run, args=(self.q, root, self.state(), self.stop), daemon=True).start()
        self._poll()

    def stop_action(self):
        if self.q:
            self.stop.set()

    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                if msg[0] == "prog":
                    self.progress.set(msg[1] / max(1, msg[2]))
                    text = f"Scanning {msg[1]:,} of {msg[2]:,}…"
                    self.meta.configure(text=text)
                    self.bar_text.configure(text=text)
                    if self.on_progress:
                        self.on_progress(msg[1], msg[2])
                elif msg[0] == "error":
                    self.q = None
                    self.progress.set(0)
                    self.meta.configure(text="")
                    self._sync()
                    self.say(f"Scan failed: {msg[1]}", err=True)
                    if self.on_error:
                        self.on_error(msg[1])
                    return
                else:
                    self._finish(msg[1])
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self, res):
        self.q = None
        self.issues = res.issues
        self.progress.set(0 if res.stopped else 1)
        self._compute()
        self.render()
        note = f"{len(res.issues):,} comics in {res.seconds:.1f}s" + (f" ({res.cache_hits:,} from cache)" if res.cache_hits else "")
        self.say(("Stopped, partial result · " if res.stopped else "Done · ") + note)
        if not res.stopped:
            self.last = self._snapshot()
            self.advance(self.s1)
        self._sync()
        if self.on_scanned:
            self.on_scanned(None if res.stopped else self.last)

    # ------------------------------------------------------------------ the numbers
    def _compute(self):
        """Sort the scanned comics into real ones and reading-order copies, and work out the stats and what needs a look."""
        o = self.state()
        self.real, self.order_issues = self.orders.split(self.issues)
        shown = self.issues if o["with_orders"] else self.real
        self.stats = sc.compute_stats(shown, o["split"], o["decades"])
        self.attn = sc.attention(self.real)
        root = self.root()
        self.suggestions = suggest(self.issues, self.orders, root) if root else []

    def _snapshot(self):
        return sc.snapshot(self.stats, self.root(), attention_count=self.attn.get("any_missing", 0))

    def _regroup(self):
        """A grouping or reading-order switch changed: redo the numbers from the scan already in hand."""
        if self.q or self.stats is None:  # nothing scanned yet (or a scan is running): nothing to regroup
            self.render()
            return
        self._compute()
        self.render()
        self._publish()

    def _publish(self):
        """Tell the app (Home's line) the numbers changed without a new scan."""
        if self.stats is not None and self.last is not None:
            self.last = self._snapshot()
            if self.on_scanned:
                self.on_scanned(self.last)

    def mark_folder(self):
        start = self.root()
        d = filedialog.askdirectory(title="Folder to mark as a reading order", initialdir=str(start) if start else None)
        if d:
            self._mark([d])

    def _mark(self, folders):
        for f in folders:
            self.orders.add(f)
        self._regroup()

    def unmark_selected(self):
        for i in self.order_table.selected():
            if 0 <= i < len(self.order_rows):
                self.orders.remove(self.order_rows[i])
        self._regroup()

    def _dismiss(self, folders):
        for f in folders:
            self.orders.dismiss(f)
        self._regroup()

    # ------------------------------------------------------------------ drawing the numbers
    def render(self):
        st = self.stats
        self._close_drill()
        if st is None:
            self.meta.configure(text="Choose your library folder, then press Scan library." if not self.root()
                                else "Press Scan library to begin.")
            for t in self.tiles.values():
                t.set("–")
            for name, chart in self.charts.items():
                chart.set_items([])
                self.sections[name][1].configure(text="")
            self.big.set_rows([])
            self.order_table.set_rows([])
            self.left_out.configure(text="")
            self.order_box.title = "Reading orders"
            self.order_box._paint()
            self._cards()
            self._sync()
            return
        all_bars = self.vars["show_all"].get()
        self.tiles["comics"].set(f"{st.comics:,}")
        self.tiles["series"].set(f"{st.series:,}")
        self.tiles["publishers"].set(f"{st.publishers:,}")
        self.tiles["bytes"].set(sc.human_size(st.bytes))
        self.tiles["average"].set(sc.human_size(st.average))
        self.tiles["pages"].set(f"{st.pages:,}" if st.pages is not None else "not read")
        for name in sc.SECTIONS:
            rows = st.sections[name]
            if name == "Years":
                shown = sc.years_view(rows, all_bars)
            else:
                ordered = sc._by_count(rows)
                shown = ordered if all_bars else sc.top_n(ordered)
            self.charts[name].set_items(row_items(shown))
            n = len([r for r in rows if r.label != sc.UNKNOWN])
            self.sections[name][1].configure(
                text=f"{n:,} in all" + ("" if all_bars or len(shown) == len(rows) else " · top 15 shown (Chart options: show every bar)"))
        cov = [Item(label, (n / of) if of else 0, f"{n:,} of {of:,}" + (f"  ·  {100 * n // of}%" if of else ""),
                    fix="Fix these" if label in FIXABLE and n < of else "")
               for label, n, of in sc.coverage_lines(st)]
        self.charts["Coverage"].set_items(cov)
        unread = st.coverage["unread"]
        self.sections["Coverage"][1].configure(
            text=f"{unread:,} real .cbr file{'s' if unread != 1 else ''} not opened" if unread else "")
        self.big.set_rows([(i.rel, sc.human_size(i.size), i.pages if i.pages is not None else "") for i in st.largest])
        # reading orders: what was left out (or included), and the folders themselves
        left = len(self.order_issues)
        folders = self.orders.folders
        if left:
            self.left_out.configure(text=(f"{_plural(left, 'reading-order comic')} included" if self.vars["with_orders"].get()
                                          else f"{_plural(left, 'reading-order comic')} left out"))
        else:
            self.left_out.configure(text="")
        self.order_box.title = f"Reading orders  ·  {_plural(left, 'comic')} in {_plural(len(folders), 'folder')}"
        self.order_box._paint()
        self.order_rows = folders
        counts = {f: [0, 0] for f in folders}
        for i in self.order_issues:
            f = self.orders.which(i.path)
            if f in counts:
                counts[f][0] += 1
                counts[f][1] += i.size
        self.order_table.set_rows([(f, f"{counts[f][0]:,}", sc.human_size(counts[f][1])) for f in folders])
        self.meta.configure(text=f"{st.comics:,} comics · {sc.human_size(st.bytes)} in {self.root() or self.vars['root'].get()}")
        self._cards()
        self._sync()

    # ------------------------------------------------------------------ what needs attention
    def _card(self, title, body, buttons, examples=""):
        """One thing that needs attention: a bold title, a plain description of what it means and what the button does,
        optionally a few example file names, and the buttons to deal with it."""
        f = ctk.CTkFrame(self.cards_box, fg_color=RAISED, border_color=BORDER, border_width=EDGE, corner_radius=0)
        f.pack(fill="x", pady=(0, 12), padx=(0, 6))
        side = ctk.CTkFrame(f, fg_color="transparent")
        side.pack(side="right", padx=(0, 16), pady=16, anchor="n")
        for label, cmd in buttons:
            tool_button(side, label, cmd, max(110, 28 + 8 * len(label))).pack(pady=(0, 8))
        words = ctk.CTkFrame(f, fg_color="transparent")
        words.pack(side="left", fill="x", expand=True, padx=20, pady=16)
        ctk.CTkLabel(words, text=title, font=(FONT, 14, "bold"), text_color=TEXT, anchor="w", justify="left",
                     wraplength=620).pack(fill="x")
        ctk.CTkLabel(words, text=body, font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                     wraplength=620).pack(fill="x", pady=(6, 0))
        if examples:
            ctk.CTkLabel(words, text=examples, font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                         wraplength=620).pack(fill="x", pady=(8, 0))
        self.card_texts.append(f"{title} {body} {examples}".strip())

    def _examples(self, missing):
        """'For example: A.cbz, B.cbz, C.cbz' from the real comics `missing(info)` is true for ('' when none)."""
        names = []
        for i in self.real:
            if missing(i.info):
                names.append(i.path.name)
                if len(names) == 3:
                    break
        return ("For example: " + ", ".join(names)) if names else ""

    def _cards(self):
        for w in self.cards_box.winfo_children():
            w.destroy()
        self.card_texts = []
        if self.stats is None:
            ctk.CTkLabel(self.cards_box, text="Scan your library to see what could be tidier.", font=TYPE_BODY,
                         text_color=MUTED, anchor="w").pack(fill="x")
            return
        a, n = self.attn, 0
        if self.suggestions:
            folders = [f for f, _c, _w in self.suggestions]
            names = ", ".join(f"{f.name} ({c})" for f, c, _why in self.suggestions[:3]) + ("…" if len(self.suggestions) > 3 else "")
            self._card(f"{_plural(len(folders), 'folder')} look{'s' if len(folders) == 1 else ''} like a reading order",
                       "Most comics in these folders have numbered names (01 - Name) or a story arc, which usually means copies "
                       "made to be read in order. If you mark them, they are counted apart, so your totals and your duplicate "
                       "checks are not doubled by them. Nothing is changed in the folders.",
                       [("Mark them", lambda: self._mark(folders)), ("Not these", lambda: self._dismiss(folders))],
                       f"Folders: {names}")
            n += 1
        missing = (
            ("no_publisher", "{} have no publisher",
             "The publisher is stored inside each comic (ComicInfo.xml). Without it the Publishers chart files these comics under "
             "Unknown and a reader such as YACReader cannot sort or filter them by publisher. Fix metadata opens the Metadata "
             "tool, where you can set a publisher for many comics at once.",
             lambda f: not f.get("publisher")),
            ("no_year", "{} have no year",
             "The year comes from ComicInfo.xml or from a year in the file name, such as (2016). Without it these comics sit "
             "under Unknown in the year chart and cannot be put in date order. Fix metadata opens the Metadata tool, where you "
             "can add the year, or read it from the file name.",
             lambda f: not str(f.get("year") or "").isdigit()),
            ("no_issue", "{} have no issue number",
             "A single issue needs a number, from ComicInfo.xml or the file name (Batman 012). Without one a reader sorts these "
             "comics by file name instead of issue order, and the Library audit cannot tell which issues of a series are missing. "
             "Fix metadata opens the Metadata tool to add them.",
             lambda f: not f.get("collected") and not f.get("issue")))
        for key, title, body, test in missing:
            if a.get(key):
                self._card(title.format(_plural(a[key], "comic")) + ".", body,
                           [("Fix metadata", lambda k=key: self._open("metadata", k))], self._examples(test))
                n += 1
        if a.get("duplicate_groups"):
            self._card(f"{_plural(a['duplicate_groups'], 'group')} of possible duplicates.",
                       "These comics share a series, a volume and an issue number, so they may be the same issue saved twice, in "
                       "another format or in another folder. This is a quick guess from the names. Open Library audit compares "
                       "file sizes and covers too, shows which copy is best, and can move the extras to Archive. Copies inside "
                       "marked reading-order folders are not counted.",
                       [("Open Library audit", lambda: self._open("audit"))])
            n += 1
        if not n:
            ctk.CTkLabel(self.cards_box, text="Nothing needs attention.", font=TYPE_BODY, text_color=MUTED,
                         anchor="w").pack(fill="x")
        self.attention_cards = n

    def _open(self, key, view=None):
        if self.open_tool:
            self.open_tool(key, view)
        else:
            self.say("That tool is not available here.", err=True)

    def _fix(self, item):
        """A Health row's link: open Metadata on the comics that lack that field."""
        self._open("metadata", FIXABLE.get(item.label, "attention"))

    # ------------------------------------------------------------------ segments and footer
    def _sync(self):
        busy, scanned = bool(self.q), self.stats is not None
        s1, s2, s3 = self.s1, self.s2, self.s3
        root = self.root()
        if not scanned:
            s1.set_state("active")
            s2.set_state("locked")
            s3.set_state("locked")
            s1.set_summary(str(root) if root else "")
            s2.set_summary("")
            s3.set_summary("")
        else:
            st = self.stats
            s1.set_state("done")
            s1.set_summary(f"{st.comics:,} comics · {self.root() or self.vars['root'].get()}")
            s2.set_state("idle")
            s2.set_summary(f"{st.series:,} series · {_plural(st.publishers, 'publisher')} · {sc.human_size(st.bytes)}")
            todo = getattr(self, "attention_cards", 0)
            s3.set_state("active" if todo else "done")
            s3.set_summary(f"{todo} to look at" if todo else "Nothing to fix")
        if busy:
            self.set_footer(self.meta.cget("text") or "Scanning…", "Stop", self.stop.set)
            return
        secondary = []
        if root:
            secondary.append(("Open library folder", self.open_root))
        if scanned:
            secondary += [("Export CSV…", self._export_menu, True), ("Copy summary", self.copy_summary)]
        self.set_footer(self.status.cget("text") or ("Press Scan library to begin." if root else "Choose your library folder."),
                        "Rescan library" if scanned else "Scan library", lambda: self.scan(), enabled=bool(root),
                        secondary=secondary)

    def say(self, msg, err=False):
        super().say(msg, err)
        if hasattr(self, "s3") and not self.q:
            self._sync()  # the footer repeats the latest message

    # ------------------------------------------------------------------ drilling into a bar
    def _pick(self, chart, item):
        for other in self.charts.values():
            if other is not chart:
                other.selected = None
                other.draw()
        self.drill_from = chart
        self.drawer_issues = sorted(item.issues, key=lambda i: i.rel.lower())
        rows = []
        for i in self.drawer_issues:
            f = i.info
            rows.append((i.rel, f.get("series") or "", f.get("year") or "", sc.human_size(i.size),
                         i.pages if i.pages is not None else ""))
        self.drawer_table.set_rows(rows)
        self.drawer_title.configure(text=f"{item.label} · {_plural(len(item.issues), 'comic')}")
        self.update_idletasks()
        # (customtkinter's own place() refuses a height, so go through tkinter's; the drawer covers the page down to the footer)
        tk.Frame.place_configure(self.drawer, relx=1.0, y=0, anchor="ne", relheight=1.0, height=-self.footer.winfo_height(),
                                 width=470)
        self.drawer.lift()

    def _close_drill(self):
        self.drawer.place_forget()
        if self.drill_from is not None:
            self.drill_from.selected = None
            self.drill_from.draw()
            self.drill_from = None

    def _open_drilled(self):
        sel = self.drawer_table.selected()
        issue = self.drawer_issues[sel[0]] if sel and sel[0] < len(self.drawer_issues) else (self.drawer_issues[0] if self.drawer_issues else None)
        if issue and issue.path.parent.exists():
            os.startfile(issue.path.parent)  # Windows

    def open_root(self):
        if self.root():
            os.startfile(self.root())  # Windows

    # ------------------------------------------------------------------ output
    def _export_menu(self, anchor):
        popup_menu(anchor, [(f"{name}…", lambda n=name: self.export_csv(n)) for name in EXPORTS], above=True)

    def export_csv(self, name):
        if not self.stats:
            return
        path = filedialog.asksaveasfilename(title=f"Export {name}", defaultextension=".csv",
                                            initialfile=f"stats-{name.lower()}.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        header, rows = sc.section_table(self.stats, name)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(rows)
            self.say(f"Exported {len(rows)} row{'s' if len(rows) != 1 else ''}.")
        except OSError as e:
            self.say(f"Could not save: {e}", err=True)

    def copy_summary(self):
        if not self.stats:
            return
        self.clipboard_clear()
        self.clipboard_append(sc.summary_text(self.stats, self.root()))
        self.say("Summary copied. Paste it anywhere.")
