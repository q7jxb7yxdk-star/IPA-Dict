import SwiftUI

struct WordDetailView: View {
    let entries: [DictionaryEntry]
    var showsNavigationTitle = true

    @State private var expandedPartsOfSpeech: Set<String> = []

    private let audioPlayer = AudioPlayerService.shared
    private let collapsedMeaningLimit = 3

    init(entry: DictionaryEntry, showsNavigationTitle: Bool = true) {
        self.entries = [entry]
        self.showsNavigationTitle = showsNavigationTitle
    }

    init(entries: [DictionaryEntry], showsNavigationTitle: Bool = true) {
        self.entries = entries
        self.showsNavigationTitle = showsNavigationTitle
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                ForEach(Array(groupedEntries.enumerated()), id: \.element.id) { groupIndex, group in
                    let isExpanded = expandedPartsOfSpeech.contains(group.id)
                    let visibleEntries = isExpanded
                        ? group.entries
                        : Array(group.entries.prefix(collapsedMeaningLimit))

                    if groupIndex > 0 {
                        Divider()
                            .padding(.vertical, 8)
                    }
                    completeGroup(group, visibleEntries: visibleEntries)

                    if group.entries.count > collapsedMeaningLimit {
                        expansionButton(for: group, isExpanded: isExpanded)
                    }
                }

                if !allSynonyms.isEmpty {
                    Divider()
                        .padding(.vertical, 8)
                    wordChipsSection(title: "同義詞", words: allSynonyms)
                }
            }
            .frame(maxWidth: 760, alignment: .leading)
            .padding(.horizontal, 24)
            .padding(.vertical, 32)
            .frame(maxWidth: .infinity)
        }
        .background(Color.detailBackground)
        .navigationTitle(showsNavigationTitle ? "Dictionary" : "")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private var groupedEntries: [MeaningGroup] {
        var order: [String] = []
        var groups: [String: [DictionaryEntry]] = [:]

        for entry in entries {
            let key = entry.partOfSpeech.lowercased()
            if groups[key] == nil {
                order.append(key)
            }
            groups[key, default: []].append(entry)
        }

        return order.compactMap { key in
            guard let entries = groups[key], let first = entries.first else {
                return nil
            }
            return MeaningGroup(
                id: key,
                partOfSpeech: first.partOfSpeech,
                entries: entries
            )
        }
    }

    private var allSynonyms: [String] {
        var seen = Set<String>()
        return entries.flatMap(\.synonyms).filter {
            seen.insert($0.lowercased()).inserted
        }
    }

    private func completeGroup(
        _ group: MeaningGroup,
        visibleEntries: [DictionaryEntry]
    ) -> some View {
        let primaryEntry = group.entries[0]
        let chineseDefinitions = uniqueValues(
            group.entries.map(\.zhDefinition)
        )
        let countability = uniqueValues(
            group.entries.map(\.countability).filter { !$0.isEmpty }
        ).joined(separator: " or ")
        let inflections = uniqueValues(
            group.entries.flatMap(\.inflections)
        )

        return VStack(alignment: .leading, spacing: 26) {
            MarkdownText("# \(primaryEntry.word.markdownEscaped)")

            HStack(spacing: 8) {
                MarkdownText(
                    "**\(group.partOfSpeech.markdownEscaped)**",
                    font: .headline
                )

                if !countability.isEmpty {
                    MarkdownText(
                        "\\[ \(countability.markdownEscaped) \\]",
                        font: .subheadline.weight(.medium),
                        color: .primary
                    )
                }
            }

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 20) {
                    pronunciationButton(
                        region: "UK",
                        word: primaryEntry.word,
                        ipa: primaryEntry.ukIPA,
                        remoteAudioURL: primaryEntry.ukAudioURL,
                        localAudioFile: "\(primaryEntry.word)_uk"
                    )

                    pronunciationButton(
                        region: "US",
                        word: primaryEntry.word,
                        ipa: primaryEntry.usIPA,
                        remoteAudioURL: primaryEntry.usAudioURL,
                        localAudioFile: "\(primaryEntry.word)_us"
                    )
                }

                VStack(alignment: .leading, spacing: 12) {
                    pronunciationButton(
                        region: "UK",
                        word: primaryEntry.word,
                        ipa: primaryEntry.ukIPA,
                        remoteAudioURL: primaryEntry.ukAudioURL,
                        localAudioFile: "\(primaryEntry.word)_uk"
                    )

                    pronunciationButton(
                        region: "US",
                        word: primaryEntry.word,
                        ipa: primaryEntry.usIPA,
                        remoteAudioURL: primaryEntry.usAudioURL,
                        localAudioFile: "\(primaryEntry.word)_us"
                    )
                }
            }

            phonemeButtons(for: primaryEntry.ukIPA)

            if !inflections.isEmpty {
                MarkdownText(
                    inflections
                        .map(\.markdownEscaped)
                        .joined(separator: " \\| "),
                    font: .body.weight(.semibold),
                    color: .primary
                )
            }

            definitionSection(
                title: "中文解釋",
                content: chineseDefinitions.joined(separator: "；"),
                sourceForTranslation: primaryEntry.enDefinition,
                contentFont: .title3.weight(.medium)
            )

            VStack(alignment: .leading, spacing: 22) {
                sectionTitle("英文解釋")

                ForEach(Array(visibleEntries.enumerated()), id: \.element.id) { index, entry in
                    VStack(alignment: .leading, spacing: 14) {
                        if visibleEntries.count > 1 {
                            MarkdownText(
                                "**\(index + 1).**",
                                font: .caption.weight(.bold),
                                color: .primary
                            )
                        }

                        MarkdownText(
                            entry.enDefinition.markdownEscaped,
                            lineSpacing: 5
                        )

                        if !entry.examples.isEmpty {
                            examplesSection(entry.examples)
                        }
                    }
                }
            }
        }
    }

    private func uniqueValues(_ values: [String]) -> [String] {
        var seen = Set<String>()
        return values.filter {
            !$0.isEmpty && seen.insert($0).inserted
        }
    }

    private func expansionButton(
        for group: MeaningGroup,
        isExpanded: Bool
    ) -> some View {
        Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                if isExpanded {
                    expandedPartsOfSpeech.remove(group.id)
                } else {
                    expandedPartsOfSpeech.insert(group.id)
                }
            }
        } label: {
            Label(
                isExpanded
                    ? "收合解釋"
                    : "顯示更多解釋（\(group.entries.count - collapsedMeaningLimit)）",
                systemImage: isExpanded ? "chevron.up" : "chevron.down"
            )
            .font(.subheadline.weight(.semibold))
        }
        .buttonStyle(.borderless)
        .foregroundStyle(.primary)
        .padding(.top, 4)
    }

    private func pronunciationButton(
        region: String,
        word: String,
        ipa: String,
        remoteAudioURL: URL?,
        localAudioFile: String
    ) -> some View {
        Button {
            if let remoteAudioURL {
                audioPlayer.playRemoteSound(url: remoteAudioURL)
            } else {
                if Bundle.main.url(
                    forResource: localAudioFile,
                    withExtension: "mp3"
                ) != nil {
                    audioPlayer.playSound(fileName: localAudioFile)
                } else {
                    audioPlayer.speak(word: word, region: region)
                }
            }
        } label: {
            HStack(spacing: 7) {
                Image(systemName: "speaker.wave.2.fill")
                    .font(.subheadline)
                    .foregroundStyle(.primary)
                MarkdownText(
                    "**\(region.markdownEscaped)**",
                    font: .body.weight(.semibold),
                    color: .primary
                )
                if !ipa.isEmpty {
                    MarkdownText(
                        ipa.markdownEscaped,
                        font: .system(.body, design: .rounded),
                        color: .accentColor
                    )
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Play \(region) pronunciation")
    }

    @ViewBuilder
    private func phonemeButtons(for ipa: String) -> some View {
        if !ipa.isEmpty {
            HStack(alignment: .top, spacing: 6) {
                Text("/")
                    .foregroundStyle(Color.accentColor)

                PhonemeFlowLayout(spacing: 7) {
                    ForEach(
                        Array(IPATokenizer.phonemes(in: ipa).enumerated()),
                        id: \.offset
                    ) { _, symbol in
                        PhonemeButton(symbol: symbol) {
                            audioPlayer.playPhoneme(symbol: symbol)
                        }
                    }
                }

                Text("/")
                    .foregroundStyle(Color.accentColor)
            }
        }
    }

    private func definitionSection(
        title: String,
        content: String,
        sourceForTranslation: String?,
        contentFont: Font
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle(title)

            if let sourceForTranslation, content.isEmpty {
                MarkdownText(
                    sourceForTranslation.markdownEscaped,
                    font: contentFont,
                    lineSpacing: 5
                )
            } else {
                MarkdownText(
                    content.markdownEscaped,
                    font: contentFont,
                    lineSpacing: 5
                )
            }
        }
    }

    private func examplesSection(_ examples: [DictionaryExample]) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("例句")

            ForEach(examples.prefix(1)) { example in
                VStack(alignment: .leading, spacing: 8) {
                    MarkdownText(
                        example.english.markdownEscaped,
                        font: .body.weight(.medium)
                    )

                    MarkdownText(
                        example.chinese.markdownEscaped,
                        color: .primary
                    )
                }
                .lineSpacing(4)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private func wordChipsSection(title: String, words: [String]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle(title)

            PhonemeFlowLayout(spacing: 8) {
                ForEach(words.prefix(20), id: \.self) { word in
                    MarkdownText(
                        word.markdownEscaped,
                        font: .subheadline.weight(.medium)
                    )
                        .padding(.horizontal, 11)
                        .padding(.vertical, 7)
                        .background(.regularMaterial, in: Capsule())
                }
            }
        }
    }

    private func sectionTitle(_ title: String) -> some View {
        MarkdownText(
            "## \(title.markdownEscaped)",
            color: .primary
        )
    }
}

private struct MeaningGroup: Identifiable {
    let id: String
    let partOfSpeech: String
    let entries: [DictionaryEntry]
}

private extension Color {
    static var detailBackground: Color {
        #if os(macOS)
        Color(nsColor: .windowBackgroundColor)
        #else
        Color(uiColor: .systemGroupedBackground)
        #endif
    }
}

#Preview {
    NavigationStack {
        WordDetailView(entry: .apple)
    }
}
