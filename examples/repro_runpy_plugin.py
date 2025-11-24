"""Minimal repro for runpy --load-plugins regression."""

from __future__ import annotations

import runpy
import sys
import tempfile
from pathlib import Path

PLUGIN_SOURCE = '''
def register(linter):
    """Register dummy plugin."""

'''

TARGET_SOURCE = '''
print('hello from target')
'''


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pylint-repro-") as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "tmp_plugin.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
        (tmp_dir / "target.py").write_text(TARGET_SOURCE, encoding="utf-8")
        sys.path.insert(0, str(tmp_dir))
        sys.argv = [
            "pylint",
            "--load-plugins",
            "tmp_plugin",
            str(tmp_dir / "target.py"),
            "--exit-zero",
        ]
        runpy.run_module("pylint", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
