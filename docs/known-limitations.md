# Known limitations

[< Docs index](README.md)

- **CBR support is untested against real RAR files.** The code path exists and is exercised only with zip-backed `.cbr` files and a corrupt-file error case.
- **Whole-archive extraction for RAR.** Opening a `.cbr` extracts all of it to a temp folder, so large CBR batches are slower than CBZ.
- **Windows-only pieces:** Folder icons (`ctypes`, `desktop.ini`), the *Open folder* buttons (`os.startfile`). Explorer may need a refresh before new folder icons appear.
- **Filename parsing is heuristic.** Unusual names (e.g. titles with ` - ` before an issue number) can parse wrongly; the review tables exist for that reason.
- **Series grouping from filenames** is a guess: it strips trailing issue/volume numbers and bracketed tags.
- **`ComicInfo.xml` rewrite** drops XML namespace declarations and appends new elements; field values and existing elements are kept.
- **YACReader may import the `Archive` folders.** Backups and converted `.cbr` files are kept as normal `.cbz` / `.cbr` files inside
  `Archive` subfolders. YACReader supports those formats and shows sub-folders of the library, and no way to exclude a folder was found,
  so those copies will probably appear as duplicate comics after a library update. This is an inference, not a tested result. Until it is
  fixed (see [roadmap](roadmap.md), item 0), move `Archive` folders out of your library or delete them once you are happy with the results.
  *Convert to ZIP* in Single issue also writes a `.zip`, which YACReader supports too.
- YACReader reads `ComicInfo.xml` **only if you enable it** (Settings > General) **and update the library** afterwards, so metadata written
  by the Metadata and Clean-up tools won't show until you do.
- Python is required to run; a double-click `.exe` is planned.
