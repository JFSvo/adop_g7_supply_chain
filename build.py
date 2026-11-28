# Build VeriOrigin into a single executable for the system you run this on.

    # python build.py            # tests, then dist/veriorigin_analyzer(.exe)
    # python build.py --skip-tests

# PyInstaller cannot cross-compile: run this on Windows to get the Windows .exe,
# and on Linux to get the Linux executable. The same command works on both.
# """

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "veriorigin_supply_chain_tool"


def run(*args, cwd=ROOT):
    print("==>", " ".join(map(str, args)), flush=True)
    subprocess.run([sys.executable, *map(str, args)], cwd=cwd, check=True)


def main():
    # pillow converts the PNG icon for Windows; harmless on Linux
    run("-m", "pip", "install", "--quiet", "pyinstaller", "PySide6", "pillow", "pytest")
    if "--skip-tests" not in sys.argv:
        run("-m", "pytest", "-q", "test_provenance_analysis.py", cwd=TOOL)  # never package failing code
    run("-m", "PyInstaller", "--noconfirm", "--clean", "veriorigin_analyzer.spec")
    exe = ROOT / "dist" / ("veriorigin_analyzer.exe" if sys.platform == "win32" else "veriorigin_analyzer")
    if not exe.is_file():
        sys.exit(f"Build finished but {exe} was not created")
    print(f"\nBuilt {exe.relative_to(ROOT)} ({exe.stat().st_size / 2**20:.0f} MB)")


if __name__ == "__main__":
    main()
