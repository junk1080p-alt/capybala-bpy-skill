# CAPYBALA BPY SKILL - BLENDER AUTOMATION

<p align="center"><a href="README.md">English</a> | <b>繁體中文</b> | <a href="README.zh-CN.md">简体中文</a></p>

一份份量扎實、經過實戰打磨的 **SKILL.md**，讓 AI coding agent 透過無頭（headless）Blender 完成建模、材質、燈光、渲染與匯出——目標是**第一次交付就達到真正的品質水準**，不是一份還要來回三輪「再修一下」的粗胚。

🦫 這是 **Capybala**（一款即將推出的 AI agent 桌面應用程式）的內建能力之一，這裡單獨拿出來分享。

<p align="center">
  <img src="gallery/wtc-towers.png" width="32%" alt="World Trade Center towers, architectural reconstruction" />
  <img src="gallery/dive-watch.png" width="32%" alt="Mechanical dive watch, product render" />
  <img src="gallery/space-station.png" width="32%" alt="Modular space station, backlit" />
</p>

## 為什麼會有這個東西

GPT-6 ASTRA 推出後，各大時間軸上突然滿滿都是令人驚艷的 3D 生成成果——完整的產品渲染圖、整棟建築、整個場景，看起來幾乎是免費生出來的。很難不去想：一個便宜、快速、完全沒受過 3D 專門訓練的模型，有沒有機會做出接近的東西？

當然不是要跟 GPT-6 那個等級比——那從來不是目標。真正想知道的是：能不能打敗「叫 LLM 隨便寫幾行 `bpy` 程式碼、賭它會好看」這種常見結果——通常是幾何對不齊、材質不管指定什麼都長得像塑膠、相機角度全憑猜測。

這份 skill，就是拿 **DeepSeek V4.1 Flash** 這個具體目標去追這個問題後的產物——一個小、便宜、沒有任何特殊之處的模型。放著不管，它產出的正是上面說的那種粗糙結果。透過這份 skill 的 Stage A → B → C 工作流程（動手前先規劃元件清單、依照校準過的相機/燈光/材質預設值建模、完工前拿實際渲染統計數據自我審查一輪），產出的就是下面這個 gallery。

這是 GPT-6 ASTRA 的水準嗎？不是，這裡沒有任何一句話這樣宣稱。但對一個完全沒有 3D 專精的模型來說，「沒有這份 skill」跟「有這份 skill」之間的落差，正是做這個專案的全部意義。

