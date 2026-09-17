"""Tests for the EnforceParamNameForType AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.enforce_param_name_for_type import (
    EnforceParamNameForType,
    base_type_name,
    declaration_type_key,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

STRUCT_DEFS = "struct SimulationBox {};\nstruct ForceField {};\n"

# The canonical mapping used across all engine-level tests.
_TYPE_TO_NAME = {
    "SimulationBox": "simulationBox",
    "ForceField": "forceField",
    "Optimizer": "optimizer",
}


@pytest.fixture
def configured_check() -> EnforceParamNameForType:
    """An EnforceParamNameForType instance pre-configured with _TYPE_TO_NAME."""
    check = EnforceParamNameForType()
    check.configure({"type_to_name": _TYPE_TO_NAME})
    return check


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
            # libclang canonical spellings include class/struct keyword
            ("class molsys::SimulationBox &", "molsys::SimulationBox"),
            ("const class molsys::SimulationBox &", "molsys::SimulationBox"),
            ("struct ns::Foo *", "ns::Foo"),
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


class TestEnforceParamNameForTypeConfiguration:
    """Tests for the configure() method."""

    def test_unconfigured_check_ignores_all_types(self, tmp_path: Path) -> None:
        """An unconfigured check (empty type_to_name) raises no diagnostics.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])

        assert diagnostics == []

    def test_configure_sets_type_to_name(self, tmp_path: Path) -> None:
        """After configure(), the mapped type is enforced.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"Foo": "foo"}})
        cpp_file = tmp_path / "example.cpp"
        content = "struct Foo {};\nvoid bar(Foo wrong) {}\n"
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])

        assert len(diagnostics) == 1
        assert "wrong" in diagnostics[0].message
        assert "foo" in diagnostics[0].message

    def test_configure_replaces_previous_mapping(self) -> None:
        """A second configure() call replaces the first mapping entirely.

        Parameters
        ----------
        (none)

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"A": "a"}})
        check.configure({"type_to_name": {"B": "b"}})

        assert check.type_to_name == {"B": ["b"]}

    def test_configure_missing_type_to_name_raises(self) -> None:
        """A config block without type_to_name raises ConfigError.

        Parameters
        ----------
        (none)

        """
        check = EnforceParamNameForType()
        with pytest.raises(ConfigError, match="type_to_name"):
            check.configure({})

    def test_configure_invalid_type_to_name_raises(self) -> None:
        """A non-dict value for type_to_name raises ConfigError.

        Parameters
        ----------
        (none)

        """
        check = EnforceParamNameForType()
        with pytest.raises(ConfigError):
            check.configure({"type_to_name": ["not", "a", "dict"]})

    def test_configure_non_str_value_raises(self) -> None:
        """A dict with a non-string value raises ConfigError.

        Parameters
        ----------
        (none)

        """
        check = EnforceParamNameForType()
        with pytest.raises(ConfigError):
            check.configure({"type_to_name": {"Foo": 42}})

    def test_configure_empty_dict_clears_mapping(self) -> None:
        """Configuring with an empty type_to_name dict clears the mapping.

        Parameters
        ----------
        (none)

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"Foo": "foo"}})
        check.configure({"type_to_name": {}})

        assert check.type_to_name == {}

    def test_global_finalize_warns_for_unseen_type(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """global_finalize warns if a configured type was never seen.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog: pytest.LogCaptureFixture
            Pytest log capture fixture.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"ns::Ghost": "ghost"}})
        cpp_file = tmp_path / "example.cpp"
        content = "void foo(int x) {}\n"
        cpp_file.write_text(content)

        run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])
        check.global_finalize()

        assert any("ns::Ghost" in r.message for r in caplog.records)

    def test_global_finalize_silent_when_type_was_seen(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """global_finalize emits no warning when the configured type was seen.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog: pytest.LogCaptureFixture
            Pytest log capture fixture.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"Foo": "foo"}})
        cpp_file = tmp_path / "example.cpp"
        content = "struct Foo {};\nvoid bar(Foo foo) {}\n"
        cpp_file.write_text(content)

        run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])
        check.global_finalize()

        assert not any("Foo" in r.message for r in caplog.records)

    def test_global_finalize_returns_false_when_unseen_type_is_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """global_finalize returns False and logs an error when unseen_type_is_error=true.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog: pytest.LogCaptureFixture
            Pytest log capture fixture.

        """
        check = EnforceParamNameForType()
        check.configure(
            {"type_to_name": {"ns::Ghost": "ghost"}, "unseen_type_is_error": True}
        )
        cpp_file = tmp_path / "example.cpp"
        content = "void foo(int x) {}\n"
        cpp_file.write_text(content)

        run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])
        result = check.global_finalize()

        assert result is False
        assert any(
            "ns::Ghost" in r.message and r.levelname == "ERROR" for r in caplog.records
        )

    def test_global_finalize_returns_true_when_all_types_seen(
        self, tmp_path: Path
    ) -> None:
        """global_finalize returns True when all configured types were seen.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        check.configure(
            {"type_to_name": {"Foo": "foo"}, "unseen_type_is_error": True}
        )
        cpp_file = tmp_path / "example.cpp"
        content = "struct Foo {};\nvoid bar(Foo foo) {}\n"
        cpp_file.write_text(content)

        run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])
        result = check.global_finalize()

        assert result is True


