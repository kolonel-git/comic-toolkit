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
