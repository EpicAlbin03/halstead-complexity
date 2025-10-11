from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence

from tree_sitter import Tree

from .tree_utils import iter_nodes


@dataclass
class RawMetrics:
    """Container for raw code metrics.

    Attributes:
        loc: Total number of lines of code
        lloc: Number of logical lines of code (each contains exactly one statement)
        sloc: Number of source lines of code
        comments: Number of comment lines
        multi: Number of lines representing multi-line delimiters
        blanks: Number of blank or whitespace-only lines
        single_comments: Number of single-line comment lines
    """

    loc: int = 0
    lloc: int = 0
    sloc: int = 0
    comments: int = 0
    multi: int = 0
    blanks: int = 0
    single_comments: int = 0

    def __add__(self, other: RawMetrics) -> RawMetrics:
        """Add two RawMetrics together."""
        return RawMetrics(
            loc=self.loc + other.loc,
            lloc=self.lloc + other.lloc,
            sloc=self.sloc + other.sloc,
            comments=self.comments + other.comments,
            multi=self.multi + other.multi,
            blanks=self.blanks + other.blanks,
            single_comments=self.single_comments + other.single_comments,
        )

    def update(self, other: RawMetrics) -> None:
        """Update this RawMetrics by adding another."""
        self.loc += other.loc
        self.lloc += other.lloc
        self.sloc += other.sloc
        self.comments += other.comments
        self.multi += other.multi
        self.blanks += other.blanks
        self.single_comments += other.single_comments


def analyze_raw_metrics(
    source: str, tree: Tree, lang_config: Dict[str, Any]
) -> RawMetrics:
    """Analyze raw metrics from source code.

    Args:
        source: The source code as a string
        tree: Parsed tree-sitter Tree
        lang_config: Language config dictionary

    Returns:
        RawMetrics object with collected metrics
    """
    lines = source.splitlines()
    loc = len(lines)
    blanks = sum(1 for line in lines if not line.strip())

    multi, comments, single_comments = _count_comment_and_multiline_lines(
        lines, lang_config
    )
    lloc = _count_lloc(tree, set(lang_config.get("statement_types", [])))
    sloc = max(0, loc - blanks - multi - single_comments)

    return RawMetrics(
        loc=loc,
        lloc=lloc,
        sloc=sloc,
        comments=comments,
        multi=multi,
        blanks=blanks,
        single_comments=single_comments,
    )


def _count_comment_and_multiline_lines(
    lines: Sequence[str], lang_config: Dict[str, Any]
) -> tuple[int, int, int]:
    """Count comment and multi-line delimiter lines.

    Args:
        lines: Source code lines
        lang_config: Language config dictionary

    Returns:
        Tuple of (multi_line_count, total_comment_count, single_comment_count)
    """
    comment_markers = lang_config.get("comment", [])
    multiline_delimiters = lang_config.get("multi_line_delimiters", [])

    multi = 0
    comments = 0
    single_comments = 0

    active_delimiter: Dict[str, Any] | None = None
    for line in lines:
        stripped = line.strip()

        if active_delimiter is not None:
            multi += 1
            if active_delimiter.get("end") and active_delimiter["end"] in stripped:
                if stripped.count(active_delimiter["end"]) >= stripped.count(
                    active_delimiter["start"]
                ):
                    active_delimiter = None
            continue

        if not stripped:
            continue

        started_multiline = False
        for delimiter in multiline_delimiters:
            if stripped.startswith(delimiter["start"]):
                started_multiline = True
                multi += 1
                if delimiter.get("end") and not stripped.endswith(delimiter["end"]):
                    active_delimiter = delimiter
                elif delimiter.get("end") and stripped.count(
                    delimiter["start"]
                ) > stripped.count(delimiter["end"]):
                    active_delimiter = delimiter
                break

        if started_multiline:
            continue

        is_single = any(stripped.startswith(marker) for marker in comment_markers)
        if is_single:
            comments += 1
            single_comments += 1
            continue

        if any(marker in stripped for marker in comment_markers):
            comments += 1

    return multi, comments, single_comments


def _count_lloc(tree: Tree, statement_node_types: set[str]) -> int:
    """Count logical lines of code (statements).

    Args:
        tree: Parsed tree-sitter Tree
        statement_node_types: Set of node types that represent statements

    Returns:
        Number of logical lines (statements)
    """
    count = 0
    for node in iter_nodes(tree):
        if node.type in statement_node_types:
            count += 1
    return count
