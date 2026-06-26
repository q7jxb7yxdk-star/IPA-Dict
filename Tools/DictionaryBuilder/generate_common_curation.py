#!/usr/bin/env python3
"""Generate conservative replacements for high-risk, high-frequency words."""

from __future__ import annotations

import argparse
import bz2
import csv
import json
import re
import sqlite3
import tarfile
from collections import defaultdict
from pathlib import Path


CORE_WORDS = """
able about above accept account across act action add after again against age ago
agree air all allow almost alone along already also always among amount animal
another answer any appear apple area arm around arrive art ask away back ball bank
base bear beautiful because become before begin behind believe below best better
between big bit blood blue body book both box boy bring brother build business buy
call can car care carry cat catch cause center century certain change check child
choose city clear close cold college come common company complete consider continue
control cost could country course cover create cut dark data day dead deal decide
develop did die different difficult do doctor dog door down dream drive drop during
each early earth east easy eat education effect end enough even ever every example
face fact family far fast father feel few field fight fish five floor fly follow
food force form found four free friend front full future game get girl give go got
government great green ground group grow had half hand happen happy hard has have
head health hear heart help here high history hold home hope horse hot hour house
how human hundred idea if important include information interest into job join just
keep kid kind know land large last late later learn leave left less let letter life
light like line live long look love low made make man many map mark may mean meet
might mile mind minute miss money month more morning most mother move much music
must name near need never next night no not note nothing now number of off often old
on once one only open or order other our out over own page paper parent part party
pass past pay people person picture plan play point possible power problem public
put question quick quite read real really reason red remember result right river
road room run said same say school sea second see seem self sentence several she
short should show side since sit six small so some something song soon sound south
speak special stand start state stay still stop story street student study such sun
system table talk teach team tell ten than that the their them then there these they
thing think this those though thought three through time to today together too top
town tree true try turn two under understand until up us use usually very voice wait
walk want war was watch water way we week well went were what when where which while
white who why will with without woman word work world would write wrong year yet you
young
""".split()

