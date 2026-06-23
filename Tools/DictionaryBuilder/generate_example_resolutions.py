#!/usr/bin/env python3
"""Generate exact bilingual example resolutions from Tatoeba."""

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

from generate_common_curation import AUTO_EXCLUDED, traditional


WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
IRREGULAR_FORMS = {
    "am": "be", "are": "be", "been": "be", "being": "be", "is": "be",
    "was": "be", "were": "be", "did": "do", "does": "do", "done": "do",
    "found": "find", "gave": "give", "given": "give", "got": "get",
    "gone": "go", "had": "have", "has": "have", "made": "make",
    "ran": "run", "said": "say", "saw": "see", "seen": "see",
    "taught": "teach", "took": "take", "taken": "take", "went": "go",
    "wrote": "write", "written": "write",
}


def normalized_sentence(value: str) -> str:
    return " ".join(
        WORD_PATTERN.findall(value.lower().replace("’", "'"))
    )


def translation_terms(value: str) -> list[str]:
    return [
        term.strip()
        for term in re.split(r"[；;，,、／/（）()\s]+", value)
        if term.strip()
    ]


def inflected_forms(word: str) -> set[str]:
    forms = {word}
    if not re.fullmatch(r"[a-z][a-z'-]*", word):
        return forms
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        forms.update({word[:-1] + "ies", word[:-1] + "ied"})
    else:
        forms.add(word + "s")
        forms.add(word + "ed")
    if word.endswith(("s", "x", "z", "ch", "sh")):
        forms.add(word + "es")
    if word.endswith("e"):
        forms.add(word + "d")
        forms.add(word[:-1] + "ing")
    else:
        forms.add(word + "ing")
    if (
        len(word) >= 3
        and word[-1] not in "aeiouwxy"
        and word[-2] in "aeiou"
        and word[-3] not in "aeiou"
    ):
        forms.update({word + word[-1] + "ed", word + word[-1] + "ing"})
    forms.update(
        form
        for form, lemma in IRREGULAR_FORMS.items()
        if lemma == word
    )
    return forms


def normalized_chinese(value: str) -> str:
    return re.sub(r"\s+", "", traditional(value))


