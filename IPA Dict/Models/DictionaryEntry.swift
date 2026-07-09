import Foundation

struct DictionaryEntry: Identifiable, Hashable, Sendable {
    let id: UUID
    let word: String
    let ukIPA: String
    let usIPA: String
    let ukAudioURL: URL?
    let usAudioURL: URL?
    let partOfSpeech: String
    let countability: String
    let inflections: [String]
    let zhDefinition: String
    let enDefinition: String
    let examples: [DictionaryExample]
    let synonyms: [String]
    let antonyms: [String]

    nonisolated init(
        id: UUID = UUID(),
        word: String,
        ukIPA: String,
        usIPA: String,
        ukAudioURL: URL? = nil,
        usAudioURL: URL? = nil,
        partOfSpeech: String,
        countability: String,
        inflections: [String] = [],
        zhDefinition: String,
        enDefinition: String,
        examples: [DictionaryExample],
        synonyms: [String] = [],
        antonyms: [String] = []
    ) {
        self.id = id
        self.word = word
        self.ukIPA = ukIPA
        self.usIPA = usIPA
        self.ukAudioURL = ukAudioURL
        self.usAudioURL = usAudioURL
        self.partOfSpeech = Self.normalizedPartOfSpeech(partOfSpeech)
        self.countability = countability
        self.inflections = inflections
        self.zhDefinition = zhDefinition
        self.enDefinition = enDefinition
        self.examples = examples
        self.synonyms = synonyms
        self.antonyms = antonyms
    }
}

struct DictionaryExample: Identifiable, Hashable, Codable, Sendable {
    let id: UUID
    let english: String
    let chinese: String

    nonisolated init(id: UUID = UUID(), english: String, chinese: String) {
        self.id = id
        self.english = english
        self.chinese = chinese
    }
}

