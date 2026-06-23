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
