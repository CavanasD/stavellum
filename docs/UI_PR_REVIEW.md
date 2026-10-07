# Desktop review and validation

Review scope: document replacement and saved paths, preview seeking, background-result handling, navigation, window sizing and startup lifecycle. Native behavior is covered by parity and contract tests. This is not an exhaustive audit of notation or Vulkan algorithms.

## Resolved findings

| Priority | Trigger and impact | Fix and verification |
| --- | --- | --- |
| P2 | Reimporting a saved project called set_document without its saved path. A subsequent Ctrl+S opened Save As instead of updating the existing project. | Preserve project_path; the regression test writes back to the original file without opening Save As. |
| P2 | The timeline listened only to sliderMoved. Arrow keys, PageUp/Down and wheel changes could leave preview time unchanged. | Listen to valueChanged and use QSignalBlocker for internal transport updates. Keyboard tests verify frame times and prevent recursive rendering. |
| P2 | A background job could return successfully but fail while applying its result. The error dialog appeared while task or preview state still indicated processing. | Route application failures through _job_error. Tests verify failure status, restored controls and retention of the previous document and preview. |
| P3 | Hidden recent-project scrollbars and uniformly styled paths made long lists difficult to navigate in small windows. | Enable scrolling, draw names and elided paths separately, and retain full-path tooltips. A 900×620 test reaches and opens the tenth item with End/Enter. |

## Desktop behavior

The editor, project wizard and welcome window share a dark theme. Editor actions use 32 px icon buttons with tooltips, accessible names and existing menu shortcuts. Playback switches between play and pause icons.

The welcome window uses compact actions and a recent-project list with a subtle selected-row background. The startup cover displays separately, scales to the available screen area and continues after initialization. Click, Enter or Space skips it; close or Escape cancels startup. A supplied project opens after the cover hands control to the welcome window.

Startup tests cover early skipping, automatic completion, single handoff, keyboard focus, cancellation, display before workspace construction and deferred project opening. The Vulkan platform-preparation test verifies preparation before the cover and workspace are constructed.

Project files, CLI behavior and score typography remain compatible. Desktop changes do not modify native ABI versions or frame-rendering behavior. Native build and migration details are documented in [rust-renderer.md](rust-renderer.md).

## Validation

Environment: Windows x64, Python 3.14 and PySide6 6.11.2. Installed DLLs correspond to the tested Rust sources.

| Check | Result |
| --- | --- |
| uv run ruff check src tests scripts | Passed |
| GUI, welcome, wizard, startup workflow, branding and splash tests | 144 passed, 1 skipped; 50.63 s |
| Native Windows splash and wizard ownership/stacking tests | 9 passed; 2.06 s |
| Native-migration snapshot contract and desktop tests | 80 passed, 1 skipped; 30.15 s |
| cargo fmt --all -- --check | Passed |
| cargo test --workspace --locked | 8 unit tests passed; doc tests passed |
| cargo clippy --workspace --all-targets --locked -- -D warnings | Passed |
| uv build --wheel | Passed; theme, splash module/artwork, 10 SVG assets and both Rust DLLs verified |
| Native-migration snapshot wheel build | Passed |
| PR title validation and git diff --check | Passed |

Desktop regression command:

    uv run python -u -m pytest -q tests/test_gui.py tests/test_welcome.py tests/test_new_project.py tests/test_startup_workflow.py tests/test_branding.py tests/test_startup_splash.py -o faulthandler_timeout=60 --basetemp artifacts/pytest-pr-ui-final-20261007 --maxfail=3

Native window verification:

    $env:QT_QPA_PLATFORM = 'windows'
    uv run pytest -q tests/test_startup_splash.py tests/test_startup_workflow.py::test_native_windows_wizard_ownership_and_stacking --basetemp artifacts/pytest-pr-ui-native-20261007

The offscreen skip is the native-window stacking test; it passes in the Windows run. The native-migration snapshot includes test_core_native, test_rust_renderer, test_rhi_batch_native, test_rhi_owned, test_gpu_readback, test_startup_workflow, test_welcome and test_branding.

Rust checks load the MSVC environment with scripts.build_rust.build_environment(). Each pytest command requires a new disposable --basetemp directory; pytest clears that directory.

## Visual evidence

scripts/preview_ui.py captures the startup cover, empty/recent-project welcome states, three editor tabs, smaller windows and the project wizard using isolated settings and demo media. Public captures replace local sample paths with placeholders:

    uv run python scripts/preview_ui.py --output artifacts/ui-preview --public-paths

The published [screenshots](screenshots) show the native cover at 960×600 logical pixels and 150% Windows scale, the welcome window at 1060×720 and the editor at 1480×920 with 100% offscreen scale. Inspected smaller windows include 900×620, 1000×700 and a 900×760 wizard. Offscreen captures at QT_SCALE_FACTOR=1.5 were also inspected.

Logs, intermediate captures and wheels remain in ignored artifacts/ and dist/ directories. Packaged artwork provenance is recorded in [STARTUP_ART.md](STARTUP_ART.md).

## Verification limits

The final checks cover affected workflows and native contracts. External FLP fixtures and the slow video-export suite were not rerun, and the listed results are not a complete final application test run. Other GPU devices and native platform behavior require corresponding device checks. CI results are reported in the PR checks section.
