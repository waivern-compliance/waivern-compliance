from pathlib import Path
from typing import Annotated

import typer

from waivern_analyser._plugins import load_plugins
from waivern_analyser.config import Config

app = typer.Typer()


@app.command()
def run(
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="The path to the Waivern YAML configuration file",
            file_okay=True,
            dir_okay=False,
            readable=True,
            rich_help_panel="Analysis",
        ),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="The output directory",
            file_okay=False,
            dir_okay=True,
            writable=True,
            rich_help_panel="Output",
            # Instead of showing the full path, to the
            # default output directory, show the relative
            # path
            show_default="./outputs/",
        ),
    ] = (Path.cwd() / "outputs"),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
):
    if config_path is None:
        config = Config.default()
    else:
        config = Config.from_file(config_path)

    print(config)


@app.command()
def ls_plugins():
    print("Loading plugins...")
    if plugins := load_plugins():
        print("Loaded plugins:")
        for plugin_name, plugin_class in plugins.items():
            print(f"- {plugin_name}: {plugin_class}")
    else:
        print("No plugins found")


if __name__ == "__main__":
    app()
