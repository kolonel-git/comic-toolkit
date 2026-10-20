"""Where files live: settings under %APPDATA%, the bundled files, the tools folder, and the old settings place read once."""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app_paths as ap
import comic_core as cc
import aceo_core as ac

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    os.environ["APPDATA"] = str(d / "Roaming")
    assert ap.data_dir() == d / "Roaming" / "ComicToolkit" and ap.settings_path() == d / "Roaming" / "ComicToolkit" / "settings.json"
    assert not ap.data_dir().exists()                     # looking is not creating
    del os.environ["APPDATA"]
    assert ap.data_dir() == Path.home() / ".comictoolkit"
    # from the source folder the bundled files are beside the code; packaged they are in PyInstaller's folder
    src = Path(ap.__file__).resolve().parent
    assert ap.resource_dir() == src and ap.program_dir() == src and not ap.frozen()
    assert ac.default_template().name.startswith("ACEO") and ac.default_template().exists()
    sys.frozen, sys._MEIPASS = True, str(d / "unpacked")
    try:
        assert ap.frozen() and ap.resource_dir() == d / "unpacked" and ap.tools_dir() == Path(sys.executable).resolve().parent / "tools"
    finally:
        del sys.frozen, sys._MEIPASS
    # a 7z.exe dropped in the tools folder is the extractor that is used first
    tools = d / "tools"; tools.mkdir(); (tools / "7z.exe").write_bytes(b"x")
    real = cc.tools_dir
    cc.tools_dir = lambda: tools
    try:
        assert cc.find_extractor() == str(tools / "7z.exe")
    finally:
        cc.tools_dir = real
    # the app reads the old settings place only when it is using the new default place
    import comic_tool as ct
    assert ct.SETTINGS == ap.settings_path()
    old = d / "old.json"; old.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
    real_new, real_old = ct.SETTINGS, ct.legacy_settings_path
    try:
        ct.SETTINGS = d / "new" / "settings.json"                 # a test's own file: the old place must not be read
        ct.legacy_settings_path = lambda: old
        assert ct.App._load_settings(None) == {}
        ct.SETTINGS = ap.settings_path()
        os.environ["APPDATA"] = str(d / "Roaming2")               # nothing saved yet: the old place is read once
        ct.SETTINGS = ap.settings_path()
        assert ct.App._load_settings(None) == {"theme": "dark"}
    finally:
        ct.SETTINGS, ct.legacy_settings_path = real_new, real_old
        os.environ.pop("APPDATA", None)
print("app paths OK")
