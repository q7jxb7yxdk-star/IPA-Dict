import SwiftUI
import UniformTypeIdentifiers

struct PersonalDictionaryDocument: FileDocument {
    static var readableContentTypes: [UTType] {
        [.sqliteDatabase, .data]
    }

    let fileURL: URL

    init(fileURL: URL) {
        self.fileURL = fileURL
    }

    init(configuration: ReadConfiguration) throws {
        guard let file = configuration.file.regularFileContents else {
            throw CocoaError(.fileReadCorruptFile)
        }

        let temporaryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("sqlite")
        try file.write(to: temporaryURL, options: .atomic)
        self.fileURL = temporaryURL
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        try FileWrapper(url: fileURL, options: .immediate)
    }
}

extension UTType {
    static var sqliteDatabase: UTType {
        UTType(filenameExtension: "sqlite")
            ?? UTType(filenameExtension: "sqlite3")
            ?? .data
    }
}
