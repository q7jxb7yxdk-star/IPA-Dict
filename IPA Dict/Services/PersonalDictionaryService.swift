import Foundation
import SQLite3

nonisolated(unsafe) private let sqliteTransient = unsafeBitCast(
    -1,
    to: sqlite3_destructor_type.self
)

nonisolated private func defaultPersonalDictionaryDatabaseURL() throws -> URL {
    let fileManager = FileManager.default
    let supportURL = try fileManager.url(
        for: .applicationSupportDirectory,
        in: .userDomainMask,
        appropriateFor: nil,
        create: true
    )
    return supportURL
        .appendingPathComponent("IPA Dict", isDirectory: true)
        .appendingPathComponent("PersonalDictionary.sqlite")
}

enum PersonalDictionaryError: LocalizedError {
    case databaseOpenFailed
    case databasePrepareFailed
    case databaseWriteFailed
    case invalidEntry
    case invalidImportFile

    var errorDescription: String? {
        switch self {
        case .databaseOpenFailed:
            "無法開啟私人字典資料庫。"
        case .databasePrepareFailed:
            "無法準備私人字典資料庫查詢。"
        case .databaseWriteFailed:
            "無法儲存私人字典內容。"
        case .invalidEntry:
            "私人字典內容不完整。"
        case .invalidImportFile:
            "選取的檔案不是有效的私人字典 SQLite。"
        }
    }
}

