# -*- coding: utf-8 -*-
# KEYWORDS: blender, triview, orthographic, silhouette, contour, calibration, 三視圖, 輪廓, 校準
"""
triview_lib.py — 三視圖（正／側／頂）參考圖的載入、輪廓萃取與尺度校準。

定位
----
「照著三視圖建模」這條路線，本質是把雕塑問題轉成量測問題：圖已經把比例與
輪廓回答完了，建模者只做「校準 → 萃取 → 放樣 → 驗證」。本模組負責最前面
兩個確定性步驟：

  Stage 0  對位與校準（common scale / datum）
           三張圖放進同一個 mm 座標系，並驗證彼此比例自洽。
  Stage 1  輪廓萃取（silhouette extraction）
           從每張圖取出外輪廓折線，簡化成可用的特徵點序列。

產物是 triview_calib.json（純資料）。後續的斷面合成／放樣／拓撲正規化在
Blender 端進行，只讀這份 JSON，不再碰圖片——圖片處理與幾何生成徹底解耦。

執行環境
--------
純 Python 3 + numpy + Pillow，**不需要 bpy**。影像處理端用工作區 venv
（run_python_native，或你的 agent 平台上等價的「執行一段腳本」工具）執行，與 assets/overlay_tools.py 同一個先例（Blender
內建 Python 沒有 Pillow）。Pillow 採延遲載入（`_pil()`），因此 Blender 端
的消費者仍可安全 `import triview_lib` 只為了呼叫 load_calib()/save_calib()。

座標與單位公約
--------------
- 影像座標：像素 (x, y)，x 向右、y 向下，原點左上（影像慣例）。
- 世界座標：mm (x, y)，x 向右、y **向上**（數學慣例）——to_mm_contour() 翻轉 y。
- 每個 view 自帶 px_per_mm；跨視圖比較前各自換算成 mm 再比。
- 輪廓方向正規化：像素座標下 signed area 為**正**（等價於世界座標下的逆時針）。
  起點正規化到最上列最左點，讓同一份圖重跑結果可逐點比對。
- 「正視圖」＝從 -Y 看向 +Y（相機側），與 SKILL.md §12 方向公約一致。

已知限制（誠實記錄）
--------------------
1. 本模組處理「已裁到單一視圖面板」的圖。`find_panels()` 只在留白充足時可靠；
   密集工程圖（尺寸線橫跨面板之間）常需人工指定 bbox——面板辨識是設定步驟，
   不是自動化保證，請把它當輔助而不是關卡。
2. 只做外輪廓。視覺外殼天生抓不到凹陷（輪拱、腋下開孔、內縮艙口），那些要靠
   加量測視角或後續特徵線放樣補。
3. 門檻是單一全域值；光線不均的照片需先做區域正規化（未內建）。
4. 不處理透視。輸入必須是正交／近正交視角，透視圖請先做校正。
"""

from __future__ import annotations

import json
import math
import os
import time

import numpy as np

SCHEMA = "triview_calib/1"

# 預設值集中在此，呼叫端一律用具名參數覆寫，不要在函式體內散落魔法數字
DEFAULT_INK_THRESHOLD = None      # None → 自動 Otsu
DEFAULT_SIMPLIFY_FRAC = 0.0012    # Douglas-Peucker epsilon = 輪廓對角線 × 此值
DEFAULT_MIN_GUTTER_PX = 18        # find_panels：判定留白溝的最小寬度
DEFAULT_MIN_PANEL_PX = 120        # find_panels：最小面板邊長
DEFAULT_PANEL_INK_FRAC = 0.004    # find_panels：投影視為「有料」的最低墨量比例


# --------------------------------------------------------------------------
# 延遲載入 Pillow（讓 Blender 端 import 本模組時不因缺 Pillow 而失敗）
# --------------------------------------------------------------------------
def _pil():
    from PIL import Image, ImageDraw  # noqa: WPS433 (lazy import by design)
    return Image, ImageDraw


# --------------------------------------------------------------------------
# Stage 0-1 · 影像基本操作
# --------------------------------------------------------------------------
def load_image(path):
    """讀入影像 → uint8 ndarray。回傳 (H, W, 3) RGB；有 alpha 先合成到白底。"""
    Image, _ = _pil()
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    return np.asarray(im, dtype=np.uint8)


def to_gray(rgb):
    """RGB(A) → 灰階 uint8。已是 2D 陣列則原樣回傳。"""
    a = np.asarray(rgb)
    if a.ndim == 2:
        return a.astype(np.uint8)
    a = a.astype(np.float32)
    if a.shape[2] == 4:
        alpha = a[:, :, 3:4] / 255.0
        a = a[:, :, :3] * alpha + 255.0 * (1.0 - alpha)
    g = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    return np.clip(g, 0, 255).astype(np.uint8)


