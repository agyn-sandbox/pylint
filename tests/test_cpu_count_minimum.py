import os
from pylint.lint import run as run_mod


def test_cpu_count_clamped_to_minimum(monkeypatch):
    """_cpu_count should never return 0 even if _query_cpu reports 0.

    This covers cases where cgroup-derived estimates truncate to 0 (e.g.,
    cpu.shares < 1024 or quota < period). The clamping in _cpu_count should
    force a minimum of 1.
    """
    # Force _query_cpu to report 0
    monkeypatch.setattr(run_mod, "_query_cpu", lambda: 0)

    # Ensure a sane cpu_count path; regardless of affinity/multiprocessing,
    # the function should clamp to at least 1.
    if hasattr(os, "sched_getaffinity"):
        monkeypatch.setattr(os, "sched_getaffinity", lambda _pid: {0, 1})

    result = run_mod._cpu_count()
    assert result >= 1
