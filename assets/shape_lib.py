# KEYWORDS: blender, bpy, bmesh, shape, sculpt, loop cut, extrude, bevel, mirror, taper, 造型, 雕塑, 車體, 曲面, 頂點編輯
"""shape_lib.py — 造型雕塑函式庫（凍結模組，與 mat_lib.py/detail_lib.py/nature_lib.py 同級，§13.10）。

解決「所有東西都是方塊/圓柱堆疊」問題（使用者原話：「我希望最少能做到畫出像是
特斯拉車機3D地圖裡面那種車體形狀，不是什麼都是正方體」）：真正的產品/載具造型
是靠「量體 → 切割出新頂點 → 移動頂點塑形 → 選擇性倒角」這套流程疊代出來的
（3D 建模師的日常工作流程，不是找 primitive 找不到就放棄複雜輪廓），加上鏡射
（對稱造型只建一半）、布林聯集（多個量體真正融合成一個連續表面）、收分
（沿軸向漸縮剖面）這三個常見輔助操作。

用法（§16.1 場景包）：copy_skill_resource_native 取出到 .capybala/test-scripts/shape_lib.py
（與 build_template.py 同層），geometry.py 的 make_xxx() 在母版建完基礎量體
（`T.add_box`/`T.add_cyl`）後、join 進 detail_lib 細節或 park_master 之前呼叫本 lib
做造型編輯。

座標公約：所有函式讀寫**世界座標**（`obj.matrix_world` 換算），不是局部座標——
因為 `loop_cut()` 回傳值要能直接餵給 `select_verts_by_bounds()`/`move_verts()`/
`bevel_edges()` 用座標比對挑頂點/邊，統一用世界座標最不容易出錯。頂點/邊比對
一律帶容差（`tol`，預設 1mm），因為浮點座標很少剛好相等。

實測：Blender 5.1.2 headless（2026-09-08），完整車體工作流（box→loop_cut→
select+move→bevel）+ add_mirror + boolean_union + taper 四項獨立驗證全部
PASS（vert 數、bounding box、bmesh.calc_volume() 皆為預期值，無退化幾何）。

2026-09-08 新增（bpy 進階技巧調研，三支獨立驗證全部 PASS）：`clean_boolean_result()`——
布林運算後清共面碎面（旋轉過的 cutter 實測確認會產生需要清理的共面切割線，軸對齊
布林通常沒有）；`add_weighted_normal()`——改善倒角面的刻面感，一律加在修飾器堆疊
最後；`linear_array()`——直線陣列包裝（欄杆/螺栓排），只適合直線重複。

匯入慣例：import shape_lib as SL
"""
import math

import bmesh
import bpy
from mathutils import Vector, Matrix


def _bm_open(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def _bm_close(bm, obj):
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()


def loop_cut(obj, axis: str, position: float):
    """沿 axis（'X'/'Y'/'Z'）在世界座標 position 處切一圈新邊迴圈（bisect_plane）。

    回傳這一刀新產生的所有頂點的「世界座標」清單（tuple 清單）——bmesh 在函式
    結束時就 free 了，沒辦法回傳活的頂點控制代碼，之後要選這批頂點的子集
    （例如只要最上面那一排），用 select_verts_by_bounds() 或直接對這份清單
    自己用座標篩選都可以。
    """
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis.upper()]
    normal_local = Vector((0, 0, 0))
    normal_local[axis_idx] = 1.0
    mat = obj.matrix_world
    inv = mat.inverted()
    plane_co_world = Vector((0, 0, 0))
    plane_co_world[axis_idx] = position
    plane_co_local = inv @ plane_co_world
    plane_no_local = (inv.to_3x3() @ normal_local).normalized()

    bm = _bm_open(obj)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    result = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co_local,
                                     plane_no=plane_no_local, clear_inner=False,
                                     clear_outer=False)
    new_verts = [g for g in result['geom_cut'] if isinstance(g, bmesh.types.BMVert)]
    coords_world = [tuple(mat @ v.co) for v in new_verts]
    _bm_close(bm, obj)
    return coords_world


def select_verts_by_bounds(obj, x=None, y=None, z=None):
    """回傳 obj 目前所有頂點裡，世界座標落在指定 (min,max) 範圍內的頂點世界座標。
    x/y/z 各給 (min,max) 或留 None（該軸不限制）。
    """
    def _in(val, rng):
        return rng is None or (rng[0] - 1e-6 <= val <= rng[1] + 1e-6)
    mat = obj.matrix_world
    out = []
    for v in obj.data.vertices:
        w = mat @ v.co
        if _in(w.x, x) and _in(w.y, y) and _in(w.z, z):
            out.append(tuple(w))
    return out


def move_verts(obj, target_coords, delta, tol=0.001):
    """把世界座標命中 target_coords（來自 loop_cut/select_verts_by_bounds 回傳值，
    容差 tol）的頂點整體平移 delta（世界座標向量）。回傳實際移動的頂點數
    （用來確認有沒有真的選中——0 代表座標沒對上，八成是 tol 太小或 target 抄錯了）。
    """
    bm = _bm_open(obj)
    mat = obj.matrix_world
    inv = mat.inverted()
    delta_local = inv.to_3x3() @ Vector(delta)
    targets = [Vector(c) for c in target_coords]
    moved = 0
    for v in bm.verts:
        w = mat @ v.co
        for t in targets:
            if (w - t).length <= tol:
                v.co += delta_local
                moved += 1
                break
    _bm_close(bm, obj)
    return moved


def bevel_edges(obj, edge_endpoints=None, width=0.005, segments=2, angle_limit_deg=None, tol=0.001):
    """選定邊做倒角/導圓角（跟 add_box 的 bevel 參數不同——那是整個物件所有邊統一
    套用的 Bevel modifier，這支是精確挑邊的 bmesh 倒角，適合手動編輯過、造型不規則
    的 mesh）。

    edge_endpoints：[(world_co_a, world_co_b), ...] 逐條邊指定兩端世界座標（來自
    loop_cut/select_verts_by_bounds 回傳值），只倒這些邊。留 None 則退回
    angle_limit_deg 模式：自動挑「兩側面夾角 ≥ 這個角度」的邊（跟 add_box 的
    bevel 邏輯類似，適合還沒手動編輯過的簡單量體整體去毛邊）。兩者至少給一個。
    """
    bm = _bm_open(obj)
    mat = obj.matrix_world
    geom = []
    if edge_endpoints is not None:
        targets = [(Vector(a), Vector(b)) for a, b in edge_endpoints]
        for e in bm.edges:
            wa, wb = mat @ e.verts[0].co, mat @ e.verts[1].co
            for ta, tb in targets:
                if ((wa - ta).length <= tol and (wb - tb).length <= tol) or \
                   ((wa - tb).length <= tol and (wb - ta).length <= tol):
                    geom.append(e)
                    break
    else:
        limit = math.radians(angle_limit_deg if angle_limit_deg is not None else 20.0)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                try:
                    if e.calc_face_angle() >= limit:
                        geom.append(e)
                except ValueError:
                    pass
    if geom:
        bmesh.ops.bevel(bm, geom=geom, offset=width, segments=segments,
                         affect='EDGES', clamp_overlap=True)
    _bm_close(bm, obj)
    return len(geom)


def add_mirror(obj, axis: str = 'X', merge: bool = True):
    """加 Mirror modifier（造型左右/前後對稱時，只建一半、鏡射出另一半）。
    軸是物件局部座標軸——母版建造時習慣把對稱軸放在局部原點，鏡射才會準。
    不自動 apply（留在 modifier 堆疊，最終渲染前如果要併入單一 mesh 供
    instance()/cut_hole() 使用，呼叫端自行 modifier_apply）。
    """
    mod = obj.modifiers.new(name="Mirror", type='MIRROR')
    mod.use_axis = (axis.upper() == 'X', axis.upper() == 'Y', axis.upper() == 'Z')
    mod.use_bisect_axis = mod.use_axis
    mod.use_clip = merge
    return mod


def boolean_union(a, b, apply: bool = True, delete_b: bool = True, solver: str = 'EXACT'):
    """布林聯集：把 b 併入 a，變成一個連續的 mesh（跟 join 不同——join 只是把兩個
    物件的 mesh 資料合併成一份 data-block，重疊/相交處不會真的融合成單一表面；
    boolean UNION 會真的在交界處重新計算表面，適合「主體量體+額外凸起造型」要
    融成一體的情境，例如車頭主體+額外拉出來的引擎蓋隆起）。
    """
    bpy.context.view_layer.objects.active = a
    mod = a.modifiers.new(name="Bool_Union", type='BOOLEAN')
    mod.object = b
    mod.operation = 'UNION'
    mod.solver = solver
    if apply:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if delete_b:
        bpy.data.objects.remove(b, do_unlink=True)
    return a


