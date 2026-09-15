# -*- coding: utf-8 -*-
# KEYWORDS: blender, bpy, triview, loft, station, cross-section, quadriflow, topology, 三視圖, 站點放樣, 斷面, 拓撲正規化
"""
triview_loft.py — 三視圖工作流的 Stage 3（站點斷面放樣）與 Stage 4（拓撲正規化）。

定位
----
`triview_build.py` 的**兩視圖視覺外殼**是「正視圖沿深度拉伸 ∩ 側視圖沿寬度拉伸」，
數學上必然**填平輪廓內側的凹陷**，而且輸出是布林碎面（三角為主、面數不規則、不利細分）。
車體的輪拱、家電的內凹握把、任何需要「沿主軸逐站修形」的造型，外殼做不到。

本檔換一條路：**沿主軸切片，每一站用兩張圖在該站的跨度組成一個斷面，再逐站橋接成
單一連續曲面**。這是車廠的標準工序（station / section / loft），也是人類建模高手
面對正交視圖時的做法——先定站點，再定每個站點的斷面。

  Stage 3  站點斷面放樣
           掃描線求每一站在兩張圖上的跨度 → 圓角矩形斷面 → 逐站橋接成單一 mesh。
  Stage 4  拓撲正規化
           以 quadriflow 把（外殼的布林碎面、或任何髒網格）重拓成全四邊、零非流形。

Stage 3 的已知代價（誠實記錄）
------------------------------
1. **斷面取外包絡會填平凹陷**：掃描線碰到多段時（輪廓在該高度有缺口）取 min..max，
   缺口被填掉。`scan_spans()` 會回報 `n_runs`，`build_station_loft()` 回報
   `max_span_runs`——凹陷是真實存在的話，數值上看得出來，不會靜默消失。
2. **斷面邊緣圓角不可量測**：那是俯視／邊緣處理的性質，正視圖+側視圖推導不出來。
   因此 `corner_radius_mm` 是**顯式設計參數**：優先取圖面標註值，其次取對該品類的
   業界知識，都沒有才退回 `auto_corner_frac × min(w, h)` 並在回報中標記為估計值。
   **這正是「量測給座標、知識給工藝」的分工**——本工作流不取代規劃，只餵給規劃真實數字。
3. **只支援一條主軸**：分支結構（樹狀、多軸總成）不在範圍內。

執行
----
    & $blender --background --python assets/triview_loft.py -- <calib.json> <out_dir> \
        [--stations N] [--a-view front|rear|top] [--corner-radius-mm R] [--no-retopo]
    & $blender --background --python assets/triview_loft.py -- --selftest

產物
----
    <out_dir>/triview_loft.blend
    <out_dir>/loft_ortho_front.png / loft_ortho_side.png
    <out_dir>/triview_loft_report.json   尺寸檢查、拓撲統計、回渲輪廓 IoU
"""

from __future__ import annotations

import json
import math
import os
import sys

import bmesh
import bpy

# 同目錄的兩支既有模組：triview_lib（輪廓/驗證純函式）、triview_build（幾何端
# 共用的 mesh/材質/回渲/量測工具）。重用而不是複製——單一真相源。
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import triview_build as TB  # noqa: E402
import triview_lib as TV  # noqa: E402

AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}

DEFAULT_STATIONS = 32
DEFAULT_ARC_SEGS = 4              # 每個圓角的分段數 → 斷面固定 4*(arc_segs+1) 點
DEFAULT_AUTO_CORNER_FRAC = 0.15   # 未給圓角時：min(w, h) 的比例（估計值）
DEFAULT_EPS_FRAC = 0.002          # 站點範圍兩端內縮比例，避開多邊形退化端點
DEFAULT_MIN_SECTION_MM = 0.05     # 斷面最小邊長；低於此視為「該站沒有材料」
DEFAULT_RASTER_SCALE = 4.0        # IoU 柵格化前的等比放大（避免 1mm/px 量化主導）
DEFAULT_IOU_MIN = 0.90            # 回渲輪廓 IoU 下限（實測後回填，見 notes）
DEFAULT_DISTRIBUTION = "cosine"   # 站點分佈：兩端加密（曲率高處），見 station_grid


# --------------------------------------------------------------------------
# Stage 3-a · 取樣配置
# --------------------------------------------------------------------------
def contour_range(contour, axis_idx):
    """輪廓在指定軸上的 (min, max)。"""
    vals = [float(p[axis_idx]) for p in contour]
    if not vals:
        raise ValueError("contour_range: empty contour")
    return (min(vals), max(vals))


def plan_axes(views, a_view=None, b_view=None):
    """依 calib 有哪些視圖決定取樣配置。

    兩種模式：
      top + side → a=top(x,y) 沿 Y 取樣/取 X 跨度；b=side(y,z) 沿 Y 取樣/取 Z 跨度；
                   站點沿 **Y（長軸）** 前進 → 適用「躺著」的物件（車、船、機身）。
      否則       → a=<寬度視圖>(x,z) 沿 Z 取樣/取 X 跨度；b=side(y,z) 沿 Z 取樣/取 Y 跨度；
                   站點沿 **Z（共同軸）** 前進 → 適用「立著」的物件（手機、家電、瓶罐）。

    a_view 未指定時：有 top 就用 top，否則依 ('front', 'rear') 順序取第一個存在的。
    回傳 dict，含 prof_a/prof_b 的輪廓、取樣與跨度軸索引、世界軸映射 axes。
    """
    if "side" not in views:
        raise ValueError("plan_axes: calib has no 'side' view — the station loft "
                         "needs a depth profile as its second source")
    bv = b_view or "side"
    if bv not in views:
        raise ValueError("plan_axes: requested b_view %r not in calib views %s"
                         % (bv, sorted(views)))
    if a_view is None:
        for cand in ("top", "front", "rear"):
            if cand in views:
                av = cand
                break
        else:
            raise ValueError("plan_axes: none of ('top','front','rear') present in "
                             "calib views %s" % (sorted(views),))
    else:
        av = a_view
    if av not in views:
        raise ValueError("plan_axes: requested a_view %r not in calib views %s"
                         % (av, sorted(views)))

    if av == "top":
        return {"mode": "top+side (stations along Y)", "a_view": av, "b_view": bv,
                "prof_a": views[av]["contour_mm"], "a_sample": 0, "a_span": 0,
                "prof_b": views[bv]["contour_mm"], "b_sample": 0, "b_span": 1,
                "axes": ("X", "Z", "Y")}
    return {"mode": "width+side (stations along Z)", "a_view": av, "b_view": bv,
            "prof_a": views[av]["contour_mm"], "a_sample": 1, "a_span": 0,
            "prof_b": views[bv]["contour_mm"], "b_sample": 1, "b_span": 0,
            "axes": ("X", "Y", "Z")}


