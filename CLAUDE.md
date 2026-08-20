# CLAUDE.md — product-title-generator（跨境商品標題產生器）

單檔前端工具，輸入一個商品核心關鍵詞，依「規格詞＋功能詞＋形容詞＋商品核心關鍵詞」結構，一次產生 50 組不重複的英文標題＋另 50 組依熱度優先排序、中英對照的標題，並依 Alibaba 國際站／Amazon 美國站的用字慣例自動切換詞庫。與 `ai-image-prompt-studio`／`ai-prompt-generator`／`ai-music-prompt-studio` 是姊妹專案，同一套 BYOK 呼叫 LLM 的手法、同一套序號授權骨架（序號鎖整個工具、12 個月效期），服務對象換成跨境電商賣家。

## 架構

單一 `index.html`：內嵌 CSS/JS、無外部資源、無建置步驟。視覺主題是深色「數據面板」風格（`--bg #0b1220` + 圓點網格背景 + 藍色 `--accent #3b82f6`），與 `ai-image-prompt-studio`（洋紅）、`ai-prompt-generator`（青）、`Prompt`（琥珀）、`ai-music-prompt-studio`（紫）刻意做出區隔。

- **核心資料模型是三組詞庫**（非姊妹專案慣用的「共用欄位＋多分頁組裝格式」模式）：`SPEC_WEIGHT`／`SPEC_COUNT`／`SPEC_SIZE`（規格詞三個子池，`mergedSpecPool()` 固定合併三池一起抽——**規格類型下拉選單已於 2026-08-16 依使用者要求移除**，若之後想恢復篩選特定子池，改回 `specPoolByType(type)` 這種依參數切換的寫法即可，三個子池陣列本身還在，沒有刪）、`FUNCTION_WORDS`（功能詞）、`ADJECTIVE_WORDS`（形容詞）。每筆結構 `{en, zh, tier, platforms?}`：`tier` 是 1~5 的**離線參考熱度分**（人工粗略標註，非真實搜尋數據，UI／警語需明確揭露）；`platforms`（可選）限制該詞只出現在特定平台，用來實作「Amazon 排除主觀宣傳詞／批發用語，Alibaba 開放」的規則——`ADJECTIVE_WORDS` 陣列後半段（Wholesale／Bulk／OEM／Custom Logo／Factory Direct／Hot Sale／Best-Selling／Low MOQ）與 `SPEC_COUNT` 的兩筆（Bulk Lot of 500／MOQ 1000 Units）都標了 `platforms:['alibaba']`；其餘未標 `platforms` 的詞視為兩平台皆可用。新增詞彙時，若屬於 Amazon 官方不建議出現在標題的主觀宣傳詞或 B2B 批發用語，務必加上 `platforms:['alibaba']`，不要漏標。
- **標題組裝順序固定**：`[spec.en, func.en, adj.en, coreTerm].join(' ')`——四個詞的順序對應「規格詞＋功能詞＋形容詞＋核心關鍵詞」的結構，不要調整順序。規格／功能／形容詞的 `en` 欄位已在資料裡預先寫好正確大小寫（含 `OEM`／`DIY`／`XL` 等縮寫），**不要**對整個標題字串做全域大小寫正規化，否則會破壞這些縮寫的大小寫。
- **核心關鍵詞保證出現在每一組標題（2026-08-16 應使用者要求新增）**：`coreTermFor(useSynonymVariety)` 一律以 `titleCase(state.fields.coreEn)` 為底，**不會被同義詞整個取代**——第一批（`useSynonymVariety:true`）想要的「同義詞增加變化」改成用附加寫法：從 `['', synonym1, synonym2, ...]` 這個池子隨機抽一個，抽到非空字串就以 `"核心關鍵詞 (同義詞)"` 的括號附加格式呈現（例如 `Green Tea Powder (Matcha Powder)`），抽到空字串就只用核心關鍵詞本身；第二批（`useSynonymVariety:false`）固定只用核心關鍵詞，不附加任何東西。**這是刻意的設計取捨**：舊版本會把核心關鍵詞整個換成同義詞（例如標題可能整組變成「Matcha Powder」完全不含「Green Tea Powder」字樣），使用者要求「核心關鍵字必須出現在每一個標題」後改成現在的附加寫法，不要改回整個替換的舊寫法。
- **第一批（隨機不重複）vs 第二批（熱度優先）的差異在 `generateBatch()` 的 `weighted`／`useSynonymVariety` 參數**：第一批 `weighted:false, useSynonymVariety:true`（均勻隨機 `pickRandom()`）；第二批 `weighted:true, useSynonymVariety:false`（依 `tier*tier` 加權隨機 `weightedPick()`，分數越高被抽中機率越高）。第二批固定排除與第一批重複的標題字串（`excludeSet`）。共用的生成邏輯抽成 `batchGenOptsBase()`（回傳 `{platform, specPool, funcPool, adjPool}`），兩個批次按鈕與 `regenerateSingleRow()` 都呼叫這個函式取得基礎設定，不要各自重複寫平台過濾邏輯。
- **`phrasesShareWord(a, b)` 的重複用字檢查已擴大到涵蓋核心關鍵詞**（原本只比對 spec/func/adj 三者兩兩之間）：`generateBatch()` 內除了原本三個描述詞兩兩比對，還會分別比對 spec/func/adj 是否各自跟 `coreTerm`（含括號附加的同義詞在內）共用字，有共用字就跳過重抽。因為 `coreTerm` 可能帶括號（同義詞附加寫法），`phrasesShareWord()` 拆字前會先把 `(`/`)` 換成空白再 split，避免 `"(matcha"` 這種帶標點的殘片比對不到。
- **兩批都輸出中英對照**（2026-08-16 應使用者要求把原本只有第二批有的中文標題也補進第一批）：`generateBatch()` 內部直接用 `coreZhOrPlaceholder()`（讀 `state.fields.coreZh`，空值時給提示文字）組出 `zh` 欄位，不再由呼叫端事後 `forEach` 補寫，兩批共用同一套組字邏輯，改動時只要修這一處。
- **去重靠字串比對，不是演算法保證**：`generateBatch()` 內用一個 `seen` 物件記錄已產生的完整標題字串，重複就跳過重抽，最多嘗試 `count*120` 次。詞庫組合空間（過濾平台後仍有數百到上千種組合）遠大於 50，實測不會出現抽不滿的狀況；若未來詞庫大幅精簡導致組合數逼近 50，需注意 `maxAttempts` 是否足夠。
- **離線星等＝三個詞 tier 的平均值四捨五入**（`Math.round((spec.tier+func.tier+adj.tier)/3)`，夾在 1~5 之間），分級對照表 `STAR_TIER = {5:'S',4:'A',3:'B',2:'C',1:'D'}`。
- **AI 熱度評分是整批一次呼叫，不是逐筆呼叫**：`buildScorePrompt()` 把整批（最多 50 筆）標題組成 `{index,titleEn,titleZh}` 的 JSON 陣列塞進單一 prompt，要求模型回傳同樣結構的 `[{index,stars,tier,reasonable,revisedEn,revisedZh,reason}]`，`runAiScoring()` 用 `parseJsonLoose()`（先剝除可能的 markdown code fence 再 `JSON.parse`）解析後依 `index` 寫回對應列。**這是刻意的成本/延遲控制設計**——100 組標題若逐筆呼叫會是 100 次 API 請求，改成兩次批次呼叫（每批各一次）。`aiScored:true` 的列在分級標籤旁會多顯示 `🤖` 圖示並把理由放進 `title` 屬性（hover 顯示）。
- **AI 評分同時檢查標題合理性並會直接改寫（2026-08-16 應使用者要求新增，同日再補兩版修正）**：`buildScorePrompt(rows, platform, coreKeyword)` 要求模型判斷三件事——(a) `titleEn` 本身是否文法/語意合理（重複用字、搭配矛盾等）、(b) `titleEn` 裡的規格詞／功能詞／形容詞跟核心關鍵詞放在一起是否合理搭配（例如「護膚用」配瑜珈墊這種明顯不搭的組合）、(c) `titleZh` 是否確實對應 `titleEn` 的意思——任一項不合格就 `reasonable:false`，並要求 `revisedEn`／`revisedZh` 兩者一起給、且互相對應（沒問題的部分也要照原意重新給一次，方便前端判斷），**明確要求修正後仍要保留核心關鍵詞本身**（prompt 裡會把 `coreKeyword` 字串直接寫進去，並說明括號內的同義詞不算數，核心關鍵詞一定要在括號外出現）。
  - `runAiScoring()` 對 `enChanged`（`revisedEn` 非空且與 `row.en` 不同）與 `zhChanged`（`revisedZh` 非空且與 `row.zh` 不同）**分別獨立判斷**，只要任一為真就套用對應那一側的覆寫——**這是修過的版本**：第一版實作只在 `enChanged` 為真時才會連帶套用 `revisedZh`，導致「AI 認為英文沒問題、只有中文對不上」這種情況被整批忽略，使用者回報「調整完後會再確認英文標題與中文標題是否符合」才發現這個缺口，已修正為兩側各自獨立套用。
  - **核心關鍵詞的程式碼安全網**：即使 prompt 已經要求，仍不能完全信任模型會照做——`runAiScoring()` 在套用 `revisedEn` 前會先檢查 `revisedEn.toLowerCase().indexOf(coreLower) >= 0`（`enHasCore`），沒通過就**完全不套用這筆英文修正**（保留原本一定含核心關鍵詞的版本），只套用中文修正（若有），並在 `row.aiReason` 附註「AI 調整建議缺少核心關鍵字，已忽略英文調整」、`reportEl` 的完成訊息也會統計 `rejected` 筆數。這個安全網跟 prompt 端的要求是兩層防護，不要因為 prompt 已經寫了就把程式碼這層拿掉。
  - **`row.specEn`／`row.funcEn`／`row.adjEn` 在英文標題被 AI 改寫時會清空成空字串**：因為 AI 改寫後的用字不保證還等於原本生成時挑的那三個詞。**這三個欄位原本是給表格「拆解」欄顯示用，該欄已於同日應使用者要求整個移除**（見下方 UI 精簡那條），現在清空這三個欄位純粹是為了 CSV 匯出的規格詞／功能詞／形容詞欄位不要出現跟目前標題無關的舊字——邏輯保留，用途從「UI 顯示」變成「CSV 資料正確性」，改這段時不要因為 UI 欄位沒了就誤以為這段清空邏輯也該一起刪掉。只有 `zhChanged`（英文沒變、只改中文）時才不動這三個欄位，因為英文標題本身沒變，原本的拆解仍然準確。
  - 套用覆寫時設 `row.aiAdjusted = true`、依新 `row.en` 長度重算 `row.overLen`——**原始未修正版本不會另外保留**，這是刻意的簡化（不是遺漏），manual.html／警語已明確揭露。`renderBatchTable()` 對 `aiAdjusted` 的列在英文標題下方加一行 `.adj-badge`（✏️ AI 已調整標題，hover 顯示 `aiReason`）。星等／分級一律照常更新，不受是否調整標題影響。
  - **測試方式**：沒有真實 API 金鑰可測，改用攔截 `window.fetch`（判斷 `url` 含 `api.anthropic.com` 就回傳偽造的 Claude 回應格式 `{content:[{type:'text',text:JSON.stringify([...])}]}`）驗證解析與覆寫邏輯，測完務必把 `window.fetch` 還原成原本的 `fetch`，避免污染同分頁後續的其他請求。已驗證過：只改英文、只改中文、兩者都改、兩者都不改四種情況皆正確套用。
