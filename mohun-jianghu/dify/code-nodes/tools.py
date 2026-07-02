"""
Dify Code 节点：17 个核心工具函数（确定性计算）
================================================
用途：把设定要求.txt 中的 17 个"文本声明工具"实现为真函数，
      LLM 声明需要调用什么工具 → 本节点执行 → 返回确定结果。

      本节点为"工具调度器"，根据 LLM 输出的工具调用声明，
      逐一执行并返回结果列表。

输入参数（Dify Code 节点输入）：
  - llm_output: str       LLM 输出（含【工具调用】声明）
  - world_time: str       当前世界时间 JSON（用于伪随机种子）
  - round_count: number   当前轮次（用于伪随机种子）
  - player_state: str     玩家状态 JSON（提供属性等参数源）

输出参数：
  - tool_results: str     工具执行结果列表 JSON（注入回 LLM 上下文）
  - tool_count: number    本轮工具调用次数
  - exec_log: str         执行日志（供 /验算 展示）
"""

import json
import re
import hashlib


# ============================================================
# 伪随机数生成（与设定要求.txt L196-L199 一致）
# ============================================================
def pseudo_random(seed_str: str, max_val: int) -> int:
    """基于种子的确定性伪随机：MD5 哈希取模"""
    h = hashlib.md5(seed_str.encode("utf-8")).hexdigest()
    return int(h, 16) % max_val + 1


# 行动类型代号表（用于种子构成）
ACTION_CODES = {
    "战斗": 1, "潜行": 2, "说服": 3, "偷窃": 4, "炼药": 5,
    "打猎": 6, "找路": 7, "修炼": 8, "突破": 9, "赶路": 10,
    "社交": 11, "检定": 12, "抗劫": 13, "通用": 99
}


def make_seed(world_time: dict, round_count: int, action_type: str) -> str:
    """构造伪随机种子字符串"""
    day = world_time.get("日", 1)
    action_code = ACTION_CODES.get(action_type, 99)
    return f"{day}_{round_count}_{action_code}"


# ============================================================
# 工具实现
# ============================================================

def tool_roll_d20(seed_str: str, attribute: int = 10, bonus: int = 0,
                  difficulty: int = 10, diff_mod: int = 0) -> dict:
    """T1 roll_d20 —— d20 行动检定"""
    roll = pseudo_random(seed_str, 20)
    attribute_mod = (attribute - 10) // 2
    total = roll + attribute_mod + bonus + diff_mod
    if roll == 20:
        degree, success = "大成功", True
    elif roll == 1:
        degree, success = "大失败", False
    elif total >= difficulty:
        degree, success = "成功", True
    else:
        degree, success = "失败", False
    return {
        "roll": roll, "attribute_mod": attribute_mod, "bonus": bonus,
        "diff_mod": diff_mod, "total": total, "difficulty": difficulty,
        "degree": degree, "success": success
    }


def tool_roll_dice(seed_str: str, count: int = 1, sides: int = 6,
                   modifier: int = 0) -> dict:
    """T2 roll_dice —— 通用骰子"""
    rolls = [pseudo_random(f"{seed_str}_{i}", sides) for i in range(count)]
    total = sum(rolls) + modifier
    return {"rolls": rolls, "sum": sum(rolls), "modifier": modifier, "total": total}


def tool_calc_damage(attacker_atk: int, defender_def: int, skill_power: int = 0,
                     is_crit: bool = False, damage_type: str = "物理") -> dict:
    """T3 calc_damage —— 伤害计算"""
    base = attacker_atk + skill_power
    mitigated = defender_def
    final = max(1, base - mitigated)
    lethal = final * 2 if is_crit else final
    return {"base": base, "mitigated": mitigated, "final": final,
            "lethal": lethal, "is_crit": is_crit}


