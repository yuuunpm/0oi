"""
墨魂·江湖 — Dify 版等效模拟器（Flask 后端）
==========================================
用 Flask 等效实现 Dify 三角色并行工作流：
  意图路由 → 知识检索(简化) → 3 LLM 并行 → merge_results → 叙事 LLM → 状态更新

复用：
  - mohun-jianghu/dify/prompts/*.md（4 份分层 Prompt）
  - mohun-jianghu/dify/code-nodes/tools.py（17 个工具函数）
  - mohun-jianghu/dify/code-nodes/merge_results.py（合并执行器）

启动：python3 app.py
"""

import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from flask import Flask, request, jsonify, render_template

# ============================================================
# 路径配置
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DIFY_DIR = BASE_DIR.parent / "mohun-jianghu" / "dify"
PROMPTS_DIR = DIFY_DIR / "prompts"
CODE_NODES_DIR = DIFY_DIR / "code-nodes"

import sys
sys.path.insert(0, str(CODE_NODES_DIR))

# 导入工具和合并器
from tools import TOOL_REGISTRY, make_seed, parse_tool_calls
from merge_results import _safe_parse_calls, _execute_call

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))


# ============================================================
# Prompt 模板渲染（简易 Jinja2 替换）
# ============================================================
def render_prompt(template_text: str, vars_dict: dict) -> str:
    """简易变量替换：{{var}} → vars_dict[var]"""
    out = template_text
    for k, v in vars_dict.items():
        # 字典/JSON 类型的值要美化
        if isinstance(v, (dict, list)):
            v_str = json.dumps(v, ensure_ascii=False, indent=2)
        else:
            v_str = str(v)
        out = out.replace("{{" + k + "}}", v_str)
    return out


def load_prompt(name: str) -> str:
    """加载 Prompt 文件"""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


# ============================================================
# LLM API 调用（OpenAI 兼容格式）
# ============================================================
def call_llm(base_url: str, api_key: str, model: str,
             system_prompt: str, user_prompt: str,
             temperature: float = 0.5, max_tokens: int = 2048,
             timeout: int = 90) -> dict:
    """调用 LLM API，返回 {text, elapsed, error}"""
    t0 = time.time()
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        elapsed = round(time.time() - t0, 2)
        if resp.status_code != 200:
            return {"text": "", "elapsed": elapsed,
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return {"text": text, "elapsed": elapsed, "error": None}
    except Exception as e:
        return {"text": "", "elapsed": round(time.time() - t0, 2), "error": str(e)}


# ============================================================
# 三角色并行执行
# ============================================================
def run_parallel_llm(config: dict, user_input: str, state: dict) -> dict:
    """
    并行执行 3 个 LLM 节点（A 世界推演 / B 原著守门人 / C 天道守护者）
    返回各节点结果 + 总耗时
    """
    base_url = config["baseURL"]
    api_key = config["apiKey"]
    model = config["model"]

    # 公共变量
    common_vars = {
        "novel_name": state.get("novel_name", ""),
        "round_count": state.get("round_count", 0),
        "world_time": state.get("world_time", {"年": "", "月": "", "日": 1, "时辰": "辰时"}),
        "player_state": state.get("player_state", {}),
        "recent_summary": state.get("game_log", []),
        "user_action": user_input,
        "player_location": state.get("player_state", {}).get("位置", "未知"),
        "tiandao_state": state.get("player_state", {}).get("天道", {}),
        "npcs_involved": "（由 LLM 自行从玩家行动中识别）",
        "items_involved": "（由 LLM 自行从玩家行动中识别）",
        "canon_fragments": "（无知识库，由 LLM 基于训练知识推演）",
        "has_nitian": state.get("player_state", {}).get("天道", {}).get("逆天改命", False),
    }

    # 任务定义
    tasks = {
        "world": {
            "prompt_file": "world_engine.md",
            "user_prompt": f"玩家本轮行动：{user_input}\n\n请列出需要调用的本角色工具（roll_d20/roll_dice/calc_damage/calc_survival_cost/calc_travel/update_state），输出 JSON 数组。",
            "temperature": 0.3,
            "max_tokens": 2048
        },
        "heavenly": {
            "prompt_file": "heavenly_will.md",
            "user_prompt": f"请基于玩家本轮行动判定天道变化，列出需要调用的本角色工具（calc_tiandao/calc_breakthrough/calc_relationship/generate_threat/calc_reward），输出 JSON 数组。",
            "temperature": 0.4,
            "max_tokens": 2048
        },
        "canon": {
            "prompt_file": "canon_keeper.md",
            "user_prompt": f"请基于玩家本轮行动，执行六项校验和 NPC 应然状态查询，列出需要调用的本角色工具（update_character_state/check_canon/check_npc_persona/calc_cultivation/calc_shop/check_character_state_change），输出 JSON 数组 + 一行校验结论。",
            "temperature": 0.3,
            "max_tokens": 2048
        }
    }

    def run_one(key: str, task: dict) -> tuple:
        sys_prompt = render_prompt(load_prompt(task["prompt_file"]), common_vars)
        r = call_llm(base_url, api_key, model, sys_prompt, task["user_prompt"],
                     temperature=task["temperature"], max_tokens=task["max_tokens"])
        return key, r

    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run_one, k, t) for k, t in tasks.items()]
        for f in as_completed(futures):
            key, r = f.result()
            results[key] = r
    parallel_elapsed = round(time.time() - t0, 2)

    return {
        "world": results["world"],
        "heavenly": results["heavenly"],
        "canon": results["canon"],
        "parallel_elapsed": parallel_elapsed
    }


