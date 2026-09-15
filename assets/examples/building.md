# 建築組合範例
> 適用範圍：規則量體建築（辦公樓/公寓/商辦），矩形平面+格狀立面，不含曲面/非矩形
> 平面或結構構件（梁柱/樓板剖面）
> 涵蓋工具：`building_lib`（`generate_facade`）、`geonodes_lib`（沿表面散布陽台/機電）、
> `mat_lib`（牆面/玻璃材質）、`build_template`（`auto_frame_and_light`）

## 前置知識

- **`assets/anatomy/buildings/`**——建築品類的組件清單/決策
  框架，動工前必查：`_INDEX.md`（由下而上逐層組裝策略+一樓共通元素）、
  `residential.md`/`office.md`（真實查證的數值範圍：WWR、樓層高、spandrel）、
  `flagship_hq.md`（決策框架，非組件清單）。本檔跟這個新目錄的關係：本檔講
  「怎麼呼叫工具」，`anatomy/buildings/` 講「這個品類該長什麼樣、數值抓多少」
  ——兩者互補，不要只查一邊。
- `assets/styles/architecture/` 四張設計師風格卡（安藤忠雄/密斯/札哈/隈研吾）
  決定造型語言，跟 `anatomy/buildings/` 的品類定位是兩個獨立維度（品類決定
  「是什麼」，風格卡決定「長什麼樣」），可以疊加使用。
- `styles/_INDEX.md` 的「建築（architecture/）」表——動工前先判斷這棟建築要不要
  套用特定設計師風格，套用時材質/比例直接抄風格卡數值，不要自己另外發明。
- `building_lib.py` 的範圍限制（見其 docstring）：只做單棟規則矩形平面量體+
  格狀立面（含由下而上逐層組裝，見下方階段一之二），曲面外牆、非矩形平面、
  退縮式摩天大樓輪廓不在函式內部處理——真的需要這類造型，量體可以當起點，
  再用 `shape_lib.taper()`/`loop_cut()`/`move_verts()` 進一步雕塑（跟 §13.10
  車體工作流是同一套工具，建築立面做完之後一樣可以繼續造型加工）。

## 工作流程（依實際呼叫順序）

### 階段一：立面量體（`generate_facade` 一次做完牆面網格+凹陷窗戶）

```python
import build_template as T
import building_lib as BL
import mat_lib as M

wall_mat = M.make_concrete("Building_Wall")
window_mat = M.make_glass("Building_Window", tint=(0.16, 0.22, 0.26), specular=0.5)

building = BL.generate_facade(width=12.0, depth=8.0, height=15.0, floors=5, bays=6,
                              window_ratio=0.6, recess=0.15, name="Tower",
                              wall_mat=wall_mat, window_mat=window_mat)
```

**窗戶玻璃用 `make_glass()`，不要用 `make_coated_glass()`**（`make_coated_glass()` 是高吸收材質，預設 tint 逼近全黑，套在整棟窗戶上會變成一片不透光黑方塊，見 `mat_lib.make_coated_glass()` docstring 與 `anatomy/buildings/residential.md`）。

**參數順序是 `(width, depth, height)`，對齊世界座標 XYZ 軸序**——不是口語「寬高深」
的順序，這支函式的第一版就因為這個認知落差寫錯過（Y/Z 範圍互換），呼叫時對照
`add_box()` 的 `size=(x,y,z)` tuple 順序去想，不要憑直覺。

**材質務必透過 `wall_mat`/`window_mat` 參數傳入**（如上），不要在拿到回傳的 `building`
之後自己呼叫 `building.data.materials.clear()` 再 append——`generate_facade()` 回傳的
是全新 mesh，一開始就沒有材質槽，`.clear()` 會把函式剛分好的 `material_index`（0=牆、
1=窗）全部重設成 0，等於整棟樓都變成牆面材質，窗戶「消失」（不是幾何消失，是材質
索引被抹平）。這是實測抓到的真實 Blender API 陷阱，不是理論風險。

### 階段一之二（多層塔樓改用這個，取代階段一）：由下而上逐層組裝

`generate_facade()` 整棟套用同一個 floors×bays 網格，做不出「一樓特殊處理+
標準層+中段變化+頂層退縮」這種由下而上的真實建造節奏（`anatomy/buildings/_INDEX.md` 有完整策略說明，這裡只示範呼叫）：

```python
ground_wall = M.make_stone("GroundWall")
ground_glass = M.make_glass("GroundGlass")
typ_wall = M.make_paint("TypicalWall", base=(0.8, 0.78, 0.74))
typ_window = M.make_glass("TypicalWindow", tint=(0.16, 0.22, 0.26), specular=0.5)

floor_specs = [{"height": 4.5, "window_ratio": 0.8, "wall_mat": ground_wall, "window_mat": ground_glass}]
floor_specs += [{"height": 3.0, "window_ratio": 0.55, "wall_mat": typ_wall, "window_mat": typ_window}] * 8
floor_specs.append({"height": 2.4, "window_ratio": 0.2, "wall_mat": typ_wall, "window_mat": typ_window})  # 頂層退縮感

building, floor_z_offsets = BL.assemble_building(width=20.0, depth=14.0, floor_specs=floor_specs,
                                                  name="Tower", bays=6)
canopy, supports = BL.make_entrance_canopy(20.0, 14.0, floor_height=floor_specs[0]["height"])
```

