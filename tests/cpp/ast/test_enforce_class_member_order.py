"""Tests for the EnforceClassMemberOrder AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.enforce_class_member_order import EnforceClassMemberOrder
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [EnforceClassMemberOrder()]
_ARGS = ["-std=c++17"]


def _diags(
    code: str, tmp_path: Path, checks: list[EnforceClassMemberOrder] | None = None
) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=checks or _CHECK)]


class TestCorrectOrderAllowed:
    """A class following the required section order is never flagged."""

    def test_full_correct_order_allowed(self, tmp_path: Path) -> None:
        """Test full correct order allowed."""
        code = (
            "class C {\n"
            "public:\n"
            "    int a;\n"
            "protected:\n"
            "    int b;\n"
            "private:\n"
            "    int c;\n"
            "public:\n"
            "    void f();\n"
            "protected:\n"
            "    void g();\n"
            "private:\n"
            "    void h();\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_sections_may_be_skipped(self, tmp_path: Path) -> None:
        """Test sections may be skipped."""
        code = (
            "class C {\n"
            "public:\n"
            "    int a;\n"
            "private:\n"
            "    int c;\n"
            "public:\n"
            "    void f();\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_default_public_struct_order_allowed(self, tmp_path: Path) -> None:
        """Test default public struct order allowed."""
        code = "struct S {\n    int a;\n    void f();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_only_variables_allowed(self, tmp_path: Path) -> None:
        """Test only variables allowed."""
        code = "class C {\npublic:\n    int a;\nprivate:\n    int b;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_only_functions_allowed(self, tmp_path: Path) -> None:
        """Test only functions allowed."""
        code = "class C {\npublic:\n    void f();\nprivate:\n    void g();\n};\n"
        assert _diags(code, tmp_path) == []

    def test_ignored_declarations_do_not_break_order(self, tmp_path: Path) -> None:
        """Nested types, usings, and friend decls don't affect ordering."""
        code = (
            "class C {\n"
            "public:\n"
            "    using Alias = int;\n"
            "    enum class E { A, B };\n"
            "    struct Nested { int x; };\n"
            "    int a;\n"
            "private:\n"
            "    int b;\n"
            "public:\n"
            "    void f();\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []


class TestOutOfOrderFlagged:
    """Sections declared before a section that must precede them are flagged."""

    def test_private_before_public_member_flagged(self, tmp_path: Path) -> None:
        """Test private before public member flagged."""
        code = "class C {\nprivate:\n    int b;\npublic:\n    int a;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member variable 'a'" in diags[0]
        assert "private member variable" in diags[0]

    def test_protected_before_public_member_flagged(self, tmp_path: Path) -> None:
        """Test protected before public member flagged."""
        code = "class C {\nprotected:\n    int b;\npublic:\n    int a;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member variable 'a'" in diags[0]

    def test_function_before_member_variable_flagged(self, tmp_path: Path) -> None:
        """Member functions declared before member variables are flagged."""
        code = "class C {\npublic:\n    void f();\n    int a;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member variable 'a'" in diags[0]
        assert "public member function" in diags[0]

    def test_public_function_before_private_member_flagged(
        self, tmp_path: Path
    ) -> None:
        """Test public function before private member flagged."""
        code = "class C {\npublic:\n    void f();\nprivate:\n    int a;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "private member variable 'a'" in diags[0]

    def test_private_function_before_public_function_flagged(
        self, tmp_path: Path
    ) -> None:
        """Test private function before public function flagged."""
        code = "class C {\nprivate:\n    void g();\npublic:\n    void f();\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member function 'f'" in diags[0]

    def test_multiple_violations_all_flagged(self, tmp_path: Path) -> None:
        """Test multiple violations all flagged."""
        code = (
            "class C {\n"
            "private:\n"
            "    int b;\n"
            "public:\n"
            "    int a;\n"
            "    void f();\n"
            "private:\n"
            "    void g();\n"
            "protected:\n"
            "    void h();\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 2
        assert any("'a'" in d for d in diags)
        assert any("'h'" in d for d in diags)


class TestStaticAndSpecialMembers:
    """Static data members and constructors/destructors participate in ordering."""

    def test_static_member_treated_as_variable(self, tmp_path: Path) -> None:
        """Test static member treated as variable."""
        code = "class C {\npublic:\n    void f();\n    static int count;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member variable 'count'" in diags[0]

    def test_constructor_treated_as_function(self, tmp_path: Path) -> None:
        """Test constructor treated as function."""
        code = "class C {\npublic:\n    C();\n    int a;\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "public member variable 'a'" in diags[0]


class TestExcludedMacros:
    """Declarations synthesized by a configured macro are ignored for ordering."""

    def _check(self, excluded_macros: list[str]) -> list[EnforceClassMemberOrder]:
        check = EnforceClassMemberOrder()
        check.configure({"excluded_macros": excluded_macros})
        return [check]

    def test_excluded_macro_member_ignored(self, tmp_path: Path) -> None:
        """A member synthesized by an excluded macro doesn't break ordering.

        The macro expands to a private field followed by a reset back to
        ``public:`` (mirroring how ``Q_OBJECT``-style macros bring their own
        access-specifier bookkeeping), which would otherwise make the
        public ``a`` that follows look like a public-after-private
        violation.
        """
        code = (
            "#define Q_OBJECT private: int _qObjectData; public:\n"
            "class C {\n"
            "public:\n"
            "    Q_OBJECT\n"
            "    int a;\n"
            "};\n"
        )
        assert _diags(code, tmp_path, self._check(["Q_OBJECT"])) == []

    def test_excluded_macro_member_still_flagged_when_not_configured(
        self, tmp_path: Path
    ) -> None:
        """The same file is flagged when the macro isn't excluded."""
        code = (
            "#define Q_OBJECT private: int _qObjectData; public:\n"
            "class C {\n"
            "public:\n"
            "    Q_OBJECT\n"
            "    int a;\n"
            "};\n"
        )
        assert _diags(code, tmp_path) != []

    def test_unrelated_macro_not_excluded(self, tmp_path: Path) -> None:
        """Only the configured macro name is excluded, not every macro."""
        code = (
            "#define OTHER_MACRO private: int _otherData; public:\n"
            "class C {\n"
            "public:\n"
            "    OTHER_MACRO\n"
            "    int a;\n"
            "};\n"
        )
        assert _diags(code, tmp_path, self._check(["Q_OBJECT"])) != []

    def test_invalid_excluded_macros_type_raises(self) -> None:
        """A non-list-of-strings ``excluded_macros`` raises ConfigError."""
        check = EnforceClassMemberOrder()
        with pytest.raises(ConfigError):
            check.configure({"excluded_macros": "Q_OBJECT"})

    def test_invalid_excluded_macros_element_type_raises(self) -> None:
        """A list containing a non-string element raises ConfigError."""
        check = EnforceClassMemberOrder()
        with pytest.raises(ConfigError):
            check.configure({"excluded_macros": [123]})


class TestEnforceClassMemberOrderCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceClassMemberOrder().id == "classMemberOrder"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = "class C {\npublic:\n    int a;\n    void f();\n};\n"
        assert _diags(code, tmp_path) == []
