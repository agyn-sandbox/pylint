"""
Reproduction for issue: running pylint via runpy removes sys.path[0] unconditionally,
causing plugins provided at sys.path[0] to fail to import.

This script:
- Creates a temporary directory with a simple plugin module `tmp_plugin.py`.
- Prepends that directory to sys.path (index 0).
- Sets sys.argv to load the plugin via --load-plugins and lint a trivial file.
- Calls runpy.run_module('pylint', run_name='__main__', alter_sys=True).

Current behavior (before fix):
- Pylint unconditionally pops sys.path[0], leading to ModuleNotFoundError for tmp_plugin.

Expected behavior (after fix):
- sys.path[0] is only removed when it is "", ".", or equals os.getcwd() (normalized).
- Since sys.path[0] is a non-cwd path (the temp plugin directory), it is retained,
  and the plugin imports successfully.

Run locally:
  python3 examples/repro_runpy_plugin.py
"""

import os
import sys
import tempfile
import textwrap
import runpy


def main() -> None:
    # Prepare temp plugin directory
    tmpdir = tempfile.mkdtemp(prefix="pylint_tmp_plugin_")
    plugin_path = os.path.join(tmpdir, "tmp_plugin.py")
    with open(plugin_path, "w", encoding="utf-8") as f:
        f.write(
            textwrap.dedent(
                """
                # Minimal plugin for reproduction
                def register(linter):
                    # Register nothing; presence is enough to prove import
                    pass
                """
            )
        )

    # Create a trivial file to lint
    target_file = os.path.join(tmpdir, "target.py")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("print('hello')\n")

    # Prepend plugin dir to sys.path so that 'tmp_plugin' is importable
    sys.path.insert(0, tmpdir)

    # Ensure our cloned pylint package is importable via PYTHONPATH
    repo_root = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, repo_root)

    # Prepare arguments: load our plugin and lint the target file
    sys.argv = [
        "pylint",
        "--load-plugins",
        "tmp_plugin",
        target_file,
        "-sn",  # no reports, short names
    ]

    # Run as a module, emulating `python -m pylint`
    try:
        runpy.run_module("pylint", run_name="__main__", alter_sys=True)
    except Exception as e:
        # Show the failure clearly
        print("ERROR:", type(e).__name__, str(e))
        raise


if __name__ == "__main__":
    main()

