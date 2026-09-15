# 日式街景 3 渲 2（日間）Anime Cel Daylight（通用風格類型，非特定作品重製——見誠實聲明）
觸發詞：日式街道、日式街景、和風街區、日本街、動漫風、二次元、3 渲 2、三渲二、賽璐璐、
cel shading、toon shading、**絕區零風、ZZZ 風、原神風街景、二遊級畫面、罪惡裝備風、
Guilty Gear 風**；以及「日式場景但使用者沒指定風格」的預設路由（見「預設路由」段）
適用年代：不適用（當代美術語言，非歷史年代分期）

> **誠實聲明**：本卡不是重製任何特定動畫/遊戲畫面，是把「日間 3 渲 2 日式街景」抽成可複用的
> 色票／著色管線／打光規則。**主要參照定為《絕區零》的環境美術方向（灰調都會 + 高飽和圖形
> 點綴）與《罪惡裝備》Xrd/Strive 系列的描邊技法（背面法）**——這兩個是本卡實際校準的目標，
> 不是隨口列出的一串「風格差不多」的作品清單。

## ★ 預設路由（本卡最重要的一條）
1. **日式場景 + 使用者沒指定風格 → 一律本卡**。不要退回寫實 PBR，也不要自動跳到夜景霓虹。
2. **品質等級預設 = 進階路線（漸層 cel，見下）**；只有「遠景/極簡/低預算快渲」才降級用基礎
   平塗路線。
3. 使用者明確要「寫實觀光照片感」→ 不用本卡，走 `anatomy/buildings/` +
   `japanese_street.md` 的一般寫實流程。
4. 使用者要「夜晚／霓虹／賽博龐克」→ **目前沒有可路由的夜景卡**（原 `anime-neon-tokyo.md`
   已下架重做）。照 `_TEMPLATE.md` 現場建卡，或明說尚未支援；不要用本卡的日間色票硬當
   夜景。構件清單仍共用 `anatomy/spaces/japanese_street.md`。
5. **不畫車與人（硬規則）**：本卡路線下預設不出現汽車/機車/公車/行人/人物立牌——這類主體
   在量化著色管線下造型保真度最低，會成為整張圖最明顯的破口。要表達「有人在生活」改用
   鐵捲門半開、晾衣桿、靜止的腳踏車、自動販賣機、路邊雜物堆、亮著的店內燈（見
   `japanese_street.md`）。使用者明確要求時，先說明是已知弱項，再走 `anatomy/car.md` /
   `proportions_lib.human_proportions()` 的專屬流程。
6. **單一主體走展示卡模式，不去蓋一整條街**：鏡頭是「在拍這個東西」→ 展示卡模式
   （`T.setup_cel_studio()`，見下）；鏡頭是「在看這個地方」→ 敘事場景模式。一條街的構件
   密度/天空佔比/招牌堆疊是為敘事場景設計的，套在單一主體上只會讓主角淹沒在配角裡。

## ★ 一句話定位
**進階漸層 cel**（硬陰影邊界 + 受光帶內柔和漸層 + AO 接觸陰影 + 冷色邊緣光）× **背面法
外輪廓線**（真幾何、線寬隨相機距離/焦距自動補償）× 灰調環境 + 高飽和圖形點綴——3D 幾何、
動畫攝影邏輯，向《絕區零》的環境美術與《罪惡裝備》Xrd/Strive 的描邊技法校準。

## ★ 理念
1. **3 渲 2 是「2D 色塊邏輯套在 3D 幾何上」，不是「畫不寫實所以將就」**：幾何骨架維持寫實
   比例（沿用 `anatomy/buildings/residential.md` / `office.md` / `japanese_house.md` 的
   數值），但明暗被量化成少數幾階、色塊邊界是硬的。這是刻意選擇的美術語言。
