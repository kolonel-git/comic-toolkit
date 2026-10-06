# The tools

[< Docs index](README.md)

The Home page groups the tools as cards; the sidebar mirrors the same groups. A **Dark mode** switch sits at the bottom of
the sidebar (first launch follows Windows; your choice is remembered).

## Comic Cover Extractor

| Tool | What it does |
|---|---|
| **Single issue** | Drop in one comic. Preview the cover and first 3 pages and the last 3 pages. Save the cover (format, quality, max height, destination, file name, conflict handling), or convert the comic to a ZIP. |
| **Bulk folder** | Extract the cover from every CBZ/CBR in a folder. Choose subfolders on or off; save into a named subfolder, a folder you choose, or beside each comic; organise as one folder, mirrored folders, or grouped by series name; JPG/PNG/WebP/original, quality, size, file name, overwrite/skip/keep-both. Shows a live example path, progress, a per-file log, and a Stop button. |
| **Folder icons** | Make each series folder show its cover in Windows Explorer: builds `folder.ico`, writes `desktop.ini`, sets the Windows attributes Explorer needs, and optionally saves `folder.jpg`. Cover from first or last issue. **Custom image for a folder…** lets you pick any folder (e.g. a `DC` or `Marvel` parent) and any image. Windows only. |

## Comic Renamer

| Tool | What it does |
|---|---|
| **Renamer** | Standardise file names across a folder (CBZ, CBR, PDF, EPUB; subfolders optional). Parses the filename, and optionally `ComicInfo.xml`, which wins when present. Pick a naming style from 8 presets or write a custom template, set issue-number padding and series capitalisation, optionally move files into series folders. A preview table shows old and new names with statuses; tick rows, double-click a new name to edit it, then apply. Nothing changes on disk until you confirm. |

See [Naming styles and templates](renamer-templates.md) for the eight presets and the custom template syntax.

## Metadata

| Tool | What it does |
|---|---|
| **Metadata** | Stamp series, issue number, volume, year, title and issue count from filenames into each CBZ's `ComicInfo.xml` (the file YACReader and most readers use). The count is read from "(of 12)" or "(3 of 12)" (round or square brackets) and written as `Count`, YACReader's "Issue count". Review table with inline editing of Series, #, Vol, Year and Of; choose which fields to write; **Set for checked rows** applies one fixed value (Series Group, Genre, Alternate series or Publisher) to every checked row, which no filename can supply (an empty value cancels a pending one; Genre takes a comma-separated list); a note on the page reminds you that YACReader shows ComicInfo data only after you enable import and update the library; fill only missing fields or overwrite existing values; fall back to the folder name when the filename has no series. Other fields already in the XML are preserved. `.cbr` files can't be written to and are skipped with a note. |

## Archive Tools

| Tool | What it does |
|---|---|
| **CBR to CBZ** | Repack RAR comics as ZIP in bulk. Each result is verified (zip integrity and matching page count) before the original is touched. Afterwards the `.cbr` is moved to `Archive` (as `.cbr.bak`), kept, or deleted. |
| **Clean-up** | Remove non-image junk (Thumbs.db, `.nfo`, `__MACOSX`, …) and files matching patterns you type (e.g. `zzz*`); optionally rename pages to `001.jpg`, `002.jpg`, … (this also flattens folders inside the archive). `ComicInfo.xml` is always kept. |
