# Rust migration / GLM coordination

The user requested a full Rust migration and Vulkan performance work, and has
contacted GLM separately. There is no direct GLM model tool in this session.

Codex owns `native/rust-renderer/`, the workspace Cargo files,
`scripts/build_rust.py`, renderer ABI integration and renderer benchmarks.
Please coordinate changes to `_rhi.py`, packaging and build entry points here
before changing them concurrently.

GLM can own Rust project/import/notation models and desktop UI migration in
separate crates. Keep existing `.stproj`, CLI and import behavior compatible.
Write findings and requested interface changes below. Do not remove existing
Python functionality until its Rust replacement has parity tests.

The first deliverable is a Rust Vulkan compositor using wgpu's Vulkan backend,
4x MSAA, instanced quads, ordered texture runs and bounded batch readback. This
is an actual native renderer replacement, not completion of the whole app
migration. MIDI/FLP imports, notation/layout and UI still need Rust ports.

## Shared interface

`sprhi_*` C ABI version 3, as described in `native/rhi/rhi.h`, remains the
boundary. Textures are premultiplied RGBA; outputs are top-down BGRA with CPU
owners independent of the device. Frame commands must preserve painter order.
Rust shaders are embedded and need no Qt SDK, QSB files or C++ renderer.

## GLM notes

Add implementation status and proposed interfaces here.

## Codex handoff status

Rust compositor, build script, Python ABI routing, wheel/sdist resources,
ownership tests and a synthetic benchmark are implemented in source. The
default compatibility build remains Qt until Rust validation passes.

The MSVC build failed because `link.exe` and a registered VS C++ toolchain were
unavailable. A preinstalled GNU Rust toolchain and CLion MinGW were found. GNU
release compilation began successfully, but terminal execution subsequently
stopped returning results, including trivial independent shell commands.
Compilation was interrupted; no DLL build, tests, Vulkan runtime or FPS gains
have been confirmed. `CARGO_BUILD_JOBS` now defaults to 2 to limit build load.

Next: restore terminal execution, compile/format/check Rust, run pixel and
ownership tests, inspect real-project output, then compare single and batched
frame production and the full FFmpeg pipeline. Do not present the synthetic
byte-count reduction as measured FPS improvement.

### 2026-10-05 GLM (ZCode) — per-frame core math crate

Status: starting `native/rust-core` (crate `stavellum-core`, cdylib+
rlib, lib name `stavellum_core`, C ABI prefix `spcore_`, ABI version 1).

Scope: port the backend-independent per-frame evaluation math out of
Python — `TimeAxis` (axis.py), `CameraTimeline.x_at/speed_at`
(camera.py), `_Track.sample` + `LayoutTimeline.at` (layout.py),
`activity_levels` envelopes (scene.py), and `_tile_plan`/`_raster_level`
(render.py). Compile-time code (`compile_layout`, `compile_camera`,
engraving) stays in Python; Python serializes the compiled curves into
the Rust scene once, then calls one `spcore_frame` per rendered frame.

Files I will touch (beyond my own crate): root `Cargo.toml` (add
workspace member only), new `src/stavellum/_core.py` ctypes wrapper +
`core.py` optional-acceleration facade, `scene.py`/`render.py`/`rhi.py`
hot-path call sites behind the facade with pure-Python fallback,
`scripts/build_rhi.py` (add cargo build path for my crate alongside the
existing one — tell me if you would rather own that file and I will use
a separate `scripts/build_core.py`), tests `tests/test_core_*`.
I will not modify `native/rust-renderer/`, `_rhi.py`, `native/rhi/`, or
your `scripts/build_rust.py`.

Measured motivation (this machine, demo project, 3 parts): command
build ~0.2–0.5 ms/frame in Python, dominated by `_Track.sample`,
`clipped_quad`, `_tile_plan`, `activity_lamp_color`; scales linearly
with parts/notes on real projects.

Interface proposal (v1): `spcore_compile` takes axis arrays, camera
scalars, zoom/tops/opacities curve keys, part dimensions, activity
notes, tile constants and viewport geometry; `spcore_frame(handle,
presentation_time, audio_time)` writes a packed `SpCoreFrame` (world_x,
scale, region, bounds, per-part rows with top/opacity/indicator/
icon_size/activity level+attack, tile plan level/raster_scale/first/
last/working_bytes + resident bitmap). Python wraps rows into
`FrameLayout`/`TilePlan` unchanged so renderers see identical types.
Parity: golden-value tests generated from the Python implementation.


### 2026-10-06 GLM (ZCode) — renderer takeover, ash rewrite, all green

The user moved all remaining work here ("不协作了，都是你干"). Decisions and
outcome, superseding the handoff note above:

- Replaced the unverified wgpu implementation with a direct `ash` Vulkan
  renderer in the same crate/dll name (`rust-ash`), keeping the C++-exact
  accounting contract so both the original and the rust-branched assertions
  in the tests pass unchanged.
- Shaders: WGSL → SPIR-V at build time via naga (`build.rs`), embedded.
- Two load-bearing performance fixes discovered by measurement:
  readback staging must use HOST_CACHED memory (WC reads cost ~70 ms/frame
  at 1080p), and returned CPU frames are pooled (GNU heap commit churn).
  Net effect: 13.5 → 666 fps in the synthetic batch benchmark.
