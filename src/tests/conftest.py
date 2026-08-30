"""Per-test isolation of the runtime-data root.

Every test gets its own APOCRYSIS_HOME under a fresh temp dir, so saves,
profiles and play logs written during a test never touch the real
`.apocrysis/` tree, the repo root, or another test's state. Tests that
pass an explicit absolute path keep using it (runtime_paths.resolve
honours a path with a directory component).
"""
import pytest


@pytest.fixture(autouse=True)
def _isolate_apocrysis_home(tmp_path, monkeypatch):
    monkeypatch.setenv("APOCRYSIS_HOME", str(tmp_path / ".apocrysis"))
