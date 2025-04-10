import os
import importlib.util
from pathlib import Path

class PluginLoader:
    def __init__(self, plugins_dir):
        """
        Initialize the plugin loader.

        Args:
            plugins_dir: Path to the plugins directory.
        """
        self.plugins_dir = plugins_dir
        self.plugins = {}

    def load_plugins(self):
        """
        Load all plugins from the plugins directory.
        """
        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.name == "__init__.py":
                continue
            plugin_name = plugin_file.stem
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            if hasattr(plugin, "MODULE_INFO"):
                self.plugins[plugin.MODULE_INFO['name']] = plugin.Module
        return self.plugins