2. **陰影邊界硬、但受光面內部有一段柔和漸層**（mid→high）：這是本卡的預設著色模型，
   加上縫隙 AO 接觸陰影與面向鏡頭的冷色邊緣光。**平塗三階路線仍保留，但定位是「遠景/快渲
   降級用」，不是另一個平起平坐的美術方向**——兩條路線的差別是品質等級，不是各有各的美術
   語言，不要把它們當成使用者自由二選一的風格分支。
3. **陰影不是「變暗」，是「往紫/藍位移 + 提高飽和」**：動畫陰影色是另一個顏色的色塊，不是
   同一色打暗。本卡色票的三階都是各自獨立的 hex，不是 base × 0.6 算出來的。
4. **描邊優先用背面法（inverse hull），Freestyle 選擇性描邊是快渲/遠景的降級選項**——這是
   《罪惡裝備》Xrd 系列的主力技法（官方 CEDEC2024 講題原名「背面法」，用了 20 年以上仍是
   第一線做法），線寬隨相機距離/焦距自動補償，逐部位可調粗細/有無。技術細節見「細節特徵」
   一節，這裡只定優先序：**背面法優先，Freestyle 是省設定成本的次選，不是平起平坐的兩條路**。
5. **外輪廓線是必要元件，不是可選裝飾**：沒有線的平面色塊會讀成「塑膠玩具」而不是「賽璐璐」。
   線只有一個來源，材質內不要再疊 outline，否則會出現雙線。
6. **色彩策略：灰調環境打底 + 焦點物件高飽和點綴，這是本卡的預設，不是二選一**——環境（牆面/
   路面/大面積量體）走低彩度，高飽和色留給焦點（招牌/道具/貼紙/燈箱），這正是《絕區零》
   街景「灰調都會 + 圖形點綴」的識別度來源，也是動畫攝影常見的「不要讓每個物件都搶戲」
   原則。全場高彩度的「觀光町屋」畫法不在本卡目標範圍內，使用者明確要那種效果時另外處理，
   不要套本卡的色票硬做。**色票是起點參考不是配額**——使用者給參考圖或指定色時一律以使用者
   為準，但沒有指定時，預設就是灰調環境+高飽和點綴，不是「隨便選一種」。
7. **白天是這張卡的主場**：高飽和晴空 + 邊緣分明的積雲是辨識度的一半，天空佔畫面比例刻意
   拉高（見形式語言）。
8. **車與人是零分項**（見預設路由#5）：不做比做壞好。

## ★ 形式語言
- **比例系統（§15.0）**：對比與焦點為主、留白與簡約為輔——張力來自「大片低飽和色塊 vs 少量
  高資訊密度構件（招牌堆疊/電線網/圖形化貼紙）」的對比，以及天空的大面積留白。不套黃金比例
  的精確有機曲線語言；招牌高度/尺寸刻意參差，不追求模矩制整數比。
- **天空佔比**：日間街景天空佔畫面高度 30–45%；鏡頭壓低讓建築天際線落在畫面上 1/3，避免
  俯視（俯視會讓天空消失、色塊感全失）。
- **外輪廓線**：優先背面法（inverse hull），完整參數與 API 見「細節特徵」；Freestyle 選擇性
  描邊（FG 粗深線 #241F26／BG 細淡線 #8A8794）是快渲/遠景的降級選項，實作走
  `build_template.setup_selective_outline()`。**兩條路線互斥，只選一個**。
- **圓角策略**：建築邊角小倒角 0.5–1.5cm（避免死直角在描邊下變成粗黑角）；招牌圓角
  R ≈ 0.05 × 短邊。
- **對稱性**：不強調對稱——街道的自然感來自參差的招牌高度與寬度。
- **圖形設計元素（識別度核心，不是加分項）**：灰調街景不是「乾淨的動畫背景」，而是**貼滿
  平面設計**——大色塊貼紙、斜切色帶、粗體字排版、警告標誌圖形、噴漆塗鴉。用
  `detail_lib.make_text()` + `shape_lib.flat_decal()` / `detail_lib.apply_image_decal()`
  貼在牆面/捲門/電箱上。純色牆面＝半成品。

