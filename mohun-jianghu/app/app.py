"""
墨魂·江湖 — 轻量级 Flask 后端
负责：游戏状态管理、LLM 调用（可配置）、10模块输出解析
"""

import json
import os
import re
import time
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ============================================================
# 游戏状态存储（内存版，demo 用）
# ============================================================
games = {}  # session_id -> game_state

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

NOVEL_DATA = {
    "射雕英雄传": {
        "worldview": "南宋宁宗年间，金兵南下，宋室偏安江南。江湖之中，东邪西毒南帝北丐中神通五绝并立，九阴真经、降龙十八掌等绝世武功引得无数英雄竞折腰。郭杨两家的孩子，正承载着父辈的血海深仇与江湖的命运。",
        "time_start": "南宋宁宗嘉定三年",
        "factions": "【正派】全真教、丐帮、江南七怪\n【邪派】白驼山、铁掌帮、金国六王府\n【中立】桃花岛、大理段氏",
        "identities": [
            {
                "name": "郭靖（原著主角）",
                "background": "蒙古大漠长大的憨厚少年，江南七怪弟子，身兼蒙古与汉人的双重身份。",
                "time": "18岁，即将南下赴嘉兴醉仙楼之约",
                "location": "蒙古大漠",
                "pros": "根骨奇佳，福缘深厚，为人正直",
                "cons": "悟性不高，心思单纯，易被人利用",
                "quests": ["赴嘉兴醉仙楼与杨康比武", "寻找杀父仇人段天德", "护送华筝公主..."]
            },
            {
                "name": "黄蓉（原著女主角）",
                "background": "东邪黄药师独女，聪慧绝伦，精通奇门遁甲，初离桃花岛闯荡江湖。",
                "time": "15岁，偷离桃花岛",
                "location": "江南",
                "pros": "智计无双，精通奇门遁甲，厨艺绝世",
                "cons": "娇纵任性，武功未成，父亲管束严",
                "quests": ["游历江湖", "结识有缘人", "寻找九阴真经下落"]
            },
            {
                "name": "临安府小乞丐",
                "background": "父母双亡的孤儿，在临安府街头讨饭为生，不知自己身世。",
                "time": "12岁，街头流浪",
                "location": "临安府",
                "pros": "出身低微不易引人注意，生存能力强",
                "cons": "一无所有，无依无靠，随时可能饿死",
                "quests": ["活下去", "填饱肚子", "寻找安身之所"]
            },
            {
                "name": "穿越者（自定义）",
                "background": "来自二十一世纪的穿越者，熟知射雕剧情，附身于一个刚死的路人身上。",
                "time": "剧情开始前三年",
                "location": "牛家村",
                "pros": "熟知剧情走向，拥有现代知识",
                "cons": "天道敌视穿越者，蝴蝶效应难测",
                "quests": ["在这个世界活下去", "选择自己的道路", "不被天道发现"]
            }
        ],
        "difficulties": ["简单（天道宽松）", "一般（平衡标准）", "困难（严格原著）", "地狱（天谴降临）"]
    },
    "三国演义": {
        "worldview": "东汉末年，黄巾起义，天下大乱。群雄并起，逐鹿中原。桃园三结义的兄弟、挟天子以令诸侯的枭雄、谈笑间樯橹灰飞烟灭的儒将……在这个英雄辈出的年代，你的选择将决定天下大势的走向。",
        "time_start": "东汉中平元年",
        "factions": "【汉室】朝廷、各路诸侯\n【群雄】袁绍、曹操、孙坚、刘备\n【黄巾】张角三兄弟",
        "identities": [
            {
                "name": "刘备（汉室宗亲）",
                "background": "中山靖王之后，织席贩履之徒，心怀天下，刚与关张桃园结义。",
                "time": "28岁，黄巾起义爆发",
                "location": "涿郡",
                "pros": "仁德之名，汉室正统，关羽张飞结义兄弟",
                "cons": "兵微将寡，无立足之地",
                "quests": ["破黄巾立功", "建立功业", "兴复汉室"]
            },
            {
                "name": "曹操（乱世奸雄）",
                "background": "宦官之后，任骑都尉，胸怀大志，刚被朝廷任命征讨黄巾。",
                "time": "30岁，黄巾起义爆发",
                "location": "洛阳",
                "pros": "智谋过人，家世显赫，朝廷人脉广",
                "cons": "出身宦官家庭，被士人轻视",
                "quests": ["平定黄巾", "建立自己的势力", "夺取天下"]
            },
            {
                "name": "寒门书生",
                "background": "出身寒微的读书人，精通兵法谋略，欲在乱世中寻得明主。",
                "time": "20岁，黄巾之乱前夕",
                "location": "颍川",
                "pros": "智计过人，精通谋略，洞察人心",
                "cons": "无兵无权，出身低微",
                "quests": ["投奔明主", "出人头地", "辅佐主公成就霸业"]
            },
            {
                "name": "穿越者（自定义）",
                "background": "穿越到三国时代的现代人，熟知历史走向，附身于一个普通士兵。",
                "time": "中平元年，黄巾之乱",
                "location": "颍川",
                "pros": "预知历史大势，现代知识",
                "cons": "身份低微，天道威压更甚",
                "quests": ["活下去", "选择阵营", "改变历史"]
            }
        ],
        "difficulties": ["简单（天道宽松）", "一般（平衡标准）", "困难（严格原著）", "地狱（天谴降临）"]
    },
    "西游记": {
        "worldview": "东胜神洲傲来国花果山，一石猴出世，惊动三界。自此大闹天宫、五行山下、西行取经……这是一个神魔漫天、妖怪遍地的世界。你将在这个光怪陆离的西游世界中，走出自己的道路。",
        "time_start": "大唐贞观年间",
        "factions": "【天庭】玉帝、王母、十万天兵\n【佛门】如来、观音、八百罗汉\n【妖族】花果山、各路妖王\n【人族】唐太宗、取经人",
        "identities": [
            {
                "name": "孙悟空（齐天大圣）",
                "background": "花果山水帘洞美猴王，师从菩提祖师，刚刚学成归来。",
                "time": "学成归来，尚未大闹天宫",
                "location": "花果山",
                "pros": "金刚不坏，七十二变，筋斗云",
                "cons": "桀骜不驯，天庭忌惮",
                "quests": ["夺宝东海龙宫", "勾销生死簿", "大闹天宫"]
            },
            {
                "name": "唐僧（金蝉子转世）",
                "background": "金山寺长老，法名玄奘，奉旨西天取经。",
                "time": "取经前夕",
                "location": "长安城",
                "pros": "金蝉子转世，佛法精深，观音护佑",
                "cons": "手无缚鸡之力，慈悲过度",
                "quests": ["西天取经", "收徒三人", "历经八十一难"]
            },
            {
                "name": "凡间道士",
                "background": "终南山修道之人，略有小成，欲下山历练。",
                "time": "贞观年间",
                "location": "终南山",
                "pros": "道法入门，降妖除魔之术",
                "cons": "修为尚浅，神通不足",
                "quests": ["下山历练", "积累功德", "追寻长生"]
            },
            {
                "name": "穿越者（自定义）",
                "background": "穿越到西游世界的现代人，附身于一个死去的小妖身上。",
                "time": "孙悟空大闹天宫之前",
                "location": "花果山附近",
                "pros": "熟知剧情，可趋吉避凶",
                "cons": "小妖身份，随时可能被打死",
                "quests": ["活下去", "修炼变强", "改变命运"]
            }
        ],
        "difficulties": ["简单（天道宽松）", "一般（平衡标准）", "困难（严格原著）", "地狱（天谴降临）"]
    }
}