# ============================================================
# 合并执行三路工具调用
# ============================================================
def merge_tool_calls(parallel_results: dict, state: dict) -> dict:
    """合并三路工具调用声明，执行真函数"""
    t0 = time.time()
    player_state = state.get("player_state", {})
    if isinstance(player_state, str):
        try:
            player_state = json.loads(player_state)
        except Exception:
            player_state = {}
    world_time = state.get("world_time", {})
    if isinstance(world_time, str):
        try:
            world_time = json.loads(world_time)
        except Exception:
            world_time = {"日": 1}
    round_count = state.get("round_count", 0)

    world_list = _safe_parse_calls(parallel_results["world"]["text"])
    heavenly_list = _safe_parse_calls(parallel_results["heavenly"]["text"])
    canon_list = _safe_parse_calls(parallel_results["canon"]["text"])

    world_results = [_execute_call(c, player_state, world_time, round_count) for c in world_list]
    heavenly_results = [_execute_call(c, player_state, world_time, round_count) for c in heavenly_list]
    canon_results = [_execute_call(c, player_state, world_time, round_count) for c in canon_list]

    all_results = world_results + heavenly_results + canon_results

    # 执行日志
    log_lines = []
    for i, r in enumerate(all_results, 1):
        tool = r.get("tool", "?")
        if "error" in r:
            log_lines.append(f"[{i}] {tool} ERROR: {r['error']}")
        else:
            log_lines.append(f"[{i}] {tool}: {json.dumps(r.get('result', {}), ensure_ascii=False)}")
    exec_log = "\n".join(log_lines) if log_lines else "无工具调用"

    elapsed = round(time.time() - t0, 3)
    return {
        "world_tool_results": json.dumps(world_results, ensure_ascii=False),
        "heavenly_tool_results": json.dumps(heavenly_results, ensure_ascii=False),
        "canon_tool_results": json.dumps(canon_results, ensure_ascii=False),
        "all_tool_results": json.dumps(all_results, ensure_ascii=False),
        "tool_count": len(all_results),
        "exec_log": exec_log,
        "elapsed": elapsed
    }


# ============================================================
# 叙事合并 LLM
# ============================================================
def run_narrator(config: dict, user_input: str, state: dict, merged: dict, parallel: dict) -> dict:
    """调用叙事 LLM 生成最终 10 模块"""
    common_vars = {
        "novel_name": state.get("novel_name", ""),
        "round_count": state.get("round_count", 0),
        "world_time": state.get("world_time", {}),
        "user_action": user_input,
        "player_state": state.get("player_state", {}),
        "recent_summary": state.get("game_log", []),
        "world_tool_results": merged["world_tool_results"],
        "heavenly_tool_results": merged["heavenly_tool_results"],
        "canon_tool_results": merged["canon_tool_results"],
    }
    sys_prompt = render_prompt(load_prompt("system_prompt.md"), common_vars)
    user_prompt = f"玩家本轮行动：{user_input}\n\n请基于三路工具执行结果，生成完整的 10 模块输出。叙事中的所有数值必须与工具 RESULT 一致。"

    # 叙事用更高 max_tokens
    return call_llm(config["baseURL"], config["apiKey"], config["model"],
                    sys_prompt, user_prompt, temperature=0.85, max_tokens=6144, timeout=120)


