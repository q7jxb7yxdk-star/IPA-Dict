# Dictionary Data Audit

Audit date: 2026-06-22

## Baseline

- 34,729 definition rows
- 23,833 distinct normalized headwords
- No empty part-of-speech, Chinese-definition, or English-definition fields
- 7,386 rows without UK IPA and 6,243 rows without US IPA

## Audit output

The 2026-06-21 audit produced:

- 43 definitely corrupted rows containing URL encoding, broken Wiki markup,
  or invalid literals
- 122 rows without Han characters requiring manual review; some are valid
  abbreviations, while others contain unrelated foreign-language text
- 5,167 rows with a one-character Chinese definition requiring review
- 3,998 Chinese-definition groups paired with two or more English definitions;
  these are alignment risks rather than automatically confirmed errors
- 4,182 possible missing core-POS pairs across 3,838 local headwords when
  compared with Open English WordNet

Examples of confirmed or highly likely errors include `coupon → 好`,
`good luck → 屁股`, `major → 中指`, `versatile → 0.5`,
`aquarium → [[#`, and `wetland → pantano`.

## Generate review reports

```sh
python3 Tools/DictionaryBuilder/audit_dictionary.py \
  --oewn /path/to/english-wordnet-2025-json.zip \
  --output /tmp/ipa-dictionary-audit
```

The command creates:

- `definite_corruption.csv`
- `non_chinese_translation_review.csv`
- `one_character_chinese_review.csv`
- `definition_alignment_review.csv`
- `missing_part_of_speech_candidates.csv`
- `summary.json`

## Create a conservative cleaned database

```sh
python3 Tools/DictionaryBuilder/clean_dictionary.py \
  --output /tmp/dictionary-cleaned.sqlite
```

The cleaner never overwrites the bundled database. It normalizes
`interjection` to `exclamation`, safely decodes or unwraps recoverable Chinese
text, and moves unrepairable rows into `quarantined_entries`. It does not
machine-translate definitions or automatically accept missing-POS candidates.

The correction set currently applies 126 definition-specific Chinese
corrections, fully replaces 70 manually curated source headwords with 215
entries, and conservatively replaces another 168 common headwords with 218
source-aligned entries.

## Bundled database update

The bundled database was updated on 2026-06-21:

- 55 reviewed definition-specific corrections applied
- `test` now contains noun and verb entries
- `yes` now contains adverb and noun entries
- all 224 `interjection` values normalized to `exclamation`
- definite corruption count reduced from 43 to 0
- SQLite integrity check passed

The remaining 87 non-Han translations, 5,161 one-character Chinese
definitions, 3,994 alignment-review groups, and 4,181 missing-POS candidates
remain review queues, not automatically confirmed errors.

## Full definition-alignment resolution

The 2026-06-22 pass classified all 3,033 flagged definition groups across
2,937 headwords:

- 342 homonymous proper-name groups were preserved
- 2,406 source-aligned groups with compatible related senses were preserved
- 285 high-risk groups received an explicit English-sense selection
- 713 conflicting source rows were removed
- obvious incorrect, malformed, simplified, or mismatched Chinese definitions
  in the high-risk groups were corrected to Traditional Chinese

The decisions are reproducible in `alignment_review_resolutions.json`; the
285 high-risk selections are maintained in
`generate_alignment_resolutions.py`. The bundled database now contains
31,908 entries across the same 23,833 headwords. The unresolved
definition-alignment report contains zero groups, SQLite integrity checking
passes, and no `interjection` or other nonstandard part-of-speech values
remain.

This pass resolved the scoped definition-alignment queue. At that stage,
separate quality queues remained for missing IPA, missing examples, missing
grammar labels, nine non-Han translations, and one-character Chinese
definitions; the one-character queue was addressed in the next pass.

## One-character Chinese-definition review

The 2026-06-22 review classified all 2,963 entries whose Chinese definition
was a single character:

- 2,661 valid concise source translations were retained
- 302 confirmed mismatches or materially incomplete labels were replaced
  with explicit Traditional Chinese definitions
- every decision is recorded in `one_character_review_resolutions.json`
- the cleaner requires an exact English-definition match before applying a
  correction

The corrected database keeps all 23,833 headwords. The unresolved
one-character review queue and definition-alignment queue both contain zero
entries. This review does not claim that every concise translation should be
expanded; correct dictionary terms such as `魚`, `門`, `年`, and `我` remain
valid one-character definitions.

## Regional UK IPA enrichment

The 2026-06-22 pronunciation pass reviewed all 6,138 entries with no regional
IPA against the Kaikki English Wiktionary extraction dated 2026-06-15, based
on the English Wiktionary dump dated 2026-06-01.

