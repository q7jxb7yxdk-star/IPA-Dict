# IPA Dictionary Builder

This tool creates the SQLite database bundled with the app. It downloads only
redistributable open-data releases and does not scrape dictionary websites.

```sh
python3 Tools/DictionaryBuilder/build_dictionary.py
```

Sources:

- FreeDict English–Chinese 2025.11.23 (CC BY-SA 3.0)
- Open English WordNet 2025 (WordNet License and CC BY 4.0)
- CMU Pronouncing Dictionary (CMU permissive license)
- Montreal Forced Aligner English UK/US dictionaries (CC BY 4.0),
  used only for regional cross-verification
- Tatoeba English–Mandarin sentence pairs (CC BY 2.0 FR)
- WikiMatrix v1 English–Chinese parallel sentences (CC BY-SA 4.0)
- English Wiktionary regional IPA via Kaikki/Wiktextract
  (CC BY-SA 4.0 / GFDL)
- CC-CEDICT Chinese–English 2026-06-22 (CC BY-SA 4.0), used as
  reverse-translation evidence for semantic mismatch review

The database is intentionally limited to the bilingual FreeDict headwords.
Each Chinese definition is paired only with English definitions from the same
FreeDict sense. Open English WordNet enriches matching parts of speech with
synonyms, but its more granular definitions are not mixed into the bilingual
entries. CMUdict supplies US pronunciation data. Tatoeba supplies at most one
bilingual example for a headword; the app displays it only when both sides
contain the relevant English and Chinese dictionary words.

Missing UK pronunciations can be reviewed against a downloaded Kaikki English
JSONL file. The importer accepts only phonemic `/…/` IPA with an explicit
supported British regional tag. Explicit General American and US-tagged
phonemic transcriptions can independently fill the US field. Neither region
is copied into the other. Untagged, abbreviated, and narrow phonetic `[…]`
transcriptions are not imported.

For a full regional rebuild, the pronunciation generator reads every exact
sense from the database. A regional value is authoritative only when the
highest-priority Kaikki candidate is unique for the same headword and part of
speech. When both regions have variants, an existing pair may be corrected
only if the current UK value occurs in the best US candidate set and the
current US value occurs in the best UK candidate set:

```sh
python3 Tools/DictionaryBuilder/generate_pronunciation_resolutions.py \
  --source /path/to/kaikki.org-dictionary-English.jsonl \
  --database "IPA Dict/Data/dictionary.sqlite" \
  --replace-existing \
  --clear-unverified \
  --cmudict /path/to/cmudict.dict
```

`--clear-unverified` removes legacy FreeDict pronunciations whose source does
not identify a region. Curated replacement headwords and manually
cross-verified values are retained. CMUdict headwords remain trusted for US
pronunciation only. The database builder likewise no longer interprets the
order of unlabelled FreeDict pronunciation elements as UK then US.

When a newer Kaikki extraction omits values retained from an older explicit
regional source, generate a candidate ledger separately and merge additions
without deleting previously verified values:

```sh
python3 Tools/DictionaryBuilder/merge_pronunciation_additions.py \
  --existing Tools/DictionaryBuilder/pronunciation_review_resolutions.json \
  --candidate /path/to/new-pronunciation-resolutions.json \
  --output Tools/DictionaryBuilder/pronunciation_review_resolutions.json
```

```sh
python3 Tools/DictionaryBuilder/generate_pronunciation_resolutions.py \
  --source /path/to/kaikki.org-dictionary-English.jsonl
```

Missing noun countability and verb transitivity labels can be matched to an
exact Kaikki sense. The generator can also use two conservative headword-wide
rules: every gloss-bearing Kaikki sense must have the same explicit grammar
label, or every Open English WordNet verb sense must have a frame with the
same transitivity. Conflicting, incomplete, or ambiguous results remain blank:

```sh
python3 Tools/DictionaryBuilder/generate_grammar_resolutions.py \
  --source /path/to/kaikki.org-dictionary-English.jsonl \
  --oewn /path/to/english-wordnet-2025-json.zip
```

The remaining verb senses can be exported with their Kaikki and OEWN evidence
for exact-sense manual review:

```sh
python3 Tools/DictionaryBuilder/generate_grammar_manual_review.py \
  --kaikki /path/to/kaikki.org-dictionary-English.jsonl \
  --oewn /path/to/english-wordnet-2025-json.zip
```

