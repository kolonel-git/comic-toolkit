# Getting started

[< Docs index](README.md)

```
pip install customtkinter tkinterdnd2 pillow
python comic_tool.py
```

Tested on Python 3.14 (Windows 11). Python 3.9+ is required (`xml.etree.ElementTree.indent`).

**For `.cbr` (RAR) files** you need one RAR-capable extractor on the machine. The app looks for, in order:
`7z` / `7za` / `unrar` on PATH, 7-Zip in `C:\Program Files\7-Zip`, then Windows' built-in `tar.exe` (bsdtar reads RAR).
Some `.cbr` files are really zips and need no extractor.

## Settings

Options for every tool and the theme are saved to `settings.json` next to the program when you close the window, and
restored on next launch. Delete the file to reset to defaults.

The library scan keeps a cache at `%APPDATA%\ComicToolkit\cache.json`. It only speeds up repeat scans, is safe to delete, and is never
the source of truth about your comics.

## Checking a library from the command line

```
python library_scan.py "D:\Comics" --deep --csv library.csv
```

This lists every comic with the series, issue, year and (with `--deep`) page count and cover size, and can write the table to CSV.
See [Architecture](architecture.md#the-library-scan) for the options.