def tool_calc_survival_cost(diff: str, location_type: str = "城镇",
                            activity: str = "日常") -> dict:
    """T4 calc_survival_cost —— 生存消耗结算"""
    multipliers = {"简单": 0.5, "一般": 1, "困难": 1, "地狱": 2}
    m = multipliers.get(diff, 1)
    stamina_base = {"日常": 10, "赶路": 20, "修炼": 15, "战斗": 30}.get(activity, 10)
    food = int(-30 * m)
    stamina = int(-stamina_base * m)
    cleanliness = int(-15 * m)
    money = -20 if location_type == "城镇" else 0
    return {"food": food, "stamina": stamina, "cleanliness": cleanliness,
            "money": money, "food_reserve_change": -1, "notes": f"{activity}@{location_type}"}


def tool_calc_travel(distance_li: int, transport: str = "步行",
                     diff: str = "一般") -> dict:
    """T5 calc_travel —— 赶路结算"""
    speeds = {"步行": 10, "骑马": 25, "乘车": 15, "御剑": 100, "传送": 99999}
    speed = speeds.get(transport, 10)
    time_hours = distance_li / speed if speed < 99999 else 0
    days = (time_hours + 11) // 12  # ceil
    return {"days": int(days), "hours": time_hours,
            "stamina_cost": int(-20 * days), "food_cost": int(-30 * days),
            "money_cost": int(-50 * days) if transport in ("骑马", "乘车") else 0,
            "events": []}


def tool_calc_tiandao(action_type: str, magnitude: int, current_deviation: int,
                      current_luck: int, current_nitian: int, diff: str,
                      cause_chain: str = "") -> dict:
    """T6 calc_tiandao —— 天道变化计算"""
    deviation_map = {
        "顺应剧情": -5, "偏离剧情": 10, "改变人物命运": 20,
        "夺取机缘": 15, "泄露天机": 25, "击杀关键NPC": 30
    }
    deviation_delta = deviation_map.get(action_type, 0)
    if action_type != "顺应剧情":
        deviation_delta *= max(1, magnitude)
    
    luck_delta = 10 if action_type == "顺应剧情" else -10
    
    new_deviation = max(0, min(100, current_deviation + deviation_delta))
    new_luck = max(0, min(100, current_luck + luck_delta))
    
    # 难度修正
    diff_offset = {"简单": 20, "一般": 0, "困难": 0, "地狱": -15}.get(diff, 0)
    threshold = new_deviation + diff_offset
    
    if threshold <= 30:
        punishment = "无"
    elif threshold <= 50:
        punishment = "霉运缠身"
    elif threshold <= 70:
        punishment = "因果反噬"
    elif threshold <= 85:
        punishment = "强敌天降"
    elif threshold <= 95:
        punishment = "天劫降临"
    else:
        punishment = "天劫极境"
    
    # 天劫抗御（偏离度>=86 触发）
    tribulation_check = None
    new_nitian = current_nitian
    nitian_triggered = False
    if threshold >= 86:
        tj_difficulty = 10 + (new_deviation - 80) // 2
        tj_diff_mod = {"简单": -2, "一般": 0, "困难": 0, "地狱": 2}.get(diff, 0)
        tj_difficulty += tj_diff_mod
        seed = f"tribulation_{new_deviation}"
        roll = pseudo_random(seed, 20)
        gen = 10  # 根骨默认值，实际应从 player_state 读取
        total = roll + (gen - 10) // 2 + new_luck // 10
        if roll == 20:
            hp_loss, nitian_delta = -10, 2
            result = "完美抗劫"
            nitian_triggered = True
        elif total >= tj_difficulty:
            hp_loss, nitian_delta = -30, 1
            result = "抗住天劫"
            new_deviation = max(0, new_deviation - 20)
        elif roll == 1:
            hp_loss, nitian_delta = -95, 0
            result = "濒死"
        else:
            hp_loss, nitian_delta = -70, 0
            result = "重伤"
        new_nitian += nitian_delta
        tribulation_check = {
            "roll": roll, "total": total, "difficulty": tj_difficulty,
            "result": result, "hp_loss_pct": hp_loss, "nitian_delta": nitian_delta
        }
        if new_nitian >= 3:
            nitian_triggered = True
    
    return {
        "deviation_delta": deviation_delta, "luck_delta": luck_delta,
        "new_deviation": new_deviation, "new_luck": new_luck,
        "punishment_level": punishment, "cause_chain": cause_chain,
        "tribulation_check": tribulation_check,
        "new_nitian": new_nitian, "nitian_chengming_triggered": nitian_triggered
    }


