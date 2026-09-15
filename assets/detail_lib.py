# KEYWORDS: blender, bpy, detail, 細節庫, detail_lib, 滾花, 防滑紋, 螺絲, 接縫, 3D文字, knurl, 凍結模組
"""detail_lib.py — 幾何細節生成函數庫（凍結模組，與 mat_lib.py 同級）。

解決「模型正確但平淡」問題：轉盤/鈕/握把類零件必須有微觀起伏（滾花、防滑紋、刻度刻痕），
純光滑圓柱 = 塑膠感（Round 9 使用者實評：轉盤應有凹凸線條）。

用法（§16.1 場景包）：copy_skill_resource_native 取出到 .capybala/test-scripts/detail_lib.py
（與 build_template.py 同層），geometry.py 的 make_xxx() 在母版合併前呼叫本 lib 的
細節函數，細節件與母版 join 成單一物件（保持 §14 母版=1 的原則，不炸實例數）。
匯入慣例：`import detail_lib as DL`（呼叫 `DL.knurl_ring(...)` 等）——2026-09-08 新增
明確建議別名，避免各場景腳本各自發明單字母別名（例如 `D`）跟同檔案的比例常數
（店面深度等常見縮寫也是 `D`）撞名，便利商店輪事故正是這樣：`D` 同時被「深度」常數
與本模組別名占用，其中一個被靜默覆蓋，改名花了 3 個回合才清乾淨殘留引用。

座標公約：所有細節函數在【世界座標】作業——參數（radius/z_center/z_top/origin）與回傳的
細節件都是世界座標，呼叫者負責把宿主放到正確位置，細節件再 join 進宿主。
FIX 2026-09-14（汽車底盤事故，案例目錄 C:\\AI\\CAR-PARTS）：本段原本寫「所有細節函數在局部座標作業」，
與實作矛盾——`knurl_ring()`/`dial_grooves()` 的徑向中心硬寫在世界原點，宿主只要不在原點
（實測受害者：煞車油壺蓋、水箱蓋、加油蓋三件的滾花環）整圈細節就靜默留在原點，join 進宿主
後變成散在原點附近的碎塊，渲染前的所有斷言都過、只有肉眼看得出來。修正：兩支函式新增
`center=` 徑向中心參數（axis='Z' 時是 (x,y)、axis='Y' 時是 (y,z)），不給時自動取宿主世界
包圍盒中心，明給的值與宿主軸心差 > `center_tol`（預設 5mm）直接 fail。
細節件一律相對「給定的宿主面/軸」偏移，凸出量 ≥0.3mm（防共面 §8#11）。
命名：細節件用宿主名 + 細節後綴（_Knurl/_Groove/_Screw），join 前存在、join 後消失。
依賴 build_template 的 log/fail；獨立使用時自動降級。
驗證：Blender 5.1.2 headless（round10）。
"""
import math
import os

import bpy
from mathutils import Vector

try:
    import build_template as T
    _log = T.log
    _fail = T.fail
except ImportError:
    import sys
    def _log(step, msg): print(f"[{step}] {msg}")
    def _fail(step, msg):
        print(f"[{step}] FATAL: {msg}")
        sys.exit(1)


# ---------------------------------------------------------------- 基礎件

