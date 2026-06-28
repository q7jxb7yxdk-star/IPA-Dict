import Foundation

struct PersonalDictionaryEntry: Identifiable, Hashable, Sendable {
    let id: Int64
    let word: String
    let normalizedWord: String
    let ukIPA: String
    let usIPA: String
    let sourceNote: String
    let sourceURL: String
    let senses: [PersonalDictionarySense]
    let createdAt: Date
    let updatedAt: Date
}

struct PersonalDictionarySense: Identifiable, Hashable, Sendable {
    let id: Int64
    let displayOrder: Int
    let partOfSpeech: String
    let countability: String
    let zhDefinition: String
    let enDefinition: String
    let exampleEnglish: String
    let exampleChinese: String
}

struct EditablePersonalDictionaryEntry: Identifiable, Hashable {
    var id = UUID()
    var word: String
    var ukIPA: String
    var usIPA: String
    var sourceNote: String
    var sourceURL: String
    var senses: [EditablePersonalDictionarySense]

    nonisolated init(
        word: String,
        ukIPA: String,
        usIPA: String,
        sourceNote: String = "",
        sourceURL: String = "",
        senses: [EditablePersonalDictionarySense]
    ) {
        self.word = word
        self.ukIPA = ukIPA
        self.usIPA = usIPA
        self.sourceNote = sourceNote
        self.sourceURL = sourceURL
        self.senses = senses.isEmpty
            ? [EditablePersonalDictionarySense()]
            : senses
    }
}

struct EditablePersonalDictionarySense: Identifiable, Hashable {
    var id = UUID()
    var partOfSpeechLine: String
    var zhDefinition: String
    var enDefinition: String
    var exampleEnglish: String
    var exampleChinese: String

    nonisolated init(
        partOfSpeechLine: String = "",
        zhDefinition: String = "",
        enDefinition: String = "",
        exampleEnglish: String = "",
        exampleChinese: String = ""
    ) {
        self.partOfSpeechLine = partOfSpeechLine
        self.zhDefinition = zhDefinition
        self.enDefinition = enDefinition
        self.exampleEnglish = exampleEnglish
        self.exampleChinese = exampleChinese
    }
}

extension EditablePersonalDictionaryEntry {
    nonisolated init(entries: [DictionaryEntry]) {
        let primary = entries.first
        self.init(
            word: primary?.word ?? "",
            ukIPA: primary?.ukIPA ?? "",
            usIPA: primary?.usIPA ?? "",
            senses: entries.map { entry in
                EditablePersonalDictionarySense(
                    partOfSpeechLine: Self.partOfSpeechLine(for: entry),
                    zhDefinition: entry.zhDefinition,
                    enDefinition: entry.enDefinition,
                    exampleEnglish: entry.examples.first?.english ?? "",
                    exampleChinese: entry.examples.first?.chinese ?? ""
                )
            }
        )
    }

    nonisolated init(personalEntry: PersonalDictionaryEntry) {
        self.init(
            word: personalEntry.word,
            ukIPA: personalEntry.ukIPA,
            usIPA: personalEntry.usIPA,
            sourceNote: personalEntry.sourceNote,
            sourceURL: personalEntry.sourceURL,
            senses: personalEntry.senses.sorted { lhs, rhs in
                lhs.displayOrder < rhs.displayOrder
            }.map { sense in
                EditablePersonalDictionarySense(
                    partOfSpeechLine: Self.partOfSpeechLine(
                        partOfSpeech: sense.partOfSpeech,
                        countability: sense.countability
                    ),
                    zhDefinition: sense.zhDefinition,
                    enDefinition: sense.enDefinition,
                    exampleEnglish: sense.exampleEnglish,
                    exampleChinese: sense.exampleChinese
                )
            }
        )
    }

    nonisolated func dictionaryEntries(
        markedAsPersonal: Bool = true
    ) -> [DictionaryEntry] {
        let normalizedWord = word.trimmingCharacters(in: .whitespacesAndNewlines)

        return senses.enumerated().map { _, sense in
            let parsed = Self.parsePartOfSpeechLine(sense.partOfSpeechLine)
            let examples: [DictionaryExample]
            if sense.exampleEnglish.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
               sense.exampleChinese.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                examples = []
            } else {
                examples = [
                    DictionaryExample(
                        english: sense.exampleEnglish,
                        chinese: sense.exampleChinese
                    )
                ]
            }

            return DictionaryEntry(
                word: normalizedWord,
                ukIPA: ukIPA,
                usIPA: usIPA,
                partOfSpeech: parsed.partOfSpeech,
                countability: parsed.countability,
                zhDefinition: sense.zhDefinition,
                enDefinition: sense.enDefinition,
                examples: examples,
                isPersonal: markedAsPersonal
            )
        }
    }

    nonisolated static func normalizedWord(_ value: String) -> String {
        value
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .split(whereSeparator: \.isWhitespace)
            .joined(separator: " ")
    }

    nonisolated static func partOfSpeechLine(for entry: DictionaryEntry) -> String {
        partOfSpeechLine(
            partOfSpeech: entry.partOfSpeech,
            countability: entry.countability
        )
    }

    nonisolated static func partOfSpeechLine(
        partOfSpeech: String,
        countability: String
    ) -> String {
        let part = partOfSpeech.trimmingCharacters(in: .whitespacesAndNewlines)
        let grammar = countability.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !grammar.isEmpty else { return part }
        return "\(part) [ \(grammar) ]"
    }

    nonisolated static func parsePartOfSpeechLine(
        _ value: String
    ) -> (partOfSpeech: String, countability: String) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let open = trimmed.lastIndex(of: "["),
              let close = trimmed.lastIndex(of: "]"),
              open < close else {
            return (trimmed, "")
        }

        let part = trimmed[..<open]
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let grammarStart = trimmed.index(after: open)
        let grammar = trimmed[grammarStart..<close]
            .trimmingCharacters(in: .whitespacesAndNewlines)

        return (String(part), String(grammar))
    }
}
