import SwiftUI

struct IPAGuideView: View {
    private let audioPlayer = AudioPlayerService.shared

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                Text("IPA 發音表")
                    .font(.system(size: 24, weight: .bold))

                Text("音素用作發音說明；按下例字後的藍色完整 IPA，可播放整個例字。例字使用本 App 的簡化 IPA 寫法。")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                ipaSection(title: "元音（Vowels）", groups: Self.vowelGroups)
                ipaSection(title: "輔音（Consonants）", groups: Self.consonantGroups)
            }
            .frame(maxWidth: 820, alignment: .leading)
            .padding(.horizontal, 20)
            .padding(.vertical, 18)
            .frame(maxWidth: .infinity, alignment: .center)
        }
        .background(Color.guideBackground)
        .navigationTitle("IPA 發音表")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    @ViewBuilder
    private func ipaSection(title: String, groups: [IPAGroup]) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title)
                .font(.system(size: 18, weight: .bold))

            ForEach(groups) { group in
                VStack(alignment: .leading, spacing: 10) {
                    if let title = group.title {
                        Text(title)
                            .font(.system(size: 14, weight: .semibold))
                    }

                    ForEach(group.items) { item in
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Text("/\(item.symbol)/")
                                .font(.system(size: 16, weight: .semibold, design: .rounded))
                                .frame(minWidth: 54, alignment: .leading)

                            Text(attributedDescription(for: item))
                                .font(.system(size: 11))
                                .foregroundStyle(.primary)
                                .fixedSize(horizontal: false, vertical: true)
                                .environment(\.openURL, OpenURLAction { url in
                                    playExample(from: url, in: item)
                                })
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 2)
                    }
                }
            }
        }
    }

    private func attributedDescription(for item: IPAItem) -> AttributedString {
        var result = AttributedString(item.description)

        for (index, example) in item.examples.enumerated() {
            let label = "/\(example.ipa)/"
            guard let range = result.range(of: label),
                  let url = URL(string: "ipa-example://play/\(index)") else {
                continue
            }

            result[range].link = url
            result[range].foregroundColor = .accentColor
            result[range].underlineStyle = .single
        }

        return result
    }

    private func playExample(from url: URL, in item: IPAItem) -> OpenURLAction.Result {
        guard url.scheme == "ipa-example",
              let indexText = url.pathComponents.last,
              let index = Int(indexText),
              item.examples.indices.contains(index) else {
            return .systemAction
        }

        let example = item.examples[index]
        audioPlayer.speak(word: example.word, region: example.region)
        return .handled
    }
}

struct IPAGroup: Identifiable {
    let id: String
    let title: String?
    let items: [IPAItem]
}

struct IPAItem: Identifiable {
    let symbol: String
    let description: String
    let examples: [IPAExample]

    init(symbol: String, description: String, examples: [IPAExample] = []) {
        self.symbol = symbol
        self.description = description
        self.examples = examples
    }

    var id: String { symbol }
}

struct IPAExample: Hashable {
    let word: String
    let ipa: String
    let region: String

    init(word: String, ipa: String, region: String = "UK") {
        self.word = word
        self.ipa = ipa
        self.region = region
    }
}

extension IPAGuideView {
    static func reference(for symbol: String) -> IPAItem? {
        let aliases = [
            "ɛ": "e",
            "ɑ": "ɑː",
            "ɔ": "ɔː",
            "ɹ": "r"
        ]
        let lookupSymbol = aliases[symbol] ?? symbol

        return (vowelGroups + consonantGroups)
            .flatMap(\.items)
            .first { $0.symbol == lookupSymbol }
            .map { IPAItem(symbol: symbol, description: $0.description) }
    }