## ★ 展示卡模式（單一主體；與敘事場景模式並列，不是它的子集）

**一句話**：單一主體（產品/道具/單一建築）的「展示卡」請求，用
`T.setup_cel_studio(mesh_objs, ground_mat=...)` 在 `subject_fn()` 裡呼叫一次取代
`T.auto_frame_and_light()`——它一次把 cel 展示卡需要的全部條件接好，參數直接寫進 `main()`。

**為什麼不能沿用 PBR 的展示卡設定**（§10.3：中性灰背景 + 三點式 AREA + AgX）：那組搬進 cel
會壞三件事——① 三盞能量相當的 AREA 燈**各自產生一條明暗界線**，cel 的硬邊界糊成好幾條；
② AgX 把色票打歪（cel 必須 Standard）；③ 地面是程序化噪聲混染，跟「cel 表面必須是乾淨色塊」
直接衝突。`setup_cel_studio()` 就是同一張展示卡的 cel 版：

| 項目 | 設定 | 理由 |
|---|---|---|
| 引擎／色彩映射 | EEVEE + `Standard` | ShaderToRGB 只在 EEVEE 有意義；AgX 會吃掉整階色票 |
| 打光 | **一盞 SUN `angle=0`**（唯一明暗界線來源）+ 低能量 `CelFill` | 明暗界線只能有一個來源；`angle=0` 切斷半影 |
| 太陽方位 | 相機方位 **`sun_offset_deg=-40°`** | 見下方「單一參數最影響成敗」 |
| 背景／地面 | 純色中性（線性 0.22）+ cel 色塊地面 | 天空漸層＋雲是敘事場景的語言，展示卡要讓主體跳出來 |
| 描邊 | `request_outline()`（背面法，ORTHO 專屬線寬公式） | 相機就位後才建，線寬用真正的最終相機算 |

**單一參數最影響成敗：`sun_offset_deg`（太陽相對相機的水平偏移）**。設 0（太陽跟相機同向）
時明暗界線會落在主體的**輪廓線上**——實測陰影只剩 2-10%，「明暗界線落在哪裡」這個畫面主體
直接消失。預設 -40° 讓界線橫過可見面（實測陰影約 36%）。

**`sun_energy` 與 `bg_color`（實測校準，960×540 calib、單一 cel 材質的參考球，量各色階像素
佔比）**：背景線性 0.22、offset -40° 時（shadow / mid / high，%）——`sun_energy` 1.8 →
46.8 / 53.2 / 0.0（受光面吃不到最亮階）、**2.0 → 36.2 / 36.8 / 27.0（預設值）**、
2.2 → 26.2 / 24.1 / 49.7（受光面開始飽和）、3.0 → 15.6 / 10.3 / 74.2（只剩兩階）。
`fill` 預設約太陽的 10%，`fill=False` 實測 37.7 / 36.2 / 26.1（與有 fill 幾乎相同）＝
它只在保底、不搶戲。

**這個量法只適用單一材質的場景**：多材質展示卡的像素會被誤歸到鄰近色階（實測三材質場景量到
「陰影 71%」，但圖上受光面明顯佔了一半）——多材質請直接看渲染圖調參，或只對單一材質給 `roi`。

**環境光遮蔽與描邊都要真的存在**：`make_cel_advanced()` 的 AO 讓物件「貼地」，背面法外殼給
剪影線——兩者是「展示卡」而不是「渲染測試」的分界。順序：建材質 → 建幾何 →
`setup_cel_studio()` → CALIB 看色階/構圖 → 正式渲染。

**已知限制（實測）**：① 地面上的**投影邊界**在 EEVEE 下會有階梯狀鋸齒（shadow map 精度問題，
提高主體網格細分完全無效，因為那不是幾何問題）。主體自身的明暗界線沒問題，鋸齒只出現在
「投射到地面上」的那條——要更乾淨就縮小地面尺寸或改走敘事場景模式。② 主體量大時
`diag×1.8` 的相機距離可能把旁邊的東西一併納入構圖，用 `ortho_margin` 微調。