**`bays` 是整棟單一參數，不能放進 `floor_specs` 逐層指定**——實測發現逐層不同
bays 會在樓層交界產生大量非流形邊（3 種 bays 混用測出 144 條），真實建築的
結構柱網本來就整棟一致，這個限制反而更貼近現實。`floor_z_offsets` 回傳每層
樓底部世界高度，接下來加陽台/冷氣機直接用這個，不用自己重新累加：

```python
bay_width = 20.0 / 6
for floor_i in range(1, 9):  # 跳過一樓，只在標準層加陽台
    z0 = floor_z_offsets[floor_i]
    for bay_i in range(6):  # 覆蓋大部分/接近整面寬度的開間，見下方註記
        BL.add_balcony(bay_width * (bay_i + 0.5), z0 + 1.0, width=bay_width * 0.9,
                       cheek_mat=cheek_mat)
```

**陽台覆蓋率跟 `cheek_mat` 是立面「凹凸/浮雕感」的關鍵**（見 `anatomy/buildings/_INDEX.md` 與 `residential.md`）：只在少數幾個開間放陽台、其餘留大片平牆，渲染出來立面扁平、陽台像裝飾
貼上去；覆蓋率拉到大部分/接近整面寬度，且每道陽台都給 `cheek_mat`（在陽台兩端加一對垂直分戶側牆，斜側光下會在相鄰陽台間投影）才會有
真實的量體進退層次——這不是材質或燈光能補的，是量體密度本身的問題。

住宅類建築記得查 `anatomy/buildings/residential.md` 的陽台類型/AC 機組章節
（`add_ac_units()` 預設加百葉格柵，不是密封箱）；辦公大樓不要加陽台，見
`office.md` 的「跟住宅的核心差異」段落。

### 階段二（選用）：局部造型加工

若風格卡要求非純方塊量體（例如安藤忠雄的量體退縮、隈研吾的表皮穿孔），在這一步
用 `shape_lib` 對 `building` 繼續雕塑：

```python
import shape_lib as SL
SL.taper(building, axis='Z', factor=0.7, pivot='MIN')   # 例：往上略微收分的量體
```

`generate_facade()` 建出來的窗格材質索引（0/1）在後續 `shape_lib` 造型操作
（`loop_cut`/`bevel_edges` 等）之後仍然有效，除非該操作本身刪除/重建了受影響的面
（例如 `boolean_union` 會產生全新的交界面，那些新面的材質索引預設是 0，需要事後
自己判斷要不要重新指定）。

### 階段三（選用）：陽台/機電設備沿立面散布

規則排列的凸出構件（陽台、遮陽板、屋頂機電箱）不要逐個手動擺放，用
`geonodes_lib.scatter_on_surface()`：

```python
import geonodes_lib as GN

balcony = T.add_box("BalconyUnit", (1.0, 0.6, 0.1), (0, 0, 0))  # 母版，之後會被隱藏
GN.scatter_on_surface(building, balcony, density=0.15, align_to_normal=True)
```

**`realize` 一律留預設 `False`**——`geonodes_lib.py`/`nature_lib.py` 都記錄過同一個
真實的記憶體崩潰地雷：instance 數量夠多、單一實例面數夠高時呼叫 `RealizeInstances`
會導致一次性配置數 GB 記憶體、直接 `EXCEPTION_ACCESS_VIOLATION` 崩潰，不是變慢。
不 realize 完全不影響最終渲染——Cycles 原生支援渲染未 realize 的 instance。

### 階段三之二（選用，但真透射玻璃立面強烈建議做）：玻璃後方室內粗模+停車格

**窗戶用 `make_glass()` 這類真透射材質時，玻璃後面若是中空樓層，渲染出來整片
立面接近純黑方塊**（見 `anatomy/buildings/_INDEX.md`「玻璃立面背後：室內粗模」）——材質再怎麼調都救不回來，缺的是幾何：

```python
interior = BL.add_interior_blockout(
    width=18.0, depth=14.0, floor_z_offsets=floor_z_offsets, floor_height=4.0,
    floor_indices=[0, 1, 2, 3, 8, 9],  # 只影響桌椅/樓梯，柱子/核心永遠貫通全高
    column_mat=column_mat, desk_mat=desk_mat, core_mat=core_mat,
    column_grid=(6.0, 6.0), column_size=0.45, inset=1.2,
    desk_spacing=(2.4, 3.2), desk_row_skip=4,
    include_core=True, core_size=(3.2, 4.4), include_stairs=True, seed=3)
```

