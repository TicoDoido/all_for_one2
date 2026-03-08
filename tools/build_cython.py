"""Build all Cython modules in this folder in-place.

Usage:
    python plugins/DECOMP_CODE/build_cython.py build_ext --inplace
or simply:
    python plugins/DECOMP_CODE/build_cython.py
"""
from __future__ import annotations

from pathlib import Path
import sys

try:
    from setuptools import Extension, setup
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"setuptools não está disponível: {exc}")

try:
    from Cython.Build import cythonize
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Cython não está instalado no ambiente atual. "
        "Instale Cython e execute novamente. "
        f"Erro original: {exc}"
    )

BASE_DIR = Path("plugins/DECOMP_CODE")
MODULES = [
    "allz",
    "aplib",
    "lzss_codec",
    "refpack_cy",
]

ext_modules = [
    Extension(
        name=f"plugins.DECOMP_CODE.{module}",
        sources=[str(BASE_DIR / f"{module}.pyx")],
    )
    for module in MODULES
]

if __name__ == "__main__":
    argv = sys.argv
    if len(argv) == 1:
        argv = [argv[0], "build_ext", "--inplace"]

    setup(
        name="plugins-decomp-code-cython",
        ext_modules=cythonize(
            ext_modules,
            language_level=3,
            compiler_directives={
                "boundscheck": False,
                "wraparound": False,
            },
        ),
        script_args=argv[1:],
    )