def create_initial_state(novel_name, identity_index, difficulty):
    """创建初始玩家状态"""
    novel = NOVEL_DATA.get(novel_name, NOVEL_DATA["射雕英雄传"])
    identity = novel["identities"][identity_index]
    diff_levels = ["简单", "一般", "困难", "地狱"]
    diff = diff_levels[difficulty] if isinstance(difficulty, int) else difficulty
    
    # 根据难度调整
    diff_mod = {"简单": 1.2, "一般": 1.0, "困难": 0.9, "地狱": 0.7}
    m = diff_mod.get(diff, 1.0)
    
    state = {
        "姓名": identity["name"].split("（")[0],
        "身份": identity["background"],
        "难度": diff,
        "位置": identity["location"],
        "世界时间": {"年": novel["time_start"], "月": "一", "日": 1, "时辰": "辰时"},
        "属性": {
            "体魄": int(12 * m), "敏捷": int(10 * m), "悟性": int(10 * m),
            "根骨": int(12 * m), "福缘": int(12 * m), "魅力": int(10 * m)
        },
        "战斗": {"气血": int(100 * m), "气血上限": int(100 * m),
                  "内力": 0, "内力上限": 0, "攻": int(6 * m), "防": int(4 * m)},
        "生存": {"饱食度": 100, "体力": 100, "体力上限": 100,
                  "清洁度": 100, "健康": "良好", "金钱": 100, "食物储备": 5},
        "武功": [],
        "物品栏": [],
        "关系": {"势力声望": {}, "NPC好感": {}},
        "天道": {"关注度": 0, "气运": 50, "偏离度": 0, "天罚等级": "无",
                  "逆天值": 0, "逆天改命": False},
        "威胁": {"当前威胁": [], "仇家": []},
        "任务": {
            "必做任务": [{"任务名称": q, "发布者": "天道", "任务类型": "主线",
                          "任务描述": q, "截止时间": "无", "奖励": "气运+",
                          "失败惩罚": "偏离度上升", "进度": 0} for q in identity["quests"][:2]],
            "支线任务": [],
            "已完成任务": [],
            "已失败任务": []
        }
    }
    return state


