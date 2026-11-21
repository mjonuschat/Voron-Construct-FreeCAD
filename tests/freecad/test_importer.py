"""Importer tests. They need FreeCAD: run them with scripts/run_freecad_tests.sh."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Construct"))

import FreeCAD as App
from voron_construct.importer import ImportFailed, import_step, open_step

SHIM_WASHER = Path(__file__).resolve().parents[1] / "data" / "m5_shim_washer.step"


def _close_all_documents():
    for name in list(App.listDocuments()):
        App.closeDocument(name)


def test_import_adds_part_with_shapes():
    _close_all_documents()
    doc = App.newDocument("ImportTarget")
    name = import_step(SHIM_WASHER, doc)
    part = doc.getObject(name)
    assert part is not None
    assert part.TypeId == "App::Part"
    assert part.Label == "m5_shim_washer"
    shapes = [
        o for o in part.OutListRecursive if hasattr(o, "Shape") and not o.Shape.isNull()
    ]
    assert shapes, "imported part contains no object with a shape"
    _close_all_documents()


def test_import_creates_document_when_none():
    _close_all_documents()
    name = import_step(SHIM_WASHER)
    doc = App.ActiveDocument
    assert doc is not None
    assert doc.getObject(name).TypeId == "App::Part"
    _close_all_documents()


def test_failed_import_rolls_back():
    _close_all_documents()
    doc = App.newDocument("RollbackTarget")
    doc.addObject("Part::Box", "Box")
    doc.recompute()
    count = len(doc.Objects)
    with tempfile.TemporaryDirectory() as tmp:
        garbage = Path(tmp) / "garbage.step"
        garbage.write_text("this is not a STEP file\n")
        try:
            import_step(garbage, doc)
        except ImportFailed as exc:
            assert exc.path == garbage
        else:
            raise AssertionError("ImportFailed not raised")
    assert len(doc.Objects) == count
    _close_all_documents()


def test_open_step_new_document():
    _close_all_documents()
    name = open_step(SHIM_WASHER)
    assert name in App.listDocuments()
    doc = App.getDocument(name)
    assert any(hasattr(o, "Shape") and not o.Shape.isNull() for o in doc.Objects)
    _close_all_documents()
