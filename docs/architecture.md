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
| `comic_core.py` | Archive reading (`Comic`), cover rendering, output-path planning, shared constants |
| `rename_core.py` | Filename parsing (including the issue count), `ComicInfo.xml` reading, name templating |
| `archive_tools.py` | Verified zip rewriting: CBR to CBZ, clean-up, `ComicInfo.xml` stamping. `CI_TAGS` maps field names to XML tags and `merge_comicinfo` writes any of them, so new fields need only a `CI_TAGS` entry |
| `folder_icons.py` | `folder.ico` / `desktop.ini` / `folder.jpg` generation (Windows) |

Logic modules (`*_core.py`, `archive_tools.py`, `folder_icons.py`) contain no UI code so they can be tested or reused
from a command line later.
