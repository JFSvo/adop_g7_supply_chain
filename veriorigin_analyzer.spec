# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['veriorigin_supply_chain_tool/veriorigin_analyzer.py'],
    pathex=[],
    binaries=[],
    datas=[('veriorigin_supply_chain_tool/VeriOrigin_logo.png', 'veriorigin_supply_chain_tool'), ('data/mock-web/vetted-source-registry.md', 'data/mock-web')],
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
