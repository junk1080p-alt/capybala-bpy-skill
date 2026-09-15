# KEYWORDS: blender, bpy, geometry nodes, geonodes, scatter, instance, curve to points, distribute points, 散布, 陣列, 沿曲面, 沿曲線
"""geonodes_lib.py — 窄範圍 Geometry Nodes 散布工具（凍結模組，與 shape_lib.py 同級）。

定位（bpy 進階技巧調研，2026-09-08）：`shape_lib.linear_array()`（Array modifier）只能
做**直線**重複——沿曲面/曲線繞行的重複陣列（塔身外牆螺栓、公車車身沿弧線排列的鉚釘、
道路旁沿曲線排列的路燈）bmesh/Array modifier 做不到，這是本檔要補的缺口。刻意只做
「沿曲線散布」跟「沿表面散布」這兩個窄範圍情境，不做通用 Geometry Nodes 包裝器——
盲寫節點連線（`nodes.new()`/`links.new()` 沒有視覺回饋）在精確箱型建模/布林密集的
硬表面工作上比 bmesh 更脆弱（接錯一個 socket 靜默產生空的/錯的幾何，沒有任何錯誤
訊息），只在「這正是 Geometry Nodes 設計來解決的問題」這個範圍內採用，不取代
shape_lib.py 既有的 bmesh 工具。

★RealizeInstances 記憶體炸彈（比照 nature_lib.py 已記錄的事實 #9，同一個地雷，
不是本檔獨立發現——寫這支之前有先查過 nature_lib.py 既有的 scatter_on_surface()，
兩者刻意同名不是巧合，是同一類散布操作，安全規則理當一致）：instance 數量夠多、
單一實例 poly 數夠高時呼叫 RealizeInstances 會讓 Blender 嘗試一次配置數 GB 記憶體，
實測導致 Malloc null → EXCEPTION_ACCESS_VIOLATION 直接崩潰，不是「跑比較慢」而是
「跑不完」。兩支函式一律 `realize: bool = False` 預設值——不 realize 的 instance
形態由 Cycles 渲染時原生展開，depsgraph 零記憶體，一般散布/渲染用途完全不需要
`realize=True`。只有需要把散布結果併入真實 mesh 供 boolean_union()/cut_hole() 等
後續操作時才設 True，且一律先過 `REALIZE_POLY_BUDGET`（跟 nature_lib.py 用同一個
門檻 500,000，這是實測校準過的數字，不要各自發明不同的安全邊界）安全檢查，超支
直接 raise 而不是靜默跑到記憶體耗盡。

兩支函式都是「在目標物件上加一個 Geometry Nodes 修飾器」，不是回傳獨立資料。
`instance_obj`（被重複的母版物件）一律設 `hide_render = True` 隱藏原始物件本身
（跟 build_template.park_master() 的母版隔離慣例一致），只讓散布出來的實例被
渲染，避免母版自己也多算一份。

★真實 bug 已修復（2026-09-09，撰寫 examples/road.md 時實測發現，跟 nature_lib.py
檔頭事實 #12 是同一個陷阱）：初版節點圖只把 instance 雲接去 Group Output，**沒有
把宿主自己的幾何併回去**——host 只要是「本來就有自己表面」的物件（`road_lib`
建出來的真實路面、任何既有 mesh），評估後會被整個「取代」成 0 頂點，只剩懸空的
散布物；host 是裸曲線/裸平面（自己沒有可見表面）時剛好測不出這個問題，這也是
初版檔頭「驗證」段落沒抓到的原因。現在兩支函式都用 `GeometryNodeJoinGeometry`
把 Group Input（宿主原始幾何）跟 instance 雲合併——套用在任何本來就有幾何的
host（`road_lib` 路面、`building_lib` 立面等）上之前，這是必須知道的修復史，
不是可以忽略的細節。

已知限制：CURVE 型物件的 `obj.bound_box`/`obj.dimensions` 不會反映 Geometry Nodes
修飾器算出來的實際幾何範圍（實測發現：對掛了本檔 scatter_along_curve() 的 curve_obj
呼叫 `auto_frame_and_light()`，算出來的構圖完全沒把散布出來的實例算進去）——曲線
散布完，構圖/包圍盒相關計算改用另一個確定會反映最終幾何的參考物件（例如同時傳入
一個真正的 MESH 物件），或事後用 evaluated depsgraph 的 `to_mesh()` 自行量測，不要
直接信任散布後的 curve_obj 本身的 bound_box。

5.1 API 落差備忘（本檔目前用不到，但未來擴充這裡的 Geometry Nodes 節點圖時會踩到，
先記錄）：Geometry Nodes 語境下 **`FunctionNodeSeparateXYZ` 已被移除**（`nodes.new()`
直接報 "Node type ... undefined"），要拆 Vector 成分改用 `FunctionNodeSeparateColor`
（Position 這類 Vector 輸出可以直接接進它的 Color 輸入 socket，Z 值從 Blue 輸出取）。
注意這**只影響 Geometry Nodes**——Shader（材質）節點樹的 `ShaderNodeSeparateXYZ`
沒有受影響、5.1.2 實測仍然存在（`road_lib.add_lane_markings()` 目前就是用這個，
不要看到這條備忘就誤以為那裡也要改）。

驗證：Blender 5.1.2 headless（2026-09-08），`scatter_along_curve()` 在一條 90° 圓弧
Bezier 曲線上排 12 個實例（evaluated mesh 頂點數精確符合 12×單一實例頂點數，渲染圖
肉眼確認每個實例確實沿切線方向對齊）、`scatter_on_surface()` 在一個 4x4m 平面上以
density=8 散布（evaluated mesh 頂點數精確符合 density×面積=128 個實例，非估計值）。
2026-09-09 修復 JoinGeometry 缺失後重新驗證：`scatter_on_surface()` 對一個 4 頂點
平面呼叫後，evaluated mesh 從錯誤的 0 頂點恢復成正確的 4 頂點（host 幾何保留）；
`scatter_along_curve()` 疊在 `road_lib.make_road_curve()` 建出的真實路面曲線上，
轉 mesh 後從錯誤的 0 頂點恢復成正確的 108 頂點（路面+UV 皆保留，與只呼叫
`make_road_curve()` 不疊加散布時的結果一致）。

匯入慣例：import geonodes_lib as GN
"""
import math

