# Comic Toolkit

A desktop app for managing a personal, local library of comic files (`.cbz`, `.cbr`, plus `.pdf` / `.epub` for renaming).
It prepares a library for a reader such as **YACReader**: it does not read comics itself, and it deliberately keeps no
database. Everything works on the files and folders on disk.

- **Platform:** Windows 10/11 (a few features are Windows-only)
- **Language / UI:** Python 3, [customtkinter](https://github.com/TomSchimansky/CustomTkinter), Notion-style light and dark themes
- **Status:** active development, currently `v0.1.0`

## Quick start

```
pip install customtkinter tkinterdnd2 pillow
python comic_tool.py
```

Opening `.cbr` files needs a RAR-capable extractor (7-Zip, unrar, or Windows' built-in `tar.exe`). See
[Getting started](docs/getting-started.md) for details.

## What's inside

The Home page shows the tools as cards, grouped as below. A Dark mode switch sits in the sidebar.

| Group | Tools | What they do |
|---|---|---|
| **Comic Cover Extractor** | Single issue, Bulk folder, Folder icons | Preview an issue's first and last pages, save covers one at a time or for a whole folder, and show covers as Explorer folder icons |
| **Comic Renamer** | Renamer | Give a collection one consistent naming pattern, with a preview table you can edit before anything changes |
| **Metadata** | Metadata | Write series, issue, volume, year and title from filenames into each CBZ's `ComicInfo.xml` |
| **Archive Tools** | CBR to CBZ, Clean-up | Repack RAR comics as verified ZIPs; strip junk files and tidy page names |

## Safety at a glance

- Review tables and **Preview changes** show what will happen before anything is written.
- Archive rewrites are verified before they replace a file; originals can be kept in an `Archive` folder.
- Conflicting names are flagged and skipped, never silently overwritten.

Backups in `Archive` folders are renamed `.bak` so comic readers such as YACReader ignore them. See
[Known limitations](docs/known-limitations.md) and the [safety model](docs/safety.md).

## Documentation

Everything else lives in [`docs/`](docs/README.md):

- [Getting started](docs/getting-started.md) · [The tools](docs/tools.md) · [Naming styles and templates](docs/renamer-templates.md)
- [Safety model](docs/safety.md) · [Known limitations](docs/known-limitations.md) · [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md) · [Reading Order (planned)](docs/reading-order.md) · [Versioning](docs/versioning.md)
- [Changelog](docs/CHANGELOG.md)
