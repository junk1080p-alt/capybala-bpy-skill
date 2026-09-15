# 80s 復古未來主義（工業設計/產品）
觸發詞：80 年代復古未來、賽博舊化、CRT 味、Synthwave 實體、復古科幻道具
適用年代：1977-1991 想像中的「未來 2000」（星際大戰道具、Blade Runner、Tron、日本シティポップ 封面器械）

## ★ 一句話定位
米白/暖灰塑膠殼 + 彩色色塊分區 + 機械開關外露的「模擬時代未來感」。

## ★ 理念
- 未來 = 更多按鈕與儀表，不是更少（與極簡主義相反）
- 塑膠是太空時代材料：米白 ABS 殼 + 模具線清晰可見
- 資訊密度即安全感：LED 數字屏、VU 指針表、實體撥桿
- 色彩分區：功能區塊用色塊區隔（橙=危險、藍=資料、綠=運行）

## ★ 形式語言
- **比例系統（§15.0）：黃金比例（不對稱重量分佈）+ 簡單整數比/模矩制（按鍵矩陣網格）混用**——左右重量分佈走 0.618/0.382，但通風槽/按鍵矩陣是等距網格語言（2×4/3×5），兩者疊加使用，不是純黃金比例卡。
- 體量：厚實箱體，厚度 = 0.382×寬（比現代產品厚一倍）
- 圓角：中等 R=3-5mm，模具圓角非連續曲率
- 線條：水平通風槽（3-5 條等距）、凹陷面板分區（每區下沉 1mm）
- 斜切：面板 15° 斜切操作區（儀表板感）
- 不對稱：左顯示區/右操作區，重量分佈 0.618/0.382

## ★ 色票
| 角色 | hex | linear | 占比 |
|---|---|---|---|
| 米白殼（老塑膠微黃） | #E8E0D0 | (0.8069,0.7454,0.6308) | 50% |
| 暖灰面板 | #9C968A | (0.3325,0.3050,0.2541) | 20% |
| 炭黑（格柵/縫） | #2A2A28 | (0.0232,0.0232,0.0212) | 15% |
| 安全橙（色塊） | #E85D26 | (0.8069,0.1095,0.0194) | 8% |
| 電子藍（色塊/LED） | #3A7BD5 | (0.0423,0.1981,0.6654) | 5% |
| LED 綠 | #4AE84A | (0.0685,0.8069,0.0685) | ≤2% |
| 忌避色（選填，非禁令） | 金屬拉絲大面積、純白（要帶暖）、深色碳纖 | | |

## ★ 材質映射表
| 部位 | factory | 參數 |
|---|---|---|
| 主殼 | make_plastic | base=hex_to_linear('#E8E0D0'), roughness=0.48（ABS 半光） |
| 面板 | make_plastic | base=hex_to_linear('#9C968A'), roughness=0.42 |
| 色塊區 | make_paint | 橙/藍, roughness=0.35 |
| 通風格柵 | make_plastic | base=hex_to_linear('#2A2A28'), roughness=0.6 |
| 金屬件（螺絲/軸） | make_metal | color=(0.6,0.6,0.62), roughness=0.4（鍍鋅件，不拋光） |
| CRT 螢幕 | make_glass + make_emissive | 玻璃罩 ior 1.5 + 內側 emissive 藍綠 strength 2 |
| LED 指示燈 | make_emissive | 綠/橙, strength=6 |

## ★ 細節特徵（detail_lib）
- 撥桿開關：矩形槽+金屬桿（make_screw 變體拉長），行程外露
- 按鈕：方形鍵帽帶 chamfer，按鍵群 2×4/3×5 矩陣（grid 對齊）
- 滾輪/旋鈕：knurl_ring(ridges=34) + 頂面指針線
- 通風槽：ridge_lines 變體（凹槽而非凸脊，mat 給炭黑）
- 螺絲：十字螺絲外露且多（每面板角落一顆）——時代特徵
- 標籤：make_text 小字（型號「MODEL CPB-2000」貼在正面右下）
- 模具線：seam_ring/seam 細線沿分模位置

## ★ 落地 checklist
- [ ] 米白殼占比 ≥45%（時代識別度核心）
- [ ] 色塊 ≤3 種且各自占比 ≤8%
- [ ] 至少 2 處外露螺絲群 + 1 處通風槽
- [ ] 至少 1 個發光元素（LED/CRT）且為視覺焦點之一
- [ ] 面板有下沉分區（≥2 區）

## ☆ 燈光/渲染
studio preset 微暖（Key 色溫偏 4500K 等效：Base 微黃）；或 night preset + CRT 自發光主光。背景可給漸層紫（Synthwave 語境）或純深灰（道具攝影語境）。

## ☆ 代表作
- IBM PC 5150（1981）：米白箱體+黑鍵盤
- 星際大戰道具面板（1977）：密集按鈕+色塊
- Atari 2600（1977）：木紋貼皮+米白殼+撥桿開關，本卡年代範圍的起點錨點（不引用「Sony TR-55」：1955 年產品，年代不符）
- Blade Runner 偵探機器械（1982）：黃銅+米白+LED
- Casio FX 科學計算機（1980s）：滑蓋+彩色功能鍵

## ☆ Prompt 模板
"A retro-futuristic 1980s device, beige ABS plastic housing with visible mold lines, charcoal recessed panel with grid-aligned square buttons, orange and blue color-block zones, exposed Phillips screws, ventilation slots, glowing green LED indicator, small CRT screen with blue-green glow, analog synth-era product photography on dark grey background"
