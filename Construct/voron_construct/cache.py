"""On-disk cache of downloaded files and tree listings, keyed by repo and branch."""

import json
import shutil
from pathlib import Path, PurePosixPath

TREE_FILE = "tree.json"


def default_cache_root() -> Path:
    try:
        import FreeCAD  # type: ignore
    except ImportError:
        return Path.home() / ".cache" / "Construct"
    return Path(FreeCAD.getUserCachePath()) / "Construct"


class Cache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _dir(self, repo: str, branch: str) -> Path:
        parts = repo.split("/")
        if len(parts) != 2 or not all(parts) or any(p in (".", "..") for p in parts):
            raise ValueError(f"repo must be 'owner/name': {repo!r}")
        return self.root / parts[0] / parts[1] / branch.replace("/", "%2F")

    def file_path(self, repo: str, branch: str, rel_path: str) -> Path:
        rel = PurePosixPath(rel_path)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError(f"invalid relative path: {rel_path!r}")
        return self._dir(repo, branch).joinpath(*rel.parts)

    def clear_files(self, repo: str, branch: str) -> None:
        d = self._dir(repo, branch)
        if not d.is_dir():
            return
        for child in d.iterdir():
            if child.name == TREE_FILE:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def read_tree(self, repo: str, branch: str) -> "tuple[str, list[dict]] | None":
        path = self._dir(repo, branch) / TREE_FILE
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["sha"], data["entries"]

    def write_tree(
        self, repo: str, branch: str, sha: str, entries: "list[dict]"
    ) -> None:
        d = self._dir(repo, branch)
        d.mkdir(parents=True, exist_ok=True)
        (d / TREE_FILE).write_text(
            json.dumps({"sha": sha, "entries": entries}), encoding="utf-8"
        )
