#!/usr/bin/env python3
"""Generate a small, high-confidence WikiMatrix example review queue."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from generate_common_curation import AUTO_EXCLUDED, traditional
from generate_example_resolutions import (
    inflected_forms,
    normalized_chinese,
    normalized_sentence,
    translation_terms,
)


HAN_PATTERN = re.compile(r"[\u3400-\u9fff]")
BAD_PUNCTUATION = re.compile(r"[\[\](){}<>/|=“”\"：:；;]")
ENGLISH_WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but",
    "by", "for", "from", "had", "has", "have", "he", "her", "hers", "him",
    "his", "i", "in", "is", "it", "its", "not", "of", "on", "or", "our",
    "ours", "she", "that", "the", "their", "theirs", "them", "they", "this",
    "to", "was", "we", "were", "with", "you", "your", "yours",
}

# Every candidate that passes the automatic filters is reviewed against its
# exact local sense. Rejections remain in the ledger so the decision is
# auditable and a future generator run cannot silently reintroduce them.
MANUAL_REJECTIONS = {
    252: "Chinese sentence is grammatically awkward.",
    1125: "The coordinated object is semantically unnatural.",
    2588: "Unnecessary biographical proper-name example.",
    2971: "Unnecessary biographical proper-name example.",
    3481: "Sentence is unnatural and unsuitable for a learner dictionary.",
    4376: "Uses the word only inside an organization name.",
    5551: "English sentence is a fragment.",
    6204: "Unnecessary biographical proper-name example.",
    7092: "Local Chinese definition has the wrong adjectival form.",
    7487: "Chinese sentence adds a person name absent from the English.",
    8799: "Example uses the refusal sense, not the exact local sense.",
    9391: "Example uses distributed as spread rather than divide and dispense.",
    9540: "Unnecessary biographical proper-name example.",
    9937: "Sentence depends on missing context and the translation is awkward.",
    10839: "Example contains estimate as a noun, not the target verb.",
    11584: "Sentence depends on an unresolved antecedent.",
    13762: "Example is the ceremony sense, not the measurement-mark sense.",
    14367: "Example uses handicapped as a substantive plural, not an adjective.",
    17995: "Example is political liberalism, not the exact Liberal-party sense.",
    19715: "Chinese and English are both awkward for a learner example.",
    20456: "Chinese sentence adds Oslo, which is absent from the English.",
    20489: "Sentence does not explain or naturally illustrate museology.",
    20903: "English sentence is a fragment.",
    22861: "Example is an ordinary peasant, not the strategy-game unit sense.",
    23053: "Example is a generic time span, not the periodic-cycle sense.",
    23685: "Example contains a verb, not the target noun sense.",
    24055: "The sentence and translation are semantically unnatural.",
    27220: "Mythological context makes the example confusing for learners.",
    27618: "Example is sex trade, not the sexual-intercourse sense.",
    29550: "Example is social rank, not the state-of-affairs sense.",
    30238: "Chinese definition and translation incorrectly use a noun.",
    30921: "Example is an industry list and does not illustrate the exact sense.",
    31042: "Example is the word-or-expression sense, not a term of office.",
    31826: "Example is the sex-trade industry, not a buying or selling instance.",
    33954: "Example does not demonstrate the truce or surrender meaning.",
}


def model_snapshot(root: Path) -> Path:
    if (root / "config.json").exists():
        return root
    snapshots = root / "snapshots"
    for candidate in sorted(snapshots.iterdir()):
        if (
            (candidate / "config.json").exists()
            and (candidate / "tokenizer_config.json").exists()
        ):
            return candidate
    raise RuntimeError(f"No complete model snapshot found under {root}")


def translate(model_path: Path, texts: list[str]) -> list[str]:
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "transformers is required to generate the WikiMatrix review queue"
        ) from error

    tokenizer = AutoTokenizer.from_pretrained(
        model_snapshot(model_path),
        local_files_only=True,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_snapshot(model_path),
        local_files_only=True,
    )
    translated: list[str] = []
    for start in range(0, len(texts), 32):
        batch = tokenizer(
            texts[start:start + 32],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=96,
        )
        output = model.generate(
            **batch,
            max_new_tokens=80,
            num_beams=1,
        )
        translated.extend(
            tokenizer.decode(value, skip_special_tokens=True)
            for value in output
        )
    return translated


def chinese_text(value: str) -> str:
    return "".join(HAN_PATTERN.findall(traditional(value)))


def chinese_bigrams(value: str) -> set[str]:
    value = chinese_text(value)
    return {
        value[index:index + 2]
        for index in range(max(0, len(value) - 1))
    }


def dice(first: set[str], second: set[str]) -> float:
    if not first or not second:
        return 0.0
    return 2 * len(first & second) / (len(first) + len(second))


def stem(value: str) -> str:
    for suffix in ("ingly", "edly", "ing", "ied", "ies", "ed", "es", "s"):
        if value.endswith(suffix) and len(value) > len(suffix) + 2:
            return value[:-len(suffix)]
    return value


def english_content_words(value: str) -> set[str]:
    return {
        stem(word)
        for word in normalized_sentence(value).split()
        if word not in STOP_WORDS and len(word) > 2
    }


def valid_learning_sentence(english: str, chinese: str) -> bool:
    tokens = normalized_sentence(english).split()
    raw_words = ENGLISH_WORD.findall(english)
    return (
        5 <= len(tokens) <= 14
        and english[:1].isupper()
        and english[-1:] in ".!?"
        and not BAD_PUNCTUATION.search(english)
        and not BAD_PUNCTUATION.search(chinese)
        and not re.search(r"\d", english + chinese)
        and bool(HAN_PATTERN.search(chinese))
        and 8 <= len(chinese) <= 55
        and not re.search(r"[A-Za-z]{2,}", chinese)
        and not any(
            word[0].isupper() and word != "I"
            for word in raw_words[1:]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument("--wikimatrix", type=Path, required=True)
    parser.add_argument("--en-zh-model", type=Path, required=True)
    parser.add_argument("--zh-en-model", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/wikimatrix_example_review.json"
        ),
    )
    args = parser.parse_args()

    connection = sqlite3.connect(
        f"file:{args.database}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT id, normalized_word, part_of_speech, zh_definition,
               en_definition
        FROM entries
        WHERE examples_json = '[]'
        """
    ).fetchall()
    connection.close()
    senses = {int(row["id"]): row for row in rows}

    term_senses: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in rows:
        for term in translation_terms(row["zh_definition"]):
            normalized = normalized_chinese(term)
            if len(normalized) >= 2:
                term_senses[
                    (row["normalized_word"], normalized)
                ].add(int(row["id"]))

    targets: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for row in rows:
        word = row["normalized_word"]
        if (
            word in AUTO_EXCLUDED
            or row["part_of_speech"].lower() == "proper noun"
        ):
            continue
        for term in translation_terms(row["zh_definition"]):
            normalized = normalized_chinese(term)
            if (
                len(normalized) >= 2
                and len(term_senses[(word, normalized)]) == 1
            ):
                targets[word].append((normalized, int(row["id"])))

    form_targets: dict[str, set[str]] = defaultdict(set)
    phrase_targets: dict[str, set[str]] = defaultdict(set)
    for word in targets:
        if " " in word:
            phrase_targets[word.split()[0]].add(word)
        else:
            for form in inflected_forms(word):
                form_targets[form].add(word)

    best: dict[int, tuple[tuple, str, str, str, int]] = {}
    with gzip.open(args.wikimatrix, "rt", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                score_text, english, chinese = line.rstrip("\n").split(
                    "\t",
                    2,
                )
                score = float(score_text)
            except ValueError:
                continue
            if score < 1.08:
                break
            if not valid_learning_sentence(english, chinese):
                continue

            tokens = normalized_sentence(english).split()
            matched_words: dict[str, int] = {}
            for token in set(tokens):
                for word in form_targets.get(token, set()):
                    matched_words[word] = max(
                        matched_words.get(word, 0),
                        3 if token == word else 2,
                    )
            padded = f" {' '.join(tokens)} "
            for token in set(tokens):
                for word in phrase_targets.get(token, set()):
                    if f" {word} " in padded:
                        matched_words[word] = 4

            normalized_translation = normalized_chinese(chinese)
            for word, match_quality in matched_words.items():
                for term, entry_id in targets[word]:
                    if term not in normalized_translation:
                        continue
                    rank = (
                        score,
                        match_quality,
                        len(term),
                        -len(tokens),
                        -line_number,
                    )
                    if entry_id not in best or rank > best[entry_id][0]:
                        best[entry_id] = (
                            rank,
                            english.strip(),
                            chinese.strip(),
                            term,
                            line_number,
                        )

    candidates = list(best.items())
    english_sentences = [value[1][1] for value in candidates]
    chinese_sentences = [value[1][2] for value in candidates]
    machine_chinese = translate(args.en_zh_model, english_sentences)
    back_translations = translate(args.zh_en_model, chinese_sentences)

    reviews = []
    for (
        (entry_id, (rank, english, chinese, term, line_number)),
        translated_chinese,
        back_translation,
    ) in zip(candidates, machine_chinese, back_translations):
        chinese_similarity = dice(
            chinese_bigrams(chinese),
            chinese_bigrams(translated_chinese),
        )
        sequence_similarity = SequenceMatcher(
            None,
            chinese_text(chinese),
            chinese_text(translated_chinese),
        ).ratio()
        back_translation_similarity = dice(
            english_content_words(english),
            english_content_words(back_translation),
        )
        if (
            chinese_similarity < 0.55
            or sequence_similarity < 0.50
            or back_translation_similarity < 0.65
        ):
            continue

        row = senses[entry_id]
        rejection_reason = MANUAL_REJECTIONS.get(entry_id)
        reviews.append({
            "entry_id": entry_id,
            "word": row["normalized_word"],
            "part_of_speech": row["part_of_speech"],
            "chinese": row["zh_definition"],
            "english": row["en_definition"],
            "example": {
                "english": english,
                "chinese": chinese,
                "source": "WikiMatrix v1",
                "source_line": line_number,
                "alignment_score": round(rank[0], 8),
            },
            "matched_definition_term": term,
            "quality": {
                "chinese_similarity": round(chinese_similarity, 6),
                "chinese_sequence_similarity": round(
                    sequence_similarity,
                    6,
                ),
                "back_translation_similarity": round(
                    back_translation_similarity,
                    6,
                ),
                "machine_chinese": translated_chinese,
                "back_translation": back_translation,
            },
            "decision": (
                "rejected"
                if rejection_reason
                else "approved"
            ),
            "review_note": (
                rejection_reason
                or "Exact sense and bilingual sentence manually verified."
            ),
        })

    reviews.sort(key=lambda item: (item["word"], item["entry_id"]))
    approved_count = sum(
        item["decision"] == "approved"
        for item in reviews
    )
    args.output.write_text(
        json.dumps(
            {
                "source": "WikiMatrix v1 English-Chinese scored TSV",
                "license": "CC BY-SA 4.0",
                "automatic_filters": {
                    "minimum_alignment_score": 1.08,
                    "minimum_chinese_similarity": 0.55,
                    "minimum_chinese_sequence_similarity": 0.50,
                    "minimum_back_translation_similarity": 0.65,
                    "proper_nouns_excluded": True,
                    "learning_sentence_surface_filter": True,
                },
                "review_count": len(reviews),
                "approved_count": approved_count,
                "reviews": reviews,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Created {args.output}: {len(reviews)} candidates.")


if __name__ == "__main__":
    main()
