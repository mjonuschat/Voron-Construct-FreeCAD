import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Construct"))
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent
        / "tools"
        / "fusion_export"
        / "FusionStepExport"
    ),
)
