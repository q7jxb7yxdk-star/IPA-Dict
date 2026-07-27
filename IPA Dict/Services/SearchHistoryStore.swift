import Combine
import Foundation

@MainActor
final class SearchHistoryStore: ObservableObject {
    @Published private(set) var words: [String]

    private let defaults: UserDefaults
    private let cloudStore: NSUbiquitousKeyValueStore
    private let storageKey = "dictionarySearchHistory"
    private let modifiedKey = "dictionarySearchHistoryModifiedAt"
    private let maximumCount = 20
    private var cloudChangeTask: Task<Void, Never>?

    init(
        defaults: UserDefaults = .standard,
        cloudStore: NSUbiquitousKeyValueStore = .default
    ) {
        self.defaults = defaults
        self.cloudStore = cloudStore
        self.words = defaults.stringArray(forKey: storageKey) ?? []

        synchronizeInitialData()
        cloudChangeTask = Task { [weak self] in
            for await _ in NotificationCenter.default.notifications(
                named: NSUbiquitousKeyValueStore.didChangeExternallyNotification,
                object: nil
            ) {
                guard !Task.isCancelled else { return }
                self?.applyNewerCloudValue()
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
        saveAndSync()
    }

    func clear() {
        words = []
        saveAndSync()
    }

    func remove(_ rawWord: String) {
        let originalCount = words.count
        words.removeAll { $0.caseInsensitiveCompare(rawWord) == .orderedSame }
        guard words.count != originalCount else { return }
        saveAndSync()
    }

    private func synchronizeInitialData() {
        cloudStore.synchronize()
        let localModified = defaults.double(forKey: modifiedKey)
        let cloudModified = cloudStore.double(forKey: modifiedKey)
        let cloudWords = cloudStore.array(forKey: storageKey) as? [String]

        guard let cloudWords else {
            saveAndSync()
            return
        }

        if localModified == 0 {
            words = Array(unique(words + cloudWords).prefix(maximumCount))
            saveAndSync()
        } else if cloudModified > localModified {
            applyCloud(words: cloudWords, modifiedAt: cloudModified)
        } else if localModified > cloudModified {
            publish(words: words, modifiedAt: localModified)
        }
    }

    private func applyNewerCloudValue() {
        let cloudModified = cloudStore.double(forKey: modifiedKey)
        guard cloudModified > defaults.double(forKey: modifiedKey),
              let cloudWords = cloudStore.array(forKey: storageKey) as? [String]
        else { return }
        applyCloud(words: cloudWords, modifiedAt: cloudModified)
    }

    private func applyCloud(words: [String], modifiedAt: Double) {
        self.words = Array(unique(words).prefix(maximumCount))
        defaults.set(self.words, forKey: storageKey)
        defaults.set(modifiedAt, forKey: modifiedKey)
    }

    private func saveAndSync() {
        let modifiedAt = Date().timeIntervalSince1970
        defaults.set(words, forKey: storageKey)
        defaults.set(modifiedAt, forKey: modifiedKey)
        publish(words: words, modifiedAt: modifiedAt)
    }

    private func publish(words: [String], modifiedAt: Double) {
        cloudStore.set(words, forKey: storageKey)
        cloudStore.set(modifiedAt, forKey: modifiedKey)
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
