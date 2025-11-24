"""Tests for parallel lint job handling."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pylint.lint import parallel
from pylint.utils.linterstats import LinterStats


def test_check_parallel_jobs_zero_uses_one_process(monkeypatch) -> None:
    created_processes: list[int] = []

    class DummyPool:
        def __init__(self, processes: int, _initializer, _initargs) -> None:
            created_processes.append(processes)

        def __enter__(self):  # pragma: no cover - context helper
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - context helper
            return False

        def imap_unordered(self, _func, _iterable):
            return iter(())

        def close(self) -> None:
            return None

        def join(self) -> None:
            return None

    class DummyLinter:
        def __init__(self) -> None:
            self.file_state = SimpleNamespace(base_name="", _is_base_filestate=True)
            self.reporter = SimpleNamespace(handle_message=lambda *_args, **_kwargs: None)
            self.stats = LinterStats()
            self.msg_status = 0

        def open(self) -> None:
            return None

        def get_checkers(self):
            return []

        def set_current_module(self, _module, _file_path) -> None:
            return None

    dummy_linter = DummyLinter()

    if parallel.multiprocessing is None:  # pragma: no cover - platform guard
        pytest.skip("multiprocessing not available")

    monkeypatch.setattr(parallel.multiprocessing, "Pool", DummyPool)

    with pytest.warns(UserWarning, match="jobs must be >= 1; defaulting to 1"):
        parallel.check_parallel(dummy_linter, jobs=0, files=[])

    assert created_processes == [1]
