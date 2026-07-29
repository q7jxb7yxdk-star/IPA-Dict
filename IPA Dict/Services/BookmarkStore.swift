import Combine
import Foundation

@MainActor
final class BookmarkStore: ObservableObject {
    @Published private(set) var words: [String]

    private let cloudStore: NSUbiquitousKeyValueStore
    private let storageKey = "dictionaryBookmarks"
    private var cloudChangeTask: Task<Void, Never>?

    init(cloudStore: NSUbiquitousKeyValueStore = .default) {
        self.cloudStore = cloudStore
        self.words = cloudStore.array(forKey: storageKey) as? [String] ?? []

        words = unique(words)
        cloudStore.synchronize()
        applyCloudValue()
        cloudChangeTask = Task { [weak self] in
            for await _ in NotificationCenter.default.notifications(
                named: NSUbiquitousKeyValueStore.didChangeExternallyNotification,
                object: nil
            ) {
                guard !Task.isCancelled else { return }
                self?.applyCloudValue()
            }
        }
    }

    deinit {
        cloudChangeTask?.cancel()
    }

    func contains(_ rawWord: String) -> Bool {
        let word = normalizedWord(rawWord)
        return !word.isEmpty && words.contains {
            $0.caseInsensitiveCompare(word) == .orderedSame
        }
    }

    func toggle(_ rawWord: String) {
        contains(rawWord) ? remove(rawWord) : add(rawWord)
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
        save()
    }

    private func applyCloudValue() {
        words = unique(cloudStore.array(forKey: storageKey) as? [String] ?? [])
    }

    private func save() {
        cloudStore.set(words, forKey: storageKey)
        cloudStore.synchronize()
    }

    private func unique(_ values: [String]) -> [String] {
        var seen = Set<String>()
        return values.map(normalizedWord).filter {
            !$0.isEmpty && seen.insert($0).inserted
        }
    }

    private func normalizedWord(_ rawWord: String) -> String {
        rawWord.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