def otsu_threshold(gray):
    """Otsu 全域門檻。回傳 0-255 整數。"""
    hist = np.bincount(np.asarray(gray, dtype=np.uint8).ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return 128
    omega = np.cumsum(hist)
    mu = np.cumsum(hist * np.arange(256, dtype=np.float64))
    mu_t = mu[-1]
    denom = omega * (total - omega)
    denom[denom <= 0] = 1e-12
    sigma_b = (mu_t * omega - total * mu) ** 2 / denom
    peak = float(sigma_b.max())
    if peak <= 0.0:
        return 128
    # 取「高原」中點而非首個極大值：完美雙峰的圖（例如純 0／255 的合成測試圖）
    # 整段都達極大，argmax 會回 0 讓門檻失效；取中點同時滿足合成圖與真實灰階圖。
    plateau = np.nonzero(sigma_b >= peak * 0.999)[0]
    return int(round(float(plateau.mean())))


def to_ink_mask(gray, threshold=None):
    """dark-ink-on-light-paper：墨線為 True。threshold=None → 自動 Otsu。"""
    th = otsu_threshold(gray) if threshold is None else int(threshold)
    return np.asarray(gray) < th


def crop(rgb, bbox):
    """bbox = (x0, y0, x1, y1)，含端點。回傳裁切後影像（不複製灰階）。"""
    x0, y0, x1, y1 = [int(v) for v in bbox]
    return np.asarray(rgb)[y0:y1 + 1, x0:x1 + 1]


# --------------------------------------------------------------------------
# Stage 0 · 面板分割（best-effort）
# --------------------------------------------------------------------------
def _segments_from_profile(profile, min_gutter, min_len, ink_frac):
    limit = max(1.0, float(profile.max()) * float(ink_frac))
    segs, start, gap = [], None, 0
    for i, solid in enumerate(profile > limit):
        if solid:
            if start is None:
                start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gutter:
                end = i - gap
                if end - start + 1 >= min_len:
                    segs.append((start, end))
                start, gap = None, 0
    if start is not None and (len(profile) - start) >= min_len:
        segs.append((start, len(profile) - 1))
    return segs


def find_panels(gray, threshold=None, min_gutter=DEFAULT_MIN_GUTTER_PX,
                min_panel=DEFAULT_MIN_PANEL_PX, ink_frac=DEFAULT_PANEL_INK_FRAC):
    """best-effort：用墨量投影的留白溝切出面板候選，依面積由大到小回傳。

    回傳 [{'bbox': (x0,y0,x1,y1), 'ink_px': int, 'area': int}, ...]。
    密集工程圖常失敗——失敗時請用人工 bbox 走 extract_silhouette()。
    """
    ink = to_ink_mask(gray, threshold)
    cols = _segments_from_profile(ink.sum(axis=0), min_gutter, min_panel, ink_frac)
    rows = _segments_from_profile(ink.sum(axis=1), min_gutter, min_panel, ink_frac)
    panels = []
    for x0, x1 in cols:
        for y0, y1 in rows:
            sub = ink[y0:y1 + 1, x0:x1 + 1]
            n = int(sub.sum())
            if n == 0:
                continue
            panels.append({
                "bbox": (int(x0), int(y0), int(x1), int(y1)),
                "ink_px": n,
                "area": int((x1 - x0 + 1) * (y1 - y0 + 1)),
            })
    panels.sort(key=lambda p: p["area"], reverse=True)
    return panels


# --------------------------------------------------------------------------
# Stage 1 · 遮罩清理
# --------------------------------------------------------------------------
def fill_holes(mask):
    """把被墨線圍住的中空區域填滿（剖面線／hatching 的內部空隙）。

    做法：從影像邊界對「非墨」像素做洪水填充，走不到的即為密閉洞。
    """
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    free = ~m
    visited = np.zeros((h, w), dtype=bool)
    stack = []
    for x in range(w):
        if free[0, x] and not visited[0, x]:
            visited[0, x] = True
            stack.append((0, x))
        if free[h - 1, x] and not visited[h - 1, x]:
            visited[h - 1, x] = True
            stack.append((h - 1, x))
    for y in range(h):
        if free[y, 0] and not visited[y, 0]:
            visited[y, 0] = True
            stack.append((y, 0))
        if free[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True
            stack.append((y, w - 1))
    while stack:
        y, x = stack.pop()
        if y > 0 and free[y - 1, x] and not visited[y - 1, x]:
            visited[y - 1, x] = True
            stack.append((y - 1, x))
        if y < h - 1 and free[y + 1, x] and not visited[y + 1, x]:
            visited[y + 1, x] = True
            stack.append((y + 1, x))
        if x > 0 and free[y, x - 1] and not visited[y, x - 1]:
            visited[y, x - 1] = True
            stack.append((y, x - 1))
        if x < w - 1 and free[y, x + 1] and not visited[y, x + 1]:
            visited[y, x + 1] = True
            stack.append((y, x + 1))
    return m | (free & ~visited)


def block_reduce_max(mask, factor):
    """區塊最大值降採樣（任何一個像素是墨 → 該區塊是墨），保留細線不折斷。"""
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    h2, w2 = h // factor, w // factor
    if h2 < 1 or w2 < 1:
        return m
    m = m[:h2 * factor, :w2 * factor]
    return m.reshape(h2, factor, w2, factor).any(axis=(1, 3))


def label_components(mask):
    """4-連通連通塊標記。回傳 (labels: int32 (H,W)，背景為 0, sizes: list)。"""
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    lab = np.zeros((h, w), dtype=np.int32)
    sizes, cur = [], 0
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0] != 0:
            continue
        cur += 1
        stack = [(int(y0), int(x0))]
        lab[y0, x0] = cur
        n = 0
        while stack:
            y, x = stack.pop()
            n += 1
            if y > 0 and m[y - 1, x] and lab[y - 1, x] == 0:
                lab[y - 1, x] = cur
                stack.append((y - 1, x))
            if y < h - 1 and m[y + 1, x] and lab[y + 1, x] == 0:
                lab[y + 1, x] = cur
                stack.append((y + 1, x))
            if x > 0 and m[y, x - 1] and lab[y, x - 1] == 0:
                lab[y, x - 1] = cur
                stack.append((y, x - 1))
            if x < w - 1 and m[y, x + 1] and lab[y, x + 1] == 0:
                lab[y, x + 1] = cur
                stack.append((y, x + 1))
        sizes.append(n)
    return lab, sizes


def largest_component(mask):
    """取最大連通塊。回傳 (mask, size_px)。用來甩掉孤立的尺寸線/圖框。"""
    m = np.asarray(mask, dtype=bool)
    lab, sizes = label_components(m)
    if not sizes:
        return m, 0
    best = int(np.argmax(sizes)) + 1
    return lab == best, sizes[best - 1]


def tighten_body_bbox(mask, dense_frac=0.40, min_run_px=40):
    """從「機身 + 相連尺寸線」的遮罩中收斂出機身本身的 bbox。

    工程圖的機身外框是封閉的，補洞後內部會變成實心（高密度）；相連的尺寸線是
    細線（低密度）。沿列／行算墨量，取連續高密度區段即為機身。
    dense_frac：門檻為「最大列墨量」的比例。min_run_px：最小連續長度（濾雜訊）。

    回傳 (x0, y0, x1, y1) 或 None。
    """
    m = np.asarray(mask, dtype=bool)
    if not m.any():
        return None

    def _span(profile):
        peak = float(profile.max())
        if peak <= 0:
            return None
        hot = profile >= peak * dense_frac
        best, cur = None, None
        for i, v in enumerate(hot):
            if v and cur is None:
                cur = i
            elif not v and cur is not None:
                if best is None or (i - cur) > (best[1] - best[0]):
                    best = (cur, i - 1)
                cur = None
        if cur is not None and (best is None or (len(hot) - cur) > (best[1] - best[0])):
            best = (cur, len(hot) - 1)
        if best is None or (best[1] - best[0] + 1) < min_run_px:
            return None
        return best

    xs = _span(m.sum(axis=0))
    ys = _span(m.sum(axis=1))
    if xs is None or ys is None:
        return None
    return (int(xs[0]), int(ys[0]), int(xs[1]), int(ys[1]))


def extract_view_body(img, roi, threshold=None, expect_aspect=None, aspect_tol=0.06,
                      dense_frac=0.40, simplify_frac=DEFAULT_SIMPLIFY_FRAC):
    """在 roi=(x0,y0,x1,y1) 內萃取「機身」：補洞 → 最大連通塊 → 密度收斂 → 輪廓。

    這是工程圖單一視圖的正式入口（find_panels 在密集圖上不可靠時的替代路徑：
    人工／半自動給 ROI，程式負責收斂與萃取）。

    回傳 dict：contour_px / bbox_px（全圖座標）/ wh_px / aspect / ok / issues
    expect_aspect：h/w 期望值；給了就驗證收斂結果，不符時 ok=False 並記 issues。
    """
    sub = crop(img, roi)
    gray = to_gray(sub)
    th = otsu_threshold(gray) if threshold is None else int(threshold)
    mask = fill_holes(to_ink_mask(gray, th))
    mask, _ = largest_component(mask)
    tight = tighten_body_bbox(mask, dense_frac=dense_frac)
    issues = []
    if tight is None:
        return {"contour_px": [], "bbox_px": None, "wh_px": (0, 0), "aspect": 0.0,
                "ok": False, "issues": ["tighten_body_bbox found no dense span"]}
    x0, y0, x1, y1 = tight
    body = np.zeros_like(mask)
    body[y0:y1 + 1, x0:x1 + 1] = mask[y0:y1 + 1, x0:x1 + 1]
    raw = trace_outer_contour(body)
    if not raw:
        return {"contour_px": [], "bbox_px": None, "wh_px": (0, 0), "aspect": 0.0,
                "ok": False, "issues": ["empty contour after tightening"]}
    bb = contour_bbox(raw)
    diag = math.hypot(bb[2] - bb[0], bb[3] - bb[1])
    simp = normalize_contour(simplify_contour(raw, eps=max(0.5, diag * simplify_frac)))
    offx, offy = int(roi[0]), int(roi[1])
    contour = [[int(p[0]) + offx, int(p[1]) + offy] for p in simp]
    gx0, gy0 = bb[0] + offx, bb[1] + offy
    gx1, gy1 = bb[2] + offx, bb[3] + offy
    w_px, h_px = gx1 - gx0 + 1, gy1 - gy0 + 1
    aspect = h_px / float(max(1, w_px))
    if expect_aspect is not None:
        rel = abs(aspect - expect_aspect) / float(expect_aspect)
        if rel > aspect_tol:
            issues.append("aspect %.4f vs expected %.4f (rel %.2f%% > %.2f%%)"
                          % (aspect, expect_aspect, rel * 100.0, aspect_tol * 100.0))
    return {"contour_px": contour, "bbox_px": [gx0, gy0, gx1, gy1],
            "wh_px": (w_px, h_px), "aspect": round(aspect, 4),
            "threshold": th, "ok": not issues, "issues": issues}


def _hot_runs(profile, frac, min_len):
    """回傳 profile 中「≥ 峰值×frac」的連續區段（長度 ≥ min_len）。"""
    peak = float(profile.max())
    if peak <= 0:
        return []
    hot = profile >= peak * frac
    runs, s = [], None
    for i, v in enumerate(hot):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s >= min_len:
                runs.append((s, i - 1))
            s = None
    if s is not None and len(hot) - s >= min_len:
        runs.append((s, len(hot) - 1))
    return runs


def extract_thin_body(img, roi, threshold=None, col_frac=0.80, min_col_px=12,
                      simplify_frac=DEFAULT_SIMPLIFY_FRAC):
    """薄型視圖（側視圖）的機身萃取。

    側視圖的機身是「全高、細長」的一條：沿列（column）算墨量，機身那些列會
    接近全高，而尺寸線／引出線的列只有局部高度。因此用「接近峰值的連續列段」
    定位機身寬度，再把輪廓限制在該列帶內取高度。

    回傳 dict：contour_px / bbox_px / wh_px / aspect / ok / issues；
    thickness_mm 需由呼叫端用該視圖的 px_per_mm 換算（本函式不假設尺度）。
    """
    sub = crop(img, roi)
    gray = to_gray(sub)
    th = otsu_threshold(gray) if threshold is None else int(threshold)
    mask = fill_holes(to_ink_mask(gray, th))
    mask, _ = largest_component(mask)
    cols = mask.sum(axis=0)
    runs = _hot_runs(cols, col_frac, min_col_px)
    if not runs:
        return {"contour_px": [], "bbox_px": None, "wh_px": (0, 0), "aspect": 0.0,
                "ok": False, "issues": ["no full-height column band found"]}
    cx0, cx1 = max(runs, key=lambda r: r[1] - r[0])
    band = np.zeros_like(mask)
    band[:, cx0:cx1 + 1] = mask[:, cx0:cx1 + 1]
    nz = np.argwhere(band)
    if nz.size == 0:
        return {"contour_px": [], "bbox_px": None, "wh_px": (0, 0), "aspect": 0.0,
                "ok": False, "issues": ["empty band"]}
    cy0, cy1 = int(nz[:, 0].min()), int(nz[:, 0].max())
    body = np.zeros_like(mask)
    body[cy0:cy1 + 1, cx0:cx1 + 1] = mask[cy0:cy1 + 1, cx0:cx1 + 1]
    raw = trace_outer_contour(body)
    if not raw:
        return {"contour_px": [], "bbox_px": None, "wh_px": (0, 0), "aspect": 0.0,
                "ok": False, "issues": ["empty contour"]}
    bb = contour_bbox(raw)
    diag = math.hypot(bb[2] - bb[0], bb[3] - bb[1])
    simp = normalize_contour(simplify_contour(raw, eps=max(0.5, diag * simplify_frac)))
    offx, offy = int(roi[0]), int(roi[1])
    contour = [[int(p[0]) + offx, int(p[1]) + offy] for p in simp]
    gx0, gy0 = bb[0] + offx, bb[1] + offy
    gx1, gy1 = bb[2] + offx, bb[3] + offy
    w_px, h_px = gx1 - gx0 + 1, gy1 - gy0 + 1
    return {"contour_px": contour, "bbox_px": [gx0, gy0, gx1, gy1],
            "wh_px": (w_px, h_px), "aspect": round(h_px / float(max(1, w_px)), 4),
            "threshold": th, "col_band": (cx0 + offx, cx1 + offx),
            "ok": True, "issues": []}


def find_body_candidates(gray, threshold=None, downscale=4, min_area_px=20000,
                         aspect_range=(1.4, 4.0), use_fill=False, limit=20):
    """在全頁上定位「像主體」的大型圖形，回傳全解析度 bbox 候選。

    密集工程圖的留白溝切分（find_panels）常失效，這支走另一條路：把墨遮罩
    降採樣後標連通塊，再用「面積 + 長寬比」挑出主體輪廓。降採樣只是為了快速
    定位，真正的輪廓萃取仍在全解析度裁切上進行。

    use_fill 預設 **False**：工程圖通常有外框，先把整頁補洞會讓「被外框圍住的
    整張圖」變成單一巨型連通塊（實測：補洞後只剩一個 2320×1480 的實心塊）。
    要補洞請先裁掉外框，或在已裁好的單一視圖上呼叫 extract_silhouette()。

    aspect_range=None → 不過濾長寬比，回傳全部大型連通塊（診斷用）。
    回傳 [{bbox, wh_px, area_px, aspect}, ...]（依面積由大到小）。
    """
    ink = to_ink_mask(gray, threshold)
    small = block_reduce_max(ink, downscale)
    if use_fill:
        small = fill_holes(small)
    lab, sizes = label_components(small)
    H, W = gray.shape
    out = []
    for i, n in enumerate(sizes, start=1):
        area = n * downscale * downscale
        if area < min_area_px:
            continue
        ys, xs = np.nonzero(lab == i)
        x0, y0 = int(xs.min()) * downscale, int(ys.min()) * downscale
        x1 = min(W - 1, (int(xs.max()) + 1) * downscale - 1)
        y1 = min(H - 1, (int(ys.max()) + 1) * downscale - 1)
        w_px, h_px = x1 - x0 + 1, y1 - y0 + 1
        aspect = h_px / float(max(1, w_px))
        if aspect_range is not None and not (aspect_range[0] <= aspect <= aspect_range[1]):
            continue
        out.append({"bbox": (x0, y0, x1, y1), "wh_px": (w_px, h_px),
                    "area_px": int(area), "aspect": round(aspect, 4)})
    out.sort(key=lambda d: d["area_px"], reverse=True)
    return out[:limit]


# --------------------------------------------------------------------------
# Stage 1 · 輪廓追蹤與簡化
# --------------------------------------------------------------------------
# 8 鄰域，順時針，起點西（配合「起點左側必為背景」的性質）
_RING = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1)]


