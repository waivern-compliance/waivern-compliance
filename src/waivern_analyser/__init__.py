from waivern_analyser._plugins import load_plugins


def main():
    print("Hello from waivern-analyser!")
    print("Loading plugins...")
    plugins = load_plugins()
    print("Loaded plugins:")
    for plugin_name, plugin_class in plugins.items():
        print(f"- {plugin_name}: {plugin_class}")