def station_grid(range_a, range_b, stations=DEFAULT_STATIONS, eps_frac=DEFAULT_EPS_FRAC,
                 distribution=DEFAULT_DISTRIBUTION):
    """兩輪廓取樣軸範圍的**交集**，切 stations 站，兩端各內縮 eps_frac。

    `distribution`：
      'cosine'（預設）——站點在兩端加密、中段放疏（Chebyshev spacing）。輪廓在兩端
                        通常正是曲率最大的地方（圓角、收邊），均勻分站會讓那些弧段
                        只落到 1-2 站，端部直接被切方；余弦分佈把站點集中到曲率高處，
                        是放樣工序的標準做法。
      'uniform'        ——等距；需要嚴格等分（例如規格化節拍）時用。

    內縮的理由：輪廓是封閉折線，掃描線正好切在極值端點（弧的最低點、直邊）時
    會遇到退化情況。scan_spans 另有端點推離保護；這裡的內縮讓站點本身也離開端點。
    """
    lo = max(float(range_a[0]), float(range_b[0]))
    hi = min(float(range_a[1]), float(range_b[1]))
    if hi - lo <= 1e-9:
        raise ValueError(
            "station_grid: the two contours do not overlap on the sampling axis "
            "(a=[%.3f, %.3f], b=[%.3f, %.3f]) — check that both views are in the "
            "same mm frame and share this axis" % (range_a[0], range_a[1],
                                                   range_b[0], range_b[1]))
    stations = int(stations)
    if stations < 2:
        raise ValueError("station_grid: stations must be >= 2, got %d" % stations)
    if distribution not in ("cosine", "uniform"):
        raise ValueError("station_grid: distribution must be 'cosine' or 'uniform', "
                         "got %r" % (distribution,))
    inset = (hi - lo) * float(eps_frac)
    lo2, hi2 = lo + inset, hi - inset
    span = hi2 - lo2
    if distribution == "uniform":
        step = span / float(stations - 1)
        return [lo2 + step * i for i in range(stations)]
    out = []
    for i in range(stations):
        u = 0.5 * (1.0 - math.cos(math.pi * i / float(stations - 1)))
        out.append(lo2 + span * u)
    return out


def scan_spans(contour, sample_idx, span_idx, samples):
    """對每個取樣值做掃描線，以 even-odd 射線法求與多邊形的所有跨度。

    回傳 list[dict]，逐站：
      t       取樣值（sample 軸上的座標）
      spans   所有交點兩兩配對出的區段 [(lo, hi), ...]；空 list = 該站沒有材料
      span    外包絡 (min, max)；spans 為空時是 None
      n_runs  len(spans)；>1 表示該站輪廓有缺口（凹陷），外包絡把它填平了

    even-odd 對「圓角矩形」這種凸輪廓在一條掃描線上必得 2 個交點；對 U 形這類
    凹輪廓在缺口高度會得到 4 個 → 2 段，正是凹缺陷的偵測訊號。

    掃描線正好切在輪廓的極值端點時（例如矩形的上緣、圓角的最低點），even-odd 的
    交點配對會退化——端點處的水平邊被算成 0 次交叉，該站會被誤判成「沒有材料」。
    因此切線落在端點上時往**內側**推一個相對極小量（極值跨度的 1e-9），脫離退化
    但不影響形狀；遠在輪廓外的取樣值不受影響，仍正確回報 span=None。
    """
    pts = [(float(p[sample_idx]), float(p[span_idx])) for p in contour]
    n = len(pts)
    if n < 3:
        raise ValueError("scan_spans: contour needs >= 3 points, got %d" % n)
    s_lo = min(p[0] for p in pts)
    s_hi = max(p[0] for p in pts)
    band = (s_hi - s_lo) * 1e-9 if s_hi > s_lo else 0.0
    out = []
    for t in samples:
        t = float(t)
        y = t
        if band > 0.0:
            if abs(y - s_lo) <= band:
                y = s_lo + band
            elif abs(y - s_hi) <= band:
                y = s_hi - band
        hits = []
        for i in range(n):
            s0, v0 = pts[i]
            s1, v1 = pts[(i + 1) % n]
            if (s0 <= y) != (s1 <= y):
                frac = (y - s0) / (s1 - s0)
                hits.append(v0 + frac * (v1 - v0))
        hits.sort()
        spans = []
        for k in range(0, len(hits) - 1, 2):   # 交點數為奇數時丟掉最後一個（切點退化）
            lo, hi = hits[k], hits[k + 1]
            if hi - lo > 1e-9:
                spans.append((lo, hi))
        if spans:
            out.append({"t": t, "spans": spans, "n_runs": len(spans),
                        "span": (spans[0][0], spans[-1][1])})
        else:
            out.append({"t": t, "spans": [], "n_runs": 0, "span": None})
    return out


