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
PersonalDictionaryService / LocalDictionaryService / CuratedDictionary / Dictionary API fallback
    ↓
DictionaryEntry models
```

查詢結果由 `WordDetailView` 顯示，私人詞條由 `PersonalEntryEditView` 編輯，發音由 `AudioPlayerService` 負責，搜尋歷史由 `SearchHistoryStore` 儲存在 `UserDefaults`，書簽由 `BookmarkStore` 儲存在 `UserDefaults`。

## 2. 主要檔案

### App entry

- `IPA Dict/IPA_DictApp.swift`
- `IPA Dict/ContentView.swift`

負責啟動 SwiftUI app，並顯示主要搜尋頁。

### Views

- `DictionarySearchView.swift`
  - 搜尋頁與結果頁容器。
  - 管理搜尋輸入框、搜尋歷史、書簽、下拉選單、loading、error state。
  - 使用 `NavigationStack` 顯示查詢結果。
  - 提供私人字典編輯與重設入口。

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

- `PersonalEntryEditView.swift`
  - 私人字典結構化編輯畫面。
  - 只開放模板中的欄位修改，例如 UK IPA、US IPA、詞性、中文釋義、英文釋義與雙語例句。
  - 不提供任意 Markdown 全文編輯，避免破壞查詢結果版面結構。

### Models

- `DictionaryEntry.swift`
  - app 內部主要字典資料模型。
  - 包含 word、UK IPA、US IPA、詞性、可數性、中文釋義、英文釋義、例句、同義詞、反義詞。
  - 也包含若干 curated static entries，例如 `apple`、`program`、`find`、`test`、`yes`、`itinerary`。

- `DictionaryAPIResponse.swift`
  - 線上 Dictionary API response 的 decoding model。
  - 負責把 API response 轉成 `DictionaryEntry`。

- `PersonalDictionaryEntry.swift`
  - 私人字典 SQLite 的資料模型。
  - 包含 `EditablePersonalDictionaryEntry` 與 `EditablePersonalDictionarySense`，用於編輯畫面與 SQLite 儲存之間轉換。

### Services

- `DictionaryService.swift`
  - 查詢入口。
  - 統一處理私人字典、本地 SQLite、精選詞庫與線上 API fallback。

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

- `BookmarkStore.swift`
  - 使用 `UserDefaults` 儲存書簽字詞。
  - 提供加入、移除、切換、清除與查詢是否已收藏。
  - 書簽是使用者偏好資料，不寫入 bundled `dictionary.sqlite` 或私人字典 SQLite。

- `PersonalDictionaryService.swift`
  - 使用 SQLite3 管理使用者私人字典。
  - 儲存在 Application Support 內的 `PersonalDictionary.sqlite`。
  - 查詢時優先於 bundled `dictionary.sqlite`。
  - 支援保存與刪除私人詞條。

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
1. 查詢 PersonalDictionaryService / 私人 SQLite
2. 如果私人字典有資料：
   - 直接返回私人詞條
3. 檢查 CuratedDictionary 是否有精選詞條
4. 查詢 LocalDictionaryService / bundled SQLite
5. 如果 bundled SQLite 有資料：
   - 有 curated：merge curated + local entries
   - 無 curated：返回 local entries
6. 如果 bundled SQLite 沒資料但 curated 有資料：
   - 直接返回 curated entries
7. 如果 private / local / curated 都沒有：
   - 使用線上 Dictionary API fallback
```

也就是：

