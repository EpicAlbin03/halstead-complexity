import json
from pathlib import Path
from typing import Any, Optional

import typer

from halstead_complexity import __app_name__, __version__

from .config import ConfigError, ConfigManager, settings
from .metrics.analysis import LanguageNotSupportedError, analyze_path, display_report

app = typer.Typer()
config_app = typer.Typer(help="Manage Halstead Complexity config files.")
app.add_typer(config_app, name="config")

# Reusable option definitions
LOCAL_OPTION = typer.Option(
    False,
    "--local",
    help="Use the config file in the current working directory.",
)
GLOBAL_OPTION = typer.Option(
    False,
    "--global",
    help="Use the global config file.",
)


def _version_callback(value: bool) -> None:
    """Handle version flag."""
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


def _handle_error(error: Exception) -> None:
    """Centralized error handling for all commands."""
    error_prefix = "✗"

    if isinstance(error, ConfigError):
        typer.secho(
            f"{error_prefix} Config error: ", fg=typer.colors.RED, bold=True, nl=False
        )
        typer.secho(str(error), fg=typer.colors.RED, err=True)
    elif isinstance(error, LanguageNotSupportedError):
        typer.secho(
            f"{error_prefix} Language not supported: ",
            fg=typer.colors.RED,
            bold=True,
            nl=False,
        )
        typer.secho(str(error), fg=typer.colors.RED, err=True)
    elif isinstance(error, FileNotFoundError):
        typer.secho(
            f"{error_prefix} File error: ", fg=typer.colors.RED, bold=True, nl=False
        )
        typer.secho(str(error), fg=typer.colors.RED, err=True)
    elif isinstance(error, ValueError):
        typer.secho(
            f"{error_prefix} Analysis error: ", fg=typer.colors.RED, bold=True, nl=False
        )
        typer.secho(str(error), fg=typer.colors.RED, err=True)
    elif isinstance(error, IOError):
        typer.secho(
            f"{error_prefix} IO error: ", fg=typer.colors.RED, bold=True, nl=False
        )
        typer.secho(str(error), fg=typer.colors.RED, err=True)
    else:
        typer.secho(
            f"{error_prefix} Unexpected error: {error}",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
    raise typer.Exit(1)


def _success_message(message: str, value: Optional[str] = None) -> None:
    """Display a success message with optional value."""
    typer.secho(f"✓ {message}", fg=typer.colors.GREEN, bold=True, nl=not value)
    if value:
        typer.secho(value, fg=typer.colors.GREEN)


def _warning_message(
    message: str, value: Optional[str] = None, err: bool = False
) -> None:
    """Display a warning message with optional value."""
    typer.secho(
        f"! {message}", fg=typer.colors.YELLOW, bold=True, nl=not value, err=err
    )
    if value:
        typer.secho(value, fg=typer.colors.YELLOW)


def _get_level_name(local: bool, global_: bool) -> str:
    """Get the level name based on flags."""
    if local:
        return "local"
    if global_:
        return "global"
    return settings.active_config_level.value


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, indent=2)
    return str(value)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Halstead Complexity CLI tool."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@config_app.command("init")
def config_init(
    local: bool = LOCAL_OPTION,
    global_: bool = GLOBAL_OPTION,
) -> None:
    """Initialize a new config file."""
    if local and global_:
        raise typer.BadParameter("Cannot specify both --local and --global")

    try:
        if not local and not global_:
            local = True

        created_path = settings.init_config(local=local, global_=global_)
        level = _get_level_name(local, global_)

        _success_message(f"Created {level} config: ", created_path)
    except Exception as e:
        _handle_error(e)