    static let vowelGroups = [
        IPAGroup(
            id: "close-monophthongs",
            title: "單元音（Monophthongs）\n閉元音（高元音）—— 口形最收攏，舌位最高",
            items: [
                IPAItem(symbol: "iː", description: "長元音。例字：E /iː/；嘴角向兩邊拉，聲音拉長。", examples: [.init(word: "E", ipa: "iː")]),
                IPAItem(symbol: "ɪ", description: "短元音。例字：sit /sɪt/；發音短促，口形比 /iː/ 放鬆。", examples: [.init(word: "sit", ipa: "sɪt")]),
                IPAItem(symbol: "uː", description: "長元音。例字：you /juː/；雙唇收圓突出，發音接近粵語「嗚」。", examples: [.init(word: "you", ipa: "juː")]),
                IPAItem(symbol: "ʊ", description: "短元音。例字：cook /kʊk/；發音短促，雙唇微圓。", examples: [.init(word: "cook", ipa: "kʊk")])
            ]
        ),
        IPAGroup(
            id: "mid-monophthongs",
            title: "中元音——口腔張開約一半，舌位高度適中",
            items: [
                IPAItem(symbol: "e", description: "短元音。例字：bed /bed/；口張開約一半。", examples: [.init(word: "bed", ipa: "bed")]),
                IPAItem(symbol: "ə", description: "短元音。例字：about /əˈbaʊt/；中央放鬆元音，常見於弱讀音節，舌頭與嘴唇保持放鬆。", examples: [.init(word: "about", ipa: "əˈbaʊt")]),
                IPAItem(symbol: "ɜː", description: "英式長元音。例字：bird /bɜːd/；口微張，聲音拉長，英式發音不帶 /r/ 音。", examples: [.init(word: "bird", ipa: "bɜːd")])
            ]
        ),
        IPAGroup(
            id: "open-monophthongs",
            title: "開口度較大的元音——口腔較張開，舌位較低",
            items: [
                IPAItem(symbol: "ɔː", description: "長元音。例字：英式 or /ɔː/；雙唇收圓，聲音拉長。", examples: [.init(word: "or", ipa: "ɔː")]),
                IPAItem(symbol: "æ", description: "短元音。例字：apple /ˈæp.əl/；嘴巴張開，舌位低而靠前。", examples: [.init(word: "apple", ipa: "ˈæp.əl")]),
                IPAItem(symbol: "ʌ", description: "短元音。例字：cup /kʌp/；口腔自然張開，舌位在中央偏後。", examples: [.init(word: "cup", ipa: "kʌp")]),
                IPAItem(symbol: "ɑː", description: "長元音。例字：英式 are /ɑː/；嘴巴張開，舌位低而靠後，聲音拉長。", examples: [.init(word: "are", ipa: "ɑː")]),
                IPAItem(symbol: "ɒ", description: "英式短元音。例字：odd /ɒd/；美式通常使用 /ɑː/ 或 /ɔː/ 一類的讀音。", examples: [.init(word: "odd", ipa: "ɒd")])
            ]
        ),
        IPAGroup(
            id: "r-colored-monophthongs",
            title: "美式 R-colored vowels（捲舌元音）",
            items: [
                IPAItem(symbol: "ɝː", description: "美式重讀長元音。例字：bird /bɝːd/；發中央元音時加入美式 /r/ 的舌形。", examples: [.init(word: "bird", ipa: "bɝːd", region: "US")]),
                IPAItem(symbol: "ɚ", description: "美式非重讀元音。例字：teacher /ˈtiː.tʃɚ/；常見於字尾的弱讀音節。", examples: [.init(word: "teacher", ipa: "ˈtiː.tʃɚ", region: "US")])
            ]
        ),
        IPAGroup(
            id: "diphthongs-to-i",
            title: "雙元音（Diphthongs）\n移向 /ɪ/ 的音",
            items: [
                IPAItem(symbol: "eɪ", description: "例字：英文字母 A /eɪ/。", examples: [.init(word: "A", ipa: "eɪ")]),
                IPAItem(symbol: "aɪ", description: "例字：eye /aɪ/。", examples: [.init(word: "eye", ipa: "aɪ")]),
                IPAItem(symbol: "ɔɪ", description: "例字：boy /bɔɪ/。", examples: [.init(word: "boy", ipa: "bɔɪ")])
            ]
        ),
        IPAGroup(
            id: "diphthongs-to-u",
            title: "移向 /ʊ/ 的音",
            items: [
                IPAItem(symbol: "əʊ", description: "英式。例字：goat /ɡəʊt/、oh /əʊ/。", examples: [.init(word: "goat", ipa: "ɡəʊt"), .init(word: "oh", ipa: "əʊ")]),
                IPAItem(symbol: "oʊ", description: "美式。例字：goat /ɡoʊt/、oh /oʊ/。", examples: [.init(word: "goat", ipa: "ɡoʊt", region: "US"), .init(word: "oh", ipa: "oʊ", region: "US")]),
                IPAItem(symbol: "aʊ", description: "例字：now /naʊ/。", examples: [.init(word: "now", ipa: "naʊ")])
            ]
        ),
        IPAGroup(
            id: "diphthongs-to-schwa",
            title: "移向中央元音 /ə/ 的音——主要見於英式讀音",
            items: [
                IPAItem(symbol: "ɪə", description: "例字：英式 ear /ɪə/；美式通常改用帶 /r/ 的讀音。", examples: [.init(word: "ear", ipa: "ɪə")]),
                IPAItem(symbol: "eə", description: "例字：英式 air /eə/；美式通常改用帶 /r/ 的讀音。", examples: [.init(word: "air", ipa: "eə")]),
                IPAItem(symbol: "ʊə", description: "例字：部分英式讀音的 tour /tʊə/；美式通常改用帶 /r/ 的讀音。", examples: [.init(word: "tour", ipa: "tʊə")])
            ]
        )
    ]

