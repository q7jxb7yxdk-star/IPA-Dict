import Combine
import SwiftUI
import Translation

@MainActor
final class DictionarySearchViewModel: ObservableObject {
    @Published var query = ""
    @Published private(set) var entries: [DictionaryEntry] = []
    @Published private(set) var entriesAwaitingTranslation: [DictionaryEntry] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var searchedWord = ""

    private let service: DictionaryService
    private var searchTask: Task<Void, Never>?

    init(service: DictionaryService? = nil) {
        self.service = service ?? DictionaryService()
    }

    func search(word rawWord: String? = nil) {
        let submittedQuery = (rawWord ?? query)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        query = ""

        guard !submittedQuery.isEmpty else {
            entries = []
            errorMessage = DictionaryServiceError.invalidWord.localizedDescription
            return
        }

        searchTask?.cancel()
        isLoading = true
        errorMessage = nil
        entries = []
        entriesAwaitingTranslation = []
        searchedWord = submittedQuery.lowercased()

        searchTask = Task {
            do {
                let results = try await service.lookup(word: submittedQuery)
                try Task.checkCancellation()
                if results.allSatisfy(\.hasCompleteChineseContent) {
                    entries = results
                    isLoading = false
                } else {
                    entriesAwaitingTranslation = results
                }
            } catch is CancellationError {
                return
            } catch {
                entries = []
                if let urlError = error as? URLError {
                    errorMessage = networkMessage(for: urlError)
                } else {
                    errorMessage = error.localizedDescription
                }
            }
            if entriesAwaitingTranslation.isEmpty {
                isLoading = false
            }
        }
    }

    func finishTranslation(with translatedEntries: [DictionaryEntry]) {
        entries = translatedEntries
        entriesAwaitingTranslation = []
        isLoading = false
    }

    func failTranslation() {
        entries = entriesAwaitingTranslation
        entriesAwaitingTranslation = []
        isLoading = false
    }

    func clearResult() {
        entries = []
        entriesAwaitingTranslation = []
        errorMessage = nil
        isLoading = false
        searchTask?.cancel()
    }

    private func networkMessage(for error: URLError) -> String {
        switch error.code {
        case .notConnectedToInternet, .networkConnectionLost:
            "目前沒有網路連線，請連線後再試一次。"
        case .timedOut:
            "字典服務回應逾時，請稍後再試。"
        default:
            "無法連接字典服務，請稍後再試。"
        }
    }
}

struct DictionarySearchView: View {
    @StateObject private var viewModel = DictionarySearchViewModel()
    @StateObject private var historyStore = SearchHistoryStore()
    @State private var translationConfiguration: TranslationSession.Configuration?
    @State private var presentedResult: DictionarySearchResult?
    @State private var showsClearHistoryConfirmation = false
    @State private var showsHistorySuggestions = false
    @State private var selectedHistoryIndex: Int?
    @FocusState private var isSearchFocused: Bool