import bpy

REALIZE_POLY_BUDGET = 500_000  # 跟 nature_lib.py 用同一個實測校準過的門檻，不要另外發明


def _rv_vector_socket(node):
    """FunctionNodeRandomValue 的 Vector 輸出——4 個輸出同名 "Value"（Vector/Float/
    Int/Bool 各一個），用 outputs["Value"] 名稱索引在目前版本剛好命中 Vector（因為
    它排第一個），但這是巧合、不是保證，換一個 Blender 版本 socket 生成順序改變就會
    悄悄接錯——一律用 bl_idname 明確篩選（跟 nature_lib.py 的同名 helper 是同一個
    寫法，遇到同一個 API 陷阱就該用同一套修法，不要各自重新踩一次）。
    """
    for s in node.outputs:
        if s.bl_idname == "NodeSocketVector" and s.enabled:
            return s
    raise KeyError("RandomValue 無 enabled Vector 輸出（data_type 未設 FLOAT_VECTOR？）")


def _rv_set_minmax(node, lo, hi):
    vec_ins = [s for s in node.inputs if s.bl_idname == "NodeSocketVector"]
    vec_ins[0].default_value = lo
    vec_ins[1].default_value = hi


def _new_group(name: str):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", socket_type="NodeSocketGeometry", in_out="INPUT")
    ng.interface.new_socket("Geometry", socket_type="NodeSocketGeometry", in_out="OUTPUT")
    group_in = ng.nodes.new("NodeGroupInput")
    group_out = ng.nodes.new("NodeGroupOutput")
    return ng, group_in, group_out


def _instance_source(ng, instance_obj):
    """ObjectInfo（As Instance=True）——回傳可直接接 InstanceOnPoints.Instance 的輸出腳位。
    一併把 instance_obj 設成 hide_render，避免母版自己也被算進最終渲染。
    """
    instance_obj.hide_render = True
    obj_info = ng.nodes.new("GeometryNodeObjectInfo")
    obj_info.inputs["Object"].default_value = instance_obj
    obj_info.inputs["As Instance"].default_value = True
    return obj_info.outputs["Geometry"]


