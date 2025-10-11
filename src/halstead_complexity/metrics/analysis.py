from __future__ import annotations

import csv
import importlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.progress import track
from rich.table import Table
from tree_sitter import Language, Parser

from ..config import settings
from .halstead import HalsteadCounters, HalsteadMetrics, analyze_halstead_metrics
from .raw_metrics import RawMetrics, analyze_raw_metrics

# Cache for dynamically loaded Language objects
language_cache: Dict[str, Optional[Language]] = {}


class LanguageNotSupportedError(Exception):
    """Raised when a language grammar module is not installed."""

    def __init__(self, language_name: str):
        self.language_name = language_name
        self.message = (
            f"Language '{language_name}' is not supported. "
            f"Please install the tree-sitter grammar: "
            f"pip install tree-sitter-{language_name}"
        )
        super().__init__(self.message)


@dataclass
class FileAnalysis:
    """Container for analysis results of a single file.

    Attributes:
        file_path: Path to the analyzed file
        raw_metrics: Raw code metrics
        halstead_metrics: Halstead complexity metrics
    """

    file_path: Path
    raw_metrics: RawMetrics
    halstead_metrics: HalsteadMetrics


@dataclass
class DirectoryAnalysis:
    """Container for analysis results of a directory.

    Attributes:
        directory_path: Path to the analyzed directory
        file_analyses: Dictionary mapping file paths to their analyses
        total_raw_metrics: Aggregated raw metrics across all files
        total_halstead_metrics: Aggregated Halstead metrics across all files
    """

    directory_path: Path
    file_analyses: Dict[Path, FileAnalysis]
    total_raw_metrics: RawMetrics
    total_halstead_metrics: Optional[HalsteadMetrics] = None


def get_language_parser(language_name: str) -> Parser:
    """Get a tree-sitter parser for the given language.

    Args:
        language_name: Name of the programming language

    Returns:
        Configured Parser object

    Raises:
        LanguageNotSupportedError: If the language grammar module is not installed
    """
    # Check if language is already cached
    if language_name in language_cache:
        cached_language = language_cache[language_name]
        if cached_language is None:
            raise LanguageNotSupportedError(language_name)
        parser = Parser(cached_language)
        return parser

    # Try to dynamically import the language module
    language: Optional[Language] = None
    module_name = f"tree_sitter_{language_name}"

    try:
        # Dynamically import the tree-sitter language module
        language_module = importlib.import_module(module_name)

        # Get the language function (usually named 'language')
        if hasattr(language_module, "language"):
            language = Language(language_module.language())  # type: ignore
        else:
            # Some modules might have a different naming convention
            # Try to find a callable that returns the language
            for attr_name in dir(language_module):
                if not attr_name.startswith("_"):
                    attr = getattr(language_module, attr_name)
                    if callable(attr):
                        try:
                            language = Language(attr())
                            break
                        except Exception:
                            continue
    except ImportError:
        language_cache[language_name] = None
        raise LanguageNotSupportedError(language_name)
    except Exception as e:
        language_cache[language_name] = None
        raise LanguageNotSupportedError(language_name) from e

    language_cache[language_name] = language

    if language is None:
        raise LanguageNotSupportedError(language_name)

    parser = Parser(language)
    return parser


def _detect_language_from_extension(
    file_path: Path, config_settings: Dict[str, Any]
) -> Optional[tuple[str, Dict[str, Any]]]:
    """Detect the programming language from file extension.

    Args:
        file_path: Path to the file
        config_settings: Config dictionary

    Returns:
        Tuple of (language_name, language_config_dict) or None if not found
    """
    extension = file_path.suffix

    languages = config_settings.get("languages", {})
    for lang_name, lang_config in languages.items():
        if extension in lang_config.get("extensions", []):
            return (lang_name, lang_config)

    return None


