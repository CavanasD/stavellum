# Startup cover artwork

The application displays a separate cover before the project welcome window. It continues automatically about 1.4 seconds after the workspace is ready. Click, Enter or Space skips the cover; an early skip continues as soon as initialization completes. The close button and Escape cancel startup. A project supplied on the command line opens after the cover finishes.

The composition uses a large application name and version on the left, translucent square overlays and a music-themed scene on the right. Text, version, overlays and controls are rendered by Qt rather than embedded in the artwork.

- Asset: src/stavellum/assets/startup-cover.png, included in the Python wheel.
- Generation: built-in image_gen tool with the imagegen skill; no CLI/API fallback.
- Composition reference: a CLion splash screen. The background is newly generated artwork without CLion or JetBrains branding.
- Widget captures: uv run python scripts/preview_ui.py --output artifacts/ui-preview --public-paths.

## Generation prompt

```text
Use case: stylized-concept. Asset type: original background artwork for a 960 x 600 desktop music-notation app startup splash (16:10 landscape). Create a polished cinematic surreal landscape, inspired by vivid professional IDE splash illustrations: still reflective turquoise sea, emerald mountain spires receding into mist, deep midnight blue sky, soft coral and pink sunset on the horizon. On the RIGHT third, a large beautiful floating three-dimensional treble-clef sculpture, unmistakably a musical treble clef, made of translucent luminous cyan and warm amber ribbons, with restrained magenta rim light. The clef floats above the water with a graceful vertical silhouette and a subtle reflected glow; it is the focal subject. The LEFT 45 percent should be very dark emerald/navy atmospheric negative space, quiet enough for large white application name text to be added later in actual UI. Atmospheric, high-end, rich painterly 3D environment, exceptionally cohesive lighting, detailed but composed. Full bleed scene. Do not render text, letters, logos, icons, app controls, UI panels, mosaic squares, frames or watermark. No hot-air balloon. The text and semi-transparent geometric square overlays will be painted by application code. Original artwork for Stavellum, not a recreation of any brand's imagery.
```
