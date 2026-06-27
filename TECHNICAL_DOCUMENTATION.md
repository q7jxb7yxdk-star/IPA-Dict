# IPA Dict 技術文件

本文件說明 IPA Dict 的 app 架構、資料流程、字典查詢邏輯、發音系統、SQLite 詞庫與資料建置 pipeline。文件使用繁體中文敘述，並保留英文技術名稱，方便維護 SwiftUI 中英字典 app。

## 1. 系統概覽

IPA Dict 是一個 SwiftUI multi-platform app，核心由以下幾層組成：

```text
SwiftUI Views
    ↓
DictionarySearchViewModel
    ↓
DictionaryService
    ↓
LocalDictionaryService / CuratedDictionary / Dictionary API fallback
    ↓
DictionaryEntry models
```

查詢結果由 `WordDetailView` 顯示，發音由 `AudioPlayerService` 負責，搜尋歷史由 `SearchHistoryStore` 儲存在 `UserDefaults`。

## 2. 主要檔案

### App entry

- `IPA Dict/IPA_DictApp.swift`
- `IPA Dict/ContentView.swift`

負責啟動 SwiftUI app，並顯示主要搜尋頁。

### Views

- `DictionarySearchView.swift`
  - 搜尋頁與結果頁容器。
  - 管理搜尋輸入框、搜尋歷史、下拉選單、loading、error state。
  - 使用 `NavigationStack` 顯示查詢結果。

- `WordDetailView.swift`
  - 顯示字典詞條內容。
  - 負責 word heading、IPA button、phoneme buttons、詞性分組、中文釋義、英文釋義、例句、同義詞連結。

- `MarkdownText.swift`
  - 使用 Swift `AttributedString(markdown:)` 做簡化 Markdown rendering。
  - 支援 heading 樣式：
    - H1: 28 pt
    - H2: 22 pt
    - H3: 18 pt
    - 一般文字: 16 pt

- `PhonemeButton.swift`
  - 單一音素按鈕。
  - `IPATokenizer` 會把 IPA 字串拆成音素 token。
  - `PhonemeFlowLayout` 讓音素按鈕自動換行。

- `TranslatedText.swift`
  - Apple Translation framework 的輔助 view。
  - 用於缺少中文內容時的翻譯 fallback 顯示。

### Models

- `DictionaryEntry.swift`
  - app 內部主要字典資料模型。
  - 包含 word、UK IPA、US IPA、詞性、可數性、中文釋義、英文釋義、例句、同義詞、反義詞。
  - 也包含若干 curated static entries，例如 `apple`、`program`、`find`、`test`、`yes`、`itinerary`。

- `DictionaryAPIResponse.swift`
  - 線上 Dictionary API response 的 decoding model。
  - 負責把 API response 轉成 `DictionaryEntry`。

### Services

- `DictionaryService.swift`
  - 查詢入口。
  - 統一處理本地 SQLite、精選詞庫與線上 API fallback。

- `LocalDictionaryService.swift`
  - 使用 SQLite3 讀取 app bundle 內的 `dictionary.sqlite`。
  - 查詢 `entries` table。
  - 將 JSON examples / synonyms / antonyms decode 成 Swift model。
  - 會把簡體中文用 `StringTransform("Hans-Hant")` 轉成繁體。

- `AudioPlayerService.swift`
  - 使用 AVFoundation 播放本地 mp3。
  - 使用 `AVPlayer` 播放遠端 audio URL。
  - 使用 `AVSpeechSynthesizer` 作為整字發音 fallback。
  - 包含 `phonemeAudioMap`。
  - 支援複合音素依序播放多個本地 mp3。

- `SearchHistoryStore.swift`
  - 使用 `UserDefaults` 儲存最近搜尋字。
  - 預設最多保留 20 個。

- `TranslationCache.swift`
  - 快取 Apple Translation fallback 結果。

## 3. 字典查詢流程

`DictionarySearchViewModel.search(word:)` 是 UI 發起查詢的入口。

流程如下：