# --------------------------------------------------------------------------
# Stage 3-b · 斷面與放樣
# --------------------------------------------------------------------------
def section_polygon(cx, cy, w, h, r, arc_segs=DEFAULT_ARC_SEGS):
    """圓角矩形斷面，**固定** 4*(arc_segs+1) 個頂點、逆時針。

    固定頂點數是逐站橋接的必要條件（相鄰兩站的頂點要一對一）。圓角半徑會被夾在
    半邊短邊之內，且不小於短邊的千分之一——半徑為 0 會讓同一圓角的四個點重合，
    產生退化面。
    """
    a = 0.5 * float(w)
    b = 0.5 * float(h)
    if a <= 0.0 or b <= 0.0:
        raise ValueError("section_polygon: section must have positive size, got w=%s h=%s"
                         % (w, h))
    short = min(a, b)
    rr = min(max(float(r), short * 1e-3), short * 0.999)
    arc_segs = int(arc_segs)
    if arc_segs < 1:
        raise ValueError("section_polygon: arc_segs must be >= 1, got %d" % arc_segs)
    corners = ((cx + (a - rr), cy - (b - rr), -90.0),   # 底右
               (cx + (a - rr), cy + (b - rr), 0.0),     # 頂右
               (cx - (a - rr), cy + (b - rr), 90.0),    # 頂左
               (cx - (a - rr), cy - (b - rr), 180.0))   # 底左
    pts = []
    for ccx, ccy, a0 in corners:
        for k in range(arc_segs + 1):
            ang = math.radians(a0 + k * 90.0 / arc_segs)
            pts.append([ccx + rr * math.cos(ang), ccy + rr * math.sin(ang)])
    return pts


def axis_parity(axes):
    """(u_axis, v_axis, t_axis) 是否為右手序。回傳 +1 / -1。

    左手序（例如 ('X','Z','Y')）若照右手序的斷面點序直接橋接，面法向會整組內翻。
    本檔一律據此決定要不要反轉斷面點序；建完仍會跑 recalc_face_normals 當最終權威，
    這裡先修對是為了讓 mesh 在 recalc 之前就是合理狀態。
    """
    if len(axes) != 3 or len(set(axes)) != 3:
        raise ValueError("axis_parity: axes must be a permutation of X/Y/Z, got %r" % (axes,))
    idx = [AXIS_INDEX[a] for a in axes]
    inv = sum(1 for x in range(3) for y in range(x + 1, 3) if idx[x] > idx[y])
    return 1 if inv % 2 == 0 else -1


def _cap_ring(bm, ring):
    """以全四邊方式封住一圈頂點（n 必須為偶數）。

    作法：環上 n 個頂點 + 一個中心點 c，面為 (r[k], r[k+1], r[k+2], c)，k 逐 2 前進。
    n/2 個面恰好用完 n 條邊界邊；偶數編號的輪輻邊各被相鄰兩個面共用 → 流形、
    且不留任何 n-gon（n-gon 封蓋在細分時會產生難看的扇形）。
    """
    n = len(ring)
    if n % 2 != 0:
        raise ValueError("_cap_ring: ring vertex count must be even, got %d" % n)
    cen = bm.verts.new(tuple(sum(v.co[i] for v in ring) / float(n) for i in range(3)))
    for k in range(0, n, 2):
        bm.faces.new((ring[k], ring[(k + 1) % n], ring[(k + 2) % n], cen))


def _longest_valid_run(sections):
    """回傳 (start, end)；sections 中 None 表示該站沒有材料。全空回傳 (0, -1)。"""
    best = (0, -1)
    cur = None
    for i, s in enumerate(sections):
        if s is not None:
            if cur is None:
                cur = i
        elif cur is not None:
            if i - 1 - cur > best[1] - best[0]:
                best = (cur, i - 1)
            cur = None
    if cur is not None and len(sections) - 1 - cur > best[1] - best[0]:
        best = (cur, len(sections) - 1)
    return best


