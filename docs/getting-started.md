# Getting started

[< Docs index](README.md)

```
pip install customtkinter tkinterdnd2 pillow pypdf
python comic_tool.py
```

`pypdf` is only used by the ACEO sheets tool. Tested on Python 3.14 (Windows 11). Python 3.9+ is required (`xml.etree.ElementTree.indent`).

**For `.cbr` (RAR) files** you need one RAR-capable extractor on the machine. The app looks for, in order:
a `tools` folder beside the program (`7z.exe` with `7z.dll`, or `unrar.exe`), `7z` / `7za` / `unrar` on PATH, 7-Zip in `C:\Program Files\7-Zip`, then Windows' built-in `tar.exe` (bsdtar reads RAR).
Some `.cbr` files are really zips and need no extractor.

## Settings

Options for every tool and the theme are saved to `%APPDATA%\ComicToolkit\settings.json` when you close the window, and
restored on next launch. Delete the file to reset to defaults.

The library scan keeps a cache at `%APPDATA%\ComicToolkit\cache.json`. It only speeds up repeat scans, is safe to delete, and is never
the source of truth about your comics.

## Checking a library from the command line

```
python library_scan.py "D:\Comics" --deep --csv library.csv
```

This lists every comic with the series, issue, year and (with `--deep`) page count and cover size, and can write the table to CSV.
See [Architecture](architecture.md#the-library-scan) for the options.

## Keyboard and shared folders

| Keys | What it does |
|---|---|
| Ctrl+K | A floating search bar: type part of a page or action name (or a word from its description), Up and Down to choose, Enter to open, Esc to close |
| Ctrl+1, Ctrl+2 | Home, Library stats |
| Ctrl+O | Add a folder (the first button of the drop box) |
| Ctrl+Enter | Press the page's main yellow button, when it can be used |
| Esc | Stop a running job |
| Tab, Enter or Space | Move between buttons, cards, switches, sliders, drop-down lists, format pickers and text fields (a blue ring shows the focus); arrow keys move a slider or a format picker |

Every tool with a drop box has **Library folder** and **Recent** under *Add folder*. *Library folder* opens the folder that Library stats scans
(it asks for it the first time; change it any time with *Library folder…* on Home, *Change…* on Library stats, or Ctrl+K). *Recent* lists the last eight folders any tool opened (saved in `settings.json`). Long runs show an
estimate of the time left and flash the taskbar button when they finish.
