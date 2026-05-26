# Spoken 开发进度

_最后更新：2026-04-13（按当前仓库代码核对）_

---

## 当前结论

**状态：核心链路已成型，项目已进入“稳定性优化 + 发布收尾”阶段。**

当前主线已经完成以下核心能力：
- `SpokenApp` + `Pipeline` + `StateController` 的分层架构已落地
- 实时识别支持多引擎降级：`XunfeiRealtimeEngine` -> `SenseVoiceOfflineEngine` -> `RealtimeWhisperEngine`
- 批量识别保留 `FasterWhisperEngine` 路径
- 文本注入支持 `SendInput`、剪贴板降级、IME 处理、Electron/UWP/UAC 判定
- UI 已升级为 `WebView2` 浮窗 + 新托盘图标
- 仓库内已补充单元测试（AI / Pipeline / Settings / State）

一句话判断：**现在不是“能不能跑”的阶段，而是“把兼容性、可安装性、打包发布补齐”的阶段。**

---

## 已完成项

### 1. 主架构重构完成

主入口 `__main__.py` 已不再承担全部业务逻辑，当前结构为：
- `__main__.py`：负责初始化、模块装配、事件分发
- `pipeline.py`：负责 ASR -> AI -> CoT 过滤 -> 注入 的主流程
- `state.py`：负责运行状态（`ready/recording/recognizing/ai_processing/error`）和模式（`A/B/C`）管理

这意味着：
- 主流程已经从“脚本式串联”升级为“模块化可测试架构”
- UI、状态、业务流转已经基本解耦
- 后续继续扩展新的 ASR / 注入 / UI 方案，成本会明显降低

### 2. ASR 主线已升级为多引擎实时架构

当前 `realtime` 模式不是单一方案，而是两层实时识别链路：

1. `asr/windows_speech.py`
   - Windows 原生 SpeechRecognizer（最接近 Win+H 的系统能力）
   - 作为默认首选实时引擎

2. `asr/xunfei_realtime.py`
   - 讯飞云端 WebSocket 实时转写
   - 支持 partial / final 回调
   - 作为云端备选（需配置密钥）

此外：
- `config/defaults.toml` 默认 `asr.mode = "realtime"`
- `config/defaults.toml` 默认 `realtime_provider = "windows"`
- `__main__.py` 已支持根据配置自动选择引擎并执行降级

### 3. 录音、流水线与 AI 处理链路完成

当前流水线核心能力：
- 录音停止后统一进入 `Pipeline`
- `run_realtime()` 处理实时路径
- `run_batch()` 处理批量路径
- `_run_ai_and_inject()` 统一完成：
  - Mode A：直接注入
  - Mode B：AI 润色
  - Mode C：转 Prompt
- AI 结果在注入前会统一经过 `strip_think_tags()` 过滤

说明：
- CoT 过滤已经从“局部补丁”升级为“流水线统一兜底”
- 空文本、静音、异常路径都有显式状态回退逻辑
- `Esc` 中断逻辑已保留在主流程中

### 4. 文本注入链路已增强

当前注入层由 `injector/dispatcher.py` 统一调度，主要能力包括：
- `SendInput` 注入
- 失败自动降级剪贴板注入
- 录音开始时记录焦点窗口，结束后恢复焦点再注入
- SendInput 路径下自动配合 `ImeGuard` 关闭 IME 干扰
- 自动识别 Electron / UWP 应用并优先走剪贴板
- 检测提权窗口（UAC），避免无权限注入导致静默失败

这部分已经明显比旧版“单一路径注入”成熟很多。

### 5. UI 层已经换新实现

#### 浮窗：`overlay/window.py`
- 已改为 `pywebview` / `WebView2` 风格的现代浮窗
- 支持毛玻璃半透明背景
- 支持状态栏、模式标签、流式文字展示
- 通过命令队列处理跨线程 UI 更新

#### 托盘：`tray/icon.py`
- 已重绘新的圆形托盘图标
- 支持 5 个状态颜色：ready / recording / recognizing / ai_processing / error
- 支持模式角标（A/B/C）
- 支持右键菜单切换模式、退出、查看日志

### 6. 配置体系基本完成

当前配置体系已经比较完整：
- 默认配置：`config/defaults.toml`
- 用户配置：`%APPDATA%\Spoken\config.toml`
- 支持默认配置 + 用户覆盖配置深度合并
- 支持敏感字段脱敏输出
- 支持运行时保存模式切换结果
- 配置校验与自动修正（mode、injection、hotkey 等）

当前默认值大致是：
- 热键：`alt+r` 录音、`alt+m` 切模式、`esc` 中断
- 模式默认：`B`
- 注入默认：`auto`
- AI 默认：开启，但优先从环境变量 `SPOKEN_AI_API_KEY` 读取 key