```text
你編輯過的字 → 讀 PersonalDictionary.sqlite
未編輯過的字 → 讀內建 dictionary.sqlite
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

`DictionaryEntry.isPersonal` 用於標記查詢結果是否來自私人字典。結果頁會以此決定是否顯示「私人筆記」提示與「還原」操作。

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

### Dictionary manifest

App bundle 內另有一個輕量 manifest：

```text
IPA Dict/Data/dictionary_manifest.json
```

用途是讓 macOS、iOS、iPadOS 都能在 UI 顯示同一個詞庫日期，而不需要先
打開 SQLite。格式如下：

```json
{
  "database_file": "dictionary.sqlite",
  "database_updated_at": "2026-06-29T20:09:00+08:00",
  "display_updated_at": "2026-06-29 20:09",
  "sha256": "...",
  "generated_at": "2026-06-29T20:09:00+08:00"
}
```

`DictionaryManifestStore` 會從 bundle 讀取此 JSON，並在首頁顯示：

```text
資料庫日期：2026-06-29 20:09
```

如果使用 Letos 或其他 SQLite 工具直接維護 bundled `dictionary.sqlite`，
修改完成後應執行：

```sh
python3 Tools/DictionaryBuilder/update_dictionary_manifest.py
```

此工具會使用 `Asia/Hong_Kong` 目前時間更新 `database_updated_at` /
`display_updated_at`，並重新計算 `dictionary.sqlite` 的 SHA-256。之後再
用 Xcode / Git Commit and Push，其他平台即可透過同一份 GitHub repo 取得
一致的資料庫檔案與顯示日期。

## 6. 私人字典與 GitHub 主詞庫

私人字典用於保存使用者手動修正的字典筆記。它不會直接修改 app bundle 內的
`dictionary.sqlite`，避免使用者資料在重新安裝 app 或更新內建詞庫時混入可重建資料。
查詢時採用 per-word override：如果某個字已被手動編輯，app 會優先讀取
`PersonalDictionary.sqlite` 內的私人版本；如果該字沒有私人版本，才讀取
app bundle 內建的 `dictionary.sqlite`。

本機私人字典位置由 `FileManager.default.url(for:in:appropriateFor:create:)`
取得 Application Support，再建立：

```text
IPA Dict/PersonalDictionary.sqlite
```

實際 sandbox 路徑會因平台與安裝方式不同而改變。

### 私人 SQLite schema

`PersonalDictionaryService` 會自動建立兩個 table：

```sql
personal_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    normalized_word TEXT NOT NULL UNIQUE,
    uk_ipa TEXT NOT NULL DEFAULT '',
    us_ipa TEXT NOT NULL DEFAULT '',
    source_note TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

```sql
personal_senses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL,
    display_order INTEGER NOT NULL,
    part_of_speech TEXT NOT NULL DEFAULT '',
    countability TEXT NOT NULL DEFAULT '',
    zh_definition TEXT NOT NULL DEFAULT '',
    en_definition TEXT NOT NULL DEFAULT '',
    example_english TEXT NOT NULL DEFAULT '',
    example_chinese TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(word_id) REFERENCES personal_words(id) ON DELETE CASCADE
)
```

每個私人詞條可以有多個 sense；app 仍沿用相同查詢結果 UI 顯示。

### GitHub 主詞庫管理

主詞庫 `dictionary.sqlite` 放在 GitHub repository，由 macOS 端統一維護。
建議流程：

1. 使用 Letos 或其他 SQLite 工具修改 `IPA Dict/Data/dictionary.sqlite`。
2. 執行 `python3 Tools/DictionaryBuilder/update_dictionary_manifest.py` 更新
   `dictionary_manifest.json` 的資料庫日期與 SHA-256。
3. 用 Xcode / Git Commit and Push 到 GitHub。
4. 其他平台顯示同一個 bundle manifest 日期，之後可再擴充成從 GitHub
   下載最新主詞庫。

App 內已移除 iCloud Drive 匯入／匯出私人字典功能，避免和 GitHub 主詞庫
管理流程混淆。私人字典只作為本機 per-word override，用於 app 內手動修正
個別詞條。

## 7. 查詢結果 UI

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

## 8. 搜尋歷史、書簽與下拉選單

`SearchHistoryStore` 負責儲存最近搜尋：

- 儲存位置：`UserDefaults`
- key：`dictionarySearchHistory`
- 最大數量：20
- 新查詢會移到最前面。

`BookmarkStore` 負責儲存書簽：

