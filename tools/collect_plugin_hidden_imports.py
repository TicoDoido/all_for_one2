#!/usr/bin/env python3
"""Collect top-level imports used by plugins to feed PyInstaller hidden-import flags."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"


def _stdlib_modules() -> set[str]:
    names = set(getattr(sys, "stdlib_module_names", set()))
    # Compat fallback for older Python if needed.
    if not names:
        names.update(
            {
                "os",
                "sys",
                "json",
                "pathlib",
                "re",
                "subprocess",
                "threading",
                "time",
                "shutil",
                "tempfile",
                "itertools",
                "functools",
                "collections",
            }
        )
    return names


def collect_hidden_imports() -> list[str]:
    if not PLUGINS_DIR.exists():
        return []

    plugin_names = {p.stem for p in PLUGINS_DIR.glob("*.py")}
    local_packages = {
        p.name
        for p in PLUGINS_DIR.iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
    }
    stdlib = _stdlib_modules()
    imports: set[str] = set()

    for file_path in sorted(PLUGINS_DIR.glob("*.py")):
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    imports.add(root)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                if node.module:
                    root = node.module.split(".", 1)[0]
                    imports.add(root)

    filtered = sorted(
        module
        for module in imports
        if module
        and module not in stdlib
        and module not in plugin_names
        and module not in local_packages
        and module != "__future__"
        and module != "plugins"
    )
    return filtered


if __name__ == "__main__":
    for module_name in collect_hidden_imports():
        print(module_name)