import SwiftUI

struct WordDetailView: View {
    let entries: [DictionaryEntry]
    var showsNavigationTitle = true
    var onSelectWord: ((String) -> Void)?

    @Environment(\.openURL) private var openURL
    @State private var expandedPartsOfSpeech: Set<String> = []

    private let audioPlayer = AudioPlayerService.shared
    private let collapsedMeaningLimit = 3

    init(
        entry: DictionaryEntry,
        showsNavigationTitle: Bool = true,
        onSelectWord: ((String) -> Void)? = nil
    ) {
        self.entries = [entry]
        self.showsNavigationTitle = showsNavigationTitle
        self.onSelectWord = onSelectWord
    }

    init(
        entries: [DictionaryEntry],
        showsNavigationTitle: Bool = true,
        onSelectWord: ((String) -> Void)? = nil
    ) {
        self.entries = entries
        self.showsNavigationTitle = showsNavigationTitle
        self.onSelectWord = onSelectWord
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                if let primaryEntry {
                    headerSection(primaryEntry)

                    ForEach(groupedEntries) { group in
                        let isExpanded = expandedPartsOfSpeech.contains(group.id)
                        let visibleEntries = isExpanded
                            ? group.entries
                            : Array(group.entries.prefix(collapsedMeaningLimit))

                        Divider()
                            .padding(.vertical, 4)

                        meaningGroupSection(group, visibleEntries: visibleEntries)

                        if group.entries.count > collapsedMeaningLimit {
                            expansionButton(for: group, isExpanded: isExpanded)
                        }
                    }

                    if !allSynonyms.isEmpty {
                        Divider()
                            .padding(.vertical, 4)
                        linkedWordsSection(title: "同義詞", words: allSynonyms)
                    }

                    Divider()
                        .padding(.vertical, 4)
                    referenceSection(for: primaryEntry)
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

    private var primaryEntry: DictionaryEntry? {
        entries.first
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

    private func headerSection(_ entry: DictionaryEntry) -> some View {
        VStack(alignment: .leading, spacing: 22) {
            MarkdownText("# \(entry.word.markdownEscaped)")

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 20) {
                    pronunciationButton(
                        region: "UK",
                        word: entry.word,
                        ipa: entry.ukIPA,
                        remoteAudioURL: entry.ukAudioURL,
                        localAudioFile: "\(entry.word)_uk"
                    )

                    pronunciationButton(
                        region: "US",
                        word: entry.word,
                        ipa: entry.usIPA,
                        remoteAudioURL: entry.usAudioURL,
                        localAudioFile: "\(entry.word)_us"
                    )
                }

                VStack(alignment: .leading, spacing: 12) {
                    pronunciationButton(
                        region: "UK",
                        word: entry.word,
                        ipa: entry.ukIPA,
                        remoteAudioURL: entry.ukAudioURL,
                        localAudioFile: "\(entry.word)_uk"
                    )

                    pronunciationButton(
                        region: "US",
                        word: entry.word,
                        ipa: entry.usIPA,
                        remoteAudioURL: entry.usAudioURL,
                        localAudioFile: "\(entry.word)_us"
                    )
                }
            }

            phonemeButtons(for: preferredIPA(for: entry))
        }
    }

    private func meaningGroupSection(
        _ group: MeaningGroup,
        visibleEntries: [DictionaryEntry]
    ) -> some View {
        let chineseDefinitions = uniqueValues(
            visibleEntries.map(\.zhDefinition)
        )
        let countability = uniqueValues(
            group.entries.map(\.countability).filter { !$0.isEmpty }
        ).joined(separator: " or ")
        let inflections = uniqueValues(
            group.entries.flatMap(\.inflections)
        )

        return VStack(alignment: .leading, spacing: 24) {
            MarkdownText(
                partOfSpeechLine(
                    partOfSpeech: group.partOfSpeech,
                    countability: countability
                ),
                font: .system(size: 16, weight: .semibold)
            )

            if !inflections.isEmpty {
                MarkdownText(
                    inflections
                        .map(\.markdownEscaped)
                        .joined(separator: " \\| "),
                    font: .system(size: 16, weight: .semibold),
                    color: .primary
                )
            }

            plainDefinitionSection(
                title: "中文釋義",
                contents: chineseDefinitions,
                emptyText: "暫無中文釋義",
                contentFont: .system(size: 16, weight: .medium)
            )

            plainDefinitionSection(
                title: "英文釋義",
                contents: uniqueValues(visibleEntries.map(\.enDefinition)),
                emptyText: "No English definition available.",
                contentFont: .system(size: 16)
            )

            examplesSection(
                visibleEntries.flatMap { entry in
                    Array(entry.examples.prefix(1))
                }
            )
        }
    }

    private func preferredIPA(for entry: DictionaryEntry) -> String {
        if !entry.ukIPA.isEmpty {
            return entry.ukIPA
        }

        return entry.usIPA
    }

    private func partOfSpeechLine(
        partOfSpeech: String,
        countability: String
    ) -> String {
        if countability.isEmpty {
            return partOfSpeech.markdownEscaped
        }

        return "\(partOfSpeech.markdownEscaped) \\[ \(countability.markdownEscaped) \\]"
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
            .font(.system(size: 16, weight: .semibold))
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
                    .font(.system(size: 16))
                    .foregroundStyle(.primary)
                MarkdownText(
                    "**\(region.markdownEscaped)**",
                    font: .system(size: 16, weight: .semibold),
                    color: .primary
                )
                if !ipa.isEmpty {
                    MarkdownText(
                        ipa.markdownEscaped,
                        font: .system(size: 16, design: .rounded),
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

    private func plainDefinitionSection(
        title: String,
        contents: [String],
        emptyText: String,
        contentFont: Font
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle(title)

            if contents.isEmpty {
                MarkdownText(
                    emptyText.markdownEscaped,
                    font: contentFont,
                    lineSpacing: 5
                )
            } else {
                ForEach(Array(contents.enumerated()), id: \.offset) { _, content in
                    MarkdownText(
                        content.markdownEscaped,
                        font: contentFont,
                        lineSpacing: 5
                    )
                }
            }
        }
    }

    private func examplesSection(_ examples: [DictionaryExample]) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("例句")

            if examples.isEmpty {
                MarkdownText(
                    "暫無例句",
                    color: .primary
                )
            } else {
                ForEach(examples.prefix(1)) { example in
                    VStack(alignment: .leading, spacing: 8) {
                        MarkdownText(
                            example.english.markdownEscaped,
                            font: .system(size: 16, weight: .medium)
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
    }

    private func linkedWordsSection(title: String, words: [String]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle(title)

            PhonemeFlowLayout(spacing: 8) {
                ForEach(words.prefix(20), id: \.self) { word in
                    Button {
                        onSelectWord?(word)
                    } label: {
                        Text(word)
                            .font(.system(size: 16, weight: .medium))
                            .underline()
                            .foregroundStyle(Color.accentColor)
                            .padding(.vertical, 4)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .disabled(onSelectWord == nil)
                    .accessibilityLabel("查詢同義詞 \(word)")
                }
            }
        }
    }

    private func referenceSection(for entry: DictionaryEntry) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("Reference")

            Button {
                if let url = cambridgeReferenceURL(for: entry.word) {
                    openURL(url)
                }
            } label: {
                Text("Cambridge Dictionary")
                    .font(.system(size: 16, weight: .medium))
                    .underline()
                    .foregroundStyle(Color.accentColor)
                    .padding(.vertical, 4)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(cambridgeReferenceURL(for: entry.word) == nil)
        }
    }

    private func cambridgeReferenceURL(for word: String) -> URL? {
        let normalizedWord = word
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        guard !normalizedWord.isEmpty,
              let encodedWord = normalizedWord.addingPercentEncoding(
                  withAllowedCharacters: .urlPathAllowed
              ) else {
            return nil
        }

        return URL(
            string: "https://dictionary.cambridge.org/dictionary/english-chinese-traditional/\(encodedWord)"
        )
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
