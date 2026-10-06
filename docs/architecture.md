# Architecture and project layout

[< Docs index](README.md)

| File | Role |
|---|---|
| `comic_tool.py` | App shell: window, sidebar, Home cards, theme toggle, drag-and-drop routing, settings load/save |
| `ui_kit.py` | Shared look: (light, dark) palette, styled widgets, form rows, drop zone, page scaffold, table helpers |
| `batch_page.py` | Base page for run-per-item tools (progress, log, Preview, Stop) |
| `page_single.py` · `page_bulk.py` · `page_icons.py` | Cover extractor pages |
| `page_rename.py` | Renamer page |
| `page_metadata.py` | Metadata page |
| `page_convert.py` · `page_cleanup.py` | Archive tool pages |
| `page_audit.py` | Library audit page: scan worker, four report tables, CSV and wishlist export, move-to-Archive for duplicates |
| `comic_core.py` | Archive reading (`Comic`), cover rendering, output-path planning, shared constants |
| `rename_core.py` | Filename parsing (including the issue count), `ComicInfo.xml` reading, name templating |
| `archive_tools.py` | Verified zip rewriting: CBR to CBZ, clean-up, `ComicInfo.xml` stamping. `CI_TAGS` maps field names to XML tags and `merge_comicinfo` writes any of them, so new fields need only a `CI_TAGS` entry |
| `audit_core.py` | Audit logic: integrity checks, duplicate grouping, missing-issue gaps, quality flags, thresholds. Never changes a file |
| `library_scan.py` | Shared library scan: one `Issue` record per comic (name fields, `ComicInfo.xml` fields, and in deep mode page count, cover size and cover hash) with a disposable cache in `%APPDATA%\ComicToolkit\cache.json`. Also a command-line report. See below |
| `folder_icons.py` | `folder.ico` / `desktop.ini` / `folder.jpg` generation (Windows) |

Logic modules (`*_core.py`, `archive_tools.py`, `folder_icons.py`, `library_scan.py`, `audit_core.py`) contain no UI code so they can be tested or reused
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
- **Stop and progress:** `stop` is a `threading.Event` checked between files; `progress(done, total, issue)` is called after each file.
- **Command line:** `python library_scan.py FOLDER [--deep] [--deep-cbr] [--no-recursive] [--no-cache] [--cache-file F] [--csv F] [--limit N]`.
