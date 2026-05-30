from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

from pi_sync.cli import _find_pi_bin, main


def test_find_pi_bin_skips_wrapper(tmp_path):
    wrapper_dir = tmp_path / "local" / "bin"
    real_dir = tmp_path / "real" / "bin"
    wrapper_dir.mkdir(parents=True)
    real_dir.mkdir(parents=True)
    wrapper = wrapper_dir / "pi"
    real = real_dir / "pi"
    wrapper.write_text("#!/bin/sh\n")
    real.write_text("#!/bin/sh\n")

    with patch.dict(os.environ, {"PATH": f"{wrapper_dir}:{real_dir}"}):
        assert _find_pi_bin(wrapper) == real


def test_install_writes_executable_wrapper(tmp_path):
    wrapper = tmp_path / "local" / "bin" / "pi"
    real = tmp_path / "real" / "bin" / "pi"
    real.parent.mkdir(parents=True)
    real.write_text("#!/bin/sh\n")

    rc = main(["install", "--wrapper", str(wrapper), "--pi-bin", str(real)])

    assert rc == 0
    assert wrapper.exists()
    assert wrapper.stat().st_mode & stat.S_IXUSR
    assert "pi-sync" in wrapper.read_text()
    assert f"exec {real}" in wrapper.read_text()


def test_install_refuses_existing_without_force(tmp_path):
    wrapper = tmp_path / "bin" / "pi"
    real = tmp_path / "real" / "pi"
    wrapper.parent.mkdir(parents=True)
    real.parent.mkdir(parents=True)
    wrapper.write_text("existing")
    real.write_text("#!/bin/sh\n")

    rc = main(["install", "--wrapper", str(wrapper), "--pi-bin", str(real)])

    assert rc != 0


def test_install_dry_run_does_not_write(tmp_path):
    wrapper = tmp_path / "bin" / "pi"
    real = tmp_path / "real" / "pi"
    real.parent.mkdir(parents=True)
    real.write_text("#!/bin/sh\n")

    rc = main(["install", "--wrapper", str(wrapper), "--pi-bin", str(real), "--dry-run"])

    assert rc == 0
    assert not wrapper.exists()
