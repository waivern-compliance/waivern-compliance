import typer

from waivern_analyser._plugins import load_plugins

app = typer.Typer()


@app.command()
def run():
    print("Hello from waivern-analyser!")


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