def _finish_output(ng, group_in, tail_socket, group_out, realize: bool,
                   est_instance_count: float, instance_obj):
    """收尾：realize=False（預設，生產標準）直接把 instance 雲接去 Group Output；
    realize=True 先過 REALIZE_POLY_BUDGET 安全檢查再接 RealizeInstances。

    ★真實 bug 修復（2026-09-09，撰寫 examples/road.md 時實測發現）：早期版本這裡
    只把 instance 雲接去 Group Output，**沒有把宿主自己的幾何（Group Input）併回去**
    ——跟 `nature_lib.py` 檔頭事實 #12 記錄的是同一個陷阱：只接 instance 雲時，宿主
    幾何（車道路面、建築牆面本身）評估後被整個「取代」成 0 頂點，只剩懸空的散布物。
    早期單獨測試 `scatter_along_curve()`/`scatter_on_surface()` 時剛好都只對一條
    「沒有自己表面」的裸曲線/裸平面測試，才沒發現這個問題——實際疊在
    `road_lib.make_road_curve()`（曲線本身帶 bevel_object 真正路面）或任何本來就有
    表面的 host 上時，host 會整個消失。現在用 `GeometryNodeJoinGeometry` 把
    Group Input（宿主原始幾何）跟 instance 雲合併，兩者都不遺失。
    """
    join = ng.nodes.new("GeometryNodeJoinGeometry")
    ng.links.new(group_in.outputs["Geometry"], join.inputs["Geometry"])

    if realize:
        max_polys = len(instance_obj.data.polygons) if hasattr(instance_obj.data, "polygons") else 0
        budget_est = est_instance_count * max_polys
        if budget_est > REALIZE_POLY_BUDGET:
            raise ValueError(
                f"realize=True 預估 {budget_est:.0f} polys 超過安全上限 {REALIZE_POLY_BUDGET}"
                f"（約 {est_instance_count:.0f} 個實例 × {max_polys} polys/實例）。"
                "RealizeInstances 在這個規模下實測會導致記憶體配置失敗、直接崩潰（不是變慢）。"
                "請降數量/密度、換更低面數的 instance_obj，或改用預設 realize=False"
                "（一般渲染用途不需要 realize，Cycles 原生支援渲染未 realize 的 instance）。")
        real = ng.nodes.new("GeometryNodeRealizeInstances")
        ng.links.new(tail_socket, real.inputs["Geometry"])
        tail_socket = real.outputs["Geometry"]
    ng.links.new(tail_socket, join.inputs["Geometry"])
    ng.links.new(join.outputs["Geometry"], group_out.inputs["Geometry"])


def scatter_along_curve(curve_obj, instance_obj, count: int, align_to_curve: bool = True,
                        jitter_pos: float = 0.0, jitter_rot_deg: float = 0.0, seed: int = 0,
                        realize: bool = False):
    """沿曲線散布 count 個 instance_obj 副本（等弧長分布，非等參數化 t 值分布——
    `GeometryNodeCurveToPoints` 的 Count 模式內部已處理，彎曲率高的路段不會擠成一團）。

    curve_obj 必須是 Curve 物件（bpy.data.objects，type=='CURVE'）；一般搭配
    bpy.ops.curve.primitive_bezier_curve_add() 或手動建的 Bezier/NURBS 曲線。

    align_to_curve=True：每個實例的旋轉直接吃 CurveToPoints 自帶的 Rotation 輸出
    （已經是「Z 軸沿切線方向」的旋轉，不需要額外算 Align Euler to Vector）——這是
    這支函式選 CurveToPoints 而不是手動取樣曲線點的主要原因，旋轉是免費附贈的。

    jitter_pos（公尺）/jitter_rot_deg（度）：均勻隨機抖動，讓排列不要死板到看起來
    像複製貼上（跟 mat_lib._obj_coords() 用隨機平移+旋轉打破材質重複感是同一個目的，
    只是這裡抖動的是位置/朝向而不是紋理座標）。0 代表不抖動、完全規則排列。

    realize：見檔頭「RealizeInstances 記憶體炸彈」說明，預設 False，只有需要真實
    mesh 供布林/幾何後續操作時才設 True（會先做安全預算檢查，超支直接 raise）。

    回傳新增的 Geometry Nodes 修飾器（`.node_group` 可再取出手動微調）。
    """
    ng, group_in, group_out = _new_group(f"GN_ScatterCurve_{instance_obj.name}")
    c2p = ng.nodes.new("GeometryNodeCurveToPoints")
    c2p.mode = 'COUNT'
    c2p.inputs["Count"].default_value = int(count)
    ng.links.new(group_in.outputs["Geometry"], c2p.inputs["Curve"])

    points_socket = c2p.outputs["Points"]
    if jitter_pos > 0.0:
        rv_pos = ng.nodes.new("FunctionNodeRandomValue")
        rv_pos.data_type = 'FLOAT_VECTOR'
        _rv_set_minmax(rv_pos, (-jitter_pos, -jitter_pos, -jitter_pos), (jitter_pos, jitter_pos, jitter_pos))
        rv_pos.inputs["Seed"].default_value = seed
        set_pos = ng.nodes.new("GeometryNodeSetPosition")
        ng.links.new(points_socket, set_pos.inputs["Geometry"])
        ng.links.new(_rv_vector_socket(rv_pos), set_pos.inputs["Offset"])
        points_socket = set_pos.outputs["Geometry"]

    inst = ng.nodes.new("GeometryNodeInstanceOnPoints")
    ng.links.new(points_socket, inst.inputs["Points"])
    ng.links.new(_instance_source(ng, instance_obj), inst.inputs["Instance"])
    if align_to_curve:
        rot_socket = c2p.outputs["Rotation"]
        if jitter_rot_deg > 0.0:
            j = math.radians(jitter_rot_deg)
            rv_rot = ng.nodes.new("FunctionNodeRandomValue")
            rv_rot.data_type = 'FLOAT_VECTOR'
            _rv_set_minmax(rv_rot, (-j, -j, -j), (j, j, j))
            rv_rot.inputs["Seed"].default_value = seed + 1
            add_rot = ng.nodes.new("ShaderNodeVectorMath")
            add_rot.operation = 'ADD'
            ng.links.new(rot_socket, add_rot.inputs[0])
            ng.links.new(_rv_vector_socket(rv_rot), add_rot.inputs[1])
            rot_socket = add_rot.outputs["Vector"]
        ng.links.new(rot_socket, inst.inputs["Rotation"])

    _finish_output(ng, group_in, inst.outputs["Instances"], group_out, realize, count, instance_obj)

    mod = curve_obj.modifiers.new(name="GN_ScatterCurve", type='NODES')
    mod.node_group = ng
    return mod


