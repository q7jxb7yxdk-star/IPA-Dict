#!/usr/bin/env python3
"""Match exact local senses to open Wiktionary Chinese translations."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from generate_common_curation import traditional


POS_MAP = {
    "adj": "adjective",
    "adv": "adverb",
    "conj": "conjunction",
    "det": "determiner",
    "intj": "exclamation",
    "name": "proper noun",
    "num": "numeral",
    "prep": "preposition",
    "pron": "pronoun",
}
WORD_PATTERN = re.compile(r"[a-z]+(?:-[a-z]+)?")
STOP_WORDS = {
    "about", "after", "also", "among", "being", "chiefly", "especially",
    "from", "have", "into", "more", "most", "often", "other", "someone",
    "something", "such", "that", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "used", "using", "usually", "very",
    "when", "where", "which", "while", "with", "without",
}


def normalized_word(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalized_pos(value: str) -> str:
    value = value.strip().lower()
    return POS_MAP.get(value, value)


def normalized_text(value: str) -> str:
    return " ".join(WORD_PATTERN.findall(value.lower()))


def content_tokens(value: str) -> set[str]:
    return {
        token
        for token in WORD_PATTERN.findall(value.lower())
        if len(token) >= 3 and token not in STOP_WORDS
    }


def similarity(left: str, right: str) -> float:
    left_normalized = normalized_text(left)
    right_normalized = normalized_text(right)
    if not left_normalized or not right_normalized:
        return 0.0
    left_tokens = content_tokens(left)
    right_tokens = content_tokens(right)
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence = difflib.SequenceMatcher(
        None,
        left_normalized,
        right_normalized,
    ).ratio()
    return jaccard * 0.7 + sequence * 0.3


def chinese_translation(value: str) -> str:
    choices = [
        traditional(part.strip())
        for part in value.split("/")
        if re.search(r"[\u3400-\u9fff]", part)
    ]
    if not choices:
        return ""
    return max(choices, key=lambda item: sum(
        character in "體學書詞語門國後發臺萬與為這個醫蘋關譯號裡麼"
        for character in item
    ))


def load_targets(
    database: Path,
    reviewed_keys: set[tuple[str, str, str]],
) -> tuple[dict[tuple[str, str], list[dict]], set[str]]:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    targets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    words = set()
    for row in connection.execute(
        """
        SELECT id, word, normalized_word, part_of_speech, countability,
               zh_definition, en_definition, examples_json
        FROM entries
        ORDER BY normalized_word, id
        """
    ):
        item = dict(row)
        key = (
            item["normalized_word"],
            item["part_of_speech"].lower(),
        )
        sense_key = (
            item["normalized_word"],
            item["part_of_speech"].lower(),
            item["en_definition"],
        )
        if sense_key in reviewed_keys:
            continue
        targets[key].append(item)
        words.add(item["normalized_word"])
    connection.close()
    return targets, words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
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
            "kaikki_translation_review.csv"
        ),
    )
    parser.add_argument(
        "--corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/ai_semantic_corrections.json"
        ),
    )
    parser.add_argument("--minimum-score", type=float, default=0.24)
    parser.add_argument("--minimum-margin", type=float, default=0.06)
    args = parser.parse_args()

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
    targets, target_words = load_targets(args.database, reviewed_keys)
    candidates_by_key: dict[
        tuple[str, str],
        list[dict],
    ] = defaultdict(list)
    with args.source.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid Kaikki JSON on line {line_number}: {error}"
                ) from error
            word = normalized_word(str(record.get("word", "")))
            if word not in target_words:
                continue
            part = normalized_pos(str(record.get("pos", "")))
            key = (word, part)
            if key not in targets:
                continue
            sense_glosses = [
                gloss
                for sense in record.get("senses", [])
                for gloss in sense.get("glosses", [])[:1]
                if isinstance(gloss, str) and gloss.strip()
            ]
            grouped: dict[str, set[str]] = defaultdict(set)
            source_languages: dict[str, set[str]] = defaultdict(set)
            for translation in record.get("translations", []):
                if str(translation.get("lang_code", "")) != "zh":
                    continue
                translated = chinese_translation(
                    str(translation.get("word", ""))
                )
                sense = str(translation.get("sense", "")).strip()
                if not translated or not sense:
                    continue
                grouped[sense].add(translated)
                source_languages[sense].add(
                    str(translation.get("lang", "Chinese"))
                )
            for sense, translations in grouped.items():
                candidates_by_key[key].append({
                    "translation_sense": sense,
                    "translations": sorted(translations),
                    "source_languages": sorted(source_languages[sense]),
                    "record_glosses": sense_glosses,
                    "source_line": line_number,
                })

    reviews = []
    for key, entries in targets.items():
        candidates = candidates_by_key.get(key, [])
        if not candidates:
            continue
        for entry in entries:
            scored = []
            for candidate in candidates:
                direct_score = similarity(
                    entry["en_definition"],
                    candidate["translation_sense"],
                )
                matching_gloss_score = max(
                    (
                        similarity(entry["en_definition"], gloss)
                        for gloss in candidate["record_glosses"]
                    ),
                    default=0.0,
                )
                score = direct_score
                if matching_gloss_score >= 0.8:
                    score += 0.08
                scored.append((score, direct_score, matching_gloss_score, candidate))
            scored.sort(key=lambda item: item[0], reverse=True)
            best = scored[0]
            second_score = scored[1][0] if len(scored) > 1 else 0.0
            margin = best[0] - second_score
            if best[0] < args.minimum_score or margin < args.minimum_margin:
                continue
            candidate = best[3]
            reviews.append({
                **entry,
                "suggested_chinese": "；".join(candidate["translations"]),
                "translation_sense": candidate["translation_sense"],
                "source_languages": " | ".join(candidate["source_languages"]),
                "match_score": f"{best[0]:.4f}",
                "direct_score": f"{best[1]:.4f}",
                "matching_gloss_score": f"{best[2]:.4f}",
                "score_margin": f"{margin:.4f}",
                "source_line": candidate["source_line"],
                "source": "Kaikki English / English Wiktionary",
                "license": "CC BY-SA 4.0 / GFDL",
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
        "suggested_chinese", "translation_sense", "source_languages",
        "match_score", "direct_score", "matching_gloss_score",
        "score_margin", "source_line", "source", "license",
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
        "source_candidate_group_count": sum(
            len(items) for items in candidates_by_key.values()
        ),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
