# 墨魂·江湖 AI 文字 MUD 世界模拟器

> 纯前端单文件实现，基于 LLM API 的复杂中文文字角色扮演游戏引擎。
> 适配设定要求.txt 中定义的全部游戏机制（10 模块输出、工具调用协议、天道系统、原著校验等）。
> 手机端友好，可部署到 GitHub Pages 免费托管。

## 两种使用方式

### 方式一：纯前端版（推荐，最简单）

只需一个 `index.html` 文件，部署到 GitHub Pages 即可，无需后端。

**核心特性：**
- 纯前端单文件，70KB，无任何依赖
- 直接调用 LLM API（豆包/GLM/DeepSeek/OpenAI 兼容）
- API Key 存储在浏览器 localStorage，不上传任何服务器
- 完整 10 模块输出解析与折叠面板展示
- 自定义角色（手动输入名称+身份+背景）
- 自动存档 + 手动存档读档
- 流式输出，实时显示生成内容
- 手机端响应式，暗色武侠风

### 方式二：Dify 版（需要自建后端，适合深度定制）

使用 Dify + dify-chat，支持知识库 RAG、Code 节点确定性工具。
详见 `dify/` 目录和下方说明。

---

## 快速开始（纯前端版）

### 第 1 步：获取 LLM API Key

任选其一：
| 服务商 | 获取地址 | 推荐模型 | 特点 |
|---|---|---|---|
| DeepSeek | https://platform.deepseek.com | deepseek-chat | 便宜、长上下文、中文好 |
| 智谱 GLM | https://open.bigmodel.cn | glm-4-plus | 中文最强之一 |
| 豆包(火山引擎) | https://www.volcengine.com | doubao-pro-32k | 字节系，响应快 |
| OpenAI | https://platform.openai.com | gpt-4o | 综合最强，需科学上网 |

### 第 2 步：部署到 GitHub Pages

1. 在 GitHub 创建一个新仓库（如 `mohun-jianghu`）
2. 将 `index.html` 上传到仓库根目录
3. 进入仓库 Settings → Pages
4. Source 选择 `main` 分支，目录选 `/ (root)`
5. 保存，等待 1-2 分钟
6. 访问 `https://你的用户名.github.io/mohun-jianghu/`

### 第 3 步：配置并开始游戏

1. 打开页面，点击右上角 ⚙️ 设置
2. 选择服务商，填写 API Key
3. 点击"测试连接"，确认成功
4. 返回首页，选择小说
5. 选择身份（支持自定义角色，手动输入名称和背景）
6. 选择难度，开始游戏

### 本地运行（可选）

```bash
# 方式 A：直接用浏览器打开
# 直接双击 index.html 即可

# 方式 B：用 Python 起静态服务
python3 serve.py
# 访问 http://localhost:8080

# 方式 C：用 Node 起静态服务
npx serve .
```

---

## 玩法说明

### 开局
1. 选择小说（内置 6 部 + 自定义输入）
2. 选择身份类型：原著关键人物 / 原著边缘人物 / 原创路人 / **自定义角色**
3. 自定义角色可手动输入：角色名称、身份背景、初始位置、角色特点
4. 选择难度：简单 / 一般 / 困难 / 地狱

### 游戏中
- 自然语言描述行动：`"我向店小二打听消息"`
- 点击系统建议的 4 个选项
- 输入斜杠指令：
  - `/状态` `/任务` `/天道` 查看对应面板
  - `/详细` `/精简` 切换模块4/5的显示详略
  - `/存档` `/读档` 保存/恢复进度
  - `/帮助` 查看所有指令
  - `/换书` 结束当前游戏，开始新小说

### 输出模块说明

每轮输出 10 个模块：
- **直接可见**（纯文本）：模块1剧情推演、模块3天道、模块6世界推演、模块10可选行动
- **折叠面板**（JSON）：模块2任务、模块4校验、模块5工具调用、模块7消耗、模块8战斗、模块9状态
- 模块4和5默认简略显示一行结论，`/详细` 可展开完整 JSON

---

## 手机端体验

