# -*- coding: utf-8 -*-
# KEYWORDS: blender, bpy, triview, visual hull, loft, boolean, silhouette, 三視圖, 視覺外殼
"""
triview_build.py — 由 triview_lib 產出的三視圖校準資料（triview_calib.json）
建立 3D 實體，並回渲正交視圖做客觀驗證。

定位
----
本檔是三視圖工作流的「幾何端」：圖 → 輪廓（triview_lib）→ 實體（本檔）→
回渲比對（本檔 verify）。核心手法是**兩視圖視覺外殼（two-view visual hull）**：

  把「正視圖輪廓沿深度方向拉伸」與「側視圖輪廓沿寬度方向拉伸」做布林交集，
  即得同時滿足兩張圖的立體。這正是人類建模高手面對「只有兩張正交視圖」時的
  標準做法（拉伸兩片輪廓再交集成形），比逐點猜座標可靠得多。

視覺外殼的已知限制（誠實記錄，不要當它能解決一切）
--------------------------------------------------
1. **抓不到輪廓內部的凹凸**：正視圖看不到的凹陷（輪拱、腋下開孔）會被填平，
   非輪廓特徵（例如 iPhone 背面相機凸台的真實長度）會被外殼放大到全寬度。
   解法是「加量測視角」或「用標註尺寸另外補件」，不是硬套外殼。
2. 需要**至少兩張正交視圖**；單視圖無法成形。
3. 輪廓必須封閉、不自交；凹多邊形建議先三角化（本檔已做）。

執行
----
    & $blender --background --python assets/triview_build.py -- <calib.json> <out_dir>

產物
----
    <out_dir>/triview_body.blend     幾何本體
    <out_dir>/ortho_front.png        回渲正視圖
    <out_dir>/ortho_side.png         回渲側視圖
    <out_dir>/triview_build_report.json  量測 vs 標註、逐視圖誤差、IoU
"""

from __future__ import annotations

import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

# 同目錄的 triview_lib（輪廓工具）；Blender 內建 Python 無 Pillow，但本檔
# 只用它的純幾何函式，不觸發影像路徑。
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import triview_lib as TV  # noqa: E402

DEFAULT_UNIT = 0.001          # mm → m
DEFAULT_SLAB_MARGIN = 3.0     # 拉伸片要比本體大多少（mm），確保交集完整包覆
COPLANAR_ESCAPE_MM = 0.5      # 共同軸退讓量（mm），預設啟用——見 extend_axis_scale
DEFAULT_BEVEL_WIDTH = 0.0012  # m，約 1.2mm 去毛邊（消費電子級）
DEFAULT_BEVEL_SEGMENTS = 3
DEFAULT_MERGE_DIST = 1e-5     # m
DEFAULT_RASTER_SCALE = 4.0    # Stage 6 閉環：IoU 柵格化前的等比放大（避免量化誤差主導）
DEFAULT_IOU_MIN = 0.90        # Stage 6 閉環：回渲輪廓 IoU 下限（實測後回填，見 notes）


# --------------------------------------------------------------------------
# 場景 / 網格基本操作
# --------------------------------------------------------------------------
def scene_reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'
    # 關閉 .blend1 輪替備份：輸出目錄只留有意義的產物
    bpy.context.preferences.filepaths.save_version = 0


def _activate(obj):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def mesh_from_polygon(name, verts3d):
    """由 3D 點列建立單一 n-gon 面片。

    **不要對這個平面三角形化**：實測（Blender 5.1.2）三角化後的平面輪廓丟進
    Solidify，會沿三角扇內部頂點的加權法向位移，把板子沿非拉伸軸撐出尖刺——
    30 點的圓角矩形三角化後厚度板 Z 向從 163.16mm 暴增到 175.98mm（甚至關掉
    even offset 仍有 168.79mm），而未三角化的 n-gon 兩種設定都精準維持 163.16mm。
    布林求解器本身會自行三角化，這裡不需要先做。
    """
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts3d], [], [list(range(len(verts3d)))])
    me.validate()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    return obj