extension DictionaryEntry {
    nonisolated static func normalizedPartOfSpeech(_ value: String) -> String {
        switch value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "interjection":
            return "exclamation"
        default:
            return value
        }
    }

    func translated(
        definition: String,
        examples translatedExamples: [String]
    ) -> DictionaryEntry {
        DictionaryEntry(
            id: id,
            word: word,
            ukIPA: ukIPA,
            usIPA: usIPA,
            ukAudioURL: ukAudioURL,
            usAudioURL: usAudioURL,
            partOfSpeech: partOfSpeech,
            countability: countability,
            inflections: inflections,
            zhDefinition: definition,
            enDefinition: enDefinition,
            examples: zip(examples, translatedExamples).map { example, translation in
                DictionaryExample(
                    id: example.id,
                    english: example.english,
                    chinese: translation
                )
            },
            synonyms: synonyms,
            antonyms: antonyms
        )
    }

    static let apple = DictionaryEntry(
        word: "apple",
        ukIPA: "/ˈæp.əl/",
        usIPA: "/ˈæp.əl/",
        partOfSpeech: "noun",
        countability: "C or U",
        zhDefinition: "蘋果",
        enDefinition: "A round fruit with firm, white flesh and a green, red, or yellow skin.",
        examples: [
            DictionaryExample(
                english: "An apple a day keeps the doctor away.",
                chinese: "每日一蘋果，醫生遠離我。"
            )
        ]
    )

    static let programNoun = DictionaryEntry(
        word: "program",
        ukIPA: "/ˈprəʊ.ɡræm/",
        usIPA: "/ˈproʊ.ɡræm/",
        partOfSpeech: "noun",
        countability: "C",
        zhDefinition: "（電腦）程式；編碼指令",
        enDefinition: "a series of instructions that can be put into a computer in order to make it perform an operation",
        examples: [
            DictionaryExample(
                english: "She's written a program to find words that frequently occur together.",
                chinese: "她設計了一個程式以便找到經常一起出現的詞語。"
            )
        ]
    )

    static let programVerb = DictionaryEntry(
        word: "program",
        ukIPA: "/ˈprəʊ.ɡræm/",
        usIPA: "/ˈproʊ.ɡræm/",
        partOfSpeech: "verb",
        countability: "T",
        zhDefinition: "為（電腦）程式設計；編制…的程式",
        enDefinition: "to write a series of instructions that make a computer perform a particular operation",
        examples: [
            DictionaryExample(
                english: "She programmed the computer to calculate the rate of exchange in twelve currencies.",
                chinese: "她為電腦編制了一套計算12種貨幣之間兌換率的程式。"
            )
        ]
    )

    static let findVerb = DictionaryEntry(
        word: "find",
        ukIPA: "/faɪnd/",
        usIPA: "/faɪnd/",
        partOfSpeech: "verb",
        countability: "",
        inflections: ["found", "found"],
        zhDefinition: "（偶然）發現，碰上；找到，尋得；找出，查明",
        enDefinition: "to discover, especially where a thing or person is, either unexpectedly or by searching, or to discover where to get or how to achieve something",
        examples: [
            DictionaryExample(
                english: "I've just found a ten-pound note in my pocket.",
                chinese: "我剛在口袋裡找到了一張十英鎊的鈔票。"
            )
        ]
    )

    static let findNoun = DictionaryEntry(
        word: "find",
        ukIPA: "/faɪnd/",
        usIPA: "/faɪnd/",
        partOfSpeech: "noun",
        countability: "C",
        zhDefinition: "發現物；被發現的人（尤指有價值或有用者）",
        enDefinition: "a good or valuable thing or a special person that has been discovered but was not known about before",
        examples: [
            DictionaryExample(
                english: "A recent find of ancient artefacts is on display at the local museum.",
                chinese: "近期發現的一些文物正在當地的博物館展出。"
            )
        ]
    )

    static let testNoun = DictionaryEntry(
        word: "test",
        ukIPA: "/test/",
        usIPA: "/test/",
        partOfSpeech: "noun",
        countability: "C",
        zhDefinition: "測驗，考查",
        enDefinition: "a way of discovering, by questions or practical activities, what someone knows, or what someone or something can do or is like",
        examples: [
            DictionaryExample(
                english: "She had to take/do an aptitude test before she got the job.",
                chinese: "她先接受了能力測試後才得到這份工作。"
            )
        ]
    )

    static let testVerb = DictionaryEntry(
        word: "test",
        ukIPA: "/test/",
        usIPA: "/test/",
        partOfSpeech: "verb",
        countability: "",
        zhDefinition: "試驗；檢驗；試用；檢測",
        enDefinition: "to put something through a process in order to discover if it is safe, works correctly, etc., or if something is present in it",
        examples: [
            DictionaryExample(
                english: "The manufacturers are currently testing the new engine.",
                chinese: "生產廠家目前正試驗這種新的引擎。"
            )
        ]
    )

    static let yesAdverb = DictionaryEntry(
        word: "yes",
        ukIPA: "/jes/",
        usIPA: "/jes/",
        partOfSpeech: "adverb",
        countability: "",
        zhDefinition: "是，對；好的",
        enDefinition: "used to give an affirmative answer or to show agreement, acceptance, or willingness",
        examples: [
            DictionaryExample(
                english: "“Are you coming?” “Yes, I am.”",
                chinese: "「你會來嗎？」「是的，我會來。」"
            )
        ]
    )

    static let yesNoun = DictionaryEntry(
        word: "yes",
        ukIPA: "/jes/",
        usIPA: "/jes/",
        partOfSpeech: "noun",
        countability: "C",
        zhDefinition: "肯定的回答；同意",
        enDefinition: "an answer or decision that shows agreement or acceptance",
        examples: [
            DictionaryExample(
                english: "We need a definite yes by Friday.",
                chinese: "我們需要你在星期五前給予明確的肯定答覆。"
            )
        ]
    )

    static let itinerary = DictionaryEntry(
        word: "itinerary",
        ukIPA: "/aɪˈtɪn.ər.ər.i/",
        usIPA: "/aɪˈtɪn.ə.rer.i/",
        partOfSpeech: "noun",
        countability: "C",
        zhDefinition: "旅行計劃，預定行程",
        enDefinition: "a detailed plan or route of a journey",
        examples: [
            DictionaryExample(
                english: "The tour operator will arrange transport and plan your itinerary.",
                chinese: "旅行社工作人員將負責安排交通和行程計劃。"
            )
        ]
    )

    static func makeEntries(from apiEntry: DictionaryAPIEntry) -> [DictionaryEntry] {
        let ukPhonetic = bestPhonetic(in: apiEntry.phonetics, marker: "-uk")
        let usPhonetic = bestPhonetic(in: apiEntry.phonetics, marker: "-us")
        let fallbackIPA = apiEntry.phonetic
            ?? apiEntry.phonetics.compactMap(\.text).first
            ?? ""

        return apiEntry.meanings.flatMap { meaning in
            meaning.definitions.map { definition in
                let synonyms = uniqueWords(
                    meaning.synonyms + definition.synonyms
                )
                let antonyms = uniqueWords(
                    meaning.antonyms + definition.antonyms
                )

                return DictionaryEntry(
                    word: apiEntry.word,
                    ukIPA: ukPhonetic.text ?? fallbackIPA,
                    usIPA: usPhonetic.text ?? fallbackIPA,
                    ukAudioURL: audioURL(from: ukPhonetic.audio),
                    usAudioURL: audioURL(from: usPhonetic.audio),
                    partOfSpeech: normalizedPartOfSpeech(meaning.partOfSpeech),
                    countability: "",
                    inflections: [],
                    zhDefinition: "",
                    enDefinition: definition.definition,
                    examples: definition.example.map {
                        [DictionaryExample(english: $0, chinese: "")]
                    } ?? [],
                    synonyms: synonyms,
                    antonyms: antonyms
                )
            }
        }
    }

    private static func bestPhonetic(
        in phonetics: [DictionaryAPIPhonetic],
        marker: String
    ) -> DictionaryAPIPhonetic {
        phonetics.first {
            ($0.audio ?? "").lowercased().contains(marker)
        } ?? phonetics.first {
            !($0.audio ?? "").isEmpty
        } ?? phonetics.first ?? DictionaryAPIPhonetic(text: nil, audio: nil)
    }

    private static func audioURL(from path: String?) -> URL? {
        guard let path, !path.isEmpty else { return nil }
        if path.hasPrefix("//") {
            return URL(string: "https:\(path)")
        }
        return URL(string: path)
    }

    private static func uniqueWords(_ words: [String]) -> [String] {
        var seen = Set<String>()
        return words.filter { seen.insert($0.lowercased()).inserted }
    }
}