def generate_game_round(state, user_action, round_count):
    """生成一轮游戏输出（mock 版，演示用）"""
    name = state["姓名"]
    diff = state["难度"]
    deviation = state["天道"]["偏离度"]
    
    # 根据偏离度确定天罚等级
    if deviation <= 30:
        tiandao_msg = "天道如常，未曾注视于你。"
        punishment = "无"
    elif deviation <= 50:
        tiandao_msg = "你感到一阵莫名的寒意，似乎冥冥中有什么在注视着你。霉运悄悄缠身。"
        punishment = "霉运缠身"
    elif deviation <= 70:
        tiandao_msg = "天道已察觉你的异常。因果之线悄然缠上你的脚踝，一丝反噬正在酝酿。"
        punishment = "因果反噬"
    else:
        tiandao_msg = "【警告】天道震怒！天地间的法则开始排斥你的存在。天劫或强敌，随时可能降临！"
        punishment = "天劫"
    
    # 根据行动生成剧情
    action = user_action.strip()
    if not action or action in ["继续", "随便走走", "看看周围"]:
        plot_text = f"""你走在{state["位置"]}的街道上，脚下的青石板被岁月磨得光滑。
街道两旁的店铺陆续开张，卖早点的吆喝声、打铁的叮当声、行人的脚步声交织在一起，构成一幅活色生香的市井画卷。
一阵风吹过，带来远处酒楼飘来的酒香与肉香，你不由地咽了口唾沫。

远处传来一阵喧哗，似乎有什么热闹正在发生。街角处，一个算命先生正闭着眼，手指飞快地掐算着什么。你路过他身边时，他突然睁开眼，浑浊的目光落在你身上，说了一句：

"这位公子，印堂发亮，又带几分煞气，近日必有奇遇，也有凶险。好自为之。"

说完便又闭上眼，不再理你。"""
    elif "打听" in action or "问" in action:
        plot_text = f"""你拉住一个路人，问起近日的江湖传闻。

那人上下打量了你一番，见你不像歹人，便压低声音道：
"客官是外乡人吧？最近江湖上可不太平。听说全真教的丘处机道长和江南七怪打了个赌，十八年后要在嘉兴醉仙楼让各自的徒弟比武。"

"还有啊——" 他凑近了些，"金国六王爷完颜洪烈最近在招揽高手，据说得了什么宝物，正跟江南的好汉们较劲呢。"

说完他匆匆走了，似乎怕被人听见。"""
    elif "吃饭" in action or "酒楼" in action or "吃东西" in action:
        plot_text = f"""你走进街边一家酒楼，店小二殷勤地迎了上来。
"客官里边请！本店的招牌菜——东坡肉、叫花鸡、西湖醋鱼，样样地道！"

你找了个靠窗的位置坐下，点了几个小菜和一壶酒。
饭菜上桌，你风卷残云般吃了起来。味道确实不错，虽然比不上前世的精细，但胜在食材新鲜、分量足。

吃到一半，你听到邻桌的两个江湖汉子在议论什么"九阴真经"和"华山论剑"，不由地竖起了耳朵。"""
    elif "修炼" in action or "练功" in action:
        plot_text = f"""你找了一处僻静的树林，盘膝坐下，开始运气行功。

天地间的灵气缓慢地涌入你的经脉，虽然微薄，但确实存在。你按照入门心法引导真气在体内循环，一圈又一圈。

一个时辰后，你睁开眼，感到神清气爽，体内的真气似乎又壮大了一丝。

【修炼进度】+15 点熟练度

远处传来一声鸟鸣，你站起身，活动了一下筋骨。是时候回去了。"""
    elif "打架" in action or "战斗" in action or "动手" in action:
        plot_text = f"""你话音刚落，对面的汉子脸色一沉，猛地一拳砸了过来！

"好小子，敢在老子面前撒野！"

你侧身一闪，拳头擦着耳边飞过，带起一阵劲风。
这汉子看起来是练家子，招式刚猛，力道不小。
你来我往，拆了十几招，双方都没能占到便宜。
最后你卖个破绽，一脚踹在他小腹上，将他踹倒在地。

"呸！算你狠！" 那汉子爬起来，丢下一句场面话，狼狈地跑了。

【战斗胜利】气血 -15，体力 -20"""
    else:
        plot_text = f"""你决定{action}。

你迈出脚步，周围的景象随之变化。街上的行人投来好奇的目光，有人低头私语，有人匆匆走过。
风卷起地上的落叶，打着旋儿从你脚边掠过。远处的钟楼传来沉闷的钟声，一下，又一下。

你感到这个世界是如此的真实——真实的风、真实的人、真实的心跳。
你不再是屏幕前的看客，而是这个江湖中的一员。
接下来你要做什么？"""
    
    world_text = f"""【世界推演】
{plot_text}

【感官细节】
空气中弥漫着市井的烟火气，有炊烟的味道，也有泥土的气息。
脚下的地面坚实而微凉，你的每一步都踏得实实在在。
远处偶尔传来马蹄声、狗吠声，还有店铺里算盘珠子噼啪作响。

你深吸一口气，确认了一件事——你真的来到了这个世界。"""
    
    # 可选行动
    actions = [
        {"action": "走进街边酒楼，打听江湖传闻", "risk": "安全", "impact": "任务推进"},
        {"action": "出城走走，看看郊外风光", "risk": "有风险", "impact": "可能遇敌"},
        {"action": "找个地方修炼武功", "risk": "安全", "impact": "熟练度+"},
        {"action": "去市集逛逛，看看有什么好东西", "risk": "安全", "impact": "购物"},
    ]
    
    # 更新状态（模拟）
    new_state = json.loads(json.dumps(state))
    new_state["生存"]["饱食度"] = max(0, new_state["生存"]["饱食度"] - 5)
    new_state["生存"]["体力"] = max(0, new_state["生存"]["体力"] - 5)
    new_state["世界时间"]["时辰"] = "巳时"
    if state["天道"]["偏离度"] < 30:
        new_state["天道"]["关注度"] = min(100, state["天道"]["关注度"] + 1)
    
    modules = {
        "module1_plot": {
            "title": "玩家剧情推演",
            "content": plot_text
        },
        "module2_quests": {
            "title": "任务面板",
            "data": new_state["任务"]
        },
        "module3_tiandao": {
            "title": "天道",
            "content": tiandao_msg,
            "level": punishment
        },
        "module4_canon": {
            "title": "原著校验",
            "data": {"总体结论": "校验通过，无冲突", "冲突与修正": []}
        },
        "module5_tools": {
            "title": "工具调用记录",
            "data": {"本轮调用次数": 0, "调用记录": []}
        },
        "module6_world": {
            "title": "世界推演",
            "content": world_text
        },
        "module7_cost": {
            "title": "时间与消耗结算",
            "data": {
                "本轮耗时": {"数值": 1, "单位": "时辰"},
                "生存消耗": {"饱食度": -5, "体力": -5, "清洁度": -3},
                "任务更新": []
            }
        },
        "module8_combat": {
            "title": "检定/战斗",
            "data": {"类型": "无", "说明": "本轮无检定与战斗"}
        },
        "module9_state": {
            "title": "状态面板",
            "data": new_state
        },
        "module10_actions": {
            "title": "可选行动",
            "actions": actions
        }
    }
    
    return modules


