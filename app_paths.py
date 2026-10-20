r"""Where the program's files live, for a run from the source folder and for the packaged (PyInstaller folder) build.

- `resource_dir()`: the program's own files (the ACEO template, the icon).
- `settings_path()`: the settings file, in `%APPDATA%ComicToolkit` (it used to sit beside the program).
- `legacy_settings_path()`: where it used to be, read once when the new one does not exist yet.
- `tools_dir()`: a folder beside the program where 7z.exe (with 7z.dll) or unrar.exe can be dropped for CBR support.
"""
import os
import sys
from pathlib import Path

APP_NAME = "ComicToolkit"


def frozen():
    return bool(getattr(sys, "frozen", False))


def resource_dir():
    """Folder holding the bundled files: PyInstaller's unpack folder when packaged, the source folder otherwise."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def program_dir():
    """The folder the program is started from: beside the .exe when packaged, the source folder otherwise."""
    return Path(sys.executable).resolve().parent if frozen() else Path(__file__).resolve().parent


def data_dir():
    """The per-user folder for settings (not created here)."""
    base = os.environ.get("APPDATA")
    return Path(base) / APP_NAME if base else Path.home() / f".{APP_NAME.lower()}"


def settings_path():
    return data_dir() / "settings.json"


def legacy_settings_path():
    return program_dir() / "settings.json"


def tools_dir():
    return program_dir() / "tools"
