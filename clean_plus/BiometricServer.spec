# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

a = Analysis(
    ['biometric_server_gui.py', 'config_manager.py', 'settings_dialog.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['websockets', 'websockets.legacy', 'websockets.legacy.server', 'websockets.legacy.protocol', 'asyncio', 'sqlite3', 'requests', 'csv', 'logging.handlers', 'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext', 'tkinter.messagebox', 'tkinter.filedialog', 'queue', 'json', 'datetime', 'threading', 'weakref', 'platform', 'socket', 'signal'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['msvcrt'],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
