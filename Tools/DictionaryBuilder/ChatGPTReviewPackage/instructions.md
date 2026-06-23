# ChatGPT dictionary review instructions

This package contains every unresolved item from the IPA Dict audit.
It contains 8,615 unique headwords in
36 JSONL batches.

## Task

Review each JSONL record and produce correction JSON files conforming to
`output_schema.json`.

Rules:

1. Keep only common, modern meanings useful in a general learner dictionary.
2. Separate noun, verb, adjective, adverb, and other valid parts of speech.
3. Never use `interjection`; use `exclamation` when that category is needed.
4. Use accurate Traditional Chinese definitions. Do not merely translate an
   English definition without checking the lexical meaning.
5. Each English definition must have its own matching Chinese definition.
6. Include exactly one natural bilingual example for every retained sense.
7. The Chinese example must contain the main Chinese definition word.
8. Preserve or correct UK/US IPA and countability/transitivity.
9. Do not invent missing meanings solely because WordNet proposes a part of
   speech. Add it only when confident it is common and useful.
10. Skip proper nouns, technical abbreviations, or uncertain entries when the
    existing value is already acceptable. Record them in `skipped_words`.
11. Do not modify IDs or return SQL. Return only schema-valid JSON.

## Suggested workflow

- Start with `batches/000-priority-common.jsonl`.
- Continue through the numbered files in order.
- Create one output JSON for each input batch.
- Do not repeat words across output files.
- When all batches are complete, combine their `word_replacements` and
  `skipped_words` into one final JSON file.

## Input record

Each JSONL line contains:

- `word`: normalized headword
- `priority`: why it appears early in the package
- `issues`: audit findings requiring review
- `current_entries`: all current database senses, pronunciations and examples

The audit lists are candidates, not proof of an error. Preserve correct data
and explicitly skip false positives.