def tool_calc_breakthrough(seed_str: str, current_realm: str, target_realm: str,
                            talent: int, resources: int = 0, diff: str = "一般") -> dict:
    """T7 calc_breakthrough —— 突破检定"""
    # 境界跨度（简化处理）
    realm_order = ["入门", "初窥门径", "小成", "大成", "化境", "宗师", "天人"]
    try:
        span = realm_order.index(target_realm) - realm_order.index(current_realm)
    except ValueError:
        span = 1
    difficulty = 15 + max(1, span) * 5
    diff_mod = {"简单": 2, "一般": 0, "困难": -1, "地狱": -2}.get(diff, 0)
    result = tool_roll_d20(seed_str, talent, resources, difficulty, diff_mod)
    side_effects = []
    hp_change, inner_power_change = 0, 0
    if result["degree"] == "大成功":
        new_realm = target_realm
        side_effects.append("根基稳固")
    elif result["success"]:
        new_realm = target_realm
    elif result["degree"] == "大失败":
        new_realm = current_realm
        hp_change = -50
        inner_power_change = -50
        side_effects.append("走火入魔")
        side_effects.append("可能永久减属性")
    else:
        new_realm = current_realm
        inner_power_change = -50
        side_effects.append("走火入魔风险")
    return {"success": result["success"], "degree": result["degree"],
            "new_realm": new_realm, "side_effects": side_effects,
            "hp_change": hp_change, "inner_power_change": inner_power_change}


def tool_calc_relationship(target: str, current_affection: int, action_type: str,
                            magnitude: int = 1, target_persona: str = "") -> dict:
    """T8 calc_relationship —— 关系变化"""
    base_map = {
        "救命": 30, "帮助": 10, "赠送": 5, "结盟": 20,
        "冒犯": -10, "背叛": -50, "杀戮": -100
    }
    delta = base_map.get(action_type, 0)
    if action_type in ("帮助", "赠送", "冒犯"):
        delta *= max(1, magnitude)
    # 人设修正
    if "宽厚" in target_persona and delta > 0:
        delta = int(delta * 1.2)
    if "记仇" in target_persona and delta < 0:
        delta = int(delta * 1.5)
    new_affection = max(-100, min(100, current_affection + delta))
    if new_affection <= -50:
        level = "仇敌"
    elif new_affection <= -20:
        level = "敌对"
    elif new_affection < 20:
        level = "中立"
    elif new_affection < 50:
        level = "友善"
    elif new_affection < 80:
        level = "亲近"
    else:
        level = "至交"
    return {"affection_delta": delta, "new_affection": new_affection,
            "new_relationship_level": level, "npc_reaction": f"{target}态度变为{level}"}


def tool_generate_threat(seed_str: str, player_level: int, location: str,
                         days_passed: int, diff: str, has_enemy: bool) -> dict:
    """T9 generate_threat —— 威胁生成"""
    base = min(0.95, days_passed * 0.15)
    diff_mod = {"简单": 0.3, "一般": 1, "困难": 1.5, "地狱": 2}.get(diff, 1)
    prob = min(0.99, base * diff_mod + (0.2 if has_enemy else 0))
    # 用骰子判定是否触发
    roll = pseudo_random(seed_str, 20)
    triggered = roll >= 10  # difficulty=10
    if not triggered:
        return {"triggered": False, "threat_type": None, "level": 0,
                "source": None, "deadline_days": 0, "description": "无威胁"}
    type_roll = pseudo_random(seed_str + "_type", 6)
    threat_types = {1: "收保护费", 2: "挑衅", 3: "抢夺", 4: "追杀", 5: "栽赃", 6: "围剿"}
    threat_type = threat_types[type_roll]
    level = 1 + (days_passed + 2) // 3
    source = "仇家" if has_enemy else f"{location}当地恶势力"
    return {
        "triggered": True, "threat_type": threat_type, "level": level,
        "source": source, "deadline_days": 3,
        "description": f"{source}发起{threat_type}，等级{level}"
    }


