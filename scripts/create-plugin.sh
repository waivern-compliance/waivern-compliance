#!/bin/bash

# A script to create a new plugin.
# 
# Arguments:
# - $1: The name of the plugin, e.g. "wordpress"

# TODO: validate plugin name:
# - no spaces
# - no special characters
# - correctly convertible to snake case (for the Python package name)
# - correctly convertible to Pascal case (for the class name)

# TODO: add error handling for when the plugin already exists

# Step 1: Initialize the script and validate arguments

# Check if the plugin name is provided
if [ -z "$1" ]; then
    echo "Error: Plugin name is required"
    exit 1
fi

# Step 2: Create the plugin directory and pyproject.toml file
plugin_name="$1"
plugin_full_name_kebab_case="waivern-compliance-tool-$1"
plugin_dir="src/plugins/$1"

uv init --name "$plugin_full_name_kebab_case" --package --lib "$plugin_dir"
uv add --package "$plugin_full_name_kebab_case" waivern-compliance-tool

# Add entry point to the plugin's pyproject.toml file
pyproject_file="$plugin_dir/pyproject.toml"

# Step 3: Add entry point to the plugin's pyproject.toml file
# Convert plugin name to proper case for class name (e.g. wordpress -> Wordpress)
plugin_full_name_snake_case="$(echo "$plugin_full_name_kebab_case" | sed 's/-/_/g')"
class_name="$(echo "$plugin_name" | sed 's/.*/\L&/; s/[a-z]/\U&/')Plugin"

echo "" >> "$pyproject_file"
echo '[project.entry-points."waivern-plugins"]' >> "$pyproject_file"
echo "$plugin_name = \"$plugin_full_name_snake_case:${class_name}\"" >> "$pyproject_file"

# Step 4: Create the plugin's __init__.py file
init_file="$plugin_dir/src/$plugin_full_name_snake_case/__init__.py"
echo "\"\"\"Plugin $plugin_name.\"\"\"

from wct.analysers import Analyser
from wct.connectors import Connector
from wct.plugins import Plugin
from wct.rulesets import Ruleset

class $class_name(Plugin):
    @classmethod
    def get_name(cls) -> str:
        \"\"\"Get the name of the plugin.

        This is used to identify the plugin in the system.
        \"\"\"
        return \"$plugin_name\"

    @classmethod
    def get_analysers(cls) -> tuple[type[Analyser], ...]:
        \"\"\"Get the new types of analysers that this plugin defines.\"\"\"
		# TODO: Add analysers here (if any - otherwise return an empty tuple)
        return ()

    @classmethod
    def get_connectors(cls) -> tuple[type[Connector], ...]:
        \"\"\"Get the new types of connectors that this plugin defines.\"\"\"
		# TODO: Add connectors here (if any - otherwise return an empty tuple)
        return ()

    @classmethod
    def get_rulesets(cls) -> tuple[type[Ruleset], ...]:
        \"\"\"Get the new types of rulesets that this plugin defines.\"\"\"
		# TODO: Add rulesets here (if any - otherwise return an empty tuple)
        return ()
" > "$init_file"

# Step 5: Finalize script
echo "Plugin '$plugin_name' created successfully at $plugin_dir"