def build_station_loft(prof_a, prof_b, name="Triview_Loft", *,
                       a_sample, a_span, b_sample, b_span, axes=("X", "Y", "Z"),
                       stations=DEFAULT_STATIONS, corner_radius_mm=None,
                       auto_corner_frac=DEFAULT_AUTO_CORNER_FRAC,
                       arc_segs=DEFAULT_ARC_SEGS, eps_frac=DEFAULT_EPS_FRAC,
                       min_section_mm=DEFAULT_MIN_SECTION_MM,
                       distribution=DEFAULT_DISTRIBUTION,
                       unit=TB.DEFAULT_UNIT, do_bevel=False,
                       bevel_width=TB.DEFAULT_BEVEL_WIDTH,
                       bevel_segments=TB.DEFAULT_BEVEL_SEGMENTS, smooth=True):
    """沿兩張輪廓的共同軸逐站放樣成單一連續 mesh。

    prof_a / prof_b：兩張 2D 輪廓（來自 triview_calib 的 contour_mm）。
    a_sample/a_span：prof_a 的「取樣軸」與「取跨度軸」索引（0=x、1=y）。
    axes：(u_axis, v_axis, t_axis)——a 的跨度值對應哪個世界軸、b 的跨度值對應
          哪個世界軸、站點值對應哪個世界軸。左手序會自動反轉斷面點序。

    回傳 (obj, info)。info 內含站點統計、斷面點數、拓撲統計、是否為估計圓角、
    `max_span_runs`（>1 表示至少有一站的輪廓有缺口，凹陷被外包絡填平）。
    """
    mode_ok, ratio_a = TB.polygon_sanity(prof_a)
    if not mode_ok:
        raise ValueError("build_station_loft: prof_a looks degenerate/self-intersecting "
                         "(area/bbox = %.4f). Check contour winding order." % ratio_a)
    mode_ok, ratio_b = TB.polygon_sanity(prof_b)
    if not mode_ok:
        raise ValueError("build_station_loft: prof_b looks degenerate/self-intersecting "
                         "(area/bbox = %.4f). Check contour winding order." % ratio_b)

    ra = contour_range(prof_a, a_sample)
    rb = contour_range(prof_b, b_sample)
    grid = station_grid(ra, rb, stations=stations, eps_frac=eps_frac,
                        distribution=distribution)
    sa = scan_spans(prof_a, a_sample, a_span, grid)
    sb = scan_spans(prof_b, b_sample, b_span, grid)

    sections = []
    gaps = 0
    max_runs = 1
    for k in range(len(grid)):
        A, B = sa[k], sb[k]
        if A["span"] is None or B["span"] is None:
            sections.append(None)
            gaps += 1
            continue
        w = A["span"][1] - A["span"][0]
        h = B["span"][1] - B["span"][0]
        if min(w, h) < float(min_section_mm):
            sections.append(None)
            gaps += 1
            continue
        max_runs = max(max_runs, A["n_runs"], B["n_runs"])
        sections.append({"t": grid[k],
                         "cx": 0.5 * (A["span"][0] + A["span"][1]),
                         "cy": 0.5 * (B["span"][0] + B["span"][1]),
                         "w": w, "h": h})

    lo, hi = _longest_valid_run(sections)
    if hi < lo:
        raise ValueError("build_station_loft: no station has material on both views "
                         "— the two contours never overlap in the sampled band")

    parity = axis_parity(axes)
    ai, bi, ti = (AXIS_INDEX[a] for a in axes)
    est_radius = corner_radius_mm is None
    design_r = corner_radius_mm
    loops = []
    r_clamped_min = None
    for s in sections[lo:hi + 1]:
        r = (auto_corner_frac * min(s["w"], s["h"])) if est_radius else float(corner_radius_mm)
        r = min(r, 0.499 * min(s["w"], s["h"]))
        r_clamped_min = r if r_clamped_min is None else min(r_clamped_min, r)
        poly = section_polygon(s["cx"], s["cy"], s["w"], s["h"], r, arc_segs)
        if parity < 0:
            poly = list(reversed(poly))
        loops.append((s["t"], poly))

    bm = bmesh.new()
    rings = []
    for t, poly in loops:
        ring = []
        for u, v in poly:
            co = [0.0, 0.0, 0.0]
            co[ai] = u * unit
            co[bi] = v * unit
            co[ti] = t * unit
            ring.append(bm.verts.new(co))
        rings.append(ring)
    nv = len(rings[0])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(nv):
            k2 = (k + 1) % nv
            bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
    _cap_ring(bm, rings[0])
    _cap_ring(bm, list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)

    if do_bevel and bevel_width > 0:
        TB.add_bevel(obj, width=bevel_width, segments=bevel_segments)
    if smooth:
        TB.shade_smooth(obj)

    info = {
        "source_a": {"view": None, "sample_axis": a_sample, "span_axis": a_span,
                     "range": [round(ra[0], 3), round(ra[1], 3)]},
        "source_b": {"view": None, "sample_axis": b_sample, "span_axis": b_span,
                     "range": [round(rb[0], 3), round(rb[1], 3)]},
        "axes": list(axes), "axis_parity": parity,
        "stations_requested": int(stations),
        "stations_used": len(loops),
        "station_span_mm": [round(loops[0][0], 3), round(loops[-1][0], 3)],
        "gap_stations": gaps,
        "distribution": distribution,
        "max_span_runs": max_runs,
        "section_verts": nv,
        "corner_radius_mm": (round(design_r, 3) if design_r is not None
                             else (round(r_clamped_min, 3) if r_clamped_min is not None else None)),
        "corner_radius_clamped_min_mm": (round(r_clamped_min, 3)
                                         if r_clamped_min is not None else None),
        "corner_radius_estimated": bool(est_radius),
        "topology": measure_topology(obj),
    }
    return obj, info