    static let consonantGroups = [
        IPAGroup(
            id: "plosives",
            title: "爆破音（Plosives）",
            items: [
                IPAItem(symbol: "p", description: "清音。例字：pen /pen/；雙唇閉合後放開，通常有較明顯送氣。", examples: [.init(word: "pen", ipa: "pen")]),
                IPAItem(symbol: "b", description: "濁音。例字：book /bʊk/；雙唇閉合後放開，聲帶振動，送氣通常比 /p/ 少。", examples: [.init(word: "book", ipa: "bʊk")]),
                IPAItem(symbol: "t", description: "清音。例字：time /taɪm/；舌尖抵住上齒齦後放開，通常有較明顯送氣。", examples: [.init(word: "time", ipa: "taɪm")]),
                IPAItem(symbol: "d", description: "濁音。例字：day /deɪ/；舌尖抵住上齒齦後放開，聲帶振動。", examples: [.init(word: "day", ipa: "deɪ")]),
                IPAItem(symbol: "k", description: "清音。例字：cat /kæt/；舌後部抵住軟顎後放開，通常有較明顯送氣。", examples: [.init(word: "cat", ipa: "kæt")]),
                IPAItem(symbol: "ɡ", description: "濁音。例字：go /ɡoʊ/；舌後部抵住軟顎後放開，聲帶振動。", examples: [.init(word: "go", ipa: "ɡoʊ", region: "US")])
            ]
        ),
        IPAGroup(
            id: "fricatives",
            title: "摩擦音（Fricatives）",
            items: [
                IPAItem(symbol: "f", description: "清音。例字：fish /fɪʃ/；上門牙輕觸下唇並吹氣。", examples: [.init(word: "fish", ipa: "fɪʃ")]),
                IPAItem(symbol: "v", description: "濁音。例字：very /ˈver.i/；上門牙輕觸下唇，聲帶振動。", examples: [.init(word: "very", ipa: "ˈver.i")]),
                IPAItem(symbol: "θ", description: "清音。例字：think /θɪŋk/；舌尖輕放在上下齒之間，讓氣流通過。", examples: [.init(word: "think", ipa: "θɪŋk")]),
                IPAItem(symbol: "ð", description: "濁音。例字：this /ðɪs/；舌尖輕放在上下齒之間，聲帶振動。", examples: [.init(word: "this", ipa: "ðɪs")]),
                IPAItem(symbol: "s", description: "清音。例字：see /siː/；上下齒靠近，讓氣流從舌面中央通過。", examples: [.init(word: "see", ipa: "siː")]),
                IPAItem(symbol: "z", description: "濁音。例字：zoo /zuː/；口形與 /s/ 相近，聲帶振動。", examples: [.init(word: "zoo", ipa: "zuː")]),
                IPAItem(symbol: "ʃ", description: "清音。例字：she /ʃiː/；雙唇微圓，舌頭稍向後縮。", examples: [.init(word: "she", ipa: "ʃiː")]),
                IPAItem(symbol: "ʒ", description: "濁音。例字：英式 measure /ˈmeʒ.ə/；口形與 /ʃ/ 相近，聲帶振動。", examples: [.init(word: "measure", ipa: "ˈmeʒ.ə")]),
                IPAItem(symbol: "h", description: "清音。例字：hat /hæt/；喉嚨放鬆，讓氣流呼出，聲帶通常不振動。", examples: [.init(word: "hat", ipa: "hæt")])
            ]
        ),
        IPAGroup(
            id: "affricates",
            title: "破擦音（Affricates）",
            items: [
                IPAItem(symbol: "tʃ", description: "清音。例字：英式 church /tʃɜːtʃ/；舌頭先阻塞氣流，再放開形成摩擦。", examples: [.init(word: "church", ipa: "tʃɜːtʃ")]),
                IPAItem(symbol: "dʒ", description: "濁音。例字：judge /dʒʌdʒ/；口形與 /tʃ/ 相近，聲帶振動。", examples: [.init(word: "judge", ipa: "dʒʌdʒ")])
            ]
        ),
        IPAGroup(
            id: "nasals",
            title: "鼻音（Nasals）",
            items: [
                IPAItem(symbol: "m", description: "濁音。例字：man /mæn/；雙唇閉合，氣流由鼻腔通過。", examples: [.init(word: "man", ipa: "mæn")]),
                IPAItem(symbol: "n", description: "濁音。例字：no /noʊ/；舌尖抵住上齒齦，氣流由鼻腔通過。", examples: [.init(word: "no", ipa: "noʊ", region: "US")]),
                IPAItem(symbol: "ŋ", description: "濁音。例字：sing /sɪŋ/；舌後部抵住軟顎，氣流由鼻腔通過。", examples: [.init(word: "sing", ipa: "sɪŋ")])
            ]
        ),
        IPAGroup(
            id: "approximants",
            title: "近音／半元音（Approximants / Semi-vowels）",
            items: [
                IPAItem(symbol: "l", description: "濁音。例字：light /laɪt/；舌尖接觸上齒齦，氣流從舌頭兩側通過。", examples: [.init(word: "light", ipa: "laɪt")]),
                IPAItem(symbol: "r", description: "濁音。例字：red /red/；字典常以 /r/ 簡寫英語近音 /ɹ/，舌頭向後收，通常不接觸上顎。", examples: [.init(word: "red", ipa: "red")]),
                IPAItem(symbol: "j", description: "濁音。例字：yes /jes/；半元音，起音接近短促的 /i/。", examples: [.init(word: "yes", ipa: "jes")]),
                IPAItem(symbol: "w", description: "濁音。例字：wet /wet/；半元音，雙唇先收圓再放開。", examples: [.init(word: "wet", ipa: "wet")])
            ]
        ),
        IPAGroup(
            id: "common-allophones",
            title: "口語常用特殊變音（進階參考）",
            items: [
                IPAItem(symbol: "ʔ", description: "喉塞音（glottal stop）。現代英式口語尤其常見；例字：button /ˈbʌt.ən/。部分說話者會在字尾 /t/ 或 /t/ 接音節鼻音前收緊聲門。", examples: [.init(word: "button", ipa: "ˈbʌt.ən")]),
                IPAItem(symbol: "ɾ", description: "閃音／彈音（flap）。常見於美式英語；例字：water /ˈwɑː.t̬ɚ/。當 /t/ 或 /d/ 位於重讀元音後、非重讀元音前，舌尖快速輕觸齒齦。", examples: [.init(word: "water", ipa: "ˈwɑː.t̬ɚ", region: "US")])
            ]
        )
    ]
}

private extension Color {
    static var guideBackground: Color {
        #if os(macOS)
        Color(nsColor: .textBackgroundColor)
        #else
        Color(uiColor: .systemBackground)
        #endif
    }
}

#Preview {
    NavigationStack {
        IPAGuideView()
    }
}
