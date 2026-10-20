# Build the packaged program: dist\ComicToolkit\ComicToolkit.exe
#   .\packaging\build.ps1               build it
#   .\packaging\build.ps1 -Shortcut     build it and put a shortcut on the desktop
# Needs Python with the program's packages (customtkinter, tkinterdnd2, pillow, pypdf) and PyInstaller (pip install pyinstaller).
param([switch]$Shortcut)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is not installed: pip install pyinstaller" }
python packaging/make_icon.py
python -m PyInstaller packaging/ComicToolkit.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "The build failed" }
New-Item -ItemType Directory -Force "dist\ComicToolkit\tools" | Out-Null
Set-Content "dist\ComicToolkit\tools\README.txt" "To open .cbr files, put 7z.exe and 7z.dll (from 7-Zip) or unrar.exe in this folder."
Write-Host "Built dist\ComicToolkit\ComicToolkit.exe"
if ($Shortcut) {
    $link = Join-Path ([Environment]::GetFolderPath("Desktop")) "Comic Toolkit.lnk"
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
    $s.TargetPath = Join-Path $root "dist\ComicToolkit\ComicToolkit.exe"
    $s.WorkingDirectory = Join-Path $root "dist\ComicToolkit"
    $s.Save()
    Write-Host "Shortcut: $link"
}
