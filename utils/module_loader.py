import os
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Type

class ModuleLoader:
    def __init__(self, modules_dir: str):
        """
        Initialize the module loader.

        Args:
            modules_dir: Path to the directory containing modules.
        """
        self.modules_dir = Path(modules_dir)
        self.modules: Dict[str, Type] = {}
        self._setup_module_path()

    def _setup_module_path(self):
        """Add modules directory to Python path if not already present."""
        if str(self.modules_dir) not in sys.path:
            sys.path.insert(0, str(self.modules_dir))

    def _validate_module(self, module) -> bool:
        """
        Validate that a module has the required attributes.
        
        Args:
            module: The module to validate
            
        Returns:
            bool: True if module is valid, False otherwise
        """
        return (
            hasattr(module, 'Module') and 
            hasattr(module.Module, 'MODULE_INFO') and
            isinstance(module.Module.MODULE_INFO, dict) and
            'name' in module.Module.MODULE_INFO and
            'description' in module.Module.MODULE_INFO
        )

    def load_modules(self) -> Dict[str, Type]:
        """
        Load all modules from the modules directory.
        
        Returns:
            Dict[str, Type]: Dictionary of loaded modules
        """
        if not self.modules_dir.exists():
            print(f"[!] Modules directory not found: {self.modules_dir}")
            return {}

        for root, _, files in os.walk(self.modules_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    module_path = Path(root) / file
                    module_name = module_path.stem
                    module_category = Path(root).relative_to(self.modules_dir)

                    try:
                        # Create module spec
                        spec = importlib.util.spec_from_file_location(
                            f"{module_category}.{module_name}",
                            module_path
                        )
                        
                        if spec is None:
                            print(f"[!] Could not create spec for {module_path}")
                            continue
                            
                        # Create and load module
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[spec.name] = module
                        spec.loader.exec_module(module)

                        # Validate and register module
                        if self._validate_module(module):
                            self.modules[f"{module_category}/{module_name}"] = module.Module
                            print(f"[+] Loaded module: {module_category}/{module_name}")
                        else:
                            print(f"[!] Module {module_category}/{module_name} is missing required attributes")
                            
                    except ImportError as e:
                        print(f"[!] Import error in {module_category}/{module_name}: {e}")
                    except Exception as e:
                        print(f"[!] Failed to load module {module_category}/{module_name}: {e}")

        return self.modules