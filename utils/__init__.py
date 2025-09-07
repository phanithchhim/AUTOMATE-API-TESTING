"""utils package initializer.

Expose schema_loader.load_schema for simple imports in scripts.
"""
from . import schema_loader

__all__ = ["schema_loader"]