The manual review is bound to a SHA-256 signature of the exact review scope,
so its index-based decisions cannot silently apply to a changed audit file.
Completed decisions are merged into `grammar_review_resolutions.json`.
The same ledger records structural resolutions for source rows that are
auxiliaries, fixed expressions, malformed glosses, or non-verb senses.
Confirmed modal and auxiliary uses remain verbs but are explicitly exempt
from T/I auditing; they are not counted as missing grammar labels.

Remaining noun countability is resolved from Kaikki's `en-noun` header
templates. Exact English-sense matches are preferred; a headword-wide value is
used only when every noun entry has the same header. The final unmatched
senses are stored in a signed manual ledger:

```sh
python3 Tools/DictionaryBuilder/generate_noun_countability_review.py \
  --kaikki /path/to/kaikki.org-dictionary-English.jsonl
```

`noun_countability_review.json` records each exact sense, its source evidence,
the reviewed `C`, `U`, or `C or U` decision, and any structural correction.

Missing examples can be matched to redistributable Tatoeba English–Mandarin
sentence pairs. A candidate is accepted only when its Chinese sentence
contains a term from the displayed Chinese definition:

```sh
python3 Tools/DictionaryBuilder/generate_example_resolutions.py \
  --english /path/to/tatoeba-eng.tsv.bz2 \
  --chinese /path/to/tatoeba-cmn.tsv.bz2 \
  --links /path/to/tatoeba-links.tar.bz2
```

The example matcher scans the full Tatoeba export, supports common English
inflections and exact multiword phrases, and normalizes common Simplified and
Traditional Chinese variants. New automatic matches require a Chinese
definition term of at least two characters that identifies only one local
sense for the headword. Existing reviewed examples are preserved from the
bundled database.

The builder does not attach a headword-level Tatoeba fallback while parsing
source senses. Such a sentence can contain the correct English and Chinese
words while illustrating a different sense. Only curated replacement
examples or examples recorded in an exact-sense review ledger are retained;
the cleaner removes legacy unreviewed fallback examples.

A separate, deliberately small WikiMatrix pass can provide additional
examples after the Tatoeba pass. It uses the original scored WikiMatrix TSV,
requires a margin score of at least 1.08, excludes proper nouns and
encyclopedic sentence patterns, checks both translation directions with
local Helsinki-NLP models, and writes every accepted or rejected candidate
to a manual-review ledger:

```sh
python3 Tools/DictionaryBuilder/generate_wikimatrix_example_review.py \
  --wikimatrix /path/to/WikiMatrix.en-zh.tsv.gz \
  --en-zh-model /path/to/opus-mt-en-zh \
  --zh-en-model /path/to/opus-mt-zh-en
```

Only rows marked `approved` in `wikimatrix_example_review.json` are applied
by the cleaner. Automatic similarity scores are candidate filters rather
than proof of correctness; every retained row is checked against the exact
local part of speech and English definition.

The review generators retain previously matched exact-sense decisions after
the bundled database has been updated, so a later audit does not discard
completed review work.

## Chinese semantic review

FreeDict occasionally contains a valid English definition paired with an
unrelated Chinese value. Format-only checks cannot detect errors such as
`endnote` translated as `音符`, `instrument` translated as `中國`, or a
computing `overwrite` sense translated as `墜毀`.

Exact-sense corrections are stored in `ai_semantic_corrections.json`. Each
record is bound to the headword, part of speech, original Chinese value, and
complete English definition. It also records the reviewed Traditional Chinese
definition, reason, and one bilingual example. Both the builder and cleaner
fail if the upstream exact sense changes instead of silently applying a stale
correction.

CC-CEDICT can be used to generate a conservative reverse-translation queue:

```sh
python3 Tools/DictionaryBuilder/generate_semantic_review.py \
  --cedict /path/to/cedict_1_0_ts_utf-8_mdbg.zip

python3 Tools/DictionaryBuilder/generate_cedict_translation_review.py \
  --cedict /path/to/cedict_1_0_ts_utf-8_mdbg.zip
```

The first command detects Chinese glosses whose CC-CEDICT meanings have no
lexical support in the local English definition. The second independently
looks for Chinese entries whose English gloss names the local headword and
ranks them against the exact local sense. These files are review queues, not
automatic corrections: polysemy can produce plausible but wrong candidates.

Kaikki/English Wiktionary translations provide a second exact-sense evidence
queue where Chinese translations are available:

