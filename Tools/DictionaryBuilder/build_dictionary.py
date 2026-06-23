#!/usr/bin/env python3
"""Build the bundled IPA Dictionary SQLite database from open data."""

from __future__ import annotations

import argparse
import bz2
import csv
import json
import re
import sqlite3
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

from clean_dictionary import (
    apply_curated_data,
    apply_alignment_resolutions,
    apply_superseded_alignment_resolutions,
    apply_one_character_resolutions,
    apply_grammar_structural_resolutions,
    apply_pronunciation_resolutions,
    apply_grammar_resolutions,
    apply_example_resolutions,
    apply_semantic_corrections,
    remap_example_resolutions,
    exclude_replaced_words,
    exclude_semantically_corrected_items,
    exclude_structurally_resolved_items,
    example_matches_chinese_definition,
    inferred_grammar_label,
    load_curated_data,
    load_alignment_resolutions,
    load_one_character_resolutions,
    load_grammar_structural_resolutions,
    load_pronunciation_resolutions,
    load_grammar_resolutions,
    load_example_resolutions,
    load_semantic_corrections,
    normalized_part_of_speech,
    safely_clean_ipa,
)
from generate_fallback_content import (
    ensure_provenance_table,
    fill_generated_examples,
    fill_generated_pronunciations,
    record_default_provenance,
    record_reviewed_semantics,
)


FREEDICT_URL = (
    "https://download.freedict.org/dictionaries/eng-zho/2025.11.23/"
    "freedict-eng-zho-2025.11.23.src.tar.xz"
)
OEWN_URL = (
    "https://github.com/globalwordnet/english-wordnet/releases/download/"
    "2025-edition/english-wordnet-2025-json.zip"
)
CMUDICT_URL = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"
TATOEBA_ENG_URL = (
    "https://downloads.tatoeba.org/exports/per_language/eng/"
    "eng_sentences.tsv.bz2"
)
TATOEBA_CMN_URL = (
    "https://downloads.tatoeba.org/exports/per_language/cmn/"
    "cmn_sentences.tsv.bz2"
)
TATOEBA_LINKS_URL = "https://downloads.tatoeba.org/exports/links.tar.bz2"

TEI = {"tei": "http://www.tei-c.org/ns/1.0"}
POS_MAP = {
    "n": "noun",
    "pn": "proper noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "int": "exclamation",
    "interjection": "exclamation",
}
OEWN_POS = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}
ARPABET_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɝ",
    "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "i",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "oʊ", "OY": "ɔɪ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "u", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}


