import Foundation

actor TranslationCache {
    static let shared = TranslationCache()

    private var translations: [String: String] = [:]

    private init() {}

    func translation(for sourceText: String) -> String? {
        translations[sourceText]
    }

    func store(_ translatedText: String, for sourceText: String) {
        translations[sourceText] = translatedText
    }
}
