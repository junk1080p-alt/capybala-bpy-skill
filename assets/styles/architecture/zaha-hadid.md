# Zaha Hadid 札哈·哈蒂（建築）
觸發詞：札哈、Zaha、參數化、流動曲線、解構主義、白色流體建築
適用年代：1993-2016（Vitra 消防站 1993 / 廣州歌劇院 2010 / Galaxy SOHO 2012）

## ★ 一句話定位
無直角的白色/灰色流體幾何，地面墻面屋面連續彎曲成一體，參數化格子表皮。

## ★ 理念
- 「90° 是多余的」：尖銳角度與流動曲面並存的早期解構，後期轉向連續流體 [src: Zaha 公開訪談語境]
- 地形化建築：建築是地景的延伸，地面隆起成為墻與屋面
- 參數化主義（Schumacher 宣言）：格子、條帶、漸變孔徑作為形式語言

## ★ 形式語言
- **比例系統（§15.0）：黃金比例×費波那契為主**——條帶寬/孔徑漸變序列走費波那契節奏（見下方細節特徵），曲率沒有固定公式，以連續、非等距的漸變感為目標。
- 曲線：大尺度連續曲面（NURBS/superellipsoid），主曲率半徑 = 建築短邊×0.5-2
- 開洞：橢圓孔洞陣列，孔徑漸變（parametric aperture gradient）
- 條帶：立面水平流線條帶，條帶寬走漸變序列
- 支撐：斜柱/V 形柱，與曲面切向連續
- 兩個時期：早期（1993-2004）尖銳碎裂灰混凝土；後期（2005-2016）白色流體 GRC

## ★ 色票（後期流體期為主）
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 流體白 | #F2F1EE | (0.8879,0.8796,0.8550) | 65% |
| 陰影灰 | #B8B6B2 | (0.4793,0.4678,0.4452) | 20% |
| 玻璃帶（深灰） | — | make_glass tint=(0.15,0.16,0.17) | 12% |
| 室內暖木點綴 | #C8A878 | (0.5776,0.3916,0.1878) | 3% |
| 忌避色（選填，非禁令） | 磚紅、傳統屋瓦色、直角窗框銀 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 流體殼體 | make_plastic | base=hex_to_linear('#F2F1EE'), roughness=0.3（GRC 半光） |
| 混凝土座 | make_concrete | base=hex_to_linear('#B8B6B2') |
| 玻璃帶 | make_glass | tint=(0.15,0.16,0.17) |
| 室內木地板 | make_wood | base=hex_to_linear('#C8A878') |

## ★ 細節特徵
- 曲面落地（bpy）：primitive_torus/sphere 布爾差集、Bezier 曲線掃掠（curve bevel）、subdivision surface modifier（關鍵：control cage + smooth）
- 條帶分割：曲面 UV 空間等分 → 實體化細長 box 沿曲線陣列（或 displacement texture 近似）
- 孔洞漸變：多顆橢圓布爾差集，孔徑按位置插值
- 禁止 box 堆疊假曲線（§15.3.6）——札哈風全部是真曲面

## ★ 落地 checklist
- [ ] 主體至少 70% 表面為連續曲面（無硬折角）
- [ ] 白色占比 ≥60%，陰影灰自然產生於曲面背光
- [ ] 至少一處孔洞/條帶漸變節奏
- [ ] subdivision smooth shading 開啟（無 facet 感）
- [ ] 地面與建築連續（無明顯基座分界）

## ☆ 燈光/渲染
outdoor_golden 或 studio 大柔光；曲面的美感靠**漸變陰影**——單一主光+弱 Fill（光比 2.5:1），sky 0.3。白色主體 mean 易超帶（§10.2.6），目標帶壓 110-140。

## ☆ 代表作
Vitra 消防站 1993（早期尖銳期）/ Phaeno 科學中心 2005 / 廣州歌劇院 2010（雙礫石）/ Galaxy SOHO 2012（四塔流體相連）/ Heydar Aliyev Center 2012（地景連續曲面巅峰）

## ☆ Prompt 模板
"Zaha Hadid style fluid white architecture, continuous curving surfaces merging ground wall and roof, no right angles, parametric strip facade with gradient elliptical openings, glass ribbon windows, smooth subdivision surfaces, soft directional light with gradient shadows"
