# Halstead Complexity Analyzer

A command-line tool for analyzing source code complexity using Halstead metrics and raw code metrics. Supports multiple programming languages through tree-sitter.

## Features

- **Halstead Complexity Metrics**: Calculate comprehensive Halstead metrics including vocabulary, length, volume, difficulty, effort, time, and estimated bugs.
- **Raw Code Metrics**: Collect basic code metrics like LOC, LLOC, SLOC, comments, multi-line strings, and blank lines.
- **Multi-language Support**: Currently supports Python and JavaScript with extensible configuration for additional languages.
- **Flexible Analysis**: Analyze individual files or entire directories recursively.
- **Customizable Output**: Filter metrics (raw only, Halstead only), save to files, or run in silent mode.
- **Configurable**: Customize analysis behavior through configuration files.

## Installation

```bash
# Using uv (recommended)
uv pip install halstead-complexity

# Or clone and install from source
git clone <repository-url>
cd halstead-complexity
uv sync
```

## Usage

### Basic Analysis

Analyze a single file:

```bash
uv run hc analyze path/to/file.py
```

Analyze a directory recursively:

```bash
uv run hc analyze path/to/directory/
```

### Command Options

- `--hal`: Show only Halstead metrics
- `--raw`: Show only raw metrics
- `--silence`: Only output a success message
- `--output <file>` or `-o <file>`: Write report to a file
- `--config <file>` or `-c <file>`: Use a custom configuration file

### Examples

Show only Halstead metrics:

```bash
uv run hc analyze file.py --hal
```

Show only raw metrics:

```bash
uv run hc analyze file.py --raw
```

Save report to a file:

```bash
uv run hc analyze file.py --output report.txt
```

Silent analysis (useful for CI/CD):

```bash
uv run hc analyze src/ --silence
```

## Metrics Explained

### Raw Metrics

- **LOC (Lines of Code)**: Total number of lines of code (excludes blank lines)
- **LLOC (Logical Lines of Code)**: Number of logical lines of code (each contains exactly one statement)
- **SLOC (Source Lines of Code)**: Number of source lines (excludes blanks, comments, and multi-line strings)
- **Comments**: Number of comment lines
- **Multi**: Number of lines in multi-line strings (e.g., docstrings in Python)
- **Blanks**: Number of blank or whitespace-only lines

### Halstead Metrics

- **η1**: Number of distinct operators
- **η2**: Number of distinct operands
- **N1**: Total number of operators
- **N2**: Total number of operands
- **Vocabulary (η)**: η1 + η2
- **Length (N)**: N1 + N2
- **Calculated Length (N̂)**: η1 × log₂(η1) + η2 × log₂(η2)
- **Volume (V)**: N × log₂(η)
- **Difficulty (D)**: (η1/2) × (N2/η2)
- **Effort (E)**: D × V
- **Time (T)**: E/18 seconds (estimated time to program)
- **Bugs (B)**: V/3000 (estimated number of delivered bugs)

## Configuration

The tool uses a hierarchical configuration system:

1. Default configuration (built-in)
2. Global configuration: `~/.config/halstead-complexity/config.json`
3. Local configuration: `./hc_config.json` (in current directory)

### Managing Configuration

Initialize a new config file:

```bash
uv run hc config init
```

View configuration:

```bash
uv run hc config list
```

Get a specific value:

```bash
uv run hc config get default_language
```

Set a value:

```bash
uv run hc config set default_language python
```

### Configuration Options

Key configuration options include:

- `default_language`: Default programming language
- `braces_single_operator`: Whether braces/brackets count as one or two operators
- `languages.<lang>.comment`: Comment symbols for the language
- `languages.<lang>.extensions`: File extensions for the language
- `languages.<lang>.excluded`: Paths to exclude from analysis
- `languages.<lang>.keywords`: Language keywords (operators)
- `languages.<lang>.symbols`: Language symbols (operators)
- `languages.<lang>.multi_word_operators`: Multi-word operators (e.g., "is not", "not in")
- `languages.<lang>.multi_line_delimiters`: Delimiters for multi-line strings/comments

## Example Output

```
Analysis Report for: examples/is_odd.py
================================================================================

Raw Metrics:
----------------------------------------
  LOC (Lines of Code):              10
  LLOC (Logical Lines of Code):     8
  SLOC (Source Lines of Code):      9
  Comments:                          1
  Multi-line strings:                0
  Blank lines:                       3

Halstead Metrics:
----------------------------------------
  η1 (Distinct operators):           21
  η2 (Distinct operands):            11
  N1 (Total operators):              35
  N2 (Total operands):               17
  Vocabulary (η):                    32
  Length (N):                        52
  Calculated Length (N̂):             130.29
  Volume (V):                        260.00
  Difficulty (D):                    16.23
  Effort (E):                        4219.09
  Time (T):                          234.39 seconds
  Bugs (B):                          0.0867
```

## Supported Languages

Currently supported:

- Python (.py)
- JavaScript (.js, .mjs, .cjs)

Additional languages can be added by extending the configuration with appropriate tree-sitter grammar support.

## Development

Run tests:

```bash
uv run pytest
```

## License

MIT

## Credits

Built with:

- [tree-sitter](https://tree-sitter.github.io/) - Incremental parsing system
- [typer](https://typer.tiangolo.com/) - CLI framework
- [confz](https://github.com/Zuehlke/ConfZ) - Configuration management
