# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

__all__ = [
    "__version__",
    "version",
    "modify_sys_path",
    "run_pylint",
    "run_epylint",
    "run_symilar",
    "run_pyreverse",
]

import os
import sys
from collections.abc import Sequence
from typing import NoReturn

from pylint.__pkginfo__ import __version__

# pylint: disable=import-outside-toplevel


def run_pylint(argv: Sequence[str] | None = None) -> None:
    """Run pylint.

    argv can be a sequence of strings normally supplied as arguments on the command line
    """
    from pylint.lint import Run as PylintRun

    try:
        PylintRun(argv or sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(1)


def _run_pylint_config(argv: Sequence[str] | None = None) -> None:
    """Run pylint-config.

    argv can be a sequence of strings normally supplied as arguments on the command line
    """
    from pylint.lint.run import _PylintConfigRun

    _PylintConfigRun(argv or sys.argv[1:])


def run_epylint(argv: Sequence[str] | None = None) -> NoReturn:
    """Run epylint.

    argv can be a list of strings normally supplied as arguments on the command line
    """
    from pylint.epylint import Run as EpylintRun

    EpylintRun(argv)


def run_pyreverse(argv: Sequence[str] | None = None) -> NoReturn:  # type: ignore[misc]
    """Run pyreverse.

    argv can be a sequence of strings normally supplied as arguments on the command line
    """
    from pylint.pyreverse.main import Run as PyreverseRun

    PyreverseRun(argv or sys.argv[1:])


def run_symilar(argv: Sequence[str] | None = None) -> NoReturn:
    """Run symilar.

    argv can be a sequence of strings normally supplied as arguments on the command line
    """
    from pylint.checkers.similar import Run as SimilarRun

    SimilarRun(argv or sys.argv[1:])


def _normalize_for_cwd_check(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def modify_sys_path() -> None:
    """Modify sys path for execution as Python module.

    Strip out the current working directory from sys.path.
    Having the working directory in `sys.path` means that `pylint` might
    inadvertently import user code from modules having the same name as
    stdlib or pylint's own modules.
    CPython issue: https://bugs.python.org/issue33053

    - Remove the first entry if it refers to the working directory ("", ".", or
      a path normalizing to ``os.getcwd()``)
    - Remove the working directory from the second and third entries when
      they are cwd-equivalent and PYTHONPATH includes a ":" at the beginning
      or the end.
      https://github.com/PyCQA/pylint/issues/3636
      Don't remove it if PYTHONPATH contains the cwd or '.' as the entry will
      only be added once.
    - Don't remove the working directory from the rest. It will be included
      if pylint is installed in an editable configuration (as the last item).
      https://github.com/PyCQA/pylint/issues/4161
    """
    env_pythonpath = os.environ.get("PYTHONPATH", "")
    cwd = os.getcwd()
    normalized_cwd = _normalize_for_cwd_check(cwd)

    def _is_cwd_equivalent(entry: object) -> bool:
        if not isinstance(entry, str):
            return False
        candidate = entry or "."
        return _normalize_for_cwd_check(candidate) == normalized_cwd

    def _pop_if_cwd(index: int) -> bool:
        if 0 <= index < len(sys.path) and _is_cwd_equivalent(sys.path[index]):
            sys.path.pop(index)
            return True
        return False

    first_removed = _pop_if_cwd(0)

    if env_pythonpath.startswith(":") and env_pythonpath not in (f":{cwd}", ":."):
        target_index = 0 if first_removed else 1
        _pop_if_cwd(target_index)
    elif env_pythonpath.endswith(":") and env_pythonpath not in (f"{cwd}:", ".:"):
        target_index = 1 if first_removed else 2
        _pop_if_cwd(target_index)


version = __version__
