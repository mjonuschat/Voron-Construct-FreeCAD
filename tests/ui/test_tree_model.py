import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6 import QtCore, QtGui, QtWidgets
from voron_construct.library import Folder, Part
from voron_construct.ui.tree_model import FolderTreeModel

Qt = QtCore.Qt


@pytest.fixture(scope="module", autouse=True)
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _part(name, directory, step=True):
    return Part(
        name=name,
        dir=directory,
        step_path=f"{directory}/{name}.step" if step else None,
        source_paths=[] if step else [f"{directory}/{name}.f3d"],
        thumb_path=None,
        size=10,
    )


def _library():
    good = _part("Bracket", "Printed")
    fusion_only = _part("Hinge", "Fusion", step=False)
    top = _part("Cover", "")
    return Folder(
        "",
        "",
        folders=[
            Folder("Fusion", "Fusion", parts=[fusion_only]),
            Folder("Printed", "Printed", parts=[good]),
        ],
        parts=[top],
    )


def _model(**options):
    model = FolderTreeModel()
    if options.get("hide_unsupported"):
        model.set_hide_unsupported(True)
    model.set_root(_library(), "owner/repo")
    return model


def _child_names(model, parent):
    return [model.index(r, 0, parent).data() for r in range(model.rowCount(parent))]


def test_rows_and_part_lookup():
    model = _model()
    assert model.rowCount() == 1
    repo = model.index(0, 0)
    assert repo.data() == "owner/repo"
    assert model.part_at(repo) is None
    assert _child_names(model, repo) == ["Fusion", "Printed", "Cover"]

    printed = model.index(1, 0, repo)
    assert model.part_at(printed) is None
    assert model.rowCount(printed) == 1
    bracket = model.index(0, 0, printed)
    assert bracket.data() == "Bracket"
    assert model.part_at(bracket).step_path == "Printed/Bracket.step"
    assert model.parent(bracket) == printed
    assert model.parent(repo) == QtCore.QModelIndex()
    assert model.part_at(QtCore.QModelIndex()) is None


def test_unsupported_part_is_grey_and_has_tooltip():
    model = _model()
    repo = model.index(0, 0)
    hinge = model.index(0, 0, model.index(0, 0, repo))
    bracket = model.index(0, 0, model.index(1, 0, repo))
    assert hinge.data() == "Hinge"

    grey = hinge.data(Qt.ForegroundRole)
    assert grey is not None
    assert QtGui.QBrush(grey).color() == QtGui.QColor(Qt.gray)
    assert "FreeCAD cannot read" in hinge.data(Qt.ToolTipRole)

    assert bracket.data(Qt.ForegroundRole) is None
    assert "cannot read" not in (bracket.data(Qt.ToolTipRole) or "")


def test_hide_unsupported_filters_rows():
    model = _model(hide_unsupported=True)
    repo = model.index(0, 0)
    assert _child_names(model, repo) == ["Printed", "Cover"]

    model.set_hide_unsupported(False)
    repo = model.index(0, 0)
    assert _child_names(model, repo) == ["Fusion", "Printed", "Cover"]
