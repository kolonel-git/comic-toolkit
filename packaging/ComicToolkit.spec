# PyInstaller spec: a folder build (dist/ComicToolkit/ComicToolkit.exe). A folder build starts faster and trips antivirus
# programs less than a single-file .exe. Build with packaging/build.ps1, or:  pyinstaller packaging/ComicToolkit.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent

datas = collect_data_files("customtkinter") + collect_data_files("tkinterdnd2")   # themes, fonts and the drag-and-drop library
datas += [(str(root / "ACEO - Full Page BLANK.pdf"), "."),                         # the default ACEO sheet template
          (str(root / "packaging" / "ComicToolkit.ico"), "packaging")]             # the window icon

a = Analysis([str(root / "comic_tool.py")], pathex=[str(root)], datas=datas,
             hiddenimports=["pypdf", "PIL._tkinter_finder"],                       # pypdf is imported on first use
             excludes=["pytest", "unittest"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ComicToolkit", console=False,
          icon=str(root / "packaging" / "ComicToolkit.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="ComicToolkit")
