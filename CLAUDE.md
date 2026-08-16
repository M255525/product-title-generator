# CLAUDE.md — product-title-generator（跨境商品標題產生器）

單檔前端工具，輸入一個商品核心關鍵詞，依「規格詞＋功能詞＋形容詞＋商品核心關鍵詞」結構，一次產生 50 組不重複的英文標題＋另 50 組依熱度優先排序、中英對照的標題，並依 Alibaba 國際站／Amazon 美國站的用字慣例自動切換詞庫。與 `ai-image-prompt-studio`／`ai-prompt-generator`／`ai-music-prompt-studio` 是姊妹專案，同一套 BYOK 呼叫 LLM 的手法、同一套序號授權骨架（序號鎖整個工具、12 個月效期），服務對象換成跨境電商賣家。

## 架構

單一 `index.html`：內嵌 CSS/JS、無外部資源、無建置步驟。視覺主題是深色「數據面板」風格（`--bg #0b1220` + 圓點網格背景 + 藍色 `--accent #3b82f6`），與 `ai-image-prompt-studio`（洋紅）、`ai-prompt-generator`（青）、`Prompt`（琥珀）、`ai-music-prompt-studio`（紫）刻意做出區隔。

- **核心資料模型是三組詞庫**（非姊妹專案慣用的「共用欄位＋多分頁組裝格式」模式）：`SPEC_WEIGHT`／`SPEC_COUNT`／`SPEC_SIZE`（規格詞三個子池，依「規格類型」下拉切換）、`FUNCTION_WORDS`（功能詞）、`ADJECTIVE_WORDS`（形容詞）。每筆結構 `{en, zh, tier, platforms?}`：`tier` 是 1~5 的**離線參考熱度分**（人工粗略標註，非真實搜尋數據，UI／警語需明確揭露）；`platforms`（可選）限制該詞只出現在特定平台，用來實作「Amazon 排除主觀宣傳詞／批發用語，Alibaba 開放」的規則——`ADJECTIVE_WORDS` 陣列後半段（Wholesale／Bulk／OEM／Custom Logo／Factory Direct／Hot Sale／Best-Selling／Low MOQ）與 `SPEC_COUNT` 的兩筆（Bulk Lot of 500／MOQ 1000 Units）都標了 `platforms:['alibaba']`；其餘未標 `platforms` 的詞視為兩平台皆可用。新增詞彙時，若屬於 Amazon 官方不建議出現在標題的主觀宣傳詞或 B2B 批發用語，務必加上 `platforms:['alibaba']`，不要漏標。
- **標題組裝順序固定**：`[spec.en, func.en, adj.en, titleCase(core)].join(' ')`——四個詞的順序對應「規格詞＋功能詞＋形容詞＋核心關鍵詞」的結構，不要調整順序。`titleCase()` 只套用在核心關鍵詞（使用者輸入的自由文字），規格／功能／形容詞的 `en` 欄位已在資料裡預先寫好正確大小寫（含 `OEM`／`DIY`／`XL` 等縮寫），**不要**對整個標題字串做全域大小寫正規化，否則會破壞這些縮寫的大小寫。
- **第一批（隨機不重複）vs 第二批（熱度優先＋中英對照）的差異在 `generateBatch()` 的 `weighted` 參數**：第一批 `weighted:false`（均勻隨機 `pickRandom()`），核心關鍵詞池含使用者填的同義詞（`coreVariants(true)`）；第二批 `weighted:true`（依 `tier*tier` 加權隨機 `weightedPick()`，分數越高被抽中機率越高），核心關鍵詞**只用主要關鍵詞**（`coreVariants(false)`，不含同義詞——因為中文標題只有一組中文核心關鍵詞可對應，若英文標題隨機換用同義詞會跟固定的中文核心關鍵詞語意兜不起來，這是刻意簡化，不是遺漏）。第二批固定排除與第一批重複的標題字串（`excludeSet`）。
- **去重靠字串比對，不是演算法保證**：`generateBatch()` 內用一個 `seen` 物件記錄已產生的完整標題字串，重複就跳過重抽，最多嘗試 `count*120` 次。詞庫組合空間（過濾平台後仍有數百到上千種組合）遠大於 50，實測不會出現抽不滿的狀況；若未來詞庫大幅精簡導致組合數逼近 50，需注意 `maxAttempts` 是否足夠。
- **離線星等＝三個詞 tier 的平均值四捨五入**（`Math.round((spec.tier+func.tier+adj.tier)/3)`，夾在 1~5 之間），分級對照表 `STAR_TIER = {5:'S',4:'A',3:'B',2:'C',1:'D'}`。
- **AI 熱度評分是整批一次呼叫，不是逐筆呼叫**：`buildScorePrompt()` 把整批（最多 50 筆）標題組成 `{index,title}` 的 JSON 陣列塞進單一 prompt，要求模型回傳同樣結構的 `[{index,stars,tier,reason}]`，`runAiScoring()` 用 `parseJsonLoose()`（先剝除可能的 markdown code fence 再 `JSON.parse`）解析後依 `index` 寫回對應列的 `stars`/`tier`/`aiReason`/`aiScored`。**這是刻意的成本/延遲控制設計**——100 組標題若逐筆呼叫會是 100 次 API 請求，改成兩次批次呼叫（每批各一次）。`aiScored:true` 的列在分級標籤旁會多顯示 `🤖` 圖示並把理由放進 `title` 屬性（hover 顯示）。
- **圖片分析只建議「核心關鍵詞候選」可點擊套用，賣點建議純參考不可插入**：`buildImagePrompt()` 要求模型回傳 `{coreKeywords:[{en,zh}], suggestions:[{en,zh}]}`，`renderImageSuggestions()` 只有 `coreKeywords` 渲染成可點擊的 `.suggest-pill`（點擊會覆蓋 `f_coreEn`/`f_coreZh`，覆蓋前若欄位非空會 `confirm()`），`suggestions`（賣點／情境形容詞）渲染成不可點擊的 `.suggest-note` 純文字——因為這些自由文字建議不保證落在系統內建的 `FUNCTION_WORDS`/`ADJECTIVE_WORDS` 詞庫裡，貿然插入會破壞「標題只能用受控詞庫組裝」這個前提，改成純參考文字讓使用者自行判斷要不要手動調整核心關鍵詞或同義詞。
- **`callLLM()` 比姊妹專案多一個可選的 `imageDataUrl` 參數**：有帶圖片時，Claude 走 `content:[{type:'image',source:{type:'base64',media_type,data}},{type:'text',text}]`，OpenAI/OpenRouter 走 `content:[{type:'text',text},{type:'image_url',image_url:{url:dataURL}}]`，Gemini 走 `parts:[{text},{inline_data:{mime_type,data}}]`（`splitDataUrl()` 用 regex 從 `data:image/...;base64,...` 字串拆出 mime/base64）。純文字呼叫（AI 熱度評分）不帶這個參數，行為與姊妹專案的 `callLLM()` 完全一致。圖片分析需要使用者選擇支援視覺輸入的模型（Claude／GPT-4o／Gemini 系列），本工具不做模型能力檢查，呼叫失敗會顯示 API 回傳的錯誤訊息。
- **CSV 匯出**：`downloadCsvBtn` 合併 `state.batch1`＋`state.batch2` 成一個表格，`csvCell()` 對含逗號/雙引號/換行的欄位做 `""` 轉義並加雙引號包裹，Blob 內容前綴 `'﻿'`（UTF-8 BOM）避免 Excel 開啟中文欄位亂碼——**這是本工具第一次在工作區內實作 CSV 下載**（姊妹專案的「已儲存的提示詞」下載是 `.txt`），之後其他專案若要加 CSV 匯出可直接參照這個 `csvCell()`/BOM 寫法。
- **平台切換會清空已產生的兩批標題**：`platformTabs` 的 click handler 若偵測到 `state.batch1.length || state.batch2.length` 非空，會先 `confirm()` 再清空——因為不同平台的詞庫過濾結果不同，保留舊資料容易造成「標題與目前平台規則不符」的混淆。
- 狀態存 `localStorage`（key: `ptgState`）：`{activePlatform, fields:{coreEn,coreZh,synonyms,specType}, batch1:[], batch2:[]}`——兩批標題本身也存進 state（不是只存欄位），重新整理頁面後仍看得到已產生的標題。

