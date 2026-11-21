import json
from pathlib import Path

from voron_construct.library import build_library, search

DATA = Path(__file__).parent / "data" / "tree_small.json"


def lib():
    return build_library(json.loads(DATA.read_text()))


def find(folder, name):
    for p in folder.parts:
        if p.name == name:
            return p
    for f in folder.folders:
        r = find(f, name)
        if r:
            return r
    return None


def all_parts(folder):
    return folder.parts + [p for f in folder.folders for p in all_parts(f)]


def test_step_part_is_importable_and_has_thumb():
    p = find(lib(), "ECAS Cutter")
    assert p.step_path == "Cutters/ECAS Cutter.step"
    assert p.thumb_path.endswith(".png")
    assert p.importable
    assert p.size == 20


def test_f3d_only_part_not_importable():
    p = find(lib(), "Misumi 3030 Cube")
    assert p.importable is False
    assert p.source_paths == ["Extrusion/Misumi/Misumi 3030 Cube.f3d"]


def test_case_insensitive_extensions():
    p = find(lib(), "Thing")
    assert p.step_path == "Misc/Thing.STEP"
    assert p.thumb_path == "Misc/Thing.PNG"


def test_step_and_stp_one_part():
    parts = [p for p in all_parts(lib()) if p.name == "Pair"]
    assert len(parts) == 1
    assert parts[0].step_path == "Misc/Pair.step"


def test_non_part_files_ignored():
    root = lib()
    assert find(root, "Voron Logo") is None
    assert find(root, "notes") is None
    assert "DXFs" not in [f.name for f in root.folders]


def test_sorting():
    root = lib()
    assert [f.name for f in root.folders] == ["Cutters", "Extrusion", "Misc"]
    misc = next(f for f in root.folders if f.name == "Misc")
    assert [p.name for p in misc.parts] == ["alpha", "Beta", "Pair", "Thing"]


def test_search_name_and_folder_toggle():
    root = lib()
    r = search(root, "ecas", False)
    assert [p.name for p in all_parts(r)] == ["ECAS Cutter"]
    assert search(root, "", False) is root
    assert [p.name for p in all_parts(search(root, "extrusion", False))] == []
    assert [p.name for p in all_parts(search(root, "extrusion", True))] == [
        "Misumi 3030 Cube"
    ]
