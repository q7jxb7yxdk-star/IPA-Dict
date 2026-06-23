#!/usr/bin/env python3
"""Generate a conservative Chinese/English semantic mismatch review queue."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import zipfile
from collections import defaultdict
from pathlib import Path

from clean_dictionary import DEFINITION_SEPARATOR_PATTERN
from generate_common_curation import traditional


ENGLISH_WORD_PATTERN = re.compile(r"[a-z]+(?:-[a-z]+)?")
CEDICT_PATTERN = re.compile(
    r"^(?P<traditional>\S+) (?P<simplified>\S+) "
    r"\[[^\]]+\] /(?P<definitions>.*)/$"
)
STOP_WORDS = {
    "about", "after", "also", "among", "being", "chiefly", "especially",
    "from", "have", "into", "more", "most", "often", "other", "relating",
    "someone", "something", "such", "that", "their", "them", "then",
    "there", "these", "they", "this", "those", "through", "used", "using",
    "usually", "very", "when", "where", "which", "while", "with", "without",
}
CONTRADICTIONS = (
    ({"mild", "gentle", "moderate"}, {"harsh", "severe", "sharp"}),
)


def english_tokens(value: str) -> set[str]:
    return {
        token
        for token in ENGLISH_WORD_PATTERN.findall(value.lower())
        if len(token) >= 4 and token not in STOP_WORDS
    }


def load_cedict(path: Path) -> dict[str, set[str]]:
    definitions: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(path) as archive:
        source_name = next(
            name for name in archive.namelist() if name.endswith(".u8")
        )
        with archive.open(source_name) as raw:
            for encoded in raw:
                line = encoded.decode("utf-8").strip()
                if not line or line.startswith("#"):
                    continue
                match = CEDICT_PATTERN.match(line)
                if not match:
                    continue
                glosses = match.group("definitions").split("/")
                tokens = set().union(*(english_tokens(gloss) for gloss in glosses))
                for value in {
                    match.group("traditional"),
                    match.group("simplified"),
                }:
                    definitions[traditional(value)].update(tokens)
    return definitions


def chinese_terms(value: str) -> set[str]:
    return {
        traditional(term.strip())
        for term in DEFINITION_SEPARATOR_PATTERN.split(value)
        if len(term.strip()) >= 2
        and re.search(r"[\u3400-\u9fff]", term)
    }


def contradiction_reasons(
    source_tokens: set[str],
    definition_tokens: set[str],
) -> list[str]:
    reasons = []
    for left, right in CONTRADICTIONS:
        if source_tokens & left and definition_tokens & right:
            reasons.append(
                "cedict_" + "_".join(sorted(source_tokens & left))
                + "_vs_english_" + "_".join(sorted(definition_tokens & right))
            )
        if source_tokens & right and definition_tokens & left:
            reasons.append(
                "cedict_" + "_".join(sorted(source_tokens & right))
                + "_vs_english_" + "_".join(sorted(definition_tokens & left))
            )
    return reasons


def reviewed_keys(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (
            str(item["word"]).strip().lower(),
            str(item["part_of_speech"]).strip().lower(),
            str(item["english"]).strip(),
        )
        for item in data.get("corrections", [])
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument("--cedict", type=Path, required=True)
    parser.add_argument(
        "--corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/ai_semantic_corrections.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/FullDictionaryAudit/"
            "semantic_mismatch_review.csv"
        ),
    )
    args = parser.parse_args()

    cedict = load_cedict(args.cedict)
    completed = reviewed_keys(args.corrections)
    connection = sqlite3.connect(
        f"file:{args.database}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    candidates = []
    for row in connection.execute(
        """
        SELECT id, word, normalized_word, part_of_speech, countability,
               zh_definition, en_definition, examples_json
        FROM entries
        ORDER BY normalized_word, id
        """
    ):
        key = (
            row["normalized_word"],
            row["part_of_speech"].lower(),
            row["en_definition"],
        )
        if key in completed or row["part_of_speech"].lower() == "proper noun":
            continue
        terms = chinese_terms(row["zh_definition"])
        term_tokens = {
            term: cedict.get(term, set())
            for term in terms
            if cedict.get(term)
        }
        if not term_tokens:
            continue
        source_tokens = set().union(*term_tokens.values())
        definition_tokens = english_tokens(
            row["normalized_word"] + " " + row["en_definition"]
        )
        overlap = source_tokens & definition_tokens
        contradictions = contradiction_reasons(
            source_tokens,
            definition_tokens,
        )
        if overlap and not contradictions:
            continue
        # A lack of lexical overlap is only a review signal, not proof.
        # Require a useful CEDICT gloss and a sufficiently descriptive
        # English definition to avoid flooding the queue with short synonyms.
        if not contradictions and (
            len(source_tokens) < 1 or len(definition_tokens) < 3
        ):
            continue
        candidates.append({
            **dict(row),
            "chinese_terms": " | ".join(sorted(term_tokens)),
            "cedict_gloss_tokens": " | ".join(sorted(source_tokens)),
            "english_content_tokens": " | ".join(sorted(definition_tokens)),
            "shared_tokens": " | ".join(sorted(overlap)),
            "semantic_reasons": (
                " | ".join(contradictions)
                if contradictions
                else "no_lexical_support_in_cedict_gloss"
            ),
            "priority": "high" if contradictions else "review",
        })
    connection.close()

    candidates.sort(key=lambda item: (
        item["priority"] != "high",
        item["normalized_word"],
        item["id"],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id", "word", "normalized_word", "part_of_speech", "countability",
        "zh_definition", "en_definition", "examples_json", "chinese_terms",
        "cedict_gloss_tokens", "english_content_tokens", "shared_tokens",
        "semantic_reasons", "priority",
    ]
    with args.output.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)
    high = sum(item["priority"] == "high" for item in candidates)
    print(json.dumps({
        "candidate_count": len(candidates),
        "high_priority_count": high,
        "reviewed_correction_count": len(completed),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
