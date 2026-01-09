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
            if plugin_file.name in ("__init__.py", "cve_plugin.py"):
                continue
            plugin_name = plugin_file.stem
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            for item in dir(plugin_module):
                if item.startswith('CVE_'):
                    plugin_class = getattr(plugin_module, item)
                    if issubclass(plugin_class, CVEPlugin):
                        plugin_instance = plugin_class(None) # Pass a dummy shell
                        self.plugins[plugin_instance.name] = plugin_class
        return self.plugins
