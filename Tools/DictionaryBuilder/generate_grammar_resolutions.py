#!/usr/bin/env python3
"""Generate exact-sense grammar labels from Kaikki/Wiktionary data."""

from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path


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


def normalized_word(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalized_definition(value: str) -> str:
    value = re.sub(r"^\([^)]*\)\s*", "", value.strip().lower())
    value = re.sub(r"\[[^]]*]", "", value)
    return " ".join(re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value))


def grammar_label(part: str, tags: set[str]) -> str:
    if part == "noun":
        countable = "countable" in tags
        uncountable = "uncountable" in tags
        if countable and uncountable:
            return "C or U"
        if countable:
            return "C"
        if uncountable:
            return "U"
    if part == "verb":
        transitive = "transitive" in tags
        intransitive = "intransitive" in tags
        if "ambitransitive" in tags or (transitive and intransitive):
            return "I or T"
        if transitive:
            return "T"
        if intransitive:
            return "I"
    return ""


def noun_header_label(item: dict) -> str:
    labels = set()
    for template in item.get("head_templates", []):
        if template.get("name") != "en-noun":
            continue
        args = template.get("args", {})
        expansion = str(template.get("expansion", "")).lower()
        if (
            args.get("1") == "~"
            or "countable and uncountable" in expansion
        ):
            labels.add("C or U")
        elif args.get("1") == "-" or "uncountable" in expansion:
            labels.add("U")
        elif (
            args.get("1") == "!"
            or "plural only" in expansion
            or "plural " in expansion
            or not args
        ):
            labels.add("C")
    return next(iter(labels)) if len(labels) == 1 else ""


def oewn_verb_label(frames: list[str]) -> str:
    transitive = any(
        frame.startswith("vt") or frame == "ditransitive"
        for frame in frames
    )
    intransitive = any(
        frame.startswith("vi")
        or frame.startswith("via")
        or frame in {"nonreferential", "nonreferential-sent"}
        for frame in frames
    )
    if transitive and intransitive:
        return "I or T"
    if transitive:
        return "T"
    if intransitive:
        return "I"
    return ""


def load_oewn_verb_consensus(
    archive: Path | None,
    targets: set[str],
) -> dict[str, str]:
    if archive is None:
        return {}
    labels_by_word: dict[str, list[str]] = defaultdict(list)
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if not name.startswith("entries-") or not name.endswith(".json"):
                continue
            data = json.loads(bundle.read(name))
            for lemma, parts in data.items():
                word = normalized_word(lemma.replace("_", " "))
                if word not in targets or "v" not in parts:
                    continue
                for sense in parts["v"].get("sense", []):
                    labels_by_word[word].append(
                        oewn_verb_label([
                            str(frame)
                            for frame in sense.get("subcat", [])
                        ])
                    )
    return {
        word: labels[0]
        for word, labels in labels_by_word.items()
        if labels and all(labels) and len(set(labels)) == 1
    }


def load_manual_verb_decisions(output_path: Path) -> dict[tuple[str, str], dict]:
    review_path = output_path.with_name("grammar_manual_review.json")
    if not review_path.exists():
        return {}
    data = json.loads(review_path.read_text(encoding="utf-8"))
    return {
        (
            normalized_word(str(item.get("word", ""))),
            str(item.get("english", "")).strip(),
        ): item
        for item in data.get("reviews", [])
        if item.get("reviewed_label") in {"T", "I", "I or T"}
    }


