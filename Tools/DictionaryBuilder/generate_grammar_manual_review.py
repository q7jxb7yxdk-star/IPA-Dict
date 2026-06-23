#!/usr/bin/env python3
"""Build an evidence ledger for manual verb-transitivity review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path


REVIEW_SCOPE_SIGNATURE = (
    "8ae843ad3af876c04d48297d3a7784945675c21a3fda9b9b97ddc4db02c19ce5"
)

# These indexes refer to the signed 440-row review scope above. Every
# non-deferred row was reviewed against its exact English definition.
INTRANSITIVE_INDEXES = {
    0, 3, 5, 8, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 25, 26,
    29, 30, 32, 33, 35, 36, 37, 42, 45, 46, 47, 48, 51, 53, 55, 57,
    60, 66, 67, 71, 83, 86, 100, 110, 117, 120, 123, 124, 125, 129,
    130, 132, 133, 151, 152, 156, 163, 165, 170, 171, 172, 177, 178,
    180, 185, 189, 190, 197, 201, 202, 206, 214, 215, 216, 219, 223,
    225, 226, 227, 238, 239, 247, 256, 257, 267, 270, 285, 288, 295,
    296, 302, 303, 307, 311, 316, 319, 320, 321, 328, 329, 354, 360,
    363, 364, 369, 370, 372, 374, 375, 376, 381, 382, 389, 390, 391,
    395, 396, 398, 402, 409, 410, 417, 418, 429, 431,
}
AMBITRANSITIVE_INDEXES = {
    6, 24, 34, 70, 75, 76, 85, 98, 114, 115, 119, 126, 139, 147,
    184, 187, 234, 264, 308, 309, 323, 324, 326, 346, 351, 352, 357,
    366, 367, 393, 394, 397, 403,
}
DEFERRED_INDEXES = {
    1, 22, 52, 112, 157, 169, 176, 181, 182, 188, 198, 211, 231,
    232, 233, 237, 242, 243, 245, 249, 253, 254, 293, 304, 327, 331,
    332, 339, 340, 341, 342, 343, 353, 419, 421, 430, 432, 433, 434,
    436,
}
STRUCTURAL_DECISIONS = {
    1: ("adjective", "", "迷人的；誘人的", "Having the power to allure.", False),
    22: ("verb", "", "將要；按計劃", None, False),
    52: ("phrase", "", "懶得；不願費心", "An expression indicating a lack of enthusiasm or willingness to do something.", False),
    112: ("verb", "", "不要；別", "The contraction of do not, used as a negative auxiliary.", False),
    157: ("exclamation", "", "明白了；懂了", "Used to say that one understands something.", False),
    169: ("verb", "", "最好；應該", "Used with an infinitive to say what someone should do or what is advisable.", False),
    176: ("verb", "", "必須；不得不", None, False),
    181: ("noun", "U", "提供住所；住房供應", "The activity of enclosing something or providing a residence for someone.", True),
    182: ("noun", "C", "外殼；殼體", "A container or covering for a mechanical component.", True),
    188: ("verb", "", "不是；並非", "The contraction of is not, used as a negative auxiliary.", False),
    198: ("adjective", "", "笑著的；發笑的", "Laughing or showing amusement.", False),
    211: ("verb", "", "讓我們…吧", "Used before a verb to suggest doing something together.", False),
    231: ("verb", "", "可以；獲准", "Used to express permission or to make a polite request.", False),
    232: ("verb", "", "可能；也許", "Used to express possibility.", False),
    233: ("verb", "", "願；但願", "Used, especially formally, to express a wish or hope.", False),
    237: ("verb", "", "可能；也許", "Used to express a possibility or a conditional action.", False),
    242: ("verb", "", "必須；一定要", "Used to express an obligation or requirement.", False),
    243: ("verb", "", "一定；想必", "Used to say that something is very likely or logically certain.", False),
    245: ("phrase", "", "沒關係；別在意", "Used to tell someone not to worry about something or that it is not important.", False),
    249: ("verb", "", "應該；應當", "Used to express duty, obligation, or what is advisable.", False),
    253: ("noun", "U", "繪畫；上油漆", "The action of applying paint to a surface.", True),
    254: ("noun", "C", "畫作；油畫", "An illustration or artwork made using paint.", True),
    293: ("verb", "T", "重新創造；再現", "To create something again or reproduce it.", True),
    304: ("phrase", "", "安息；願逝者安息", None, False),
    327: ("adjective", "", "自成一體的；獨立的", "Not requiring external or additional support; complete in itself.", False),
    331: ("noun", "C", "背景；環境", "The time, place, and circumstances in which something occurs.", True),
    332: ("verb", "", "將；應當", "Used to express determination, obligation, or a formal future action.", False),
    339: ("verb", "", "真該；應該", "Used with verbs such as see or hear to emphasize that something is remarkable.", False),
    340: ("verb", "", "應該會；可能會", "Used to express an expected or probable future event.", False),
    341: ("verb", "", "應該；最好", "Used to give advice or make a recommendation.", False),
    342: ("verb", "", "應該；理應", "Used to express expectation or what ought to happen.", False),
    343: ("exclamation", "", "去你的（粗俗、冒犯）", "A vulgar and offensive expression of extreme anger or rejection.", False),
    353: ("verb", "T", "用匙舀；用匙盛", "To serve or transfer something using a spoon.", True),
    419: ("verb", "", "過去常常；曾經", "Used to describe a past habit or state that no longer exists.", False),
    421: ("noun", "U", "投票；表決", "The act or process of casting a vote.", True),
    430: ("verb", "", "不會；將不", "The contraction of will not, used as a negative auxiliary.", False),
    432: ("verb", "", "會；將會", "Used as an auxiliary to express a conditional action or state.", False),
    433: ("verb", "", "願意；可否", "Used in questions to make a polite request or invitation.", False),
    434: ("verb", "", "想要；希望", "Used to express a want or desire politely.", False),
    436: ("noun", "C or U", "摔跤；摔跤運動", "A sport in which two opponents grapple and try to subdue each other.", True),
}


def normalized_word(value: str) -> str:
    return " ".join(value.strip().lower().split())


def grammar_label(tags: set[str]) -> str:
    transitive = "transitive" in tags
    intransitive = "intransitive" in tags
    if "ambitransitive" in tags or (transitive and intransitive):
        return "I or T"
    if transitive:
        return "T"
    if intransitive:
        return "I"
    return ""


def oewn_verb_label(frames: list[str]) -> str:
    transitive = any(
        frame.startswith("vt") or frame == "ditransitive"
        for frame in frames
    )
    intransitive = any(
        frame.startswith("vi")
        or frame.startswith("via")
        or frame in {"nonreferential", "nonreferential-sent"}
        for frame in frames
    )
    if transitive and intransitive:
        return "I or T"
    if transitive:
        return "T"
    if intransitive:
        return "I"
    return ""


def load_kaikki_evidence(
    source: Path,
    targets: set[str],
) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    with source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid Kaikki JSON on line {line_number}: {error}"
                ) from error
            word = normalized_word(str(item.get("word", "")))
            if (
                item.get("lang_code") != "en"
                or item.get("pos") != "verb"
                or word not in targets
            ):
                continue
            entry_tags = {str(tag) for tag in item.get("tags", [])}
            for sense in item.get("senses", []):
                tags = entry_tags | {
                    str(tag)
                    for tag in sense.get("tags", [])
                }
                label = grammar_label(tags)
                for gloss in sense.get("glosses", []):
                    result[word].append({
                        "definition": str(gloss),
                        "label": label,
                        "tags": sorted(tags),
                    })
    return result


def load_oewn_evidence(
    archive: Path,
    targets: set[str],
) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    synsets: dict[str, dict] = {}
    entries: dict[str, list[dict]] = defaultdict(list)
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if name.startswith("verb.") and name.endswith(".json"):
                synsets.update(json.loads(bundle.read(name)))
            elif name.startswith("entries-") and name.endswith(".json"):
                data = json.loads(bundle.read(name))
                for lemma, parts in data.items():
                    word = normalized_word(lemma.replace("_", " "))
                    if word not in targets or "v" not in parts:
                        continue
                    entries[word].extend(parts["v"].get("sense", []))
    for word, senses in entries.items():
        for sense in senses:
            frames = [str(frame) for frame in sense.get("subcat", [])]
            synset = synsets.get(str(sense.get("synset", "")), {})
            result[word].append({
                "definition": " ".join(
                    str(value)
                    for value in synset.get("definition", [])
                ),
                "label": oewn_verb_label(frames),
                "frames": frames,
            })
    return result


def syntax_marker(definition: str) -> tuple[str, str]:
    lowered = definition.lower()
    if re.search(r"\bditransitive\b", lowered):
        return "T", "explicit_ditransitive_marker"
    if re.search(r"\breflexive\b", lowered):
        return "T", "explicit_reflexive_marker"
    if re.search(r"\bergative\b", lowered):
        return "I or T", "explicit_ergative_marker"
    return "", ""


def scope_signature(reviews: list[dict]) -> str:
    payload = "\n".join(
        f"{item['entry_id']}\t{item['word']}\t{item['english']}"
        for item in reviews
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def apply_manual_decisions(reviews: list[dict]) -> None:
    signature = scope_signature(reviews)
    if signature != REVIEW_SCOPE_SIGNATURE:
        raise RuntimeError(
            "Manual verb review scope changed; refusing to apply index-based "
            f"decisions ({signature})."
        )
    all_indexes = set(range(len(reviews)))
    classified = (
        INTRANSITIVE_INDEXES
        | AMBITRANSITIVE_INDEXES
        | DEFERRED_INDEXES
    )
    if (
        INTRANSITIVE_INDEXES & AMBITRANSITIVE_INDEXES
        or INTRANSITIVE_INDEXES & DEFERRED_INDEXES
        or AMBITRANSITIVE_INDEXES & DEFERRED_INDEXES
    ):
        raise RuntimeError("Manual review index sets overlap.")
    if not classified <= all_indexes:
        raise RuntimeError("Manual review index is outside the signed scope.")
    for index, item in enumerate(reviews):
        if index in DEFERRED_INDEXES:
            (
                new_part,
                new_countability,
                new_chinese,
                new_english,
                grammar_applicable,
            ) = STRUCTURAL_DECISIONS[index]
            item["structural_resolution"] = {
                "new_part_of_speech": new_part,
                "new_countability": new_countability,
                "new_chinese": new_chinese,
                "new_english": new_english or item["english"],
                "grammar_applicable": grammar_applicable,
            }
            item["status"] = "completed_structural_review"
            item["review_reason"] = (
                "Reviewed structural correction for an auxiliary, fixed "
                "expression, malformed gloss, or non-verb source sense."
            )
            continue
        if index in INTRANSITIVE_INDEXES:
            label = "I"
        elif index in AMBITRANSITIVE_INDEXES:
            label = "I or T"
        else:
            label = "T"
        item["reviewed_label"] = label
        item["review_reason"] = (
            "Manual syntactic review of the exact displayed sense, checked "
            "against available Kaikki and OEWN evidence."
        )
        item["status"] = "completed_manual_review"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kaikki", type=Path, required=True)
    parser.add_argument("--oewn", type=Path, required=True)
    parser.add_argument(
        "--review",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/FullDictionaryAudit/"
            "missing_grammar_labels.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/grammar_manual_review.json"
        ),
    )
    args = parser.parse_args()

    existing_data = None
    if args.output.exists():
        existing_data = json.loads(
            args.output.read_text(encoding="utf-8")
        )
    rows = [
        row
        for row in csv.DictReader(
            args.review.open(encoding="utf-8-sig")
        )
        if row["part_of_speech"].lower() == "verb"
    ]
    targets = {
        normalized_word(row["normalized_word"])
        for row in rows
    }
    kaikki = load_kaikki_evidence(args.kaikki, targets)
    oewn = load_oewn_evidence(args.oewn, targets)

    reviews = []
    for row in rows:
        word = normalized_word(row["normalized_word"])
        suggested_label, suggestion_reason = syntax_marker(
            row["en_definition"]
        )
        reviews.append({
            "entry_id": int(row["id"]),
            "word": word,
            "part_of_speech": row["part_of_speech"],
            "chinese": row["zh_definition"],
            "english": row["en_definition"],
            "source_evidence": {
                "kaikki": kaikki.get(word, []),
                "oewn": oewn.get(word, []),
            },
            "suggested_label": suggested_label,
            "suggestion_reason": suggestion_reason,
            "reviewed_label": "",
            "review_reason": "",
            "status": "pending_manual_review",
        })

    current_signature = scope_signature(reviews)
    if current_signature == REVIEW_SCOPE_SIGNATURE:
        apply_manual_decisions(reviews)
    elif (
        existing_data
        and existing_data.get("scope_signature") == REVIEW_SCOPE_SIGNATURE
    ):
        apply_manual_decisions(existing_data["reviews"])
        existing_data["structural_count"] = sum(
            isinstance(item.get("structural_resolution"), dict)
            for item in existing_data["reviews"]
        )
        args.output.write_text(
            json.dumps(existing_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        existing_by_key = {
            (
                item["word"],
                item["english"],
            ): item
            for item in existing_data.get("reviews", [])
        }
        unexpected = [
            item
            for item in reviews
            if (
                item["word"],
                item["english"],
            ) not in existing_by_key
            or existing_by_key[(
                item["word"],
                item["english"],
            )].get("reviewed_label")
        ]
        if unexpected:
            raise RuntimeError(
                "Current verb review queue does not match the deferred "
                "portion of the signed manual review."
            )
        print(
            f"Retained {args.output}: "
            f"{existing_data['completed_count']} completed decisions; "
            f"{existing_data['structural_count']} structural decisions."
        )
        return
    else:
        raise RuntimeError(
            "Manual verb review scope changed without a matching signed "
            "review ledger."
        )
    completed = sum(
        bool(item["reviewed_label"])
        for item in reviews
    )
    args.output.write_text(
        json.dumps(
            {
                "sources": [
                    "Kaikki English 2026-06-15 / English Wiktionary",
                    "Open English WordNet 2025",
                ],
                "license": (
                    "CC BY-SA 4.0 / GFDL; WordNet License / CC BY 4.0"
                ),
                "review_count": len(reviews),
                "completed_count": completed,
                "structural_count": sum(
                    isinstance(item.get("structural_resolution"), dict)
                    for item in reviews
                ),
                "scope_signature": scope_signature(reviews),
                "reviews": reviews,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"Created {args.output}: {len(reviews)} verb rows, "
        f"{completed} completed, {len(reviews) - completed} deferred."
    )


if __name__ == "__main__":
    main()
