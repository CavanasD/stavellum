# FLP 与 MIDI 导入兼容说明

导入器只读输入文件，不打开或保存原 FLP，不加载音源插件。WAV 是实际听感来源；源音符时钟与量化后的记谱分开保存。

## 已验证的格式与结果

| 输入 | 验证结果 | 验证的内容 |
| --- | --- | --- |
| FL 26 Basic with limiter 公开模板 | 完整解析，Playlist 为空时明确报告没有音符 | 三字节 0xAC 工程头部 framing、空编曲 |
| FL 26.1.5.5618 公开最小样本 | 空 Pattern 4 个 Clip、半长裁切 4 个 Clip、Audio Clip 及半长裁切各 1 个记录均完整读取 | 88 字节记录、空 Pattern 隐式身份、Audio Clip 诊断；这些样本没有音乐音符 |
| FL 24 Create a chord progression 公开模板 | 4 个 80 字节 Playlist 记录，51 个音符成功导入 | 旧版本回归、真实 Pattern 音符 |
| 自动生成的明确二进制测试 | 对照预期事件逐条比对通过 | 32/60/80/88 字节布局、重复／循环／裁切／静音、不同 PPQ、零长度步进触发、通道颜色、编曲选择 |

解析出的音符数量不能替代与 FL Studio 导出参考 MIDI 对照。精确演奏对照目前由受控测试覆盖；为新 FL 小版本加入兼容性前，应另行验证真实保存文件。公开样本只作为可选本地缓存，不随仓库重新分发。

可以使用 `python scripts/verify_flp.py INPUT.flp --compile --confirm-fixed-timing` 在本机重复检查；输入路径由命令参数提供，不硬编码私人绝对路径。`--output REPORT.json` 可保存不含输入绝对路径的诊断摘要；`--reference-midi REFERENCE.mid` 比较音高、精确拍位起止及重复事件数量。仅在确已确认工程速度固定时使用 `--confirm-fixed-timing`。

## 适配方法与失败行为

- 固定版本 PyFLP 2.2.1 的顶层解析器在 Python 3.14 有空枚举构造问题，也不识别 80／88 字节 Playlist。本应用使用其音符、通道参数和音轨结构解析定义，自行验证事件 framing；不修改已安装 PyFLP、不全局 monkeypatch、不写回 FLP。
- Playlist 按 FL 版本选择布局，而不单凭长度整除来猜测。例如 17600 字节既可包含 220 个 80 字节记录，也可包含 200 个 88 字节记录。
- FL 24／26 实测的 0xAC 事件包含三个字节；后续 0xC0 是独立文本事件。网上曾有相互不同的推断，本应用按真实样本验证的格式读取。
- 仅展开所选 Arrangement 中实际放置、未静音的 Clip。分谱身份来自 Channel Rack，Playlist 行不是乐器身份。
- Pattern 裁切偏移按整数时钟读取；Audio Clip 偏移属于音频结构，不作为 MIDI 音符。未知记录长度、无效身份、音符字段截断和声明通道数量不一致均失败并建议补充 MIDI。
- 未命名的空 Pattern 可能没有单独序列化的 Pattern 事件；保留诊断，不凭空补音符。若整个编曲没有音符，明确提示补充 MIDI。
- 音符颜色编号兼作 FL 的 MIDI 通道字段：先保留编号、保持一个 Rack 通道的身份。确认插件路由后，可通过界面显式按通道拆分，不能自动把颜色当作多音色路由。
- Channel Rack 通道色另存为来源轨道的 RGB 色值，用于活动矩形填充；Playlist／Mixer 颜色和音符颜色编号不参与选色。合并分谱按自身来源顺序优先选择普通奏法轨道，多个普通来源取最前一个，没有普通来源则取首个来源；独立分谱各自选色。用户填写的非空奏法设置优先于名称，`arco / normal / sustain / sustained / legato / 普通 / 弓奏 / 常规` 视为普通，其他显式值视为特殊；没有设置时沿用名称识别，未标奏法的名称视为普通。保存、重导入及按 MIDI 通道拆分均保留来源颜色；缺失或无效色值回退白色。
- 活动矩形适度提亮通道色，激活时整块持续亮起、隐藏边框，每个原始音符起音另有 100 毫秒的亮闪，音符结束后保留 120 毫秒释放衰减。静音时恢复黑色内部与浅色边框；合并分谱持色不随奏法变化。力度和重叠音符的响应取最大值，起音闪烁也取最大值，不叠加和弦亮度；闪烁随短音的释放一起衰减，预览跳转和视频逐帧均按绝对音频时间计算。