def clean_boolean_result(obj, angle_limit_deg: float = 5.0):
    """boolean_union()/cut_hole() 之後的清理（2026-09-08 新增，bpy 進階技巧調研）：
    布林運算的交界處常留下大量共面的細碎三角/四邊面（求解器為了描述交線切出的
    退化細分），肉眼看不出差別但頂點/面數暴增，之後 loop_cut()/bevel_edges() 這類
    靠幾何拓樸判斷的操作會被這些多餘的邊干擾。`bmesh.ops.dissolve_limit()` 是
    標準清理手法：把「兩側面法向量夾角小於 angle_limit_deg」的邊直接融解——
    真正的造型邊（法向量明顯轉折）保留，只清掉共面/近共面的多餘切割線。

    回傳實際融解掉的面數（0 代表這批幾何本來就乾淨，不代表函式失敗）。
    boolean_union() 預設 solver='EXACT' 求解器碎面問題本來就比 FAST 求解器輕微，
    但仍建議布林運算後養成習慣呼叫一次本函式，尤其是多次疊加布林運算之後。
    """
    bm = _bm_open(obj)
    result = bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle_limit_deg),
                                      use_dissolve_boundaries=False,
                                      verts=list(bm.verts), edges=list(bm.edges))
    dissolved = len(result.get('region', []))
    _bm_close(bm, obj)
    return dissolved


def add_weighted_normal(obj, keep_sharp: bool = True):
    """加 Weighted Normal modifier（2026-09-08 新增，bpy 進階技巧調研，概念確認於
    MIT 授權 hard_surf_utils 專案）：硬表面倒角邊在低面數下常出現「刻面感」（同一個
    圓角面被畫成一段一段的平面拼接，而不是平滑的圓弧過渡）——這不是幾何精度不夠，
    是預設的逐頂點法向量平均沒有考慮各面的實際面積權重。Weighted Normal 依面積
    重新加權計算頂點法向量，不增加任何一個頂點就能顯著改善倒角面的視覺平滑度，
    是硬表面渲染的標準修飾器，不是取巧。

    一律加在修飾器堆疊**最後**（`obj.modifiers.new()` 預設就是附加到堆疊尾端，
    不需要額外排序——Bevel/Mirror/Boolean 等造型類修飾器必須先完成，Weighted
    Normal 才能拿到最終幾何算出正確法向量，加在中間或最前面等於算了假資料）。
    keep_sharp=True 啟用修飾器自身的 `keep_sharp` 選項，讓手動標記的 Sharp 邊
    不被這個修飾器抹平——真正該保持銳利的邊（例：箱型體的直角）不會被誤判成
    需要平滑。
    """
    mod = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    mod.keep_sharp = keep_sharp
    return mod


def linear_array(obj, axis: str = 'X', count: int = 2, offset: float = 1.0, apply: bool = False):
    """直線陣列（2026-09-08 新增，bpy 進階技巧調研）：欄杆/螺栓排/窗戶欄位這類沿單一
    直線方向規則重複的元素，用 Array modifier 包裝，不要手動迴圈複製物件——modifier
    版本改一個 count 參數就能重排，手動複製要逐一搬動每個實例。

    axis：物件局部座標軸（'X'/'Y'/'Z'），offset：相鄰兩個實例間距（沿該軸的相對位移，
    公尺，物件局部座標系下）。**只適合直線重複**——沿曲面/曲線繞行的重複陣列
    （例：塔身外牆螺栓、公車車身沿弧線排列的鉚釘）Array modifier 做不到，需要
    Curve modifier 疊加或真正的表面散布，屬於另一類工具，不是本函式的範圍。
    apply=True 立刻烘進 mesh（供 boolean_union()/cut_hole() 等需要真實幾何而非
    modifier 堆疊的後續操作使用），預設 False 保留在堆疊上方便之後調整 count。
    """
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis.upper()]
    mod = obj.modifiers.new(name="Array", type='ARRAY')
    mod.count = count
    mod.use_relative_offset = True
    dims = obj.dimensions[axis_idx] or 1.0
    displace = [0.0, 0.0, 0.0]
    displace[axis_idx] = offset / dims
    mod.relative_offset_displace = tuple(displace)
    if apply:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return mod


def cut_window(obj, cutter, glass_mat, frame_inset: float = 0.02, recess: float = 0.005):
    """快速開窗（2026-09-08 新增，使用者原話：「AI給車體開窗做的很差」）：把 obj
    表面上落在 cutter 世界包圍盒範圍內的既有面，整片改成玻璃材質——**不是**布林
    交集/差集，這是刻意的選擇，不是省事：車體外殼、帷幕牆這類**薄殼**（沒有實際
    厚度的曲面）本身通常不是封閉實體，布林運算在薄殼上要嘛直接失敗、要嘛產生
    退化幾何；改用「選面換材質」完全不受這個限制，而且窗戶的曲率**直接繼承
    host 原本的曲面**，不會有「窗戶是貼上去的一塊平面、跟周圍鈑金曲率不連續」
    這種一眼假的問題——這正是「AI 車體開窗做得很差」的根本原因：常見做法要嘛
    切一塊平面貼上去（曲率斷裂），要嘛硬做布林在薄殼上炸出破面。

    做法：`bmesh.ops.inset_region()`（不是 `inset_individual()`——這裡要把整片
    選中範圍當**一個**窗戶處理，不是逐面各自獨立內縮；building_lib.generate_facade()
    用 inset_individual 是因為那裡本來就要「每一格網格各自獨立一扇窗」，跟這裡
    「一片範圍是一整扇窗」的需求相反，不要混用）對選中區域的外圍整體內縮出窗框，
    內縮完的面再往內推一點點景深，最後把這片內推後的面材質指向 glass_mat。

    cutter：任意物件，只用它的世界座標包圍盒定義「窗戶範圍」，不需要跟 obj 有
    真正的拓樸/相交關係（一個簡單的 `add_box()` 就夠）——面的中心點落在這個
    範圍內就算選中。非長方形窗戶輪廓（例：跑車異形後窗）用多個 cutter 分次呼叫
    疊加範圍，或呼叫前自己用 `select_verts_by_bounds()` 類似邏輯先篩出更精確的
    面清單（本函式目前只支援長方體範圍篩選，這是刻意的範圍限縮，不是遺漏）。

    glass_mat：材質直接 append 到 obj 現有材質列表（不清空既有材質槽——車體本來
    的烤漆材質要保留，這裡只新增一個玻璃專用槽；已經 append 過同一個 glass_mat
    的話重複呼叫會重用既有索引，不會疊加出重複材質槽）。

    frame_inset（公尺）：窗框寬度，>0 讓玻璃比 cutter 範圍窄一圈，露出一圈原本
    的車身/牆面材質當窗框——真實車窗/建築窗都有窗框或膠條，玻璃直接頂到切割
    邊緣在近景會顯得假。recess（公尺）：玻璃比周圍鈑金/牆面內凹的深度，真實
    車窗通常會比車身外殼略微內凹，這個參數做出這個真實的深度差異，不是純平貼。

    回傳實際處理的面數（0 代表 cutter 範圍完全沒圈到任何面，八成是 cutter
    位置/尺寸不對，不是本函式壞了）。

    已知限制：跟 `building_lib.generate_facade()` 有同一類材質陷阱——**不要**
    在呼叫本函式前後對 obj 呼叫 `obj.data.materials.clear()`，那會把所有面的
    material_index 重設成 0，抹平本函式剛分好的玻璃/車身材質區隔。
    """
    mesh = obj.data
    existing_names = [m.name if m else None for m in mesh.materials]
    if glass_mat.name in existing_names:
        glass_idx = existing_names.index(glass_mat.name)
    else:
        mesh.materials.append(glass_mat)
        glass_idx = len(mesh.materials) - 1

    bpy.context.view_layer.update()
    corners = [cutter.matrix_world @ Vector(c) for c in cutter.bound_box]
    xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
    lo = Vector((min(xs), min(ys), min(zs)))
    hi = Vector((max(xs), max(ys), max(zs)))

    bm = _bm_open(obj)
    mat = obj.matrix_world
    selected = []
    for f in bm.faces:
        c = mat @ f.calc_center_median()
        if lo.x <= c.x <= hi.x and lo.y <= c.y <= hi.y and lo.z <= c.z <= hi.z:
            selected.append(f)
    if not selected:
        _bm_close(bm, obj)
        return 0

    if frame_inset > 0 or recess > 0:
        bmesh.ops.inset_region(bm, faces=selected, thickness=frame_inset,
                               depth=-abs(recess), use_boundary=True)
    for f in selected:
        f.material_index = glass_idx
    _bm_close(bm, obj)
    return len(selected)


def taper(obj, axis: str = 'Y', factor: float = 0.5, pivot: str = 'MIN'):
    """沿 axis 方向做線性收分（scale 隨該軸座標線性插值）——車頭變窄、瓶頸內縮、
    塔身收分都是這個操作。factor：遠端（pivot 對面那端）相對近端的縮放比例
    （1.0=不變，0.5=縮一半，>1=展開變寬）。pivot：'MIN' 或 'MAX'，決定哪一端
    是縮放基準（不動的那一端）。垂直 axis 的兩個軸（例如 axis='Y' 時的 X/Z）
    跟著同比例縮放，維持剖面形狀不失真——縮放以「該斷面自身的外框中心」為基準。
    """
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis.upper()]
    bm = _bm_open(obj)
    coords = [v.co[axis_idx] for v in bm.verts]
    lo, hi = min(coords), max(coords)
    span = (hi - lo) or 1.0
    # Scale the perpendicular axes about THIS part's own cross-section centre, never about
    # the world origin: add_box()/add_cyl() call transform_apply(), which bakes the world
    # location into the mesh (SKILL 8 #9), so a part's mesh coordinates sit wherever the
    # part is. Scaling about the origin also TRANSLATES the cross-section, so the taper
    # displaces the part instead of just narrowing it -- a 26 mm saddle slab centred at
    # z=0.897 was dragged ~430 mm down (to z~0.46) and squashed to ~13.5 mm thick, landing
    # on the rear fender. The object transform stayed identity, so a normal-based check
    # could not see it.
    perp = [i for i in range(3) if i != axis_idx]
    centre = [0.5 * (min(v.co[i] for v in bm.verts) + max(v.co[i] for v in bm.verts))
              for i in perp]
    for v in bm.verts:
        t = (v.co[axis_idx] - lo) / span
        if pivot.upper() == 'MAX':
            t = 1.0 - t
        scale = 1.0 + (factor - 1.0) * t
        for k, i in enumerate(perp):
            v.co[i] = centre[k] + (v.co[i] - centre[k]) * scale
    _bm_close(bm, obj)
    return obj


