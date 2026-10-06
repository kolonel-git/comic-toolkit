# Roadmap

[< Docs index](README.md)

Scope: stay stateless (no database of record), YACReader-friendly, no built-in reader, no online metadata lookups, Windows desktop.
Last reviewed against everything learned so far on 2026-10-06 (see [CHANGELOG](CHANGELOG.md), Session 13).

## What the review changed

| Finding | Effect on the plan |
|---|---|
| YACReader imports `ComicInfo.xml` only when enabled, and only on a library update | Every tool that writes metadata shows a reminder. Documented above. |
| YACReader supports cbz/cbr/zip/rar/7z/pdf and shows library sub-folders; no ignore option found | Our `Archive` backups probably show up as duplicate comics. Item 0 (done): backups are stored as `.bak` so readers ignore them. |
| YACReader stores story-arc fields as plain text, has no reading-list import, and keeps Reading Lists in its own database | Reading Order is metadata-based (with an optional filename prefix). No `.cbl`, no database writes. |
| YACReader's editable fields are a fixed list (Series, Title, Issue number/count, Volume, Story arc/number/count, Alternate series/number/count, Series Group, Genre) | The Metadata extension is limited to fields YACReader shows. Reading Order may use the Alternate trio, which has a count. |
| Health, Stats, the folder browser and the pipeline all need the same library scan (walk files, parse names, read `ComicInfo.xml`, page counts) | Build one shared scan layer first, with an optional disposable cache, instead of four separate scanners. |
| Unreviewed automatic writes are risky, and a watcher can only run while the app is open | The watcher queues files for review by default and polls inside the app. A command-line mode is an optional later step. |
| A PyInstaller build would lose `settings.json` (`__file__` points at a temporary or internal folder) and must bundle drag-and-drop and theme assets | Settings move to `%APPDATA%\ComicToolkit`; the app is built as a folder, not a single file. |

## Build order

**0. Backup safety fix (done, 2026-10-06).** The `Archive` folder stays, but backups are named `<file>.bak` (e.g. `Batman 01.cbz.bak`),
so no reader recognises them; restoring is a rename. Change is in `archive_tools.move_to_archive`. Existing scans already skip `Archive`.
Still to do: confirm in YACReader that `.bak` files are ignored. A restore button and a log note were not added.

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

**4. Reading Order** (own Home group "Reading Orders"; full spec in [reading-order.md](reading-order.md)). Needs item 1's generic field writer and benefits from item 2.

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
