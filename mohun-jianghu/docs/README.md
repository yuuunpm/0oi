# 墨魂·江湖 AI 文字 MUD 世界模拟器

> 基于 Dify + dify-chat 的复杂中文文字角色扮演游戏引擎，支持动态切换小说原著世界。
> 适配设定要求.txt 中定义的全部游戏机制（10 模块输出、17 工具调用、天道系统、原著校验等）。

## 核心特性

- **永不遗忘**：系统提示词每轮强制注入，规则永远不会丢失
- **动态小说**：支持随时换书（射雕→三国→西游），每局独立知识库
- **大文件 RAG**：支持上传 5-10MB TXT 小说，按章回切分索引
- **状态持久化**：会话变量保存完整玩家状态，跨轮自动延续
- **确定性工具**：17 个核心工具用 Python 实现，LLM 不再自算数值
- **折叠面板 UI**：dify-chat 原生支持 `<details>` 折叠，JSON 模块默认收起

## 目录结构

```
mohun-jianghu/
├── dify/
│   ├── prompts/
│   │   └── system_prompt.md          # 系统提示词（含会话变量注入点）
│   ├── code-nodes/
│   │   ├── intent_classifier.py      # 意图分类器（开局/行动/指令/换书）
│   │   ├── state_parser.py           # 状态解析与更新（模块9→会话变量）
│   │   ├── tools.py                  # 17个核心工具函数（确定性计算）
│   │   └── knowledge_base_manager.py # 动态知识库管理
│   └── chatflow-dsl/
│       └── mohun-jianghu-chatflow.json # Chatflow DSL 配置
├── docker/
│   └── docker-compose.yml            # dify-chat + Ollama 一键部署
├── scripts/
│   ├── deploy.sh                     # 快速部署脚本
│   └── preprocess_novel.py           # 小说预处理（按章回切分）
└── docs/
    └── README.md                     # 本文档
```

## 快速开始

### 前提条件
- Docker 20+ 和 Docker Compose
- 已部署 Dify（[官方文档](https://docs.dify.ai/)）

### 1. 部署前端和 Embedding

```bash
cd mohun-jianghu
bash scripts/deploy.sh
```

部署完成后：
- dify-chat：http://localhost:3200
- Ollama：http://localhost:11434（自动拉取 bge-m3 embedding 模型）

### 2. 在 Dify 中配置模型

1. 打开 Dify → 设置 → 模型供应商
2. 添加 LLM（推荐 DeepSeek-V3 / GLM-4 / 豆包 API，长上下文+中文强）
3. 添加 Embedding：
   - 供应商：Ollama
   - Base URL：`http://host.docker.internal:11434`
   - Model：`bge-m3`

### 3. 导入 Chatflow

1. Dify → 创建空白应用 → 导入 DSL
2. 选择 `dify/chatflow-dsl/mohun-jianghu-chatflow.json`
3. **重要**：手动将 `dify/code-nodes/*.py` 的内容复制到对应的 Code 节点

### 4. 配置会话变量

在 Chatflow 编排页面确认以下会话变量已创建：

| 变量名 | 类型 | 默认值 |
|---|---|---|
| `novel_name` | string | `""` |
| `game_phase` | string | `"not_started"` |
| `player_state` | string | `"{}"` |
| `world_time` | string | `{"年":"","月":"","日":1,"时辰":"辰时"}` |
| `round_count` | number | `0` |
| `game_log` | string | `"[]"` |
| `dataset_id` | string | `""` |
| `display_mode` | string | `"simple"` |

### 5. 获取 API Key 并接入 dify-chat

1. Dify 应用页面 → 访问 API → 创建 API 密钥
2. 打开 dify-chat（http://localhost:3200）
3. 管理员登录（密码：`mohun_admin_2026`）
4. 添加应用 → 填入 Dify API Key

### 6. 开始游戏

在 dify-chat 输入框直接输入小说名即可开局：
```
射雕英雄传
```

系统会自动初始化世界，生成 4 个可选身份，然后进入游戏。

## 玩法说明

### 开局
- 输入小说名 → 系统初始化世界 → 选择身份 → 选择难度 → 开始游戏
- 也可上传 TXT 小说文件到知识库（5-10MB 支持）

### 游戏中
- 自然语言描述行动：`"我向店小二打听最近江湖上的传闻"`
- 选择系统建议的 4 个选项之一
- 输入斜杠指令：
  - `/状态` `/任务` `/天道` 查看对应面板
  - `/详细` `/精简` 切换模块4/5的显示详略
  - `/存档` `/读档` 保存/恢复进度
  - `/换书 三国演义` 结束当前游戏，开始新小说

### 输出模块说明

每轮输出 10 个模块：
- **直接可见**（纯文本）：模块1剧情推演、模块3天道、模块6世界推演、模块10可选行动
- **折叠面板**（JSON）：模块2任务、模块4校验、模块5工具调用、模块7消耗、模块8战斗、模块9状态

## 技术架构

```
用户输入 → 意图分类器 → 路由
                          ├── 开局/换书 → 世界初始化 LLM
                          ├── 系统指令 → 直接响应
                          └── 游戏行动 → 知识库RAG → 游戏引擎LLM → 状态更新 → 输出
```

### 关键设计

1. **防遗忘**：系统提示词含 `{{player_state}}` `{{game_log}}` 等变量占位符，每轮自动注入最新值
2. **状态闭环**：LLM 输出模块9 JSON → Code 节点解析 → 写入会话变量 → 下一轮注入系统提示词
3. **游戏日志**：每轮摘要存入 `game_log`，保留最近 20 轮，解决长对话遗忘
4. **确定性工具**：17 个工具用 Python 实现，伪随机种子 = 日数 + 轮次 + 行动代号
5. **动态知识库**：每局游戏独立知识库，换书时清理旧库

## 常见问题

### Q: LLM 几轮后忘记规则？
A: 不会。系统提示词每轮强制注入，不依赖对话历史。如果仍出现遗忘，检查系统提示词是否正确配置在 LLM 节点的 System Prompt 中（而非开场白）。

### Q: 5-10MB 小说检索不准？
A: 用 `scripts/preprocess_novel.py` 按章回切分后再上传，知识库检索策略选"混合检索"（向量+关键词），Top-K 设为 6-8。

### Q: 想用本地模型？
A: Ollama 拉取生成模型：`docker exec mohun-ollama ollama pull qwen2.5:14b`，在 Dify 中配置 Ollama 作为 LLM 供应商。

### Q: dify-chat 的 `<details>` 不渲染？
A: 确认使用 lexmin/dify-chat 镜像（非 Dify 自带 UI）。dify-chat 内部用 react-markdown + rehype-raw，支持 `<details>` 标签。

## 许可证

本项目代码遵循 MIT 许可证。设定要求.txt 的版权归原作者所有。
