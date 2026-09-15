# Leica 徠卡經典味（工業設計/產品）
觸發詞：徠卡味、Leica、旁軸經典、德味、 rangefinder、黑漆銀件
適用年代：1954-now（M3 1954 / M6 1984 / M11 2022，機械美學一脈相承）

## ★ 一句話定位
黑漆黃銅機身 + 拋光銀件 + 荔枝皮蒙皮的機械精密感，六十年不變的設計語言。

## ★ 理念
- 工具主義：相機是攝影的「延伸器官」，每個操作件位置服務於盲操（眼睛不離觀景窗）
- 材料耐久：黃銅底+黑漆，磨損處露銅是「使用的勳章」（lemon 味：patina）
- 減法美學：相比日式同類，按鍵數最少、面板最乾淨，複雜藏在機械內部
- 紅點信仰：品牌符號極小但極強

## ★ 形式語言
- **比例系統（§15.0）：黃金比例×費波那契為主，但硬性規格優先**——蒙皮帶占機身高 0.618、鏡頭軸心在 0.382W 都是黃金比例語言，但機身 138×77×38mm 是真實產品規格，寬高比 ≈1.79 跟 1.618 有落差時**照規格走，不要為了湊 1.618 改外形尺寸**（§15.5 硬性規格優先權）。
- 體量：138×77×38mm 基準（M 機身），寬高比 ≈1.79（接近 1.618 但更寬扁，**實測規格優先於黃金比例** §15.5）
- 厚度分層：頂蓋 14mm / 蒙皮帶 60mm / 底板 11mm（蒙皮帶占 0.618 機身高——天然黃金分割）
- 圓角：機身四角 R=2mm，頂蓋邊緣倒角帶拋光亮線
- 線條：頂蓋-蒙皮-底板三段水平分層是唯一裝飾線；腰線即分層線
- 鏡頭：軸心位於 0.382W（偏左=使用者右手位），鏡筒三段收分

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 黑漆（頂蓋/底板可選黑版） | #14140F | (0.0070,0.0070,0.0048) | 25% |
| 銀件（頂蓋/底板/轉盤） | #C9C9C6 | (0.5841,0.5841,0.5647) | 25% |
| 荔枝皮黑 | #1B1814 | (0.0110,0.0091,0.0070) | 35% |
| 鏡筒黑（陽極） | #101010 | (0.0052,0.0052,0.0052) | 10% |
| 紅點 | #D42020 | (0.6584,0.0144,0.0144) | ≤1% |
| 鍍膜藍紫（鏡片反射） | #2A2A6E | (0.0232,0.0232,0.1559) | 鏡面 |
| 忌避色（選填，非禁令） | 彩色殼、拉絲紋大面積（Leica 用拋光/噴砂）、塑膠感高光 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 頂蓋/底板銀 | make_brushed_metal | color=hex_to_linear('#C9C9C6'), rough_mid=0.16（近拋光） |
| 黑漆版頂蓋 | make_paint | base=hex_to_linear('#14140F'), roughness=0.22, clearcoat=True（鋼琴漆感） |
| 蒙皮 | make_leather | base=hex_to_linear('#1B1814'), grain_scale=900, bump_scale=0.0025 |
| 鏡筒 | make_anodized | color=hex_to_linear('#101010'), roughness=0.4 |
| 對焦環滾花 | make_metal | color=hex_to_linear('#C9C9C6'), roughness=0.25 |
| 鏡片 | make_coated_glass | tint=hex_to_linear('#2A2A6E'), ior=1.62, specular=0.85 |
| 紅點 | make_paint | base=hex_to_linear('#D42020'), roughness=0.15, clearcoat=True |
| LOGO 鐫刻 | make_metal（凹）/make_text | 紅漆填字或白琺瑯 |

## ★ 細節特徵（detail_lib）
- 對焦環：knurl_ring(ridges=89, ridge_depth=0.0005) （0.5mm，函式參數單位是公尺，別直接寫 mm）細密菱形滾花——Leica 鏡頭簽名
- 光圈環：dial_grooves + 刻度刻字（f/2 8 2.8 4…）
- 快門盤：knurl_ring(ridges=55) + 環周速度刻字（1000 500 250…紅字 B）
- 過片扳手：金屬桿+黑塑膠指墊，120° 行程
- 觀景窗：**前窗+目鏡成對**（anatomy/camera.md 成對組件表）
- 背帶環：圓環+三角扣，軸 X
- 紅點：⌀5.5mm，凸出 0.5mm，鏡頭軸左側
- 螺絲：底面 3 顆隱藏於底板凹窩

## ★ 落地 checklist
- [ ] 三段分層（頂蓋/蒙皮/底板）高度比 ≈ 14:60:11
- [ ] 鏡頭軸心在 0.382W
- [ ] 至少 2 處滾花（對焦環+快門盤），齒數 ≥55
- [ ] 紅點唯一彩色元素，占比 ≤1%
- [ ] 觀景窗前窗+背面目鏡成對（assertions 驗證）
- [ ] 銀件用近拋光 roughness ≤0.2，不出現粗糙拉絲

## ☆ 燈光/渲染
studio preset；側上 45° 主光拉銀件高光帶；Fill -20%（黑漆機身要保留暗部層次）；背景深灰 #2E2E2E。AgX Punchy 慎用（紅點會過豔，look 改 Neutral 或 Punchy 但紅漆色票降飽和 10%）。

## ☆ 代表作
- Leica M3（1954）：銀 chrome 版基準
- Leica M6（1984）：黑漆版+紅點經典
- Leica MP（2003）：機械回歸，黃銅露邊 patina 美學
- Noctilux 50mm f/1.2（1966）：鏡頭滾花的巔峰

## ☆ Prompt 模板
"A classic Leica-style rangefinder film camera, chrome top plate and baseplate with black leatherette body wrap, three-segment lens barrel with finely knurled focus ring, small red dot logo, viewfinder front window on top-right front and matching eyepiece on back, engraved dials, precision German mechanical aesthetics, three-quarter product photo on dark grey background"
