# 桌面 UI 与 PR 规范：Review 记录

PR 标题：`feat(ui): 精简桌面界面并完善启动与 PR 工作流`

依赖 [Rust 迁移基础 PR #1](https://github.com/CavanasD/stavellum/pull/1)。
本次 UI 分支基于 `feat/rust-vulkan-migration`，Rust 格式化提交已归入基础分支。

## 问题与结果

欢迎页、编辑器和新建向导原先使用不同的控件样式；常用编辑操作主要藏在菜单里。
现在三者使用统一的深色主题、暖色主操作和清晰的卡片层次。
编辑器将新建、打开、保存、MP4 导出与更新预览收为谱面右上角的 32px 图标按钮，
移除单独的品牌导航栏，保留操作提示和原有菜单快捷键。播放/暂停也使用紧凑图标。
起始页使用纯色背景、紧凑的图标文字按钮和可滚动的最近工程列表，
移除大 Logo、宣传标题、发光谱线与右侧流程卡片。
最近工程选中项移除左侧亮条，仅保留淡色背景。
工程列表前新增可跳过的独立启动封面，参考 CLion 的名称、版本与方格构图，
使用原创音乐主题背景；主窗口准备好后约 1.4 秒自动进入，点击或 Enter 可提前继续。
关闭封面会取消启动，传入的工程在封面结束后打开。
素材来源和最终生成提示词见 [STARTUP_ART.md](STARTUP_ART.md)。
新增贡献规范、PR 模板、标题检查及 Windows CI，要求提供当前提交的验证证据。

Review 范围为桌面打开/保存/重新导入、预览时间轴、后台任务结果处理与窗口布局，
并运行 Python 回归套件及 Rust 检查。本次未逐行审查所有记谱和 Vulkan 算法。

## 已修复的发现

| 优先级 | 触发与影响 | 修复与验证 |
| --- | --- | --- |
| P2 | 已保存工程重新导入时，`_source_imported` 调用 `set_document` 未传保存路径。之后 Ctrl+S 会变成另存为，原工程不会按预期更新。 | 保留当前 `project_path`；回归测试确认不打开另存为对话框，并写回原文件。 |
| P2 | 时间轴只监听 `sliderMoved`，方向键、PageUp/Down 或滚轮改变滑块值时，预览与内部时间不更新。 | 监听 `valueChanged`；内部刷新用 `QSignalBlocker` 避免递归。键盘回归测试确认帧时间变化，以及内部播放进度刷新不触发额外渲染。 |
| P2 | 后台任务成功返回，但结果应用/渲染器初始化失败时，只弹出错误，任务标签和预览状态仍可能表示正在处理。 | 统一经过 `_job_error`，显示失败状态并恢复操作；测试确认上一份工程和预览继续保留。 |
| P3 | 最近工程隐藏滚动条；长路径与名称共用同一文本样式，较小窗口中难以浏览。 | 启用按需滚动、分别绘制名称与省略路径，完整路径保留在提示中；测试确认 900×620 下可用 End/Enter 打开第十项。 |

## 变更边界

- 新主题只作用于桌面控件，工程格式、CLI、谱面字体与视频帧绘制逻辑保持兼容。
- 箭头和操作 SVG 随包发布，在深色界面和不同缩放比例下保持清晰。
- Rust 文件只经 `cargo fmt` 调整格式，未修改原生 ABI 或渲染行为。
- 本机忽略的核心 DLL 早于源码，曾导致总数校验测试失败；重建后通过。这不是当前源码新增的缺陷。
- `docs/PR_DESCRIPTION.md` 保留为之前 Rust 迁移的历史记录。

## 验证证据

环境：Windows x64、Python 3.14、PySide6 6.11.2；安装当前源码构建的 Rust DLL 后执行。

| 命令/检查 | 结果 |
| --- | --- |
| `uv run ruff check src tests scripts` | 通过 |
| `uv run python -u -m pytest -q tests/test_gui.py tests/test_welcome.py tests/test_new_project.py tests/test_startup_workflow.py tests/test_branding.py tests/test_startup_splash.py -o faulthandler_timeout=60 --basetemp artifacts/pytest-pr-ui-final-20261007 --maxfail=3` | 144 通过，1 跳过，50.63 秒 |
| `QT_QPA_PLATFORM=windows` 下启动封面全部测试和向导所有权/层叠测试 | 9 通过，2.06 秒；覆盖离屏跳过项 |
| `cargo fmt --all -- --check` | 通过 |
| `cargo test --workspace --locked` | 8 个单元测试通过，文档测试通过 |
| `cargo clippy --workspace --all-targets --locked -- -D warnings` | 通过 |
| `uv build --wheel` | 通过；确认包含主题、启动模块/PNG、全部 10 个 SVG 和两份 Rust DLL |
| PR 标题检查 | 合规中文标题通过，非规范标题被拒绝 |
| `git diff --check` | 通过 |

最终相关测试的唯一跳过项为离屏平台无法检查原生窗口层叠，已在原生 Windows 平台补测通过。
在新启动封面加入前，曾运行 `not slow` 完整套件：1221 通过、6 跳过；这是阶段记录，
不作为最终提交的完整套件结果。其余 5 项跳过来自缺少外部 FLP 模板/工程。
最终整组回归还适配了旧的 Vulkan 平台准备测试，使其验证先准备 Qt、显示封面、
再构造主窗口和打开工程，避免模拟事件循环返回后遗留真实延迟回调。

实际界面截图由 `scripts/preview_ui.py` 生成，已检查欢迎页空态/最近工程、
三个编辑器页与新建向导，窗口尺寸为 1060×720、900×620、1480×920、1000×700 和 900×760。
另用 `QT_SCALE_FACTOR=1.5` 检查了欢迎页和编辑器较小窗口。
启动封面另检查了 100% / 150% 缩放，小屏幕按可用区域等比缩小。
截图、测试日志和 wheel 存放在忽略的 `artifacts/`、`dist/`，不随源码提交。
公开 PR 使用的三张实际截图另存于 [screenshots](screenshots)，示例路径替换为公开占位路径。
生成命令为 `uv run python scripts/preview_ui.py --output artifacts/pr-ui-screenshots-final --public-paths`。
启动封面截图来自原生 Windows，逻辑尺寸 960×600、系统缩放 150%；欢迎页与编辑器分别为
1060×720 和 1480×920、离屏缩放 100%。

## 限制与合并要求

GitHub 工作流随 UI PR 发布；远端检查以 PR 的 Actions 状态为准。
CI 使用离屏 Qt，GPU 导出和原生窗口行为仍需设备验证。
维护者需要在 GitHub 配置分支保护，才能把仓库中的 CI 检查设为合并必需条件。
未下载外部 FLP 参考工程，相关跳过不能视为格式验证通过。