## 需要人工确认或 MIDI 补充的情况

首版仅支持固定速度和固定拍号。MIDI 存在速度／拍号变化时拒绝导入；Type 2、SMPTE 时间基准也拒绝导入。不同 MIDI 通道和中途 GM Program 更换保留为独立源轨；同通道的 Program、延音踏板和 All Notes Off 状态跨 MIDI 轨共享。

FLP 中所选编曲播放的 Automation Clip / Pattern 事件目标若全部已确认为音量，不再要求额外确认固定速度；未知、截断或无法绑定的目标仍标记“固定速度未确认”。判断依据原生目标编号，不看名称。若实际变速，必须使用固定速度 MIDI 或等待后续变速支持。拍号变化、独立通道循环、未验证的 Pattern 时间伸缩会明确拒绝。

Layer、Slide、通道琶音器及插件内部生成音符不能可靠等价制谱：导入器保留原输入／目标音高并输出诊断，最终音色、混音和演奏细节由 WAV 保留。零长度步进触发以十六分音符表达触发位置并提示采样尾音不能由这个时值代表。Keyswitch 不按低音范围猜测，只有用户指定才过滤。

导入器检查工程主音高、通道音高、键盘微调／根音、Add to key、采样伸缩音高及音符微调。存在非默认设置时逐通道报告具体音分或根音；主音高只对启用响应或响应状态未知的通道提示。首版保留钢琴卷帘的源音高，不猜测插件对这些设置的处理方式；确认实际发声后，可用分谱移调修正整半音，非整半音和插件内部移调仍需补充 MIDI。调号覆盖只更改记谱，不会把源音符整体移调。

音色识别采用名称及明确 GM／FL Keys 提示；Kontakt、FLEX、Wrapper 名称不代表内部 Patch。同一个声部的普通、Pizz、Spiccato／Staccato 可合并并保存奏法，Violin I／II、不同数字后缀及 MIDI 通道仍分开。所有建议默认为未确认，确认后才显示图标。

## 自动跳音与前倚音

新导入事件增加可空的 `key_release_tick`，与原有 `duration_tick` 分别表达真实按键释放和发声长度。MIDI Note Off（含零力度 Note On）提供真实释放；CC64 只延长发声时间，文件尾修复和控制器强制结束不作为真实按键证据。FLP 只有长度大于零且起止均未裁切的音填写门控；步进触发及裁切音保持未知。

识别在量化之前进行，按来源轨道／通道独立推断。跳音要求明确奏法或连续至少四次规律攻击：间隔 0.25–2 拍、门控比例 35%–65%，允许同起点同门控的和弦；恢复谱面节奏槽不改变源时钟。倚音只处理单个前倚音：门控 ≤0.25 拍且 ≤120 ms，距主音 ≤0.5 拍且 ≤180 ms，释放间隙 ≤80 ms，相邻音高差 1–2 半音、力度不高于主音，主音至少长三倍且不短于量化格。

主音接近量化格，短音明显偏离当前格时才考虑倚音；正规 32/64 分及相应三连网格、连续快速音型、复调、拨奏、明确连奏、Slide、Keyswitch 和未知门控保持原记谱。机械量化的真实装饰音可能漏识别。每分谱可独立关闭两项功能；`import/frame/render/parts` 支持 `--no-auto-staccato`、`--no-auto-grace`，命令行未指定时沿用保存值。

