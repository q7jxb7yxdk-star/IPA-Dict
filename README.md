# IPA Dict

IPA Dict 是一個使用 SwiftUI 製作的 multi-platform 中英字典 app prototype，支援 iOS、iPadOS 與 macOS。它以本地 SQLite 字典庫為主，提供英文單字查詢、繁體中文釋義、英文釋義、雙語例句、UK / US IPA 音標、音素拆解、發音說明與 IPA 發音表。

這個專案的重點不是單純顯示字典資料，而是建立一個適合語言學習的查詢介面：查一個字時，可以同時看意思、例句、音標，並逐個音素練習發音。

## 主要功能

- SwiftUI multi-platform 介面，支援 iOS、iPadOS、macOS。
- 本地 SQLite 字典庫查詢，常用詞可離線讀取。
- 查詢結果以 Markdown 風格排版：
  - 單字標題
  - UK / US IPA
  - 可點擊音素
  - 詞性與文法標籤
  - 名詞複數形式；不可數或通常只用單數的名詞會清楚標示
  - 中文釋義
  - 英文釋義
  - 一組雙語例句
  - 同義詞及反義詞連結
- UK / US IPA 可以點擊播放整字發音。
- IPA 會拆成音素按鈕，例如 `/ˈæp.əl/` 可拆成 `æ`、`p`、`ə`、`l`。
- 查詢結果的個別音素按鈕會在音素下方顯示發音說明，不播放 MP3；點擊外部即可關閉。
- 音素說明的 Cambridge reference 會在 App 內開啟：iOS / iPadOS 使用 `SFSafariViewController`，macOS 使用 `WKWebView`。
- 獨立「IPA 發音表」整理元音、輔音、例字及發音方法；音素本身只作說明，點擊例字的完整 IPA 會以系統語音播放整個例字。
- 遠端整字發音使用 `AVPlayer`；沒有遠端錄音時，macOS、iOS、iPadOS 都會使用 `AVSpeechSynthesizer` 作為系統語音 fallback。
- 搜尋歷史記錄，輸入框 focus 時以類似 Google 搜尋的下拉選單顯示；首頁記錄可向左滑動單筆刪除。
- 支援中文反向查詢：輸入繁體或簡體中文釋義時顯示相關英文字候選，按 Enter 可查詢最相關的英文字。
- 支援複數名詞查詢：輸入 `indexes`、`indices` 等複數時，可開啟其單數詞頭 `index`。
- 動詞詞性下方顯示 present participle、past tense 及 past participle。
- 支援動詞 tense 查詢：沒有獨立詞頭的 tense（例如 `went`）可開啟原形 `go`。
- 書簽功能，可在查詢結果頁收藏單字，並在首頁快速重新查詢。
- macOS 與 iPadOS 使用 `NavigationSplitView` 顯示字典、IPA 發音表、私隱與授權及書簽 sidebar；iPhone 使用單欄 navigation。
- App 內提供「私隱與授權」頁面；完整公開政策位於
  `https://q7jxb7yxdk-star.github.io/IPA-Dict/privacy-policy/`，唯一來源位於
  `docs/privacy-policy/index.md`。
- 同義詞及反義詞以文字連結形式顯示，可點擊查詢；只有資料存在時才顯示對應區塊。
- 精選詞庫 `CuratedDictionary` 可覆蓋或補充 SQLite 缺失詞條。
- 主詞庫 `dictionary.sqlite` 放在 GitHub repository，由 macOS 端修改後 Commit and Push 統一管理。

## App 畫面結構

查詢結果大致格式如下：

```text
# WORD

UK /.../  US /.../

/ 音素 音素 音素 /

---

{詞性，例如：}

noun [ C ]

複數：words

或

verb

present participle: **going** | past tense: **went** | past participle: **gone**

## 中文釋義

...

## 英文釋義

...

## 例句

...

---

## 同義詞

word link

## 反義詞

word link
```

## 專案結構

```text
IPA Dict/
├── IPA Dict/
│   ├── Data/
│   │   ├── dictionary.sqlite
│   │   ├── CuratedDictionary.swift
│   │   └── DictionaryLicenses.md
│   ├── Models/
│   │   ├── DictionaryEntry.swift
│   │   └── DictionaryAPIResponse.swift
│   ├── Services/
│   │   ├── DictionaryService.swift
│   │   ├── LocalDictionaryService.swift
│   │   ├── AudioPlayerService.swift
│   │   ├── BookmarkStore.swift
│   │   ├── SearchHistoryStore.swift
│   │   └── TranslationCache.swift
│   └── Views/
│       ├── DictionarySearchView.swift
│       ├── IPAGuideView.swift
│       ├── WordDetailView.swift
│       ├── MarkdownText.swift
│       └── PhonemeButton.swift
├── Tools/
│   └── DictionaryBuilder/
├── README.md
└── TECHNICAL_DOCUMENTATION.md
```