def trace_outer_contour(mask):
    """Moore 鄰域邊界追蹤。回傳像素座標序列 [(x, y), ...]（含起點，不含重複終點）。"""
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    nz = np.argwhere(m)
    if nz.size == 0:
        return []
    sy, sx = int(nz[0][0]), int(nz[0][1])   # 最上列最左點 → 其西側必為背景
    start = (sx, sy)
    b, c = start, (sx - 1, sy)
    contour = [start]
    max_iter = 8 * int(m.sum()) + 64
    for _ in range(max_iter):
        di = _RING.index((c[0] - b[0], c[1] - b[1]))
        nxt = None
        for k in range(8):
            idx = (di + k) % 8
            nb = (b[0] + _RING[idx][0], b[1] + _RING[idx][1])
            if 0 <= nb[0] < w and 0 <= nb[1] < h and m[nb[1], nb[0]]:
                nxt = (idx, nb)
                break
        if nxt is None:
            break
        idx, nb = nxt
        prev = _RING[(idx - 1) % 8]
        c = (b[0] + prev[0], b[1] + prev[1])
        b = nb
        if b == start:
            break
        contour.append(b)
    return contour


def _simplify_open(pts, eps):
    """Douglas-Peucker（迭代版，避免長輪廓遞迴爆棧）。"""
    n = len(pts)
    if n < 3:
        return list(pts)
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        denom = math.hypot(dx, dy)
        best_d, best_k = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            if denom <= 1e-12:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / denom
            if d > best_d:
                best_d, best_k = d, k
        if best_d > eps:
            keep[best_k] = True
            stack.append((i, best_k))
            stack.append((best_k, j))
    return [p for p, k in zip(pts, keep) if k]