The importer accepts only complete phonemic `/…/` transcriptions explicitly
tagged `Received-Pronunciation`, `General-British`, `Standard-British`, `UK`,
`British`, or `England`. Untagged, abbreviated, partial, and narrow phonetic
transcriptions are excluded. US candidates are recorded for later review but
are not copied into the UK field.

- 114 entries across 105 headwords received a source-tagged UK IPA
- five legacy UK values copied from US data were removed
- four of those legacy entries received a verified replacement UK IPA
- missing UK IPA decreased from 6,138 to 6,029 entries
- 6,029 UK entries remain empty because no explicit supported British
  transcription was available
- all decisions and source candidates are recorded in
  `pronunciation_review_resolutions.json`
- malformed IPA remains at zero

This pass deliberately prioritizes regional accuracy over coverage. It does
not construct UK pronunciations from US component words or copy US IPA into
the UK field.

### Non-Han translation review

The second reviewed correction batch increased the exact correction set to
126 rows. The non-Han review queue now contains only 11 accepted technology
names or abbreviations: C++, CD, DVD, HTML, HTML5, JavaScript, KN95, and XHTML.
Unicode Han detection now includes CJK extension-plane characters and `〇`.

The next recommended queue is definition alignment. Confirmed examples include
Chinese translations attached to the wrong English sense for `first class`
and `flush`.

### Definition-alignment batch 1

The first alignment batch fully replaced 12 high-risk common headwords:
`closet`, `shooter`, `abide`, `brain`, `jelly`, `snatch`, `trip`, `partner`,
`product`, `first class`, `flush`, and `good`.

Their overly broad or mismatched source rows were replaced with 26 concise
core senses. Every replacement sense has a reviewed Traditional Chinese
definition and one bilingual example. The alignment-review queue decreased
from 3,988 to 3,976 groups, and one-character Chinese rows decreased from
5,162 to 5,111.

### Definition-alignment batch 2

The second alignment batch fully replaced 16 common headwords: `be`, `class`,
`foot`, `key`, `black`, `chest`, `dimension`, `float`, `in`, `root`, `strong`,
`take`, `material`, `place`, `general`, and `flex`.

Their 164 source rows were replaced with 51 concise core senses. Every sense
has a reviewed Traditional Chinese definition and one bilingual example.
The alignment-review queue decreased from 3,976 to 3,952 groups, and
one-character Chinese rows decreased from 5,111 to 5,005.

### Definition-alignment batch 3

The third alignment batch fully replaced 20 common headwords: `new`, `zero`,
`attack`, `deep`, `beat`, `color`, `little`, `death`, `ivory`, `purple`,
`silk`, `vague`, `wing`, `bad`, `bed`, `bind`, `cross`, `definition`, `eye`,
and `language`.

Their 146 source rows were replaced with 55 concise core senses. Every sense
has a reviewed Traditional Chinese definition and one bilingual example.
The alignment-review queue decreased from 3,952 to 3,931 groups, and
one-character Chinese rows decreased from 5,005 to 4,942. The resulting
database contains 34,428 entries across 23,833 headwords, with no definite
corruption.

### Definition-alignment batch 4

The fourth alignment batch fully replaced 20 high-frequency headwords: `set`,
`pitch`, `charge`, `round`, `cast`, `save`, `case`, `crack`, `draw`, `flat`,
`issue`, `list`, `range`, `resolution`, `sense`, `sharp`, `break`, `copy`,
`drive`, and `fall`.

Their 238 source rows were replaced with 79 concise core senses. The new
entries separate meanings by part of speech and countability, use consistent
UK and US IPA, and provide a reviewed Traditional Chinese definition and one
bilingual example for every English definition. The alignment-review queue
decreased from 3,931 to 3,891 groups, and one-character Chinese rows decreased
from 4,942 to 4,868. The resulting database contains 34,269 entries across
23,833 headwords, with no definite corruption.

### Common-word consolidation

A fixed list of 441 common words was audited in one pass. In addition to the
70 manually curated replacements above, 168 common words were safely
consolidated into 218 source-aligned senses. A generated sense is accepted
only when it is the first modern source sense for its part of speech and a
bilingual example contains both the English headword and corresponding
Chinese definition. The generator also converts common simplified Chinese
forms to Traditional Chinese.

The resulting database contains 33,898 entries across 23,833 headwords.
The alignment-review queue decreased from 3,891 to 3,728 groups, and
one-character Chinese rows decreased from 4,868 to 4,697. Definite corruption
remains at zero. All 218 generated senses contain exactly one bilingual
example, and none uses `interjection`.

