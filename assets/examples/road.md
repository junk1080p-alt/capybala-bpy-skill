# 馬路組合範例
> 適用範圍：單段直線/曲線道路（含車道線、地形貼合、沿路道具），不含路口/路網自動生成
> 涵蓋工具：`road_lib`（全部三支函式）、`geonodes_lib`（`scatter_along_curve` 排路燈）、
> `build_template`（`auto_frame_and_light`）

## 前置知識

- **`road_lib.py` 的範圍限制**（docstring 已明講，不是本檔重複提醒）：路口/路網自動
  生成不在範圍內——真實演算法是圖論（節點=路口、邊=路段）+ 2D 計算幾何（切線交點
  求裁切、Sutherland–Hodgman 多邊形裁剪補路口面），複雜度跟 retopology/G2 曲面連續性
  同一級。多路段交會時，路口**手動建**（在交會點另外建一塊路口面，讓路段端點對齊）。
- 沒有 `anatomy/road.md`——道路品類目前靠本檔決定流程，沒有組件清單類參考。**本檔只涵蓋路面本體+車道線+路燈這三項，真實道路場景通常還有這些本檔不處理的組件，Stage A 規劃時要自己想到，不要因為本檔沒寫就跳過**：路緣石（curb，路面與人行道交界的高低差量體，`add_box` 沿路緣一條即可）、排水溝蓋/人孔蓋（路面上的小型圓形/方形嵌板，`add_cyl`/`add_box` 淺嵌+材質區隔）、交通標誌/號誌（`add_cyl` 桿+`add_box`/`flat_decal` 牌面）、護欄/分隔島（路側或中央分隔，`curve_tube`/`add_box` 陣列）、斑馬線（車道線以外的另一種路面標線，`add_lane_markings()` 目前只做車道虛線，斑馬線要另外疊加平行短條紋）。這些component 目前沒有專屬函式，見上方各自建議的基礎工具組合。
- `nature_lib.py`（§18）——路側植栽/行道樹用它的 `make_tree()`/`scatter_on_surface()`，
  不是本檔範圍，兩者可以在同一個場景裡各自呼叫、互不干擾。

## 工作流程（依實際呼叫順序）

### 階段一：建路

```python
import build_template as T
import road_lib as RL
import geonodes_lib as GN

road, length_m = RL.make_road_curve(
    points=[(0, 0, 0), (10, 6, 0), (25, 4, 1.5)],
    width=4.0, name="MainRoad")
print(f"路長 {length_m:.1f}m")  # 實測：這條彎道弧長 27.13m（三點折線直線距離 25.36m，
                                 # 弧長本來就該比直線距離長，是數學上的下限檢查）
```

`points` 之間用 Bezier AUTO 控制柄自動平滑，不是尖角折線——不需要自己算轉彎緩和曲線。
`length_m` 是這條路徑的實際弧長，之後 `add_lane_markings()` 跟本檔階段三的路燈間距
計算都要用這個值，不要自己用端點直線距離估計（彎道會低估）。

### 階段二：貼合地形（若地面不是完全平坦）

```python
RL.conform_to_terrain(road, terrain_obj, offset=0.03)
```

`terrain_obj` 是既有的地形 mesh（`nature_lib.make_terrain()`/`make_terrain_pure_bpy()`
建的，或任何場景既有地面）。Shrinkwrap 是在 Curve 物件的 bevel 幾何算完之後才跑的
修飾器，貼的是已經有寬度的路面網格，不是貼曲線本身的細線——不需要先轉 mesh 才能貼合。

### 階段三：沿路排路燈

```python
lamp = T.add_cyl("StreetLamp", radius=0.08, depth=3.0, loc=(0, 0, 1.5))
count = max(2, round(length_m / 12.0))   # 約每 12m 一盞，用實際弧長換算，不是猜數字
GN.scatter_along_curve(road, lamp, count=count, align_to_curve=True)
```

**這一步一定要排在階段四（轉 mesh）之前**——`scatter_along_curve()` 是加在 `road`
這個 CURVE 物件上的 Geometry Nodes 修飾器，`bpy.ops.object.convert(target='MESH')`
會把當時整個修飾器堆疊（含這個散布修飾器）一起烘進最終 mesh；順序顛倒的話轉 mesh
時修飾器已經不在了，路燈不會被烘進去。`align_to_curve=True` 讓每盞燈直接繼承
`CurveToPoints` 自帶的切線旋轉，不需要自己算路燈該朝哪個方向。