class TestEnforceParamNameForType:
    """Tests for the EnforceParamNameForType check via the shared engine."""

    def test_flags_wrong_name_for_mapped_type(
        self, tmp_path: Path, configured_check: EnforceParamNameForType
    ) -> None:
        """A mapped type with the wrong parameter name is flagged.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        configured_check: EnforceParamNameForType
            Pre-configured check instance.

        """
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(
            cpp_file, content, ["-std=c++23"], checks=[configured_check]
        )

        assert len(diagnostics) == 1
        assert diagnostics[0].check_id == "paramNameForType"
        assert "simBox" in diagnostics[0].message
        assert "simulationBox" in diagnostics[0].message

    def test_correct_name_passes_clean(
        self, tmp_path: Path, configured_check: EnforceParamNameForType
    ) -> None:
        """A mapped type using the required name raises no diagnostics.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        configured_check: EnforceParamNameForType
            Pre-configured check instance.

        """
        cpp_file = tmp_path / "clean.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox simulationBox) {}\n"

        diagnostics = run_ast_checks(
            cpp_file, content, ["-std=c++23"], checks=[configured_check]
        )

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
        self,
        tmp_path: Path,
        decl: str,
        configured_check: EnforceParamNameForType,
    ) -> None:
        """Reference/pointer/const decoration doesn't hide a naming violation.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        decl: str
            A function declaration using a decorated SimulationBox parameter
            named "box" instead of "simulationBox".
        configured_check: EnforceParamNameForType
            Pre-configured check instance.

        """
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + decl + "\n"

        diagnostics = run_ast_checks(
            cpp_file, content, ["-std=c++23"], checks=[configured_check]
        )

        assert len(diagnostics) == 1
        assert "box" in diagnostics[0].message

    def test_unmapped_type_is_ignored(
        self, tmp_path: Path, configured_check: EnforceParamNameForType
    ) -> None:
        """Parameters of a type with no entry in type_to_name aren't flagged.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        configured_check: EnforceParamNameForType
            Pre-configured check instance.

        """
        cpp_file = tmp_path / "example.cpp"
        content = "void foo(int whatever) {}\n"

        diagnostics = run_ast_checks(
            cpp_file, content, ["-std=c++23"], checks=[configured_check]
        )

        assert diagnostics == []

    def test_unnamed_parameter_is_ignored(
        self, tmp_path: Path, configured_check: EnforceParamNameForType
    ) -> None:
        """An unnamed parameter (e.g. in a declaration) isn't flagged.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        configured_check: EnforceParamNameForType
            Pre-configured check instance.

        """
        cpp_file = tmp_path / "example.cpp"
        content = STRUCT_DEFS + "void foo(SimulationBox);\n"

        diagnostics = run_ast_checks(
            cpp_file, content, ["-std=c++23"], checks=[configured_check]
        )

        assert diagnostics == []

    @pytest.mark.parametrize("type_name", list(_TYPE_TO_NAME))
    def test_each_mapped_type_is_enforced(
        self,
        tmp_path: Path,
        type_name: str,
        configured_check: EnforceParamNameForType,
    ) -> None:
        """Every entry in the configured type_to_name is individually enforced.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        type_name: str
            The mapped type name being tested.
        configured_check: EnforceParamNameForType
            Pre-configured check instance.

        """
        cpp_file = tmp_path / "example.cpp"
        content = (
            f"struct {type_name} {{}};\n"
            f"void foo({type_name} wrongName) {{}}\n"
        )

        diagnostics = run_ast_checks(
            cpp_file, content, ["-std=c++23"], checks=[configured_check]
        )

        assert len(diagnostics) == 1
        assert _TYPE_TO_NAME[type_name] in diagnostics[0].message

    def test_flags_namespaced_type_with_qualified_key(
        self, tmp_path: Path
    ) -> None:
        """A namespaced type is flagged when the TOML key uses the qualified name.

        libclang spells namespaced types as "ns::Type", so the configured key
        must match that fully-qualified spelling.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"ns::Foo": "foo"}})
        cpp_file = tmp_path / "example.cpp"
        content = "namespace ns { struct Foo {}; }\nvoid bar(ns::Foo wrong) {}\n"
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])

        assert len(diagnostics) == 1
        assert "wrong" in diagnostics[0].message
        assert "foo" in diagnostics[0].message

    def test_unqualified_key_misses_namespaced_type(
        self, tmp_path: Path
    ) -> None:
        """An unqualified key does NOT match a namespaced type (by design).

        Users must use the fully-qualified name in the TOML.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"Foo": "foo"}})  # missing "ns::"
        cpp_file = tmp_path / "example.cpp"
        content = "namespace ns { struct Foo {}; }\nvoid bar(ns::Foo wrong) {}\n"
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])

        assert diagnostics == []

    def test_unqualified_key_does_not_match_type_used_inside_its_own_namespace(
        self, tmp_path: Path
    ) -> None:
        """Unqualified key doesn't match when type is used inside its own namespace.

        When ``ns::Foo`` is used as ``Foo`` inside ``namespace ns { ... }``,
        libclang's canonical spelling is still ``ns::Foo``, so a key ``"Foo"``
        must not match it.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"Foo": "foo"}})  # missing "ns::"
        cpp_file = tmp_path / "example.cpp"
        # Foo is used without qualifier inside namespace ns — libclang canonical
        # spelling is still "ns::Foo", so unqualified key must not match.
        content = (
            "namespace ns {\n"
            "struct Foo {};\n"
            "void bar(Foo wrong) {}\n"
            "}\n"
        )
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])

        assert diagnostics == []

    def test_qualified_key_matches_type_used_via_using_namespace(
        self, tmp_path: Path
    ) -> None:
        """Qualified key matches a type brought in by 'using namespace'.

        When a .cpp file has ``using namespace ns;`` and uses ``Foo`` without
        a qualifier, the qualified key ``"ns::Foo"`` must still match because
        ``declaration_type_key`` walks the declaration hierarchy rather than
        parsing the spelling string.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        check = EnforceParamNameForType()
        check.configure({"type_to_name": {"ns::Foo": "foo"}})
        cpp_file = tmp_path / "example.cpp"
        content = (
            "namespace ns { struct Foo {}; }\n"
            "using namespace ns;\n"
            "void bar(Foo wrong) {}\n"
        )
        cpp_file.write_text(content)

        diagnostics = run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])

        assert len(diagnostics) == 1
        assert "wrong" in diagnostics[0].message
        assert "foo" in diagnostics[0].message