def simplify_contour(pts, eps):
    """對封閉輪廓做 Douglas-Peucker：在最遠點切兩段各自簡化，避免接縫失真。"""
    pts = list(pts)
    n = len(pts)
    if n < 5:
        return pts
    p0 = pts[0]
    d = [(p[0] - p0[0]) ** 2 + (p[1] - p0[1]) ** 2 for p in pts]
    k = int(np.argmax(d))
    if k == 0:
        k = n // 2
    a = _simplify_open(pts[:k + 1], eps)
    b = _simplify_open(pts[k:] + [pts[0]], eps)
    return a[:-1] + b[:-1]


def normalize_contour(pts):
    """起點正規化到（最上列 → 最左）並使像素空間 signed area 為正。

    像素 y 向下時 signed area 為正 ⇔ 世界座標（y 向上）下為逆時針。
    """
    if not pts:
        return []
    arr = list(pts)
    top = min(p[1] for p in arr)
    cands = [i for i, p in enumerate(arr) if p[1] == top]
    s = min(cands, key=lambda i: arr[i][0])
    arr = arr[s:] + arr[:s]
    if polygon_area(arr) < 0:
        arr = [arr[0]] + arr[1:][::-1]
    return arr


# --------------------------------------------------------------------------
# 幾何小工具
# --------------------------------------------------------------------------
def contour_bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def polygon_area(pts):
    """Shoelace。正負號代表纏繞方向。"""
    n = len(pts)
    if n < 3:
        return 0.0
    acc = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        acc += x0 * y1 - x1 * y0
    return 0.5 * acc


