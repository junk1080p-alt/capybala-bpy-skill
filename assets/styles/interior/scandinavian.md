# 北歐風 Scandinavian（室內設計）
觸發詞：北歐風、IKEA 味、hygge、斯堪地那維亞、Nordic

## ★ 一句話定位
淺色木+白墻+灰藍織物，機能主義的溫暖極簡，光線是第一位的材料。

## ★ 理念
- 「民主設計」（IKEA 語境）：美觀/實用/優質/永續/低價五位一體 [src: IKEA 公開設計原則]
- hygge：燭光、織物、暖光的舒適共處感（丹麥）
- 光線稀缺地理決定美學：大窗、淺色反射面、多層次人工暖光

## ★ 形式語言
- **比例系統（§15.0）：留白與簡約 + 簡單整數比/模矩制**——墻面留白 60% 以上是核心語言（留白系統），櫃體走 600mm 模矩整數倍；不是黃金比例卡，不要預設套 `fib_split`/`golden_series`。
- 傢俱：細錐腿（橡木/桦木）、圓角小（R=5-15mm）、輕盈離地（沙發腿高 150mm）
- 櫃體：無把手（push-open）或細木棒拉手；模數 600mm
- 線條：直線為主+單件曲線單品（蛋椅/天鵝椅式點綴）
- 留白：墻面 60% 以上空白，裝飾品少而大（1 盞燈+2 盆栽+1 畫）

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 墻白（微暖） | #F4F1EA | (0.9047,0.8796,0.8228) | 45% |
| 淺橡木 | #D9BE97 | (0.6939,0.5149,0.3095) | 25% |
| 灰藍織物 | #7C8FA0 | (0.2016,0.2747,0.3515) | 12% |
| 炭黑細件 | #2B2B2B | (0.0242,0.0242,0.0242) | 8% |
| 芥末黃點綴 | #D9A648 | (0.6939,0.3813,0.0648) | 5% |
| 植物綠 | #4A6B45 | (0.0685,0.1470,0.0595) | 5% |
| 忌避色（選填，非禁令） | 深紅木色、金色五金、高對比黑白、大理石大面 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 地板/傢俱木 | make_wood | base=hex_to_linear('#D9BE97'), roughness=0.5（哑光油面） |
| 墻面 | make_plastic | base=hex_to_linear('#F4F1EA'), roughness=0.92（哑光乳膠漆） |
| 沙發/窗簾 | make_fabric | base=hex_to_linear('#7C8FA0'), weave_scale=1600 |
| 燈具金屬細件 | make_metal | color=hex_to_linear('#2B2B2B'), roughness=0.4（黑哑光烤漆） |
| 毛毯/抱枕 | make_fabric | base=hex_to_linear('#D9A648') 或白 |

## ★ 細節特徵
- 燈具：紙/布面罩吊燈（emissive 暖光 2700K 等效 (1,0.82,0.6) strength=4）+ 細黑線桿
- 織物層疊：沙發 2 毛毯+3 抱枕（隨機旋轉微抖 §10.1 環境敘事）
- 盆栽：龜背芋/琴葉榕（簡化葉片幾何），陶盆淺灰
- 掛畫：細黑框+抽象色塊（make_text 替代或純色面）
- 地毯：平織灰白，低 bump

## ★ 落地 checklist
- [ ] 白+淺木合計 ≥65%，彩色全部是織物/小件（可換不固定）
- [ ] 至少 3 層次暖光（主燈+立燈+燭光/窗光）
- [ ] 傢俱腿細錐化，離地
- [ ] 裝飾物件 ≤5 件（少而大）
- [ ] 植物 ≥1 盆

## ☆ 燈光/渲染
outdoor_golden 或 studio 暖化（Key 微暖 (1,0.95,0.88)）；室內場景 practical lights 多盞低強度（每盞 30-60W 等效）；目標 mean 120-160（明亮空氣感）。

## ☆ 代表作
IKEA STOCKHOLM 系列 / Hans Wegner Y 椅語境 / Artek 弯曲桦木 / Menu/Audo 當代丹麥

## ☆ Prompt 模板
"Scandinavian interior, white walls, light oak floor and furniture with tapered legs, grey-blue fabric sofa with layered throws, mustard accent cushion, black thin-frame pendant lamp with warm glow, monstera plant in grey pot, minimal large wall art, bright soft daylight"
