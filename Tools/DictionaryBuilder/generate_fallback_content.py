#!/usr/bin/env python3
"""Fill source gaps with deterministic, explicitly generated fallback data."""

from __future__ import annotations

import json
import re
import sqlite3


WORD_TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?|\d+")
DIGRAPHS = (
    ("tion", "ʃən"),
    ("sion", "ʒən"),
    ("ture", "tʃə"),
    ("ough", "ʌf"),
    ("eigh", "eɪ"),
    ("igh", "aɪ"),
    ("air", "ɛə"),
    ("ear", "ɪə"),
    ("ure", "jʊə"),
    ("ch", "tʃ"),
    ("sh", "ʃ"),
    ("th", "θ"),
    ("ph", "f"),
    ("ng", "ŋ"),
    ("qu", "kw"),
    ("ck", "k"),
    ("ee", "iː"),
    ("ea", "iː"),
    ("oo", "uː"),
    ("ai", "eɪ"),
    ("ay", "eɪ"),
    ("oa", "oʊ"),
    ("ow", "aʊ"),
    ("oi", "ɔɪ"),
    ("oy", "ɔɪ"),
    ("au", "ɔː"),
    ("aw", "ɔː"),
    ("er", "ɝ"),
    ("ir", "ɝ"),
    ("ur", "ɝ"),
)
LETTERS = {
    "a": "æ", "b": "b", "c": "k", "d": "d", "e": "ɛ", "f": "f",
    "g": "ɡ", "h": "h", "i": "ɪ", "j": "dʒ", "k": "k", "l": "l",
    "m": "m", "n": "n", "o": "ɑ", "p": "p", "q": "k", "r": "ɹ",
    "s": "s", "t": "t", "u": "ʌ", "v": "v", "w": "w", "x": "ks",
    "y": "j", "z": "z",
}


def ensure_provenance_table(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(entry_provenance)"
        )
    }
    if columns and "entry_id" not in columns:
        connection.execute("DROP TABLE entry_provenance")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS entry_provenance (
            entry_id INTEGER NOT NULL,
            content_kind TEXT NOT NULL,
            provenance TEXT NOT NULL,
            source TEXT NOT NULL,
            generator_version TEXT NOT NULL,
            PRIMARY KEY (entry_id, content_kind),
            FOREIGN KEY (entry_id) REFERENCES entries(id)
        )
    """)


def record_provenance(
    connection: sqlite3.Connection,
    entry_id: int,
    kind: str,
    provenance: str,
    source: str,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO entry_provenance (
            entry_id, content_kind, provenance, source, generator_version
        ) VALUES (?, ?, ?, ?, 'fallback-v1')
        """,
        (entry_id, kind, provenance, source),
    )


def generated_example(
    word: str,
    part: str,
    chinese: str,
) -> tuple[str, str]:
    labels = {
        "noun": "noun",
        "verb": "verb",
        "adjective": "adjective",
        "adverb": "adverb",
        "preposition": "preposition",
        "conjunction": "conjunction",
        "pronoun": "pronoun",
        "determiner": "determiner",
        "exclamation": "exclamation",
        "proper noun": "proper noun",
        "phrase": "expression",
        "proverb": "proverb",
    }
    label = labels.get(part.lower(), "word")
    english = (
        f'This example uses the {label} "{word}" in the sense shown here.'
    )
    chinese_example = (
        f'此例使用「{word}」表達「{chinese}」這個意思。'
    )
    return english, chinese_example


def fill_generated_examples(connection: sqlite3.Connection) -> int:
    ensure_provenance_table(connection)
    rows = connection.execute(
        """
        SELECT id, normalized_word, part_of_speech,
               zh_definition, en_definition
        FROM entries
        WHERE examples_json = '[]'
        ORDER BY id
        """
    ).fetchall()
    for entry_id, word, part, chinese, english in rows:
        english_example, chinese_example = generated_example(
            word,
            part,
            chinese,
        )
        connection.execute(
            "UPDATE entries SET examples_json = ? WHERE id = ?",
            (
                json.dumps([{
                    "english": english_example,
                    "chinese": chinese_example,
                }], ensure_ascii=False),
                entry_id,
            ),
        )
        record_provenance(
            connection,
            entry_id,
            "example",
            "generated_fallback",
            "definition-backed metalinguistic example",
        )
    return len(rows)


def heuristic_us_word(word: str) -> str:
    value = word.lower().replace("’", "'")
    value = re.sub(r"[^a-z']", "", value)
    if not value:
        return "ə"
    output = []
    index = 0
    while index < len(value):
        matched = False
        for spelling, ipa in DIGRAPHS:
            if value.startswith(spelling, index):
                output.append(ipa)
                index += len(spelling)
                matched = True
                break
        if matched:
            continue
        character = value[index]
        if character == "'":
            index += 1
            continue
        if (
            character == "e"
            and index == len(value) - 1
            and len(value) > 2
        ):
            index += 1
            continue
        output.append(LETTERS.get(character, "ə"))
        index += 1
    joined = "".join(output) or "ə"
    return "ˈ" + joined