def _cyl(name, r, depth, loc, rot=(0, 0, 0), verts=32, mat=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc,
                                        rotation=rot, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    return o


def _box(name, size, loc, rot=(0, 0, 0), mat=None):
    # FIX 2026-09-10（電風扇案例事故，真 probe 實測抓到）：primitive_cube_add(size=1.0) 建出來
    # 的邊長就是 1.0（不是 2.0，-0.5..0.5 的立方體邊長本來就是 1），這裡原本又除以 2，讓所有
    # 靠 _box() 蓋的細節件（knurl_ring 的滾花條、make_screw 的十字槽……）實際尺寸只剩指定值
    # 的一半——滾花條整個縮進母體表面內，渲染完全看不到。跟 build_template.add_box() 的
    # `obj.scale = size`（沒有除以 2）比對即可確認：那支是對的，這支多除了一次。
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        o.data.materials.append(mat)
    return o


def join_into(host: bpy.types.Object, parts: list, keep_active: bool = True) -> bpy.types.Object:
    """把細節件全部 join 進宿主母版（細節不另立物件，§14 實例數不炸）。"""
    parts = [p for p in parts if p and p.name != host.name]
    if not parts:
        return host
    bpy.ops.object.select_all(action="DESELECT")
    host.select_set(True)
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = host
    bpy.ops.object.join()
    return host


# ---------------------------------------------------------------- 徑向中心（2026-09-14 新增）

RADIAL_CENTER_TOL = 0.005   # 5mm：宣告的 center 與宿主實際軸心差超過此值即 fail


def _host_radial_center(host_name: str, axis: str):
    """宿主世界包圍盒在「徑向平面」上的中心點；宿主不存在時回 None。
    axis='Z'（直立圓柱/轉盤）→ (x, y)；axis='Y'（橫向鏡筒）→ (y, z)，因為該軸分支的
    軸向座標走 z_center、徑向平面是 (y, z)（見 knurl_ring 的 axis='Y'）。"""
    host = bpy.data.objects.get(host_name) if host_name else None
    if host is None:
        return None
    corners = [host.matrix_world @ Vector(c) for c in host.bound_box]
    i, j = (0, 1) if axis == "Z" else (1, 2)
    return (sum(c[i] for c in corners) / 8.0, sum(c[j] for c in corners) / 8.0)


def _radial_center(host_name: str, center, axis: str, tol: float = RADIAL_CENTER_TOL):
    """解析環狀細節（滾花/刻痕）要繞的「徑向中心」(c1, c2)。

    `center=None`（預設）：自動取宿主軸心，宿主不在原點時印一行說明改繞哪裡——2026-09-14
    汽車底盤事故：三件零件（煞車油壺蓋/水箱蓋/加油蓋）的呼叫端沒給中心參數，舊版就把整圈
    滾花建在世界原點，join 進宿主後變成散在原點附近的碎塊，渲染前的斷言全過、只有肉眼
    看得出來。讓「取宿主軸心」成為預設，正確用法就不必靠呼叫端記得傳參數。
    宿主查不到（名字打錯/呼叫順序錯）：沿用世界原點並印 WARNING，不 fail——還原舊行為但
    訊息指名是「找不到宿主」，不是靜默照做。
    `center=(c1, c2)`：以宣告值為準；與宿主實際軸心差超過 `tol` 時直接 fail——宣告的中心
    跟宿主對不上，細節一定整圈長在別的地方，寧可當場停下來，也不要交付一坨肉眼看不出、
    量測卻很明顯的碎幾何。
    """
    host_c = _host_radial_center(host_name, axis)
    if center is None:
        if host_c is None:
            _log("detail_lib", f"WARNING: {host_name} 找不到宿主物件，徑向中心沿用世界原點"
                               "——宿主若不在原點，滾花/刻痕會整圈留在原點（確認名字或明給 center=）")
            return (0.0, 0.0)
        if abs(host_c[0]) > tol or abs(host_c[1]) > tol:
            _log("detail_lib", f"{host_name} 未給 center，自動改以宿主軸心 "
                               f"({host_c[0]:.3f}, {host_c[1]:.3f}) 為徑向中心")
        return host_c
    c1, c2 = float(center[0]), float(center[1])
    if host_c is not None and (abs(c1 - host_c[0]) > tol or abs(c2 - host_c[1]) > tol):
        _fail("detail_lib", f"{host_name}：center=({c1:.3f}, {c2:.3f}) 與宿主軸心 "
                            f"({host_c[0]:.3f}, {host_c[1]:.3f}) 差超過 {tol * 1000:.0f}mm"
                            "——細節會整圈長在別的地方（確認宿主名或座標）")
    return (c1, c2)


# ---------------------------------------------------------------- 滾花（knurling）

def knurl_ring(host_name: str, radius: float, height: float, z_center: float,
               ridges: int = 48, ridge_depth: float = 0.0004, ridge_width_deg: float = 0.32,
               mat=None, axis: str = "Z", center=None,
               center_tol: float = RADIAL_CENTER_TOL) -> list:
    """圓柱外緣滾花環：ridges 根細長 box 沿圓周放射排列，每根径向嵌入 ridge_depth。
    轉盤/鈕/鏡頭對焦環的標準細節。axis='Z'=直立轉盤（預設），'Y'=橫向鏡筒環。
    ridge 數量建議走費波那契鄰數（34/55/89，§15.2 細節節奏）或 48（常見工程值）。
    `center`：徑向中心（axis='Z' → (x, y)；axis='Y' → (y, z)）。不給＝自動取宿主世界
    包圍盒中心（見 `_radial_center()`）——宿主不在原點時務必讓它自動取，或明確傳對的值。
    回傳細節件 list，呼叫者 join_into 宿主。"""
    c1, c2 = _radial_center(host_name, center, axis, center_tol)
    parts = []
    for i in range(ridges):
        ang = 2 * math.pi * i / ridges
        # ridge 中心嵌進表面 ridge_depth/2：一半在內一半在外 → 渲染出凹凸
        rr = radius - ridge_depth / 2
        rad_len = ridge_depth * 2.2          # 径向總長（含嵌入量）
        tan_w = 2 * math.pi * radius * (ridge_width_deg / 360.0)  # 弧長換算弦寬
        if axis == "Z":
            loc = (c1 + rr * math.cos(ang), c2 + rr * math.sin(ang), z_center)
            rot = (0, 0, ang)
            size = (tan_w, rad_len, height * 0.92)
        else:  # 'Y' 軸圓柱（鏡筒）：滾花繞 Y 軸
            loc = (z_center, c1 + rr * math.sin(ang), c2 + rr * math.cos(ang))
            rot = (ang, 0, 0)
            size = (rad_len, height * 0.92, tan_w)
        parts.append(_box(f"{host_name}_Knurl{i:03d}", size, loc, rot=rot, mat=mat))
    _log("detail_lib", f"{host_name} 滾花環：{ridges} 根 ridge，深 {ridge_depth*1000:.2f}mm，軸 {axis}")
    return parts


def dial_grooves(host_name: str, radius: float, z_top: float, count: int = 12,
                 groove_w: float = 0.0006, groove_len_ratio: float = 0.55,
                 groove_depth: float = 0.0004, mat=None, center=None,
                 center_tol: float = RADIAL_CENTER_TOL) -> list:
    """轉盤頂面放射刻痕（快門速度盤的刻度溝）：count 條細 box 自 0.45R 伸向 0.9R。
    count 走費波那契（8/13/21）；刻度粗細對比 = 每第 3 條加寬（視覺節奏 §15.2）。
    `center`：徑向中心 (x, y)——不給＝自動取宿主世界包圍盒中心，語意同 `knurl_ring()`
    （見 `_radial_center()`；宿主不在原點時別硬寫 (0,0)，那會讓整圈刻痕留在世界原點）。"""
    c1, c2 = _radial_center(host_name, center, "Z", center_tol)
    parts = []
    r_in = radius * (1 - groove_len_ratio) / 2
    r_out = radius * (1 + groove_len_ratio) / 2
    for i in range(count):
        ang = 2 * math.pi * i / count
        w = groove_w * (1.6 if i % 3 == 0 else 1.0)   # 每 3 條一粗=節奏對比
        rmid = (r_in + r_out) / 2
        rlen = r_out - r_in
        loc = (c1 + rmid * math.cos(ang), c2 + rmid * math.sin(ang), z_top - groove_depth / 2)
        parts.append(_box(f"{host_name}_Grv{i:02d}", (w, rlen, groove_depth * 2),
                          loc, rot=(0, 0, ang + math.pi / 2), mat=mat))
    _log("detail_lib", f"{host_name} 頂面刻痕：{count} 條（每 3 條加粗）")
    return parts


# ---------------------------------------------------------------- 防滑紋/握把

def grip_strip(host_name: str, length: float, width: float, rows: int = 6,
               cols: int = 14, dot_r: float = 0.0005, dot_h: float = 0.0004,
               origin=(0, 0, 0), normal_axis: str = "Y", mat=None) -> list:
    """矩陣式防滑凸點帶（相機握把/工具手柄）：rows×cols 個微小圓柱凸點。
    normal_axis='Y'=凸點朝 ±Y（機身側面），'Z'=朝上（平面防滑墊）。
    行列間距自動走 length/width 均分；凸點高度 dot_h 即凸出量（≥0.3mm 防共面）。"""
    parts = []
    dy = width / (rows + 1)
    dx = length / (cols + 1)
    for r in range(rows):
        for c in range(cols):
            lx = origin[0] - length / 2 + dx * (c + 1)
            lz = origin[2] - width / 2 + dy * (r + 1)
            if normal_axis == "Y":
                loc = (lx, origin[1], lz)
                rot = (math.radians(90), 0, 0)
            else:
                loc = (lx, lz, origin[2])
                rot = (0, 0, 0)
            parts.append(_cyl(f"{host_name}_Grip{r:02d}_{c:02d}", dot_r, dot_h,
                              loc, rot=rot, verts=8, mat=mat))
    _log("detail_lib", f"{host_name} 防滑凸點帶：{rows}×{cols}={len(parts)} 點")
    return parts


def ridge_lines(host_name: str, length: float, count: int = 5, spacing: float = 0.0012,
                ridge_h: float = 0.0005, ridge_w: float = 0.0004,
                origin=(0, 0, 0), axis: str = "X", space_axis: str | None = None,
                mat=None) -> list:
    """平行細脊線（握把橡膠紋/散熱鰭）：count 條等距細長凸脊。
    注意：等距是工程件常態（§15.5#3 結構合理性>形式比例）；設計件可改 spacing 序列。

    axis：每條脊線本身延伸的方向（'X' 或 'Y'）。
    space_axis（2026-09-08 新增，公車輪事故修正）：脊線群彼此排開的方向，預設 None
    時沿用舊行為——axis='X' 時排開方向預設 'Z'（垂直握把上的水平紋，Round 9 對焦環
    情境）、axis='Y' 時排開方向預設 'X'。**平放的水平面（車頂機組散熱鰭這類）不能用
    預設值**：脊線跟排開方向都在同一個水平面上（例如脊線沿 X、排開沿 Y），這時必須
    明確傳 `space_axis='Y'`——公車輪事故：呼叫端只傳了 `axis='X'`、預期「沿 X 延伸、
    沿 Y 排開」，但沒有 `space_axis` 參數可用，退回舊行為「沿 X 延伸、沿 Z 排開」，
    8 條脊線疊在同一個 (x,y) 沿 Z 往上長，實測結果：3 條陷進機組本體內部、其餘懸空
    在機組上方，肉眼看是幾條斷開懸空的線，不是貼合機組表面的散熱鰭。
    """
    axis_idx = {"X": 0, "Y": 1, "Z": 2}
    run = axis.upper()
    space = (space_axis.upper() if space_axis else ("Z" if run == "X" else "X"))
    size_by_run = {"X": (length, ridge_w, ridge_h), "Y": (ridge_w, length, ridge_h),
                   "Z": (ridge_w, ridge_h, length)}
    size = size_by_run[run]
    parts = []
    for i in range(count):
        off = (i - (count - 1) / 2) * spacing
        loc = list(origin)
        loc[axis_idx[space]] += off
        parts.append(_box(f"{host_name}_Ridge{i:02d}", size, tuple(loc), mat=mat))
    _log("detail_lib", f"{host_name} 平行脊線：{count} 條 × {spacing*1000:.1f}mm（沿 {run}，排開沿 {space}）")
    return parts


# ---------------------------------------------------------------- 接縫/螺絲

def _stitch_seg(name, p0, p1, r, mat, verts=8):
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    length = (b - a).length
    if length < 1e-9:
        length = 1e-6
    mid = (a + b) / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=tuple(mid), vertices=verts)
    o = bpy.context.active_object
    o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(b - a)
    if mat:
        o.data.materials.append(mat)
    return o