def analyze_file(
    file_path: Path, config_settings: Optional[Dict[str, Any]] = None
) -> Optional[FileAnalysis]:
    """Analyze a single source code file.

    Args:
        file_path: Path to the file to analyze
        config_settings: Config dictionary (uses default if None)

    Returns:
        FileAnalysis object with results, or None if file cannot be analyzed

    Raises:
        LanguageNotSupportedError: If the language grammar module is not installed
    """
    if config_settings is None:
        config_settings = settings.get_all_settings()

    lang_info = _detect_language_from_extension(file_path, config_settings)
    if lang_info is None:
        return None

    lang_name, lang_config = lang_info

    parser = get_language_parser(lang_name)

    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    tree = parser.parse(bytes(source_code, "utf-8"))

    raw_metrics = analyze_raw_metrics(source_code, tree, lang_config)

    halstead_metrics = analyze_halstead_metrics(
        source_code, tree, lang_config, config_settings
    )

    return FileAnalysis(
        file_path=file_path,
        raw_metrics=raw_metrics,
        halstead_metrics=halstead_metrics,
    )


def _should_exclude_path(path: Path, excluded: tuple[str, ...]) -> bool:
    """Check if a path should be excluded from analysis.

    Args:
        path: Path to check
        excluded: Tuple of excluded path patterns

    Returns:
        True if the path should be excluded
    """
    path_str = str(path)
    path_parts = path.parts

    for exclude_pattern in excluded:
        if exclude_pattern in path_parts:
            return True
        if exclude_pattern in path_str:
            return True

    return False


def _get_all_source_files(
    directory: Path, config_settings: Dict[str, Any]
) -> list[Path]:
    """Get all source files in a directory recursively for the default language.

    Args:
        directory: Directory to search
        config_settings: Config dictionary

    Returns:
        List of Path objects for source files matching the default language
    """
    source_files: list[Path] = []

    default_lang = config_settings.get("default_language", "python")
    languages = config_settings.get("languages", {})

    if default_lang not in languages:
        return source_files

    lang_config = languages[default_lang]
    extensions = set(lang_config.get("extensions", []))
    exclusions = tuple(lang_config.get("excluded", []))

    for item in directory.rglob("*"):
        if item.is_file():
            if item.suffix in extensions:
                if not _should_exclude_path(item, exclusions):
                    source_files.append(item)

    return source_files


def analyze_directory(
    directory_path: Path, config_settings: Optional[Dict[str, Any]] = None
) -> DirectoryAnalysis:
    """Analyze all source files in a directory recursively.

    Args:
        directory_path: Path to the directory to analyze
        config_settings: Config dictionary (uses default if None)

    Returns:
        DirectoryAnalysis object with aggregated results
    """
    if config_settings is None:
        config_settings = settings.get_all_settings()

    source_files = _get_all_source_files(directory_path, config_settings)

    file_analyses: Dict[Path, FileAnalysis] = {}
    total_raw = RawMetrics()

    aggregated_counters = HalsteadCounters()

    for file_path in track(source_files, description="Analyzing files..."):
        analysis = analyze_file(file_path, config_settings)
        if analysis is not None:
            file_analyses[file_path] = analysis
            total_raw.update(analysis.raw_metrics)

            # Aggregate Halstead metrics
            metrics = analysis.halstead_metrics
            aggregated_counters.operators.update(metrics.operators)
            aggregated_counters.operands.update(metrics.operands)
            aggregated_counters.operator_count += metrics.N1
            aggregated_counters.operand_count += metrics.N2

            # Merge operator counts
            for op, count in metrics.operator_counts.items():
                aggregated_counters.operator_counts[op] = (
                    aggregated_counters.operator_counts.get(op, 0) + count
                )

            # Merge operand counts
            for operand, count in metrics.operand_counts.items():
                aggregated_counters.operand_counts[operand] = (
                    aggregated_counters.operand_counts.get(operand, 0) + count
                )

    # Create aggregated Halstead metrics if we have any files
    total_halstead = None
    if file_analyses:
        total_halstead = HalsteadMetrics.from_counters(aggregated_counters)

    return DirectoryAnalysis(
        directory_path=directory_path,
        file_analyses=file_analyses,
        total_raw_metrics=total_raw,
        total_halstead_metrics=total_halstead,
    )