## 序號授權（鎖定整個工具，12 個月）

比照 `ai-image-prompt-studio`／`ai-prompt-generator`／`ai-music-prompt-studio` 的「單一工具、整個鎖住」模式：`#licenseGate` 全螢幕遮罩預設鎖定，驗證通過才加上 `.hidden`；載入時一律對後端即時重驗，背景每 20 分鐘重驗一次。`localStorage` key：`ptgSerial`。

- **綁定的 Google Sheet 是使用者指定沿用的既有表**：<https://docs.google.com/spreadsheets/d/1pqGlCvUstowBzZh7J4xEa0jy3KoK4UeHUiyMTzcSGo4/edit>。`Code.gs` 採用 `ai-music-prompt-studio` 那套更保守的**雙層掃描**版本（`findLicenseSheet_()` 掃描 `ss.getSheets()` 每一個分頁＋`findHeaderRow_()` 在每個分頁裡找表頭列），不是 `ai-image-prompt-studio` 那個假設「表頭一定在第一分頁的 `values[0]`」的簡化版——因為這份既有 Sheet 的實際分頁/表頭位置在動工當下未知，用更保守的版本可以避免重踩 `ai-music-prompt-studio` 已經記錄過的坑（`server_error` 但訊息不明顯，容易被忽略）。
- `LICENSE_CHECK_URL` 部署前為空字串，會顯示「尚未設定授權伺服器網址」的 fail-closed 訊息並停留在鎖定畫面；部署步驟見 `SETUP-授權伺服器設定.md`，部署走 clasp（不要建議複製貼上，已知的剪貼簿踩坑）。
- **這支後端只做序號驗證，不代理任何付費 API**（LLM 串接是 BYOK），也**不處理跑馬燈**。

