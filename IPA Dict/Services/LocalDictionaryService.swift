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
        let resolvedWord = try resolvedHeadword(for: word)

        let sql = """
            SELECT word, uk_ipa, us_ipa, part_of_speech, countability,
                   plural_forms_json, verb_forms_json,
                   zh_definition, en_definition,
                   examples_json, synonyms_json, antonyms_json
            FROM entries
            WHERE normalized_word = ?
            ORDER BY id
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw LocalDictionaryError.queryFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, resolvedWord, -1, sqliteTransient)

        var entries: [DictionaryEntry] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let entryWord = columnText(statement, 0)
            let chineseDefinition = traditionalChinese(columnText(statement, 7))
            let examples = decodeExamples(columnText(statement, 9))
            entries.append(
                DictionaryEntry(
                    word: entryWord,
                    ukIPA: columnText(statement, 1),
                    usIPA: columnText(statement, 2),
                    partOfSpeech: DictionaryEntry.normalizedPartOfSpeech(
                        columnText(statement, 3)
                    ),
                    countability: columnText(statement, 4),
                    pluralForms: decodeJSON(columnText(statement, 5)),
                    verbForms: decodeVerbForms(columnText(statement, 6)),
                    inflections: [],
                    zhDefinition: chineseDefinition,
                    enDefinition: columnText(statement, 8),
                    examples: Array(examples.prefix(1)),
                    synonyms: decodeJSON(columnText(statement, 10)),
                    antonyms: decodeJSON(columnText(statement, 11))
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
            WITH candidates AS (
                SELECT word, normalized_word, normalized_word AS matched_form,
                       0 AS source_rank,
                       0 AS alias_rank
                FROM entries
                WHERE normalized_word LIKE ?

                UNION ALL

                SELECT plural_lookup.normalized_headword AS word,
                       plural_lookup.normalized_headword AS normalized_word,
                       plural_lookup.plural_form AS matched_form,
                       1 AS source_rank,
                       0 AS alias_rank
                FROM plural_lookup
                JOIN entries
                  ON entries.normalized_word = plural_lookup.normalized_headword
                WHERE plural_lookup.plural_form LIKE ?
                GROUP BY plural_lookup.normalized_headword,
                         plural_lookup.plural_form

                UNION ALL

                SELECT verb_form_lookup.normalized_headword AS word,
                       verb_form_lookup.normalized_headword AS normalized_word,
                       verb_form_lookup.verb_form AS matched_form,
                       1 AS source_rank,
                       MIN(verb_form_lookup.priority) AS alias_rank
                FROM verb_form_lookup
                JOIN entries
                  ON entries.normalized_word = verb_form_lookup.normalized_headword
                WHERE verb_form_lookup.verb_form LIKE ?
                GROUP BY verb_form_lookup.normalized_headword,
                         verb_form_lookup.verb_form
            )
            SELECT COALESCE(
                       MIN(CASE WHEN word = lower(word) THEN word END),
                       MIN(word COLLATE NOCASE)
                   ),
                   normalized_word
            FROM candidates
            GROUP BY normalized_word
            ORDER BY
                MIN(CASE WHEN matched_form = ? THEN 0 ELSE 1 END),
                MIN(source_rank),
                MIN(alias_rank),
                MIN(matched_form),
                normalized_word
            LIMIT ?
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw LocalDictionaryError.queryFailed
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_text(statement, 1, "\(prefix)%", -1, sqliteTransient)
        sqlite3_bind_text(statement, 2, "\(prefix)%", -1, sqliteTransient)
        sqlite3_bind_text(statement, 3, "\(prefix)%", -1, sqliteTransient)
        sqlite3_bind_text(statement, 4, prefix, -1, sqliteTransient)
        sqlite3_bind_int(statement, 5, Int32(limit))

        var words: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let word = columnText(statement, 0)
            if !word.isEmpty {
                words.append(word)
            }
        }
        return words
    }

    private func resolvedHeadword(for word: String) throws -> String {
        let sql = """
            SELECT normalized_headword
            FROM (
                SELECT normalized_word AS normalized_headword,
                       0 AS match_rank,
                       0 AS alias_rank
                FROM entries
                WHERE normalized_word = ?

                UNION ALL

                SELECT normalized_headword, 1 AS match_rank, 0 AS alias_rank
                FROM plural_lookup
                WHERE plural_form = ?

                UNION ALL

                SELECT normalized_headword, 1 AS match_rank, priority AS alias_rank
                FROM verb_form_lookup
                WHERE verb_form = ?
            )
            ORDER BY match_rank, alias_rank, normalized_headword
            LIMIT 1
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw LocalDictionaryError.queryFailed
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_text(statement, 1, word, -1, sqliteTransient)
        sqlite3_bind_text(statement, 2, word, -1, sqliteTransient)
        sqlite3_bind_text(statement, 3, word, -1, sqliteTransient)

        guard sqlite3_step(statement) == SQLITE_ROW else { return word }
        return columnText(statement, 0)
    }

    func reverseSuggestions(
        chinese rawQuery: String,
        limit: Int = 20
    ) throws -> [String] {
        let query = traditionalChinese(
            rawQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        )
        guard !query.isEmpty else { return [] }
        try openDatabaseIfNeeded()

        let sql = """
            SELECT word, normalized_word,
                   MIN(CASE WHEN zh_definition = ? THEN 0 ELSE 1 END) AS match_rank,
                   MIN(LENGTH(zh_definition)) AS definition_length
            FROM entries
            WHERE zh_definition LIKE ?
            GROUP BY normalized_word
            ORDER BY match_rank, definition_length, normalized_word
            LIMIT ?
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw LocalDictionaryError.queryFailed
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_text(statement, 1, query, -1, sqliteTransient)
        sqlite3_bind_text(statement, 2, "%\(query)%", -1, sqliteTransient)
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

    private func decodeVerbForms(_ value: String) -> VerbForms? {
        guard let data = value.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(VerbForms.self, from: data)
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