@config_app.command("get")
def config_get(
    key: str,
    local: bool = LOCAL_OPTION,
    global_: bool = GLOBAL_OPTION,
) -> None:
    """Get a config value."""
    if local and global_:
        raise typer.BadParameter("Cannot specify both --local and --global")

    try:
        if not local and not global_:
            try:
                value = settings.get_setting(key)
                source_level = settings.find_setting_source(key)

                active_level = settings.active_config_level.value
                active_value = settings.get_setting_from_flags(
                    key,
                    local=(active_level == "local"),
                    global_=(active_level == "global"),
                )
                if active_value is None and source_level != active_level:
                    _warning_message(f"Key '{key}' not found in {active_level} config")

                _success_message(f"{source_level.capitalize()} config:")
                typer.secho(_format_value(value), fg=typer.colors.GREEN)
            except ConfigError as e:
                _handle_error(e)
        else:
            level = _get_level_name(local, global_)
            value = settings.get_setting_from_flags(key, local, global_)

            if value is None:
                _warning_message(f"Key '{key}' not found in {level} config")

                try:
                    merged_value = settings.get_setting(key)
                    source_level = settings.find_setting_source(key)
                    _success_message(f"{source_level.capitalize()} config:")
                    typer.secho(_format_value(merged_value), fg=typer.colors.GREEN)
                except ConfigError:
                    raise typer.Exit(1)
            else:
                _success_message(f"{level.capitalize()} config:")
                typer.secho(_format_value(value), fg=typer.colors.GREEN)

    except Exception as e:
        _handle_error(e)


@config_app.command("set")
def config_set(
    key: str,
    value: str,
    local: bool = LOCAL_OPTION,
    global_: bool = GLOBAL_OPTION,
) -> None:
    """Set a config value."""
    if local and global_:
        raise typer.BadParameter("Cannot specify both --local and --global")

    try:
        level = _get_level_name(local, global_)

        # Try to parse as JSON for complex types, fall back to string
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value

        settings.update_setting_from_flags(key, parsed_value, local, global_)

        display_value = (
            json.dumps(parsed_value)
            if not isinstance(parsed_value, str)
            else parsed_value
        )
        _success_message(f"Updated '{key}' to '{display_value}' in {level} config")
    except Exception as e:
        _handle_error(e)


@config_app.command("list")
def config_list(
    local: bool = LOCAL_OPTION,
    global_: bool = GLOBAL_OPTION,
) -> None:
    """List all config values."""
    if local and global_:
        raise typer.BadParameter("Cannot specify both --local and --global")

    try:
        level = _get_level_name(local, global_)
        config_settings = settings.list_settings(local, global_)

        _success_message(f"{level.capitalize()} config:")
        typer.echo(json.dumps(config_settings, indent=2))
    except Exception as e:
        _handle_error(e)


@config_app.command("path")
def config_path(
    local: bool = LOCAL_OPTION,
    global_: bool = GLOBAL_OPTION,
) -> None:
    """Show the path to the config file."""
    if local and global_:
        raise typer.BadParameter("Cannot specify both --local and --global")

    try:
        level = _get_level_name(local, global_)
        path, exists, config_type = settings.get_config_file_path(local, global_)

        if not exists:
            _warning_message(
                f"No {level} config found. Use 'config init --{level}' to create one.",
                err=True,
            )
            _warning_message("Current config: ", path)
        else:
            _success_message(f"{config_type.capitalize()} config: ", path)
    except Exception as e:
        _handle_error(e)


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to a file or directory to analyze"),
    hal: bool = typer.Option(False, "--hal", help="Only show Halstead metrics"),
    raw: bool = typer.Option(False, "--raw", help="Only show raw metrics"),
    tokens: bool = typer.Option(False, "--tokens", help="Show operators and operands"),
    silence: bool = typer.Option(
        False, "--silence", help="Only output success message"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write report to file"
    ),
    config_path: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Analyze source code file or directory for complexity metrics."""
    if hal and raw:
        raise typer.BadParameter("Cannot specify both --hal and --raw")

    try:
        if config_path:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            try:
                temp_settings = ConfigManager(local_file=str(config_file))
                config_settings = temp_settings.get_all_settings()
            except Exception as e:
                raise ConfigError(
                    f"Failed to load config file: {config_path}",
                    path=str(config_file),
                    original_error=e,
                )
        else:
            config_settings = settings.get_all_settings()

        target_path = Path(path)
        result = analyze_path(target_path, config_settings)

        if output:
            output_file = Path(output)
            try:
                display_report(result, hal, raw, tokens, output_file=output_file)
                if silence:
                    _success_message("Report written to: ", output)
                else:
                    _success_message("Report written to: ", output)
            except Exception as e:
                raise IOError(f"Error writing to file: {output}") from e
        else:
            if silence:
                _success_message("Analysis completed successfully.")
            else:
                display_report(result, hal, raw, tokens)
    except Exception as e:
        _handle_error(e)
