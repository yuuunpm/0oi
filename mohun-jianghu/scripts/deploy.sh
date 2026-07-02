#!/usr/bin/env bash
# 墨魂·江湖 — 快速部署脚本
# 用法：bash deploy.sh

set -e

echo "═══════════════════════════════════════════════════"
echo "  墨魂·江湖 AI 文字 MUD 世界模拟器 — 部署脚本"
echo "═══════════════════════════════════════════════════"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[错误] 未检测到 Docker，请先安装 Docker 和 Docker Compose。"
    exit 1
fi

# 检查 Dify 是否已运行
echo ""
echo "[步骤 1] 检查 Dify 服务..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:80/v1 | grep -q "200\|401"; then
    echo "  ✓ Dify 已在运行（http://localhost:80）"
else
    echo "  ✗ 未检测到 Dify，开始部署 Dify..."
    echo ""
    echo "  请先按 Dify 官方文档部署 Dify："
    echo "    git clone https://github.com/langgenius/dify.git"
    echo "    cd dify/docker"
    echo "    cp .env.example .env"
    echo "    docker compose up -d"
    echo ""
    echo "  Dify 部署完成后再运行本脚本。"
    exit 1
fi

# 部署 dify-chat + ollama
echo ""
echo "[步骤 2] 部署 dify-chat（前端）和 Ollama（embedding）..."
cd "$(dirname "$0")/../docker"
docker compose up -d

echo ""
echo "[步骤 3] 等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "[步骤 4] 检查服务状态："

if curl -s -o /dev/null -w "%{http_code}" http://localhost:3200 | grep -q "200\|302"; then
    echo "  ✓ dify-chat 运行中 → http://localhost:3200"
else
    echo "  ✗ dify-chat 启动失败，请检查日志：docker logs mohun-dify-chat"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags | grep -q "200"; then
    echo "  ✓ Ollama 运行中 → http://localhost:11434"
else
    echo "  ! Ollama 仍在启动中，请稍等..."
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  部署完成！后续配置步骤："
echo "═══════════════════════════════════════════════════"
echo ""
echo "1. 在 Dify 中配置 LLM 模型（推荐 DeepSeek-V3 或 GLM-4）"
echo "   → http://localhost:80 → 设置 → 模型供应商"
echo ""
echo "2. 在 Dify 中配置 Embedding 模型（Ollama bge-m3）"
echo "   → 设置 → 模型供应商 → Ollama"
echo "   → Base URL: http://host.docker.internal:11434"
echo "   → Model: bge-m3"
echo ""
echo "3. 在 Dify 中导入墨魂江湖 Chatflow"
echo "   → 创建空白应用 → 导入 DSL → 选择 dify/chatflow-dsl/mohun-jianghu-chatflow.json"
echo "   → 注意：DSL 中的 code_file 路径需手动复制 dify/code-nodes/*.py 内容到对应 Code 节点"
echo ""
echo "4. 在 Dify 中创建应用并获取 API Key"
echo "   → 应用 → 访问 API → API 密钥"
echo ""
echo "5. 在 dify-chat 中添加应用"
echo "   → http://localhost:3200"
echo "   → 管理员登录（密码：mohun_admin_2026）"
echo "   → 添加应用 → 填入 Dify API Key"
echo ""
echo "6. 开始游戏！输入小说名即可开局"
echo ""