    var body: some View {
        NavigationStack {
            homeContent
                .background(Color.searchBackground)
                .navigationTitle("IPA Dictionary")
                .navigationDestination(item: $presentedResult) { result in
                    resultContent(result)
                }
                .onChange(of: viewModel.entries) { _, entries in
                    guard !entries.isEmpty else { return }
                    let word = viewModel.searchedWord
                    historyStore.add(word)
                    presentedResult = DictionarySearchResult(
                        word: word,
                        entries: entries
                    )
                    isSearchFocused = false
                    showsHistorySuggestions = false
                    selectedHistoryIndex = nil
                    viewModel.clearResult()
                }
                .onChange(of: presentedResult) { _, result in
                    if result == nil {
                        viewModel.query = ""
                        viewModel.clearResult()
                    }
                }
                .onChange(of: viewModel.entriesAwaitingTranslation) { _, entries in
                    guard !entries.isEmpty else { return }
                    translationConfiguration = TranslationSession.Configuration(
                        source: Locale.Language(identifier: "en"),
                        target: Locale.Language(identifier: "zh-Hant")
                    )
                }
                .translationTask(translationConfiguration) { session in
                    await translatePendingEntries(using: session)
                }
                .confirmationDialog(
                    "清除所有搜尋記錄？",
                    isPresented: $showsClearHistoryConfirmation,
                    titleVisibility: .visible
                ) {
                    Button("清除全部", role: .destructive) {
                        historyStore.clear()
                    }
                    Button("取消", role: .cancel) {}
                } message: {
                    Text("清除後無法復原。")
                }
                .onAppear {
                    isSearchFocused = false
                    showsHistorySuggestions = false
                    selectedHistoryIndex = nil
                }
                .onChange(of: isSearchFocused) { _, isFocused in
                    if isFocused {
                        showsHistorySuggestions = true
                    } else {
                        showsHistorySuggestions = false
                        selectedHistoryIndex = nil
                    }
                }
                .onChange(of: viewModel.query) {
                    selectedHistoryIndex = nil
                    if isSearchFocused {
                        showsHistorySuggestions = true
                    }
                }
        }
    }

    private var homeContent: some View {
        ZStack(alignment: .top) {
            VStack(spacing: 0) {
                searchHeader
                Divider()

                if viewModel.isLoading || viewModel.errorMessage != nil {
                    statusContent
                } else {
                    historyContent
                }
            }

            floatingHistoryDropdown
        }
    }

    private func resultContent(_ result: DictionarySearchResult) -> some View {
        ZStack(alignment: .top) {
            VStack(spacing: 0) {
                searchHeader
                Divider()

                ZStack {
                    WordDetailView(
                        entries: result.entries,
                        showsNavigationTitle: false
                    )

                    if viewModel.isLoading {
                        Color.searchBackground.opacity(0.88)
                            .ignoresSafeArea()

                        ContentUnavailableView {
                            ProgressView()
                            Text("正在查詢字典…")
                        }
                        .foregroundStyle(.primary)
                    } else if let errorMessage = viewModel.errorMessage {
                        VStack {
                            Spacer()

                            HStack(spacing: 10) {
                                Image(systemName: "exclamationmark.circle")
                                Text(errorMessage)
                                Spacer()
                            }
                            .foregroundStyle(.primary)
                            .padding()
                            .background(
                                .regularMaterial,
                                in: RoundedRectangle(cornerRadius: 14)
                            )
                            .padding()
                        }
                    }
                }
                .contentShape(Rectangle())
                .onTapGesture {
                    dismissSearchSuggestions()
                }
            }

            floatingHistoryDropdown
        }
        .background(Color.searchBackground)
        .navigationTitle(result.word)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private func translatePendingEntries(using session: TranslationSession) async {
        let pendingEntries = viewModel.entriesAwaitingTranslation
        guard !pendingEntries.isEmpty else { return }

        do {
            var translatedEntries: [DictionaryEntry] = []

            for entry in pendingEntries {
                let definition = try await translation(
                    for: entry.enDefinition,
                    existingTranslation: entry.zhDefinition,
                    using: session
                )

                var translatedExamples: [String] = []
                for example in entry.examples {
                    let translatedExample = try await translation(
                        for: example.english,
                        existingTranslation: example.chinese,
                        using: session
                    )
                    translatedExamples.append(translatedExample)
                }

                translatedEntries.append(
                    entry.translated(
                        definition: definition,
                        examples: translatedExamples
                    )
                )
            }

            viewModel.finishTranslation(with: translatedEntries)
        } catch {
            viewModel.failTranslation()
        }
    }

    private func translation(
        for sourceText: String,
        existingTranslation: String,
        using session: TranslationSession
    ) async throws -> String {
        if !existingTranslation.isEmpty {
            return existingTranslation
        }

        if let cached = await TranslationCache.shared.translation(for: sourceText) {
            return cached
        }

        let response = try await session.translate(sourceText)
        await TranslationCache.shared.store(
            response.targetText,
            for: sourceText
        )
        return response.targetText
    }

    private var searchHeader: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.primary)

