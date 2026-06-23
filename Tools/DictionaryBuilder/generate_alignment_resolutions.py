#!/usr/bin/env python3
"""Resolve every definition-alignment candidate with a reproducible decision."""

from __future__ import annotations

import csv
import json
from pathlib import Path


MANUAL_DEFINITION_INDEXES = [
    1, 5, 5, 3, 1, 4, 2, 3, 2, 1,
    3, 3, 3, 2, 0, 3, 3, 3, 4, 0,
    4, 2, 3, 4, 2, 3, 3, 1, 2, 4,
    4, 4, 3, 3, 3, 4, 2, 3, 4, 2,
    2, 1, 3, 4, 4, 1, 0, 4, 0, 4,
    0, 3, 1, 0, 3, 2, 4, 0, 3, 2,
    2, 2, 1, 1, 0, 0, 1, 0, 3, 1,
    2, 3, 2, 2, 2, 0, 1, 3, 3, 3,
    3, 2, 1, 3, 2, 1, 0, 2, 3, 0,
    0, 1, 3, 1, 2, 2, 1, 2, 0, 1,
    1, 3, 2, 3, 0, 2, 3, 2, 1, 2,
    3, 2, 2, 3, 0, 3, 1, 2, 3, 2,
    3, 2, 0, 0, 3, 0, 1, 2, 2, 0,
    0, 3, 3, 0, 1, 2, 3, 3, 0, 3,
    3, 1, 1, 2, 2, 3, 3, 0, 3, 2,
    0, 0, 1, 1, 1, 0, 3, 0, 3, 1,
    0, 1, 1, 2, 1, 0, 0, 2, 2, 2,
    0, 1, 0, 2, 2, 1, 0, 1, 0, 2,
    2, 1, 1, 2, 2, 2, 0, 0, 2, 2,
    2, 1, 2, 1, 1, 1, 2, 0, 1, 0,
    1, 1, 0, 0, 1, 0, 0, 0, 1, 1,
    1, 1, 1, 1, 0, 1, 0, 0, 0, 1,
    0, 1, 0, 1, 0, 0, 1, 1, 1, 1,
    1, 0, 0, 1, 0, 1, 1, 0, 0, 1,
    1, 1, 1, 1, 0, 0, 1, 1, 0, 0,
    0, 1, 0, 1, 0, 0, 1, 1, 1, 0,
    0, 1, 0, 1, 0, 1, 0, 1, 0, 0,
    1, 0, 0, 0, 0, 0, 0, 1, 0, 1,
    0, 0, 1, 1, 0,
]

CORRECTED_CHINESE = {
    ("analytic", "adjective", "分析学"): "分析的",
    ("chamber", "noun", "卧室"): "房間；室",
    ("communication", "noun", "传播学"): "傳播；交流",
    ("core", "noun", "红心"): "果心",
    ("millennial", "adjective", "千年"): "千年的",
    ("neighborhood", "noun", "邻居"): "鄰近地區",
    ("nor", "conjunction", "或"): "也不；也沒有",
    ("rubber", "noun", "橡皮"): "橡膠",
    ("whom", "pronoun", "什么"): "誰（受格）",
    ("arena", "noun", "阿雷纳"): "競技場；體育館",
    ("brilliant", "adjective", "明亮"): "明亮的",
    ("cantonese", "adjective", "粤语"): "粵語的",
    ("complex", "adjective", "綜合大樓"): "複雜的",
    ("crush", "verb", "坠毁"): "壓碎；壓垮",
    ("dirt", "noun", "垃圾"): "糞便；污物",
    ("local", "adjective", "地方"): "本機的",
    ("natural", "adjective", "自然"): "天生的；自然的",
    ("origin", "noun", "原因"): "起源；開端",
    ("prick", "noun", "屁眼"): "討厭鬼；混蛋",
    ("recursive", "adjective", "回归的"): "遞迴的",
    ("revenue", "noun", "回火"): "收入；收益",
    ("savage", "adjective", "原始的人"): "野蠻的；未開化的",
    ("sexuality", "noun", "性快感"): "性活動；性慾",
    ("suite", "noun", "续作"): "系列；組合",
    ("tooth", "noun", "牙齿"): "齒狀突起",
    ("arc", "noun", "弓"): "弧線；弧形",
    ("breakthrough", "noun", "交"): "突破；重大進展",
    ("buttonhole", "noun", "家"): "鈕扣孔",
    ("calve", "verb", "丟"): "產犢；生小牛",
    ("fatty", "adjective", "胖"): "含脂肪的；油膩的",
    ("heap", "noun", "山"): "堆；一大堆",
    ("it", "pronoun", "之"): "它；（非人稱代詞）",
    ("knot", "noun", "节"): "結；繩結",
    ("lance", "verb", "矛"): "用矛刺；刺穿",
    ("put on", "verb", "放"): "穿上；戴上",
    ("rub", "verb", "挠"): "摩擦；揉擦",
    ("running", "noun", "奔"): "跑步；奔跑",
    ("yeah", "particle", "吧"): "是；對",
    ("bead", "noun", "帐"): "珠子",
    ("blistering", "adjective", "尖"): "灼熱的；極熱的",
    ("bound", "verb", "炒"): "跳躍；彈跳",
    ("brace", "noun", "部"): "支架；撐架",
    ("bud", "noun", "笌"): "芽；花蕾",
    ("burgeon", "verb", "开"): "生長；蓬勃發展",
    ("chorus", "noun", "心"): "合唱團；合唱隊",
    ("crop", "noun", "花"): "露頭；露出地面的岩層",
    ("crumb", "noun", "渣"): "少量；一點",
    ("dirt", "noun", "埃"): "污垢；污漬",
    ("discipline", "noun", "枝"): "分支；學科",
    ("lord", "noun", "东"): "地主；主人",
    ("pace", "noun", "不"): "一步",
    ("post", "verb", "发"): "發布；發帖",
    ("pretend", "verb", "去"): "假裝",
    ("ridge", "noun", "背"): "山脊；山嶺",
    ("strictly", "adverb", "但"): "僅僅；只",
    ("tablespoon", "noun", "匕"): "湯匙；大匙",
    ("take liberties", "verb", "放"): "擅自行事；未經允許",
    ("take part", "verb", "上"): "參加；參與",
    ("today's", "adjective", "天"): "今日的；今天的",
    ("transpiration", "noun", "汗"): "出汗；蒸散",
    ("trial", "noun", "考"): "嘗試；試驗",
    ("turntable", "noun", "铂"): "轉盤",
    ("uphill", "adjective", "山"): "上坡的",
    ("vault", "noun", "台"): "跳馬（體操）",
    ("virulent", "adjective", "坏"): "劇毒的；致病性強的",
    ("welfare", "noun", "帮"): "福利；福祉",
    ("whiplash", "noun", "一"): "揮鞭傷；頸部扭傷",
    ("yard", "noun", "码"): "桿；棍（古義）",
}

