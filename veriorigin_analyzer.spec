# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
ROOT = Path(SPECPATH)

a = Analysis(
    ['veriorigin_supply_chain_tool/veriorigin_analyzer.py'],
    pathex=[],
    binaries=[],
    datas=[ (str(ROOT / "veriorigin_supply_chain_tool" / "VeriOrigin_logo.png"), "veriorigin_supply_chain_tool"),
            (str(ROOT / "veriorigin_supply_chain_tool" / "privacy_allowlist.json"), "veriorigin_supply_chain_tool"),
            (str(ROOT / "veriorigin_supply_chain_tool" / "vetted_registry.json"), "veriorigin_supply_chain_tool"),
            (str(ROOT / "testbed-repo" / "package.json"), "testbed-repo")],
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
    name='veriorigin_analyzer',
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
    icon=['veriorigin_supply_chain_tool/VeriOrigin_icon.png'],
)