### 7. 热键能力已具备两套实现

`hotkey/manager.py` 当前同时保留：
- `PushToTalkHotkey`
- `ToggleRecordHotkey`

但要注意：
- **当前 `__main__.py` 实际接线使用的是 `ToggleRecordHotkey`**
- 因此仓库当前真实默认行为仍应按“按一次开始 / 再按一次停止”理解
- PTT 能力已经有代码实现，但还没有在主入口中作为默认方案接上

### 8. 依赖与测试文件已补齐到更完整状态

当前 `requirements.txt` 已包含：
- ASR 相关：`PyAudio`、`sounddevice`、`websockets`
- UI / 托盘：`pystray`、`Pillow`、`pywebview`
- AI / 配置：`openai`、`tomli-w`
- 工具链：`pyinstaller`、`pytest`

仓库内已有测试文件：
- `tests/test_ai_processor.py`
- `tests/test_pipeline.py`
- `tests/test_settings.py`
- `tests/test_state.py`

说明项目已经进入“开始系统化回归验证”的阶段。

---

## 当前待完善 / 风险项

### 🔴 高优先级

1. **SendInput 兼容性仍需继续验证**
   - 当前架构已经支持失败自动降级剪贴板
   - 但 `sendinput.py` 仍然存在“部分窗口/中文输入不稳定”的风险
   - 现阶段属于“有 fallback，但主路径兼容性还不够稳”

2. ~~主入口热键默认行为与历史文档不一致~~ ✅ **已解决**
   - `config/defaults.toml` 已统一为 `record_mode = "toggle"`
   - `README.md` 已同步更新
   - PTT 能力代码仍保留，用户可通过配置切回 `push_to_talk`

3. ~~配置示例与当前代码命名需要统一核对~~ ✅ **已解决**
   - 当前代码主用配置章节名 `injection` 已统一
   - `README.md` 配置示例已核对

### 🟡 中优先级

4. ~~打包发布链路还未最终收口~~ ✅ **已解决**
   - `spoken.spec` + `build.bat` / `build.ps1` 已补齐
   - 单目录模式（onedir），保留控制台便于调试
   - 下一步：在实际环境验证打包产物可正常运行

5. **测试需要做一次本机完整回归**
   - 仓库已经有单元测试文件
   - 但仍需要在目标环境完整跑一遍 `pytest`
   - 特别要补验证：Windows 热键、WebView2 浮窗、注入兼容性、麦克风设备访问

6. **其他文档仍有历史信息残留**
   - `README.md` 里仍存在旧热键 / 旧默认值 / 旧打包说明
   - 当前 `PROGRESS.md` 已按代码修正，但其他文档还需要后续同步

### 🟢 低优先级

7. **设置界面仍未落地**
   - 当前仍以 `config.toml` 为主
   - 后续可考虑补 GUI 设置页或托盘配置入口

8. **开机自启、安装器、发布产物整理**
   - 这些更偏发布工程化
   - 不影响核心功能，但会影响交付体验

---

## 当前真实文件结构（节选）

```text
spoken/
├── __main__.py
├── pipeline.py
├── state.py
├── spoken.spec
├── build.bat
├── build.ps1
├── config/
│   ├── defaults.toml
│   └── settings.py
├── asr/
│   ├── engine.py
│   ├── faster_whisper.py
│   ├── windows_speech.py
│   └── xunfei_realtime.py
├── injector/
│   ├── base.py
│   ├── clipboard.py
│   ├── dispatcher.py
│   ├── ime.py
│   └── sendinput.py
├── overlay/
│   └── window.py
├── tray/
│   └── icon.py
├── hotkey/
│   └── manager.py
├── ai/
│   ├── processor.py
│   └── prompts.py
├── tests/
│   ├── test_ai_processor.py
│   ├── test_pipeline.py
│   ├── test_settings.py
│   └── test_state.py
├── requirements.txt
└── PROGRESS.md
```

---

## 下一阶段建议

当前核心架构、打包链路和文档均已补齐，建议按下面顺序收尾：

1. **环境回归测试**：在目标 Windows 机器上完整跑通 `pytest`，验证所有单元测试通过
2. **SendInput 兼容性实测**：覆盖 VS Code、Edge、记事本、微信、飞书等常用目标窗口
3. **打包产物验证**：跑通 `build.ps1`，确认 `dist/spoken/` 可直接运行且资源文件完整
4. **安装体验优化**：可考虑补充开机自启脚本或安装器（如 Inno Setup / MSIX）
5. **设置 GUI（可选）**：后续若用户反馈配置门槛高，可补托盘配置入口或 WebView2 设置页

---

## 备注

本文件已根据当前仓库代码重新整理，优先以代码现状为准；历史版本号、旧 zip 名称、旧安装步骤不再作为主依据。
