# -*- coding: utf-8 -*-
# KEYWORDS: blender, triview, blueprint, annotation, svg, contour, 平面圖, 標註, 元件表, 檢查圖
"""
blueprint_lib.py — 三視圖「標註平面圖」產生器（Stage A.5 檢查介面 / Stage C 比對圖）。

定位
----
triview_lib.py 把圖變成輪廓；triview_build.py / triview_loft.py 把輪廓變成幾何。
本模組補上兩者之間（以及幾何之後）缺的那一環：**一張人可以指著它說話的圖**。

它把量測輪廓畫回原圖（輪廓疊圖），並在圖上打兩類可引用編號：

  * 元件標註  A-1 / A-2 …（來自 Stage A 元件表：名稱、尺寸、備註、內縮狀態）
  * 特徵標註  F1 / F2 …（把輪廓切成「直線／曲線／轉折點／短邊」並逐一編號，
               附長度、弦偏差、轉折角、估算半徑）

兩個使用時機
------------
1. **Stage A 之後、Stage B 之前**：元件表還是文字時先出圖。人類可中途檢查
   「A-3 的位置不對」「F7 這條曲線不對」——用編號回報，不必描述座標。
2. **Stage C**：把回渲輪廓餵進來（`extra_contours`），同一份編號疊圖比對——
   尺寸與 IoU 之外，多一個人眼可讀的提示：「F2 這條差 3mm」。

輸出
----
  <out>/blueprint_<view>.svg   向量版（含圖例表），可縮放、可再編輯、可分享
  <out>/blueprint_<view>.png   點陣預覽（小字級，元件多時仍可讀）
  <out>/blueprint_data.json    機器可讀：特徵表 + 元件表 + 內縮檢查結果

執行環境
--------
純 Python 3 + numpy + Pillow，**不需要 bpy**（與 triview_lib 同一先例）。
Pillow 延遲載入，故 Blender 端仍可 import 本模組只為讀資料。
輸出只寫到呼叫端指定的目錄（一律在 workspace 內的 .capybala/），不寫入 skill_dir。

座標與單位公約
--------------
- 量測資料一律 **mm**，座標系同 triview_calib 的 `contour_mm`：
  原點＝該視圖 bbox 底部中心，x 向右、y 向上（與 SKILL.md §12 「正面朝 -Y」一致）。
- 繪圖座標（sheet px）只存在於 build_annotations() 之後；mm↔px 一律走
  `mm_to_px()` / `px_to_mm()`，不要在別處手算比例。

已知限制（誠實記錄）
--------------------
1. 特徵切分是**幾何啟發式**：先取轉折角 ≥ corner_min_deg 的尖角，再對尖角之間
   （整圈無尖角時為全部）的折線做「直線 vs 圓弧」貪婪擬合，切出 LINE／CURVE
   分段——不是 CAD 特徵辨識。圓弧半徑是取樣三點的外接圓估計值；切點會落在
   交界處的 ±1 個取樣點內。
2. 輪廓本身來自 triview_lib 的簡化折線（Douglas-Peucker），比對原圖帶有簡化
   誤差；短於 min_feature_mm 的細節標成 SHORT 但**仍保留編號**，不靜默丟棄。
3. 標籤避讓用「字元數 × 字級」估算字寬，不是真實字型度量；極端密集時仍可能
   重疊，會計數並回報 `label_overlaps`。
4. 內縮檢查只驗證「元件 bbox 是否落在量測輪廓內」，不驗證 bbox 內容是否正確。
5. 未提供原圖時仍可出圖（純向量版），但沒有輪廓疊圖可看。
"""

from __future__ import annotations

import base64
import io
import json
import math
import os
import sys
import time

import numpy as np

try:  # triview_lib 是同層資產；缺席時只影響 calib 讀寫
    import triview_lib as TV  # noqa: N816 (reserved alias per SKILL.md §16.2)
except ImportError:  # pragma: no cover - 只在使用 load_calib 時才需要
    TV = None

BP_SCHEMA = "triview_blueprint/1"
COMPONENTS_SCHEMA = "blueprint_components/1"

# --- 預設值（呼叫端一律用具名參數覆寫，不要在函式體內散落魔法數字） ---
DEFAULT_CORNER_MIN_DEG = 25.0      # 轉折 ≥ 此角度 → 一個 CORNER feature
DEFAULT_MIN_FEATURE_MM = 0.6       # 短於此長度 → SHORT（仍保留編號）
DEFAULT_FIT_TOL_MM = 0.35          # 特徵切分前的折線擬合容差（先擬合、後編號）
DEFAULT_STRAIGHT_TOL_FRAC = 0.0015  # 直線／圓弧擬合容差：中段最大偏移 ≤ 弦長 × 此值
DEFAULT_STRAIGHT_TOL_MIN_MM = 0.10
DEFAULT_FONT_PX = 10.0             # 主標註字級（元件多時往下調）
DEFAULT_LEGEND_FONT_PX = 10.0
DEFAULT_CROP_MARGIN_PX = 36        # 裁圖留邊（保留周邊尺寸線脈絡）
DEFAULT_SHEET_MARGIN_PX = 28
DEFAULT_LEGEND_W_PX = 470
DEFAULT_GUTTER_PX = 26
DEFAULT_CONTAIN_TOL_MM = 0.4       # 元件 bbox 允許凸出量測輪廓的容差
DEFAULT_MIN_AREA_FRAC = 0.97       # 元件 bbox 落在輪廓內的最低面積比例
DEFAULT_RASTER_SCALE = 4.0         # px/mm，面積交集計算用
CONTAIN_MARGIN_MM = 4.0            # 柵格留邊
DEFAULT_PNG_SCALE = 2.0
DEFAULT_MAJOR_MIN_MM = 3.0       # 短於此長度的線段算次要：不標在圖上，但保留編號
DEFAULT_SPIKE_MIN_DEG = 150.0    # 折返角 ≥ 此值 → SPIKE（輪廓萃取的尖刺雜訊）
DEFAULT_LABEL_MINOR = False      # 預設只標主要特徵，元件多時圖面才讀得下去

FONT_CANDIDATES_CJK = ("msjh.ttc", "msyh.ttc", "msjhl.ttc",
                       "NotoSansCJK-Regular.ttc", "PingFang.ttc", "Arial Unicode.ttf")
FONT_CANDIDATES_LATIN = ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "Helvetica.ttc")
SVG_FONT_STACK = "Segoe UI, Microsoft JhengHei, Helvetica, Arial, sans-serif"

COL_CONTOUR = "#d81f26"
COL_MODEL = "#1f6fd8"
COL_COMPONENT = "#0a7d3c"
COL_LEADER = "#7a7a7a"
COL_INK = "#111111"
COL_DIM = "#555555"

KIND_LABEL = {"LINE": "直線", "CURVE": "曲線", "CORNER": "轉折", "SHORT": "短邊",
              "SPIKE": "折返"}
VIEW_LETTER = {"front": "F", "rear": "R", "side": "S", "top": "T", "back": "B"}


# --------------------------------------------------------------------------
# Pillow 延遲載入與字型
# --------------------------------------------------------------------------
def _pil():
    from PIL import Image, ImageDraw, ImageFont  # noqa: WPS433 (lazy by design)
    return Image, ImageDraw, ImageFont


_FONT_CACHE = {}
_FONT_WARNED = []


def _font_dirs():
    dirs = []
    win = os.environ.get("WINDIR")
    if win:
        dirs.append(os.path.join(win, "Fonts"))
    dirs += ["/System/Library/Fonts", "/Library/Fonts",
             "/usr/share/fonts/truetype", "/usr/share/fonts"]
    return [d for d in dirs if os.path.isdir(d)]


def load_font(size_px):
    """回傳 (font, cjk_ok)。找不到 TrueType 時退回 Pillow 內建點陣字並回報 False。"""
    key = max(6, int(round(size_px)))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    Image, _, ImageFont = _pil()
    dirs = _font_dirs()
    for name in FONT_CANDIDATES_CJK + FONT_CANDIDATES_LATIN:
        for d in dirs:
            path = os.path.join(d, name)
            if os.path.isfile(path):
                try:
                    font = ImageFont.truetype(path, key)
                    _FONT_CACHE[key] = (font, name in FONT_CANDIDATES_CJK)
                    return _FONT_CACHE[key]
                except Exception:  # noqa: BLE001 - 換下一個候選字型
                    pass
        try:  # fontconfig 依名稱解析（Linux/macOS 常見）
            font = ImageFont.truetype(name, key)
            _FONT_CACHE[key] = (font, name in FONT_CANDIDATES_CJK)
            return _FONT_CACHE[key]
        except Exception:  # noqa: BLE001
            pass
    if not _FONT_WARNED:
        _FONT_WARNED.append(True)
        print("WARNING: blueprint_lib: no TrueType font found; using bitmap default "
              "(non-ASCII labels will be replaced with '?')")
    _FONT_CACHE[key] = (ImageFont.load_default(), False)
    return _FONT_CACHE[key]


def _ascii_fallback(text):
    return "".join(ch if ord(ch) < 128 else "?" for ch in text)


# --------------------------------------------------------------------------
# 幾何工具（純 mm 空間）
# --------------------------------------------------------------------------
def _r2(seq):
    return [round(float(v), 4) for v in seq]


def polygon_area(pts):
    """Shoelace（mm 空間，y 向上）。正＝逆時針。"""
    pts = list(pts)
    n = len(pts)
    if n < 3:
        return 0.0
    acc = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        acc += float(x0) * float(y1) - float(x1) * float(y0)
    return 0.5 * acc