## 如何執行

1. 使用 Xcode 開啟：

   ```text
   IPA Dict.xcodeproj
   ```

2. 選擇 target / destination：

   - iPhone simulator
   - iPad simulator
   - My Mac

3. 按 Run。

專案內已包含 app bundle 使用的 `dictionary.sqlite`。如果要重新建置字典資料，請參考 `Tools/DictionaryBuilder/README.md` 與 `TECHNICAL_DOCUMENTATION.md`。

目前 bundled `dictionary.sqlite` 包含 35,411 筆詞義及 28,734 個詞頭。
`entries.id` 已按照 `normalized_word` 不分大小寫排序，並連續編號為
`1–35,411`。同一個 word 的不同詞性及詞義會維持相鄰，方便使用 SQLite
工具檢查及維護。

最近一次缺詞審核共人工檢查 1,130 個英語學習候選：接受 1,060 個詞頭，
新增 1,240 筆完整詞義；其餘 70 個屈折詞、自由組合、錯誤詞形及低價值
項目沒有加入。完成後已驗證 SQLite integrity、JSON、雙語例句、IPA、排序、
連續 ID、重複詞義及同義詞／反義詞關聯。

## 字典資料來源

本專案使用可再散布的開放資料建立本地詞庫，不抓取 Cambridge Dictionary 等不可直接再散布的網站內容。

目前資料來源包含：

- FreeDict English–Chinese
- Open English WordNet
- CMU Pronouncing Dictionary
- Montreal Forced Aligner English UK / US dictionaries
- Tatoeba English–Mandarin sentence pairs
- WikiMatrix English–Chinese parallel sentences
- English Wiktionary data via Kaikki / Wiktextract
- CC-CEDICT

目前 bundled `dictionary.sqlite` 已包含一批由本地 Wiktextract raw JSONL gzip
審核匯入的 UK IPA 修正。匯入規則只接受明確標示為
Received Pronunciation、UK 或 British 的音標，不會把 US IPA 推斷成 UK IPA。
截至 2026-06-27，已把 1,583 筆原本的 generated fallback UK IPA
替換為 verified source。

詳細授權請參考：

- `IPA Dict/Data/DictionaryLicenses.md`
- `Tools/DictionaryBuilder/README.md`

## 發音系統

`AudioPlayerService` 支援兩種整字播放方式：

1. 詞條有遠端 audio URL 時，使用 `AVPlayer` 播放。
2. 沒有遠端錄音時，使用 `AVSpeechSynthesizer`；UK 使用 `en-GB`，US 使用 `en-US`。

IPA 發音表不播放獨立音素檔案。音素只顯示發音說明；例字後的完整 IPA 是可點擊連結，按下後會以系統語音播放整個例字。專案與 App bundle 均不包含 MP3 或其他 IPA 錄音檔。

macOS app 保持 App Sandbox，不加入 `com.apple.security.exception.mach-lookup.global-name` temporary exception。iOS / iPadOS 會在系統語音播放前啟用 `AVAudioSession` 的 `.playback`／`.spokenAudio`。

## 注意事項

- 這仍是一個 prototype，部分功能和資料仍可繼續改善。
- SQLite 詞庫是主要資料來源；`CuratedDictionary` 用於修正常用詞、補充缺字或覆蓋錯誤結果。
- App bundle 內的 `dictionary.sqlite` 是主要內建詞庫；app 不提供直接編輯詞條或私人筆記功能。
- 如果使用 Letos 或其他 SQLite 工具直接維護 bundled `dictionary.sqlite`，修改後直接用 Xcode / Git Commit and Push 到 GitHub；首頁日期會讀取 bundled SQLite 的檔案修改時間，不需要額外更新 manifest。
- 搜尋歷史與書簽直接儲存在 iCloud Key-Value Storage，在登入同一 Apple ID 的 macOS、iOS、iPadOS 裝置間同步；KVS 同時提供裝置上的持久快取，資料不會寫入 bundled `dictionary.sqlite`。
- App bundle 包含 `PrivacyInfo.xcprivacy`，聲明不追蹤、不使用第三方分析，亦不由開發者收集使用者資料。
- 跨平台主詞庫由 GitHub repository 管理；其他裝置需使用包含最新版 `dictionary.sqlite` 的 app build。
- 如果 SQLite 沒有某個字，但 `CuratedDictionary` 有資料，app 會直接顯示精選詞條。
- 若本地資料和精選詞庫都沒有，app 會嘗試使用線上 Dictionary API fallback。
- 發音若沒有遠端錄音，會使用系統語音合成。

## 後續改善方向

- 改善 IPA tokenizer，支援更多複合音素和變體。
- 增加詞庫審核工具的 UI。
- 繼續擴充同義詞、反義詞及相關詞的資料覆蓋率。
- 把書簽延伸成生字本、複習模式。
- 增加詞庫版本資訊與資料更新介面。
