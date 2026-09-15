# 車體組合範例
> 適用範圍：四門/兩門房車、跑車類車體殼體（單一連續量體，不含底盤懸吊/引擎機構/內裝）
> 涵蓋工具：`shape_lib`（造型雕塑 + `cut_window`）、`mat_lib`（烤漆/玻璃/磨損）、
> `build_template`（`add_box`/`auto_frame_and_light`）

## 前置知識

- **SKILL.md §13.10「造型雕塑操作」**——本範例延續該節「車體工作流範例」①-⑤步（`add_box`
  →`loop_cut`→`move_verts`→`bevel_edges` 做出擋風玻璃斜角），本檔從步驟⑤之後繼續，
  不重複那段已經寫過的內容。動工前務必先讀那節，本檔假設你已經知道那五步。
- **SKILL.md §13.10 規則 7（船帆事故）**——玻璃艙絕對不要用獨立物件拼接，這正是
  `cut_window()` 存在的理由，見下方階段三。
- **`anatomy/car.md` 已補上六面組件清單**（車燈/後視鏡/門把/輪拱
  等配對關係+「最低限度表現原則」）——Stage A 規劃前先查那份，本檔只涵蓋「殼體
  造型+開窗+材質」這個技法子集，不重複組件盤點的內容。
- `styles/` 沒有專屬車輛風格卡；`industrial/` 底下的工業設計風格卡（例如 `apple-ive.md`
  的陽極鋁+無縫拼接語言）可以借來定義烤漆/飾條的材質方向，不是只能套用在電子產品上。
- **本檔只涵蓋「殼體+開窗+基礎烤漆/磨損」這一個技法子集，走完本檔六個階段不等於整台車完工**——車燈/後視鏡/門把/輪拱這些組件本身要靠 `anatomy/car.md` 的六面清單規劃，其中車輪還細分到輻條/中心蓋/氣嘴/卡鉗/螺帽五個次組件。本檔跟 anatomy 圖譜是互補關係，不要因為走完本檔的程式碼骨架就以為 Stage A 元件表已經全部落地。

## 工作流程（依實際呼叫順序）

### 階段一：主體量體 + 擋風玻璃斜角（§13.10 既有範例，此處僅接續）

```python
import build_template as T
import shape_lib as SL
import mat_lib as M
import proportions_lib as PR

p = PR.car_proportions(length=4.2, category="sedan")  # 別再手填猜測尺寸，見 anatomy/car.md
body = T.add_box("CarBody", size=(p["width"], 4.2, p["height"]), loc=(0, 0, p["height"] / 2))
new_loop = SL.loop_cut(body, axis='Y', position=0.3)
top = [c for c in new_loop if abs(c[2] - 1.1) < 0.01]
SL.move_verts(body, top, delta=(0, 1.0, -0.5))
SL.bevel_edges(body, angle_limit_deg=15.0, width=0.03, segments=3)
```

做到這裡是一個有擋風玻璃斜角、邊緣已導圓角的**單一連續殼體**，`add_box` 本來就建完整
對稱量體、不是半邊——`add_mirror()` 只在 Stage A 就決定「只建一半省工」時才用得上，
這裡不需要再鏡射，直接兩側開窗即可。後面步驟都建立在「殼體是連續的」這個前提上，
之後不要改用獨立物件拼接任何部件。

### 階段二：先上車身烤漆材質（順序很重要）

```python
body_mat = M.make_paint("CarPaint_Red", base=(0.55, 0.04, 0.03), roughness=0.28,
                        metallic=0.15, clearcoat=True)
body.data.materials.append(body_mat)   # 車身材質務必先 append，佔材質槽 0
```

**這步必須在下一步「開窗」之前做**（實測抓到的真實順序陷阱）：`body` 剛建出來時
所有面的 `material_index` 都是預設值 0；`cut_window()` 會把玻璃材質 append 到
「目前材質列表的下一個可用索引」再把選中的窗戶面指過去——如果先開窗、後上漆，
玻璃會佔走槽 0，車身原本沒被選中的面卻**還是**指向槽 0，等於整台車（含玻璃）
都變成玻璃材質，車身烤漆變成完全沒有任何面在用的孤兒材質槽。先讓車身材質佔好
槽 0，之後 `cut_window()` 呼叫幾次都只會往後加新槽，不會互相打架。

