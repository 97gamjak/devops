"""Tests for ASTChecksRule, the Rule adapter around the AST-check engine."""

from __future__ import annotations

import json
import typing

import clang.cindex as clang
import pytest

from devops.cpp.ast.rule import ASTChecksRule, _args_from_compile_commands
from devops.rules import FileRuleInput, ResultTypeEnum

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")


class TestASTChecksRule:
    """Tests for ASTChecksRule."""

    def test_ok_on_clean_file(self, tmp_path: Path) -> None:
        """A file with no violations returns Ok.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "clean.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simulationBox) {}\n"
        cpp_file.write_text(content)

        rule = ASTChecksRule()
        result = rule.apply(FileRuleInput(file_content=content, path=cpp_file))

        assert result.value == ResultTypeEnum.Ok

    def test_error_on_violation(self, tmp_path: Path) -> None:
        """A file with a violation returns an Error with a description.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "bad.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        rule = ASTChecksRule(
            check_config={
                "paramNameForType": {"type_to_name": {"SimulationBox": "simulationBox"}}
            }
        )
        result = rule.apply(FileRuleInput(file_content=content, path=cpp_file))

        assert result.value == ResultTypeEnum.Error
        assert "simBox" in result.description
        assert "paramNameForType" in result.description

    def test_ok_when_path_missing(self) -> None:
        """No path means nothing to parse, so the rule returns Ok."""
        rule = ASTChecksRule()
        result = rule.apply(FileRuleInput(file_content="void foo() {}", path=None))

        assert result.value == ResultTypeEnum.Ok


def _write_compile_commands(
    tmp_path: Path, directory: Path, file: Path, command: str
) -> None:
    """Write a one-entry compile_commands.json under `directory`."""
    (directory / "compile_commands.json").write_text(
        json.dumps(
            [{"directory": str(tmp_path), "file": str(file), "command": command}]
        )
    )


class TestArgsFromCompileCommands:
    """`-include`/PCH handling: bare (GCC) and -Xclang-wrapped (Clang) forms.

    Regression coverage for a real bug: a bare `-include <pch>.hxx` (as GCC
    emits for CMake's target_precompile_headers, unlike Clang's
    `-Xclang -include -Xclang <pch>.hxx`) used to have its file argument
    silently dropped by the positional-source-file heuristic (it ends in
    `.hxx`, one of `_SOURCE_EXTENSIONS`) while the `-include` flag itself
    was kept — leaving a dangling `-include` that then swallowed the next
    *unrelated* flag in the args list as its filename, producing a fatal
    "file not found" libclang parse error for a file that was never
    referenced by the project at all.
    """

    def test_bare_include_and_its_file_are_both_dropped(self, tmp_path: Path) -> None:
        """Test bare include and its file are both dropped."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        command = (
            "/usr/bin/g++-13 -Winvalid-pch -include "
            f"{tmp_path}/cmake_pch.hxx -std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        assert "-include" not in args
        assert not any(a.endswith("cmake_pch.hxx") for a in args)
        # No flag is left dangling right before our own appended flags.
        idx = args.index("-Wno-unknown-warning-option")
        assert args[idx - 1] != "-include"

    def test_xclang_wrapped_include_pch_is_dropped(self, tmp_path: Path) -> None:
        """Test xclang wrapped include pch is dropped."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        command = (
            "/usr/bin/clang++-20 -Xclang -include-pch -Xclang "
            f"{tmp_path}/pch.pch -std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        assert "-include-pch" not in args
        assert not any(a.endswith("pch.pch") for a in args)

    def test_xclang_wrapped_include_is_dropped(self, tmp_path: Path) -> None:
        """Test xclang wrapped include is dropped (Clang's own -include form)."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        command = (
            "/usr/bin/clang++-20 -Xclang -include -Xclang "
            f"{tmp_path}/cmake_pch.hxx -std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        assert "-include" not in args
        assert not any(a.endswith("cmake_pch.hxx") for a in args)

    def test_other_xclang_pairs_are_preserved(self, tmp_path: Path) -> None:
        """Test other xclang pairs are preserved."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        command = (
            "/usr/bin/clang++-20 -Xclang -fsome-frontend-flag "
            f"-std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        assert "-Xclang" in args
        assert "-fsome-frontend-flag" in args