def saddle_stitches(host_name: str, p0, p1, count: int, stitch_len_ratio: float = 0.55,
                    radius: float = 0.0004, mat=None, offset=(0, 0, 0)) -> list:
    """馬鞍縫線（saddle stitch）：沿一條路徑（p0→p1）等距排列 count 段短圓管，
    模擬皮件手縫/機縫的虛線感（來源：`mechanical_watch` 參考案例
    分析，2026-09-10 新增——原案例對每一針手動各呼叫一次 `shape_lib.
    curve_tube()`，這裡把「沿路徑等距排列短線段」的規律收斂成一支函式，呼叫端
    只給起訖點跟針數）。

    真實縫線不是一條連續實線——針腳之間有間隔，遠看才有「一針一針」的顆粒感，
    連續實線看起來像貼了一條裝飾條，不是手工/機縫的線跡。`stitch_len_ratio`
    控制每針佔「總長/count」的比例（<1 代表針與針之間留間隙，0.5-0.6 是常見
    針長/針距比例，值越小虛線感越明顯，值越接近 1 越像連續線）。

    p0/p1：縫線路徑起訖點（世界座標，皮件邊緣的縫線通常跟邊緣平行、內縮一小段
    距離，呼叫端自己算好給值）。radius：線跡圓管半徑（縫線本身很細，常見
    0.3-0.5mm）。offset：整條路徑額外的世界座標偏移——皮帶兩側各一條平行縫線
    時，呼叫兩次、第二次給非零 offset 即可，不用重新算 p0/p1。

    回傳每一針物件的 list，呼叫者自行 `join_into` 併入宿主母版。"""
    from mathutils import Vector
    a = Vector(p0) + Vector(offset)
    b = Vector(p1) + Vector(offset)
    step = (b - a) / count
    seg_len = step.length * stitch_len_ratio
    direction = step.normalized() if step.length > 1e-9 else Vector((1, 0, 0))
    parts = []
    for i in range(count):
        mid = a + step * (i + 0.5)
        s0 = mid - direction * (seg_len / 2)
        s1 = mid + direction * (seg_len / 2)
        parts.append(_stitch_seg(f"{host_name}_Stitch{i:02d}", tuple(s0), tuple(s1), radius, mat))
    _log("detail_lib", f"{host_name} 縫線：{count} 針（針長/針距比 {stitch_len_ratio}）")
    return parts