## 頂部共用跑馬燈

`#marqueeBar` 內容抓自工作區既有的共用授權伺服器（`https://script.google.com/macros/s/AKfycbwKX0.../exec`，與 `Prompt`／`ai-prompt-generator`／`ai-image-prompt-studio`／`ai-music-prompt-studio`／`ai-video-studio` 系列共用同一個 Google Sheet），做法完全比照姊妹專案——跟本工具自己的序號授權後端是兩個互不相干的系統。`localStorage` key：`ptgMarquee`。

## Port 分配

固定用 **8791**（工作區已用 8765-8794，8791 為 `ai-music-prompt-studio` 建置時確認的空號，該專案本身佔用 8790）。`launcher.py` 已就緒，本次未打包桌面版 exe（比照近期幾個專案的做法，序號後端還要走 clasp/OAuth 部署，優先把功能做完；要打包時比照 `ai-image-prompt-studio` 的 PyInstaller 指令模式）。

## 隱私與警語

無伺服器端經手使用者資料；欄位內容、產生的標題、API 設定皆只存在使用者瀏覽器的 localStorage。序號驗證只會傳送序號本身給授權伺服器，不會傳送任何商品資訊或標題內容。首頁與手冊皆明列使用警語：星等/分級非真實搜尋數據、平台規則僅供參考、請勿輸入真實個資或機密資料、僅供教學與個人使用禁止商業化。修改功能時這些警語需一併檢視是否仍準確。

## 指令

無建置/測試指令。修改 `index.html` 或 `manual.html` 後直接用瀏覽器開啟驗證，或暫起 `python -m http.server <port>` 測完關閉。修改內嵌 `<script>` 後可用以下方式快速檢查語法：

```bash
python -c "
import re
html = open('index.html', encoding='utf-8').read()
open('_check.js','w',encoding='utf-8').write(re.findall(r'<script>(.*?)</script>', html, re.S)[0])
"
node --check _check.js
```

**測試序號授權邏輯前，需先照 `SETUP-授權伺服器設定.md` 部署好 Apps Script 並回填 `LICENSE_CHECK_URL`**，否則會顯示「尚未設定授權伺服器網址」的 fail-closed 錯誤訊息並停留在鎖定畫面；開發階段要測試詞庫/標題產生/AI/圖片分析等其他功能，可在瀏覽器 devtools 手動對 `#licenseGate` 加上 `hidden` class 暫時繞過。

## 本次未做（後續視需要再處理）

- 桌面版 exe 未打包。
- 根目錄 `專案目錄.docx` 尚未加入本專案的列。
