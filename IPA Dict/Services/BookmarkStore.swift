import Combine
import Foundation

@MainActor
final class BookmarkStore: ObservableObject {
    @Published private(set) var words: [String]

    private let defaults: UserDefaults
    private let storageKey = "dictionaryBookmarks"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.words = defaults.stringArray(forKey: storageKey) ?? []
    }

    func contains(_ rawWord: String) -> Bool {
        let word = normalizedWord(rawWord)
        guard !word.isEmpty else { return false }
        return words.contains { $0.caseInsensitiveCompare(word) == .orderedSame }
    }

    func toggle(_ rawWord: String) {
        if contains(rawWord) {
            remove(rawWord)
        } else {
            add(rawWord)
        }
    }

    func add(_ rawWord: String) {
        let word = normalizedWord(rawWord)
        guard !word.isEmpty else { return }

        words.removeAll { $0.caseInsensitiveCompare(word) == .orderedSame }
        words.insert(word, at: 0)
        save()
    }

    func remove(_ rawWord: String) {
        let word = normalizedWord(rawWord)
        guard !word.isEmpty else { return }

        words.removeAll { $0.caseInsensitiveCompare(word) == .orderedSame }
        save()
    }

    func clear() {
        words = []
        defaults.removeObject(forKey: storageKey)
    }

    private func normalizedWord(_ rawWord: String) -> String {
        rawWord
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
    }

    private func save() {
        defaults.set(words, forKey: storageKey)
    }
}