def load_manual_noun_decisions(output_path: Path) -> dict[tuple[str, str], dict]:
    review_path = output_path.with_name("noun_countability_review.json")
    if not review_path.exists():
        return {}
    data = json.loads(review_path.read_text(encoding="utf-8"))
    return {
        (
            normalized_word(str(item.get("word", ""))),
            str(item.get("english", "")).strip(),
        ): item
        for item in data.get("reviews", [])
        if item.get("reviewed_label") in {"C", "U", "C or U"}
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--oewn",
        type=Path,
        help=(
            "Optional Open English WordNet JSON zip. A verb label is used "
            "only when every OEWN sense has the same transitivity."
        ),
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/FullDictionaryAudit/"
            "missing_grammar_labels.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/grammar_review_resolutions.json"
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
    targets = {
        (normalized_word(row["normalized_word"]), row["part_of_speech"])
        for row in rows
    }
    labels: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    headword_sense_counts: dict[tuple[str, str], int] = defaultdict(int)
    headword_labeled_counts: dict[tuple[str, str], int] = defaultdict(int)
    headword_labels: dict[tuple[str, str], set[str]] = defaultdict(set)
    noun_header_labels: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    noun_headword_labels: dict[str, set[str]] = defaultdict(set)

    with args.source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid Kaikki JSON on line {line_number}: {error}"
                ) from error
            if item.get("lang_code") != "en":
                continue
            word = normalized_word(str(item.get("word", "")))
            part = POS_MAP.get(
                str(item.get("pos", "")),
                str(item.get("pos", "")),
            )
            if (word, part) not in targets:
                continue
            header_label = noun_header_label(item) if part == "noun" else ""
            if header_label:
                noun_headword_labels[word].add(header_label)
            entry_tags = {
                str(tag)
                for tag in item.get("tags", [])
            }
            for sense in item.get("senses", []):
                if not sense.get("glosses"):
                    continue
                headword_sense_counts[(word, part)] += 1
                tags = entry_tags | {
                    str(tag)
                    for tag in sense.get("tags", [])
                }
                label = grammar_label(part, tags)
                if label:
                    headword_labeled_counts[(word, part)] += 1
                    headword_labels[(word, part)].add(label)
                for gloss in sense.get("glosses", []):
                    definition = normalized_definition(str(gloss))
                    if definition:
                        if label:
                            labels[(word, part, definition)].add(label)
                        if header_label:
                            noun_header_labels[
                                (word, part, definition)
                            ].add(header_label)

    kaikki_consensus = {
        key: next(iter(values))
        for key, values in headword_labels.items()
        if headword_sense_counts[key] > 0
        and headword_labeled_counts[key] == headword_sense_counts[key]
        and len(values) == 1
    }
    oewn_consensus = load_oewn_verb_consensus(
        args.oewn,
        {
            word
            for word, part in targets
            if part == "verb"
        },
    )
    noun_headword_consensus = {
        word: next(iter(values))
        for word, values in noun_headword_labels.items()
        if len(values) == 1
    }
    manual_verb_decisions = load_manual_verb_decisions(args.output)
    manual_noun_decisions = load_manual_noun_decisions(args.output)

    resolutions = []
    current_keys = set()
    for row in rows:
        key = (
            normalized_word(row["normalized_word"]),
            row["part_of_speech"],
            normalized_definition(row["en_definition"]),
        )
        current_keys.add((
            normalized_word(row["normalized_word"]),
            row["part_of_speech"].lower(),
            row["en_definition"].strip(),
        ))
        candidates = sorted(labels.get(key, set()))
        exact_label = candidates[0] if len(candidates) == 1 else ""
        noun_header_candidates = sorted(
            noun_header_labels.get(key, set())
        )
        noun_exact_label = (
            noun_header_candidates[0]
            if len(noun_header_candidates) == 1
            else ""
        )
        noun_consensus_label = (
            noun_headword_consensus.get(
                normalized_word(row["normalized_word"]),
                "",
            )
            if row["part_of_speech"] == "noun"
            else ""
        )
        kaikki_label = kaikki_consensus.get((
            normalized_word(row["normalized_word"]),
            row["part_of_speech"],
        ), "")
        oewn_label = (
            oewn_consensus.get(
                normalized_word(row["normalized_word"]),
                "",
            )
            if row["part_of_speech"] == "verb"
            else ""
        )
        manual_decision = manual_verb_decisions.get((
            normalized_word(row["normalized_word"]),
            row["en_definition"].strip(),
        ))
        manual_noun_decision = manual_noun_decisions.get((
            normalized_word(row["normalized_word"]),
            row["en_definition"].strip(),
        ))
        if manual_decision and row["part_of_speech"] == "verb":
            label = manual_decision["reviewed_label"]
            status = "matched_manual_exact_verb_review"
        elif manual_noun_decision and row["part_of_speech"] == "noun":
            label = manual_noun_decision["reviewed_label"]
            status = "matched_manual_exact_noun_review"
        elif noun_exact_label:
            label = noun_exact_label
            status = "matched_exact_kaikki_noun_header"
        elif exact_label:
            label = exact_label
            status = "matched_exact_kaikki_sense"
        elif kaikki_label and oewn_label and kaikki_label != oewn_label:
            label = ""
            status = "deferred_cross_source_conflict"
        elif kaikki_label:
            label = kaikki_label
            status = "matched_unanimous_kaikki_headword"
        elif oewn_label:
            label = oewn_label
            status = "matched_unanimous_oewn_verb_frames"
        elif noun_consensus_label:
            label = noun_consensus_label
            status = "matched_unanimous_kaikki_noun_headers"
        else:
            label = ""
            status = "deferred_no_unambiguous_match"
        resolutions.append({
            "entry_id": int(row["id"]),
            "word": row["normalized_word"],
            "part_of_speech": row["part_of_speech"],
            "english": row["en_definition"],
            "grammar_label": label,
            "candidates": candidates,
            "noun_header_candidates": noun_header_candidates,
            "noun_headword_consensus": noun_consensus_label,
            "kaikki_headword_consensus": kaikki_label,
            "oewn_verb_consensus": oewn_label,
            "manual_review_reason": (
                manual_decision.get("review_reason", "")
                if manual_decision
                else (
                    manual_noun_decision.get("review_reason", "")
                    if manual_noun_decision
                    else ""
                )
            ),
            "status": status,
        })
    resolutions.extend(
        item
        for item in existing_resolutions
        if item.get("grammar_label")
        and (
            normalized_word(str(item.get("word", ""))),
            str(item.get("part_of_speech", "")).lower(),
            str(item.get("english", "")).strip(),
        ) not in current_keys
    )

    matched = sum(bool(item["grammar_label"]) for item in resolutions)
    args.output.write_text(
        json.dumps(
            {
                "source": (
                    "Kaikki English dictionary extracted 2026-06-15 "
                    "from enwiktionary dump 2026-06-01; optional Open "
                    "English WordNet 2025 verb frames"
                ),
                "license": (
                    "CC BY-SA 4.0 / GFDL; WordNet License / CC BY 4.0"
                ),
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
        f"{matched} reliable grammar matches."
    )


if __name__ == "__main__":
    main()
