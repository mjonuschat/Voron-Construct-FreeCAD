"""STEP import into FreeCAD documents. Needs the FreeCAD API."""

from pathlib import Path

import FreeCAD as App
import Import

if App.GuiUp:
    import FreeCADGui  # noqa: F401
    import ImportGui

# Import mode 0 puts everything in the target document. The user's preference may be
# a multi-document mode, which writes files next to the document and asks to save
# it first.
SINGLE_DOCUMENT = 0


class ImportFailed(Exception):
    def __init__(self, path: Path, reason: str):
        super().__init__(f"Could not import {path}: {reason}")
        self.path = path
        self.reason = reason


def import_step(path: Path, doc=None) -> str:
    """Import the STEP into a new App::Part labelled with the file's base name.

    Uses `doc`, else the active document, else a new document. Returns the part's Name.
    On failure the transaction is aborted, the document is unchanged and
    ImportFailed is raised.
    """
    path = Path(path)
    if doc is None:
        doc = App.ActiveDocument or App.newDocument()
    doc.openTransaction(f"Import {path.name}")
    try:
        before = {obj.Name for obj in doc.Objects}
        part = doc.addObject("App::Part", "Part")
        part.Label = path.stem
        (ImportGui if App.GuiUp else Import).insert(
            str(path), doc.Name, mode=SINGLE_DOCUMENT
        )
        created = [
            obj for obj in doc.Objects if obj.Name not in before and obj is not part
        ]
        created_names = {obj.Name for obj in created}
        for obj in created:
            if not any(parent.Name in created_names for parent in obj.InList):
                part.addObject(obj)
        doc.recompute()
    except Exception as exc:
        doc.abortTransaction()
        raise ImportFailed(path, str(exc)) from exc
    doc.commitTransaction()
    return part.Name


def open_step(path: Path) -> str:
    """Open the STEP as a new document; returns the document's Name."""
    path = Path(path)
    doc = App.newDocument(path.stem)
    try:
        (ImportGui if App.GuiUp else Import).insert(
            str(path), doc.Name, mode=SINGLE_DOCUMENT
        )
    except Exception as exc:
        App.closeDocument(doc.Name)
        raise ImportFailed(path, str(exc)) from exc
    doc.recompute()
    return doc.Name
