import Foundation

struct DictionaryReport {
    let queriedWord: String
    let missingWord: String
    let createdAt: Date

    var issueKind: String {
        missingWord.isEmpty ? "詞條錯誤" : "遺失詞"
    }

    var checklistLine: String {
        let missingPart = missingWord.isEmpty
            ? "詞條錯誤"
            : "遺失詞：\(missingWord)"
        return "- [ ] \(Self.timestampFormatter.string(from: createdAt)) — 查詢詞：\(queriedWord) — \(missingPart)"
    }

    var issueTitle: String {
        if missingWord.isEmpty {
            return "Dictionary report: \(queriedWord)"
        }

        return "Missing dictionary word: \(missingWord)"
    }

    var issueBody: String {
        """
        ## Dictionary Report

        - 查詢詞：\(queriedWord)
        - 遺失詞：\(missingWord.isEmpty ? "（沒有填寫）" : missingWord)
        - 問題類型：\(issueKind)
        - 時間：\(Self.timestampFormatter.string(from: createdAt))

        ## 待修清單

        - [ ] 檢查 \(missingWord.isEmpty ? queriedWord : missingWord) 的詞性、IPA、中文釋義、英文釋義及例句
        """
    }

    private static let timestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_Hant_HK")
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter
    }()
}

struct DictionaryReportStore {
    private let fileName = "DictionaryReports.md"

    func append(_ report: DictionaryReport) throws -> URL {
        let url = try reportFileURL()
        let fileManager = FileManager.default

        if !fileManager.fileExists(atPath: url.path) {
            try initialDocument.write(
                to: url,
                atomically: true,
                encoding: .utf8
            )
        }

        let handle = try FileHandle(forWritingTo: url)
        defer {
            try? handle.close()
        }

        try handle.seekToEnd()
        let line = "\(report.checklistLine)\n"
        if let data = line.data(using: .utf8) {
            try handle.write(contentsOf: data)
        }

        return url
    }

    func githubIssueURL(for report: DictionaryReport) -> URL? {
        var components = URLComponents(
            string: "https://github.com/q7jxb7yxdk-star/IPA-Dict/issues/new"
        )
        components?.queryItems = [
            URLQueryItem(name: "title", value: report.issueTitle),
            URLQueryItem(name: "body", value: report.issueBody)
        ]
        return components?.url
    }

    private func reportFileURL() throws -> URL {
        guard let documentsURL = FileManager.default.urls(
            for: .documentDirectory,
            in: .userDomainMask
        ).first else {
            throw DictionaryReportStoreError.documentsDirectoryUnavailable
        }

        return documentsURL.appendingPathComponent(fileName)
    }

    private var initialDocument: String {
        """
        # Dictionary Reports

        """
    }
}

enum DictionaryReportStoreError: LocalizedError {
    case documentsDirectoryUnavailable

    var errorDescription: String? {
        switch self {
        case .documentsDirectoryUnavailable:
            "找不到可寫入的 Documents 目錄。"
        }
    }
}
