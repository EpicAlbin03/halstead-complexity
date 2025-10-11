# halstead-complexity

A command-line tool for measuring Halstead complexity metrics in source code. Supports Python and JavaScript out of the box, with the ability to add support for any language via tree-sitter grammars.

## Quick Start

```bash
# Install the tool
pip install halstead-complexity[python]

# Initialize a config file
hc config init

# Analyze a file or directory
hc analyze <path>

# Show each token counted
hc analyze <path> --tokens

# Other options
hc analyze <path> --hal # Only Halstead metrics
hc analyze <path> --raw # Only raw metrics
hc analyze <path> --silence # Only output success message
hc analyze <path> -o report.csv # Write report to file (txt or csv)
hc analyze --help # Show all options
```

## Installation

```bash
pip install halstead-complexity
```

or

```bash
uv add halstead-complexity
```

### Language Support

The tool does not come with any language dependencies by default. To add support for other languages, you'll need to install the corresponding tree-sitter grammar packages (see [Adding Support for More Languages](https://github.com/EpicAlbin03/halstead-complexity?tab=readme-ov-file#adding-support-for-more-languages) below).

However, the default configuration includes support for Python and JavaScript. If that is all you need, you can simply install the package with the optional dependencies (python, javascript, all):

```bash
pip install halstead-complexity[python]
```

## Metrics

### Raw Metrics

- **LOC**: Total number of lines of code
- **LLOC**: Number of logical lines of code (each contains exactly one statement)
- **SLOC**: Number of source lines of code
- **Comments**: Number of comment lines
- **Multi-lines**: Number of lines representing multi-line delimiters
- **Blank lines**: Number of blank or whitespace-only lines

The equation `SLOC` + `Multi-lines` + `Comments` + `Blank lines` = `LOC` should always hold.

### Halstead Metrics

- **η₁**: Total number of distinct operators
- **η₂**: Total number of distinct operands
- **N₁**: Total number of operators
- **N₂**: Total number of operands
- **Vocabulary:** η = η₁ + η₂
- **Length:** N = N₁ + N₂
- **Volume:** V = N × log₂(η)
- **Difficulty:** D = (η₁ / 2) × (N₂ / η₂)
- **Effort:** E = D × V
- **Time:** T = E / 18 seconds
- **Delivered Bugs:** B = V / 3000

## Configuration

The tool uses a hierarchical configuration system with three levels of precedence:

1. **Default config** - Built-in configuration (lowest precedence)
2. **Global config** - User-wide configuration at `~/.config/halstead-complexity/config.json`
3. **Local config** - Project-specific configuration at `./hc_config.json` (highest precedence)

### Creating a Configuration File

Initialize a new configuration file:

```bash
# Create a local config in the current directory
hc config init --local

# Create a global config for all projects
hc config init --global
```

### Configuration Structure