## ★ 天空配方

`build_template.add_stylized_sky()`（純色雙色漸層 + 選填雲遮罩；**不要**用 `build_world()`
的 Nishita Sky Texture——那個算不出高飽和晴空 + 邊緣分明的積雲）：

```python
# 日間強晴（本卡預設）
T.add_stylized_sky(zenith_color=M.hex_to_linear('#1E6FD9'),
                   horizon_color=M.hex_to_linear('#C9E6F8'),
                   cloud_color=(1.0, 1.0, 1.0), cloud_coverage=0.30,
                   cloud_scale=2.0, cloud_softness=0.14, strength=1.0)

# 日間薄雲（陰天情境，雲量高、對比降一階）
T.add_stylized_sky(zenith_color=M.hex_to_linear('#4E90DC'),
                   horizon_color=M.hex_to_linear('#DCE9F2'),
                   cloud_color=(0.99, 0.99, 1.0), cloud_coverage=0.62,
                   cloud_scale=3.2, cloud_softness=0.35, strength=1.0)
```

## ★ 色票（起點參考，不是配額——使用者給參考圖/指定色時一律以參考為準；
以 `mat_lib.hex_to_linear()` 實算，非手算）

### A. 環境組（灰調環境的起點色——本卡預設方向，見理念#6）
三階一組（亮 = 受光面 / 中 = 半影 / 暗 = 陰影面），另加 high = 受光帶漸層頂端。
末欄是典型畫面佔比參考印象，不是驗收項目。

| 角色 | 亮(base) | 中(mid) | 暗(shadow) | 漸層頂(high) | 典型佔比（僅參考） |
|---|---|---|---|---|---|
| 建築外牆（灰暖混凝土） | #B9B4AC | #8E8B96 | #565468 | #D8D2C6 | 30-45% |
| 瀝青路面 | #7E8087 | #63656F | #4A4B5E | #9BA0A8 | 15-25% |
| 金屬/電柱/電線 | #9C9A98 | #77747F | #4E4A62 | #B8B6B4 | ≤8% |
| 天空天頂 | #1E6FD9 | — | — | — | 天空 55-70% |
| 天空地平 | #C9E6F8 | — | — | — | 天空 30-45% |

### B. 焦點點綴組（高飽和色，貼在招牌/道具/貼紙/燈箱這類焦點物件上）

| 角色 | 亮(base) | 中(mid) | 暗(shadow) | 漸層頂(high) |
|---|---|---|---|---|
| 招牌/道具（飽和黃） | #E8B23A | #C08A2E | #6E4A56 | #F6D478 |
| 招牌（朱紅） | #E2402F | #A8313F | #6B2350 | #F0705C |
| 植栽 | #4F8C3B | #35663A | #22463C | #6FA854 |
| 點綴藍 | #2F6FD0 | #27539B | #2A2A5E | #5C93E4 |

### C. 線條與邊緣光

| 角色 | 值 |
|---|---|
| 前景描邊線 | #241F26（近黑紫） |
| 背景描邊線 | #8A8794（灰紫淡線） |
| 冷色邊緣光 rim | #8FB8E8（面向鏡頭的冷藍勾邊） |

### D. 避免（沒有參考圖/指定色時的預設判斷，使用者指定時一律照做）
- 低飽和灰褐**寫實照片味**（整片 #8A8578 那種水泥灰）：會讓 3 渲 2 讀成「去飽和的照片」
  而不是色塊。要灰就給灰一個冷/暖位移（A 組示範的就是這件事）。
- 大面積純白受光面（#FFFFFF）：白留給雲與高光，整片純白會把色階吃掉。
- 高飽和品紅/青藍霓虹：那是夜景路線語言，日間用會讀成傍晚。

## ★ 材質映射表（直接可貼進 materials.py）