def analyze_path(
    path: Path, config_settings: Optional[Dict[str, Any]] = None
) -> FileAnalysis | DirectoryAnalysis:
    """Analyze a file or directory path.

    Args:
        path: Path to analyze (file or directory)
        config_settings: Config dictionary (uses default if None)

    Returns:
        FileAnalysis for files, DirectoryAnalysis for directories

    Raises:
        FileNotFoundError: If the path does not exist
        ValueError: If the path is neither a file nor a directory, or if analysis fails
    """
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if path.is_file():
        result = analyze_file(path, config_settings)
        if result is None:
            raise ValueError(f"Unable to analyze file: {path}")
        return result
    elif path.is_dir():
        return analyze_directory(path, config_settings)
    else:
        raise ValueError(f"Path is neither a file nor a directory: {path}")


def _write_csv_report(
    result: FileAnalysis | DirectoryAnalysis,
    hal_only: bool,
    raw_only: bool,
    output_file: Path,
    show_tokens: bool = False,
) -> None:
    """Write analysis results to a CSV file.

    Args:
        result: Analysis results (FileAnalysis or DirectoryAnalysis)
        hal_only: Only include Halstead metrics
        raw_only: Only include raw metrics
        output_file: Path to the output CSV file
        show_tokens: Include operators and operands in the output
    """
    rows: list[dict[str, Any]] = []

    # Collect all unique operators and operands if showing tokens
    all_operators: set[str] = set()
    all_operands: set[str] = set()

    if show_tokens:
        if isinstance(result, FileAnalysis):
            all_operators = set(result.halstead_metrics.operators)
            all_operands = set(result.halstead_metrics.operands)
        else:  # DirectoryAnalysis
            for file_analysis in result.file_analyses.values():
                all_operators.update(file_analysis.halstead_metrics.operators)
                all_operands.update(file_analysis.halstead_metrics.operands)
            if result.total_halstead_metrics:
                all_operators.update(result.total_halstead_metrics.operators)
                all_operands.update(result.total_halstead_metrics.operands)

    if isinstance(result, FileAnalysis):
        # Single file analysis
        row: dict[str, Any] = {"File": str(result.file_path)}

        # Add raw metrics if requested
        if not hal_only:
            row.update(
                {
                    "LOC": result.raw_metrics.loc,
                    "LLOC": result.raw_metrics.lloc,
                    "SLOC": result.raw_metrics.sloc,
                    "Comments": result.raw_metrics.comments,
                    "Multi-lines": result.raw_metrics.multi,
                    "Blank lines": result.raw_metrics.blanks,
                }
            )

        # Add Halstead metrics if requested
        if not raw_only:
            row.update(
                {
                    "η1 (Distinct operators)": result.halstead_metrics.n1,
                    "η2 (Distinct operands)": result.halstead_metrics.n2,
                    "N1 (Total operators)": result.halstead_metrics.N1,
                    "N2 (Total operands)": result.halstead_metrics.N2,
                    "Vocabulary (η)": result.halstead_metrics.vocabulary,
                    "Length (N)": result.halstead_metrics.length,
                    "Volume (V)": round(result.halstead_metrics.volume, 2),
                    "Difficulty (D)": round(result.halstead_metrics.difficulty, 2),
                    "Effort (E)": round(result.halstead_metrics.effort, 2),
                    "Time (T) (seconds)": round(result.halstead_metrics.time, 2),
                    "Delivered Bugs (B)": round(result.halstead_metrics.bugs, 4),
                }
            )

        # Add token details if requested - each token as a separate column
        if show_tokens:
            # Add operator columns
            for op in sorted(all_operators):
                col_name = f"Op: {op}"
                row[col_name] = result.halstead_metrics.operator_counts.get(op, 0)

            # Add operand columns
            for operand in sorted(all_operands):
                col_name = f"Opnd: {operand}"
                row[col_name] = result.halstead_metrics.operand_counts.get(operand, 0)

        rows.append(row)

    else:  # DirectoryAnalysis
        # For directory analysis, create rows for each file plus a total row
        for file_path, file_analysis in sorted(result.file_analyses.items()):
            rel_path = file_path.relative_to(result.directory_path)
            row: dict[str, Any] = {"File": str(rel_path)}

            # Add raw metrics if requested
            if not hal_only:
                row.update(
                    {
                        "LOC": file_analysis.raw_metrics.loc,
                        "LLOC": file_analysis.raw_metrics.lloc,
                        "SLOC": file_analysis.raw_metrics.sloc,
                        "Comments": file_analysis.raw_metrics.comments,
                        "Multi-lines": file_analysis.raw_metrics.multi,
                        "Blank lines": file_analysis.raw_metrics.blanks,
                    }
                )

            # Add Halstead metrics if requested
            if not raw_only:
                row.update(
                    {
                        "η1 (Distinct operators)": file_analysis.halstead_metrics.n1,
                        "η2 (Distinct operands)": file_analysis.halstead_metrics.n2,
                        "N1 (Total operators)": file_analysis.halstead_metrics.N1,
                        "N2 (Total operands)": file_analysis.halstead_metrics.N2,
                        "Vocabulary (η)": file_analysis.halstead_metrics.vocabulary,
                        "Length (N)": file_analysis.halstead_metrics.length,
                        "Volume (V)": round(file_analysis.halstead_metrics.volume, 2),
                        "Difficulty (D)": round(
                            file_analysis.halstead_metrics.difficulty, 2
                        ),
                        "Effort (E)": round(file_analysis.halstead_metrics.effort, 2),
                        "Time (T) (seconds)": round(
                            file_analysis.halstead_metrics.time, 2
                        ),
                        "Delivered Bugs (B)": round(
                            file_analysis.halstead_metrics.bugs, 4
                        ),
                    }
                )

            # Add token details if requested - each token as a separate column
            if show_tokens:
                # Add operator columns
                for op in sorted(all_operators):
                    col_name = f"Op: {op}"
                    row[col_name] = file_analysis.halstead_metrics.operator_counts.get(
                        op, 0
                    )

                # Add operand columns
                for operand in sorted(all_operands):
                    col_name = f"Opnd: {operand}"
                    row[col_name] = file_analysis.halstead_metrics.operand_counts.get(
                        operand, 0
                    )

            rows.append(row)

        # Add total row
        total_row: dict[str, Any] = {"File": "TOTAL"}

        # Add aggregated raw metrics if requested
        if not hal_only:
            total_row.update(
                {
                    "LOC": result.total_raw_metrics.loc,
                    "LLOC": result.total_raw_metrics.lloc,
                    "SLOC": result.total_raw_metrics.sloc,
                    "Comments": result.total_raw_metrics.comments,
                    "Multi-lines": result.total_raw_metrics.multi,
                    "Blank lines": result.total_raw_metrics.blanks,
                }
            )

        # Add aggregated Halstead metrics if requested
        if not raw_only and result.total_halstead_metrics:
            total_row.update(
                {
                    "η1 (Distinct operators)": result.total_halstead_metrics.n1,
                    "η2 (Distinct operands)": result.total_halstead_metrics.n2,
                    "N1 (Total operators)": result.total_halstead_metrics.N1,
                    "N2 (Total operands)": result.total_halstead_metrics.N2,
                    "Vocabulary (η)": result.total_halstead_metrics.vocabulary,
                    "Length (N)": result.total_halstead_metrics.length,
                    "Volume (V)": round(result.total_halstead_metrics.volume, 2),
                    "Difficulty (D)": round(
                        result.total_halstead_metrics.difficulty, 2
                    ),
                    "Effort (E)": round(result.total_halstead_metrics.effort, 2),
                    "Time (T) (seconds)": round(result.total_halstead_metrics.time, 2),
                    "Delivered Bugs (B)": round(result.total_halstead_metrics.bugs, 4),
                }
            )

        # Add token details if requested - each token as a separate column
        if show_tokens and result.total_halstead_metrics:
            # Add operator columns
            for op in sorted(all_operators):
                col_name = f"Op: {op}"
                total_row[col_name] = result.total_halstead_metrics.operator_counts.get(
                    op, 0
                )

            # Add operand columns
            for operand in sorted(all_operands):
                col_name = f"Opnd: {operand}"
                total_row[col_name] = result.total_halstead_metrics.operand_counts.get(
                    operand, 0
                )

        rows.append(total_row)

    # Write to CSV file
    if rows:
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def display_report(
    result: FileAnalysis | DirectoryAnalysis,
    hal_only: bool = False,
    raw_only: bool = False,
    show_tokens: bool = False,
    output_file: Optional[Path] = None,
) -> None:
    """Display a formatted report using Rich tables.

    Args:
        result: Analysis results (FileAnalysis or DirectoryAnalysis)
        hal_only: Only show Halstead metrics
        raw_only: Only show raw metrics
        show_tokens: Show operators and operands
        output_file: Optional file path to write the report to
    """
    if output_file and output_file.suffix.lower() == ".csv":
        _write_csv_report(result, hal_only, raw_only, output_file, show_tokens)
        return

    # Create console - if output_file is provided, use StringIO to capture output
    string_output = None
    if output_file:
        string_output = io.StringIO()
        console = Console(file=string_output, record=True)
    else:
        console = Console()

    if isinstance(result, FileAnalysis):
        # Title
        console.print(
            f"\n[bold cyan]Analysis Report for:[/bold cyan] {result.file_path}\n"
        )

        # Raw Metrics Table
        if not hal_only:
            raw_table = Table(
                title="Raw Metrics",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            raw_table.add_column("Metric", style="cyan", no_wrap=True)
            raw_table.add_column("Value", justify="right", style="green")

            raw_table.add_row("LOC (Lines of Code)", str(result.raw_metrics.loc))
            raw_table.add_row(
                "LLOC (Logical Lines of Code)", str(result.raw_metrics.lloc)
            )
            raw_table.add_row(
                "SLOC (Source Lines of Code)", str(result.raw_metrics.sloc)
            )
            raw_table.add_row("Comments", str(result.raw_metrics.comments))
            raw_table.add_row("Multi-lines", str(result.raw_metrics.multi))
            raw_table.add_row("Blank lines", str(result.raw_metrics.blanks))

            console.print(raw_table)
            console.print()

        # Halstead Metrics Table
        if not raw_only:
            hal_table = Table(
                title="Halstead Metrics",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            hal_table.add_column("Metric", style="cyan", no_wrap=True)
            hal_table.add_column("Value", justify="right", style="green")

            hal_table.add_row(
                "η1 (Distinct operators)", str(result.halstead_metrics.n1)
            )
            hal_table.add_row("η2 (Distinct operands)", str(result.halstead_metrics.n2))
            hal_table.add_row("N1 (Total operators)", str(result.halstead_metrics.N1))
            hal_table.add_row("N2 (Total operands)", str(result.halstead_metrics.N2))
            hal_table.add_row("Vocabulary (η)", str(result.halstead_metrics.vocabulary))
            hal_table.add_row("Length (N)", str(result.halstead_metrics.length))
            hal_table.add_row("Volume (V)", f"{result.halstead_metrics.volume:.2f}")
            hal_table.add_row(
                "Difficulty (D)", f"{result.halstead_metrics.difficulty:.2f}"
            )
            hal_table.add_row("Effort (E)", f"{result.halstead_metrics.effort:.2f}")
            hal_table.add_row(
                "Time (T) (seconds)", f"{result.halstead_metrics.time:.2f}"
            )
            hal_table.add_row(
                "Delivered Bugs (B)", f"{result.halstead_metrics.bugs:.4f}"
            )

            console.print(hal_table)
            console.print()

        # Tokens Tables
        if show_tokens:
            # Operators Table
            op_table = Table(
                title="Distinct Operators",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            op_table.add_column(
                f"Operator ({result.halstead_metrics.n1})", style="yellow"
            )
            op_table.add_column(
                f"Count ({sum(result.halstead_metrics.operator_counts.values())})",
                justify="right",
                style="green",
            )

            for op in sorted(result.halstead_metrics.operators):
                count = result.halstead_metrics.operator_counts.get(op, 0)
                op_table.add_row(f"'{op}'", str(count))

            console.print(op_table)
            console.print()

            # Operands Table
            operand_table = Table(
                title="Distinct Operands",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            operand_table.add_column(
                f"Operand ({result.halstead_metrics.n2})", style="yellow"
            )
            operand_table.add_column(
                f"Count ({sum(result.halstead_metrics.operand_counts.values())})",
                justify="right",
                style="green",
            )

            for operand in sorted(result.halstead_metrics.operands):
                count = result.halstead_metrics.operand_counts.get(operand, 0)
                operand_table.add_row(f"'{operand}'", str(count))

            console.print(operand_table)
            console.print()

    else:  # DirectoryAnalysis
        # Title
        console.print(
            f"\n[bold cyan]Analysis Report for Directory:[/bold cyan] {result.directory_path}"
        )
        console.print(f"[bold]Files analyzed:[/bold] {len(result.file_analyses)}\n")

        # Aggregated Raw Metrics Table
        if not hal_only:
            raw_table = Table(
                title="Aggregated Raw Metrics",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            raw_table.add_column("Metric", style="cyan", no_wrap=True)
            raw_table.add_column("Value", justify="right", style="green")

            raw_table.add_row("LOC (Lines of Code)", str(result.total_raw_metrics.loc))
            raw_table.add_row(
                "LLOC (Logical Lines of Code)", str(result.total_raw_metrics.lloc)
            )
            raw_table.add_row(
                "SLOC (Source Lines of Code)", str(result.total_raw_metrics.sloc)
            )
            raw_table.add_row("Comments", str(result.total_raw_metrics.comments))
            raw_table.add_row("Multi-lines", str(result.total_raw_metrics.multi))
            raw_table.add_row("Blank lines", str(result.total_raw_metrics.blanks))

            console.print(raw_table)
            console.print()

        # Aggregated Halstead Metrics Table
        if not raw_only and result.total_halstead_metrics:
            hal_table = Table(
                title="Aggregated Halstead Metrics",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            hal_table.add_column("Metric", style="cyan", no_wrap=True)
            hal_table.add_column("Value", justify="right", style="green")

            hal_table.add_row(
                "η1 (Distinct operators)", str(result.total_halstead_metrics.n1)
            )
            hal_table.add_row(
                "η2 (Distinct operands)", str(result.total_halstead_metrics.n2)
            )
            hal_table.add_row(
                "N1 (Total operators)", str(result.total_halstead_metrics.N1)
            )
            hal_table.add_row(
                "N2 (Total operands)", str(result.total_halstead_metrics.N2)
            )
            hal_table.add_row(
                "Vocabulary (η)", str(result.total_halstead_metrics.vocabulary)
            )
            hal_table.add_row("Length (N)", str(result.total_halstead_metrics.length))
            hal_table.add_row(
                "Volume (V)", f"{result.total_halstead_metrics.volume:.2f}"
            )
            hal_table.add_row(
                "Difficulty (D)", f"{result.total_halstead_metrics.difficulty:.2f}"
            )
            hal_table.add_row(
                "Effort (E)", f"{result.total_halstead_metrics.effort:.2f}"
            )
            hal_table.add_row(
                "Time (T) (seconds)", f"{result.total_halstead_metrics.time:.2f}"
            )
            hal_table.add_row(
                "Delivered Bugs (B)", f"{result.total_halstead_metrics.bugs:.4f}"
            )

            console.print(hal_table)
            console.print()

        # Individual Files Table
        if result.file_analyses:
            files_table = Table(
                title="Individual Files",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            files_table.add_column("File", style="cyan")

            for file_path in sorted(result.file_analyses.keys()):
                rel_path = file_path.relative_to(result.directory_path)
                files_table.add_row(str(rel_path))

            console.print(files_table)
            console.print()

    # Write to file if output_file is provided
    if output_file and string_output:
        output_content = string_output.getvalue()
        stripped_content = output_content.strip()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(stripped_content)
            f.write("\n")