- **單筆重新產生（2026-08-16 應使用者要求新增）**：每筆生成的標題有 `uid`（`makeUid()`，時間戳+隨機字串組成，跟排序/篩選無關，純粹用來在陣列裡定位這一列），表格最後一欄的「🔄 換一個」按鈕（`.regen-btn`，`data-batch`/`data-uid`）呼叫 `regenerateSingleRow(batchKey, uid)`：用 `rows.findIndex` 找到對應列的陣列位置，重新呼叫 `generateBatch(1, opts)` 產生一筆新標題（沿用同一批次的 `weighted`/`useSynonymVariety` 設定），`excludeSet` 排除同一批次裡其他列的標題（第二批還會額外排除第一批全部標題，跟整批產生時的規則一致），成功後把新產生的列**沿用原本的 `uid`** 直接取代陣列該位置（不是 push 到最後），這樣使用者視覺上會覺得是「原地換掉」而不是跳到列表最後。若詞庫組合一時抽不出新的不重複結果（極端情況），`generateBatch` 回傳空陣列，此時顯示 toast 提示並保留原標題不變。
- **圖片分析只建議「核心關鍵詞候選」可點擊套用，賣點建議純參考不可插入**：`buildImagePrompt()` 要求模型回傳 `{coreKeywords:[{en,zh}], suggestions:[{en,zh}]}`，`renderImageSuggestions()` 只有 `coreKeywords` 渲染成可點擊的 `.suggest-pill`（點擊會覆蓋 `f_coreEn`/`f_coreZh`，覆蓋前若欄位非空會 `confirm()`），`suggestions`（賣點／情境形容詞）渲染成不可點擊的 `.suggest-note` 純文字——因為這些自由文字建議不保證落在系統內建的 `FUNCTION_WORDS`/`ADJECTIVE_WORDS` 詞庫裡，貿然插入會破壞「標題只能用受控詞庫組裝」這個前提，改成純參考文字讓使用者自行判斷要不要手動調整核心關鍵詞或同義詞。
- **產品說明欄位（2026-08-16 應使用者要求新增）**：`state.fields.description`（`f_description` textarea，`defaultFields()` 已含此欄，`fieldsHasContent()`/`renderFieldsFromState()`/`bindFieldInputs()`/`presetSelect` 套用邏輯都要一併涵蓋，5 組 `PRESETS` 也各自補了一段虛構的產品說明範例）。**這個欄位完全不影響離線生成路徑**（`generateBatch()`/`coreTermFor()` 都不會讀它），純粹是餵給 AI 當額外上下文：`buildScorePrompt(rows, platform, coreKeyword, description)` 多一個參數，非空時插入一行「這項商品的補充說明（賣家提供，判斷是否合理搭配時請以這段內容為準）：...」，並在檢查項 (b)（規格/功能/形容詞跟核心關鍵詞搭配是否合理）的敘述後面附註「（及上述補充說明）」；`buildImagePrompt()`（無參數，直接讀 `state.fields.description` closure 變數）非空時同樣插入一行類似說明，並在賣點建議那一項附註「與上述產品說明」。呼叫端 `runAiScoring()`/`analyzeImageBtn` click handler 不需要額外改動，兩個 prompt builder 內部各自處理是否有值。**測試方式**：跟其他 AI 邏輯一樣攔截 `window.fetch` 讀取 `opts.body` 反解 `messages[0].content` 確認文字裡含有填入的產品說明內容（圖片路徑要注意 `content` 是陣列，需要 `find(c=>c.type==='text')` 取出文字部分，不能直接當字串比對）。
- **`callLLM()` 比姊妹專案多一個可選的 `imageDataUrl` 參數**：有帶圖片時，Claude 走 `content:[{type:'image',source:{type:'base64',media_type,data}},{type:'text',text}]`，OpenAI/OpenRouter 走 `content:[{type:'text',text},{type:'image_url',image_url:{url:dataURL}}]`，Gemini 走 `parts:[{text},{inline_data:{mime_type,data}}]`（`splitDataUrl()` 用 regex 從 `data:image/...;base64,...` 字串拆出 mime/base64）。純文字呼叫（AI 熱度評分）不帶這個參數，行為與姊妹專案的 `callLLM()` 完全一致。圖片分析需要使用者選擇支援視覺輸入的模型（Claude／GPT-4o／Gemini 系列），本工具不做模型能力檢查，呼叫失敗會顯示 API 回傳的錯誤訊息。
- **CSV 匯出**：`downloadCsvBtn` 合併 `state.batch1`＋`state.batch2` 成一個表格，`csvCell()` 對含逗號/雙引號/換行的欄位做 `""` 轉義並加雙引號包裹，Blob 內容前綴 `'﻿'`（UTF-8 BOM）避免 Excel 開啟中文欄位亂碼——**這是本工具第一次在工作區內實作 CSV 下載**（姊妹專案的「已儲存的提示詞」下載是 `.txt`），之後其他專案若要加 CSV 匯出可直接參照這個 `csvCell()`/BOM 寫法。
- **平台切換會清空已產生的兩批標題**：`platformTabs` 的 click handler 若偵測到 `state.batch1.length || state.batch2.length` 非空，會先 `confirm()` 再清空——因為不同平台的詞庫過濾結果不同，保留舊資料容易造成「標題與目前平台規則不符」的混淆。
- 狀態存 `localStorage`（key: `ptgState`）：`{activePlatform, fields:{coreEn,coreZh,synonyms,description}, batch1:[], batch2:[]}`——兩批標題本身也存進 state（不是只存欄位），重新整理頁面後仍看得到已產生的標題。
- **表格「拆解」欄已移除（2026-08-16 應使用者要求）**：`renderBatchTable()` 的 `<thead>` 少了「拆解」一欄，`<tbody>` 也不再組 `tagsCell`，表格從 6 欄變 5 欄（#／標題英／標題中／星等／分級／操作），`table.titles` 的 `min-width` 同步從 860px 降到 740px；`td.tags`/`.tags-na` 這兩條 CSS 規則也一併刪除（不再有任何元素使用）。**這只是 UI 精簡，不是拿掉資料**——`row.specEn`/`funcEn`/`adjEn` 這三個底層欄位還在，CSV 匯出（`downloadCsvBtn`）依然會輸出規格詞／功能詞／形容詞三欄，改動時不要誤以為連 CSV 那幾欄也該一起拿掉。
- **「🗑 清除全部資料」按鈕（2026-08-16 應使用者要求新增）**：跟原本只清欄位的「清空欄位」（`clearBtn`）是兩個獨立按鈕，`clearAllBtn` 除了跟 `clearBtn` 一樣重置 `state.fields`，還會清空 `state.batch1`/`state.batch2`、重置 `sortState`、清空兩批的 report 訊息、重置圖片上傳區（`currentImageDataUrl`／`imagePreview`／`imageSuggestions`／`imageReport`）——是目前唯一「一次歸零整個工作區」的入口，本質上等同重新整理頁面後清 localStorage 但不用真的清 localStorage（序號、API 設定不受影響，只清商品資料）。有內容時走 `confirm()` 二次確認再執行。
- **表格排序（2026-08-16 新增）**：`sortState = {batch1:null, batch2:null}` 是模組層級變數，**刻意不存進 `localStorage`**（排序只是畫面顯示順序，不是資料本身，重新整理頁面應該回到原始順序）。`renderBatchTable(batchKey, rows)` 依 `sortState[batchKey]` 對傳入的 `rows` 做「複製後排序」（`rows.slice().sort(...)`），不會 mutate `state.batch1`/`state.batch2` 本身——CSV 匯出讀的是 `state.batch1`/`state.batch2` 原始順序，不受畫面排序影響。點擊「星等」或「分級」的 `<th class="sortable-th">` 都觸發同一個排序（兩者本來就 1:1 對應，`tier` 永遠是 `STAR_TIER[stars]`），在 `desc`/`asc` 間切換。產生新一批（`genBatch1Btn`/`genBatch2Btn`）或切換平台／套用範例時，對應的 `sortState[batchKey]` 會重置為 `null`。
- **API 連線設定面板已於 2026-08-16 應使用者要求移到 `<main>` 最上方**（原本在圖片分析面板之後），理由是 AI 熱度評分／圖片分析都依賴這組設定，先填能減少使用者來回捲動；`#apiPanel` 的 DOM 位置改變不影響任何 JS 邏輯（`initAiPanel()`／`callLLM()` 都是用 `id` 選取元素，與版面順序無關）。