# ============================================================
# 初始化游戏（世界初始化）
# ============================================================
def run_init_world(config: dict, novel_name: str) -> dict:
    """世界初始化 LLM 调用"""
    sys_prompt = f"""你是【墨魂·江湖】世界初始化引擎。基于小说《{novel_name}》生成：
1）世界观简述（200字内）
2）时间线起点
3）主要势力格局
4）4个可选开局身份（最后一个为自定义），每个标注：身份名称与背景、初始时间点、初始位置、优势与劣势、初始必做任务预览。

输出格式：
## 世界观
...
## 时间线起点
...
## 主要势力
...
## 可选身份
1. [身份名] - [背景]
   - 初始时间：...
   - 初始位置：...
   - 优势：...
   - 劣势：...
   - 初始任务：...
2. ...
3. ...
4. 【自定义】玩家可手动输入角色名称、身份背景、初始位置、特点
"""
    user_prompt = f"请基于小说《{novel_name}》开始世界初始化。"
    return call_llm(config["baseURL"], config["apiKey"], config["model"],
                    sys_prompt, user_prompt, temperature=0.9, max_tokens=4096, timeout=120)


# ============================================================
# 路由
# ============================================================
@app.route("/")
def index():
    return render_template("dify_sim.html")


@app.route("/api/init", methods=["POST"])
def api_init():
    """世界初始化"""
    data = request.json
    config = data.get("config", {})
    novel_name = data.get("novel_name", "").strip()
    if not novel_name:
        return jsonify({"error": "请输入小说名称"}), 400
    if not config.get("apiKey"):
        return jsonify({"error": "请先配置 API Key"}), 400

    r = run_init_world(config, novel_name)
    return jsonify({
        "text": r["text"],
        "elapsed": r["elapsed"],
        "error": r["error"]
    })


@app.route("/api/action", methods=["POST"])
def api_action():
    """玩家行动 → 三角色并行 → 合并 → 叙事"""
    data = request.json
    config = data.get("config", {})
    user_input = data.get("user_input", "").strip()
    state = data.get("state", {})

    if not user_input:
        return jsonify({"error": "请输入行动"}), 400
    if not config.get("apiKey"):
        return jsonify({"error": "请先配置 API Key"}), 400

    timeline = {}

    # 1. 三角色并行
    t0 = time.time()
    parallel = run_parallel_llm(config, user_input, state)
    timeline["parallel"] = parallel["parallel_elapsed"]

    # 检查并行节点错误
    errors = []
    for k in ["world", "heavenly", "canon"]:
        if parallel[k]["error"]:
            errors.append(f"{k}: {parallel[k]['error']}")
    if errors:
        # 即使有错误也继续，叙事 LLM 会基于部分结果生成
        pass

    # 2. 合并工具调用
    t1 = time.time()
    merged = merge_tool_calls(parallel, state)
    timeline["merge"] = merged["elapsed"]

    # 3. 叙事 LLM
    t2 = time.time()
    narrator = run_narrator(config, user_input, state, merged, parallel)
    timeline["narrator"] = narrator["elapsed"]

    timeline["total"] = round(time.time() - t0, 2)

    return jsonify({
        "narrator_text": narrator["text"],
        "narrator_error": narrator["error"],
        "tool_count": merged["tool_count"],
        "exec_log": merged["exec_log"],
        "all_tool_results": merged["all_tool_results"],
        "parallel": {
            "world": {"elapsed": parallel["world"]["elapsed"], "error": parallel["world"]["error"]},
            "heavenly": {"elapsed": parallel["heavenly"]["elapsed"], "error": parallel["heavenly"]["error"]},
            "canon": {"elapsed": parallel["canon"]["elapsed"], "error": parallel["canon"]["error"]},
        },
        "timeline": timeline
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "mohun-jianghu-dify-simulator"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