# --------------------------------------------------------------------------
# Stage 4 · 拓撲正規化
# --------------------------------------------------------------------------
def measure_topology(obj):
    """回報四邊/三角/n-gon 面數、非流形邊數與四邊面占比。"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nv = len(bm.verts)
    nf = len(bm.faces)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return {"verts": nv, "faces": nf, "quads": quads, "tris": tris, "ngons": ngons,
            "nonmanifold": nonman, "quad_ratio": round(quads / float(nf), 4) if nf else 0.0}


def quadriflow_retopo(obj, target_faces=None, target_edge_length=None,
                      preserve_boundary=False, symmetry=False, seed=0,
                      op_name="quadriflow_remesh"):
    """以 quadriflow 把 obj 重拓成四邊網格（就地修改）。

    target_faces 給目標面數（mode='FACES'）；target_edge_length 給目標邊長
    （mode='EDGE'，優先）。**target 是目標值不是保證值**——實測 300 會得到 253 面。

    op_name：operator 名稱，預設 'quadriflow_remesh'。拉成參數有兩個現實理由：
    Blender 若在未來版本改名，呼叫端可切換而不必改本檔；自測要能驗證「API 缺席」
    的錯誤路徑（bpy.ops 的子模組不能 `del` 屬性，只能改用查不到的名字）。

    API 不存在時 raise：拓撲正規化是 Stage 4 的核心產出，靜默跳過會讓下游誤以為
    拿到的是乾淨網格，寧可讓呼叫端明確知道這一步沒做。
    """
    op = getattr(bpy.ops.object, op_name, None)
    if op is None:
        raise RuntimeError(
            "quadriflow operator %r unavailable in this Blender build — Stage 4 "
            "topology normalisation cannot run. Needs a build with the quadriflow "
            "solver compiled in (Blender >= 2.81)." % op_name)
    before = {"verts": len(obj.data.vertices), "faces": len(obj.data.polygons)}
    kwargs = {"use_mesh_symmetry": bool(symmetry), "seed": int(seed),
              "use_preserve_sharp": False, "use_preserve_boundary": bool(preserve_boundary),
              "smooth_normals": False}
    if target_edge_length is not None:
        kwargs["mode"] = "EDGE"
        kwargs["target_edge_length"] = float(target_edge_length)
        target = float(target_edge_length)
    else:
        kwargs["mode"] = "FACES"
        kwargs["target_faces"] = int(target_faces if target_faces else 500)
        target = kwargs["target_faces"]
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError:
        pass
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    op(**kwargs)
    return {"before": before, "after": measure_topology(obj),
            "mode": kwargs["mode"], "target": target}


# --------------------------------------------------------------------------
# 報告
# --------------------------------------------------------------------------
def resolve_corner_radius_mm(calib, mode=None, explicit=None):
    """決定斷面圓角半徑，並回報它的來源（**標註 > 知識 > 估計**的優先序）。

    邊緣圓角無法從兩張正交輪廓推導（那是第三個平面的性質），所以這條優先序就是
    「量測拿不到的東西，依序問圖面標註、再問對該品類的知識、最後才退回估計」。

    **務必分清是哪個平面的圓角**（用錯平面等於憑空捏造尺寸）：
      - 斷面所在的平面由 `mode` 決定：width+side 模式的斷面是 (X, Y) 平面（對應
        **俯視圖**的圓角）；top+side 模式的斷面是 (X, Z) 平面（對應**正視圖**的圓角）。
      - **正視圖的外輪廓圓角不是斷面圓角**：它是輪廓在 XZ 平面的收邊，本工作流
        已經由「站點寬度隨輪廓變化」自動重現（前端輪廓在端部變窄 → 放樣出來自然收圓），
        不需要、也不應該再拿去當斷面半徑——那是兩個不同平面的特徵。
      - 找不到對應平面的標註值時回傳 None，交由 `auto_corner_frac` 估計。

    回傳 (radius_mm_or_None, source_str)。
    """
    if explicit is not None:
        return float(explicit), "explicit"
    ann = calib.get("annotated_dims_mm") or {}
    prefer = {"width+side": ("top", "corner_r"),
              "top+side": ("front", "corner_r")}.get(str(mode or "").split(" ")[0])
    order = [prefer] if prefer else []
    order.extend([("top", "corner_r"), ("front", "corner_r")])
    for view, key in order:
        val = (ann.get(view) or {}).get(key)
        if isinstance(val, (int, float)) and val > 0:
            tag = "annotated:%s.%s" % (view, key)
            if prefer and (view, key) != prefer:
                # 用了別人的平面的標註值：標記出來，呼叫端才知道這個半徑不是斷面平面
                # 的權威數字（實際值仍會被 0.499*min(w,h) 夾住，所以可用但要知情）。
                tag += "+plane_mismatch"
            return float(val), tag
    return None, "estimated"


def build_loft_report(obj, calib, loft_info, ortho, closure, retopo_info):
    spec = calib.get("subject", {}).get("spec_mm", {})
    dims = TB.footprint_dims(obj)
    report = {
        "source_calib": calib.get("source", {}),
        "subject": calib.get("subject", {}).get("name"),
        "loft": loft_info,
        "mesh": dims,
        "topology": measure_topology(obj),
        "retopo": retopo_info,
        "ortho": ortho,
        "closure": closure,
        "spec_mm": spec,
        "checks": [],
    }
    for key, ref in (("width_mm", spec.get("width")), ("depth_mm", spec.get("depth")),
                     ("height_mm", spec.get("height"))):
        if ref:
            got = dims[key]
            report["checks"].append({"dim": key, "got_mm": got, "spec_mm": ref,
                                     "rel_err_pct": round(100.0 * (got - ref) / ref, 3)})
    return report


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
def _pop_opt(argv, flag, cast=str):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 >= len(argv):
            raise SystemExit("triview_loft: %s needs a value" % flag)
        val = argv[i + 1]
        del argv[i:i + 2]
        return cast(val)
    return None


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    if len(argv) < 2:
        if "--selftest" in sys.argv:
            checks, fails = _selftest()
            for c in checks:
                print("  ok:", c)
            print("TOTAL_CHECKS_FAILED: %d" % len(fails))
            for f in fails:
                print("  FAIL:", f)
            return 1 if fails else 0
        print("usage: blender --background --python triview_loft.py -- <calib.json> <out_dir>")
        print("       [--stations N] [--a-view front|rear|top] [--corner-radius-mm R]")
        print("       [--no-retopo] [--retopo-faces N]")
        print("       blender --background --python triview_loft.py -- --selftest")
        return 2

    stations = _pop_opt(argv, "--stations", int) or DEFAULT_STATIONS
    a_view = _pop_opt(argv, "--a-view", str)
    corner = _pop_opt(argv, "--corner-radius-mm", float)
    retopo_faces = _pop_opt(argv, "--retopo-faces", int) or 2000
    no_retopo = "--no-retopo" in argv
    if no_retopo:
        argv.remove("--no-retopo")
    calib_path, out_dir = argv[0], argv[1]

    calib = TV.load_calib(calib_path)
    views = calib["views"]
    plan = plan_axes(views, a_view=a_view)
    corner, corner_src = resolve_corner_radius_mm(calib, mode=plan["mode"], explicit=corner)

    TB.scene_reset()
    obj, loft_info = build_station_loft(
        plan["prof_a"], plan["prof_b"], name="Triview_Loft",
        a_sample=plan["a_sample"], a_span=plan["a_span"],
        b_sample=plan["b_sample"], b_span=plan["b_span"], axes=plan["axes"],
        stations=stations, corner_radius_mm=corner)
    loft_info["mode"] = plan["mode"]
    loft_info["source_a"]["view"] = plan["a_view"]
    loft_info["source_b"]["view"] = plan["b_view"]
    loft_info["corner_radius_source"] = corner_src

    dims = TB.footprint_dims(obj)
    center = TB.world_center(obj)
    view_mm = max(dims["height_mm"], dims["width_mm"], dims["depth_mm"]) * 1.25
    res = (900, 900)
    os.makedirs(out_dir, exist_ok=True)
    TB._ensure_sun()   # 重用 triview_build 的場景光源（幾何端共用工具層）
    p_front = TB.render_ortho("front", os.path.join(out_dir, "loft_ortho_front.png"),
                              view_mm, res=res, center=center)
    p_side = TB.render_ortho("side", os.path.join(out_dir, "loft_ortho_side.png"),
                             view_mm, res=res, center=center)
    m_front = TB.measure_render(p_front, view_mm, res)
    m_side = TB.measure_render(p_side, view_mm, res)

    closure = {
        "front": TB.silhouette_iou(p_front, view_mm, views.get("front", {}).get("contour_mm", [])),
        "side": TB.silhouette_iou(p_side, view_mm, views.get("side", {}).get("contour_mm", [])),
    }
    retopo_info = None
    if not no_retopo:
        retopo_info = quadriflow_retopo(obj, target_faces=retopo_faces)

    report = build_loft_report(obj, calib, loft_info,
                               {"view_mm": view_mm, "res": list(res),
                                "front": m_front, "side": m_side},
                               closure, retopo_info)
    report_path = os.path.join(out_dir, "triview_loft_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    tol = float(os.environ.get("TRIVIEW_TOL_PCT", "2.0"))
    spec_ok = True
    try:
        TB.assert_spec(report, rel_tol_pct=tol, label="triview_loft")
    except AssertionError as exc:
        spec_ok = False
        print("SPEC_ASSERT_FAIL: %s" % exc)

    iou_min = float(os.environ.get("TRIVIEW_IOU_MIN", str(DEFAULT_IOU_MIN)))
    closure_ok = True
    for tag in ("front", "side"):
        try:
            TB.assert_iou(closure[tag], iou_min, label="triview_loft:%s" % tag)
        except AssertionError as exc:
            closure_ok = False
            print("CLOSURE_ASSERT_FAIL: %s" % exc)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "triview_loft.blend"))
    print("SCENE_STATE:" + json.dumps({
        "mesh": dims, "loft": {k: loft_info[k] for k in
                               ("mode", "stations_used", "gap_stations", "distribution",
                                "max_span_runs", "corner_radius_mm",
                                "corner_radius_clamped_min_mm",
                                "corner_radius_estimated", "corner_radius_source",
                                "section_verts")},
        "topology": measure_topology(obj), "retopo": retopo_info,
        "render_front": m_front, "render_side": m_side,
        "closure": closure, "iou_min": iou_min,
        "spec_assert_ok": spec_ok, "closure_assert_ok": closure_ok, "tol_pct": tol}))
    print("REPORT:" + report_path)
    if not spec_ok:
        print("TRIVIEW_LOFT_FAILED_SPEC")
        return 3
    if not closure_ok:
        print("TRIVIEW_LOFT_FAILED_CLOSURE")
        return 4
    print("TRIVIEW_LOFT_OK")
    return 0


# --------------------------------------------------------------------------
# 自測
# --------------------------------------------------------------------------
def _rect(w, h, cx=0.0):
    """無圓角矩形輪廓（逆時針），供解析解比對。"""
    x0, x1 = cx - w / 2.0, cx + w / 2.0
    return [[x0, 0.0], [x1, 0.0], [x1, h], [x0, h]]


def _u_notch(w, h, notch_w, notch_h):
    """U 形（頂部中央挖一個缺口）輪廓，逆時針——用於驗證凹陷偵測。"""
    x0, x1 = -w / 2.0, w / 2.0
    n0, n1 = -notch_w / 2.0, notch_w / 2.0
    y0 = h - notch_h
    return [[x0, 0.0], [x1, 0.0], [x1, h], [n1, h], [n1, y0], [n0, y0], [n0, h], [x0, h]]


def _rounded(w, h, r, cx=0.0, arc_segs=8):
    """圓角矩形輪廓（逆時針），角落依序：底左→底右→頂右→頂左。"""
    x0, x1 = cx - w / 2.0, cx + w / 2.0
    y0, y1 = 0.0, h
    arcs = (((x0 + r, y0 + r), 180.0), ((x1 - r, y0 + r), 270.0),
            ((x1 - r, y1 - r), 0.0), ((x0 + r, y1 - r), 90.0))
    pts = []
    for (ccx, ccy), a0 in arcs:
        for k in range(arc_segs + 1):
            a = math.radians(a0 + k * 90.0 / arc_segs)
            pts.append([ccx + r * math.cos(a), ccy + r * math.sin(a)])
    return pts


def _selftest():
    """合成資料驗證掃描層與放樣層（不需外部檔案）。"""
    checks, fails = [], []

    def chk(name, cond, detail=""):
        checks.append(name)
        if not cond:
            fails.append("%s %s" % (name, detail))

    # --- 掃描層 -----------------------------------------------------------
    rect = _rect(80.0, 170.0)
    spans = scan_spans(rect, 1, 0, [85.0, 0.0, 170.0])
    chk("scan.rect_mid_span", abs((spans[0]["span"][1] - spans[0]["span"][0]) - 80.0) < 1e-6,
        "span=%s" % (spans[0]["span"],))
    chk("scan.rect_mid_runs", spans[0]["n_runs"] == 1, "n_runs=%d" % spans[0]["n_runs"])
    chk("scan.rect_endpoint", spans[1]["span"] is not None
        and abs((spans[1]["span"][1] - spans[1]["span"][0]) - 80.0) < 1e-6,
        "span=%s" % (spans[1]["span"],))

    outside = scan_spans(rect, 1, 0, [500.0])
    chk("scan.outside_is_none", outside[0]["span"] is None and outside[0]["n_runs"] == 0,
        "span=%s" % (outside[0]["span"],))

    rnd = _rounded(80.0, 170.0, 12.0)
    s_mid = scan_spans(rnd, 1, 0, [85.0])[0]
    chk("scan.rounded_mid", abs((s_mid["span"][1] - s_mid["span"][0]) - 80.0) < 0.5,
        "w=%.3f" % (s_mid["span"][1] - s_mid["span"][0],))
    # z=6 落在下緣圓角區（圓角中心在 z=12）：解析寬度 = 2*(28 + sqrt(12²−6²))
    want_arc = 2.0 * (28.0 + math.sqrt(144.0 - 36.0))
    s_arc = scan_spans(rnd, 1, 0, [6.0])[0]
    chk("scan.rounded_arc", abs((s_arc["span"][1] - s_arc["span"][0]) - want_arc) < 0.5,
        "got %.3f want %.3f" % (s_arc["span"][1] - s_arc["span"][0], want_arc))

    u = _u_notch(80.0, 170.0, 20.0, 70.0)
    su = scan_spans(u, 1, 0, [120.0, 50.0])
    chk("scan.notch_two_runs", su[0]["n_runs"] >= 2, "n_runs=%d" % su[0]["n_runs"])
    chk("scan.notch_envelope", abs((su[0]["span"][1] - su[0]["span"][0]) - 80.0) < 1e-6,
        "env=%s" % (su[0]["span"],))
    chk("scan.below_notch_one_run", su[1]["n_runs"] == 1, "n_runs=%d" % su[1]["n_runs"])

    # --- 站點格 -----------------------------------------------------------
    g = station_grid((0.0, 170.0), (0.0, 170.0), stations=5, eps_frac=0.0)
    chk("grid.endpoints", abs(g[0] - 0.0) < 1e-9 and abs(g[-1] - 170.0) < 1e-9, "g=%s" % (g,))
    g2 = station_grid((0.0, 170.0), (0.0, 170.0), stations=5, eps_frac=0.002)
    chk("grid.inset", g2[0] > 0.0 and g2[-1] < 170.0, "g=%s" % (g2,))
    try:
        station_grid((0.0, 10.0), (20.0, 30.0), stations=5)
        chk("grid.disjoint_raises", False, "should have raised")
    except ValueError as exc:
        chk("grid.disjoint_raises", "do not overlap" in str(exc), "msg=%s" % exc)

    # --- 斷面 -------------------------------------------------------------
    poly = section_polygon(0.0, 0.0, 80.0, 10.0, 4.0, arc_segs=4)
    chk("section.fixed_count", len(poly) == 4 * (4 + 1), "n=%d" % len(poly))
    chk("section.ccw", TV.polygon_area(poly) > 0.0, "area=%.3f" % TV.polygon_area(poly))
    chk("section.extent", abs(max(p[0] for p in poly) - 40.0) < 1e-9
        and abs(max(p[1] for p in poly) - 5.0) < 1e-9,
        "bbox=%s" % ([min(p[0] for p in poly), max(p[0] for p in poly)],))

    # --- 放樣層（解析解：80 × 10 斷面 × 170 高） ---------------------------
    TB.scene_reset()
    obj, info = build_station_loft(_rect(80.0, 170.0), _rect(10.0, 170.0),
                                   name="ST_Loft", a_sample=1, a_span=0,
                                   b_sample=1, b_span=0, axes=("X", "Y", "Z"),
                                   stations=17, eps_frac=0.0, corner_radius_mm=4.0,
                                   arc_segs=4)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    vol = bm.calc_volume(signed=True) * 1e9
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    r = 4.0
    expect = (80.0 * 10.0 - (4.0 - math.pi) * r * r) * 170.0
    chk("loft.volume_within_2pct", abs(vol - expect) / expect < 0.02,
        "got %.0f want %.0f" % (vol, expect))
    chk("loft.signed_volume_positive", vol > 0.0, "vol=%.0f (normals inward?)" % vol)
    chk("loft.nonmanifold_zero", nonman == 0, "nonmanifold=%d" % nonman)
    tp = info["topology"]
    chk("loft.all_quads", tp["quad_ratio"] == 1.0,
        "quads=%d tris=%d ngons=%d" % (tp["quads"], tp["tris"], tp["ngons"]))
    d = TB.footprint_dims(obj)
    chk("loft.dims", abs(d["width_mm"] - 80.0) < 0.5 and abs(d["depth_mm"] - 10.0) < 0.5
        and abs(d["height_mm"] - 170.0) < 0.5,
        "got w%.2f d%.2f h%.2f" % (d["width_mm"], d["depth_mm"], d["height_mm"]))
    chk("loft.section_verts", info["section_verts"] == 20, "nv=%d" % info["section_verts"])
    chk("loft.no_gaps", info["gap_stations"] == 0, "gaps=%d" % info["gap_stations"])
    chk("loft.radius_not_estimated", info["corner_radius_estimated"] is False)

    # 凹陷：U 形寬度輪廓 → 缺口高度必須被回報（外包絡填平的真實代價）
    TB.scene_reset()
    obj2, info2 = build_station_loft(_u_notch(80.0, 170.0, 20.0, 70.0),
                                     _rect(10.0, 170.0),
                                     name="ST_Notch", a_sample=1, a_span=0,
                                     b_sample=1, b_span=0, axes=("X", "Y", "Z"),
                                     stations=17, eps_frac=0.0, corner_radius_mm=3.0)
    chk("loft.notch_reported", info2["max_span_runs"] >= 2,
        "max_span_runs=%d" % info2["max_span_runs"])

    # 軸向奇偶：左手序 ('X','Z','Y') 仍須外翻（以 signed volume > 0 驗證）
    chk("parity.right_handed", axis_parity(("X", "Y", "Z")) == 1)

    # 圓角半徑來源優先序：顯式 > 對應平面的圖面標註 > 估計
    ann = {"annotated_dims_mm": {"front": {"corner_r": 11.7},
                                 "top": {"corner_r": 8.0},
                                 "rear": {"plateau_corner_r": 11.96}}}
    chk("cfgr.explicit_wins",
        resolve_corner_radius_mm(ann, mode="width+side", explicit=5.0)[0] == 5.0)
    chk("cfgr.section_plane_matched",
        resolve_corner_radius_mm(ann, mode="width+side") == (8.0, "annotated:top.corner_r")
        and resolve_corner_radius_mm(ann, mode="top+side") == (11.7, "annotated:front.corner_r"),
        "width+side=%s top+side=%s" % (resolve_corner_radius_mm(ann, mode="width+side"),
                                       resolve_corner_radius_mm(ann, mode="top+side")))
    chk("cfgr.estimate_when_absent",
        resolve_corner_radius_mm({}, mode="width+side") == (None, "estimated"),
        "got %s" % (resolve_corner_radius_mm({}, mode="width+side"),))
    chk("cfgr.plane_mismatch_flagged",
        resolve_corner_radius_mm({"annotated_dims_mm": {"front": {"corner_r": 11.7}}},
                                 mode="width+side") == (11.7, "annotated:front.corner_r+plane_mismatch"),
        "front-view rounding is a different plane; usable only as flagged last resort")
    chk("parity.left_handed", axis_parity(("X", "Z", "Y")) == -1)
    try:
        axis_parity(("X", "X", "Y"))
        chk("parity.rejects_bad_axes", False, "should have raised")
    except ValueError:
        chk("parity.rejects_bad_axes", True)

    TB.scene_reset()
    top = _rect(80.0, 10.0)              # 俯視 (x, y)：x ∈ [-40, 40]、y ∈ [0, 10]
    side = _rect(10.0, 170.0, cx=5.0)    # 側視 (y, z)：y ∈ [0, 10]、z ∈ [0, 170]
    obj3, info3 = build_station_loft(top, side, name="ST_LH", a_sample=1, a_span=0,
                                     b_sample=0, b_span=1, axes=("X", "Z", "Y"),
                                     stations=17, eps_frac=0.0, corner_radius_mm=4.0)
    bm = bmesh.new()
    bm.from_mesh(obj3.data)
    vol3 = bm.calc_volume(signed=True) * 1e9
    nonman3 = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    d3 = TB.footprint_dims(obj3)
    chk("loft.lefthanded_volume_positive", vol3 > 0.0, "vol=%.0f" % vol3)
    chk("loft.lefthanded_manifold", nonman3 == 0, "nonmanifold=%d" % nonman3)
    chk("loft.lefthanded_dims",
        abs(d3["width_mm"] - 80.0) < 0.5 and abs(d3["depth_mm"] - 10.0) < 0.5
        and abs(d3["height_mm"] - 170.0) < 0.5,
        "got w%.2f d%.2f h%.2f" % (d3["width_mm"], d3["depth_mm"], d3["height_mm"]))
    chk("loft.lefthanded_parity_flag", info3["axis_parity"] == -1)

    # 退化守衛：蝴蝶結輪廓必須被擋下
    TB.scene_reset()
    try:
        build_station_loft([[0, 0], [10, 10], [10, 0], [0, 10]], _rect(10.0, 170.0),
                           name="ST_Bad", a_sample=1, a_span=0, b_sample=1, b_span=0)
        chk("loft.degenerate_raises", False, "should have raised")
    except ValueError as exc:
        chk("loft.degenerate_raises", "degenerate" in str(exc), "msg=%s" % exc)

    # --- Stage 4 ----------------------------------------------------------
    TB.scene_reset()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.active_object
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=2.0)
    cyl = bpy.context.active_object
    mod = cube.modifiers.new("Bool", 'BOOLEAN')
    mod.operation = 'INTERSECT'
    mod.solver = 'MANIFOLD'
    mod.object = cyl
    for o in bpy.context.selected_objects:
        o.select_set(False)
    cube.select_set(True)
    bpy.context.view_layer.objects.active = cube
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cyl, do_unlink=True)
    before_quads = measure_topology(cube)["quad_ratio"]
    res = quadriflow_retopo(cube, target_faces=200)
    chk("retopo.nonmanifold_zero", res["after"]["nonmanifold"] == 0,
        "nonmanifold=%d" % res["after"]["nonmanifold"])
    chk("retopo.all_quads", res["after"]["quad_ratio"] >= 0.95,
        "quad_ratio=%.4f" % res["after"]["quad_ratio"])
    chk("retopo.actually_changed", before_quads < 1.0 and res["after"]["faces"] > 0,
        "before_quad_ratio=%.3f after_faces=%d" % (before_quads, res["after"]["faces"]))
    chk("retopo.mode_reported", res["mode"] == "FACES" and res["target"] == 200)

    pure = measure_topology(cube)
    chk("retopo.measure_pure_quads", pure["quad_ratio"] == 1.0,
        "quad_ratio=%.4f" % pure["quad_ratio"])

    try:
        quadriflow_retopo(cube, target_faces=100, op_name="__missing_quadriflow_op__")
        chk("retopo.missing_api_raises", False, "should have raised")
    except RuntimeError as exc:
        chk("retopo.missing_api_raises", "quadriflow" in str(exc), "msg=%s" % exc)

    return checks, fails


if __name__ == "__main__":
    sys.exit(main())
