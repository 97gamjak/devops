"""Tests for the NoForbiddenInclude AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.no_forbidden_include import (
    NoForbiddenInclude,
    matches_forbidden_include,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path, config: dict | None = None) -> list[str]:
    (tmp_path / "mp-units" / "systems").mkdir(parents=True)
    (tmp_path / "mp-units" / "core.h").write_text("// empty\n")
    (tmp_path / "mp-units" / "systems" / "si.h").write_text("// empty\n")
    (tmp_path / "mp-units-other.h").write_text("// empty\n")
    p = tmp_path / "test.cpp"
    p.write_text(code)
    check = NoForbiddenInclude()
    check.configure(config if config is not None else {"libs": ["mp-units"]})
    args = [*_ARGS, f"-I{tmp_path}"]
    return [d.message for d in run_ast_checks(p, code, args, checks=[check])]


class TestNoForbiddenInclude:
    """Includes of forbidden libraries are flagged."""

    @pytest.mark.parametrize(
        "line",
        [
            '#include "mp-units/core.h"',
            "#include <mp-units/core.h>",
            "#include <mp-units/systems/si.h>",
        ],
    )
    def test_flagged(self, tmp_path: Path, line: str) -> None:
        """Test lib and all subfiles are flagged, quoted or not."""
        assert len(_diags(line + "\n", tmp_path)) == 1

    def test_similar_name_allowed(self, tmp_path: Path) -> None:
        """Test a file merely sharing the name prefix is allowed."""
        assert _diags('#include "mp-units-other.h"\n', tmp_path) == []

    def test_no_libs_allowed(self, tmp_path: Path) -> None:
        """Test nothing is flagged when unconfigured."""
        assert _diags("#include <mp-units/core.h>\n", tmp_path, {}) == []

    def test_exclude_paths(self, tmp_path: Path) -> None:
        """Test excluded including files are allowed."""
        cfg = {"libs": ["mp-units"], "exclude_paths": ["*test.cpp"]}
        assert _diags("#include <mp-units/core.h>\n", tmp_path, cfg) == []


class TestMatching:
    """Pattern matching semantics."""

    def test_glob(self) -> None:
        """Test glob patterns."""
        assert matches_forbidden_include("a/b_deprecated.hpp", ("*_deprecated.hpp",))

    def test_trailing_slash(self) -> None:
        """Test trailing slash directory prefix."""
        assert matches_forbidden_include("mp-units/x.h", ("mp-units/",))


class TestConfig:
    """Configuration validation."""

    def test_invalid_config_raises(self) -> None:
        """Test invalid config raises."""
        with pytest.raises(ConfigError):
            NoForbiddenInclude().configure({"libs": "mp-units"})

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoForbiddenInclude().id == "noForbiddenInclude"