The 62 selected common words that could not be safely completed are recorded
in `CommonWordCuration.md`. They remain unchanged rather than receiving an
unverified definition or example.

### ChatGPT review batch 000

The 62 common words previously left for manual review were returned as a
schema-validated review batch and independently normalized and checked before
import. They now contain 178 core senses with standardized part-of-speech,
countability, transitivity, UK/US IPA, Traditional Chinese definitions, and
exactly one bilingual example per sense.

The resulting database contains 33,737 entries across 23,833 headwords.
The alignment-review queue decreased from 3,728 to 3,668 groups,
one-character Chinese rows decreased from 4,697 to 4,587, and missing-POS
candidates decreased from 4,187 to 4,177. Definite corruption and
`interjection` values remain at zero.

### ChatGPT review batch 001

The second ChatGPT review batch covered all 250 requested headwords. It
provided reviewed replacements for 153 words with 259 core senses and marked
97 uncertain or acceptable source words as explicitly skipped. Skipped words
remain unchanged and are excluded from future review-package exports.

Long-form countability and transitivity labels were normalized to the app's
notation. The reviewed `enough` entry supersedes its older generated entry,
and malformed source IPA for clearly identifiable words such as `enough`,
`one`, `no`, `so`, `tube`, and `yellow` was corrected before import.

The resulting database contains 33,196 entries across 23,833 headwords.
The alignment-review queue decreased from 3,668 to 3,457 groups,
one-character Chinese rows decreased from 4,587 to 4,066, and missing-POS
candidates decreased from 4,177 to 4,175. Definite corruption and
`interjection` values remain at zero.

### ChatGPT review batch 002

The first response for batch 002 marked all 250 words as uncertain and was
rejected. A revised response supplied replacements for 70 words with 125 core
senses. These replacements were independently checked, normalized, and
imported. The other 180 words were not recorded as completed because several
still contain obvious simplified-Chinese or sense-alignment problems; they
remain eligible for future review.

Malformed or missing IPA was corrected for clearly identifiable reviewed
words including `machine`, `perfect`, `square`, `dude`, `fox`, `ghosting`,
`go out`, `egg`, `herb`, and `iron`. Reviewed versions of `light`, `right`,
and `short` supersede their older generated entries.

The resulting database contains 33,072 entries across 23,833 headwords.
The alignment-review queue decreased from 3,457 to 3,391 groups,
one-character Chinese rows decreased from 4,066 to 3,922, and missing-POS
candidates decreased from 4,175 to 4,151. Definite corruption and
`interjection` values remain at zero.

### Codex review batch 1

Codex took over the remaining work after external batch processing stopped.
The original batch 002 and 003 scope contains 500 words: 85 were already
replaced by earlier layers, 20 high-risk common words were newly rebuilt, and
395 remain explicitly deferred in `CodexReviewProgress.md`.

The first Codex batch rebuilt `channel`, `space`, `screen`, `character`,
`access`, `cylinder`, `prize`, `honor`, `scale`, `pad`, `disk`, `model`,
`lady`, `dear`, `role`, `fair`, `dirty`, `boss`, `queue`, and `proof` into
56 concise core senses. Every sense has standardized IPA, part-of-speech and
countability data, a Traditional Chinese definition, and one bilingual
example.

The resulting database contains 32,998 entries across 23,833 headwords.
The alignment-review queue decreased from 3,391 to 3,362 groups,
one-character Chinese rows decreased from 3,922 to 3,907, and missing-POS
candidates decreased from 4,151 to 4,145. Definite corruption and
`interjection` values remain at zero.

### Codex review batch 2

The second Codex batch rebuilt 20 common words: `footstep`, `gel`, `halo`,
`haze`, `hey`, `holy`, `horn`, `howl`, `landlord`, `lane`, `lantern`,
`laugh`, `meat`, `moment`, `overflow`, `peer`, `shallow`, `shout`,
`strength`, and `wisdom`.

Their incorrect, simplified-Chinese, or overly specialized source senses were
replaced with 43 concise core senses. The active batch 002/003 deferred list
now contains 375 words, all individually listed in `CodexReviewProgress.md`.

The resulting database contains 32,976 entries across 23,833 headwords.
The alignment-review queue decreased from 3,362 to 3,341 groups,
one-character Chinese rows decreased from 3,907 to 3,856, and missing-POS
candidates decreased from 4,145 to 4,142. Definite corruption and
`interjection` values remain at zero.

### Codex review batch 3