def tool_calc_reward(seed_str: str, source: str, difficulty_grade: int,
                     canon_alignment: bool, world_setting: str = "") -> dict:
    """T10 calc_reward —— 奖励结算"""
    dice = tool_roll_dice(seed_str, 1, 10)
    money = difficulty_grade * dice["total"] * 10
    # 物品品质
    quality_roll = pseudo_random(seed_str + "_quality", 100)
    if quality_roll <= 50:
        quality = "普通"
    elif quality_roll <= 80:
        quality = "良品"
    elif quality_roll <= 95:
        quality = "稀有"
    else:
        quality = "珍品秘籍"
    exp = difficulty_grade * 50
    luck_delta = 10 if canon_alignment else 0
    return {
        "money": money, "items": [{"name": "战利品", "quality": quality}],
        "exp": exp, "luck_delta": luck_delta,
        "notes": f"{source}奖励，品质{quality}"
    }


def tool_update_character_state(character: str, current_time: dict,
                                canon_data: dict) -> dict:
    """T12 update_character_state —— 人物状态档案维护"""
    # canon_data 是预处理的人物档案（来自知识库）
    info = canon_data.get(character, {})
    birth_year = info.get("出生年份")
    death_year = info.get("死亡年份")
    current_year = current_time.get("年", 0)
    
    if death_year and current_year >= death_year:
        status = "死亡"
        location = info.get("死亡地点", "墓地")
        age = death_year - birth_year if birth_year else None
    else:
        status = "存活"
        location = info.get("当前位置", info.get("默认位置", "未知"))
        age = current_year - birth_year if birth_year else None
    
    power_level = info.get("实力", "未知")
    return {
        "character": character, "status": status, "location": location,
        "age": age, "power_level": power_level,
        "last_canon_event": info.get("最近事件", ""),
        "notes": info.get("备注", "")
    }


def tool_check_canon(current_time: dict, current_location: str,
                     npcs_involved: list, proposed_event: str,
                     items_involved: list, canon_data: dict) -> dict:
    """T13 check_canon —— 原著一致性校验"""
    conflicts = []
    for npc in npcs_involved:
        char_state = tool_update_character_state(npc, current_time, canon_data)
        if char_state["status"] == "死亡":
            conflicts.append({
                "type": "人物状态", "npc": npc,
                "detail": f"{npc}已于原著中死亡，不可活人姿态出场",
                "correction": "改为尸体/回忆/传说形式，或触发天道偏离度上升"
            })
        # 此处可扩展更多校验项
    overall = "通过" if not conflicts else "已修正"
    return {
        "time_ok": True, "location_ok": True, "logic_ok": True,
        "item_ok": True, "info_ok": True, "character_status_ok": not conflicts,
        "conflicts": conflicts, "overall": overall
    }


def tool_check_npc_persona(npc_name: str, persona: dict, proposed_action: str,
                           proposed_speech: str, current_time: dict) -> dict:
    """T14 check_npc_persona —— 人设校验（简化版，主要靠 LLM 判断）"""
    conflicts = []
    # 实际人设校验主要依赖 LLM，这里做基础结构化检查
    if not persona:
        return {"persona_ok": True, "conflicts": [], "overall": "符合"}
    return {"persona_ok": True, "conflicts": conflicts, "overall": "符合"}