def polyline_length(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def dedupe(pts, eps_mm=0.05):
    """移除重合點（含首尾重合），保留順序。"""
    out = []
    for p in pts:
        p = [float(p[0]), float(p[1])]
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps_mm:
            out.append(p)
    if len(out) > 2 and math.hypot(out[-1][0] - out[0][0], out[-1][1] - out[0][1]) <= eps_mm:
        out.pop()
    return out


def turn_signed_deg(p0, p1, p2):
    """在 p1 的帶號轉折角（度）。正＝往逆時針偏（左轉）。"""
    ax, ay = p1[0] - p0[0], p1[1] - p0[1]
    bx, by = p2[0] - p1[0], p2[1] - p1[1]
    la = math.hypot(ax, ay)
    lb = math.hypot(bx, by)
    if la < 1e-9 or lb < 1e-9:
        return 0.0
    cosv = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
    ang = math.degrees(math.acos(cosv))
    return ang if (ax * by - ay * bx) > 0 else -ang


def max_perp_dev(seg):
    """中段點到首尾弦的最大垂直距離（mm）——直線/曲線判定的依據。"""
    if len(seg) < 3:
        return 0.0
    p0 = seg[0]
    p1 = seg[-1]
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return max(math.hypot(p[0] - p0[0], p[1] - p0[1]) for p in seg)
    return max(abs(dy * (p[0] - p0[0]) - dx * (p[1] - p0[1])) / L for p in seg)


def circum_radius(a, b, c):
    """三點外接圓半徑（mm）。共線或退化時回 None。"""
    ax, ay = a
    bx, by = b
    cx, cy = c
    A = math.hypot(bx - ax, by - ay)
    B = math.hypot(cx - bx, cy - by)
    C = math.hypot(cx - ax, cy - ay)
    area2 = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
    if area2 < 1e-9 or min(A, B, C) < 1e-9:
        return None
    return (A * B * C) / (2.0 * area2)


def _circle_from_3(a, b, c):
    """三點外接圓圓心。共線／退化時回 None。"""
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    cx, cy = float(c[0]), float(c[1])
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    return [ux, uy]


def _fit_dev(seg):
    """回傳 (直線擬合最大偏差, 圓弧擬合最大偏差, 圓半徑, 圓心)。"""
    dev_line = max_perp_dev(seg)
    if len(seg) >= 3:
        center = _circle_from_3(seg[0], seg[len(seg) // 2], seg[-1])
        if center is not None:
            radius = math.hypot(seg[0][0] - center[0], seg[0][1] - center[1])
            dev_arc = max(abs(math.hypot(p[0] - center[0], p[1] - center[1]) - radius)
                          for p in seg)
            return dev_line, dev_arc, radius, center
    return dev_line, float("inf"), None, None


def _decompose_run(run_pts, tol_frac, tol_min):
    """把一段折線貪婪地切成「直線／圓弧」混合（每段都必須落在擬合容差內）。

    回傳 [{'i0','i1','kind','radius','center'}]，索引為 run_pts 內的相對索引。
    這是啟發式分段（線／弧二選一），不是 CAD 特徵辨識。

    關鍵細節：**任意三點都恰可配出一個圓**，所以 3 點以下的視窗無法判別線或弧。
    視窗不足 4 點時，連同後面第 4 點一起擬合再判（borrowed probe），否則直邊末端
    一定會被「配得出來的大半徑圓」吃掉。
    """
    out = []
    m = len(run_pts)
    i = 0
    while i < m - 1:
        best = {"i0": i, "i1": i + 1, "kind": "LINE", "radius": None, "center": None}
        j = i + 1
        while j < m:
            sub = run_pts[i:j + 1]
            n = len(sub)
            probe = run_pts[i:j + 3] if (n < 4 and j + 3 <= m) else sub
            dl, da, p_radius, p_center = _fit_dev(probe)
            tol = max(tol_min, polyline_length(probe) * tol_frac)
            if n >= 3 and min(dl, da) > tol:
                break
            if n <= 2:
                best.update({"kind": "LINE", "radius": None, "center": None})
            elif n == 3:
                best.update({"kind": "CURVE" if da < dl else "LINE",
                             "radius": p_radius, "center": p_center})
            else:
                dl2, da2, radius2, center2 = _fit_dev(sub)
                best.update({"kind": "CURVE" if da2 < dl2 else "LINE",
                             "radius": radius2, "center": center2})
            best["i1"] = j
            j += 1
        out.append(best)
        i = best["i1"] if best["i1"] > i else i + 1
    # 收尾：末端 2 點殘段若落在前一段的圓上，併回前一段（消除圓形接縫處的小碎段）
    while len(out) >= 2:
        last, prev = out[-1], out[-2]
        if not ((last["i1"] - last["i0"] + 1) <= 2 and prev["kind"] == "CURVE"
                and prev["center"]):
            break
        radius = prev["radius"]
        tol_arc = max(tol_min, 0.01 * radius)
        tail = run_pts[last["i0"]:last["i1"] + 1]
        if not all(abs(math.hypot(p[0] - prev["center"][0], p[1] - prev["center"][1]) - radius)
                   <= tol_arc for p in tail):
            break
        prev["i1"] = last["i1"]
        out.pop()
    return out


def _fit_break_indices(pts, tol_frac, tol_min):
    """封閉輪廓上「直線／圓弧切換」的索引（無尖角輪廓的補充分段點）。"""
    n = len(pts)
    if n < 4:
        return []
    loop = list(pts) + [pts[0]]
    subs = _decompose_run(loop, tol_frac, tol_min)
    return sorted({int(s["i1"]) % n for s in subs})


def point_in_polygon(pt, poly):
    """射線法。邊界上算「內」。"""
    x, y = float(pt[0]), float(pt[1])
    n = len(poly)
    inside = False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xin = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xin:
                inside = not inside
    return inside


def dist_to_polygon(pt, poly):
    """點到多邊形邊界的最短距離（mm）。"""
    px, py = float(pt[0]), float(pt[1])
    best = float("inf")
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 <= 1e-12:
            d = math.hypot(px - ax, py - ay)
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        if d < best:
            best = d
    return best


def outward_normal(p0, p1, positive_area):
    """弦 p0→p1 的外法向單位向量（mm 空間）。正面積＝逆時針。"""
    dx = float(p1[0]) - float(p0[0])
    dy = float(p1[1]) - float(p0[1])
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return [0.0, -1.0]
    nx, ny = (dy / L, -dx / L) if positive_area else (-dy / L, dx / L)
    return [nx, ny]


def point_at_half(seg):
    """折線中點（沿弧長走到一半處）。"""
    if len(seg) == 1:
        return [float(seg[0][0]), float(seg[0][1])]
    total = polyline_length(seg)
    if total <= 1e-9:
        return [float(seg[0][0]), float(seg[0][1])]
    half = total / 2.0
    walked = 0.0
    for i in range(len(seg) - 1):
        a, b = seg[i], seg[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if walked + L >= half:
            t = (half - walked) / L if L > 1e-9 else 0.0
            return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
        walked += L
    return [float(seg[-1][0]), float(seg[-1][1])]


def _rasterize(pts, x_min, y_min, w, h, ppmm):
    """多邊形 → 布林柵格（純 numpy/math，不依賴 Pillow）。"""
    mask = np.zeros((h, w), dtype=bool)
    n = len(pts)
    poly = [((float(p[0]) - x_min) * ppmm, (float(p[1]) - y_min) * ppmm) for p in pts]
    for j in range(h):
        yc = j + 0.5
        xs = []
        for i in range(n):
            xa, ya = poly[i]
            xb, yb = poly[(i + 1) % n]
            if (ya > yc) != (yb > yc):
                xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            a = max(0, int(math.ceil(xs[k] - 0.5)))
            b = min(w, int(math.floor(xs[k + 1] - 0.5)) + 1)
            if b > a:
                mask[j, a:b] = True
    return mask


# --------------------------------------------------------------------------
# calib ↔ px 映射（與 triview_lib.to_mm_contour 互為反函式）
# --------------------------------------------------------------------------
def mm_to_px(view, pt):
    """mm → 原圖像素。與 triview_lib.to_mm_contour(origin='bbox_bottom_center') 對應。"""
    x0, y0, x1, y1 = [float(v) for v in view["bbox_px"]]
    ppm = float(view["px_per_mm"])
    cx = x0 + (x1 - x0) / 2.0
    return [cx + float(pt[0]) * ppm, y1 - float(pt[1]) * ppm]


def px_to_mm(view, pt):
    """原圖像素 → mm（mm_to_px 的反函式，供往返自檢與外部換算）。"""
    x0, y0, x1, y1 = [float(v) for v in view["bbox_px"]]
    ppm = float(view["px_per_mm"])
    cx = x0 + (x1 - x0) / 2.0
    return [(float(pt[0]) - cx) / ppm, (y1 - float(pt[1])) / ppm]


def _load_calib(path):
    if TV is None:
        raise RuntimeError("blueprint_lib: needs triview_lib (sibling asset) to read calib JSON")
    return TV.load_calib(path)


# --------------------------------------------------------------------------
# 特徵切分：輪廓 → F1..Fn（直線 / 曲線 / 轉折 / 短邊）
# --------------------------------------------------------------------------
def _perp_dist_to_line(pt, a, b):
    """點到直線 a→b 的（無限延伸）垂直距離（mm）；a==b 時退回點距。"""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 <= 1e-12:
        return math.hypot(pt[0] - ax, pt[1] - ay)
    t = ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L2
    ex, ey = ax + t * dx, ay + t * dy
    return math.hypot(pt[0] - ex, pt[1] - ey)


def fit_polyline(pts_mm, tol_mm=DEFAULT_FIT_TOL_MM, min_edge_mm=DEFAULT_MIN_FEATURE_MM):
    """短邊合併（封閉輪廓）：把階梯雜訊併回它本來代表的那條線／弧。

    **先擬合、後編號**：工程圖輪廓沿邊界常是 1px 一階的階梯（@5.5px/mm ≈ 0.18mm／階），
    每一階都帶一個 ~90° 的假轉折，直接切分會把一條 R11.96 圓角拆成十幾段 SHORT、
    各拿一個編號（實測 F40–F50），雜訊被編號之後反而變成「可引用」的假特徵。

    做法只動「至少一側邊長 < min_edge_mm」的微段，且合併引入的偏移必須 ≤ tol_mm：
    反覆移除「移除後偏移最小」的那個頂點，直到沒有可合併的微段。

    為什麼不用全域 Douglas–Peucker（已實測不可行）：DP 只保證「與弦的偏移 ≤ tol」，
    會把取樣較稀的平滑圓弧整段壓成弦——弦與弦之間的轉折超過 corner_min_deg，
    反而生出整排假 CORNER，同時把真正的 SPIKE（尖刺折返）當成共線點吃掉。
    局部短邊合併沒有這兩個副作用：正常取樣間距（數 mm）的點一律不動，
    真的轉折兩側的邊長也遠大於門檻。

    tol_mm <= 0 或 min_edge_mm <= 0 時原樣回傳（可關閉，供既有行為對照）。
    薄型視圖（側視圖）真實特徵常在 1–3mm，門檻要調小——跟 major_min_mm 一樣
    可逐視圖覆寫。
    """
    pts = [[float(p[0]), float(p[1])] for p in pts_mm]
    n_in = len(pts)
    tol = 0.0 if tol_mm is None else float(tol_mm)
    edge = 0.0 if min_edge_mm is None else float(min_edge_mm)
    if tol <= 0.0 or edge <= 0.0 or n_in < 4:
        return {"pts": pts, "n_in": n_in, "n_out": n_in, "removed": 0,
                "tol_mm": tol, "min_edge_mm": edge}

    work = list(pts)
    removed = 0
    guard = 0
    while len(work) > 3 and guard < 8 * n_in:
        guard += 1
        n = len(work)
        best = None
        for i in range(n):
            a, b, c = work[(i - 1) % n], work[i], work[(i + 1) % n]
            e0 = math.hypot(b[0] - a[0], b[1] - a[1])
            e1 = math.hypot(c[0] - b[0], c[1] - b[1])
            if min(e0, e1) >= edge:
                continue
            d = _perp_dist_to_line(b, a, c)
            if d > tol:
                continue
            if best is None or d < best[0]:
                best = (d, i)
        if best is None:
            break
        del work[best[1]]
        removed += 1

    if len(work) < 3:
        return {"pts": pts, "n_in": n_in, "n_out": n_in, "removed": 0,
                "tol_mm": tol, "min_edge_mm": edge}
    return {"pts": work, "n_in": n_in, "n_out": len(work),
            "removed": n_in - len(work), "tol_mm": tol, "min_edge_mm": edge}


def view_prefix(view_name):
    return VIEW_LETTER.get(str(view_name).lower(), str(view_name)[:1].upper() or "X")


def segments_from_contour(pts_mm, view=None, corner_min_deg=DEFAULT_CORNER_MIN_DEG,
                          min_feature_mm=DEFAULT_MIN_FEATURE_MM,
                          straight_tol_frac=DEFAULT_STRAIGHT_TOL_FRAC,
                          straight_tol_min_mm=DEFAULT_STRAIGHT_TOL_MIN_MM,
                          major_min_mm=DEFAULT_MAJOR_MIN_MM, prefix=None,
                          fit_tol_mm=DEFAULT_FIT_TOL_MM):
    """把封閉輪廓切成可引用的特徵序列（依輪廓順序混編 segment 與 corner）。

    fit_tol_mm 是**切分前的折線擬合容差**（先擬合、後編號，見 fit_polyline）：
    工程圖輪廓的階梯雜訊不先併掉，一條圓角會被切成十幾段各拿一個編號。
    傳 0 可關閉（回到純切分行為，供對照）。

    major_min_mm 控制「主要／次要」分級（只影響是否標在圖上，不影響編號）：
    薄型視圖（側視圖）的相機凸台等真實特徵常在 1–3mm 間，這種視圖要調小
    （例：1.0），否則會被整批歸成次要、圖上只看得到外框兩條長邊。

    回傳 list[dict]，每筆含：
      id, view, kind(LINE|CURVE|CORNER|SHORT|SPIKE), major, p0_mm, p1_mm, mid_mm,
      length_mm, dev_mm, turn_deg, convex, radius_mm, out_normal_mm, vertex_index
    """
    pts = dedupe(pts_mm)
    if fit_tol_mm is not None and float(fit_tol_mm) > 0.0:
        pts = fit_polyline(pts, fit_tol_mm, min_edge_mm=min_feature_mm)["pts"]
    n = len(pts)
    if n < 3:
        raise ValueError("segments_from_contour: need >=3 distinct points, got %d" % n)
    area = polygon_area(pts)
    ccw = area > 0.0
    turns = [turn_signed_deg(pts[(i - 1) % n], pts[i], pts[(i + 1) % n]) for i in range(n)]
    sharp = {i for i in range(n) if abs(turns[i]) >= corner_min_deg}
    # 無尖角的輪廓（平滑圓角／整圈曲面）光靠轉折角切不出東西，會整圈變一段 CURVE；
    # 補上「直線／圓弧擬合切換點」當作額外切分索引，讓圓角與直邊各自成段。
    # 注意：擬合切換點只是分段邊界，不是轉折——只有真正的尖角才發 CORNER 標註。
    corners = sorted(sharp | set(_fit_break_indices(pts, straight_tol_frac,
                                                    straight_tol_min_mm)))

    seq = []  # [(kind, payload)]
    if not corners:
        seq.append(("seg", pts + [pts[0]]))
    elif len(corners) == 1:
        i0 = corners[0]
        seq.append(("seg", pts[i0:] + pts[:i0 + 1]))
        if i0 in sharp:
            seq.append(("corner", i0))
    else:
        m = len(corners)
        for k in range(m):
            i0 = corners[k]
            i1 = corners[(k + 1) % m]
            idxs = [i0]
            i = i0
            guard = 0
            while i != i1 and guard <= n:
                i = (i + 1) % n
                idxs.append(i)
                guard += 1
            seq.append(("seg", [pts[j] for j in idxs]))
            if i1 in sharp:
                seq.append(("corner", i1))

    feats = []
    for item_kind, payload in seq:
        if item_kind == "seg":
            seg = payload
            length = polyline_length(seg)
            dev = max_perp_dev(seg)
            tol = max(straight_tol_min_mm, length * straight_tol_frac)
            if length < min_feature_mm:
                kind = "SHORT"
            elif dev <= tol:
                kind = "LINE"
            else:
                kind = "CURVE"
            radius = None
            if kind == "CURVE" and len(seg) >= 3:
                fit_pts = seg
                if math.hypot(seg[-1][0] - seg[0][0], seg[-1][1] - seg[0][1]) < 1e-9:
                    fit_pts = seg[:-1]  # 封閉輪廓首尾同一點：去掉重複尾巴才能配圓
                if len(fit_pts) >= 3:
                    radius = circum_radius(fit_pts[0], fit_pts[len(fit_pts) // 2], fit_pts[-1])
            feats.append({
                "kind": kind,
                "p0_mm": _r2(seg[0]),
                "p1_mm": _r2(seg[-1]),
                "mid_mm": _r2(point_at_half(seg)),
                "length_mm": round(length, 3),
                "dev_mm": round(dev, 3),
                "turn_deg": 0.0,
                "convex": None,
                "radius_mm": None if radius is None else round(radius, 3),
                "out_normal_mm": _r2(outward_normal(seg[0], seg[-1], ccw)),
                "vertex_index": None,
                "n_pts": len(seg),
            })
        else:
            i = payload
            v = pts[i]
            prev = pts[(i - 1) % n]
            nxt = pts[(i + 1) % n]
            na = outward_normal(prev, v, ccw)
            nb = outward_normal(v, nxt, ccw)
            bx, by = na[0] + nb[0], na[1] + nb[1]
            L = math.hypot(bx, by)
            bis = [bx / L, by / L] if L > 1e-9 else na
            t = turns[i]
            feats.append({
                "kind": "SPIKE" if abs(t) >= DEFAULT_SPIKE_MIN_DEG else "CORNER",
                "p0_mm": _r2(prev),
                "p1_mm": _r2(nxt),
                "mid_mm": _r2(v),
                "length_mm": 0.0,
                "dev_mm": 0.0,
                "turn_deg": round(t, 2),
                "convex": bool((t > 0) == ccw),
                "radius_mm": None,
                "out_normal_mm": _r2(bis),
                "vertex_index": int(i),
                "n_pts": 1,
            })

    pre = prefix or view_prefix(view or "x")
    for k, f in enumerate(feats, start=1):
        f["id"] = "%s%d" % (pre, k)
        f["view"] = view
    _mark_major(feats, major_min_mm=major_min_mm)
    return feats


def _mark_major(feats, major_min_mm=DEFAULT_MAJOR_MIN_MM):
    """就地標記主要／次要（次要特徵仍保留編號，只是預設不畫在圖上）。

    主要＝值得標在圖上讓人指認的：線段長度 ≥ major_min_mm 且不是折返雜訊；
    轉折則看兩側線段，任一邊次要就跟著次要——元件多時圖面才讀得下去。
    """
    n = len(feats)
    for f in feats:
        if f["kind"] in ("LINE", "CURVE"):
            f["major"] = bool(f["length_mm"] >= major_min_mm)
        elif f["kind"] in ("SHORT", "SPIKE"):
            f["major"] = False
        else:
            f["major"] = None
    for i, f in enumerate(feats):
        if f["kind"] != "CORNER":
            continue
        nb = [feats[j]["major"] for j in (i - 1, i + 1)
              if 0 <= j < n and feats[j]["major"] is not None]
        f["major"] = bool(nb) and all(nb)


# --------------------------------------------------------------------------
# 元件表：讀取、內縮檢查
# --------------------------------------------------------------------------
def normalize_components(doc):
    """接受 doc dict / 元件 list → (components, meta)。缺 bbox 時用 center+size 展開。"""
    if isinstance(doc, (list, tuple)):
        comps, meta = list(doc), {}
    else:
        schema = doc.get("schema")
        if schema and schema != COMPONENTS_SCHEMA:
            raise ValueError("components: unexpected schema %r (want %r)"
                             % (schema, COMPONENTS_SCHEMA))
        comps = list(doc.get("components", []))
        meta = {k: v for k, v in doc.items() if k != "components"}
    out = []
    for raw in comps:
        c = dict(raw)
        if "bbox_mm" not in c:
            if "center_mm" in c and "size_mm" in c:
                cx, cy = c["center_mm"]
                w, h = c["size_mm"]
                c["bbox_mm"] = [cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0]
            else:
                raise ValueError("component %r needs bbox_mm or center_mm+size_mm"
                                 % c.get("id"))
        if len(c["bbox_mm"]) != 4:
            raise ValueError("component %r: bbox_mm must be [x0,y0,x1,y1]" % c.get("id"))
        c.setdefault("view", None)
        c.setdefault("name", "")
        c.setdefault("note", "")
        c.setdefault("source", "")
        c.setdefault("exclude_from_containment", False)
        c["bbox_mm"] = _r2(c["bbox_mm"])
        out.append(c)
    return out, meta


def load_components(path):
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    return normalize_components(doc)


def save_components(comps, path, meta=None):
    doc = dict(meta or {})
    doc.setdefault("schema", COMPONENTS_SCHEMA)
    doc["components"] = list(comps)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    return path


def component_containment(contour_mm, bbox_mm, ppmm=DEFAULT_RASTER_SCALE):
    """元件 bbox 相對量測輪廓的內縮狀態。

    回傳 {corners_inside, area_frac, outside_mm, inside}
      corners_inside：4 個角落在輪廓內的數量
      area_frac    ：bbox 落在輪廓內的面積比例
      outside_mm   ：最遠凸出角到輪廓邊界的距離（落在裡面則為 0）
    """
    if not contour_mm:
        raise ValueError("component_containment: empty contour")
    b = [float(v) for v in bbox_mm]
    xs = [float(p[0]) for p in contour_mm]
    ys = [float(p[1]) for p in contour_mm]
    x_min = min(min(xs), b[0]) - CONTAIN_MARGIN_MM
    x_max = max(max(xs), b[2]) + CONTAIN_MARGIN_MM
    y_min = min(min(ys), b[1]) - CONTAIN_MARGIN_MM
    y_max = max(max(ys), b[3]) + CONTAIN_MARGIN_MM
    w = max(2, int((x_max - x_min) * ppmm) + 1)
    h = max(2, int((y_max - y_min) * ppmm) + 1)
    m_contour = _rasterize(contour_mm, x_min, y_min, w, h, ppmm)
    rect = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]
    m_rect = _rasterize(rect, x_min, y_min, w, h, ppmm)
    area_rect = int(m_rect.sum())
    inter = int((m_rect & m_contour).sum())
    corners = rect
    inside_flags = [point_in_polygon(c, contour_mm) for c in corners]
    outside = 0.0
    for c, ok in zip(corners, inside_flags):
        if not ok:
            outside = max(outside, dist_to_polygon(c, contour_mm))
    center = [(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0]
    return {
        "corners_inside": int(sum(1 for f in inside_flags if f)),
        "center_inside": bool(point_in_polygon(center, contour_mm)),
        "area_frac": round(inter / float(area_rect), 4) if area_rect else 0.0,
        "outside_mm": round(outside, 3),
        "inside": bool(all(inside_flags)),
    }


def assert_component_within_contour(contour_mm, comps, view=None,
                                    tol_mm=DEFAULT_CONTAIN_TOL_MM,
                                    min_area_frac=DEFAULT_MIN_AREA_FRAC):
    """檢查元件 bbox 是否落在量測輪廓內。回傳問題清單（不 raise）。

    標了 exclude_from_containment 的元件（刻意凸出的按鍵、鏡頭凸台）跳過檢查，
    但仍會計算並寫入 _containment 供圖例顯示。
    """
    issues = []
    for c in comps:
        if view is not None and c.get("view") not in (None, view):
            continue
        res = component_containment(contour_mm, c["bbox_mm"])
        c["_containment"] = res
        if c.get("exclude_from_containment"):
            continue
        tag = "%s %s" % (c.get("id"), c.get("name") or c.get("view") or "")
        # 判準：bbox 中心必須在輪廓內，且面積比達標。四角落在圓角之外不算問題（外接
        # 框套在圓角造型上本來就會被切掉角）。圓形／橢圓狀元件請用緊貼的外接框，
        # 或直接標 exclude_from_containment——bbox 面積比對非矩形件天生偏低。
        if not res["center_inside"] or res["area_frac"] < min_area_frac:
            issues.append("%s: bbox %.1f%% 落在輪廓內 (< %.1f%%)，中心%s，最遠凸出 %.2fmm "
                          "(corners_inside=%d/4)"
                          % (tag.strip(), res["area_frac"] * 100.0, min_area_frac * 100.0,
                             "在外" if not res["center_inside"] else "在內",
                             res["outside_mm"], res["corners_inside"]))
    return issues


# --------------------------------------------------------------------------
# 標籤避讓與圖元（後端無關）
# --------------------------------------------------------------------------
def _text_w(text, size):
    """估算文字寬度（非真實字型度量，只用於避讓與欄寬判斷）。"""
    w = 0.0
    for ch in str(text):
        w += size * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w


def _truncate(text, max_w, size, tail="…"):
    """把字串截到估算寬度內（中文與 ASCII 混排時仍能收得住）。"""
    text = str(text)
    if _text_w(text, size) <= max_w:
        return text
    out = ""
    for ch in text:
        if _text_w(out + ch + tail, size) > max_w:
            break
        out += ch
    return out + tail


# 圖例欄寬（px）：ID | 類型或名稱 | 長度·角度或尺寸 | 起點→終點或內縮狀態
LEGEND_COLS = (40.0, 100.0, 92.0)


def _overlaps(r, rects):
    for o in rects:
        if not (r[2] < o[0] or r[0] > o[2] or r[3] < o[1] or r[1] > o[3]):
            return True
    return False


def _rot(ux, uy, deg):
    a = math.radians(deg)
    return (ux * math.cos(a) - uy * math.sin(a), ux * math.sin(a) + uy * math.cos(a))


def _directions_from(out_dir, spread=(0.0, 45.0, -45.0, 90.0, -90.0)):
    ux, uy = out_dir
    L = math.hypot(ux, uy)
    if L < 1e-9:
        ux, uy = 0.0, -1.0
    else:
        ux, uy = ux / L, uy / L
    out = [_rot(ux, uy, d) for d in spread]
    return [(round(a, 4), round(b, 4)) for a, b in out]


def _place(state, anchor, dirs, box_w, box_h, dists):
    """多方位×多距離找第一個不碰撞且不超界的標籤位置。

    回傳 (cx, cy, rect)；全部候選都不可用時硬放在最遠候選並累計 overlaps。
    """
    bx0, by0, bx1, by1 = state["bounds"]
    for d in dists:
        for (ux, uy) in dirs:
            cx = anchor[0] + ux * d
            cy = anchor[1] + uy * d
            r = [cx - box_w / 2.0, cy - box_h / 2.0, cx + box_w / 2.0, cy + box_h / 2.0]
            if r[0] < bx0 or r[1] < by0 or r[2] > bx1 or r[3] > by1:
                continue
            if not _overlaps(r, state["placed"]):
                state["placed"].append(r)
                return cx, cy, r
    state["overlaps"] += 1
    ux, uy = dirs[0]
    d = dists[-1]
    cx = anchor[0] + ux * d
    cy = anchor[1] + uy * d
    r = [cx - box_w / 2.0, cy - box_h / 2.0, cx + box_w / 2.0, cy + box_h / 2.0]
    state["placed"].append(r)
    return cx, cy, r


def _fmt_pt(p):
    return "%.1f,%.1f" % (p[0], p[1])


def _fmt_mm(v):
    return "%.2f" % float(v)


def _legend_lines(view_name, view, features, components, title=None, source=None,
                  major_min_mm=DEFAULT_MAJOR_MIN_MM):
    """組出圖例文字行：[(text, size, color, dx)]，dx 為欄位偏移。"""
    lines = []
    dims = view.get("dims_mm") or [0.0, 0.0]
    lines.append((title or ("%s — 標註平面圖" % view_name), "head"))
    lines.append(("視圖 %s ｜ 量測 %.2f × %.2f mm ｜ px_per_mm %.4f"
                  % (view_name, dims[0], dims[1], float(view.get("px_per_mm", 0.0))), "dim"))
    lines.append(("紅線＝量測輪廓（triview_lib）；藍虛線＝回渲輪廓（若有）", "dim"))
    lines.append(("", None))
    counts = {}
    for f in features:
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    summary = " ｜ ".join("%s %d" % (KIND_LABEL.get(k, k), counts[k]) for k in sorted(counts))
    lines.append(("特徵 %d 個（%s）— 可直接說「F7 這條線不對」" % (len(features), summary), "head"))
    lines.append(("ID|類型|長度·角度|起點 → 終點 (mm)", "header"))
    for f in features:
        if f["kind"] in ("CORNER", "SPIKE"):
            metric = "%.1f°%s" % (f["turn_deg"], "凸" if f.get("convex") else "凹")
            span = _fmt_pt(f["mid_mm"])
        else:
            metric = "%.2f mm" % f["length_mm"]
            if f["kind"] == "CURVE" and f.get("radius_mm"):
                metric += " R%.1f" % f["radius_mm"]
            span = "%s → %s" % (_fmt_pt(f["p0_mm"]), _fmt_pt(f["p1_mm"]))
        lines.append(("%s|%s|%s|%s" % (f["id"], KIND_LABEL.get(f["kind"], f["kind"]),
                                       metric, span), "row"))
    minors = [f["id"] for f in features if not f.get("major", True)]
    if minors:
        shown = "、".join(minors[:16]) + (" …" if len(minors) > 16 else "")
        lines.append(("未標於圖的次要特徵 %d 個（<%.1fmm 短邊／折返），編號仍可引用：%s"
                      % (len(minors), major_min_mm, shown), "dim"))
    lines.append(("", None))
    lines.append(("元件 %d 個 — 來自 Stage A 元件表" % len(components), "head"))
    lines.append(("ID|名稱|尺寸 (mm)|內縮", "header"))
    for c in components:
        b = c["bbox_mm"]
        size = "%.1f × %.1f" % (abs(b[2] - b[0]), abs(b[3] - b[1]))
        r = c.get("_containment")
        if c.get("exclude_from_containment"):
            state_txt = "略過(凸出預期)" if r and r["outside_mm"] > 0 else "略過"
        elif r is None:
            state_txt = "未檢查"
        elif r["center_inside"] and r["area_frac"] >= DEFAULT_MIN_AREA_FRAC:
            state_txt = "OK %.0f%%" % (r["area_frac"] * 100.0)
        else:
            state_txt = "越界 %.0f%%" % (r["area_frac"] * 100.0)
        lines.append(("%s|%s|%s|%s" % (c.get("id"), c.get("name") or "-", size, state_txt),
                      "row"))
    lines.append(("", None))
    src = (source or {}).get("document") if isinstance(source, dict) else None
    lines.append((("輪廓來源：%s" % src) if src else "輪廓來源：未標註", "dim"))
    lines.append(("數值單位 mm；標註字級可調（元件多時調小）", "dim"))
    return lines


# --------------------------------------------------------------------------
# 圖元組裝（後端無關）
# --------------------------------------------------------------------------
def build_annotations(view_name, view, features, components=None, crop=None,
                      sheet_scale=1.0, font_px=DEFAULT_FONT_PX,
                      legend_font_px=DEFAULT_LEGEND_FONT_PX, legend=True,
                      legend_w=DEFAULT_LEGEND_W_PX, gutter=DEFAULT_GUTTER_PX,
                      sheet_margin=DEFAULT_SHEET_MARGIN_PX, title=None,
                      extra_contours=None, crop_margin=DEFAULT_CROP_MARGIN_PX,
                      show_feature_labels=True, show_component_labels=True,
                      label_minor=DEFAULT_LABEL_MINOR,
                      major_min_mm=DEFAULT_MAJOR_MIN_MM, source=None):
    """算出整張圖的繪圖圖元（座標一律 sheet px）與版面尺寸。

    回傳 (prims, meta)。prims 為純資料，emit_svg()/emit_png() 各自消費。
    """
    bbox = [int(v) for v in view["bbox_px"]]
    if crop is None:
        m = int(crop_margin)
        crop = [bbox[0] - m, bbox[1] - m, bbox[2] + m, bbox[3] + m]
    crop = [int(v) for v in crop]
    cw = crop[2] - crop[0] + 1
    ch = crop[3] - crop[1] + 1
    dw = cw * sheet_scale
    dh = ch * sheet_scale
    ox, oy = float(sheet_margin), float(sheet_margin)

    def to_sheet(pt_img):
        return [ox + (float(pt_img[0]) - crop[0]) * sheet_scale,
                oy + (float(pt_img[1]) - crop[1]) * sheet_scale]

    ppm = float(view["px_per_mm"])

    def to_sheet_mm(pt_mm):
        return to_sheet(mm_to_px(view, pt_mm))

    def dir_mm_to_sheet(vec_mm):
        # mm 向量 → sheet 向量（x 同向、y 因翻正而反向）
        return (float(vec_mm[0]) * ppm * sheet_scale, -float(vec_mm[1]) * ppm * sheet_scale)

    prims = [{"k": "image", "xy": [ox, oy, dw, dh]}]

    contour = view.get("contour_mm") or []
    if contour:
        prims.append({"k": "poly", "pts": [to_sheet_mm(p) for p in contour],
                      "stroke": COL_CONTOUR, "w": 2.0, "close": True})
    for extra in (extra_contours or []):
        prims.append({"k": "poly", "pts": [to_sheet_mm(p) for p in extra],
                      "stroke": COL_MODEL, "w": 2.0, "close": True, "dash": True})

    state = {"placed": [], "overlaps": 0, "labels": 0,
             "bounds": (sheet_margin - 10.0, sheet_margin - 10.0,
                        ox + dw + 10.0, oy + dh + 10.0)}
    if show_feature_labels:
        dists = [14.0, 22.0, 32.0, 44.0, 58.0, 74.0]
        for f in features:
            if not label_minor and not f.get("major", True):
                continue      # 次要特徵不畫標籤（編號仍在圖例裡，可照樣引用）
            state["labels"] += 1
            anchor = to_sheet_mm(f["mid_mm"])
            dirs = _directions_from(dir_mm_to_sheet(f.get("out_normal_mm") or [0.0, -1.0]))
            box_w = _text_w(f["id"], font_px) + 6.0
            box_h = font_px * 1.5
            cx, cy, _ = _place(state, anchor, dirs, box_w, box_h, dists)
            if f["kind"] == "CORNER":
                prims.append({"k": "circle", "c": anchor, "r": 2.6,
                              "stroke": COL_CONTOUR, "w": 1.2, "fill": "#ffffff"})
            else:
                prims.append({"k": "circle", "c": anchor, "r": 1.7,
                              "stroke": COL_CONTOUR, "w": 1.0, "fill": COL_CONTOUR})
            if math.hypot(cx - anchor[0], cy - anchor[1]) > font_px * 0.9:
                prims.append({"k": "line", "a": anchor, "b": [cx, cy],
                              "stroke": COL_LEADER, "w": 0.7})
            prims.append({"k": "text", "xy": [cx, cy + font_px * 0.36], "t": f["id"],
                          "size": font_px, "color": COL_CONTOUR, "anchor": "middle",
                          "weight": "bold"})

    if show_component_labels:
        for c in (components or []):
            if c.get("view") not in (None, view_name):
                continue
            b = c["bbox_mm"]
            lo = to_sheet_mm([b[0], b[1]])
            hi = to_sheet_mm([b[2], b[3]])
            rect = [min(lo[0], hi[0]), min(lo[1], hi[1]),
                    max(lo[0], hi[0]), max(lo[1], hi[1])]
            prims.append({"k": "rect", "xy": rect, "stroke": COL_COMPONENT,
                          "w": 1.4, "dash": True})
            anchor = [(rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0]
            box_w = _text_w(c.get("id", ""), font_px) + 6.0
            box_h = font_px * 1.5
            base = max((rect[2] - rect[0]) / 2.0, (rect[3] - rect[1]) / 2.0) + box_h
            dists = [base + k * (box_h + 3.0) for k in range(4)] + [base + 90.0, base + 130.0]
            dirs = [(0.0, -1.0), (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0),
                    (-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)]
            cx, cy, _ = _place(state, anchor, dirs, box_w, box_h, dists)
            if math.hypot(cx - anchor[0], cy - anchor[1]) > box_h:
                prims.append({"k": "line", "a": anchor, "b": [cx, cy],
                              "stroke": COL_COMPONENT, "w": 0.7})
            prims.append({"k": "text", "xy": [cx, cy + font_px * 0.36], "t": c.get("id", ""),
                          "size": font_px, "color": COL_COMPONENT, "anchor": "middle",
                          "weight": "bold"})

    sheet_w = ox * 2 + dw
    sheet_h = oy * 2 + dh
    legend_h = 0.0
    if legend:
        lines = _legend_lines(view_name, view, features, components or [],
                              title=title, source=source, major_min_mm=major_min_mm)
        line_h = legend_font_px * 1.55
        legend_h = sheet_margin * 2 + line_h * len(lines) + 8.0
        lx = ox + dw + gutter
        sheet_w = lx + legend_w + sheet_margin
        sheet_h = max(sheet_h, sheet_margin * 2 + legend_h)
        prims.append({"k": "rect", "xy": [lx, oy, legend_w, legend_h],
                      "stroke": "#dddddd", "w": 1.0, "fill": "#fbfbfb"})
        y = oy + sheet_margin + legend_font_px
        for text, role in lines:
            if text:
                if role == "head":
                    color, size, weight = COL_INK, legend_font_px, "bold"
                elif role == "header":
                    color, size, weight = COL_DIM, legend_font_px * 0.92, "bold"
                elif role == "row":
                    color, size, weight = COL_INK, legend_font_px * 0.92, "normal"
                else:
                    color, size, weight = COL_DIM, legend_font_px * 0.88, "normal"
                if role == "row":
                    cells = text.split("|")
                    widths = list(LEGEND_COLS) + [
                        max(60.0, legend_w - 20.0 - sum(LEGEND_COLS))]
                    x = lx + 10.0
                    for idx, cell in enumerate(cells):
                        cw = widths[idx] if idx < len(widths) else 0.0
                        prims.append({"k": "text", "xy": [x, y],
                                      "t": _truncate(cell, cw - 5.0, size),
                                      "size": size, "color": color, "anchor": "start",
                                      "weight": weight})
                        x += cw
                else:
                    prims.append({"k": "text", "xy": [lx + 10.0, y], "t": text,
                                  "size": size, "color": color, "anchor": "start",
                                  "weight": weight})
            y += line_h

    meta = {"sheet_w": sheet_w, "sheet_h": sheet_h, "crop": crop,
            "draw_rect": [ox, oy, dw, dh], "legend_rect": [ox + dw + gutter, oy, legend_w, legend_h]
            if legend else None,
            "label_overlaps": state["overlaps"], "label_count": state["labels"],
            "feature_count": len(features),
            "minor_count": len([f for f in features if not f.get("major", True)]),
            "spike_count": len([f for f in features if f["kind"] == "SPIKE"]),
            "component_count": len([c for c in (components or [])
                                    if c.get("view") in (None, view_name)])}
    return prims, meta


# --------------------------------------------------------------------------
# 輸出：SVG / PNG
# --------------------------------------------------------------------------
def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def emit_svg(prims, sheet_w, sheet_h, out_path, bg_b64=None, bg_rect=None):
    """向量輸出（真文字、可再編輯）。bg_b64 為底圖 PNG 的 base64 字串。"""
    w = int(math.ceil(sheet_w))
    h = int(math.ceil(sheet_h))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<svg xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink" '
             'width="%d" height="%d" viewBox="0 0 %d %d">' % (w, h, w, h),
             '<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (w, h)]
    if bg_b64 and bg_rect:
        x, y, ww, hh = bg_rect
        parts.append('<image x="%g" y="%g" width="%g" height="%g" '
                     'xlink:href="data:image/png;base64,%s"/>' % (x, y, ww, hh, bg_b64))
    for p in prims:
        k = p.get("k")
        if k == "image":
            continue
        dash = ' stroke-dasharray="6 4"' if p.get("dash") else ""
        if k == "poly":
            pts = " ".join("%g,%g" % (q[0], q[1]) for q in p["pts"])
            parts.append('<polyline points="%s" fill="none" stroke="%s" '
                         'stroke-width="%g" stroke-linejoin="round"%s/>'
                         % (pts, p["stroke"], p["w"], dash))
        elif k == "rect":
            x, y, ww, hh = p["xy"]
            fill = p.get("fill", "none")
            parts.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" '
                         'stroke="%s" stroke-width="%g"%s/>'
                         % (x, y, ww, hh, fill, p["stroke"], p["w"], dash))
        elif k == "line":
            parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                         'stroke-width="%g"/>'
                         % (p["a"][0], p["a"][1], p["b"][0], p["b"][1], p["stroke"], p["w"]))
        elif k == "circle":
            parts.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" '
                         'stroke-width="%g"/>'
                         % (p["c"][0], p["c"][1], p["r"], p.get("fill", "none"),
                            p["stroke"], p["w"]))
        elif k == "text":
            weight = ' font-weight="bold"' if p.get("weight") == "bold" else ""
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'text-anchor="%s" font-family="%s"%s>%s</text>'
                         % (p["xy"][0], p["xy"][1], p["size"], p["color"],
                            p.get("anchor", "start"), SVG_FONT_STACK, weight,
                            _esc(p["t"])))
    parts.append("</svg>")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return out_path


def emit_png(prims, base_img, out_path, sheet_w, sheet_h, scale=DEFAULT_PNG_SCALE):
    """點陣輸出。base_img 為已裁好的 PIL Image（可 None）；scale 同時放大字級。"""
    Image, ImageDraw, _ = _pil()
    _, _, cjk_ok = (None, None, load_font(DEFAULT_FONT_PX * scale)[1])
    W = max(1, int(round(sheet_w * scale)))
    H = max(1, int(round(sheet_h * scale)))
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    if base_img is not None:
        for p in prims:
            if p.get("k") == "image":
                x, y, ww, hh = p["xy"]
                tw = max(1, int(round(ww * scale)))
                th = max(1, int(round(hh * scale)))
                resample = Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC
                canvas.paste(base_img.resize((tw, th), resample),
                             (int(round(x * scale)), int(round(y * scale))))
                break
    draw = ImageDraw.Draw(canvas)
    for p in prims:
        k = p.get("k")
        if k == "image":
            continue
        if k == "poly":
            pts = [(q[0] * scale, q[1] * scale) for q in p["pts"]]
            if p.get("close"):
                pts = pts + [pts[0]]
            draw.line(pts, fill=p["stroke"], width=max(1, int(round(p["w"] * scale))),
                      joint="curve")
        elif k == "rect":
            x, y, ww, hh = [v * scale for v in p["xy"]]
            if p.get("fill", "none") != "none":
                draw.rectangle([x, y, x + ww, y + hh], fill=p["fill"])
            _dashed_rect(draw, x, y, ww, hh, p["stroke"],
                         max(1, int(round(p["w"] * scale))), bool(p.get("dash")))
        elif k == "line":
            draw.line([p["a"][0] * scale, p["a"][1] * scale,
                       p["b"][0] * scale, p["b"][1] * scale],
                      fill=p["stroke"], width=max(1, int(round(p["w"] * scale))))
        elif k == "circle":
            cx, cy, r = p["c"][0] * scale, p["c"][1] * scale, p["r"] * scale
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=p.get("fill", None) if p.get("fill", "none") != "none" else None,
                         outline=p["stroke"],
                         width=max(1, int(round(p["w"] * scale))))
        elif k == "text":
            size = p["size"] * scale
            font, ok = load_font(size)[0], cjk_ok
            text = p["t"] if ok else _ascii_fallback(p["t"])
            anchor = {"middle": "ms", "end": "rs"}.get(p.get("anchor"), "ls")
            try:
                draw.text((p["xy"][0] * scale, p["xy"][1] * scale), text, font=font,
                          fill=p["color"], anchor=anchor)
            except TypeError:  # 舊版 Pillow 不支援 anchor
                draw.text((p["xy"][0] * scale, p["xy"][1] * scale), text, font=font,
                          fill=p["color"])
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    canvas.save(out_path)
    return out_path


def _dashed_rect(draw, x, y, w, h, color, width, dash, seg=6.0, gap=4.0):
    if not dash:
        draw.rectangle([x, y, x + w, y + h], outline=color, width=width)
        return
    seg = max(2.0, seg)
    gap = max(2.0, gap)
    top = x
    while top < x + w:
        draw.line([top, y, min(top + seg, x + w), y], fill=color, width=width)
        top += seg + gap
    left = y
    while left < y + h:
        draw.line([x, left, x, min(left + seg, y + h)], fill=color, width=width)
        left += seg + gap
    right = y
    while right < y + h:
        draw.line([x + w, right, x + w, min(right + seg, y + h)], fill=color, width=width)
        right += seg + gap
    bottom = x
    while bottom < x + w:
        draw.line([bottom, y + h, min(bottom + seg, x + w), y + h], fill=color, width=width)
        bottom += seg + gap


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def _crop_panel(image_path, bbox_px, margin_px):
    Image, _, _ = _pil()
    im = Image.open(image_path).convert("RGB")
    x0 = max(0, int(bbox_px[0]) - int(margin_px))
    y0 = max(0, int(bbox_px[1]) - int(margin_px))
    x1 = min(im.width - 1, int(bbox_px[2]) + int(margin_px))
    y1 = min(im.height - 1, int(bbox_px[3]) + int(margin_px))
    sub = im.crop((x0, y0, x1 + 1, y1 + 1))
    buf = io.BytesIO()
    sub.save(buf, format="PNG")
    return {"crop": [x0, y0, x1, y1], "image": sub, "png_bytes": buf.getvalue()}


def render_blueprint(calib, out_dir, components=None, images=None, views=None,
                     sheet_scale=1.0, font_px=DEFAULT_FONT_PX,
                     legend_font_px=DEFAULT_LEGEND_FONT_PX, png_scale=DEFAULT_PNG_SCALE,
                     legend=True, extra_contours=None, title=None,
                     crop_margin=DEFAULT_CROP_MARGIN_PX,
                     contain_tol_mm=DEFAULT_CONTAIN_TOL_MM,
                     min_area_frac=DEFAULT_MIN_AREA_FRAC,
                     embed_image=True, corner_min_deg=DEFAULT_CORNER_MIN_DEG,
                     min_feature_mm=DEFAULT_MIN_FEATURE_MM,
                     major_min_mm=DEFAULT_MAJOR_MIN_MM,
                     label_minor=DEFAULT_LABEL_MINOR, write_json=True,
                     fit_tol_mm=DEFAULT_FIT_TOL_MM):
    """calib → 標註平面圖（SVG + PNG）+ data.json。

    calib      : calib dict 或 calib JSON 路徑
    components : 元件 list / doc dict / JSON 路徑（None＝只畫特徵）
    images     : {view: 面板圖路徑}（None＝純向量版，無疊圖底圖）
    extra_contours : {view: [mm 輪廓]}（Stage C 餵回渲輪廓，畫成藍虛線）
    major_min_mm   : 主/次分級門檻（mm），可傳 float（全視圖共用）或
                     {'side': 1.0} 這種 dict 逐視圖覆寫——薄型視圖的真實特徵較小。
    fit_tol_mm     : 切分前的折線擬合容差（mm），同樣支援 float 或逐視圖 dict。
                     預設 0.35 併掉工程圖輪廓的階梯雜訊（先擬合、後編號）；
                     薄型視圖建議 0.15，避免真實的 1–3mm 階差被吃掉。
    回傳 {"views": {...}, "data_path": ..., "issues": {...}}
    """
    if isinstance(calib, str):
        calib = _load_calib(calib)
    if components is None:
        comps, cmeta = [], {}
    elif isinstance(components, str):
        comps, cmeta = load_components(components)
    else:
        comps, cmeta = normalize_components(components)

    views_doc = calib.get("views", {})
    names = list(views or views_doc.keys())
    os.makedirs(out_dir, exist_ok=True)
    out = {"views": {}, "issues": {}, "label_overlaps": {}}
    subject = calib.get("subject", {})
    source = calib.get("source", {})

    for name in names:
        view = views_doc.get(name)
        if not view:
            print("WARNING: blueprint: calib has no view %r; skipped" % name)
            continue
        contour = view.get("contour_mm") or []
        v_major = (major_min_mm.get(name, DEFAULT_MAJOR_MIN_MM)
                   if isinstance(major_min_mm, dict) else major_min_mm)
        v_fit = (fit_tol_mm.get(name, DEFAULT_FIT_TOL_MM)
                 if isinstance(fit_tol_mm, dict) else fit_tol_mm)
        feats = segments_from_contour(contour, view=name, corner_min_deg=corner_min_deg,
                                      min_feature_mm=min_feature_mm,
                                      major_min_mm=v_major,
                                      fit_tol_mm=v_fit) if contour else []
        fit_info = fit_polyline(contour, v_fit, min_edge_mm=min_feature_mm) if contour else None
        sub = [c for c in comps if c.get("view") in (None, name)]
        issues = (assert_component_within_contour(contour, sub, view=name, tol_mm=contain_tol_mm,
                                                 min_area_frac=min_area_frac)
                  if contour else [])
        panel = None
        img_path = (images or {}).get(name)
        if img_path:
            if os.path.isfile(img_path):
                panel = _crop_panel(img_path, view["bbox_px"], crop_margin)
            else:
                print("WARNING: blueprint: image for view %r not found: %s" % (name, img_path))
        extra = (extra_contours or {}).get(name)
        prims, meta = build_annotations(
            name, view, feats, components=sub,
            crop=panel["crop"] if panel else None,
            sheet_scale=sheet_scale, font_px=font_px, legend_font_px=legend_font_px,
            legend=legend, title=title, extra_contours=extra,
            crop_margin=crop_margin, label_minor=label_minor, source=source,
            major_min_mm=v_major)

        svg_path = os.path.join(out_dir, "blueprint_%s.svg" % name)
        png_path = os.path.join(out_dir, "blueprint_%s.png" % name)
        bg_b64 = None
        bg_rect = None
        if panel is not None and embed_image:
            bg_b64 = base64.b64encode(panel["png_bytes"]).decode("ascii")
            bg_rect = prims[0]["xy"]
        emit_svg(prims, meta["sheet_w"], meta["sheet_h"], svg_path,
                 bg_b64=bg_b64, bg_rect=bg_rect)
        emit_png(prims, panel["image"] if panel else None, png_path,
                 meta["sheet_w"], meta["sheet_h"], scale=png_scale)
        out["views"][name] = {
            "svg": svg_path, "png": png_path, "sheet": [meta["sheet_w"], meta["sheet_h"]],
            "features": feats, "components": sub, "issues": issues,
            "label_overlaps": meta["label_overlaps"],
            "label_count": meta["label_count"], "minor_count": meta["minor_count"],
            "spike_count": meta["spike_count"],
            "has_backdrop": bool(panel is not None),
            "fit": (None if fit_info is None else
                    {"tol_mm": fit_info["tol_mm"],
                     "min_edge_mm": fit_info["min_edge_mm"],
                     "n_in": fit_info["n_in"],
                     "n_out": fit_info["n_out"], "removed": fit_info["removed"]}),
        }
        out["issues"][name] = issues
        out["label_overlaps"][name] = meta["label_overlaps"]

    if write_json:
        data = {
            "schema": BP_SCHEMA,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "subject": subject,
            "source": source,
            "components_meta": cmeta,
            "counts": {k: {"features": len(v["features"]), "components": len(v["components"]),
                            "issues": len(v["issues"]), "label_overlaps": v["label_overlaps"],
                            "label_count": v["label_count"], "minor_count": v["minor_count"],
                            "spike_count": v["spike_count"]}
                       for k, v in out["views"].items()},
            "views": {k: {"features": v["features"],
                          "components": [{kk: vv for kk, vv in c.items() if not kk.startswith("_note")}
                                         for c in v["components"]],
                          "issues": v["issues"], "svg": os.path.basename(v["svg"]),
                          "png": os.path.basename(v["png"]), "has_backdrop": v["has_backdrop"],
                          "fit": v.get("fit")}
                      for k, v in out["views"].items()},
        }
        path = os.path.join(out_dir, "blueprint_data.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        out["data_path"] = path
    return out


# --------------------------------------------------------------------------
# 自我測試（合成資料，不需外部檔案）
# --------------------------------------------------------------------------
def _rounded_rect_contour(w_mm, h_mm, r_mm, seg_per_corner=6):
    hw, hh = w_mm / 2.0, h_mm / 2.0
    pts = []
    corners = [(hw - r_mm, hh - r_mm, 0.0), (-hw + r_mm, hh - r_mm, 90.0),
               (-hw + r_mm, -hh + r_mm, 180.0), (hw - r_mm, -hh + r_mm, 270.0)]
    for cx, cy, a0 in corners:
        for k in range(seg_per_corner + 1):
            a = math.radians(a0 + 90.0 * k / float(seg_per_corner))
            pts.append([cx + r_mm * math.cos(a), cy + r_mm * math.sin(a)])
    return dedupe(pts, eps_mm=0.001)


def _selftest():
    checks, fails = [], []

    def chk(name, cond, detail=""):
        checks.append(name)
        if not cond:
            fails.append("%s %s" % (name, detail))

    import tempfile

    # --- 幾何基本量 ---
    sq = [[0, 0], [10, 0], [10, 5], [0, 5]]
    chk("geo.area_ccw", abs(polygon_area(sq) - 50.0) < 1e-9, "%.3f" % polygon_area(sq))
    chk("geo.area_cw_sign", polygon_area(list(reversed(sq))) < 0)
    n_out = outward_normal([0, 0], [1, 0], True)
    chk("geo.outward_ccw", abs(n_out[0]) < 1e-9 and abs(n_out[1] + 1.0) < 1e-9, str(n_out))
    chk("geo.dedupe", len(dedupe([[0, 0], [0.01, 0], [1, 1], [0, 0]])) == 2)
    chk("geo.turn_90", abs(abs(turn_signed_deg([0, 0], [1, 0], [1, 1])) - 90.0) < 1e-6)
    chk("geo.perp_dev_line", max_perp_dev([[0, 0], [1, 0], [2, 0]]) < 1e-9)
    chk("geo.perp_dev_bulge", abs(max_perp_dev([[0, 0], [1, 1], [2, 0]]) - 1.0) < 1e-6)
    chk("geo.circum_radius", abs(circum_radius([-1, 0], [0, 1], [1, 0]) - 1.0) < 1e-6)
    chk("geo.point_in", point_in_polygon([5, 2], sq) and not point_in_polygon([15, 2], sq))

    # --- mm ↔ px 往返 ---
    view = {"bbox_px": [100, 200, 500, 1000], "px_per_mm": 4.0, "dims_mm": [100.0, 200.0]}
    bad = 0.0
    for p in ([0.0, 0.0], [12.5, -30.0], [-49.9, 199.0]):
        back = px_to_mm(view, mm_to_px(view, p))
        bad = max(bad, abs(back[0] - p[0]), abs(back[1] - p[1]))
    chk("map.roundtrip", bad < 1e-9, "max err %.2e" % bad)
    chk("map.origin_bottom_center",
        abs(mm_to_px(view, [0.0, 0.0])[0] - 300.0) < 1e-9 and
        abs(mm_to_px(view, [0.0, 0.0])[1] - 1000.0) < 1e-9)

    # --- 特徵切分 A：尖角輪廓（DP 簡化後的實際樣態）→ 4 直線 + 4 轉折 ---
    sharp = [[-50.0, -30.0], [50.0, -30.0], [50.0, 30.0], [-50.0, 30.0]]
    sf = segments_from_contour(sharp, view="front")
    sk = [f["kind"] for f in sf]
    chk("feat.sharp_count", len(sf) == 8, str(sk))
    chk("feat.sharp_4_line", sk.count("LINE") == 4, str(sk))
    chk("feat.sharp_4_corner", sk.count("CORNER") == 4, str(sk))
    slines = [f for f in sf if f["kind"] == "LINE"]
    chk("feat.sharp_line_len", abs(slines[0]["length_mm"] - 100.0) < 0.01,
        "%.2f" % slines[0]["length_mm"])
    chk("feat.ids_sequential", [f["id"] for f in sf] == ["F%d" % (i + 1) for i in range(8)],
        str([f["id"] for f in sf]))
    scor = [f for f in sf if f["kind"] == "CORNER"]
    chk("feat.corner_angle", all(85.0 <= abs(c["turn_deg"]) <= 95.0 for c in scor),
        str([c["turn_deg"] for c in scor]))
    chk("feat.out_normal_unit",
        all(abs(math.hypot(*f["out_normal_mm"]) - 1.0) < 1e-3 for f in sf))

    # 極短邊 → SHORT（仍保留編號，不靜默丟棄），且歸為次要。
    # 注意：預設會先做短邊合併（先擬合、後編號），所以這裡用 fit_tol_mm=0.0
    # 明確關閉擬合，單獨驗證 SHORT 分類本身。
    tabbed = [[-50.0, -30.0], [50.0, -30.0], [50.4, -30.0], [50.4, -29.5],
              [50.0, -29.5], [50.0, 30.0], [-50.0, 30.0]]
    tfeats = segments_from_contour(tabbed, view="front", fit_tol_mm=0.0)
    tk = [f["kind"] for f in tfeats]
    chk("feat.short_flagged", "SHORT" in tk, str(tk))
    chk("feat.short_is_minor",
        any(f["kind"] == "SHORT" and not f["major"] for f in tfeats),
        str([(f["id"], f["major"]) for f in tfeats]))
    # 同一條輪廓在預設模式下，微凸起的階梯會被先併掉（特徵數下降），
    # 留下來的微段才是真的偏離主輪廓、值得指認的那一個。
    tfit = segments_from_contour(tabbed, view="front")
    chk("feat.tab_merged_by_default", len(tfit) < len(tfeats),
        "raw=%d fit=%d" % (len(tfeats), len(tfit)))

    # 折返雜訊（±180°，輪廓萃取的尖刺）→ SPIKE，且必為次要
    spiked = [[-50.0, -30.0], [50.0, -30.0], [50.0, -25.0], [50.0, -30.0],
              [50.0, 30.0], [-50.0, 30.0]]
    spf = segments_from_contour(spiked, view="front")
    spk = [f["kind"] for f in spf]
    chk("feat.spike_detected", spk.count("SPIKE") >= 1, str(spk))
    chk("feat.spike_is_minor",
        all(not f["major"] for f in spf if f["kind"] == "SPIKE"),
        str([(f["id"], f["major"]) for f in spf if f["kind"] == "SPIKE"]))

    # --- 特徵切分 B：圓角矩形（無尖角）→ 4 直線 + 4 圓弧，且全部算主要 ---
    contour = _rounded_rect_contour(100.0, 60.0, 8.0, seg_per_corner=6)
    feats = segments_from_contour(contour, view="front")
    kinds = [f["kind"] for f in feats]
    chk("feat.round_count", len(feats) == 8, str(kinds))
    chk("feat.round_4_line", kinds.count("LINE") == 4, str(kinds))
    chk("feat.round_4_curve", kinds.count("CURVE") == 4, str(kinds))
    chk("feat.round_no_corner", kinds.count("CORNER") == 0, str(kinds))
    chk("feat.round_all_major", all(f.get("major") for f in feats),
        str([(f["id"], f.get("major")) for f in feats]))
    lens = sorted(round(f["length_mm"], 1) for f in feats if f["kind"] == "LINE")
    chk("feat.round_line_lens", abs(lens[0] - 44.0) < 0.5 and abs(lens[-1] - 84.0) < 0.5,
        str(lens))
    arcs = [f for f in feats if f["kind"] == "CURVE"]
    chk("feat.round_arc_radius",
        all(c["radius_mm"] and abs(c["radius_mm"] - 8.0) < 0.3 for c in arcs),
        str([c["radius_mm"] for c in arcs]))

    # --- 特徵切分 C：圓形 → 全為圓弧、半徑 ≈ 10、總長 ≈ 周長 ---
    circ = [[10.0 * math.cos(a), 10.0 * math.sin(a)]
            for a in np.linspace(0, 2 * math.pi, 25)[:-1]]
    cir_f = segments_from_contour(circ, view="side")
    cir_kinds = [f["kind"] for f in cir_f]
    chk("feat.circle_prefix", cir_f[0]["id"].startswith("S"), cir_f[0]["id"])
    chk("feat.circle_cover", abs(sum(f["length_mm"] for f in cir_f) - 62.832) < 1.5,
        "%.2f" % sum(f["length_mm"] for f in cir_f))
    chk("feat.circle_no_long_line",
        max([f["length_mm"] for f in cir_f if f["kind"] == "LINE"] or [0.0]) < 5.0,
        str(cir_kinds))
    chk("feat.circle_radius",
        any(f["radius_mm"] and abs(f["radius_mm"] - 10.0) < 0.5 for f in cir_f),
        str([f["radius_mm"] for f in cir_f]))

    # --- 特徵切分 D：階梯雜訊（先擬合、後編號）---
    # 工程圖掃出來的輪廓沿邊界是 1px 一階的階梯；不先擬合就切分，一條圓角會被拆成
    # 十幾段 SHORT 各拿一個編號，雜訊反而變成「可引用」的假特徵。
    def _staircase(pts, step=0.18):
        """沿輪廓以 1px 步進重取樣並量化到像素格，模擬掃描階梯。"""
        out, n = [], len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            k = max(1, int(round(L / step)))
            for j in range(k):
                t = j / float(k)
                x = a[0] + (b[0] - a[0]) * t
                y = a[1] + (b[1] - a[1]) * t
                out.append([round(x / step) * step, round(y / step) * step])
        return dedupe(out, eps_mm=1e-6)

    stair = _staircase(_rounded_rect_contour(80.0, 50.0, 12.0, seg_per_corner=8))
    raw = segments_from_contour(stair, view="front", fit_tol_mm=0.0)
    fit = segments_from_contour(stair, view="front")
    n_raw = sum(1 for f in raw if f["kind"] == "SHORT")
    n_fit = sum(1 for f in fit if f["kind"] == "SHORT")
    chk("fit.staircase_raw_short", n_raw >= 8, "raw_short=%d" % n_raw)
    chk("fit.staircase_removed", n_fit == 0, "raw_short=%d fit_short=%d" % (n_raw, n_fit))
    chk("fit.staircase_fewer_features",
        len(fit) * 3 <= len(raw), "raw=%d fit=%d" % (len(raw), len(fit)))
    chk("fit.staircase_no_tiny_feature",
        all(f["length_mm"] >= DEFAULT_MIN_FEATURE_MM
            for f in fit if f["kind"] in ("LINE", "CURVE")),
        str(sorted(round(f["length_mm"], 3) for f in fit if f["kind"] in ("LINE", "CURVE"))[:6]))
    st = fit_polyline(stair, DEFAULT_FIT_TOL_MM)
    chk("fit.stats", st["n_in"] > st["n_out"] and
        st["removed"] == st["n_in"] - st["n_out"],
        str({k: st[k] for k in ("n_in", "n_out", "removed")}))
    st0 = fit_polyline(stair, 0.0)
    chk("fit.disabled_passthrough", st0["n_out"] == st0["n_in"] and st0["removed"] == 0,
        str({k: st0[k] for k in ("n_in", "n_out", "removed")}))

    # --- 元件內縮 ---
    inside_comp = {"id": "A-1", "name": "inside", "view": "front",
                   "bbox_mm": [-20.0, 5.0, 20.0, 25.0]}
    comps, _ = normalize_components({"components": [inside_comp]})
    r_in = component_containment(contour, inside_comp["bbox_mm"])
    chk("contain.inside_true", r_in["inside"] and r_in["corners_inside"] == 4, str(r_in))
    chk("contain.inside_frac", r_in["area_frac"] > 0.999, str(r_in))
    chk("contain.no_issue", assert_component_within_contour(contour, comps, view="front") == [])

    out_comp = {"id": "A-9", "name": "out", "view": "front",
                "bbox_mm": [30.0, 5.0, 90.0, 25.0]}
    comps2, _ = normalize_components({"components": [out_comp]})
    issues = assert_component_within_contour(contour, comps2, view="front")
    chk("contain.flags_outside", len(issues) == 1, str(issues))
    chk("contain.issue_names_id", issues and "A-9" in issues[0], str(issues))
    skipped = {"id": "A-10", "name": "tab", "view": "front",
               "bbox_mm": [46.0, 22.0, 56.0, 32.0], "exclude_from_containment": True}
    comps3, _ = normalize_components({"components": [skipped]})
    chk("contain.exclude_skipped",
        assert_component_within_contour(contour, comps3, view="front") == [])
    chk("contain.exclude_still_measured", comps3[0]["_containment"]["area_frac"] < 0.5,
        str(comps3[0]["_containment"]))
    chk("contain.center_size_expand",
        normalize_components([{"id": "X", "center_mm": [0, 0], "size_mm": [10, 4]}])[0][0]
        ["bbox_mm"] == [-5.0, -2.0, 5.0, 2.0])

    # --- 繪圖 / 輸出（夾具自身的 bbox 與 mm 輪廓必須自洽：mm 原點＝bbox 底部中心） ---
    view_draw = {"bbox_px": [100, 400, 499, 639], "px_per_mm": 4.0,
                 "dims_mm": [100.0, 60.0],
                 "contour_mm": [[-50.0, 0.0], [50.0, 0.0], [50.0, 60.0], [-50.0, 60.0]]}
    feats_front = segments_from_contour(view_draw["contour_mm"], view="front")
    comps_draw, _ = normalize_components({"components": [
        {"id": "A-1", "name": "panel", "view": "front", "bbox_mm": [-20.0, 10.0, 20.0, 50.0]}]})
    for c in comps_draw:
        c["_containment"] = component_containment(view_draw["contour_mm"], c["bbox_mm"])
    prims, meta = build_annotations("front", view_draw, feats_front, components=comps_draw,
                                    source={"document": "selftest synthetic"})
    chk("draw.has_contour_poly", any(p["k"] == "poly" for p in prims))
    chk("draw.has_text", any(p["k"] == "text" for p in prims))
    chk("draw.sheet_positive", meta["sheet_w"] > 100 and meta["sheet_h"] > 100,
        str([meta["sheet_w"], meta["sheet_h"]]))
    chk("draw.no_overlap_when_roomy", meta["label_overlaps"] == 0, str(meta["label_overlaps"]))
    chk("draw.label_count_major_only", meta["label_count"] == 8, str(meta["label_count"]))
    _, meta_all = build_annotations("front", view_draw, feats_front, legend=False,
                                    label_minor=True)
    chk("draw.label_minor_switch", meta_all["label_count"] >= meta["label_count"],
        "%s vs %s" % (meta_all["label_count"], meta["label_count"]))
    prims_nl, meta_nl = build_annotations("front", view_draw, feats_front, legend=False)
    chk("draw.no_legend_narrower", meta_nl["sheet_w"] < meta["sheet_w"],
        "%s vs %s" % (meta_nl["sheet_w"], meta["sheet_w"]))
    chk("txt.width_monotonic", _text_w("AB", 10.0) < _text_w("ABC", 10.0))
    chk("txt.truncate_fits",
        _text_w(_truncate("相機平台帶（側視）", 50.0, 9.0), 9.0) <= 50.0,
        _truncate("相機平台帶（側視）", 50.0, 9.0))
    chk("txt.truncate_noop", _truncate("盤", 100.0, 9.0) == "盤")

    tmp_dir = tempfile.mkdtemp(prefix="bp_selftest_")
    svg = os.path.join(tmp_dir, "bp.svg")
    png = os.path.join(tmp_dir, "bp.png")
    emit_svg(prims, meta["sheet_w"], meta["sheet_h"], svg)
    emit_png(prims, None, png, meta["sheet_w"], meta["sheet_h"], scale=1.0)
    chk("io.svg_written", os.path.getsize(svg) > 500, str(os.path.getsize(svg)))
    with open(svg, "r", encoding="utf-8") as fh:
        svg_txt = fh.read()
    chk("io.svg_is_svg", svg_txt.startswith("<?xml") and "<svg" in svg_txt)
    chk("io.svg_has_feature_id", "F1" in svg_txt and "A-1" in svg_txt)
    chk("io.png_written", os.path.getsize(png) > 1000, str(os.path.getsize(png)))
    arr = np.asarray(_pil()[0].open(png).convert("RGB"))
    non_white = float((arr.sum(axis=2) < 720).mean())
    chk("io.png_has_ink", non_white > 0.0005, "ink frac %.5f" % non_white)

    # --- 元件 JSON 往返 ---
    comp_path = os.path.join(tmp_dir, "comps.json")
    save_components(comps2, comp_path, meta={"subject": "selftest"})
    back, bmeta = load_components(comp_path)
    chk("io.components_roundtrip",
        len(back) == 1 and back[0]["bbox_mm"] == comps2[0]["bbox_mm"] and
        bmeta.get("subject") == "selftest", str(back))
    bad_schema = os.path.join(tmp_dir, "bad.json")
    with open(bad_schema, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"schema": "nope/9", "components": []}))
    try:
        load_components(bad_schema)
        chk("io.schema_guard", False, "no raise")
    except ValueError:
        chk("io.schema_guard", True)

    for p in (svg, png, comp_path, bad_schema):
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.rmdir(tmp_dir)
    except OSError:
        pass
    return checks, fails


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        c, f = _selftest()
        for name in c:
            print("  ok:", name)
        print("TOTAL_CHECKS: %d" % len(c))
        print("TOTAL_CHECKS_FAILED: %d" % len(f))
        for x in f:
            print("  FAIL:", x)
        sys.exit(1 if f else 0)
    argv = sys.argv[1:]
    if "--calib" in argv:
        def _arg(flag, default=None):
            return argv[argv.index(flag) + 1] if flag in argv else default
        imgs = {}
        i = 0
        while i < len(argv):
            if argv[i] == "--image" and i + 1 < len(argv):
                pair = argv[i + 1].split("=", 1)
                if len(pair) == 2:
                    imgs[pair[0]] = pair[1]
                i += 1
            i += 1
        majors = {}
        i = 0
        while i < len(argv):
            if argv[i] == "--major" and i + 1 < len(argv):
                pair = argv[i + 1].split("=", 1)
                if len(pair) == 2:
                    majors[pair[0]] = float(pair[1])
                i += 1
            i += 1
        major_min = majors or float(_arg("--major-min-mm", DEFAULT_MAJOR_MIN_MM))
        res = render_blueprint(_arg("--calib"), _arg("--out", "blueprint_out"),
                               components=_arg("--components"), images=imgs or None,
                               font_px=float(_arg("--font-px", DEFAULT_FONT_PX)),
                               sheet_scale=float(_arg("--sheet-scale", 1.0)),
                               png_scale=float(_arg("--png-scale", DEFAULT_PNG_SCALE)),
                               major_min_mm=major_min,
                               label_minor=("--all-features" in argv),
                               legend=("--no-legend" not in argv))
        for name, info in res["views"].items():
            print("VIEW %s: %d features, %d components, %d issues, %d label_overlaps -> %s"
                  % (name, len(info["features"]), len(info["components"]),
                     len(info["issues"]), info["label_overlaps"], info["svg"]))
        if res.get("data_path"):
            print("DATA: %s" % res["data_path"])
        sys.exit(0)
    print(__doc__)