def download(url: str, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {destination.name}…")
    subprocess.run(
        ["curl", "--fail", "--location", url, "--output", str(destination)],
        check=True,
    )


def normalized_word(word: str) -> str:
    return " ".join(word.strip().lower().split())


def normalized_sentence(sentence: str) -> str:
    value = (
        sentence.strip().lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    value = re.sub(r"[^\w\s']+", "", value, flags=re.UNICODE)
    return " ".join(value.split())


def example_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text")
        return text if isinstance(text, str) else ""
    return ""


def traditional_score(text: str) -> int:
    markers = set("體學書詞語門國後發臺萬與為這個醫蘋關譯號裡麼")
    return sum(character in markers for character in text)


def extract_countability(definition: str) -> tuple[str, str]:
    match = re.match(
        r"^\((?P<label>(?:countable|uncountable)"
        r"(?:,\s*(?:countable|uncountable))?)\)\s*",
        definition,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", definition
    labels = match.group("label").lower()
    if "countable" in labels and "uncountable" in labels:
        countability = "C or U"
    elif labels == "countable":
        countability = "C"
    else:
        countability = "U"
    return countability, definition[match.end():]


def prefer_traditional(quotes: list[str]) -> str:
    values = [value.strip() for value in quotes if value.strip()]
    if not values:
        return ""
    traditional_markers = set("蘋醫學書詞語門國體後發臺萬與為這個")
    for value in reversed(values):
        if traditional_markers.intersection(value):
            return value
    return values[-1]


def parse_freedict(archive: Path) -> dict[str, list[dict]]:
    with tarfile.open(archive) as bundle:
        member = bundle.getmember("eng-zho/eng-zho.tei")
        source = bundle.extractfile(member)
        if source is None:
            raise RuntimeError("FreeDict TEI source is missing")
        root = ET.parse(source).getroot()

    results: dict[str, list[dict]] = defaultdict(list)
    for entry in root.findall(".//tei:entry", TEI):
        orth = entry.findtext("./tei:form/tei:orth", default="", namespaces=TEI)
        word = normalized_word(orth)
        if not word:
            continue
        pronunciations = [
            text.strip()
            for text in (
                node.text or "" for node in entry.findall("./tei:form/tei:pron", TEI)
            )
            if text.strip()
        ]
        raw_pos = entry.findtext("./tei:gramGrp/tei:pos", default="", namespaces=TEI)
        normalized_pos = raw_pos.strip()
        part_of_speech = POS_MAP.get(
            normalized_pos.lower(),
            normalized_pos or "other",
        )
        part_of_speech = normalized_part_of_speech(part_of_speech)
        if part_of_speech == "other" and " " in word:
            part_of_speech = "phrase"

        for sense in entry.findall("./tei:sense", TEI):
            translations = [
                node.text or ""
                for node in sense.findall("./tei:cit[@type='trans']/tei:quote", TEI)
            ]
            chinese = prefer_traditional(translations)
            definitions = [
                (node.text or "").strip()
                for node in sense.findall(".//tei:def", TEI)
                if (node.text or "").strip()
            ]
            if chinese or definitions:
                results[word].append({
                    "part_of_speech": part_of_speech,
                    "pronunciations": pronunciations,
                    "chinese": chinese,
                    "definitions": definitions,
                })
    return results


def parse_cmudict(path: Path) -> dict[str, str]:
    pronunciations: dict[str, str] = {}
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip() or line.startswith(";;;"):
                continue
            word, *phones = line.strip().split()
            word = re.sub(r"\(\d+\)$", "", word).lower()
            if word in pronunciations:
                continue
            ipa_parts: list[str] = []
            primary_stress_index: int | None = None
            last_vowel_end = 0
            for phone in phones:
                stress = phone[-1] if phone[-1:].isdigit() else ""
                base = phone[:-1] if stress else phone
                symbol = ARPABET_IPA.get(base, "")
                if not symbol:
                    continue
                if stress == "1" and primary_stress_index is None:
                    primary_stress_index = last_vowel_end
                ipa_parts.append(symbol)
                if base in {
                    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
                    "IH", "IY", "OW", "OY", "UH", "UW",
                }:
                    last_vowel_end = len(ipa_parts)
            if ipa_parts:
                if primary_stress_index is not None:
                    ipa_parts.insert(primary_stress_index, "ˈ")
                pronunciations[word] = "/" + "".join(ipa_parts) + "/"
    return pronunciations


def load_oewn(archive: Path) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    entries_by_word: dict[str, list[dict]] = defaultdict(list)
    synset_lemmas: dict[str, list[str]] = defaultdict(list)
    synset_data: dict[str, dict] = {}

    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if name.startswith("entries-") and name.endswith(".json"):
                data = json.loads(bundle.read(name))
                for lemma, pos_entries in data.items():
                    normalized = normalized_word(lemma.replace("_", " "))
                    for pos_code, details in pos_entries.items():
                        for sense in details.get("sense", []):
                            synset = sense.get("synset")
                            if not synset:
                                continue
                            entries_by_word[normalized].append({
                                "pos": OEWN_POS.get(pos_code, pos_code),
                                "synset": synset,
                            })
                            synset_lemmas[synset].append(normalized)
            elif (
                name.endswith(".json")
                and not name.startswith("entries-")
                and name != "frames.json"
            ):
                synset_data.update(json.loads(bundle.read(name)))
    return (
        {
            word: [
                {**item, **synset_data.get(item["synset"], {})}
                for item in senses
            ]
            for word, senses in entries_by_word.items()
        },
        synset_lemmas,
    )


def load_tatoeba_examples(
    english_path: Path,
    chinese_path: Path,
    links_path: Path,
    headwords: set[str],
    oewn_examples: set[str],
) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    single_words = {
        word for word in headwords
        if " " not in word and re.fullmatch(r"[a-z][a-z'-]*", word)
    }
    exact_ids: dict[int, tuple[str, str]] = {}
    candidates_by_id: dict[int, list[str]] = {}
    candidate_counts: dict[str, int] = defaultdict(int)

    with bz2.open(english_path, "rt", encoding="utf-8") as source:
        for row in csv.reader(source, delimiter="\t"):
            if len(row) < 3:
                continue
            sentence_id = int(row[0])
            sentence = row[2].strip()
            normalized = normalized_sentence(sentence)
            if normalized in oewn_examples:
                exact_ids[sentence_id] = (normalized, sentence)

            tokens = normalized.split()
            if not 3 <= len(tokens) <= 14:
                continue
            for word in set(tokens).intersection(single_words):
                if candidate_counts[word] >= 5:
                    continue
                candidates_by_id.setdefault(sentence_id, []).append(word)
                candidate_counts[word] += 1

    chinese_sentences: dict[int, str] = {}
    with bz2.open(chinese_path, "rt", encoding="utf-8") as source:
        for row in csv.reader(source, delimiter="\t"):
            if len(row) >= 3:
                chinese_sentences[int(row[0])] = row[2].strip()

    best_exact: dict[str, tuple[str, str]] = {}
    best_fallback: dict[str, tuple[str, str]] = {}
    with tarfile.open(links_path, "r:bz2") as archive:
        links = archive.extractfile("links.csv")
        if links is None:
            raise RuntimeError("Tatoeba links.csv is missing")
        for raw_line in links:
            first, second = map(int, raw_line.split(b"\t"))
            if first in chinese_sentences:
                chinese_id, english_id = first, second
            elif second in chinese_sentences:
                chinese_id, english_id = second, first
            else:
                continue
            chinese = chinese_sentences[chinese_id]

            if english_id in exact_ids:
                normalized, english = exact_ids[english_id]
                current = best_exact.get(normalized)
                if current is None or traditional_score(chinese) > traditional_score(current[1]):
                    best_exact[normalized] = (english, chinese)

            for word in candidates_by_id.get(english_id, []):
                current = best_fallback.get(word)
                english = exact_ids.get(english_id, ("", ""))[1]
                if not english:
                    # Candidate English text is recovered below only when selected.
                    continue
                if current is None or traditional_score(chinese) > traditional_score(current[1]):
                    best_fallback[word] = (english, chinese)

    # Candidate sentence text is needed even when it was not an exact WordNet example.
    selected_candidate_ids = {
        sentence_id
        for sentence_id in candidates_by_id
        if any(word not in best_fallback for word in candidates_by_id[sentence_id])
    }
    candidate_texts: dict[int, str] = {}
    with bz2.open(english_path, "rt", encoding="utf-8") as source:
        for row in csv.reader(source, delimiter="\t"):
            if len(row) >= 3 and int(row[0]) in selected_candidate_ids:
                candidate_texts[int(row[0])] = row[2].strip()

    with tarfile.open(links_path, "r:bz2") as archive:
        links = archive.extractfile("links.csv")
        if links is None:
            raise RuntimeError("Tatoeba links.csv is missing")
        for raw_line in links:
            first, second = map(int, raw_line.split(b"\t"))
            if first in chinese_sentences:
                chinese_id, english_id = first, second
            elif second in chinese_sentences:
                chinese_id, english_id = second, first
            else:
                continue
            english = candidate_texts.get(english_id)
            if not english:
                continue
            chinese = chinese_sentences[chinese_id]
            for word in candidates_by_id.get(english_id, []):
                current = best_fallback.get(word)
                if current is None or traditional_score(chinese) > traditional_score(current[1]):
                    best_fallback[word] = (english, chinese)

    return best_exact, best_fallback


def create_database(
    destination: Path,
    freedict: dict[str, list[dict]],
    oewn: dict[str, list[dict]],
    synset_lemmas: dict[str, list[str]],
    cmu: dict[str, str],
    exact_examples: dict[str, tuple[str, str]],
    fallback_examples: dict[str, tuple[str, str]],
    corrections_path: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    connection = sqlite3.connect(destination)
    connection.executescript("""
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;
        PRAGMA temp_store = MEMORY;
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            normalized_word TEXT NOT NULL,
            uk_ipa TEXT NOT NULL DEFAULT '',
            us_ipa TEXT NOT NULL DEFAULT '',
            part_of_speech TEXT NOT NULL DEFAULT '',
            countability TEXT NOT NULL DEFAULT '',
            zh_definition TEXT NOT NULL DEFAULT '',
            en_definition TEXT NOT NULL DEFAULT '',
            examples_json TEXT NOT NULL DEFAULT '[]',
            synonyms_json TEXT NOT NULL DEFAULT '[]',
            antonyms_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX entries_word_index ON entries(normalized_word);
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    insert = """
        INSERT INTO entries (
            word, normalized_word, uk_ipa, us_ipa, part_of_speech,
            countability, zh_definition, en_definition, examples_json,
            synonyms_json, antonyms_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    row_count = 0
    inserted_rows: set[tuple[str, str, str, str]] = set()
    example_used_words: set[str] = set()
    for word, free_senses in sorted(freedict.items()):
        oewn_senses = oewn.get(word, [])
        for free_sense in free_senses:
            if not free_sense["chinese"]:
                continue
            pos = free_sense["part_of_speech"]
            matching_oewn = [
                sense for sense in oewn_senses if sense.get("pos") == pos
            ]
            synonyms = sorted({
                lemma
                for sense in matching_oewn
                for lemma in synset_lemmas.get(sense.get("synset", ""), [])
                if lemma != word
            })[:20]

            for definition in free_sense["definitions"] or [""]:
                countability, clean_definition = extract_countability(definition)
                if not countability:
                    countability = inferred_grammar_label(pos, clean_definition)
                if not clean_definition:
                    continue
                row_key = (
                    word,
                    pos,
                    free_sense["chinese"],
                    clean_definition,
                )
                if row_key in inserted_rows:
                    continue
                inserted_rows.add(row_key)

                # FreeDict pronunciation elements are not region-labelled.
                # Their order must not be interpreted as UK then US.
                # CMUdict is explicitly General American, while reviewed
                # regional UK/US values are applied later from the
                # pronunciation resolution ledger.
                uk_ipa = ""
                us_ipa = safely_clean_ipa(cmu.get(word, ""))
                # Headword-level fallback examples are not sense-safe.
                # Exact reviewed example ledgers are applied after all
                # source and structural corrections have been built.
                examples_json = "[]"

                connection.execute(insert, (
                    word,
                    word,
                    uk_ipa,
                    us_ipa,
                    pos,
                    countability,
                    free_sense["chinese"],
                    clean_definition,
                    examples_json,
                    json.dumps(synonyms, ensure_ascii=False),
                    "[]",
                ))
                row_count += 1

    corrected, replacements = apply_curated_data(
        connection,
        curated_data := load_curated_data(corrections_path),
    )
    superseded_resolution_words = {
        word.strip().lower()
        for word in curated_data.get(
            "superseded_resolution_words",
            [],
        )
    }
    structural_resolutions = exclude_replaced_words(
        load_grammar_structural_resolutions(corrections_path),
        superseded_resolution_words,
    )
    apply_alignment_resolutions(
        connection,
        exclude_replaced_words(
            load_alignment_resolutions(corrections_path),
            superseded_resolution_words,
        ),
    )
    apply_one_character_resolutions(
        connection,
        exclude_structurally_resolved_items(
            exclude_replaced_words(
                load_one_character_resolutions(corrections_path),
                superseded_resolution_words,
            ),
            structural_resolutions,
        ),
    )
    grammar_corrections = apply_grammar_resolutions(
        connection,
        exclude_structurally_resolved_items(
            exclude_replaced_words(
                load_grammar_resolutions(corrections_path),
                superseded_resolution_words,
            ),
            structural_resolutions,
        ),
    )
    grammar_structural_corrections = apply_grammar_structural_resolutions(
        connection,
        structural_resolutions,
    )
    apply_superseded_alignment_resolutions(
        connection,
        exclude_replaced_words(
            load_alignment_resolutions(corrections_path),
            superseded_resolution_words,
        ),
    )
    semantic_corrections = load_semantic_corrections(corrections_path)
    example_corrections = apply_example_resolutions(
        connection,
        exclude_semantically_corrected_items(
            remap_example_resolutions(
                exclude_replaced_words(
                    load_example_resolutions(corrections_path),
                    superseded_resolution_words,
                ),
                structural_resolutions,
            ),
            semantic_corrections,
        ),
        replace_existing=True,
    )
    semantic_correction_count = apply_semantic_corrections(
        connection,
        semantic_corrections,
    )
    pronunciation_uk, pronunciation_us = apply_pronunciation_resolutions(
        connection,
        exclude_replaced_words(
            load_pronunciation_resolutions(corrections_path),
            superseded_resolution_words,
        ),
    )
    ensure_provenance_table(connection)
    generated_examples = fill_generated_examples(connection)
    generated_uk, generated_us = fill_generated_pronunciations(connection)
    reviewed_semantic_provenance = record_reviewed_semantics(
        connection,
        semantic_corrections,
    )
    default_provenance = record_default_provenance(connection)
    grammar_labels_inferred = 0
    for entry_id, part, countability, english in connection.execute(
        """
        SELECT id, part_of_speech, countability, en_definition
        FROM entries
        """
    ):
        if countability.strip():
            continue
        inferred = inferred_grammar_label(part, english)
        if not inferred:
            continue
        connection.execute(
            "UPDATE entries SET countability = ? WHERE id = ?",
            (inferred, entry_id),
        )
        grammar_labels_inferred += 1
    row_count = connection.execute(
        "SELECT COUNT(*) FROM entries"
    ).fetchone()[0]
    headword_count = connection.execute(
        "SELECT COUNT(DISTINCT normalized_word) FROM entries"
    ).fetchone()[0]

    metadata = {
        "schema_version": "2",
        "entry_count": str(row_count),
        "headword_count": str(headword_count),
        "freedict_version": "2025.11.23",
        "oewn_version": "2025",
        "cmudict_version": "master",
        "tatoeba_export": "2026-06-20",
        "curated_corrections": str(corrected),
        "curated_replacement_entries": str(replacements),
        "kaikki_pronunciation_uk": str(pronunciation_uk),
        "kaikki_pronunciation_us": str(pronunciation_us),
        "kaikki_grammar_labels": str(grammar_corrections),
        "grammar_structural_corrections": str(
            grammar_structural_corrections
        ),
        "grammar_labels_inferred": str(grammar_labels_inferred),
        "tatoeba_reviewed_examples": str(example_corrections),
        "ai_semantic_corrections": str(semantic_correction_count),
        "generated_fallback_examples": str(generated_examples),
        "generated_fallback_uk_ipa": str(generated_uk),
        "generated_fallback_us_ipa": str(generated_us),
        "reviewed_semantic_provenance": str(
            reviewed_semantic_provenance
        ),
        "default_provenance_records": str(default_provenance),
    }
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        metadata.items(),
    )
    connection.execute("ANALYZE")
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    print(f"Created {destination} with {row_count:,} entries.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path.home() / ".cache" / "ipa-dict-builder",
    )
    parser.add_argument(
        "--corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/curated_corrections.json"
        ),
    )
    args = parser.parse_args()

    freedict_archive = args.cache / "eng-zho-2025.11.23.tar.xz"
    oewn_archive = args.cache / "english-wordnet-2025-json.zip"
    cmudict_path = args.cache / "cmudict.dict"
    tatoeba_english_path = args.cache / "tatoeba-eng.tsv.bz2"
    tatoeba_chinese_path = args.cache / "tatoeba-cmn.tsv.bz2"
    tatoeba_links_path = args.cache / "tatoeba-links.tar.bz2"
    download(FREEDICT_URL, freedict_archive)
    download(OEWN_URL, oewn_archive)
    download(CMUDICT_URL, cmudict_path)
    download(TATOEBA_ENG_URL, tatoeba_english_path)
    download(TATOEBA_CMN_URL, tatoeba_chinese_path)
    download(TATOEBA_LINKS_URL, tatoeba_links_path)

    print("Parsing FreeDict…")
    freedict = parse_freedict(freedict_archive)
    print("Parsing Open English WordNet…")
    oewn, synset_lemmas = load_oewn(oewn_archive)
    print("Parsing CMUdict…")
    cmu = parse_cmudict(cmudict_path)
    oewn_examples = {
        normalized_sentence(example_text(example))
        for senses in oewn.values()
        for sense in senses
        for example in sense.get("example", [])
        if example_text(example)
    }
    print("Parsing Tatoeba sentence pairs…")
    exact_examples, fallback_examples = load_tatoeba_examples(
        tatoeba_english_path,
        tatoeba_chinese_path,
        tatoeba_links_path,
        set(freedict),
        oewn_examples,
    )
    print(
        f"Matched {len(exact_examples):,} exact examples and "
        f"{len(fallback_examples):,} headword examples."
    )
    create_database(
        args.output,
        freedict,
        oewn,
        synset_lemmas,
        cmu,
        exact_examples,
        fallback_examples,
        args.corrections,
    )


if __name__ == "__main__":
    main()
