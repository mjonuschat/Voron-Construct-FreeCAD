"""Find Fusion archives that have no STEP file next to them (standard library only)."""

import os
from pathlib import Path

SOURCE_EXTENSIONS = {".f3d", ".f3z"}
STEP_EXTENSIONS = {".step", ".stp"}


def find_missing(root: Path) -> list[Path]:
    """Return sorted .f3d/.f3z files under root lacking a same-named .step/.stp."""
    missing = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        steps = {
            Path(n).stem for n in filenames if Path(n).suffix.lower() in STEP_EXTENSIONS
        }
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() in SOURCE_EXTENSIONS and path.stem not in steps:
                missing.append(path)
    return sorted(missing)


def step_target(source: Path) -> Path:
    """Return the .step path next to source."""
    return source.with_suffix(".step")
