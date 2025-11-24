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


def modify_sys_path() -> None:
    """Modify sys path for execution as Python module.

    Strip out the current working directory from sys.path.
    Having the working directory in `sys.path` means that `pylint` might
    inadvertently import user code from modules having the same name as
    stdlib or pylint's own modules.
    CPython issue: https://bugs.python.org/issue33053

    Intent and rules for removal:
    - Remove the first entry only if it represents the current working directory.
      Specifically if it is one of: empty string "", dot ".", or equals
      os.getcwd() after normalization.
      Normalization rules:
        * Use os.path.abspath + os.path.normpath on all platforms.
        * On Windows, also apply os.path.normcase to compare case-insensitively.
        * Prefer os.path.realpath to resolve symlinks when available.
      This ensures we do not unintentionally drop a user-supplied sys.path[0]
      (e.g., a plugin directory) when pylint is executed via runpy.

    - Remove the working directory from the second and third entries
      if PYTHONPATH includes a ":" at the beginning or the end.
      https://github.com/PyCQA/pylint/issues/3636
      Don't remove it if PYTHONPATH contains the cwd or '.' as the entry will
      only be added once.
    - Don't remove the working directory from the rest. It will be included
      if pylint is installed in an editable configuration (as the last item).
      https://github.com/PyCQA/pylint/issues/4161
    """
    def _normalize(p: str) -> str:
        """Normalize paths for robust cross-platform comparison.

        - abspath + normpath on all platforms
        - normcase on Windows (case-insensitive filesystem)
        - realpath to resolve symlinks when possible
        """
        try:
            np = os.path.abspath(p)
        except Exception:
            np = p
        try:
            np = os.path.normpath(np)
        except Exception:
            # keep original if normpath fails for any reason
            pass
        if os.name == "nt":
            try:
                np = os.path.normcase(np)
            except Exception:
                pass
        try:
            np = os.path.realpath(np)
        except Exception:
            pass
        return np

    def _is_cwd_entry(entry: str, cwd: str) -> bool:
        # Treat empty string and dot as cwd
        if entry in ("", "."):
            return True
        return _normalize(entry) == _normalize(cwd)

    env_pythonpath = os.environ.get("PYTHONPATH", "")
    cwd = os.getcwd()

    # Conditionally remove sys.path[0] only if it's the working directory
    if sys.path and _is_cwd_entry(sys.path[0], cwd):
        sys.path.pop(0)

    # Handle duplicates introduced by PYTHONPATH leading/trailing ':'
    if env_pythonpath.startswith(":") and env_pythonpath not in (f":{cwd}", ":."):
        # Remove next cwd entry at position 0, if present
        if sys.path and _is_cwd_entry(sys.path[0], cwd):
            sys.path.pop(0)
    elif env_pythonpath.endswith(":") and env_pythonpath not in (f"{cwd}:", ".:"):
        # Remove next cwd entry at position 1, if present
        if len(sys.path) > 1 and _is_cwd_entry(sys.path[1], cwd):
            sys.path.pop(1)


version = __version__
