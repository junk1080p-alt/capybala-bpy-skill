# Mies van der Rohe 密斯（建築）
觸發詞：密斯、少即是多、Less is more、玻璃盒子、鋼構現代主義
（不用「包豪斯」單獨當觸發詞——包浩斯涵蓋更廣、色彩語言偏原色幾何塊，跟密斯晚期的黑白玻璃鋼構不同調，誤觸發風險高）
適用年代：1927-1969（Barcelona Pavilion 1929 / Farnsworth House 1951 / Seagram 1958）

## ★ 一句話定位
鋼柱+大片透明玻璃的通用空間，結構外露且排成完美格律，「上帝在細節中」。

## ★ 理念
- 「Less is more」/「God is in the details」[src: Mies 語錄，廣泛記載]
- 通用空間（universal space）：室內無承重墻，功能自由佈置
- 結構誠實（修正版）：鋼柱外露，Seagram 的工字鋼是裝飾性貼面——視覺誠實勝過構造誠實
- 格律：模數化柱網，一切尺寸是模數的整數倍

## ★ 形式語言
- **比例系統（§15.0）：簡單整數比／模矩制為主**——「一切尺寸是模數的整數倍」是密斯的核心語言，不是黃金比例；柱距/玻璃分割/挑檐收邊全部照模矩單位的整數倍生成，不要套 `fib_split`/`golden_series`。
- 體量：水平延展低層（Pavilion：寬高比 ≥3:1）或垂直塔樓（Seagram：1:2.6 高瘦）
- 平面：自由平面，大理石/縞瑪瑙墻片獨立於結構（Pavilion 的簽名）
- 柱：十字形斷面鋼柱（Pavilion）或工字鋼（Seagram），柱距模數化
- 玻璃：從地到頂通高，無窗框分割或極細分割（分割對齊柱網）
- 屋頂：薄板挑檐，邊緣一條精細金屬收邊

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 鋼構黑 | #232323 | (0.0168,0.0168,0.0168) | 12% |
| 玻璃（淡綠反射） | — | make_glass tint=(0.82,0.87,0.85) | 45% |
| 大理石墻片（Pavilion） | #7A8A72 / 縞瑪瑙 #C89A5A | (0.1946,0.2541,0.1683)/(0.5776,0.3231,0.1022) | 20% |
| 石材地面（石灰華） | #D9CDB8 | (0.6939,0.6105,0.4793) | 20% |
| 水盤（Pavilion） | 玻璃黑水面 | roughness=0.02 | 3% |
| 忌避色（選填，非禁令） | 塗裝彩色、木紋暖色大面積、混凝土粗面 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 鋼柱/框架 | make_metal | color=hex_to_linear('#232323'), roughness=0.35, metallic=1 |
| 玻璃幕墻 | make_glass | tint=(0.82,0.87,0.85), roughness=0.02 |
| 大理石墻片 | make_stone | base=hex_to_linear('#7A8A72'), roughness=0.15（拋光） |
| 石灰華地面 | make_stone | base=hex_to_linear('#D9CDB8'), roughness=0.5 |
| 水面 | make_plastic | base=(0.02,0.03,0.03), roughness=0.02（鏡面近似） |

## ★ 細節特徵
- 工字鋼柱：H 斷面擠出（bpy: 三塊 box 組合或 profile curve）
- 幕墻分割：細鋼壓條對齊柱網（ridge_lines，寬 40mm）
- 挑檐收邊：一條 15mm 金屬亮邊（make_metal roughness=0.2）
- 傢俱：Barcelona 椅（如需要，X 形鋼架+皮墊——make_leather）
- 對拉細節全部隱藏，接縫精確均勻

## ★ 落地 checklist
- [ ] 結構柱外露且柱距等分（模數）
- [ ] 玻璃占比 ≥40%，能看到室內結構
- [ ] 至少一面獨立石材墻片（不承重、自由佈置）
- [ ] 挑檐薄且帶金屬收邊
- [ ] 零彩色塗裝

## ☆ 燈光/渲染
outdoor_golden；玻璃反射是主角——sky_strength 提到 0.4（需要環境反射），水面場景加低角度光拉長倒影。AgX look=Punchy 可用。

## ☆ 代表作
Barcelona Pavilion 1929 / Farnsworth House 1951 / Seagram Building 1958 / Neue Nationalgalerie 1968

## ☆ Prompt 模板
"Mies van der Rohe style pavilion, exposed black steel columns on strict grid, floor-to-ceiling glass walls, freestanding polished marble partitions, thin flat roof with fine metal edge, travertine floor, reflecting pool, golden hour reflections in glass"
