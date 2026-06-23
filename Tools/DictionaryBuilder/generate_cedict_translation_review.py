#!/usr/bin/env python3
"""Match local English senses to CC-CEDICT reverse-translation evidence."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sqlite3
import zipfile
from collections import defaultdict
from pathlib import Path

from generate_common_curation import traditional


CEDICT_PATTERN = re.compile(
    r"^(?P<traditional>\S+) (?P<simplified>\S+) "
    r"\[[^\]]+\] /(?P<definitions>.*)/$"
)
WORD_PATTERN = re.compile(r"[a-z]+(?:-[a-z]+)?")
STOP_WORDS = {
    "about", "after", "also", "among", "being", "chiefly", "especially",
    "from", "have", "into", "more", "most", "often", "other", "someone",
    "something", "such", "that", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "used", "using", "usually", "very",
    "when", "where", "which", "while", "with", "without",
}


def tokens(value: str) -> set[str]:
    return {
        token
        for token in WORD_PATTERN.findall(value.lower())
        if len(token) >= 3 and token not in STOP_WORDS
    }


def normalized_text(value: str) -> str:
    return " ".join(WORD_PATTERN.findall(value.lower()))


def similarity(left: str, right: str) -> float:
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence = difflib.SequenceMatcher(
        None,
        normalized_text(left),
        normalized_text(right),
    ).ratio()
    return jaccard * 0.75 + sequence * 0.25


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cedict", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/FullDictionaryAudit/"
            "cedict_translation_review.csv"
        ),
    )
    parser.add_argument(
        "--corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/ai_semantic_corrections.json"
        ),
    )
    parser.add_argument("--minimum-score", type=float, default=0.16)
    parser.add_argument("--minimum-margin", type=float, default=0.035)
    args = parser.parse_args()

    connection = sqlite3.connect(
        f"file:{args.database}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    entries = [dict(row) for row in connection.execute(
        """
        SELECT id, word, normalized_word, part_of_speech, countability,
               zh_definition, en_definition, examples_json
        FROM entries
        ORDER BY normalized_word, id
        """
    )]
    connection.close()
    reviewed_keys = set()
    if args.corrections.exists():
        reviewed_keys = {
            (
                str(item["word"]).strip().lower(),
                str(item["part_of_speech"]).strip().lower(),
                str(item["english"]).strip(),
            )
            for item in json.loads(
                args.corrections.read_text(encoding="utf-8")
            ).get("corrections", [])
        }
    entries = [
        entry
        for entry in entries
        if (
            entry["normalized_word"],
            entry["part_of_speech"].lower(),
            entry["en_definition"],
        ) not in reviewed_keys
    ]
    target_words = {entry["normalized_word"] for entry in entries}
    reverse: dict[str, list[dict]] = defaultdict(list)

    with zipfile.ZipFile(args.cedict) as archive:
        source_name = next(
            name for name in archive.namelist() if name.endswith(".u8")
        )
        with archive.open(source_name) as raw:
            for source_line, encoded in enumerate(raw, 1):
                line = encoded.decode("utf-8").strip()
                if not line or line.startswith("#"):
                    continue
                match = CEDICT_PATTERN.match(line)
                if not match:
                    continue
                chinese = traditional(match.group("traditional"))
                for gloss in match.group("definitions").split("/"):
                    gloss_tokens = tokens(gloss)
                    for word in gloss_tokens & target_words:
                        reverse[word].append({
                            "chinese": chinese,
                            "gloss": gloss.strip(),
                            "source_line": source_line,
                        })

    reviews = []
    for entry in entries:
        candidates = reverse.get(entry["normalized_word"], [])
        if not candidates:
            continue
        scored = []
        for candidate in candidates:
            score = similarity(entry["en_definition"], candidate["gloss"])
            scored.append((score, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        margin = best_score - second_score
        if best_score < args.minimum_score or margin < args.minimum_margin:
            continue
        reviews.append({
            **entry,
            "suggested_chinese": best["chinese"],
            "cedict_gloss": best["gloss"],
            "match_score": f"{best_score:.4f}",
            "score_margin": f"{margin:.4f}",
            "source_line": best["source_line"],
            "source": "CC-CEDICT 2026-06-22",
            "license": "CC BY-SA 4.0",
        })

    reviews.sort(key=lambda item: (
        -float(item["match_score"]),
        item["normalized_word"],
        item["id"],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id", "word", "normalized_word", "part_of_speech", "countability",
        "zh_definition", "en_definition", "examples_json",
        "suggested_chinese", "cedict_gloss", "match_score", "score_margin",
        "source_line", "source", "license",
    ]
    with args.output.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(reviews)
    print(json.dumps({
        "review_count": len(reviews),
        "headword_with_reverse_evidence_count": len(reverse),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
