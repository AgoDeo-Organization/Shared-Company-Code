"""Unit tests for file utility helpers."""

from __future__ import annotations

from julien_python_toolkit import file_utilities



def test_path_to_this_file_returns_parent_directory() -> None:
    """path_to_this_file should resolve and return the parent directory."""

    result = file_utilities.path_to_this_file("/tmp/folder/data.txt")

    assert result == "/tmp/folder"



def test_join_combines_path_segments() -> None:
    """join should merge multiple path parts in order."""

    result = file_utilities.join("root", "folder", "data.txt")

    assert result.endswith("root/folder/data.txt")



def test_join_with_single_argument_returns_same_value() -> None:
    """Single segment joins are returned unchanged."""

    result = file_utilities.join("only")

    assert result == "only"
