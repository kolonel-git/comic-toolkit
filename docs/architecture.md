# Architecture and project layout

[< Docs index](README.md)

| File | Role |
|---|---|
| `comic_tool.py` | App shell: window, sidebar, Home cards, theme toggle, drag-and-drop routing, settings load/save |
| `ui_kit.py` | Shared look (and `FlowRow`, a row of widgets that wraps when it is too narrow, and a compact `DropZone`): neo-brutalist (light, dark) palette (`BG`, `INK`, `YELLOW`/`PINK`/`CYAN`, `ACCENT`), the `Shadow` hard-shadow wrapper, `AbstractStrip` shape bands, `IconTile`, canvas `Toggle` and `Slider`, styled widgets, form rows, drop zone (with Add folder / Choose comics buttons), `Splitter` (draggable divider), `toolbar` (grouped buttons with dividers), page scaffold with a resizable options panel, table helpers (resizable columns, horizontal scrollbar) |
| `batch_page.py` | Base page for run-per-item tools (progress, log, Preview, Stop) |
| `page_single.py` · `page_bulk.py` · `page_icons.py` | Cover extractor pages (Bulk folder and Single issue are built on the `flow_kit.py` shell; Single issue shares its picks with the picker window) |
| `flow_kit.py` | The shared page shell: `SegmentPage` (header, a scrolling column of `Segment`s (or, with `split = True`, a plain column a page fills with panes that scroll on their own) and a pinned footer set with `set_footer`, which only touches what changed (one slim bar, about 50 px, on every page); `advance` folds a finished segment and opens the next), `Segment` (states active / done / idle / locked, a one-line summary; it only repaints when something changed, and `on_open` lets a section catch up when opened), `Block` (the same small interface for a titled block of a column: nothing folds), `make_panes` / `add_block` / `fit_right` on `SegmentPage` (two columns with a draggable `Splitter`; the right one scrolls on its own, its width is saved as `_split_width` and the left one keeps `left_min`), `Advanced` (the shut block of rare settings; `track` counts changed ones), `LazyTable` (filterable table that loads rows as you scroll, `grow=True` to fill the height it is given, optional pictures per row loaded off the main thread), `ChoiceCards`, `section`, `facts`, `path_row`, `labelled` |
| `picker_core.py` · `picker_window.py` | Pick pages from a comic: grid layout, cover guessing, selection helpers and JPG extraction (no UI) · the thumbnail window (canvas grid, background loader thread, rubber band, reorder and full-view dialogs), opened from the Single issue page, which can start it with the picks so far and is told (`on_change`) when they change |
| `intake_core.py` · `page_intake.py` | Add to library: plan names, places, duplicates and steps (using the Renamer settings) and run convert, clean, verify and dispose of the original · the page (drop and inbox intake, review table, worker thread) |
| `page_rename.py` | Renamer page: card and list views, four settings tabs, per-type template editor, conflict handling |
| `metadata_core.py` | Metadata editing logic: `Row` (a comic with its pending edits), what is missing (`lacks`, `matches`, `FILTERS`), `fill_from_filename`, `changes` / `writes`, the offer to a series (`others_lacking`) and `SuggestIndex` (suggestions taken from the library). No UI code |
| `page_metadata.py` | Metadata page on the shell's two-column layout: comics table on the left; on the right (its own scroll) the one-comic and many-comics forms and the live list of pending changes with save (worker threads for reading and writing) |
| `page_convert.py` | CBR to CBZ page on the shell's two-column layout: the `.cbr` list and its background check on the left; the original / existing-`.cbz` cards, the advanced switches and the review with the run on the right |
| `page_order.py` | Reading order page on the shell's two-column layout: the issue list with drag and tick boxes on the left; Stamp, Review and the footer on the right; plan preview, write worker, copy mode, and marking the folder of copies as a reading order (the list shared with Library stats) |
| `page_aceo.py` | ACEO sheets page: cover list with ordering, sheet preview, options, PDF creation worker |
| `page_audit.py` | Library audit page on the segment shell (Library, Checks, Findings): scan and fix workers, the summary strip, type chips (and a Reading orders chip) over one lazy findings table, the Details panel placed over the right half of the page, tick and Fix N checked behind a confirmation with a file-by-file Details list, Ignore list (JSON in the `ignored` setting), Ignored and Archive dialogs, wishlist. The app gives it the shared `ReadingOrders` and a function that opens other tools |
| `comic_core.py` | Archive reading (`Comic`), cover rendering, output-path planning, shared constants; `picked_files` / `common_root` for the Choose comics buttons |
| `rename_core.py` | Filename parsing (years in any brackets, year-like volumes, issue count, collected-edition format, volume, range, tags, series cleanup), type override and hand edits, `ComicInfo.xml` reading, file search and rename |
| `name_format.py` | Naming: per-type templates and presets, tokens, token formats, fallbacks, escapes, template validation, text options, folder templates, the in-app format guide |
| `archive_tools.py` | Verified zip rewriting: CBR to CBZ (`convert_to_cbz`, and `convert_one`, which also tidies the `.part` file before it takes its place), clean-up, `ComicInfo.xml` stamping. `CI_TAGS` maps field names to XML tags and `merge_comicinfo` writes any of them, so new fields need only a `CI_TAGS` entry |
| `reading_order.py` | Reading-order logic: ordering key, ComicInfo field mapping (story arc / alternate series), per-issue plan, the sort keys for *Suggest order* (series, publication date, issue number, file name), block moves (from `blocks.py`), preview text, in-place or copy write with optional filename prefix |
| `aceo_core.py` | ACEO sheets: reads the card slots from a template PDF, loads covers from comics or images, fits them into the slots, renders each page and draws the template's card outlines on top in the chosen colour and thickness (`pypdf` and Pillow) |
| `stats_core.py` | Library statistics: `compute_stats` over `Issue` records (totals, groups per series, publisher, year and format, metadata coverage, largest and smallest files), top-N with an *Other* row, summary text, CSV tables, the Home snapshot. No UI code |
| `page_stats.py` | Library stats page on the segment shell: scan worker, tiles, `BarChart` (canvas bars with hover, click and a *Fix these* link), the side drawer, reading-order section, Needs attention cards, CSV export and summary copy |
| `blocks.py` | Moving a block of selected items inside an ordered list (up or down, to an edge, to a gap, to a position). No UI code |
| `cardlist.py` | The card list: one card per item on a canvas (only the visible ones are drawn), picked up and dragged anywhere, selected with click, Ctrl, Shift or a box; a stacked drag card with a count, a drop line, scrolling near the edges, Alt+Up / Alt+Down and the other keys, Ctrl+Z and undo. Used by Reading order; ACEO is next |
| `reading_orders.py` | The marked reading-order folders (`ReadingOrders`: add, remove, `covers`, `which`, `split`, saved in settings.json) and the guess at which folders look like one (`suggest`). No UI code |
| `audit_core.py` | Audit logic: integrity checks, type-aware duplicate grouping with a best-copy keeper (`duplicates_for` leaves reading-order copies out and an outside copy always outranks one inside), missing gaps per type, warning limits, junk and CBR findings, `reading_order_rows`, `build_findings`, `plan_fixes` / `plan_lines` / `describe_plan` / `apply_fix` (the only code that changes files), `build_details` (the data behind the Details panel), Archive folder listing and purge |
| `library_scan.py` | Shared library scan: one `Issue` record per comic (name fields, `ComicInfo.xml` fields, and in deep mode page count, cover size and cover hash) with a disposable cache in `%APPDATA%\ComicToolkit\cache.json`. Also a command-line report. See below |
| `tests/` | Test scripts and `run_all.py` (`python tests/run_all.py`); see `tests/README.md` |
| `folder_icons.py` | `folder.ico` / `desktop.ini` / `folder.jpg` generation (Windows) |

