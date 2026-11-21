"""Qt item model showing the library as repo root, folders and parts."""

from __future__ import annotations

import posixpath

from PySide6 import QtCore, QtGui, QtWidgets

from ..library import Folder, Part

Qt = QtCore.Qt
_NO_PARENT = QtCore.QModelIndex()

UNSUPPORTED_TOOLTIP = (
    "Only a Fusion 360 file ({}) is available. FreeCAD cannot read it."
)


def _part_key(part: Part) -> tuple[str, str]:
    return part.dir, part.name


class _Node:
    __slots__ = ("children", "name", "parent", "part", "row")

    def __init__(
        self, name: str, part: Part | None, parent: _Node | None, row: int
    ) -> None:
        self.name = name
        self.part = part
        self.parent = parent
        self.children: list[_Node] = []
        self.row = row


class FolderTreeModel(QtCore.QAbstractItemModel):
    """One root row named after the repo; folders first, then parts."""

    # Emitted when a part row needs its thumbnail; answer with set_thumbnail().
    thumbnail_requested = QtCore.Signal(object)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._folder: Folder | None = None
        self._repo_name = ""
        self._hide_unsupported = False
        self._show_thumbnails = False
        self._roots: list[_Node] = []
        self._part_nodes: dict[tuple[str, str], _Node] = {}
        self._thumbnails: dict[tuple[str, str], QtGui.QIcon | None] = {}
        self._requested: set[tuple[str, str]] = set()

    # Configuration

    def set_root(self, folder: Folder, repo_name: str = "") -> None:
        if repo_name != self._repo_name:
            self._thumbnails.clear()
            self._requested.clear()
        self._folder = folder
        self._repo_name = repo_name
        self._rebuild()

    def set_hide_unsupported(self, hide: bool) -> None:
        if hide != self._hide_unsupported:
            self._hide_unsupported = hide
            self._rebuild()

    def set_show_thumbnails(self, show: bool) -> None:
        if show != self._show_thumbnails:
            self._show_thumbnails = show
            self._rebuild()

    def set_thumbnail(self, part: Part, path) -> None:
        key = _part_key(part)
        self._thumbnails[key] = QtGui.QIcon(QtGui.QPixmap(str(path))) if path else None
        node = self._part_nodes.get(key)
        if node is not None:
            index = self.createIndex(node.row, 0, node)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])

    def part_at(self, index: QtCore.QModelIndex) -> Part | None:
        if not index.isValid():
            return None
        return index.internalPointer().part

    # Tree building

    def _rebuild(self) -> None:
        self.beginResetModel()
        self._roots = []
        self._part_nodes = {}
        if self._folder is not None:
            root = _Node(self._repo_name, None, None, 0)
            self._fill(root, self._folder)
            self._roots = [root]
        self.endResetModel()

    def _fill(self, node: _Node, folder: Folder) -> bool:
        """Add the visible content of `folder` to `node`; True if any was added."""
        for sub in folder.folders:
            child = _Node(sub.name, None, node, len(node.children))
            if self._fill(child, sub):
                node.children.append(child)
        for part in folder.parts:
            if self._hide_unsupported and not part.importable:
                continue
            child = _Node(part.name, part, node, len(node.children))
            node.children.append(child)
            self._part_nodes[_part_key(part)] = child
        return bool(node.children)

    # QAbstractItemModel

    def index(self, row: int, column: int, parent=_NO_PARENT) -> QtCore.QModelIndex:
        children = (
            parent.internalPointer().children if parent.isValid() else self._roots
        )
        if column != 0 or not 0 <= row < len(children):
            return QtCore.QModelIndex()
        return self.createIndex(row, 0, children[row])

    def parent(self, index=_NO_PARENT) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        parent = index.internalPointer().parent
        if parent is None:
            return QtCore.QModelIndex()
        return self.createIndex(parent.row, 0, parent)

    def rowCount(self, parent=_NO_PARENT) -> int:
        if parent.column() > 0:
            return 0
        return (
            len(parent.internalPointer().children)
            if parent.isValid()
            else len(self._roots)
        )

    def columnCount(self, parent=_NO_PARENT) -> int:
        return 1

    def data(self, index: QtCore.QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        node: _Node = index.internalPointer()
        part = node.part
        if role == Qt.DisplayRole:
            return node.name
        if role == Qt.DecorationRole:
            return self._icon(part)
        if part is None:
            return None
        if role == Qt.ForegroundRole and not part.importable:
            return QtGui.QBrush(QtGui.QColor(Qt.gray))
        if role == Qt.ToolTipRole:
            if part.importable:
                return part.step_path
            ext = (
                posixpath.splitext(part.source_paths[0])[1]
                if part.source_paths
                else ".f3d"
            )
            return UNSUPPORTED_TOOLTIP.format(ext)
        return None

    def _icon(self, part: Part | None) -> QtGui.QIcon:
        style = QtWidgets.QApplication.style()
        if part is None:
            return style.standardIcon(QtWidgets.QStyle.SP_DirIcon)
        if self._show_thumbnails and part.thumb_path:
            key = _part_key(part)
            icon = self._thumbnails.get(key)
            if icon is not None:
                return icon
            if key not in self._requested:
                self._requested.add(key)
                self.thumbnail_requested.emit(part)
        return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
