import pytest
from voron_construct.settings import DictBackend, Settings, SettingsStore, validate_repo


def test_defaults():
    s = SettingsStore(DictBackend()).load()
    assert s == Settings()
    assert s.repo == "PrintersForAnts/Voron-Construct"
    assert s.branch == "" and s.token == "" and s.font_size == 0
    assert s.show_thumbnails is False
    assert s.search_folders is True
    assert s.hide_unsupported is False


def test_roundtrip():
    store = SettingsStore(DictBackend())
    s = Settings("a/b", "dev", "tok", 12, True, False, True)
    store.save(s)
    assert store.load() == s


def test_repo_changed_on_branch_only():
    a = Settings(repo="a/b", branch="main")
    assert a.repo_changed(Settings(repo="a/b", branch="dev"))
    assert not a.repo_changed(Settings(repo=" A/B ", branch=" main "))
    assert a.repo_changed(Settings(repo="a/c", branch="main"))


def test_validate_repo_accepts_url_forms():
    assert validate_repo(" owner/name ") == "owner/name"
    assert validate_repo("https://github.com/owner/name") == "owner/name"
    assert validate_repo("https://github.com/owner/name.git") == "owner/name"


@pytest.mark.parametrize("text", ["", "a", "a/b/c", "a b/c"])
def test_validate_repo_rejects_garbage(text):
    with pytest.raises(ValueError):
        validate_repo(text)
