# Comic Toolkit

A desktop app for managing a personal, local library of comic files (`.cbz`, `.cbr`, plus `.pdf` / `.epub` for renaming).
It prepares a library for a reader such as **YACReader**: it does not read comics itself, and it deliberately keeps no
database. Everything works on the files and folders on disk.

- **Platform:** Windows 10/11 (a few features are Windows-only, noted below)
- **Language / UI:** Python 3, [customtkinter](https://github.com/TomSchimansky/CustomTkinter), Notion-style light and dark themes
- **Status:** active development. See [CHANGELOG.md](CHANGELOG.md) for history and [Roadmap](#roadmap) for what's next

---

## Quick start

```
pip install customtkinter tkinterdnd2 pillow
python comic_tool.py
```

Tested on Python 3.14 (Windows 11). Python 3.9+ is required (`xml.etree.ElementTree.indent`).

**For `.cbr` (RAR) files** you need one RAR-capable extractor on the machine. The app looks for, in order:
`7z` / `7za` / `unrar` on PATH, 7-Zip in `C:\Program Files\7-Zip`, then Windows' built-in `tar.exe` (bsdtar reads RAR).
Some `.cbr` files are really zips and need no extractor.

---

## The tools

The Home page groups the tools as cards; the sidebar mirrors the same groups. A **Dark mode** switch sits at the bottom of
the sidebar (first launch follows Windows; your choice is remembered).

### Comic Cover Extractor

| Tool | What it does |
|---|---|
| **Single issue** | Drop in one comic. Preview the cover and first 3 pages and the last 3 pages. Save the cover (format, quality, max height, destination, file name, conflict handling), or convert the comic to a ZIP. |
| **Bulk folder** | Extract the cover from every CBZ/CBR in a folder. Choose subfolders on or off; save into a named subfolder, a folder you choose, or beside each comic; organise as one folder, mirrored folders, or grouped by series name; JPG/PNG/WebP/original, quality, size, file name, overwrite/skip/keep-both. Shows a live example path, progress, a per-file log, and a Stop button. |
| **Folder icons** | Make each series folder show its cover in Windows Explorer: builds `folder.ico`, writes `desktop.ini`, sets the Windows attributes Explorer needs, and optionally saves `folder.jpg`. Cover from first or last issue. **Custom image for a folder…** lets you pick any folder (e.g. a `DC` or `Marvel` parent) and any image. Windows only. |

### Comic Renamer

| Tool | What it does |
|---|---|
| **Renamer** | Standardise file names across a folder (CBZ, CBR, PDF, EPUB; subfolders optional). Parses the filename, and optionally `ComicInfo.xml`, which wins when present. Pick a naming style from 8 presets or write a custom template, set issue-number padding and series capitalisation, optionally move files into series folders. A preview table shows old and new names with statuses; tick rows, double-click a new name to edit it, then apply. Nothing changes on disk until you confirm. |

**Naming presets**

`Series 001 (2016)` · `Series #001 (2016)` · `Series v2 001 (2016)` · `Series Vol 2 #001 (2016)` ·
`Series - 001 - Title (2016)` · `Series 001 - Title` · `Series (2016) 001` · `Series 001`

**Custom templates** use the tokens `{series}` `{volume}` `{issue}` `{year}` `{title}`. Wrap optional parts in `[ ]`:
the whole group disappears when any value inside it is empty, e.g. `{series}[ v{volume}][ #{issue}][ ({year})]`.

### Metadata

| Tool | What it does |
|---|---|
| **Metadata** | Stamp series, issue number, volume, year and title from filenames into each CBZ's `ComicInfo.xml` (the file YACReader and most readers use). Review table with inline editing of Series, #, Vol and Year; choose which fields to write; fill only missing fields or overwrite existing values; fall back to the folder name when the filename has no series. Other fields already in the XML are preserved. `.cbr` files can't be written to and are skipped with a note. |

### Archive Tools

| Tool | What it does |
|---|---|
| **CBR to CBZ** | Repack RAR comics as ZIP in bulk. Each result is verified (zip integrity and matching page count) before the original is touched. Afterwards the `.cbr` is moved to `Archive`, kept, or deleted. |
| **Clean-up** | Remove non-image junk (Thumbs.db, `.nfo`, `__MACOSX`, …) and files matching patterns you type (e.g. `zzz*`); optionally rename pages to `001.jpg`, `002.jpg`, … (this also flattens folders inside the archive). `ComicInfo.xml` is always kept. |

---

## Safety model

- **Preview before change.** Renamer and Metadata show a review table. CBR to CBZ, Clean-up and Folder icons have **Preview changes**, which logs what would happen without writing anything.
- **Verified writes.** Archive rewrites go to a `.part` file, are verified (zip test plus page count), and only then swapped in. A failure never leaves a half-written comic.
- **The `Archive` folder.** Backups of modified comics and converted `.cbr` files are moved into an `Archive` folder next to the file. All folder scans in the app skip any folder named `Archive`. Don't name a real library folder `Archive`.
- **No overwrites by surprise.** Conflicting names are flagged (Renamer: *Exists* / *Duplicate*, skipped on apply) or resolved by your Skip / Keep both / Overwrite choice.
- **Delete is opt-in.** Deleting an original after conversion is an explicit option and only happens after verification.
- **Stop buttons** on the batch tools halt between files.

---

## Settings

Options for every tool and the theme are saved to `settings.json` next to the program when you close the window, and
restored on next launch. Delete the file to reset to defaults.

---

## Project layout

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
| `rename_core.py` | Filename parsing, `ComicInfo.xml` reading, name templating |
| `archive_tools.py` | Verified zip rewriting: CBR to CBZ, clean-up, `ComicInfo.xml` stamping |
| `folder_icons.py` | `folder.ico` / `desktop.ini` / `folder.jpg` generation (Windows) |

Logic modules (`*_core.py`, `archive_tools.py`, `folder_icons.py`) contain no UI code so they can be tested or reused
from a command line later.

---

## Known limitations

- **CBR support is untested against real RAR files.** The code path exists and is exercised only with zip-backed `.cbr` files and a corrupt-file error case.
- **Whole-archive extraction for RAR.** Opening a `.cbr` extracts all of it to a temp folder, so large CBR batches are slower than CBZ.
- **Windows-only pieces:** Folder icons (`ctypes`, `desktop.ini`), the *Open folder* buttons (`os.startfile`). Explorer may need a refresh before new folder icons appear.
- **Filename parsing is heuristic.** Unusual names (e.g. titles with ` - ` before an issue number) can parse wrongly; the review tables exist for that reason.
- **Series grouping from filenames** is a guess: it strips trailing issue/volume numbers and bracketed tags.
- **`ComicInfo.xml` rewrite** drops XML namespace declarations and appends new elements; field values and existing elements are kept.
- **YACReader may import the `Archive` folders.** Backups and converted `.cbr` files are kept as normal `.cbz` / `.cbr` files inside
  `Archive` subfolders. YACReader supports those formats and shows sub-folders of the library, and no way to exclude a folder was found,
  so those copies will probably appear as duplicate comics after a library update. This is an inference, not a tested result. Until it is
  fixed (see Roadmap item 0), move `Archive` folders out of your library or delete them once you are happy with the results.
  *Convert to ZIP* in Single issue also writes a `.zip`, which YACReader supports too.
- YACReader reads `ComicInfo.xml` **only if you enable it** (Settings > General) **and update the library** afterwards, so metadata written
  by the Metadata and Clean-up tools won't show until you do.
- Python is required to run; a double-click `.exe` is planned.

---

## Roadmap

Scope: stay stateless (no database of record), YACReader-friendly, no built-in reader, no online metadata lookups, Windows desktop.
Last reviewed against everything learned so far on 2026-10-06 (see CHANGELOG, Session 13).

### What the review changed

| Finding | Effect on the plan |
|---|---|
| YACReader imports `ComicInfo.xml` only when enabled, and only on a library update | Every tool that writes metadata shows a reminder. Documented above. |
| YACReader supports cbz/cbr/zip/rar/7z/pdf and shows library sub-folders; no ignore option found | Our `Archive` backups probably show up as duplicate comics. New item 0: store backups so readers ignore them. |
| YACReader stores story-arc fields as plain text, has no reading-list import, and keeps Reading Lists in its own database | Reading Order is metadata-based (with an optional filename prefix). No `.cbl`, no database writes. |
| YACReader's editable fields are a fixed list (Series, Title, Issue number/count, Volume, Story arc/number/count, Alternate series/number/count, Series Group, Genre) | The Metadata extension is limited to fields YACReader shows. Reading Order may use the Alternate trio, which has a count. |
| Health, Stats, the folder browser and the pipeline all need the same library scan (walk files, parse names, read `ComicInfo.xml`, page counts) | Build one shared scan layer first, with an optional disposable cache, instead of four separate scanners. |
| Unreviewed automatic writes are risky, and a watcher can only run while the app is open | The watcher queues files for review by default and polls inside the app. A command-line mode is an optional later step. |
| A PyInstaller build would lose `settings.json` (`__file__` points at a temporary or internal folder) and must bundle drag-and-drop and theme assets | Settings move to `%APPDATA%\ComicToolkit`; the app is built as a folder, not a single file. |

### Build order

**0. Backup safety fix (proposed, needs sign-off).** Keep the `Archive` folder but name backups `<file>.bak` (e.g. `Batman 01.cbz.bak`),
so no reader recognises them; restoring is a rename. Small change in `archive_tools.move_to_archive` plus a tiny "restore" note in the log.
Existing scans already skip `Archive`.

**1. Metadata extensions.** Parse `Count` from "(of N)" (the parser's bracket-stripping currently discards it) and write it as `Count`
(YACReader's "Issue count"); read `Publisher`; add a **Set for selected rows** action for fixed-value fields that can't come from a filename
(`SeriesGroup`, `Genre`, `AlternateSeries`). `CI_TAGS` and `merge_comicinfo` become a generic field writer that Reading Order reuses.
Small; extends the existing Metadata table. Adds a YACReader reminder banner.

**2. Shared library scan (`library_scan.py`).** One worker-thread scan that walks a library and yields an `Issue` record: path, size, mtime,
fields parsed from the name, `ComicInfo.xml` fields, and lazily page count, cover size and cover hash. Results can be cached in
`%APPDATA%\ComicToolkit\cache.json`, keyed by path + size + mtime. It is a cache, not a database: safe to delete, never the source of
truth. CBR files are slower (whole-archive extraction), so deep reads of CBR are opt-in. Health, Stats, the browser and the pipeline sit on it.

**3. Health tool** (new Home group "Library Audit"). Results table with a segmented switch between four reports; every report can export CSV.
- *Corrupt or broken:* CBZ zip CRC test; CBR via the extractor's test command; archives with zero pages; pages Pillow can't open (sampled:
  cover, middle, last).
- *Duplicates:* tier 1 same series + volume + issue (from `ComicInfo.xml` or the name); tier 2 identical size; optional tier 3 cover-image
  similarity (a small perceptual hash built with Pillow, no new dependency; slower, uses the cache). Report only, plus "move to Archive";
  never delete automatically. `Archive` folders are excluded.
- *Missing issues:* group by series and volume; compare numbers against the highest owned number or against `Count` when known; ignore
  non-integer numbers and annuals/specials as extras. Output like "Batman v2: missing #13, #27-#29". **Wishlist** = export to `.txt` / `.csv`
  or copy to clipboard; no tracking (stateless).
- *Quality:* flag page counts that are unusually low or high, very large or very small files, and low-resolution covers, using the same sampled
  pages instead of decoding every page. Report only.

**4. Reading Order** (own Home group "Reading Orders"; full spec below). Needs item 1's generic field writer and benefits from item 2.

**5. Stats dashboard.** Totals, size on disk, issues per series / publisher / year, format mix (cbz/cbr/pdf/epub), largest files. Built on the
scan layer; publisher needs the `Publisher` read from item 1. Drawn with simple bars on a CustomTkinter canvas (no new dependency) plus CSV
export; missing values go in an "Unknown" bucket.

**6. Folder tree browser.** A lazily loaded folder tree with a cover and counts for the selected folder, acting as a launcher: "open in
Single issue / Bulk folder / Renamer / Metadata / Clean-up / Health" using the existing `set_folder` / `load` methods. It is a navigation hub,
not a reader, so it doesn't duplicate YACReader's library view.

**7. Downloads watcher and "Process new comics" pipeline.** Order matters: CBR to CBZ, clean-up, metadata from filename, rename from the
now-stamped `ComicInfo.xml`, then move into `<library>/<Series>/` (the series-folder naming already exists). One combined review table reuses
the existing core functions, which have no UI code. The watcher polls a chosen downloads folder every few seconds **while the app is open**,
waits for file sizes to stop changing, and adds files to a staging list. Default is review-then-run; an auto-run switch is optional. Needs a
"library root" setting. A command-line `--process` mode for Task Scheduler can follow later.

**8. Packaging.** PyInstaller **folder build** (less antivirus noise than a single file) with a shortcut and icon; bundle the `customtkinter`
assets and the `tkinterdnd2` drag-and-drop files; move `settings.json` to `%APPDATA%\ComicToolkit`; optionally ship 7-Zip's `7za.exe` so CBR
works without a separate install (check its licence terms first).

### Planned: Reading Order (specified, not built)

Its own group on the Home page ("Reading Orders"); roadmap item 4. For a series or event (e.g. a crossover) you open one window, put the issues
in the order you want to read them, and the tool records that order **inside each comic's `ComicInfo.xml`**, so no file has to be
renamed.

- **How the order is stored:** `StoryArc` (the reading order's name, e.g. "Court of Owls") and `StoryArcNumber` (the issue's
  position, 1, 2, 3, ...). These are standard `ComicInfo.xml` fields (Anansi Project schema) and are what readers use for reading
  orders. YACReader 9.14+ shows them in a **Story arc** column (right-click the table header to enable it) and lists the arc as
  "(number/count) name".
- **YACReader setup:** importing `ComicInfo.xml` is **off by default**: turn it on in Settings > General, then update the library.
  The table view has an **Arc number** column (confirmed on the user's install), so position within an arc can be shown and sorted.
- **YACReader behaviour to design around** (user research plus source/changelog review): `StoryArc` is stored and searched as one
  plain text string (no splitting on commas; search is a substring match); sorting by the Story arc column groups alphabetically by arc
  name, so the arc number column is what orders issues inside an arc. YACReader's own **Reading Lists** (stored in its `library.ydb`
  database, built by hand in the app) are the native way to mix comics from several folders; the tool does not write to that database.
- **Input:** one folder, or issues dragged in from several folders.
- **Window:** list with cover thumbnails; drag to reorder plus up/down buttons; **Suggest order** pre-sorts by series, issue number
  and year (using the existing filename parser); live preview of the arc name and number each row will get.
- **Reordering later:** re-running renumbers the whole arc (position 1...n, gaps closed), because positions are just metadata.
- **Issues already in another arc:** YACReader keeps `StoryArc` as one plain string and does not split comma-separated values, so the
  multi-arc form (`Arc A,Arc B`) would just display as one long name. Instead, the review table shows each issue's current arc and
  you choose per issue: replace it or skip it.
- **Shared engine:** reuses the Metadata tool's generic `ComicInfo.xml` field writer (roadmap item 1), its review-table pattern and the
  verified-write path, so it is mostly a new page and ordering window.
- **YACReader reminder:** after writing, update the library in YACReader (with ComicInfo import enabled) to see the new order.
- **Safety:** same as the Metadata tool: originals are kept in `Archive` (or replaced, your choice) and every write is verified.
  `.cbr` files can't be written to and are skipped (convert them first).
- **Fields YACReader lets you edit per issue** (user-supplied list): Series, Title; Issue number, Issue count, Volume; Story arc,
  Arc number, Arc count; Alternate series, Alt. number, Alt. count; Series Group, Genre. Most correspond to standard `ComicInfo.xml`
  tags (`Series`, `Title`, `Number`, `Count`, `Volume`, `StoryArc`, `StoryArcNumber`, `AlternateSeries`, `AlternateNumber`,
  `AlternateCount`, `SeriesGroup`, `Genre`). There is **no standard tag for Arc count**, so it may not import from `ComicInfo.xml`.
- **Where to store the order (to test at build time):** either *Story arc* (`StoryArc` + `StoryArcNumber`; no count) or *Alternate
  series* (`AlternateSeries` + `AlternateNumber` + `AlternateCount`, a complete name/position/total triple that YACReader also exposes).
  Test which one YACReader imports and shows best; the tool may offer both as a choice. `SeriesGroup` could additionally label an
  event or crossover.
- **Display strategy (decided, to be confirmed by testing at build time):** write the metadata always; offer the filename prefix as
  a first-class option. Test with real files in YACReader whether the arc number column sorts numerically or as text, then set the
  prefix default accordingly (metadata alone if sorting is numeric and reliable).
- **Optional extras (both off by default until tested):**
  - *Also gather copies:* copy the ordered issues into a new folder you name (parent location asked each time, last parent
    remembered) and stamp **only the copies**, so the originals are never modified.
  - *Filename prefix:* also number the filenames (`01 - `, `001 - `, `[01] ` ...; style, separator and padding chosen per run) for
    browsing in Explorer, where metadata isn't visible. The Renamer, Metadata and series detection would recognise and ignore this
    prefix, and the Renamer would strip it unless "keep reading-order number" is ticked.
- **Dropped from the original idea:** the `.cbl` reading-list export (YACReader does not support it), read/unread tracking (YACReader
  does that), a saved order file, undo.
- **To verify when built, in the real YACReader:** whether `StoryArcNumber` sorts numerically or as text (decides whether to
  zero-pad, e.g. `01`), where the "(n/count)" count comes from, and that the arc shows up for CBZ files after a library update.

---

## Versioning

Git tags follow `vMAJOR.MINOR.PATCH` and stay at `v0.x.y` until the first public release (`v1.0.0`).

- **MINOR** (`v0.2.0`, `v0.3.0`, ...): a new tool or a meaningful new capability.
- **PATCH** (`v0.1.1`, ...): bug fixes, small behaviour tweaks, documentation-only releases.
- Tags are annotated (`git tag -a`) and sit on the commit that finishes that release, after README and CHANGELOG are updated.

| Tag | Contents |
|---|---|
| `v0.1.0` | Initial import: Single issue, Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Clean-up; light/dark themes; settings |
| `v0.2.0` | Roadmap items 0-1: backup safety fix and Metadata extensions |
| `v0.3.0` | Roadmap items 2-3: shared library scan and the Library Audit tool |
| `v0.4.0` | Roadmap item 4: Reading Order |
| `v0.5.0` | Roadmap items 5-6: Stats dashboard and folder browser |
| `v0.6.0` | Roadmap item 7: downloads watcher and processing pipeline |
| `v0.7.0` | Roadmap item 8: packaged Windows build |
| `v1.0.0` | First public release |

The planned versions are a guide and can be merged or split as the work lands.

---

## Maintenance

`README.md` and `CHANGELOG.md` are updated at the end of every working session: the README to reflect what the tool does
now, the changelog to record what was done and why, as a new timestamped block at the top.
