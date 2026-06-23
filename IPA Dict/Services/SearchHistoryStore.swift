import Combine
import Foundation

@MainActor
final class SearchHistoryStore: ObservableObject {
    @Published private(set) var words: [String]

    private let defaults: UserDefaults
    private let storageKey = "dictionarySearchHistory"
    private let maximumCount = 20

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.words = defaults.stringArray(forKey: storageKey) ?? []
    }

    func add(_ rawWord: String) {
        let word = rawWord
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        guard !word.isEmpty else { return }

        words.removeAll { $0.caseInsensitiveCompare(word) == .orderedSame }
        words.insert(word, at: 0)
        words = Array(words.prefix(maximumCount))
        save()
    }

    func clear() {
        words = []
        defaults.removeObject(forKey: storageKey)
    }

    private func save() {
        defaults.set(words, forKey: storageKey)
    }
}
