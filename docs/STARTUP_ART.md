# 启动封面主视觉

应用启动时先显示独立的 Stavellum 封面，主窗口准备好后停留约 1.4 秒，
随后进入工程列表。点击或按 Enter / Space 可跳过；提前点击会在主窗口准备好后立即继续。
右上角关闭按钮和 Escape 会退出启动流程。通过命令行传入的工程在封面结束后打开。

布局参考用户提供的 CLion 启动封面截图：左侧名称与版本、半透明方格、右侧主视觉。
工程列表选中项使用淡色背景，已移除左侧亮条。
文字、版本、方格和控件由 Qt 绘制，背景图片不包含这些内容。

- 保存位置：`src/stavellum/assets/startup-cover.png`，随 Python wheel 发布。
- 生成方式：内置 `image_gen` 工具，使用 `imagegen` 技能，非 CLI/API 回退模式。
- 参考图只用于理解布局；背景为新生成的音乐主题图像，没有使用 CLion / JetBrains 标识。
- 实际界面截图：`uv run python scripts/preview_ui.py --output artifacts/ui-preview`。

## 最终生成提示词

```text
Use case: stylized-concept. Asset type: original background artwork for a 960 x 600 desktop music-notation app startup splash (16:10 landscape). Create a polished cinematic surreal landscape, inspired by vivid professional IDE splash illustrations: still reflective turquoise sea, emerald mountain spires receding into mist, deep midnight blue sky, soft coral and pink sunset on the horizon. On the RIGHT third, a large beautiful floating three-dimensional treble-clef sculpture, unmistakably a musical treble clef, made of translucent luminous cyan and warm amber ribbons, with restrained magenta rim light. The clef floats above the water with a graceful vertical silhouette and a subtle reflected glow; it is the focal subject. The LEFT 45 percent should be very dark emerald/navy atmospheric negative space, quiet enough for large white application name text to be added later in actual UI. Atmospheric, high-end, rich painterly 3D environment, exceptionally cohesive lighting, detailed but composed. Full bleed scene. Do not render text, letters, logos, icons, app controls, UI panels, mosaic squares, frames or watermark. No hot-air balloon. The text and semi-transparent geometric square overlays will be painted by application code. Original artwork for Stavellum, not a recreation of any brand's imagery.
```
