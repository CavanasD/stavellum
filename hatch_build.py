"""Package the built Vulkan backend as a Windows x64 wheel."""

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Initial source installs must work before the development SDK is prepared.
        if version == "editable":
            return
        resource_root = Path(self.root) / "src/stavellum/native/rhi"
        names = ("stavellum_rhi.dll", "quad.vert.qsb", "quad.frag.qsb")
        missing = [name for name in names if not (resource_root / name).is_file()]
        if missing:
            raise RuntimeError(
                "Build and install the Vulkan backend before packaging: "
                "uv run python scripts/build_rhi.py --install; missing " + ", ".join(missing)
            )
        build_data["pure_python"] = False
        build_data["tag"] = "py3-none-win_amd64"
        for name in names:
            build_data["force_include"][str(resource_root / name)] = (
                "stavellum/native/rhi/" + name
            )