```text
使用者輸入 word
    ↓
DictionarySearchViewModel.search()
    ↓
DictionaryService.lookup(word:)
    ↓
1. 檢查 CuratedDictionary 是否有精選詞條
2. 查詢 LocalDictionaryService / SQLite
3. 如果 SQLite 有資料：
   - 有 curated：merge curated + local entries
   - 無 curated：返回 local entries
4. 如果 SQLite 沒資料但 curated 有資料：
   - 直接返回 curated entries
5. 如果 local / curated 都沒有：
   - 使用線上 Dictionary API fallback
```

目前 `CuratedDictionary` 的用途包括：

- 修正常用字錯誤。
- 補充 SQLite 缺字，例如 `itinerary`。
- 覆蓋不理想的詞性或中文釋義。
- 保留人工審核過的例句。

## 4. DictionaryEntry 資料模型

`DictionaryEntry` 欄位：

```swift
let word: String
let ukIPA: String
let usIPA: String
let ukAudioURL: URL?
let usAudioURL: URL?
let partOfSpeech: String
let countability: String
let inflections: [String]
let zhDefinition: String
let enDefinition: String
let examples: [DictionaryExample]
let synonyms: [String]
let antonyms: [String]
```

`DictionaryExample` 欄位：

```swift
let english: String
let chinese: String
```

`DictionaryEntry.normalizedPartOfSpeech(_:)` 會把不想直接顯示的詞性做 normalize，例如：

```swift
interjection -> exclamation
```

## 5. SQLite 詞庫

Bundled database：

```text
IPA Dict/Data/dictionary.sqlite
```

`LocalDictionaryService` 目前查詢 `entries` table，使用欄位：

```sql
word
uk_ipa
us_ipa
part_of_speech
countability
zh_definition
en_definition
examples_json
synonyms_json
antonyms_json
```

查詢條件：

```sql
WHERE normalized_word = ?
ORDER BY id
```

詞庫不是直接手改 SQLite 作為唯一來源；可重建修正會記錄在
`Tools/DictionaryBuilder/` 內的 JSON 帳本，再由建庫工具重建資料庫。
發音修正主要記錄於：

```text
Tools/DictionaryBuilder/pronunciation_review_resolutions.json
Tools/DictionaryBuilder/ipa_fallback_review_batches.json
```

2026-06-27 的 Wiktextract UK IPA 批次使用使用者提供的
`raw-wiktextract-data.jsonl.gz` 進行本地掃描。該批次只採用明確帶有
`Received-Pronunciation`、`UK` 或 `British` tag 的 IPA，並以
`word + part_of_speech + en_definition` 精準匹配現有詞條；US IPA
不會被複製或推斷成 UK IPA。該批次把 1,583 筆
`uk_ipa:generated_fallback` 替換為 verified source。

最近一次詞庫驗證結果：

```text
malformed_ipa_count = 0
suspicious_regional_ipa_count = 0
invalid_example_count = 0
semantic_correction_failure_count = 0
missing_part_of_speech_candidate_count = 0
```

app 顯示時，每個 entry 只取最多一個例句：

```swift
examples: Array(examples.prefix(1))
```

## 6. 查詢結果 UI

`WordDetailView` 會把同一個查詢字的 entries 依 part of speech 分組。

畫面結構：

```text
# word

UK /ipa/  US /ipa/

/ phoneme buttons /

---

noun [ C ]

## 中文釋義

...

## 英文釋義

...

## 例句

...

---

## 同義詞

linked words
```

同義詞不是 capsule chip，而是類似網頁的文字連結：

- accent color
- underline
- plain button style

點擊後透過 `onSelectWord` callback 回到 `DictionarySearchView` 執行新查詢。

## 7. 搜尋歷史與下拉選單

`SearchHistoryStore` 負責儲存最近搜尋：

- 儲存位置：`UserDefaults`
- key：`dictionarySearchHistory`
- 最大數量：20
- 新查詢會移到最前面。

`DictionarySearchView` 的下拉選單設計目標是類似 Google 搜尋框：

- 首次打開 app 不自動 focus。
- 首次打開 app 不自動彈出歷史。
- 使用者點擊輸入框 focus 後顯示歷史。
- Esc 可關閉下拉。
- 上下方向鍵可選擇歷史項目。
- Enter / Submit 可查詢選中的歷史項目。

相關 state：