- 响应式设计，自适应窄屏
- 底部输入栏带安全区适配（iPhone 刘海/底部横条）
- 右侧悬浮按钮：📊状态 / 📋任务 / 💾存档 / ⋯更多
- 顶部快捷指令栏可横向滚动
- 所有 JSON 模块默认折叠，点击展开

---

## 项目结构

```
mohun-jianghu/
├── index.html                    # 纯前端成品（核心，70KB 单文件）
├── serve.py                      # 本地静态文件服务（可选）
├── 设定要求.txt                   # 游戏设定原文
├── dify/                         # Dify 版（可选，真严谨真并行）
│   ├── prompts/                  # 4 份分层 Prompt
│   │   ├── world_engine.md       # A·世界推演引擎（T1-T5,T11）
│   │   ├── heavenly_will.md      # C·天道守护者（T6-T10）
│   │   ├── canon_keeper.md       # B·原著守门人（T12-T17）
│   │   └── system_prompt.md      # 叙事合并节点（接收三路结果生成10模块）
│   ├── code-nodes/               # Code 节点
│   │   ├── tools.py              # 17 个工具函数（T1-T17）
│   │   ├── merge_results.py      # 三路工具调用合并执行器（新增）
│   │   ├── state_parser.py       # 模块9 解析+状态更新
│   │   ├── intent_classifier.py  # 意图分类
│   │   └── knowledge_base_manager.py
│   └── chatflow-dsl/             # Chatflow 蓝图（3 LLM 并行架构）
├── docker/docker-compose.yml     # Dify 版部署配置
├── scripts/                      # 部署脚本 + 小说预处理
└── docs/README.md                # 本文档
```

---

## 技术架构（纯前端版）

```
用户输入 → buildMessages()（系统提示词+历史+当前状态）
         → callLLM()（流式调用 LLM API）
         → parseOutput()（解析 10 模块）
         → updateStateFromModules()（更新玩家状态）
         → render()（渲染折叠面板 UI）
         → saveGameState()（localStorage 自动存档）
```

### 关键设计

1. **防遗忘**：系统提示词每轮完整注入，含当前轮次和完整玩家状态 JSON
2. **状态闭环**：LLM 输出模块9 JSON → 解析更新 → 下一轮注入系统提示词
3. **历史管理**：保留最近 10 轮对话历史，超过 60 条自动截断
4. **自动存档**：每轮结束自动写入 localStorage，刷新页面不丢失
5. **流式输出**：支持 SSE 流式，实时显示生成内容
6. **模块解析**：正则提取 `模块N【...】` 标题 + ` ```json ` 代码块，分发到对应面板

---

## Dify 版（可选，深度定制 — 真严谨、真并行）

如果需要：知识库 RAG（上传 5-10MB TXT 小说）、Code 节点确定性工具执行、可视化工作流编排、**三角色并行架构**，可使用 Dify 版。

### 三角色并行架构（v2 升级）

将单一 LLM 节点拆为 3 个并行 LLM 节点 + 1 个合并 Code 节点 + 1 个叙事 LLM：

```
                          ┌→ [A] 世界推演 LLM (调用 T1-T5,T11)        ┐
                          │                                            │
意图路由 → 知识检索 ──┬──→┼→ [B] 原著校验 LLM (调用 T12-T17,用检索片段) ┼→ 合并 Code → 叙事 LLM → 状态更新 → 输出
                    │    │                                            │
                    └──→ └→ [C] 天道判定 LLM (调用 T6-T10)            ┘