def rasterize_polygon(pts, size, origin=(0, 0)):
    """在 size=(w, h) 的布林畫布上填實多邊形（even-odd 由 PIL 處理）。"""
    Image, ImageDraw = _pil()
    im = Image.new("1", (int(size[0]), int(size[1])), 0)
    poly = [(float(x - origin[0]), float(y - origin[1])) for x, y in pts]
    if len(poly) >= 3:
        ImageDraw.Draw(im).polygon(poly, fill=1)
    return np.array(im, dtype=bool)


def iou_contours(pts_a, pts_b, pad=4):
    """兩個輪廓（同一座標系、同單位）的 IoU。"""
    xa = contour_bbox(pts_a)
    xb = contour_bbox(pts_b)
    x0 = min(xa[0], xb[0]) - pad
    y0 = min(xa[1], xb[1]) - pad
    x1 = max(xa[2], xb[2]) + pad
    y1 = max(xa[3], xb[3]) + pad
    size = (int(x1 - x0 + 1), int(y1 - y0 + 1))
    ma = rasterize_polygon(pts_a, size, (x0, y0))
    mb = rasterize_polygon(pts_b, size, (x0, y0))
    inter = int((ma & mb).sum())
    union = int((ma | mb).sum())
    return (inter / union) if union else 0.0