## 序號授權（鎖定整個工具，12 個月）

比照 `ai-image-prompt-studio`／`ai-prompt-generator`／`ai-music-prompt-studio` 的「單一工具、整個鎖住」模式：`#licenseGate` 全螢幕遮罩預設鎖定，驗證通過才加上 `.hidden`；載入時一律對後端即時重驗，背景每 20 分鐘重驗一次。`localStorage` key：`ptgSerial`。

- **綁定的 Google Sheet 是使用者指定沿用的既有表**：<https://docs.google.com/spreadsheets/d/1pqGlCvUstowBzZh7J4xEa0jy3KoK4UeHUiyMTzcSGo4/edit>。`Code.gs` 採用 `ai-music-prompt-studio` 那套更保守的**雙層掃描**版本（`findLicenseSheet_()` 掃描 `ss.getSheets()` 每一個分頁＋`findHeaderRow_()` 在每個分頁裡找表頭列），不是 `ai-image-prompt-studio` 那個假設「表頭一定在第一分頁的 `values[0]`」的簡化版——因為這份既有 Sheet 的實際分頁/表頭位置在動工當下未知，用更保守的版本可以避免重踩 `ai-music-prompt-studio` 已經記錄過的坑（`server_error` 但訊息不明顯，容易被忽略）。
- **已於 2026-08-16 完成部署並端對端驗證**：`LICENSE_CHECK_URL` 已回填 `https://script.google.com/macros/s/AKfycbwYlSTK5tgPIQSB6e2eHgaP8Jc89ZKgyP_OYy9UHfAKZ-8RmKVGLZ-wJeyjr3l1blcz/exec`。GET 健康檢查與 POST 假序號（正確回傳 `serial_not_found`，證明找得到 Sheet 裡的表頭欄位）皆已用 Node `fetch()`／真實線上頁面測過。
- **這支後端只做序號驗證，不代理任何付費 API**（LLM 串接是 BYOK），也**不處理跑馬燈**。
- **部署踩坑**：clasp 沒有指令能把新腳本綁定到一個「已存在」的 Sheet——`clasp create --type sheets --parentId <既有SheetId>` 會把 `parentId` 當成 Drive 資料夾 id，平白新建一份空白試算表（已用 Drive MCP `trash_file` 清掉），**之後要幫其他專案接既有 Sheet 的 Apps Script，一律請使用者自己開 Extensions→Apps Script 建立綁定專案，把 Script ID 給 Claude 做 `clasp clone`/`push --force`**。使用者一開始手動複製貼上 Code.gs 到編輯器出現「Unexpected token 'finally'」（已知剪貼簿踩坑），改走 clasp 推送後，使用者瀏覽器分頁需要手動重新整理（F5）才會看到新內容，不會自動同步。第一次部署「誰可以存取」沒選對「任何人」，`curl -sI` 回 403、`curl -sL` 被導去 Google 登入頁；改對設定後重新部署會拿到**新的** `/exec` 網址（不是原本那組）。之後序號驗證連不上／一直失敗的報修，先檢查部署的存取權限設定，不要預設是程式碼問題。

