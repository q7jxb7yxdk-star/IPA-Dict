import Combine
import Foundation

@MainActor
final class SearchHistoryStore: ObservableObject {
    @Published private(set) var words: [String]

    private let cloudStore: NSUbiquitousKeyValueStore
    private let storageKey = "dictionarySearchHistory"
    private let maximumCount = 20
    private var cloudChangeTask: Task<Void, Never>?

    init(cloudStore: NSUbiquitousKeyValueStore = .default) {
        self.cloudStore = cloudStore
        self.words = cloudStore.array(forKey: storageKey) as? [String] ?? []

        words = Array(unique(words).prefix(maximumCount))
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

    func add(_ rawWord: String) {
        let word = normalizedWord(rawWord)
        guard !word.isEmpty else { return }
        words.removeAll { $0.caseInsensitiveCompare(word) == .orderedSame }
        words.insert(word, at: 0)
        words = Array(words.prefix(maximumCount))
        save()
    }

    func clear() {
        words = []
        save()
    }

    func remove(_ rawWord: String) {
        let originalCount = words.count
        words.removeAll { $0.caseInsensitiveCompare(rawWord) == .orderedSame }
        guard words.count != originalCount else { return }
        save()
    }

    private func applyCloudValue() {
        words = Array(
            unique(cloudStore.array(forKey: storageKey) as? [String] ?? [])
                .prefix(maximumCount)
        )
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
