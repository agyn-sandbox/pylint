# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import ntpath
import re
from pathlib import Path

import pytest

import pylint.lint.expand_modules as expand_modules_module
from pylint.checkers import BaseChecker
from pylint.lint.expand_modules import (
    _is_ignored_file,
    _is_in_ignore_list_re,
    expand_modules,
)
from pylint.testutils import CheckerTestCase, create_files, set_config
from pylint.testutils._run import _Run as Run
from pylint.typing import MessageDefinitionTuple


def test__is_in_ignore_list_re_match() -> None:
    patterns = [
        re.compile(".*enchilada.*"),
        re.compile("unittest_.*"),
        re.compile(".*tests/.*"),
    ]
    assert _is_in_ignore_list_re("unittest_utils.py", patterns)
    assert _is_in_ignore_list_re("cheese_enchiladas.xml", patterns)
    assert _is_in_ignore_list_re("src/tests/whatever.xml", patterns)


def test__is_ignored_file_normalizes_relative_paths() -> None:
    ignore_paths_patterns = [re.compile(r"^src/gen/.*$")]
    assert _is_ignored_file("./src/gen/module.py", [], [], ignore_paths_patterns)
    assert _is_ignored_file("src/gen/module.py", [], [], ignore_paths_patterns)
    assert not _is_ignored_file("./src/app/module.py", [], [], ignore_paths_patterns)


def test__is_ignored_file_normalizes_windows_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    ignore_paths_patterns = [re.compile(r"^src\\gen\\.*$")]
    monkeypatch.setattr(
        expand_modules_module.os.path, "normpath", ntpath.normpath, raising=False
    )
    assert _is_ignored_file(".\\src\\gen\\module.py", [], [], ignore_paths_patterns)
    assert _is_ignored_file("src\\gen\\module.py", [], [], ignore_paths_patterns)
    assert not _is_ignored_file(
        ".\\src\\app\\module.py", [], [], ignore_paths_patterns
    )


@pytest.mark.parametrize("target", ("src/", "."))
@pytest.mark.parametrize("ignore_pattern", (r"^src/gen/.*$", r"^src\\\\gen\\\\.*$"))
def test_expand_modules_respects_ignore_paths_on_recursive_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, ignore_pattern: str
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(project_root))
    create_files(
        [
            "src/__init__.py",
            "src/app/__init__.py",
            "src/app/ok.py",
            "src/gen/__init__.py",
            "src/gen/failing.py",
        ],
        chroot=str(tmp_path),
    )
    (tmp_path / "src" / "app" / "ok.py").write_text(
        "def ok():\n    return 1\n", encoding="utf-8"
    )
    (tmp_path / "src" / "gen" / "failing.py").write_text(
        "def broken():\n    return unknown\n", encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    run = Run(
        [
            "--recursive=y",
            "--disable=all",
            f"--ignore-paths={ignore_pattern}",
            target,
        ],
        exit=False,
    )

    descriptors = run.linter._iterate_file_descrs(
        tuple(run.linter._discover_files([target]))
    )
    base = tmp_path.resolve()

    def to_relative(path_str: str) -> str:
        candidate = Path(path_str)
        if not candidate.is_absolute():
            candidate = (base / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate.relative_to(base).as_posix()

    linted_paths = {to_relative(descriptor.filepath) for descriptor in descriptors}

    assert "src/gen/failing.py" not in linted_paths
    assert "src/gen/__init__.py" not in linted_paths
    assert "src/app/ok.py" in linted_paths


TEST_DIRECTORY = Path(__file__).parent.parent
INIT_PATH = str(TEST_DIRECTORY / "lint/__init__.py")
EXPAND_MODULES = str(TEST_DIRECTORY / "lint/unittest_expand_modules.py")
this_file = {
    "basename": "lint.unittest_expand_modules",
    "basepath": EXPAND_MODULES,
    "isarg": True,
    "name": "lint.unittest_expand_modules",
    "path": EXPAND_MODULES,
}

this_file_from_init = {
    "basename": "lint",
    "basepath": INIT_PATH,
    "isarg": False,
    "name": "lint.unittest_expand_modules",
    "path": EXPAND_MODULES,
}

unittest_lint = {
    "basename": "lint",
    "basepath": INIT_PATH,
    "isarg": False,
    "name": "lint.unittest_lint",
    "path": str(TEST_DIRECTORY / "lint/unittest_lint.py"),
}

test_utils = {
    "basename": "lint",
    "basepath": INIT_PATH,
    "isarg": False,
    "name": "lint.test_utils",
    "path": str(TEST_DIRECTORY / "lint/test_utils.py"),
}

test_pylinter = {
    "basename": "lint",
    "basepath": INIT_PATH,
    "isarg": False,
    "name": "lint.test_pylinter",
    "path": str(TEST_DIRECTORY / "lint/test_pylinter.py"),
}

test_caching = {
    "basename": "lint",
    "basepath": INIT_PATH,
    "isarg": False,
    "name": "lint.test_caching",
    "path": str(TEST_DIRECTORY / "lint/test_caching.py"),
}


init_of_package = {
    "basename": "lint",
    "basepath": INIT_PATH,
    "isarg": True,
    "name": "lint",
    "path": INIT_PATH,
}


class TestExpandModules(CheckerTestCase):
    """Test the expand_modules function while allowing options to be set."""

    class Checker(BaseChecker):
        """This dummy checker is needed to allow options to be set."""

        name = "checker"
        msgs: dict[str, MessageDefinitionTuple] = {}
        options = (("test-opt", {"action": "store_true", "help": "help message"}),)

    CHECKER_CLASS: type = Checker

    @pytest.mark.parametrize(
        "files_or_modules,expected",
        [
            ([__file__], [this_file]),
            (
                [str(Path(__file__).parent)],
                [
                    init_of_package,
                    test_caching,
                    test_pylinter,
                    test_utils,
                    this_file_from_init,
                    unittest_lint,
                ],
            ),
        ],
    )
    @set_config(ignore_paths="")
    def test_expand_modules(self, files_or_modules, expected):
        """Test expand_modules with the default value of ignore-paths."""
        ignore_list, ignore_list_re = [], []
        modules, errors = expand_modules(
            files_or_modules,
            ignore_list,
            ignore_list_re,
            self.linter.config.ignore_paths,
        )
        modules.sort(key=lambda d: d["name"])
        assert modules == expected
        assert not errors

    @pytest.mark.parametrize(
        "files_or_modules,expected",
        [
            ([__file__], []),
            (
                [str(Path(__file__).parent)],
                [
                    init_of_package,
                ],
            ),
        ],
    )
    @set_config(ignore_paths=".*/lint/.*")
    def test_expand_modules_with_ignore(self, files_or_modules, expected):
        """Test expand_modules with a non-default value of ignore-paths."""
        ignore_list, ignore_list_re = [], []
        modules, errors = expand_modules(
            files_or_modules,
            ignore_list,
            ignore_list_re,
            self.linter.config.ignore_paths,
        )
        modules.sort(key=lambda d: d["name"])
        assert modules == expected
        assert not errors