```swift
@State private var showsHistorySuggestions = false
@State private var selectedHistoryIndex: Int?
@State private var hasActivatedSearch = false
@State private var hasCompletedInitialAppearance = false
@FocusState private var isSearchFocused: Bool
```

## 8. 發音系統

`AudioPlayerService` 使用 AVFoundation。

### 整字發音

整字發音順序：

1. 如果 entry 有遠端音檔 URL，使用 `AVPlayer` 播放。
2. 如果 app bundle 有本地 mp3，例如 `word_uk.mp3`，使用 `AVAudioPlayer` 播放。
3. 如果都沒有，使用 `AVSpeechSynthesizer`：
   - UK: `en-GB`
   - US: `en-US`

### 音素發音

音素按鈕呼叫：

```swift
audioPlayer.playPhoneme(symbol: symbol)
```

音素會查 `phonemeAudioMap`。此 map 的 value 是 `[String]`，因此同一個 IPA symbol 可以播放一個或多個本地音檔：

```swift
"æ": ["ipa_ae"]
"ə": ["ipa_schwa"]
"ɪ": ["ipa_i_short"]
"iː": ["ipa_i"]
"θ": ["ipa_theta"]
"ð": ["ipa_eth"]
"ʃ": ["ipa_sh"]
"ʒ": ["ipa_zh"]
"p": ["ipa_p"]
"l": ["ipa_l"]
"aɪ": ["ipa_a", "ipa_i_short"]
"tʃ": ["ipa_t_ch"]
"dʒ": ["ipa_d_zh"]
```

例如 `æ` 會播放 app bundle 內的 `ipa_ae.mp3`，`aɪ` 會依序播放 `ipa_a.mp3` 與 `ipa_i_short.mp3`。`tʃ` 與 `dʒ` 使用獨立 affricate MP3，避免順序播放 `t + ʃ` 或 `d + ʒ` 時聽起來像兩個音。

本地音素音檔位於：

```text
IPA Dict/Audio/Phonemes/
```

正式 app bundle 只包含 MP3。多數音檔使用 Wikimedia Commons 原始 OGG
轉檔；部分 Wikimedia consonant 原始錄音包含多段示範聲音，先前曾使用
single-shot 裁剪版。若裁剪後仍聽起來像多音節或多段示範，app bundle
改用 IPAHelp 的短版 MP3 作為單一音素按鈕音檔。原始 OGG、完整轉檔 MP3、
single-shot 裁剪版、裁剪報告及舊版私人比較音檔不放入 synchronized app
source folder。Wikimedia Commons 與 IPAHelp 來源紀錄保存在同目錄的
`ATTRIBUTION.md`。

可使用以下唯讀工具檢查 app bundle 音素 MP3 是否與
`AudioPlayerService.phonemeAudioMap` 一致，並確認音檔可解碼且沒有過長：

```sh
python3 Tools/audit_phoneme_audio.py
```

## 9. IPA Tokenizer

`IPATokenizer.phonemes(in:)` 會先 normalize 常見英文 IPA 變體，例如：

- `d͡ʒ` / `d͜ʒ` -> `dʒ`
- `t͡ʃ` / `t͜ʃ` -> `tʃ`
- `ɫ` -> `l`
- `ɚ` -> `ər`
- `ɝ` -> `ɜr`
- `ᵻ` -> `ɪ`
- `ᵿ` -> `ʊ`

然後移除不應顯示為音素按鈕的符號：

- `/`
- `[`
- `]`
- primary stress `ˈ`
- secondary stress `ˌ`
- syllable dot `.`
- spaces
- optional pronunciation parentheses
- common IPA diacritics and tie bars

然後依序拆出 compound phonemes，例如：

```swift
tʃ
dʒ
eɪ
aɪ
ɔɪ
aʊ
əʊ
oʊ
ɪə
eə
ʊə
iː
ɑː
ɔː
uː
ɜː
```

如果遇到長音符號 `ː`，會合併到前一個音素。

## 10. 翻譯 fallback

當查詢結果缺少中文釋義時，`DictionarySearchView` 會使用 Apple Translation framework：

```swift
TranslationSession.Configuration(
    source: Locale.Language(identifier: "en"),
    target: Locale.Language(identifier: "zh-Hant")
)
```

