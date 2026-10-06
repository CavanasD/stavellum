"""Golden parity between the Python per-frame math and the Rust core."""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest

from stavellum._core import CoreTarget, library_path
from stavellum.render import RasterFrameRenderer
from stavellum.scene import activity_levels, compile_scene

sys.path.insert(0, "tests")
from test_render import rendered_document  # noqa: E402


def native_available() -> bool:
    return library_path().is_file()


@pytest.mark.integration
@pytest.mark.skipif(not native_available(), reason="Rust core DLL has not been built")
def test_rust_core_matches_python_layout_camera_activity_and_tile_plan():
    document = rendered_document(piano=True)
    scene = compile_scene(document)
    assets = RasterFrameRenderer(scene)
    settings = scene.settings
    try:
        with CoreTarget(scene, cache_limit=assets.cache_limit) as core:
            # Cover intro, announcement expansion, mid-scroll and the tail.
            duration = min(scene.score_duration, 24.0)
            times = [index * duration / 200 for index in range(201)]
            if scene.layout.expansion_start is not None:
                start = scene.layout.expansion_start
                times.extend((start - 1e-3, start + 1e-3,
                             start + scene.layout.expansion_duration))
            times.append(max(0.0, scene.layout.tempo_exit_time - 1e-3))
            worst = {}
            for time in times:
                audio = settings.audio_time(time)
                frame, rows = core.frame(time, audio)
                layout = scene.layout_at(time)
                world_x = scene.camera_x_at(time)
                plan = assets._tile_plan(layout, world_x)
                compare = {
                    "world_x": (frame.world_x, world_x),
                    "scale": (frame.scale, layout.scale),
                    "region_top": (frame.region_top, layout.region_bounds[0]),
                    "region_bottom": (frame.region_bottom, layout.region_bounds[1]),
                    "bounds_top": (frame.bounds_top, layout.bounds[0]),
                    "bounds_bottom": (frame.bounds_bottom, layout.bounds[1]),
                    "tile_level": (frame.tile_level, plan.level),
                    "tile_first": (frame.tile_first, plan.first_index),
                    "tile_last": (frame.tile_last, plan.last_index),
                    "tile_raster": (frame.tile_raster_scale, plan.raster_scale),
                    "tile_bytes": (frame.tile_working_bytes, plan.working_bytes),
                }
                for part, row in zip(scene.parts, rows):
                    reference = layout.rows[part.part_id]
                    level, attack = activity_levels(part, audio)
                    compare.update({
                        f"{part.part_id}.top": (row.top, reference.top),
                        f"{part.part_id}.opacity": (row.opacity, reference.opacity),
                        f"{part.part_id}.x": (row.indicator_x, reference.indicator_rect[0]),
                        f"{part.part_id}.y": (row.indicator_y, reference.indicator_rect[1]),
                        f"{part.part_id}.w": (row.indicator_w, reference.indicator_rect[2]),
                        f"{part.part_id}.h": (row.indicator_h, reference.indicator_rect[3]),
                        f"{part.part_id}.icon": (row.icon_size, reference.icon_size),
                        f"{part.part_id}.level": (row.activity_level, level),
                        f"{part.part_id}.attack": (row.activity_attack, attack),
                    })
                for name, (actual, wanted) in compare.items():
                    if isinstance(actual, int) and isinstance(wanted, int):
                        assert actual == wanted, (name, time, actual, wanted)
                        continue
                    assert math.isfinite(actual), (name, time)
                    error = abs(actual - wanted) / max(1e-12, abs(wanted))
                    if error > worst.get(name, (0.0, 0.0))[0]:
                        worst[name] = (error, time)
                    assert error < 1e-9, (name, time, actual, wanted)
            # Report the tightest-achieved parity in the assertion message.
            slowest = max(worst.items(), key=lambda item: item[1][0])
            assert slowest[1][0] < 1e-9, slowest
    finally:
        assets.close()


@pytest.mark.integration
@pytest.mark.skipif(not native_available(), reason="Rust core DLL has not been built")
def test_rust_core_rejects_short_axis_without_crashing():
    script = r'''
import ctypes, json
from stavellum._core import CoreTarget, CurveKey, Note, LayoutConsts, library_path
dll = ctypes.CDLL(str(library_path()))
pointer = ctypes.c_void_p
dll.spcore_compile.restype = pointer
dll.spcore_compile.argtypes = (pointer, pointer, ctypes.c_int64,
    ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int64,
    pointer, ctypes.c_int64, pointer, pointer, ctypes.c_int64,
    pointer, pointer, ctypes.c_int64, pointer, pointer, pointer, pointer)
dll.spcore_last_error.restype = ctypes.c_char_p
dll.spcore_last_error.argtypes = ()
beats = (ctypes.c_double * 1)(0.0)
xs = (ctypes.c_double * 1)(0.0)
zoom = (CurveKey * 1)(CurveKey(0.0, 0.0, 0.0, 0.0))
zero = (ctypes.c_int64 * 1)(0)
empty_notes = (Note * 0)()
dims = (ctypes.c_double * 2)(1.0, 0.5)
consts = LayoutConsts()
consts.expansion_start = float("nan")
consts.tempo_owner = -1
consts.cache_limit = 1.0
handle = dll.spcore_compile(beats, xs, 1, 2.0, 0.0, 0.0, 1,
    zoom, 1, zoom, zero, 1, zoom, zero, 1, dims, empty_notes, zero,
    ctypes.byref(consts))
error = dll.spcore_last_error().decode("utf-8", "replace")
print(json.dumps({"handle": bool(handle), "error": error}))
'''
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 0, result.stdout + result.stderr
    import json

    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["handle"] is False and "至少两个" in report["error"]
