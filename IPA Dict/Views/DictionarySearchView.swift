import Combine
import SwiftUI
import Translation
import UniformTypeIdentifiers

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

    func personalDraft(
        word: String,
        fallbackEntries: [DictionaryEntry]
    ) async throws -> EditablePersonalDictionaryEntry {
        try await service.personalDraft(
            word: word,
            fallbackEntries: fallbackEntries
        )
    }

    func savePersonalDraft(
        _ draft: EditablePersonalDictionaryEntry
    ) async throws -> [DictionaryEntry] {
        try await service.savePersonalDraft(draft)
    }

    func deletePersonalEntry(word: String) async throws {
        try await service.deletePersonalEntry(word: word)
    }

    func personalDatabaseURL() async throws -> URL {
        try await service.personalDatabaseURL()
    }

    func personalExportDocument() async throws -> PersonalDictionaryDocument {
        try await service.personalExportDocument()
    }

    func importPersonalDatabase(from url: URL) async throws {
        try await service.importPersonalDatabase(from: url)
    }

    func clearResult() {
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
    @State private var showsClearHistoryConfirmation = false
    @State private var showsClearBookmarksConfirmation = false
    @State private var showsHistorySuggestions = false
    @State private var selectedHistoryIndex: Int?
    @State private var hasActivatedSearch = false
    @State private var hasCompletedInitialAppearance = false
    @State private var editingDraft: EditablePersonalDictionaryEntry?
    @State private var isSavingPersonalEntry = false
    @State private var showsResetPersonalConfirmation = false
    @State private var personalActionError: String?
    @State private var personalActionMessage: String?
    @State private var exportDocument: PersonalDictionaryDocument?
    @State private var showsPersonalExport = false
    @State private var showsPersonalImport = false
    @FocusState private var isSearchFocused: Bool

    var body: some View {
        ZStack {
            dictionaryNavigation

            if editingDraft != nil {
                personalEditorOverlay
                    .transition(.opacity)
                    .zIndex(100)
            }
        }
        .alert(
            "私人字典操作失敗",
            isPresented: personalErrorAlertBinding
        ) {
            Button("好", role: .cancel) {
                personalActionError = nil
            }
        } message: {
            Text(personalActionError ?? "")
        }
        .alert(
            "私人字典",
            isPresented: personalMessageAlertBinding
        ) {
            Button("好", role: .cancel) {
                personalActionMessage = nil
            }
        } message: {
            Text(personalActionMessage ?? "")
        }
        .fileExporter(
            isPresented: $showsPersonalExport,
            document: exportDocument,
            contentType: .sqliteDatabase,
            defaultFilename: "PersonalDictionary.sqlite"
        ) { result in
            handlePersonalExportCompletion(result)
        }
        .fileImporter(
            isPresented: $showsPersonalImport,
            allowedContentTypes: [.sqliteDatabase, .data],
            allowsMultipleSelection: false
        ) { result in
            handlePersonalImportSelection(result)
        }
    }

    private var dictionaryNavigation: some View {
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
                .confirmationDialog(
                    "還原原始詞庫？",
                    isPresented: $showsResetPersonalConfirmation,
                    titleVisibility: .visible
                ) {
                    Button("刪除私人修改", role: .destructive) {
                        resetPersonalEntry()
                    }
                    Button("取消", role: .cancel) {}
                } message: {
                    Text("這會刪除此字的私人筆記，查詢結果會回到原本字典資料。")
                }
                .onAppear {
                    isSearchFocused = false
                    showsHistorySuggestions = false
                    selectedHistoryIndex = nil
                    hasActivatedSearch = false
                    hasCompletedInitialAppearance = false

                    Task { @MainActor in
                        await Task.yield()
                        isSearchFocused = false
                        hasCompletedInitialAppearance = true
                    }
                }
                .onChange(of: isSearchFocused) { _, isFocused in
                    if isFocused && hasCompletedInitialAppearance {
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
                    if isSearchFocused && hasActivatedSearch {
                        showsHistorySuggestions = true
                    }
                }
        }
    }

    private var personalEditorOverlay: some View {
        PersonalEntryEditView(
            draft: Binding(
                get: {
                    editingDraft ?? EditablePersonalDictionaryEntry(
                        word: "",
                        ukIPA: "",
                        usIPA: "",
                        senses: []
                    )
                },
                set: { editingDraft = $0 }
            ),
            isSaving: isSavingPersonalEntry,
            onSave: {
                savePersonalEntry()
            },
            onCancel: {
                if !isSavingPersonalEntry {
                    editingDraft = nil
                }
            }
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.searchBackground.ignoresSafeArea())
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
        .toolbar {
            ToolbarItem(placement: .secondaryAction) {
                personalDictionaryMenu
            }
        }
    }

    private var personalErrorAlertBinding: Binding<Bool> {
        Binding(
            get: { personalActionError != nil },
            set: { isPresented in
                if !isPresented {
                    personalActionError = nil
                }
            }
        )
    }

    private var personalMessageAlertBinding: Binding<Bool> {
        Binding(
            get: { personalActionMessage != nil },
            set: { isPresented in
                if !isPresented {
                    personalActionMessage = nil
                }
            }
        )
    }

    private func resultContent(_ result: DictionarySearchResult) -> some View {
        ZStack(alignment: .top) {
            VStack(spacing: 0) {
                searchHeader
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
            ToolbarItem(placement: .secondaryAction) {
                personalDictionaryMenu
            }

            ToolbarItemGroup(placement: .primaryAction) {
                if result.isPersonal {
                    Text("私人筆記")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Button("還原") {
                        showsResetPersonalConfirmation = true
                    }
                }

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

                Button("編輯") {
                    preparePersonalEditor(for: result)
                }
            }
        }
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
                .font(.system(size: 16))
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
                .onTapGesture {
                    activateSearchSuggestions()
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
        .simultaneousGesture(
            TapGesture().onEnded {
                activateSearchSuggestions()
            }
        )
        .padding(.horizontal)
        .padding(.vertical)
        .frame(maxWidth: 820)
        .zIndex(10)
    }

    private var personalDictionaryMenu: some View {
        Menu {
            Button {
                preparePersonalDictionaryExport()
            } label: {
                Label("匯出到 iCloud Drive", systemImage: "square.and.arrow.up")
            }

            Button {
                showsPersonalImport = true
            } label: {
                Label("從 iCloud Drive 匯入", systemImage: "square.and.arrow.down")
            }
        } label: {
            Label("私人字典", systemImage: "externaldrive")
        }
        .disabled(isSavingPersonalEntry)
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

    private var historyContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text("最近搜尋")
                        .font(.system(size: 22, weight: .bold))

                    Spacer()

                    if !historyStore.words.isEmpty {
                        Button("清除記錄") {
                            showsClearHistoryConfirmation = true
                        }
                        .font(.system(size: 16))
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
                        .font(.system(size: 16))
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
                                        .font(.system(size: 16, weight: .medium))
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

                Divider()
                    .padding(.top, 6)

                bookmarkContent
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

    private var bookmarkContent: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("書簽")
                    .font(.system(size: 22, weight: .bold))

                Spacer()

                if !bookmarkStore.words.isEmpty {
                    Button("清除書簽") {
                        showsClearBookmarksConfirmation = true
                    }
                    .font(.system(size: 16))
                    .buttonStyle(.borderless)
                    .foregroundStyle(.primary)
                }
            }

            if bookmarkStore.words.isEmpty {
                ContentUnavailableView(
                    "尚無書簽",
                    systemImage: "star",
                    description: Text("在查詢結果頁點擊星號，就可以把單字加入書簽。")
                        .font(.system(size: 16))
                )
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity, minHeight: 180)
            } else {
                LazyVStack(spacing: 0) {
                    ForEach(bookmarkStore.words, id: \.self) { word in
                        HStack(spacing: 12) {
                            Button {
                                viewModel.search(word: word)
                            } label: {
                                HStack(spacing: 12) {
                                    Image(systemName: "star.fill")
                                    Text(word)
                                        .font(.system(size: 16, weight: .medium))
                                    Spacer()
                                    Image(systemName: "arrow.up.left")
                                }
                                .foregroundStyle(.primary)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)

                            Button {
                                bookmarkStore.remove(word)
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.system(size: 16))
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.borderless)
                            .help("移除書簽")
                            .accessibilityLabel("移除 \(word) 書簽")
                        }
                        .padding(.vertical, 14)

                        if word != bookmarkStore.words.last {
                            Divider()
                        }
                    }
                }
            }
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
        CGFloat(min(dropdownWords.count, 10)) * 49
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
                                    .font(.system(size: 16, weight: .medium))
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
        if let selectedHistoryIndex,
           dropdownWords.indices.contains(selectedHistoryIndex) {
            selectDropdownWord(dropdownWords[selectedHistoryIndex])
            return
        }

        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        viewModel.search()
    }

    private func selectDropdownWord(_ word: String) {
        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        viewModel.search(word: word)
    }

    private func selectLinkedWord(_ word: String) {
        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        hasActivatedSearch = false
        viewModel.search(word: word)
    }

    private func preparePersonalEditor(for result: DictionarySearchResult) {
        Task { @MainActor in
            do {
                let draft = try await viewModel.personalDraft(
                    word: result.word,
                    fallbackEntries: result.entries
                )
                editingDraft = draft
            } catch {
                personalActionError = error.localizedDescription
            }
        }
    }

    private func savePersonalEntry() {
        guard let draft = editingDraft else { return }
        isSavingPersonalEntry = true

        Task { @MainActor in
            do {
                let savedEntries = try await viewModel.savePersonalDraft(draft)
                presentedResult = DictionarySearchResult(
                    word: EditablePersonalDictionaryEntry.normalizedWord(draft.word),
                    entries: savedEntries
                )
                editingDraft = nil
            } catch {
                personalActionError = error.localizedDescription
            }
            isSavingPersonalEntry = false
        }
    }

    private func resetPersonalEntry() {
        guard let result = presentedResult else { return }

        Task { @MainActor in
            do {
                try await viewModel.deletePersonalEntry(word: result.word)
                viewModel.search(word: result.word)
            } catch {
                personalActionError = error.localizedDescription
            }
        }
    }

    private func preparePersonalDictionaryExport() {
        Task { @MainActor in
            do {
                exportDocument = try await viewModel.personalExportDocument()
                showsPersonalExport = true
            } catch {
                personalActionError = error.localizedDescription
            }
        }
    }

    private func handlePersonalExportCompletion(
        _ result: Result<URL, Error>
    ) {
        switch result {
        case .success:
            personalActionMessage = "私人字典已匯出。你可以在 iCloud Drive／Files App 保留這個 SQLite 備份。"
        case .failure(let error):
            personalActionError = error.localizedDescription
        }
    }

    private func handlePersonalImportSelection(
        _ result: Result<[URL], Error>
    ) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            importPersonalDictionary(from: url)
        case .failure(let error):
            personalActionError = error.localizedDescription
        }
    }

    private func importPersonalDictionary(from url: URL) {
        Task { @MainActor in
            do {
                try await viewModel.importPersonalDatabase(from: url)
                personalActionMessage = "私人字典已匯入。原本本機私人字典已自動備份。"

                if let word = presentedResult?.word {
                    viewModel.search(word: word)
                }
            } catch {
                personalActionError = error.localizedDescription
            }
        }
    }

    private func activateSearchSuggestions() {
        hasActivatedSearch = true
        isSearchFocused = true
        selectedHistoryIndex = nil
        viewModel.updateSuggestions(for: viewModel.query)
        showsHistorySuggestions = !viewModel.isLoading
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
        isSearchFocused = false
        showsHistorySuggestions = false
        selectedHistoryIndex = nil
        hasActivatedSearch = false
    }
}

private struct DictionarySearchResult: Identifiable, Hashable {
    let id = UUID()
    let word: String
    let entries: [DictionaryEntry]

    var isPersonal: Bool {
        entries.contains { $0.isPersonal }
    }
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