| 部位 | factory | 參數 |
|---|---|---|
| **環境/背景物件** | `mat_lib.make_cel_advanced()` | 例：`M.make_cel_advanced("Mat_Wall", base=M.hex_to_linear('#B9B4AC'), mid=M.hex_to_linear('#8E8B96'), shadow=M.hex_to_linear('#565468'), high=M.hex_to_linear('#D8D2C6'), rim_strength=0.0)`——色值來自 A 組或參考圖；環境件通常關 rim（邊緣光給焦點） |
| **焦點物件** | `mat_lib.make_cel_advanced()` | 同上，需要勾邊時加 `rim_color=M.hex_to_linear('#8FB8E8'), rim_strength=0.45` |
| 遠景/快渲降級（基礎路線） | `mat_lib.make_cel()` | CONSTANT 三階純平塗，見「著色管線」段 |
| Cycles 備援路線 | `mat_lib.make_toon()` | SUN 能量壓到 1.2-1.8；做不出漸層與 rim，僅保底 |
| 玻璃（店面櫥窗，日間） | `mat_lib.make_cel_advanced()` | 用天空地平色當 base：base #C9E6F8 / mid #9AB4CE / shadow #5B7A9E / high #E4F2FC，`rim_strength=0.0`。**不要用 `make_glass()`**（Transmission 在 EEVEE 下與成品路徑不一致，且 3 渲 2 要的是色塊不是折射） |
| 天空 | `build_template.add_stylized_sky()` | 見上方天空配方 |
| 外輪廓線（優先） | `build_template.setup_inverse_hull()` | 背面法，見「細節特徵」 |
| 外輪廓線（快渲降級） | `build_template.setup_selective_outline()` | `T.setup_selective_outline(fg_collections=["FG"], bg_collections=["BG"])`——layout 階段把焦點物件分進 `FG`、背景建築分進 `BG` |
| 動畫攝影後製 | `build_template.setup_anime_post()` | `T.setup_anime_post(bloom_threshold=0.85, bloom_strength=0.12)`——高門檻局部泛光，只暈自發光招牌/燈管 |
| **禁用** | `make_concrete` / `make_stone` / `make_wood` / `make_leather` / `make_brushed_metal` / `add_procedural_wear` 這類程序化寫實紋理系列 | 加了雜訊/凹凸/磨損會直接摧毀色塊——3 渲 2 的表面必須是乾淨色塊（漸層來自光照 ramp，不是紋理雜訊） |

## ★ 3 渲 2 著色管線（本卡核心，Blender 5.1.2 headless 實測）

### 進階路線（預設）：漸層 cel
`mat_lib.make_cel_advanced()` 內建節點鏈：
`Diffuse → ShaderToRGB → RGBToBW → ColorRamp(LINEAR, 4 stops) → AO×MapRange → MULTIPLY → LayerWeight.Facing^3×0.45 → ADD(rim) → Emission`

- **硬邊界 + 帶內漸層怎麼同時成立**：ColorRamp 用 LINEAR 插值但放 4 個 stop——
  `shadow@0.0 / shadow@0.28 / mid@0.31 / high@1.0`。0.28→0.31 的窄間隔就是硬陰影邊界；
  0.31→1.0 的長間隔就是受光帶內的柔和漸層（mid→high）。stops 參數可調邊界位置。
- **AO 接觸陰影**：`ShaderNodeAmbientOcclusion`（distance 0.6）經 MapRange(0.55→1.0) 乘回
  色塊——物件落地處/縫隙處自然變暗，「貼地感」的來源。基礎路線沒有這個，物件會像浮貼紙。
- **冷色邊緣光**：`LayerWeight.Facing` ^ 3 × 0.45 加一層冷藍——面向鏡頭的輪廓內側一條冷光，
  把焦點物件從灰底環境裡「拔」出來。環境件 `rim_strength=0.0` 關掉。
