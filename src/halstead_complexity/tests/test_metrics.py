"""
Comprehensive tests for metrics modules.

This module tests:
- raw_metrics.py: RawMetrics class and analyze_raw_metrics function
- halstead.py: HalsteadCounters, HalsteadMetrics, and analyze_halstead_metrics
- analysis.py: FileAnalysis, DirectoryAnalysis, and analysis functions
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Any

import pytest
from tree_sitter import Language, Parser, Tree

from halstead_complexity.config import settings
from halstead_complexity.metrics.analysis import (
    DirectoryAnalysis,
    FileAnalysis,
    LanguageNotSupportedError,
    analyze_directory,
    analyze_file,
    analyze_path,
    get_language_parser,
    language_cache,
)
from halstead_complexity.metrics.halstead import (
    HalsteadCounters,
    HalsteadMetrics,
    analyze_halstead_metrics,
)
from halstead_complexity.metrics.raw_metrics import RawMetrics, analyze_raw_metrics

# Import tree-sitter languages
try:
    import tree_sitter_python as tspython

    PYTHON_LANGUAGE: Language | None = Language(tspython.language())
    _has_python: bool = True
except ImportError:
    PYTHON_LANGUAGE = None  # type: ignore
    _has_python = False

try:
    import tree_sitter_javascript as tsjavascript

    JAVASCRIPT_LANGUAGE: Language | None = Language(tsjavascript.language())
    _has_javascript: bool = True
except ImportError:
    JAVASCRIPT_LANGUAGE = None  # type: ignore
    _has_javascript = False


# ============================================================================
# Fixtures and Helper Functions
# ============================================================================


@pytest.fixture
def examples_dir() -> Path:
    """Return the examples directory path."""
    path = Path(__file__).parent.parent / "examples"
    if not path.exists():
        pytest.skip("examples directory not found")
    return path


@pytest.fixture
def config() -> dict[str, Any]:
    """Return the configuration settings."""
    return settings.get_all_settings()


@pytest.fixture
def python_lang_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return Python language configuration."""
    return config["languages"]["python"]


def get_python_parser() -> Parser:
    """Get a parser for Python code."""
    if not _has_python or PYTHON_LANGUAGE is None:
        pytest.skip("tree-sitter-python not available")
    return Parser(PYTHON_LANGUAGE)


def get_javascript_parser() -> Parser:
    """Get a parser for JavaScript code."""
    if not _has_javascript or JAVASCRIPT_LANGUAGE is None:
        pytest.skip("tree-sitter-javascript not available")
    return Parser(JAVASCRIPT_LANGUAGE)


def parse_python(code: str) -> Tree:
    """Parse Python code and return tree."""
    parser = get_python_parser()
    return parser.parse(bytes(code, "utf-8"))


def parse_javascript(code: str) -> Tree:
    """Parse JavaScript code and return tree."""
    parser = get_javascript_parser()
    return parser.parse(bytes(code, "utf-8"))


# ============================================================================
# Tests for raw_metrics.py
# ============================================================================


class TestRawMetrics:
    """Tests for the RawMetrics dataclass."""

    def test_default_initialization(self) -> None:
        """Test that all fields default to 0."""
        metrics = RawMetrics()

        assert metrics.loc == 0
        assert metrics.lloc == 0
        assert metrics.sloc == 0
        assert metrics.comments == 0
        assert metrics.multi == 0
        assert metrics.blanks == 0
        assert metrics.single_comments == 0

    def test_initialization_with_values(self) -> None:
        """Test initialization with specific values."""
        metrics = RawMetrics(
            loc=100,
            lloc=80,
            sloc=70,
            comments=10,
            multi=5,
            blanks=15,
            single_comments=8,
        )

        assert metrics.loc == 100
        assert metrics.lloc == 80
        assert metrics.sloc == 70
        assert metrics.comments == 10
        assert metrics.multi == 5
        assert metrics.blanks == 15
        assert metrics.single_comments == 8

    def test_add_operation(self) -> None:
        """Test adding two RawMetrics instances."""
        m1 = RawMetrics(
            loc=10, lloc=8, sloc=7, comments=2, multi=1, blanks=2, single_comments=1
        )
        m2 = RawMetrics(
            loc=20, lloc=16, sloc=14, comments=4, multi=2, blanks=4, single_comments=3
        )

        result = m1 + m2

        assert result.loc == 30
        assert result.lloc == 24
        assert result.sloc == 21
        assert result.comments == 6
        assert result.multi == 3
        assert result.blanks == 6
        assert result.single_comments == 4

    def test_add_preserves_originals(self) -> None:
        """Test that addition doesn't modify original instances."""
        m1 = RawMetrics(loc=10, lloc=8)
        m2 = RawMetrics(loc=20, lloc=16)

        _ = m1 + m2

        assert m1.loc == 10
        assert m2.loc == 20

    def test_update_method(self) -> None:
        """Test the update method modifies in-place."""
        m1 = RawMetrics(loc=10, lloc=8, sloc=7, comments=2, multi=1, blanks=2)
        m2 = RawMetrics(loc=20, lloc=16, sloc=14, comments=4, multi=2, blanks=4)

        m1.update(m2)

        assert m1.loc == 30
        assert m1.lloc == 24
        assert m1.sloc == 21
        assert m1.comments == 6
        assert m1.multi == 3
        assert m1.blanks == 6


