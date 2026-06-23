#!/usr/bin/env python3
"""Generate the signed manual review for remaining noun countability."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


REVIEW_SCOPE_SIGNATURE = (
    "be1755fca10f81abff4bc9c6e128e5a295384ba29ae8fee71edab4bd1ddcf256"
)

UNCOUNTABLE_INDEXES = {
    2, 8, 9, 14, 15, 18, 19, 22, 23, 24, 25, 26, 31, 35, 41, 46,
    48, 55, 56, 65, 67, 74, 78, 80, 105, 118, 129, 130, 134, 140,
    141, 142, 146,
}
COUNTABLE_OR_UNCOUNTABLE_INDEXES = {
    12, 17, 37, 39, 47, 62, 66, 71, 87, 90, 99, 102, 107, 108,
    113, 114, 126, 128, 131, 145,
}
STRUCTURAL_DECISIONS = {
    27: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "後天",
        "new_english": "The day that is two days after today.",
        "grammar_applicable": False,
    },
    28: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "前天",
        "new_english": "The day that was two days before today.",
        "grammar_applicable": False,
    },
    36: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "下方；下面",
        "new_english": "A place or position below.",
        "grammar_applicable": False,
    },
    38: {
        "new_part_of_speech": "noun",
        "new_countability": "C",
        "new_chinese": "木板便橋；棧板橋",
        "new_english": "A simple bridge or walkway made from duckboards.",
        "grammar_applicable": True,
    },
    89: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "一點鐘",
        "new_english": "The time shown as 1:00 on a twelve-hour clock.",
        "grammar_applicable": False,
    },
    93: {
        "action": "delete",
        "grammar_applicable": False,
    },
    100: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "相當多；不少",
        "new_english": "An indefinite but fairly large number.",
        "grammar_applicable": False,
    },
    116: {
        "new_part_of_speech": "noun",
        "new_countability": "U",
        "new_chinese": "腹瀉（粗俗）",
        "new_english": "Diarrhea.",
        "grammar_applicable": True,
    },
    132: {
        "new_part_of_speech": "noun",
        "new_countability": "C",
        "new_chinese": "謝意；感謝的話",
        "new_english": "An expression of appreciation or gratitude.",
        "grammar_applicable": True,
    },
    135: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "這次；這個時候",
        "new_english": "On this occasion or at this particular time.",
        "grammar_applicable": False,
    },
    136: {
        "new_part_of_speech": "phrase",
        "new_countability": "",
        "new_chinese": "這邊；這個方向",
        "new_english": "In the indicated direction or manner.",
        "grammar_applicable": False,
    },
}


def normalized_word(value: str) -> str:
    return " ".join(value.strip().lower().split())


def noun_header_label(item: dict) -> str:
    labels = set()
    for template in item.get("head_templates", []):
        if template.get("name") != "en-noun":
            continue
        args = template.get("args", {})
        expansion = str(template.get("expansion", "")).lower()
        if (
            args.get("1") == "~"
            or "countable and uncountable" in expansion
        ):
            labels.add("C or U")
        elif args.get("1") == "-" or "uncountable" in expansion:
            labels.add("U")
        elif (
            args.get("1") in {"!", "p"}
            or "plural only" in expansion
            or "plural " in expansion
            or not args
        ):
            labels.add("C")
    return next(iter(labels)) if len(labels) == 1 else ""


def scope_signature(reviews: list[dict]) -> str:
    payload = "\n".join(
        f"{item['entry_id']}\t{item['word']}\t{item['english']}"
        for item in reviews
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kaikki", type=Path, required=True)
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
            "Tools/DictionaryBuilder/noun_countability_review.json"
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
        if row["part_of_speech"].lower() == "noun"
    ]
    targets = {
        normalized_word(row["normalized_word"])
        for row in rows
    }
    evidence: dict[str, list[dict]] = defaultdict(list)
    with args.kaikki.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            word = normalized_word(str(item.get("word", "")))
            if (
                item.get("lang_code") != "en"
                or item.get("pos") != "noun"
                or word not in targets
            ):
                continue
            header_label = noun_header_label(item)
            for sense in item.get("senses", []):
                for gloss in sense.get("glosses", []):
                    evidence[word].append({
                        "header_label": header_label,
                        "definition": str(gloss),
                        "tags": [
                            str(tag)
                            for tag in sense.get("tags", [])
                        ],
                    })

    reviews = []
    for index, row in enumerate(rows):
        structural = STRUCTURAL_DECISIONS.get(index)
        if structural and structural.get("action") == "delete":
            label = ""
            status = "completed_structural_review"
        elif structural:
            label = structural["new_countability"]
            status = "completed_structural_review"
        elif index in UNCOUNTABLE_INDEXES:
            label = "U"
            status = "completed_manual_countability_review"
        elif index in COUNTABLE_OR_UNCOUNTABLE_INDEXES:
            label = "C or U"
            status = "completed_manual_countability_review"
        else:
            label = "C"
            status = "completed_manual_countability_review"
        reviews.append({
            "entry_id": int(row["id"]),
            "word": row["normalized_word"],
            "part_of_speech": row["part_of_speech"],
            "chinese": row["zh_definition"],
            "english": row["en_definition"],
            "source_evidence": evidence.get(row["normalized_word"], []),
            "reviewed_label": label,
            "structural_resolution": structural,
            "review_reason": (
                "Manual countability review of the exact displayed sense, "
                "checked against Kaikki noun headers and glosses."
            ),
            "status": status,
        })

    signature = scope_signature(reviews)
    if signature != REVIEW_SCOPE_SIGNATURE:
        if (
            existing_data
            and existing_data.get("scope_signature")
            == REVIEW_SCOPE_SIGNATURE
            and not reviews
        ):
            print(
                f"Retained {args.output}: "
                f"{existing_data['completed_count']} completed noun reviews."
            )
            return
        raise RuntimeError(
            "Noun review scope changed; refusing to apply signed decisions "
            f"({signature})."
        )
    args.output.write_text(
        json.dumps(
            {
                "source": (
                    "Kaikki English 2026-06-15 / English Wiktionary"
                ),
                "license": "CC BY-SA 4.0 / GFDL",
                "review_count": len(reviews),
                "completed_count": len(reviews),
                "structural_count": len(STRUCTURAL_DECISIONS),
                "scope_signature": signature,
                "reviews": reviews,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"Created {args.output}: {len(reviews)} completed noun reviews, "
        f"{len(STRUCTURAL_DECISIONS)} structural decisions."
    )


if __name__ == "__main__":
    main()
