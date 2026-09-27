"""Tests for the EnforceMemberFunctionLeadingUnderscore AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.enforce_member_function_leading_underscore import (
    EnforceMemberFunctionLeadingUnderscore,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [EnforceMemberFunctionLeadingUnderscore()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestPrivateMethodsFlagged:
    """Private member functions without a leading underscore are flagged."""

    def test_private_method_flagged(self, tmp_path: Path) -> None:
        """Test private method flagged."""
        code = "class C {\nprivate:\n    void compute();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "private member function 'compute'" in diags[0]
        assert "'_compute'" in diags[0]

    def test_private_static_method_flagged(self, tmp_path: Path) -> None:
        """Test private static method flagged."""
        code = "class C {\nprivate:\n    static void compute();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_private_template_method_flagged(self, tmp_path: Path) -> None:
        """Test private template method flagged."""
        code = "class C {\nprivate:\n    template<typename T> void compute(T);\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "compute" in diags[0]

    def test_private_struct_method_flagged(self, tmp_path: Path) -> None:
        """Test private struct method flagged."""
        code = "struct S {\nprivate:\n    void compute();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestProtectedMethodsFlagged:
    """Protected member functions without a leading underscore are flagged."""

    def test_protected_method_flagged(self, tmp_path: Path) -> None:
        """Test protected method flagged."""
        code = "class C {\nprotected:\n    void hook();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "protected member function 'hook'" in diags[0]


class TestMethodsAllowed:
    """Public methods, prefixed methods, and language-fixed names are allowed."""

    def test_public_method_allowed(self, tmp_path: Path) -> None:
        """Test public method allowed."""
        code = "class C {\npublic:\n    void compute();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_default_public_struct_method_allowed(self, tmp_path: Path) -> None:
        """Test default public struct method allowed."""
        code = "struct S {\n    void compute();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_private_method_with_underscore_allowed(self, tmp_path: Path) -> None:
        """Test private method with underscore allowed."""
        code = "class C {\nprivate:\n    void _compute();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_constructor_allowed(self, tmp_path: Path) -> None:
        """Test constructor allowed."""
        code = "class C {\nprivate:\n    C();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_destructor_allowed(self, tmp_path: Path) -> None:
        """Test destructor allowed."""
        code = "class C {\nprivate:\n    ~C();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_copy_constructor_and_assignment_allowed(self, tmp_path: Path) -> None:
        """Test copy constructor and assignment allowed."""
        code = (
            "class C {\nprivate:\n    C(const C&);\n    C& operator=(const C&);\n};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_operator_overload_allowed(self, tmp_path: Path) -> None:
        """Test operator overload allowed."""
        code = (
            "class C {\nprivate:\n"
            "    void operator()();\n"
            "    bool operator==(const C&) const;\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_conversion_operator_allowed(self, tmp_path: Path) -> None:
        """Test conversion operator allowed."""
        code = "class C {\nprivate:\n    operator int() const;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_overriding_method_allowed(self, tmp_path: Path) -> None:
        """Test overriding method allowed."""
        code = (
            "class Base {\npublic:\n"
            "    virtual void doThing();\n"
            "    virtual ~Base() = default;\n"
            "};\n"
            "class C : public Base {\nprivate:\n"
            "    void doThing() override;\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_free_function_allowed(self, tmp_path: Path) -> None:
        """Test free function allowed."""
        code = "void compute();\n"
        assert _diags(code, tmp_path) == []

    def test_macro_synthesized_method_allowed(self, tmp_path: Path) -> None:
        """A method declared entirely inside a macro body is not flagged."""
        code = (
            "#define DECLARE_FIXTURE(name) \\\n"
            "    class name { \\\n"
            "    private: \\\n"
            "        void testBody(); \\\n"
            "    };\n"
            "DECLARE_FIXTURE(Foo)\n"
        )
        assert _diags(code, tmp_path) == []


class TestMixedAccessSpecifiers:
    """Only methods under a private/protected section are flagged."""

    def test_only_restricted_methods_flagged(self, tmp_path: Path) -> None:
        """Test only restricted methods flagged."""
        code = (
            "class C {\n"
            "public:\n"
            "    void pub();\n"
            "private:\n"
            "    void priv();\n"
            "protected:\n"
            "    void prot();\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 2
        assert any("priv" in d for d in diags)
        assert any("prot" in d for d in diags)


class TestEnforceMemberFunctionLeadingUnderscoreCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert (
            EnforceMemberFunctionLeadingUnderscore().id
            == "memberFunctionLeadingUnderscore"
        )

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = (
            "class C {\nprivate:\n    void _compute();\nprotected:\n"
            "    void _hook();\n};\n"
        )
        assert _diags(code, tmp_path) == []
