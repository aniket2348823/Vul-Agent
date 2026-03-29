"""Pytest configuration and shared fixtures."""
import sys
from pathlib import Path

# Ensure plugin cli is importable
plugin_root = Path(__file__).resolve().parent.parent
if str(plugin_root) not in sys.path:
    sys.path.insert(0, str(plugin_root))
