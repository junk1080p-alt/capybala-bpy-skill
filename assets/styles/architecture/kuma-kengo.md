# 隈研吾 Kengo Kuma（建築）
觸發詞：隈研吾、負建築、木格柵、粒子化、日式現代建築、GC 齒科
適用年代：1995-now（水/玻璃屋 1995 / GC 齒科 2010 / 角川武藏野博物館 2020）

## ★ 一句話定位
建築「消失」於環境：細木條/石板粒子化表皮，半透明、輕、反紀念性。

## ★ 理念
- 「負建築」：建築不主張自己，而是讓環境勝出 [src: 隈研吾《負建築》2004]
- 「粒子」：把體量分解成細小單元（木條 30-60mm），消解建築的重量感
- 材料地域性：當地木/石/竹/紙，現代工法重譯傳統

## ★ 形式語言
- **比例系統（§15.0）：黃金比例×費波那契為主**——格柵間隙漸變（密→疏）、木條粒子節奏本質是費波那契式的漸變感，不是等距柵欄。
- 體量：低平鋪開，高度 ≤ 樹冠；水平延展優先於垂直
- 表皮：細木條格柵，條寬 30-60mm，間隙漸變（密→疏，parametric louvers）
- 屋頂：薄平屋頂或傳統坡屋頂的现代轉譯（深出挑 ≥1.5m）
- 透明性：格柵後是玻璃，室內外視覺連續
- 結構：細柱陣（鋼柱包木），柱距 = 格柵模數

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 杉木淺色 | #C8A578 | (0.5776,0.3763,0.1878) | 40% |
| 燒杉炭色（變體） | #3A3632 | (0.0423,0.0369,0.0319) | 30% |
| 玻璃半透 | — | make_glass tint=(0.8,0.82,0.8) | 15% |
| 石材基座（灰） | #8A8782 | (0.2541,0.2423,0.2232) | 10% |
| 室內紙白 | #EDE8DC | (0.8469,0.8069,0.7157) | 5% |
| 忌避色（選填，非禁令） | 塗裝彩色、金屬幕墻、清水混凝土大面（那是安藤的地盤） | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 木格柵條 | make_wood | base=hex_to_linear('#C8A578'), grain_scale=8, roughness=0.62（鋸切面非拋光） |
| 燒杉板 | make_wood | base=hex_to_linear('#3A3632'), roughness=0.78 |
| 玻璃 | make_glass | tint=(0.8,0.82,0.8) |
| 石基座 | make_stone | base=hex_to_linear('#8A8782'), roughness=0.6 |
| 和紙內裝 | make_fabric | base=hex_to_linear('#EDE8DC'), roughness=0.95 |

## ★ 細節特徵（detail_lib）
- 格柵：ridge_lines 變體——細木條陣列，母版 1 條 + instance 等距放置（§14 復用）；間隙漸變用位置函數
- 節點：木條交叉處露鋼銷/螺栓（小圓柱 chrome）——工法誠實
- 出挑檐下：格柵延伸到屋面底（連續粒子感）
- 地面：碎石/苔蘚（noise displacement）環繞，建築輕觸地

## ★ 落地 checklist
- [ ] 木條粒表皮至少一個主立面，條寬 ≤60mm
- [ ] 格柵間隙有漸變節奏（非全等距）
- [ ] 建築高度 ≤ 環境樹高（水平優先）
- [ ] 出挑 ≥1m，檐下格柵連續
- [ ] 零彩色塗裝

## ☆ 燈光/渲染
outdoor_golden；格柵的**條狀陰影**是視覺主角——側光角度低（仰角 20-30°）拉長條影；sky 0.3；室內透出暖光（night 場景時 practical light 從格柵縫漏出=招牌畫面）。

## ☆ 代表作
水/玻璃屋 1995 / GC 齒科 2010（白色玻璃纖維粒子）/ 檮原木橋博物館 2010 / 角川武藏野博物館 2020（石粒子 55 層）/ 新國立競技場 2019（木格柵+鋼）

## ☆ Prompt 模板
"Kengo Kuma style architecture, low horizontal wooden pavilion with fine timber louver screen (30-60mm slats with gradually varying gaps), glass behind louvers, deep overhanging thin roof, stone base, surrounded by gravel and moss, warm low-angle sunlight casting striped shadows through the lattice"