class TestAnalyzeRawMetrics:
    """Tests for the analyze_raw_metrics function."""

    def test_simple_python_code(self, python_lang_config: dict[str, Any]) -> None:
        """Test analyzing simple Python code."""
        code = "def add(a, b):\n    return a + b\n\nresult = add(1, 2)\n"
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc == 4
        assert metrics.lloc > 0
        assert metrics.sloc > 0

    def test_python_with_single_line_comments(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test analyzing Python code with single-line comments."""
        code = "# This is a comment\ndef foo():\n    # Another comment\n    return 42\n"
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc == 4
        assert metrics.comments == 2
        assert metrics.single_comments == 2

    def test_python_with_docstring(self, python_lang_config: dict[str, Any]) -> None:
        """Test analyzing Python code with docstrings (multi-line comments)."""
        code = 'def foo():\n    """\n    Docstring.\n    Multiple lines.\n    """\n    return 42\n'
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc == 6
        assert metrics.multi >= 2

    def test_python_with_blank_lines(self, python_lang_config: dict[str, Any]) -> None:
        """Test analyzing Python code with blank lines."""
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n\n"
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc == 6
        assert metrics.blanks >= 2

    def test_empty_code(self, python_lang_config: dict[str, Any]) -> None:
        """Test analyzing empty code returns zero metrics."""
        code = ""
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc == 0
        assert metrics.blanks == 0
        assert metrics.lloc == 0
        assert metrics.sloc == 0

    def test_only_comments(self, python_lang_config: dict[str, Any]) -> None:
        """Test analyzing code with only comments."""
        code = "# Comment 1\n# Comment 2\n# Comment 3\n"
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc == 3
        assert metrics.comments == 3
        assert metrics.single_comments == 3
        assert metrics.lloc == 0


# ============================================================================
# Tests for halstead.py
# ============================================================================


class TestHalsteadCounters:
    """Tests for the HalsteadCounters dataclass."""

    def test_default_initialization(self) -> None:
        """Test default initialization creates empty sets and counts."""
        counters = HalsteadCounters()

        assert isinstance(counters.operators, set)
        assert isinstance(counters.operands, set)
        assert len(counters.operators) == 0
        assert len(counters.operands) == 0
        assert counters.operator_count == 0
        assert counters.operand_count == 0
        assert isinstance(counters.operator_counts, dict)
        assert isinstance(counters.operand_counts, dict)

    def test_accumulate_operators(self) -> None:
        """Test accumulating operator data."""
        counters = HalsteadCounters()
        counters.operators.update({"+", "-", "*"})
        counters.operator_count = 10
        counters.operator_counts = {"+": 5, "-": 3, "*": 2}

        assert len(counters.operators) == 3
        assert counters.operator_count == 10
        assert sum(counters.operator_counts.values()) == 10

    def test_accumulate_operands(self) -> None:
        """Test accumulating operand data."""
        counters = HalsteadCounters()
        counters.operands.update({"x", "y", "z"})
        counters.operand_count = 7
        counters.operand_counts = {"x": 3, "y": 2, "z": 2}

        assert len(counters.operands) == 3
        assert counters.operand_count == 7
        assert sum(counters.operand_counts.values()) == 7


class TestHalsteadMetrics:
    """Tests for the HalsteadMetrics dataclass."""

    def test_from_counters_basic(self) -> None:
        """Test creating metrics from basic counters."""
        counters = HalsteadCounters()
        counters.operators = {"+", "="}
        counters.operands = {"a", "b", "result"}
        counters.operator_count = 3
        counters.operand_count = 4

        metrics = HalsteadMetrics.from_counters(counters)

        assert metrics.n1 == 2
        assert metrics.n2 == 3
        assert metrics.N1 == 3
        assert metrics.N2 == 4
        assert metrics.vocabulary == 5
        assert metrics.length == 7

    def test_volume_calculation(self) -> None:
        """Test volume is calculated as length * log2(vocabulary)."""
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operands = {"x", "y"}
        counters.operator_count = 1
        counters.operand_count = 2

        metrics = HalsteadMetrics.from_counters(counters)

        # vocabulary = 1 + 2 = 3, length = 1 + 2 = 3
        # volume = 3 * log2(3)
        expected_volume = 3 * math.log2(3)
        assert math.isclose(metrics.volume, expected_volume, rel_tol=1e-9)

    def test_difficulty_calculation(self) -> None:
        """Test difficulty is (n1/2) * (N2/n2)."""
        counters = HalsteadCounters()
        counters.operators = {"+", "="}
        counters.operands = {"x", "y"}
        counters.operator_count = 3
        counters.operand_count = 4

        metrics = HalsteadMetrics.from_counters(counters)

        # difficulty = (2 / 2) * (4 / 2) = 1 * 2 = 2
        assert metrics.difficulty == 2.0

    def test_effort_calculation(self) -> None:
        """Test effort is difficulty * volume."""
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operands = {"x", "y"}
        counters.operator_count = 1
        counters.operand_count = 2

        metrics = HalsteadMetrics.from_counters(counters)

        expected_effort = metrics.difficulty * metrics.volume
        assert math.isclose(metrics.effort, expected_effort, rel_tol=1e-9)

    def test_time_calculation(self) -> None:
        """Test time is effort / 18."""
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operands = {"x", "y"}
        counters.operator_count = 1
        counters.operand_count = 2

        metrics = HalsteadMetrics.from_counters(counters)

        expected_time = metrics.effort / 18
        assert math.isclose(metrics.time, expected_time, rel_tol=1e-9)

    def test_bugs_calculation(self) -> None:
        """Test bugs is volume / 3000."""
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operands = {"x", "y"}
        counters.operator_count = 1
        counters.operand_count = 2

        metrics = HalsteadMetrics.from_counters(counters)

        expected_bugs = metrics.volume / 3000
        assert math.isclose(metrics.bugs, expected_bugs, rel_tol=1e-9)

    def test_zero_operands_handling(self) -> None:
        """Test graceful handling of zero operands."""
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operator_count = 1

        metrics = HalsteadMetrics.from_counters(counters)

        assert metrics.n2 == 0
        assert metrics.difficulty == 0.0
        assert metrics.volume == 0.0

    def test_empty_counters(self) -> None:
        """Test metrics from empty counters are all zero."""
        counters = HalsteadCounters()

        metrics = HalsteadMetrics.from_counters(counters)

        assert metrics.n1 == 0
        assert metrics.n2 == 0
        assert metrics.N1 == 0
        assert metrics.N2 == 0
        assert metrics.vocabulary == 0
        assert metrics.length == 0
        assert metrics.volume == 0.0
        assert metrics.difficulty == 0.0
        assert metrics.effort == 0.0
        assert metrics.time == 0.0
        assert metrics.bugs == 0.0


class TestAnalyzeHalsteadMetrics:
    """Tests for the analyze_halstead_metrics function."""

    def test_simple_assignment(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test analyzing a simple assignment expression."""
        code = "result = a + b"
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n1 >= 2  # At least = and +
        assert metrics.n2 >= 3  # At least result, a, b
        assert metrics.N1 >= 2
        assert metrics.N2 >= 3
        assert metrics.volume > 0

    def test_python_function(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test analyzing a Python function."""
        code = "def add(a, b):\n    return a + b\n"
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n1 >= 2  # Multiple operators
        assert metrics.n2 >= 3  # Multiple operands
        assert metrics.vocabulary > 0

    def test_numeric_literals(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test that numeric literals are counted as operands."""
        code = "x = 42 + 3.14"
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n2 >= 3  # x, 42, 3.14

    def test_string_literals(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test that string literals are counted as operands."""
        code = 'message = "Hello, World!"'
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n2 >= 2  # message, string

    def test_empty_code_returns_zero(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test that empty code returns zero metrics."""
        code = ""
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n1 == 0
        assert metrics.n2 == 0
        assert metrics.volume == 0.0


# ============================================================================
# Tests for analysis.py
# ============================================================================


class TestFileAnalysis:
    """Tests for the FileAnalysis dataclass."""

    def test_structure_and_fields(self) -> None:
        """Test FileAnalysis contains expected fields."""
        path = Path("/tmp/test.py")
        raw_metrics = RawMetrics(loc=10, lloc=8, sloc=7)
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operands = {"x"}
        counters.operator_count = 1
        counters.operand_count = 1
        halstead_metrics = HalsteadMetrics.from_counters(counters)

        analysis = FileAnalysis(
            file_path=path,
            raw_metrics=raw_metrics,
            halstead_metrics=halstead_metrics,
        )

        assert analysis.file_path == path
        assert analysis.raw_metrics.loc == 10
        assert analysis.halstead_metrics.n1 == 1


class TestDirectoryAnalysis:
    """Tests for the DirectoryAnalysis dataclass."""

    def test_structure_and_aggregation(self) -> None:
        """Test DirectoryAnalysis contains expected fields."""
        path = Path("/tmp/project")
        file_analyses: dict[Path, FileAnalysis] = {}
        total_raw = RawMetrics(loc=100, lloc=80)
        counters = HalsteadCounters()
        counters.operators = {"+"}
        counters.operands = {"x"}
        counters.operator_count = 1
        counters.operand_count = 1
        total_halstead = HalsteadMetrics.from_counters(counters)

        analysis = DirectoryAnalysis(
            directory_path=path,
            file_analyses=file_analyses,
            total_raw_metrics=total_raw,
            total_halstead_metrics=total_halstead,
        )

        assert analysis.directory_path == path
        assert len(analysis.file_analyses) == 0
        assert analysis.total_raw_metrics.loc == 100
        assert analysis.total_halstead_metrics is not None
        assert analysis.total_halstead_metrics.n1 == 1


class TestAnalyzeFile:
    """Tests for the analyze_file function."""

    def test_analyze_existing_python_file(self, examples_dir: Path) -> None:
        """Test analyzing an existing Python file."""
        is_odd_file = examples_dir / "is_odd.py"
        if not is_odd_file.exists():
            pytest.skip("is_odd.py not found")

        analysis = analyze_file(is_odd_file)

        assert analysis is not None
        assert analysis.file_path == is_odd_file
        assert analysis.raw_metrics.loc > 0
        assert analysis.halstead_metrics.vocabulary > 0

    def test_analyze_nonexistent_file(self) -> None:
        """Test that analyzing non-existent file returns None."""
        fake_file = Path("/tmp/nonexistent_file_12345.py")

        analysis = analyze_file(fake_file)

        assert analysis is None

    def test_analyze_unsupported_extension(self) -> None:
        """Test that unsupported file extension returns None."""
        fake_file = Path("/tmp/test.unsupported")

        analysis = analyze_file(fake_file)

        assert analysis is None

    def test_analyze_with_tempfile(self) -> None:
        """Test analyzing a temporary Python file."""
        code = "def hello():\n    return 'world'\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analysis = analyze_file(temp_path)
            assert analysis is not None
            assert analysis.raw_metrics.loc > 0
        finally:
            temp_path.unlink(missing_ok=True)


class TestAnalyzeDirectory:
    """Tests for the analyze_directory function."""

    def test_analyze_examples_directory(self, examples_dir: Path) -> None:
        """Test analyzing directory with Python files."""
        analysis = analyze_directory(examples_dir)

        assert analysis is not None
        assert analysis.directory_path == examples_dir
        assert len(analysis.file_analyses) >= 1
        assert analysis.total_raw_metrics.loc > 0

    def test_analyze_empty_directory(self, tmp_path: Path) -> None:
        """Test analyzing an empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        analysis = analyze_directory(empty_dir)

        assert analysis is not None
        assert len(analysis.file_analyses) == 0
        assert analysis.total_raw_metrics.loc == 0
        assert analysis.total_halstead_metrics is None


class TestAnalyzePath:
    """Tests for the analyze_path function."""

    def test_with_file_path(self, examples_dir: Path) -> None:
        """Test analyze_path with a file returns FileAnalysis."""
        is_odd_file = examples_dir / "is_odd.py"
        if not is_odd_file.exists():
            pytest.skip("is_odd.py not found")

        result = analyze_path(is_odd_file)

        assert isinstance(result, FileAnalysis)
        assert result.file_path == is_odd_file

    def test_with_directory_path(self, examples_dir: Path) -> None:
        """Test analyze_path with a directory returns DirectoryAnalysis."""
        result = analyze_path(examples_dir)

        assert isinstance(result, DirectoryAnalysis)
        assert result.directory_path == examples_dir

    def test_with_nonexistent_path(self) -> None:
        """Test analyze_path raises FileNotFoundError for non-existent path."""
        fake_path = Path("/tmp/nonexistent_path_12345")

        with pytest.raises(FileNotFoundError):
            analyze_path(fake_path)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_analysis_pipeline(self) -> None:
        """Test complete workflow from code to analysis."""
        code = "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nresult = factorial(5)\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analysis = analyze_file(temp_path)

            assert analysis is not None
            assert analysis.raw_metrics.loc > 0
            assert analysis.halstead_metrics.volume > 0
            assert analysis.halstead_metrics.difficulty > 0
            assert analysis.halstead_metrics.effort > 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_complexity_comparison(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test that complex code has higher metrics than simple code."""
        simple_code = "x = 1"
        complex_code = "def f(a, b, c):\n    if a > b:\n        return a * c\n    elif b > c:\n        return b * a\n    else:\n        return c * (a + b)\n"

        simple_tree = parse_python(simple_code)
        complex_tree = parse_python(complex_code)

        simple_metrics = analyze_halstead_metrics(
            simple_code, simple_tree, python_lang_config, config
        )
        complex_metrics = analyze_halstead_metrics(
            complex_code, complex_tree, python_lang_config, config
        )

        assert complex_metrics.vocabulary > simple_metrics.vocabulary
        assert complex_metrics.volume > simple_metrics.volume
        assert complex_metrics.effort > simple_metrics.effort


# ============================================================================
# Tests for Specific Example Files
# ============================================================================


class TestExampleFiles:
    """Tests for specific example files with expected metrics.

    Note: These tests verify exact metrics. If the analysis logic or example
    files change, these values will need to be updated.
    """

    def test_is_odd_py_exact_metrics(self, examples_dir: Path) -> None:
        """Test exact metrics for is_odd.py example."""
        is_odd_file = examples_dir / "is_odd.py"
        if not is_odd_file.exists():
            pytest.skip("is_odd.py not found")

        analysis = analyze_file(is_odd_file)
        assert analysis is not None

        # Raw metrics
        assert analysis.raw_metrics.loc == 12
        assert analysis.raw_metrics.lloc == 9
        assert analysis.raw_metrics.sloc == 9
        assert analysis.raw_metrics.comments == 1
        assert analysis.raw_metrics.multi == 0
        assert analysis.raw_metrics.blanks == 2

        # Halstead metrics
        assert analysis.halstead_metrics.n1 == 11
        assert analysis.halstead_metrics.n2 == 11
        assert analysis.halstead_metrics.N1 == 24
        assert analysis.halstead_metrics.N2 == 17
        assert analysis.halstead_metrics.vocabulary == 22
        assert analysis.halstead_metrics.length == 41
        assert math.isclose(analysis.halstead_metrics.volume, 182.84, abs_tol=0.5)
        assert math.isclose(analysis.halstead_metrics.difficulty, 8.50, abs_tol=0.1)
        assert math.isclose(analysis.halstead_metrics.effort, 1554.11, abs_tol=1.0)

    def test_is_odd_js_exact_metrics(self, examples_dir: Path) -> None:
        """Test exact metrics for is_odd.js example."""
        is_odd_file = examples_dir / "is_odd.js"
        if not is_odd_file.exists():
            pytest.skip("is_odd.js not found")

        analysis = analyze_file(is_odd_file)
        assert analysis is not None

        # Raw metrics
        assert analysis.raw_metrics.loc == 13
        assert analysis.raw_metrics.lloc == 9
        assert analysis.raw_metrics.sloc == 11
        assert analysis.raw_metrics.comments == 1
        assert analysis.raw_metrics.multi == 0
        assert analysis.raw_metrics.blanks == 1

        # Halstead metrics
        assert analysis.halstead_metrics.n1 == 11
        assert analysis.halstead_metrics.n2 == 12
        assert analysis.halstead_metrics.N1 == 29
        assert analysis.halstead_metrics.N2 == 19
        assert analysis.halstead_metrics.vocabulary == 23
        assert analysis.halstead_metrics.length == 48
        assert math.isclose(analysis.halstead_metrics.volume, 217.13, abs_tol=0.5)
        assert math.isclose(analysis.halstead_metrics.difficulty, 8.71, abs_tol=0.1)
        assert math.isclose(analysis.halstead_metrics.effort, 1890.85, abs_tol=1.0)

    def test_calculator_py_exact_metrics(self, examples_dir: Path) -> None:
        """Test exact metrics for calculator.py example."""
        calc_file = examples_dir / "calculator.py"
        if not calc_file.exists():
            pytest.skip("calculator.py not found")

        analysis = analyze_file(calc_file)
        assert analysis is not None

        # Raw metrics
        assert analysis.raw_metrics.loc == 201
        assert analysis.raw_metrics.lloc == 169
        assert analysis.raw_metrics.sloc == 127
        assert analysis.raw_metrics.comments == 7
        assert analysis.raw_metrics.multi == 21
        assert analysis.raw_metrics.blanks == 46

        # Halstead metrics
        assert analysis.halstead_metrics.n1 == 33
        assert analysis.halstead_metrics.n2 == 138
        assert analysis.halstead_metrics.N1 == 542
        assert analysis.halstead_metrics.N2 == 442
        assert analysis.halstead_metrics.vocabulary == 171
        assert analysis.halstead_metrics.length == 984
        assert math.isclose(analysis.halstead_metrics.volume, 7299.17, abs_tol=1.0)
        assert math.isclose(analysis.halstead_metrics.difficulty, 52.85, abs_tol=0.5)
        assert math.isclose(analysis.halstead_metrics.effort, 385745.10, abs_tol=10.0)

    def test_calculator_js_exact_metrics(self, examples_dir: Path) -> None:
        """Test exact metrics for calculator.js example."""
        calc_file = examples_dir / "calculator.js"
        if not calc_file.exists():
            pytest.skip("calculator.js not found")

        analysis = analyze_file(calc_file)
        assert analysis is not None

        # Raw metrics
        assert analysis.raw_metrics.loc == 305
        assert analysis.raw_metrics.lloc == 109
        assert analysis.raw_metrics.sloc == 163
        assert analysis.raw_metrics.comments == 8
        assert analysis.raw_metrics.multi == 97
        assert analysis.raw_metrics.blanks == 37

        # Halstead metrics
        assert analysis.halstead_metrics.n1 == 42
        assert analysis.halstead_metrics.n2 == 117
        assert analysis.halstead_metrics.N1 == 610
        assert analysis.halstead_metrics.N2 == 388
        assert analysis.halstead_metrics.vocabulary == 159
        assert analysis.halstead_metrics.length == 998
        assert math.isclose(analysis.halstead_metrics.volume, 7298.26, abs_tol=1.0)
        assert math.isclose(analysis.halstead_metrics.difficulty, 69.64, abs_tol=0.5)
        assert math.isclose(analysis.halstead_metrics.effort, 508258.12, abs_tol=10.0)

    def test_examples_directory_aggregated_metrics(self, examples_dir: Path) -> None:
        """Test aggregated metrics for examples directory (Python files only)."""
        analysis = analyze_directory(examples_dir)
        assert analysis is not None

        # Should contain both Python example files
        assert len(analysis.file_analyses) == 2

        # Aggregated raw metrics
        assert analysis.total_raw_metrics.loc == 213
        assert analysis.total_raw_metrics.lloc == 178
        assert analysis.total_raw_metrics.sloc == 136
        assert analysis.total_raw_metrics.comments == 8
        assert analysis.total_raw_metrics.multi == 21
        assert analysis.total_raw_metrics.blanks == 48

        # Aggregated Halstead metrics
        assert analysis.total_halstead_metrics is not None
        assert analysis.total_halstead_metrics.n1 == 35
        assert analysis.total_halstead_metrics.n2 == 142
        assert analysis.total_halstead_metrics.N1 == 566
        assert analysis.total_halstead_metrics.N2 == 459
        assert analysis.total_halstead_metrics.vocabulary == 177
        assert analysis.total_halstead_metrics.length == 1025
        assert math.isclose(
            analysis.total_halstead_metrics.volume, 7654.30, abs_tol=1.0
        )
        assert math.isclose(
            analysis.total_halstead_metrics.difficulty, 56.57, abs_tol=0.5
        )
        assert math.isclose(
            analysis.total_halstead_metrics.effort, 432979.79, abs_tol=10.0
        )


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_file_with_only_whitespace(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test analyzing file with only whitespace."""
        code = "   \n\n\t\n   \n"
        tree = parse_python(code)

        metrics = analyze_raw_metrics(code, tree, python_lang_config)

        assert metrics.loc >= 0
        assert metrics.blanks >= 0
        assert metrics.lloc == 0

    def test_file_with_syntax_errors(self):
        """Test that files with syntax errors are handled gracefully."""
        code = "def incomplete_function(\n    # Missing closing parenthesis"
        tree = parse_python(code)
        config = settings.get_all_settings()
        lang_config = config["languages"]["python"]

        # Should still be able to analyze, even with errors
        metrics = analyze_raw_metrics(code, tree, lang_config)
        assert metrics is not None

    def test_very_long_identifier(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test handling of very long identifiers."""
        long_name = "a" * 1000
        code = f"{long_name} = 42"
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n2 >= 1  # Should count the long identifier

    def test_unicode_in_strings(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test handling of Unicode characters in strings."""
        code = 'message = "Hello 世界 🌍"'
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n2 >= 2  # message and string literal

    def test_nested_structures(
        self, python_lang_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Test analyzing deeply nested structures."""
        code = """
def outer():
    def middle():
        def inner():
            return [[[[42]]]]
        return inner()
    return middle()
"""
        tree = parse_python(code)

        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.vocabulary > 0
        assert metrics.volume > 0


# ============================================================================
# Parametrized Tests
# ============================================================================


class TestParametrized:
    """Parametrized tests for various scenarios."""

    @pytest.mark.parametrize(
        "code,expected_min_operators,expected_min_operands",
        [
            ("x = 1", 1, 2),  # =, x, 1
            ("x = 1 + 2", 2, 3),  # =, +, x, 1, 2
            ("x = 1 + 2 - 3", 3, 4),  # =, +, -, x, 1, 2, 3
            ("x = y = z = 0", 1, 4),  # =, x, y, z, 0
        ],
    )
    def test_operator_operand_counts(
        self,
        code: str,
        expected_min_operators: int,
        expected_min_operands: int,
        python_lang_config: dict[str, Any],
        config: dict[str, Any],
    ) -> None:
        """Test various code patterns have expected operator/operand counts."""
        tree = parse_python(code)
        metrics = analyze_halstead_metrics(code, tree, python_lang_config, config)

        assert metrics.n1 >= expected_min_operators
        assert metrics.n2 >= expected_min_operands

    @pytest.mark.parametrize(
        "extension,should_succeed",
        [
            (".py", True),
            (".js", True),
            (".txt", False),
            (".md", False),
            (".unsupported", False),
        ],
    )
    def test_file_extensions(
        self, extension: str, should_succeed: bool, tmp_path: Path
    ) -> None:
        """Test that only supported file extensions are analyzed."""
        test_file = tmp_path / f"test{extension}"

        if extension in [".py", ".js"]:
            content = "x = 1" if extension == ".py" else "var x = 1;"
            test_file.write_text(content)
        else:
            test_file.write_text("some content")

        analysis = analyze_file(test_file)

        if should_succeed:
            assert analysis is not None
        else:
            assert analysis is None

    @pytest.mark.parametrize(
        "loc,lloc,sloc",
        [
            (0, 0, 0),
            (1, 1, 1),
            (10, 8, 7),
            (100, 80, 70),
        ],
    )
    def test_raw_metrics_values(self, loc: int, lloc: int, sloc: int) -> None:
        """Test RawMetrics with various values."""
        metrics = RawMetrics(loc=loc, lloc=lloc, sloc=sloc)

        assert metrics.loc == loc
        assert metrics.lloc == lloc
        assert metrics.sloc == sloc


# ============================================================================
# Config Options Tests
# ============================================================================


class TestConfigOptions:
    """Test different combinations of config options."""

    def test_braces_single_operator_false(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test with braces_single_operator=False (default)."""
        code = "x = [1, 2, 3]"
        tree = parse_python(code)
        config_settings = {"braces_single_operator": False}

        metrics = analyze_halstead_metrics(
            code, tree, python_lang_config, config_settings
        )

        # With False, [ and ] are counted separately
        assert metrics is not None
        assert metrics.n1 >= 3  # =, [, ]
        assert "[" in str(metrics)  # Verify brackets are tracked

    def test_braces_single_operator_true(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test with braces_single_operator=True."""
        code = "x = [1, 2, 3]"
        tree = parse_python(code)
        config_settings = {"braces_single_operator": True}

        metrics = analyze_halstead_metrics(
            code, tree, python_lang_config, config_settings
        )

        # With True, [] is counted as a single operator
        assert metrics is not None
        assert "[]" in str(metrics)  # Verify brackets are tracked
        assert metrics.n1 >= 2  # =, []
        assert metrics.n2 >= 4  # x, 1, 2, 3
        assert metrics.vocabulary > 0
        assert metrics.volume > 0

    def test_braces_with_nested_structures(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test braces_single_operator with nested structures."""
        code = "x = [[1, 2], {3: 4}]"
        tree = parse_python(code)

        # Test with False
        config_false = {"braces_single_operator": False}
        metrics_false = analyze_halstead_metrics(
            code, tree, python_lang_config, config_false
        )

        # Test with True
        config_true = {"braces_single_operator": True}
        metrics_true = analyze_halstead_metrics(
            code, tree, python_lang_config, config_true
        )

        # With True, should have fewer unique operators
        assert metrics_false is not None
        assert metrics_true is not None
        assert metrics_false.n1 >= metrics_true.n1

    @pytest.mark.skipif(not _has_javascript, reason="JavaScript not available")
    def test_template_literal_single_operand_false(self) -> None:
        """Test with template_literal_single_operand=False (default)."""
        code = "const x = `Hello ${name} World`;"
        parser = get_javascript_parser()
        tree = parser.parse(bytes(code, "utf-8"))

        config = settings.get_all_settings()
        js_lang_config = config["languages"]["javascript"]
        config_settings = {"template_literal_single_operand": False}

        metrics = analyze_halstead_metrics(code, tree, js_lang_config, config_settings)

        # With False, template string parts are counted separately
        assert metrics is not None
        assert metrics.n2 >= 3  # x, name, and string parts
        assert metrics.vocabulary > 0
        assert metrics.volume > 0

    @pytest.mark.skipif(not _has_javascript, reason="JavaScript not available")
    def test_template_literal_single_operand_true(self) -> None:
        """Test with template_literal_single_operand=True."""
        code = "const x = `Hello ${name} World`;"
        parser = get_javascript_parser()
        tree = parser.parse(bytes(code, "utf-8"))

        config = settings.get_all_settings()
        js_lang_config = config["languages"]["javascript"]
        config_settings = {"template_literal_single_operand": True}

        metrics = analyze_halstead_metrics(code, tree, js_lang_config, config_settings)

        # With True, entire template string is counted as single operand
        assert metrics is not None
        assert metrics.n2 >= 2  # x and template string (name is inside)
        assert metrics.vocabulary > 0
        assert metrics.volume > 0

    @pytest.mark.skipif(not _has_javascript, reason="JavaScript not available")
    def test_template_literal_with_multiple_expressions(self) -> None:
        """Test template literals with multiple ${} expressions."""
        code = "const msg = `${greeting} ${name} at ${time}`;"
        parser = get_javascript_parser()
        tree = parser.parse(bytes(code, "utf-8"))

        config = settings.get_all_settings()
        js_lang_config = config["languages"]["javascript"]

        # Test with False
        config_false = {"template_literal_single_operand": False}
        metrics_false = analyze_halstead_metrics(
            code, tree, js_lang_config, config_false
        )

        # Test with True
        config_true = {"template_literal_single_operand": True}
        metrics_true = analyze_halstead_metrics(code, tree, js_lang_config, config_true)

        # With True, should have fewer total operands
        assert metrics_false is not None
        assert metrics_true is not None
        assert metrics_false.N2 >= metrics_true.N2

    def test_both_options_together(self, python_lang_config: dict[str, Any]) -> None:
        """Test with both config options enabled."""
        code = """
x = [1, 2, 3]
y = {4, 5, 6}
z = (7, 8, 9)
"""
        tree = parse_python(code)
        config_settings = {
            "braces_single_operator": True,
            "template_literal_single_operand": True,
        }

        metrics = analyze_halstead_metrics(
            code, tree, python_lang_config, config_settings
        )

        # Should analyze successfully with both options
        assert metrics is not None
        assert metrics.n1 > 0
        assert metrics.n2 > 0
        assert metrics.vocabulary > 0
        assert metrics.volume > 0

    def test_both_options_disabled(self, python_lang_config: dict[str, Any]) -> None:
        """Test with both config options disabled."""
        code = """
x = [1, 2, 3]
y = {4, 5, 6}
z = (7, 8, 9)
"""
        tree = parse_python(code)
        config_settings = {
            "braces_single_operator": False,
            "template_literal_single_operand": False,
        }

        metrics = analyze_halstead_metrics(
            code, tree, python_lang_config, config_settings
        )

        # Should analyze successfully with both options disabled
        assert metrics is not None
        assert metrics.n1 > 0
        assert metrics.n2 > 0
        assert metrics.vocabulary > 0
        assert metrics.volume > 0

    def test_config_options_with_empty_code(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test config options with empty code."""
        code = ""
        tree = parse_python(code)

        for braces in [False, True]:
            for template in [False, True]:
                config_settings = {
                    "braces_single_operator": braces,
                    "template_literal_single_operand": template,
                }

                metrics = analyze_halstead_metrics(
                    code, tree, python_lang_config, config_settings
                )

                # Empty code should return metrics with zero values
                assert metrics is not None
                assert metrics.n1 == 0
                assert metrics.n2 == 0
                assert metrics.vocabulary == 0
                assert metrics.volume == 0.0

    def test_config_options_with_only_whitespace(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test config options with whitespace-only code."""
        code = "   \n\t  \n   "
        tree = parse_python(code)

        config_settings = {
            "braces_single_operator": True,
            "template_literal_single_operand": True,
        }

        metrics = analyze_halstead_metrics(
            code, tree, python_lang_config, config_settings
        )

        # Whitespace-only code should return metrics with zero values
        assert metrics is not None
        assert metrics.n1 == 0
        assert metrics.n2 == 0
        assert metrics.vocabulary == 0
        assert metrics.volume == 0.0

    def test_braces_with_function_calls(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test braces_single_operator with function calls."""
        code = """
def foo(a, b, c):
    return [a, b, c]

result = foo(1, 2, 3)
"""
        tree = parse_python(code)

        # Test with False
        config_false = {"braces_single_operator": False}
        metrics_false = analyze_halstead_metrics(
            code, tree, python_lang_config, config_false
        )

        # Test with True
        config_true = {"braces_single_operator": True}
        metrics_true = analyze_halstead_metrics(
            code, tree, python_lang_config, config_true
        )

        # Both should produce valid metrics
        assert metrics_false is not None
        assert metrics_true is not None
        assert metrics_false.volume > 0
        assert metrics_true.volume > 0

    def test_braces_with_comprehensions(
        self, python_lang_config: dict[str, Any]
    ) -> None:
        """Test braces_single_operator with list/dict/set comprehensions."""
        code = """
squares = [x**2 for x in range(10)]
evens = {x for x in range(10) if x % 2 == 0}
mapping = {x: x**2 for x in range(5)}
"""
        tree = parse_python(code)

        # Test with False
        config_false = {"braces_single_operator": False}
        metrics_false = analyze_halstead_metrics(
            code, tree, python_lang_config, config_false
        )

        # Test with True
        config_true = {"braces_single_operator": True}
        metrics_true = analyze_halstead_metrics(
            code, tree, python_lang_config, config_true
        )

        # Both should produce valid metrics
        assert metrics_false is not None
        assert metrics_true is not None
        # With False, should have more unique operators
        assert metrics_false.n1 >= metrics_true.n1

    @pytest.mark.parametrize(
        "braces_single,template_single",
        [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ],
    )
    def test_all_config_combinations(
        self,
        braces_single: bool,
        template_single: bool,
        python_lang_config: dict[str, Any],
    ) -> None:
        """Test all combinations of config options."""
        code = """
def calculate(x, y):
    result = [x + y, x - y, x * y]
    return result

data = calculate(10, 5)
"""
        tree = parse_python(code)
        config_settings = {
            "braces_single_operator": braces_single,
            "template_literal_single_operand": template_single,
        }

        metrics = analyze_halstead_metrics(
            code, tree, python_lang_config, config_settings
        )

        # All combinations should work
        assert metrics is not None
        assert metrics.n1 > 0
        assert metrics.n2 > 0
        assert metrics.N1 > 0
        assert metrics.N2 > 0
        assert metrics.vocabulary > 0
        assert metrics.length > 0
        assert metrics.volume > 0
        assert metrics.difficulty > 0
        assert metrics.effort > 0


class TestCSVExport:
    """Test CSV export functionality."""

    def test_csv_export_single_file(self, tmp_path: Path) -> None:
        """Test CSV export for a single file."""
        csv_file = tmp_path / "output.csv"
        test_file = Path("src/halstead_complexity/examples/is_odd.py")

        if not test_file.exists():
            pytest.skip("Test file not found")

        result = analyze_file(test_file)
        assert result is not None

        # Import here to avoid issues if analysis module changes
        from halstead_complexity.metrics.analysis import display_report

        display_report(result, output_file=csv_file)

        assert csv_file.exists()

        # Read and verify CSV content
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert "File" in rows[0]
        assert "LOC" in rows[0]
        assert "η1 (Distinct operators)" in rows[0]
        assert int(rows[0]["LOC"]) > 0

    def test_csv_export_directory(self, tmp_path: Path) -> None:
        """Test CSV export for a directory."""
        csv_file = tmp_path / "output.csv"
        test_dir = Path("src/halstead_complexity/examples")

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        result = analyze_directory(test_dir)

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, output_file=csv_file)

        assert csv_file.exists()

        # Read and verify CSV content
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should have rows for each file plus TOTAL
        assert len(rows) > 1
        assert rows[-1]["File"] == "TOTAL"

    def test_csv_export_with_tokens(self, tmp_path: Path) -> None:
        """Test CSV export with token information."""
        csv_file = tmp_path / "output_tokens.csv"
        test_file = Path("src/halstead_complexity/examples/is_odd.py")

        if not test_file.exists():
            pytest.skip("Test file not found")

        result = analyze_file(test_file)
        assert result is not None

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, show_tokens=True, output_file=csv_file)

        assert csv_file.exists()

        # Read and verify CSV content
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            rows = list(reader)

        assert len(rows) == 1

        # Should have operator columns
        op_columns = [h for h in headers if h.startswith("Op: ")]
        assert len(op_columns) > 0

        # Should have operand columns
        opnd_columns = [h for h in headers if h.startswith("Opnd: ")]
        assert len(opnd_columns) > 0

        # Verify some known operators exist
        assert any("def" in col for col in op_columns)
        assert any("if" in col for col in op_columns)

    def test_csv_export_hal_only(self, tmp_path: Path) -> None:
        """Test CSV export with only Halstead metrics."""
        csv_file = tmp_path / "output_hal.csv"
        test_file = Path("src/halstead_complexity/examples/is_odd.py")

        if not test_file.exists():
            pytest.skip("Test file not found")

        result = analyze_file(test_file)
        assert result is not None

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, hal_only=True, output_file=csv_file)

        assert csv_file.exists()

        # Read and verify CSV content
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            rows = list(reader)

        assert len(rows) == 1

        # Should NOT have raw metrics
        assert "LOC" not in headers
        assert "LLOC" not in headers

        # Should have Halstead metrics
        assert "η1 (Distinct operators)" in headers
        assert "Volume (V)" in headers

    def test_csv_export_raw_only(self, tmp_path: Path) -> None:
        """Test CSV export with only raw metrics."""
        csv_file = tmp_path / "output_raw.csv"
        test_file = Path("src/halstead_complexity/examples/is_odd.py")

        if not test_file.exists():
            pytest.skip("Test file not found")

        result = analyze_file(test_file)
        assert result is not None

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, raw_only=True, output_file=csv_file)

        assert csv_file.exists()

        # Read and verify CSV content
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            rows = list(reader)

        assert len(rows) == 1

        # Should have raw metrics
        assert "LOC" in headers
        assert "LLOC" in headers

        # Should NOT have Halstead metrics
        assert "η1 (Distinct operators)" not in headers
        assert "Volume (V)" not in headers

    def test_csv_export_tokens_directory(self, tmp_path: Path) -> None:
        """Test CSV export with tokens for directory analysis."""
        csv_file = tmp_path / "output_dir_tokens.csv"
        test_dir = Path("src/halstead_complexity/examples")

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        result = analyze_directory(test_dir)

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, show_tokens=True, output_file=csv_file)

        assert csv_file.exists()

        # Read and verify CSV content
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            rows = list(reader)

        # Should have rows for each file plus TOTAL
        assert len(rows) > 1
        assert rows[-1]["File"] == "TOTAL"

        # Should have operator and operand columns
        op_columns = [h for h in headers if h.startswith("Op: ")]
        opnd_columns = [h for h in headers if h.startswith("Opnd: ")]

        assert len(op_columns) > 0
        assert len(opnd_columns) > 0

        # Each row should have token counts (including 0 for unused tokens)
        for row in rows:
            for col in op_columns[:3]:  # Check first few operator columns
                assert col in row
                # Value should be a valid integer
                assert row[col].isdigit()

    def test_csv_export_non_csv_extension(self, tmp_path: Path) -> None:
        """Test that non-CSV files use text format."""
        txt_file = tmp_path / "output.txt"
        test_file = Path("src/halstead_complexity/examples/is_odd.py")

        if not test_file.exists():
            pytest.skip("Test file not found")

        result = analyze_file(test_file)
        assert result is not None

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, output_file=txt_file)

        assert txt_file.exists()

        # Read content - should be formatted text, not CSV
        content = txt_file.read_text(encoding="utf-8")

        # Should contain formatted output markers
        assert "Analysis Report" in content or "Metric" in content
        # Should NOT be CSV format (no comma-separated values in first line)
        first_line = content.split("\n")[0]
        assert first_line.count(",") < 5  # Text format shouldn't have many commas

    def test_csv_token_counts_accuracy(self, tmp_path: Path) -> None:
        """Test that token counts in CSV are accurate."""
        csv_file = tmp_path / "output.csv"
        test_file = Path("src/halstead_complexity/examples/is_odd.py")

        if not test_file.exists():
            pytest.skip("Test file not found")

        result = analyze_file(test_file)
        assert result is not None

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, show_tokens=True, output_file=csv_file)

        # Read CSV
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        row = rows[0]

        # Verify operator counts match expected values
        # The is_odd.py file has specific operators
        if "Op: def" in row:
            assert int(row["Op: def"]) == 1  # One function definition

        if "Op: if" in row:
            assert int(row["Op: if"]) == 1  # One if statement

        # Sum of all operator counts should equal N1
        op_columns = [h for h in row.keys() if h.startswith("Op: ")]
        total_operators = sum(int(row[col]) for col in op_columns)
        assert total_operators == int(row["N1 (Total operators)"])

        # Sum of all operand counts should equal N2
        opnd_columns = [h for h in row.keys() if h.startswith("Opnd: ")]
        total_operands = sum(int(row[col]) for col in opnd_columns)
        assert total_operands == int(row["N2 (Total operands)"])

    def test_csv_directory_total_row(self, tmp_path: Path) -> None:
        """Test that TOTAL row correctly aggregates values."""
        csv_file = tmp_path / "output.csv"
        test_dir = Path("src/halstead_complexity/examples")

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        result = analyze_directory(test_dir)

        from halstead_complexity.metrics.analysis import display_report

        display_report(result, output_file=csv_file)

        # Read CSV
        import csv

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Get TOTAL row and individual file rows
        total_row = rows[-1]
        file_rows = rows[:-1]

        assert total_row["File"] == "TOTAL"

        # LOC should be sum of all files
        total_loc = sum(int(row["LOC"]) for row in file_rows)
        assert int(total_row["LOC"]) == total_loc

        # LLOC should be sum of all files
        total_lloc = sum(int(row["LLOC"]) for row in file_rows)
        assert int(total_row["LLOC"]) == total_lloc


# ============================================================================
# Dynamic Import Tests
# ============================================================================


class TestDynamicImport:
    """Test dynamic language import functionality."""

    def test_dynamic_import_python(self, tmp_path: Path) -> None:
        """Test dynamically loading and using Python language parser."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x = 1 + 2")

        result = analyze_file(py_file)
        assert result is not None
        assert result.halstead_metrics.N1 > 0

    def test_dynamic_import_javascript(self, tmp_path: Path) -> None:
        """Test dynamically loading and using JavaScript language parser."""
        js_file = tmp_path / "test.js"
        js_file.write_text("const x = 1 + 2;")

        result = analyze_file(js_file)
        assert result is not None
        assert result.halstead_metrics.N1 > 0

    def test_language_caching(self) -> None:
        """Test that language parsers are cached."""
        language_cache.clear()
        get_language_parser("python")
        assert "python" in language_cache
        assert language_cache["python"] is not None

    def test_unsupported_language_error(self) -> None:
        """Test that requesting a non-existent language raises appropriate error."""
        with pytest.raises(LanguageNotSupportedError) as exc_info:
            get_language_parser("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "tree-sitter-nonexistent" in str(exc_info.value)
        assert "pip install" in str(exc_info.value)

    def test_multiple_languages(self, tmp_path: Path) -> None:
        """Test analyzing files in different languages."""
        from halstead_complexity.metrics.analysis import analyze_file

        py_file = tmp_path / "script.py"
        py_file.write_text("x = 1")

        js_file = tmp_path / "script.js"
        js_file.write_text("const x = 1;")

        py_result = analyze_file(py_file)
        js_result = analyze_file(js_file)

        assert py_result is not None
        assert js_result is not None
