# 学习通 Chaoxing Agent Skill

> **For AI Agents reading this**: clone this repo into `~/.hermes/skills/` or register it as an external skill directory, then load `skill: chaoxing-public`. See [Agent Self-Setup](#-agent-self-setup) below.

一个为 **Hermes Agent**、**OpenClaw** 等 AI 编程助手设计的 学习通 (超星/Chaoxing/SuperStar MOOC) 自动化技能包。零手动配置——告诉你的 AI 助手这个仓库地址，它自己就能装好。

## ✨ 功能

- **全课程扫描** — 批量检测所有课程的作业和考试状态
- **作业自动化** — 识别题型、填充富文本/附件、自动提交、回查确认
- **考试工作流** — 进入考试、提取题目、批量答题、交卷、核验分数
- **自动过滑块验证码** — Capsolver 后端流水线（零键鼠全自动）或 Playwright CLI（手动完成滑块）
- **多 Agent 兼容** — 支持 Hermes / OpenClaw / Claude Code / Open Code 等
- **可靠性保障** — 隐藏输入验证、AJAX 等待、DOM 重新查询、QID 随机化处理
- **失败自动修复** — 检测低分/空选/提交失败，判断重考入口，自动重试并修正

---

## 🤖 Agent Self-Setup

**对你的 AI 助手说这句话即可：**

> 帮我装一下学习通 skill：https://github.com/iwillwill-ALLWILL/chaoxing-agent-skill

如果你用的是 Hermes Agent，AI 会自动执行以下步骤。如果是 OpenClaw 或其他工具，把这段复制给它：

### Hermes Agent

```bash
# 1. 克隆仓库
git clone https://github.com/iwillwill-ALLWILL/chaoxing-agent-skill.git ~/chaoxing-agent-skill

# 2. 注册为外部 skill 目录
hermes config set skills.external_dirs "[$(cd ~/chaoxing-agent-skill/skills && pwd)]"
# 如果上面命令把值存成了字符串（YAML 引号问题），用 Python 修复：
python -c "
import yaml, pathlib
p = pathlib.Path.home() / 'AppData/Local/hermes/config.yaml'
c = yaml.safe_load(p.read_text())
c.setdefault('skills', {})['external_dirs'] = [str(pathlib.Path.home() / 'chaoxing-agent-skill/skills')]
p.write_text(yaml.dump(c, default_flow_style=False, allow_unicode=True, sort_keys=False))
"

# 3. 重启 Hermes (/reset) 后生效
# 加载方式: skill_view('chaoxing-public') 或直接说"扫学习通"
```

### OpenClaw / 通用 Agent

```bash
# 1. 克隆
git clone https://github.com/iwillwill-ALLWILL/chaoxing-agent-skill.git ~/chaoxing-agent-skill

# 2. 将 skills/ 目录加入你的 agent 的 skill 搜索路径
# 3. 加载 skill: chaoxing-public
# 4. SKILL.md 内容即为系统提示词，可直接注入
```

### 验证安装

```bash
ls ~/chaoxing-agent-skill/skills/productivity/chaoxing/SKILL.md
# 文件存在 = 安装成功
```

---

## 🔑 验证码处理

超星滑块验证码是考试流程中唯一的交互步骤。提供两种方案：

### 方案 A：Playwright CLI（免费，推荐 Claude Code / Open Code 用户）

无需任何 API key，通过有头浏览器手动完成滑块：

```bash
# 一次性安装
npm install -g @playwright/cli
playwright install chromium

# 使用时
python scripts/playwright_captcha.py --manual --url "<考试页面URL>"
```

脚本会打开有头浏览器，你手动完成滑块验证后按回车继续。

### 方案 B：Capsolver 全自动（付费）

～$0.001/次，零键鼠全自动。**⚠️ Capsolver 已取消免费额度，最低一次性充值 $6：**

1. 注册 https://dashboard.capsolver.com
2. 充值（最低 $6）
3. 获取 API Key（格式：`CAP-...`）
4. 在终端设置环境变量：

```bash
export CAPSOLVER_KEY="CAP-你的key"
# Windows PowerShell:
$env:CAPSOLVER_KEY="CAP-你的key"
```

> 💡 **建议**：日常用 Playwright CLI 手动模式（免费），考试时用 Capsolver 自动模式。

其他一切（登录、扫描、答题、提交）都通过你已登录的浏览器自动完成，无需额外配置。

---

## 📁 仓库结构

```
chaoxing-agent-skill/
├── README.md
├── skills/productivity/chaoxing/
│   ├── SKILL.md                       ← 主技能文件（AI 直接加载）
│   ├── references/
│   │   ├── captcha-solving.md         ← 🔑 滑块验证码全自动流水线
│   │   ├── reliability-pitfalls.md    ← 10 个真实坑点+修复
│   │   ├── browser-relay-patterns.md  ← Relay 集成模式
│   │   ├── homework-workflow.md       ← 作业流程详解
│   │   ├── exam-status-audit.md       ← 考试批量审计
│   │   └── privacy-sanitization.md    ← 隐私脱敏指南
│   └── scripts/
│       ├── captcha_pipeline.py        ← 🔑 CAPTCHA 后端流水线（需 Chrome Relay）
│       ├── playwright_captcha.py      ← 🔑 Playwright CLI 方案（通用 Agent）
│       ├── relay_helpers.py           ← Relay 统一 API
│       ├── scan_homework_status.py    ← 批量扫描作业
│       └── verify_submission.py       ← 提交状态验证
└── examples/
```

---

## 🎯 使用示例

对 AI 助手说这些话：

| 你说 | AI 做 |
|------|------|
| "扫一下学习通有哪些作业没交" | 全课程扫描，列出待处理 |
| "帮我把这门课的作业交了" | 识别题型 → 填充 → 提交 → 验证 |
| "这个考试帮我做一下" | 进考试 → 采题 → 答题 → 交卷 |
| "上次考试分数太低了重考一下" | 检测重考入口 → 重进 → 重做 → 验证 |
| "学习通有什么要处理的" | 全量审计，区分可处理/不可处理 |

---

## ⚙️ 前置要求

- 浏览器已登录 学习通
- **Hermes**：Chrome Relay 已安装（Edge 端口 12123 或 Chrome 端口 12122）
- **OpenClaw**：内置 browser tools 即可
- **Claude Code / Open Code**：安装 Playwright CLI（`npm install -g @playwright/cli && playwright install chromium`）
- Python 3.8+（仅脚本需要）
- Capsolver 账号（可选，仅全自动滑块验证码需要，最低充值 $6）

---

## ⚠️ 隐私

本仓库不含任何个人身份信息。所有 `courseId`、`clazzId`、`enc` 等使用占位符。详见 `references/privacy-sanitization.md`。

---

MIT License
