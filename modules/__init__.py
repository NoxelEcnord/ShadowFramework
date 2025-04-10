"""
Shadow Framework Modules Package
This package contains all the core modules for the Shadow Framework.
"""

from pathlib import Path

__all__ = ['auxiliary', 'exploit', 'post']
__version__ = '1.0.0'

# Ensure all module directories are treated as packages
for module_type in __all__:
    (Path(__file__).parent / module_type / '__init__.py').touch(exist_ok=True)
