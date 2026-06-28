import SwiftUI

struct PhonemeButton: View {
    let symbol: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(symbol)
                .font(.system(size: 16, weight: .semibold, design: .rounded))
                .frame(minWidth: 24, minHeight: 30)
                .padding(.horizontal, 3)
        }
        .buttonStyle(.bordered)
        .buttonBorderShape(.capsule)
        .tint(.accentColor)
        .foregroundStyle(Color.accentColor)
        .accessibilityLabel("Play \(symbol) phoneme")
    }
}

enum IPATokenizer {
    private static let compoundPhonemes = [
        "tʃ", "dʒ", "eɪ", "aɪ", "ɔɪ", "aʊ", "əʊ", "oʊ",
        "ɪə", "eə", "ʊə", "iː", "ɑː", "ɔː", "uː", "ɜː",
        "æː", "ɛː", "ɪː", "ʊː", "əː", "ɝː", "aː", "oː",
        "eɪː", "aɪː", "oʊː"
    ]

    static func phonemes(in transcription: String) -> [String] {
        var remaining = normalized(transcription)

        var result: [String] = []

        while !remaining.isEmpty {
            if let compound = compoundPhonemes.first(where: { remaining.hasPrefix($0) }) {
                result.append(compound)
                remaining.removeFirst(compound.count)
            } else {
                let symbol = String(remaining.removeFirst())
                if symbol == "." {
                    continue
                } else if symbol == "ː", let previous = result.popLast() {
                    result.append(previous + symbol)
                } else {
                    result.append(symbol)
                }
            }
        }

        return result
    }

    private static func normalized(_ transcription: String) -> String {
        var value = transcription
            .replacingOccurrences(of: "d͡ʒ", with: "dʒ")
            .replacingOccurrences(of: "d͜ʒ", with: "dʒ")
            .replacingOccurrences(of: "t͡ʃ", with: "tʃ")
            .replacingOccurrences(of: "t͜ʃ", with: "tʃ")
            .replacingOccurrences(of: "ɫ", with: "l")
            .replacingOccurrences(of: "ɚ", with: "ər")
            .replacingOccurrences(of: "ɝ", with: "ɜr")
            .replacingOccurrences(of: "ᵻ", with: "ɪ")
            .replacingOccurrences(of: "ᵿ", with: "ʊ")
            .replacingOccurrences(of: "ä", with: "a")

        [
            "/", "[", "]", "ˈ", "ˌ", " ", "(", ")", "-",
            "~", "ˑ", "ʰ", "ʲ", "̃", "̈", "̝", "̞", "̟", "̩",
            "̬", "̯", "͡", "͜", "‿"
        ].forEach {
            value = value.replacingOccurrences(of: $0, with: "")
        }

        return value
    }
}

struct PhonemeFlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout ()
    ) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var currentLineWidth: CGFloat = 0
        var totalHeight: CGFloat = 0
        var lineHeight: CGFloat = 0
        var widestLine: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            let proposedWidth = currentLineWidth == 0
                ? size.width
                : currentLineWidth + spacing + size.width

            if proposedWidth > maxWidth, currentLineWidth > 0 {
                widestLine = max(widestLine, currentLineWidth)
                totalHeight += lineHeight + spacing
                currentLineWidth = size.width
                lineHeight = size.height
            } else {
                currentLineWidth = proposedWidth
                lineHeight = max(lineHeight, size.height)
            }
        }

        widestLine = max(widestLine, currentLineWidth)
        totalHeight += lineHeight
        return CGSize(width: widestLine, height: totalHeight)
    }

    func placeSubviews(
        in bounds: CGRect,
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout ()
    ) {
        var x = bounds.minX
        var y = bounds.minY
        var lineHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)

            if x + size.width > bounds.maxX, x > bounds.minX {
                x = bounds.minX
                y += lineHeight + spacing
                lineHeight = 0
            }

            subview.place(
                at: CGPoint(x: x, y: y),
                anchor: .topLeading,
                proposal: ProposedViewSize(size)
            )
            x += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
    }
}
