"""Dialog for editing the Construct browser settings."""

from __future__ import annotations

from PySide6 import QtWidgets

from ..settings import Settings, validate_repo


class SettingsDialog(QtWidgets.QDialog):
    def __init__(
        self, settings: Settings, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Construct Settings")

        self._repo = QtWidgets.QLineEdit(settings.repo)
        self._repo.setPlaceholderText("owner/repo")
        self._repo_error = QtWidgets.QLabel()
        self._repo_error.setStyleSheet("color: red;")
        self._repo_error.setVisible(False)
        self._branch = QtWidgets.QLineEdit(settings.branch)
        self._branch.setPlaceholderText("Repository default")
        self._token = QtWidgets.QLineEdit(settings.token)
        self._token.setEchoMode(QtWidgets.QLineEdit.Password)
        self._token.setPlaceholderText("Optional, raises the rate limit")
        self._font_size = QtWidgets.QSpinBox()
        self._font_size.setRange(0, 48)
        self._font_size.setSpecialValueText("System")
        self._font_size.setValue(settings.font_size)
        self._show_thumbnails = QtWidgets.QCheckBox("Show thumbnails")
        self._show_thumbnails.setChecked(settings.show_thumbnails)
        self._search_folders = QtWidgets.QCheckBox("Search folder names")
        self._search_folders.setChecked(settings.search_folders)
        self._hide_unsupported = QtWidgets.QCheckBox("Hide unsupported parts")
        self._hide_unsupported.setChecked(settings.hide_unsupported)

        form = QtWidgets.QFormLayout()
        form.addRow("Repository:", self._repo)
        form.addRow("", self._repo_error)
        form.addRow("Branch:", self._branch)
        form.addRow("GitHub access token:", self._token)
        form.addRow("Font size:", self._font_size)
        form.addRow("", self._show_thumbnails)
        form.addRow("", self._search_folders)
        form.addRow("", self._hide_unsupported)

        self._buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._buttons)

        self._repo.textChanged.connect(self._validate)
        self._validate()

    def _validate(self) -> None:
        try:
            validate_repo(self._repo.text())
        except ValueError:
            self._repo_error.setText(
                "Enter the repository as owner/repo or a GitHub URL."
            )
            self._repo_error.setVisible(True)
            valid = False
        else:
            self._repo_error.setVisible(False)
            valid = True
        self._buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(valid)

    def settings(self) -> Settings:
        """The edited settings; only call after the dialog was accepted."""
        return Settings(
            repo=validate_repo(self._repo.text()),
            branch=self._branch.text().strip(),
            token=self._token.text().strip(),
            font_size=self._font_size.value(),
            show_thumbnails=self._show_thumbnails.isChecked(),
            search_folders=self._search_folders.isChecked(),
            hide_unsupported=self._hide_unsupported.isChecked(),
        )