# ============================================================
# API 路由
# ============================================================

@app.route("/api/novels", methods=["GET"])
def list_novels():
    """获取可用小说列表"""
    return jsonify(list(NOVEL_DATA.keys()))


@app.route("/api/novel/<name>", methods=["GET"])
def get_novel(name):
    """获取小说详情（世界设定+可选身份）"""
    if name not in NOVEL_DATA:
        return jsonify({"error": f"未找到小说：{name}"}), 404
    return jsonify(NOVEL_DATA[name])


@app.route("/api/start", methods=["POST"])
def start_game():
    """开始新游戏"""
    data = request.get_json()
    novel_name = data.get("novel_name", "射雕英雄传")
    identity_index = data.get("identity_index", 0)
    difficulty = data.get("difficulty", 1)  # 0=简单, 1=一般, 2=困难, 3=地狱
    
    if novel_name not in NOVEL_DATA:
        return jsonify({"error": f"未找到小说：{novel_name}"}), 404
    
    state = create_initial_state(novel_name, identity_index, difficulty)
    session_id = str(uuid.uuid4())
    
    games[session_id] = {
        "state": state,
        "novel_name": novel_name,
        "round": 0,
        "history": [],
        "game_phase": "playing"
    }
    
    # 生成开局输出
    novel = NOVEL_DATA[novel_name]
    identity = novel["identities"][identity_index]
    diff_names = ["简单", "一般", "困难", "地狱"]
    diff = diff_names[difficulty] if isinstance(difficulty, int) else difficulty
    
    opening = f"""【天道开场】

天地玄黄，宇宙洪荒。
命运的长河奔流不息，而你，是误入其中的一粒微尘。

{novel_name} 的世界，因你的到来，泛起了一丝涟漪。

天道默默注视着这一切。
是顺应天命，还是逆天改命？
——你的选择，将决定一切。

【开局信息】
姓名：{state["姓名"]}
身份：{identity["name"]}
难度：{diff}
位置：{identity["location"]}
时间：{novel["time_start"]}

你睁开眼，发现自己正站在{identity["location"]}的土地上。
一切，都是那么真实。"""
    
    return jsonify({
        "session_id": session_id,
        "state": state,
        "novel_name": novel_name,
        "opening": opening
    })


@app.route("/api/action", methods=["POST"])
def game_action():
    """执行游戏行动"""
    data = request.get_json()
    session_id = data.get("session_id", "")
    user_action = data.get("action", "")
    
    if session_id not in games:
        return jsonify({"error": "会话不存在，请重新开始游戏"}), 404
    
    game = games[session_id]
    game["round"] += 1
    
    modules = generate_game_round(game["state"], user_action, game["round"])
    game["state"] = modules["module9_state"]["data"]
    game["history"].append({"round": game["round"], "action": user_action})
    
    return jsonify({
        "round": game["round"],
        "modules": modules,
        "state": game["state"]
    })


@app.route("/api/save", methods=["POST"])
def save_game():
    """存档"""
    data = request.get_json()
    session_id = data.get("session_id", "")
    if session_id not in games:
        return jsonify({"error": "会话不存在"}), 404
    return jsonify({"save_data": games[session_id]})


@app.route("/api/load", methods=["POST"])
def load_game():
    """读档"""
    data = request.get_json()
    save_data = data.get("save_data", {})
    session_id = str(uuid.uuid4())
    games[session_id] = save_data
    return jsonify({"session_id": session_id, "state": save_data.get("state", {})})


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
