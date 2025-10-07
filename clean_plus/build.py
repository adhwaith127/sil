#!/usr/bin/env python3
"""
Fixed Build script for creating Windows executable from Biometric Server GUI
This script properly handles all dependencies and PyInstaller configuration
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Build configuration
APP_NAME = "BiometricServer"
MAIN_SCRIPT = "biometric_server_gui.py"
ICON_FILE = "biometric.ico"

# Additional Python modules that are part of your application
ADDITIONAL_MODULES = [
    'config_manager.py',
    'settings_dialog.py',
]

# Hidden imports that PyInstaller might miss
HIDDEN_IMPORTS = [
    'websockets',
    'websockets.legacy',
    'websockets.legacy.server',
    'websockets.legacy.protocol',
    'asyncio',
    'sqlite3',
    'requests',
    'csv',
    'logging.handlers',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'queue',
    'json',
    'datetime',
    'threading',
    'weakref',
    'platform',
    'socket',
    'signal',
]

# Platform-specific excludes
EXCLUDES = []
if sys.platform == 'win32':
    EXCLUDES.append('fcntl')  # Linux-only module
else:
    EXCLUDES.append('msvcrt')  # Windows-only module


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


def check_required_files():
    """Check if all required files exist"""
    missing_files = []
    
    # Check main script
    if not os.path.exists(MAIN_SCRIPT):
        missing_files.append(MAIN_SCRIPT)
    
    # Check additional modules
    for module in ADDITIONAL_MODULES:
        if not os.path.exists(module):
            missing_files.append(module)
    
    if missing_files:
        print("\nERROR: Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nMake sure all files are in the same directory as build.py")
        return False
    
    return True


def create_spec_file():
    """Create a PyInstaller spec file with proper configuration"""
    
    # Collect data files
    datas_list = []
    if os.path.exists('config.json'):
        datas_list.append("('config.json', '.')")
    if os.path.exists(ICON_FILE):
        datas_list.append(f"('{ICON_FILE}', '.')")
    
    datas_str = '[' + ', '.join(datas_list) + ']' if datas_list else '[]'
    
    # Create module list string
    modules_list = [f"'{MAIN_SCRIPT}'"] + [f"'{m}'" for m in ADDITIONAL_MODULES]
    modules_str = '[' + ', '.join(modules_list) + ']'
    
    # Icon path for EXE
    icon_path = f"'{ICON_FILE}'" if os.path.exists(ICON_FILE) else 'None'
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

a = Analysis(
    {modules_str},
    pathex=[],
    binaries=[],
    datas={datas_str},
    hiddenimports={HIDDEN_IMPORTS},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={EXCLUDES},
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon_path},
)
'''
    
    with open(f'{APP_NAME}.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"Created {APP_NAME}.spec file")
    return True


def build_executable():
    """Build the executable using PyInstaller"""
    print("\n" + "="*60)
    print(f"Building {APP_NAME}.exe...")
    print("="*60 + "\n")
    
    # Create spec file
    if not create_spec_file():
        return False
    
    # Build using spec file
    cmd = ['pyinstaller', '--clean', '--noconfirm', f'{APP_NAME}.spec']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("Build completed successfully!")
            print(f"Executable location: dist/{APP_NAME}.exe")
            print("="*60)
            
            # Verify the executable was created
            exe_path = os.path.join('dist', f'{APP_NAME}.exe')
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\nExecutable size: {size_mb:.2f} MB")
                create_test_batch()
                return True
            else:
                print("\nWARNING: Build reported success but executable not found!")
                return False
        else:
            print("\n" + "="*60)
            print("Build failed!")
            print("="*60)
            print("\nError output:")
            print(result.stderr)
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print("\nError details:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"\nUnexpected error during build: {e}")
        return False


def create_test_batch():
    """Create a batch file for testing the executable"""
    batch_content = f'''@echo off
echo Starting {APP_NAME}...
cd /d "%~dp0"
if exist "dist\\{APP_NAME}.exe" (
    start "" "dist\\{APP_NAME}.exe"
) else (
    echo ERROR: {APP_NAME}.exe not found in dist folder!
    pause
)
'''
    
    with open('run_biometric_server.bat', 'w') as f:
        f.write(batch_content)
    
    print("Created run_biometric_server.bat for easy testing")


def create_debug_batch():
    """Create a batch file that runs the EXE with console output visible"""
    batch_content = f'''@echo off
echo Starting {APP_NAME} in debug mode (with console)...
cd /d "%~dp0"
if exist "dist\\{APP_NAME}.exe" (
    "dist\\{APP_NAME}.exe"
    echo.
    echo Program exited. Press any key to close...
    pause > nul
) else (
    echo ERROR: {APP_NAME}.exe not found in dist folder!
    pause
)
'''
    
    with open('run_biometric_server_debug.bat', 'w') as f:
        f.write(batch_content)
    
    print("Created run_biometric_server_debug.bat for debugging")


def clean_build():
    """Clean build artifacts"""
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = [f'{APP_NAME}.spec']
    
    print("\nCleaning build artifacts...")
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"Removed {dir_name}/")
            except Exception as e:
                print(f"Warning: Could not remove {dir_name}: {e}")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                print(f"Removed {file_name}")
            except Exception as e:
                print(f"Warning: Could not remove {file_name}: {e}")


def main():
    """Main build process"""
    print("="*60)
    print(f"Building {APP_NAME} Windows Executable")
    print("="*60 + "\n")
    
    # Check if required files exist
    if not check_required_files():
        sys.exit(1)
    
    # Check and install requirements
    print("\nChecking requirements...")
    check_requirements()
    
    # Clean previous builds if requested
    if '--clean' in sys.argv:
        clean_build()
    
    # Build the executable
    print("\nStarting build process...")
    if build_executable():
        create_debug_batch()
        
        print("\n" + "="*60)
        print("BUILD SUCCESS!")
        print("="*60)
        print(f"\nYour executable is ready at: dist/{APP_NAME}.exe")
        print("\nNext steps:")
        print("1. Test it using: run_biometric_server.bat")
        print("2. If issues occur, use: run_biometric_server_debug.bat")
        print("3. Deploy the dist/ folder contents to your target machine")
        print("\nNote: The executable needs to create/access these folders:")
        print("  - E:\\BiometricServer\\logs")
        print("  - E:\\BiometricServer\\database")
        print("  - E:\\BiometricServer\\queue")
        print("  Ensure proper permissions on the target machine.")
        
    else:
        print("\n" + "="*60)
        print("BUILD FAILED!")
        print("="*60)
        print("\nTroubleshooting:")
        print("1. Check that all .py files are present")
        print("2. Ensure all packages are installed (websockets, requests)")
        print("3. Try running with --clean flag: python build.py --clean")
        print("4. Check the error messages above for specific issues")
        sys.exit(1)


if __name__ == "__main__":
    main()