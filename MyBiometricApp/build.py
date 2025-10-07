#!/usr/bin/env python3
"""
Build script for creating Windows executable from Biometric Server GUI
This script handles PyInstaller configuration and builds the .exe file
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Build configuration
APP_NAME = "BiometricServer"
MAIN_SCRIPT = "biometric_server_gui.py"
ICON_FILE = "biometric.ico"  # Optional, create your own icon

# PyInstaller options
PYINSTALLER_OPTIONS = [
    '--onefile',           # Single executable file
    '--windowed',          # No console window
    '--clean',             # Clean PyInstaller cache
    '--noconfirm',         # Replace output directory without confirmation
    f'--name={APP_NAME}',  # Name of the executable
    '--add-data=biometric.ico;.' if os.path.exists('biometric.ico') else '',  # Include icon if exists
]

# Hidden imports that PyInstaller might miss
HIDDEN_IMPORTS = [
    'websockets',
    'asyncio', 
    'sqlite3',
    'requests',
    'csv',
    'logging.handlers',
    'tkinter',
    'tkinter.filedialog',  # Add this
    'queue',
    'json',  # Add this
]


def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'pyinstaller',
        'websockets',
        'requests',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Installing missing packages...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        print("Packages installed successfully!")
    else:
        print("All required packages are installed.")


def create_spec_file():
    """Create a PyInstaller spec file for advanced configuration"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{MAIN_SCRIPT}'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.')] if os.path.exists('config.json') else [],
    hiddenimports={HIDDEN_IMPORTS},
    hookspath=[],
    hooksconfig={{}},
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
    name='{APP_NAME}',
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
'''
    
    with open(f'{APP_NAME}.spec', 'w') as f:
        f.write(spec_content)
    
    print(f"Created {APP_NAME}.spec file")


def build_executable():
    """Build the executable using PyInstaller"""
    print("\n" + "="*60)
    print(f"Building {APP_NAME}.exe...")
    print("="*60 + "\n")
    
    # Check if spec file exists, otherwise create it
    if not os.path.exists(f'{APP_NAME}.spec'):
        create_spec_file()
    
    # Build using spec file
    cmd = ['pyinstaller', f'{APP_NAME}.spec']
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*60)
        print("Build completed successfully!")
        print(f"Executable location: dist/{APP_NAME}.exe")
        print("="*60)
        
        # Create a batch file for easy testing
        create_test_batch()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        return False


def create_test_batch():
    """Create a batch file for testing the executable"""
    batch_content = f'''@echo off
echo Starting {APP_NAME}...
cd /d "%~dp0"
start "" "dist\\{APP_NAME}.exe"
'''
    
    with open('run_biometric_server.bat', 'w') as f:
        f.write(batch_content)
    
    print("Created run_biometric_server.bat for easy testing")


def create_installer_script():
    """Create an Inno Setup script for creating an installer (optional)"""
    iss_content = f'''[Setup]
AppName={APP_NAME}
AppVersion=1.0
DefaultDirName={{autopf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
UninstallDisplayIcon={{app}}\\{APP_NAME}.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename={APP_NAME}_Setup

[Files]
Source: "dist\\{APP_NAME}.exe"; DestDir: "{{app}}"

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
Name: "{{group}}\\Uninstall {APP_NAME}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{{app}}\\{APP_NAME}.exe"; Description: "Launch {APP_NAME}"; Flags: postinstall nowait skipifsilent
'''
    
    with open(f'{APP_NAME}_installer.iss', 'w') as f:
        f.write(iss_content)
    
    print(f"Created {APP_NAME}_installer.iss for Inno Setup (optional)")


def clean_build():
    """Clean build artifacts"""
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = [f'{APP_NAME}.spec']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name}/")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"Removed {file_name}")


def main():
    """Main build process"""
    print("="*60)
    print(f"Building {APP_NAME} Windows Executable")
    print("="*60 + "\n")
    
    # Check if main script exists
    if not os.path.exists(MAIN_SCRIPT):
        print(f"Error: {MAIN_SCRIPT} not found!")
        print("Make sure the biometric_server_gui.py file is in the same directory.")
        sys.exit(1)
    
    # Check and install requirements
    check_requirements()
    
    # Clean previous builds (optional)
    if '--clean' in sys.argv:
        print("\nCleaning previous build artifacts...")
        clean_build()
    
    # Build the executable
    if build_executable():
        print("\n" + "="*60)
        print("BUILD SUCCESS!")
        print("="*60)
        print(f"\nYour executable is ready at: dist/{APP_NAME}.exe")
        print("\nYou can:")
        print("1. Run the executable directly from dist/ folder")
        print("2. Use run_biometric_server.bat to test it")
        print("3. Create an installer using Inno Setup (optional)")
        
        # Create installer script (optional)
        create_installer_script()
    else:
        print("\n" + "="*60)
        print("BUILD FAILED!")
        print("="*60)
        print("\nPlease check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