def us_to_uk(value: str) -> str:
    result = value
    result = result.replace("oʊ", "əʊ")
    result = result.replace("ɝ", "ɜː")
    result = result.replace("ɚ", "ə")
    result = re.sub(r"(?<=[ɑɔɜəɛɪʊ])ɹ(?=$|[.\s])", "", result)
    result = result.replace("ɑɹ", "ɑː")
    result = result.replace("ɔɹ", "ɔː")
    return result


def generated_pronunciation(
    word: str,
    region: str,
) -> str:
    tokens = WORD_TOKEN_PATTERN.findall(word)
    if not tokens:
        tokens = [word]
    parts = []
    for token in tokens:
        if token.isdigit():
            parts.append(" ".join(heuristic_us_word(char) for char in token))
        else:
            parts.append(heuristic_us_word(token))
    value = " ".join(parts)
    if region == "uk":
        value = us_to_uk(value)
    return f"/{value}/"


def fill_generated_pronunciations(
    connection: sqlite3.Connection,
) -> tuple[int, int]:
    ensure_provenance_table(connection)
    rows = connection.execute(
        """
        SELECT id, normalized_word, part_of_speech,
               en_definition, uk_ipa, us_ipa
        FROM entries
        WHERE uk_ipa = '' OR us_ipa = ''
        ORDER BY id
        """
    ).fetchall()
    uk_added = 0
    us_added = 0
    for entry_id, word, part, english, uk_ipa, us_ipa in rows:
        next_us = us_ipa or generated_pronunciation(word, "us")
        next_uk = uk_ipa or generated_pronunciation(word, "uk")
        connection.execute(
            "UPDATE entries SET uk_ipa = ?, us_ipa = ? WHERE id = ?",
            (next_uk, next_us, entry_id),
        )
        if not uk_ipa:
            uk_added += 1
            record_provenance(
                connection,
                entry_id,
                "uk_ipa",
                "generated_fallback",
                "deterministic grapheme-to-phoneme approximation",
            )
        if not us_ipa:
            us_added += 1
            record_provenance(
                connection,
                entry_id,
                "us_ipa",
                "generated_fallback",
                "deterministic grapheme-to-phoneme approximation",
            )
    return uk_added, us_added


def record_reviewed_semantics(
    connection: sqlite3.Connection,
    corrections: list[dict],
) -> int:
    ensure_provenance_table(connection)
    recorded = 0
    for item in corrections:
        word = str(item["word"]).strip().lower()
        part = str(item["part_of_speech"]).strip()
        english = str(item["english"]).strip()
        row = connection.execute(
            """
            SELECT id FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND en_definition = ?
            """,
            (word, part, english),
        ).fetchone()
        if row is None:
            continue
        entry_id = row[0]
        record_provenance(
            connection,
            entry_id,
            "zh_definition",
            "ai_reviewed",
            "Codex exact-sense semantic review",
        )
        recorded += 1
        if isinstance(item.get("example"), dict):
            record_provenance(
                connection,
                entry_id,
                "example",
                "ai_reviewed",
                "Codex exact-sense bilingual example",
            )
    return recorded


def record_default_provenance(connection: sqlite3.Connection) -> int:
    ensure_provenance_table(connection)
    rows = connection.execute(
        """
        SELECT id, normalized_word, part_of_speech, en_definition,
               zh_definition, uk_ipa, us_ipa, examples_json
        FROM entries
        """
    ).fetchall()
    inserted = 0
    for (
        entry_id, word, part, english, chinese,
        uk_ipa, us_ipa, examples_json,
    ) in rows:
        values = [
            ("en_definition", "verified_source", "open dictionary source"),
        ]
        if chinese:
            values.append((
                "zh_definition",
                "source_or_curated",
                "FreeDict or exact-sense reviewed correction",
            ))
        if uk_ipa:
            values.append((
                "uk_ipa",
                "verified_source",
                "explicit regional source or reviewed correction",
            ))
        if us_ipa:
            values.append((
                "us_ipa",
                "verified_source",
                "CMUdict, explicit regional source, or reviewed correction",
            ))
        if examples_json != "[]":
            values.append((
                "example",
                "source_or_reviewed",
                "open bilingual source or exact-sense review",
            ))
        for kind, provenance, source in values:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO entry_provenance (
                    entry_id, content_kind, provenance,
                    source, generator_version
                ) VALUES (?, ?, ?, ?, 'fallback-v1')
                """,
                (entry_id, kind, provenance, source),
            )
            inserted += cursor.rowcount
    return inserted
