"""Line-based rule flagging forbidden spellings, like a reverse dictionary.

Configured via ``[cpp.forbidden_spellings]`` as ``word = "replacement"``
pairs. Matching is a plain, case-sensitive, whole-word text search on every
line (comments and strings included), so it deliberately lives outside the
AST framework.
"""

from __future__ import annotations

import re

from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType


class CheckForbiddenSpellings(Rule):
    """Rule flagging whole-word occurrences of configured forbidden spellings."""

    def __init__(self, spellings: dict[str, str]) -> None:
        """Initialize the rule.

        Parameters
        ----------
        spellings: dict[str, str]
            Mapping of forbidden spelling to the spelling to use instead.

        """
        self.spellings = dict(spellings)
        # Longest first so overlapping alternatives prefer the longer spelling.
        alternatives = "|".join(
            re.escape(word) for word in sorted(self.spellings, key=len, reverse=True)
        )
        self._pattern = re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")
        super().__init__(
            name="CheckForbiddenSpellings",
            func=self._check_line,
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
            description="Do not use forbidden spellings.",
        )

    def _check_line(self, line: str) -> ResultType:
        found = list(dict.fromkeys(self._pattern.findall(line)))
        if not found:
            return ResultType(ResultTypeEnum.Ok)
        hints = ", ".join(f"'{w}' -> '{self.spellings[w]}'" for w in found)
        return ResultType(
            ResultTypeEnum.Error,
            f"Forbidden spelling in line {line.strip()!r}: use {hints}.",
        )