def scatter_on_surface(mesh_obj, instance_obj, density: float, align_to_normal: bool = True,
                       jitter_rot_deg: float = 0.0, seed: int = 0, realize: bool = False):
    """在 mesh_obj 表面上依密度散布 instance_obj 副本（`GeometryNodeDistributePointsOnFaces`
    的 Poisson-disc-like 隨機分布，不是等距網格——真實的螺栓/鉚釘/裝飾釘排列本來就有
    輕微不規則感，等距網格反而看起來像貼花而非真實五金件）。

    density：每平方公尺期望的實例數量（Density 輸入，數值越大越密集，跟表面實際
    面積無關——`DistributePointsOnFaces` 內部已經用面積正規化，同一個 density 值
    套在小面板跟大牆面上，實際「單位面積內幾顆」的視覺密度一致）。

    align_to_normal=True：用 `FunctionNodeAlignEulerToVector` 把每個實例的 Z 軸
    對齊到採樣點的表面法向量（螺栓頭朝外、裝飾釘垂直於表面本來就該這樣，不對齊
    會讓所有實例朝著同一個世界方向，看起來像穿模插進表面）。

    realize：見檔頭「RealizeInstances 記憶體炸彈」說明，預設 False；設 True 時的
    預算檢查用 `density × mesh_obj 表面積` 粗估實例數（呼叫端密度/面積差異很大時
    這是粗估值，寧可低估後現場 raise，也不要略過檢查）。

    回傳新增的 Geometry Nodes 修飾器。
    """
    ng, group_in, group_out = _new_group(f"GN_ScatterSurface_{instance_obj.name}")
    dist = ng.nodes.new("GeometryNodeDistributePointsOnFaces")
    dist.inputs["Density"].default_value = float(density)
    dist.inputs["Seed"].default_value = seed
    ng.links.new(group_in.outputs["Geometry"], dist.inputs["Mesh"])

    inst = ng.nodes.new("GeometryNodeInstanceOnPoints")
    ng.links.new(dist.outputs["Points"], inst.inputs["Points"])
    ng.links.new(_instance_source(ng, instance_obj), inst.inputs["Instance"])
    if align_to_normal:
        align = ng.nodes.new("FunctionNodeAlignEulerToVector")
        align.axis = 'Z'
        ng.links.new(dist.outputs["Normal"], align.inputs["Vector"])
        rot_socket = align.outputs["Rotation"]
        if jitter_rot_deg > 0.0:
            j = math.radians(jitter_rot_deg)
            rv_rot = ng.nodes.new("FunctionNodeRandomValue")
            rv_rot.data_type = 'FLOAT_VECTOR'
            _rv_set_minmax(rv_rot, (-j, -j, -j), (j, j, j))
            rv_rot.inputs["Seed"].default_value = seed + 1
            add_rot = ng.nodes.new("ShaderNodeVectorMath")
            add_rot.operation = 'ADD'
            ng.links.new(rot_socket, add_rot.inputs[0])
            ng.links.new(_rv_vector_socket(rv_rot), add_rot.inputs[1])
            rot_socket = add_rot.outputs["Vector"]
        ng.links.new(rot_socket, inst.inputs["Rotation"])

    area = sum(p.area for p in mesh_obj.data.polygons) or 1.0
    est_count = density * area
    _finish_output(ng, group_in, inst.outputs["Instances"], group_out, realize, est_count, instance_obj)

    mod = mesh_obj.modifiers.new(name="GN_ScatterSurface", type='NODES')
    mod.node_group = ng
    return mod