- 儲存位置：`UserDefaults`
- key：`dictionaryBookmarks`
- 未設定最大數量。
- 結果頁工具列以 `star` / `star.fill` 顯示目前字是否已收藏。
- 首頁會顯示書簽區，點擊書簽字詞可直接重新查詢，也可逐個移除或清除全部。

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

## 9. 發音系統

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

音素會查 `phonemeAudioMap`。此 map 的 value 是 `[String]`，因此同一個 IPA symbol 技術上可以播放一個或多個本地音檔；但實際維護原則是：可被使用者點擊的常見複合音素應優先使用單一 MP3，避免按下一個 IPA button 時聽到兩段分開播放的聲音。

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
"eɪ": ["ipa_ei"]
"aɪ": ["ipa_ai"]
"ɔɪ": ["ipa_oi"]
"əʊ": ["ipa_schwa_u"]
"oʊ": ["ipa_ou"]
"aʊ": ["ipa_au"]
"ɪə": ["ipa_i_schwa"]
"eə": ["ipa_e_schwa"]
"ʊə": ["ipa_u_schwa"]
"tʃ": ["ipa_t_ch"]
"dʒ": ["ipa_d_zh"]
```

例如 `æ` 會播放 app bundle 內的 `ipa_ae.mp3`，`aɪ` 會播放 `ipa_ai.mp3`。`tʃ` 與 `dʒ` 使用獨立 affricate MP3，避免順序播放 `t + ʃ` 或 `d + ʒ` 時聽起來像兩個音。`eɪ`、`aɪ`、`ɔɪ`、`əʊ`、`oʊ`、`aʊ`、`ɪə`、`eə`、`ʊə` 也使用單一 MP3。

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

常見雙元音的單一 MP3 來自 Wikimedia Commons 的可再散布 word recordings，
再轉成 MP3 放入 app bundle。這些檔案的用途是讓一個 IPA button 對應一次
播放行為，而不是用 `playSoundSequence` 連播兩個 vowel MP3。

可使用以下唯讀工具檢查 app bundle 音素 MP3 是否與
`AudioPlayerService.phonemeAudioMap` 一致，並確認音檔可解碼且沒有過長：

```sh
python3 Tools/audit_phoneme_audio.py
```

## 10. IPA Tokenizer

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

`əl`、`əm`、`ən`、`ər` 不作為獨立 compound phoneme。以 `ər` 為例，
tokenizer 會拆成 `ə` 與 `r`；這可避免把 Cambridge IPA 表沒有列出的組合
當成獨立音素，也避免誤播不存在的單一音檔。syllable dot `.` 會作為
compound matching 的邊界，不會讓雙元音或其他複合音素跨 syllable 合併。

## 11. 翻譯 fallback

當查詢結果缺少中文釋義時，`DictionarySearchView` 會使用 Apple Translation framework：

```swift
TranslationSession.Configuration(
    source: Locale.Language(identifier: "en"),
    target: Locale.Language(identifier: "zh-Hant")
)
```

翻譯結果會經由 `TranslationCache` 快取。

注意：人工維護詞庫時，中文釋義不應依賴即時英文翻譯產生。翻譯 fallback 主要是 UI prototype 的保底機制。

## 12. 字典資料建置 pipeline

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

## 13. 精選詞庫維護

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

## 14. 資料授權

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

## 15. 已知限制

- IPA tokenizer 仍是簡化版，未完整覆蓋所有 IPA 符號與語音變體。
- 目前本地音素 mp3 對應表只涵蓋部分音素。
- SQLite 詞庫仍可能存在缺詞、詞性缺漏、IPA 缺失或例句不足。
- 私人字典是本機 per-word override；跨平台主詞庫目前透過 GitHub repository 更新，而不是 app 內自動同步。
- Apple Translation fallback 可能與正確字典釋義不同，不應作為正式詞庫資料來源。
- ContentUnavailableView 的部分系統文字樣式由 SwiftUI 控制，不能完全套用自訂字體。

## 16. 建議測試流程

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
- 編輯私人詞條後，再查同一個字會優先顯示私人字典內容。
- 首頁會顯示 `dictionary_manifest.json` 的資料庫日期。