**已修復的真實 bug**：早期版本的 `scatter_along_curve()` 疊在有真實路面的曲線上，轉 mesh 後路面會整個消失變成 0 頂點，只剩懸空路燈——`geonodes_lib.py` 已修好這個問題（見該檔案 docstring），目前版本疊加使用安全。

### 階段四：轉 mesh + 車道線

```python
import bpy
bpy.context.view_layer.objects.active = road
bpy.ops.object.select_all(action='DESELECT')
road.select_set(True)
bpy.ops.object.convert(target='MESH')

lane_mat = RL.add_lane_markings(road, length_m, style="dashed",
                                dash_length_m=3.0, gap_length_m=6.0)
```

`add_lane_markings()` 用轉 mesh 後 Blender 自動產生的 UV（U 軸精確對應沿路長度
0~1 參數，實測驗證過）換算實際公尺驅動虛線間距——**呼叫時機必須在 `convert
(target='MESH')` 之後**，UV 是轉 mesh 這一步才會生成的。`add_lane_markings()`
內部會 `road.data.materials.clear()` 再 append 新材質——這是安全的，因為
`add_lane_markings()` 本來就是要整條路只有一種柏油+車道線材質，沒有「材質索引
需要保留」的問題（跟 `building_lib`/`cut_window` 那種「已經分好多種材質索引、
`.clear()` 會抹平」的情境不同，不要混淆這兩條規則）。

### 階段五：構圖+渲染

```python
T.auto_frame_and_light([road, terrain_obj], style="product", azimuth_deg=200.0, elevation_deg=55.0)
```

**已知限制**：轉成 CURVE 再轉 MESH 之後的 `road` 物件，`bound_box` 在某些情況下
可能無法完整反映散布修飾器算出的最終範圍（跟 `geonodes_lib.py` docstring 記錄的
曲線 bound_box 限制是同一類問題）——若構圖明顯不合理（路燈被裁到畫面外、鏡頭離太遠
或太近），改成手動指定相機位置，或用 `road`/`terrain_obj` 以外真正涵蓋整個場景範圍
的參考物件餵給 `auto_frame_and_light()`。

## 常見錯誤（實戰回填區）

| # | 錯誤 | 判讀方式 | 修正 |
|---|---|---|---|
| 1 | `scatter_along_curve()` 疊在真實路面曲線上，轉 mesh 後路面消失 | 轉 mesh 後頂點數是 0，只剩懸空路燈 | 已在 `geonodes_lib.py` 修復（`GeometryNodeJoinGeometry` 併回宿主幾何），目前版本正常，若又出現同樣症狀先確認 `geonodes_lib.py` 版本是否夠新 |
| 2 | 先轉 mesh、後排路燈散布 | 路燈完全沒出現在最終幾何裡 | `scatter_along_curve()` 必須在 `convert(target='MESH')` 之前呼叫，散布是修飾器，轉 mesh 才會把它烘進去 |
| 3 | `add_lane_markings()` 在 `convert(target='MESH')` 之前呼叫 | 車道線材質完全沒有效果／報錯找不到 UV | UV 是轉 mesh 這一步才生成的，`add_lane_markings()` 必須排在轉 mesh 之後 |

## 驗證方式

1. `length_m` 合理性：彎道路徑的 `length_m` 應該大於三個端點連成的折線總直線距離
   （彎道弧長必然更長，這是數學下限，不是「大概對」而已）。
2. 路燈+路面共存檢查（轉 mesh 之後）：
   ```python
   print(len(road.data.vertices))  # 應該 > 0（純路面幾何），路燈本身是未 realize 的
                                    # instance，不會出現在頂點數裡，但路面不能是 0
   ```
3. 地形貼合檢查（若做了階段二）：
   ```python
   import bpy
   deps = bpy.context.evaluated_depsgraph_get()
   zs = [ (road.matrix_world @ v.co).z for v in road.evaluated_get(deps).to_mesh().vertices ]
   print(min(zs), max(zs))  # 應該隨地形起伏有變化，不是單一數值（單一數值=沒真的貼合）
   ```
4. 渲染圖肉眼確認：路面跟著地形起伏、路燈沿弧線正確朝向切線方向、車道線虛線間距
   看起來規律（不是忽密忽疏）。
