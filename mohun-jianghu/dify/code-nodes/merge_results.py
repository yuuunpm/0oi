"""
Dify Code 节点：三路工具调用合并执行器（merge_results）
========================================================
用途：并行接收 3 个 LLM 节点（world_engine / heavenly_will / canon_keeper）
      输出的工具调用声明 JSON，统一调用 tools.py 执行，返回汇总结果。

      叙事节点（narrator）会拿到这三路结果作为上下文，生成最终 10 模块。

输入参数（Dify Code 节点输入）：
  - world_calls: str       角色 A（世界推演）输出的工具调用 JSON 数组
  - heavenly_calls: str    角色 C（天道）输出的工具调用 JSON 数组
  - canon_calls: str       角色 B（原著守门人）输出的工具调用 JSON 数组
  - player_state: str      当前玩家状态 JSON
  - world_time: str        当前世界时间 JSON
  - round_count: number    当前轮次

输出参数：
  - world_tool_results: str     A 路工具执行结果 JSON
  - heavenly_tool_results: str  C 路工具执行结果 JSON
  - canon_tool_results: str     B 路工具执行结果 JSON
  - all_tool_results: str       三路合并后的完整结果（供模块5 工具调用记录）
  - tool_count: number          本轮工具调用总次数
  - exec_log: str               执行日志（供 /验算 展示）
  - merged_state_changes: str   合并后的状态变更字典（供 update_state 写回）
"""

import json
import sys
import os

# 引入 tools.py（同目录）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import (
    TOOL_REGISTRY, make_seed, parse_tool_calls,
    tool_roll_d20, tool_roll_dice, tool_calc_tiandao,
    tool_calc_breakthrough, tool_calc_cultivation,
)


def _safe_parse_calls(text: str) -> list:
    """从 LLM 输出中解析工具调用数组，兼容多种格式"""
    if not text or not text.strip():
        return []
    text = text.strip()

    # 优先尝试解析为 JSON 数组
    try:
        # 提取第一个 JSON 数组（可能被 ```json 包裹或前后有说明文字）
        import re
        match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', text)
        if match:
            arr = json.loads(match.group(0))
            if isinstance(arr, list):
                return arr
    except Exception:
        pass

    # 兼容旧格式：【工具调用】TOOL: xxx PARAMS: {...}
    calls = parse_tool_calls(text)
    if calls:
        return [{"tool": c["tool"], "params": c.get("params", {}), "reason": ""} for c in calls]

    return []


def _execute_call(call: dict, player_state: dict, world_time: dict,
                  round_count: int) -> dict:
    """执行单次工具调用，返回结构化结果"""
    tool_name = call.get("tool", "")
    params = call.get("params", {}) or {}
    reason = call.get("reason", "")

    if tool_name not in TOOL_REGISTRY:
        return {"tool": tool_name, "params": params, "reason": reason,
                "error": f"未知工具: {tool_name}"}

    # 构造种子
    action_type = params.get("action_type", params.get("activity", "通用"))
    seed = make_seed(world_time, round_count, action_type)

    try:
        # 对需要种子的工具注入 seed
        if tool_name in ("roll_d20", "roll_dice", "calc_breakthrough",
                         "calc_cultivation", "generate_threat", "calc_reward"):
            r = TOOL_REGISTRY[tool_name](seed, **{k: v for k, v in params.items()
                                                  if k != "action_type"})
        elif tool_name == "calc_tiandao":
            # 从玩家状态读取当前天道数值
            td = player_state.get("天道", {})
            r = tool_calc_tiandao(
                params.get("action_type", "偏离剧情"),
                params.get("magnitude", 1),
                td.get("偏离度", 0), td.get("气运", 0),
                td.get("逆天值", 0), player_state.get("难度", "一般"),
                params.get("cause_chain", "")
            )
        elif tool_name == "calc_breakthrough":
            td_attr = player_state.get("属性", {})
            r = tool_calc_breakthrough(
                seed,
                params.get("current_realm", "入门"),
                params.get("target_realm", "初窥门径"),
                td_attr.get("根骨", 10),
                params.get("resources", 0),
                player_state.get("难度", "一般")
            )
        elif tool_name == "calc_cultivation":
            td_attr = player_state.get("属性", {})
            r = tool_calc_cultivation(
                seed, params.get("skill_name", ""),
                params.get("current_proficiency", 0),
                td_attr.get("悟性", 10),
                params.get("duration", 1), params.get("resources", 0),
                player_state.get("难度", "一般")
            )
        else:
            # 通用调用
            r = TOOL_REGISTRY[tool_name](**params)

        return {"tool": tool_name, "params": params, "reason": reason,
                "result": r}
    except Exception as e:
        return {"tool": tool_name, "params": params, "reason": reason,
                "error": str(e)}


