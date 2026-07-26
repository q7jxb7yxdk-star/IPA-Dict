import Combine
import SwiftUI
import Translation
#if os(iOS)
import UIKit
#endif

@MainActor
final class DictionarySearchViewModel: ObservableObject {
    @Published var query = ""
    @Published private(set) var entries: [DictionaryEntry] = []
    @Published private(set) var entriesAwaitingTranslation: [DictionaryEntry] = []
    @Published private(set) var suggestions: [String] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var searchedWord = ""

    private let service: DictionaryService
    private var searchTask: Task<Void, Never>?
    private var suggestionTask: Task<Void, Never>?
    private var submittedSearchTask: Task<Void, Never>?

    init(service: DictionaryService? = nil) {
        self.service = service ?? DictionaryService()
    }

    func search(word rawWord: String? = nil) {
        submittedSearchTask?.cancel()
        submittedSearchTask = nil
        performSearch(word: rawWord)
    }

    func searchAfterTextFieldSubmit(word rawWord: String) {
        submittedSearchTask?.cancel()
        submittedSearchTask = Task { [weak self] in
            await Task.yield()
            guard !Task.isCancelled, let self else { return }
            submittedSearchTask = nil
            performSearch(word: rawWord)
        }
    }

    private func performSearch(word rawWord: String? = nil) {
        let submittedQuery = (rawWord ?? query)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        query = ""

        guard !submittedQuery.isEmpty else {
            entries = []
            errorMessage = DictionaryServiceError.invalidWord.localizedDescription
            return
        }

        searchTask?.cancel()
        suggestionTask?.cancel()
        suggestions = []
        isLoading = true
        errorMessage = nil
        entries = []
        entriesAwaitingTranslation = []
        searchedWord = submittedQuery.lowercased()

        searchTask = Task {
            do {
                let results = try await service.lookup(word: submittedQuery)
                try Task.checkCancellation()
                searchedWord = results.first?.word.lowercased()
                    ?? submittedQuery.lowercased()
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

    func updateSuggestions(for rawQuery: String) {
        let query = rawQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        suggestionTask?.cancel()

        guard !query.isEmpty else {
            suggestions = []
            return
        }

        suggestionTask = Task {
            try? await Task.sleep(for: .milliseconds(120))
            guard !Task.isCancelled else { return }
            let words = await service.suggestions(prefix: query)
            guard !Task.isCancelled else { return }
            suggestions = words
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
        submittedSearchTask?.cancel()
        submittedSearchTask = nil
        entries = []
        entriesAwaitingTranslation = []
        errorMessage = nil
        isLoading = false
        searchTask?.cancel()
        suggestionTask?.cancel()
        suggestions = []
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
    @StateObject private var bookmarkStore = BookmarkStore()
    @State private var translationConfiguration: TranslationSession.Configuration?
    @State private var presentedResult: DictionarySearchResult?
    @State private var isShowingResult = false
    @State private var showsClearHistoryConfirmation = false
    @State private var showsClearBookmarksConfirmation = false
    @State private var showsHistorySuggestions = false
    @State private var selectedHistoryIndex: Int?
    @State private var hasActivatedSearch = false
    @State private var hasCompletedInitialAppearance = false
    @State private var showsBookmarkSheet = false
    @State private var sidebarDestination = SidebarDestination.dictionary
    @State private var sidebarVisibility = NavigationSplitViewVisibility.all
    @FocusState private var focusedSearchField: SearchField?

    var body: some View {
        dictionaryNavigation
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.searchBackground.ignoresSafeArea())
        .bookmarkPresentation(isPresented: $showsBookmarkSheet) {
            NavigationStack {
                bookmarkListContent(
                    emptyDescription: "在查詢結果頁點擊星號，就可以把單字加入書簽。"
                )
                .navigationTitle("書簽")
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("完成") {
                            showsBookmarkSheet = false
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var dictionaryNavigation: some View {
        if usesPhoneNavigation {
            NavigationStack {
                dictionaryRoot
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            NavigationSplitView(columnVisibility: $sidebarVisibility) {
                bookmarkSidebar
            } detail: {
                NavigationStack {
                    switch sidebarDestination {
                    case .dictionary:
                        dictionaryRoot
                    case .ipaGuide:
                        IPAGuideView()
                    }
                }
            }
            .navigationSplitViewStyle(.balanced)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .onAppear {
                sidebarVisibility = .all
            }
        }
    }

    private var dictionaryRoot: some View {
        homeContent
            .background(Color.searchBackground)
            .navigationTitle(homeNavigationTitle)
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(
                usesPhoneNavigation ? .hidden : .visible,
                for: .navigationBar
            )
            #endif
            .navigationDestination(isPresented: $isShowingResult) {
                if let presentedResult {
                    resultContent(presentedResult)
                }
            }
            .onChange(of: viewModel.entries) { _, entries in
                guard !entries.isEmpty else { return }
                let word = viewModel.searchedWord
                historyStore.add(word)
                presentedResult = DictionarySearchResult(
                    word: word,
                    entries: entries
                )
                if !isShowingResult {
                    isShowingResult = true
                }
                focusedSearchField = nil
                showsHistorySuggestions = false
                selectedHistoryIndex = nil
            }
            .onChange(of: isShowingResult) { _, isPresented in
                if !isPresented {
                    presentedResult = nil
                    viewModel.query = ""
                    viewModel.clearResult()
                }
            }
            .onChange(of: viewModel.entriesAwaitingTranslation) { _, entries in
                guard entries.contains(where: { !$0.hasCompleteChineseContent }) else {
                    if !entries.isEmpty {
                        viewModel.finishTranslation(with: entries)
                    }
                    translationConfiguration = nil
                    return
                }
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
            .confirmationDialog(
                "清除所有書簽？",
                isPresented: $showsClearBookmarksConfirmation,
                titleVisibility: .visible
            ) {
                Button("清除全部", role: .destructive) {
                    bookmarkStore.clear()
                }
                Button("取消", role: .cancel) {}
            } message: {
                Text("清除後無法復原。")
            }
            .onAppear {
                focusedSearchField = nil
                showsHistorySuggestions = false
                selectedHistoryIndex = nil
                hasActivatedSearch = false
                hasCompletedInitialAppearance = false

                Task { @MainActor in
                    await Task.yield()
                    focusedSearchField = nil
                    hasCompletedInitialAppearance = true
                }
            }
            .onChange(of: focusedSearchField) { _, focusedField in
                if focusedField != nil && hasCompletedInitialAppearance {
                    hasActivatedSearch = true
                    showsHistorySuggestions = true
                } else {
                    showsHistorySuggestions = false
                    selectedHistoryIndex = nil
                }
            }
            .onChange(of: viewModel.query) {
                selectedHistoryIndex = nil
                viewModel.updateSuggestions(for: viewModel.query)
                if focusedSearchField != nil && hasActivatedSearch {
                    showsHistorySuggestions = true
                }
            }
    }

    private var usesPhoneNavigation: Bool {
        #if os(iOS)
        UIDevice.current.userInterfaceIdiom == .phone
        #else
        false
        #endif
    }

    private var bookmarkSidebar: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(spacing: 4) {
                sidebarButton(
                    title: "字典",
                    systemImage: "book.closed",
                    destination: .dictionary
                )
                sidebarButton(
                    title: "IPA 發音表",
                    systemImage: "waveform",
                    destination: .ipaGuide
                )
            }
            .padding(.horizontal, 10)
            .padding(.top, 10)
            .padding(.bottom, 8)

            Divider()

            HStack {
                Text("書簽")
                    .font(.system(size: 22, weight: .bold))

                Spacer()

                if !bookmarkStore.words.isEmpty {
                    Button("清除") {
                        showsClearBookmarksConfirmation = true
                    }
                    .font(.system(size: 14))
                    .buttonStyle(.borderless)
                }
            }
            .padding(.horizontal, 18)
            .padding(.top, 18)
            .padding(.bottom, 10)

            Divider()

            bookmarkListContent(
                emptyDescription: "在查詢結果頁點擊星號，就可以把單字加入書簽。"
            )
        }
        .navigationTitle("書簽")
        .navigationSplitViewColumnWidth(min: 220, ideal: 260, max: 320)
        .frame(minWidth: 220, idealWidth: 260)
        .background(Color.searchBackground)
    }

    private func sidebarButton(
        title: String,
        systemImage: String,
        destination: SidebarDestination
    ) -> some View {
        Button {
            sidebarDestination = destination
        } label: {
            HStack(spacing: 10) {
                Image(systemName: systemImage)
                    .frame(width: 20)
                Text(title)
                    .font(.system(size: 14))
                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .contentShape(Rectangle())
            .background(
                sidebarDestination == destination
                    ? Color.accentColor.opacity(0.14)
                    : Color.clear,
                in: RoundedRectangle(cornerRadius: 8)
            )
        }
        .buttonStyle(.plain)
        .foregroundStyle(.primary)
    }

    @ViewBuilder
    private func bookmarkListContent(emptyDescription: String) -> some View {
        if bookmarkStore.words.isEmpty {
            ContentUnavailableView(
                "尚無書簽",
                systemImage: "star",
                description: Text(emptyDescription)
                    .font(.system(size: 14))
            )
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.horizontal, 12)
        } else {
            List {
                ForEach(bookmarkStore.words, id: \.self) { word in
                    HStack(spacing: 10) {
                        Button {
                            selectBookmarkedWord(word)
                        } label: {
                            HStack(spacing: 10) {
                                Image(systemName: "star.fill")
                                Text(word)
                                    .font(.system(size: 14))
                                Spacer()
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)

                        Button {
                            bookmarkStore.remove(word)
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.secondary)
                        }
                        .buttonStyle(.borderless)
                        .help("移除書簽")
                        .accessibilityLabel("移除 \(word) 書簽")
                    }
                }
            }
            .listStyle(.sidebar)
        }
    }

    private var homeContent: some View {
        ZStack(alignment: .top) {
            Color.searchBackground

            if !isShowingResult {
                VStack(spacing: 0) {
                    homeTitle
                    searchHeader(focus: .home)
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
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Color.searchBackground)
    }

    @ViewBuilder
    private var homeTitle: some View {
        #if os(iOS)
        HStack(spacing: 12) {
            Text("IPA Dictionary")
                .font(.system(size: 24, weight: .bold))
                .foregroundStyle(.primary)

            Spacer()

            if usesPhoneNavigation {
                NavigationLink {
                    IPAGuideView()
                } label: {
                    Image(systemName: "waveform")
                        .font(.system(size: 18, weight: .semibold))
                }
                .buttonStyle(.borderless)
                .foregroundStyle(.primary)
                .accessibilityLabel("打開 IPA 發音表")

                Button {
                    openBookmarks()
                } label: {
                    Image(systemName: "list.star")
                        .font(.system(size: 18, weight: .semibold))
                }
                .buttonStyle(.borderless)
                .foregroundStyle(.primary)
                .accessibilityLabel("打開書簽")
            }
        }
            .frame(maxWidth: 820, alignment: .leading)
            .padding(.horizontal)
            .padding(.top, 0)
            .padding(.bottom, 2)
        #endif
    }

    private var homeNavigationTitle: String {
        #if os(iOS)
        ""
        #else
        "IPA Dictionary"
        #endif
    }

    private func resultContent(_ result: DictionarySearchResult) -> some View {
        ZStack(alignment: .top) {
            VStack(spacing: 0) {
                searchHeader(focus: .result)
                Divider()

                ZStack {
                    WordDetailView(
                        entries: result.entries,
                        showsNavigationTitle: false,
                        onSelectWord: { word in
                            selectLinkedWord(word)
                        }
                    )

                    if viewModel.isLoading {
                        Color.searchBackground.opacity(0.88)
                            .ignoresSafeArea()

                        ContentUnavailableView {
                            ProgressView()
                            Text("正在查詢字典…")
                                .font(.system(size: 16))
                        }
                        .foregroundStyle(.primary)
                    } else if let errorMessage = viewModel.errorMessage {
                        VStack {
                            Spacer()

                            HStack(spacing: 10) {
                                Image(systemName: "exclamationmark.circle")
                                Text(errorMessage)
                                    .font(.system(size: 16))
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
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button {
                    bookmarkStore.toggle(result.word)
                } label: {
                    Image(
                        systemName: bookmarkStore.contains(result.word)
                            ? "star.fill"
                            : "star"
                    )
                }
                .help(
                    bookmarkStore.contains(result.word)
                        ? "移除書簽"
                        : "加入書簽"
                )
                .accessibilityLabel(
                    bookmarkStore.contains(result.word)
                        ? "移除書簽"
                        : "加入書簽"
                )

                if usesPhoneNavigation {
                    NavigationLink {
                        IPAGuideView()
                    } label: {
                        Image(systemName: "waveform")
                    }
                    .help("打開 IPA 發音表")
                    .accessibilityLabel("打開 IPA 發音表")

                    Button {
                        openBookmarks()
                    } label: {
                        Image(systemName: "list.star")
                    }
                    .help("打開書簽")
                    .accessibilityLabel("打開書簽")
                }
            }
        }
        #if os(iOS)
        .toolbar(.visible, for: .navigationBar)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private func translatePendingEntries(using session: TranslationSession) async {
        let pendingEntries = viewModel.entriesAwaitingTranslation
        guard !pendingEntries.isEmpty else { return }
        guard pendingEntries.contains(where: { !$0.hasCompleteChineseContent }) else {
            viewModel.finishTranslation(with: pendingEntries)
            return
        }

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

    private func searchHeader(focus: SearchField) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.primary)

            TextField(
                "輸入英文單字或中文釋義，例如 apple／蘋果",
                text: $viewModel.query
            )
                .textFieldStyle(.plain)
                .font(.system(size: 16))
                .foregroundStyle(.primary)
                .focused($focusedSearchField, equals: focus)
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
            .font(.system(size: 16))
            .buttonStyle(.bordered)
            .foregroundStyle(.primary)
            .disabled(viewModel.isLoading)
        }
        .padding(12)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .contentShape(RoundedRectangle(cornerRadius: 16))
        .padding(.horizontal)
        .padding(.top, searchHeaderTopPadding)
        .padding(.bottom, searchHeaderBottomPadding)
        .frame(maxWidth: 820)
        .zIndex(10)
    }

    private var searchHeaderTopPadding: CGFloat {
        #if os(iOS)
        2
        #else
        16
        #endif
    }

    private var searchHeaderBottomPadding: CGFloat {
        #if os(iOS)
        10
        #else
        16
        #endif
    }

    @ViewBuilder
    private var floatingHistoryDropdown: some View {
        if showsHistoryDropdown {
            historyDropdown
                .padding(.horizontal)
                .padding(.top, historyDropdownTopPadding)
                .frame(maxWidth: 820)
                .transition(
                    .opacity.combined(with: .move(edge: .top))
                )
                .zIndex(20)
        }
    }

    private var historyDropdownTopPadding: CGFloat {
        #if os(iOS)
        isShowingResult ? 70 : 92
        #else
        74
        #endif
    }

    @ViewBuilder
    private var statusContent: some View {
        if viewModel.isLoading {
            ContentUnavailableView {
                ProgressView()
                Text("正在查詢字典…")
                    .font(.system(size: 16))
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
                    .font(.system(size: 16))
            )
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(Rectangle())
            .onTapGesture {
                dismissSearchSuggestions()
            }
        }
    }

    private var homeSectionTitleFontSize: CGFloat {
        #if os(iOS)
        18
        #else
        22
        #endif
    }

    private var emptyStateDescriptionFontSize: CGFloat {
        #if os(iOS)
        14
        #else
        16
        #endif
    }

    private var homeVerticalPadding: CGFloat {
        #if os(iOS)
        18
        #else
        28
        #endif
    }

    private var historyEmptyMinHeight: CGFloat {
        #if os(iOS)
        170
        #else
        280
        #endif
    }

    private var historyContent: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("最近搜尋")
                    .font(.system(size: homeSectionTitleFontSize, weight: .bold))

                Spacer()

                if !historyStore.words.isEmpty {
                    Button("清除記錄") {
                        showsClearHistoryConfirmation = true
                    }
                    .font(.system(size: 14))
                    .buttonStyle(.borderless)
                    .foregroundStyle(.primary)
                }
            }
            .frame(maxWidth: 760)
            .padding(.horizontal, 24)
            .padding(.top, homeVerticalPadding)

            if filteredHistory.isEmpty {
                ContentUnavailableView(
                    historyStore.words.isEmpty ? "尚無搜尋記錄" : "沒有符合的搜尋記錄",
                    systemImage: "clock.arrow.circlepath",
                    description: Text(
                        historyStore.words.isEmpty
                            ? "成功查詢的英文單字會顯示在這裡。"
                            : "請輸入其他字母或直接查詢新單字。"
                    )
                    .font(.system(size: emptyStateDescriptionFontSize))
                )
                .foregroundStyle(.primary)
                .frame(
                    maxWidth: .infinity,
                    minHeight: historyEmptyMinHeight,
                    maxHeight: .infinity
                )
            } else {
                List {
                    ForEach(filteredHistory, id: \.self) { word in
                        Button {
                            viewModel.search(word: word)
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "clock.arrow.circlepath")
                                Text(word)
                                    .font(.system(size: 14))
                                Spacer()
                                Image(systemName: "arrow.up.left")
                            }
                            .foregroundStyle(.primary)
                            .padding(.vertical, 8)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                            Button(role: .destructive) {
                                historyStore.remove(word)
                            } label: {
                                Label("刪除", systemImage: "trash")
                            }
                        }
                        .accessibilityHint("向左滑動可刪除此搜尋記錄")
                        .listRowBackground(Color.clear)
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
                .frame(maxWidth: 760, maxHeight: .infinity)
            }

        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Color.searchBackground)
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
            && !dropdownWords.isEmpty
            && !viewModel.isLoading
    }

    private var historyDropdownHeight: CGFloat {
        CGFloat(min(dropdownWords.count, 10)) * 42
    }

    private var dropdownWords: [String] {
        isShowingDictionarySuggestions ? viewModel.suggestions : historyStore.words
    }

    private var isShowingDictionarySuggestions: Bool {
        !viewModel.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var historyDropdown: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(
                        Array(dropdownWords.enumerated()),
                        id: \.element
                    ) { index, word in
                        Button {
                            selectDropdownWord(word)
                        } label: {
                            HStack(spacing: 12) {
                                Image(
                                    systemName: isShowingDictionarySuggestions
                                        ? "book"
                                        : "clock.arrow.circlepath"
                                )
                                Text(word)
                                    .font(.system(size: 14))
                                Spacer()
                                Image(systemName: "arrow.up.left")
                            }
                            .foregroundStyle(.primary)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 10)
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

                        if index < dropdownWords.count - 1 {
                            Divider()
                        }
                    }
                }
            }
            .onChange(of: selectedHistoryIndex) { _, index in
                guard let index,
                      dropdownWords.indices.contains(index) else {
                    return
                }
                withAnimation(.easeInOut(duration: 0.12)) {
                    proxy.scrollTo(dropdownWords[index], anchor: .center)
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
        guard !viewModel.isLoading else { return }

        let submittedWord: String
        if let selectedHistoryIndex,
           dropdownWords.indices.contains(selectedHistoryIndex) {
            submittedWord = dropdownWords[selectedHistoryIndex]
        } else {
            submittedWord = viewModel.query
        }

        focusedSearchField = nil
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        viewModel.searchAfterTextFieldSubmit(word: submittedWord)
    }

    private func selectDropdownWord(_ word: String) {
        focusedSearchField = nil
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        viewModel.search(word: word)
    }

    private func selectLinkedWord(_ word: String) {
        focusedSearchField = nil
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        hasActivatedSearch = false
        viewModel.search(word: word)
    }

    private func selectBookmarkedWord(_ word: String) {
        sidebarDestination = .dictionary
        focusedSearchField = nil
        showsHistorySuggestions = false
        showsBookmarkSheet = false
        selectedHistoryIndex = nil
        hasActivatedSearch = false
        viewModel.search(word: word)
    }

    private func openBookmarks() {
        dismissSearchSuggestions()
        showsBookmarkSheet = true
    }

    private func activateSearchSuggestions() {
        hasActivatedSearch = true
        focusedSearchField = isShowingResult ? .result : .home
        selectedHistoryIndex = nil
        viewModel.updateSuggestions(for: viewModel.query)
        showsHistorySuggestions = !viewModel.isLoading
    }

    private func handleEscapeKey() -> KeyPress.Result {
        if showsHistoryDropdown {
            showsHistorySuggestions = false
            selectedHistoryIndex = nil
        } else {
            focusedSearchField = nil
        }
        return .handled
    }

    private func moveHistorySelection(for key: KeyEquivalent) {
        guard showsHistoryDropdown else {
            activateSearchSuggestions()
            selectedHistoryIndex = key == .upArrow
                ? dropdownWords.indices.last
                : dropdownWords.indices.first
            return
        }

        guard !dropdownWords.isEmpty else {
            selectedHistoryIndex = nil
            return
        }

        switch key {
        case .downArrow:
            let nextIndex = (selectedHistoryIndex ?? -1) + 1
            selectedHistoryIndex = min(
                nextIndex,
                dropdownWords.count - 1
            )
        case .upArrow:
            let previousIndex = (
                selectedHistoryIndex ?? dropdownWords.count
            ) - 1
            selectedHistoryIndex = max(previousIndex, 0)
        default:
            break
        }
    }

    private func dismissSearchSuggestions() {
        focusedSearchField = nil
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        hasActivatedSearch = false
    }
}

private enum SidebarDestination: Hashable {
    case dictionary
    case ipaGuide
}

private enum SearchField: Hashable {
    case home
    case result
}

private struct DictionarySearchResult: Identifiable, Hashable {
    let id = UUID()
    let word: String
    let entries: [DictionaryEntry]
}

private extension DictionaryEntry {
    var hasCompleteChineseContent: Bool {
        !zhDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && examples.allSatisfy {
                !$0.chinese.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            }
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

private extension View {
    @ViewBuilder
    func bookmarkPresentation<Content: View>(
        isPresented: Binding<Bool>,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        #if os(iOS)
        fullScreenCover(isPresented: isPresented, content: content)
        #else
        sheet(isPresented: isPresented, content: content)
        #endif
    }
}

#Preview {
    DictionarySearchView()
}
