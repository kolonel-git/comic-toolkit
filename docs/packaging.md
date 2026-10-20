# Packaging

The program can be built as a **folder** that starts with a double-click (`dist\ComicToolkit\ComicToolkit.exe`), so Python does not have to be installed. A folder build starts faster and trips antivirus programs less than a single-file `.exe`, which unpacks itself on every start.

## Build it

```
pip install pyinstaller
.\packaging\build.ps1              # builds dist\ComicToolkit\
.\packaging\build.ps1 -Shortcut    # also puts "Comic Toolkit" on the desktop
```

The packages the program itself needs (`customtkinter`, `tkinterdnd2`, `pillow`, `pypdf`) must be installed in the same Python. `build/` and `dist/` are git-ignored. Copy the whole `dist\ComicToolkit` folder wherever you like; the `.exe` needs the `_internal` folder beside it.

What is in `packaging/`:

| File | What it is |
|---|---|
| `ComicToolkit.spec` | the PyInstaller recipe: the program, `customtkinter`'s themes and fonts, the `tkinterdnd2` drag-and-drop files, the ACEO template PDF, the icon, and `pypdf` (which is imported on first use, so it is named by hand) |
| `build.ps1` | runs the recipe, adds the `tools` folder and, with `-Shortcut`, the desktop shortcut |
| `make_icon.py` | draws `ComicToolkit.ico` (the square, circle and triangle of the sidebar logo); run it again after changing the drawing |

## Where files live (`app_paths.py`)

- **Settings:** `%APPDATA%\ComicToolkit\settings.json`, for a run from the source folder and for the packaged program alike. If that file does not exist yet, the old `settings.json` beside the program is read once, and the next close writes the new place. Delete the file to reset to the defaults.
- **The library scan cache:** `%APPDATA%\ComicToolkit\cache.json` (unchanged).
- **Bundled files** (the ACEO template, the icon): beside the code when run from the source, in the `_internal` folder when packaged.

## Opening `.cbr` files

Comic Toolkit does not bundle a RAR extractor. It looks, in this order, for `7z.exe` or `unrar.exe` in a **`tools` folder beside the program**, then `7z`, `7za` or `unrar` on the PATH, 7-Zip in Program Files and Windows' own `tar.exe`. To make a packaged copy work without installing anything, put `7z.exe` and `7z.dll` (from a 7-Zip install) or `unrar.exe` in `dist\ComicToolkit\tools`.

It is not shipped in the build because of the licences: 7-Zip is LGPL with an extra "unRAR restriction" on its RAR code, and `unrar.exe` is freeware that may not be used to build a RAR compressor. Both can be redistributed under their terms, but that is for the owner to decide before sharing a build. Note that `7za.exe` (the stand-alone console version) cannot read RAR at all; it needs `7z.exe` with `7z.dll`.