def main(world_calls: str, heavenly_calls: str, canon_calls: str,
         player_state: str, world_time: str, round_count: number) -> dict:
    """Dify Code 节点主入口"""
    # 解析状态
    try:
        ps = json.loads(player_state) if player_state else {}
    except Exception:
        ps = {}
    try:
        wt = json.loads(world_time) if world_time else {"日": 1}
    except Exception:
        wt = {"日": 1}

    # 解析三路调用声明
    world_list = _safe_parse_calls(world_calls)
    heavenly_list = _safe_parse_calls(heavenly_calls)
    canon_list = _safe_parse_calls(canon_calls)

    # 分别执行
    world_results = [_execute_call(c, ps, wt, round_count) for c in world_list]
    heavenly_results = [_execute_call(c, ps, wt, round_count) for c in heavenly_list]
    canon_results = [_execute_call(c, ps, wt, round_count) for c in canon_list]

    # 汇总
    all_results = world_results + heavenly_results + canon_results
    tool_count = len(all_results)

    # 执行日志
    log_lines = []
    for i, r in enumerate(all_results, 1):
        tool = r.get("tool", "?")
        if "error" in r:
            log_lines.append(f"[{i}] {tool} ERROR: {r['error']}")
        else:
            log_lines.append(f"[{i}] {tool}: {json.dumps(r.get('result', {}), ensure_ascii=False)}")
    exec_log = "\n".join(log_lines) if log_lines else "无工具调用"

    # 合并状态变更（供 narrator 写回 player_state）
    # 主要是天道变化、伤害、消耗、关系等
    merged_changes = {}
    for r in all_results:
        if "result" not in r:
            continue
        res = r["result"]
        tool = r["tool"]
        if tool == "calc_tiandao":
            td = merged_changes.setdefault("天道", {})
            td["偏离度"] = res.get("new_deviation", td.get("偏离度", 0))
            td["气运"] = res.get("new_luck", td.get("气运", 0))
            td["逆天值"] = res.get("new_nitian", td.get("逆天值", 0))
            td["天罚等级"] = res.get("punishment_level", td.get("天罚等级", "无"))
            td["逆天改命"] = res.get("nitian_chengming_triggered", False)
        elif tool == "calc_damage":
            combat = merged_changes.setdefault("战斗", {})
            # 伤害扣气血由 narrator 在叙事中体现
            combat["本轮伤害"] = res.get("lethal", 0)
        elif tool == "calc_survival_cost":
            surv = merged_changes.setdefault("生存", {})
            surv["饱食度_delta"] = res.get("food", 0)
            surv["体力_delta"] = res.get("stamina", 0)
            surv["清洁度_delta"] = res.get("cleanliness", 0)
            surv["金钱_delta"] = res.get("money", 0)
        elif tool == "calc_relationship":
            rel = merged_changes.setdefault("关系", {})
            npc好感 = rel.setdefault("NPC好感", {})
            npc好感[r.get("params", {}).get("target", "?")] = res.get("new_affection", 0)

    return {
        "world_tool_results": json.dumps(world_results, ensure_ascii=False),
        "heavenly_tool_results": json.dumps(heavenly_results, ensure_ascii=False),
        "canon_tool_results": json.dumps(canon_results, ensure_ascii=False),
        "all_tool_results": json.dumps(all_results, ensure_ascii=False),
        "tool_count": tool_count,
        "exec_log": exec_log,
        "merged_state_changes": json.dumps(merged_changes, ensure_ascii=False),
    }
