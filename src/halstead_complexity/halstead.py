from __future__ import annotations

import math
from dataclasses import dataclass, field

from tree_sitter import Tree

from .config import LanguageDefinition
from .tree_utils import iter_leaf_nodes


@dataclass
class HalsteadCounters:
    distinct_operators: set[str] = field(default_factory=lambda: set[str]())
    distinct_operands: set[str] = field(default_factory=lambda: set[str]())
    total_operators: int = 0
    total_operands: int = 0

    def update(self, other: "HalsteadCounters") -> None:
        self.distinct_operators.update(other.distinct_operators)
        self.distinct_operands.update(other.distinct_operands)
        self.total_operators += other.total_operators
        self.total_operands += other.total_operands

    def to_metrics(self) -> "HalsteadMetrics":
        return HalsteadMetrics.from_counters(self)


@dataclass
class HalsteadMetrics:
    distinct_operators: int
    distinct_operands: int
    total_operators: int
    total_operands: int
    vocabulary: int
    length: int
    calculated_length: float
    volume: float
    difficulty: float
    effort: float
    time_required: float
    delivered_bugs: float

    @classmethod
    def from_counters(cls, counters: HalsteadCounters) -> "HalsteadMetrics":
        n1 = len(counters.distinct_operators)
        n2 = len(counters.distinct_operands)
        N1 = counters.total_operators
        N2 = counters.total_operands
        vocabulary = n1 + n2
        length = N1 + N2

        calc_length = 0.0
        if n1:
            calc_length += n1 * math.log(n1, 2)
        if n2:
            calc_length += n2 * math.log(n2, 2)

        volume = length * math.log(vocabulary, 2) if vocabulary else 0.0
        difficulty = (n1 * N2) / (2.0 * n2) if n2 else 0.0
        effort = difficulty * volume
        time_required = effort / 18.0
        delivered_bugs = volume / 3000.0

        return cls(
            distinct_operators=n1,
            distinct_operands=n2,
            total_operators=N1,
            total_operands=N2,
            vocabulary=vocabulary,
            length=length,
            calculated_length=calc_length,
            volume=volume,
            difficulty=difficulty,
            effort=effort,
            time_required=time_required,
            delivered_bugs=delivered_bugs,
        )


class HalsteadVisitor:
    """Collect Halstead metrics from a parsed syntax tree."""

    def __init__(self, language: LanguageDefinition):
        self.language = language
        self.operators = language.operators
        self.operand_node_types = set(language.operand_node_types)
        self.count_paired_delimiters = language.paired_delimiters_single_operator
        self._paired_open = {
            "(": "()",
            "[": "[]",
            "{": "{}",
        }
        self._paired_close = {
            ")",
            "]",
            "}",
        }

    def visit(self, tree: Tree, source: bytes) -> HalsteadCounters:
        counters = HalsteadCounters()
        for node in iter_leaf_nodes(tree):
            start_byte = node.start_byte
            end_byte = node.end_byte
            if end_byte <= start_byte:
                continue

            raw_text = source[start_byte:end_byte]
            text = raw_text.decode("utf-8", errors="ignore").strip()
            if not text:
                continue

            if self.count_paired_delimiters:
                if text in self._paired_open:
                    paired_name = self._paired_open[text]
                    counters.total_operators += 1
                    counters.distinct_operators.add(paired_name)
                    continue
                if text in self._paired_close:
                    continue

            if text in self.operators:
                counters.total_operators += 1
                counters.distinct_operators.add(text)
                continue

            if node.type in self.operand_node_types:
                counters.total_operands += 1
                counters.distinct_operands.add(text)

        return counters
