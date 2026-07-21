# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Clear Audio Windows executable.
# Usage: pyinstaller audio_guide.spec

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH)
_icon_source = project_root / "sources" / "logo.ico"
if not _icon_source.is_file():
    _icon_source = project_root / "sources" / "logo.ico"

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(_icon_source), "sources")] if _icon_source.is_file() else [],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ClearAudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "sources" / "logo.ico"),
)