def seam_ring(host_name: str, radius: float, z: float, gap: float = 0.0004,
              verts: int = 64, axis: str = "Z", mat=None, center=None,
              center_tol: float = RADIAL_CENTER_TOL):
    """分模線/接縫環：極薄深色圓柱（gap 厚）嵌在兩件交接處 → 裝配真實感。
    材質給 near-black 高粗糙（mat_lib.make_rubber 調色即可）。回傳單一物件。
    `center`：徑向中心（axis='Z' → (x, y)；axis='Y' → (y, z)）。不給＝自動取宿主世界
    包圍盒中心（見 `_radial_center()`）。2026-09-14 內裝案例：這支跟 knurl_ring/
    dial_grooves 是同一個坑——舊版環心寫死世界原點，零件不在原點時整圈接縫留在原點。"""
    c1, c2 = _radial_center(host_name, center, axis, center_tol)
    if axis == "Z":
        o = _cyl(f"{host_name}_Seam", radius * 1.001, gap, (c1, c2, z), verts=verts, mat=mat)
    else:
        o = _cyl(f"{host_name}_Seam", radius * 1.001, gap, (z, c1, c2),
                 rot=(0, math.radians(90), 0), verts=verts, mat=mat)
    return o


def make_screw(host_name: str, head_r: float = 0.0016, head_h: float = 0.0012,
               loc=(0, 0, 0), mat=None, cross_mat=None, axis: str = "Z") -> list:
    """十字螺絲母版件：圓頭 + 十字槽（兩條垂直細 box 嵌入頂面）。
    cross_mat 給深色（槽內陰影感）。回傳 [head, cross1, cross2]，呼叫者 join。"""
    rot = (math.radians(90), 0, 0) if axis == "Y" else (0, 0, 0)
    head = _cyl(f"{host_name}_Head", head_r, head_h, loc, rot=rot, verts=20, mat=mat)
    parts = [head]
    slot_w = head_r * 0.35
    slot_len = head_r * 1.5
    slot_d = head_h * 0.35
    for i, ang in enumerate((0, math.pi / 2)):
        if axis == "Z":
            off = (loc[0], loc[1], loc[2] + head_h / 2 - slot_d / 2)
            size = (slot_len, slot_w, slot_d)
        else:
            off = (loc[0] + head_h / 2 - slot_d / 2, loc[1], loc[2])
            size = (slot_d, slot_len, slot_w)
        parts.append(_box(f"{host_name}_Cross{i}", size, off, rot=(0, 0, ang), mat=cross_mat))
    _log("detail_lib", f"{host_name} 十字螺絲件 ×{len(parts)}")
    return parts