Logic modules (`*_core.py`, `archive_tools.py`, `folder_icons.py`, `library_scan.py`, `audit_core.py`, `stats_core.py`, `metadata_core.py`, `reading_orders.py`, `reading_order.py`, `blocks.py`, `name_format.py`, `aceo_core.py`) contain no UI code so they can be tested or reused
from a command line.

## The library scan

`scan_library(root, recursive, deep, deep_cbr, include_other, use_cache, cache_path, progress, stop)` returns a `ScanResult` whose `issues`
are `Issue` records. Tools should call it from a worker thread and read the records instead of walking the library themselves.

- **Light scan** (default): size, modified time, fields parsed from the filename, and `ComicInfo.xml` for zip-based files. Real RAR files are
  not opened, so their `ci_read` is `False`, which means "unknown", not "empty".
- **Deep scan**: also page count, cover width and height, and a 64-bit difference hash of the cover (`cover_hash`, 16 hex characters;
  `hash_distance` counts differing bits, so 0 is identical and small numbers mean the same cover re-encoded). Errors found on the way
  (`Not a valid zip`, `No images found`, `Cover unreadable`) are stored in `Issue.error`. Real RAR files are opened only with `deep_cbr`.
  Deep mode reads the first page, not the whole archive, so it does not replace a full integrity test.
- **`Issue.info`** is the filename fields overridden by `ComicInfo.xml`, the same rule the Renamer uses.
- **Cache:** entries are keyed by lower-cased path and reused only when size and modified time match and the entry holds what the scan asks
  for (a light entry never answers a deep scan). Entries for deleted files under the scanned root are dropped, a corrupt or version-mismatched
  cache is ignored, and a cache that can't be written is silently skipped. Parsed filename fields are never cached, so parser fixes apply at once.
- **Picked files:** `only=[files]` scans exactly those files (they must lie inside `root`) and skips the cache clean-up, so the cache entries of the other files in the folder are kept.
- **Stop and progress:** `stop` is a `threading.Event` checked between files; `progress(done, total, issue)` is called after each file.
- **Command line:** `python library_scan.py FOLDER [--deep] [--deep-cbr] [--no-recursive] [--no-cache] [--cache-file F] [--csv F] [--limit N]`.