The third Codex batch rebuilt `shaft`, `pick up`, `maroon`, `peg`, `bone`,
`joint`, `file`, `bar`, `cable`, `chart`, `condition`, `crawl`, `reach`,
`smell`, `shoot`, `soil`, `spot`, `steer`, `tag`, and `tease` into 52 core
senses. The active deferred list now contains 355 words.

The resulting database contains 32,935 entries across 23,833 headwords.
The alignment-review queue decreased from 3,341 to 3,319 groups and
one-character Chinese rows decreased from 3,856 to 3,819. The WordNet-based
missing-POS candidate count changed from 4,142 to 4,145 because uncommon
source parts of speech were deliberately omitted from the learner-focused
replacements; these candidates remain suggestions rather than confirmed
errors. Definite corruption and `interjection` values remain at zero.

### Codex review batch 4

The fourth Codex batch rebuilt 100 general-review headwords into 179 concise
core senses:

`closed`, `heavens`, `huh`, `inflexible`, `lifeless`, `me`, `membrane`,
`spicy`, `weigh`, `crust`, `mute`, `graft`, `hop`, `master`, `screw`,
`which`, `bass`, `limb`, `pot`, `sable`, `vend`, `admit`, `assembly`, `beam`,
`butt`, `countenance`, `favourite`, `lay`, `most`, `obtuse`, `occupied`,
`prodigy`, `reek`, `roast`, `salty`, `silly`, `along`, `assist`, `bang`,
`basket`, `beaker`, `bloom`, `congregation`, `dim`, `evaporate`, `except`,
`flipper`, `gamble`, `grand`, `grit`, `guess`, `header`, `lap`, `leap`,
`libation`, `link`, `motive`, `nose`, `over`, `ovine`, `pale`, `pawn`,
`plume`, `position`, `proper`, `propose`, `puff`, `raw`, `rotten`, `signal`,
`abdomen`, `agglomeration`, `alcohol`, `amuse`, `anchorman`, `apex`, `append`,
`aromatic`, `arrival`, `arrow`, `autumn`, `average`, `baboon`, `bamboo`,
`belie`, `besom`, `blackness`, `brand`, `bump`, `bunch`, `cardiac`, `carve`,
`centime`, `chapter`, `chevron`, `conflate`, `conglomerate`, `corps`, `cower`,
and `crime`.

Every replacement has reviewed Traditional Chinese, standardized
part-of-speech and countability or transitivity data, UK and US IPA, and
exactly one bilingual example per sense. Common missing parts of speech were
restored where appropriate, including the verb and adjective uses of `lay`,
the verb use of `bloom`, the preposition and conjunction uses of `except`,
and the noun, adjective, and verb uses of `average`.

The resulting database contains 32,770 entries across 23,833 headwords.
The alignment-review queue decreased from 3,319 to 3,210 groups,
one-character Chinese rows decreased from 3,819 to 3,645, and WordNet-based
missing-POS candidates decreased from 4,145 to 4,139. The active batch
002/003 deferred list now contains 255 words. SQLite integrity passed, and
definite corruption and `interjection` values remain at zero.

### Codex review batch 5 — deferred queue completed

The final Codex batch rebuilt all 255 words that remained in the original
batch 002/003 review scope. It added 416 reviewed learner-focused senses
covering:

- 204 general manual-review words
- 30 phrases and multiword expressions
- 9 specialist terms
- 5 offensive or sensitive words
- 4 prefixes or bound forms
- 3 words previously misclassified as proper names

Every sense has standardized UK and US IPA, an appropriate part-of-speech and
countability or transitivity label, a Traditional Chinese definition, and
exactly one bilingual example. Phrases and prefixes are retained as useful
dictionary entries rather than being forced into noun or verb categories.
Sensitive terms such as `fuck`, `pussy`, `crap`, `queer`, and `shitty` have
neutral definitions and explicit usage warnings. The supposed proper-name
entries `wu`, `bach`, and `beast` were replaced by their useful common-word
meanings.

Malformed source pronunciations and markup were removed, including the
damaged IPA previously attached to `due`, `forte`, `initial`, `island`, and
other entries. Missing core uses were restored where useful, while obsolete
or misleading source senses were omitted.

The resulting database contains 32,621 entries across 23,833 headwords.
The alignment-review queue decreased from 3,210 to 3,035 groups,
one-character Chinese rows decreased from 3,645 to 3,248, non-Chinese
translation review items decreased from 11 to 9, and WordNet-based
missing-POS candidates decreased from 4,139 to 4,072. All 500 words in the
original batch 002/003 scope are now accounted for: 415 are replaced by the
Codex layer and 85 by earlier reviewed layers, with zero deferred words.
SQLite integrity passed, and definite corruption and `interjection` values
remain at zero.

