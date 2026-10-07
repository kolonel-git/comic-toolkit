# Known limitations

[< Docs index](README.md)

- **CBR support is untested against real RAR files.** The code path exists and is exercised only with zip-backed `.cbr` files and a corrupt-file error case.
- **Whole-archive extraction for RAR.** Opening a `.cbr` extracts all of it to a temp folder, so large CBR batches are slower than CBZ.
- **Windows-only pieces:** Folder icons (`ctypes`, `desktop.ini`), the *Open folder* buttons (`os.startfile`). Explorer may need a refresh before new folder icons appear.
- **Filename parsing is heuristic.** Unusual names (e.g. titles with ` - ` before an issue number) can parse wrongly; the review tables exist for that reason.
- **Collected-edition detection is keyword based.** A series whose real title contains a format word (for example a series called *Deluxe*) is read as a collected edition; change its type on its card or in the Type column. A bare `Vol 3` is an issue unless you change **A name with only “Vol 3” is**. Series spelling is not unified beyond case and a leading *The*: `Walking Dead` and `Walking Dead Deluxe` are different series.
- **Renamer settings from before the revamp are not carried over.** The old naming style, custom template and collected-style choices are ignored; everything else of the page starts at its defaults, and the new per-type templates start at the old defaults.
- **Renamer details.** Hand edits on a card exist only until you rescan, rename or leave the app (nothing is saved between runs). The template box is narrow, so a long template scrolls inside it; the live example under it shows the result. `{publisher}` is empty unless ComicInfo.xml is used and has a publisher. A year is only recognised from 1900 to next year, and a year in the *middle* of the series name is not touched.
- **Series grouping from filenames** is a guess: it strips trailing issue/volume numbers and bracketed tags.
- **`ComicInfo.xml` rewrite** drops XML namespace declarations and appends new elements; field values and existing elements are kept.
- **`Archive` backups are renamed `.bak`, untested in YACReader.** Backups and converted `.cbr` files are stored as `<name>.cbz.bak` /
  `<name>.cbr.bak` so YACReader should not recognise them as comics. That is an inference, not a tested result. Backups made by earlier
  versions kept their real `.cbz` / `.cbr` names and may still be imported: add `.bak` to them by hand, or move those `Archive` folders out
  of your library. *Convert to ZIP* in Single issue also writes a `.zip`, which YACReader supports too.
- **Issue count is recognised only as "(of N)" / "(3 of 12)".** A bare "(3/12)" is not parsed, to avoid confusing it with dates. The
  Renamer reads the new fields but has no tokens for them, and the Metadata table shows no columns for Series Group, Genre, Alternate series
  or Publisher (they appear only in what gets written).
- YACReader reads `ComicInfo.xml` **only if you enable it** (Settings > General) **and update the library** afterwards, so metadata written
  by the Metadata and Clean-up tools won't show until you do.
- **The scan's deep mode reads only each archive's first page**, so it can miss corruption deeper in a file; use the Audit tool's full integrity test for that.
  Real RAR files are skipped unless **Open real .cbr files** (or `--deep-cbr`) is on. The cover-similarity levels (Strict 4, Normal 8, Loose 12 differing bits of 64)
  are untested on real covers (see [manual tests](manual-tests.md), C7 and D5).
- **Audit reports are heuristics.** Duplicates by series/issue depend on filename parsing; identical size can be a coincidence; covers from different editions
  of the same issue look alike (and variant covers may not). Missing-issue gaps assume numbering is continuous, so series with deliberate gaps (or issue #0, which is
  treated as not expected) will show false gaps. The quality limits (pages, size, cover height) are fixed constants in `audit_core.py`.
- **The audit holds its results in memory only.** Nothing is saved between runs except the scan cache; a very large library shows every row at once.
- **Removing issue numbers is one-way per file.** The number is deleted from `ComicInfo.xml` (a `.bak` backup is kept unless you chose to replace), and the Metadata tool will
  add it back from the filename on its next run unless **Issue number** is unticked under *Fields to write*. Whether YACReader then really sorts by filename is untested
  (see [manual tests](manual-tests.md), B9 and E13).
- **Reading Order has no cover thumbnails,** and the whole list lives in memory only (no saved order file). It writes only CBZ (or zip-backed) files.
  Whether YACReader sorts the arc number numerically, and which of *Story arc* / *Alternate series* it shows best, is untested (see [manual tests](manual-tests.md), E).
  The filename-prefix recogniser (`01 - Name`, `[01] Name`) can misread a real name such as `100 - Bullets 05`.
- Python is required to run; a double-click `.exe` is planned.
