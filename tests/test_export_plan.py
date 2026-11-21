from pathlib import Path

import plan


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_find_missing_skips_files_with_step(tmp_path):
    a = touch(tmp_path / "a" / "part.f3d")
    touch(tmp_path / "a" / "part.step")
    b = touch(tmp_path / "a" / "other.f3d")
    touch(tmp_path / "a" / "third.f3d")
    touch(tmp_path / "a" / "third.stp")
    assert plan.find_missing(tmp_path) == [b]
    assert a not in plan.find_missing(tmp_path)


def test_find_missing_case_insensitive(tmp_path):
    touch(tmp_path / "Part.F3D")
    touch(tmp_path / "Part.STEP")
    missing = touch(tmp_path / "Lone.F3D")
    assert plan.find_missing(tmp_path) == [missing]


def test_f3z_counted(tmp_path):
    z = touch(tmp_path / "x" / "asm.f3z")
    assert plan.find_missing(tmp_path) == [z]


def test_git_dir_ignored(tmp_path):
    touch(tmp_path / ".git" / "objects" / "hidden.f3d")
    real = touch(tmp_path / "real.f3d")
    assert plan.find_missing(tmp_path) == [real]


def test_target_path():
    assert plan.step_target(Path("/a/b/part.f3z")) == Path("/a/b/part.step")


def test_partial_step_does_not_hide_source(tmp_path):
    source = touch(tmp_path / "X.f3d")
    touch(tmp_path / "X.partial.step")
    assert plan.find_missing(tmp_path) == [source]