def hausdorff(a_pts, b_pts, sample=600):
    """對稱 Hausdorff 距離（同一單位）。點數多時等距抽樣，控制成本。

    **這是「點對頂點」版本，只在兩邊取樣密度相近時可用**：拿粗折線（例如只標了
    13 個點的側視圖輪廓）去比密集的回渲輪廓時，粗折線單邊中點到最近頂點的距離
    可達邊長一半（實測單邊 160mm → 80mm），那是取樣密度差不是形狀差異。
    幾何端要跟粗參考比對時改用 `triview_build.boundary_hausdorff_mm`（點對線段）。
    """
    a = np.asarray(a_pts, dtype=np.float64)
    b = np.asarray(b_pts, dtype=np.float64)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    if len(a) > sample:
        a = a[np.linspace(0, len(a) - 1, sample).astype(int)]
    if len(b) > sample:
        b = b[np.linspace(0, len(b) - 1, sample).astype(int)]
    d_ab = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)).min(axis=1).max()
    d_ba = np.sqrt(((b[:, None, :] - a[None, :, :]) ** 2).sum(-1)).min(axis=1).max()
    return float(max(d_ab, d_ba))


# --------------------------------------------------------------------------
# Stage 1 · 單一視圖的輪廓萃取
# --------------------------------------------------------------------------
def extract_silhouette(img, bbox=None, threshold=None,
                       simplify_frac=DEFAULT_SIMPLIFY_FRAC,
                       keep_largest=True):
    """從一張（已裁或待裁的）圖取出主體外輪廓。

    回傳 dict：
      contour_px   : [[x, y], ...]  像素座標、封閉折線、已正規化方向與起點
      bbox_px      : [x0, y0, x1, y1]
      size_px      : [w, h]
      ink_px       : 主體遮罩像素數（診斷用）
      threshold    : 實際使用的門檻
      area_px      : 多邊形面積
    失敗（找不到任何墨）時 contour_px 為空。
    """
    sub = crop(img, bbox) if bbox is not None else np.asarray(img)
    gray = to_gray(sub)
    th = otsu_threshold(gray) if threshold is None else int(threshold)
    mask = to_ink_mask(gray, th)
    mask = fill_holes(mask)
    size = 0
    if keep_largest:
        mask, size = largest_component(mask)
    if not mask.any():
        return {"contour_px": [], "bbox_px": None, "size_px": [0, 0],
                "ink_px": 0, "threshold": th, "area_px": 0.0}
    raw = trace_outer_contour(mask)
    bb = contour_bbox(raw)
    diag = math.hypot(bb[2] - bb[0], bb[3] - bb[1])
    simp = simplify_contour(raw, eps=max(0.5, diag * simplify_frac))
    simp = normalize_contour(simp)
    offx = int(bbox[0]) if bbox is not None else 0
    offy = int(bbox[1]) if bbox is not None else 0
    contour = [[int(p[0]) + offx, int(p[1]) + offy] for p in simp]
    return {
        "contour_px": contour,
        "bbox_px": [bb[0] + offx, bb[1] + offy, bb[2] + offx, bb[3] + offy],
        "size_px": [bb[2] - bb[0] + 1, bb[3] - bb[1] + 1],
        "ink_px": int(mask.sum()),
        "threshold": th,
        "area_px": abs(polygon_area(contour)),
    }