## 頂部共用跑馬燈

`#marqueeBar` 內容抓自工作區既有的共用授權伺服器（`https://script.google.com/macros/s/AKfycbwKX0.../exec`，與 `Prompt`／`ai-prompt-generator`／`ai-image-prompt-studio`／`ai-music-prompt-studio`／`ai-video-studio` 系列共用同一個 Google Sheet），做法完全比照姊妹專案——跟本工具自己的序號授權後端是兩個互不相干的系統。`localStorage` key：`ptgMarquee`。

**2026-08-20 更新（`Code.gs` 未改動、不需重新部署）**：`render()` 新增 `lastKey`（`JSON.stringify(items)`）比對，內容沒變就不重繪，CSS animation 不再被重置歸零重跑；新增 `appendParsedText()`／`buildTrackContent()` 支援 `[文字](https://...)` 連結語法（`createTextNode` 組 DOM，避免 XSS），資料格式仍是純字串陣列，向下相容。已 commit＋push（GitHub Pages 自動重新部署）。

## 加入主畫面（PWA，2026-08-16 新增）

比照 `ai-image-prompt-studio`／`ai-prompt-generator`／`ai-music-prompt-studio` 的既有做法：`manifest.json`＋`icons/`（藍色 `#3b82f6` 背景「標」字圖示，`icon-192.png`／`icon-512.png`／`apple-touch-icon.png` 皆用 PIL 產生）＋`service-worker.js`（network-first＋同源快取備援，`fetch(req,{cache:'reload'})` 從一開始就寫上，不是事後補的踩坑修正）。頁尾 `.footer-meta` 新增「📲 加入主畫面」按鈕（`#installBtn`），獨立 IIFE，跟序號授權閘門互不相依。

