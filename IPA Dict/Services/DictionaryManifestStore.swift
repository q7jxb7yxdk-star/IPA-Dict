import Combine
import Foundation

struct DictionaryManifest: Decodable {
    let databaseFile: String
    let databaseUpdatedAt: String
    let displayUpdatedAt: String
    let sha256: String
    let generatedAt: String

    enum CodingKeys: String, CodingKey {
        case databaseFile = "database_file"
        case databaseUpdatedAt = "database_updated_at"
        case displayUpdatedAt = "display_updated_at"
        case sha256
        case generatedAt = "generated_at"
    }
}

@MainActor
final class DictionaryManifestStore: ObservableObject {
    @Published private(set) var manifest: DictionaryManifest?

    init(bundle: Bundle = .main) {
        manifest = Self.loadManifest(from: bundle)
    }

    var displayText: String {
        guard let manifest else {
            return "資料庫日期：未知"
        }
        return "資料庫日期：\(manifest.displayUpdatedAt)"
    }

    private static func loadManifest(
        from bundle: Bundle
    ) -> DictionaryManifest? {
        guard let url = bundle.url(
            forResource: "dictionary_manifest",
            withExtension: "json"
        ),
              let data = try? Data(contentsOf: url) else {
            return nil
        }
        return try? JSONDecoder().decode(DictionaryManifest.self, from: data)
    }
}
