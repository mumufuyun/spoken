# Spoken — Windows 全局语音输入工具

按住热键说话，松手后文字自动输入到当前光标位置。支持 AI 润色、翻译、摘要等 6 种模式。

---

## 快速开始

1. **运行**：双击 `Spoken.exe`
2. **说话**：按住 `Alt + R`（默认热键），对着麦克风说话
3. **松手**：文字自动输入到当前窗口的光标处

---

## 六种输出模式

按 `Alt + M` 循环切换：

| 模式 | 名称 | 说明 |
|------|------|------|
| **A** | 直出 | 语音识别后直接输入，零延迟 |
| **B** | 润色 | AI 修正语法、标点、错别字 |
| **C** | 转 Prompt | 把口语描述转成结构化 AI 指令 |
| **D** | 翻译 | 翻译成自然英文 |
| **E** | 摘要 | 输出一段精炼摘要 |
| **F** | 结构化纪要 | 按 主题/事项/待办/时间 组织 |

> **提示**：AI 模式（B~F）需要联网。如果 AI 调用失败，会自动降级为 Mode A 直出。

---

## 热键一览

| 热键 | 功能 |
|------|------|
| `Alt + R` | 开始 / 停止录音 |
| `Alt + M` | 切换模式（A→B→C→D→E→F→A） |
| `Esc` | 中断当前处理 |

热键可在配置文件中修改（见下文）。

---

## 状态说明

### 托盘图标颜色

| 颜色 | 状态 | 含义 |
|------|------|------|
| 🟢 绿色 | ready | 就绪，等待录音 |
| 🔵 蓝色 | starting | 正在启动语音引擎 |
| 🔴 红色 | recording | 录音中 |
| 🟡 黄色 | recognizing | 识别中 |
| 🟣 紫色 | ai_processing | AI 处理中 |
| 🔵 蓝色 | injecting | 正在注入文字 |
| 🟠 橙色 | error | 发生错误 |

### 浮窗状态条

录音时屏幕底部会出现浮窗，实时显示识别内容和当前状态。

---

## 配置说明

用户配置文件路径：

```
%APPDATA%\Spoken\config.toml
```

### 常用配置示例

```toml
[hotkey]
# 录音热键：toggle 模式（按一次开始，再按一次停止）
toggle_record = "alt+r"
# 模式切换
switch_mode = "alt+m"
# 中断
interrupt = "esc"

[asr]
# 实时识别引擎：xunfei（讯飞）或 windows（Windows 原生）
realtime_provider = "xunfei"

[ai]
# 是否启用 AI
enabled = true
# AI 接口地址（公司 Friday 平台）
base_url = "https://aigc.sankuai.com/v1/openai/native"
# AppID（Friday 平台使用纯数字 AppID）
api_key = "22046856405852057673"
# 模型名
model = "gpt-4o-mini"
# 超时秒数
 timeout_sec = 15

[mode]
# 默认启动模式
default = "B"
```

### 修改热键

常用热键写法：
- `alt+r`、`ctrl+alt+r`
- `win+space`（Win+空格）
- `f1` ~ `f12`
- `semicolon`（分号键）

---

## 常见问题

### 热键没反应
- 检查是否与其他软件冲突
- 某些场景（如注入管理员权限窗口）需要以管理员身份运行 Spoken

### 无法注入文字
- Spoken 会自动在 `SendInput` 和 `剪贴板` 之间切换
- VS Code、Notion、Cursor 等应用默认走剪贴板方案

### 录音不工作 / 没声音
- 确认麦克风可用（Windows 设置 → 隐私 → 麦克风权限）
- 如果使用 Windows 原生引擎，需在「隐私和安全性 → 语音」中开启「在线语音识别」
- 讯飞引擎需要联网，确认网络正常

### AI 返回 401 错误
- 检查 `api_key` 是否正确（Friday 平台应为纯数字 AppID）
- 如果设置过环境变量 `SPOKEN_AI_API_KEY`，确认它没有被旧的 MiniMax key 覆盖

### 如何清除旧的环境变量

PowerShell：
```powershell
[Environment]::SetEnvironmentVariable("SPOKEN_AI_API_KEY", $null, "User")
```

或图形界面：Win + R → `sysdm.cpl` → 高级 → 环境变量 → 用户变量 → 删除 `SPOKEN_AI_API_KEY`

---

## 开发信息

### 源码运行

```bash
cd D:\spoken
py -3.12 -m pip install -r requirements.txt
py -3.12 -m spoken
```

### 打包

```bash
.venv\Scripts\python.exe -m PyInstaller spoken.spec --clean --noconfirm
```

输出：`dist/Spoken.exe`

### 测试

```bash
py -3.12 -m pytest -q
```
