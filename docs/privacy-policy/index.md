---
title: IPA Dict 私隱政策
description: IPA Dict 在 iOS、iPadOS 及 macOS 的資料處理政策
---

# IPA Dict 私隱政策

最後更新：2026-07-30

IPA Dict 是一個在 iOS、iPadOS 及 macOS 運行的英中本地字典 App。本政策說明 App 如何處理資料。

## 我們不會收集的資料

IPA Dict：

- 不設使用者帳戶；
- 不包含廣告或第三方分析 SDK；
- 不追蹤使用者；
- 不收集位置、聯絡人、相片、健康資料或廣告識別碼；
- 不會讓開發者查看使用者的搜尋記錄或書簽。

## 搜尋記錄與書簽

搜尋記錄與書簽儲存在 Apple 的 iCloud Key-Value Storage，讓登入同一 Apple ID 的裝置可以同步。這些資料由 Apple 的 iCloud 服務處理，開發者不能讀取使用者的私人 iCloud 儲存內容。

使用者可以在 App 內逐項刪除或清除搜尋記錄及書簽。iCloud 會把刪除操作同步至其他裝置。

## 字典查詢

App 會優先查詢隨 App 提供的本地 SQLite 詞庫。本地查詢不會把查詢詞傳送至開發者。

如果本地詞庫沒有結果，App 可能把查詢詞傳送至 Free Dictionary API（`dictionaryapi.dev`），以取得即時的備用結果。該服務可能按其自身政策處理 IP 位址、查詢內容及技術日誌。開發者不會收到或保存這些服務日誌。

## 外部網站

App 可以按使用者要求打開：

- Cambridge Dictionary 的詞條或音標參考頁；
- GitHub Issues 問題報告頁；
- 本專案的授權及支援頁面。

上述網站可能按其各自的私隱政策處理網絡資料。只有使用者主動打開相關頁面時，App 才會連接該網站。

## 錯誤或遺失詞報告

當使用者建立字典報告時，App 會先在 App 的本機 Documents 目錄寫入 `DictionaryReports.md`。該檔案不會由開發者自動收取。

App 之後會打開 GitHub Issues 頁面並預先填寫報告內容。只有使用者在 GitHub 確認提交後，內容才會傳送至 GitHub。已提交的 Issue 受 GitHub 的帳戶、保留及刪除政策約束。

## 資料保留與刪除

- 搜尋記錄及書簽：可在 App 內清除，並由 iCloud 同步刪除。
- 本機報告檔案：刪除 App 會移除 App container 內的本機檔案。
- GitHub Issue：已提交的內容須透過 GitHub 管理。

## 兒童私隱

IPA Dict 不會故意收集兒童的個人資料。App 不包含廣告、社交功能或帳戶系統。

## 政策更新

如果資料處理方式有重大改變，本政策及 App 內說明會同步更新。

## 聯絡及支援

如對私隱或 App 有疑問，請使用 [IPA Dict GitHub Issues](https://github.com/q7jxb7yxdk-star/IPA-Dict/issues)。
