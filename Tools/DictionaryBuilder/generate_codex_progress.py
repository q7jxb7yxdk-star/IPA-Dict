#!/usr/bin/env python3
"""Generate a transparent progress report for the current Codex review scope."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path


OFFENSIVE = {"fuck", "pussy", "crap", "queer", "shitty"}
TECHNICAL = {
    "ammonic", "dyad", "enzyme", "genus", "kn95", "phenol", "radix",
    "sepulchral", "sol",
}


def load_target_words(batch_directory: Path) -> list[str]:
    result: list[str] = []
    for batch_number in (2, 3):
        path = batch_directory / f"{batch_number:03d}-review.jsonl"
        result.extend(
            json.loads(line)["word"]
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return list(dict.fromkeys(result))


def replacement_words(directory: Path, filename: str) -> set[str]:
    path = directory / filename
    if not path.exists():
        return set()
    return set(
        json.loads(path.read_text(encoding="utf-8"))
        .get("word_replacements", {})
    )


def category(
    word: str,
    parts: set[str],
) -> str:
    if word in OFFENSIVE:
        return "offensive_or_sensitive"
    if word.endswith("-"):
        return "prefix_or_bound_form"
    if "proper noun" in parts:
        return "proper_name"
    if word in TECHNICAL:
        return "specialist_term"
    if " " in word:
        return "phrase_or_multiword_expression"
    return "general_manual_review"


def main() -> None:
    tools = Path("Tools/DictionaryBuilder")
    target = load_target_words(tools / "ChatGPTReviewPackage/batches")
    layers = {
        "manual": replacement_words(tools, "curated_corrections.json"),
        "generated": replacement_words(tools, "common_word_replacements.json"),
        "chatgpt": replacement_words(
            tools, "chatgpt_reviewed_replacements.json"
        ),
        "codex": replacement_words(
            tools, "codex_reviewed_replacements.json"
        ),
    }
    connection = sqlite3.connect("IPA Dict/Data/dictionary.sqlite")
    deferred: list[tuple[str, str]] = []
    status: dict[str, str] = {}
    for word in target:
        matched = next(
            (name for name, words in layers.items() if word in words),
            None,
        )
        if matched:
            status[word] = f"replaced_{matched}"
            continue
        parts = {
            row[0].lower()
            for row in connection.execute(
                "SELECT DISTINCT part_of_speech FROM entries "
                "WHERE normalized_word = ?",
                (word,),
            )
        }
        reason = category(word, parts)
        status[word] = reason
        deferred.append((word, reason))
    connection.close()

    counts = Counter(status.values())
    lines = [
        "# Codex Review Progress",
        "",
        "Scope: original review batches 002 and 003.",
        "",
        f"- Unique words in scope: {len(target)}",
        f"- Newly replaced by Codex: {counts['replaced_codex']}",
        f"- Already replaced by earlier layers: "
        f"{sum(value for key, value in counts.items() if key.startswith('replaced_') and key != 'replaced_codex')}",
        f"- Still deferred: {len(deferred)}",
        "",
        "## Deferred categories",
        "",
    ]
    for name, count in sorted(
        ((key, value) for key, value in counts.items()
         if not key.startswith("replaced_")),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- `{name}`: {count}")
    lines.extend([
        "",
        "## Deferred words",
        "",
        "| Word | Reason |",
        "|---|---|",
    ])
    lines.extend(f"| `{word}` | `{reason}` |" for word, reason in deferred)
    output = tools / "CodexReviewProgress.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Created {output}: {counts['replaced_codex']} newly replaced, "
        f"{len(deferred)} deferred."
    )


if __name__ == "__main__":
    main()
