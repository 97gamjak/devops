"""Tests for the EnforceParamNameForType AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.enforce_param_name_for_type import (
    TYPE_TO_NAME,
    base_type_name,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

STRUCT_DEFS = "struct SimulationBox {};\nstruct ForceField {};\n"


class TestBaseTypeName:
    """Tests for the base_type_name helper."""

    @pytest.mark.parametrize(
        ("spelling", "expected"),
        [
            ("SimulationBox", "SimulationBox"),
            ("const SimulationBox &", "SimulationBox"),
            ("SimulationBox *", "SimulationBox"),
            ("const SimulationBox *", "SimulationBox"),
            ("SimulationBox &&", "SimulationBox"),
        ],
    )
    def test_strips_qualifiers_and_decoration(
        self, spelling: str, expected: str
    ) -> None:
        """Cv-qualifiers and pointer/reference decoration are stripped.

        Parameters
        ----------
        spelling: str
            Raw libclang type spelling.
        expected: str
            The bare base type name it should resolve to.

        """
        assert base_type_name(spelling) == expected


class TestEnforceParamNameForType:
    """Tests for the EnforceParamNameForType check via the shared engine."""

    def test_flags_wrong_name_for_mapped_type(self, tmp_path: Path) -> None:
        """A mapped type with the wrong parameter name is flagged.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"])

        assert len(diagnostics) == 1
        assert diagnostics[0].check_id == "paramNameForType"
        assert "simBox" in diagnostics[0].message
        assert "simulationBox" in diagnostics[0].message

    def test_correct_name_passes_clean(self, tmp_path: Path) -> None:
        """A mapped type using the required name raises no diagnostics.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "clean.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox simulationBox) {}\n"

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"])

        assert diagnostics == []

    @pytest.mark.parametrize(
        "decl",
        [
            "void foo(const SimulationBox &box) {}",
            "void foo(SimulationBox *box) {}",
            "void foo(const SimulationBox *box) {}",
        ],
    )
    def test_flags_regardless_of_ref_or_pointer_decoration(
        self, tmp_path: Path, decl: str
    ) -> None:
        """Reference/pointer/const decoration doesn't hide a naming violation.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        decl: str
            A function declaration using a decorated SimulationBox parameter
            named "box" instead of "simulationBox".

        """
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + decl + "\n"

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"])

        assert len(diagnostics) == 1
        assert "box" in diagnostics[0].message

    def test_unmapped_type_is_ignored(self, tmp_path: Path) -> None:
        """Parameters of a type with no entry in TYPE_TO_NAME aren't flagged.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "example.cpp"
        content = "void foo(int whatever) {}\n"

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"])

        assert diagnostics == []

    def test_unnamed_parameter_is_ignored(self, tmp_path: Path) -> None:
        """An unnamed parameter (e.g. in a declaration) isn't flagged.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox);\n"

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"])

        assert diagnostics == []

    @pytest.mark.parametrize("type_name", list(TYPE_TO_NAME))
    def test_each_mapped_type_is_enforced(
        self, tmp_path: Path, type_name: str
    ) -> None:
        """Every entry in TYPE_TO_NAME is individually enforced.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        type_name: str
            The mapped type name being tested.

        """
        cpp_file = tmp_path / "example.cpp"
        content = (
            f"struct {type_name} {{}};\n"
            f"void foo({type_name} wrongName) {{}}\n"
        )

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"])

        assert len(diagnostics) == 1
        assert TYPE_TO_NAME[type_name] in diagnostics[0].message