Gallery 裡的每一張圖，都是 **Capybala 自己的 agent runtime**（尚未公開）驅動 DeepSeek V4.1 Flash、透過這份 skill 生成的。skill 本身不依賴那個 agent——見下方[跟 agent 一起使用](#跟-agent-一起使用)——任何能跑 Python、能讀寫檔案的 coding agent 都能用同樣的方式運作。

## 誠實面對的限制（看 gallery 之前請先讀這段）

- **下面每一張圖都是用 DeepSeek V4.1 Flash 做的**——不是更聰明、更貴的模型。換一個模型套用這份 skill，結果會往任一方向移動：更強的模型可能更懂得照著判斷邏輯走、產出更乾淨的結果；較弱的模型可能需要更多修正輪次，或達不到這裡展示的水準。這個 gallery 不是任何模型的保證值。
- **這個 gallery 是精選過的，不是平均水準。** 這些是一堆嘗試裡挑出來值得展示的成果，很多其他嘗試沒有做到這個水準——對一個「輔助模型判斷，不是取代判斷」的工具來說，這是正常現象。
- **有兩類主題是目前已知、確實存在的弱項：車輛跟人形。** 車身鈑件（複合曲面、接縫、可信的比例）跟人體結構，都是這份 skill 技法庫還很薄弱、結果不穩定的領域——比起下面展示的產品/建築/硬表面類主體，車輛跟人形更容易做得粗糙、需要更多手動修正，甚至直接失敗。下面那台復古腳踏車是剛好做得不錯的個案，不代表車輛類的一般水準。

## Gallery

| | | |
|---|---|---|
| ![World Trade Center](gallery/wtc-towers.png) 世界貿易中心雙塔 | ![Dive watch](gallery/dive-watch.png) 機械潛水錶 | ![Espresso machine](gallery/espresso-machine.png) 雙孔義式咖啡機 |
| ![Vintage roadster](gallery/vintage-roadster.png) 復古敞篷腳踏車 | ![Cargo bike](gallery/cargo-bike.png) 貨運腳踏車 | ![Leifeng Pagoda](gallery/leifeng-pagoda.png) 雷峰塔 |
| ![Nova Tower](gallery/nova-tower.png) Nova Tower 辦公大樓 | ![Residential tower](gallery/residential-tower.png) 20 層住宅大樓 | ![Space station](gallery/space-station.png) 模組化太空站 |
| ![Launch vehicle](gallery/launch-vehicle.png) 發射台上的運載火箭 | ![Vintage fan](gallery/vintage-fan.png) 復古鍍鉻電風扇 | |

### 更多角度與細節

<p align="center">
  <img src="gallery/wtc-night-lowangle.png" width="24%" alt="WTC towers, low angle, dusk" />
  <img src="gallery/wtc-night-reflect.png" width="24%" alt="WTC towers, reflective glass, dusk" />
  <img src="gallery/wtc-memorial-street.png" width="24%" alt="WTC memorial plaza, street level" />
  <img src="gallery/wtc-memorial-calib.png" width="24%" alt="WTC memorial plaza, an earlier exposure-calibration pass" />
</p>
<p align="center"><em>最後一張是曝光校準過程中的中間渲染，刻意原樣保留——這份 skill 在正式出圖前會跑一輪自我校正，這是那個過程的真實樣貌，不是藏起來的失誤。</em></p>

<p align="center">
  <img src="gallery/dive-watch-detail.png" width="32%" alt="Dive watch, bezel and crown macro detail" />
  <img src="gallery/vintage-roadster-drivetrain.png" width="32%" alt="Vintage roadster, drivetrain detail" />
  <img src="gallery/leifeng-plaque.png" width="32%" alt="Leifeng Pagoda, entrance plaque detail" />
</p>

<p align="center">
  <img src="gallery/space-station-eclipse.png" width="24%" alt="Space station, eclipse rim lighting" />
  <img src="gallery/space-station-lowgraze.png" width="24%" alt="Space station, low graze lighting" />
  <img src="gallery/space-station-wing.png" width="24%" alt="Space station, solar wing front" />
</p>

上面每個場景（加上這些額外角度）的完整解析度 `.blend` 專案檔，都打包成下載檔放在這個 repo 的 [Releases](../../releases) 頁面——歡迎自己用 Blender 5.1 打開來看，每個場景實際上是怎麼建出來的。

## 裡面到底裝了什麼

這不是一句短短的 prompt，而是一份完整的操作手冊加上一整套程式庫：

- **`SKILL.md`**——agent 動手前要讀的操作手冊：上面提到的 Stage A → B → C 工作流程、經過驗證的 Blender 5.1 API 落差對照表、依真實渲染輸出校準過的相機/燈光/曝光預設值，還有一長串「這樣做會出問題，這是修法」的規則，涵蓋最容易被忽略的視覺失誤（穿模、懸空、材質死板無生氣、相機構圖錯誤等等）。
- **`assets/*.py`**——一套純 `bpy` Python 程式庫（材質、參數化造型、建築、道路、自然地景、細節加工、從參考圖重建三視圖、幾何量測工具），讓 agent 直接呼叫，不用每次都手刻基礎形狀。不依賴任何 app——就是普通的 Blender Python，裝了 Blender 的人都能直接跑。
- **`assets/anatomy/`**——依產品/建築/容器類別分類的組件清單（例如「機械錶該有哪些零件，不要做成一個空殼」），確保明顯的東西不會被漏掉。
- **`assets/styles/`**——具名的設計風格參考卡（建築師、工業設計流派、類型風格），附上具體的比例/材質/色票數值，而不是模糊的氛圍形容詞。
- **`assets/examples/`**——依主題類型整理的完整端到端範例。
- **`assets/scene_pkg/`**——結構化的場景包格式（config/layout/geometry/materials/assertions），給規模超出單一腳本的場景用。

## 需求環境

- Blender 5.1.x（針對 5.1.2 驗證過；其他 5.1.x 版本應該很接近，見 `SKILL.md` 開頭的版本漂移警告）
- Python 3（`assets/*.py` 程式庫用 Blender 內建的直譯器就夠；`assets/component_measure.py` 這類獨立腳本透過 `blender --background --python ...` 執行）
- 選用：[ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)（MIT）——如果你想從支援 MCP 的用戶端互動控制，而不是純無頭腳本——`SKILL.md` §0–§1 兩條路徑都有涵蓋，包含一支六級 `blender.exe` 路徑解析器（`assets/find_blender.ps1`，Windows），避免寫死安裝路徑。

## 跟 agent 一起使用

`SKILL.md` 原本是為了在 Capybala 自己的工具組裡跑的 agent 而寫的，所以有一部分指令會呼叫特定的原生工具名稱（`read_image_native`、`run_python_native`、`read_file_native`、`write_file_native`）——每一處出現這些名稱的地方，都在原地附註了其他平台的等價操作。如果你是人類直接照著手冊操作，或是要接到別的 agent 架構上，這些指令對應的都是最普通的動作：「看一下這張圖」「跑這段 Python」「讀/寫這個檔案」。真正的 Blender/bpy 技法內容——`assets/` 底下的所有東西——完全沒有這種依賴，可以獨立使用。

這份文件也遵循 **Claude Code** 與其他支援可載入 skill 的 agent 平台通用的 skill 檔案慣例——只要在 `SKILL.md` 最上面加上標準的 YAML frontmatter（`name`/`description`），把整個資料夾丟進 `.claude/skills/`（或你平台的對應位置），就能直接在那邊使用。

### 關於語言的說明

`SKILL.md` 本身就是用**繁體中文**撰寫的（程式碼、函式名稱、API 引用照 Python/Blender 的規矩維持英文，只有說明文字是中文）。這份 README 是英文原文翻譯過來的，對繁體中文讀者來說沒有任何障礙——`SKILL.md` 可以直接讀，不需要再翻譯。

## 技術亮點

幾個真正有工程深度、不只是「叫模型小心一點」這種空話的地方：

**幾何品質是量出來的，不是叫模型自己看著辦。** `build_template.py` 內建一套建完就自動跑的稽核：`audit_interpenetration()` 兩兩掃描物件找真正的重疊（先用包圍盒快篩，緊密貼合的機構件——卡鉗貼碟盤、輪圈套輪胎——可選用 BVH 網格級相交判定，這種情況下包圍盒重疊本身沒有意義）；`audit_floating()` 對每個物件的底面做 raycast 找支撐面，但分得清楚「放在什麼上面」跟「側向鎖固/螺栓固定在什麼側面」是兩回事（`mark_side_attached()`/`mark_joint_attached()` 會把懸臂或鎖固的零件改走表面間距檢查，而不是重力式支撐檢查，牆上的告示牌不會被誤判成懸空）；`audit_spacing()` 抓陣列裡座標悄悄跑掉的那一件。這些不是選配建議——結果會寫進 Stage C 強制要查的場景狀態欄位，而且容差會依主體實際尺度自動調整（一台 138mm 的相機跟一棟 40 層大樓，容差不會用同一套毫米級標準）。

**用「製造業」的思維取代「疊方塊」。** 這份 skill 把幾何當成真實物件實際被製造出來的樣子在處理：開口用布林差集挖出來、有真實的壁厚（不是「那裡就不建牆」這種假開口）；邊緣的倒角/導圓角半徑是依物件尺度主動決定的值（不是 Blender 預設的零倒角）；任何現實中會用車床車出來的零件——錶冠、旋鈕、相機鏡筒、瓶蓋——一律用迴轉剖面函式建出來，而不是圓柱體加倒角修飾器，因為真實車製件的半徑是沿軸向連續變化的，這是「拉伸再倒角」這個組合在結構上做不到的事。

**曝光是通過／不通過的硬性關卡，不是憑感覺看看。** 每一種場景類型（棚拍、戶外黃金時刻、夜景）都有數字化的亮度目標帶，渲染結果超出範圍會在送到人眼前就自動判定失敗。燈光能量來自依真實渲染輸出校準過、並依主體包圍盒縮放的預設值，而不是照抄絕對數字；另外還有一個 mean/median 落差檢查，專門抓「一個亮點（一扇亮著的窗、一塊招牌）把平均值撐進合格範圍，但畫面其餘大部分接近全黑」這種假通過。

**複刻真實物件被當成量測問題處理，不是憑感覺畫。** 當有真實世界的對應物件時，參考資料會被分成四個證據等級——從官方正交工程圖到只有規格數字——每一級明確規定它能證明到什麼程度，讓一張普通照片可以用來推估比例，但永遠不會被拿來跟標註尺寸的工程圖同等級引用。整套比對流程（校準 → 擷取輪廓 → 放樣 → 閉環驗證）會把規劃階段的元件清單跟實際量測到的幾何互相比對兩次——動工前一次、完工後一次；還有一支標註圖產生器，會把量測到的輪廓畫回原始參考照片上並標上編號，讓後續的修正意見可以直接說「A-3 位置不對」，不需要用一整段文字描述座標。

## 授權

MIT——見 [LICENSE](../LICENSE)。
