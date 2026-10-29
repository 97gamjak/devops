"""Tests for ASTChecksRule, the Rule adapter around the AST-check engine."""

from __future__ import annotations

import json
import typing

import clang.cindex as clang
import pytest

from devops.cpp.ast.rule import (
    ASTChecksRule,
    _args_for_header,
    _args_from_compile_commands,
    _load_entries,
)
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

    def test_check_file_matches_apply(self, tmp_path: Path) -> None:
        """check_file() is equivalent to apply() with a FileRuleInput."""
        cpp_file = tmp_path / "bad.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        check_config = {
            "paramNameForType": {"type_to_name": {"SimulationBox": "simulationBox"}}
        }
        via_apply = ASTChecksRule(check_config=check_config).apply(
            FileRuleInput(file_content=content, path=cpp_file)
        )
        via_check_file = ASTChecksRule(check_config=check_config).check_file(
            cpp_file, content
        )

        assert via_apply.value == via_check_file.value == ResultTypeEnum.Error
        assert via_apply.description == via_check_file.description

    def test_from_spec_rebuilds_equivalent_rule(self, tmp_path: Path) -> None:
        """from_spec(worker_spec()) behaves like the original instance.

        This is the contract devops.cpp.checks relies on to run AST checks
        across a ProcessPoolExecutor: a worker can't receive the original
        rule (it holds an unpicklable clang.CompilationDatabase), only its
        worker_spec(), and must rebuild an equivalent rule from that.
        """
        cpp_file = tmp_path / "bad.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        original = ASTChecksRule(
            check_config={
                "paramNameForType": {"type_to_name": {"SimulationBox": "simulationBox"}}
            }
        )
        rebuilt = ASTChecksRule.from_spec(original.worker_spec())

        result = rebuilt.check_file(cpp_file, content)
        assert result.value == ResultTypeEnum.Error
        assert "simBox" in result.description

    def test_collect_and_merge_state_roundtrip(self, tmp_path: Path) -> None:
        """merge_state(collect_state()) carries a check's state across instances.

        Mirrors how devops.cpp.checks merges a worker process's
        EnforceParamNameForType._seen_type_names snapshot back into the
        main process's rule after a parallel run.
        """
        cpp_file = tmp_path / "ok.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simulationBox) {}\n"
        cpp_file.write_text(content)

        type_to_name = {"SimulationBox": "simulationBox"}
        worker_rule = ASTChecksRule(
            check_config={
                "paramNameForType": {
                    "type_to_name": type_to_name,
                    "unseen_type_is_error": True,
                }
            }
        )
        worker_rule.check_file(cpp_file, content)

        main_rule = ASTChecksRule(
            check_config={
                "paramNameForType": {
                    "type_to_name": type_to_name,
                    "unseen_type_is_error": True,
                }
            }
        )
        # The main process's rule never saw any file directly in this test,
        # only the state collected from the (simulated) worker.
        main_rule.merge_state(worker_rule.collect_state())

        assert main_rule.finalize_run() is True


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

    Two bugs are covered here, both discovered from real project failures:

    1. A bare `-include <pch>.hxx` (as GCC emits for CMake's
       `target_precompile_headers`, unlike Clang's
       `-Xclang -include -Xclang <pch>.hxx`) used to have its file argument
       silently dropped by the positional-source-file heuristic (it ends in
       `.hxx`, one of `_SOURCE_EXTENSIONS`) while the `-include` flag itself
       was kept — leaving a dangling `-include` that then swallowed the next
       *unrelated* flag in the args list as its filename, producing a fatal
       "file not found" libclang parse error for a file that was never
       referenced by the project at all.

    2. The fix for (1) then dropped every `-include`/`-include-pch`
       unconditionally. That broke real headers that rely on the textual
       PCH header (the plain `-include`, not the compiled `-include-pch`
       binary) always being force-included first for standard-library
       symbols (`<optional>`, `<format>`, ...) they don't include
       themselves — producing a cascade of unrelated "no member"/"too many
       errors" failures when checking such a header standalone. So a plain
       `-include <file>` is now kept (normalized to a bare pair) whenever
       that file exists on disk, and only dropped when it's missing (e.g. a
       fresh/partial checkout) — while `-include-pch` (the compiled binary,
       generally incompatible with pip's bundled libclang regardless of
       whether it exists) is still always dropped.

    3. The fix for (2) in turn missed that a *compiled* PCH cache
       (`.gch`/`.pch`) sitting next to the plain `-include <file>` is
       auto-detected and silently preferred by GCC/Clang themselves, even
       without an explicit `-include-pch`. A plain `-include` is now also
       dropped whenever such a sibling cache file exists, for the same
       incompatibility reason as `-include-pch`.
    """

    def test_bare_include_dropped_when_file_missing(self, tmp_path: Path) -> None:
        """Test bare include dropped when file missing."""
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

    def test_bare_include_kept_when_file_exists(self, tmp_path: Path) -> None:
        """Test bare include kept when file exists."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        pch_header = tmp_path / "cmake_pch.hxx"
        pch_header.write_text("#include <optional>\n")
        command = (
            f"/usr/bin/g++-13 -Winvalid-pch -include {pch_header} "
            f"-std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        idx = args.index("-include")
        assert args[idx + 1] == str(pch_header)

    def test_bare_include_dropped_when_compiled_pch_sibling_exists(
        self, tmp_path: Path
    ) -> None:
        """A plain `-include` is dropped when a compiled .pch/.gch sits beside it.

        GCC/Clang both auto-detect and silently prefer a compiled cache next
        to a plain `-include <file>` (`.gch` for GCC, `.pch` for Clang,
        emitted together by CMake's `target_precompile_headers()`),
        regardless of whether `-include-pch` was passed explicitly. That
        compiled cache is serialized by the project's own compiler and is
        generally incompatible with pip's bundled libclang, so keeping the
        textual file here doesn't actually avoid the fatal parse error it
        was kept to avoid.
        """
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        pch_header = tmp_path / "cmake_pch.hxx"
        pch_header.write_text("#include <optional>\n")
        (tmp_path / "cmake_pch.hxx.pch").write_bytes(b"not a real pch")
        command = (
            f"/usr/bin/g++-13 -Winvalid-pch -include {pch_header} "
            f"-std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        assert "-include" not in args
        assert not any(a.endswith("cmake_pch.hxx") for a in args)

    def test_xclang_wrapped_include_pch_is_always_dropped(self, tmp_path: Path) -> None:
        """The compiled PCH binary is dropped even when the file exists."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        pch_binary = tmp_path / "pch.pch"
        pch_binary.write_bytes(b"not a real pch")
        command = (
            f"/usr/bin/clang++-20 -Xclang -include-pch -Xclang {pch_binary} "
            f"-std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        assert "-include-pch" not in args
        assert not any(a.endswith("pch.pch") for a in args)

    def test_xclang_wrapped_include_dropped_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """Test xclang wrapped include dropped when file missing."""
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

    def test_xclang_wrapped_include_kept_when_file_exists(self, tmp_path: Path) -> None:
        """Kept (and normalized to a bare pair) when the file exists."""
        db_dir = tmp_path
        cpp_file = tmp_path / "foo.cpp"
        cpp_file.write_text("void f() {}\n")
        pch_header = tmp_path / "cmake_pch.hxx"
        pch_header.write_text("#include <optional>\n")
        command = (
            f"/usr/bin/clang++-20 -Xclang -include -Xclang {pch_header} "
            f"-std=c++23 -o foo.o -c {cpp_file}"
        )
        _write_compile_commands(tmp_path, db_dir, cpp_file, command)

        db = clang.CompilationDatabase.fromDirectory(str(db_dir))
        args = _args_from_compile_commands(db, cpp_file)

        assert args is not None
        idx = args.index("-include")
        assert args[idx + 1] == str(pch_header)

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


class TestHeaderCompileArgs:
    """A header is checked with the flags of a TU that can reach it.

    Headers never have a compile-database entry of their own (CMake only
    records translation units), so they must not fall back to bare default
    flags: that loses every per-target ``-I``/``-isystem`` (e.g. a header-only
    dependency such as ``mstd``) and makes libclang abort on the first include.
    """

    @staticmethod
    def _project(root: Path) -> Path:
        """Build a tiny project; only the ``mod`` target sees ``dep``.

        The unrelated ``sibling.cpp`` sits right next to the header, so
        libclang's path-similarity guess for a header with no entry of its
        own picks it -- the wrong unit, which has no ``dep`` on its path.

        Parameters
        ----------
        root: Path
            Directory to create the project in.

        Returns
        -------
        Path
            The header that depends on ``<dep/dep.hpp>``.

        """
        dep_inc = root / "external/dep/include"
        (dep_inc / "dep").mkdir(parents=True)
        (dep_inc / "dep/dep.hpp").write_text("#define DEP 1\n")
        (root / "include/mod/sub").mkdir(parents=True)
        (root / "include/other").mkdir(parents=True)
        (root / "src").mkdir()
        header = root / "include/mod/sub/a.hpp"
        header.write_text("#pragma once\n#include <dep/dep.hpp>\nint a = DEP;\n")
        (root / "include/other/b.hpp").write_text("#pragma once\n")
        mod_cpp = root / "src/mod.cpp"
        sibling = root / "include/mod/sub/sibling.cpp"
        mod_cpp.write_text('#include "sub/a.hpp"\n')
        sibling.write_text('#include "b.hpp"\n')
        entries = [
            {
                "directory": str(root),
                "file": str(sibling),
                "command": f"/usr/bin/clang++ -std=c++23 -I{root}/include/other "
                f"-c {sibling}",
            },
            {
                "directory": str(root),
                "file": str(mod_cpp),
                "command": f"/usr/bin/clang++ -std=c++23 -I {root}/include/mod "
                f"-isystem {dep_inc} -c {mod_cpp}",
            },
        ]
        (root / "compile_commands.json").write_text(json.dumps(entries))
        return header

    def test_header_uses_flags_of_tu_that_reaches_it(self, tmp_path: Path) -> None:
        """The header gets the flags of the unit with its dir on the -I path."""
        header = self._project(tmp_path)
        db = clang.CompilationDatabase.fromDirectory(str(tmp_path))

        args = _args_for_header(_load_entries(db), header)

        assert args is not None
        assert "-isystem" in args
        assert str(tmp_path / "external/dep/include") in args

    def test_most_specific_include_dir_wins(self, tmp_path: Path) -> None:
        """``include/other`` beats a broader ``include`` for the same header."""
        header = self._project(tmp_path)
        broad = tmp_path / "src/broad.cpp"
        broad.write_text("")
        entries = json.loads((tmp_path / "compile_commands.json").read_text())
        entries.append(
            {
                "directory": str(tmp_path),
                "file": str(broad),
                "command": f"/usr/bin/clang++ -DBROAD -I{tmp_path}/include -c {broad}",
            }
        )
        (tmp_path / "compile_commands.json").write_text(json.dumps(entries))
        db = clang.CompilationDatabase.fromDirectory(str(tmp_path))

        args = _args_for_header(_load_entries(db), header)

        assert args is not None
        assert "-DBROAD" not in args

    def test_stem_match_wins_over_broader_sibling_on_tied_depth(
        self, tmp_path: Path
    ) -> None:
        """A same-named TU wins a depth tie even with fewer include dirs.

        Mirrors a real-world shared test-fixture header: many ``.cpp`` files
        put the same directory on their ``-I`` path (tying on depth), but
        only the header's own same-named TU actually has the dependency it
        needs on its path. A breadth-only tie-break would instead pick a
        "richer" sibling that ties on depth but lacks that dependency.
        """
        (tmp_path / "include/foo").mkdir(parents=True)
        (tmp_path / "include/other").mkdir()
        (tmp_path / "include/third").mkdir()
        dep_inc = tmp_path / "external/dep/include"
        (dep_inc / "dep").mkdir(parents=True)
        (dep_inc / "dep/dep.hpp").write_text("#define DEP 1\n")
        header = tmp_path / "include/foo/foo.hpp"
        header.write_text("#pragma once\n#include <dep/dep.hpp>\nint v = DEP;\n")
        (tmp_path / "src").mkdir()
        own_tu = tmp_path / "src/foo.cpp"
        own_tu.write_text('#include "foo/foo.hpp"\n')
        richer_tu = tmp_path / "src/bar.cpp"
        richer_tu.write_text("")
        entries = [
            {
                "directory": str(tmp_path),
                "file": str(own_tu),
                "command": f"/usr/bin/clang++ -std=c++23 -I{tmp_path}/include "
                f"-isystem {dep_inc} -c {own_tu}",
            },
            {
                "directory": str(tmp_path),
                "file": str(richer_tu),
                "command": f"/usr/bin/clang++ -std=c++23 -I{tmp_path}/include "
                f"-I{tmp_path}/include/other -I{tmp_path}/include/third "
                f"-DRICHER -c {richer_tu}",
            },
        ]
        (tmp_path / "compile_commands.json").write_text(json.dumps(entries))
        db = clang.CompilationDatabase.fromDirectory(str(tmp_path))

        args = _args_for_header(_load_entries(db), header)

        assert args is not None
        assert "-DRICHER" not in args
        assert str(dep_inc) in args

    def test_same_dir_stem_match_beats_weak_unrelated_explicit_match(
        self, tmp_path: Path
    ) -> None:
        """A stem-matching sibling in the header's own dir beats a weak ``-I``.

        Mirrors a header living directly in a shared directory (e.g.
        ``apps/validation.hpp``) whose only *explicit* ``-I`` match is an
        unrelated TU that happens to put that whole directory on its path
        (e.g. ``-I apps``) without needing anything the header actually
        depends on. Its same-directory, same-named sibling (``validation.cpp``)
        has the real dependency and should win instead.
        """
        (tmp_path / "apps/commandLine").mkdir(parents=True)
        (tmp_path / "apps/commandLine/args.hpp").write_text("#pragma once\n")
        (tmp_path / "unrelated").mkdir()
        header = tmp_path / "apps/validation.hpp"
        header.write_text('#pragma once\n#include "args.hpp"\n')
        own_tu = tmp_path / "apps/validation.cpp"
        own_tu.write_text("")
        other_tu = tmp_path / "apps/other.cpp"
        other_tu.write_text("")
        unrelated_tu = tmp_path / "unrelated/unrelated.cpp"
        unrelated_tu.write_text("")
        entries = [
            {
                "directory": str(tmp_path),
                "file": str(own_tu),
                "command": f"/usr/bin/clang++ -std=c++23 "
                f"-I{tmp_path}/apps/commandLine -c {own_tu}",
            },
            {
                "directory": str(tmp_path),
                "file": str(other_tu),
                "command": f"/usr/bin/clang++ -std=c++23 "
                f"-I{tmp_path}/apps/commandLine -c {other_tu}",
            },
            {
                "directory": str(tmp_path),
                "file": str(unrelated_tu),
                "command": f"/usr/bin/clang++ -std=c++23 -I{tmp_path}/apps "
                f"-DUNRELATED -c {unrelated_tu}",
            },
        ]
        (tmp_path / "compile_commands.json").write_text(json.dumps(entries))
        db = clang.CompilationDatabase.fromDirectory(str(tmp_path))

        args = _args_for_header(_load_entries(db), header)

        assert args is not None
        assert "-DUNRELATED" not in args
        assert any(str(tmp_path / "apps/commandLine") in a for a in args)

    def test_none_when_no_tu_reaches_header(self, tmp_path: Path) -> None:
        """A header outside every include path gets no borrowed flags."""
        self._project(tmp_path)
        lonely = tmp_path / "lonely/x.hpp"
        lonely.parent.mkdir()
        lonely.write_text("")
        db = clang.CompilationDatabase.fromDirectory(str(tmp_path))

        assert _args_for_header(_load_entries(db), lonely) is None

    def test_rule_parses_header_without_fatal_error(self, tmp_path: Path) -> None:
        """End to end: no ``astParseError`` for a header with a per-target dep."""
        header = self._project(tmp_path)
        content = header.read_text()

        with_db = ASTChecksRule(compile_commands_db=str(tmp_path))
        without_db = ASTChecksRule()
        ok = with_db.apply(FileRuleInput(file_content=content, path=header))
        broken = without_db.apply(FileRuleInput(file_content=content, path=header))

        assert ok.value == ResultTypeEnum.Ok
        assert broken.value == ResultTypeEnum.Error
        assert "astParseError" in broken.description