def structural_resolution_keys(output: Path) -> set[tuple[str, str, str]]:
    keys = set()
    for name in (
        "grammar_manual_review.json",
        "noun_countability_review.json",
    ):
        path = output.with_name(name)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        keys.update(
            (
                str(item.get("word", "")).strip().lower(),
                str(item.get("part_of_speech", "")).lower(),
                str(item.get("english", "")).strip(),
            )
            for item in data.get("reviews", [])
            if isinstance(item.get("structural_resolution"), dict)
        )
    return keys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--review",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/FullDictionaryAudit/"
            "missing_examples.csv"
        ),
    )
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--chinese", type=Path, required=True)
    parser.add_argument("--links", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/example_review_resolutions.json"
        ),
    )
    args = parser.parse_args()

    existing_resolutions = []
    if args.output.exists():
        existing_resolutions = json.loads(
            args.output.read_text(encoding="utf-8")
        ).get("resolutions", [])
    rows = list(csv.DictReader(
        args.review.open(encoding="utf-8-sig")
    ))
    term_senses: dict[tuple[str, str], set[tuple[str, str, str]]] = (
        defaultdict(set)
    )
    for row in rows:
        for term in translation_terms(row["zh_definition"]):
            normalized_term = normalized_chinese(term)
            if len(normalized_term) >= 2:
                term_senses[
                    (row["normalized_word"], normalized_term)
                ].add((
                    row["part_of_speech"].lower(),
                    row["zh_definition"].strip(),
                    row["en_definition"].strip(),
                ))

    target_terms: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        word = row["normalized_word"]
        if word in AUTO_EXCLUDED:
            continue
        target_terms[word].update(
            normalized_chinese(term)
            for term in translation_terms(row["zh_definition"])
            if (
                len(normalized_chinese(term)) >= 2
                and len(term_senses[
                    (word, normalized_chinese(term))
                ]) == 1
            )
        )

    form_targets: dict[str, set[str]] = defaultdict(set)
    phrase_targets: dict[str, set[str]] = defaultdict(set)
    for word in target_terms:
        if " " in word:
            phrase_targets[word.split()[0]].add(word)
        else:
            for form in inflected_forms(word):
                form_targets[form].add(word)

    candidates: dict[int, tuple[str, dict[str, int]]] = {}
    with bz2.open(args.english, "rt", encoding="utf-8") as stream:
        for record in csv.reader(stream, delimiter="\t"):
            if len(record) < 3:
                continue
            english = record[2].strip()
            tokens = normalized_sentence(english).split()
            if not 3 <= len(tokens) <= 20:
                continue
            matches: dict[str, int] = {}
            for token in set(tokens):
                for word in form_targets.get(token, set()):
                    matches[word] = max(matches.get(word, 0), 2 if token == word else 1)
            normalized = " ".join(tokens)
            padded = f" {normalized} "
            for token in set(tokens):
                for phrase in phrase_targets.get(token, set()):
                    if f" {phrase} " in padded:
                        matches[phrase] = 3
            if not matches:
                continue
            candidates[int(record[0])] = (english, matches)

    chinese_ids: set[int] = set()
    links: list[tuple[int, int]] = []
    with tarfile.open(args.links, "r:bz2") as archive:
        source = archive.extractfile("links.csv")
        if source is None:
            raise RuntimeError("Tatoeba links.csv is missing")
        for raw in source:
            first, second = map(int, raw.split(b"\t"))
            if first in candidates:
                links.append((first, second))
                chinese_ids.add(second)
            elif second in candidates:
                links.append((second, first))
                chinese_ids.add(first)

    chinese_sentences: dict[int, str] = {}
    with bz2.open(args.chinese, "rt", encoding="utf-8") as stream:
        for record in csv.reader(stream, delimiter="\t"):
            if len(record) >= 3 and int(record[0]) in chinese_ids:
                chinese_sentences[int(record[0])] = record[2].strip()

    best: dict[tuple[str, str], tuple[tuple, dict]] = {}
    for english_id, chinese_id in links:
        chinese = chinese_sentences.get(chinese_id)
        if not chinese:
            continue
        english, words = candidates[english_id]
        normalized_translation = normalized_chinese(chinese)
        sentence_length = len(normalized_sentence(english).split())
        for word, match_quality in words.items():
            for term in target_terms[word]:
                if term and term in normalized_translation:
                    score = (
                        match_quality,
                        len(term),
                        traditional(chinese) == chinese,
                        -sentence_length,
                        -english_id,
                    )
                    example = {
                        "english": english,
                        "chinese": chinese,
                        "source": "Tatoeba",
                        "english_sentence_id": english_id,
                        "chinese_sentence_id": chinese_id,
                    }
                    key = (word, term)
                    if key not in best or score > best[key][0]:
                        best[key] = (score, example)

    resolutions = []
    current_keys = set()
    connection = sqlite3.connect(
        f"file:{args.database}?mode=ro",
        uri=True,
    )
    trusted_examples = {
        (
            word,
            part.lower(),
            chinese,
            english,
            examples_json,
        )
        for word, part, chinese, english, examples_json
        in connection.execute(
            """
            SELECT normalized_word, part_of_speech, zh_definition,
                   en_definition, examples_json
            FROM entries
            WHERE examples_json != '[]'
            """
        )
    }
    connection.close()
    existing_by_key = {
        (
            str(item.get("word", "")).strip().lower(),
            str(item.get("part_of_speech", "")).lower(),
            str(item.get("chinese", "")).strip(),
            str(item.get("english", "")).strip(),
        ): item
        for item in existing_resolutions
        if isinstance(item.get("example"), dict)
        and (
            str(item.get("word", "")).strip().lower(),
            str(item.get("part_of_speech", "")).lower(),
            str(item.get("chinese", "")).strip(),
            str(item.get("english", "")).strip(),
            json.dumps(
                [{
                    "english": item["example"]["english"],
                    "chinese": item["example"]["chinese"],
                }],
                ensure_ascii=False,
            ),
        ) in trusted_examples
    }
    for row in rows:
        resolution_key = (
            row["normalized_word"].strip().lower(),
            row["part_of_speech"].lower(),
            row["zh_definition"].strip(),
            row["en_definition"].strip(),
        )
        current_keys.add(resolution_key)
        examples = [
            best[(row["normalized_word"], normalized_chinese(term))][1]
            for term in translation_terms(row["zh_definition"])
            if (
                row["normalized_word"],
                normalized_chinese(term),
            ) in best
        ]
        example = examples[0] if examples else None
        if example is None and resolution_key in existing_by_key:
            example = existing_by_key[resolution_key]["example"]
        resolutions.append({
            "entry_id": int(row["id"]),
            "word": row["normalized_word"],
            "part_of_speech": row["part_of_speech"],
            "chinese": row["zh_definition"],
            "english": row["en_definition"],
            "example": example,
            "status": (
                "matched_tatoeba_bilingual_example"
                if example
                else "deferred_no_safe_bilingual_example"
            ),
        })
    resolutions.extend(
        item
        for item in existing_resolutions
        if isinstance(item.get("example"), dict)
        and (
            str(item.get("word", "")).strip().lower(),
            str(item.get("part_of_speech", "")).lower(),
            str(item.get("chinese", "")).strip(),
            str(item.get("english", "")).strip(),
        ) not in current_keys
    )
    structural_keys = structural_resolution_keys(args.output)
    resolutions = [
        item
        for item in resolutions
        if (
            str(item.get("word", "")).strip().lower(),
            str(item.get("part_of_speech", "")).lower(),
            str(item.get("english", "")).strip(),
        ) not in structural_keys
    ]

    matched = sum(item["example"] is not None for item in resolutions)
    args.output.write_text(
        json.dumps(
            {
                "source": "Tatoeba English and Mandarin exports",
                "license": "CC BY 2.0 FR",
                "resolution_count": len(resolutions),
                "matched_count": matched,
                "resolutions": resolutions,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"Created {args.output}: {len(resolutions)} rows, "
        f"{matched} safe bilingual examples."
    )


if __name__ == "__main__":
    main()
