import Foundation

enum CuratedDictionary {
    private static let entries: [String: [DictionaryEntry]] = [
        "apple": [.apple],
        "program": [.programNoun, .programVerb],
        "find": [.findVerb, .findNoun],
        "test": [.testNoun, .testVerb],
        "yes": [.yesAdverb, .yesNoun]
    ]

    private static let fullyReplacedWords: Set<String> = ["yes"]

    static func entries(for word: String) -> [DictionaryEntry]? {
        entries[word.lowercased()]
    }

    static func merge(
        curatedEntries: [DictionaryEntry],
        apiEntries: [DictionaryEntry]
    ) -> [DictionaryEntry] {
        let normalizedWord = curatedEntries.first?.word.lowercased() ?? ""
        let enrichedCurated = curatedEntries.map { curated in
            let matchingAPIEntry = apiEntries.first {
                DictionaryEntry.normalizedPartOfSpeech($0.partOfSpeech)
                    .caseInsensitiveCompare(
                        DictionaryEntry.normalizedPartOfSpeech(
                            curated.partOfSpeech
                        )
                    )
                    == .orderedSame
            }

            return DictionaryEntry(
                word: curated.word,
                ukIPA: curated.ukIPA.isEmpty
                    ? matchingAPIEntry?.ukIPA ?? ""
                    : curated.ukIPA,
                usIPA: curated.usIPA.isEmpty
                    ? matchingAPIEntry?.usIPA ?? ""
                    : curated.usIPA,
                ukAudioURL: matchingAPIEntry?.ukAudioURL,
                usAudioURL: matchingAPIEntry?.usAudioURL,
                partOfSpeech: curated.partOfSpeech,
                countability: curated.countability,
                inflections: curated.inflections,
                zhDefinition: curated.zhDefinition,
                enDefinition: curated.enDefinition,
                examples: curated.examples,
                synonyms: matchingAPIEntry?.synonyms ?? curated.synonyms,
                antonyms: matchingAPIEntry?.antonyms ?? curated.antonyms
            )
        }

        let curatedPartsOfSpeech = Set(
            curatedEntries.map {
                DictionaryEntry.normalizedPartOfSpeech($0.partOfSpeech)
                    .lowercased()
            }
        )
        let additionalEntries = fullyReplacedWords.contains(normalizedWord)
            ? []
            : apiEntries.filter {
                !curatedPartsOfSpeech.contains(
                    DictionaryEntry.normalizedPartOfSpeech($0.partOfSpeech)
                        .lowercased()
                )
            }

        return enrichedCurated + additionalEntries
    }
}