翻譯結果會經由 `TranslationCache` 快取。

注意：人工維護詞庫時，中文釋義不應依賴即時英文翻譯產生。翻譯 fallback 主要是 UI prototype 的保底機制。

## 11. 字典資料建置 pipeline

工具位於：

```text
Tools/DictionaryBuilder/
```

主要入口：

```sh
python3 Tools/DictionaryBuilder/build_dictionary.py
```

資料來源包含：

- FreeDict English–Chinese
- Open English WordNet
- CMU Pronouncing Dictionary
- Montreal Forced Aligner English UK / US dictionaries
- Tatoeba English–Mandarin sentence pairs
- WikiMatrix English–Chinese parallel sentences
- English Wiktionary via Kaikki / Wiktextract
- CC-CEDICT

建置原則：

- 只使用可再散布的開放資料。
- 不抓取不可直接再散布的商業字典網站內容。
- 中文釋義應來自雙語詞庫或人工審核，不應用英文釋義即時機器翻譯替代。
- Open English WordNet 可補充 synonyms，但不把其無中文對應的細分英文 definitions 自動混入 bilingual entries。
- 例句最多顯示一個，且中文翻譯需與詞義一致。

詳細資料建置說明請看：

```text
Tools/DictionaryBuilder/README.md
```

## 12. 精選詞庫維護

精選詞庫位於：

```text
IPA Dict/Data/CuratedDictionary.swift
```

精選詞條通常定義在：

```text
IPA Dict/Models/DictionaryEntry.swift
```

新增一個 curated word 的基本步驟：

1. 在 `DictionaryEntry.swift` 新增 static entry。
2. 在 `CuratedDictionary.entries` 註冊該 word。
3. 若 SQLite 沒有該 word，`DictionaryService` 仍會直接返回 curated entry。
4. 確認 UI 顯示：
   - 詞性
   - UK / US IPA
   - 中文釋義
   - 英文釋義
   - 雙語例句
   - 同義詞如有需要

範例：

```swift
static let itinerary = DictionaryEntry(
    word: "itinerary",
    ukIPA: "/aɪˈtɪn.ər.ər.i/",
    usIPA: "/aɪˈtɪn.ə.rer.i/",
    partOfSpeech: "noun",
    countability: "C",
    zhDefinition: "旅行計劃，預定行程",
    enDefinition: "a detailed plan or route of a journey",
    examples: [
        DictionaryExample(
            english: "The tour operator will arrange transport and plan your itinerary.",
            chinese: "旅行社工作人員將負責安排交通和行程計劃。"
        )
    ]
)
```

## 13. 資料授權

App bundle 內字典資料的授權說明位於：

```text
IPA Dict/Data/DictionaryLicenses.md
```

資料工具的來源與授權說明位於：

```text
Tools/DictionaryBuilder/README.md
```

維護資料時需注意：

- 不要直接複製不可再散布網站的完整內容。
- 若使用 AI 協助修正詞義，需要把結果視作人工審核內容，而不是來源引用。
- 新增或修改詞條時，應保留可追溯的資料來源或審核記錄。

## 14. 已知限制

- IPA tokenizer 仍是簡化版，未完整覆蓋所有 IPA 符號與語音變體。
- 目前本地音素 mp3 對應表只涵蓋部分音素。
- SQLite 詞庫仍可能存在缺詞、詞性缺漏、IPA 缺失或例句不足。
- Apple Translation fallback 可能與正確字典釋義不同，不應作為正式詞庫資料來源。
- ContentUnavailableView 的部分系統文字樣式由 SwiftUI 控制，不能完全套用自訂字體。

## 15. 建議測試流程

修改 UI 後：

```sh
git diff --check
```

建議手動查詢：

- `apple`
- `program`
- `find`
- `test`
- `yes`
- `itinerary`

檢查項目：

- 搜尋框首次打開不自動彈出歷史。
- 點擊搜尋框會顯示歷史。
- Esc 可關閉下拉。
- 查詢結果排版正確。
- UK / US IPA 可點擊。
- 音素按鈕可點擊。
- 同義詞連結可查詢。
- 詞性、中文釋義、英文釋義、例句顯示完整。
