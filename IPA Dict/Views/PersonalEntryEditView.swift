import SwiftUI

struct PersonalEntryEditView: View {
    @Binding var draft: EditablePersonalDictionaryEntry
    let isSaving: Bool
    var onSave: () -> Void
    var onCancel: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            editorToolbar

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    wordSection
                    pronunciationSection
                    sensesSection
                    sourceSection
                }
                .frame(maxWidth: 900, alignment: .leading)
                .padding(.horizontal, 28)
                .padding(.vertical, 24)
                .frame(maxWidth: .infinity, alignment: .center)
            }
        }
    }

    private var editorToolbar: some View {
        HStack(spacing: 12) {
            Button("取消") {
                onCancel()
            }
            .disabled(isSaving)

            Spacer()

            Text("編輯字典筆記")
                .font(.system(size: 18, weight: .semibold))

            Spacer()

            Button {
                onSave()
            } label: {
                if isSaving {
                    ProgressView()
                } else {
                    Text("儲存")
                }
            }
            .disabled(isSaving || !canSave)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
        .background(.regularMaterial)
    }

    private var wordSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("# \(draft.word)")
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .textSelection(.enabled)

            Text("版面模板、標題和分隔線由 App 固定產生；這裡只編輯模板中的內容欄位。")
                .font(.system(size: 16))
                .foregroundStyle(.secondary)
        }
    }

    private var pronunciationSection: some View {
        editorSection(title: "音標") {
            editableTextField("UK IPA", text: $draft.ukIPA)
            editableTextField("US IPA", text: $draft.usIPA)

            VStack(alignment: .leading, spacing: 8) {
                Text("音素預覽")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.secondary)

                let ipa = draft.ukIPA.isEmpty ? draft.usIPA : draft.ukIPA
                if ipa.isEmpty {
                    Text("儲存 IPA 後，查詢結果會自動拆成可點擊音素。")
                        .font(.system(size: 16))
                        .foregroundStyle(.secondary)
                } else {
                    Text(IPATokenizer.phonemes(in: ipa).joined(separator: "  "))
                        .font(.system(size: 16, design: .rounded))
                        .foregroundStyle(Color.accentColor)
                        .textSelection(.enabled)
                }
            }
        }
    }

    private var sensesSection: some View {
        editorSection(title: "詞義") {
            ForEach($draft.senses) { $sense in
                senseEditor(sense: $sense)
            }

            Button {
                draft.senses.append(EditablePersonalDictionarySense())
            } label: {
                Label("新增詞義", systemImage: "plus.circle")
            }

            Text("每個詞義會自動顯示為：詞性、中文釋義、英文釋義、例句。例句每個詞義只保留一組。")
                .font(.system(size: 16))
                .foregroundStyle(.secondary)
        }
    }

    private var sourceSection: some View {
        editorSection(title: "私人來源備註") {
            editableTextField("來源 URL", text: $draft.sourceURL)
            VStack(alignment: .leading, spacing: 8) {
                Text("備註")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.secondary)
                TextEditor(text: $draft.sourceNote)
                    .font(.system(size: 16))
                    .frame(minHeight: 90)
                    .padding(8)
                    .background(Color.editorFieldBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.primary.opacity(0.12), lineWidth: 0.5)
                    }
            }
        }
    }

    private func editorSection<Content: View>(
        title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("## \(title)")
                .font(.system(size: 22, weight: .bold))

            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func senseEditor(
        sense: Binding<EditablePersonalDictionarySense>
    ) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            if draft.senses.count > 1 {
                HStack {
                    Spacer()

                    Button(role: .destructive) {
                        draft.senses.removeAll { $0.id == sense.wrappedValue.id }
                    } label: {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.borderless)
                    .accessibilityLabel("刪除此詞義")
                }
            }

            editableTextField("詞性", text: sense.partOfSpeechLine)
            editableTextEditor("中文釋義", text: sense.zhDefinition)
            editableTextEditor("英文釋義", text: sense.enDefinition)
            editableTextEditor("例句英文", text: sense.exampleEnglish)
            editableTextEditor("例句中文", text: sense.exampleChinese)
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.editorCardBackground)
        )
    }

    private func editableTextField(
        _ title: String,
        text: Binding<String>
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.secondary)
            TextField("", text: text, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 16))
                .lineLimit(1...3)
        }
    }

    private func editableTextEditor(
        _ title: String,
        text: Binding<String>
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.secondary)
            TextEditor(text: text)
                .font(.system(size: 16))
                .frame(minHeight: 110)
                .padding(8)
                .background(Color.editorFieldBackground)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.primary.opacity(0.12), lineWidth: 0.5)
                }
        }
    }

    private var canSave: Bool {
        !draft.word.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && draft.senses.contains { sense in
                !sense.partOfSpeechLine.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                    || !sense.zhDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                    || !sense.enDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            }
    }
}

private extension Color {
    static var editorCardBackground: Color {
        #if os(macOS)
        Color(nsColor: .controlBackgroundColor)
        #else
        Color(uiColor: .secondarySystemGroupedBackground)
        #endif
    }

    static var editorFieldBackground: Color {
        #if os(macOS)
        Color(nsColor: .textBackgroundColor)
        #else
        Color(uiColor: .systemBackground)
        #endif
    }
}

#Preview {
    @Previewable @State var draft = EditablePersonalDictionaryEntry(
        entries: [.apple]
    )

    PersonalEntryEditView(
        draft: $draft,
        isSaving: false,
        onSave: {},
        onCancel: {}
    )
}