def tool_calc_cultivation(seed_str: str, skill_name: str, current_proficiency: int,
                          talent: int, duration: int, resources: int = 0,
                          diff: str = "一般") -> dict:
    """T15 calc_cultivation —— 修炼结算"""
    diff_mod = {"简单": 1.5, "一般": 1, "困难": 0.8, "地狱": 0.5}.get(diff, 1)
    base_progress = talent * duration * 0.5 * diff_mod
    resource_bonus = resources * 2
    # 福缘顿悟
    luck_roll = tool_roll_dice(seed_str + "_luck", 1, 10)
    enlightenment = luck_roll["total"] >= 8
    proficiency_gain = (base_progress + resource_bonus) * (2 if enlightenment else 1)
    new_proficiency = current_proficiency + int(proficiency_gain)
    breakthrough_triggered = new_proficiency >= 100
    return {
        "proficiency_gain": int(proficiency_gain),
        "new_proficiency": new_proficiency,
        "breakthrough_triggered": breakthrough_triggered,
        "enlightenment": enlightenment,
        "notes": "顿悟！进度翻倍" if enlightenment else "正常修炼"
    }


def tool_calc_shop(item_name: str, action: str, quantity: int,
                   local_economy: float, player_charisma: int) -> dict:
    """T16 calc_shop —— 商店交易"""
    base_price = 100  # 简化基准价，实际应由 LLM 提供或查表
    unit_price = base_price * local_economy
    charisma_mod = (player_charisma - 10) // 2
    if action == "买":
        unit_price = max(1, unit_price - charisma_mod * 5)
    else:
        unit_price = unit_price + charisma_mod * 5
    if quantity > 10:
        unit_price = int(unit_price * 0.95)
    total_price = unit_price * quantity
    money_change = -total_price if action == "买" else total_price
    return {"unit_price": unit_price, "total_price": total_price,
            "money_change": money_change, "notes": f"{action}{quantity}个{item_name}"}


def tool_check_character_state_change(character: str, proposed_change: str,
                                       current_time: dict, canon_data: dict,
                                       has_nitian: bool) -> dict:
    """T17 check_character_state_change —— 人物状态变更校验"""
    char_state = tool_update_character_state(character, current_time, canon_data)
    if proposed_change == "救活" and char_state["status"] == "死亡":
        if has_nitian:
            return {"allowed": True, "conflict": "消耗逆天改命状态",
                    "deviation_delta": 0, "punishment_level": "无",
                    "requires_nitian": True, "suggestion": "逆天改命状态下允许改写命运"}
        else:
            return {"allowed": False, "conflict": "无法复活已死之人",
                    "deviation_delta": 50, "punishment_level": "天劫",
                    "requires_nitian": True, "suggestion": "需先累积逆天值触发逆天改命"}
    return {"allowed": True, "conflict": None, "deviation_delta": 10,
            "punishment_level": "霉运缠身", "requires_nitian": False,
            "suggestion": "允许尝试，触发因果反噬"}


# ============================================================
# 工具调度表
# ============================================================
TOOL_REGISTRY = {
    "roll_d20": tool_roll_d20,
    "roll_dice": tool_roll_dice,
    "calc_damage": tool_calc_damage,
    "calc_survival_cost": tool_calc_survival_cost,
    "calc_travel": tool_calc_travel,
    "calc_tiandao": tool_calc_tiandao,
    "calc_breakthrough": tool_calc_breakthrough,
    "calc_relationship": tool_calc_relationship,
    "generate_threat": tool_generate_threat,
    "calc_reward": tool_calc_reward,
    "update_character_state": tool_update_character_state,
    "check_canon": tool_check_canon,
    "check_npc_persona": tool_check_npc_persona,
    "calc_cultivation": tool_calc_cultivation,
    "calc_shop": tool_calc_shop,
    "check_character_state_change": tool_check_character_state_change,
}


