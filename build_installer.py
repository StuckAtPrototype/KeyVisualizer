"""
Build script that creates both the executable and the installer.

This script:
1. Builds the KeyVisualizer.exe using PyInstaller
2. Creates a Windows installer using Inno Setup

Requirements:
- PyInstaller (pip install pyinstaller)
- Inno Setup (download from https://jrsoftware.org/isdl.php)

Usage:
    python build_installer.py
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_inno_setup():
    """Check if Inno Setup is installed and return the compiler path."""
    # Common Inno Setup installation paths
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def build_exe():
    """Build the executable using PyInstaller."""
    print("=" * 60)
    print("STEP 1: Building executable with PyInstaller")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "KeyVisualizer",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
    ]
    
    # Add icon if present
    icon_path = os.path.join(script_dir, "keyvisualizer.ico")
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
        print(f"Using icon: {icon_path}")
    else:
        print("No icon file found (keyvisualizer.ico)")
    
    # Hidden imports
    hidden_imports = [
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "pynput.keyboard",
        "pynput.keyboard._win32",
        "pynput.mouse",
        "pynput.mouse._win32",
        "pynput._util",
        "pynput._util.win32",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Add main script
    cmd.append("keyVisualizer.py")
    
    print("\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("\n" + "=" * 60)
        print("ERROR: PyInstaller build failed!")
        print("=" * 60)
        sys.exit(1)
    
    # Check if exe was created
    exe_path = os.path.join(script_dir, "dist", "KeyVisualizer.exe")
    if not os.path.exists(exe_path):
        print("\n" + "=" * 60)
        print("ERROR: Executable was not created!")
        print("=" * 60)
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Executable built successfully!")
    print(f"Location: {exe_path}")
    print(f"Size: {os.path.getsize(exe_path) / (1024*1024):.1f} MB")
    print("=" * 60)
    return True


def build_installer():
    """Build the installer using Inno Setup."""
    print("\n" + "=" * 60)
    print("STEP 2: Building installer with Inno Setup")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if Inno Setup is installed
    iscc_path = check_inno_setup()
    if not iscc_path:
        print("\nERROR: Inno Setup not found!")
        print("\nPlease install Inno Setup from:")
        print("https://jrsoftware.org/isdl.php")
        print("\nAfter installation, run this script again.")
        sys.exit(1)
    
    print(f"Found Inno Setup: {iscc_path}")
    
    # Check if .iss file exists
    iss_file = os.path.join(script_dir, "installer.iss")
    if not os.path.exists(iss_file):
        print(f"\nERROR: Inno Setup script not found: {iss_file}")
        sys.exit(1)
    
    # Check if exe exists
    exe_path = os.path.join(script_dir, "dist", "KeyVisualizer.exe")
    if not os.path.exists(exe_path):
        print("\nERROR: KeyVisualizer.exe not found in dist folder!")
        print("Please run build step 1 first.")
        sys.exit(1)
    
    # Check if LICENSE file exists
    license_path = os.path.join(script_dir, "LICENSE")
    if not os.path.exists(license_path):
        print("\nERROR: LICENSE file not found!")
        print("Please ensure LICENSE file exists before building installer.")
        sys.exit(1)
    
    # Run Inno Setup
    print("\nRunning Inno Setup compiler...")
    cmd = [iscc_path, iss_file]
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("\n" + "=" * 60)
        print("ERROR: Installer build failed!")
        print("=" * 60)
        sys.exit(1)
    
    # Find the created installer
    installer_output = os.path.join(script_dir, "installer_output")
    if os.path.exists(installer_output):
        installers = list(Path(installer_output).glob("KeyVisualizer_Setup_*.exe"))
        if installers:
            installer_path = installers[0]
            print("\n" + "=" * 60)
            print("INSTALLER BUILD SUCCESSFUL!")
            print("=" * 60)
            print(f"\nInstaller location: {installer_path}")
            print(f"Size: {os.path.getsize(installer_path) / (1024*1024):.1f} MB")
            print("\nYou can now distribute this installer to users!")
            print("=" * 60)
            return True
    
    print("\n" + "=" * 60)
    print("WARNING: Installer may have been created but not found")
    print("Check the installer_output folder")
    print("=" * 60)
    return False


def main():
    print("=" * 60)
    print("KeyVisualizer Installer Builder")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Build KeyVisualizer.exe using PyInstaller")
    print("2. Create a Windows installer using Inno Setup")
    print("\n" + "=" * 60 + "\n")
    
    # Build exe
    if not build_exe():
        sys.exit(1)
    
    # Build installer
    if not build_installer():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("ALL BUILDS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