- 實測（`.capybala/test-scripts/zzz_look_proto.py` A/B 同框 + `zzz_lib_e2e.py` lib 本體端
  到端）：圓柱曲面受光帶漸層、落地接觸陰影、FG 粗線/BG 細線分層、合成後製不污染平塗——
  全部可見。

### 基礎路線（遠景/快渲降級用）：純平塗三階
`mat_lib.make_cel()`：`Diffuse → ShaderToRGB → CONSTANT ColorRamp(3 stops) → Emission`。
實測三階輸出 sRGB 與色票 hex 完全相符、top-5 直方圖格佔 96.8%。輸出走 Emission，調光不
改變色票。適合遠景建築群/極簡構圖/需要極快迭代時——**不是另一個美術方向，是品質降級**。

### 兩條路線共用的必要設定
1. `scene.view_settings.view_transform = 'Standard'`（`T.set_view_transform('standard')`）。
   **AgX 會把色票打歪**：實測主色階 #E89490(232,148,144) → AgX 下 #C29490(194,148,144)，
   紅通道掉 38；端到端複驗下牆面主色階佔比 9.1% → AgX 下 0.0%（整階消失）。
   **注意**：`set_view_transform()` 只記 override、實際套用在 `setup_render()` 內——
   不走 `T.main()` 的腳本要自己補 `scene.view_settings.view_transform = "Standard"`。
2. `ShaderToRGB` **只在 EEVEE 有意義**。丟給 Cycles 不報錯但最亮階整片消失、畫面塌到 mid 階
   （實測 100% 落在 mid band）——「安靜地做錯」，比報錯更危險。進階與基礎路線都鎖 EEVEE。
3. **SUN `angle = 0`**：切斷半影（penumbra），陰影邊界才夠硬。光源尺寸被調大時必須歸零。
4. **法線清理（進階路線必做）**：bevel 後開 Harden Normals（需先開 Auto Smooth 才生效）、
   複雜/布林網格在 modifier stack 末尾加 Weighted Normal——否則平滑著色的法線平均化會讓
   漸層 cel 的明暗界線在平面上滲出漸層（實測開與不開差 5.1% 畫素、最大 21%）。
   `shape_lib.add_weighted_normal()` 已存在，bevel 後呼叫即可。

## ★ 細節特徵

1. **外輪廓線——背面法優先，是《罪惡裝備》系列自 Xrd 起畫線的主力**（官方 CEDEC2024
   講題原名「背面法」，用了 20 年以上仍是第一線做法）：
   - **背面法** `T.setup_inverse_hull(objects, px=2.4)`：複製一份真幾何、沿法線外推、只畫
     背面——外推出去的部分在剪影處露出來就是線。線寬由 `T.outline_push_distance()` 依相機
     距離與焦距自動算（距離拉遠線跟著變粗、zoom in 線跟著變細，畫面寬度才穩定；固定線寬的
     後果是近景粗黑邊、遠景鋸齒）。逐部位線寬／要不要線用頂點色 `Col` 的 alpha 控制：
     0.5 標準、1.0 兩倍、0.25 一半、0 完全不要線（實測四檔逐位命中）。`z_offset` 把外殼往
     相機反方向推 → 只剩最外圈剪影線（實測線畫素 0.326%→0.106%）。**Blender 不支援
     multipass shader**（官方環境對照表明載 Blender ✕），所以這條路一定要真幾何，不能用
     shader 假裝——失敗過的 7 種 shader/modifier 路線缺的正是「真外殼」＋「只畫背面」。
   - **Freestyle**（快渲/遠景降級）：`setup_selective_outline()`（FG 粗深線／BG 細淡線）或
     `setup_freestyle()`（全場單一線寬，實測 2.7s / 2.9s 出圖）。不必複製幾何、設定便宜；
     代價是無法逐部位控制線寬、線寬不隨距離/FOV 補償。
   - **兩者不要同時用**（會疊線）。內描邊（皺褶／分件／瓦楞這類圖案內部的線，背面法畫不出）
     用 `T.make_internal_line()`——幾何版「本村線」，與貼圖解析度無關、放大不糊。