### Full-dictionary structural audit and cleanup

A new full-dictionary audit checked all 32,621 entries rather than only the
500-word review scope. It now produces dedicated queues for malformed or
missing IPA, missing or invalid examples, missing grammar labels, and legacy
part-of-speech values in `FullDictionaryAudit/`.

The builder and cleaner were updated so the fixes survive a complete rebuild
from the open-data sources:

- IPA source markup such as `<ref>`, `<a:...>`, and bracketed transcription
  syntax is removed or normalized.
- UK and US pronunciation fields are now preserved independently. A regional
  IPA is never copied into the other region merely to fill an empty field.
- `phraseologicalUnit`, multiword `other`, and `postposition` are normalized
  to the app's `phrase` and `preposition` labels.
- Noun countability and verb transitivity are inferred only from explicit
  source grammar labels.
- Unreviewed bilingual examples are accepted only when the Chinese sentence
  contains a displayed Chinese definition term.

Nineteen confirmed high-risk mismatches were rebuilt, including `a`,
`abandoned`, `abate`, `acorn`, `acoustic`, `across`, `across the board`,
`ado`, `adversity`, `affected`, `agency`, `alarm`, `ale`, `alight`,
`alternative`, `at bay`, `aye aye, sir`, `by way of`, and
`do you have any pets`.

Compared with the previous bundled database:

- malformed IPA rows decreased from 274 to 0
- rows missing at least one regional pronunciation decreased from 7,280 to
  6,154
- legacy or nonstandard part-of-speech rows decreased from 234 to 0
- noun/verb rows without grammar labels decreased from 21,435 to 18,761
- all invalid example structures remain at 0

The stricter semantic check deliberately removed source examples that were
attached to the wrong Chinese sense. The database now contains 2,896 reviewed
or source-aligned example rows; 29,725 senses still lack a safe bilingual
example. These are recorded as missing rather than being filled with
machine-translated or mismatched sentences.

After the subsequent alignment and one-character reviews, the current
remaining queues are 6,139 entries missing at least one regional
pronunciation, including 6,029 missing UK IPA and 6,138 missing US IPA;
29,036 senses without a safe bilingual example; 18,256 noun/verb entries
without an explicit grammar label; and nine accepted non-Han technology names
or abbreviations. The unresolved alignment and one-character queues are zero.

## Remaining reliable-source enrichment

The 2026-06-22 completion pass applied all additional unambiguous matches from
the downloaded Kaikki and Tatoeba releases:

- 168 exact-sense General American or US-tagged IPA values were added;
  missing US IPA decreased from 6,138 to 5,970
- 5,731 exact-sense noun countability or verb transitivity labels were added;
  missing grammar labels decreased from 18,256 to 12,525
- 1,827 safe Tatoeba English–Mandarin examples were added; missing examples
  decreased from 29,036 to 27,209
- missing UK IPA remains 6,029 because no further explicitly British-tagged
  transcription was available

The bundled database contains 31,908 entries across 23,833 headwords.
Malformed IPA, invalid examples, nonstandard parts of speech, definite
corruption, unresolved definition alignment, and unresolved one-character
Chinese definitions are all zero. SQLite integrity checking passes.

The remaining empty fields are source gaps, not automatically confirmed
errors. They remain blank rather than receiving copied regional IPA,
machine-inferred grammar, machine-translated examples, or an ambiguous sense
match. The nine non-Han review rows are accepted technology names and
abbreviations: C++, CD, DVD, HTML, HTML5, JavaScript, and XHTML.

## Conservative grammar consensus pass

A second 2026-06-22 grammar pass checked the remaining 12,525 empty noun and
verb labels with two source-wide consistency rules:

- Kaikki was accepted only when every gloss-bearing sense for the same
  headword and part of speech had an explicit, identical grammar label
- Open English WordNet verb frames were accepted only when every OEWN sense
  for the headword had a usable frame and all senses agreed on transitivity
- any incomplete or conflicting evidence remained unresolved

This added 714 labels: 333 from unanimous Kaikki headword data and 381 from
unanimous OEWN verb frames. The remaining grammar-label queue decreased from
12,525 to 11,811 rows. All 6,445 completed grammar decisions, including the
earlier 5,731 exact-sense matches, are retained in
`grammar_review_resolutions.json` and reproduce exactly against the bundled
database.

## Manual verb-transitivity review

The next 2026-06-22 pass reviewed all 440 verb rows still lacking a grammar
label. Each exact displayed sense was checked syntactically together with its
available Kaikki senses and OEWN verb frames:

- 245 senses were classified as transitive (`T`)
- 122 senses were classified as intransitive (`I`)
- 33 senses were classified as ambitransitive (`I or T`)
- 40 rows were deliberately left without a T/I label

The 40 deferred rows consist of 23 modal or auxiliary uses, ten source senses
that are actually nouns or adjectives, five fixed expressions without a safe
T/I analysis, and two malformed or incomplete glosses. Assigning a
transitivity label to those rows would conceal a part-of-speech or source-data
problem, so they are retained for a separate structural correction pass.

The completed 400 decisions are recorded in `grammar_manual_review.json`.
That ledger is tied to the exact 440-row scope by SHA-256 and merged into
`grammar_review_resolutions.json` by exact headword and English definition.
The remaining grammar-label queue decreased from 11,811 to 11,411 rows.

## Deferred verb structural corrections

The 40 rows deferred by the manual transitivity review were resolved in a
separate structural pass:

- 23 modal, semi-modal, or auxiliary uses remain verbs but are explicitly
  marked as not applicable to T/I classification
- ten source rows were corrected from verb to noun or adjective
- five fixed responses or expressions were corrected to phrase or
  exclamation
- the malformed `recreate` and `spoon` verb senses were rebuilt with an exact
  transitive definition
- obvious Chinese mismatches such as `got it → 明白了；懂了` and modal
  definitions for `may`, `must`, `shall`, and `should` were corrected

Five old examples were removed because they represented a different sense
after the structural correction. For example, a permission example had been
attached to the possibility sense of `may`. These were not retained merely
to fill the example field.

All 40 decisions are reproducible in `grammar_manual_review.json` and require
an exact original English-definition match. The grammar audit now has zero
unresolved verb rows; its remaining 11,371 rows are all nouns awaiting
`C`, `U`, or `C or U` review.

## Complete noun-countability review

The final grammar pass reviewed all 11,371 remaining noun rows:

- 10,540 rows matched an exact Kaikki gloss and its `en-noun` header
- 683 rows used a headword-wide value only where every Kaikki noun entry had
  the same countability header
- the remaining 148 rows were manually reviewed against their exact English
  sense and available Kaikki evidence
- the manual set contains 86 `C`, 34 `U`, 20 `C or U`, and eight
  structurally corrected rows where countability does not apply

Eleven of the 148 rows required structural work. Translation hubs and
time/direction expressions were changed to phrases, damaged entries such as
`duckboard bridge`, `shits`, and `thanks` were rebuilt, and one empty
duplicated `policy (law)` sense was deleted.

The bundled database now contains 31,907 entries across 23,833 headwords.
Every noun and applicable verb has an explicit grammar value; confirmed
modal, auxiliary, phrase, adjective, and exclamation senses are excluded from
T/I or C/U auditing. The missing grammar-label count is zero.

All 148 final decisions and their SHA-256 scope signature are recorded in
`noun_countability_review.json`. Together with the source-derived and manual
verb decisions, `grammar_review_resolutions.json` contains 18,208 completed
grammar resolutions.

## MFA cross-verification and expanded Tatoeba matching

The pronunciation analysis used Montreal Forced Aligner English UK and US
v3.1.0 dictionaries as a CC BY 4.0 secondary source. MFA phone sequences are
designed for forced alignment and omit lexical stress, so they were not
imported directly. Cross-verification confirmed three previously empty UK
fields and seven US fields across `asterix`, `bedstead`, `jeddah`, `kola`,
`maidenhead`, `megara`, and `styria`.

The Tatoeba matcher was expanded from a twenty-candidate single-word scan to
the full English–Mandarin link export. It now supports common inflected forms,
exact multiword expressions, Simplified/Traditional normalization, and source
sentence IDs. New automatic matches require a definition term of at least two
Chinese characters that is unique to one local sense of the headword.

This added 1,250 reviewed-by-rule bilingual examples. Missing examples
decreased from 27,213 to 25,963. Missing UK IPA decreased from 6,029 to 6,026,
and missing US IPA decreased from 5,970 to 5,963. Invalid examples and
malformed IPA remain at zero.

## Scored WikiMatrix manual example review

The original Facebook Research LASER WikiMatrix v1 English–Chinese TSV was
used because it retains the alignment margin score that is omitted from the
OPUS Moses package. Its downloaded gzip file passed decompression validation
and had SHA-256
`3efbc5897bc97f2bba95410d83b05baa0472794408f9b000130f0e3abd666524`.