def solidify(obj, thickness, name="Solidify"):
    """沿面法向加厚成實體板。

    use_even_offset 刻意關閉（= Blender 預設）：開啟後在銳角處的補償位移会把
    頂點往外推，對帶尖角的輪廓（車頭/機鼻）會產生爆走的尖刺；我們的外殼板最後
    一定被另一片板約束，角落厚度均勻性不重要，穩定性優先。
    """
    mod = obj.modifiers.new(name, 'SOLIDIFY')
    mod.thickness = float(thickness)
    mod.offset = 0.0
    mod.use_even_offset = False
    _activate(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def apply_boolean_intersect(target, cutter, name="Hull", solver="MANIFOLD"):
    """布林交集。**solver 預設 MANIFOLD**（Blender 5.1 新增），不要用 EXACT。

    實測（Blender 5.1.2）兩片拉伸板的視覺外殼交集，三種 solver 的差距是決定性的：

        solver    尺寸(w,d,h)              體積      非流形邊
        FLOAT     80.99 × 8.65 × 163.16    36,374    56
        EXACT     77.97 × 8.65 × 163.16    44,627    47   ← 尺寸對但幾何是壞的
        MANIFOLD  77.97 × 8.65 × 163.16   109,328     0   ← 唯一乾淨的結果

    正確體積約 110,000mm³（78 × 8.65 × 163 的圓角矩形柱）。EXACT 雖然尺寸看起來
    正確，體積卻只剩 40%、產生 47 條非流形邊、法向分布整個缺少 -X 面——渲染時
    正面正常、側面只剩一條細線，光看「尺寸對」完全檢查不出來。

    另註：5.1 的 solver 列舉是 ('FLOAT', 'EXACT', 'MANIFOLD')，**舊版的 'FAST'
    名稱已不存在**（會拋 TypeError）。
    """
    mod = target.modifiers.new(name, 'BOOLEAN')
    mod.operation = 'INTERSECT'
    mod.solver = solver
    mod.object = cutter
    _activate(target)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def cleanup_mesh(obj, merge_dist=DEFAULT_MERGE_DIST, dissolve_deg=1.0):
    """焊接重疊頂點 + 有限溶解，讓布林產物的碎面收乾淨。"""
    _activate(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=merge_dist)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(dissolve_deg),
                             verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def add_bevel(obj, width=DEFAULT_BEVEL_WIDTH, segments=DEFAULT_BEVEL_SEGMENTS):
    """外露邊緣去毛邊。寬度為 0 時不動作（刻意銳邊的情境）。"""
    if width <= 0:
        return obj
    mod = obj.modifiers.new("Bevel", 'BEVEL')
    mod.width = float(width)
    mod.segments = int(segments)
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(25.0)
    mod.harden_normals = False
    _activate(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def shade_smooth(obj):
    _activate(obj)
    bpy.ops.object.shade_smooth()
    return obj


# --------------------------------------------------------------------------
# 視覺外殼
# --------------------------------------------------------------------------
def extend_axis_scale(contour, axis_index=1, margin=1.0, snap_eps=0.05):
    """把輪廓在指定軸上「以中心為基準等比放大」，兩端各多出約 margin/2。

    為什麼必需：兩視圖視覺外殼的兩片拉伸板，在**共同軸**（本例 Z：正視圖與側視圖
    輪廓都剛好從 0 到 163.16mm）上會產生完全共面的頂面／底面。共面重疊是布林
    求解器的經典不穩定輸入，實測（Blender 5.1.2, EXACT solver）後果是三種壞結果
    之一：體積只剩預期值的 40% 且出現 47 條非流形邊、法向分布整個缺少 -X 面
    （渲染時側視圖只剩一條細線）。

    修法：讓其中一片（負責約束厚度的那片）在共同軸上「比對方長一點」，共面消失；
    多出來的部分本來就會被另一片切掉，不影響最終形狀。

    **用等比縮放而不是「把極值端點往外推」**：後者（直接移動 z 位於極值的頂點）
    會讓相鄰頂點落到同一位置而產生退化／自交的多邊形，實測布林直接靜默失敗、
    回傳未交集的原始板（結果尺寸等於目標板本身）。等比縮放保持多邊形簡單性，
    形狀不會走樣，是本專案驗證過可用的做法。
    """
    pts = [[float(p[0]), float(p[1])] for p in contour]
    vals = [p[axis_index] for p in pts]
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span <= 1e-9:
        return pts
    factor = (span + margin) / span
    pivot = 0.5 * (lo + hi)
    for p in pts:
        p[axis_index] = pivot + (p[axis_index] - pivot) * factor
    return pts


def profile_to_slab(name, contour_mm, plane, thickness_mm, unit=DEFAULT_UNIT,
                    center_mm=None):
    """把 2D 輪廓做成一片厚板（供布林交集用）。

    plane='XZ'：輪廓 (x, z)，沿 Y 拉伸（正視圖）
    plane='YZ'：輪廓 (y, z)，沿 X 拉伸（側視圖）
    center_mm：輪廓在拉伸軸上的中值（未給則取自身 bbox 中心）
    """
    pts = list(contour_mm)
    if plane == 'XZ':
        verts = [(x * unit, 0.0, z * unit) for x, z in pts]
    elif plane == 'YZ':
        verts = [(0.0, y * unit, z * unit) for y, z in pts]
    else:
        raise ValueError("plane must be 'XZ' or 'YZ'")
    obj = mesh_from_polygon(name, verts)
    solidify(obj, thickness_mm * unit)
    if center_mm is not None:
        axis = 1 if plane == 'XZ' else 0
        obj.location[axis] = float(center_mm) * unit
    return obj


def polygon_sanity(contour, min_fill_ratio=0.25):
    """廉價的自交／退化守衛：多邊形面積 ÷ 包圍盒面積不得過低。

    自我交叉的多邊形（例如圓角矩形的角落圓弧排列次序顛倒，串成蝴蝶結）面積會
    塌成包圍盒的一小角——實測同一組圓角矩形資料，順序錯時布林體積只剩 0.8%。
    正常主體剪影的填充率通常 0.6~0.99，因此門檻設 0.25 只攔截明顯的退化輸入，
    不會誤殺細長或凹陷的合理輪廓。

    回傳 (ratio, ok)。
    """
    pts = [[float(p[0]), float(p[1])] for p in contour]
    if len(pts) < 3:
        return 0.0, False
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bbox = (max(xs) - min(xs)) * (max(ys) - min(ys))
    if bbox <= 0:
        return 0.0, False
    acc = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        acc += x0 * y1 - x1 * y0
    ratio = abs(0.5 * acc) / bbox
    return round(ratio, 4), ratio >= min_fill_ratio


def build_visual_hull(front_mm, side_mm, name="Triview_Body",
                      depth_override_mm=None, width_override_mm=None,
                      unit=DEFAULT_UNIT, margin=DEFAULT_SLAB_MARGIN,
                      do_bevel=True, bevel_width=DEFAULT_BEVEL_WIDTH,
                      coplanar_escape_mm=COPLANAR_ESCAPE_MM):
    """兩視圖視覺外殼。front_mm=(x,z) 輪廓；side_mm=(y,z) 輪廓（y 為深度、>=0）。

    depth_override_mm / width_override_mm：用圖面標註值覆寫外殼量到的尺寸
    （外殼量測會受線寬影響；有標註數字時以標註為準，這是尺寸權威來源）。

    coplanar_escape_mm：>0 時把側視圖那片沿共同軸（Z）等比外擴此量，破壞兩片的
    共面。實測在 solver='MANIFOLD' 下不需要（0 即可得到乾淨結果），保留作為
    其他 solver／其他版本布林失效時的退路（見 extend_axis_scale）。
    """
    def _span(pts, idx):
        vals = [p[idx] for p in pts]
        return min(vals), max(vals)

    for tag, prof in (("front", front_mm), ("side", side_mm)):
        ratio, ok = polygon_sanity(prof)
        if not ok:
            raise ValueError(
                "build_visual_hull: %s contour looks degenerate/self-intersecting "
                "(area/bbox = %.4f < threshold). Check contour winding order — "
                "bowtie-ordered vertices collapse the boolean to near-zero volume." % (tag, ratio))

    fx0, fx1 = _span(front_mm, 0)
    fz0, fz1 = _span(front_mm, 1)
    sy0, sy1 = _span(side_mm, 0)
    sz0, sz1 = _span(side_mm, 1)

    width = (fx1 - fx0) if width_override_mm is None else float(width_override_mm)
    depth = (sy1 - sy0) if depth_override_mm is None else float(depth_override_mm)
    height = fz1 - fz0

    # 重新置中：把各視圖輪廓平移到共用原點（z 底 = 0、x/y 置中）
    fcx = 0.5 * (fx0 + fx1)
    front_local = [[x - fcx, z - fz0] for x, z in front_mm]
    scy = 0.5 * (sy0 + sy1)
    side_local = [[y - scy, z - sz0] for y, z in side_mm]
    # Z 為兩視圖共同軸（兩片拉伸板在此軸上會共面）。MANIFOLD solver 已能正確處理，
    # 預設不擴張；coplanar_escape_mm>0 才啟用退路（見 extend_axis_scale）
    if coplanar_escape_mm > 0.0:
        side_local = extend_axis_scale(side_local, axis_index=1, margin=coplanar_escape_mm)

    front_slab = profile_to_slab(name + "_FrontSlab", front_local, 'XZ',
                                 depth + 2 * margin, unit=unit, center_mm=0.0)
    side_slab = profile_to_slab(name + "_SideSlab", side_local, 'YZ',
                                width + 2 * margin, unit=unit, center_mm=0.0)
    body = apply_boolean_intersect(front_slab, side_slab)
    body.name = name
    cleanup_mesh(body)
    if do_bevel:
        add_bevel(body, width=bevel_width)
    shade_smooth(body)
    return body, {"width_mm": round(width, 3), "depth_mm": round(depth, 3),
                  "height_mm": round(height, 3)}


# --------------------------------------------------------------------------
# 回渲正交視圖 + 客觀量測
# --------------------------------------------------------------------------
def _ensure_camera():
    cam_data = bpy.data.cameras.new("TriviewCam")
    cam_data.type = 'ORTHO'
    cam_data.clip_start = 0.001
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("TriviewCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def _ensure_sun():
    if any(o.type == 'LIGHT' for o in bpy.data.objects):
        return
    ld = bpy.data.lights.new("KeySun", type='SUN')
    ld.energy = 3.0
    lo = bpy.data.objects.new("KeySun", ld)
    lo.rotation_euler = (math.radians(60), 0.0, math.radians(-125))
    bpy.context.collection.objects.link(lo)


def world_center(obj):
    """物件世界座標包圍盒中心（m）。"""
    bpy.context.view_layer.update()
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return tuple(sum(p[i] for p in pts) / 8.0 for i in range(3))


def render_ortho(axis, out_png, view_mm, res=(900, 900), samples=16, center=(0.0, 0.0, 0.0)):
    """沿指定軸正交回渲。axis='front' 從 -Y 看；'side' 從 +X 看；'top' 從 +Z 看。

    center 是**取景中心（m）**——必須是主體的實際世界中心，不是世界原點：機身
    通常以 z=0 為底、中心在半高處，盯著 z=0 拍會把主體裁掉一半（實測：163mm
    高的機身在 900px 畫面裡只拍到 102mm，另一半被切掉）。

    view_mm 為視野邊長（mm）；sensor_fit='HORIZONTAL' → ortho_scale 對應畫面寬，
    因此 px_per_mm = res_x / view_mm，量測可直接換算回 mm。
    """
    sc = bpy.context.scene
    cam = _ensure_camera()
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in \
        {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items} else 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = out_png
    if hasattr(sc, "eevee"):
        try:
            sc.eevee.taa_render_samples = samples
        except Exception as exc:  # 裝飾性設定，失敗只警告不中斷
            print("WARNING: eevee samples not set:", exc)

    cam.data.ortho_scale = view_mm * 0.001
    cam.data.sensor_fit = 'HORIZONTAL'
    cx, cy, cz = center
    d = 1.0
    if axis == 'front':
        loc, tgt = Vector((cx, cy - d, cz)), Vector((0.0, 1.0, 0.0))
    elif axis == 'side':
        loc, tgt = Vector((cx + d, cy, cz)), Vector((-1.0, 0.0, 0.0))
    elif axis == 'top':
        loc, tgt = Vector((cx, cy, cz + d)), Vector((0.0, 0.0, -1.0))
    else:
        raise ValueError("axis must be front/side/top")
    cam.location = loc
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = tgt.to_track_quat('-Z', 'Y')
    bpy.ops.render.render(write_still=True)
    return out_png


def measure_render(png_path, view_mm, res=(900, 900)):
    """讀回正交渲染，量測不透明輪廓的 mm 尺寸與輪廓點（畫面座標）。"""
    img = bpy.data.images.load(png_path, check_existing=False)
    w, h = img.size
    px = list(img.pixels)
    alpha = px[3::4]
    # 影像為 bottom-up：直接以列索引建構，之後不再翻轉，量測用 bbox 即可
    import numpy as np
    a = np.asarray(alpha, dtype=np.float32).reshape(h, w)
    mask = a > 0.5
    ys, xs = np.nonzero(mask)
    img.user_clear()
    bpy.data.images.remove(img)
    if xs.size == 0:
        return None
    scale = view_mm / float(w)          # mm per pixel（HORIZONTAL fit）
    w_mm = (xs.max() - xs.min() + 1) * scale
    h_mm = (ys.max() - ys.min() + 1) * scale
    return {"w_mm": round(float(w_mm), 3), "h_mm": round(float(h_mm), 3),
            "px_per_mm": round(1.0 / scale, 4), "px": int(xs.size),
            "bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}


# --------------------------------------------------------------------------
# Stage 6 · 閉環驗證：回渲剪影 ↔ 來源輪廓
# --------------------------------------------------------------------------
def _alpha_to_contour_mm(mask, ppm, min_px=40):
    """alpha 布林遮罩 → mm 輪廓 + 量測。**純函式**（與檔案讀取分離，方便自測）。

    `mask` 必須是 **bottom-up 列序**：第 0 列是畫面底部（Blender `image.pixels`
    的原生順序）。因此列索引本身就是「由下往上」的高度，**不可再套
    to_mm_contour() 的 y 翻正**（那是給 top-down 影像用的，會讓模型上下顛倒）。

        ppm  = res_x / view_mm            （sensor_fit='HORIZONTAL'）
        mm_x = (col − bbox 中心 x) / ppm
        mm_z = (row − bbox 最底列)  / ppm

    這正好對上 triview_calib 的 contour_mm 慣例（x 以 bbox 中心為 0、z 由底部 0 起），
    所以可以直接與來源輪廓比對。
    """
    import numpy as np
    m = np.asarray(mask, dtype=bool)
    ys, xs = np.nonzero(m)
    if xs.size < int(min_px):
        return None
    cx = 0.5 * float(xs.min() + xs.max())
    row0 = float(ys.min())
    pts_px = TV.trace_outer_contour(m)
    if len(pts_px) < 8:
        return None
    ppm = float(ppm)
    contour_mm = [[round((float(x) - cx) / ppm, 4),
                   round((float(y) - row0) / ppm, 4)] for x, y in pts_px]
    return {"contour_mm": contour_mm, "px_per_mm": round(ppm, 4),
            "bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "bbox_mm": [round((xs.max() - xs.min() + 1) / ppm, 3),
                        round((ys.max() - ys.min() + 1) / ppm, 3)]}


def silhouette_contour_mm(png_path, view_mm, min_px=40):
    """讀一張回渲 PNG，取 alpha 剪影後換算成 mm 輪廓（見 _alpha_to_contour_mm）。

    回傳 None 表示剪影為空或過小（該視圖渲染失敗、或主體不在畫面內）。
    """
    img = bpy.data.images.load(png_path, check_existing=False)
    try:
        w, h = img.size
        px = list(img.pixels)
    finally:
        img.user_clear()
        bpy.data.images.remove(img)
    import numpy as np
    alpha = np.asarray(px[3::4], dtype=np.float32).reshape(h, w)
    return _alpha_to_contour_mm(alpha > 0.5, float(w) / float(view_mm), min_px=min_px)


def _polygon_mask_np(poly, size, origin):
    """把多邊形填進布林畫布（純 numpy 掃描線 even-odd）。

    為什麼不用 `triview_lib.rasterize_polygon`：那支走 Pillow，而 **Blender 內建
    Python 沒有 Pillow**（實測 ModuleNotFoundError），幾何端跑不了。本檔是幾何端，
    因此以 numpy 自實作同一件事；影像端（venv）仍用 triview_lib 的 PIL 版本。
    """
    import numpy as np
    w, h = int(size[0]), int(size[1])
    ox, oy = float(origin[0]), float(origin[1])
    mask = np.zeros((h, w), dtype=bool)
    if len(poly) < 3 or w < 1 or h < 1:
        return mask
    P = np.asarray([[float(p[0]) - ox, float(p[1]) - oy] for p in poly],
                   dtype=np.float64)
    ax = P[:, 0][None, :]
    ay = P[:, 1][None, :]
    bx = np.roll(P[:, 0], -1)[None, :]
    by = np.roll(P[:, 1], -1)[None, :]
    ys = (np.arange(h, dtype=np.float64) + 0.5)[:, None]
    cross = (ay <= ys) != (by <= ys)
    dy = np.where(np.abs(by - ay) < 1e-12, 1e-12, by - ay)
    xint = np.where(cross, ax + (ys - ay) / dy * (bx - ax), np.nan)
    xint = np.sort(xint, axis=1)          # NaN 會被排到最後
    counts = cross.sum(axis=1)
    for row in range(h):
        k = int(counts[row]) // 2
        if k <= 0:
            continue
        seg = xint[row, :2 * k].reshape(k, 2)
        c0 = np.clip(np.ceil(seg[:, 0] - 0.5).astype(np.int64), 0, w - 1)
        c1 = np.clip(np.floor(seg[:, 1] - 0.5).astype(np.int64), 0, w - 1)
        for a, b in zip(c0, c1):
            if b >= a:
                mask[row, a:b + 1] = True
    return mask


def iou_contours_np(pts_a, pts_b, pad=4):
    """兩個輪廓（同一座標系、同單位）的 IoU——純 numpy，Blender 端可用。"""
    import numpy as np
    ax = [float(p[0]) for p in pts_a]
    az = [float(p[1]) for p in pts_a]
    bx = [float(p[0]) for p in pts_b]
    bz = [float(p[1]) for p in pts_b]
    x0 = min(min(ax), min(bx)) - pad
    y0 = min(min(az), min(bz)) - pad
    size = (int(math.ceil(max(max(ax), max(bx)) + pad - x0)) + 1,
            int(math.ceil(max(max(az), max(bz)) + pad - y0)) + 1)
    ma = _polygon_mask_np(pts_a, size, (x0, y0))
    mb = _polygon_mask_np(pts_b, size, (x0, y0))
    union = int(np.logical_or(ma, mb).sum())
    if not union:
        return 0.0
    return float(np.logical_and(ma, mb).sum()) / float(union)


def _boundary_distance_mm(query_pts, polyline_pts, sample=800):
    """每個 query 點到 polyline（**含線段**，不只頂點）的最短距離（mm）。

    「只比頂點」在這裡是錯的：參考輪廓是粗折線——側視圖只有 13 個點，單邊長達
    160mm，該邊中點到最近頂點的距離可達 80mm。那是取樣密度差，不是形狀差異，
    卻會讓 Hausdorff 從 2mm 跳到 80mm。點對線段才是幾何上正確的「到邊界距離」。
    """
    import numpy as np
    q = np.asarray(query_pts, dtype=np.float64)
    if q.ndim != 2 or q.shape[0] == 0:
        return np.asarray([])
    if sample and q.shape[0] > int(sample):
        q = q[np.linspace(0, q.shape[0] - 1, int(sample)).astype(int)]
    p = np.asarray(polyline_pts, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] < 2:
        return np.asarray([])
    ab = np.roll(p, -1, axis=0) - p                       # (n, 2)
    ap = q[:, None, :] - p[None, :, :]                    # (m, n, 2)
    denom = (ab ** 2).sum(-1)
    denom = np.where(denom < 1e-18, 1e-18, denom)
    t = np.clip((ap * ab[None, :, :]).sum(-1) / denom[None, :], 0.0, 1.0)
    proj = p[None, :, :] + t[:, :, None] * ab[None, :, :]
    d = np.sqrt(((q[:, None, :] - proj) ** 2).sum(-1))
    return d.min(axis=1)


def boundary_hausdorff_mm(a_pts, b_pts, sample=800):
    """對稱的「到邊界」Hausdorff 距離（點對線段，非點對頂點）。

    用於「粗參考折線 vs 密集回渲輪廓」這種取樣密度不對稱的比對。影像端的
    `triview_lib.hausdorff` 是點對頂點版本，只在兩邊密度相近時可用。
    """
    if not a_pts or not b_pts:
        return float("nan")
    d_ab = _boundary_distance_mm(a_pts, b_pts, sample=sample)
    d_ba = _boundary_distance_mm(b_pts, a_pts, sample=sample)
    if d_ab.size == 0 or d_ba.size == 0:
        return float("nan")
    return float(max(d_ab.max(), d_ba.max()))


def silhouette_iou(render_png, view_mm, ref_contour_mm,
                   raster_scale=DEFAULT_RASTER_SCALE):
    """回渲剪影 vs 來源輪廓：IoU（無因次）與到邊界的 Hausdorff 距離（mm）。

    **柵格化前先等比放大 raster_scale**：iou_contours 是 1 單位 = 1 像素在柵格上填色，
    78×163mm 的物件在 1mm/px 下只有 86×171 的畫布，輪廓線寬造成的量化誤差會主導
    IoU；放大後解析度變細，IoU 才反映真實形狀差異。等比放大不改變 IoU 本身
    （分子分母同時放大），純粹是數值精度。
    """
    got = silhouette_contour_mm(render_png, view_mm)
    if got is None:
        return {"iou": None, "hausdorff_mm": None, "ok": False,
                "reason": "no silhouette in render"}
    if not ref_contour_mm or len(ref_contour_mm) < 3:
        return {"iou": None, "hausdorff_mm": None, "ok": False,
                "reason": "no reference contour"}
    s = float(raster_scale)
    a_pts = [[float(p[0]) * s, float(p[1]) * s] for p in ref_contour_mm]
    b_pts = [[float(p[0]) * s, float(p[1]) * s] for p in got["contour_mm"]]
    iou = iou_contours_np(a_pts, b_pts, pad=int(4 * s))
    hd = boundary_hausdorff_mm(ref_contour_mm, got["contour_mm"])
    ref_x = [float(p[0]) for p in ref_contour_mm]
    ref_z = [float(p[1]) for p in ref_contour_mm]
    return {"iou": round(float(iou), 4),
            "hausdorff_mm": round(float(hd), 3),
            "ref_pts": len(ref_contour_mm), "got_pts": len(got["contour_mm"]),
            "render_bbox_mm": got["bbox_mm"],
            "ref_bbox_mm": [round(max(ref_x) - min(ref_x), 3),
                            round(max(ref_z) - min(ref_z), 3)],
            "ok": True}


def assert_iou(closure, min_iou, label="triview"):
    """回渲輪廓與來源輪廓的 IoU 硬性門檻——輪廓像不像跟尺寸對不對同罪。"""
    if not closure or not closure.get("ok") or closure.get("iou") is None:
        raise AssertionError("%s: closure comparison unavailable (%s)"
                            % (label, (closure or {}).get("reason", "no data")))
    if float(closure["iou"]) < float(min_iou):
        raise AssertionError(
            "%s: re-rendered silhouette IoU %.4f below %.3f (hausdorff %.3f mm, "
            "%d ref pts vs %d render pts)"
            % (label, closure["iou"], float(min_iou),
               closure.get("hausdorff_mm") or float("nan"),
               closure.get("ref_pts", 0), closure.get("got_pts", 0)))
    return True


def footprint_dims(obj, unit=DEFAULT_UNIT):
    """物件世界座標 bbox（mm）。"""
    bpy.context.view_layer.update()
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return {"width_mm": round((max(xs) - min(xs)) / unit, 3),
            "depth_mm": round((max(ys) - min(ys)) / unit, 3),
            "height_mm": round((max(zs) - min(zs)) / unit, 3),
            "verts": len(obj.data.vertices), "faces": len(obj.data.polygons)}


def assert_spec(report, rel_tol_pct=2.0, label="triview"):
    """對照標註尺寸做硬性斷言：任一維度相對誤差超過 rel_tol_pct 就 raise。

    這是「跑通但尺寸走樣」的防線——尺寸錯跟方向錯同罪，必須靠數值擋下來，
    不能靠人眼看渲染圖（1-2% 的尺寸誤差在圖上根本看不出來）。
    """
    bad = [c for c in report.get("checks", []) if abs(c.get("rel_err_pct", 0.0)) > rel_tol_pct]
    if bad:
        detail = "; ".join("%s got %.3fmm vs spec %.3fmm (%.2f%%)"
                           % (c["dim"], c["got_mm"], c["spec_mm"], c["rel_err_pct"]) for c in bad)
        raise AssertionError("%s: %d dimension(s) outside %.1f%% tolerance — %s"
                             % (label, len(bad), rel_tol_pct, detail))
    return True


def build_report(obj, calib, out_dir, ortho_front, ortho_side, view_mm, res,
                 hull_info, closure=None):
    spec = calib.get("subject", {}).get("spec_mm", {})
    ref_front = calib.get("views", {}).get("front", {}).get("contour_mm", [])
    measured = footprint_dims(obj)
    report = {
        "source_calib": calib.get("source", {}),
        "hull_input": hull_info,
        "mesh": measured,
        "spec_mm": spec,
        "ortho": {"view_mm": view_mm, "res": list(res),
                  "front": ortho_front, "side": ortho_side},
        "closure": closure or {},
        "checks": [],
    }
    for key, ref in (("width_mm", spec.get("width")), ("depth_mm", spec.get("depth")),
                     ("height_mm", spec.get("height"))):
        if ref:
            got = measured[key]
            report["checks"].append({"dim": key, "got_mm": got, "spec_mm": ref,
                                     "rel_err_pct": round(100.0 * (got - ref) / ref, 3)})
    if ortho_front and spec.get("width"):
        report["checks"].append({"dim": "render_front_w_mm", "got_mm": ortho_front["w_mm"],
                                 "spec_mm": spec["width"],
                                 "rel_err_pct": round(100.0 * (ortho_front["w_mm"] - spec["width"]) / spec["width"], 3)})
    if ortho_side and spec.get("depth"):
        report["checks"].append({"dim": "render_side_d_mm", "got_mm": ortho_side["w_mm"],
                                 "spec_mm": spec["depth"],
                                 "rel_err_pct": round(100.0 * (ortho_side["w_mm"] - spec["depth"]) / spec["depth"], 3)})
    report["reference_front_contour_pts"] = len(ref_front)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "triview_build_report.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    return report, path


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    if len(argv) < 2:
        if "--selftest" in sys.argv:
            c, f = _selftest()
            for i in c:
                print("  ok:", i)
            print("TOTAL_CHECKS_FAILED: %d" % len(f))
            for x in f:
                print("  FAIL:", x)
            return 1 if f else 0
        print("usage: blender --background --python triview_build.py -- <calib.json> <out_dir>")
        print("       blender --background --python triview_build.py -- --selftest")
        return 2
    calib_path, out_dir = argv[0], argv[1]
    calib = TV.load_calib(calib_path)
    views = calib["views"]
    front = views["front"]["contour_mm"]
    side = views["side"]["contour_mm"]
    spec = calib.get("subject", {}).get("spec_mm", {})

    scene_reset()
    obj, hull_info = build_visual_hull(
        front, side, name="Triview_Body",
        depth_override_mm=spec.get("depth"),
        width_override_mm=spec.get("width"))

    dims = footprint_dims(obj)
    center = world_center(obj)
    view_mm = max(dims["height_mm"], dims["width_mm"], dims["depth_mm"]) * 1.25
    res = (900, 900)
    os.makedirs(out_dir, exist_ok=True)
    _ensure_sun()
    of = render_ortho('front', os.path.join(out_dir, "ortho_front.png"), view_mm, res=res, center=center)
    os_ = render_ortho('side', os.path.join(out_dir, "ortho_side.png"), view_mm, res=res, center=center)

    mf = measure_render(of, view_mm, res)
    ms = measure_render(os_, view_mm, res)

    # Stage 6 閉環：回渲剪影與來源輪廓比對（尺寸對之外，形狀也要對）
    closure = {"front": silhouette_iou(of, view_mm, views["front"]["contour_mm"]),
               "side": silhouette_iou(os_, view_mm, views["side"]["contour_mm"])}
    report, rpath = build_report(obj, calib, out_dir, mf, ms, view_mm, res, hull_info,
                                 closure=closure)

    # 尺寸硬性斷言：不合格就非零退出（跑通但尺寸走樣要靠數值擋，不是靠肉眼看圖）
    tol = float(os.environ.get("TRIVIEW_TOL_PCT", "2.0"))
    spec_ok = True
    try:
        assert_spec(report, rel_tol_pct=tol)
    except AssertionError as exc:
        spec_ok = False
        print("SPEC_ASSERT_FAIL: %s" % exc)

    iou_min = float(os.environ.get("TRIVIEW_IOU_MIN", str(DEFAULT_IOU_MIN)))
    closure_ok = True
    for tag in ("front", "side"):
        try:
            assert_iou(closure[tag], iou_min, label="triview_build:%s" % tag)
        except AssertionError as exc:
            closure_ok = False
            print("CLOSURE_ASSERT_FAIL: %s" % exc)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "triview_body.blend"))
    print("SCENE_STATE:" + json.dumps({"mesh": dims, "hull": hull_info,
                                       "render_front": mf, "render_side": ms,
                                       "closure": closure, "iou_min": iou_min,
                                       "spec_assert_ok": spec_ok,
                                       "closure_assert_ok": closure_ok, "tol_pct": tol}))
    print("REPORT:" + rpath)
    print("OBJECTS:" + json.dumps([o.name for o in bpy.data.objects]))
    if not spec_ok:
        print("TRIVIEW_BUILD_FAILED_SPEC")
        return 3
    if not closure_ok:
        print("TRIVIEW_BUILD_FAILED_CLOSURE")
        return 4
    print("TRIVIEW_BUILD_OK")
    return 0


def _selftest():
    """合成輪廓驗證外殼管線（不需外部檔案）：體積、非流形邊、尺寸、斷言。"""
    checks, fails = [], []

    def chk(name, cond, detail=""):
        checks.append(name)
        if not cond:
            fails.append("%s %s" % (name, detail))

    import bmesh as _bm

    # 合成資料：80 × 170 的圓角矩形正視圖 + 10mm 厚（10 寬 × 170 高）的側視圖。
    # **頂點必須依逆時針順序**：角落圓弧的排列次序若顛倒（例如把「上左弧」接在
    # 「上右弧」後面），多邊形會自我交叉成蝴蝶結，布林求出的體積會塌成近乎零
    # （實測：同樣的圓角矩形，順序錯 → 體積 1068mm³，順序對 → 134764mm³）。
    def rounded(w, h, r, cx=0.0):
        x0, x1 = cx - w / 2.0, cx + w / 2.0
        y0, y1 = 0.0, h
        n = 8
        arcs = [((x0 + r, y0 + r), 180.0),   # 下左弧：左 → 下
                ((x1 - r, y0 + r), 270.0),   # 下右弧：下 → 右
                ((x1 - r, y1 - r), 0.0),     # 上右弧：右 → 上
                ((x0 + r, y1 - r), 90.0)]    # 上左弧：上 → 左
        pts = []
        for (ccx, ccy), a0 in arcs:
            for k in range(n + 1):
                a = math.radians(a0 + k * 90.0 / n)
                pts.append([ccx + r * math.cos(a), ccy + r * math.sin(a)])
        return pts

    front = rounded(80.0, 170.0, 12.0)
    side = rounded(10.0, 170.0, 4.9, cx=0.0)   # 側視圖以厚度為寬、置中於 0

    scene_reset()
    body, info = build_visual_hull(front, side, name="ST", depth_override_mm=10.0,
                                   width_override_mm=80.0, do_bevel=False)
    bm = _bm.new()
    bm.from_mesh(body.data)
    vol = bm.calc_volume(signed=False) * 1e9
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    expect_vol = (80.0 * 170.0 - (4.0 - math.pi) * 12.0 ** 2) * 10.0
    chk("selftest.volume_within_5pct", abs(vol - expect_vol) / expect_vol < 0.05,
        "got %.0f want %.0f" % (vol, expect_vol))
    chk("selftest.nonmanifold_low", nonman <= 2, "nonmanifold=%d" % nonman)

    d = footprint_dims(body)
    chk("selftest.dims", abs(d["width_mm"] - 80.0) < 0.5 and abs(d["depth_mm"] - 10.0) < 0.5
        and abs(d["height_mm"] - 170.0) < 0.6,
        "got w%.2f d%.2f h%.2f" % (d["width_mm"], d["depth_mm"], d["height_mm"]))

    # 布林求解器：MANIFOLD 才能給出乾淨幾何（EXACT 會體積剩 40%）
    scene_reset()
    a = profile_to_slab("A", [[x, z] for x, z in front], 'XZ', 16.0, center_mm=0.0)
    b = profile_to_slab("B", [[y, z] for y, z in side], 'YZ', 96.0, center_mm=0.0)
    res = apply_boolean_intersect(a, b)
    bm = _bm.new()
    bm.from_mesh(res.data)
    v2 = bm.calc_volume(signed=False) * 1e9
    nm2 = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    chk("selftest.manifold_solver_clean", abs(v2 - expect_vol) / expect_vol < 0.05 and nm2 <= 2,
        "vol=%.0f (want %.0f) nonmanifold=%d" % (v2, expect_vol, nm2))

    # 斷言工具本身：合格報告通過、超差報告擋下
    ok_report = {"checks": [{"dim": "w", "got_mm": 80.0, "spec_mm": 80.4, "rel_err_pct": -0.5}]}
    bad_report = {"checks": [{"dim": "w", "got_mm": 90.0, "spec_mm": 80.0, "rel_err_pct": 12.5}]}
    chk("selftest.assert_passes", assert_spec(ok_report, 2.0) is True)
    try:
        assert_spec(bad_report, 2.0)
        chk("selftest.assert_blocks", False, "should have raised")
    except AssertionError:
        chk("selftest.assert_blocks", True)

    # 纏繞/退化守衛（見 polygon_sanity）
    ratio, ok = polygon_sanity(front)
    chk("selftest.sanity_guard_ok", ok, "ratio=%.4f" % ratio)
    bowtie = [[0, 0], [10, 10], [10, 0], [0, 10]]   # 順序顛倒 → 自交
    b_ratio, b_ok = polygon_sanity(bowtie)
    chk("selftest.sanity_guard_blocks", not b_ok, "ratio=%.4f" % b_ratio)

    # 共面退路：擴張後兩片在共同軸上不再共面
    ext = extend_axis_scale([[0.0, 0.0], [1.0, 0.0], [1.0, 10.0], [0.0, 10.0]], 1, 1.0)
    zs = [p[1] for p in ext]
    chk("selftest.extend_axis_scale", abs((max(zs) - min(zs)) - 11.0) < 1e-6
        and abs(min(zs) + 0.5) < 1e-6, "z=%s" % (zs,))

    # --- Stage 6 閉環：bottom-up 換算與 IoU ---------------------------------
    import numpy as np
    mask = np.zeros((200, 200), dtype=bool)
    mask[20:120, 30:70] = True      # 40 px 寬 × 100 px 高；第 0 列 = 畫面底部
    ppm = 4.0                       # 4 px/mm → 10mm × 25mm
    got = _alpha_to_contour_mm(mask, ppm)
    chk("closure.mask_contour", got is not None and got["bbox_mm"] == [10.0, 25.0],
        "bbox_mm=%s" % (None if got is None else got["bbox_mm"],))
    if got is not None:
        zs_mm = [p[1] for p in got["contour_mm"]]
        xs_mm = [p[0] for p in got["contour_mm"]]
        chk("closure.bottom_up", abs(min(zs_mm)) < 0.3
            and abs(max(zs_mm) - 24.75) < 0.3,
            "z range=%.3f..%.3f" % (min(zs_mm), max(zs_mm)))
        chk("closure.x_centered", abs(min(xs_mm) + max(xs_mm)) < 0.3,
            "x range=%.3f..%.3f" % (min(xs_mm), max(xs_mm)))
        ref = got["contour_mm"]
        s = DEFAULT_RASTER_SCALE
        a_pts = [[x * s, y * s] for x, y in ref]
        chk("closure.iou_self", abs(iou_contours_np(a_pts, a_pts) - 1.0) < 1e-9,
            "iou=%s" % iou_contours_np(a_pts, a_pts))
        b_pts = [[(x + 3.0) * s, y * s] for x, y in ref]     # 右移 3mm
        iou_shift = iou_contours_np(a_pts, b_pts)
        chk("closure.iou_shift_drops", iou_shift < 0.85,
            "iou=%.4f (10mm wide silhouette shifted 3mm)" % iou_shift)
        chk("closure.hausdorff_self", boundary_hausdorff_mm(ref, ref) == 0.0)
        # 粗折線 vs 加密點：點對線段必須趨近 0，點對頂點版本會爆到邊長一半
        coarse = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        dense = []
        for (q0, q1) in (((0.0, 0.0), (10.0, 0.0)), ((10.0, 0.0), (10.0, 10.0)),
                         ((10.0, 10.0), (0.0, 10.0)), ((0.0, 10.0), (0.0, 0.0))):
            for k in range(60):
                f = k / 60.0
                dense.append([q0[0] + (q1[0] - q0[0]) * f, q0[1] + (q1[1] - q0[1]) * f])
        d_cd = boundary_hausdorff_mm(coarse, dense)
        d_vv = TV.hausdorff(coarse, dense)
        chk("closure.boundary_not_vertex", d_cd < 0.01 and d_vv > 1.0,
            "boundary=%.4f vertex=%.4f" % (d_cd, d_vv))
    else:
        chk("closure.bottom_up", False, "no contour")
        chk("closure.x_centered", False, "no contour")
        chk("closure.iou_self", False, "no contour")
        chk("closure.iou_shift_drops", False, "no contour")
        chk("closure.hausdorff_self", False, "no contour")
        chk("closure.boundary_not_vertex", False, "no contour")

    ok_c = {"iou": 0.95, "ok": True, "hausdorff_mm": 0.4, "ref_pts": 30, "got_pts": 28}
    bad_c = {"iou": 0.60, "ok": True, "hausdorff_mm": 4.0, "ref_pts": 30, "got_pts": 28}
    miss_c = {"iou": None, "ok": False, "reason": "no silhouette in render"}
    chk("closure.assert_passes", assert_iou(ok_c, 0.90) is True)
    try:
        assert_iou(bad_c, 0.90)
        chk("closure.assert_blocks_low_iou", False, "should have raised")
    except AssertionError:
        chk("closure.assert_blocks_low_iou", True)
    try:
        assert_iou(miss_c, 0.90)
        chk("closure.assert_blocks_missing", False, "should have raised")
    except AssertionError:
        chk("closure.assert_blocks_missing", True)

    return checks, fails


if __name__ == "__main__":
    sys.exit(main())