**柱子固定貫通全高、方形斷面**（真實結構柱不會「有的層有有的沒有」），桌子是規則等距網格+方形桌側板（不是隨機散布的圓柱椅配方桌），完整說明見 `building_lib.add_interior_blockout()` docstring。

基地周邊順手加一組平面停車格（`building_lib.make_parking_lot()`）——長期以來基地周邊元素只有「種幾棵樹+一條馬路」，明顯比真實商辦/住宅
基地單薄：

```python
pavement, lines = BL.make_parking_lot(
    center=(0.0, -20.0), rows=2, cols=6,
    pavement_mat=asphalt_mat, line_mat=white_paint_mat)
```

### 階段四：構圖+渲染

```python
T.auto_frame_and_light([building], style="product", azimuth_deg=40.0, elevation_deg=25.0)
T.build_camera()
T.build_lights(dict(T.PRESETS["studio"]))
```

**已知限制**：若主體是細長/巨大建築（例如高塔），構圖後畫面裡天空/地面占比會明顯
變大，`check_exposure()` 的全畫面 `luma_band` 可能被大量背景拉低觸發假警報，即使
主體本身曝光正確清晰可見——這種情況改用 `preset_overrides` 放寬 `luma_band`，不要
照抄 studio 預設的 100-170 帶（見 `auto_frame_and_light()` docstring 已知限制段落）。

### 階段四之二：建築 hero 鏡頭（氣派帥視角，需要地面環境時）

純主體展示卡（樓浮在深灰地上）走上面的 studio + 三點式即可。要「帥」的氣派建築鏡頭，
把樓放進自己的地面環境（前庭／廣場／街道）→ 走 `outdoor_golden`／`night` preset +
低機位廣角 PERSP，配方（實測數值：相機型別/鏡頭/機位高/`sky_strength`/太陽角/泛光/亮度帶）
與三條鐵律（**鏡面帷幕牆仰角定律**、天空占比 derate 陷阱、廣角才有壓迫感）見
`anatomy/buildings/_INDEX.md` 的「高層建築 hero 鏡頭」段。

```python
# 低機位仰視（黃金時刻）：機位低於立面大部分 → 拋光帷幕反射天空、讀起來銀白
T.set_camera(loc=(235, -245, 15), target=(-45, -5, 255), lens=20, fstop=8.0)
T.apply_socket_overrides(mats, C.LOOK_OVERRIDES, label="hero")   # 鏡頭專屬反光 pass
T.assert_mirror_sky_fraction(tower, min_frac=0.6)                # 先驗證再渲
```

`set_aspect("9:16")` 是這類鏡頭的預設畫幅（直幅才裝得下高樓＋廣場）；`luma_band` 通常要
放寬（大面積天空會把全畫面 mean 拉高，見上表實測值與 §10.2 規則 8）。

## 常見錯誤（實戰回填區）

| # | 錯誤 | 判讀方式 | 修正 |
|---|---|---|---|
| 1 | `generate_facade(width, height, depth, ...)` 憑口語「寬高深」順序呼叫 | Y/Z 兩軸範圍互換，牆面比例整個錯掉 | 正確順序是 `(width, depth, height)`，對齊 XYZ 軸序，不是口語順序 |
| 2 | 拿到回傳物件後自己 `.materials.clear()` 再 append | 整棟樓變單一材質，窗戶「消失」 | 材質一律透過 `wall_mat`/`window_mat` 參數傳入，不要事後清空重來 |
| 3 | 屋頂/地板只用 4 個角頂點手動封面（若要自己修改 `generate_facade()` 內部邏輯時容易重蹈覆轍） | 量出大量非流形邊（早期版本實測 56 條），全部落在 z=0/z=height | 屋頂/地板要貼齊牆面頂/底排的實際細分頂點走一圈 n-gon，不能只用 4 角 |
| 4 | `assemble_building()` 的 `floor_specs` 裡放 `bays` 逐層指定不同值 | 樓層交界處大量非流形邊（實測 3 種 bays 混用產生 144 條） | `bays` 是 `assemble_building()` 的頂層參數，不放進 `floor_specs` 字典裡 |

## 驗證方式

1. 標準 CALIB 快渲先過曝光帶（注意上方「已知限制」——細長建築可能需要放寬 `luma_band`）。
2. 材質正確性檢查：
   ```python
   from collections import Counter
   print(dict(Counter(p.material_index for p in building.data.polygons)))
   # 應該同時看到 0（牆）跟 1（窗）兩個索引都有非零面數
   ```
3. 流形檢查（若對 `generate_facade()` 產出的量體做過進一步 boolean/雕塑）：
   ```python
   import bmesh
   bm = bmesh.new(); bm.from_mesh(building.data)
   bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
   print(bad)  # 期望 0
   ```
4. 渲染圖肉眼確認：窗格排列規則、每扇窗有真實內凹陰影（不是平貼紋理的假窗）。