# ---------------------------------------------------------------- 曲線/桁架（curve/truss）
# 2026-09-09 新增，來源：AURORA LIVE 演唱會舞台參考案例（SKILL.md §10.3）——
# 兩個 box/cyl 硬拼補不到的形狀類別：任意折線路徑上的等截面圓管（霓虹燈管/纜線/扶手/
# 管路），以及兩點間的箱型桁架（舞台/展場/工業構架的標準構件）。

def curve_tube(name: str, points: list, radius: float, mat=None, resolution: int = 3,
               smooth: bool = False) -> bpy.types.Object:
    """沿一串世界座標點串出一根等截面圓管（Curve + bevel_depth，非逐段 box/cyl 硬拼）
    ——霓虹燈管/纜線/扶手/管路這類「路徑是折線或曲線，但截面永遠是圓」的構件，用
    曲線一次成型比逐段接 box/cylinder 精確、也省物件數。
    points：≥2 個 (x,y,z) 世界座標，依序連成路徑。radius：管半徑。resolution：截面圓
    分段數（bevel_resolution，值越大越圓，預設 3≈8 邊形，霓虹燈管建議 4-6）。
    連到目前作用中的 collection（跟 `bpy.ops.mesh.primitive_*_add()` 同一個目標），
    不強制指定路徑，呼叫端場景腳本自己控制 `active`/collection 切換時機。

    smooth（2026-09-10 新增，來源：紅白機參考案例的手把接線 vs 本 skill 紅白機
    v3 事故的接線）：預設 `False` 維持原本的 **POLY spline**（點與點之間是直線硬折，
    要平滑轉角只能多給密集的點，不是靠曲線插值）——霓虹燈管/扶手/管路這類本來就該有
    明確折角、路徑固定的構件用這個。`True` 改用 **BEZIER spline**，每個控制點的
    `handle_left_type`/`handle_right_type` 設 `'AUTO'`（Blender 自動算平滑切線），
    同一串世界座標點會沿途自然彎曲插值，不再是硬折線——電線/纜線/軟管/繩索這類真實
    世界會自然下垂/彎曲的構件用 `smooth=True`。
    v3 事故案例：手把接線只給 3 個「Z 座標單調遞增、Y 座標單調外擴」的控制點，配
    `POLY`（本函式舊行為，等同這裡的預設）+ `resolution=2`，渲出來是一根硬棒筆直
    往上翹，完全不是垂墜的電線；改進後的做法給了 7 個真正描出「先揚起、繞過去、再垂
    落」弧線的控制點，配 BEZIER 自動切線，同一種構件看起來完全不同。**問題的一半是
    點給太少/形狀沒描出真實垂墜弧線，另一半是折線本身的視覺語言就不適合軟性線材**
    ——`smooth=True` 解決後者，但前者（控制點路徑本身要像真的垂墜/繞行，不能單調
    朝同一方向遞增）永遠是呼叫端的責任，不會因為切了 BEZIER 就自動變對。"""
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12 if smooth else 1
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    if smooth:
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(len(points) - 1)
        for pt, co in zip(spline.bezier_points, points):
            pt.co = co
            pt.handle_left_type = 'AUTO'
            pt.handle_right_type = 'AUTO'
    else:
        spline = curve.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for pt, co in zip(spline.points, points):
            pt.co = (*co, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def truss(name: str, a, b, width: float, chord_r: float = 0.045, brace_r: float = 0.023,
         brace_spacing: float = 0.85, mat=None, brace_mat=None, vertices: int = 12) -> list:
    """兩點間的箱型桁架（box truss）——演唱會舞台/展場/工業構架的標準構件：四根
    縱向弦桿（chord）沿正方形截面四角平行延伸，週期性加交叉斜撐（brace）與方形
    框架（frame），不是拿一根粗圓柱充數。
    a/b：桁架兩端世界座標。width：正方形截面邊長。chord_r/brace_r：弦桿/斜撐圓柱
    半徑。brace_spacing：沿長度方向每隔多少公尺放一組斜撐+框架（實戰案例用
    0.85m，跨距越大這個值可以放寬，避免物件數暴增）。mat/brace_mat：弦桿/斜撐材質，
    brace_mat 省略時跟 mat 同材質。回傳所有生成物件的 list（呼叫端視需要自行
    join_into 一個母版，跟 detail_lib 的細節件是同一個模式）。"""
    a_v, b_v = Vector(a), Vector(b)
    d = b_v - a_v
    length = d.length
    n = d.normalized()
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = n.cross(ref).normalized() * width / 2
    v = n.cross(u).normalized() * width / 2
    offsets = [u + v, -u + v, -u - v, u - v]
    parts = []

    def _rod(rname, p1, p2, r, m, verts):
        mid = (p1 + p2) / 2
        depth = (p2 - p1).length
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=mid)
        o = bpy.context.object
        o.name = rname
        o.rotation_euler = (p2 - p1).to_track_quat('Z', 'Y').to_euler()
        if m:
            o.data.materials.append(m)
        return o

    for i, q in enumerate(offsets):
        parts.append(_rod(f'{name}_Chord{i}', a_v + q, b_v + q, chord_r, mat, vertices))
    steps = max(1, int(length / brace_spacing))
    brace_material = brace_mat if brace_mat is not None else mat
    for i in range(steps):
        aa = a_v + d * (i / steps)
        bb = a_v + d * ((i + 1) / steps)
        for j in range(4):
            q, r = offsets[j], offsets[(j + 1) % 4]
            parts.append(_rod(f'{name}_Brace{i}_{j}', aa + q, bb + r, brace_r, brace_material, 8))
            parts.append(_rod(f'{name}_Frame{i}_{j}', aa + q, aa + r, brace_r, brace_material, 8))
    return parts


# ---------------------------------------------------------------- 螺旋彈簧/自由造型平面貼花
# 2026-09-09 新增，來源：BOLT 07 卡通卡丁車參考案例（SKILL.md §10.3）。

def coil_spring(name: str, a, b, coil_radius: float, turns: float, tube_radius: float,
                mat=None, points_per_turn: int = 30) -> object:
    """兩點間的螺旋彈簧（避震器彈簧/線圈）——沿 a→b 軸線參數化算出真正的螺旋路徑，
    再用 `curve_tube()` 一次成型，不是疊一排 torus 假裝彈簧。
    a/b：彈簧兩端世界座標（沿這條軸線螺旋前進）。coil_radius：螺旋半徑（線圈繞多寬）。
    turns：總圈數。tube_radius：彈簧鋼絲本身的粗細。points_per_turn：每圈取樣點數
    （越高越平滑，預設 30 通常夠用，緊湊小彈簧可以拉到 40+）。"""
    a_v, b_v = Vector(a), Vector(b)
    d = b_v - a_v
    axis = d.normalized()
    ref = Vector((0, 1, 0)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u)
    total_points = max(2, int(turns * points_per_turn))
    points = []
    for i in range(total_points + 1):
        t = i / total_points
        angle = t * turns * 2 * math.pi
        center = a_v + d * t
        offset = coil_radius * (u * math.cos(angle) + v * math.sin(angle))
        points.append(tuple(center + offset))
    return curve_tube(name, points, tube_radius, mat)


def flat_decal(name: str, points: list, mat=None) -> object:
    """自由造型平面貼花（車身閃電/隊標/塗裝色塊這類不規則輪廓，非矩形/文字能表達的
    形狀）：給一圈世界座標點（依序連成一個閉合多邊形輪廓，不用自己閉合，函式自動
    首尾相連），直接建一個單面 N-gon——這是 `make_text()`（文字）跟 `box()` 貼片
    （矩形色塊）都做不到的「任意手繪輪廓」類貼花。
    points：≥3 個 (x,y,z) 世界座標，依序排列成輪廓——**貼在彎曲表面上時，每個點的
    座標要自己算到貼合宿主曲面**（例如貼在一個橢球鼻錐上，各點的座標要依橢球方程
    算出對應的表面高度，不能全部給同一個平面座標，否則貼花會浮空或穿模）。單面
    N-gon 沒有厚度，需要立體感時呼叫端可以另外接 Solidify 修飾器，這支只負責形狀。"""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in points], [], [list(range(len(points)))])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------- 相對定位（anchor）