# ---------------------------------------------------------------- 3D 文字（LOGO/刻字）

def make_text(host_name: str, text: str, size: float = 0.01, loc=(0, 0, 0),
              rot=(0, 0, 0), extrude: float = 0.0009, bevel: float = 0.0002,
              mat=None, align_center_x: bool = True) -> bpy.types.Object:
    """3D Text → mesh（LOGO/刻字標準路徑，camera_pkg 實戰校準）。
    extrude=字厚（凸出量 ≥0.9mm 防共面）、bevel=字緣倒角（琺瑯字圓潤感）。
    預設繞 X 轉 90° 由呼叫者給 rot（文字面朝向觀眾 -Y 時 rot=(π/2,0,0)）。
    align_center_x：轉 mesh 後把 x 中心對齊 loc.x（text 原點在左下，不對齊會跑版）。

    **前後成對刻字（車牌/車頂燈箱正反兩面字這類）千萬別直接把 rot 的 X 分量取負號**
    （2026-09-09 香港的士案例實測抓到的真實 bug：`rot=(π/2,0,0)` 面朝 -Y 是對的，
    但反面若寫成 `rot=(-π/2,0,0)`，繞 X 軸的旋轉永遠不會動到 local X 軸——結果是
    文字法向確實翻到 +Y、朝向正確，但文字的「讀字方向」左右分量沒有跟著翻面，
    對站在 +Y 那側、面朝 -Y 看過來的觀眾而言，等同於文字整個顛倒/鏡射，肉眼判讀
    像是字被反著刻。正確做法：面朝 +Y 那面要用 `rot=(π/2, 0, π)`（在 X 分量不變
    的前提下，額外繞 Z 轉 180°，用 `mathutils.Vector` 驗證：这样 local X→世界 -X、
    local Y→世界 +Z、法向→世界 +Y，跟站在 +Y 側往 -Y 看的觀眾左右手座標系一致）。
    通式：同一段文字要贴在主體前後两个相对面上時，反面 rot 用「正面 rot 的 X 分量
    不變，Z 分量加 π」，不要只對 X 分量取負號。"""
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = host_name
    o.data.body = text
    o.data.size = size
    o.data.extrude = extrude
    o.data.bevel_depth = bevel
    o.data.align_x = "CENTER" if align_center_x else "LEFT"
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    if mat:
        o.data.materials.append(mat)
    return o