```

**三大目标**：
- **速度快**：A/B/C 三路并行，总延迟 = max(A,B,C) 而非三者之和
- **长记忆**：game_log 保留 20 轮摘要 + 每份 Prompt 注入 recent_summary + NPC 档案持久化
- **工具准确性**：LLM 只输出工具调用声明（决策），真执行由 Code 节点跑 tools.py 真函数

### 4 份分层 Prompt

| 文件 | 角色 | 工具组 | 输出 |
|---|---|---|---|
| `prompts/world_engine.md` | A·世界推演引擎 | T1 roll_d20 / T2 roll_dice / T3 calc_damage / T4 calc_survival_cost / T5 calc_travel / T11 update_state | 工具调用 JSON 数组 |
| `prompts/heavenly_will.md` | C·天道守护者 | T6 calc_tiandao / T7 calc_breakthrough / T8 calc_relationship / T9 generate_threat / T10 calc_reward | 工具调用 JSON 数组 |
| `prompts/canon_keeper.md` | B·原著守门人 | T12 update_character_state / T13 check_canon / T14 check_npc_persona / T15 calc_cultivation / T16 calc_shop / T17 check_character_state_change | 工具调用 JSON 数组 + 校验结论 |
| `prompts/system_prompt.md` | 叙事合并节点 | 无（接收三路结果） | 完整 10 模块输出 |

### Code 节点

| 文件 | 用途 |
|---|---|
| `code-nodes/tools.py` | 17 个工具函数实现（T1-T17）+ 伪随机种子法 + 工具调度表 |
| `code-nodes/merge_results.py` | **新增** 三路工具调用合并执行器：解析 3 个 LLM 输出的 JSON 数组 → 统一调用 tools.py → 返回汇总结果 |
| `code-nodes/state_parser.py` | 解析叙事 LLM 输出的模块9 JSON → 更新 player_state/game_log/world_time |
| `code-nodes/intent_classifier.py` | 意图分类路由（init_game/game_action/save/load/query/verbose/simple） |
| `code-nodes/knowledge_base_manager.py` | 动态知识库 CRUD |

### 部署 Dify 版

```bash
cd mohun-jianghu
bash scripts/deploy.sh
```

详见 `dify/` 目录下的 4 份 Prompt、5 个 Code 节点和 Chatflow DSL（17 节点 + 21 边 + 9 会话变量）。

### Dify 版 vs 纯前端版

| 特性 | 纯前端版 | Dify 版（v2 并行） |
|---|---|---|
| 部署难度 | 极低（上传1个文件） | 中（需部署 Dify） |
| 大文件 RAG | 不支持 | 支持（5-10MB TXT） |
| 确定性工具 | LLM 自算（可能幻觉） | Code 节点真函数（确定性） |
| 知识库 | 不支持 | 动态知识库 |
| 工作流并行 | 不支持 | 3 LLM 并行 + 合并节点 |
| NPC 原著校验 | LLM 兼任 | 独立 LLM 节点 + 检索增强 |
| 手机体验 | 好 | 取决于 dify-chat |
| 成本 | 仅 LLM API | LLM API ×3 节点 + 服务器 |
| 延迟 | 单次 LLM 调用 | max(A,B,C) + 合并 + 叙事 |

---

## 常见问题

### Q: LLM 几轮后忘记规则？
A: 不会。系统提示词每轮完整注入，包含当前轮次和完整玩家状态。如果仍出现遗忘，检查是否使用了短上下文模型（建议 32K+）。

### Q: API Key 安全吗？
A: Key 存储在浏览器 localStorage，不会上传到 GitHub Pages 或任何中间服务器。前端直接调用 LLM API，是点对点通信。但注意：如果你把仓库设为公开，别人看不到你的 Key（Key 在 localStorage 不在代码里）。

### Q: 支持哪些 LLM？
A: 任何兼容 OpenAI API 格式的服务：DeepSeek、GLM、豆包、OpenAI、Ollama 本地等。

### Q: 想离线玩？
A: 用 Ollama 本地部署模型（如 qwen2.5:14b），Base URL 填 `http://localhost:11434/v1`，API Key 随便填。

### Q: 手机上怎么玩？
A: 部署到 GitHub Pages 后，手机浏览器打开链接即可。建议添加到主屏幕，像 App 一样使用。

### Q: 输出格式乱/JSON 解析失败？
A: LLM 输出格式不完全稳定。前端有容错解析，偶尔某个模块解析失败不影响其他模块显示。换用更强的模型（如 DeepSeek-V3 / GLM-4-Plus）可改善格式稳定性。

---

## 许可证

MIT License. 设定要求.txt 的版权归原作者所有。
