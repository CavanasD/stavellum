"""Load an explicit Git revision for diagnostics without shipping old backends."""

from __future__ import annotations

import importlib
import importlib.util
import io
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_package(ref, directory, *, current_native=False):
    """Keep historical imports and resources isolated from production modules."""
    commit = subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
                            cwd=ROOT, check=True, capture_output=True, text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
    archive = subprocess.run(["git", "archive", "--format=zip", commit, "src"],
                             cwd=ROOT, check=True, capture_output=True,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        roots = [Path(name).parent for name in source.namelist()
                 if len(Path(name).parts) == 3 and name.endswith("/__init__.py")]
        if len(roots) != 1:
            raise RuntimeError("Git baseline must contain exactly one Python package under src")
        package_root = roots[0]
        for item in source.infolist():
            item_path = Path(item.filename)
            if not item_path.is_relative_to(package_root):
                continue
            relative = item_path.relative_to(package_root)
            destination = (directory / relative).resolve()
            if not destination.is_relative_to(directory):
                raise RuntimeError("Git baseline contains an invalid resource path")
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                data = source.read(item)
                if item_path.suffix == ".py":
                    # Adapt historical package imports and diagnostic variables after a rename.
                    data = (data.decode("utf-8").replace(package_root.name, "stavellum")
                            .replace(package_root.name.upper(), "STAVELLUM").encode("utf-8"))
                destination.write_bytes(data)
    # A distinct namespace per output keeps simultaneous historical revisions apart.
    name = "stavellum._benchmark_baseline_" + commit[:12] + "_" + str(abs(hash(str(directory))))
    spec = importlib.util.spec_from_file_location(name, directory / "__init__.py",
                                                submodule_search_locations=[str(directory)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    if current_native:
        sys.modules[f"{name}._rhi"] = importlib.import_module("stavellum._rhi")
    return package, commit


def renderer(package, *, rhi=False):
    module = importlib.import_module(f"{package.__name__}.{'rhi' if rhi else 'render'}")
    return module.RhiFrameRenderer if rhi else module.FrameRenderer
