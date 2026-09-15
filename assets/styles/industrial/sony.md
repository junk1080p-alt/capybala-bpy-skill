# Sony 索尼味（工業設計/產品）
觸發詞：索尼味、Sony、Walkman 風、索尼數碼相機、索尼黑卡
（不用「黑科技」單獨當觸發詞——中文口語泛用說法，跟 Sony 無必然關聯，會誤觸發本卡）
適用年代：三段——A. 隨身聽時代 1979-1995；B. 特麗瓚/AV 時代 1985-2000；C. 數碼黑卡時代 2010-now

## ★ 一句話定位
精密黑色機身 + 銀色飾條點綴，按鈕密集但秩序井然的「專業器械感」。

## ★ 理念
- 「Doing What Sony Does」：技術優先，設計服務於功能密度，不藏機械結構而是把它排整齊 [src: Sony 設計公開訪談語境]
- 隨身聽時代：把「可攜」做到極小極輕，鋁合金外殼直接外露材質本色
- 黑卡相機時代（RX100/α 系列）：一見全黑的機身上藏著極密的操作件——轉盤、撥輪、自定義鍵，每個件都有明確倒角與間隙
- 標誌细节：橙色/黃色點綴極少但出現即關鍵功能提示（錄像鈕、對焦點）

## ★ 形式語言
- **比例系統（§15.0）：黃金比例×費波那契為主**——長寬比、厚度分層、分區線位置、按鈕間距全部走本卡自己已經列的黃金比例/費波那契數值，是全庫最典型的黃金比例系統卡片之一。
- 體量：長方體為主，長寬比 1:1.618（隨身聽）或 1:0.618（豎握相機）
- 厚度分層：機身厚度 = 主體 0.618 + 鏡頭/機構突出 0.382
- 圓角：小圓角 R=1-2mm（不是 Apple 的大連續圓角）——邊緣俐落帶倒角高光（chamfer 0.3-0.5mm 亮銀邊）
- 線條：貫穿機身的銀色分模線或飾條，位置在 0.618H 或頂蓋交界
- 按鈕語言：矩形/圓形按鈕密集但網格對齊，間距走費波那契（1.5/2.5/4mm）

## ★ 色票
### A. 隨身聽時代（1979-1995）
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 鋁銀本色 | #C8C9CB | (0.5776,0.5841,0.5972) | 55% |
| 黑塑膠件 | #1A1A1C | (0.0103,0.0103,0.0116) | 35% |
| 海綿橙（點綴） | #E8722A | (0.8069,0.1683,0.0232) | ≤3% |
| 忌避色（選填，非禁令） | 木紋色/暖白 | | |
### B. AV 黑金時代（1985-2000）
| 香檳金飾條 | #B9A577 | (0.4852,0.3763,0.1845) | 8% |
| 消光黑主體 | #17171A | (0.0086,0.0086,0.0103) | 85% |
| 銀按鈕 | #9FA1A4 | (0.3467,0.3564,0.3712) | 7% |
### C. 數碼黑卡時代（2010-now）
| 主體黑（帶微藍） | #141416 | (0.0070,0.0070,0.0080) | 80% |
| 銀飾圈/飾條 | #D5D6D8 | (0.6654,0.6724,0.6867) | 12% |
| 橙點綴（錄像/AE-L） | #F26B21 | (0.8879,0.1470,0.0152) | ≤2% |
| 蒙皮黑（荔枝紋） | #101012 | (0.0052,0.0052,0.0060) | 餘量 |

## ★ 材質映射表（materials.py 直接用）
| 部位 | factory | 參數 |
|---|---|---|
| 主體殼（時代 C） | make_anodized | color=hex_to_linear('#141416'), roughness=0.42 |
| 銀飾條/鏡圈 | make_brushed_metal | color=hex_to_linear('#D5D6D8'), rough_mid=0.18 |
| 按鈕塑膠 | make_plastic | base=hex_to_linear('#1A1A1C'), roughness=0.35 |
| 蒙皮 | make_leather | base=hex_to_linear('#101012'), grain_scale=1100 |
| 橙色點綴件 | make_paint | base=hex_to_linear('#F26B21'), roughness=0.28, clearcoat=True |
| 螢幕玻璃 | make_glass | ior=1.52, roughness=0.02 |
| 時代 A 鋁殼 | make_brushed_metal | color=hex_to_linear('#C8C9CB'), rough_mid=0.3 |

## ★ 細節特徵（detail_lib）
- 所有轉盤/撥輪：knurl_ring 滾花，齒數 55/89（密集細齒是 Sony 器械感的來源）
- 模式轉盤頂面：dial_grooves 21 條 + 刻度刻字
- 按鍵群：網格排列，每鍵帶 0.2mm chamfer 亮邊（倒角材質給 make_metal 銀）
- 接縫：外露但均勻（0.15mm 縫線感，seam_ring）
- 螺絲：外露十字螺絲在底面/側面（不藏，機械誠實）
- LOGO：Sony 字體鐳射銀（make_text extrude 0.3mm，材質銀漆）
- 鏡頭環：刻字環（焦距/光圈數值）+ 對焦環滾花

## ★ 落地 checklist
- [ ] 時代已選定（A/B/C），config 所有尺寸從該時代代表機型比例出發
- [ ] 黑色占比 ≥70%（時代 C），銀飾條 ≤15%，橙點綴 ≤2% 且只在功能件（比例取自色票欄，屬視覺印象**非配額**，使用者指定時以使用者為準）
- [ ] 至少 3 處滾花件（轉盤×2+對焦環）
- [ ] chamfer 亮邊出現在主體棱線（Sony 的「精工感」來源）
- [ ] 色彩取自卡片參考色或使用者指定色（**不做占比審計**）

## ☆ 燈光/渲染
studio preset；主光稍側（chamfer 亮邊要拉出細高光線）；Key 強度 -10%（黑機身反光少，防死黑靠 Fill +10%）。

## ☆ 代表作
- TPS-L2 Walkman（1979）：藍銀雙色、海綿橙、按鍵密集
- D-50 Discman（1984）：消光黑+銀飾條
- RX100（2012）：口袋黑卡、鏡圈銀環、轉盤滾花
- α7 系列（2013-）：軍艦部+握把蒙皮+橙錄像鈕
- PS5（2020）：白黑雙層曲面包夾（現代變體，曲面語言不同於直線時代）

## ☆ Prompt 模板（概念圖用）
"A compact Sony-style digital camera, matte black anodized body with precision silver chamfered edges, knurled control dials with fine 55-tooth ridges, small orange accent button, dense but grid-aligned controls, Leica-like lens barrel with engraved markings, product photography on dark grey studio background, three-quarter view" (時代 C；A 時代改 brushed aluminum + black plastic + orange foam accents)
