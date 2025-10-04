import json
from typing import Optional

import typer

from halstead_complexity import __app_name__, __version__

from .config import Config, ConfZConfig, get_config_source

app = typer.Typer()
config_app = typer.Typer(help="Manage Halstead Complexity configuration files.")
app.add_typer(config_app, name="config")

CONFIG_OPTIONS = {
    "local": typer.Option(
        True,
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
    """Callback to display the application version."""
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
    """Version command for the main CLI. If no subcommand is provided, show help."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@config_app.command("init")
def config_init(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    """Initialize a new configuration file with default values."""
    source = get_config_source(local, global_)
    config = Config(source=source)

    try:
        config.init()
        typer.secho(
            f"Configuration file created at: {config.source_path}",
            fg=typer.colors.GREEN,
        )
    except FileExistsError:
        typer.secho(
            f"Error: Configuration file already exists at {config.source_path}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@config_app.command("get")
def config_get(
    key: str,
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    """Get a configuration value by key (use dot notation for nested keys)."""
    source = get_config_source(local, global_)
    config = Config(source=source)

    try:
        value = config.get(key)
        if value is None:
            typer.secho(
                f"Key '{key}' not found in configuration",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)

        # Format output based on type
        if isinstance(value, (dict, list, tuple)):
            typer.echo(json.dumps(value, indent=2))
        else:
            typer.echo(str(value))
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str,
    value: str,
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    """Set a configuration value (use dot notation for nested keys)."""
    source = get_config_source(local, global_)
    config = Config(source=source)

    try:
        # Try to parse the value as JSON to support complex types
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat it as a string
            parsed_value = value

        config.set(key, parsed_value)
        typer.secho(
            f"Successfully set '{key}' to '{parsed_value}' in {config.source_path}",
            fg=typer.colors.GREEN,
        )
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@config_app.command("list")
def config_list(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    """List all configuration values from the current source."""
    source = get_config_source(local, global_)
    config = Config(source=source)

    try:
        config_data = config.list()
        typer.echo(json.dumps(config_data, indent=2))
    except FileNotFoundError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@config_app.command("path")
def config_path(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    """Show the path to the configuration file."""
    source = get_config_source(local, global_)
    config = Config(source=source)

    path = config.source_path
    if path:
        typer.echo(str(path))
    else:
        typer.secho(
            "No path available (using default configuration)",
            fg=typer.colors.YELLOW,
        )


@app.command()
def analyze() -> None:
    print(ConfZConfig().default_language)
