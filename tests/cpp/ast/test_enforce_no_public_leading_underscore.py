"""Tests for the EnforceNoPublicLeadingUnderscore AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.enforce_no_public_leading_underscore import (
    EnforceNoPublicLeadingUnderscore,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [EnforceNoPublicLeadingUnderscore()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestPublicMembersFlagged:
    """Public data members starting with an underscore are flagged."""

    def test_public_field_flagged(self, tmp_path: Path) -> None:
        """Test public field flagged."""
        code = "class C {\npublic:\n    int _count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member variable '_count'" in diags[0]
        assert "'count'" in diags[0]

    def test_public_static_field_flagged(self, tmp_path: Path) -> None:
        """Test public static field flagged."""
        code = "class C {\npublic:\n    static int _count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_default_public_struct_field_flagged(self, tmp_path: Path) -> None:
        """Test default public struct field flagged."""
        code = "struct S {\n    int _count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestPublicMethodsFlagged:
    """Public member functions starting with an underscore are flagged."""

    def test_public_method_flagged(self, tmp_path: Path) -> None:
        """Test public method flagged."""
        code = "class C {\npublic:\n    void _compute();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member function '_compute'" in diags[0]
        assert "'compute'" in diags[0]

    def test_public_static_method_flagged(self, tmp_path: Path) -> None:
        """Test public static method flagged."""
        code = "class C {\npublic:\n    static void _compute();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_public_template_method_flagged(self, tmp_path: Path) -> None:
        """Test public template method flagged."""
        code = "class C {\npublic:\n    template<typename T> void _compute(T);\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_default_public_struct_method_flagged(self, tmp_path: Path) -> None:
        """Test default public struct method flagged."""
        code = "struct S {\n    void _compute();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestMembersAllowed:
    """Private/protected members and already-clean names are never flagged."""

    def test_private_field_allowed(self, tmp_path: Path) -> None:
        """Test private field allowed."""
        code = "class C {\nprivate:\n    int _count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_protected_field_allowed(self, tmp_path: Path) -> None:
        """Test protected field allowed."""
        code = "class C {\nprotected:\n    int _count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_public_field_without_underscore_allowed(self, tmp_path: Path) -> None:
        """Test public field without underscore allowed."""
        code = "class C {\npublic:\n    int count;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_local_and_global_variables_allowed(self, tmp_path: Path) -> None:
        """Test local and global variables allowed."""
        code = "int _global;\nvoid f() {\n    int _local;\n    (void)_local;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_macro_synthesized_member_allowed(self, tmp_path: Path) -> None:
        """A member declared entirely inside a macro body is not flagged."""
        code = (
            "#define DECLARE_FIXTURE(name) \\\n"
            "    class name { \\\n"
            "    public: \\\n"
            "        static int _test_info; \\\n"
            "    };\n"
            "DECLARE_FIXTURE(Foo)\n"
        )
        assert _diags(code, tmp_path) == []


class TestMethodsAllowed:
    """Private/protected methods and language-fixed names are never flagged."""

    def test_private_method_allowed(self, tmp_path: Path) -> None:
        """Test private method allowed."""
        code = "class C {\nprivate:\n    void _compute();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_protected_method_allowed(self, tmp_path: Path) -> None:
        """Test protected method allowed."""
        code = "class C {\nprotected:\n    void _compute();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_public_method_without_underscore_allowed(self, tmp_path: Path) -> None:
        """Test public method without underscore allowed."""
        code = "class C {\npublic:\n    void compute();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_constructor_allowed(self, tmp_path: Path) -> None:
        """Test constructor allowed."""
        code = "class C {\npublic:\n    C();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_destructor_allowed(self, tmp_path: Path) -> None:
        """Test destructor allowed."""
        code = "class C {\npublic:\n    ~C();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_operator_overload_allowed(self, tmp_path: Path) -> None:
        """Test operator overload allowed."""
        code = (
            "class C {\npublic:\n"
            "    void operator()();\n"
            "    bool operator==(const C&) const;\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_conversion_operator_allowed(self, tmp_path: Path) -> None:
        """Test conversion operator allowed."""
        code = "class C {\npublic:\n    operator int() const;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_overriding_method_allowed(self, tmp_path: Path) -> None:
        """Only the base declaration is flagged; the override itself is not."""
        code = (
            "class Base {\npublic:\n"
            "    virtual void _doThing();\n"
            "    virtual ~Base() = default;\n"
            "};\n"
            "class C : public Base {\npublic:\n"
            "    void _doThing() override;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "_doThing" in diags[0]

    def test_free_function_allowed(self, tmp_path: Path) -> None:
        """Test free function allowed."""
        code = "void _compute();\n"
        assert _diags(code, tmp_path) == []

    def test_macro_synthesized_method_allowed(self, tmp_path: Path) -> None:
        """A method declared entirely inside a macro body is not flagged."""
        code = (
            "#define DECLARE_FIXTURE(name) \\\n"
            "    class name { \\\n"
            "    public: \\\n"
            "        void _testBody(); \\\n"
            "    };\n"
            "DECLARE_FIXTURE(Foo)\n"
        )
        assert _diags(code, tmp_path) == []


class TestMixedAccessSpecifiers:
    """Only members/methods under a public section are flagged."""

    def test_only_public_members_flagged(self, tmp_path: Path) -> None:
        """Test only public members flagged."""
        code = (
            "class C {\n"
            "public:\n"
            "    int _pub;\n"
            "private:\n"
            "    int _priv;\n"
            "protected:\n"
            "    int _prot;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "_pub" in diags[0]

    def test_only_public_methods_flagged(self, tmp_path: Path) -> None:
        """Test only public methods flagged."""
        code = (
            "class C {\n"
            "public:\n"
            "    void _pub();\n"
            "private:\n"
            "    void _priv();\n"
            "protected:\n"
            "    void _prot();\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "_pub" in diags[0]


class TestEnforceNoPublicLeadingUnderscoreCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceNoPublicLeadingUnderscore().id == "noPublicLeadingUnderscore"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = "class C {\npublic:\n    int count;\n    void compute();\n};\n"
        assert _diags(code, tmp_path) == []