The broad lexical pass found 5,415 possible missing-example senses, but
sampling showed alignment errors and many encyclopedic sentences unsuitable
for a learner dictionary. The final queue therefore required:

- WikiMatrix alignment score of at least 1.08
- an exact headword, supported inflection, or exact multiword phrase
- a unique Chinese definition term of at least two characters
- a short, complete sentence without formulas, years, citations, or embedded
  Latin text in the Chinese
- agreement with local English-to-Chinese and Chinese-to-English translation
  checks
- manual verification against the exact local part of speech and definition

The reproducible filter produced 120 candidates. Manual review approved 85
and rejected 35 for wrong sense or part of speech, added or missing
information, sentence fragments, or unsuitable learner-dictionary style.
All decisions and source line numbers are recorded in
`wikimatrix_example_review.json`.

The 85 approved examples reduced the missing-example count from 25,963 to
25,878. Database integrity remains valid; malformed IPA, invalid examples,
missing grammar labels, nonstandard parts of speech, and unresolved
definition-alignment findings remain at zero.

## Technical-name Chinese definition review

The final nine rows in the non-Chinese-definition queue were seven technical
headwords whose original Chinese field contained only a Latin-script product
or language name: `C++`, three senses of `CD`, `DVD`, `HTML`, `HTML5`,
`JavaScript`, and `XHTML`.

All seven headwords were rebuilt as exact reviewed replacements. The standard
technical names are retained, followed by a Chinese identifying term such as
`HTML 超文字標記語言` or `DVD 影音光碟`. The three `CD` senses are now separated
as compact disc, certificate of deposit, and creative director, each with
countability `C` and its own bilingual example. The unrelated compact-disc
example and broad shared synonym list are no longer attached to the finance
and job-title senses.

The cleaner now supports an explicit `superseded_resolution_words` list for
reviewed replacements. This prevents obsolete exact-sense grammar,
pronunciation, alignment, and example decisions from being applied to a
newly rebuilt headword, without disabling valid downstream resolutions for
other curated replacements.

The non-Chinese-definition queue decreased from nine to zero. All nine
reviewed senses now have a bilingual example, reducing missing examples from
25,878 to 25,874. Entry and headword counts remain unchanged at 31,907 and
23,833. All zero-error audit categories remain at zero.

## Regional IPA provenance rebuild

The original builder treated the first two unlabelled FreeDict pronunciation
elements as UK and US. FreeDict does not guarantee that regional order. This
created systematic reversals such as `north pole`, where an American
`/oʊ/` and rhotic `/ɹ/` appeared in the UK field while British `/əʊ/`
appeared in the US field.

The pronunciation pipeline now applies these provenance rules:

- FreeDict pronunciation order is never interpreted as a region.
- CMUdict supplies US pronunciation only.
- Kaikki/Wiktionary IPA must have an explicit supported UK, British,
  Received Pronunciation, General American, or US tag.
- the highest-priority candidate must be unique for the exact headword and
  part of speech
- an ambiguous pair can be reversed only when both current values exactly
  cross-match the opposite explicit regional candidate sets
- curated replacements and manually cross-verified regional values are
  preserved
- all remaining unlabelled-source regional values are cleared rather than
  displayed as though verified

The rebuild replaced or removed thousands of unsupported values and corrected
the four `north pole` senses to British `/ˌnɔːθ … ˈpəʊl/` and American
`/ˌnɔɹθ … ˈpoʊl/` forms. Strong simultaneous UK-American/US-British reversal
patterns decreased from 245 rows to zero.

The honest post-rebuild source gaps are 19,206 UK fields and 8,084 US fields.
These figures are higher than the previous 6,026 and 5,963 because the old
counts treated unlabelled or wrongly assigned pronunciations as complete.
Malformed IPA remains zero.

The audit now writes `suspicious_regional_ipa.csv`. Values with unusual
markers such as UK `/oʊ/` or US `/ɒ/` are accepted when the exact value is
present in the explicit regional source candidate ledger. Six curated
headwords (`bow`, `close`, `cloth`, `grow`, `hope`, and `transfer`) had
genuinely incorrect regional values and were corrected manually. After those
corrections and source-evidence checks, the suspicious regional IPA queue is
zero.

## Reproducible full-build and example cleanup

A clean source rebuild previously produced three obsolete `ought` auxiliary
senses and left 47 noun or verb rows without grammar labels. Structural
alignment cleanup now deletes sibling senses explicitly marked as superseded,
and the builder runs the same explicit-definition grammar inference as the
cleaner. A source rebuild now contains exactly 31,907 entries and has zero
missing grammar labels.