**這次一開始就用「自己實作 `notify()`，不依賴外部 `showToast`」的寫法**（不是像早期姊妹專案那樣先踩坑再修）——因為 PWA 安裝腳本是獨立 `<script>`／獨立 IIFE，主程式的 `showToast()` 宣告在另一個 IIFE 裡，函式作用域不會跨 `<script>` 區塊共享，`typeof showToast` 在安裝腳本裡永遠是 `'undefined'`；`notify()` 直接操作 `#toast` DOM 元素自己實作，是全部姊妹專案 2026-08-16 前已知的系統性 bug 的修正版寫法，日後任何新專案要加類似的「主程式定義工具函式、獨立掛載小功能想沿用」情境，直接照這個寫法（自己拿 DOM 元素、不依賴跨 IIFE 函式），不要重踩。

iOS／iPadOS／macOS Safari 相容性判斷（`isIOSDevice`／`isMacDesktop`／`isSafariEngine`／`isStandalone`）與 `<head>` 的 `apple-touch-icon`／`apple-mobile-web-app-*` meta 標籤，比照姊妹專案逐字複製，未另外調整。本次未實測 Chromium 的 `beforeinstallprompt` 觸發／SW 註冊之外的實機安裝流程（iOS 裝置無法在此環境測試）。

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
- Sheet 內尚未有真實序號可測試「解鎖成功＋剩餘天數顯示」這條路徑（目前只驗證過假序號的拒絕路徑）；要開放給使用者，直接到 Sheet 有「序號」欄的分頁新增一列，序號欄填值、開始/結束日期留空即可。
