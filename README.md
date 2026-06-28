# IPA Dict

IPA Dict 是一個使用 SwiftUI 製作的 multi-platform 中英字典 app prototype，支援 iOS、iPadOS 與 macOS。它以本地 SQLite 字典庫為主，提供英文單字查詢、繁體中文釋義、英文釋義、雙語例句、UK / US IPA 音標、音素拆解與發音功能。

這個專案的重點不是單純顯示字典資料，而是建立一個適合語言學習的查詢介面：查一個字時，可以同時看意思、例句、音標，並逐個音素練習發音。

## 主要功能

- SwiftUI multi-platform 介面，支援 iOS、iPadOS、macOS。
- 本地 SQLite 字典庫查詢，常用詞可離線讀取。
- 查詢結果以 Markdown 風格排版：
  - 單字標題
  - UK / US IPA
  - 可點擊音素
  - 詞性與文法標籤
  - 中文釋義
  - 英文釋義
  - 一組雙語例句
  - 同義詞連結
- UK / US IPA 可以點擊播放整字發音。
- IPA 會拆成音素按鈕，例如 `/ˈæp.əl/` 可拆成 `æ`、`p`、`ə`、`l`。
- 每個音素可對應本地音檔播放，例如 `æ -> ipa_ae.mp3`、`ə -> ipa_schwa.mp3`。
- 常見複合音素會優先使用單一 MP3，避免點擊一次音素時聽到兩段分開播放的聲音。
- 使用 AVFoundation 播放本地音檔、遠端音檔與系統語音 fallback。
- 搜尋歷史記錄，輸入框 focus 時以類似 Google 搜尋的下拉選單顯示。
- 同義詞以文字連結形式顯示，可點擊查詢。
- 精選詞庫 `CuratedDictionary` 可覆蓋或補充 SQLite 缺失詞條。

## App 畫面結構

查詢結果大致格式如下：

```text
# WORD

UK /.../  US /.../

/ 音素 音素 音素 /

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
│   │   ├── SearchHistoryStore.swift
│   │   └── TranslationCache.swift
│   └── Views/
│       ├── DictionarySearchView.swift
│       ├── WordDetailView.swift
│       ├── MarkdownText.swift
│       ├── PhonemeButton.swift
│       └── TranslatedText.swift
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

## 發音與音素音檔

`AudioPlayerService` 支援三種播放方式：

1. 本地 mp3 音檔。
2. 遠端 audio URL。
3. 使用 `AVSpeechSynthesizer` 作為 fallback。

音素對應表位於 `AudioPlayerService.phonemeAudioMap`。單一音素通常對應一個本地音檔；常見雙元音與 affricate 也優先對應單一 MP3，避免按下一個 IPA button 時聽到兩個分開音檔。例如：

```swift
"æ": ["ipa_ae"]
"ə": ["ipa_schwa"]
"ɪ": ["ipa_i_short"]
"iː": ["ipa_i"]
"θ": ["ipa_theta"]
"ð": ["ipa_eth"]
"ʃ": ["ipa_sh"]
"ʒ": ["ipa_zh"]
"aɪ": ["ipa_ai"]
"eɪ": ["ipa_ei"]
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

對應音檔需要加入 app bundle，例如 `ipa_ae.mp3`、`ipa_schwa.mp3`。目前音素音檔放在：

```text
IPA Dict/Audio/Phonemes/
```

音素錄音主要取自 Wikimedia Commons 的可再散布音檔。部分 consonant
錄音即使裁剪後仍較像多段示範聲音；這些單一音素按鈕改用 IPAHelp 的短版
MP3，以便點擊音素時只聽到乾淨的單一音。個別作者、來源頁面、裁剪紀錄、
IPAHelp replacement 清單及授權資料記錄於
`IPA Dict/Audio/Phonemes/ATTRIBUTION.md`。

常見雙元音例如 `eɪ`、`aɪ`、`ɔɪ`、`əʊ`、`oʊ`、`aʊ`、`ɪə`、`eə`、`ʊə`
也使用單一 MP3。`əl`、`əm`、`ən`、`ər` 不作為獨立 IPA 音素處理；
例如 `ər` 會拆成 `ə` 與 `r`，避免把不存在於 Cambridge IPA 表的組合當作
獨立音素。

## 注意事項

- 這仍是一個 prototype，部分功能和資料仍可繼續改善。
- SQLite 詞庫是主要資料來源；`CuratedDictionary` 用於修正常用詞、補充缺字或覆蓋錯誤結果。
- 如果 SQLite 沒有某個字，但 `CuratedDictionary` 有資料，app 會直接顯示精選詞條。
- 若本地資料和精選詞庫都沒有，app 會嘗試使用線上 Dictionary API fallback。
- 部分發音若沒有本地音檔或遠端音檔，會使用系統語音合成。

## 後續改善方向

- 增加更多音素本地音檔。
- 改善 IPA tokenizer，支援更多複合音素和變體。
- 增加詞庫審核工具的 UI。
- 讓同義詞、反義詞、相關詞形成更完整的可瀏覽詞網。
- 加入收藏、生字本、複習模式。
- 增加詞庫版本資訊與資料更新介面。
