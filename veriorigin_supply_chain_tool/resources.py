import sys
from pathlib import Path

def bundled_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent