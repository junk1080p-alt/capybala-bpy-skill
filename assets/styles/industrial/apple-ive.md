# Apple / Jony Ive 蘋果味（工業設計/產品）
觸發詞：蘋果味、Apple 風、Jony Ive、unibody、iPhone/Mac 風
適用年代：1997-now（分兩段：半透明糖果期 1997-2001 / 金屬玻璃極簡期 2001-now）

## ★ 一句話定位
陽極氧化鋁+玻璃的單色極簡，接縫近乎消失，每個圓角都是連續曲率。

## ★ 理念
- 「Simplicity is not the absence of clutter, it's the essence of order」——Jony Ive [src: Leander Kahney《Jony Ive》傳記]
- 材料誠實：鋁就是鋁、玻璃就是玻璃，不用塑膠仿金屬
- Unibody：整塊鋁削出，結構即外殼，無裝配縫感
- 對稱與秩序：孔陣列等距、圖標對齊網格、開口必帶倒角

## ★ 形式語言
- **比例系統（§15.0）：對稱與均衡為主**——「嚴格軸對稱（正面）」是本卡核心語言，不是黃金比例卡；分模線/天線帶藏於 0.382 位置、開孔等距陣列是疊加在對稱系統上的局部細節手法，不代表整體比例走黃金比例。
- 體量：薄。厚度永遠是長寬的 0.03-0.08 倍（iPhone 15：7.8mm/71.6mm ≈ 0.109，含鏡頭凸起）
- 圓角：**連續圓角（squircle）**，外廓 R = 0.15-0.2×短邊；bpy 落地：bevel modifier + smooth shading，或 superellipse 曲線輪廓
- 線條：零裝飾線。唯一允許的線 = 分模線/天線帶（藏於 0.382 位置）
- 對稱性：嚴格軸對稱（正面），側面按鈕以音量組為中心微偏
- 開孔語言：圓孔必等距陣列（grip_strip 變體，間距 = 孔徑×2.5）

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 太空灰鋁 | #4A4A4C | (0.0685,0.0685,0.0723) | 主 |
| 銀鋁 | #E3E4E5 | (0.7681,0.7758,0.7835) | 主 |
| 午夜黑 | #1D1D1F | (0.0123,0.0123,0.0137) | 主 |
| 玻璃黑（正面全螢幕） | #0A0A0A | (0.0030,0.0030,0.0030) | 正面 |
| 鈦金屬（2023+） | #8A8681 | (0.2541,0.2384,0.2195) | 主 |
| 點綴：僅允許系統級彩色（螢幕內容） | | | 實體殼體禁用彩色 |
| 忌避色（選填，非禁令） | 橙/紅/黃實體殼、拉絲紋（Apple 用噴砂不用拉絲） | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| unibody 殼 | make_anodized | color=hex_to_linear('#4A4A4C'), roughness=0.35（噴砂感，**不要拉絲**） |
| 正面玻璃 | make_glass | tint=(0.02,0.02,0.02), ior=1.52, roughness=0.01 |
| 鏡頭環/飾圈 | make_metal | color=hex_to_linear('#8A8681'), roughness=0.15（拋光倒角） |
| 按鈕 | make_anodized | 同殼色，roughness=0.3 |
| 橡膠/矽膠殼（配件） | make_rubber | roughness=0.8 |
| 螢幕發光 | make_emissive | 依內容，strength=3-6 |

## ★ 細節特徵（detail_lib）
- 按鍵：極少（3-5 個），每個必帶 chamfer 微倒角亮邊
- 開孔：speaker 孔陣列 = grip_strip(rows=1, cols=6, dot_r 按實際)，等距
- 螺絲：底面兩顆五角/十字，僅此兩處
- 接縫：玻璃-鋁交接縫 ≤0.1mm，用極細 seam（深色橡膠色）
- LOGO：鏡面蘋果/品牌標，凸起 0.1mm（低调，extrude 小）
- 禁止：外露螺絲群、滾花轉盤、彩色按鍵

## ★ 落地 checklist
- [ ] 外廓圓角為連續曲率（非圓弧近似——squircle 曲線或 bevel segments ≥4）
- [ ] 全機只有 1 種主材質色（單色原則）+ 玻璃黑
- [ ] 接縫數量 ≤3 且全部 ≤0.2mm 視覺寬
- [ ] 噴砂 roughness 0.3-0.4，不出現拉絲紋
- [ ] 開孔全部等距陣列

## ☆ 燈光/渲染
studio preset + 大面積柔光（area light size ×2）：鋁殼要出「一條細長高光帶」而非點狀高光。Key -20%，加頂部柔光箱 Fill +20%。背景純白或純灰 #E8E8E8 無限延伸（cyclorama）。

## ☆ 代表作
- iMac G3（1998）：半透明糖果色（特殊期，非極簡期）
- PowerBook G4 鋁（2003）：unibody 前身
- iPhone 5（2012）：鑽石切割亮邊 + 陽極鋁的巅峰
- MacBook Pro unibody（2008-）：整塊鋁削
- Apple Watch Ultra（2022）：鈦金屬 + 橙色行動按鈕（唯一點綴色例外）

## ☆ Prompt 模板
"A minimalist Apple-style product, single-piece anodized aluminum unibody in space grey, seamless continuous-curvature rounded corners, black glass front, tiny chamfered buttons, precise evenly-spaced speaker holes, no visible screws except bottom, studio product photo on white cyclorama background, soft elongated highlights"
