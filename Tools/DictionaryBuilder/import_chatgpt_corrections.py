#!/usr/bin/env python3
"""Normalize and merge schema-valid ChatGPT dictionary corrections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


COUNTABILITY_MAP = {
    "": "",
    "c": "C",
    "u": "U",
    "c or u": "C or U",
    "t": "T",
    "i": "I",
    "i or t": "I or T",
    "countable": "C",
    "uncountable": "U",
    "countable/uncountable": "C or U",
    "uncountable/countable": "C or U",
    "c/u": "C or U",
    "u/c": "C or U",
    "singular": "C",
    "singular/countable": "C",
    "singular/uncountable": "U",
    "transitive": "T",
    "intransitive": "I",
    "transitive/intransitive": "I or T",
    "intransitive/transitive": "I or T",
}
PART_OF_SPEECH_MAP = {
    "number": "numeral",
    "interjection": "exclamation",
}

IPA_OVERRIDES = {
    "after": ("/ˈɑːf.tər/", "/ˈæf.tɚ/"),
    "deliver": ("/dɪˈlɪv.ər/", "/dɪˈlɪv.ɚ/"),
    "difference": ("/ˈdɪf.ər.əns/", "/ˈdɪf.ɚ.əns/"),
    "double": ("/ˈdʌb.əl/", "/ˈdʌb.əl/"),
    "dude": ("/djuːd/", "/duːd/"),
    "egg": ("/eɡ/", "/eɡ/"),
    "enough": ("/ɪˈnʌf/", "/ɪˈnʌf/"),
    "figure": ("/ˈfɪɡ.ər/", "/ˈfɪɡ.jɚ/"),
    "fox": ("/fɒks/", "/fɑːks/"),
    "ghosting": ("/ˈɡəʊ.stɪŋ/", "/ˈɡoʊ.stɪŋ/"),
    "go out": ("/ˌɡəʊ ˈaʊt/", "/ˌɡoʊ ˈaʊt/"),
    "herb": ("/hɜːb/", "/ɝːb/"),
    "iron": ("/ˈaɪən/", "/ˈaɪɚn/"),
    "machine": ("/məˈʃiːn/", "/məˈʃiːn/"),
    "no": ("/nəʊ/", "/noʊ/"),
    "one": ("/wʌn/", "/wʌn/"),
    "perfect": ("/ˈpɜː.fekt/", "/ˈpɝː.fekt/"),
    "roar": ("/rɔːr/", "/rɔːr/"),
    "so": ("/səʊ/", "/soʊ/"),
    "source": ("/sɔːs/", "/sɔːrs/"),
    "square": ("/skweər/", "/skwer/"),
    "surface": ("/ˈsɜː.fɪs/", "/ˈsɝː.fɪs/"),
    "tire": ("/ˈtaɪər/", "/ˈtaɪr/"),
    "tower": ("/ˈtaʊ.ər/", "/ˈtaʊ.ɚ/"),
    "tube": ("/tjuːb/", "/tuːb/"),
    "yellow": ("/ˈjel.əʊ/", "/ˈjel.oʊ/"),
}


def normalized_entry(entry: dict) -> dict:
    countability = entry.get("countability", "").strip().lower()
    if countability not in COUNTABILITY_MAP:
        raise ValueError(f"Unsupported countability: {countability!r}")
    part = entry["part_of_speech"].strip().lower()
    examples = entry.get("examples", [])
    if len(examples) != 1:
        raise ValueError(
            f"{entry['word']}: expected exactly one bilingual example"
        )
    word = entry["word"].strip()
    uk_ipa = entry.get("uk_ipa", "").strip()
    us_ipa = entry.get("us_ipa", "").strip()
    if word.lower() in IPA_OVERRIDES:
        uk_ipa, us_ipa = IPA_OVERRIDES[word.lower()]
    return {
        "word": word,
        "uk_ipa": uk_ipa,
        "us_ipa": us_ipa,
        "part_of_speech": PART_OF_SPEECH_MAP.get(part, part),
        "countability": COUNTABILITY_MAP[countability],
        "chinese": entry["chinese"].strip(),
        "english": entry["english"].strip(),
        "examples": [{
            "english": examples[0]["english"].strip(),
            "chinese": examples[0]["chinese"].strip(),
        }],
    }


def import_corrections(source: Path, destination: Path) -> None:
    source_data = json.loads(source.read_text(encoding="utf-8"))
    replacements = {}
    for word, entries in source_data.get("word_replacements", {}).items():
        normalized_word = word.strip().lower()
        normalized = [normalized_entry(entry) for entry in entries]
        if any(entry["word"].lower() != normalized_word for entry in normalized):
            raise ValueError(f"{word}: entry word does not match dictionary key")
        replacements[normalized_word] = normalized

    source_skipped = [
        {
            "word": item["word"].strip().lower(),
            "reason": item["reason"].strip(),
        }
        for item in source_data.get("skipped_words", [])
    ]
    existing = {"word_replacements": {}, "skipped_words": []}
    if destination.exists():
        existing = json.loads(destination.read_text(encoding="utf-8"))
    existing_replacements = existing.setdefault("word_replacements", {})
    overlap = existing_replacements.keys() & replacements.keys()
    conflicting = {
        word for word in overlap
        if existing_replacements[word] != replacements[word]
    }
    if conflicting:
        raise ValueError(
            "Conflicting corrections already imported: "
            + ", ".join(sorted(conflicting))
        )
    existing_replacements.update(replacements)
    skipped_by_word = {
        item["word"]: item
        for item in existing.setdefault("skipped_words", [])
    }
    for item in source_skipped:
        if item["word"] in existing_replacements:
            raise ValueError(
                f"{item['word']}: cannot be both replaced and skipped"
            )
        skipped_by_word[item["word"]] = item
    existing["skipped_words"] = [
        skipped_by_word[word] for word in sorted(skipped_by_word)
    ]
    destination.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Imported {len(replacements)} words and "
        f"{sum(map(len, replacements.values()))} senses; recorded "
        f"{len(source_skipped)} skipped words in {destination}."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/chatgpt_reviewed_replacements.json"
        ),
    )
    args = parser.parse_args()
    import_corrections(args.source, args.output)


if __name__ == "__main__":
    main()