def arc_text_ring(host_name: str, text: str, radius: float, z_center: float,
                  start_deg: float, step_deg: float, size: float = 0.01,
                  extrude: float = 0.0009, mat=None, axis: str = "Y", center=None,
                  center_tol: float = RADIAL_CENTER_TOL) -> list:
    """沿圓柱面刻字：逐字元各自建一個 make_text，繞host軸放在弧線上並隨角度自轉，
    做出「文字真的刻在彎曲鏡筒/轉盤面上」的效果，取代整段文字硬貼在一塊平面上
    （2026-09-09 新增，來源：ARGENT 35 復古相機參考案例，實測比對後
    確認優於平面貼字，見 SKILL.md §10.3）。
    radius=刻字所在圓周半徑，z_center=沿軸的位置，start_deg/step_deg=起始角度與
    每字元角度增量（度，需配合字元寬度與字距試調，無固定公式）。axis='Y'=橫向鏡筒
    （常見鏡頭刻字），'Z'=直立轉盤刻度。空白字元照樣建字（含空白的間距節奏），
    呼叫者若不想要空白參與可自行先 text.replace(' ', '') 再傳入。
    `center`：徑向中心（axis='Z' → (x, y)；axis='Y' → (y, z)）。不給＝自動取宿主世界
    包圍盒中心（見 `_radial_center()`）——2026-09-14 內裝案例：舊版字元整圈繞世界原點，
    零件不在原點時刻字會留在原點（與 knurl_ring/dial_grooves/seam_ring 同源坑）。
    回傳細節件 list，呼叫者 join_into 宿主。"""
    c1, c2 = _radial_center(host_name, center, axis, center_tol)
    parts = []
    for i, ch in enumerate(text):
        a = math.radians(start_deg + i * step_deg)
        if axis == "Y":
            loc = (z_center, c1 + radius * math.sin(a), c2 + radius * math.cos(a))
            rot = (math.pi / 2, -a, 0)
        else:  # 'Z' 軸（直立轉盤/刻度環）
            loc = (c1 + radius * math.sin(a), c2 + radius * math.cos(a), z_center)
            rot = (0, 0, -a)
        parts.append(make_text(f"{host_name}_Arc{i:02d}", ch, size=size, loc=loc,
                               rot=rot, extrude=extrude, mat=mat))
    _log("detail_lib", f"{host_name} 弧線刻字：{len(text)} 字元，半徑 {radius*1000:.1f}mm，軸 {axis}")
    return parts


# ---------------------------------------------------------------- 圖片貼花

