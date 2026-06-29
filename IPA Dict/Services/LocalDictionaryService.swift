import Foundation
import SQLite3

nonisolated(unsafe) private let sqliteTransient = unsafeBitCast(
    -1,
    to: sqlite3_destructor_type.self
)

enum LocalDictionaryError: Error {
    case databaseMissing
    case databaseOpenFailed
    case queryFailed
}

actor LocalDictionaryService {
    private var database: OpaquePointer?

    deinit {
        sqlite3_close(database)
    }

    func lookup(word rawWord: String) throws -> [DictionaryEntry] {
        let word = rawWord
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        guard !word.isEmpty else { return [] }
        try openDatabaseIfNeeded()

        let sql = """
            SELECT word, uk_ipa, us_ipa, part_of_speech, countability,
                   zh_definition, en_definition, examples_json,
                   synonyms_json, antonyms_json
            FROM entries
            WHERE normalized_word = ?
            ORDER BY id
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw LocalDictionaryError.queryFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, word, -1, sqliteTransient)

        var entries: [DictionaryEntry] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let entryWord = columnText(statement, 0)
            let chineseDefinition = traditionalChinese(columnText(statement, 5))
            let examples = decodeExamples(columnText(statement, 7))
            entries.append(
                DictionaryEntry(
                    word: entryWord,
                    ukIPA: columnText(statement, 1),
                    usIPA: columnText(statement, 2),
                    partOfSpeech: DictionaryEntry.normalizedPartOfSpeech(
                        columnText(statement, 3)
                    ),
                    countability: columnText(statement, 4),
                    inflections: [],
                    zhDefinition: chineseDefinition,
                    enDefinition: columnText(statement, 6),
                    examples: Array(examples.prefix(1)),
                    synonyms: decodeJSON(columnText(statement, 8)),
                    antonyms: decodeJSON(columnText(statement, 9))
                )
            )
        }
        return entries
    }

    func suggestions(prefix rawPrefix: String, limit: Int = 20) throws -> [String] {
        let prefix = rawPrefix
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        guard !prefix.isEmpty else { return [] }
        try openDatabaseIfNeeded()

        let sql = """
            SELECT word, normalized_word
            FROM entries
            WHERE normalized_word LIKE ?
            GROUP BY normalized_word
            ORDER BY
                CASE WHEN normalized_word = ? THEN 0 ELSE 1 END,
                normalized_word
            LIMIT ?
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw LocalDictionaryError.queryFailed
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_text(statement, 1, "\(prefix)%", -1, sqliteTransient)
        sqlite3_bind_text(statement, 2, prefix, -1, sqliteTransient)
        sqlite3_bind_int(statement, 3, Int32(limit))

        var words: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let word = columnText(statement, 0)
            if !word.isEmpty {
                words.append(word)
            }
        }
        return words
    }

    private func openDatabaseIfNeeded() throws {
        guard database == nil else { return }
        guard let url = Bundle.main.url(
            forResource: "dictionary",
            withExtension: "sqlite"
        ) else {
            throw LocalDictionaryError.databaseMissing
        }
        guard sqlite3_open_v2(
            url.path,
            &database,
            SQLITE_OPEN_READONLY,
            nil
        ) == SQLITE_OK else {
            throw LocalDictionaryError.databaseOpenFailed
        }
    }

    private func columnText(_ statement: OpaquePointer?, _ index: Int32) -> String {
        guard let value = sqlite3_column_text(statement, index) else { return "" }
        return String(cString: value)
    }

    private func decodeJSON(_ value: String) -> [String] {
        guard let data = value.data(using: .utf8) else { return [] }
        return (try? JSONDecoder().decode([String].self, from: data)) ?? []
    }

    private func decodeExamples(_ value: String) -> [DictionaryExample] {
        guard let data = value.data(using: .utf8) else { return [] }
        let examples = (
            try? JSONDecoder().decode([StoredDictionaryExample].self, from: data)
        ) ?? []

        return examples.compactMap {
            let chinese = traditionalChinese($0.chinese)
            guard !$0.english.trimmingCharacters(
                      in: .whitespacesAndNewlines
                  ).isEmpty,
                  !chinese.trimmingCharacters(
                      in: .whitespacesAndNewlines
                  ).isEmpty else {
                return nil
            }
            return DictionaryExample(english: $0.english, chinese: chinese)
        }
    }

    private func traditionalChinese(_ value: String) -> String {
        value.applyingTransform(
            StringTransform("Hans-Hant"),
            reverse: false
        ) ?? value
    }
}

private struct StoredDictionaryExample: Decodable {
    let english: String
    let chinese: String
}
