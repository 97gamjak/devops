"""Line-based rule flagging forbidden spellings, like a reverse dictionary.

Configured via ``[cpp.forbidden_spellings]`` as ``word = "replacement"``
pairs. Matching is a plain, case-sensitive text search (whole words by
default, or also inside longer words per spelling) on every line (comments
and strings included), so it deliberately lives outside the AST framework.
"""

from __future__ import annotations

import re
import typing

from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType

if typing.TYPE_CHECKING:
    from devops.config.config_cpp import ForbiddenSpelling


class CheckForbiddenSpellings(Rule):
    """Rule flagging whole-word occurrences of configured forbidden spellings."""

    def __init__(self, spellings: dict[str, ForbiddenSpelling]) -> None:
        """Initialize the rule.

        Parameters
        ----------
        spellings: dict[str, ForbiddenSpelling]
            Mapping of forbidden spelling to its replacement and match mode.

        """
        self.spellings = dict(spellings)

        def alternatives(*, within_words: bool) -> str:
            words = [
                w for w, s in self.spellings.items() if s.within_words == within_words
            ]
            # Longest first so overlapping alternatives prefer the longer one.
            return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))

        parts = []
        if whole := alternatives(within_words=False):
            parts.append(rf"(?<!\w)(?:{whole})(?!\w)")
        if inner := alternatives(within_words=True):
            parts.append(inner)
        self._pattern = re.compile("|".join(parts))
        super().__init__(
            name="CheckForbiddenSpellings",
            func=self._check_line,
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
            description="Do not use forbidden spellings.",
        )

    def _check_line(self, line: str) -> ResultType:
        found = list(dict.fromkeys(m.group(0) for m in self._pattern.finditer(line)))
        if not found:
            return ResultType(ResultTypeEnum.Ok)
        hints = ", ".join(f"'{w}' -> '{self.spellings[w].replacement}'" for w in found)
        return ResultType(
            ResultTypeEnum.Error,
            f"Forbidden spelling in line {line.strip()!r}: use {hints}.",
        )