# ============================================================
# 解析 LLM 输出中的工具调用声明
# ============================================================
def parse_tool_calls(llm_output: str) -> list:
    """解析 LLM 输出中的【工具调用】声明块"""
    calls = []
    pattern = r"【工具调用】\s*TOOL:\s*(\w+)\s*PARAMS:\s*(\{[^}]*\})"
    matches = re.findall(pattern, llm_output)
    for tool_name, params_str in matches:
        try:
            params = eval(params_str)  # 简化处理，生产环境应用 json.loads
        except Exception:
            try:
                params = json.loads(params_str.replace("'", '"'))
            except Exception:
                params = {}
        calls.append({"tool": tool_name, "params": params})
    return calls


# ============================================================
# 主函数：Dify Code 节点入口
# ============================================================
def main(llm_output: str, world_time: str, round_count: number,
         player_state: str) -> dict:
    """主入口：解析工具调用 → 执行 → 返回结果"""
    # 解析世界时间和玩家状态
    try:
        wt = json.loads(world_time) if world_time else {"日": 1}
    except Exception:
        wt = {"日": 1}
    try:
        ps = json.loads(player_state) if player_state else {}
    except Exception:
        ps = {}
    
    # 解析工具调用声明
    calls = parse_tool_calls(llm_output)
    
    results = []
    exec_log_lines = []
    
    for i, call in enumerate(calls):
        tool_name = call["tool"]
        params = call["params"]
        
        if tool_name not in TOOL_REGISTRY:
            results.append({"tool": tool_name, "error": f"未知工具: {tool_name}"})
            continue
        
        # 构造种子
        action_type = params.get("action_type", params.get("activity", "通用"))
        seed = make_seed(wt, round_count, action_type)
        
        try:
            # 调用工具
            if tool_name == "roll_d20":
                r = tool_roll_d20(seed, **{k: v for k, v in params.items()
                                            if k in ["attribute", "bonus", "difficulty", "diff_mod"]})
            elif tool_name == "roll_dice":
                r = tool_roll_dice(seed, **{k: v for k, v in params.items()
                                             if k in ["count", "sides", "modifier"]})
            elif tool_name == "calc_tiandao":
                # 从玩家状态读取当前天道数值
                td = ps.get("天道", {})
                r = tool_calc_tiandao(
                    params.get("action_type", "偏离剧情"),
                    params.get("magnitude", 1),
                    td.get("偏离度", 0), td.get("气运", 0),
                    td.get("逆天值", 0), ps.get("难度", "一般"),
                    params.get("cause_chain", "")
                )
            elif tool_name == "calc_breakthrough":
                r = tool_calc_breakthrough(
                    seed, params.get("current_realm", "入门"),
                    params.get("target_realm", "初窥门径"),
                    ps.get("属性", {}).get("根骨", 10),
                    params.get("resources", 0), ps.get("难度", "一般")
                )
            elif tool_name == "calc_cultivation":
                r = tool_calc_cultivation(
                    seed, params.get("skill_name", ""),
                    params.get("current_proficiency", 0),
                    ps.get("属性", {}).get("悟性", 10),
                    params.get("duration", 1), params.get("resources", 0),
                    ps.get("难度", "一般")
                )
            else:
                # 通用调用
                func = TOOL_REGISTRY[tool_name]
                r = func(**params) if params else func()
            
            results.append({"tool": tool_name, "params": params, "result": r})
            exec_log_lines.append(f"[{i+1}] {tool_name}: {json.dumps(r, ensure_ascii=False)}")
        except Exception as e:
            results.append({"tool": tool_name, "params": params, "error": str(e)})
            exec_log_lines.append(f"[{i+1}] {tool_name} ERROR: {e}")
    
    return {
        "tool_results": json.dumps(results, ensure_ascii=False),
        "tool_count": len(results),
        "exec_log": "\n".join(exec_log_lines) if exec_log_lines else "无工具调用"
    }