# 2026-09-09 新增，簡化版取自 arXiv 2608.26238《Procedura》論文的 mate-driven placement
# 概念——依實際需求簡化實作出一個初版（零件相對位置的錨點定位）。
#
# 問題：目前所有案例腳本（本 skill 自己的 building_lib.py 也一樣）都是每個 box/cyl
# 呼叫給一組手寫的絕對 (x,y,z) 座標——host 物件的尺寸/位置一旦事後調整，所有靠近它、
# 依附它的物件座標全部要手動重算，這正是元件錯位/漂移類 bug 的根源之一（論文原話：
# 這是「造成漂移的主因」）。論文的完整解法是形式化的「接合面」代數求解
# （`Tj = Fi·Δ(φ)·Fj⁻¹`，處理任意旋轉自由度的機構接合）——這支刻意只做其中最常
# 用、最不複雜的子集：**「取某物件目前包圍盒上的一個具名參考點」**，不解旋轉，
# 夠用本 skill 目前絕大多數「A 貼著/靠著 B 的某個面」場景。真的需要旋轉關節式
# 接合（例如會轉動的鉸鏈）再另外處理，不是這支的範圍。

def bbox_world(obj) -> tuple:
    """回傳 obj 目前世界座標下的包圍盒 (min, max)——所有 anchor()/relative_loc() 的
    共同基礎。逐一把 obj.bound_box 的 8 個局部角點乘 matrix_world 再取極值，不用
    obj.dimensions（那個是局部包圍盒尺寸，物件被 rotation_euler 轉過時不會反映
    真正的世界座標範圍）。"""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def anchor(obj, face: str = 'center', frac=(0.5, 0.5)) -> Vector:
    """讀取 obj 目前的世界座標包圍盒，回傳其上一個具名參考點——**相對定位的核心**：
    下一個物件的座標從這裡「算出來」，不是自己猜一個絕對數字寫死。host 物件之後
    如果尺寸/位置改了，只要重新呼叫 anchor()（腳本重跑一次就會自動重新算），所有
    依附它的物件位置就自動跟著對，不用逐一手動改座標。
    face：'+X'/'-X'/'+Y'/'-Y'/'+Z'/'-Z' 六面之一，或 'center'（包圍盒中心）。
    frac：該面上的滑動位置 (u, v)（沿另外兩軸的 0-1 內插），(0.5, 0.5)=面正中央，
    用來取「面上偏一邊」的點（例如車門把手不在側面正中央，在偏後方 70% 處，就傳
    frac=(0.7, 0.5) 之類，實際對應哪個分量看 face 指定的是哪個軸）。"""
    lo, hi = bbox_world(obj)
    center = (lo + hi) / 2
    if face == 'center':
        return center
    axis_map = {'X': 0, 'Y': 1, 'Z': 2}
    sign = 1 if face[0] == '+' else -1
    axis = axis_map[face[1]]
    other_axes = [a for a in range(3) if a != axis]
    point = [center.x, center.y, center.z]
    point[axis] = hi[axis] if sign > 0 else lo[axis]
    for i, a in enumerate(other_axes):
        point[a] = lo[a] + (hi[a] - lo[a]) * frac[i]
    return Vector(point)


def relative_loc(obj, face: str = 'center', frac=(0.5, 0.5), offset=(0.0, 0.0, 0.0)) -> tuple:
    """`anchor()` 的日常包裝：算出的錨點再疊加一個 (dx, dy, dz) 世界座標偏移，直接
    回傳 tuple，可以原樣餵給 `box()`/`cyl()`/`T.add_box()` 的 loc 參數——這是實際
    寫場景腳本時真正會呼叫的版本，`anchor()` 是給要自己疊加更複雜邏輯的呼叫端用的
    底層版本。用法示例：`box('Handle', SL.relative_loc(door, '+Y', frac=(0.5, 0.3),
    offset=(0, 0.02, 0)), size, mat)`——car 側門把手貼在門的 +Y 面、偏下方 30%
    高度、再往外推 2cm，門的尺寸/位置日後改了，把手位置重跑腳本就自動對。"""
    a = anchor(obj, face, frac)
    return (a.x + offset[0], a.y + offset[1], a.z + offset[2])


