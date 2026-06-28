import SwiftUI

struct PersonalEntryEditView: View {
    @Binding var draft: EditablePersonalDictionaryEntry
    let isSaving: Bool
    var onSave: () -> Void
    var onCancel: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                wordSection
                pronunciationSection
                sensesSection
                sourceSection
            }
            .formStyle(.grouped)
            .navigationTitle("編輯字典筆記")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") {
                        onCancel()
                    }
                    .disabled(isSaving)
                }

                ToolbarItem(placement: .confirmationAction) {
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
            }
        }
    }

    private var wordSection: some View {
        Section {
            LabeledContent("查詢字") {
                Text(draft.word)
                    .textSelection(.enabled)
            }
        } footer: {
            Text("版面模板、標題和分隔線由 App 固定產生；這裡只編輯模板中的內容欄位。")
        }
    }

    private var pronunciationSection: some View {
        Section("音標") {
            editableTextField("UK IPA", text: $draft.ukIPA)
            editableTextField("US IPA", text: $draft.usIPA)

            VStack(alignment: .leading, spacing: 8) {
                Text("音素預覽")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                let ipa = draft.ukIPA.isEmpty ? draft.usIPA : draft.ukIPA
                if ipa.isEmpty {
                    Text("儲存 IPA 後，查詢結果會自動拆成可點擊音素。")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text(IPATokenizer.phonemes(in: ipa).joined(separator: "  "))
                        .font(.system(.body, design: .rounded))
                        .foregroundStyle(Color.accentColor)
                        .textSelection(.enabled)
                }
            }
        }
    }

    private var sensesSection: some View {
        Section {
            ForEach($draft.senses) { $sense in
                senseEditor(sense: $sense)
            }

            Button {
                draft.senses.append(EditablePersonalDictionarySense())
            } label: {
                Label("新增詞義", systemImage: "plus.circle")
            }
        } header: {
            Text("詞義")
        } footer: {
            Text("每個詞義會自動顯示為：詞性、中文釋義、英文釋義、例句。例句每個詞義只保留一組。")
        }
    }

    private var sourceSection: some View {
        Section("私人來源備註") {
            editableTextField("來源 URL", text: $draft.sourceURL)
            VStack(alignment: .leading, spacing: 8) {
                Text("備註")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                TextEditor(text: $draft.sourceNote)
                    .frame(minHeight: 72)
            }
        }
    }

    private func senseEditor(
        sense: Binding<EditablePersonalDictionarySense>
    ) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("詞義")
                    .font(.headline)

                Spacer()

                if draft.senses.count > 1 {
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
        .padding(.vertical, 8)
    }

    private func editableTextField(
        _ title: String,
        text: Binding<String>
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            TextField(title, text: text, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(1...3)
        }
    }

    private func editableTextEditor(
        _ title: String,
        text: Binding<String>
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            TextEditor(text: text)
                .frame(minHeight: 86)
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