```sh
python3 Tools/DictionaryBuilder/generate_kaikki_translation_review.py \
  --source /path/to/kaikki.org-dictionary-English.jsonl
```

AI review may select or rewrite a candidate, but generated content is recorded
as such and never presented as a source quotation. A correction is applied
only after its exact English sense and part of speech have been checked.

## Complete fallback mode

The builder and cleaner fill every remaining empty example and regional IPA
field after all source-backed and reviewed layers have run. These values are
explicitly marked `generated_fallback` in the SQLite `entry_provenance` table:

- missing examples receive a deterministic definition-backed metalinguistic
  example containing the exact headword and displayed Chinese definition
- missing IPA receives a deterministic grapheme-to-phoneme approximation
- generated values never replace a source-backed or reviewed value

Generated examples are intentionally factual about word usage rather than
inventing a potentially wrong real-world context. Generated IPA is a reading
aid, especially for rare names and multiword expressions, and must not be
treated as an authoritative regional transcription. `entry_provenance`
distinguishes `verified_source`, `source_or_reviewed`, `ai_reviewed`, and
`generated_fallback`.

## Audit and cleanup

See `DictionaryAudit.md` for the current data-quality baseline.

Run `audit_dictionary.py` to produce CSV review queues. Run
`clean_dictionary.py --output <path>` to create a conservative cleaned copy.
The cleanup command never overwrites the bundled database and never generates
Chinese definitions with machine translation.

The full audit also checks malformed or missing UK/US IPA, missing and invalid
bilingual examples, missing noun countability or verb transitivity labels,
and legacy part-of-speech names. The current generated queues are stored in
`FullDictionaryAudit/`.

The builder and cleaner strip source-reference markup from IPA, normalize
bracketed phonetic transcriptions, normalize legacy part-of-speech names, and
infer grammar labels only when the source definition explicitly says
`countable`, `uncountable`, `transitive`, or `intransitive`. Unreviewed
Tatoeba examples are retained only when their Chinese sentence contains a
displayed Chinese definition term.

`curated_corrections.json` contains definition-specific Chinese corrections
and complete replacements for selected unreliable headwords. Both the builder
and cleaner require every correction to match exactly, so source changes
cannot silently skip a reviewed correction.

`generate_common_curation.py` audits a fixed list of common words and creates
`common_word_replacements.json`. It keeps only the first modern source sense
for each part of speech when a bilingual example contains both the headword
and its Chinese definition. Function words and incomplete matches remain in
`CommonWordCuration.md` for manual review. The builder and cleaner merge the
generated replacements automatically.

```sh
python3 Tools/DictionaryBuilder/generate_common_curation.py \
  --database "IPA Dict/Data/dictionary.sqlite" \
  --curated Tools/DictionaryBuilder/curated_corrections.json \
  --output Tools/DictionaryBuilder/common_word_replacements.json \
  --report Tools/DictionaryBuilder/CommonWordCuration.md
```

ChatGPT review output is normalized with:

```sh
python3 Tools/DictionaryBuilder/import_chatgpt_corrections.py \
  /path/to/batch-corrections.json
```

The importer converts long-form countability and transitivity labels to the
app's `C`, `U`, `C or U`, `T`, `I`, and `I or T` notation. Reviewed entries
are stored separately in `chatgpt_reviewed_replacements.json` and merged after
the manual and generated correction layers.

Codex-reviewed entries are stored in `codex_reviewed_replacements.json` as the
final replacement layer. Run `generate_codex_progress.py` to regenerate
`CodexReviewProgress.md`, which lists every word in the active review scope
and distinguishes completed replacements from genuinely deferred items.

`generate_alignment_resolutions.py` records the disposition of every
definition-alignment group in `alignment_review_resolutions.json`. Proper
names and source senses that legitimately share a Chinese definition are
preserved. The 285 high-risk groups use explicit, manually selected English
definitions and corrected Traditional Chinese definitions; the cleaner
verifies each retained English definition exists before deleting any
conflicting rows.

```sh
python3 Tools/DictionaryBuilder/generate_alignment_resolutions.py
```

`generate_one_character_resolutions.py` records the review of every
single-character Chinese definition. Valid concise translations are retained
instead of being mechanically expanded. Confirmed mismatches use exact
headword, part-of-speech, Chinese-definition, and English-definition matching
before the cleaner applies a corrected Traditional Chinese definition.

```sh
python3 Tools/DictionaryBuilder/generate_one_character_resolutions.py
```
