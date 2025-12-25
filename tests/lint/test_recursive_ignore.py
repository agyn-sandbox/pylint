"""Tests ensuring recursive discovery respects ignore options."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

from pathlib import Path

import pytest

from pylint.lint import Run
from pylint.testutils import GenericTestReporter


def _write_module(path: Path) -> None:
    path.write_text("import os\n", encoding="utf-8")


def _build_sample_tree(root: Path) -> None:
    (root / "a").mkdir()
    _write_module(root / "a" / "foo.py")

    (root / ".hidden").mkdir()
    _write_module(root / ".hidden" / "bar.py")

    (root / "pkg").mkdir()
    _write_module(root / "pkg" / "__init__.py")
    _write_module(root / "pkg" / "mod.py")

    (root / "pkg" / ".hiddenpkg").mkdir()
    _write_module(root / "pkg" / ".hiddenpkg" / "baz.py")

    (root / ".a").mkdir()
    _write_module(root / ".a" / "foo.py")

    _write_module(root / "single.py")


def _linted_paths(
    base: Path,
    targets: list[Path],
    *,
    recursive: bool,
    extra_args: list[str] | None = None,
) -> set[Path]:
    reporter = GenericTestReporter()
    args = [
        "--rcfile=/dev/null",
        "--disable=all",
        "--enable=missing-module-docstring",
        "--persistent=n",
        "--score=n",
        "--reports=n",
        "--jobs=1",
        "--recursive=y" if recursive else "--recursive=n",
    ]
    if extra_args:
        args.extend(extra_args)
    args.extend(str(target) for target in targets)
    Run(args, reporter=reporter, exit=False)
    return {
        Path(message.abspath).resolve().relative_to(base)
        for message in reporter.messages
        if message.symbol == "missing-module-docstring"
    }


@pytest.fixture()
def sample_tree(tmp_path: Path) -> Path:
    _build_sample_tree(tmp_path)
    return tmp_path


def test_recursive_ignore_patterns_skip_hidden_directories(sample_tree: Path) -> None:
    linted = _linted_paths(
        sample_tree,
        [sample_tree],
        recursive=True,
        extra_args=["--ignore-patterns=^\\.\\w"],
    )

    assert Path("single.py") in linted
    assert Path("pkg/__init__.py") in linted
    assert Path("pkg/mod.py") in linted
    assert Path("a/foo.py") in linted

    assert Path(".hidden/bar.py") not in linted
    assert Path("pkg/.hiddenpkg/baz.py") not in linted
    assert Path(".a/foo.py") not in linted


def test_recursive_ignore_option_skips_directory(sample_tree: Path) -> None:
    linted = _linted_paths(
        sample_tree,
        [sample_tree],
        recursive=True,
        extra_args=["--ignore=.a"],
    )

    assert Path(".a/foo.py") not in linted
    assert Path("a/foo.py") in linted
    assert Path("single.py") in linted


def test_recursive_ignore_paths_skip_pattern(sample_tree: Path) -> None:
    linted = _linted_paths(
        sample_tree,
        [sample_tree],
        recursive=True,
        extra_args=["--ignore-paths=.*/\\.a(?:/|\\\\|$).*"],
    )

    assert Path(".a/foo.py") not in linted
    assert Path("a/foo.py") in linted
    assert Path("pkg/__init__.py") in linted
    assert Path("pkg/mod.py") in linted


def test_recursive_ignore_patterns_on_filename(sample_tree: Path) -> None:
    linted = _linted_paths(
        sample_tree,
        [sample_tree],
        recursive=True,
        extra_args=["--ignore-patterns=^foo\\.py$"],
    )

    assert Path("a/foo.py") not in linted
    assert Path(".a/foo.py") not in linted
    assert Path("pkg/__init__.py") in linted
    assert Path("pkg/mod.py") in linted
    assert Path("single.py") in linted


def test_non_recursive_single_file_unchanged(sample_tree: Path) -> None:
    linted = _linted_paths(
        sample_tree,
        [sample_tree / "single.py"],
        recursive=False,
    )

    assert Path("single.py") in linted
