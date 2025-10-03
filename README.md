## Halstead Complexity CLI

A command line tool for computing Halstead complexity metrics and raw code metrics
across single files or entire directory trees using [Tree-sitter](https://tree-sitter.github.io/tree-sitter/).
The tool reads language-specific operator and operand definitions from a JSON
configuration file and produces aggregated as well as per-file reports.

### Installation

```bash
pip install -e .
```

The package depends on `tree-sitter` and on language-specific bindings such as
`tree-sitter-python`. Install the bindings for every language you plan to
analyze, for example:

```bash
pip install tree-sitter-python
```

### Quick start

1. Create the default configuration (stored in your Typer app directory):

   ```bash
   hc init
   ```

2. Edit the generated `config.json` to customise language definitions.
3. Run the analysis:

   ```bash
   hc analyze path/to/project
   ```

The command prints a textual report by default. Use `--output report.txt` to
write the report to a file. Specify `--language` to force a language defined in
the configuration and `--config` to point at an alternate configuration file.

### Report contents

The report contains a global summary followed by per-file details. Halstead
metrics include:

- $\eta_1$ – distinct operators
- $\eta_2$ – distinct operands
- $N_1$ – total operators
- $N_2$ – total operands
- Vocabulary $\eta = \eta_1 + \eta_2$
- Length $N = N_1 + N_2$
- Calculated length $\hat{N} = \eta_1 \log_2 \eta_1 + \eta_2 \log_2 \eta_2$
- Volume $V = N \log_2 \eta$
- Difficulty $D = (\eta_1 / 2) * (N_2 / \eta_2)$
- Effort $E = D * V$
- Time required $T = E / 18$ seconds
- Delivered bugs $B = V / 3000$

Raw metrics include Lines of Code (LOC), Logical Lines of Code (LLOC), Source
Lines of Code (SLOC), the number of comment lines, multi-line string lines,
blank lines, and single-line comment counts. The invariant
$\text{SLOC} + \text{Multi} + \text{Single comments} + \text{Blank} = \text{LOC}$
is preserved.

### Configuration

Language-specific behaviour is defined in `config.json`. Every language entry
supplies keywords and symbols (treated as operators), operand node types,
statement node types, and optional parser module overrides. Example:

```json
{
  "default_language": "python",
  "languages": {
    "python": {
      "comment": ["#"],
      "extensions": [".py"],
      "excluded": ["__pycache__", ".pytest_cache"],
      "keywords": [
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield"
      ],
      "symbols": [
        "(",
        ")",
        "[",
        "]",
        ":",
        ",",
        ";",
        "+",
        "-",
        "*",
        "/",
        "|",
        "&",
        "<",
        ">",
        "=",
        ".",
        "%",
        "{",
        "}",
        "==",
        "!=",
        "<=",
        ">=",
        "~",
        "^",
        "<<",
        ">>",
        "**",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "&=",
        "|=",
        "^=",
        "<<=",
        ">>=",
        "**=",
        "//",
        "//=",
        "@",
        "@=",
        "->",
        "...",
        ":=",
        "!"
      ],
      "operand_node_types": ["identifier", "string", "integer", "float", "number"],
      "statement_node_types": [
        "expression_statement",
        "assignment",
        "return_statement",
        "if_statement",
        "for_statement",
        "while_statement",
        "function_definition",
        "class_definition",
        "import_statement",
        "import_from_statement",
        "with_statement",
        "try_statement",
        "match_statement"
      ],
      "multiline_delimiters": [
        ["\"\"\"", "\"\"\""],
        ["'''", "'''"]
      ]
    }
  }
}
```

- `comment`: prefixes for single-line comments.
- `excluded`: directory or file names to ignore during traversal.
- `keywords` and `symbols`: combined to form the operator set.
- `operand_node_types`: Tree-sitter node types considered operands.
- `statement_node_types`: node types counted for logical lines of code.
- `multiline_delimiters`: pairs marking multi-line string regions.
- `parser_module` (optional): explicit module name (e.g. `tree_sitter_python`).

When analysing directories the tool respects the exclusion lists for every
language. If no file extension match is found, the default language is used (if
configured).

### Development

Run the unit tests after making changes:

```bash
pytest
```

Ensure the required Tree-sitter language packages are installed before running
the test suite.
