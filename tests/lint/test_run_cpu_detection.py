"""Tests for CPU detection helpers in pylint.lint.run."""

from __future__ import annotations

import builtins
import io

from pylint.lint import run as lint_run


def _patch_cgroup(monkeypatch, files: dict[str, str]) -> None:
    """Patch cgroup file helpers for ``lint_run._query_cpu``."""

    class _FakePath:
        def __init__(self, path: str) -> None:
            self._path = path

        def is_file(self) -> bool:  # pragma: no cover - redirection helper
            return self._path in files

    real_open = builtins.open

    def _fake_open(path: str, *args, **kwargs):
        if path in files:
            return io.StringIO(files[path])
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(lint_run, "Path", _FakePath)
    monkeypatch.setattr("builtins.open", _fake_open)


def test_query_cpu_shares_fraction_clamped_to_one(monkeypatch) -> None:
    files = {
        "/sys/fs/cgroup/cpu/cpu.cfs_quota_us": "-1",
        "/sys/fs/cgroup/cpu/cpu.shares": "2",
    }
    _patch_cgroup(monkeypatch, files)

    assert lint_run._query_cpu() == 1


def test_query_cpu_quota_period_fraction_clamped_to_one(monkeypatch) -> None:
    files = {
        "/sys/fs/cgroup/cpu/cpu.cfs_quota_us": "50000",
        "/sys/fs/cgroup/cpu/cpu.cfs_period_us": "100000",
    }
    _patch_cgroup(monkeypatch, files)

    assert lint_run._query_cpu() == 1


def test_cpu_count_ignores_zero_share(monkeypatch) -> None:
    monkeypatch.setattr(lint_run.os, "sched_getaffinity", lambda _pid: {0, 1})

    monkeypatch.setattr(lint_run, "_query_cpu", lambda: 0)
    assert lint_run._cpu_count() == 2

    monkeypatch.setattr(lint_run, "_query_cpu", lambda: 1)
    assert lint_run._cpu_count() == 1
