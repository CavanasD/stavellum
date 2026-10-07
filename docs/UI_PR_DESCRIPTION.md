# feat: add Rust native backends and simplify the desktop UI

## Summary

Add Rust backends for Vulkan compositing and per-frame scene evaluation, with Python bindings and Windows wheel packaging. Native C ABI versions remain compatible, and the Qt C++ rendering backend remains selectable.

Unify the editor, project wizard and welcome window under a shared desktop theme. Move frequently used editor actions into compact icon buttons, simplify the recent-project list and add a skippable startup cover. Fix saved-path handling after reimport, keyboard seeking and error states when applying background results.

## Changes

- Implement instanced quads, adjacent texture batching, persistently mapped buffers, tightly packed readback and batched submissions in the Rust Vulkan compositor. Compile WGSL shaders during the build.
- Implement native time-axis evaluation, camera motion, track interpolation, activity envelopes and tile planning in the Rust scene core. Add parity and native contract tests.
- Add Windows build tooling and package both Rust DLLs in the wheel. Retain Python import, notation, layout and desktop workflows.
- Use packaged SVG icons for new, open, save, video export, preview refresh and playback. Preserve tooltips, accessible names and menu shortcuts.
- Simplify the welcome window, make recent projects scrollable and keyboard-accessible, and elide names and paths separately. Use a subtle selection background without a side stripe.
- Show a separate startup cover before the welcome window. Continue automatically about 1.4 seconds after initialization, allow click/Enter/Space to skip, and cancel startup on close or Escape. Open a supplied project after the cover finishes.
- Preserve the saved path after reimport; update preview time on keyboard slider changes without recursive rendering; restore failure state and controls when a background result cannot be applied.
- Add contribution guidelines, a PR template, title validation and Windows Python/Rust checks. Include reproducible UI captures and review evidence.

Project files, Python runtime dependencies, CLI arguments and native ABI versions remain compatible. Source builds require rebuilding native DLLs after native code changes; wheel installations include the compiled libraries.

Startup artwork provenance and its generation prompt are documented in [STARTUP_ART.md](STARTUP_ART.md).

## Validation

Local environment: Windows x64, Python 3.14 and PySide6 6.11.2, with DLLs built from the corresponding Rust sources.

| Check | Result |
| --- | --- |
| uv run ruff check src tests scripts | Passed |
| Native-migration snapshot: core, compositor, readback, startup, welcome and branding tests | 80 passed, 1 skipped; 30.15 s |
| Final GUI, welcome, wizard, startup workflow, branding and splash tests | 144 passed, 1 skipped; 50.63 s |
| Native Windows splash and wizard ownership/stacking tests | 9 passed; 2.06 s; covers the offscreen skip |
| cargo fmt --all -- --check | Passed |
| cargo test --workspace --locked | 8 unit tests passed; doc tests passed |
| cargo clippy --workspace --all-targets --locked -- -D warnings | Passed |
| uv build --wheel | Passed; verified the theme, splash module/artwork, 10 SVG assets and both Rust DLLs |
| Native-migration snapshot wheel build | Passed |
| PR title validation and git diff --check | Passed |

The skipped test requires native Windows window stacking and cannot run on the offscreen Qt platform. Rust checks use the MSVC environment loaded by scripts.build_rust.build_environment().
Detailed commands and regression coverage are listed in [UI_PR_REVIEW.md](UI_PR_REVIEW.md).

## UI evidence

These are captures of running Qt widgets. Local sample paths are replaced with public placeholders. The welcome window is 1060×720 and the editor is 1480×920 at 100% offscreen scale. The native startup cover is 960×600 logical pixels at 150% Windows scale. Smaller 900×620 and 1000×700 windows and 150% offscreen scale were also inspected.

Reproduce with:

    uv run python scripts/preview_ui.py --output artifacts/ui-preview --public-paths

![Startup cover](screenshots/startup.png)

![Project welcome window](screenshots/welcome.png)

![Editor actions](screenshots/editor.png)

## Limitations

The listed checks cover native contracts and affected desktop workflows, rather than a complete final application test run. External FLP reference projects and the slow video-export suite were not rerun. GPU performance has not been remeasured on other hardware; historical benchmark figures are not presented as current validation.

CI uses offscreen Qt. GPU export and device-specific behavior require corresponding hardware checks. Remote check results are available in the PR checks section. No project-format migration is required.
