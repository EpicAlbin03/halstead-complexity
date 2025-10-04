"""Module for collecting Halstead complexity metrics."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from tree_sitter import Tree

from ..config import ConfZConfig, LanguageConfig
from .tree_utils import iter_leaf_nodes


@dataclass
class HalsteadCounters:
    """Mutable counters for collecting Halstead metrics during traversal.

    Attributes:
        operators: Set of unique operators found in the code
        operands: Set of unique operands found in the code
        operator_count: Total number of operator occurrences
        operand_count: Total number of operand occurrences
        operator_counts: Dictionary mapping each operator to its count
        operand_counts: Dictionary mapping each operand to its count
    """

    operators: set[str] = field(default_factory=lambda: set[str]())
    operands: set[str] = field(default_factory=lambda: set[str]())
    operator_count: int = 0
    operand_count: int = 0
    operator_counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    operand_counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())


@dataclass(frozen=True)
class HalsteadMetrics:
    """Immutable Halstead complexity metrics.

    Attributes:
        n1: Number of distinct operators (η1)
        n2: Number of distinct operands (η2)
        N1: Total number of operators
        N2: Total number of operands
        vocabulary: Program vocabulary (η = η1 + η2)
        length: Program length (N = N1 + N2)
        volume: Program volume (V = N * log2(η))
        difficulty: Program difficulty (D = (η1/2) * (N2/η2))
        effort: Programming effort (E = D * V)
        time: Time required to program (T = E / 18 seconds)
        bugs: Estimated number of bugs (B = V / 3000)
        operators: Set of distinct operators (for token display)
        operands: Set of distinct operands (for token display)
        operator_counts: Dictionary mapping each operator to its count
        operand_counts: Dictionary mapping each operand to its count
    """

    n1: int
    n2: int
    N1: int
    N2: int
    vocabulary: int
    length: int
    volume: float
    difficulty: float
    effort: float
    time: float
    bugs: float
    operators: frozenset[str] = field(default_factory=lambda: frozenset())
    operands: frozenset[str] = field(default_factory=lambda: frozenset())
    operator_counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    operand_counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())

    @classmethod
    def from_counters(cls, counters: HalsteadCounters) -> HalsteadMetrics:
        """Create HalsteadMetrics from HalsteadCounters.

        Args:
            counters: The counters collected during traversal

        Returns:
            Computed Halstead metrics
        """
        n1 = len(counters.operators)
        n2 = len(counters.operands)
        N1 = counters.operator_count
        N2 = counters.operand_count

        vocabulary = n1 + n2
        length = N1 + N2

        # Avoid division by zero and log(0)
        volume = length * math.log2(vocabulary) if vocabulary > 0 else 0.0
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 and n1 > 0 else 0.0
        effort = difficulty * volume
        time = effort / 18 if effort > 0 else 0.0
        bugs = volume / 3000 if volume > 0 else 0.0

        return cls(
            n1=n1,
            n2=n2,
            N1=N1,
            N2=N2,
            vocabulary=vocabulary,
            length=length,
            volume=volume,
            difficulty=difficulty,
            effort=effort,
            time=time,
            bugs=bugs,
            operators=frozenset(counters.operators),
            operands=frozenset(counters.operands),
            operator_counts=dict(counters.operator_counts),
            operand_counts=dict(counters.operand_counts),
        )


def analyze_halstead_metrics(
    source: str, tree: Tree, lang_config: LanguageConfig, config: ConfZConfig
) -> HalsteadMetrics:
    """Analyze Halstead complexity metrics from source code.

    Args:
        source: The source code as a string
        tree: Parsed tree-sitter Tree
        lang_config: Language configuration
        config: Full configuration object

    Returns:
        HalsteadMetrics with computed complexity values
    """
    counters = HalsteadCounters()

    # Build lookup sets for fast checking
    keywords_set = set(lang_config.keywords)
    symbols_set = set(lang_config.symbols)
    multi_word_ops_set = set(lang_config.multi_word_operators)
    all_operators = keywords_set | symbols_set | multi_word_ops_set
    operand_types_set = set(lang_config.operand_types)

    # Track which template strings we've already counted (to avoid double-counting)
    counted_template_strings = set[int]()

    # Traverse leaf nodes and classify
    for node in iter_leaf_nodes(tree):
        node_text = (
            node.text.decode("utf-8")
            if isinstance(node.text, bytes)
            else str(node.text)
        )

        if not node_text or not node_text.strip():
            continue

        # Check if we're inside a template string and should count as single operand
        if config.template_literal_single_operand:
            # Check if this node is inside a string/template_string
            current = node.parent
            template_parent = None
            while current:
                if current.type in ("string", "template_string"):
                    template_parent = current
                    break
                current = current.parent

            # If we found a template parent, handle it specially
            if template_parent:
                parent_id = id(template_parent)
                # Only count the template string once
                if parent_id not in counted_template_strings:
                    counted_template_strings.add(parent_id)
                    full_text = (
                        template_parent.text.decode("utf-8")
                        if isinstance(template_parent.text, bytes)
                        else str(template_parent.text)
                    )
                    counters.operands.add(full_text)
                    counters.operand_count += 1
                    counters.operand_counts[full_text] = (
                        counters.operand_counts.get(full_text, 0) + 1
                    )
                # Skip this node since it's part of a template string we already counted
                continue

        # Check if it's an operator
        if node_text in all_operators:
            counters.operators.add(node_text)
            counters.operator_count += 1
            counters.operator_counts[node_text] = (
                counters.operator_counts.get(node_text, 0) + 1
            )
        # Check if it's an operand by node type
        elif node.type in operand_types_set:
            counters.operands.add(node_text)
            counters.operand_count += 1
            counters.operand_counts[node_text] = (
                counters.operand_counts.get(node_text, 0) + 1
            )

    return HalsteadMetrics.from_counters(counters)
