import pytest
from voron_construct.cache import Cache


def test_paths_separate_per_repo_and_branch(tmp_path):
    c = Cache(tmp_path)
    a = c.file_path("o/r", "main", "a.step")
    assert a == tmp_path / "o" / "r" / "main" / "a.step"
    assert a != c.file_path("o/r2", "main", "a.step")
    assert a != c.file_path("o/r", "dev", "a.step")


@pytest.mark.parametrize("bad", ["../x", "/etc/passwd", "a/../../x"])
def test_rejects_traversal(tmp_path, bad):
    with pytest.raises(ValueError):
        Cache(tmp_path).file_path("o/r", "main", bad)


def test_rejects_bad_repo(tmp_path):
    with pytest.raises(ValueError):
        Cache(tmp_path).file_path("norepo", "main", "a")


def test_spaces_and_unicode_ok(tmp_path):
    p = Cache(tmp_path).file_path("o/r", "main", "dir x/Bauteil ü.step")
    assert p.name == "Bauteil ü.step"


def test_branch_with_slash_encoded(tmp_path):
    p = Cache(tmp_path).file_path("o/r", "feature/x", "a")
    assert p == tmp_path / "o" / "r" / "feature%2Fx" / "a"


def test_tree_roundtrip_with_sha(tmp_path):
    c = Cache(tmp_path)
    c.write_tree("o/r", "main", "abc", [{"path": "a", "type": "blob"}])
    assert c.read_tree("o/r", "main") == ("abc", [{"path": "a", "type": "blob"}])


def test_clear_files_keeps_tree(tmp_path):
    c = Cache(tmp_path)
    c.write_tree("o/r", "main", "abc", [])
    f = c.file_path("o/r", "main", "d/a.step")
    f.parent.mkdir(parents=True)
    f.write_text("x")
    c.clear_files("o/r", "main")
    assert not f.exists()
    assert not f.parent.exists()
    assert c.read_tree("o/r", "main") == ("abc", [])


def test_clear_files_missing_dir_ok(tmp_path):
    Cache(tmp_path).clear_files("o/r", "main")


def test_read_tree_missing_returns_none(tmp_path):
    assert Cache(tmp_path).read_tree("o/r", "main") is None
