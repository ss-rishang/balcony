"""
Automatic loading of all custom Resource Node modules.

This module automatically imports all .py files in the custom_nodes directory.
Custom classes register themselves via their __init_subclass__ method.
"""

import importlib
import pkgutil
from pathlib import Path

# Get the directory of this package
package_dir = Path(__file__).parent  # type: ignore

# Automatically import all modules in this package
for module_info in pkgutil.iter_modules([str(package_dir)]):
    try:
        importlib.import_module(f".{module_info.name}", __name__)
    except ImportError:
        pass  # Skip modules that can't be imported
