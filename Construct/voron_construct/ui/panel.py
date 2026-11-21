"""Dock panel for browsing the Construct library and importing parts."""

from __future__ import annotations

import posixpath

from PySide6 import QtCore, QtGui, QtWidgets

from ..controller import Controller
from ..library import Folder, Part, search
from ..settings import Settings, SettingsStore
from .settings_dialog import SettingsDialog
from .tree_model import FolderTreeModel

THUMBNAIL_SIZE = 128


def _format_size(size: int | None) -> str:
    if size is None:
        return ""
    if size < 1024:
        return f"{size} bytes"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class ConstructPanel(QtWidgets.QDockWidget):
    def __init__(
        self,
        controller: Controller,
        store: SettingsStore,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__("Construct", parent)
        self.setObjectName("ConstructPanel")
        self._controller = controller
        self._store = store
        self._settings: Settings = store.load()
        self._library: Folder | None = None
        self._load_generation = 0
        self._current: Part | None = None
        self._busy = 0

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search")
        self._search.setClearButtonEnabled(True)
        self._settings_button = QtWidgets.QToolButton()
        self._settings_button.setText("Settings")
        self._settings_button.setToolTip("Construct settings")

        self._model = FolderTreeModel(self)
        self._tree = QtWidgets.QTreeView()
        self._tree.setHeaderHidden(True)
        self._tree.setModel(self._model)

        self._thumbnail = QtWidgets.QLabel()
        self._thumbnail.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        self._thumbnail.setAlignment(QtCore.Qt.AlignCenter)
        self._thumbnail.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._badge = QtWidgets.QLabel()
        self._badge.setStyleSheet("font-weight: bold;")
        self._path = QtWidgets.QLabel()
        self._path.setWordWrap(True)
        self._path.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self._size = QtWidgets.QLabel()
        self._repo = QtWidgets.QLabel()
        self._import_button = QtWidgets.QPushButton("Import")
        self._open_button = QtWidgets.QPushButton("Open")
        self._status = QtWidgets.QLabel()
        self._status.setWordWrap(True)
        close_button = QtWidgets.QPushButton("Close")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self._search)
        top.addWidget(self._settings_button)

        info = QtWidgets.QVBoxLayout()
        info.addWidget(self._badge)
        info.addWidget(self._path)
        info.addWidget(self._size)
        info.addWidget(self._repo)
        info.addStretch(1)
        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self._import_button)
        actions.addWidget(self._open_button)
        info.addLayout(actions)
        detail = QtWidgets.QHBoxLayout()
        detail.addWidget(self._thumbnail)
        detail.addLayout(info, 1)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self._status, 1)
        bottom.addWidget(close_button)

        self._content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._content)
        layout.addLayout(top)
        layout.addWidget(self._tree, 1)
        layout.addLayout(detail)
        layout.addLayout(bottom)
        self.setWidget(self._content)

        self._search.textChanged.connect(self._apply_filter)
        self._settings_button.clicked.connect(self._edit_settings)
        self._tree.selectionModel().currentChanged.connect(self._on_current_changed)
        self._model.thumbnail_requested.connect(
            self._fetch_row_thumbnail, QtCore.Qt.QueuedConnection
        )
        self._import_button.clicked.connect(self._import)
        self._open_button.clicked.connect(self._open)
        close_button.clicked.connect(self.close)

        self._apply_view_settings()
        self._show_details(None)
        self._reload()

    # Loading and filtering

    def _reload(self) -> None:
        self._load_generation += 1
        generation = self._load_generation
        self._library = None
        self._status.clear()
        self._model.set_root(Folder("", ""), self._settings.repo)
        self._show_details(None)

        def loaded(folder: Folder) -> None:
            if generation == self._load_generation:
                self._library = folder
                self._apply_filter()

        def failed(message: str) -> None:
            if generation == self._load_generation:
                self._status.setText(message)

        self._controller.load(self._settings, loaded, failed)

    def _apply_filter(self) -> None:
        if self._library is None:
            return
        text = self._search.text().strip()
        self._model.set_root(
            search(self._library, text, self._settings.search_folders),
            self._settings.repo,
        )
        if text:
            self._tree.expandAll()
        else:
            self._tree.expand(self._model.index(0, 0))
        self._show_details(None)

    def _apply_view_settings(self) -> None:
        font = QtGui.QFont()
        if self._settings.font_size > 0:
            font.setPointSize(self._settings.font_size)
        self._content.setFont(font)
        self._model.set_show_thumbnails(self._settings.show_thumbnails)
        self._model.set_hide_unsupported(self._settings.hide_unsupported)

    def _edit_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        old, new = self._settings, dialog.settings()
        self._store.save(new)
        self._settings = new
        self._apply_view_settings()
        if self._controller.apply_settings(old, new):
            self._reload()
        else:
            self._apply_filter()

    # Thumbnails and details

    def _fetch_row_thumbnail(self, part: Part) -> None:
        self._controller.thumbnail(
            self._settings, part, lambda path: self._model.set_thumbnail(part, path)
        )

    def _on_current_changed(self, current: QtCore.QModelIndex, _previous) -> None:
        self._show_details(self._model.part_at(current))

    def _show_details(self, part: Part | None) -> None:
        self._current = part
        self._thumbnail.clear()
        if part is None:
            for label in (self._badge, self._path, self._size, self._repo):
                label.clear()
        else:
            path = part.step_path or (part.source_paths[0] if part.source_paths else "")
            self._badge.setText(posixpath.splitext(path)[1].upper())
            self._path.setText(path)
            self._size.setText(_format_size(part.size))
            self._repo.setText(self._settings.repo)
            self._thumbnail.setText("No preview")
            if part.thumb_path:
                self._controller.thumbnail(
                    self._settings, part, lambda p: self._set_detail_thumbnail(part, p)
                )
        self._update_buttons()

    def _set_detail_thumbnail(self, part: Part, path) -> None:
        if part is not self._current or not path:
            return
        pixmap = QtGui.QPixmap(str(path))
        if pixmap.isNull():
            return
        self._thumbnail.setPixmap(
            pixmap.scaled(
                THUMBNAIL_SIZE,
                THUMBNAIL_SIZE,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        )

    def _update_buttons(self) -> None:
        enabled = (
            self._current is not None and self._current.importable and self._busy == 0
        )
        self._import_button.setEnabled(enabled)
        self._open_button.setEnabled(enabled)

    # Import and open

    def _import(self) -> None:
        self._run_step(self._controller.import_part)

    def _open(self) -> None:
        self._run_step(self._controller.open_part)

    def _run_step(self, action) -> None:
        part = self._current
        if part is None or not part.importable:
            return
        self._busy += 1
        self._status.setText("Downloading...")
        self._update_buttons()

        def done() -> None:
            self._busy -= 1
            self._status.clear()
            self._update_buttons()

        def failed(message: str) -> None:
            self._busy -= 1
            self._status.setText(message)
            self._update_buttons()

        action(self._settings, part, done, failed)


def create_panel(parent: QtWidgets.QWidget | None = None) -> ConstructPanel:
    """Build the panel wired to GitHub, the cache, FreeCAD settings and the importer."""
    from .. import importer
    from ..cache import Cache, default_cache_root
    from ..github import GitHubClient
    from ..settings import FreeCADBackend
    from .threads import run_async

    controller = Controller(
        client_factory=lambda s: GitHubClient(s.token),
        cache=Cache(default_cache_root()),
        import_fn=importer.import_step,
        open_fn=importer.open_step,
        run_async=run_async,
    )
    return ConstructPanel(controller, SettingsStore(FreeCADBackend()), parent)
