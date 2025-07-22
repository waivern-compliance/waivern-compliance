from pathlib import Path
from typing import Annotated

import typer

from waivern_analyser._plugins import load_plugins
from waivern_analyser.analyser import Analyser
from waivern_analyser.config.analyser_config import AnalyserConfig

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
        # FIXME: what to do in the default case?
        # config = AnalyserConfig.default()
        config = AnalyserConfig.from_yaml_file(Path(__file__).parent / "waivern.yaml")
    else:
        config = AnalyserConfig.from_yaml_file(config_path)

    analyser = Analyser.from_config(config)
    report_items = list(analyser.run())

    # Print results
    for item in report_items:
        print(item)


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
