$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (!(Test-Path ".venv\Scripts\python.exe")) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name Judy --paths src --collect-all PySide6 --collect-all keyring run_judy.py
New-Item -ItemType Directory -Force dist\installer | Out-Null
Write-Host "Build complete: dist\Judy\Judy.exe"
Write-Host "Compile installer\Judy.iss with Inno Setup 6 to create the setup installer."
