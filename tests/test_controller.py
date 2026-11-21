import pytest
from voron_construct.cache import Cache
from voron_construct.controller import Controller
from voron_construct.github import GitHubError
from voron_construct.library import Folder, Part
from voron_construct.settings import Settings

ENTRIES_1 = [{"path": "a/x.step", "type": "blob", "size": 5}]
ENTRIES_2 = [{"path": "a/y.step", "type": "blob", "size": 5}]


class FakeClient:
    def __init__(self, sha="s1", entries=ENTRIES_1, error=None):
        self.sha, self.entries, self.error = sha, entries, error
        self.tree_fetches = 0
        self.downloads = []

    def resolve(self, repo, branch=""):
        if self.error:
            raise self.error
        return branch or "main", self.sha

    def fetch_tree(self, repo, sha):
        self.tree_fetches += 1
        return self.entries

    def download(self, repo, ref, rel_path, dest):
        self.downloads.append((repo, ref, rel_path))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"data")


def run_inline(work, on_done, on_error):
    try:
        result = work()
    except Exception as exc:  # mirrors run_async, which forwards any error
        on_error(exc)
        return
    on_done(result)


def make(tmp_path, client):
    imported, opened = [], []
    ctl = Controller(
        lambda s: client, Cache(tmp_path), imported.append, opened.append, run_inline
    )
    return ctl, imported, opened


def part(step="a/x.step", thumb=None):
    return Part("x", "a", step, [], thumb, 5)


def load(ctl, settings=None):
    trees, errors = [], []
    ctl.load(settings or Settings(), trees.append, errors.append)
    return trees, errors


def names(folder):
    return [p.name for f in folder.folders for p in f.parts]


def test_load_uses_cached_tree_then_refreshes_on_new_sha(tmp_path):
    Cache(tmp_path).write_tree(
        "PrintersForAnts/Voron-Construct", "_default", "old", ENTRIES_1
    )
    ctl, _, _ = make(tmp_path, FakeClient("new", ENTRIES_2))
    trees, errors = load(ctl)
    assert len(trees) == 2 and errors == []
    assert names(trees[0]) == ["x"]
    assert names(trees[1]) == ["y"]
    assert (
        Cache(tmp_path).read_tree("PrintersForAnts/Voron-Construct", "_default")[0]
        == "new"
    )


def test_load_same_sha_does_not_refetch_tree(tmp_path):
    Cache(tmp_path).write_tree(
        "PrintersForAnts/Voron-Construct", "_default", "s1", ENTRIES_1
    )
    client = FakeClient("s1")
    ctl, _, _ = make(tmp_path, client)
    trees, _ = load(ctl)
    assert len(trees) == 1 and client.tree_fetches == 0


def test_new_sha_clears_cached_files(tmp_path):
    repo = "PrintersForAnts/Voron-Construct"
    cache = Cache(tmp_path)
    cache.write_tree(repo, "_default", "old", ENTRIES_1)
    f = cache.file_path(repo, "_default", "a/x.step")
    f.parent.mkdir(parents=True)
    f.write_bytes(b"stale")
    ctl, _, _ = make(tmp_path, FakeClient("new", ENTRIES_2))
    load(ctl)
    assert not f.exists()


def test_thumbnail_async_returns_none_without_thumb(tmp_path):
    ctl, _, _ = make(tmp_path, FakeClient())
    got = []
    ctl.thumbnail(Settings(), part(), got.append)
    assert got == [None]


def test_thumbnail_downloads_with_sha(tmp_path):
    client = FakeClient()
    ctl, _, _ = make(tmp_path, client)
    load(ctl)
    got = []
    ctl.thumbnail(Settings(), part(thumb="a/x.png"), got.append)
    assert got[0].read_bytes() == b"data"
    assert client.downloads == [("PrintersForAnts/Voron-Construct", "s1", "a/x.png")]


def test_rate_limit_keeps_cached_tree_and_reports(tmp_path):
    Cache(tmp_path).write_tree(
        "PrintersForAnts/Voron-Construct", "_default", "old", ENTRIES_1
    )
    ctl, _, _ = make(tmp_path, FakeClient(error=GitHubError("rate_limit", "slow down")))
    trees, errors = load(ctl)
    assert len(trees) == 1 and names(trees[0]) == ["x"]
    assert errors == ["slow down"]


def test_not_found_shows_empty_tree(tmp_path):
    Cache(tmp_path).write_tree(
        "PrintersForAnts/Voron-Construct", "_default", "old", ENTRIES_1
    )
    ctl, _, _ = make(tmp_path, FakeClient(error=GitHubError("not_found", "gone")))
    trees, errors = load(ctl)
    assert errors == ["gone"]
    assert trees[-1] == Folder("", "", [], [])


def test_error_without_cache_shows_empty_tree(tmp_path):
    ctl, _, _ = make(tmp_path, FakeClient(error=GitHubError("network", "offline")))
    trees, errors = load(ctl)
    assert errors == ["offline"]
    assert trees == [Folder("", "", [], [])]


def test_switching_repo_does_not_reuse_other_repo_files(tmp_path):
    client = FakeClient()
    ctl, imported, _ = make(tmp_path, client)
    for repo in ("o/one", "o/two"):
        s = Settings(repo=repo)
        load(ctl, s)
        ctl.import_part(s, part(), lambda: None, lambda e: None)
    assert [d[0] for d in client.downloads] == ["o/one", "o/two"]
    assert imported[0] != imported[1]


def test_import_downloads_once_then_uses_cache(tmp_path):
    client = FakeClient()
    ctl, imported, _ = make(tmp_path, client)
    load(ctl)
    for _ in range(2):
        ctl.import_part(Settings(), part(), lambda: None, lambda e: None)
    assert len(client.downloads) == 1 and len(imported) == 2
    assert client.downloads[0][1] == "s1"


def test_download_before_load_reads_sha_from_cached_tree(tmp_path):
    Cache(tmp_path).write_tree(
        "PrintersForAnts/Voron-Construct", "_default", "cached", ENTRIES_1
    )
    client = FakeClient()
    ctl, _, opened = make(tmp_path, client)
    ctl.open_part(Settings(), part(), lambda: None, lambda e: None)
    assert client.downloads[0][1] == "cached" and len(opened) == 1


def test_import_unsupported_part_raises(tmp_path):
    ctl, _, _ = make(tmp_path, FakeClient())
    with pytest.raises(ValueError):
        ctl.import_part(Settings(), part(step=None), lambda: None, lambda e: None)
    with pytest.raises(ValueError):
        ctl.open_part(Settings(), part(step=None), lambda: None, lambda e: None)


def test_import_failure_reported(tmp_path):
    client = FakeClient()
    ctl, _, _ = make(tmp_path, client)
    load(ctl)

    def boom(path):
        raise RuntimeError("bad step")

    ctl._import_fn = boom
    errors, done = [], []
    ctl.import_part(Settings(), part(), lambda: done.append(1), errors.append)
    assert errors == ["bad step"] and done == []


def test_apply_settings_reload_flag(tmp_path):
    ctl, _, _ = make(tmp_path, FakeClient())
    a = Settings()
    assert ctl.apply_settings(a, Settings(repo="o/other")) is True
    assert ctl.apply_settings(a, Settings(font_size=12)) is False