### 階段三：開窗（`cut_window`——這是本範例最關鍵的一步）

```python
glass_mat = M.make_coated_glass("CarGlass", tint=(0.02, 0.03, 0.05), ior=1.52)

# 擋風玻璃：cutter 只是定義範圍的框，不需要真的貼合車體曲率
windshield_cutter = T.add_box("WindshieldCutter", (1.6, 0.9, 1.0), (0, 1.05, 0.85))
windshield_cutter.hide_render = True
windshield_cutter.hide_viewport = True
SL.cut_window(body, windshield_cutter, glass_mat, frame_inset=0.04, recess=0.015)

# 側窗：左右各建一個 cutter，範圍卡在殼體 X=±0.9 的側面上（略往內縮到 ±0.85，
# 確保 cutter 中心真的落在殼體表面附近，不是恰好卡在邊界外側選不到任何面）
side_l_cutter = T.add_box("SideWindowL", (0.12, 1.3, 0.4), (-0.85, -0.2, 0.75))
side_l_cutter.hide_render = True
side_l_cutter.hide_viewport = True
SL.cut_window(body, side_l_cutter, glass_mat, frame_inset=0.03, recess=0.01)

side_r_cutter = T.add_box("SideWindowR", (0.12, 1.3, 0.4), (0.85, -0.2, 0.75))
side_r_cutter.hide_render = True
side_r_cutter.hide_viewport = True
SL.cut_window(body, side_r_cutter, glass_mat, frame_inset=0.03, recess=0.01)
```

實測（Blender 5.1.2 headless）：三次 `cut_window()` 呼叫分別選中 3+3+3 個面，
`body.data.materials` 最終順序精確是 `['CarPaint_Red', 'CarGlass']`（槽 0/槽 1），
`material_index` 分布 98:9（車身:玻璃），跟預期完全吻合。

**為什麼是 `cut_window` 不是 `cut_hole`**：車體殼體是薄殼、不是有厚度的封閉實體，
`cut_hole()` 的布林差集在這種幾何上會失敗或產生退化面（見 `shape_lib.cut_window()`
docstring）。`cut_window` 直接在殼體現有的面上選區域換材質+局部內縮，窗戶曲率
100% 繼承車頂/車側本身的曲面，這正是避免「玻璃艙變船帆」（§13.10 規則 7）的根本
原因——不是這個函式比較會算角度，是它的做法讓曲率不連續這種錯誤**在結構上不可能
發生**。

`windshield_cutter`/`side_l_cutter` 的尺寸/位置只是**框出範圍**，不需要精確貼合
車體曲率——`cut_window` 用世界包圍盒篩選現有面，範圍寬一點窄一點只影響窗戶邊界
落在哪幾條既有邊上，不影響曲率保留這個核心效果。

### 階段四：飾條材質（車身烤漆已在階段二上好）

```python
trim_mat = M.make_brushed_metal("CarTrim", color=(0.6, 0.6, 0.62))
```

**同一個物件不要中途呼叫 `body.data.materials.clear()`**——這會把已經分好的
玻璃/車身面材質索引全部重設成 0（`building_lib.py`/`shape_lib.py` docstring 都
記錄過這個真實的 Blender API 陷阱）。真的需要「重新配色」時，改成直接改
`body_mat` 這個既有 Material 物件的節點參數，不要清空材質槽重來。

門把/飾條這類小型金屬件：現階段沒有專屬函式，用 `add_box`/`add_cyl` 建小物件、
`bevel_edges` 導角、套 `trim_mat`，`boolean_union` 或直接擺位貼合車身即可，不需要
複雜工具（這類小型剛性零件本來就該是獨立物件，不是連續殼體的一部分——判準見
SKILL.md §13.10「物件數是下限不是上限」段落）。

### 階段五：磨損（選用，二手車/戰損車才需要）

