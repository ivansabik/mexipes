"""Tests for recipe schema helpers."""

from mexipes.schemas.recipe import validate_box_2d


def test_validate_box_2d():
    assert validate_box_2d([0, 0, 500, 500])
    assert not validate_box_2d([0, 0, 0, 500])
    assert not validate_box_2d([0, 0, 500])
    assert not validate_box_2d([0, 0, 500, 1001])
