from __future__ import annotations

import argparse

import pytest

from pylint.config.argument import (
    _regexp_csv_transfomer,
    _regexp_paths_csv_transfomer,
)


def test_regexp_csv_with_quantifier_group() -> None:
    patterns = _regexp_csv_transfomer("(foo{1,3})")

    assert len(patterns) == 1
    assert patterns[0].pattern == "(foo{1,3})"


def test_regexp_csv_with_simple_separator() -> None:
    patterns = _regexp_csv_transfomer("foo,bar")

    assert [pattern.pattern for pattern in patterns] == ["foo", "bar"]


def test_regexp_csv_invalid_expression_raises_argparse_error() -> None:
    with pytest.raises(argparse.ArgumentTypeError) as excinfo:
        _regexp_csv_transfomer("foo{1,3")

    assert "Error in provided regular expression" in str(excinfo.value)


def test_regexp_csv_comma_inside_character_class() -> None:
    patterns = _regexp_csv_transfomer("prefix[a,b]suffix")

    assert len(patterns) == 1
    assert patterns[0].pattern == "prefix[a,b]suffix"


def test_regexp_csv_character_class_with_leading_closing_bracket() -> None:
    patterns = _regexp_csv_transfomer("[],]")

    assert len(patterns) == 1
    assert patterns[0].pattern == "[],]"


def test_regexp_csv_escaped_comma() -> None:
    patterns = _regexp_csv_transfomer(r"foo\,,bar")

    assert [pattern.pattern for pattern in patterns] == [r"foo\,", "bar"]


def test_regexp_paths_csv_handles_quantifier_and_separator() -> None:
    patterns = _regexp_paths_csv_transfomer("dir{1,3},other")

    assert [pattern.pattern for pattern in patterns] == [
        "dir{1,3}|dir{1,3}",
        "other|other",
    ]