# --------------------------------------------------------------------------
# Stage 0 · 尺度校準與跨視圖一致性
# --------------------------------------------------------------------------
def calibrate_view(view, known_mm, axis="height"):
    """以一個已知長度鎖定 px_per_mm。axis='height' 量 y 向，'width' 量 x 向。"""
    if not view.get("contour_px"):
        raise ValueError("calibrate_view: view has no contour")
    x0, y0, x1, y1 = view["bbox_px"]
    px = (y1 - y0 + 1) if axis == "height" else (x1 - x0 + 1)
    scale = float(px) / float(known_mm)
    view["px_per_mm"] = scale
    view["calibration"] = {"axis": axis, "known_mm": float(known_mm), "px": int(px)}
    view["dims_mm"] = [round((x1 - x0 + 1) / scale, 4), round((y1 - y0 + 1) / scale, 4)]
    return scale


def to_mm_contour(contour_px, px_per_mm, origin="bbox_bottom_center"):
    """像素輪廓 → mm 輪廓（y 翻正）。原點可選 bbox_bottom_center / bbox_min。"""
    pts = np.asarray(contour_px, dtype=np.float64)
    x0, y0, x1, y1 = contour_bbox(contour_px)
    xs = (pts[:, 0] - x0) / px_per_mm
    ys = (y1 - pts[:, 1]) / px_per_mm
    if origin == "bbox_bottom_center":
        xs = xs - (x1 - x0) / (2.0 * px_per_mm)
    elif origin != "bbox_min":
        raise ValueError("origin must be 'bbox_bottom_center' or 'bbox_min'")
    return [[round(float(a), 4), round(float(b), 4)] for a, b in zip(xs, ys)]


def check_consistency(views, expected_mm, rel_tol=0.02):
    """比對各視圖換算出的 dims_mm 與權威尺寸，回報問題清單（不 raise）。

    expected_mm: {'front': [w, h], 'side': [w, h], ...}
    """
    issues = []
    for name, view in views.items():
        exp = expected_mm.get(name)
        if exp is None or not view.get("dims_mm"):
            continue
        got = view["dims_mm"]
        for i, lbl in enumerate(("width", "height")):
            if exp[i] is None:
                continue
            err = abs(got[i] - exp[i]) / float(exp[i])
            if err > rel_tol:
                issues.append(
                    "%s.%s: %.3fmm vs expected %.3fmm (rel err %.2f%% > %.2f%%)"
                    % (name, lbl, got[i], exp[i], err * 100.0, rel_tol * 100.0)
                )
    return issues


def cross_view_ratio(views, name_a, name_b, axis="height", expected=None, rel_tol=0.03):
    """跨視圖同一物理量的比值檢查（例：正視圖高 vs 側視圖高，兩者應為同一個 163.4mm）。"""
    a = views.get(name_a, {}).get("dims_mm")
    b = views.get(name_b, {}).get("dims_mm")
    if not a or not b:
        return None
    idx = 1 if axis == "height" else 0
    if b[idx] == 0:
        return None
    ratio = a[idx] / b[idx]
    if expected is not None and abs(ratio - expected) / expected > rel_tol:
        return "cross-view %s/%s %s ratio %.4f vs expected %.4f" % (
            name_a, name_b, axis, ratio, expected)
    return None


