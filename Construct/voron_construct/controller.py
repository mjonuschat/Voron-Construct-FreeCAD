"""UI logic shared by the panel: loading the library and fetching files, without Qt."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .cache import Cache
from .github import GitHubClient, GitHubError
from .library import Folder, Part, build_library
from .settings import Settings

RunAsync = Callable[
    [Callable[[], object], Callable[[object], None], Callable[[Exception], None]], None
]


def _branch_key(settings: Settings) -> str:
    return settings.branch or "_default"


class Controller:
    def __init__(
        self,
        client_factory: Callable[[Settings], GitHubClient],
        cache: Cache,
        import_fn: Callable[[Path], object],
        open_fn: Callable[[Path], object],
        run_async: RunAsync,
    ) -> None:
        self._client_factory = client_factory
        self._cache = cache
        self._import_fn = import_fn
        self._open_fn = open_fn
        self._run_async = run_async
        self._shas: dict[tuple[str, str], str] = {}

    def apply_settings(self, old: Settings, new: Settings) -> bool:
        return old.repo_changed(new)

    def load(
        self,
        settings: Settings,
        on_done: Callable[[Folder], None],
        on_error: Callable[[str], None],
    ) -> None:
        repo, key = settings.repo, _branch_key(settings)
        cached = self._cache.read_tree(repo, key)
        if cached is not None:
            self._shas[(repo, key)] = cached[0]
            on_done(build_library(cached[1]))
        cached_sha = cached[0] if cached is not None else None

        def work() -> tuple[str, list[dict]] | None:
            client = self._client_factory(settings)
            _, sha = client.resolve(repo, settings.branch)
            if sha == cached_sha:
                return None
            entries = client.fetch_tree(repo, sha)
            self._cache.clear_files(repo, key)
            self._cache.write_tree(repo, key, sha, entries)
            return sha, entries

        def done(result: object) -> None:
            if result is None:
                return
            sha, entries = result  # type: ignore[misc]
            self._shas[(repo, key)] = sha
            on_done(build_library(entries))

        def failed(exc: Exception) -> None:
            on_error(str(exc))
            empty = isinstance(exc, GitHubError) and exc.kind == "not_found"
            if empty or cached is None:
                self._shas.pop((repo, key), None)
                on_done(Folder("", "", [], []))

        self._run_async(work, done, failed)

    def _ref(self, settings: Settings) -> str | None:
        key = (settings.repo, _branch_key(settings))
        if key not in self._shas:
            cached = self._cache.read_tree(*key)
            if cached is not None:
                self._shas[key] = cached[0]
        return self._shas.get(key)

    def _fetch(
        self,
        settings: Settings,
        rel_path: str,
        on_path: Callable[[Path], None],
        on_error: Callable[[str], None],
    ) -> None:
        repo, key = settings.repo, _branch_key(settings)
        dest = self._cache.file_path(repo, key, rel_path)
        ref = self._ref(settings)

        def work() -> Path:
            if not dest.is_file():
                if ref is None:
                    raise GitHubError("not_found", "Library has not been loaded")
                self._client_factory(settings).download(repo, ref, rel_path, dest)
            return dest

        def done(path: object) -> None:
            try:
                on_path(path)  # type: ignore[arg-type]
            except Exception as exc:  # report any importer error to the UI
                on_error(str(exc))

        self._run_async(work, done, lambda exc: on_error(str(exc)))

    def thumbnail(
        self,
        settings: Settings,
        part: Part,
        on_done: Callable[[Path | None], None],
    ) -> None:
        if part.thumb_path is None:
            on_done(None)
            return
        self._fetch(settings, part.thumb_path, on_done, lambda _msg: on_done(None))

    def import_part(
        self,
        settings: Settings,
        part: Part,
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        self._run_step(settings, part, self._import_fn, on_done, on_error)

    def open_part(
        self,
        settings: Settings,
        part: Part,
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        self._run_step(settings, part, self._open_fn, on_done, on_error)

    def _run_step(self, settings, part, action, on_done, on_error) -> None:
        if not part.importable:
            raise ValueError(f"{part.name} has no STEP file")

        def run(path: Path) -> None:
            action(path)
            on_done()

        self._fetch(settings, part.step_path, run, on_error)
