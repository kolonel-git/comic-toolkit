# Architecture and project layout

[< Docs index](README.md)

| File | Role |
|---|---|
| `comic_tool.py` | App shell: window, sidebar, Home cards, theme toggle, drag-and-drop routing, settings load/save |
| `ui_kit.py` | Shared look: neo-brutalist (light, dark) palette (`BG`, `INK`, `YELLOW`/`PINK`/`CYAN`, `ACCENT`), the `Shadow` hard-shadow wrapper, `AbstractStrip` shape bands, `IconTile`, canvas `Toggle` and `Slider`, styled widgets, form rows, drop zone (with Add folder / Choose comics buttons), `Splitter` (draggable divider), `toolbar` (grouped buttons with dividers), page scaffold with a resizable options panel, table helpers (resizable columns, horizontal scrollbar) |
| `batch_page.py` | Base page for run-per-item tools (progress, log, Preview, Stop) |
| `page_single.py` · `page_bulk.py` · `page_icons.py` | Cover extractor pages (Bulk folder is the first page built on the `flow_kit.py` shell) |
| `flow_kit.py` | The shared page shell: `SegmentPage` (header, a scrolling column of `Segment`s and a pinned footer set with `set_footer`; `advance` folds a finished segment and opens the next), `Segment` (states active / done / idle / locked, a one-line summary), `Advanced` (the shut block of rare settings; `track` counts changed ones), `LazyTable` (filterable table that loads rows as you scroll, optional pictures per row loaded off the main thread), `ChoiceCards`, `section`, `facts`, `path_row`, `labelled` |
| `picker_core.py` · `picker_window.py` | Pick pages from a comic: grid layout, cover guessing, selection helpers and JPG extraction (no UI) · the thumbnail window (canvas grid, background loader thread, rubber band, reorder and full-view dialogs), opened from the Single issue page |
| `intake_core.py` · `page_intake.py` | Add to library: plan names, places, duplicates and steps (using the Renamer settings) and run convert, clean, verify and dispose of the original · the page (drop and inbox intake, review table, worker thread) |
| `page_rename.py` | Renamer page: card and list views, four settings tabs, per-type template editor, conflict handling |
| `page_metadata.py` | Metadata page |
| `page_convert.py` | CBR to CBZ page |
| `page_order.py` | Reading order page: issue list with drag and tick boxes, plan preview, write worker, copy mode |
| `page_aceo.py` | ACEO sheets page: cover list with ordering, sheet preview, options, PDF creation worker |
| `page_audit.py` | Library audit page: scan and fix workers, type chips over one findings list, tick and Fix checked, Ignore list (JSON in the `ignored` setting), Ignored and Archive dialogs, wishlist |
| `comic_core.py` | Archive reading (`Comic`), cover rendering, output-path planning, shared constants; `picked_files` / `common_root` for the Choose comics buttons |
| `rename_core.py` | Filename parsing (years in any brackets, year-like volumes, issue count, collected-edition format, volume, range, tags, series cleanup), type override and hand edits, `ComicInfo.xml` reading, file search and rename |
| `name_format.py` | Naming: per-type templates and presets, tokens, token formats, fallbacks, escapes, template validation, text options, folder templates, the in-app format guide |
| `archive_tools.py` | Verified zip rewriting: CBR to CBZ, clean-up, `ComicInfo.xml` stamping. `CI_TAGS` maps field names to XML tags and `merge_comicinfo` writes any of them, so new fields need only a `CI_TAGS` entry |
| `reading_order.py` | Reading-order logic: ordering key, ComicInfo field mapping (story arc / alternate series), per-issue plan, block moves and send-to-top/bottom for multi-selection, preview text, in-place or copy write with optional filename prefix |
| `aceo_core.py` | ACEO sheets: reads the card slots from a template PDF, loads covers from comics or images, fits them into the slots, renders each page and draws the template's card outlines on top in the chosen colour and thickness (`pypdf` and Pillow) |
| `stats_core.py` | Library statistics: `compute_stats` over `Issue` records (totals, groups per series, publisher, year and format, metadata coverage, largest and smallest files), top-N with an *Other* row, summary text, CSV tables, the Home snapshot. No UI code |
| `page_stats.py` | Library stats page: scan worker, tiles, `BarChart` (canvas bars with hover and click), drill-down table, CSV export and summary copy |
| `audit_core.py` | Audit logic: integrity checks, type-aware duplicate grouping with a best-copy keeper, missing gaps per type, warning limits, junk and CBR findings, `build_findings`, `plan_fixes` / `apply_fix` (the only code that changes files), Archive folder listing and purge |
| `library_scan.py` | Shared library scan: one `Issue` record per comic (name fields, `ComicInfo.xml` fields, and in deep mode page count, cover size and cover hash) with a disposable cache in `%APPDATA%\ComicToolkit\cache.json`. Also a command-line report. See below |
| `tests/` | Test scripts and `run_all.py` (`python tests/run_all.py`); see `tests/README.md` |
| `folder_icons.py` | `folder.ico` / `desktop.ini` / `folder.jpg` generation (Windows) |

Logic modules (`*_core.py`, `archive_tools.py`, `folder_icons.py`, `library_scan.py`, `audit_core.py`, `stats_core.py`, `reading_order.py`, `name_format.py`, `aceo_core.py`) contain no UI code so they can be tested or reused
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
