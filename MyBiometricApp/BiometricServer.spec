# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['biometric_server_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.')] if os.path.exists('config.json') else [],
    hiddenimports=['websockets', 'asyncio', 'sqlite3', 'requests', 'csv', 'logging.handlers', 'tkinter', 'tkinter.filedialog', 'queue', 'json'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[], 
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BiometricServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='biometric.ico' if os.path.exists('biometric.ico') else None,
)
