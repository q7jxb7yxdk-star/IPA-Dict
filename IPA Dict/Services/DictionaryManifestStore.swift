import Combine
import Foundation

@MainActor
final class DictionaryManifestStore: ObservableObject {
    @Published private(set) var displayText = "資料庫日期：未知"

    init(bundle: Bundle = .main) {
        displayText = Self.databaseDateText(from: bundle)
    }

    private static func databaseDateText(from bundle: Bundle) -> String {
        guard let url = bundle.url(
            forResource: "dictionary",
            withExtension: "sqlite"
        ) else {
            return "資料庫日期：未知"
        }

        do {
            let attributes = try FileManager.default.attributesOfItem(
                atPath: url.path
            )
            guard let updatedAt = attributes[.modificationDate] as? Date else {
                return "資料庫日期：未知"
            }

            return "資料庫日期：\(Self.displayFormatter.string(from: updatedAt))"
        } catch {
            return "資料庫日期：未知"
        }
    }

    private static let displayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_Hant_HK")
        formatter.timeZone = TimeZone(identifier: "Asia/Hong_Kong")
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter
    }()
}