def apply_image_decal(name: str, image_path: str, width: float, height: float, center,
                       normal=(0.0, -1.0, 0.0), up=(0.0, 0.0, 1.0), proud: float = 0.05,
                       roughness: float = 0.35, metallic: float = 0.0,
                       emission_strength: float = 0.0) -> bpy.types.Object:
    """真實圖片貼花（LOGO/品牌標誌/警示符號/QR code），取代手工布林堆疊幾何湊近似輪廓
    （2026-09-10 新增，來源：iPod Classic + iPhone 17 Pro Max 兩次蘋果標事故——`make_logo()`
    用圓盤挖咬口+挖凹口+黏葉片湊蘋果標輪廓，兩次都渲得出「看得出想畫蘋果、但形狀不對」
    的結果，因為真實蘋果標的咬口弧線跟葉片形狀本來就不是任何簡單布林運算能精確湊出來的
    曲線）。真實世界既有清晰、免費、透明背景的官方標誌圖（品牌 LOGO、警告符號、QR code、
    認證標章），上網抓一張比手刻布林幾何準、快、也更省 token——形狀 100% 準確，不需要
    猜任何弧度/角度參數。

    用法：先用 asset_fetch_lib.fetch_reference_image(url, dest_path) 把圖存到本機（該函式
    已驗證下載內容真的是圖片，不是失效連結回傳的 HTML），再呼叫本函式貼上去。

    image_path：本機圖片檔案路徑，強烈建議透明背景 PNG（Alpha 決定標誌輪廓，貼上去背景
    不會蓋住宿主材質）——非透明的方形圖也能用，但 width/height 務必按圖片實際長寬比設，
    否則貼花會被拉伸變形。width/height：貼花實際尺寸（跟場景其他 add_box/add_cyl 同一個
    長度單位）。center：貼花中心世界座標。normal：貼花朝外方向（單位向量，預設面朝 -Y，
    跟 build_template 的「主體正面朝 -Y」慣例一致，非正面貼花記得改）。up：貼花「向上」
    方向（單位向量，決定貼花不會顛倒/歪斜，會自動投影到垂直於 normal 的平面，不需要
    呼叫端自己先正交化）。proud：貼花離開主體表面的微幅凸出量（防共面 Z-fighting，同
    §8#11 慣例，預設 0.05mm；貼在曲面上時務必按實際曲率加大，不然邊緣會看起來嵌入/
    穿透表面）。roughness/metallic：貼花材質基礎屬性（貼在金屬機身上通常維持低 roughness
    帶一點金屬感；emission_strength>0 讓貼花自體發光，適合面板上的品牌燈標/夜間可見標誌）。

    回傳貼花物件（未 join，呼叫者視情況 join 進宿主或保留獨立物件）。渲染引擎需為 Cycles
    （本 skill 的 build_template.py 全程使用 Cycles）——Alpha 直接接 Principled BSDF 的
    Alpha 輸入即可正確處理透明度，不需要 EEVEE 專用的 blend_method/shadow_method 設定。
    """
    from mathutils import Vector, Matrix
    n = Vector(normal).normalized()
    u_raw = Vector(up).normalized()
    u = (u_raw - n * u_raw.dot(n))
    if u.length < 1e-6:
        _fail("detail_lib", f"apply_image_decal({name}): up 向量跟 normal 幾乎平行，投影後長度趨近 0，換一個 up。")
    u = u.normalized()
    r = u.cross(n).normalized()

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=tuple(Vector(center) + n * proud))
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = Matrix((r, u, n)).transposed().to_euler()
    obj.scale = (width, height, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    img = bpy.data.images.load(image_path)
    mat = bpy.data.materials.new(f"{name}_Mat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-300, 0)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission_strength > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    obj.data.materials.append(mat)
    _log("detail_lib", f"{name} 圖片貼花完成：{width:.2f}x{height:.2f}，來源 {image_path}")
    return obj


def apply_surface_mark(mat: bpy.types.Material, image_path: str, center, size,
                       plane=("X", "Z"), darken: float = 0.10, rough_add: float = 0.06,
                       gain: float = 1.0, image=None):
    """把圖案的 alpha 當遮罩、**直接混進既有材質**（Base Color 暗化 + Roughness 提高），
    做出「同一塊材料被加工過」的同色系印記——不新增任何幾何。

    跟 `apply_image_decal()` 的分工是「印記的邊界是不是實體邊界」：
    - `apply_image_decal()`：建一片獨立貼花平面。適合本身有實體輪廓的標誌——印刷貼紙、
      警示標籤、QR code、金屬銘牌，圖案的邊界就是物件的邊界，平板不會造成誤讀。
    - 本函式：把圖案寫進宿主 shader。適合**貼在既有平面內、要讀成「表面本身被處理過」**
      的同色系蝕刻（玻璃背板雷雕標誌、面板霧面印花、木作烙印）。獨立平板即使在圖案外
      完全透明，仍然是一塊多出來的幾何——它會改變該區域的受光與反射，讓整片相鄰表面
      被提亮（實測：貼花在場時背板中灰帶 mean 122→153、clipping 0.21%→0.66% 擋下曝光
      驗證，且把圖案本身改暗完全沒有改善）。寫進宿主 shader 不會有這個副作用，因為
      表面上並沒有多出任何幾何或法線。

    mat：要疊印記的既有材質（`mat_lib` factory 建出來的即可）。
    image_path：圖檔路徑（透明背景 PNG；**只取 alpha 當遮罩**，RGB 不參與）。
    center：印記中心的世界座標（只用 plane 指定的兩個軸向分量，第三軸忽略）。
    size：(寬, 高)——印記在 plane 兩軸上的實際尺寸（跟場景其他長度同單位）。
    plane：印記所在的兩個世界軸，預設 ("X", "Z")＝貼在朝 ±Y 的平面上。
    darken：印記處 Base Color 的暗化比例（0.10＝暗 10%；同色系蝕刻 0.05-0.15）。
    rough_add：印記處 Roughness 增量（加工面比周圍略粗，0.03-0.10）。
    gain：遮罩增益。圖檔的 alpha 峰值常小於 1（tone-on-tone 遮罩常見 0.5），
      設成 1/alpha_peak 可讓印記達到 darken 指定的完整強度。
    image：已載入的 `bpy.data.images` 影像（多材質共用同一張圖時傳入，避免重複載入）。

    回傳實際使用的 image（呼叫端可重複利用）。可對同一材質重複呼叫疊多個印記；
    影像取樣模式設為 EXTEND，圖檔四周留 alpha=0 的邊界即可避免邊緣拖影。
    """
    if mat.node_tree is None:
        _fail("detail_lib", f"apply_surface_mark({mat.name}): 材質沒有節點樹，"
                            "需 mat_lib factory 建出來的材質（可直接呼叫本函式疊加）")
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        _fail("detail_lib", f"apply_surface_mark({mat.name}): 節點樹裡找不到 Principled BSDF")
    if image is None:
        image = bpy.data.images.load(image_path)
    ax_u, ax_v = plane
    axis_idx = {"X": 0, "Y": 1, "Z": 2}
    if ax_u not in axis_idx or ax_v not in axis_idx or ax_u == ax_v:
        _fail("detail_lib", f"apply_surface_mark({mat.name}): plane={plane} 不是兩個相異軸。")

    # --- 遮罩鏈：Object 座標 → 減中心 → 除以尺寸 → 當作貼圖 UV ---
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for slot, (ax, c, s) in enumerate(((ax_u, center[axis_idx[ax_u]], size[0]),
                                       (ax_v, center[axis_idx[ax_v]], size[1]))):
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[1].default_value = float(c)
        nt.links.new(sep.outputs[axis_idx[ax]], sub.inputs[0])
        div = nt.nodes.new("ShaderNodeMath")
        div.operation = "DIVIDE"
        div.inputs[1].default_value = float(s)
        nt.links.new(sub.outputs[0], div.inputs[0])
        nt.links.new(div.outputs[0], comb.inputs[slot])
    comb.inputs[2].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "EXTEND"
    tex.location = (-700, 0)
    nt.links.new(comb.outputs[0], tex.inputs["Vector"])
    mask = nt.nodes.new("ShaderNodeMath")
    mask.operation = "MULTIPLY"
    mask.inputs[1].default_value = float(gain)
    nt.links.new(tex.outputs["Alpha"], mask.inputs[0])

    # --- Base Color：把印記混成「同色系但略暗」---
    # 用 MULTIPLY + 灰階係數，而非 MIX + 一個寫死的暗色：宿主 Base Color 多半是節點
    # 算出來的（mat_lib factory 幾乎都如此），讀它的 default_value 會拿到過期常數、
    # 把顏色乘錯。MULTIPLY 直接對流進來的顏色作用，linked / 未 linked 都正確。
    bc = bsdf.inputs["Base Color"]
    src = bc.links[0].from_socket if bc.links else None
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    nt.links.new(mask.outputs[0], mix.inputs[0])
    if src is not None:
        nt.links.new(src, mix.inputs[1])
    else:
        mix.inputs[1].default_value = bc.default_value
    shade = max(0.0, 1.0 - darken)
    mix.inputs[2].default_value = (shade, shade, shade, 1.0)
    nt.links.new(mix.outputs[0], bc)

    # --- Roughness：印記處略粗 ---
    if rough_add > 0.0:
        rmul = nt.nodes.new("ShaderNodeMath")
        rmul.operation = "MULTIPLY"
        rmul.inputs[1].default_value = float(rough_add)
        nt.links.new(mask.outputs[0], rmul.inputs[0])
        rgh = bsdf.inputs["Roughness"]
        radd = nt.nodes.new("ShaderNodeMath")
        radd.operation = "ADD"
        radd.use_clamp = True
        rsrc = rgh.links[0].from_socket if rgh.links else None
        if rsrc is not None:
            nt.links.new(rsrc, radd.inputs[0])
        else:
            radd.inputs[0].default_value = rgh.default_value
        nt.links.new(rmul.outputs[0], radd.inputs[1])
        nt.links.new(radd.outputs[0], rgh)

    _log("detail_lib", f"{mat.name} 表面蝕刻完成：圖案 {size[0]:.2f}x{size[1]:.2f}"
                       f"（平面 {ax_u}{ax_v}），來源 {os.path.basename(image_path)}")
    return image


# ---------------------------------------------------------------- 細節地板自檢

def audit_detail_density(objects: list, min_detail_ratio: float = 0.25):
    """場景級細節密度審計（§10.1 細節軸的數值化）：
    細節件（名稱含 _Knurl/_Grv/_Grip/_Ridge/_Seam/_Screw/_Head/_Cross/Text）
    占總物件數比例 ≥ min_detail_ratio，不足即 fail——「跑通但平淡」要靠數值抓。
    注意：細節已 join 進母版時本審計失效，改在 build 階段由呼叫者統計零件數傳入。"""
    keys = ("_Knurl", "_Grv", "_Grip", "_Ridge", "_Seam", "_Screw", "_Head", "_Cross", "Text")
    total = len(objects)
    detail = sum(1 for o in objects if any(k in o.name for k in keys))
    ratio = detail / total if total else 0.0
    if ratio < min_detail_ratio:
        _fail("detail_lib", f"細節密度 {ratio:.2%} < 地板 {min_detail_ratio:.0%}"
                            f"（{detail}/{total}）——轉盤/鈕/握把是否漏了滾花/防滑紋？")
    _log("detail_lib", f"細節密度審計通過：{detail}/{total} = {ratio:.1%}")
    return ratio
