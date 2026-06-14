# 学习通 (Chaoxing) Agent Skill

一个为 **Hermes Agent**、**OpenClaw** 等 AI 编程助手设计的 学习通 (超星/Chaoxing/SuperStar MOOC) 自动化技能包。

通过浏览器 Relay 控制用户已登录的浏览器，实现课程扫描、作业提交、考试答题、状态审计和自动复盘。

## ✨ 功能

- **全课程扫描** — 批量检测所有课程的作业和考试状态
- **作业自动化** — 识别题型、填充富文本/附件、自动提交、回查确认
- **考试工作流** — 进入考试、提取题目、批量答题、交卷、核验分数
- **自动过滑块验证码** — Capsolver 后端流水线 + Tampermonkey 用户脚本，零键鼠全自动
- **可靠性保障** — 隐藏输入验证、AJAX 等待、DOM 重新查询、QID 随机化处理
- **失败自动修复** — 检测低分/空选/提交失败，判断重考入口，自动重试并修正

## 📁 结构

```
chaoxing-agent-skill/
├── README.md
├── skills/
│   └── productivity/
│       └── chaoxing/
│           ├── SKILL.md                          # 主技能文件
│           ├── references/
│           │   ├── browser-relay-patterns.md     # 浏览器 Relay 集成模式
│           │   ├── homework-workflow.md          # 作业提交流程详解
│           │   ├── exam-status-audit.md          # 考试状态批量审计
│           │   ├── reliability-pitfalls.md       # 可靠性坑点全集
│           │   └── privacy-sanitization.md       # 隐私脱敏指南
│           └── scripts/
│               ├── relay_helpers.py              # Relay 辅助函数（Chrome Relay / OpenClaw）
│               ├── scan_homework_status.py       # 批量扫描作业状态
│               └── verify_submission.py          # 验证提交状态
└── examples/
    ├── course-inventory.example.json             # 课程清单模板
    └── config.example.yaml                       # 配置文件模板
```

## 🚀 使用方式

### 在 Hermes Agent 中使用

将此仓库克隆到 Hermes 的 skills 目录：

```bash
git clone https://github.com/iwillwill-ALLWILL/chaoxing-agent-skill.git ~/.hermes/skills/chaoxing-agent-skill
```

或者在 `config.yaml` 中添加外部 skills 目录：

```yaml
skills:
  external_dirs:
    - path/to/chaoxing-agent-skill/skills
```

然后在对话中直接说 "帮我扫描学习通作业" 或 "帮我做这个考试" 即可。

### 在 OpenClaw 中使用

将 `skills/` 目录配置到 OpenClaw 加载路径中，或直接把 `SKILL.md` 内容作为系统提示词注入。

### 手动使用脚本

1. 确保浏览器 Relay 已运行（Chrome Relay 默认端口 12123）
2. 准备课程清单 JSON（参考 `examples/course-inventory.example.json`）
3. 在任意 `mooc1.chaoxing.com` 页面打开一个标签页
4. 运行脚本：

```bash
# 扫描作业状态
python skills/productivity/chaoxing/scripts/scan_homework_status.py <tab_id> course-inventory.json

# 验证提交状态
python skills/productivity/chaoxing/scripts/verify_submission.py <tab_id> tasks.json
```

## ⚙️ 前置要求

- 浏览器已登录 学习通 (passport2.chaoxing.com)
- 浏览器 Relay 已安装并运行（Chrome Relay、OpenClaw browser tools 或 Playwright CDP）
- Python 3.8+（仅脚本需要）

## ⚠️ 隐私说明

本仓库是一个**通用技能模板**，不含任何个人身份信息。使用时请确保：

1. 不要将含真实 `courseId`、`clazzId`、`answerId`、`enc` 的配置文件提交到公开仓库
2. 参考 `references/privacy-sanitization.md` 了解完整的脱敏清单
3. 将个人配置文件加入 `.gitignore`

## 🔧 技术栈

- **浏览器 Relay**：Chrome Relay（Edge 端口 12123）或 OpenClaw browser tools
- **核心原理**：通过控制用户已登录的浏览器，利用同源 `fetch()` 批量操作，避免直接 HTTP API（`uf` cookie 是 TLS 指纹绑定的）
- **JS 注入**：通过 Relay 在页面上下文中执行 JavaScript，实现 DOM 操作和答案保存
- **可靠性模式**：隐藏输入验证、AJAX drain 等待、DOM 引用刷新、QID 动态采集

## 🤝 适用场景

- ✅ 批量扫描学习通作业/考试状态
- ✅ 自动化提交富文本/附件型作业
- ✅ 批量答题考试（仅限允许的课程）
- ✅ 检测低分并自动重考修复
- ✅ 审计学习通账户完成度

## ❌ 不适用场景

- 其他平台（智慧树/知到）
- 需要人工判断的内容（论文批改、创意写作评估）
- 绕过平台安全限制或违反使用条款的行为

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE)