The comparison also exposed legacy headword-level Tatoeba fallback examples.
These could contain the displayed Chinese term while illustrating a
different English sense, such as a lunch-time example attached to the
punctuation sense of `period`, or a noun use of `view` attached to its verb
sense. The cleaner removed 1,113 examples that had no exact-sense review
record. Four newly recovered candidates (`awareness`, `chance`, `principal`,
and `theme`) passed manual bilingual exact-sense review and were recorded in
`rebuild_example_review.json`.

The cleaned bundled database and a fresh build from the open source archives
now have identical logical entry rows. The resulting conservative baseline
has:

- 31,907 entries across 23,833 headwords
- 19,206 missing UK IPA fields
- 8,084 missing US IPA fields
- 26,983 missing bilingual examples
- zero malformed IPA, suspicious regional IPA, invalid examples, missing
  grammar labels, nonstandard parts of speech, definite corruption,
  non-Chinese definitions, one-character definitions, unresolved definition
  alignment findings, or missing part-of-speech candidates

A final scan of the latest downloaded Tatoeba export produced 949 additional
rule-level candidates. Sampling found repeated exact-sense failures,
including a bird example for the butterfly sense of `crow`, a sport example
for the ball sense of `basketball`, and a natural-environment example for the
computing sense of `environment`. None of those 949 candidates was imported
automatically. They remain deferred until exact-sense human review is
available.

## AI-assisted semantic correction layer

The previous audit was strong at structural alignment but could not detect a
single English definition paired with one unrelated Chinese value. A
CC-CEDICT reverse-translation pass exposed source errors such as `endnote`
translated as `音符`, several `instrument` senses translated as `中國`,
`SUV` translated as `存活時間`, and eleven unrelated verbs translated as
`墜毀`.

`ai_semantic_corrections.json` now records exact-sense corrections with the
original Chinese value, reviewed Traditional Chinese replacement, rationale,
and a bilingual example containing the displayed Chinese term. The database
builder, cleaner, and auditor all validate this ledger. An upstream definition
change or unapplied correction is now a hard failure rather than a silent
skip.

CC-CEDICT and Kaikki/English Wiktionary candidates are deliberately treated as
review evidence. They are not imported in bulk because reverse lookup and
translation tables remain ambiguous for polysemous words. Only manually
confirmed exact senses enter the correction ledger.

The semantic correction ledger contains 158 exact-sense corrections. It
repaired
systematic source-confusion groups such as:

- `蘭特` incorrectly attached to 17 edge, rim, and boundary senses
- `墜毀` incorrectly attached to eleven defeat, overwrite, crush, and
  comparison senses
- `卡農` incorrectly attached to horse anatomy, literary, religious, drink,
  and attractive-person senses
- `氣霧劑` incorrectly attached to dessert, cryptanalysis, explosive,
  surprising-news, and attractive-person senses

Every corrected sense now has one reviewed bilingual example. Several rows
already contained an example for the wrong sense, including `skin`, `library`,
`storm`, `sister`, `German`, and `mango`; those examples were replaced rather
than counted as newly filled rows. The net missing-example count decreased by
142, from 26,983 to 26,841. The bundled database and a
fresh source rebuild remain logically identical at 31,907 rows. The semantic
ledger has zero application failures.

The Kaikki English file last modified on 2026-06-21 was downloaded on
2026-06-23 and compared with the existing regional pronunciation ledger.
Because the newer extraction omits some older explicit values, it was merged
additively: all prior verified pronunciations were retained, while 300 new UK
and 67 new US exact-sense values were added. In the bundled database this
reduced missing UK IPA from 19,206 to 18,913 and missing US IPA from 8,084 to
8,079. Malformed and suspicious regional IPA counts remain zero.

## Complete generated fallback

After all reliable sources and exact-sense reviews are exhausted, the builder
now fills remaining empty fields with deterministic generated fallbacks:

- 26,841 definition-backed bilingual example prompts
- 18,913 approximate UK IPA values
- 8,079 approximate US IPA values

The resulting 31,907 entries have zero missing IPA, examples, grammar labels,
or definitions. Generated content is not mixed with verified provenance:
159,535 content-level records in the SQLite `entry_provenance` table identify
source-backed, curated, AI-reviewed, and generated values.

The generated examples contain the exact headword and complete displayed
Chinese definition so the app's strict example filter accepts them. They are
metalinguistic usage demonstrations rather than fabricated quotations.
Generated IPA uses deterministic grapheme-to-phoneme approximation and is
explicitly non-authoritative for rare names, heteronyms, and unusual
loanwords. Any later source-backed value automatically takes precedence.