- Toolchain reality: no MSVC on this machine. `.cargo/config.toml` pins the
  MinGW linker (static libgcc); `scripts/build_rust.py` now auto-falls back
  to the preinstalled GNU toolchain when vswhere finds nothing, and no
  longer mistakes Git's coreutils `link.exe` for MSVC.
- Validation: cargo test plus the full native integration suite pass
  (test_rust_renderer 3, test_rhi_owned 3, batch+readback 3, test_rhi
  REAL 1). Full pytest green after pinning one CPU-internals tempo
  test that assumed the auto backend could never select a working GPU.
- Measured (RTX 5070 Laptop): 1080p batch-4 stream 538 fps vs 234 fps CPU
  (2.3×); 4K 149 vs 78 (1.9×); synthetic 666 fps at batch 8.

Next planned in `native/rust-core`: the per-frame evaluation math port
described below (axis/camera/layout sampling/activity/tile plan).

### 2026-10-06 GLM (ZCode) — rust-core delivered (ABI v1)

`native/rust-core` (lib `stavellum_core.dll`, prefix `spcore_`) ports the
per-frame evaluation math: `TimeAxis` (x/beat/integral/difference/polynomial,
PCHIP derivatives), `CameraTimeline` x/speed/acceleration, `_Track.sample`
quintic Hermite + `LayoutTimeline.at` (rows, indicators, bounds, region,
tempo padding), `activity_levels` envelopes and `_raster_level`/tile-plan
header. Python side: `src/stavellum/_core.py` (ctypes + scene serializer).

Parity: `tests/test_core_native.py` compares 200+ timestamps across intro,
expansion, tempo-exit and mid-scroll against the Python implementation with
relative error < 1e-9 on every field, plus the invalid-axis error contract.
Both crates build via `scripts/build_rust.py [--install]`; clippy is clean.

Two repr(C)/ctypes field-order mismatches (tempo_owner inside LayoutConsts,
doubles/ints inside CoreFrame) were caught by the golden test — the exact
class of bug the parity harness exists for. Hot-path wiring of `_core` into
`layout_at`/`commands` is deliberately left as follow-up work; the crate is
consumer-ready but the Python call sites still use the pure-Python path.

### 2026-10-06 GLM (ZCode) — three-agent review, all findings triaged

Reviewers: Vulkan renderer (P0:1 P1:1 P2:3 P3:6), rust-core parity
(P1:1 P2:4 P3:5), integration/packaging (P1:2 P2:6 P3:4). Fixes landed:

- P0 renderer: wrong-thread `sprhi_close` freed the renderer despite
  returning an error (use-after-free); ownership is now taken only after
  the thread check passes.
- P1 renderer: duplicate texture ids waiting in the pending-upload queue
  were accepted and silently leaked GPU objects; upload now rejects them
  with the C++ message.
- P1 core: `raster_level` could livelock on a degenerate zoom (exp
  underflow); degenerate ratios now return level 0 and the loop is bounded.
- P2 renderer: `stage_pending` restores not-yet-staged uploads on failure;
  descriptor sets are recycled through a spare list instead of leaking
  pools under eviction churn; the post-copy barrier declares TRANSFER_READ.
- P2 core: `spcore_compile` validates declared totals against per-part
  counts (no more trusted-length slices); track keys must strictly
  increase; `camera_speed` documented as the raw camera value.
- P2 integration: `.cargo/config.toml` is portable again (machine linkers
  live in gitignored `.cargo/config.local.toml`; build_rust.py exports
  `CARGO_TARGET_..._GNU_LINKER` from STAVELLUM_MINGW/PATH/local config);
  `_rhi.py` PySide6 gate applies only to the legacy Qt DLL; dead
  `.cache/rhi/build/stavellum_rust.dll` fallback removed; sdist ships
  `.cargo/config.toml` + README-zh; README.md build path points at
  build_rust.py; dead "rust-wgpu" test arms removed; integration tests
  skip (not fail) on DLL-present/GPU-absent machines via a cached probe.
- P3: naga's automatic coordinate-space adjustment is now explicitly
  disabled in build.rs and the shader owns the Vulkan y-down mapping;
  format probes split per attachment role; RGBA env matches C++ nonzero
  semantics; instance asks for Vulkan 1.0; `native_swizzle_path` reports
  "none" on the BGRA path; welcome drag is left-button only; stray
  vulkaninfo dump untracked; test_welcome rewritten for the new page.

Accepted risks (documented, not fixed): per-texture dedicated
vkAllocateMemory (live allocations stay far below the 4096 guarantee for
realistic cache budgets) and partial-object leaks on early failures in
`Renderer::new` (init-time only).

Validation after fixes: full pytest 1170 passed / 0 failed, all eight
pixel-contract integration tests green, cargo test 8 passed across both
crates, clippy and ruff clean, and the golden parity harness extended to a
multi-part scene with announcement expansion, hidden rows, negative times,
camera speed and inconsistent-totals rejection.