旧 MIDI 项目没有释放信息时保持未知，需重新导入获得真实门控。旧 FLP 原 JSON 缺少此字段且没有全局 `step_trigger_duration` 时，用保存的起止补充门控并附诊断；旧裁切情况无法逐音恢复。显式保存的 `null` 永不迁移为已知门控，有步进触发诊断的旧工程建议重新导入。原项目格式版本仍为 1，旧文件可读取；新字段不保证旧程序能读取。

## 音量自动化与力度渐变

`ProjectIR` 保存原生目标、原始曲线点、tension、完整元数据、Min/Max、裁切偏移、来源及路由，并用十六进制保留原始曲线／事件记录；原始音符力度保持不变。目标绑定已在独立 FL Studio 校准工程核定：E227 的目标编号、E234 的拍位增量及右端点曲线模式、E223 的绝对 tick / 目标 / 整数值。Channel Rack 主音量与 Mixer Insert / 总线 / Master 推子使用 FL 自带 `utils.VolTodB` 对应的增益换算；Mixer 归一化满量程为通道的 1.25 倍。旧通道路由字节和新版 E104 路由均解析。

校准支持低字节模式 0（Single，零张力为线性）和 2（Hold）。Single 正／负非零张力已对照原生渲染 WAV；高字节方向标志保留，不能当作曲线模式。未验证形状、控制器映射公式、LFO 与时间倍率保留来源并报告，不能用线性曲线代替。Pattern 原始事件按实际离散保持保存；密集同向录制可恢复渐变，孤立台阶保持跳变。所选 Arrangement 的重复、裁切、静音与来源轨道关联在导入时展开。

沿串联路由相乘增益，共享 Mixer 节点应用于所有经过它的声部。静态分叉仅在所有可听路径的共同控制足以确定变化时支持；静音路径剔除，支路自动化、未知路由或未知混音关系跳过并诊断。合成曲线按转折、突跳、重置分段，合并连续同向变化；累计至少 1 dB、持续至少一个当前分谱量化格（含启用的三连网格）才生成发夹线。检测下限为 −60 dB，实际端点不吸附到音符或量化格。

区段须与可制谱音符存在时间重叠，可跨中间休止；完全静默的区段不生成记号。合并分谱同时发声的来源须共同渐强或共同渐弱，变化与保持并存、方向冲突会跳过受影响区段。使用完成分小节后的精确 `SpannerAnchor`，钢琴逻辑声部只在下方谱表标一次。预览、视频、MusicXML 与 PDF 共享结果；不扩展 MIDI CC7 / CC11 或音源内部参数。

界面提供逐分谱“识别音量自动化的渐强／渐弱”开关，默认启用；`import/frame/render/parts` 支持 `--no-auto-dynamics`，未指定时沿用保存值。项目格式仍为版本 1；缺少自动化字段的旧 FLP 文件加载后提示重新导入，重新导入保留可匹配的分谱设置。仅废弃速度设置 `tempo_display_mode` / `tempo_hold_seconds` 被显式丢弃，其余未知字段仍报错。

## 一手参考资料

- [PyFLP 2.2.1 导入与模型参考](https://pyflp.readthedocs.io/en/stable/reference.html)
- [PyFLP PR #205：新版 Playlist 与公开 FL 26 保存样本讨论](https://github.com/demberto/PyFLP/pull/205)
- [公开 FL 25／26 最小测试附件](https://github.com/user-attachments/files/31938992/empty-fl2025-fl2026.zip)
- [PyFLP PR #208：三字节 0xAC framing 的实测修正](https://github.com/demberto/PyFLP/pull/208)
- [FL Studio 官方 Playlist：Pattern Clip、Slip Edit 与编曲身份](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/playlist.htm)
- [FL Studio 官方 Performance Mode：Play truncated notes in clips](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/playlist_performance.htm)
- [FL Studio 官方导出说明](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fformats_save_export.htm)
- [FL Studio 官方 Automation Clip：目标、曲线模式与 Min/Max](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/playlist_automationclip.htm)

导出参考 WAV 应从 Song 起点开始并保留尾音。如果使用“Prepare for MIDI export”，它会替换音源，应先制作工程副本。