RARE_MARKERS = re.compile(
    r"\b(?:obsolete|archaic|dated|rare|historical|vulgar|slang|dialectal|"
    r"nonstandard|chiefly\s+heraldry|taxonomy|entomology)\b",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
HAN_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
SIMPLIFIED_PHRASE_TO_TRADITIONAL = {
    "关系": "關係",
    "没关系": "沒關係",
    "联系": "聯繫",
    "梁赞": "梁贊",
    "后台": "後台",
    "面包": "麵包",
    "里面": "裡面",
    "里程": "里程",
    "圣经": "聖經",
    "钟表": "鐘錶",
    "钟点": "鐘點",
    "钟头": "鐘頭",
    "干线": "幹線",
    "干燥": "乾燥",
    "干净": "乾淨",
    "干杯": "乾杯",
    "头发": "頭髮",
    "理发": "理髮",
    "美发": "美髮",
    "护发": "護髮",
    "复数": "複數",
    "复杂": "複雜",
    "重复": "重複",
    "复制": "複製",
    "复印": "複印",
    "复合": "複合",
    "复兴": "復興",
    "复活": "復活",
    "恢复": "恢復",
    "征服": "征服",
    "征收": "徵收",
    "征兆": "徵兆",
    "象征": "象徵",
    "适合": "適合",
    "适当": "適當",
    "适应": "適應",
    "适用": "適用",
    "适宜": "適宜",
    "标准": "標準",
    "准确": "準確",
    "准备": "準備",
    "获胜": "獲勝",
    "获得": "獲得",
    "获利": "獲利",
    "获释": "獲釋",
    "计划": "計劃",
    "划分": "劃分",
    "区划": "區劃",
    "划船": "划船",
    "制作": "製作",
    "制造": "製造",
    "制度": "制度",
    "控制": "控制",
    "只身": "隻身",
    "只手": "隻手",
    "船只": "船隻",
    "叶子": "葉子",
    "叶片": "葉片",
    "占据": "佔據",
    "占领": "佔領",
    "占用": "佔用",
    "占有": "佔有",
    "冲击": "衝擊",
    "冲突": "衝突",
    "冲动": "衝動",
    "冲绳": "沖繩",
    "冲洗": "沖洗",
    "冲锋": "衝鋒",
    "冲浪": "衝浪",
    "武装冲突": "武裝衝突",
}
SIMPLIFIED_TO_TRADITIONAL = str.maketrans({
    "头": "頭", "发": "發", "学": "學", "国": "國", "车": "車",
    "书": "書", "门": "門", "见": "見", "听": "聽", "说": "說",
    "话": "話", "这": "這", "为": "為", "开": "開", "关": "關",
    "东": "東", "万": "萬", "与": "與", "后": "後", "时": "時",
    "个": "個", "还": "還", "会": "會", "样": "樣", "长": "長",
    "点": "點", "间": "間", "无": "無", "气": "氣", "动": "動",
    "实": "實", "体": "體", "应": "應", "对": "對", "业": "業",
    "产": "產", "从": "從", "进": "進", "过": "過", "边": "邊",
    "经": "經", "给": "給", "总": "總", "当": "當", "两": "兩",
    "几": "幾", "让": "讓", "则": "則", "种": "種", "现": "現",
    "机": "機", "电": "電", "数": "數", "员": "員", "亲": "親",
    "爱": "愛", "习": "習", "问": "問", "读": "讀", "写": "寫",
    "买": "買", "卖": "賣", "钱": "錢", "岁": "歲", "张": "張",
    "线": "線", "级": "級", "医": "醫", "声": "聲", "处": "處",
    "变": "變", "难": "難", "虽": "雖", "却": "卻", "着": "著",
    "么": "麼", "吗": "嗎", "们": "們", "题": "題", "据": "據",
    "习": "習", "终": "終", "达": "達", "丽": "麗", "广": "廣",
    "乐": "樂", "语": "語", "觉": "覺", "认": "認", "识": "識",
    "亚": "亞", "纳": "納", "尔": "爾", "罗": "羅", "马": "馬",
    "岛": "島", "质": "質", "圣": "聖", "贝": "貝", "伦": "倫",
    "苏": "蘇", "兰": "蘭", "汉": "漢", "齐": "齊", "龙": "龍",
    "华": "華",
    "丢": "丟", "兹": "茲", "于": "於", "吨": "噸",
    "卢": "盧", "诺": "諾", "图": "圖", "区": "區", "县": "縣",
    "乡": "鄉", "镇": "鎮", "岛": "島", "桥": "橋", "矿": "礦",
    "铁": "鐵", "铜": "銅", "铝": "鋁", "银": "銀", "钢": "鋼",
    "钟": "鐘", "鸟": "鳥", "鱼": "魚", "麦": "麥", "黄": "黃",
    "蓝": "藍", "绿": "綠", "红": "紅", "黑": "黑", "药": "藥",
    "艺": "藝", "术": "術", "图": "圖", "义": "義", "类": "類",
    "仅": "僅", "优": "優", "传": "傳", "伤": "傷", "伟": "偉",
    "价": "價", "债": "債", "倾": "傾", "儿": "兒", "党": "黨",
    "兴": "興", "养": "養", "兽": "獸", "农": "農", "军": "軍",
    "凤": "鳳", "击": "擊", "刘": "劉", "创": "創", "别": "別",
    "剂": "劑", "剑": "劍", "剧": "劇", "办": "辦", "务": "務",
    "劳": "勞", "势": "勢", "协": "協", "单": "單", "卢": "盧",
    "厅": "廳", "历": "歷", "压": "壓", "厌": "厭", "参": "參",
    "双": "雙", "叠": "疊", "号": "號", "叹": "嘆", "吓": "嚇",
    "呜": "嗚", "咏": "詠", "响": "響", "哑": "啞", "哗": "嘩",
    "唤": "喚", "啸": "嘯", "喷": "噴", "团": "團", "园": "園",
    "围": "圍", "圆": "圓", "圣": "聖", "场": "場", "块": "塊",
    "坚": "堅", "坛": "壇", "坝": "壩", "坟": "墳", "坠": "墜",
    "墙": "牆", "壮": "壯", "壳": "殼", "壶": "壺", "备": "備",
    "够": "夠", "夺": "奪", "奖": "獎", "奥": "奧", "妇": "婦",
    "妈": "媽", "娇": "嬌", "婴": "嬰", "孙": "孫", "宝": "寶",
    "审": "審", "宪": "憲", "宫": "宮", "宽": "寬", "宾": "賓",
    "寝": "寢", "导": "導", "寿": "壽", "将": "將", "尔": "爾",
    "尘": "塵", "尝": "嘗", "层": "層", "属": "屬", "岁": "歲",
    "岂": "豈", "岗": "崗", "峡": "峽", "峦": "巒", "巅": "巔",
    "币": "幣", "师": "師", "帐": "帳", "带": "帶", "帮": "幫",
    "庄": "莊", "庆": "慶", "库": "庫", "庙": "廟", "废": "廢",
    "异": "異", "弃": "棄", "弯": "彎", "弹": "彈", "强": "強",
    "归": "歸", "录": "錄", "彻": "徹", "径": "徑", "忆": "憶",
    "忧": "憂", "怀": "懷", "态": "態", "怜": "憐", "恶": "惡",
    "恼": "惱", "悦": "悅", "悬": "懸", "惊": "驚", "惧": "懼",
    "惨": "慘", "惩": "懲", "惯": "慣", "愤": "憤", "愿": "願",
    "懒": "懶", "战": "戰", "户": "戶", "扑": "撲", "执": "執",
    "扩": "擴", "扫": "掃", "扬": "揚", "扰": "擾", "抚": "撫",
    "抛": "拋", "抢": "搶", "护": "護", "报": "報", "担": "擔",
    "拟": "擬", "拢": "攏", "拣": "揀", "拥": "擁", "拦": "攔",
    "拨": "撥", "择": "擇", "挚": "摯", "挠": "撓", "挡": "擋",
    "挣": "掙", "挤": "擠", "挥": "揮", "捞": "撈", "损": "損",
    "捡": "撿", "换": "換", "捣": "搗", "掷": "擲", "掺": "摻",
    "揽": "攬", "搀": "攙", "搁": "擱", "搂": "摟", "搅": "攪",
    "携": "攜", "摄": "攝", "摆": "擺", "摇": "搖", "撑": "撐",
    "敌": "敵", "敛": "斂", "断": "斷", "旧": "舊", "旷": "曠",
    "昼": "晝", "显": "顯", "晋": "晉", "晒": "曬", "晓": "曉",
    "晕": "暈", "暂": "暫", "朴": "樸", "杀": "殺", "杂": "雜",
    "权": "權", "条": "條", "来": "來", "杨": "楊", "杰": "傑",
    "极": "極", "构": "構", "枢": "樞", "枣": "棗", "枪": "槍",
    "枫": "楓", "柜": "櫃", "标": "標", "栈": "棧", "栋": "棟",
    "栏": "欄", "树": "樹", "样": "樣", "桥": "橋", "桦": "樺",
    "桨": "槳", "桩": "樁", "梦": "夢", "检": "檢", "楼": "樓",
    "横": "橫", "樱": "櫻", "欢": "歡", "欧": "歐", "残": "殘",
    "毁": "毀", "毕": "畢", "毙": "斃", "氢": "氫", "汇": "匯",
    "汉": "漢", "汤": "湯", "沟": "溝", "没": "沒", "沦": "淪",
    "沪": "滬", "泪": "淚", "泻": "瀉", "泼": "潑", "泽": "澤",
    "洁": "潔", "浅": "淺", "浆": "漿", "测": "測", "济": "濟",
    "浏": "瀏", "浑": "渾", "浓": "濃", "涛": "濤", "涟": "漣",
    "涡": "渦", "涣": "渙", "涤": "滌", "润": "潤", "涨": "漲",
    "涩": "澀", "渊": "淵", "渔": "漁", "渗": "滲", "温": "溫",
    "湾": "灣", "湿": "濕", "溃": "潰", "溅": "濺", "滚": "滾",
    "满": "滿", "滤": "濾", "滥": "濫", "滨": "濱", "滩": "灘",
    "潇": "瀟", "潜": "潛", "澜": "瀾", "灭": "滅", "灯": "燈",
    "灵": "靈", "灾": "災", "炉": "爐", "炼": "煉", "烁": "爍",
    "烂": "爛", "烛": "燭", "烟": "煙", "烦": "煩", "烧": "燒",
    "烫": "燙", "热": "熱", "焕": "煥", "爱": "愛", "爷": "爺",
    "牵": "牽", "牺": "犧", "状": "狀", "犹": "猶", "狭": "狹",
    "狮": "獅", "独": "獨", "狱": "獄", "猎": "獵", "猪": "豬",
    "猫": "貓", "玛": "瑪", "环": "環", "现": "現", "玺": "璽",
    "琼": "瓊", "瑶": "瑤", "电": "電", "画": "畫", "畅": "暢",
    "畴": "疇", "疗": "療", "疮": "瘡", "疯": "瘋", "痒": "癢",
    "痪": "瘓", "痫": "癇", "瘫": "癱", "皱": "皺", "盐": "鹽",
    "监": "監", "盖": "蓋", "盘": "盤", "着": "著", "睁": "睜",
    "睑": "瞼", "瞒": "瞞", "矫": "矯", "矿": "礦", "码": "碼",
    "砖": "磚", "砚": "硯", "硕": "碩", "确": "確", "碍": "礙",
    "礼": "禮", "祷": "禱", "祸": "禍", "禅": "禪", "离": "離",
    "秃": "禿", "积": "積", "称": "稱", "稳": "穩", "穷": "窮",
    "窃": "竊", "窍": "竅", "窑": "窯", "窝": "窩", "窥": "窺",
    "竖": "豎", "竞": "競", "笃": "篤", "笋": "筍", "笔": "筆",
    "笼": "籠", "筛": "篩", "筝": "箏", "筹": "籌", "签": "簽",
    "简": "簡", "箫": "簫", "篮": "籃", "粮": "糧", "紧": "緊",
    "纯": "純", "纱": "紗", "纲": "綱", "纳": "納", "纵": "縱",
    "纸": "紙", "纽": "紐", "练": "練", "组": "組", "细": "細",
    "织": "織", "绍": "紹", "经": "經", "绑": "綁", "结": "結",
    "绕": "繞", "绘": "繪", "给": "給", "络": "絡", "绝": "絕",
    "统": "統", "绣": "繡", "继": "繼", "绩": "績", "绪": "緒",
    "续": "續", "绿": "綠", "维": "維", "绵": "綿", "绷": "繃",
    "绸": "綢", "综": "綜", "绽": "綻", "缀": "綴", "缅": "緬",
    "缆": "纜", "缔": "締", "缕": "縷", "编": "編", "缘": "緣",
    "缚": "縛", "缝": "縫", "缠": "纏", "缩": "縮", "缴": "繳",
    "网": "網", "罗": "羅", "罚": "罰", "罢": "罷", "翘": "翹",
    "耻": "恥", "职": "職", "联": "聯", "聪": "聰", "肃": "肅",
    "肠": "腸", "肤": "膚", "肾": "腎", "肿": "腫", "胀": "脹",
    "胜": "勝", "胶": "膠", "脉": "脈", "脏": "臟", "脑": "腦",
    "脚": "腳", "脱": "脫", "脸": "臉", "腊": "臘", "腾": "騰",
    "舆": "輿", "舰": "艦", "舱": "艙", "艰": "艱", "艳": "豔",
    "艺": "藝", "节": "節", "芦": "蘆", "苍": "蒼", "苏": "蘇",
    "苹": "蘋", "范": "範", "茎": "莖", "荐": "薦", "荚": "莢",
    "荧": "熒", "药": "藥", "莱": "萊", "莲": "蓮", "获": "獲",
    "莹": "瑩", "萝": "蘿", "营": "營", "萦": "縈", "萧": "蕭",
    "萨": "薩", "葱": "蔥", "蓝": "藍", "蓦": "驀", "蔷": "薔",
    "虑": "慮", "虚": "虛", "虽": "雖", "虾": "蝦", "蚀": "蝕",
    "蚁": "蟻", "蚂": "螞", "蚕": "蠶", "蛮": "蠻", "蝇": "蠅",
    "蝉": "蟬", "衅": "釁", "衔": "銜", "补": "補", "衬": "襯",
    "袭": "襲", "装": "裝", "裤": "褲", "见": "見", "观": "觀",
    "规": "規", "视": "視", "览": "覽", "觉": "覺", "触": "觸",
    "誉": "譽", "计": "計", "订": "訂", "认": "認", "讨": "討",
    "让": "讓", "训": "訓", "议": "議", "讯": "訊", "记": "記",
    "讲": "講", "许": "許", "论": "論", "讽": "諷", "设": "設",
    "访": "訪", "证": "證", "评": "評", "识": "識", "诉": "訴",
    "词": "詞", "译": "譯", "试": "試", "诗": "詩", "诚": "誠",
    "话": "話", "诞": "誕", "诠": "詮", "询": "詢", "该": "該",
    "详": "詳", "语": "語", "误": "誤", "诱": "誘", "说": "說",
    "请": "請", "诸": "諸", "诺": "諾", "读": "讀", "课": "課",
    "谁": "誰", "调": "調", "谅": "諒", "谈": "談", "谊": "誼",
    "谋": "謀", "谓": "謂", "谕": "諭", "谚": "諺", "谜": "謎",
    "谢": "謝", "谣": "謠", "谦": "謙", "谨": "謹", "谱": "譜",
    "谷": "穀", "贝": "貝", "贞": "貞", "负": "負", "贡": "貢",
    "财": "財", "责": "責", "贤": "賢", "败": "敗", "账": "賬",
    "货": "貨", "质": "質", "贩": "販", "贫": "貧", "购": "購",
    "贮": "貯", "贯": "貫", "贵": "貴", "贷": "貸", "贸": "貿",
    "费": "費", "贺": "賀", "贼": "賊", "贾": "賈", "贿": "賄",
    "赁": "賃", "资": "資", "赋": "賦", "赌": "賭", "赏": "賞",
    "赐": "賜", "赔": "賠", "赖": "賴", "赚": "賺", "赛": "賽",
    "赞": "讚", "赠": "贈", "赢": "贏", "赵": "趙", "赶": "趕",
    "趋": "趨", "跃": "躍", "践": "踐", "踪": "蹤", "躯": "軀",
    "车": "車", "转": "轉", "轮": "輪", "软": "軟", "轰": "轟",
    "轴": "軸", "轻": "輕", "载": "載", "较": "較", "辅": "輔",
    "辆": "輛", "辈": "輩", "辉": "輝", "辐": "輻", "辑": "輯",
    "输": "輸", "辞": "辭", "辩": "辯", "边": "邊", "辽": "遼",
    "达": "達", "迁": "遷", "过": "過", "迈": "邁", "运": "運",
    "还": "還", "这": "這", "进": "進", "远": "遠", "违": "違",
    "连": "連", "迟": "遲", "迹": "跡", "选": "選", "递": "遞",
    "遗": "遺", "遥": "遙", "邮": "郵", "邻": "鄰", "郑": "鄭",
    "酝": "醞", "酱": "醬", "酿": "釀", "释": "釋", "鉴": "鑑",
    "针": "針", "钉": "釘", "钓": "釣", "钙": "鈣", "钝": "鈍",
    "钞": "鈔", "钟": "鐘", "钢": "鋼", "钥": "鑰", "钦": "欽",
    "钩": "鉤", "钮": "鈕", "钱": "錢", "钻": "鑽", "铁": "鐵",
    "铃": "鈴", "铅": "鉛", "铜": "銅", "铝": "鋁", "铲": "鏟",
    "银": "銀", "铺": "鋪", "链": "鏈", "销": "銷", "锁": "鎖",
    "锄": "鋤", "锅": "鍋", "锋": "鋒", "锐": "銳", "错": "錯",
    "锡": "錫", "锣": "鑼", "锦": "錦", "锯": "鋸", "锻": "鍛",
    "镜": "鏡", "镰": "鐮", "长": "長", "门": "門", "闪": "閃",
    "闭": "閉", "问": "問", "闲": "閒", "间": "間", "闷": "悶",
    "闹": "鬧", "闻": "聞", "闽": "閩", "阀": "閥", "阁": "閣",
    "阅": "閱", "阔": "闊", "队": "隊", "阳": "陽", "阴": "陰",
    "阵": "陣", "阶": "階", "际": "際", "陆": "陸", "陈": "陳",
    "险": "險", "随": "隨", "隐": "隱", "难": "難", "雾": "霧",
    "静": "靜", "韦": "韋", "韩": "韓", "韵": "韻", "页": "頁",
    "顶": "頂", "项": "項", "顺": "順", "须": "須", "顾": "顧",
    "顿": "頓", "预": "預", "领": "領", "颇": "頗", "颈": "頸",
    "频": "頻", "题": "題", "颜": "顏", "额": "額", "风": "風",
    "飞": "飛", "饭": "飯", "饮": "飲", "饰": "飾", "饱": "飽",
    "饼": "餅", "馆": "館", "馒": "饅", "马": "馬", "驼": "駝",
    "驾": "駕", "骂": "罵", "骄": "驕", "验": "驗", "骑": "騎",
    "骗": "騙", "骚": "騷", "骤": "驟", "髅": "髏", "鱼": "魚",
    "鲁": "魯", "鲜": "鮮", "鲤": "鯉", "鲸": "鯨", "鳞": "鱗",
    "鸟": "鳥", "鸡": "雞", "鸣": "鳴", "鸭": "鴨", "鸳": "鴛",
    "鸯": "鴦", "鸽": "鴿", "鸿": "鴻", "鹅": "鵝", "鹤": "鶴",
    "鹰": "鷹", "麦": "麥", "黄": "黃", "齐": "齊", "齿": "齒",
    "龙": "龍", "龟": "龜",
})
POS_PRIORITY = {
    "verb": 0, "noun": 1, "adjective": 2, "adverb": 3,
    "preposition": 4, "pronoun": 5, "determiner": 6,
    "conjunction": 7, "article": 8, "exclamation": 9,
}
AUTO_EXCLUDED = {
    "about", "above", "across", "after", "against", "all", "along", "any",
    "as", "at", "before", "behind", "below", "between", "by", "can", "could",
    "down", "for", "from", "get", "how", "if", "into", "it", "just", "let",
    "may", "might", "more", "most", "must", "no", "not", "of", "on", "one",
    "or", "other", "out", "over", "should", "since", "so", "some", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "though", "through", "to", "under", "until", "up", "us", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "why",
    "will", "with", "would", "yet", "you",
}


def normalized_sentence(text: str) -> str:
    return " ".join(WORD_PATTERN.findall(text.lower().replace("’", "'")))


def definition_score(definition: str, has_example: bool) -> tuple:
    rare = bool(RARE_MARKERS.search(definition))
    label_count = definition[:80].count("(")
    return (rare, not has_example, label_count, len(definition))


def translation_key(text: str) -> str:
    return re.split(r"[；;，,／/（）()]", text.strip(), maxsplit=1)[0].strip()


def traditional(text: str) -> str:
    for simplified, traditional_phrase in SIMPLIFIED_PHRASE_TO_TRADITIONAL.items():
        text = text.replace(simplified, traditional_phrase)
    return text.translate(SIMPLIFIED_TO_TRADITIONAL)


def example_matches(word: str, chinese_definition: str, example: dict) -> bool:
    english = normalized_sentence(str(example.get("english", ""))).split()
    chinese = str(example.get("chinese", ""))
    key = translation_key(chinese_definition)
    return word in english and bool(key) and key in chinese


def load_tatoeba_examples(
    words: set[str],
    translations: dict[str, set[str]],
    english_path: Path,
    chinese_path: Path,
    links_path: Path,
) -> dict[tuple[str, str], dict]:
    candidates: dict[int, tuple[str, str]] = {}
    with bz2.open(english_path, "rt", encoding="utf-8") as source:
        for row in csv.reader(source, delimiter="\t"):
            if len(row) < 3:
                continue
            english = row[2].strip()
            tokens = normalized_sentence(english).split()
            if not 3 <= len(tokens) <= 16:
                continue
            matches = words.intersection(tokens)
            if matches:
                candidates[int(row[0])] = (english, next(iter(matches)))

    chinese_ids: set[int] = set()
    linked: list[tuple[int, int]] = []
    with tarfile.open(links_path, "r:bz2") as archive:
        source = archive.extractfile("links.csv")
        if source is None:
            raise RuntimeError("Tatoeba links.csv is missing")
        for raw in source:
            first, second = map(int, raw.split(b"\t"))
            if first in candidates:
                linked.append((first, second))
                chinese_ids.add(second)
            elif second in candidates:
                linked.append((second, first))
                chinese_ids.add(first)

    chinese_sentences: dict[int, str] = {}
    with bz2.open(chinese_path, "rt", encoding="utf-8") as source:
        for row in csv.reader(source, delimiter="\t"):
            if len(row) >= 3 and int(row[0]) in chinese_ids:
                chinese_sentences[int(row[0])] = row[2].strip()

    result: dict[tuple[str, str], dict] = {}
    for english_id, chinese_id in linked:
        chinese = chinese_sentences.get(chinese_id)
        if not chinese:
            continue
        english, word = candidates[english_id]
        for key in translations[word]:
            if key and key in chinese:
                result.setdefault(
                    (word, key),
                    {"english": english, "chinese": chinese},
                )
    return result


def select_entries(
    connection: sqlite3.Connection,
    words: list[str],
    already_curated: set[str],
    limit: int,
    tatoeba_paths: tuple[Path, Path, Path],
) -> tuple[dict[str, list[dict]], list[dict]]:
    candidates: list[tuple[int, str, list[tuple]]] = []
    for word in words:
        if word in already_curated or word in AUTO_EXCLUDED:
            continue
        rows = connection.execute(
            """
            SELECT word, uk_ipa, us_ipa, part_of_speech, countability,
                   zh_definition, en_definition, examples_json
            FROM entries WHERE normalized_word = ?
            """,
            (word,),
        ).fetchall()
        if not rows:
            continue
        alignment = len(rows) - len({(row[3], row[5]) for row in rows})
        one_character = sum(len(row[5].strip()) == 1 for row in rows)
        missing_examples = sum(row[7] == "[]" for row in rows)
        risk = alignment * 3 + one_character * 2 + missing_examples
        if risk:
            candidates.append((risk, word, rows))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = candidates[:limit]

    translations = {
        word: {translation_key(row[5]) for row in rows}
        for _, word, rows in selected
    }
    examples = load_tatoeba_examples(
        {word for _, word, _ in selected},
        translations,
        *tatoeba_paths,
    )

    replacements: dict[str, list[dict]] = {}
    review: list[dict] = []
    for risk, word, rows in selected:
        grouped: dict[str, list[tuple]] = defaultdict(list)
        for row in rows:
            grouped[row[3]].append(row)

        chosen: list[tuple] = []
        for group_rows in grouped.values():
            viable = [row for row in group_rows if not RARE_MARKERS.search(row[6])]
            if not viable:
                continue
            # FreeDict and OEWN preserve their primary sense first. Keeping the
            # first modern sense per part of speech is safer than preferring a
            # short definition, which can accidentally promote a slang sense.
            chosen.append(viable[0])
        chosen.sort(
            key=lambda row: (
                POS_PRIORITY.get(row[3], 99),
                definition_score(row[6], row[7] != "[]"),
            )
        )
        chosen = chosen[:5]

        entries: list[dict] = []
        unresolved = 0
        for row in chosen:
            source_examples = json.loads(row[7])
            example = next(
                (
                    item for item in source_examples
                    if example_matches(word, row[5], item)
                ),
                None,
            )
            key = translation_key(row[5])
            example = example or examples.get((word, key))
            if example is None:
                unresolved += 1
                continue
            entries.append({
                "word": row[0],
                "uk_ipa": row[1],
                "us_ipa": row[2],
                "part_of_speech": row[3],
                "countability": row[4],
                "chinese": traditional(row[5]),
                "english": row[6],
                "examples": [{
                    "english": example["english"],
                    "chinese": traditional(example["chinese"]),
                }],
            })

        status = "replaced" if entries and unresolved == 0 else "unresolved"
        if status == "replaced":
            replacements[word] = entries
        review.append({
            "word": word,
            "risk_score": risk,
            "source_senses": len(rows),
            "replacement_senses": len(entries),
            "unresolved_senses": unresolved,
            "status": status,
        })
    return replacements, review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--curated", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("/private/tmp/ipa-dict-builder"))
    parser.add_argument("--limit", type=int, default=230)
    args = parser.parse_args()

    curated = json.loads(args.curated.read_text(encoding="utf-8"))
    already_curated = set(curated.get("word_replacements", {}))
    connection = sqlite3.connect(args.database)
    replacements, review = select_entries(
        connection,
        CORE_WORDS,
        already_curated,
        args.limit,
        (
            args.cache / "tatoeba-eng.tsv.bz2",
            args.cache / "tatoeba-cmn.tsv.bz2",
            args.cache / "tatoeba-links.tar.bz2",
        ),
    )
    connection.close()

    args.output.write_text(
        json.dumps({"word_replacements": replacements}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    replaced = sorted(replacements)
    unresolved = [item for item in review if item["status"] != "replaced"]
    lines = [
        "# Common-word curation",
        "",
        f"- Core words inspected: {len(CORE_WORDS)}",
        f"- Previously curated words: {len(already_curated)}",
        f"- New replacement words: {len(replaced)}",
        f"- New replacement senses: {sum(map(len, replacements.values()))}",
        f"- Selected words still requiring review: {len(unresolved)}",
        "",
        "## Newly replaced words",
        "",
        ", ".join(f"`{word}`" for word in replaced) or "None",
        "",
        "## Still requiring manual review",
        "",
        "| Word | Risk | Source senses | Kept senses | Unresolved senses |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| `{item['word']}` | {item['risk_score']} | "
        f"{item['source_senses']} | {item['replacement_senses']} | "
        f"{item['unresolved_senses']} |"
        for item in unresolved
    )
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Generated {len(replaced)} replacement words and "
        f"{sum(map(len, replacements.values()))} senses; "
        f"{len(unresolved)} selected words remain for manual review."
    )


if __name__ == "__main__":
    main()
