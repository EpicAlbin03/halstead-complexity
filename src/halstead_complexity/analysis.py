from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, Optional

from tree_sitter import Language, Parser

from .config import AppConfig, LanguageDefinition
from .halstead import HalsteadCounters, HalsteadMetrics, HalsteadVisitor
from .raw_metrics import RawMetrics, analyze_raw_metrics


@dataclass
class FileAnalysis:
    path: Path
    language: str
    halstead: HalsteadMetrics
    raw: RawMetrics


@dataclass
class AnalysisSummary:
    files: list[FileAnalysis]
    halstead: HalsteadMetrics
    raw: RawMetrics


@dataclass
class LanguageRuntime:
    definition: LanguageDefinition
    parser: Parser

    @classmethod
    def create(cls, definition: LanguageDefinition) -> "LanguageRuntime":
        module_name = (
            definition.parser_module
            or f"tree_sitter_{definition.name.replace('-', '_')}"
        )
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                f"Unable to import parser module '{module_name}' for language '{definition.name}'."
            ) from error
        language_ptr = module.language()
        language = Language(language_ptr)  # type: ignore[arg-type]
        parser = Parser()
        parser.language = language
        return cls(definition=definition, parser=parser)


class Analyzer:
    def __init__(self, config: AppConfig):
        self.config = config
        self._runtimes: Dict[str, LanguageRuntime] = {}

    def analyze(
        self, target: Path, language_name: Optional[str] = None
    ) -> AnalysisSummary:
        files = list(self._collect_files(target, language_name))
        files.sort(key=lambda item: str(item[0]))
        if not files:
            raise ValueError(f"No source files found under {target!s}")

        aggregate_counters = HalsteadCounters()
        aggregate_raw = RawMetrics()
        results: list[FileAnalysis] = []

        for file_path, definition in files:
            runtime = self._runtime_for_language(definition)
            source_bytes = file_path.read_bytes()
            source_text = source_bytes.decode("utf-8", errors="ignore")
            tree = runtime.parser.parse(source_bytes)

            counters = HalsteadVisitor(definition).visit(tree, source_bytes)
            aggregate_counters.update(counters)

            halstead_metrics = counters.to_metrics()
            raw_metrics = analyze_raw_metrics(source_text, tree, definition)
            aggregate_raw.update(raw_metrics)

            results.append(
                FileAnalysis(
                    path=file_path,
                    language=definition.name,
                    halstead=halstead_metrics,
                    raw=raw_metrics,
                )
            )

        return AnalysisSummary(
            files=results,
            halstead=aggregate_counters.to_metrics(),
            raw=aggregate_raw,
        )

    def _runtime_for_language(self, definition: LanguageDefinition) -> LanguageRuntime:
        runtime = self._runtimes.get(definition.name)
        if runtime is None:
            runtime = LanguageRuntime.create(definition)
            self._runtimes[definition.name] = runtime
        return runtime

    def _collect_files(
        self, target: Path, language_name: Optional[str]
    ) -> Iterator[tuple[Path, LanguageDefinition]]:
        if target.is_file():
            definition = self._resolve_language(target, language_name)
            if definition:
                yield target, definition
            return

        if not target.exists():
            raise FileNotFoundError(f"Path {target!s} does not exist")

        excluded = self.config.excluded_names()
        for root, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in excluded]
            for filename in filenames:
                if filename in excluded:
                    continue
                path = Path(root, filename)
                if not path.is_file():
                    continue
                definition = self._resolve_language(path, language_name)
                if definition is not None:
                    yield path, definition

    def _resolve_language(
        self, path: Path, language_name: Optional[str]
    ) -> Optional[LanguageDefinition]:
        if language_name:
            return self.config.language(language_name)

        definition = self.config.language_for_extension(path.suffix.lower())
        if definition is not None:
            return definition

        default = self.config.default_language
        if default is not None:
            return self.config.language(default)
        return None


def _format_float(value: float) -> str:
    formatted = f"{value:.3f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def _format_halstead(metrics: HalsteadMetrics, indent: int) -> list[str]:
    prefix = " " * indent
    return [
        f"{prefix}Distinct operators: {metrics.distinct_operators}",
        f"{prefix}Distinct operands: {metrics.distinct_operands}",
        f"{prefix}Total operators: {metrics.total_operators}",
        f"{prefix}Total operands: {metrics.total_operands}",
        f"{prefix}Vocabulary: {metrics.vocabulary}",
        f"{prefix}Length: {metrics.length}",
        f"{prefix}Calculated length: {_format_float(metrics.calculated_length)}",
        f"{prefix}Volume: {_format_float(metrics.volume)}",
        f"{prefix}Difficulty: {_format_float(metrics.difficulty)}",
        f"{prefix}Effort: {_format_float(metrics.effort)}",
        f"{prefix}Time required (sec): {_format_float(metrics.time_required)}",
        f"{prefix}Delivered bugs: {_format_float(metrics.delivered_bugs)}",
    ]


def _format_raw(raw: RawMetrics, indent: int) -> list[str]:
    prefix = " " * indent
    return [
        f"{prefix}LOC: {raw.loc}",
        f"{prefix}LLOC: {raw.lloc}",
        f"{prefix}SLOC: {raw.sloc}",
        f"{prefix}Comments: {raw.comments}",
        f"{prefix}Multi: {raw.multi}",
        f"{prefix}Blanks: {raw.blank}",
        f"{prefix}Single comments: {raw.single_comments}",
    ]


def format_summary(summary: AnalysisSummary) -> str:
    lines: list[str] = []
    lines.append("Summary")
    lines.append("=====")
    lines.append("Halstead metrics")
    lines.extend(_format_halstead(summary.halstead, indent=2))
    lines.append("Raw metrics")
    lines.extend(_format_raw(summary.raw, indent=2))

    if len(summary.files) <= 1:
        return "\n".join(lines)

    lines.append("")
    lines.append("Files")
    lines.append("-----")
    for file in summary.files:
        lines.append(f"{file.path} [{file.language}]")
        lines.append("    Halstead:")
        lines.extend(_format_halstead(file.halstead, indent=8))
        lines.append("    Raw:")
        lines.extend(_format_raw(file.raw, indent=8))
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
