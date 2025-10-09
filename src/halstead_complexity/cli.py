import json
from typing import Optional

import typer

from halstead_complexity import __app_name__, __version__

from .config import ConfigError, ConfigManager

app = typer.Typer()
config_app = typer.Typer(help="Manage Halstead Complexity configuration files.")
app.add_typer(config_app, name="config")

CONFIG_OPTIONS = {
    "local": typer.Option(
        False,
        "--local",
        help="Use the configuration file in the current working directory.",
    ),
    "global": typer.Option(
        False,
        "--global",
        help="Use the global configuration file.",
    ),
}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


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
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@config_app.command("init")
def config_init(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    if not local and not global_:
        local = True

    try:
        config = ConfigManager.get_instance()
        created_path = config.init_config(local=local, global_=global_)
        level = config.get_active_config_level()

        typer.secho(
            f"✓ Created {level.value} config: ",
            fg=typer.colors.GREEN,
            bold=True,
            nl=False,
        )
        typer.secho(created_path, fg=typer.colors.GREEN)
    except ConfigError as e:
        typer.secho("✗ Config error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.secho(e, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(
            f"✗ Unexpected error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1)


@config_app.command("get")
def config_get(
    key: str,
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    try:
        config = ConfigManager.get_instance()
        level = (
            "local"
            if local
            else "global"
            if global_
            else config.get_active_config_level().value
        )
        value = config.get_setting_from_flags(key, local, global_)

        if value is None:
            typer.secho(
                f"! Key '{key}' not found in {level} config",
                bold=True,
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)

        typer.secho(
            f"✓ {str(level).capitalize()} config: ",
            fg=typer.colors.GREEN,
            bold=True,
        )
        if isinstance(value, (dict, list, tuple)):
            typer.secho(
                json.dumps(value, indent=2),
                fg=typer.colors.GREEN,
            )
        else:
            typer.secho(
                str(value),
                fg=typer.colors.GREEN,
            )
    except ConfigError as e:
        typer.secho("✗ Config error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.secho(e, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(
            f"✗ Unexpected error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str,
    value: str,
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    try:
        config = ConfigManager.get_instance()
        level = (
            "local"
            if local
            else "global"
            if global_
            else config.get_active_config_level().value
        )

        # Try to parse the value as JSON to support complex types
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat it as a string
            parsed_value = value

        config.update_setting_from_flags(key, parsed_value, local, global_)

        typer.secho(
            f"Updated '{key}' to '{parsed_value}' in {level} config",
            fg=typer.colors.GREEN,
            bold=True,
        )
    except ConfigError as e:
        typer.secho("✗ Config error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.secho(e, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(
            f"✗ Unexpected error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1)


@config_app.command("list")
def config_list(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    try:
        config = ConfigManager.get_instance()
        level = config.get_active_config_level()
        settings = config.list_settings(local, global_)

        typer.secho(
            f"✓ {level.value.capitalize()} config: ",
            fg=typer.colors.GREEN,
            bold=True,
        )
        typer.echo(json.dumps(settings, indent=2))
    except ConfigError as e:
        typer.secho("✗ Config error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.secho(e, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(
            f"✗ Unexpected error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1)


@config_app.command("path")
def config_path(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    try:
        config = ConfigManager.get_instance()
        level = (
            "local"
            if local
            else "global"
            if global_
            else config.get_active_config_level().value
        )
        path, exists, config_type = config.get_config_file_path(local, global_)

        if not exists:
            typer.secho(
                f"! No {level} config found. Use 'config init --{level}' to create one.",
                fg=typer.colors.YELLOW,
                bold=True,
                err=True,
            )
            typer.secho(
                "Current config: ",
                fg=typer.colors.YELLOW,
                bold=True,
                nl=False,
            )
            typer.secho(path, fg=typer.colors.YELLOW)
        else:
            typer.secho(
                f"✓ {config_type.capitalize()} config: ",
                fg=typer.colors.GREEN,
                bold=True,
                nl=False,
            )
            typer.secho(path, fg=typer.colors.GREEN)
    except ConfigError as e:
        typer.secho("✗ Config error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.secho(e, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(
            f"✗ Unexpected error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1)


# @app.command()
# def analyze(
#     path: str = typer.Argument(..., help="Path to file or directory to analyze"),
#     hal: bool = typer.Option(False, "--hal", help="Only show Halstead metrics"),
#     raw: bool = typer.Option(False, "--raw", help="Only show raw metrics"),
#     tokens: bool = typer.Option(False, "--tokens", help="Show operators and operands"),
#     silence: bool = typer.Option(
#         False, "--silence", help="Only output success message"
#     ),
#     output: Optional[str] = typer.Option(
#         None, "--output", "-o", help="Write report to file"
#     ),
#     config_path: Optional[str] = typer.Option(
#         None, "--config", "-c", help="Path to config file"
#     ),
# ) -> None:
#     """Analyze source code file or directory for complexity metrics."""

#     # Load configuration
#     if config_path:
#         # Load custom config from specified path
#         config_file = Path(config_path)
#         if not config_file.exists():
#             typer.secho(
#                 f"Error: Configuration file not found: {config_path}",
#                 fg=typer.colors.RED,
#                 err=True,
#             )
#             raise typer.Exit(1)

#         # For now, use default config (custom config loading can be enhanced later)
#         config = ConfZConfig()
#     else:
#         config = ConfZConfig()

#     # Analyze the path
#     target_path = Path(path)
#     if not target_path.exists():
#         typer.secho(
#             f"Error: Path not found: {path}",
#             fg=typer.colors.RED,
#             err=True,
#         )
#         raise typer.Exit(1)

#     result = analyze_path(target_path, config)

#     if result is None:
#         typer.secho(
#             f"Error: Unable to analyze path: {path}",
#             fg=typer.colors.RED,
#             err=True,
#         )
#         raise typer.Exit(1)

#     # Output report
#     if output:
#         # Write Rich table report to file
#         output_file = Path(output)
#         try:
#             display_report(result, hal, raw, tokens, output_file=output_file)
#             if silence:
#                 typer.secho(
#                     f"Analysis completed successfully. Report written to: {output}",
#                     fg=typer.colors.GREEN,
#                 )
#             else:
#                 typer.secho(
#                     f"Report written to: {output}",
#                     fg=typer.colors.GREEN,
#                 )
#         except Exception as e:
#             typer.secho(
#                 f"Error writing to file: {e}",
#                 fg=typer.colors.RED,
#                 err=True,
#             )
#             raise typer.Exit(1)
#     else:
#         # If no output file, silence mode just shows success message
#         if silence:
#             typer.secho("Analysis completed successfully.", fg=typer.colors.GREEN)
#         else:
#             # Display Rich tables to console
#             display_report(result, hal, raw, tokens)
