# Known limitations

[< Docs index](README.md)

- **CBR support is untested against real RAR files.** The code path exists and is exercised only with zip-backed `.cbr` files and a corrupt-file error case.
- **Whole-archive extraction for RAR.** Opening a `.cbr` extracts all of it to a temp folder, so large CBR batches are slower than CBZ.
- **Windows-only pieces:** Folder icons (`ctypes`, `desktop.ini`), the *Open folder* buttons (`os.startfile`). Explorer may need a refresh before new folder icons appear.
- **Filename parsing is heuristic.** Unusual names (e.g. titles with ` - ` before an issue number) can parse wrongly; the review tables exist for that reason.
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
- Python is required to run; a double-click `.exe` is planned.
