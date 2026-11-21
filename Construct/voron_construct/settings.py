"""Persistent user settings for the Construct browser."""

import re
from dataclasses import asdict, dataclass, fields
from typing import Any, Protocol

_PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Construct"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_URL_RE = re.compile(r"^https://github\.com/([^/\s]+/[^/\s]+?)(?:\.git)?/?$")


@dataclass
class Settings:
    repo: str = "PrintersForAnts/Voron-Construct"
    branch: str = ""
    token: str = ""
    font_size: int = 0
    show_thumbnails: bool = False
    search_folders: bool = True
    hide_unsupported: bool = False

    def repo_changed(self, other: "Settings") -> bool:
        """True if the repo (any case) or branch differs, ignoring outer spaces."""
        return (
            self.repo.strip().lower() != other.repo.strip().lower()
            or self.branch.strip() != other.branch.strip()
        )


def validate_repo(text: str) -> str:
    """Return the trimmed ``owner/name`` from text or a GitHub URL, else ValueError."""
    text = text.strip()
    match = _URL_RE.match(text)
    if match:
        text = match.group(1)
    if not _REPO_RE.match(text):
        raise ValueError(f"Invalid repository: {text!r}")
    return text


class Backend(Protocol):
    def get(self, key: str, default: Any) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


class DictBackend:
    """In-memory backend for tests."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value


class FreeCADBackend:
    """Backend over FreeCAD's parameter store; FreeCAD is imported lazily."""

    def __init__(self) -> None:
        import FreeCAD

        self._params = FreeCAD.ParamGet(_PARAM_PATH)

    def get(self, key: str, default: Any) -> Any:
        if isinstance(default, bool):
            return self._params.GetBool(key, default)
        if isinstance(default, int):
            return self._params.GetInt(key, default)
        return self._params.GetString(key, default)

    def set(self, key: str, value: Any) -> None:
        if isinstance(value, bool):
            self._params.SetBool(key, value)
        elif isinstance(value, int):
            self._params.SetInt(key, value)
        else:
            self._params.SetString(key, value)


class SettingsStore:
    def __init__(self, backend: Backend) -> None:
        self._backend = backend

    def load(self) -> Settings:
        defaults = Settings()
        return Settings(
            **{
                f.name: self._backend.get(f.name, getattr(defaults, f.name))
                for f in fields(Settings)
            }
        )

    def save(self, settings: Settings) -> None:
        for key, value in asdict(settings).items():
            self._backend.set(key, value)
