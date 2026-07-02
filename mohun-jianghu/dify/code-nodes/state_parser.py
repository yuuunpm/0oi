"""
Dify Code 节点：状态解析与更新
================================
用途：从 LLM 输出中解析模块9（状态面板）的 JSON，更新会话变量 player_state。
      同时解析模块7（时间消耗）更新 world_time，并追加 game_log 摘要。

输入参数（Dify Code 节点输入）：
  - llm_output: str        LLM 完整输出文本
  - player_state: str      当前会话变量中的玩家状态 JSON
  - world_time: str        当前会话变量中的世界时间 JSON
  - game_log: str          当前会话变量中的游戏日志（JSON 数组字符串）
  - round_count: number    当前轮次

输出参数：
  - new_player_state: str  更新后的玩家状态 JSON
  - new_world_time: str    更新后的世界时间 JSON
  - new_game_log: str      追加本轮摘要后的游戏日志
  - new_round_count: number 新轮次
  - parse_error: str       解析错误信息（成功则为空字符串）
"""

import json
import re


def _extract_json_blocks(text: str) -> list:
    """从文本中提取所有 ```json ... ``` 代码块内容"""
    pattern = r"```json\s*([\s\S]*?)```"
    matches = re.findall(pattern, text)
    return matches


def _try_parse_json(text: str):
    """容错 JSON 解析：尝试多种方式解析，返回 (obj, error)"""
    text = text.strip()
    # 去除可能的尾随逗号
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    try:
        return json.loads(text), None
    except Exception as e:
        return None, str(e)


def _find_state_json(json_blocks: list):
    """从多个 JSON 块中识别玩家状态 JSON（含 '姓名' 和 '属性' 字段）"""
    for block in json_blocks:
        obj, err = _try_parse_json(block)
        if obj is None:
            continue
        if isinstance(obj, dict) and "姓名" in obj and "属性" in obj:
            return obj, None
    return None, "未找到包含'姓名'和'属性'字段的状态JSON"


def _find_module7_json(json_blocks: list):
    """识别模块7（时间与消耗）JSON：含 '本轮耗时' 字段"""
    for block in json_blocks:
        obj, err = _try_parse_json(block)
        if obj is None:
            continue
        if isinstance(obj, dict) and "本轮耗时" in obj:
            return obj, None
    return None, "未找到模块7"


def _clamp(value: int, lo: int, hi: int) -> int:
    """边界约束"""
    return max(lo, min(hi, value))


def _validate_and_clamp_state(state: dict) -> dict:
    """对玩家状态做边界校验，确保数值合法"""
    try:
        # 战斗
        c = state.get("战斗", {})
        c["气血"] = _clamp(int(c.get("气血", 0)), 0, int(c.get("气血上限", 100)))
        c["内力"] = _clamp(int(c.get("内力", 0)), 0, int(c.get("内力上限", 0)))
        # 生存
        s = state.get("生存", {})
        for k in ["饱食度", "体力", "清洁度"]:
            if k in s:
                s[k] = _clamp(int(s.get(k, 0)), 0, 100)
        # 属性
        a = state.get("属性", {})
        for k in a:
            a[k] = _clamp(int(a[k]), 1, 99)
        # 天道
        t = state.get("天道", {})
        for k in ["关注度", "气运", "偏离度"]:
            if k in t:
                t[k] = _clamp(int(t.get(k, 0)), 0, 100)
        # 任务进度
        for task in state.get("任务", {}).get("必做任务", []):
            if "进度" in task:
                task["进度"] = _clamp(int(task["进度"]), 0, 100)
    except Exception:
        # 边界校验失败时保留原状态
        pass
    return state


def _generate_round_summary(round_num: int, llm_output: str) -> dict:
    """生成本轮日志摘要（用于 game_log，解决长对话遗忘）"""
    # 提取模块6世界推演的前 200 字作为摘要
    summary = ""
    m6_match = re.search(r"模块6【世界推演】\s*([\s\S]*?)(?=━━━|模块[0-9]|```json|$)", llm_output)
    if m6_match:
        summary = m6_match.group(1).strip()[:200]
    return {
        "轮次": round_num,
        "摘要": summary
    }


def main(llm_output: str, player_state: str, world_time: str,
         game_log: str, round_count: number) -> dict:
    """主函数：Dify Code 节点入口"""
    parse_error = ""
    new_player_state = player_state
    new_world_time = world_time
    new_round_count = round_count + 1
    
    # 1. 解析 JSON 代码块
    json_blocks = _extract_json_blocks(llm_output)
    
    # 2. 解析并更新玩家状态
    new_state, err = _find_state_json(json_blocks)
    if new_state is not None:
        new_state = _validate_and_clamp_state(new_state)
        new_player_state = json.dumps(new_state, ensure_ascii=False)
    else:
        parse_error += f"状态解析失败：{err}；"
    
    # 3. 解析模块7并更新世界时间
    m7, err = _find_module7_json(json_blocks)
    if m7 is not None:
        # 从模块7提取耗时，更新 world_time
        # 注意：完整的时辰/日期推算逻辑由 LLM 在叙事中完成，这里只做记录
        # 复杂的时辰进位（如子时跨日）保留给 LLM 在下一轮的 world_time 中体现
        try:
            current_wt = json.loads(world_time) if world_time else {}
            # 简单记录：保留原 world_time，让 LLM 在下一轮输出中体现推进
            new_world_time = json.dumps(current_wt, ensure_ascii=False)
        except Exception:
            pass
    else:
        parse_error += f"模块7解析失败：{err}；"
    
    # 4. 追加游戏日志摘要（保留最近 20 轮）
    try:
        log_list = json.loads(game_log) if game_log else []
    except Exception:
        log_list = []
    summary = _generate_round_summary(round_count, llm_output)
    log_list.append(summary)
    if len(log_list) > 20:
        log_list = log_list[-20:]
    new_game_log = json.dumps(log_list, ensure_ascii=False)
    
    return {
        "new_player_state": new_player_state,
        "new_world_time": new_world_time,
        "new_game_log": new_game_log,
        "new_round_count": new_round_count,
        "parse_error": parse_error
    }
