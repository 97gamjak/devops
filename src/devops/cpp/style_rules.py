"""C++ rules for mstd devops."""

from devops.rules import Rule, RuleInputType, RuleType
from devops.utils import check_key_sequence_ordered


class CheckKeySeqOrder(Rule):
    """Rule to check that a specific key sequence appears only in a given order."""

    def __init__(self, key_sequence: str) -> None:
        """Initialize CheckKeySeqOrder with the given key sequence.

        Parameters
        ----------
        key_sequence: str
            The key sequence to check.

        """
        super().__init__(
            name=key_sequence,
            func=lambda line: check_key_sequence_ordered(
                key_sequence,
                line
            ),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
            description=f'Use "{key_sequence}" only in this given order.'
        )


rule01 = CheckKeySeqOrder("static inline constexpr")

cpp_style_rules = [rule01]
