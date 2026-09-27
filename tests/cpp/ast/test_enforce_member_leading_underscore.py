"""Tests for the EnforceMemberLeadingUnderscore AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.enforce_member_leading_underscore import (
    EnforceMemberLeadingUnderscore,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [EnforceMemberLeadingUnderscore()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestPrivateMembersFlagged:
    """Private data members without a leading underscore are flagged."""

    def test_private_field_flagged(self, tmp_path: Path) -> None:
        """Test private field flagged."""
        code = "class C {\nprivate:\n    int count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "private member variable 'count'" in diags[0]
        assert "'_count'" in diags[0]

    def test_private_static_field_flagged(self, tmp_path: Path) -> None:
        """Test private static field flagged."""
        code = "class C {\nprivate:\n    static int count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "count" in diags[0]

    def test_private_struct_field_flagged(self, tmp_path: Path) -> None:
        """Test private struct field flagged."""
        code = "struct S {\nprivate:\n    int count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestProtectedMembersFlagged:
    """Protected data members without a leading underscore are flagged."""

    def test_protected_field_flagged(self, tmp_path: Path) -> None:
        """Test protected field flagged."""
        code = "class C {\nprotected:\n    int count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "protected member variable 'count'" in diags[0]

    def test_protected_static_const_field_flagged(self, tmp_path: Path) -> None:
        """Test protected static const field flagged."""
        code = "class C {\nprotected:\n    static const int count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestMembersAllowed:
    """Public members and already-prefixed members are never flagged."""

    def test_public_field_allowed(self, tmp_path: Path) -> None:
        """Test public field allowed."""
        code = "class C {\npublic:\n    int count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_default_public_struct_field_allowed(self, tmp_path: Path) -> None:
        """Test default public struct field allowed."""
        code = "struct S {\n    int count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_private_field_with_underscore_allowed(self, tmp_path: Path) -> None:
        """Test private field with underscore allowed."""
        code = "class C {\nprivate:\n    int _count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_protected_field_with_underscore_allowed(self, tmp_path: Path) -> None:
        """Test protected field with underscore allowed."""
        code = "class C {\nprotected:\n    int _count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_local_and_global_variables_allowed(self, tmp_path: Path) -> None:
        """Test local and global variables allowed."""
        code = "int global;\nvoid f() {\n    int local;\n    (void)local;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_macro_synthesized_member_allowed(self, tmp_path: Path) -> None:
        """A member declared entirely inside a macro body is not flagged.

        Mirrors gtest's ``TEST_F(...)`` expanding to a fixture class with its
        own private ``test_info_`` member: the whole class is synthesized on
        the macro-invocation line, so there is no user-typed name to rename.
        """
        code = (
            "#define DECLARE_FIXTURE(name) \\\n"
            "    class name { \\\n"
            "    private: \\\n"
            "        static int test_info_; \\\n"
            "    };\n"
            "DECLARE_FIXTURE(Foo)\n"
        )
        assert _diags(code, tmp_path) == []

    def test_field_sharing_a_macro_call_line_still_allowed(
        self, tmp_path: Path
    ) -> None:
        """A macro-instantiation line's own range covers the whole invocation."""
        code = "#define NOOP(x)\nclass C {\nprivate:\n    NOOP(1) int count;\n};\n"
        # The macro invocation and the field share line 4, so this is the
        # documented trade-off: skipped rather than flagged.
        assert _diags(code, tmp_path) == []

    def test_lambda_capture_allowed(self, tmp_path: Path) -> None:
        """Test lambda capture allowed."""
        code = (
            "void f() {\n"
            "    int count = 1;\n"
            "    auto l = [count]() { return count; };\n"
            "    (void)l;\n"
            "}\n"
        )
        assert _diags(code, tmp_path) == []


class TestMixedAccessSpecifiers:
    """Only members under a private/protected section are flagged."""

    def test_only_restricted_members_flagged(self, tmp_path: Path) -> None:
        """Test only restricted members flagged."""
        code = (
            "class C {\n"
            "public:\n"
            "    int pub;\n"
            "private:\n"
            "    int priv;\n"
            "protected:\n"
            "    int prot;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 2
        assert any("priv" in d for d in diags)
        assert any("prot" in d for d in diags)


class TestEnforceMemberLeadingUnderscoreCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceMemberLeadingUnderscore().id == "memberLeadingUnderscore"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = "class C {\nprivate:\n    int _count;\nprotected:\n    int _flag;\n};\n"
        assert _diags(code, tmp_path) == []
