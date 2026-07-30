import SwiftUI

struct LegalInformationView: View {
    private let privacyPolicyURL = URL(
        string: "https://q7jxb7yxdk-star.github.io/IPA-Dict/privacy-policy/"
    )!
    private let dictionaryLicensesURL = URL(
        string: "https://github.com/q7jxb7yxdk-star/IPA-Dict/blob/main/IPA%20Dict/Data/DictionaryLicenses.md"
    )!
    private let supportURL = URL(
        string: "https://github.com/q7jxb7yxdk-star/IPA-Dict/issues"
    )!

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                MarkdownText("# 私隱與資料授權")

                section(
                    title: "私隱政策",
                    text: "IPA Dict 不設使用者帳戶、不顯示廣告、不使用分析 SDK，亦不追蹤使用者。搜尋記錄與書簽透過 Apple 的 iCloud Key-Value Storage，在登入同一 Apple ID 的裝置間同步；開發者無法查看這些資料。"
                )

                section(
                    title: "網絡服務",
                    text: "查詢本地詞庫沒有結果時，App 可能把查詢詞傳送至 Free Dictionary API。使用者主動打開 Cambridge Dictionary 參考或 GitHub 問題報告時，相關網站會按其私隱政策處理網絡資料。"
                )

                section(
                    title: "錯誤報告",
                    text: "App 會先在本機 Documents 目錄記錄報告。只有使用者在 GitHub 頁面確認提交後，報告內容才會傳送至 GitHub。"
                )

                section(
                    title: "字典資料授權",
                    text: "本地詞庫使用 FreeDict、Open English WordNet、Wiktionary／Kaikki、CMUdict、MFA、Tatoeba 及 WikiMatrix 等可再散布來源；詳細條款見下方連結。"
                )

                VStack(alignment: .leading, spacing: 12) {
                    legalLink("完整私隱政策", destination: privacyPolicyURL)
                    legalLink("字典資料授權", destination: dictionaryLicensesURL)
                    legalLink("支援與問題回報", destination: supportURL)
                }
                .font(.system(size: 16))

                Text("最後更新：2026-07-30")
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: 820, alignment: .leading)
            .padding(.horizontal, 20)
            .padding(.vertical, 18)
            .frame(maxWidth: .infinity, alignment: .center)
        }
        .background(Color.legalBackground)
        .navigationTitle("私隱與授權")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private func section(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            MarkdownText("## \(title)")
            Text(text)
                .font(.system(size: 16))
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func legalLink(_ title: String, destination: URL) -> some View {
        Link(destination: destination) {
            HStack(spacing: 8) {
                Text(title)
                    .underline()
                Image(systemName: "arrow.up.right.square")
            }
        }
        .accessibilityLabel("打開\(title)")
    }
}

private extension Color {
    static var legalBackground: Color {
        #if os(macOS)
        Color(nsColor: .windowBackgroundColor)
        #else
        Color(uiColor: .systemGroupedBackground)
        #endif
    }
}

#Preview {
    NavigationStack {
        LegalInformationView()
    }
}
