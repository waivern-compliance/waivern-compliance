import typer

from waivern_analyser._plugins import load_plugins

app = typer.Typer()
plugins_app = typer.Typer()
app.add_typer(plugins_app, name="plugins")


@app.command()
def main():
    print("Hello from waivern-analyser!")


@plugins_app.command()
def ls():
    print("Loading plugins...")
    if plugins := load_plugins():
        print("Loaded plugins:")
        for plugin_name, plugin_class in plugins.items():
            print(f"- {plugin_name}: {plugin_class}")
    else:
        print("No plugins found")


if __name__ == "__main__":
    app()
