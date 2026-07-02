"""
Dify Code 节点：意图分类器 + 开局/换书/指令处理
================================================
用途：识别用户输入类型（开局/游戏行动/系统指令/换书/存档读档），
      返回意图标签，供 Chatflow 路由到不同分支。

输入参数：
  - user_input: str       用户输入
  - game_phase: str       当前游戏阶段
  - novel_name: str       当前小说名（用于判断是否在游戏中）

输出参数：
  - intent: str           意图标签
  - novel_name_extracted: str  从输入中提取的小说名（换书/开局时）
  - response: str         直接回复（处理简单指令时使用，否则为空）
"""

import re


def main(user_input: str, game_phase: str, novel_name: str) -> dict:
    """主入口：意图分类"""
    text = user_input.strip()
    
    # ========== 1. 存档/读档 ==========
    if text in ["/存档", "/save"]:
        return {"intent": "save", "novel_name_extracted": "",
                "response": "【存档】请复制以下 JSON 保存到本地文件："}
    
    if text.startswith("/读档") or text.startswith("/load"):
        return {"intent": "load", "novel_name_extracted": "",
                "response": "【读档】请粘贴之前保存的状态 JSON："}
    
    # ========== 2. 换书 ==========
    if text.startswith("/换书") or text.startswith("/newgame"):
        # 提取小说名
        parts = text.split(maxsplit=1)
        new_novel = parts[1].strip() if len(parts) > 1 else ""
        return {"intent": "switch_novel", "novel_name_extracted": new_novel,
                "response": ""}
    
    # ========== 3. 系统查询指令 ==========
    query_commands = {
        "/状态": "state", "/status": "state",
        "/剧情": "plot", "/plot": "plot",
        "/任务": "quest", "/quest": "quest",
        "/天道": "tiandao", "/tiandao": "tiandao",
        "/帮助": "help", "/help": "help",
    }
    if text in query_commands:
        return {"intent": "query", "novel_name_extracted": "",
                "response": ""}
    
    # ========== 4. 简略/详细切换 ==========
    if text == "/详细":
        return {"intent": "verbose", "novel_name_extracted": "",
                "response": "已切换为详细模式，后续将展示模块4/5的完整过程。"}
    if text == "/精简":
        return {"intent": "simple", "novel_name_extracted": "",
                "response": "已切换为精简模式，模块4/5仅显示一行结论。"}
    
    # ========== 5. 快捷行动指令 ==========
    quick_actions = ["/补满", "/休息", "/赶路", "/跳过时间", "/验算"]
    for cmd in quick_actions:
        if text.startswith(cmd):
            return {"intent": "game_action", "novel_name_extracted": "",
                    "response": ""}
    
    # ========== 6. 开局判断 ==========
    # 如果还没开始游戏（game_phase 为 not_started 或 waiting_novel）
    if game_phase in ["not_started", "waiting_novel", ""]:
        # 检测是否是小说名输入
        # 简单规则：非斜杠开头的短文本视为小说名
        if not text.startswith("/") and len(text) < 50:
            return {"intent": "init_game", "novel_name_extracted": text,
                    "response": ""}
        # 检测"开始游戏"等关键词
        if any(kw in text for kw in ["开始", "开局", "新游戏", "射雕", "三国", "西游", "水浒", "红楼"]):
            # 尝试提取小说名
            for novel_kw in ["射雕英雄传", "神雕侠侣", "倚天屠龙记", "天龙八部",
                              "三国演义", "西游记", "水浒传", "红楼梦", "笑傲江湖",
                              "鹿鼎记", "侠客行", "碧血剑", "连城诀"]:
                if novel_kw in text:
                    return {"intent": "init_game", "novel_name_extracted": novel_kw,
                            "response": ""}
            return {"intent": "init_game", "novel_name_extracted": text,
                    "response": ""}
    
    # ========== 7. 游戏中的行动 ==========
    if game_phase == "playing":
        return {"intent": "game_action", "novel_name_extracted": "",
                "response": ""}
    
    # ========== 8. 默认：视为游戏行动 ==========
    return {"intent": "game_action", "novel_name_extracted": "",
            "response": ""}