# --------------------------------------------------------------------------
# 輸出：視覺驗證疊圖 + JSON
# --------------------------------------------------------------------------
def render_overlay(img, contours, out_path, bbox=None, color=(255, 40, 40), width=3):
    """把萃取出的輪廓畫回原圖並存檔——這是「人／視覺模型可驗證」的產物。"""
    Image, ImageDraw = _pil()
    base = Image.fromarray(np.asarray(img, dtype=np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(base)
    if bbox is not None:
        x0, y0, x1, y1 = [int(v) for v in bbox]
        draw.rectangle([x0, y0, x1, y1], outline=(0, 140, 255), width=2)
    seq = contours if isinstance(contours, (list, tuple)) and contours and isinstance(contours[0], (list, tuple)) and contours[0] and isinstance(contours[0][0], (list, tuple)) else [contours]
    for pts in seq:
        if not pts:
            continue
        poly = [(float(p[0]), float(p[1])) for p in pts]
        draw.line(poly + [poly[0]], fill=color, width=width, joint="curve")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    base.save(out_path)
    return out_path


def save_calib(doc, path):
    doc = dict(doc)
    doc.setdefault("schema", SCHEMA)
    doc.setdefault("saved_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    return path


def load_calib(path):
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema") != SCHEMA:
        raise ValueError("load_calib: unexpected schema %r (want %r)" % (doc.get("schema"), SCHEMA))
    return doc


# --------------------------------------------------------------------------
# 自我測試（以跑代審：不需外部檔案，合成圖驗證全套管線）
# --------------------------------------------------------------------------
def _round_rect_mask(w, h, radius, x0, y0, x1, y1):
    yy, xx = np.mgrid[0:h, 0:w]
    inside = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    cx = np.clip(xx, x0 + radius, x1 - radius)
    cy = np.clip(yy, y0 + radius, y1 - radius)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return inside & (dist <= radius)


def _selftest():
    """合成圖驗證：輪廓萃取、簡化、校準、IoU、Hausdorff、JSON 往返。"""
    checks, fails = [], []

    def chk(name, cond, detail=""):
        checks.append(name)
        if not cond:
            fails.append("%s %s" % (name, detail))

    h, w = 900, 420
    body = _round_rect_mask(w, h, 46, 70, 60, 350, 840)
    # 內部剖面線（模擬工程圖 hatching）——應被 fill_holes 吃掉
    hatch = np.zeros_like(body)
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(-h, w + h, 14):
        hatch |= (np.abs((xx + yy) - i) <= 1)
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    canvas[body | (hatch & body)] = 0

    res = extract_silhouette(canvas)
    chk("selftest.contour_found", len(res["contour_px"]) > 8, "got %d pts" % len(res["contour_px"]))
    bb = res["bbox_px"]
    chk("selftest.bbox_x", abs(bb[0] - 70) <= 3 and abs(bb[2] - 350) <= 3, str(bb))
    chk("selftest.bbox_y", abs(bb[1] - 60) <= 3 and abs(bb[3] - 840) <= 3, str(bb))

    truth = [[70, 60], [350, 60], [350, 840], [70, 840]]
    iou_img = iou_contours(res["contour_px"], truth)
    chk("selftest.iou_image", iou_img > 0.985, "iou=%.4f" % iou_img)

    # 校準：宣告高度 = 163.4mm → 檢查換算出的寬度
    view = {"contour_px": res["contour_px"], "bbox_px": res["bbox_px"]}
    calibrate_view(view, 163.4, axis="height")
    chk("selftest.px_per_mm", abs(view["px_per_mm"] - (781 / 163.4)) < 0.05,
        "scale=%.4f" % view["px_per_mm"])
    mm = to_mm_contour(res["contour_px"], view["px_per_mm"])
    xs = [p[0] for p in mm]
    chk("selftest.mm_centered", abs((min(xs) + max(xs)) / 2.0) < 0.6, "cx=%.3f" % ((min(xs) + max(xs)) / 2.0))
    chk("selftest.mm_y_up", abs(min(p[1] for p in mm)) < 0.2 and abs(max(p[1] for p in mm) - 163.4) < 0.4,
        "y=[%.2f, %.2f]" % (min(p[1] for p in mm), max(p[1] for p in mm)))

    chk("selftest.hausdorff_zero", hausdorff(res["contour_px"], res["contour_px"]) < 1e-6)
    chk("selftest.signed_area_positive", polygon_area(res["contour_px"]) > 0)

    issues = check_consistency({"front": view}, {"front": [65.35, 163.4]}, rel_tol=0.02)
    chk("selftest.consistency_flags", len(issues) == 1, "issues=%r" % (issues,))

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_triview_selftest.json")
    save_calib({"views": {"front": {k: v for k, v in view.items() if k != "contour_px"}}}, tmp)
    back = load_calib(tmp)
    os.remove(tmp)
    chk("selftest.json_roundtrip", abs(back["views"]["front"]["px_per_mm"] - view["px_per_mm"]) < 1e-9)

    return checks, fails


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        c, f = _selftest()
        for i in c:
            print("  ok:", i)
        print("TOTAL_CHECKS_FAILED: %d" % len(f))
        for x in f:
            print("  FAIL:", x)
        sys.exit(1 if f else 0)
    print(__doc__)
