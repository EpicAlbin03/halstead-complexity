from typing import Optional

import typer

from halstead_complexity import __app_name__, __version__

from .config import Config

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
    pass


@config_app.command("get")
def config_get(
    key: str,
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    pass


@config_app.command("set")
def config_set(
    key: str,
    value: str,
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    pass


@config_app.command("list")
def config_list(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    pass


@config_app.command("path")
def config_path(
    local: bool = CONFIG_OPTIONS["local"],
    global_: bool = CONFIG_OPTIONS["global"],
) -> None:
    print(local)


@app.command()
def analyze() -> None:
    print(Config().default_language)