            TextField("輸入英文單字，例如 apple", text: $viewModel.query)
                .textFieldStyle(.plain)
                .foregroundStyle(.primary)
                .focused($isSearchFocused)
                .submitLabel(.search)
                .autocorrectionDisabled()
                #if os(iOS)
                .textInputAutocapitalization(.never)
                #endif
                .onSubmit {
                    submitSearch()
                }
                .onKeyPress(.escape) {
                    handleEscapeKey()
                }
                .onKeyPress(
                    keys: [.upArrow, .downArrow],
                    phases: .down
                ) { keyPress in
                    moveHistorySelection(for: keyPress.key)
                    return .handled
                }

            if !viewModel.query.isEmpty {
                Button {
                    viewModel.query = ""
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.primary)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("清除搜尋")
            }

            Button("查詢") {
                submitSearch()
            }
            .buttonStyle(.bordered)
            .foregroundStyle(.primary)
            .disabled(viewModel.isLoading)
        }
        .padding(12)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .contentShape(RoundedRectangle(cornerRadius: 16))
        .simultaneousGesture(
            TapGesture().onEnded {
                isSearchFocused = true
                showsHistorySuggestions = true
            }
        )
        .padding(.horizontal)
        .padding(.vertical)
        .frame(maxWidth: 820)
        .zIndex(10)
    }

    @ViewBuilder
    private var floatingHistoryDropdown: some View {
        if showsHistoryDropdown {
            historyDropdown
                .padding(.horizontal)
                .padding(.top, 74)
                .frame(maxWidth: 820)
                .transition(
                    .opacity.combined(with: .move(edge: .top))
                )
                .zIndex(20)
        }
    }

    @ViewBuilder
    private var statusContent: some View {
        if viewModel.isLoading {
            ContentUnavailableView {
                ProgressView()
                Text("正在查詢字典…")
            }
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(Rectangle())
            .onTapGesture {
                dismissSearchSuggestions()
            }
        } else if let errorMessage = viewModel.errorMessage {
            ContentUnavailableView(
                "查詢失敗",
                systemImage: "exclamationmark.magnifyingglass",
                description: Text(errorMessage)
            )
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(Rectangle())
            .onTapGesture {
                dismissSearchSuggestions()
            }
        }
    }

    private var historyContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text("最近搜尋")
                        .font(.title2.bold())

                    Spacer()

                    if !historyStore.words.isEmpty {
                        Button("清除記錄") {
                            showsClearHistoryConfirmation = true
                        }
                        .buttonStyle(.borderless)
                        .foregroundStyle(.primary)
                    }
                }

                if filteredHistory.isEmpty {
                    ContentUnavailableView(
                        historyStore.words.isEmpty ? "尚無搜尋記錄" : "沒有符合的搜尋記錄",
                        systemImage: "clock.arrow.circlepath",
                        description: Text(
                            historyStore.words.isEmpty
                                ? "成功查詢的英文單字會顯示在這裡。"
                                : "請輸入其他字母或直接查詢新單字。"
                        )
                    )
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, minHeight: 280)
                } else {
                    LazyVStack(spacing: 0) {
                        ForEach(filteredHistory, id: \.self) { word in
                            Button {
                                viewModel.search(word: word)
                            } label: {
                                HStack(spacing: 12) {
                                    Image(systemName: "clock.arrow.circlepath")
                                    Text(word)
                                        .font(.body.weight(.medium))
                                    Spacer()
                                    Image(systemName: "arrow.up.left")
                                }
                                .foregroundStyle(.primary)
                                .padding(.vertical, 14)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)

                            if word != filteredHistory.last {
                                Divider()
                            }
                        }
                    }
                }
            }
            .frame(maxWidth: 760, alignment: .leading)
            .padding(.horizontal, 24)
            .padding(.vertical, 28)
            .frame(maxWidth: .infinity)
        }
        .contentShape(Rectangle())
        .onTapGesture {
            dismissSearchSuggestions()
        }
    }

    private var filteredHistory: [String] {
        let query = viewModel.query
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        guard !query.isEmpty else {
            return historyStore.words
        }
        return historyStore.words.filter { $0.localizedCaseInsensitiveContains(query) }
    }

    private var showsHistoryDropdown: Bool {
        showsHistorySuggestions
            && !filteredHistory.isEmpty
            && !viewModel.isLoading
    }

    private var historyDropdownHeight: CGFloat {
        CGFloat(min(filteredHistory.count, 10)) * 49
    }

    private var historyDropdown: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(
                        Array(filteredHistory.enumerated()),
                        id: \.element
                    ) { index, word in
                        Button {
                            selectHistoryWord(word)
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "clock.arrow.circlepath")
                                Text(word)
                                    .font(.body.weight(.medium))
                                Spacer()
                                Image(systemName: "arrow.up.left")
                            }
                            .foregroundStyle(.primary)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 12)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .background(
                            selectedHistoryIndex == index
                                ? Color.primary.opacity(0.09)
                                : Color.clear
                        )
                        .onHover { isHovering in
                            if isHovering {
                                selectedHistoryIndex = index
                            }
                        }
                        .accessibilityAddTraits(
                            selectedHistoryIndex == index
                                ? .isSelected
                                : []
                        )
                        .id(word)

                        if index < filteredHistory.count - 1 {
                            Divider()
                        }
                    }
                }
            }
            .onChange(of: selectedHistoryIndex) { _, index in
                guard let index,
                      filteredHistory.indices.contains(index) else {
                    return
                }
                withAnimation(.easeInOut(duration: 0.12)) {
                    proxy.scrollTo(filteredHistory[index], anchor: .center)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: historyDropdownHeight)
        .background(
            .regularMaterial,
            in: RoundedRectangle(cornerRadius: 14)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.primary.opacity(0.12), lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.16), radius: 14, y: 6)
    }

    private func submitSearch() {
        if let selectedHistoryIndex,
           filteredHistory.indices.contains(selectedHistoryIndex) {
            selectHistoryWord(filteredHistory[selectedHistoryIndex])
            return
        }

        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        viewModel.search()
    }

    private func selectHistoryWord(_ word: String) {
        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        viewModel.search(word: word)
    }

    private func handleEscapeKey() -> KeyPress.Result {
        if showsHistoryDropdown {
            showsHistorySuggestions = false
            selectedHistoryIndex = nil
        } else {
            isSearchFocused = false
        }
        return .handled
    }

    private func moveHistorySelection(for key: KeyEquivalent) {
        guard showsHistoryDropdown else {
            isSearchFocused = true
            showsHistorySuggestions = true
            selectedHistoryIndex = key == .upArrow
                ? filteredHistory.indices.last
                : filteredHistory.indices.first
            return
        }

        guard !filteredHistory.isEmpty else {
            selectedHistoryIndex = nil
            return
        }

        switch key {
        case .downArrow:
            let nextIndex = (selectedHistoryIndex ?? -1) + 1
            selectedHistoryIndex = min(
                nextIndex,
                filteredHistory.count - 1
            )
        case .upArrow:
            let previousIndex = (
                selectedHistoryIndex ?? filteredHistory.count
            ) - 1
            selectedHistoryIndex = max(previousIndex, 0)
        default:
            break
        }
    }

    private func dismissSearchSuggestions() {
        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
    }
}

private struct DictionarySearchResult: Identifiable, Hashable {
    let id = UUID()
    let word: String
    let entries: [DictionaryEntry]
}

private extension DictionaryEntry {
    var hasCompleteChineseContent: Bool {
        !zhDefinition.isEmpty
    }
}

private extension Color {
    static var searchBackground: Color {
        #if os(macOS)
        Color(nsColor: .windowBackgroundColor)
        #else
        Color(uiColor: .systemGroupedBackground)
        #endif
    }
}

#Preview {
    DictionarySearchView()
}
