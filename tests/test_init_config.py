"""Tests for devops.__init__.init_config function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from devops.config import init_config
from devops.config.config import GlobalConfig

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from _pytest.logging import LogCaptureFixture


def test_init_config_single_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init_config when a single config file exists."""
    # Create a single config file
    config_file = tmp_path / "devops.toml"
    config_file.write_text('[exclude]\nbuggy_cpp_macros = ["MACRO1"]\n')

    # Change to the temp directory so the config file is found
    monkeypatch.chdir(tmp_path)

    # Call init_config
    config = init_config()

    # Verify the config was loaded correctly
    assert isinstance(config, GlobalConfig)
    assert config.exclude.buggy_cpp_macros == ["MACRO1"]


def test_init_config_single_hidden_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init_config when a single hidden config file exists."""
    # Create a single hidden config file
    config_file = tmp_path / ".devops.toml"
    config_file.write_text('[exclude]\nbuggy_cpp_macros = ["MACRO2"]\n')

    # Change to the temp directory so the config file is found
    monkeypatch.chdir(tmp_path)

    # Call init_config
    config = init_config()

    # Verify the config was loaded correctly
    assert isinstance(config, GlobalConfig)
    assert config.exclude.buggy_cpp_macros == ["MACRO2"]


def test_init_config_no_config_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    """Test init_config when no config file exists."""
    # Change to the temp directory which has no config files
    monkeypatch.chdir(tmp_path)

    # Capture logs
    with caplog.at_level(logging.DEBUG):
        config = init_config()

    # Verify default config is returned
    assert isinstance(config, GlobalConfig)
    assert config.exclude.buggy_cpp_macros == []

    # Verify the debug message was logged
    assert "No config file found. Using default configuration." in caplog.text


def test_init_config_multiple_config_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    """Test init_config when multiple config files exist."""
    # Create multiple config files
    config_file1 = tmp_path / "devops.toml"
    config_file1.write_text('[exclude]\nbuggy_cpp_macros = ["MACRO1"]\n')

    config_file2 = tmp_path / ".devops.toml"
    config_file2.write_text('[exclude]\nbuggy_cpp_macros = ["MACRO2"]\n')

    # Change to the temp directory
    monkeypatch.chdir(tmp_path)

    # Capture logs at WARNING level
    with caplog.at_level(logging.WARNING):
        config = init_config()

    # Verify default config is returned (since multiple files were found)
    assert isinstance(config, GlobalConfig)
    assert config.exclude.buggy_cpp_macros == []

    # Verify the warning message was logged
    assert "Multiple config files found" in caplog.text
    assert "devops.toml" in caplog.text
    assert ".devops.toml" in caplog.text
    assert "Using no config file." in caplog.text


def test_init_config_multiple_config_files_warning_contains_all_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    """Test that the warning message lists all found config files."""
    # Create multiple config files
    config_file1 = tmp_path / "devops.toml"
    config_file1.write_text('[exclude]\nbuggy_cpp_macros = ["MACRO1"]\n')

    config_file2 = tmp_path / ".devops.toml"
    config_file2.write_text('[exclude]\nbuggy_cpp_macros = ["MACRO2"]\n')

    # Change to the temp directory
    monkeypatch.chdir(tmp_path)

    # Capture logs at WARNING level
    with caplog.at_level(logging.WARNING):
        init_config()

    # Verify both file names are in the warning message
    warning_messages = [
        record.message for record in caplog.records if record.levelname == "WARNING"
    ]
    assert len(warning_messages) == 1

    warning_msg = warning_messages[0]
    assert "devops.toml" in warning_msg
    assert ".devops.toml" in warning_msg