The configuration file is a JSON file with the following structure (see [default config](https://github.com/EpicAlbin03/halstead-complexity/blob/main/src/halstead_complexity/default_config.json)):

```json
{
  "default_language": "python",
  "braces_single_operator": false,
  "template_literal_single_operand": false,
  "languages": {
    "python": {
      "comment": ["#"],
      "extensions": [".py"],
      "excluded": ["__pycache__", ".pytest_cache", ".venv"],
      "statement_types": [...],
      "operand_types": [...],
      "keywords": [...],
      "symbols": [...],
      "multi_word_operators": ["is not", "not in"],
      "multi_line_delimiters": [
        {"start": "\"\"\"", "end": "\"\"\""},
        {"start": "'''", "end": "'''"}
      ]
    }
  }
}
```

### Configuration Fields

- **`default_language`**: The default language to use when analyzing files. Used for directory analysis. Single file analysis will use the file extension to determine the language. Must be one of the languages defined in `languages`.
- **`braces_single_operator`**: Whether to treat opening/closing braces as single operators (default: `false`)

  true: `{}` is a single operator

  false: `{` and `}` are separate operators

- **`template_literal_single_operand`**: Whether to treat template literals as single operands (default: `false`)

  true: `f"{n} is odd."` is a single operand

  false: `" is odd."` is an operand and `{` `}` are operators

- **`languages`**: Language-specific configurations

Each language configuration includes:

- **`comment`**: Single-line comment syntax (e.g., `["#"]` for Python, `["//"]` for JavaScript)
- **`extensions`**: File extensions for this language (e.g., `[".py"]`, `[".js", ".mjs"]`)
- **`excluded`**: Directories to exclude when analyzing (e.g., `["__pycache__", "node_modules"]`)
- **`statement_types`**: Tree-sitter node types that represent statements
- **`operand_types`**: Tree-sitter node types that represent operands (identifiers, literals, etc.)
- **`keywords`**: Language keywords that are considered operators
- **`symbols`**: Operator symbols (e.g., `+`, `-`, `==`, `!=`)
- **`multi_word_operators`**: Multi-word operators (e.g., `"is not"`, `"not in"`)
- **`multi_line_delimiters`**: Multi-line comment/string delimiters

## Adding Support for More Languages

The tool uses [tree-sitter](https://tree-sitter.github.io/tree-sitter/) for parsing source code, which means you can add support for any language that has a tree-sitter grammar.

### Step 1: Install the Tree-Sitter Grammar

First, install the Python bindings for the tree-sitter grammar. Most languages have packages available on PyPI with the naming convention `tree-sitter-{language}`.

```bash
# Example: Adding Rust support
pip install tree-sitter-rust
```

Find tree-sitter grammars by:

- Searching for `tree-sitter-{language}` on [PyPI](https://pypi.org/search/?q=tree-sitter-rust)
- Checking the [list of parsers](https://github.com/tree-sitter/tree-sitter/wiki/List-of-parsers) (all these may not exists on PyPI)

### Step 2: Configure the Language

Add a configuration for the new language to your config file:

```bash
# Initialize a config file if you haven't already
hc config init
```

Edit the config file (e.g., `hc_config.json`) and add your language configuration:

- See the [default config](https://github.com/EpicAlbin03/halstead-complexity/blob/main/src/halstead_complexity/default_config.json) for an example.
- Check the grammar definition in the tree-sitter repository (e.g., `tree-sitter-rust/grammar.js`)

## CLI Reference

**Usage**:

```console
$ hc [OPTIONS] COMMAND [ARGS]...
```

**Options**:

- `-v, --version`: Show the application&#x27;s version and exit.
- `--install-completion`: Install completion for the current shell.
- `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
- `--help`: Show this message and exit.

**Commands**:

- `analyze`: Analyze source code file or directory for complexity metrics.
- `config`: Manage Halstead Complexity config files.

## `hc analyze`

Analyze source code file or directory for complexity metrics.

**Usage**:

```console
$ hc analyze [OPTIONS] PATH
```

**Arguments**:

- `PATH`: Path to a file or directory to analyze [required]

**Options**:

- `--hal`: Only show Halstead metrics
- `--raw`: Only show raw metrics
- `--tokens`: Show operators and operands
- `--silence`: Only output success message
- `-o, --output TEXT`: Write report to file
- `-c, --config TEXT`: Path to config file
- `--help`: Show this message and exit.

## `hc config`

Manage Halstead Complexity config files.

**Usage**:

```console
$ hc config [OPTIONS] COMMAND [ARGS]...
```

**Options**:

- `--help`: Show this message and exit.

**Commands**:

- `init`: Initialize a new config file.
- `get`: Get a config value.
- `set`: Set a config value.
- `list`: List all config values.
- `path`: Show the path to the config file.

### `hc config init`

Initialize a new config file.

**Usage**:

```console
$ hc config init [OPTIONS]
```

**Options**:

- `--local`: Use the config file in the current working directory.
- `--global`: Use the global config file.
- `--help`: Show this message and exit.

### `hc config get`

Get a config value.

**Usage**:

```console
$ hc config get [OPTIONS] KEY
```

**Arguments**:

- `KEY`: [required]

**Options**:

- `--local`: Use the config file in the current working directory.
- `--global`: Use the global config file.
- `--help`: Show this message and exit.

### `hc config set`

Set a config value.

**Usage**:

```console
$ hc config set [OPTIONS] KEY VALUE
```

**Arguments**:

- `KEY`: [required]
- `VALUE`: [required]

**Options**:

- `--local`: Use the config file in the current working directory.
- `--global`: Use the global config file.
- `--help`: Show this message and exit.

### `hc config list`

List all config values.

**Usage**:

```console
$ hc config list [OPTIONS]
```

**Options**:

- `--local`: Use the config file in the current working directory.
- `--global`: Use the global config file.
- `--help`: Show this message and exit.

### `hc config path`

Show the path to the config file.

**Usage**:

```console
$ hc config path [OPTIONS]
```

**Options**:

- `--local`: Use the config file in the current working directory.
- `--global`: Use the global config file.
- `--help`: Show this message and exit.

## Contributing

- More default language support is welcome. Please add the configuration to the [default config](https://github.com/EpicAlbin03/halstead-complexity/blob/main/src/halstead_complexity/default_config.json) and include the optional dependency in the [pyproject.toml](https://github.com/EpicAlbin03/halstead-complexity/blob/main/pyproject.toml).
- For now the project is focused on Halstead complexity. But it could potentially be expanded to include other metrics such as cyclomatic complexity and maintainability index.

## Credits

This project was inspired by:

- [Radon](https://github.com/rubik/radon)
- [HalsteadComplexity](https://github.com/robjoh01/HalsteadComplexity)

## License

Licensed under the [MIT license](https://github.com/EpicAlbin03/halstead-complexity/blob/main/LICENSE)
