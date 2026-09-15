# 中世紀現代 Mid-Century Modern（室內設計）
觸發詞：中世紀現代、MCM、Mid-century、Eames、1950s 傢俱、瘋狂麥迪遜風

## ★ 一句話定位
胡桃木+錐形細腿+芥末黃/橄欖綠色塊，戰後樂觀主義的有機幾何。

## ★ 理念
- 「設計為大眾」：Eames 的量產哲學——膠合板/塑膠殼工業化但有機 [src: Eames 夫婦公開語境]
- 室內外連續：大玻璃+開闊平面+原子時代圖案
- 功能雕塑化：傢俱是可用雕塑（Egg Chair/Sputnik 燈）

## ★ 形式語言
- **比例系統（§15.0）：黃金比例×費波那契為主**——曲木殼體的大圓角、雕塑感有機造型呼應「有機、流動」語感；沒有既有的模矩/對稱語言，走大小曲線對比（見 §15.3）而非直線網格。
- 傢俱腿：錐形外八（splayed），胡桃木，腿高 200-250mm
- 殼體：曲木膠合板（plywood curve）+ 玻璃纖維殼，圓角大 R=30-80mm
- 圖案：原子星爆/幾何放射/Boomerang 形（地毯/壁紙）
- 層次：低櫃（sideboard 高 600-700mm）+ 高單椅 + 吊燈懸垂

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 胡桃木 | #6B4A32 | (0.1470,0.0685,0.0319) | 35% |
| 奶油白墻 | #EFE9DC | (0.8632,0.8148,0.7157) | 30% |
| 芥末黃 | #D9A634 | (0.6939,0.3813,0.0343) | 10% |
| 橄欖綠 | #7A8A4A | (0.1946,0.2541,0.0685) | 10% |
| 焦橙 | #C85A2A | (0.5776,0.1022,0.0232) | 8% |
| 黑鐵細件 | #1E1E1E | (0.0130,0.0130,0.0130) | 7% |
| 忌避色（選填，非禁令） | 灰藍北歐色、灰泥侘寂色、高光亮面塑膠 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 胡桃木傢俱 | make_wood | base=hex_to_linear('#6B4A32'), grain_scale=5, roughness=0.4（打磨上蠟） |
| 墻面 | make_plastic | base=hex_to_linear('#EFE9DC'), roughness=0.9 |
| 沙發織物 | make_fabric | base=hex_to_linear('#7A8A4A') 或芥末黃 |
| 塑膠殼椅（Eames） | make_plastic | base=(0.92,0.9,0.85) 或焦橙, roughness=0.35 |
| 黑鐵桿腿 | make_metal | color=hex_to_linear('#1E1E1E'), roughness=0.45 |
| 黃銅點綴 | make_metal | color=(0.72,0.56,0.28), roughness=0.25 |

## ★ 細節特徵
- 錐形腿：cylinder 上粗下細（vertices 16，scale 頂 1.0 底 0.6）外八 8-12°
- 曲木殼：subdivision surface 或 lathe 旋轉體
- Sputnik 吊燈：球心+12 放射細桿+球形燈泡（emissive 暖白）
- 地毯：幾何放射圖案（雙色 fabric，或純色+邊飾）
- 邊櫃：細木棒拉手（圓棒 ⌀16mm）+ 錐腿

## ★ 落地 checklist
- [ ] 胡桃木+奶油白 ≥60%，色塊色（黃/綠/橙）各 ≤10% 且出現在軟裝
- [ ] 所有座具腿錐形外八
- [ ] 至少 1 件「雕塑性」單品（蛋椅/Sputnik/曲木椅）
- [ ] 黃銅點綴 ≤2 處（拉手/燈桿）
- [ ] 圖案元素（星爆/boomerang）出現 1 處（地毯/壁紙/掛畫）

## ☆ 燈光/渲染
outdoor_golden（大窗灑入）或 studio 暖化；Sputnik 場景用 night+emissive 多點光源。目標 mean 115-155，暖色溫（Key (1,0.94,0.85)）。

## ☆ 代表作
Eames Lounge Chair 670（1956）/ Saarinen Tulip 桌（1957）/ Jacobsen Egg Chair（1958）/ Nelson Marshmallow 沙發（1956）/ 《廣告狂人》Draper 公寓場景

## ☆ Prompt 模板
"Mid-century modern interior, walnut sideboard with tapered splayed legs and brass pulls, olive green fabric sofa, mustard accent chair, Sputnik chandelier with warm bulbs, cream walls, atomic starburst pattern rug, large windows with golden afternoon light"