def parametric_surface(name: str, u_res: int, v_res: int, fn, mat=None,
                       smooth: bool = True, solidify: float = None) -> object:
    """通用參數曲面 → mesh（來源：雷峰塔參考案例，西湖塔樓翹角屋頂的建法，
    2026-09-09 新增）。`fn(u, v) -> (x, y, z)` 是呼叫端自己給的世界座標函式，
    u/v 各自跑 [0,1]，本函式只管照 (u_res+1)×(v_res+1) 網格取樣、連成四邊面、
    可選 SOLIDIFY 補厚度——不管 fn 內部長什麼樣，圓頂/馬鞍面/翹曲屋頂/自訂曲面
    都是同一套呼叫方式，差別只在 fn 怎麼寫。

    這解決的問題：以前想做「非平面」的曲面（穹頂、翹曲屋頂），得手動算一堆頂點
    座標再 from_pydata，每個形狀重新推一次頂點/面索引邏輯。有了這個函式，重點
    全部移到「設計 fn(u,v) 這個數學式」，網格化的部分不用每次重寫。

    fn 回傳的點如果需要之後在曲面上放裝飾線條/物件（屋脊瓦壟、電纜、接縫），
    直接呼叫同一個 fn() 取樣點餵給 `curve_tube()`/`line`——保證裝飾完全貼合曲面，
    不會跟曲面本身「各算各的」導致穿模或懸空（見 `curved_eave_roof()` 用法示範）。

    solidify：非 None 時加一個 SOLIDIFY modifier（不 apply，呼叫端自己視需要
    apply_all_modifiers）；None 時曲面是零厚度單層面片（適合只當裝飾參考面）。"""
    v, f = [], []
    for j in range(v_res + 1):
        for i in range(u_res + 1):
            v.append(fn(i / u_res, j / v_res))
    for j in range(v_res):
        for i in range(u_res):
            a = j * (u_res + 1) + i
            f.append((a, a + 1, a + u_res + 2, a + u_res + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if solidify is not None:
        mod = o.modifiers.new('Solidify', 'SOLIDIFY')
        mod.thickness = solidify
    return o


def curved_eave_roof(name: str, center, sides: int, ridge_z: float, eave_r: float,
                     rise: float, ridge_r_frac: float = 0.34,
                     eave_curl: float = 0.18, eave_curl_pow: float = 7.0,
                     corner_lift: float = 0.38, corner_pow: float = 5.0,
                     corner_sharp: float = 5.0, mat=None,
                     u_steps: int = 16, v_steps: int = 8, thickness: float = 0.05):
    """東亞式翹角曲面屋頂（來源：雷峰塔參考案例實測驗證優於平面屋頂，
    2026-09-09 新增）——中式/日式/韓式塔樓、亭子、牌樓這類「屋簷角往上翹」的
    屋頂，不是西式人字屋頂（`building_lib.make_pitched_roof()`）能表現的形狀，
    平面斜頂+bevel 頂多做出直線斜面，做不出屋簷角上揚的連續曲面。

    核心數學（`parametric_surface()` 的 fn 範例，直接看這個函式怎麼組出 fn 就懂
    怎麼自己客製）：
    - t∈[0,1]：徑向位置，0=屋脊（最高、最靠中心），1=屋簷邊緣（最低、最外圍）。
      半徑用線性內插 `ridge_r_frac~1.0`，高度用 `rise*(1-t)**2`——平方是為了讓
      屋脊附近曲率變化平緩，接近屋簷才開始明顯往下彎，視覺上更像真實瓦頂的
      弧度而不是一段直線斜面。
    - `eave_curl*t**eave_curl_pow`：整條屋簷邊緣的上揚量，高次冪讓上揚只在
      t 接近 1（屋簷邊緣本身）才出現，屋頂中段幾乎不受影響。
    - `corner_lift*t**corner_pow*abs(2*u-1)**corner_sharp`：**翼角起翹**——
      u∈[0,1] 是同一個多邊形面內的切向位置，0.5=面中央、0/1=面與面交界的角。
      `abs(2u-1)**corner_sharp` 在 u=0.5 時為 0、u=0/1 時為 1，讓額外上揚量
      集中在屋頂的角落，中段幾乎沒有——這正是中式建築屋頂「屋角高高翹起、
      屋脊中段平緩下垂」的視覺特徵，兩個指數（eave_curl_pow/corner_pow/
      corner_sharp）數字越大，曲線越集中在邊緣/角落、中段越平緩；數字越小，
      整條曲線變化越均勻平緩（更接近日式屋頂較收斂的翹度）。

    sides：多邊形邊數（4=攢尖亭、6=六角亭、8=八角塔）。center=(x,y)，
    ridge_z=屋脊最高點世界 Z，eave_r=屋簷邊緣半徑（不含 ridge_r_frac 內縮），
    rise=從屋簷到屋脊的高度差。

    回傳建好的屋頂曲面物件（已 append mat、SOLIDIFY thickness）；呼叫端如果要
    在屋脊/瓦壟加裝飾線條，直接複用本函式內部同一個 `_rp(face, u, t)` 座標公式
    （示範見下方 `curved_eave_roof_ridge_lines()`），不要自己重新估算屋頂曲面
    座標——手估的點幾乎一定跟真正的曲面對不齊，出現裝飾線懸空或穿模。"""
    cx, cy = center

    def _rp(face, u, t):
        a = 2 * math.pi * face / sides
        b = 2 * math.pi * (face + 1) / sides
        radius = eave_r * (ridge_r_frac + (1.0 - ridge_r_frac) * t)
        xx = (1 - u) * math.cos(a) + u * math.cos(b)
        yy = (1 - u) * math.sin(a) + u * math.sin(b)
        zz = (ridge_z - rise) + rise * (1 - t) ** 2 \
            + eave_curl * t ** eave_curl_pow \
            + corner_lift * t ** corner_pow * abs(2 * u - 1) ** corner_sharp
        return (cx + radius * xx, cy + radius * yy, zz)

    v, f = [], []
    for face in range(sides):
        start = len(v)
        for k in range(v_steps + 1):
            for j in range(u_steps + 1):
                v.append(_rp(face, j / u_steps, k / v_steps))
        for k in range(v_steps):
            for j in range(u_steps):
                a = start + k * (u_steps + 1) + j
                f.append((a, a + 1, a + u_steps + 2, a + u_steps + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    mod = o.modifiers.new('Roof thickness', 'SOLIDIFY')
    mod.thickness = thickness
    o['_rp_sides'] = sides  # 供呼叫端事後重建 _rp() 座標時核對 sides 是否一致
    return o


def domed_spoke_ring(name: str, center, axis_normal, up_hint, r_inner: float, r_outer: float,
                     dome_depth: float, count: int, tube_r: float, mat=None,
                     ring_radii: list = None, ring_tube_r: float = None,
                     resolution: int = 3) -> tuple:
    """放射狀穹頂輻條環（風扇/喇叭網罩/傘骨/篩網這類「輻條從中心到邊緣呈拋物線
    深度」的結構，來源：`retro_fan` 參考案例分析，2026-09-10 新增）。

    真實網罩/傘狀結構的輻條**不是平貼一個平面**——中心凹陷（或凸起）、邊緣跟外緣
    夾圈齊平，是一片淺穹頂，不是硬拼出來的貼片。深度公式用拋物線
    `depth(r) = dome_depth * (1 - (r/r_outer)**2)`：`r=r_outer`（最外緣）時深度=0
    （跟外緣夾圈齊平，不會跟夾圈脫節），`r=r_inner`（最靠中心處）深度最大，二次方
    讓曲率在邊緣附近變化平緩、接近中心才明顯內凹/外凸——比每根輻條手動給幾個
    折點更接近真實金屬網罩的弧度，也保證所有輻條共用同一條曲面，不會各自對不齊。

    center=(x,y,z)：穹頂頂點（r=0 處，不一定是輻條實際起點，r_inner 可以 >0 留出
    中心蓋/葉轂的位置）。axis_normal：穹頂朝外的法向量（決定深度累加的方向，例如
    前網罩用 `(0,-1,0)` 朝觀眾凹陷、後網罩用 `(0,1,0)` 朝後凸起）。up_hint：任一
    不與 axis_normal 平行的向量，用來算出輻條所在平面的兩個正交基準軸（跟
    `basis_quat()` 解決的是同一類「已知法向量、還需要另外兩軸」問題，這裡直接
    內部處理，呼叫端不用自己算）。

    count：輻條數量（§15.2 費波那契節奏 34/55/89，或工程慣用偶數）。tube_r：輻條
    圓管半徑（`curve_tube` 截面）。ring_radii：可選，給一串半徑值（例如
    `[0.37,0.59,0.81,1.0]*r_outer`，通常走§15.2 黃金分割或簡單整數比）在對應半徑
    加同心環，同一套拋物線深度公式算 Y，保證跟輻條完全貼合、不會各算各的導致
    環浮在輻條前後方。ring_tube_r 不給則沿用 tube_r。

    回傳 `(spokes, rings)` 兩個 list，呼叫端自行 `join_into`。"""
    n = Vector(axis_normal).normalized()
    u_raw = Vector(up_hint).normalized()
    u = (u_raw - n * u_raw.dot(n))
    if u.length < 1e-6:
        raise ValueError(f"domed_spoke_ring({name}): up_hint 跟 axis_normal 幾乎平行，換一個 up_hint。")
    u = u.normalized()
    right = u.cross(n).normalized()
    c = Vector(center)
    spokes = []
    for i in range(count):
        ang = 2 * math.pi * i / count
        dir2d = right * math.cos(ang) + u * math.sin(ang)
        pts = []
        for j in range(9):
            t = j / 8.0
            r = r_inner + (r_outer - r_inner) * t
            depth = dome_depth * (1.0 - (r / r_outer) ** 2)
            pts.append(tuple(c + dir2d * r + n * depth))
        spokes.append(curve_tube(f"{name}_Spoke{i:03d}", pts, tube_r, mat=mat, resolution=resolution))
    rings = []
    if ring_radii:
        rr = ring_tube_r if ring_tube_r is not None else tube_r
        for k, r in enumerate(ring_radii):
            depth = dome_depth * (1.0 - (r / r_outer) ** 2)
            ring_pts = [tuple(c + (right * math.cos(a) + u * math.sin(a)) * r + n * depth)
                       for a in (2 * math.pi * m / 96 for m in range(97))]
            rings.append(curve_tube(f"{name}_Ring{k:02d}", ring_pts, rr, mat=mat, resolution=resolution))
    return spokes, rings


def swept_blade(name: str, root_r: float, tip_r: float, axis_center, phase_deg: float,
                half_width_fn, sweep_fn=None, twist_fn=None, thickness: float = 0.01,
                bevel_width: float = 0.002, mat=None, radial_res: int = 20,
                chord_res: int = 24, plane: str = "XZ") -> object:
    """扭掠扇葉/螺旋槳葉片（風扇/螺旋槳/渦輪這類「沿半徑方向同時有掃掠角+弦寬+
    扭轉」的曲面葉片，來源：`retro_fan` 參考案例分析，2026-09-10 新增）
    ——取代「一片矩形/梯形扭轉幾度」的平板做法：真實葉片剖面沿半徑方向弦寬會漸縮、
    掃掠角會漸增，不是均勻扭轉的平板，做出來的立體感/真實感差距很大。

    半徑方向 `t∈[0,1]`（0=葉根 `root_r`，1=葉尖 `tip_r`）同時取樣三個呼叫端自訂的
    函式：`half_width_fn(t)`——葉片半寬（弦寬的一半，決定這個半徑處葉片多寬）；
    `sweep_fn(t)`（可選，預設 0）——葉片剖面在這個半徑處额外偏轉的角度（弧度），
    模擬螺旋槳/風扇葉片沿半徑方向漸增的掃掠感；`twist_fn(t)`（可選，預設 0）——
    這個半徑處剖面沿葉片自身平面法向的额外扭轉（弧度），模擬攻角隨半徑變化。
    三個函式都只是「輸入 t、回傳一個數字」，呼叫端自己決定曲線形狀（線性/正弦/
    冪次都可以），本函式只管照這三個函式的取樣結果組出網格——跟 `parametric_
    surface()` 是同一種「呼叫端給數學式、函式管網格化」分工，只是這裡專門處理
    「徑向葉片」這個更窄但更常見的形狀類別，呼叫端不用自己重新推一次頂點/面
    索引邏輯。

    axis_center=(x,y,z)：葉片旋轉軸（葉轂中心）。phase_deg：這片葉片繞軸的角度
    （多片葉片時，每片傳不同的 phase_deg 做圓周陣列，不要各自複製貼上再手動
    改角度）。plane：葉片所在的旋轉平面（'XZ'=繞 Y 軸旋轉的葉片，例如桌扇正面
    朝 -Y 時葉片在 XZ 平面內；'XY'=繞 Z 軸；'YZ'=繞 X 軸），決定 `phase_deg` 實際
    對應哪兩個世界軸。

    建出的曲面先 `SOLIDIFY`（`thickness`）給厚度、再 `BEVEL`（`bevel_width`）收邊，
    两者都直接 apply（回傳的物件是已經有厚度跟導角的實體，不是還帶著待 apply
    的 modifier）。"""
    axis_map = {"XZ": (0, 2, 1), "XY": (0, 1, 2), "YZ": (1, 2, 0)}
    if plane not in axis_map:
        raise ValueError(f"swept_blade({name}): plane={plane!r} 只接受 XZ/XY/YZ。")
    ia, ib, ic = axis_map[plane]
    phase = math.radians(phase_deg)
    cx = Vector(axis_center)
    sweep_fn = sweep_fn or (lambda t: 0.0)
    twist_fn = twist_fn or (lambda t: 0.0)
    v, f = [], []
    for i in range(radial_res + 1):
        t = i / radial_res
        r = root_r + (tip_r - root_r) * t
        half = half_width_fn(t)
        sweep = sweep_fn(t)
        twist = twist_fn(t)
        for j in range(chord_res + 1):
            q = 2.0 * j / chord_res - 1.0  # -1..1 across the chord
            a = phase + sweep + q * half + twist * q
            p = [0.0, 0.0, 0.0]
            p[ia] = r * math.cos(a)
            p[ib] = r * math.sin(a)
            p[ic] = 0.0
            v.append((cx.x + p[0], cx.y + p[1], cx.z + p[2]))
    for i in range(radial_res):
        for j in range(chord_res):
            a = i * (chord_res + 1) + j
            f.append((a, a + 1, a + chord_res + 2, a + chord_res + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    sol = o.modifiers.new("Blade thickness", "SOLIDIFY")
    sol.thickness = thickness
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=sol.name)
    if bevel_width > 0:
        bev = o.modifiers.new("Blade edge", "BEVEL")
        bev.width = bevel_width
        bev.segments = 2
        bpy.ops.object.modifier_apply(modifier=bev.name)
    return o


def flat_ring(name: str, center, axis_normal, up_hint, r_inner: float, r_outer: float,
             thickness: float, mat=None, segments: int = 96) -> bpy.types.Object:
    """扁平環形量體（錶圈/鏡片框/輪圈/喇叭盆邊這類「內外徑+厚度」的環狀薄片，
    來源：`mechanical_watch` 參考案例分析，2026-09-10 新增——原始
    寫法固定沿 Z 軸手算四圈頂點，這裡改成跟 `domed_spoke_ring()` 同一套
    axis_normal/up_hint 方向慣例，可用在任意朝向，不限水平面）。

    跟 `detail_lib.knurl_ring()`（滾花環，貼在既有量體表面的裝飾細節）不是同一類
    工具——這支是量體本身：內外徑之間夾出一圈實心環帶，沿 axis_normal 方向有
    真實厚度（內壁+外壁+兩端面共 4 圈面），適合當獨立物件（錶圈、鏡頭卡口環、
    喇叭紙盆外緣、輪圈胎唇），不是貼在別的物件表面的紋理。

    center=(x,y,z)：環的中心。axis_normal：環的法向（厚度方向）。up_hint：任一
    不與 axis_normal 平行的向量，純粹決定環的角度取樣起點，不影響環本身的旋轉
    對稱外觀（跟其他物件對齊時才需要在意）。r_inner/r_outer：內/外半徑。
    thickness：沿 axis_normal 的厚度，環以 center 為中心對稱分布（前後各
    thickness/2）。"""
    n = Vector(axis_normal).normalized()
    u_raw = Vector(up_hint).normalized()
    u = (u_raw - n * u_raw.dot(n))
    if u.length < 1e-6:
        raise ValueError(f"flat_ring({name}): up_hint 跟 axis_normal 幾乎平行，換一個 up_hint。")
    u = u.normalized()
    right = u.cross(n).normalized()
    c = Vector(center)
    half = thickness / 2.0
    N = segments
    v = []
    for zz, r in ((-half, r_inner), (-half, r_outer), (half, r_inner), (half, r_outer)):
        for i in range(N):
            a = 2 * math.pi * i / N
            p = c + (right * math.cos(a) + u * math.sin(a)) * r + n * zz
            v.append(tuple(p))
    f = []
    for i in range(N):
        j = (i + 1) % N
        f.append((i, j, N + j, N + i))               # 底面（環形貼面，朝 -axis_normal）
        f.append((2 * N + i, 3 * N + i, 3 * N + j, 2 * N + j))  # 頂面（朝 +axis_normal）
        f.append((i, 2 * N + i, 2 * N + j, j))        # 內壁
        f.append((N + i, N + j, 3 * N + j, 3 * N + i))  # 外壁
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    bev = o.modifiers.new('Ring edge', 'BEVEL')
    bev.width = min(0.007, thickness * 0.3)
    bev.segments = 2
    return o


def domed_disc(name: str, center, axis_normal, up_hint, radius: float, dome_height: float,
               mat=None, rings: int = 14, segments: int = 64, dome_power: float = 2.0,
               solidify: float = None) -> object:
    """實心穹頂圓盤（錶鏡/鏡頭蓋/圓頂燈罩這類「邊緣固定貼合外框、表面微凸」的
    透明/半透明圓盤，來源：機械錶案例補強，見 `assets/anatomy/watch.md`，
    2026-09-10 新增）——直接組 `parametric_surface()` 的 fn 再呼叫它，不是重新
    手刻網格。

    跟 `domed_spoke_ring()` 不是同一類：那支只生成放射輻條+可選同心環（線狀
    構件，適合網罩/傘骨這類「看得穿」的鏤空結構）；這支是**連續填滿的曲面本身**
    （適合錶鏡/鏡片這類需要真的擋住後方、有折射效果的透明實面）。深度公式沿用
    同一條拋物線慣例：`depth(r) = dome_height * (1 - (r/radius)**dome_power)`，
    `r=radius`（最外緣）時深度=0，貼齊外框（錶圈/鏡頭卡口環）不會跟外框脫節，
    `r=0`（正中心）凸起量最大。

    真實錶鏡/光學鏡片幾乎都是微凸弧面（哪怕肉眼看像平的）——完全平面的透明圓盤
    在高光/環境反射下會顯得死板，微凸弧面才有真實鏡面該有的連續高光滑動感跟
    輕微放大/變形效果。`dome_height` 抓半徑的 5-15%（藍寶石錶鏡常見弧度，> 20%
    會開始像放大鏡）。`dome_power`：2.0=標準拋物面；>2 邊緣更平、只有中心明顯
    凸起；<2 反之（整片弧度更均勻）。

    center=(x,y,z)：圓盤中心（在最凸起處，即 r=0 那一點）。axis_normal：凸起
    方向（法向）。up_hint：任一不與 axis_normal 平行的向量，只決定網格角度
    取樣起點，不影響外觀旋轉對稱性（同 `domed_spoke_ring()` 慣例）。rings/
    segments：徑向/周向網格密度。solidify：給值則加實際厚度（更真實的折射
    效果，但增加面數/渲染成本），預設 None＝零厚度單層面（`make_glass()`
    的 Transmission 對單層面已經足夠表現「看起來是玻璃」的效果，多數情境
    夠用，不強制要真厚度）。"""
    n = Vector(axis_normal).normalized()
    u_raw = Vector(up_hint).normalized()
    u = (u_raw - n * u_raw.dot(n))
    if u.length < 1e-6:
        raise ValueError(f"domed_disc({name}): up_hint 跟 axis_normal 幾乎平行，換一個 up_hint。")
    u = u.normalized()
    right = u.cross(n).normalized()
    c = Vector(center)

    def fn(uu, vv):
        r = uu * radius
        a = vv * 2 * math.pi
        depth = dome_height * (1.0 - uu ** dome_power)
        p = c + (right * math.cos(a) + u * math.sin(a)) * r + n * depth
        return tuple(p)

    return parametric_surface(name, rings, segments, fn, mat=mat, smooth=True, solidify=solidify)


def gear_wheel(name: str, center, axis_normal, up_hint, radius: float, teeth: int,
              face_width: float, mat=None, root_ratio: float = 0.86,
              hub_r: float = None, hub_depth: float = None, spoke_count: int = 0,
              spoke_r: float = None, spoke_mat=None, bevel_width: float = 0.0015) -> tuple:
    """真實輪齒外形的齒輪片（時鐘/鐘錶機芯/齒輪箱這類「可見齒輪」的通用建構件，
    來源：`mechanical_watch` 參考案例分析，2026-09-10 新增）——
    取代「一個圓柱充當齒輪」的做法：沿圓周在 `root_ratio*radius`（齒根）跟
    `radius`（齒頂）之間交替取值，做出真正的梯形輪齒剪影，近景特寫看得出齒形，
    不是一圈光滑邊緣充數。**這是外觀導向的靜態齒輪，齒形是簡化梯形、不是嚙合
    精度的漸開線齒形，不能用來模擬真實咬合運動**（原案例 README 也明講「靜態
    展示模型，齒輪配置以視覺效果為主，未模擬可運作機芯」，見 `assets/anatomy/
    watch.md`）。

    center/axis_normal/up_hint：同 `domed_spoke_ring()` 的方向慣例（axis_normal=
    齒輪厚度方向/轉軸方向，up_hint 只決定齒的角度取樣起點，不影響外觀旋轉對稱
    性）。radius：齒頂半徑。teeth：齒數。face_width：沿 axis_normal 的齒輪厚度。
    root_ratio：齒根半徑=`radius*root_ratio`（0.82-0.90 常見，值越小齒縫越深）。

    hub_r/hub_depth：給值則在中心加一段沿 axis_normal 凸出的軸座圓管（放齒輪
    軸承/寶石軸承的位置，見 `anatomy/watch.md` 寶石軸承段）；不給則只回傳齒盤
    本體，呼叫端自己疊軸座。spoke_count：給值 >0 則從中心（或 hub_r 外緣）往
    齒根內緣放射 spoke_count 根輻條（`curve_tube`，粗細用 `spoke_r`，材質
    `spoke_mat` 不給則沿用 `mat`）——鐘錶/機械齒輪常見鏤空放射輻條盤面，不是
    實心圓餅。

    回傳 `(gear_obj, hub_obj_or_None, spokes_list)`。"""
    n = Vector(axis_normal).normalized()
    u_raw = Vector(up_hint).normalized()
    u = (u_raw - n * u_raw.dot(n))
    if u.length < 1e-6:
        raise ValueError(f"gear_wheel({name}): up_hint 跟 axis_normal 幾乎平行，換一個 up_hint。")
    u = u.normalized()
    right = u.cross(n).normalized()
    c = Vector(center)
    half = face_width / 2.0
    root_r = radius * root_ratio
    N = teeth * 4
    v = []
    for zz in (-half, half):
        for i in range(N):
            a = 2 * math.pi * i / N
            r = radius if (i % 4) in (1, 2) else root_r
            p = c + (right * math.cos(a) + u * math.sin(a)) * r + n * zz
            v.append(tuple(p))
    f = []
    for i in range(N):
        j = (i + 1) % N
        f.append((i, j, N + j, N + i))  # 齒形外緣側面
    for side, base in ((0, 0), (1, N)):
        zz = -half if side == 0 else half
        v.append(tuple(c + n * zz))
        center_idx = len(v) - 1
        for i in range(N):
            j = (i + 1) % N
            f.append((center_idx, j + base, i + base) if side == 0 else (center_idx, i + base, j + base))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    if bevel_width > 0:
        bev = o.modifiers.new('Gear tooth edge', 'BEVEL')
        bev.width = bevel_width
        bev.segments = 2

    hub = None
    if hub_r and hub_depth:
        hub = curve_tube(f"{name}_Hub", [tuple(c - n * hub_depth / 2), tuple(c + n * hub_depth / 2)], hub_r, mat=mat)

    spokes = []
    if spoke_count > 0:
        sr = spoke_r if spoke_r is not None else face_width * 0.35
        smat = spoke_mat if spoke_mat is not None else mat
        inner_r = hub_r if hub_r else root_r * 0.15
        for i in range(spoke_count):
            a = 2 * math.pi * i / spoke_count
            dir2d = right * math.cos(a) + u * math.sin(a)
            p0 = c + dir2d * inner_r
            p1 = c + dir2d * (root_r * 0.92)
            spokes.append(curve_tube(f"{name}_Spoke{i:02d}", [tuple(p0), tuple(p1)], sr, mat=smat))
    return o, hub, spokes


def basis_quat(x_dir, y_dir, z_dir) -> object:
    """由三個世界座標方向向量（局部 X/Y/Z 軸各自要指向哪個世界方向）組出旋轉
    四元數（2026-09-10 新增，來源：雷峰塔匾額實測事故）——貼牆招牌/鏡子/沿切線
    平躺的橫桿這類「已知量體的寬/高/厚要分別對齊哪個世界方向」的定位需求，
    不要手動 `Matrix((x_dir, y_dir, z_dir)).to_quaternion()`。

    **這個坑真的有人踩過**：`mathutils.Matrix((a, b, c))` 是拿 a/b/c 當「列」
    （row）組矩陣，但 Blender 物件的旋轉矩陣要求 a/b/c 是「行」（column）——
    局部 X 軸在世界座標的方向要放在矩陣第一「行」，不是第一「列」。旋轉矩陣是
    正交矩陣，轉置剛好等於反矩陣，所以拿 rows 直接組出來的四元數不是隨便錯，
    是精確地把整個旋轉**反著做**，實測案例（雷峰塔匾額，`Matrix((t_dir, up,
    n_vec)).to_quaternion()`）：招牌整片歪斜貼歪、邊框有兩條變成穿過門洞的
    斜條狀物，肉眼完全看不出「差在哪」，因為量體本身沒錯、位置也沒錯，只有
    朝向被鏡射/反轉。

    本函式內部正確地轉置後再取四元數，呼叫端只要保證 x_dir/y_dir/z_dir 三者
    互相垂直（不驗證，呼叫端自己算好，例如 `y_dir = z_dir.cross(x_dir)`）。"""
    m = Matrix((tuple(x_dir), tuple(y_dir), tuple(z_dir))).transposed()
    return m.to_quaternion().normalized()


def tapered_rod(name: str, a, b, r1: float, r2: float, mat=None, verts: int = 24) -> object:
    """單一椎狀量體做出兩端粗細不同的桿（車製家具腿/欄杆望柱/瓶頸這類天然帶
    椎度的桿件，來源：木質閱讀角參考案例椅腳/桌腳）。跟 `curve_tube()`
    的差別：`curve_tube()` 是等截面圓管沿折線路徑，這支是兩點間直線、但半徑
    從 `r1`（a 端）線性過渡到 `r2`（b 端）——真實車製木腿/欄杆望柱幾乎都不是
    等粗圓柱，一支 primitive 就地做出椎度比事後再用 `taper()` 修飾器簡單。"""
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=d.length, location=tuple((a + b) / 2))
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    if mat:
        o.data.materials.append(mat)
    return o


def radial_dish(name: str, center, rings: int, segments: int, profile_fn, mat=None,
                smooth: bool = True) -> object:
    """極座標網格（碗/鞍形座椅面/圓盤這類從中心向外輻射的曲面，來源：
    木質閱讀角參考案例溫莎椅鞍形椅面）——跟 `parametric_surface()` 是同一類「先寫
    profile_fn 數學式、本函式只管網格化」的分工，差別是這支走**極座標**（中心
    一點往外，適合圓形/超橢圓輪廓的碗、盤、鞍形椅面），`parametric_surface()`
    走**矩形 u,v 網格**（適合屋頂/布料這類本來就是四邊形展開的曲面）——輪廓是
    「從一個中心點向外擴散」就用這支，是「兩個獨立方向各自展開」就用那支。

    `profile_fn(radius_frac, angle_rad) -> (x, y, z)`：呼叫端自訂形狀，
    `radius_frac` 從 0（中心）到 1（邊緣），`angle_rad` 是極角——超橢圓輪廓
    範例：`x = center[0] + copysign(abs(cos(a))**0.52, cos(a)) * rx * r`
    （指數 <1 讓輪廓比純橢圓更方，見鞍形椅面案例）。中心點另外算一次
    （radius_frac=0 通常退化，profile_fn 需自行處理 r=0 的情況）。"""
    v = [profile_fn(0.0, 0.0)]
    f = []
    for k in range(1, rings + 1):
        r = k / rings
        for i in range(segments):
            a = i * 2 * math.pi / segments
            v.append(profile_fn(r, a))
    for i in range(segments):
        f.append((0, 1 + i, 1 + (i + 1) % segments))
    for k in range(rings - 1):
        for i in range(segments):
            a = 1 + k * segments + i
            b = 1 + k * segments + (i + 1) % segments
            f.append((a, b, b + segments, a + segments))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def lathe(name: str, profile_fn, z_list: list, segments: int = 48, mat=None) -> object:
    """車床（surface of revolution）：沿 Z 軸把 `profile_fn(z) -> radius` 繞一圈
    revolve 成實體（來源：棒球棍參考案例驗證過的技法，球棒的
    球形握把/收分握柄/球棒端頭全部是這樣車出來的，不是拼接量體）。適合任何
    「繞單一軸旋轉對稱」的造型：球棒/球桿、瓶身、車削桌腳/欄杆望柱、保齡球瓶、
    燈座、花瓶、旋鈕。**不對稱剖面（例如車體）不適用，改用 `profile_loft()`**。

    `profile_fn(z) -> float`（該高度的半徑）——多段造型（握把→收分→本體→頭部）
    建議每段各自用 smoothstep 過渡（`t*t*(3-2*t)`，零斜率兩端），讓段與段之間
    相切連續、渲染看不出接縫，不要用線性內插直接銜接（會有可見的折線稜角）。

    `z_list`：取樣站高度清單，曲率大的區域（收分、圓頭）建議加密取樣，直線
    區段可以稀疏——不要求等間距。首尾兩端自動封面（三角扇）。"""
    verts, faces, rings = [], [], []
    for z in z_list:
        r = profile_fn(z)
        idx = []
        for k in range(segments):
            a = 2.0 * math.pi * k / segments
            idx.append(len(verts))
            verts.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(idx)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(segments):
            k2 = (k + 1) % segments
            faces.append((A[k], A[k2], B[k2], B[k]))
    c0 = len(verts)
    verts.append((0.0, 0.0, z_list[0]))
    c1 = len(verts)
    verts.append((0.0, 0.0, z_list[-1]))
    for k in range(segments):
        k2 = (k + 1) % segments
        faces.append((c0, rings[0][k2], rings[0][k]))
        faces.append((c1, rings[-1][k], rings[-1][k2]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def lathe_profile(name: str, points: list, segments: int = 64, mat=None,
                  center=(0.0, 0.0, 0.0), cap_start: bool = True,
                  cap_end: bool = True) -> object:
    """開放剖面路徑車床（surface of revolution，剖面沿任意路徑排列、允許路徑反折——
    取代 `lathe()` 的「profile_fn(z)->radius 高度單值函數」限制，來源：`ramen_yatai`
    參考案例逆向分析，2026-09-10 新增，見 `assets/anatomy/vessel.md`）。

    `lathe()` 的剖面是高度的函數，每個 z 只能對應一個半徑，做得出球棒/瓶身這類
    **實心**迴轉體，但做不出碗/杯/花瓶/捲邊鍋沿這類**雙層中空**容器——真實碗的
    剖面是沿外壁往上到碗口、翻過邊緣、再沿內壁往下收回中心，同一個高度上外壁
    跟內壁是兩個不同半徑，`profile_fn(z)` 這個介面本身就表達不出這種「路徑會
    反折」的形狀。

    這支改吃一串 `(r, z)` 點（沿任意路徑排列，r/z 都不要求單調，可以忽大忽小、
    忽升忽降），依序繞 Z 軸旋轉、逐段連成環帶——剖面在紙上怎麼畫（沿外壁上去、
    翻邊、沿內壁下來、收到底部中心），點列就怎麼給，不用拆成「外壁一段 z 函數
    +內壁另一段 z 函數」兩次呼叫再自己手動拼接兩片曲面。

    points：`[(r0,z0), (r1,z1), ...]`（局部座標，r=到旋轉軸的距離，z=沿軸高度），
    至少 2 點。center：整條剖面的世界座標偏移。cap_start/cap_end：路徑兩端的
    r 若不是 0（沒有自然收攏到軸心），要不要在該端加三角扇封面補成實心面——
    r≈0 的一端本來就會退化成一個點、天然封閉（跟 `domed_disc()`/`gear_wheel()`
    的極點處理同一套邏輯），封面與否沒有視覺差異；只有「端點半徑明顯不是 0」
    的開放剖面（例如只想露出容器外壁、故意不建看不到的底面，見 `anatomy/
    vessel.md`「關鍵技術決策#3」的取捨判準）才需要主動關閉對應的 cap。"""
    if len(points) < 2:
        raise ValueError(f"lathe_profile({name}): points 至少要 2 個 (r,z) 點。")
    cx, cy, cz = center
    P = len(points)
    v = []
    for r, z in points:
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            v.append((cx + r * math.cos(a), cy + r * math.sin(a), cz + z))
    f = []
    for j in range(P - 1):
        base_a, base_b = j * segments, (j + 1) * segments
        for i in range(segments):
            k = (i + 1) % segments
            f.append((base_a + i, base_a + k, base_b + k, base_b + i))

    def _cap(point_index, flip):
        r, z = points[point_index]
        if abs(r) < 1e-9:
            return
        v.append((cx, cy, cz + z))
        center_idx = len(v) - 1
        base = point_index * segments
        for i in range(segments):
            k = (i + 1) % segments
            f.append((center_idx, base + k, base + i) if flip else (center_idx, base + i, base + k))

    if cap_start:
        _cap(0, flip=False)
    if cap_end:
        _cap(P - 1, flip=True)
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Pole vertices at a capped r≈0 end are `segments` distinct-but-coincident verts (same
    # pattern as domed_disc()/gear_wheel()), not merged — remove_doubles welds them into one so
    # the cap is a real watertight n-gon-fan instead of leaving `segments` zero-length boundary
    # edges (probe-verified: without this, a capped bowl profile reports 48 non-manifold edges
    # for segments=48, all zero-length at the exact same point, invisible in render but a real
    # topology defect for any downstream boolean/export use).
    bpy.ops.mesh.remove_doubles(threshold=1e-7)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return o


def profile_loft(name: str, y_list: list, section_fn, mat=None, cap_ends: bool = True,
                 smooth: bool = True) -> tuple:
    """車體式縱向 loft——跟 `lathe()` 同一個「先寫剖面函式、本函式只管網格化」家族，
    差別是 `lathe()` 繞軸旋轉（限旋轉對稱造型），這支沿指定軸把一系列**不對稱**
    2D 剖面串起來（來源：車體/巴士底盤這類「有平底、圓頂、左右不必然對稱」的
    量體，SKILL.md §13.10 規則 8 記錄過的公車窗戶事故就是這類車身缺一個正式
    共用函式，各任務各自土法煉鋼寫 loft、車身跟面板兩邊剖面對不上）。

    `section_fn(y) -> [(x, z), ...]`：該 y 站的剖面輪廓點列（同一個拓樸順序，
    例如逆時針：左下→左上→右上→右下→回到左下，**每一站點數必須相同**，本函式
    按索引直接對應連相鄰站——點數不一致會連出扭曲面，呼叫端自己保證一致）。

    **回傳 `(obj, section_fn)`，不是只回傳 obj**——呼叫端幫車身貼窗戶/飾條/
    保桿這類附加面板時，一律呼叫回傳的 `section_fn(y)` 查該 y 位置車身的
    真實剖面範圍，不要另外憑經驗猜一個固定寬度常數：車身本體跟面板兩者的
    「真相源」統一成同一個函式，才不會出現面板比車身實際外緣寬、懸空凸出
    車殼的錯位（公車窗戶事故的根因）。"""
    verts, faces, rings = [], [], []
    for y in y_list:
        pts = section_fn(y)
        idx = []
        for x, z in pts:
            idx.append(len(verts))
            verts.append((x, y, z))
        rings.append(idx)
    n = len(rings[0])
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((A[k], A[k2], B[k2], B[k]))
    if cap_ends:
        faces.append(tuple(rings[0]))
        faces.append(tuple(reversed(rings[-1])))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o, section_fn


def rotation_pivot(name: str, loc, children: list, parent_pivot=None,
                   axis: str = None, limit_deg: tuple = None) -> object:
    """可轉動零件的樞軸 EMPTY（來源：BOLT 07 卡丁車參考案例；2026-09-10
    正式收進函式，取代之前只在文件裡手把手教的寫法）——輪子/車門/砲塔/方向盤
    這類「這一整組東西繞一根軸轉」的零件，組裝時把它們全部 `parent` 給一個
    立在旋轉軸心的 EMPTY，之後只轉這個 EMPTY 的本地軸就好，不用逐一計算每個
    子零件自己的旋轉中心；匯出 GLB 給遊戲引擎/動畫軟體用時，這個父子階層會
    被完整保留，引擎才知道「轉哪個節點=轉整組輪子」。

    `parent_pivot`：可疊套，做「轉向+自轉」這類複合旋轉（見下方範例）——
    先建轉向樞軸（轉向軸心，垂直軸），children 只放自轉樞軸本身（不是輪胎
    mesh），再建自轉樞軸（車軸中心，水平軸，`parent_pivot=轉向樞軸`），children
    放真正的輪胎/輪框 mesh。階層長這樣：`SteerPivot → SpinPivot → 輪胎/輪框`，
    轉向時轉 `SteerPivot`（連帶整組跟著轉向），自轉時只轉 `SpinPivot`（不影響
    轉向角度）——跟真實汽車轉向柱+輪軸是同一套機構邏輯，不是憑空設計的階層。

    `axis`/`limit_deg`（2026-09-10 新增）：純標記用途，不影響幾何或實際能轉多少
    度（Blender 本身不會強制限制）——寫成物件自訂屬性（`axis`/`limit_deg_min`/
    `limit_deg_max`），glTF 匯出器預設會把自訂屬性原樣帶進 `extras` 欄位，遊戲
    引擎讀 GLB 時可以直接查這個節點該繞哪一軸轉、轉幾度是合理範圍（例如方向盤
    轉向 `axis='Z', limit_deg=(-35, 35)`），不用另外維護一份文件對照表。

    回傳建好的樞軸 EMPTY，呼叫端存起來供之後動畫/腳本控制旋轉用。"""
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.empty_display_size = 0.1
    if axis is not None:
        o["axis"] = axis
    if limit_deg is not None:
        o["limit_deg_min"], o["limit_deg_max"] = limit_deg
    if parent_pivot is not None:
        o.parent = parent_pivot
        o.matrix_parent_inverse = parent_pivot.matrix_world.inverted()
    bpy.context.view_layer.update()
    for c in children:
        c.parent = o
        c.matrix_parent_inverse = o.matrix_world.inverted()
    return o


def rounded_box(name: str, size: tuple, loc: tuple, corner_r: float, edge_r: float = 0.0005,
                axis: str = 'Z', mat=None, corner_segments: int = 10, edge_segments: int = 2) -> object:
    """雙層選邊導角量體——corner_r 只導「沿 axis 方向的四條角柱邊」（大半徑，做出
    圓潤的轉角柱），edge_r 再對全部邊補一層極小導角（消除剩餘硬邊的刻面感）。
    跟 `add_box(bevel=)` 的差別：那支只有一個統一半徑套全部 12 條邊，做不出
    「轉角比上下邊緣更圓」這種常見消費性電子產品輪廓（iPod/手機/遙控器一類——
    四個角是大圓角柱，頂面/底面本身邊緣只是輕微倒角，不是跟角柱同樣的弧度）。

    `axis`：角柱沿哪個局部軸（多半是機身厚度方向以外的長軸，例如手機/播放器
    直放時通常是 'Z'）。兩階段各自的分段數/半徑都可調，corner_segments 建議
    ≥8 讓大圓角柱夠平滑，edge_segments 給 2 就夠（只是消刻面感不是造型）。

    **`corner_r` 務必小於量體最薄那一軸尺寸的一半**（實測抓到的真坑：11mm 厚
    的量體傳 `corner_r=6mm` 會讓相鄰角柱的倒角面自己互相交疊，即使兩個
    bevel 呼叫都已經帶 `clamp_overlap=True`，交疊嚴重到還是會產生一整排
    細碎的皺褶面，不是平滑圓角柱——`clamp_overlap` 防的是「單一半徑選過大
    導致自我重疊」，防不了「兩個獨立角柱本來就離太近」這種跨物件層級的衝突，
    呼叫端自己要先檢查比例合不合理。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.edges.ensure_lookup_table()
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis.upper()]
    other = [i for i in range(3) if i != axis_idx]
    corner_edges = [e for e in bm.edges
                    if all(abs(e.verts[0].co[i] - e.verts[1].co[i]) < 1e-9 for i in other)]
    if corner_r > 0 and corner_edges:
        bmesh.ops.bevel(bm, geom=corner_edges, offset=corner_r, segments=corner_segments,
                        affect='EDGES', clamp_overlap=True)
    if edge_r > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=edge_r, segments=edge_segments,
                        affect='EDGES', clamp_overlap=True)
    bm.to_mesh(o.data)
    bm.free()
    if mat:
        o.data.materials.append(mat)
    for f in o.data.polygons:
        f.use_smooth = True
    o.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    return o
