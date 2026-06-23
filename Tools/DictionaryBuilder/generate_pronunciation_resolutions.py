#!/usr/bin/env python3
"""Build a reproducible UK/US IPA resolution ledger from Kaikki data."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


POS_MAP = {
    "adj": "adjective",
    "adv": "adverb",
    "conj": "conjunction",
    "det": "determiner",
    "num": "numeral",
    "pron": "pronoun",
    "name": "proper noun",
    "intj": "exclamation",
    "prep": "preposition",
    "prep_phrase": "phrase",
    "adv_phrase": "phrase",
}
UK_TAG_PRIORITY = {
    "received-pronunciation": 0,
    "general-british": 1,
    "standard-british": 1,
    "uk": 2,
    "british": 2,
    "england": 3,
}
US_TAG_PRIORITY = {
    "general-american": 0,
    "us": 1,
}
IPA_PATTERN = re.compile(r"^/[^/\n]+/$")
COMPLETED_RESOLUTIONS = [
    {
        "word": "asterix",
        "part_of_speech": "proper noun",
        "english": (
            "A series of French comic books written by René Goscinny and "
            "illustrated by Albert Uderzo about an Ancient Gaul named Asterix."
        ),
        "us_ipa": "/ˈæstəɹɪks/",
    },
    {
        "word": "bedstead",
        "part_of_speech": "noun",
        "english": (
            "The framework that supports a bed; the rigid structural "
            "components of a bed, excluding the mattress, box spring, etc; "
            "bedframe."
        ),
        "us_ipa": "/ˈbɛd.stɛd/",
    },
    {
        "word": "father",
        "part_of_speech": "noun",
        "english": (
            "(Christianity) One of the chief ecclesiastical authorities "
            "of the first centuries after Christ."
        ),
        "uk_ipa": "/ˈfɑː.ðə(ɹ)/",
    },
    {
        "word": "father",
        "part_of_speech": "proper noun",
        "english": (
            "(Wicca) One of the triune gods of the Horned God in Wicca, "
            "representing a man, younger than the elderly Sage and older "
            "than the boyish Master."
        ),
        "uk_ipa": "/ˈfɑː.ðə(ɹ)/",
    },
    {
        "word": "man",
        "part_of_speech": "proper noun",
        "english": "The genus Homo.",
        "uk_ipa": "/ˈmæn/",
    },
    {
        "word": "jeddah",
        "part_of_speech": "proper noun",
        "english": "A port city in Mecca Province, Saudi Arabia.",
        "uk_ipa": "/ˈdʒɛdə/",
        "us_ipa": "/ˈdʒɛdə/",
    },
    {
        "word": "kola",
        "part_of_speech": "noun",
        "english": "A nut of this tree.",
        "us_ipa": "/ˈkoʊlə/",
    },
    {
        "word": "maidenhead",
        "part_of_speech": "noun",
        "english": "(literally, countable) The hymen.",
        "us_ipa": "/ˈmeɪdənhɛd/",
    },
    {
        "word": "maidenhead",
        "part_of_speech": "noun",
        "english": "(metonym, uncountable) Virginity.",
        "us_ipa": "/ˈmeɪdənhɛd/",
    },
    {
        "word": "megara",
        "part_of_speech": "proper noun",
        "english": "A city west of Athens in the Attica prefecture, Greece.",
        "uk_ipa": "/ˈmɛɡəɹə/",
    },
    {
        "word": "south",
        "part_of_speech": "proper noun",
        "english": (
            "(US) The south-eastern states of the United States, including "
            "many of the same states as formed the Confederacy."
        ),
        "uk_ipa": "/ˈsaʊ̯θ/",
    },
    {
        "word": "north pole",
        "part_of_speech": "proper noun",
        "english": "A city in Alaska.",
        "us_ipa": "/ˌnɔɹθ ˈpoʊl/",
    },
    {
        "word": "north pole",
        "part_of_speech": "proper noun",
        "english": "A hamlet in New York.",
        "us_ipa": "/ˌnɔɹθ ˈpoʊl/",
    },
    {
        "word": "styria",
        "part_of_speech": "proper noun",
        "english": "A southeastern state of Austria, with its capital in Graz.",
        "uk_ipa": "/ˈstɪɹiə/",
        "us_ipa": "/ˈstɪɹiə/",
    },
]


def normalized_word(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalized_pos(value: str) -> str:
    value = value.strip().lower()
    return POS_MAP.get(value, value)


def candidate_priority(
    tags: list[str],
    priorities: dict[str, int],
) -> int | None:
    normalized = {tag.strip().lower() for tag in tags}
    values = [
        priority
        for tag, priority in priorities.items()
        if tag in normalized
    ]
    return min(values) if values else None


def collect_candidates(
    source: Path,
    target_words: set[str],
) -> dict[tuple[str, str], dict[str, list[tuple[int, str]]]]:
    candidates: dict[
        tuple[str, str],
        dict[str, list[tuple[int, str]]],
    ] = defaultdict(lambda: {"uk": [], "us": []})

    with source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid Kaikki JSON on line {line_number}: {error}"
                ) from error
            if item.get("lang_code") != "en":
                continue
            word = normalized_word(str(item.get("word", "")))
            if word not in target_words:
                continue
            part = normalized_pos(str(item.get("pos", "")))
            for sound in item.get("sounds", []):
                ipa = str(sound.get("ipa", "")).strip()
                if not IPA_PATTERN.fullmatch(ipa) or "-" in ipa:
                    continue
                tags = [
                    str(tag)
                    for tag in sound.get("tags", [])
                ]
                uk_priority = candidate_priority(tags, UK_TAG_PRIORITY)
                if uk_priority is not None:
                    candidate = (uk_priority, ipa)
                    if candidate not in candidates[(word, part)]["uk"]:
                        candidates[(word, part)]["uk"].append(candidate)
                us_priority = candidate_priority(tags, US_TAG_PRIORITY)
                if us_priority is not None:
                    candidate = (us_priority, ipa)
                    if candidate not in candidates[(word, part)]["us"]:
                        candidates[(word, part)]["us"].append(candidate)
    return candidates


def select_candidate(values: list[tuple[int, str]]) -> tuple[str, list[str]]:
    if not values:
        return "", []
    best_priority = min(priority for priority, _ in values)
    best = list(dict.fromkeys(
        ipa
        for priority, ipa in values
        if priority == best_priority
    ))
    return (
        best[0] if len(best) == 1 else "",
        list(dict.fromkeys(ipa for _, ipa in values)),
    )


def best_candidates(values: list[tuple[int, str]]) -> list[str]:
    if not values:
        return []
    best_priority = min(priority for priority, _ in values)
    return list(dict.fromkeys(
        ipa
        for priority, ipa in values
        if priority == best_priority
    ))


def curated_replacement_words(corrections: Path) -> set[str]:
    words: set[str] = set()
    paths = [
        corrections,
        corrections.with_name("common_word_replacements.json"),
        corrections.with_name("chatgpt_reviewed_replacements.json"),
        corrections.with_name("codex_reviewed_replacements.json"),
    ]
    for path in paths:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        words.update(
            normalized_word(word)
            for word in data.get("word_replacements", {})
        )
    return words


def cmudict_words(path: Path | None) -> set[str]:
    if path is None:
        return set()
    words = set()
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip() or line.startswith(";;;"):
                continue
            word = re.sub(
                r"\(\d+\)$",
                "",
                line.split()[0].lower(),
            )
            words.add(word)
    return words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Kaikki postprocessed English JSONL.",
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/FullDictionaryAudit/missing_ipa.csv"
        ),
    )
    parser.add_argument(
        "--database",
        type=Path,
        help=(
            "Read all exact senses from this database instead of the "
            "missing-IPA CSV."
        ),
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help=(
            "Mark unique exact-POS regional IPA as authoritative so the "
            "cleaner replaces existing unlabelled-source values."
        ),
    )
    parser.add_argument(
        "--clear-unverified",
        action="store_true",
        help=(
            "Clear existing regional fields that have no explicit regional, "
            "curated, cross-verified, or CMUdict provenance."
        ),
    )
    parser.add_argument(
        "--cmudict",
        type=Path,
        help="CMUdict file whose headwords are trusted as US pronunciations.",
    )
    parser.add_argument(
        "--corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/curated_corrections.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/pronunciation_review_resolutions.json"
        ),
    )
    args = parser.parse_args()

    if args.database:
        connection = sqlite3.connect(
            f"file:{args.database}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, normalized_word, part_of_speech, en_definition,
                       uk_ipa, us_ipa
                FROM entries
                ORDER BY id
                """
            )
        ]
        connection.close()
    else:
        rows = list(csv.DictReader(
            args.review.open(encoding="utf-8-sig")
        ))
    existing_resolutions = []
    if args.output.exists():
        existing_resolutions = json.loads(
            args.output.read_text(encoding="utf-8")
        ).get("resolutions", [])
    targets = {
        normalized_word(row["normalized_word"])
        for row in rows
    }
    candidates = collect_candidates(args.source, targets)
    curated_words = curated_replacement_words(args.corrections)
    cmu_words = cmudict_words(args.cmudict)

    resolutions = []
    current_keys = set()
    for row in rows:
        word = normalized_word(row["normalized_word"])
        part = normalized_pos(row["part_of_speech"])
        current_keys.add((word, part, row["en_definition"]))
        regional = candidates.get((word, part))
        source_part = part
        if regional is None and not args.replace_existing:
            alternatives = [
                value
                for (candidate_word, _), value in candidates.items()
                if candidate_word == word
            ]
            unique_uk = [
                value
                for alternative in alternatives
                for value in alternative["uk"]
            ]
            unique_us = [
                value
                for alternative in alternatives
                for value in alternative["us"]
            ]
            unique_uk = list(dict.fromkeys(unique_uk))
            unique_us = list(dict.fromkeys(unique_us))
            regional = {"uk": unique_uk, "us": unique_us}
            source_part = "headword_fallback"

        regional = regional or {"uk": [], "us": []}
        uk_ipa, uk_candidates = select_candidate(regional["uk"])
        us_ipa, us_candidates = select_candidate(regional["us"])
        if args.replace_existing:
            current_uk = str(row.get("uk_ipa", "")).strip()
            current_us = str(row.get("us_ipa", "")).strip()
            best_uk = best_candidates(regional["uk"])
            best_us = best_candidates(regional["us"])
            # FreeDict historically supplied unlabelled pronunciations in
            # source order. If the current values exactly cross-match the
            # best explicit regional candidate sets, the two fields are
            # demonstrably reversed even when each region has variants.
            if (
                not uk_ipa
                and current_us
                and current_us in best_uk
            ):
                uk_ipa = current_us
            if (
                not us_ipa
                and current_uk
                and current_uk in best_us
            ):
                us_ipa = current_uk
        resolutions.append({
            "entry_id": int(row["id"]),
            "word": word,
            "part_of_speech": row["part_of_speech"],
            "english": row["en_definition"],
            "uk_ipa": uk_ipa,
            "us_ipa": us_ipa,
            "uk_candidates": uk_candidates,
            "us_candidates": us_candidates,
            "source_part_of_speech": source_part,
            "replace_uk": bool(
                args.replace_existing
                and uk_ipa
                and source_part != "headword_fallback"
            ),
            "replace_us": bool(
                args.replace_existing
                and us_ipa
                and source_part != "headword_fallback"
            ),
            "clear_uk": bool(
                args.clear_unverified
                and not uk_ipa
                and word not in curated_words
            ),
            "clear_us": bool(
                args.clear_unverified
                and not us_ipa
                and word not in curated_words
                and word not in cmu_words
            ),
            "status": (
                "matched_regional_ipa"
                if uk_ipa or us_ipa
                else "deferred_no_explicit_regional_ipa"
            ),
        })

    for item in existing_resolutions:
        key = (
            normalized_word(item["word"]),
            normalized_pos(item["part_of_speech"]),
            item["english"],
        )
        if key in current_keys:
            continue
        if item.get("uk_ipa") or item.get("us_ipa"):
            resolutions.append(item)

    resolution_indexes = {
        (
            normalized_word(item["word"]),
            normalized_pos(item["part_of_speech"]),
            item["english"],
        ): index
        for index, item in enumerate(resolutions)
    }
    for completed in COMPLETED_RESOLUTIONS:
        key = (
            completed["word"],
            completed["part_of_speech"],
            completed["english"],
        )
        completed_item = {
            "entry_id": 0,
            **completed,
            "uk_ipa": completed.get("uk_ipa", ""),
            "us_ipa": completed.get("us_ipa", ""),
            "uk_candidates": (
                [completed["uk_ipa"]]
                if completed.get("uk_ipa")
                else []
            ),
            "us_candidates": (
                [completed["us_ipa"]]
                if completed.get("us_ipa")
                else []
            ),
            "source_part_of_speech": completed["part_of_speech"],
            "status": "matched_cross_verified_regional_ipa",
            "replace_uk": bool(completed.get("uk_ipa")),
            "replace_us": bool(completed.get("us_ipa")),
        }
        if key in resolution_indexes:
            current = resolutions[resolution_indexes[key]]
            completed_item["entry_id"] = current.get("entry_id", 0)
            completed_item["uk_ipa"] = (
                completed.get("uk_ipa")
                or current.get("uk_ipa", "")
            )
            completed_item["us_ipa"] = (
                completed.get("us_ipa")
                or current.get("us_ipa", "")
            )
            completed_item["replace_uk"] = bool(
                completed_item["uk_ipa"]
                and (
                    completed.get("uk_ipa")
                    or current.get("replace_uk", False)
                )
            )
            completed_item["replace_us"] = bool(
                completed_item["us_ipa"]
                and (
                    completed.get("us_ipa")
                    or current.get("replace_us", False)
                )
            )
            completed_item["clear_uk"] = bool(
                current.get("clear_uk", False)
                and not completed_item["uk_ipa"]
            )
            completed_item["clear_us"] = bool(
                current.get("clear_us", False)
                and not completed_item["us_ipa"]
            )
            completed_item["uk_candidates"] = list(dict.fromkeys(
                current.get("uk_candidates", [])
                + completed_item["uk_candidates"]
            ))
            completed_item["us_candidates"] = list(dict.fromkeys(
                current.get("us_candidates", [])
                + completed_item["us_candidates"]
            ))
            resolutions[resolution_indexes[key]] = completed_item
        else:
            resolution_indexes[key] = len(resolutions)
            resolutions.append(completed_item)

    matched_uk = sum(bool(item.get("uk_ipa")) for item in resolutions)
    matched_us = sum(bool(item.get("us_ipa")) for item in resolutions)

    args.output.write_text(
        json.dumps(
            {
                "source": (
                    "Kaikki English dictionary extracted 2026-06-15 "
                    "from enwiktionary dump 2026-06-01"
                ),
                "source_url": (
                    "https://kaikki.org/dictionary/English/"
                    "kaikki.org-dictionary-English.jsonl"
                ),
                "license": "CC BY-SA 4.0 / GFDL",
                "cross_verification_source": (
                    "Montreal Forced Aligner English UK/US dictionaries "
                    "v3.1.0"
                ),
                "cross_verification_license": "CC BY 4.0",
                "resolution_count": len(resolutions),
                "authoritative_replacement_mode": args.replace_existing,
                "clear_unverified_mode": args.clear_unverified,
                "matched_uk_count": matched_uk,
                "matched_us_count": matched_us,
                "resolutions": resolutions,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"Created {args.output}: {len(resolutions)} rows, "
        f"UK matched {matched_uk}, US matched {matched_us}."
    )


if __name__ == "__main__":
    main()
