import Foundation

struct DictionaryAPIEntry: Decodable {
    let word: String
    let phonetic: String?
    let phonetics: [DictionaryAPIPhonetic]
    let meanings: [DictionaryAPIMeaning]
}

struct DictionaryAPIPhonetic: Decodable {
    let text: String?
    let audio: String?
}

struct DictionaryAPIMeaning: Decodable {
    let partOfSpeech: String
    let definitions: [DictionaryAPIDefinition]
    let synonyms: [String]
    let antonyms: [String]
}

struct DictionaryAPIDefinition: Decodable {
    let definition: String
    let example: String?
    let synonyms: [String]
    let antonyms: [String]
}

struct DictionaryAPIErrorResponse: Decodable {
    let title: String?
    let message: String?
    let resolution: String?
}
