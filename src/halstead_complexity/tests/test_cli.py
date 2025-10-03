from pathlib import Path
from typing import Any, Dict

from typer.testing import CliRunner

from halstead_complexity import __app_name__, __version__, cli, config

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert f"{__app_name__} v{__version__}\n" in result.stdout


_TEST_CONFIG: Dict[str, Any] = {
    "default_language": "python",
    "languages": {
        "python": {
            "comment": ["#"],
            "extensions": [".py"],
            "excluded": [],
            "keywords": [
                "and",
                "as",
                "assert",
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
                "if",
                "import",
                "in",
                "is",
                "not",
                "or",
                "pass",
                "raise",
                "return",
                "try",
                "while",
                "with",
                "yield",
            ],
            "symbols": [
                "(",
                ")",
                ":",
                ",",
                "+",
                "-",
                "*",
                "/",
                "=",
                ".",
                "%",
            ],
            "operand_node_types": [
                "identifier",
                "string",
                "integer",
                "float",
                "number",
            ],
            "statement_node_types": [
                "expression_statement",
                "assignment",
                "return_statement",
                "if_statement",
                "else_clause",
                "for_statement",
                "while_statement",
                "function_definition",
            ],
            "multiline_delimiters": [['"""', '"""'], ["'''", "'''"]],
        }
    },
}


def _configure_global(tmp_path: Path) -> None:
    config.CONFIG_DIR_PATH = tmp_path


def _write_config(path: Path) -> Path:
    config.write_config(path, _TEST_CONFIG)
    return path


def test_analyze_single_file_outputs_summary(tmp_path: Path) -> None:
    _configure_global(tmp_path)
    config_path = _write_config(tmp_path / "config.toml")
    source_path = tmp_path / "sample.py"
    source_path.write_text("def foo():\n    return 42\n", encoding="utf-8")

    result = runner.invoke(
        cli.app,
        [
            "analyze",
            str(source_path),
            "--config",
            str(config_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Summary" in result.stdout
    assert "LOC:" in result.stdout
    assert "Files" not in result.stdout


def test_analyze_writes_output_file(tmp_path: Path) -> None:
    _configure_global(tmp_path)
    config_path = _write_config(tmp_path / "config.toml")
    source_path = tmp_path / "sample.py"
    source_path.write_text("value = 3\n", encoding="utf-8")
    output_path = tmp_path / "report.txt"

    result = runner.invoke(
        cli.app,
        [
            "analyze",
            str(source_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Analysis written to" in result.stdout
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Summary" in content
    assert "Files" not in content


def test_analyze_with_silence_suppresses_stdout(tmp_path: Path) -> None:
    _configure_global(tmp_path)
    config_path = _write_config(tmp_path / "config.toml")
    source_path = tmp_path / "sample.py"
    source_path.write_text("value = 7\n", encoding="utf-8")
    output_path = tmp_path / "report.txt"

    result = runner.invoke(
        cli.app,
        [
            "analyze",
            str(source_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--silence",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Summary" in content
    assert "Files" not in content


def test_analyze_with_invalid_default_language_requires_override(
    tmp_path: Path,
) -> None:
    _configure_global(tmp_path)
    config_data = config.default_config()
    config_data["default_language"] = "javascript"
    config_path = tmp_path / "config.toml"
    config.write_config(config_path, config_data)
    source_path = tmp_path / "sample.py"
    source_path.write_text("value = 1\n", encoding="utf-8")

    failure = runner.invoke(
        cli.app,
        [
            "analyze",
            str(source_path),
            "--config",
            str(config_path),
        ],
        catch_exceptions=False,
    )
    assert failure.exit_code != 0
    assert "Default language 'javascript'" in failure.stdout

    success = runner.invoke(
        cli.app,
        [
            "analyze",
            str(source_path),
            "--config",
            str(config_path),
            "--set",
            "default_language=python",
        ],
        catch_exceptions=False,
    )
    assert success.exit_code == 0


def test_config_set_and_get(tmp_path: Path) -> None:
    _configure_global(tmp_path)
    target = config.global_config_path()
    config.write_config(target, _TEST_CONFIG)

    result_set = runner.invoke(
        cli.app,
        [
            "config",
            "set",
            "default_language",
            "javascript",
            "--config",
            str(target),
        ],
        catch_exceptions=False,
    )
    assert result_set.exit_code == 0

    result_get = runner.invoke(
        cli.app,
        [
            "config",
            "get",
            "default_language",
            "--config",
            str(target),
        ],
        catch_exceptions=False,
    )
    assert result_get.exit_code == 0
    assert result_get.stdout.strip() == "javascript"


def test_analyze_creates_default_config_when_missing(tmp_path: Path) -> None:
    _configure_global(tmp_path)
    with runner.isolated_filesystem():
        source_path = Path("script.py")
        source_path.write_text("value = 5\n", encoding="utf-8")
        result = runner.invoke(
            cli.app,
            [
                "analyze",
                str(source_path),
                "--silence",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Created default configuration" in result.stdout
    assert config.global_config_path().exists()