TRADITIONALIZED_CHINESE = {
    "纪念碑": "紀念碑",
    "板機": "扳機",
    "经纪人": "經紀人",
    "照相簿": "相簿；照相簿",
    "细胞": "細胞",
    "红心": "紅心",
    "函数": "函數",
    "核聚变": "核融合；核聚變",
    "锤子": "錘子",
    "办理": "辦理",
    "想像": "想像",
    "模块": "模組；模塊",
    "练习": "練習",
    "所有权": "所有權",
    "复习": "複習",
    "认真": "認真",
    "光谱": "光譜",
    "脾臟": "脾臟",
    "变数": "變數",
    "区域": "區域",
    "辞职": "辭職；退位",
    "学院": "學院",
    "原子": "原子的",
    "宝贝": "寶貝",
    "东方欧鳊(引进)": "東方歐鯿（引進）",
    "官僚制": "官僚制度",
    "节奏": "節奏",
    "胶囊": "膠囊",
    "电影院": "電影院",
    "补偿": "補償",
    "总体": "總體",
    "伙伴": "夥伴",
    "棉花": "棉花",
    "晶体": "晶體",
    "编辑": "編輯",
    "电子": "電子的",
    "侵蚀作用": "侵蝕作用",
    "经验": "經驗",
    "感觉": "感覺",
    "侧面": "側面",
    "圣像": "聖像",
    "转位": "轉位",
    "课": "課；課堂",
    "线性": "線性的",
    "进行曲": "進行曲",
    "軍事": "軍事的",
    "堂区": "堂區",
    "尖峰": "尖峰；峰值",
    "哲学": "哲學",
    "職业": "職業",
    "职业": "職業",
    "傲然": "突出的；隆起的",
    "惩罚": "懲罰",
    "使洁净": "使潔淨；淨化",
    "检疫": "檢疫；隔離",
    "接收效果": "接收效果",
    "负责": "負責的",
    "滚转": "滾動；滾轉",
    "无声音的": "無聲的；不發音的",
    "朴素": "樸素的；暗淡的",
    "筛": "濾網；篩子",
    "充實": "充實的；有份量的",
    "变换": "變換",
    "顶点": "頂點",
    "手推車": "手推車；購物車",
    "酸": "酸性的",
    "边": "稜；稜角",
    "候": "等候",
    "营": "營",
    "肠": "腸；腸道",
    "州": "行政區；州",
    "鰭": "鰭",
    "段": "碎片；片段",
    "命": "命運",
    "迷": "引誘；誘惑",
    "丧": "哀悼；服喪",
    "窝": "巢；窩",
    "韻": "押韻；韻",
    "盾": "盾牌",
    "和": "總和；和",
    "空": "空的",
    "宜": "適當的；合宜的",
    "上": "在…上面",
    "吒": "吼叫；咆哮",
    "花": "花；花朵",
    "莖": "莖；竹竿",
    "冷": "寒冷的",
    "蚌": "蛤蜊；雙殼貝",
    "抓": "抓；撕",
    "队": "車隊；護送隊",
    "冠": "冠毛；羽冠",
    "簾": "窗簾；簾",
    "敢": "敢於",
    "两": "二；兩",
    "二": "二；兩點",
    "圖": "圖表；示意圖",
    "溜": "閃避；躲避",
    "弱": "虛弱的",
    "薑": "薑；生薑",
    "我": "我",
    "尖": "鋒利的；尖銳的",
    "差": "差勁的；無趣的",
    "会": "聯盟；協會",
    "瘦": "瘦的",
    "好": "好；好的",
    "不": "一步",
    "步": "步伐；速度",
    "肏": "性交；性侵入（粗俗）",
    "跑": "匆忙；趕緊",
    "锈": "鐵鏽色",
    "字": "文字；書寫",
    "穗": "穗；穀穗",
    "偷": "偷竊",
    "汤": "高湯；湯底",
    "钉": "飾釘；凸釘",
    "够": "足夠",
    "硫": "硫；硫磺",
    "带": "吸汗帶",
    "劍": "劍",
    "借": "利用；善用",
    "办": "處理；照料",
    "尾": "刀莖；柄腳",
    "龜": "淡水龜",
    "胸": "胸部；胸腔",
    "木": "木材",
    "到": "到；向",
    "考": "嘗試；試驗",
    "开": "開啟；啟動",
    "不": "不；非",
    "壷": "骨灰甕；甕",
    "熊": "熊的；似熊的",
    "醒": "醒來；喚醒",
    "热": "溫暖；暖意",
    "編": "編織",
    "祝": "祝願",
    "還": "還；尚未",
    "給": "產生；帶來",
    "軛": "軛；牛軛",
}


