import SwiftUI
import Translation

struct TranslatedText: View {
    let sourceText: String
    var font: Font = .body
    var foregroundStyle: Color = .primary
    var placeholder: String = "翻譯中…"

    @State private var translatedText = ""
    @State private var translationError: String?
    @State private var configuration: TranslationSession.Configuration?

    var body: some View {
        Group {
            if sourceText.isEmpty {
                EmptyView()
            } else if !translatedText.isEmpty {
                Text(translatedText)
                    .font(font)
                    .foregroundStyle(foregroundStyle)
            } else if let translationError {
                Text(translationError)
                    .font(.caption)
                    .foregroundStyle(.primary)
            } else {
                HStack(spacing: 7) {
                    ProgressView()
                        .controlSize(.small)
                    Text(placeholder)
                        .font(font)
                        .foregroundStyle(.primary)
                }
            }
        }
        .task(id: sourceText) {
            translatedText = ""
            translationError = nil
            configuration = TranslationSession.Configuration(
                source: Locale.Language(identifier: "en"),
                target: Locale.Language(identifier: "zh-Hant")
            )
        }
        .translationTask(configuration) { session in
            do {
                let response = try await session.translate(sourceText)
                translatedText = response.targetText
            } catch {
                translationError = "目前無法產生中文翻譯"
            }
        }
    }
}
