# AI Coding 方法论

> CLAUDE.md 和 settings.json 的编写规范
>
> **核心原则**：分层文档、保持精简、精准配置

---

## 1. CLAUDE.md 编写规范

### 1.1 核心原则

```
┌─────────────────────────────────────────────────────────────────┐
│  CLAUDE.md = 项目名片                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 只写 3-5 项核心信息                                        │
│  2. 只写 AI 每次必读的内容                                       │
│  3. 详细信息放到 docs/ 手册中                                     │
│  4. 不超过 30 行                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 必须包含的 5 项

| 序号 | 内容 | 说明 |
|------|------|------|
| 1 | **一句话描述** | 这是什么项目 |
| 2 | **项目结构** | 目录概览 |
| 3 | **技术栈** | 用什么技术 |
| 4 | **启动命令** | 怎么跑起来 |
| 5 | **核心文件** | 入口和关键文件 |

### 1.3 禁止包含的内容

```
❌ 详细开发规范（→ docs/dev-guide.md）
❌ API 接口文档（→ docs/api.md）
❌ Agent 定义（→ .claude/agents/）
❌ Skill 定义（→ .claude/skills/）
❌ 团队成员、项目历史等
```

### 1.4 模板

```markdown
# 项目名称

一句话描述（不超过 20 字）。

## 项目结构

- backend/      # 后端
- frontend/     # 前端
- docs/         # 详细文档

## 技术栈

- 后端：Python 3.11 + FastAPI
- 前端：Vue 3 + Vite

## 启动命令

- 后端：cd backend && uvicorn main:app --reload
- 前端：cd frontend && npm run dev

## 核心文件

- backend/main.py       # 入口
- backend/api/*.py      # API 路由

## 详细文档

- 开发规范：./docs/dev-guide.md
- API 文档：./docs/api.md
```

---

## 2. settings.json 编写规范

### 2.1 配置层级（从高到低）

```
Managed Settings（不可覆盖）
        ↓
命令行参数
        ↓
settings.local.json（本地）
        ↓
.claude/settings.json（项目）
        ↓
~/.claude/settings.json（全局）
```

### 2.2 permissions 三级权限

| 级别 | 说明 | 适用 |
|------|------|------|
| `allow` | 直接执行，不询问 | 可信任的操作 |
| `ask` | 执行前询问 | 危险操作 |
| `deny` | 禁止执行 | 最高优先级，不可覆盖 |

### 2.3 AI Coding 推荐配置

```json
{
  "permissions": {
    "allow": [
      "Edit(*)",
      "Write(*)",
      "Read",
      "Glob",
      "Grep",
      "Bash(*)",
      "WebFetch(domain:*)",
      "WebSearch"
    ],
    "deny": [],
    "ask": [
      "Bash(rm *)",
      "Bash(rmdir *)",
      "Bash(unlink *)",
      "Bash(kill *)",
      "Bash(killall *)",
      "Bash(pkill *)"
    ]
  },
  "outputStyle": "Explanatory",
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80"
  },
  "language": "chinese",
  "respectGitignore": true
}
```

### 2.4 配置说明

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `Edit/Write allow` | 必要 | AI Coding 必须能写代码 |
| `Bash allow` | 必要 | 需要执行命令 |
| `rm/kill ask` | 谨慎 | 危险操作需确认 |
| `outputStyle` | Explanatory | 详细解释 |
| `language` | chinese | 全程中文 |
| `autocompact 80%` | 延迟压缩 | 保持更多上下文 |

---

## 3. 解决问题对照

| 问题 | 解决方法 |
|------|----------|
| A 改 B 错 | 小步提交 + 精准指令 + `ask` 确认 |
| CLAUDE.md 太长降智 | 分层文档 + 精简到 3-5 项 |
| 危险操作失控 | `ask` 确认 |
| 上下文耗尽 | 设置 `autocompact 80%` |

---

## 4. 持续进化

```
遇到问题 → 思考原因 → 调整配置 → 验证效果 → 继续优化
```

配置不是一步到位的，是随着你的使用经验不断完善。
