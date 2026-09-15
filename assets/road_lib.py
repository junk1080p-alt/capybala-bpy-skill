# KEYWORDS: blender, bpy, road, street, curve, bevel object, shrinkwrap, lane marking, 道路, 馬路, 車道線, 曲線建路
"""road_lib.py — 單段道路生成（凍結模組，與 shape_lib.py/geonodes_lib.py 同級）。

範圍（bpy 進階技巧調研，2026-09-08，調研結論明確劃了界線，照抄不擴大）：只做「單條
直線/曲線道路，含車道線」，**不做**路口/路網自動生成——查證確認連商業道路生成外掛
（Roadscape、City Road Builder Pro）都把多路口自動接合當作主打付費功能，真正的演算法
是圖論（節點=路口、邊=路段）+ 2D 計算幾何（相鄰路段切線交點求裁切點、Sutherland–
Hodgman 多邊形裁剪補路口面），複雜度跟這次調研另外標記「暫不處理」的 retopology/
G2 曲面連續性是同一個等級，不是隨手加一個函式就能做。路口目前只能手動建（在指定
交會點另外建一塊路口面，讓路段端點對齊即可），這是刻意的範圍，不是漏做。

技術路線確認（不是憑感覺選的）：真正的道路生成工具用 **Curve + bevel_object**（剖面
曲線決定路寬/路緣斷面），不是 bmesh 手動逐頂點拉出一條 ribbon——Blender 5.1.2 實測
確認：帶 bevel_object 的曲線 `bpy.ops.object.convert(target='MESH')` 後**自動產生
UV 貼圖，U 軸精確對應「沿路長度的 0~1 參數」**，車道線材質直接用這組免費的 UV 驅動
虛線圖案，不需要另外用 Geometry Nodes 的 Curve/Spline Parameter 節點（調研原本建議
的做法，但這條路線更簡單、且已用真實數字驗證比對過兩者結果一致）。

地形貼合：`conform_to_terrain()` 用 Shrinkwrap 修飾器（PROJECT 模式）——這是 Blender
核心修飾器，不是取巧；修飾器堆疊在 Curve 物件的 bevel 幾何算完之後才跑，所以
Shrinkwrap 貼的是已經有寬度的路面網格，不是貼曲線本身的細線。

用法（§16.1 場景包）：copy_skill_resource_native 取出到 .capybala/test-scripts/road_lib.py
（與 build_template.py 同層）。典型流程：`make_road_curve()` 建路 → 視需要
`conform_to_terrain()` 貼地形 → 視需要 `add_lane_markings()` 上車道線材質 →
`bpy.ops.object.convert(target='MESH')` 轉真實 mesh 供後續 boolean/audit 使用。

驗證：Blender 5.1.2 headless（2026-09-08）：`make_road_curve()` 對一條直線段驗證
回傳長度精確等於端點距離、對一條有彎曲的路徑驗證回傳長度大於端點直線距離（弧長
必然更長，數學上驗證過不是隨便一個數字）；轉 mesh 後量測實際寬度精確符合 width
參數；`add_lane_markings()` 用實際渲染圖肉眼確認虛線間距/實線連續性正確；
`conform_to_terrain()` 用起伏地形實測確認路面確實貼合地形高度變化，不是浮在
平均高度的一個平面上。

匯入慣例：import road_lib as RL
"""
import math

import bpy
from mathutils import Vector


def _curve_arc_length(curve_obj) -> float:
    """量測曲線目前（未套 bevel_object 前）的弧長——建立階段先量，之後套上
    bevel_object 只改斷面形狀不改路徑本身，長度不會變。用 evaluated depsgraph
    的 to_mesh()（曲線無斷面時求值為一條逐段折線）加總所有邊長，實測驗證：
    直線段精確等於端點距離，彎曲段精確大於端點直線距離（不會算出比直線還短
    的荒謬結果）。
    """
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    eval_obj = curve_obj.evaluated_get(deps)
    mesh = eval_obj.to_mesh()
    length = sum((mesh.vertices[e.vertices[0]].co - mesh.vertices[e.vertices[1]].co).length
                for e in mesh.edges)
    eval_obj.to_mesh_clear()
    return length


