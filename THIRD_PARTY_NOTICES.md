# Stavellum licensing and third-party notices

Copyright (c) 2026 Creeper19472 and Stavellum contributors.

Stavellum's original code, documentation, logo and original instrument SVGs
are released under **GPL-3.0-or-later**. The complete, downloaded GNU GPL v3
text is in [LICENSE](LICENSE). Third-party components retain their own terms.

## Why the complete application uses GPL

The FLP importer directly imports and uses PyFLP's note, channel and track
implementations. [PyFLP 2.2.1](https://github.com/demberto/PyFLP/tree/v2.2.1)
is licensed under GPL v3 or later, without a linking exception. The complete
application is therefore distributed under GPL v3 or later, rather than
advertised as an unrestricted MIT application. See the
[GNU GPL FAQ on GPL libraries](https://www.gnu.org/licenses/gpl-faq.html#IfLibraryIsGPL).
Changing to an MIT-only application would require replacing this dependency
with an implementation whose license permits that distribution.

## Runtime dependencies

The versions below are those recorded in `uv.lock` at release preparation.
The wheel contains Stavellum's own native DLL and shaders; Python dependencies
are installed separately. It does not bundle Qt runtime DLLs or FFmpeg.

| Component | Version | License | Source and license |
| --- | --- | --- | --- |
| PyFLP | 2.2.1 | GPL-3.0-or-later | [Upstream](https://github.com/demberto/PyFLP/tree/v2.2.1), [license](LICENSES/PyFLP-2.2.1.txt) |
| PySide6 / Shiboken6 / Qt | 6.11.2 | LGPL-3.0-only (or the applicable GPL alternative) | [Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/), [Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations), [LGPL text](LICENSES/LGPL-3.0.txt) |
| Mido | 1.3.3 | MIT | [Upstream](https://github.com/mido/mido/tree/1.3.3), [license](LICENSES/Mido-1.3.3.txt) |
| music21 code | 9.9.2 | BSD-3-Clause | [Upstream](https://github.com/cuthbertLab/music21), [license](LICENSES/music21-9.9.2.txt) |
| Verovio | 6.3.0 | LGPL-3.0-only | [Upstream](https://github.com/rism-digital/verovio/tree/version-6.3.0), [LGPL](LICENSES/Verovio-6.3.0-LESSER.txt) and [GPL](LICENSES/Verovio-6.3.0.txt) |

Stavellum does not use or redistribute music21's score corpus. Its code license
does not automatically cover that corpus or user-imported music.
Dependencies' transitive packages retain their upstream licenses as well;
`uv.lock` records their versions and distribution hashes.

Qt is dynamically linked. Users may replace the installed Qt/PySide6 libraries
and rebuild Stavellum's native backend against the matching development SDK.
Stavellum does not prohibit modification, relinking or reverse engineering.
The build commands and the supported Qt version are documented in the README.

## Fonts and visual assets

Edwin Roman / Italic, Source Han Serif SC and Leland remain under **SIL Open
Font License 1.1**. Their copyright notices, complete license texts and source
records are preserved in [the fonts directory](src/stavellum/fonts/README.md).
Verovio also supplies its own font resources, including Bravura.

The five instrument SVGs shipped here are original Stavellum line drawings,
covered by the project license. The logo is stored once at
`src/stavellum/assets/logo.png`; the application and README share that file.

Font Awesome Free **7.3.1** SVG icons (Solid, Regular and Brands) are bundled
under **CC BY 4.0**; accompanying non-icon metadata/code is under **MIT**.
Copyright 2026 Fonticons, Inc. Original attribution comments are retained in
the SVG archive and embedded project icons. The complete upstream notice is
in [the bundled license](src/stavellum/assets/fontawesome/LICENSE.txt).
See [upstream](https://github.com/FortAwesome/Font-Awesome/tree/7.3.1) and
[the Free license](https://fontawesome.com/license/free).
`scripts/prepare_fontawesome.py` reproduces the pinned resources from the
official `@fortawesome/fontawesome-free` npm package; the catalog records
the package integrity, archive SHA-256 and individual SVG SHA-256 values.
User-provided Font Awesome Pro libraries are not distributed with Stavellum;
their original license and attribution continue to apply to their files.

## Native build tools and external encoder

The Qt SDK, Visual Studio, CMake, Ninja, Qt shader tools and Vulkan-Headers are
build dependencies, not bundled SDKs. Vulkan-Headers 1.4.341 has its upstream
[license notice](LICENSES/Vulkan-Headers-1.4.341.txt); individual headers retain
their own SPDX identifiers. Reproducing the native library requires the
matching Qt SDK, Vulkan headers and C++ toolchain documented in the README.

FFmpeg and ffprobe are external executables. Their license depends on how the
installed binaries were built (including optional GPL components such as
libx264); this repository does not redistribute them. See
[FFmpeg's legal information](https://ffmpeg.org/legal.html).

## Distribution

Source releases include the application source, tests, build scripts, native
source and all bundled asset notices. GPL distributions of the complete
application must provide the complete corresponding source, including build
instructions. When redistributing dependencies or an installer, also supply
their notices and corresponding source as required by their GPL/LGPL terms.
The current wheel installs dependencies separately; it is not a standalone
desktop installer or a complete collection of dependency source archives.

Imported FLP/MIDI, original recordings, exported music and third-party project
files retain their owners' rights. The application license does not grant
rights to those works. No private input music or local `artifacts/` content
is included in source or wheel releases.

Downloaded license files and their SHA-256 checksums are recorded in
[LICENSES/SOURCES.md](LICENSES/SOURCES.md).