2. **選擇性描邊走 `select_by_collection`**（實測 FG 出粗深線、BG 無線/細線，分層正確）。
   layout 階段就要把物件分進 FG/BG collection——**事後補分要重跑整個 layout**。
3. **5.1 API 陷阱（兩處，函式已內建處理）**：
   - `lineset.linestyle` 預設 `None`，直接寫 `.color` 會 AttributeError——必須先
     `bpy.data.linestyles.new()`。
   - **scene compositor 的 node group 內 GroupInput 不會收到渲染畫面**——group 必須自己放
     `CompositorNodeRLayers` 取像素。只接 GroupInput 的 group 實測輸出全黑/全白垃圾。
     `setup_anime_post()` 已內建正確接法。
4. **線色用線性值**，不要填「看起來夠黑的 0-1 灰」；要更黑的線加粗（thickness 3+），不要靠
   把色值調更黑硬救（抗鋸齒混色會讓核心畫素比理論值亮）。
5. **構件清單不在本卡重複**：招牌類型、電柱電線、自動販賣機、導盲磚、路地縫隙等構件定義見
   `anatomy/spaces/japanese_street.md`；本卡只管這些構件「上哪一階顏色、線畫多粗、天空怎麼
   配」。
6. **落地審計**：`T.audit_band_count()`——進階路線的判準與基礎路線不同：漸層 cel 的受光帶是
   連續漸層，量化後色格數天然比純平塗多（實測純平塗單材質 3 階；漸層 cel 單材質 5-7 階）。
   進階路線不要用「≤4 階」當門檻——改驗：① 陰影邊界硬度（邊界兩側色差的梯度寬度 ≤2px）、
   ② `top[].hex` 與這次實際採用的色比對（抓 AgX 誤用造成的色偏，不是驗有沒有照色票走）。
   色彩配額與飽和度上限不作審計——那是審美判斷，交給人眼與參考圖。`T.main()` 在 Standard
   下自動跑 soft 版寫進 `SCENE_STATE.band_audit`，進階路線僅供參考。

## ★ 落地 checklist
- [ ] **先判模式**：單一主體（在拍「這個東西」）→ 展示卡模式 `T.setup_cel_studio()`；整個
      街區/場景（在看「這個地方」）→ 敘事場景模式（天空配方＋構件密度那條）
- [ ] **展示卡模式專屬**：`sun_offset_deg` 沒有被設成 0；`sun_energy` 用 2.0 起跑；
      `ground_mat` 有傳（沒傳會沿用噪聲地面，跟色塊語言衝突）
- [ ] **品質等級選定**：預設進階路線（漸層 cel）；只有遠景/快渲才降級基礎平塗
- [ ] **沒有畫汽車/機車/公車/行人/人物立牌**（硬規則）
- [ ] 環境走灰調、焦點物件走高飽和點綴（本卡預設方向）；有參考圖/指定色時以使用者為準
- [ ] 全場材質來自 `make_cel_advanced()`（或基礎路線 `make_cel()`），沒有混入程序化寫實
      紋理系列
- [ ] 陰影色是設計過的獨立色塊（明度壓低＋飽和度提升＋色相往冷側位移），不是同一色乘係數
      ——風格卡有色票三階就直傳，只有 base 色時走 `M.cel_shadow_color()`
- [ ] `view_transform = 'Standard'` 真的套上（讀 `scene.view_settings.view_transform` 確認，
      不只呼叫 `set_view_transform()`）
- [ ] 引擎 = EEVEE；SUN `angle = 0`
- [ ] bevel 物件有 Harden Normals（先開 Auto Smooth）或 stack 末尾 Weighted Normal
- [ ] 外輪廓線已選定且只選一個：優先 `T.setup_inverse_hull()`（背面法）；快渲或遠景才用
      `setup_selective_outline()`／`setup_freestyle()`