```python
M.add_procedural_wear(body_mat, edge_color=(0.75, 0.73, 0.7), dirt_color=(0.04, 0.035, 0.03),
                      edge_intensity=0.4, dirt_intensity=0.3, ao_distance=0.12)
```

全新展示車不要加這步。`ao_distance` 已經是依車體實際尺度（~1-2m 量級）校準過的
合理值，不需要再依 `auto_frame_and_light()` 的 bbox 對角線重算——這個量級的物件跟
`mat_lib.py` 校準時用的測試量體差不多大。

### 階段六：構圖+渲染

```python
T.auto_frame_and_light([body], style="product", azimuth_deg=35.0, elevation_deg=25.0)
T.build_camera()
T.build_lights(dict(T.PRESETS["studio"]))
```

車輛展示照一般用 `style="product"`（均勻棚拍）；戰損/氛圍照可以用 `"dramatic"`。
elevation 建議 20-30 度（略帶俯角，展現車頂+車側），不要用預設的 35 度俯角公式
生搬硬套所有物件——那是給任意尺度主體的合理起點，車輛這種扁長型主體實測略低
一點的仰角構圖更好看。

## 常見錯誤（實戰回填區）

| # | 錯誤 | 判讀方式 | 修正 |
|---|---|---|---|
| 1 | 玻璃艙用 11 個獨立 `add_box` 拼接，每片各自算旋轉角度貼上 | 渲染出來玻璃艙像插了幾片船帆，各面法向不連續，即使每片座標數值都對 | 改用本檔階段三的 `cut_window()`，窗戶直接繼承殼體曲率 |
| 2 | 開窗前呼叫 `body.data.materials.clear()` 清空「殘留材質槽」 | 玻璃/車身材質索引全部變 0，渲染出來整台車同一個顏色 | 不要清空——`cut_window()`/新建 mesh 從一開始就沒有殘留物可清，這個殘留物假設本身就是錯的 |
| 3 | `cutter` 尺寸做得跟窗戶最終形狀完全一致，以為要精確貼合 | 花費過多回合微調 cutter 頂點座標 | `cut_window` 只用 cutter 的世界包圍盒篩選範圍，不需要精確輪廓，框大概位置即可 |
| 4 | 先開窗、後上車身烤漆材質 | 渲染出來整台車（含玻璃）都是玻璃材質，車身烤漆完全沒有任何面在用 | 一律先 append 車身材質佔好槽 0，再呼叫 `cut_window()`（見階段二說明） |

## 驗證方式

1. 標準 CALIB 快渲（`BLENDER_TEMPLATE_CALIB=1`）先過曝光帶。
2. **曲率保留檢查**（車體專屬，不是每個任務都要做，但開窗後建議至少做一次）：
   ```python
   glass_polys = [p for p in body.data.polygons if p.material_index == <glass_idx>]
   zs = [body.data.vertices[i].co.z for p in glass_polys for i in p.vertices]
   print(min(zs), max(zs))  # 應該有一定範圍變化，不是單一數值（單一數值=被拍平成平面）
   ```
3. 渲染圖肉眼確認：車頂到玻璃艙到後窗是不是視覺上連續的一片曲面過渡，不是好幾片
   各自朝不同方向的平板——這正是 §13.10 規則 7 事故要避免的觀感。

## 其他車型（`proportions_lib.car_proportions(length, category=...)` 換 category 即可）

本檔工作流（量體→開窗→材質）四類車型通用，差異只在比例跟局部造型：

| 類別 | 跟房車的關鍵差異 | 備註 |
|---|---|---|
| `suv` | 車頂/腰線更高、輪拱明顯外凸容納更大輪胎、常有車頂行李架 | 開窗步驟不變，`p["height"]`/`p["wheel_diameter"]` 直接代入 |
| `bus` | 車身接近方形箱體，側面連續帶狀窗（多片 `cut_window` 沿長軸排列），無獨立引擎蓋 | 車門用 `p["door_front_w"]`（固定值，不是均分軸距） |
| `truck` | 車頭獨立駕駛艙（跟房車同一套量體→塑形流程）+ 後方分離貨廂（獨立量體，直接 box 不需開窗塑形） | 駕駛艙跟貨廂是兩個物件，中間留車架間隙 |
