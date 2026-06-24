import SwiftUI

struct MarkdownText: View {
    private let source: String
    private let font: Font?
    private let color: Color
    private let lineSpacing: CGFloat

    init(
        _ source: String,
        font: Font? = nil,
        color: Color = .primary,
        lineSpacing: CGFloat = 0
    ) {
        self.source = source
        self.font = font
        self.color = color
        self.lineSpacing = lineSpacing
    }

    var body: some View {
        Text(attributedSource)
            .font(resolvedFont)
            .foregroundStyle(color)
            .lineSpacing(lineSpacing)
            .textSelection(.enabled)
    }

    private var resolvedFont: Font {
        if let font {
            return font
        }

        switch heading.level {
        case 1:
            return .system(size: 28, weight: .bold, design: .rounded)
        case 2:
            return .system(size: 22, weight: .bold)
        case 3:
            return .system(size: 18, weight: .bold)
        default:
            return .system(size: 16)
        }
    }

    private var attributedSource: AttributedString {
        (try? AttributedString(
            markdown: heading.content,
            options: .init(
                interpretedSyntax: .inlineOnlyPreservingWhitespace,
                failurePolicy: .returnPartiallyParsedIfPossible
            )
        )) ?? AttributedString(heading.content)
    }

    private var heading: (level: Int, content: String) {
        let firstLine = source.prefix { $0 != "\n" }
        let markerCount = firstLine.prefix { $0 == "#" }.count

        guard (1...6).contains(markerCount) else {
            return (0, source)
        }

        let markerEnd = source.index(source.startIndex, offsetBy: markerCount)
        guard markerEnd < source.endIndex, source[markerEnd] == " " else {
            return (0, source)
        }

        let contentStart = source.index(after: markerEnd)
        return (markerCount, String(source[contentStart...]))
    }
}

extension String {
    var markdownEscaped: String {
        replacingOccurrences(
            of: #"([\\`*_{}\[\]()<>#+\-.!|])"#,
            with: #"\\$1"#,
            options: .regularExpression
        )
    }
}
