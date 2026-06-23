import Foundation

enum DictionaryServiceError: LocalizedError {
    case invalidWord
    case wordNotFound(String)
    case invalidResponse
    case server(String)
    case decoding

    var errorDescription: String? {
        switch self {
        case .invalidWord:
            "請輸入要查詢的英文單字。"
        case .wordNotFound(let word):
            "找不到「\(word)」的字典資料。"
        case .invalidResponse:
            "字典服務回傳了無法辨識的回應。"
        case .server(let message):
            message
        case .decoding:
            "暫時無法讀取這筆字典資料。"
        }
    }
}

struct DictionaryService {
    private let session: URLSession
    private let localDictionary: LocalDictionaryService

    init(
        session: URLSession = .shared,
        localDictionary: LocalDictionaryService = LocalDictionaryService()
    ) {
        self.session = session
        self.localDictionary = localDictionary
    }

    func lookup(word rawWord: String) async throws -> [DictionaryEntry] {
        let word = rawWord.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !word.isEmpty else {
            throw DictionaryServiceError.invalidWord
        }

        if let localEntries = try? await localDictionary.lookup(word: word),
           !localEntries.isEmpty {
            if let curatedEntries = CuratedDictionary.entries(for: word) {
                return CuratedDictionary.merge(
                    curatedEntries: curatedEntries,
                    apiEntries: localEntries
                )
            }
            return localEntries
        }

        guard var components = URLComponents(
            string: "https://api.dictionaryapi.dev/api/v2/entries/en/"
        ) else {
            throw DictionaryServiceError.invalidResponse
        }
        components.path += word.lowercased()

        guard let url = components.url else {
            throw DictionaryServiceError.invalidWord
        }

        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw DictionaryServiceError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200:
            do {
                let apiEntries = try JSONDecoder().decode(
                    [DictionaryAPIEntry].self,
                    from: data
                )
                let entries = apiEntries.flatMap(DictionaryEntry.makeEntries)
                guard !entries.isEmpty else {
                    throw DictionaryServiceError.wordNotFound(word)
                }

                if let curatedEntries = CuratedDictionary.entries(for: word) {
                    return CuratedDictionary.merge(
                        curatedEntries: curatedEntries,
                        apiEntries: entries
                    )
                }

                return entries
            } catch let error as DictionaryServiceError {
                throw error
            } catch {
                throw DictionaryServiceError.decoding
            }

        case 404:
            throw DictionaryServiceError.wordNotFound(word)

        default:
            if let apiError = try? JSONDecoder().decode(
                DictionaryAPIErrorResponse.self,
                from: data
            ) {
                throw DictionaryServiceError.server(
                    apiError.message ?? apiError.title ?? "字典服務暫時無法使用。"
                )
            }
            throw DictionaryServiceError.server(
                "字典服務暫時無法使用（\(httpResponse.statusCode)）。"
            )
        }
    }
}
