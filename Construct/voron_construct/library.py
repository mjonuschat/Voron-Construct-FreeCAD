"""Group a GitHub repo tree into folders and parts."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field

STEP_EXTENSIONS = (".step", ".stp")
SOURCE_EXTENSIONS = (".f3d", ".f3z")
THUMB_EXTENSION = ".png"


@dataclass
class Part:
    name: str
    dir: str
    step_path: str | None
    source_paths: list[str]
    thumb_path: str | None
    size: int | None

    @property
    def importable(self) -> bool:
        return self.step_path is not None


@dataclass
class Folder:
    name: str
    path: str
    folders: list[Folder] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)


def _build_parts(entries: list[dict]) -> list[Part]:
    groups: dict[tuple[str, str], dict] = {}
    for entry in entries:
        if entry.get("type") != "blob":
            continue
        path = entry["path"]
        directory, filename = posixpath.split(path)
        stem, ext = posixpath.splitext(filename)
        ext = ext.lower()
        if ext not in STEP_EXTENSIONS + SOURCE_EXTENSIONS + (THUMB_EXTENSION,):
            continue
        group = groups.setdefault(
            (directory, stem.lower()),
            {"name": stem, "steps": [], "sources": [], "thumb": None},
        )
        item = (path, entry.get("size"))
        if ext in STEP_EXTENSIONS:
            group["steps"].append((ext, item))
        elif ext in SOURCE_EXTENSIONS:
            group["sources"].append(item)
        else:
            group["thumb"] = path

    parts = []
    for (directory, _), group in groups.items():
        if not group["steps"] and not group["sources"]:
            continue
        steps = sorted(group["steps"], key=lambda s: s[0] != ".step")
        step = steps[0][1] if steps else None
        sources = sorted(group["sources"])
        size_item = step or (sources[0] if sources else None)
        parts.append(
            Part(
                name=group["name"],
                dir=directory,
                step_path=step[0] if step else None,
                source_paths=[p for p, _ in sources],
                thumb_path=group["thumb"],
                size=size_item[1] if size_item else None,
            )
        )
    return parts


def _sort_folder(folder: Folder) -> None:
    folder.folders.sort(key=lambda f: f.name.lower())
    folder.parts.sort(key=lambda p: p.name.lower())
    for sub in folder.folders:
        _sort_folder(sub)


def build_library(entries: list[dict]) -> Folder:
    root = Folder(name="", path="")
    folders: dict[str, Folder] = {"": root}

    def get_folder(path: str) -> Folder:
        if path in folders:
            return folders[path]
        parent = get_folder(posixpath.dirname(path))
        folder = Folder(name=posixpath.basename(path), path=path)
        parent.folders.append(folder)
        folders[path] = folder
        return folder

    for part in _build_parts(entries):
        get_folder(part.dir).parts.append(part)
    _sort_folder(root)
    return root


def _prune(folder: Folder, needle: str, include_folders: bool) -> Folder | None:
    if include_folders and folder.path and needle in folder.name.lower():
        return folder
    parts = [p for p in folder.parts if needle in p.name.lower()]
    subs = [
        s for s in (_prune(f, needle, include_folders) for f in folder.folders) if s
    ]
    if not parts and not subs:
        return None
    return Folder(folder.name, folder.path, subs, parts)


def search(root: Folder, text: str, include_folders: bool) -> Folder:
    if not text:
        return root
    pruned = _prune(root, text.lower(), include_folders)
    return pruned or Folder(root.name, root.path)