actor PersonalDictionaryService {
    static let shared = PersonalDictionaryService()

    private var database: OpaquePointer?
    private let databaseURLProvider: @Sendable () throws -> URL

    init(
        databaseURLProvider: @escaping @Sendable () throws -> URL = {
            try defaultPersonalDictionaryDatabaseURL()
        }
    ) {
        self.databaseURLProvider = databaseURLProvider
    }

    deinit {
        sqlite3_close(database)
    }

    func lookup(word rawWord: String) throws -> [DictionaryEntry] {
        guard let personalEntry = try personalEntry(word: rawWord) else {
            return []
        }
        return EditablePersonalDictionaryEntry(
            personalEntry: personalEntry
        ).dictionaryEntries(markedAsPersonal: true)
    }

    func draft(word rawWord: String) throws -> EditablePersonalDictionaryEntry? {
        guard let personalEntry = try personalEntry(word: rawWord) else {
            return nil
        }
        return EditablePersonalDictionaryEntry(personalEntry: personalEntry)
    }

    func save(_ draft: EditablePersonalDictionaryEntry) throws -> [DictionaryEntry] {
        let word = draft.word.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedWord = EditablePersonalDictionaryEntry.normalizedWord(word)
        guard !word.isEmpty, !normalizedWord.isEmpty else {
            throw PersonalDictionaryError.invalidEntry
        }

        let senses = draft.senses.filter { sense in
            !sense.partOfSpeechLine.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || !sense.zhDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || !sense.enDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || !sense.exampleEnglish.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || !sense.exampleChinese.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        guard !senses.isEmpty else {
            throw PersonalDictionaryError.invalidEntry
        }

        try openDatabaseIfNeeded()
        let now = Self.iso8601Formatter.string(from: Date())

        try execute("BEGIN IMMEDIATE TRANSACTION")
        do {
            let existingID = try wordID(normalizedWord: normalizedWord)
            let wordID: Int64
            if let existingID {
                try updateWord(
                    id: existingID,
                    word: word,
                    normalizedWord: normalizedWord,
                    ukIPA: draft.ukIPA,
                    usIPA: draft.usIPA,
                    sourceNote: draft.sourceNote,
                    sourceURL: draft.sourceURL,
                    updatedAt: now
                )
                try deleteSenses(wordID: existingID)
                wordID = existingID
            } else {
                wordID = try insertWord(
                    word: word,
                    normalizedWord: normalizedWord,
                    ukIPA: draft.ukIPA,
                    usIPA: draft.usIPA,
                    sourceNote: draft.sourceNote,
                    sourceURL: draft.sourceURL,
                    createdAt: now,
                    updatedAt: now
                )
            }

            for (index, sense) in senses.enumerated() {
                let parsed = EditablePersonalDictionaryEntry.parsePartOfSpeechLine(
                    sense.partOfSpeechLine
                )
                try insertSense(
                    wordID: wordID,
                    displayOrder: index,
                    partOfSpeech: parsed.partOfSpeech,
                    countability: parsed.countability,
                    zhDefinition: sense.zhDefinition,
                    enDefinition: sense.enDefinition,
                    exampleEnglish: sense.exampleEnglish,
                    exampleChinese: sense.exampleChinese
                )
            }

            try execute("COMMIT")
        } catch {
            try? execute("ROLLBACK")
            throw error
        }

        return try lookup(word: word)
    }

    func delete(word rawWord: String) throws {
        let normalizedWord = EditablePersonalDictionaryEntry.normalizedWord(rawWord)
        guard !normalizedWord.isEmpty else { return }
        try openDatabaseIfNeeded()

        let sql = "DELETE FROM personal_words WHERE normalized_word = ?"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, normalizedWord, -1, sqliteTransient)

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw PersonalDictionaryError.databaseWriteFailed
        }
    }

    func databaseURL() throws -> URL {
        try databaseURLProvider()
    }

    func exportCopyURL() throws -> URL {
        try openDatabaseIfNeeded()
        let sourceURL = try databaseURLProvider()
        let exportURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(Self.exportFileName())

        if FileManager.default.fileExists(atPath: exportURL.path) {
            try FileManager.default.removeItem(at: exportURL)
        }

        sqlite3_close(database)
        database = nil
        try FileManager.default.copyItem(at: sourceURL, to: exportURL)
        try openDatabaseIfNeeded()
        return exportURL
    }

    func importDatabase(from sourceURL: URL) throws {
        let destinationURL = try databaseURLProvider()
        let securityScoped = sourceURL.startAccessingSecurityScopedResource()
        defer {
            if securityScoped {
                sourceURL.stopAccessingSecurityScopedResource()
            }
        }

        try validateImportDatabase(at: sourceURL)

        sqlite3_close(database)
        database = nil

        let fileManager = FileManager.default
        try fileManager.createDirectory(
            at: destinationURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )

        if fileManager.fileExists(atPath: destinationURL.path) {
            let backupURL = destinationURL
                .deletingLastPathComponent()
                .appendingPathComponent(Self.backupFileName())
            if fileManager.fileExists(atPath: backupURL.path) {
                try fileManager.removeItem(at: backupURL)
            }
            try fileManager.copyItem(at: destinationURL, to: backupURL)
        }

        if fileManager.fileExists(atPath: destinationURL.path) {
            try fileManager.removeItem(at: destinationURL)
        }
        try fileManager.copyItem(at: sourceURL, to: destinationURL)
        try openDatabaseIfNeeded()
    }

    private func personalEntry(word rawWord: String) throws -> PersonalDictionaryEntry? {
        let normalizedWord = EditablePersonalDictionaryEntry.normalizedWord(rawWord)
        guard !normalizedWord.isEmpty else { return nil }
        try openDatabaseIfNeeded()

        let sql = """
            SELECT id, word, normalized_word, uk_ipa, us_ipa, source_note,
                   source_url, created_at, updated_at
            FROM personal_words
            WHERE normalized_word = ?
            LIMIT 1
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, normalizedWord, -1, sqliteTransient)

        guard sqlite3_step(statement) == SQLITE_ROW else {
            return nil
        }

        let id = sqlite3_column_int64(statement, 0)
        let entry = PersonalDictionaryEntry(
            id: id,
            word: columnText(statement, 1),
            normalizedWord: columnText(statement, 2),
            ukIPA: columnText(statement, 3),
            usIPA: columnText(statement, 4),
            sourceNote: columnText(statement, 5),
            sourceURL: columnText(statement, 6),
            senses: try senses(wordID: id),
            createdAt: Self.date(from: columnText(statement, 7)),
            updatedAt: Self.date(from: columnText(statement, 8))
        )
        return entry
    }

    private func senses(wordID: Int64) throws -> [PersonalDictionarySense] {
        let sql = """
            SELECT id, display_order, part_of_speech, countability,
                   zh_definition, en_definition, example_english,
                   example_chinese
            FROM personal_senses
            WHERE word_id = ?
            ORDER BY display_order, id
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_int64(statement, 1, wordID)

        var senses: [PersonalDictionarySense] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            senses.append(
                PersonalDictionarySense(
                    id: sqlite3_column_int64(statement, 0),
                    displayOrder: Int(sqlite3_column_int(statement, 1)),
                    partOfSpeech: columnText(statement, 2),
                    countability: columnText(statement, 3),
                    zhDefinition: columnText(statement, 4),
                    enDefinition: columnText(statement, 5),
                    exampleEnglish: columnText(statement, 6),
                    exampleChinese: columnText(statement, 7)
                )
            )
        }
        return senses
    }

    private func wordID(normalizedWord: String) throws -> Int64? {
        let sql = "SELECT id FROM personal_words WHERE normalized_word = ? LIMIT 1"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, normalizedWord, -1, sqliteTransient)

        guard sqlite3_step(statement) == SQLITE_ROW else {
            return nil
        }
        return sqlite3_column_int64(statement, 0)
    }

    private func updateWord(
        id: Int64,
        word: String,
        normalizedWord: String,
        ukIPA: String,
        usIPA: String,
        sourceNote: String,
        sourceURL: String,
        updatedAt: String
    ) throws {
        let sql = """
            UPDATE personal_words
            SET word = ?, normalized_word = ?, uk_ipa = ?, us_ipa = ?,
                source_note = ?, source_url = ?, updated_at = ?
            WHERE id = ?
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        bind(statement, [
            word,
            normalizedWord,
            ukIPA,
            usIPA,
            sourceNote,
            sourceURL,
            updatedAt,
        ])
        sqlite3_bind_int64(statement, 8, id)
        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw PersonalDictionaryError.databaseWriteFailed
        }
    }

    private func insertWord(
        word: String,
        normalizedWord: String,
        ukIPA: String,
        usIPA: String,
        sourceNote: String,
        sourceURL: String,
        createdAt: String,
        updatedAt: String
    ) throws -> Int64 {
        let sql = """
            INSERT INTO personal_words (
                word, normalized_word, uk_ipa, us_ipa, source_note,
                source_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        bind(statement, [
            word,
            normalizedWord,
            ukIPA,
            usIPA,
            sourceNote,
            sourceURL,
            createdAt,
            updatedAt,
        ])
        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw PersonalDictionaryError.databaseWriteFailed
        }
        return sqlite3_last_insert_rowid(database)
    }

    private func deleteSenses(wordID: Int64) throws {
        let sql = "DELETE FROM personal_senses WHERE word_id = ?"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_int64(statement, 1, wordID)
        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw PersonalDictionaryError.databaseWriteFailed
        }
    }

    private func insertSense(
        wordID: Int64,
        displayOrder: Int,
        partOfSpeech: String,
        countability: String,
        zhDefinition: String,
        enDefinition: String,
        exampleEnglish: String,
        exampleChinese: String
    ) throws {
        let sql = """
            INSERT INTO personal_senses (
                word_id, display_order, part_of_speech, countability,
                zh_definition, en_definition, example_english,
                example_chinese
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databasePrepareFailed
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_int64(statement, 1, wordID)
        sqlite3_bind_int(statement, 2, Int32(displayOrder))
        bind(statement, [
            partOfSpeech,
            countability,
            zhDefinition,
            enDefinition,
            exampleEnglish,
            exampleChinese,
        ], startingAt: 3)

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw PersonalDictionaryError.databaseWriteFailed
        }
    }

    private func openDatabaseIfNeeded() throws {
        guard database == nil else { return }
        let url = try databaseURLProvider()
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )

        guard sqlite3_open_v2(
            url.path,
            &database,
            SQLITE_OPEN_CREATE | SQLITE_OPEN_READWRITE | SQLITE_OPEN_FULLMUTEX,
            nil
        ) == SQLITE_OK else {
            throw PersonalDictionaryError.databaseOpenFailed
        }
        try createSchemaIfNeeded()
    }

    private func createSchemaIfNeeded() throws {
        try execute("""
            PRAGMA foreign_keys = ON;
        """)
        try execute("""
            CREATE TABLE IF NOT EXISTS personal_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                normalized_word TEXT NOT NULL UNIQUE,
                uk_ipa TEXT NOT NULL DEFAULT '',
                us_ipa TEXT NOT NULL DEFAULT '',
                source_note TEXT NOT NULL DEFAULT '',
                source_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        try execute("""
            CREATE TABLE IF NOT EXISTS personal_senses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                display_order INTEGER NOT NULL,
                part_of_speech TEXT NOT NULL DEFAULT '',
                countability TEXT NOT NULL DEFAULT '',
                zh_definition TEXT NOT NULL DEFAULT '',
                en_definition TEXT NOT NULL DEFAULT '',
                example_english TEXT NOT NULL DEFAULT '',
                example_chinese TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(word_id) REFERENCES personal_words(id)
                    ON DELETE CASCADE
            );
        """)
        try execute("""
            CREATE INDEX IF NOT EXISTS idx_personal_senses_word_order
            ON personal_senses(word_id, display_order);
        """)
    }

    private func validateImportDatabase(at url: URL) throws {
        var importDatabase: OpaquePointer?
        guard sqlite3_open_v2(
            url.path,
            &importDatabase,
            SQLITE_OPEN_READONLY,
            nil
        ) == SQLITE_OK else {
            sqlite3_close(importDatabase)
            throw PersonalDictionaryError.invalidImportFile
        }
        defer { sqlite3_close(importDatabase) }

        let integrity = singleTextValue(
            database: importDatabase,
            sql: "PRAGMA integrity_check"
        )
        guard integrity == "ok" else {
            throw PersonalDictionaryError.invalidImportFile
        }

        let requiredTables = ["personal_words", "personal_senses"]
        for table in requiredTables {
            let exists = singleTextValue(
                database: importDatabase,
                sql: """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name = '\(table)'
                    LIMIT 1
                """
            )
            guard exists == table else {
                throw PersonalDictionaryError.invalidImportFile
            }
        }
    }

    private func singleTextValue(
        database: OpaquePointer?,
        sql: String
    ) -> String {
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            return ""
        }
        defer { sqlite3_finalize(statement) }
        guard sqlite3_step(statement) == SQLITE_ROW,
              let value = sqlite3_column_text(statement, 0) else {
            return ""
        }
        return String(cString: value)
    }

    private func execute(_ sql: String) throws {
        guard sqlite3_exec(database, sql, nil, nil, nil) == SQLITE_OK else {
            throw PersonalDictionaryError.databaseWriteFailed
        }
    }

    private func bind(
        _ statement: OpaquePointer?,
        _ values: [String],
        startingAt startIndex: Int32 = 1
    ) {
        for (offset, value) in values.enumerated() {
            sqlite3_bind_text(
                statement,
                startIndex + Int32(offset),
                value,
                -1,
                sqliteTransient
            )
        }
    }

    private func columnText(_ statement: OpaquePointer?, _ index: Int32) -> String {
        guard let value = sqlite3_column_text(statement, index) else { return "" }
        return String(cString: value)
    }

    private static let iso8601Formatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static func date(from value: String) -> Date {
        iso8601Formatter.date(from: value) ?? Date(timeIntervalSince1970: 0)
    }

    private static func exportFileName() -> String {
        "PersonalDictionary-\(fileTimestamp()).sqlite"
    }

    private static func backupFileName() -> String {
        "PersonalDictionary-backup-\(fileTimestamp()).sqlite"
    }

    private static func fileTimestamp() -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd-HHmmss"
        return formatter.string(from: Date())
    }
}
