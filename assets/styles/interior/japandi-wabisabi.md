# 侘寂 Wabi-sabi / Japandi（室內設計）
觸發詞：侘寂、wabi-sabi、日式極簡、Japandi、枯山水、禪意

## ★ 一句話定位
不完美的天然材料+極低傢俱+留白，接受老化與粗糙的安靜美學。

## ★ 理念
- 侘寂三原則：無常（不完美）、樸素（不裝飾）、自然（不造作）[src: 侘寂美學通說]
- Japandi = 日式+北歐混血：北歐機能 + 日式材料觀
- 「減到只剩呼吸」：物件數量是北歐風的一半

## ★ 形式語言
- **比例系統（§15.0）：留白與簡約為主，奇數佈置呼應費波那契節奏**——留白/減量是核心語言；1/3/5 件的奇數擺位可視為費波那契數列的體現，但不強制套 `golden_series` 算精確分段，「不完美」本身比公式精確更重要。
- 傢俱：極低（座高 300-350mm，比北歐更低）、無腿或粗短腿、邊緣手工感（非精確圓角）
- 線條：橫向延展，零垂直裝飾
- 不對稱：奇數佈置（1/3/5 件），故意「不完美」擺位
- 表面：手工痕跡可見（抹刀紋灰泥、拉坯不均陶器、木節保留）

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 灰泥墻（抹刀紋） | #C9C2B6 | (0.5841,0.5395,0.4678) | 40% |
| 深色老木（胡桃/煙燻） | #5A4A3A | (0.1022,0.0685,0.0423) | 25% |
| 米白織物（亞麻） | #E5DFD2 | (0.7835,0.7379,0.6445) | 15% |
| 陶土色 | #A8785A | (0.3916,0.1878,0.1022) | 8% |
| 炭黑（鐵器/枝幹） | #242220 | (0.0176,0.0160,0.0144) | 7% |
| 苔綠（點綴） | #6B7A5A | (0.1470,0.1946,0.1022) | 5% |
| 忌避色（選填，非禁令） | 亮面任何材質、彩色塑膠、金屬光澤、純白高光 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 灰泥墻 | make_concrete | base=hex_to_linear('#C9C2B6'), pit_scale=0.0012（抹刀紋 bump 加大）, roughness=0.95 |
| 老木傢俱 | make_wood | base=hex_to_linear('#5A4A3A'), grain_scale=4, distortion=6（紋理更野）, roughness=0.7 |
| 亞麻織物 | make_fabric | base=hex_to_linear('#E5DFD2'), bump_scale=0.0018（粗織） |
| 陶器 | make_stone | base=hex_to_linear('#A8785A'), roughness=0.65 |
| 鐵器 | make_metal | color=hex_to_linear('#242220'), roughness=0.75（生鐵非鋼） |
| 和紙燈罩 | make_fabric + emissive | base=(0.9,0.87,0.8) + 內置暖光 |

## ★ 細節特徵
- 陶器：拉坯不均（圓柱 scale 微抖 0.97-1.03）+ 口緣波狀
- 枝幹：枯枝單支入瓶（curve 掃掠，零葉或少葉）
- 石：天然卵石（icosphere subdiv + noise displacement）
- 坐墊：亞麻皺折（noise bump 大尺度）
- 零：把手、裝飾線、亮面五金——有就錯

## ★ 落地 checklist
- [ ] 全部材質 roughness ≥0.6（唯一例外：陶器上釉局部）
- [ ] 傢俱最高點 ≤800mm（極低生活線）
- [ ] 物件總數 ≤ 北歐風的一半，奇數佈置
- [ ] 至少一處「不完美」：歪陶/木節/抹刀紋特寫
- [ ] 光源隱蔽（和紙燈/窗光），無裸露燈泡

## ☆ 燈光/渲染
單一側窗光（Sun 低強度 1.2-1.8 + sky 0.2）：陰影要柔長；或 night + 和紙燈 interior practical 為主光。目標 mean 95-135（壓暗的安靜感），dark_pct 可放到 25%。

## ☆ 代表作
Leonard Koren《Wabi-Sabi》1994 / 京都俵屋旅館語境 / Axel Vervoordt 侘寂室內 / Japandi 風 2017- 全球流行

## ☆ Prompt 模板
"Wabi-sabi interior, textured lime plaster walls with trowel marks, low dark walnut wooden furniture with hand-finished edges, linen cushions with natural wrinkles, irregular hand-thrown ceramic vase with single dry branch, hidden warm light through washi paper lamp, asymmetric odd-numbered arrangement, quiet shadowed atmosphere"