- [ ] 用背面法時：`px` 已對齊實際畫幅、`T.audit_outline_shell()` 回報的實際外推距離與期望值
      相符（不符就是相機矩陣沒更新或被 modifier 改了形狀）
- [ ] 用 Freestyle 時：物件已分進 FG/BG collection（事後補分要重跑整個 layout）
- [ ] 呼叫 `setup_anime_post()`（高門檻局部泛光），沒有用全場低門檻 bloom
- [ ] 焦點物件有 rim（`rim_strength≈0.45`）、環境件 rim 關掉
- [ ] 天空用 `add_stylized_sky()`，佔畫面 30-45%，鏡頭不是俯視
- [ ] 牆面/捲門/電箱有圖形設計元素（貼紙/色帶/粗體字/塗鴉），不是純色牆
- [ ] 構件清單/密度有查 `anatomy/spaces/japanese_street.md` 並選定場域類型

## ☆ 燈光/渲染建議
- **本卡有兩種模式，打光規則不同**：敘事場景模式（一整條街）＝下面這套街景邏輯；展示卡
  模式（單一主體）＝`T.setup_cel_studio()`。**不要拿三點式 AREA 去補任一種**——三盞燈各自
  產生一條明暗界線，cel 的硬邊界會糊成好幾條。
- **打光只決定「明暗界線落在哪裡」，不決定色彩**：一盞 SUN（決定投影方向與明暗界線位置）+
  低能量世界環境光（避免暗階掉到純黑）。**主體的明暗由主體自己的著色管線決定，不跟場景
  多光源加算綁**（《罪惡裝備》每個角色都有專屬虛擬光，理由是避免明暗隨場景移動劇烈跳動、
  干擾辨識——他們明確拒絕用多光源加算，說會過曝、降低辨識度）。所以「加一盞燈把暗面打亮」
  在這條路線無效，只會改變色階落點，不要為了補暗面加燈。
- **太陽角度要斜**（30-45°）：明暗界線落在建築立面上會有清楚的大色塊分界；頂光會讓對比
  消失、色階糊在一起。
- **空氣感/遠近**：靠「遠景物件飽和度遞減 + 明度遞增」（aerial perspective）——遠景建築的
  色票往天空地平色混 15-30%，比體積霧便宜且不會污染色塊。**不要**靠 DoF 淺景深（模糊會把
  色塊邊界弄糊，直接殺掉 3 渲 2 的識別度）。
- **局部泛光可以、全場泛光不行**：`setup_anime_post()` 的 threshold=0.85 只讓自發光招牌/
  燈管暈開；全場低門檻泛光會把硬邊界糊掉，不要用。

## ☆ 代表作（美術語言錨點，非重製對象）
《絕區零》（米哈遊，2024——本卡環境美術的主要參照：灰調都會 + 高飽和焦點 + 圖形設計感
街景）、《罪惡裝備》Xrd/Strive（Arc System Works——本卡外輪廓線技法的主要參照：背面法、
逐部位線寬控制、主體專屬虛擬光不跟場景光綁）、《原神》（米哈遊，2020——ramp 漸層 cel 與
選擇性描邊的技術源頭，`make_cel_advanced()` 的節點鏈設計參照）。

## ☆ Prompt 模板（選填；只在需要 2D 概念示意圖時用）
"advanced cel-shaded Japanese street in bright daylight, hard-edged shadow boundaries with
soft gradient confined inside the lit band only, AO contact shadows grounding every object,
cool blue facing rim light on focal props, backface-method outlines (thick dark on
foreground, thin pale on background buildings), desaturated grey-warm environment with
saturated accent props and graphic-design stickers/typography on shutters and walls,
high-saturation blue sky #1E6FD9 fading to pale #C9E6F8 with crisp-edged cumulus, localized
bloom only on emissive signs, no cars no people, Zenless Zone Zero / Guilty Gear Xrd key-art
look, no full-frame bloom"
