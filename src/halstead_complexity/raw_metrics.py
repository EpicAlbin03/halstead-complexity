from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tree_sitter import Tree

from .config import LanguageDefinition, MultilineDelimiter
from .tree_utils import iter_nodes


@dataclass
class RawMetrics:
    loc: int = 0
    lloc: int = 0
    sloc: int = 0
    comments: int = 0
    multi: int = 0
    blank: int = 0
    single_comments: int = 0

    def update(self, other: "RawMetrics") -> None:
        self.loc += other.loc
        self.lloc += other.lloc
        self.sloc += other.sloc
        self.comments += other.comments
        self.multi += other.multi
        self.blank += other.blank
        self.single_comments += other.single_comments


def analyze_raw_metrics(
    source: str, tree: Tree, language: LanguageDefinition
) -> RawMetrics:
    lines = source.splitlines()
    loc = len(lines)
    blank = sum(1 for line in lines if not line.strip())

    multi, comments, single_comments = _count_comment_and_multiline_lines(
        lines, language
    )
    lloc = _count_lloc(tree, set(language.statement_node_types))
    sloc = max(0, loc - blank - multi - single_comments)

    return RawMetrics(
        loc=loc,
        lloc=lloc,
        sloc=sloc,
        comments=comments,
        multi=multi,
        blank=blank,
        single_comments=single_comments,
    )


def _count_comment_and_multiline_lines(
    lines: Sequence[str], language: LanguageDefinition
) -> tuple[int, int, int]:
    comment_markers = language.comment_markers
    multiline_delimiters = language.multiline_delimiters

    multi = 0
    comments = 0
    single_comments = 0

    active_delimiter: MultilineDelimiter | None = None
    for line in lines:
        stripped = line.strip()

        if active_delimiter is not None:
            multi += 1
            if active_delimiter.end and active_delimiter.end in stripped:
                if stripped.count(active_delimiter.end) >= stripped.count(
                    active_delimiter.start
                ):
                    active_delimiter = None
            continue

        if not stripped:
            continue

        started_multiline = False
        for delimiter in multiline_delimiters:
            if stripped.startswith(delimiter.start):
                started_multiline = True
                multi += 1
                if delimiter.end and not stripped.endswith(delimiter.end):
                    active_delimiter = delimiter
                elif stripped.count(delimiter.start) > stripped.count(delimiter.end):
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
    count = 0
    for node in iter_nodes(tree):
        if node.type in statement_node_types:
            count += 1
    return count
