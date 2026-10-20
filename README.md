# Comic Toolkit

A desktop app for managing a personal, local library of comic files (`.cbz`, `.cbr`, plus `.pdf` / `.epub` for renaming).
It prepares a library for a reader such as **YACReader**: it does not read comics itself, and it deliberately keeps no
database. Everything works on the files and folders on disk.

- **Platform:** Windows 10/11 (a few features are Windows-only)
- **Language / UI:** Python 3, [customtkinter](https://github.com/TomSchimansky/CustomTkinter), neo-brutalist light and dark themes
- **Status:** active development, latest tag `v0.9.0`. Every page is being rebuilt on a shared layout (a header, two resizable columns and a footer); Bulk folder, Library stats, Metadata, Library audit, CBR to CBZ and Single issue are done, the rest follow (see the [UI revamp plan](docs/ui-revamp-plan.md) and the [roadmap](docs/roadmap.md))

## Quick start

```
pip install customtkinter tkinterdnd2 pillow pypdf
python comic_tool.py
```

To run it without Python, build the folder version: see [Packaging](docs/packaging.md).

Opening `.cbr` files needs a RAR-capable extractor (7-Zip, unrar, or Windows' built-in `tar.exe`). See
[Getting started](docs/getting-started.md) for details.

## What's inside

The Home page shows the tools as cards, grouped as below. A Dark mode switch sits in the sidebar. Every page takes a folder or
individual comics (drop them, or use **Add folder…** / **Choose comics…**), and the sidebar, the options panels, the two columns of Bulk folder, Metadata and Library audit, and every table column can be dragged to the size you like.

| Group | Tools | What they do |
|---|---|---|
| **Comic Cover Extractor** | Single issue, Bulk folder, Folder icons | Preview an issue's first and last pages, save covers one at a time or for a whole folder, and show covers as Explorer folder icons |
| **Comic Renamer** | Renamer | Rename a collection with a naming format for each type (issues, annuals, TPBs, omnibuses, compendiums…), correcting each file on a card before anything changes, with full control of numbers, capitalisation, separators and folders |
| **Metadata** | Metadata | Repair the details inside your comics: see what is missing, fix one comic or many at once with suggestions from your own library, review every change and save |
| **Archive Tools** | CBR to CBZ | Repack RAR comics as verified ZIPs, in bulk, with a dry run and a choice of what happens to each original |
| **Library Audit** | Library audit | Scan a library once, then see broken files, duplicates, missing issues (per type), junk files and CBR files in one list under a strip of counts, open a details panel that points to the tool that fixes each kind of problem, fix them in place after a confirmation, leave reading-order folders out of the duplicates, ignore what you don't care about, and manage the Archive folders |
| **Reading Orders** | Reading order | Arrange issues in the order to read them and record it in each comic's `ComicInfo.xml`, optionally also in the filenames or a folder of copies |
| **Library stats** | Dashboard (sidebar, or the summary line on Home) | Totals, size on disk, bars per series, publisher, year and format, metadata coverage and the largest files, with click-through to the comics, CSV export and a copyable summary |
| **ACEO Cards** | ACEO sheets | Fill full pages of 8 ACEO trading cards with the covers you pick, from the blank template PDF, and save a print-ready PDF |

## Safety at a glance

- Review tables and **Preview changes** show what will happen before anything is written.
- Archive rewrites are verified before they replace a file; originals can be kept in an `Archive` folder.
- Conflicting names are flagged and skipped, never silently overwritten.

Backups in `Archive` folders are renamed `.bak` so comic readers such as YACReader ignore them. See
[Known limitations](docs/known-limitations.md) and the [safety model](docs/safety.md).

## Documentation

Everything else lives in [`docs/`](docs/README.md):

- [Getting started](docs/getting-started.md) · [The tools](docs/tools.md) · [Naming styles and templates](docs/renamer-templates.md)
- [Safety model](docs/safety.md) · [Known limitations](docs/known-limitations.md) · [Architecture](docs/architecture.md) · [Manual tests](docs/manual-tests.md)
- [Roadmap](docs/roadmap.md) · [UI revamp plan](docs/ui-revamp-plan.md) · [Reading Order](docs/reading-order.md) · [Versioning](docs/versioning.md)
- [Changelog](docs/CHANGELOG.md) · [Tests](tests/README.md)
