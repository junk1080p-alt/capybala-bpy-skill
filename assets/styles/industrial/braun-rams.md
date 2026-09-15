# Braun / Dieter Rams 拉姆斯味（工業設計/產品）
觸發詞：Braun、博朗、迪特拉姆斯、Rams 味、功能主義、十誡
適用年代：1956-1995（ET66 計算機 1987、T3 剃鬚刀 1966、SK 音響系列）

## ★ 一句話定位
幾何格律化的功能主義：每個元素都有理由，色票只有灰白黑+單一功能色。

## ★ 理念（Rams 十誡濃縮）[src: Dieter Rams "Ten Principles for Good Design", 1970s]
1. 創新 / 2. 有用 / 3. 美學 / 4. 易理解 / 5. 不唐突 / 6. 誠實 / 7. 耐久 / 8. 徹頭徹尾 / 9. 環保 / 10. 儘可能少的設計
- 「Weniger, aber besser」Less but better——減到不能再減，但每個留下的元素執行到 120%
- 產品像「工具」：中性、安靜、給使用者自由

## ★ 形式語言
- **比例系統（§15.0）：簡單整數比/模矩制為主，面板分區線混用黃金比例**——按鈕/孔/刻度網格照模矩整數倍生成（`config.py` 定義模矩常數）；面板顯示區/操作區的分區線可以照原文的 0.618H，兩者不衝突（大分區用黃金比例，元件網格用模矩）。
- **格律系統（grid）是靈魂**：按鈕/孔/刻度全部對齊隱形網格，網格模數 = 最小元素尺寸
- 體量：長方體，比例走整數比或 1:1.618；邊緣小圓角 R=1-1.5mm
- 圓形元素：完美的正圓，同心圓套疊（轉盤中嵌按鈕）
- 線條：水平分區線把面板分成「顯示區/操作區」，分區位置 0.618H
- 對稱：功能對稱（不必幾何對稱，但視覺重量平衡）

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 暖灰殼 | #D8D4CF | (0.6867,0.6584,0.6240) | 50% |
| 炭灰面板 | #3C3C3C | (0.0452,0.0452,0.0452) | 25% |
| 純黑（按鍵/格柵） | #141414 | (0.0070,0.0070,0.0070) | 15% |
| 功能綠（開/運行） | #5A8F5A | (0.1022,0.2747,0.1022) | ≤5% |
| 功能紅（停止/錄音） | #C03A2B | (0.5271,0.0423,0.0242) | ≤5% |
| 銀（金屬件） | #B8B8B8 | (0.4793,0.4793,0.4793) | ≤10% |
| 忌避色（選填，非禁令） | 漸層、金屬光澤殼體、彩色塑膠 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 殼體 | make_plastic | base=hex_to_linear('#D8D4CF'), roughness=0.55（霧面細砂，無 clearcoat） |
| 面板 | make_plastic | base=hex_to_linear('#3C3C3C'), roughness=0.45 |
| 按鍵 | make_plastic | base=hex_to_linear('#141414'), roughness=0.5 |
| 功能色鍵 | make_paint | green/red, roughness=0.4, clearcoat=False |
| 金屬網/飾件 | make_metal | color=hex_to_linear('#B8B8B8'), roughness=0.3 |
| 顯示窗 | make_glass | tint=(0.85,0.87,0.82), roughness=0.1 |

## ★ 細節特徵（detail_lib）
- 揚聲器格柵：圓孔陣列 grip_strip(rows=4, cols=10, dot_r=0.0008)（0.8mm，函式參數單位是公尺，別直接寫 mm）——Braun 的簽名視覺
- 轉盤：同心圓，外環 knurl_ring(ridges=34) 細齒，內盤光滑帶單一指標線
- 滑桿開關：矩形槽 + 圓角滑塊，行程可見
- 刻度印刷：極細白字（make_text extrude 0.05mm 近似印刷），對齊網格
- 螺絲：全部隱藏（底面除外）
- 接縫：均勻 0.3mm，不藏但不強調

## ★ 落地 checklist
- [ ] 全機色數 ≤4（灰白黑+1 功能色）
- [ ] 所有圓孔/按鈕對齊同一網格模數（SCENE_STATE 報格律座標）
- [ ] 功能色只出現在「可操作件」（按鈕/指示燈），絕不用於裝飾
- [ ] 無漸層、無高光塑膠感（roughness ≥0.45）
- [ ] 至少一處同心圓套疊結構

## ☆ 燈光/渲染
studio preset，中性白背景 #F0EFED；光比低（Fill/Key = 0.4），要「安靜的博物館陳列感」，陰影柔短。

## ☆ 代表作
- SK 4 唱機「白雪公主之棺」（1956）：淺木+白漆+透明壓克力蓋
- T3 剃鬚刀（1966）：完美圓形網罩+單色
- ET66 計算機（1987）：格律按鍵+功能色圓點（iPhone 計算機 App 原型）
- 606 萬用置物系統（1960）：模數化格律的極致

## ☆ Prompt 模板
"A Dieter Rams Braun-style functional device, warm grey matte plastic housing with charcoal panel, strict geometric grid alignment of round black buttons and speaker holes, single green function indicator, concentric dial with fine knurled ring, no gradients no gloss, quiet museum-like product photography on off-white background"