def make_road_curve(points, width: float, name: str = "Road", thickness: float = 0.15,
                    banking_deg: float = 0.0, resolution: int = 12):
    """建一條道路：Bezier 路徑（AUTO 平滑控制點）+ 矩形斷面 bevel_object，真正的路寬
    來自斷面曲線尺寸，不是事後縮放猜出來的。

    points：≥2 個世界座標 (x,y,z) waypoint，控制點之間用 AUTO 控制柄自動平滑
    （不是尖角直線段，符合真實道路的平滑轉彎）。width：路面總寬（公尺）。
    thickness：路面斷面厚度（公尺，路緣視覺用，太薄在近景會看起來像一張紙）。
    banking_deg：路面橫向傾斜角（度，彎道超高/排水坡度用），>0 代表路面往路徑
    右側傾斜，套用在所有控制點上（本函式只支援整條路統一坡度，逐點不同坡度
    需要呼叫端事後自行改 `road_obj.data.splines[0].bezier_points[i].tilt`）。

    回傳 (road_obj, length_m)——length_m 是這條路徑的實際弧長（公尺），供
    `add_lane_markings()` 換算虛線間距用，呼叫端不需要自己重算一次。
    """
    if len(points) < 2:
        raise ValueError("make_road_curve: points 至少需要 2 個座標")

    curve_data = bpy.data.curves.new(f"{name}_Path", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = resolution
    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    tilt = math.radians(banking_deg)
    for i, p in enumerate(points):
        bp = spline.bezier_points[i]
        bp.co = Vector(p)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
        bp.tilt = tilt

    road_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(road_obj)
    length_m = _curve_arc_length(road_obj)

    profile_data = bpy.data.curves.new(f"{name}_Profile", type='CURVE')
    profile_data.dimensions = '2D'
    profile_data.fill_mode = 'BOTH'
    pspline = profile_data.splines.new('POLY')
    pspline.points.add(3)
    half = width / 2.0
    corners = [(-half, 0.0, 0.0, 1.0), (half, 0.0, 0.0, 1.0),
               (half, -thickness, 0.0, 1.0), (-half, -thickness, 0.0, 1.0)]
    for i, c in enumerate(corners):
        pspline.points[i].co = c
    pspline.use_cyclic_u = True
    profile_obj = bpy.data.objects.new(f"{name}_Profile", profile_data)
    bpy.context.collection.objects.link(profile_obj)
    # 斷面曲線只是給 bevel_object 參照的形狀定義，本身不該被渲染/顯示成一條額外的線。
    profile_obj.hide_render = True
    profile_obj.hide_viewport = True

    curve_data.bevel_mode = 'OBJECT'
    curve_data.bevel_object = profile_obj
    curve_data.use_fill_caps = True

    return road_obj, length_m


def conform_to_terrain(road_obj, terrain_obj, offset: float = 0.02):
    """路面貼合地形：Shrinkwrap（PROJECT 模式，沿世界 Z 軸投影）——道路很少蓋在
    完全平坦的地面上，這支把已經有寬度的路面網格（bevel 算完之後的修飾器堆疊
    階段）往下投影貼到 terrain_obj 表面，不是貼曲線本身的細線。

    offset（公尺）：路面貼合後往上微幅抬升，避免跟地形表面 z-fighting 或
    因浮點誤差輕微陷入地形（跟 build_template.assert_grounded() 的 tol 是
    同一類「留一點容差」的道理，只是這裡是預先抬高而不是事後檢查）。
    """
    mod = road_obj.modifiers.new(name="ConformToTerrain", type='SHRINKWRAP')
    mod.target = terrain_obj
    mod.wrap_method = 'PROJECT'
    mod.use_project_z = True
    mod.use_negative_direction = True
    mod.use_positive_direction = False
    mod.offset = offset
    return mod


def add_lane_markings(road_obj, length_m: float, style: str = "dashed",
                      asphalt_color=(0.045, 0.045, 0.05), stripe_color=(0.85, 0.8, 0.35),
                      stripe_width_ratio: float = 0.05, dash_length_m: float = 3.0,
                      gap_length_m: float = 6.0, roughness: float = 0.75):
    """幫 road_obj（已轉成 MESH，或至少已設定 bevel_object 使其擁有 UV 的曲線）建一份
    柏油+車道線材質並替換掉現有材質——**呼叫時機**：必須在 `bpy.ops.object.convert
    (target='MESH')` 之後（或至少已經 `bpy.context.view_layer.update()` 讓 bevel 幾何
    真正算出來），UV 才會存在。

    技術：柏油材質的 UV 貼圖 U 軸（`make_road_curve()` 轉 mesh 後自動生成，已實測
    確認精確對應「沿路長度的 0~1 參數」）換算成實際公尺（乘上 length_m），車道線
    用 modulo 運算做 dashed 虛線間距（style='solid' 則跳過 modulo，整條連續）；
    V 軸（斷面方向）取中線±stripe_width_ratio/2 範圍當車道線遮罩，不是整個路面
    寬度都畫線。

    dash_length_m/gap_length_m：虛線的實/虛段長度（公尺，非比例值——車道線國際
    上是絕對長度單位，不是路長的固定比例，路越長虛線段數越多、長度不變）。

    直接**清空並重建**材質槽（`obj.data.materials.clear()` 後 append）——不是往
    既有材質疊層（跟 `mat_lib.add_procedural_wear()` 疊層邏輯不同，這裡的道路
    材質本身就是全新的柏油+車道線一體成型，沒有「既有材質」的概念）。清空這一步
    是必要的：實測發現曲線轉 mesh、疊加多個造型修飾器後，物件常帶著一個空的
    材質槽 0（沿用先前不同物件的殘留狀態），不清空直接 append 會讓新材質變成
    槽 1，但面仍指向槽 0（None），渲染出來變成完全不受材質影響的預設灰色
    ——這正是 `add_procedural_wear()` 開發時期發現的同一個陷阱，這裡直接
    採用同一個修法，不是另外重新踩一次。
    """
    mat = bpy.data.materials.new(f"{road_obj.name}_Asphalt")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0

    uvmap = nt.nodes.new("ShaderNodeUVMap")
    if road_obj.data.uv_layers:
        uvmap.uv_map = road_obj.data.uv_layers[0].name
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uvmap.outputs["UV"], sep.inputs["Vector"])

    # 中線遮罩：V（斷面方向，0~1）距離中心 0.5 在容許範圍內
    center = nt.nodes.new("ShaderNodeMath")
    center.operation = 'SUBTRACT'
    center.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["Y"], center.inputs[0])
    center_abs = nt.nodes.new("ShaderNodeMath")
    center_abs.operation = 'ABSOLUTE'
    nt.links.new(center.outputs["Value"], center_abs.inputs[0])
    width_mask = nt.nodes.new("ShaderNodeMath")
    width_mask.operation = 'LESS_THAN'
    width_mask.inputs[1].default_value = stripe_width_ratio / 2.0
    nt.links.new(center_abs.outputs["Value"], width_mask.inputs[0])
    final_mask = width_mask.outputs["Value"]

    if style == "dashed":
        meters = nt.nodes.new("ShaderNodeMath")
        meters.operation = 'MULTIPLY'
        meters.inputs[1].default_value = length_m
        nt.links.new(sep.outputs["X"], meters.inputs[0])
        period = dash_length_m + gap_length_m
        modn = nt.nodes.new("ShaderNodeMath")
        modn.operation = 'MODULO'
        modn.inputs[1].default_value = period
        nt.links.new(meters.outputs["Value"], modn.inputs[0])
        dash_mask = nt.nodes.new("ShaderNodeMath")
        dash_mask.operation = 'LESS_THAN'
        dash_mask.inputs[1].default_value = dash_length_m
        nt.links.new(modn.outputs["Value"], dash_mask.inputs[0])
        combine = nt.nodes.new("ShaderNodeMath")
        combine.operation = 'MULTIPLY'
        nt.links.new(dash_mask.outputs["Value"], combine.inputs[0])
        nt.links.new(final_mask, combine.inputs[1])
        final_mask = combine.outputs["Value"]
    elif style != "solid":
        raise ValueError(f"add_lane_markings: 未知 style '{style}'（可用：dashed/solid）")

    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (*asphalt_color, 1.0)
    mix.inputs["Color2"].default_value = (*stripe_color, 1.0)
    nt.links.new(final_mask, mix.inputs["Factor"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])

    road_obj.data.materials.clear()
    road_obj.data.materials.append(mat)
    return mat