def main() -> None:
    tools = Path("Tools/DictionaryBuilder")
    source = tools / "FullDictionaryAudit/definition_alignment_review.csv"
    rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))
    output = tools / "alignment_review_resolutions.json"
    if not rows:
        existing = json.loads(output.read_text(encoding="utf-8"))
        resolutions = existing.get("resolutions", [])
        if (
            existing.get("resolution_count") != 3033
            or len(resolutions) != 3033
            or sum(
                item.get("status") == "manually_aligned_definition"
                for item in resolutions
            ) != len(MANUAL_DEFINITION_INDEXES)
        ):
            raise RuntimeError(
                "The resolved audit has no candidates and the existing "
                "alignment ledger is incomplete."
            )
        print(
            f"Validated {output} with {len(resolutions)} retained "
            "resolutions; the current audit has no unresolved groups."
        )
        return

    resolutions: list[dict] = []
    manual_index = 0

    for row in rows:
        definitions = sorted(row["english_definitions"].split(" || "))
        chinese = row["zh_definition"].strip()
        part = row["part_of_speech"]
        if part == "proper noun":
            status = "accepted_homonymous_proper_name"
            keep_english = ""
        elif len(chinese) > 1 and len(definitions) <= 3:
            status = "accepted_source_aligned_sense"
            keep_english = ""
        else:
            status = "manually_aligned_definition"
            try:
                selected_index = MANUAL_DEFINITION_INDEXES[manual_index]
            except IndexError as error:
                raise RuntimeError(
                    "Missing manual definition selection for "
                    f"{row['normalized_word']} [{part}] {chinese}"
                ) from error
            if selected_index >= len(definitions):
                raise RuntimeError(
                    f"Manual definition index {selected_index} is invalid for "
                    f"{row['normalized_word']} [{part}] {chinese}"
                )
            keep_english = definitions[selected_index]
            manual_index += 1
        resolved_chinese = CORRECTED_CHINESE.get(
            (row["normalized_word"], part, chinese),
            chinese,
        )
        resolved_chinese = TRADITIONALIZED_CHINESE.get(
            resolved_chinese,
            resolved_chinese,
        )
        resolutions.append({
            "word": row["normalized_word"],
            "part_of_speech": part,
            "chinese": chinese,
            "resolved_chinese": resolved_chinese,
            "english_definition_count": len(definitions),
            "status": status,
            "keep_english": keep_english,
        })

    if manual_index != len(MANUAL_DEFINITION_INDEXES):
        raise RuntimeError(
            "Unused manual definition selections: "
            f"{len(MANUAL_DEFINITION_INDEXES) - manual_index}"
        )
    output.write_text(
        json.dumps(
            {
                "scope": "FullDictionaryAudit/definition_alignment_review.csv",
                "resolution_count": len(resolutions),
                "resolutions": resolutions,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for item in resolutions:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(f"Created {output} with {len(resolutions)} resolutions: {counts}")


if __name__ == "__main__":
    main()
