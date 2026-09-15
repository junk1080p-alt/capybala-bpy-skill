# -*- coding: utf-8 -*-
# KEYWORDS: blender, component, 元件表, audit, 對賬, 校正, triview, 三視圖, checklist, stage-a
"""component_lib —— 元件表 × 三視圖 的雙向對賬（純 Python 3，只用 stdlib）

定位（SKILL.md §16.9.4）
------------------------------------------------------------------
triview 把「輪廓」變成量測值，blueprint_lib 把它畫成人可指認的圖，
本模組處理再上面一層——**元件（零件）**：Stage A 拆出來的元件表，與三視圖之間的對賬。

兩個檢查點：

  CP1（規劃期：Stage A 元件表完成後、Stage B 動工前）
      audit_depth()       拆解深度（§11 Stage A item 3）：全表最深 LEVEL 是否達到期望值。
                          **不需要 calib／三視圖**——原創設計類也跑得到，這是它過去唯一
                          一條「寫成 MUST 卻沒有任何可執行檢查」的規則。
      audit_coverage()    缺件／盲區：元件宣告的視圖是否存在、框是否落在量測輪廓內、
                          有沒有視圖完全沒被任何元件覆蓋（含 audit_depth，門檻 4）。
      audit_params()      參數可查性：每個元件需要的參數，能不能在圖面標註
                          （annotated_dims_mm）或量測輪廓裡查到；查不到的分級列出。
      render_checklist()  產出給視覺（read_image_native，或你的 agent 平台上等價的視覺輸入
                          工具）逐項核對的 Markdown 清單。

  CP2（建模後：Stage B 框架完成、細節之前）
      compare()           把 component_measure 量到的實測值與元件表的規劃值逐項比對，
                          回報尺寸／位置／方向偏差，並給出建議修正的常數。

資料契約（schema "components/2"）
------------------------------------------------------------------
    {
      "schema": "components/2",
      "subject": "iPhone 17 Pro Max",
      "components": [
        {"id": "A-3", "name": "相機平台", "level": 3,
         "views": ["rear", "side"],
         "bbox_mm": {"rear": [x0, y0, x1, y1], "side": [x0, y0, x1, y1]},
         "params": [{"name": "length_mm", "value": 72.05, "source": "annotation",
                     "conflicts": [{"value": 72.20, "source": "measured",
                                    "note": "掃描線量測"}],
                     "resolved_by": "annotation",
                     "resolution_note": "圖面標註優先於掃描（§16.9 三層權威）"}],
         "objects": ["Mst_CameraPlateau*"],
         "axis": [1, 0, 0],
         "appearance": {"material": "Mat_Anodized*", "finish": "satin",
                        "color_hex": "#2b2f36", "flat_axis": "y",
                        "max_extent_mm": 0.05, "evidence": "photo:rear_closeup.jpg"},
         "locked": true, "verified_at": "v4",
         "change_note": "本輪只收角半徑，尺寸與位置不動", "note": "..."}
      ]
    }

  - v1（"blueprint_components/1"，單一 view + 單一 bbox_mm）可自動升級讀入；
    寫出時一律 v2。
  - 座標系：各視圖的 mm 平面座標，原點在該視圖 bbox 底部中心、u 向右、v 向上
    ——與 triview_calib 的 contour_mm 同系。
  - `params[].source` 分級（權威順序同 SKILL.md §16.9 的三層）：
      annotation  圖面 callout 直給（可由 calib.annotated_dims_mm 驗證）
      measured    可由量測輪廓取得
      derived     由其他參數推算（須在 note 說明來源）
      estimated   無依據的估計，需視覺／規格確認
      missing     完全沒有
  - `objects[]` 支援 fnmatch 萬用字元，供 component_measure 在 .blend 裡找對應物件。
  - `axis` 是期望長軸方向（世界座標單位向量，可選），供 CP2 的方向偏差檢查。
  - `locked` + `verified_at`（選配）：這個元件已通過 CP2 且經確認。**已凍結的元件被
    改動就是違規**——`diff` 會擋下來，要動必須先解鎖並寫 `change_note` 說明理由。
    這解決的是「同一區一輪一輪被重寫、每寫一次洗掉上一次」的迴圈。
  - `change_note`（選配）：本輪對這個元件改了什麼、為什麼。`diff` 會列出沒寫的元件。
  - `appearance`（選配但 CP1 會要求）：外觀規格——`material`（期望材質名的 fnmatch
    樣式，由 component_measure 回報的 `materials` 驗）、`finish`/`color_hex`（記錄用）、
    `flat_axis` + `max_extent_mm`（該貼合的表面沿該世界軸的最大厚度，防「說好要平面化
    卻做成立體」）、`evidence`（**必填**：這個外觀判斷的依據，`annotation`／
    `photo:<檔名>`／`reference:<url>`／`mat_lib:<factory>`）。
    不驗外觀的元件（內部不可見件、void 開口）改用 `appearance_skipped: "<理由>"` 明講。
  - `params[].conflicts` + `resolved_by`（選配但 CP1 會擋）：同一個尺寸出現互斥來源
    （圖面標註 vs 掃描量測 vs 兩張圖給不同數字）時，**全部候選值都要記在 `conflicts`**，
    並用 `resolved_by` + `resolution_note` 寫明由誰、依什麼裁定。**未結衝突（有
    conflicts 卻沒有 resolved_by）會讓 CP1 直接失敗**——禁止靜默挑一個「看起來比較
    合理」的值往下走。
  - meta 的 `open_items[]`：已知但未結案的落差，audit 會原樣列出（不擋，但必須出現在
    交付說明裡，不得靜默消失）。

視圖 → 世界軸對應（Blender 世界座標，Z 上、主體正面朝 -Y）
------------------------------------------------------------------
    front : u=+X, v=+Z        rear : u=-X, v=+Z
    side  : u=+Y, v=+Z        back : u=-Y, v=+Z
    top   : u=+X, v=+Y        bottom : u=+X, v=-Y

  **rear / back 是鏡像視圖**（u 軸取負）：同一件偏 +X 的零件在 front 的 u 為正、
  在 rear 的 u 為負。這跟「繞到背後看產品」的直覺一致，也是 calib 的 front/rear
  輪廓左右對稱時看不出差異的原因——非對稱件（相機平台、側鍵、連接埠）才會暴露。
  因此**填元件表的 rear/back 框時，u 值照「圖上看到的左右」填，不要直接抄世界 x**
  （這個約定由 `_selftest` 的 `mirror.rear.u` / `mirror.back.u` 鎖住）。

執行環境
------------------------------------------------------------------
純 Python 3（stdlib only），**不經 bpy、不依賴 numpy/Pillow**——所以它能在任何
Python 直譯器裡跑，也能被 Blender 端 import。這一點與 triview_lib 的影像端刻意不同：
本模組做的是資料對賬，不需要點陣圖能力。

CLI
------------------------------------------------------------------
    python component_lib.py audit     --calib C --components K --out DIR
    python component_lib.py checklist --calib C --components K --out DIR
    python component_lib.py compare   --calib C --components K --measured M --out DIR
    python component_lib.py diff      --old A.json --new B.json --out DIR [--scope ...]
    python component_lib.py depth     --components K [--min-level 6] [--out DIR]
    python component_lib.py selftest

  audit = CP1-A 覆蓋／盲區 + CP1-B 參數可查性 + CP1-C 外觀規格，任一有問題就 exit 1。
  depth = CP1-A0 拆解深度（§11 Stage A item 3）：**不需要 calib／三視圖**，是原創設計類
          （§16.9.0 B 類，沒有參考圖可量）唯一的結構性閘門，深度不足 exit 1。
  diff  = 版本史：兩個元件表之間的逐項變更 + 已凍結元件被改動的違規，有違規 exit 1。

已知限制
------------------------------------------------------------------
  1. 缺件檢查只做「幾何/資料層」的自動判定（視圖盲區、框超界、參數來源虛報）。
     真正的「圖上有、表中沒有」要靠 render_checklist() 產出的清單 + 視覺核對，
     本模組不假裝能取代那一步。
  2. compare() 的方向偏差需要 component_measure 提供 PCA 主軸；只給 AABB 時略過方向項。
  3. 位置偏差以 AABB 中心為準——對非對稱元件，中心偏移不等於錯位，仍要看兩個邊的
     各自偏移（本模組兩者都報）。
  4. 開口類元件（USB 孔/麥克風孔/SIM 卡槽）在元件表標 `"void": true` + `"host"`，
     compare() 只驗 host 是否存在、不進缺件清單——AABB 對「空洞」沒有意義，硬量會
     拿到 host 的尺寸而誤判為尺寸偏差。
"""

import argparse
import fnmatch
import json
import math
import os
import sys

SCHEMA_V1 = "blueprint_components/1"
SCHEMA = "components/2"
MEASURED_SCHEMA = "components_measured/1"

# (u_axis, v_axis, u_sign, v_sign)；軸索引對應世界 [x, y, z]
VIEW_AXES = {
    "front": (0, 2, 1.0, 1.0),
    "rear": (0, 2, -1.0, 1.0),
    "side": (1, 2, 1.0, 1.0),
    "back": (1, 2, -1.0, 1.0),
    "top": (0, 1, 1.0, 1.0),
    "bottom": (0, 1, 1.0, -1.0),
}

PARAM_SOURCES = ("annotation", "measured", "derived", "estimated", "missing")

# --- 預設容差（呼叫端一律用具名參數覆寫） ---
DEFAULT_CONTAIN_TOL_MM = 0.5     # 元件框允許超出量測輪廓的量
DEFAULT_POS_TOL_MM = 0.5         # CP2 位置偏差門檻
DEFAULT_SIZE_TOL_MM = 0.5        # CP2 尺寸偏差門檻
DEFAULT_ANG_TOL_DEG = 2.0        # CP2 方向偏差門檻
DEFAULT_ANN_TOL_MM = 0.01        # 標註值比對容差
DEFAULT_AXIS_NAMES = {
    0: ("X", "寬"),
    1: ("Y", "深"),
    2: ("Z", "高"),
}

# --- 外觀／凍結／深度 ---
AXIS_INDEX = {"x": 0, "y": 1, "z": 2}
APPEARANCE_MIN_EVIDENCE_CHARS = 3   # evidence 至少要有意義的幾個字元
# 元件表深度下限（CP1-A 預設）：低於此值的表幾乎無法支撐 CP2 逐件校正（§11 LEVEL 1–6 的精神）
MIN_EXPECTED_COMPONENT_LEVEL = 4
# 原創設計類（§16.9.0 B 類，無參考圖可量）的期望深度＝§11 Stage A item 3 的六級。
# 兩者不同是有理由的：三視圖流程至少還有量測輪廓能逐件校正，原創設計類沒有——深度
# 就是它唯一能防止「物件很多但讀起來很粗糙」的結構性防線，所以 `depth` 子命令預設用它。
MIN_EXPECTED_COMPONENT_LEVEL_ORIGINAL = 6


# --------------------------------------------------------------------------
# 基本幾何（純 math）
# --------------------------------------------------------------------------
def _r(v, n=4):
    return round(float(v), n)


def bbox_center(b):
    """[u0,v0,u1,v1] → [cu, cv]"""
    return [_r((b[0] + b[2]) / 2.0), _r((b[1] + b[3]) / 2.0)]


def bbox_size(b):
    """[u0,v0,u1,v1] → [ du, dv ]，永遠為正。"""
    return [_r(abs(b[2] - b[0])), _r(abs(b[3] - b[1]))]


def aabb_to_view_bbox(aabb, view):
    """世界軸對齊盒 [x0,y0,z0,x1,y1,z1]（mm） → 該視圖 [u0,v0,u1,v1]（mm 平面）。

    輸入的 min/max 順序可以不整齊（呼叫端不必先排序）。
    """
    if view not in VIEW_AXES:
        raise ValueError("unknown view %r (known: %s)" % (view, sorted(VIEW_AXES)))
    ua, va, us, vs = VIEW_AXES[view]
    uu = sorted([us * float(aabb[ua]), us * float(aabb[ua + 3])])
    vv = sorted([vs * float(aabb[va]), vs * float(aabb[va + 3])])
    return [_r(uu[0]), _r(vv[0]), _r(uu[1]), _r(vv[1])]


def view_delta_to_world(view, du, dv):
    """把某視圖的平面位移 (du, dv) 轉回世界軸分量 [dx, dy, dz]（mm）。"""
    ua, va, us, vs = VIEW_AXES[view]
    out = [0.0, 0.0, 0.0]
    out[ua] += us * float(du)
    out[va] += vs * float(dv)
    return [_r(v) for v in out]


def merge_bbox(boxes):
    """多個 [u0,v0,u1,v1] 的聯集；空清單回 None。"""
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def contour_bbox(contour):
    """量測輪廓 → [x0,y0,x1,y1]（mm）。"""
    if not contour:
        return None
    xs = [float(p[0]) for p in contour]
    ys = [float(p[1]) for p in contour]
    return [min(xs), min(ys), max(xs), max(ys)]


def angle_between_axes(a, b):
    """兩個方向向量的夾角（度），取軸向（無正負），退化回 0。"""
    la = math.sqrt(sum(float(v) ** 2 for v in a))
    lb = math.sqrt(sum(float(v) ** 2 for v in b))
    if la < 1e-9 or lb < 1e-9:
        return 0.0
    dot = sum(float(a[i]) * float(b[i]) for i in range(3)) / (la * lb)
    return _r(math.degrees(math.acos(max(-1.0, min(1.0, abs(dot))))), 2)


# --------------------------------------------------------------------------
# 元件表：讀取／正規化／寫出
# --------------------------------------------------------------------------
def _expand_center_size(center, size):
    cx, cy = float(center[0]), float(center[1])
    w, h = float(size[0]), float(size[1])
    return [cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0]


def normalize_component(raw):
    """單筆元件 → 內部形狀（_views / _bbox / _params），保留原欄位。"""
    c = dict(raw)
    cid = c.get("id")
    if not cid:
        raise ValueError("component without id: %r" % (raw,))

    bbox = c.get("bbox_mm")
    if isinstance(bbox, dict):
        by_view = {k: [float(x) for x in v] for k, v in bbox.items()}
    elif bbox is not None:
        v0 = c.get("view")
        if not v0:
            raise ValueError("component %s: bbox_mm is a list but no 'view' given" % cid)
        by_view = {v0: [float(x) for x in bbox]}
    elif "center_mm" in c and "size_mm" in c:
        v0 = c.get("view") or (c.get("views") or ["front"])[0]
        by_view = {v0: _expand_center_size(c["center_mm"], c["size_mm"])}
    else:
        by_view = {}

    for v, b in by_view.items():
        if len(b) != 4:
            raise ValueError("component %s view %s: bbox must be [u0,v0,u1,v1]" % (cid, v))
        if v not in VIEW_AXES:
            raise ValueError("component %s: unknown view %r" % (cid, v))

    raw_views = c.get("views")
    if raw_views is None:
        v0 = c.get("view")
        views = [v0] if v0 else []
    elif isinstance(raw_views, str):
        views = [raw_views]
    else:
        views = list(raw_views)
    for v in by_view:
        if v not in views:
            views.append(v)

    params = c.get("params", [])
    if isinstance(params, dict):
        params = [{"name": k, "value": v} for k, v in params.items()]
    params = [dict(p) for p in params]

    c["_views"] = views
    c["_bbox"] = by_view
    c["_params"] = params
    return c


def normalize_table(doc):
    """元件表文件（v1 或 v2）→ (components, meta)。"""
    if isinstance(doc, (list, tuple)):
        raw_list, meta = list(doc), {}
    else:
        schema = doc.get("schema")
        if schema and schema not in (SCHEMA, SCHEMA_V1):
            raise ValueError("components: unexpected schema %r (want %r)" % (schema, SCHEMA))
        raw_list = list(doc.get("components", []))
        meta = {k: v for k, v in doc.items() if k != "components"}
    comps = [normalize_component(r) for r in raw_list]
    ids = [c["id"] for c in comps]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError("duplicate component ids: %s" % dup)
    return comps, meta


def load_table(path):
    with open(path, "r", encoding="utf-8") as fh:
        return normalize_table(json.load(fh))


def public_component(c):
    """剝掉內部 `_` 欄位，輸出成 v2 形狀。"""
    out = {k: v for k, v in c.items() if not k.startswith("_")}
    out["views"] = list(c["_views"])
    out["bbox_mm"] = {k: [_r(x) for x in v] for k, v in c["_bbox"].items()}
    if c["_params"]:
        out["params"] = c["_params"]
    out.pop("view", None)
    return out


def save_table(comps, path, meta=None):
    doc = dict(meta or {})
    doc["schema"] = SCHEMA
    doc["components"] = [public_component(c) for c in comps]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    return path


def to_blueprint_v1(comps, meta=None):
    """輸出 blueprint_lib 吃得下的 v1 文件（每個視圖一筆）。

    blueprint_lib 的元件框是單視圖的；本模組的元件可跨多視圖，
    因此這裡把多視圖元件攤開成 `<id>@<view>`，其餘欄位原樣帶過。
    """
    flat = []
    for c in comps:
        for v in c["_views"]:
            b = c["_bbox"].get(v)
            if not b:
                continue
            item = {k: v2 for k, v2 in c.items() if not k.startswith("_")}
            item["id"] = "%s@%s" % (c["id"], v) if len(c["_views"]) > 1 else c["id"]
            item["view"] = v
            item["bbox_mm"] = [_r(x) for x in b]
            item.pop("views", None)
            flat.append(item)
    doc = dict(meta or {})
    doc["schema"] = SCHEMA_V1
    doc["components"] = flat
    return doc


# --------------------------------------------------------------------------
# 參數來源
# --------------------------------------------------------------------------
def flatten_annotated(calib):
    """calib['annotated_dims_mm'] 攤平成 {'front.body_w': 77.98, ...}。"""
    out = {}

    def walk(prefix, node):
        if isinstance(node, dict):
            for k, v in node.items():
                walk("%s.%s" % (prefix, k) if prefix else str(k), v)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            out[prefix] = float(node)

    walk("", calib.get("annotated_dims_mm", {}) or {})
    return out


def param_conflicts(param):
    """回傳這個參數「尚未裁定」的候選值（有 `conflicts` 但沒有 `resolved_by`）。

    同一個尺寸出現兩個互斥來源（圖面標註 vs 掃描量測、兩張圖給不同數字）時，
    三層權威（§16.9）只能決定「優先序」，不能取代「有人真的裁定過」這件事——
    沒有 `resolved_by` 就等於還沒裁定，此時往下建模＝靜默挑值，同一個數字會在
    輪次之間反覆翻盤，而且每次翻盤都會被下游當成新事實。
    """
    conf = param.get("conflicts") or []
    if not conf:
        return []
    if str(param.get("resolved_by", "") or "").strip():
        return []
    out = []
    for x in conf:
        out.append(dict(x) if isinstance(x, dict)
                   else {"value": x, "source": "?", "note": ""})
    return out


def verify_param(param, flat_ann, tol_mm=DEFAULT_ANN_TOL_MM):
    """檢查單一參數的 source 宣告是否成立。

    回傳 dict：{name, value, declared, status, matched, note}
      status:
        confirmed        value 與圖面標註相符（matched 列出所有同值的標註項）
        unmatched        source 說 annotation，但標註表找不到同值 → 虛報，必須修正
        declared        非 annotation（measured/derived/estimated），無自動可驗對象
        no-value         沒有 value，等於還沒填
    """
    name = str(param.get("name", "?"))
    declared = str(param.get("source", "") or "").strip().lower()
    val = param.get("value", None)
    rec = {"name": name, "value": val, "declared": declared,
           "status": "declared", "matched": [], "note": param.get("note", "")}

    if val is None:
        rec["status"] = "no-value"
        return rec

    hits = sorted(k for k, v in flat_ann.items() if abs(v - float(val)) <= tol_mm)
    if declared.startswith("annotation"):
        if hits:
            rec["status"] = "confirmed"
            rec["matched"] = hits
        else:
            rec["status"] = "unmatched"
    else:
        rec["status"] = "declared"
        rec["matched"] = hits  # 有對到也記下來（方便升級成 annotation）
    return rec


def audit_params(comps, calib, tol_mm=DEFAULT_ANN_TOL_MM):
    """CP1-B：逐元件檢查參數可查性。回傳 {'items': [...], 'problems': [...], 'stats': {...}}"""
    flat = flatten_annotated(calib)
    views = calib.get("views", {}) or {}
    items, problems = [], []
    stats = {"confirmed": 0, "unmatched": 0, "declared": 0, "no-value": 0,
             "conflict": 0, "components_without_params": 0}

    for c in comps:
        rec = {"id": c["id"], "name": c.get("name", ""), "params": [],
               "views_with_contour": [v for v in c["_views"] if (views.get(v) or {}).get("contour_mm")]}
        if not c["_params"]:
            stats["components_without_params"] += 1
            rec["verdict"] = "no-params-declared"
            problems.append("%s %s：沒有列出任何參數（無法判定可查性；"
                            "至少列出尺寸/位置參數並標 source）" % (c["id"], c.get("name", "")))
            items.append(rec)
            continue

        worst = "confirmed"
        for p in c["_params"]:
            pr = verify_param(p, flat, tol_mm)
            stats[pr["status"]] = stats.get(pr["status"], 0) + 1
            conf = param_conflicts(p)
            pr["conflicts_open"] = conf
            if conf:
                stats["conflict"] += 1
                worst = "conflict"
                cand = "、".join("%s=%s" % (x.get("source", "?"), x.get("value"))
                                for x in conf)
                problems.append("%s %s：參數 %s 尚未裁定（目前採 %.4g，其他候選 %s）"
                                "——補 resolved_by + resolution_note 寫明由誰依什麼裁定，"
                                "或先問使用者，不要靜默挑值"
                                % (c["id"], c.get("name", ""), pr["name"],
                                   float(pr["value"]), cand))
            if pr["status"] == "unmatched":
                if worst != "conflict":
                    worst = "unmatched"
                problems.append("%s %s：參數 %s=%.4g 標為 annotation，但圖面標註找不到同值 "
                                "→ 虛報，改成 measured/estimated 或修正數值"
                                % (c["id"], c.get("name", ""), pr["name"], float(pr["value"])))
            elif pr["status"] == "no-value" and worst == "confirmed":
                worst = "needs-value"
            elif pr["status"] == "declared" and worst == "confirmed":
                worst = "needs-review"
            rec["params"].append(pr)

        rec["verdict"] = worst
        items.append(rec)

    stats["annotation_coverage"] = _r(
        stats["confirmed"] / float(max(1, stats["confirmed"] + stats["unmatched"] +
                                       stats["declared"] + stats["no-value"])), 4)
    return {"items": items, "problems": problems, "stats": stats,
            "annotated_keys": sorted(flat)}


# --------------------------------------------------------------------------
# CP1-A0：元件表拆解深度（§11 Stage A item 3）——不需要 calib
# --------------------------------------------------------------------------
def audit_depth(comps, min_level=MIN_EXPECTED_COMPONENT_LEVEL):
    """拆解深度審計（§11 Stage A item 3 / §16.9.5 規則 7）。**不讀 calib、不碰三視圖**。

    與 `audit_coverage()` 分家的理由：深度是「這個主體有沒有被認真拆解過」的性質，
    跟「有沒有參考圖可量」無關。三視圖流程被 §16.9.0 明文排除原創設計類，於是唯一會查
    深度的檢查過去只服務得到 B 類以外的任務——原創主體永遠不會被查。這支獨立出來之後，
    兩條路線共用同一份真相源：三視圖走 `audit`（預設門檻 4），原創設計走 `depth`
    子命令（預設門檻 `MIN_EXPECTED_COMPONENT_LEVEL_ORIGINAL`）。

    回傳 `{'problems': [...], 'stats': {...}}`；`stats` 含 `component_count`／
    `level_histogram`／`max_level`／`depth_exempt`／`depth_exempt_ignored`。
    意義上確實拆不動的主體（例：本身就是單一鈑金件、沒有內部構件）在**最深的那個
    元件**上寫 `depth_exempt` 說明理由即可放行——寫在淺層元件上不算（否則隨便哪個
    淺層元件都能一句話放行整表，閘門就形同不存在）；不要為了湊層級硬造不存在的子零件。
    """
    hist = {}
    for c in comps:
        lv = c.get("level")
        if isinstance(lv, int) and not isinstance(lv, bool):
            hist[lv] = hist.get(lv, 0) + 1
    max_level = max(hist) if hist else 0
    # 豁免只認「最深那一層」的元件——任何一個淺層元件寫了 depth_exempt 就讓整表放行，
    # 等於閘門形同不存在（淺層元件幾乎都很好寫理由）。要豁免就在真的拆不下去的最深
    # 分支上寫；寫在淺層的記進 depth_exempt_ignored、不計入放行。
    def _has_exempt(c):
        return bool(str(c.get("depth_exempt", "") or "").strip())

    def _lv(c):
        v = c.get("level")
        return v if isinstance(v, int) and not isinstance(v, bool) else None

    exempt = [c["id"] for c in comps if _lv(c) == max_level and max_level and _has_exempt(c)]
    exempt_ignored = [c["id"] for c in comps if _has_exempt(c) and c["id"] not in exempt]
    problems = []
    if max_level < min_level and not exempt:
        problems.append("元件表最深只到 LEVEL %d（< %d）：拆解深度不足——"
                        "元件表拆到多細，直接決定 CP2 能逐件校正到多細；"
                        "把大元件底下的小元件（按鈕/墊片/螺絲/密封件…）遞迴拆出來，"
                        "或在意義上確實拆不動的元件上寫 depth_exempt 說明理由"
                        % (max_level, min_level))
    stats = {
        "component_count": len(comps),
        "level_histogram": {str(k): hist[k] for k in sorted(hist)},
        "max_level": max_level,
        "min_level": min_level,
        "depth_exempt": exempt,
        "depth_exempt_ignored": exempt_ignored,
    }
    return {"problems": problems, "stats": stats}


# --------------------------------------------------------------------------
# CP1-A：覆蓋／盲區
# --------------------------------------------------------------------------
def audit_coverage(comps, calib, tol_mm=DEFAULT_CONTAIN_TOL_MM):
    """CP1-A：視圖覆蓋與框界檢查。回傳 {'views': {...}, 'problems': [...], 'stats': {...}}"""
    views = calib.get("views", {}) or {}
    problems = []
    per_view = {v: {"components": [], "count": 0} for v in views}

    for c in comps:
        if not c["_views"]:
            problems.append("%s %s：沒有宣告任何視圖" % (c["id"], c.get("name", "")))
            continue
        for v in c["_views"]:
            if v not in views:
                problems.append("%s：宣告視圖 %r 不在 calib 中（可用：%s）"
                                % (c["id"], v, sorted(views)))
                continue
            per_view[v]["count"] += 1
            per_view[v]["components"].append(c["id"])
            b = c["_bbox"].get(v)
            if not b:
                problems.append("%s：視圖 %s 沒有 bbox_mm" % (c["id"], v))
                continue
            cb = contour_bbox((views.get(v) or {}).get("contour_mm"))
            if not cb:
                continue
            over = max(cb[0] - b[0], b[2] - cb[2], cb[1] - b[1], b[3] - cb[3])
            if over > tol_mm:
                # 刻意凸出的構成元件（按鍵、相機平台、鏡頭凸台）本來就會超出機身輪廓
                # ——標 exclude_from_containment 者仍納入覆蓋統計（它確實屬於這個視圖），
                # 但不列為違規。跟 blueprint_lib.assert_component_within_contour 同一語意。
                if c.get("exclude_from_containment"):
                    per_view[v].setdefault("excluded_over", []).append(
                        {"id": c["id"], "over_mm": _r(over)})
                    continue
                problems.append("%s %s：視圖 %s 的框超出量測輪廓 %.2fmm "
                                "（框 %s，輪廓 %s）"
                                % (c["id"], c.get("name", ""), v, over,
                                   [round(x, 2) for x in b], [round(x, 2) for x in cb]))

    blind = sorted(v for v, d in per_view.items() if d["count"] == 0)
    for v in blind:
        problems.append("視圖 %s 沒有任何元件指派（盲區）——若該視圖確實沒有可拆元件，"
                        "請在元件表 meta 的 note 說明，不要讓它靜默留白" % v)

    # 元件表深度（§11 LEVEL 1–6 的精神）——邏輯住在 audit_depth()，與 `depth` 子命令
    # 共用同一份真相源；這裡只是把它接進 CP1-A 的彙總（三視圖流程用預設門檻 4）。
    depth = audit_depth(comps, min_level=MIN_EXPECTED_COMPONENT_LEVEL)
    problems.extend(depth["problems"])

    stats = {
        "component_count": len(comps),
        "views_total": len(views),
        "views_covered": len(views) - len(blind),
        "blind_views": blind,
        "per_view_counts": {v: per_view[v]["count"] for v in sorted(per_view)},
        **depth["stats"],
    }
    return {"views": per_view, "problems": problems, "stats": stats}


# --------------------------------------------------------------------------
# CP1-C：外觀規格
# --------------------------------------------------------------------------
def audit_appearance(comps):
    """CP1-C：外觀規格有沒有被寫下來、有沒有依據。

    幾何對賬管「形狀對不對」，管不到「看起來對不對」——顏色、霧面/鏡面、該貼合的
    平面是不是被做成立體，過去全靠渲染後目視，改壞了沒有東西擋得住。規則：每個
    元件要嘛宣告 `appearance`（含 `evidence`），要嘛用 `appearance_skipped` 明講
    不驗外觀的理由（內部不可見件、void 開口…）——「想過但決定不驗」與「根本沒想到」
    是兩件事，後者才是這條要擋的。
    """
    items, problems = [], []
    stats = {"declared": 0, "skipped": 0, "missing": 0, "no_evidence": 0,
             "material_patterns": 0, "flat_limits": 0}
    for c in comps:
        app = c.get("appearance") or {}
        skipped = str(c.get("appearance_skipped", "") or "").strip()
        rec = {"id": c["id"], "name": c.get("name", ""),
               "material": app.get("material"), "flat_axis": app.get("flat_axis"),
               "evidence": app.get("evidence")}
        if skipped:
            stats["skipped"] += 1
            rec["verdict"] = "skipped"
            rec["note"] = skipped
            items.append(rec)
            continue
        if not app:
            stats["missing"] += 1
            rec["verdict"] = "missing"
            problems.append("%s %s：沒有宣告外觀（appearance）——列出期望的材質樣式、"
                            "霧面/鏡面、貼合平面厚度，並在 evidence 寫依據；"
                            "確實不驗外觀請改用 appearance_skipped 說明理由"
                            % (c["id"], c.get("name", "")))
            items.append(rec)
            continue
        ev = str(app.get("evidence", "") or "").strip()
        if len(ev) < APPEARANCE_MIN_EVIDENCE_CHARS:
            stats["no_evidence"] += 1
            rec["verdict"] = "no-evidence"
            problems.append("%s %s：appearance 缺 evidence——外觀判斷也要能回答"
                            "「憑什麼這樣認為」（標註／實機照／參考圖／材質庫）"
                            % (c["id"], c.get("name", "")))
        else:
            rec["verdict"] = "ok"
        if app.get("material"):
            stats["material_patterns"] += 1
        fa, me = app.get("flat_axis"), app.get("max_extent_mm")
        if bool(fa) != isinstance(me, (int, float)):
            problems.append("%s %s：flat_axis 與 max_extent_mm 必須成對出現"
                            "（只給一個等於沒有設限）" % (c["id"], c.get("name", "")))
        elif fa and str(fa).lower() not in AXIS_INDEX:
            problems.append("%s %s：flat_axis=%r 不是 x/y/z"
                            % (c["id"], c.get("name", ""), fa))
        elif fa:
            stats["flat_limits"] += 1
        items.append(rec)
    stats["declared"] = len(comps) - stats["missing"]
    return {"items": items, "problems": problems, "stats": stats}


# --------------------------------------------------------------------------
# CP2：規劃 vs 實測
# --------------------------------------------------------------------------
def _suggest_size_fix(c, axis_label, planned, measured):
    """給出尺寸修正建議：優先對應同名的 params 項。"""
    cand = [p for p in c["_params"] if isinstance(p.get("value"), (int, float))]
    for p in cand:
        nm = str(p.get("name", "")).lower()
        if axis_label in nm or ("size" in nm) or ("length" in nm) or ("thickness" in nm):
            return {"param": p["name"], "from": float(p["value"]), "to": _r(measured),
                    "note": "尺寸偏差 %.3fmm" % (measured - planned)}
    return {"param": None, "to": _r(measured),
            "note": "元件表未列對應尺寸參數，建議新增（例如 %s_mm）" % axis_label}


def compare(comps, measured, calib=None, pos_tol_mm=DEFAULT_POS_TOL_MM,
            size_tol_mm=DEFAULT_SIZE_TOL_MM, ang_tol_deg=DEFAULT_ANG_TOL_DEG):
    """CP2：元件表的規劃值 vs component_measure 的實測值。

    measured：component_measure 輸出（schema "components_measured/1"），
              每個項目需有 aabb_mm（世界 mm），選配 axes（PCA 主軸，由長到短）。
    回傳 {'items': [...], 'problems': [...], 'stats': {...}}
    """
    if isinstance(measured, str):
        with open(measured, "r", encoding="utf-8") as fh:
            measured = json.load(fh)
    mlist = measured.get("components", measured) if isinstance(measured, dict) else measured
    mby = {m.get("id"): m for m in mlist}

    items, problems = [], []
    stats = {"compared": 0, "missing_in_model": 0, "pos_fail": 0, "size_fail": 0,
             "ang_fail": 0, "not_in_table": 0, "void_ok": 0,
             "material_fail": 0, "extent_fail": 0}

    for c in comps:
        m = mby.get(c["id"])
        rec = {"id": c["id"], "name": c.get("name", ""), "views": {}, "axis": None}

        # void 元件（開口）：沒有自己的 mesh，數值上無從比對——只確認 host 存在
        # （host 在＝這個面確實建出來了、開口是在實體上挖的）。刻意與 missing 分開：
        # 「量不到」跟「沒建」是兩件事，混為一談會讓開口類元件永遠卡在缺件清單裡。
        if m is not None and m.get("void"):
            rec["status"] = "void-ok" if m.get("host_present") else "void-host-missing"
            rec["host"] = m.get("host")
            if not m.get("host_present"):
                stats["missing_in_model"] += 1
                problems.append("%s %s：開口元件的 host「%s」在模型裡不存在——"
                                "開口無從挖起，確認 host 物件名或補建"
                                % (c["id"], c.get("name", ""), m.get("host")))
            else:
                stats["void_ok"] += 1
            items.append(rec)
            continue

        if m is None or not m.get("aabb_mm"):
            stats["missing_in_model"] += 1
            rec["status"] = "missing-in-model"
            problems.append("%s %s：模型裡找不到對應物件（objects=%s）——"
                            "補建，或修正元件表的 objects 樣式"
                            % (c["id"], c.get("name", ""), c.get("objects", [])))
            items.append(rec)
            continue

        aabb = m["aabb_mm"]
        worst = "ok"
        for v in c["_views"]:
            pb = c["_bbox"].get(v)
            if not pb:
                continue
            mb = aabb_to_view_bbox(aabb, v)
            pc, mc = bbox_center(pb), bbox_center(mb)
            ps, ms = bbox_size(pb), bbox_size(mb)
            du, dv = _r(mc[0] - pc[0]), _r(mc[1] - pc[1])
            dw, dh = _r(ms[0] - ps[0]), _r(ms[1] - ps[1])
            edge = {"u0": _r(mb[0] - pb[0]), "v0": _r(mb[1] - pb[1]),
                    "u1": _r(mb[2] - pb[2]), "v1": _r(mb[3] - pb[3])}
            pos_bad = max(abs(du), abs(dv)) > pos_tol_mm
            size_bad = max(abs(dw), abs(dh)) > size_tol_mm
            if pos_bad or size_bad:
                worst = "fail"
            rec["views"][v] = {
                "planned": [_r(x) for x in pb], "measured": [_r(x) for x in mb],
                "d_center": [du, dv], "d_size": [dw, dh], "d_edges": edge,
                "pos_ok": not pos_bad, "size_ok": not size_bad,
                "world_shift_mm": view_delta_to_world(v, du, dv),
            }
            if size_bad:
                stats["size_fail"] += 1
                for ax_i, (pl, me) in (("u", (ps[0], ms[0])), ("v", (ps[1], ms[1]))):
                    if abs(me - pl) > size_tol_mm:
                        rec.setdefault("suggest", []).append(
                            dict(_suggest_size_fix(c, ax_i, pl, me), view=v, axis=ax_i))
            if pos_bad:
                stats["pos_fail"] += 1

        # 外觀：材質樣式與貼合厚度（appearance 有宣告才檢查，向後相容）
        app = c.get("appearance") or {}
        mat_pat = app.get("material")
        if mat_pat and m.get("materials") is not None:
            names = [str(x) for x in (m.get("materials") or [])]
            hit = any(fnmatch.fnmatch(nm.lower(), str(mat_pat).lower()) for nm in names)
            rec["material"] = {"expected": str(mat_pat), "measured": names, "ok": bool(hit)}
            if not hit:
                stats["material_fail"] += 1
                worst = "fail"
                problems.append("%s %s：材質不符——表列 %s，模型實際 %s"
                                % (c["id"], c.get("name", ""), mat_pat,
                                   names or "(沒有任何材質槽)"))
        fa, me = app.get("flat_axis"), app.get("max_extent_mm")
        idx = AXIS_INDEX.get(str(fa).lower()) if fa else None
        if idx is not None and isinstance(me, (int, float)):
            ext = _r(aabb[idx + 3] - aabb[idx])
            rec["extent"] = {"axis": str(fa).lower(), "limit_mm": float(me),
                             "measured_mm": ext, "ok": bool(ext <= float(me))}
            if ext > float(me):
                stats["extent_fail"] += 1
                worst = "fail"
                problems.append("%s %s：沿 %s 軸厚度 %.3fmm 超過上限 %.3fmm——"
                                "該貼合平面的做成立體了，檢查 proud/offset 與幾何"
                                % (c["id"], c.get("name", ""), str(fa).upper(),
                                   ext, float(me)))

        # 方向
        if c.get("axis") and m.get("axes"):
            a = angle_between_axes(c["axis"], m["axes"][0])
            rec["axis"] = {"planned": list(c["axis"]), "measured": [_r(x, 4) for x in m["axes"][0]],
                           "delta_deg": a, "ok": a <= ang_tol_deg}
            if a > ang_tol_deg:
                stats["ang_fail"] += 1
                worst = "fail"
                problems.append("%s %s：長軸方向偏差 %.2f°（> %.2f°）——"
                                "檢查建構時該元件的旋轉/朝向"
                                % (c["id"], c.get("name", ""), a, ang_tol_deg))

        rec["status"] = worst
        if worst == "fail":
            for v, d in rec["views"].items():
                if not (d["pos_ok"] and d["size_ok"]):
                    problems.append(
                        "%s %s @%s：中心偏移 (%.3f, %.3f)mm、尺寸差 (%.3f, %.3f)mm"
                        "（位置%s 尺寸%s）"
                        % (c["id"], c.get("name", ""), v,
                           d["d_center"][0], d["d_center"][1],
                           d["d_size"][0], d["d_size"][1],
                           "OK" if d["pos_ok"] else "NG", "OK" if d["size_ok"] else "NG"))
        stats["compared"] += 1
        items.append(rec)

    for mid, m in mby.items():
        if mid not in {c["id"] for c in comps}:
            stats["not_in_table"] += 1
            problems.append("模型量到 %s（物件 %s），但元件表沒有這一項——"
                            "確認是否漏件，或這是輔助/環境物件"
                            % (mid, m.get("objects", [])))

    return {"items": items, "problems": problems, "stats": stats,
            "measured_source": measured.get("blend") if isinstance(measured, dict) else None}


# --------------------------------------------------------------------------
# 偏差對照表（CP2 報告）
# --------------------------------------------------------------------------

def _fmt_span(bbox):
    """[u0,v0,u1,v1] → '77.97 x 163.16'（寬 x 高）"""
    w, h = bbox_size(bbox)
    return "%.2f x %.2f" % (w, h)


def _fmt_off(vals):
    """[du,dv] → '+0.25, -0.10'"""
    return "%+.2f, %+.2f" % (float(vals[0]), float(vals[1]))


def _item_worst_mm(item):
    """該元件所有視圖的最大絕對偏差（mm）——只用來排序，不含方向項。"""
    worst = 0.0
    for d in item.get("views", {}).values():
        worst = max(worst, abs(d["d_center"][0]), abs(d["d_center"][1]),
                    abs(d["d_size"][0]), abs(d["d_size"][1]))
    return worst


def render_compare(res, subject=None, title=None, tolerances=None):
    """把 compare() 的結果寫成人可讀的 Markdown 偏差對照表。

    逐元件逐視圖列出規劃尺寸、實測尺寸、中心偏移與尺寸差。開口類元件（void）
    另立一表——它們沒有可量的 AABB，只驗 host 存在，混進尺寸表只會製造假偏差。
    """
    st = res.get("stats", {}) or {}
    L = ["# %s" % (title or "元件校正（CP2）— 規劃 vs 實測"), ""]
    if subject:
        L.append("- 主體：%s" % subject)
    if res.get("measured_source"):
        L.append("- 實測來源：`%s`" % res["measured_source"])
    L.append("- 彙總：比對 %d、缺件 %d、位置 NG %d、尺寸 NG %d、方向 NG %d、開口驗證 %d"
             % (st.get("compared", 0), st.get("missing_in_model", 0),
                st.get("pos_fail", 0), st.get("size_fail", 0),
                st.get("ang_fail", 0), st.get("void_ok", 0)))
    if tolerances:
        L.append("- 容差：" + "、".join("%s %s" % (k, v)
                                    for k, v in sorted(tolerances.items())))
    L.append("")

    sized, voids, missing, axes, appear = [], [], [], [], []
    for it in res.get("items", []):
        status = it.get("status", "")
        if status.startswith("void"):
            voids.append(it)
        elif status == "missing-in-model":
            missing.append(it)
        elif it.get("views"):
            sized.append(it)
        if it.get("axis"):
            axes.append(it)
        if it.get("material") or it.get("extent"):
            appear.append(it)

    L.append("## 偏差對照表")
    L.append("")
    L.append("| 元件 | 名稱 | 視圖 | 規劃 (寬 x 高) | 實測 (寬 x 高) | Δ中心 (u, v) | Δ尺寸 (du, dv) | 判定 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for it in sized:
        for v, d in it["views"].items():
            ok = d["pos_ok"] and d["size_ok"]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (it["id"], it.get("name", ""), v,
                        _fmt_span(d["planned"]), _fmt_span(d["measured"]),
                        _fmt_off(d["d_center"]), _fmt_off(d["d_size"]),
                        "OK" if ok else "**NG**"))
    L.append("")

    ranked = sorted(((_item_worst_mm(it), it) for it in sized),
                    key=lambda p: p[0], reverse=True)
    ranked = [p for p in ranked if p[0] > 0]
    if ranked:
        L.append("### 最大偏差（前 5）")
        L.append("")
        for mm, it in ranked[:5]:
            views = ", ".join(it["views"].keys())
            L.append("- %s %s（%s）：最大 %.2fmm" % (it["id"], it.get("name", ""), views, mm))
        L.append("")

    if axes:
        L.append("### 長軸方向")
        L.append("")
        L.append("| 元件 | 名稱 | 規劃軸 | 實測軸 | 偏差 | 判定 |")
        L.append("|---|---|---|---|---|---|")
        for it in axes:
            a = it["axis"]
            L.append("| %s | %s | %s | %s | %.2f° | %s |"
                     % (it["id"], it.get("name", ""),
                        "(" + ", ".join("%.2f" % x for x in a["planned"]) + ")",
                        "(" + ", ".join("%.2f" % x for x in a["measured"]) + ")",
                        a["delta_deg"], "OK" if a["ok"] else "**NG**"))
        L.append("")

    if appear:
        L.append("### 外觀（材質／貼合厚度）")
        L.append("")
        L.append("| 元件 | 名稱 | 期望材質 | 模型實際材質 | 貼合軸 | 上限 (mm) | 實測 (mm) | 判定 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for it in appear:
            mt = it.get("material") or {}
            ex = it.get("extent") or {}
            ok = (mt.get("ok", True) is not False) and (ex.get("ok", True) is not False)
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (it["id"], it.get("name", ""),
                        mt.get("expected", "—"),
                        ", ".join(mt.get("measured", [])) if mt.get("measured") else "—",
                        (ex.get("axis", "") or "—").upper(),
                        "%.3f" % ex["limit_mm"] if "limit_mm" in ex else "—",
                        "%.3f" % ex["measured_mm"] if "measured_mm" in ex else "—",
                        "OK" if ok else "**NG**"))
        L.append("")

    if voids:
        L.append("### 開口類元件（void，不量 AABB）")
        L.append("")
        L.append("| 元件 | 名稱 | host | 判定 |")
        L.append("|---|---|---|---|")
        for it in voids:
            L.append("| %s | %s | %s | %s |"
                     % (it["id"], it.get("name", ""), it.get("host", ""),
                        "host 存在" if it["status"] == "void-ok" else "**host 不存在**"))
        L.append("")

    if missing:
        L.append("### 模型裡找不到")
        L.append("")
        for it in missing:
            L.append("- %s %s" % (it["id"], it.get("name", "")))
        L.append("")

    sugg = [it for it in res.get("items", []) if it.get("suggest")]
    if sugg:
        L.append("### 建議修正")
        L.append("")
        for it in sugg:
            for sf in it["suggest"]:
                L.append("- %s %s：%s" % (it["id"], sf.get("view", ""), sf.get("note", "")))
        L.append("")

    L.append("## 問題")
    L.append("")
    for p in res.get("problems", []):
        L.append("- %s" % p)
    if not res.get("problems"):
        L.append("- (無)")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# 版本史與凍結（CP1-D）
# --------------------------------------------------------------------------
def _brief(v, max_len=160):
    """把任意值縮成一行，供 Markdown 變更表使用。"""
    try:
        s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        s = str(v)
    return s if len(s) <= max_len else s[:max_len] + "…"


def _component_signature(c):
    """元件在 diff 裡的可比較欄位（只收會影響模型的東西）。"""
    return {
        "name": c.get("name", ""),
        "level": c.get("level"),
        "views": sorted(c["_views"]),
        "bbox_mm": {v: [_r(x) for x in b] for v, b in sorted(c["_bbox"].items())},
        "params": {str(p.get("name")): p.get("value") for p in c["_params"]},
        "objects": sorted(str(x) for x in (c.get("objects") or [])),
        "appearance": c.get("appearance") or {},
        "exclude_from_containment": bool(c.get("exclude_from_containment")),
        "void": bool(c.get("void")),
    }


def _matches_scope(cid, scope):
    """cid 是否落在本輪允許修改的範圍內（scope=None 表不檢查）。"""
    if scope is None:
        return True
    for pat in scope:
        if pat == cid or fnmatch.fnmatchcase(cid, pat):
            return True
    return False


def diff_tables(old_doc, new_doc, note_field="change_note", scope=None):
    """兩個元件表之間的逐項變更 + 已凍結元件被改動的違規（CP1-D）。

    這是「真相源漂移」的煞車：同一項數值在不同版本之間可能來回翻好幾次，沒有 diff
    就沒有東西記錄「這輪動了什麼、為什麼」。`locked` 的元件被改動＝違規（problems，
    呼叫端應 exit 1），必須先解鎖並寫 `change_note` 說明；改了卻沒寫說明的列在
    `warnings`（提醒，不擋）。

    `scope`：本輪允許修改的元件 id 清單（支援 fnmatch 樣式）。給了 scope 時，落在
    scope 外的任何新增／刪除／變更都是問題——「圖上看得出來的全部要改」如果在同一輪
    裡同時動到好幾個元件群，已驗證區就會被反覆打掉；拆成「一輪鎖一個元件群」，每輪
    的 diff 就只該出現那一群的欄位變動。
    """
    old_comps, _ = normalize_table(old_doc)
    new_comps, _ = normalize_table(new_doc)
    ob = {c["id"]: c for c in old_comps}
    nb = {c["id"]: c for c in new_comps}

    changes, problems, warnings = [], [], []
    stats = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0,
             "locked_changed": 0, "note_missing": 0, "out_of_scope": 0,
             "scoped": scope is not None,
             "old_count": len(old_comps), "new_count": len(new_comps)}

    def _scope_guard(cid, name, what):
        if _matches_scope(cid, scope):
            return
        stats["out_of_scope"] += 1
        problems.append("%s %s：落在本輪修改範圍（scope）外卻被%s——"
                        "一輪只鎖一個元件群，其他群要動請另開一輪"
                        % (cid, name, what))

    for cid in sorted(set(ob) | set(nb)):
        if cid not in ob:
            c = nb[cid]
            stats["added"] += 1
            _scope_guard(cid, c.get("name", ""), "新增")
            changes.append({"id": cid, "name": c.get("name", ""), "status": "added",
                            "locked": bool(c.get("locked")), "fields": []})
            continue
        if cid not in nb:
            c = ob[cid]
            stats["removed"] += 1
            _scope_guard(cid, c.get("name", ""), "刪除")
            changes.append({"id": cid, "name": c.get("name", ""), "status": "removed",
                            "locked": bool(c.get("locked")), "fields": []})
            if c.get("locked"):
                stats["locked_changed"] += 1
                problems.append("%s %s：已凍結的元件被刪除（原 verified_at=%s）"
                                "——要拿掉請先解鎖並在交付說明寫理由"
                                % (cid, c.get("name", ""), c.get("verified_at", "?")))
            continue

        so, sn = _component_signature(ob[cid]), _component_signature(nb[cid])
        fields = []
        for k in sorted(set(so) | set(sn)):
            a, b = so.get(k), sn.get(k)
            if a != b:
                fields.append({"field": k, "old": a, "new": b})

        locked = bool(nb[cid].get("locked"))
        rec = {"id": cid, "name": sn.get("name", ""),
               "status": "changed" if fields else "unchanged",
               "locked": locked, "fields": fields}
        if not fields:
            stats["unchanged"] += 1
            changes.append(rec)
            continue

        stats["changed"] += 1
        note = str(nb[cid].get(note_field) or "").strip()
        rec["note"] = note
        touched = ", ".join(f["field"] for f in fields)
        _scope_guard(cid, sn.get("name", ""), "改動（%s）" % touched)
        if not note:
            stats["note_missing"] += 1
            warnings.append("%s %s：這輪改了 %s，但沒有 %s 說明理由"
                            % (cid, sn.get("name", ""), touched, note_field))
        if locked:
            stats["locked_changed"] += 1
            problems.append("%s %s：已凍結（locked，verified_at=%s）卻被改動（%s）"
                            "——先解鎖並寫 %s，或改回原值"
                            % (cid, sn.get("name", ""), nb[cid].get("verified_at", "?"),
                               touched, note_field))
        changes.append(rec)

    return {"changes": changes, "problems": problems, "warnings": warnings,
            "scope": (None if scope is None else sorted(scope)), "stats": stats}


def render_diff(res, old_label="old", new_label="new", title=None):
    """diff_tables() 結果 → 人可讀的變更紀錄（Markdown）。"""
    st = res.get("stats", {}) or {}
    L = ["# %s" % (title or "元件表變更紀錄（版本史）"), ""]
    L.append("- 比較：`%s` → `%s`" % (old_label, new_label))
    L.append("- 彙總：新增 %d、刪除 %d、改動 %d、未變 %d；已凍結被改動 %d、缺變更說明 %d"
             % (st.get("added", 0), st.get("removed", 0), st.get("changed", 0),
                st.get("unchanged", 0), st.get("locked_changed", 0),
                st.get("note_missing", 0)))
    if st.get("scoped"):
        L.append("- 本輪修改範圍（scope）：%s；範圍外被動到 %d 件"
                 % (", ".join(res.get("scope") or []) or "(空)",
                    st.get("out_of_scope", 0)))
    L.append("")

    touched = [c for c in res.get("changes", []) if c["status"] != "unchanged"]
    L.append("## 逐項變更")
    L.append("")
    if not touched:
        L.append("- (無變更)")
        L.append("")
    for c in touched:
        mark = {"added": "新增", "removed": "刪除", "changed": "改動"}[c["status"]]
        L.append("### %s %s — %s%s" % (c["id"], c.get("name", ""), mark,
                                       "　[LOCKED]" if c.get("locked") else ""))
        for f in c.get("fields", []):
            L.append("- `%s`：`%s` → `%s`"
                     % (f["field"], _brief(f["old"]), _brief(f["new"])))
        if c.get("note"):
            L.append("- 說明：%s" % c["note"])
        L.append("")

    if res.get("warnings"):
        L.append("## 提醒（不擋）")
        L.append("")
        for w in res["warnings"]:
            L.append("- %s" % w)
        L.append("")

    L.append("## 違規")
    L.append("")
    for p in res.get("problems", []):
        L.append("- %s" % p)
    if not res.get("problems"):
        L.append("- (無)")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# 視覺核對清單
# --------------------------------------------------------------------------
def render_checklist(comps, calib, audit=None, params=None, subject=None, title=None):
    """產出給視覺逐項核對的 Markdown。"""
    subject = subject or (calib.get("subject", {}) or {}).get("name") or "(未命名)"
    audit = audit or audit_coverage(comps, calib)
    params = params or audit_params(comps, calib)
    pby = {it["id"]: it for it in params["items"]}
    ann = flatten_annotated(calib)

    L = []
    L.append("# 元件核對清單 — %s" % (title or subject))
    L.append("")
    L.append("> 用法：拿這份清單搭配原圖，用 `read_image_native`（或你的 agent 平台上等價的視覺輸入工具）逐項核對。")
    L.append("> 每項回答三件事：(1) 圖上看得見嗎？(2) 位置／比例對嗎？(3) 有標註數字嗎？")
    L.append("> 核對結果回填「圖上確認」，再把 `source`／`note` 更新回元件表，重跑 audit。")
    L.append("")
    L.append("## 視圖覆蓋")
    L.append("")
    L.append("| 視圖 | 元件數 | 狀態 |")
    L.append("|---|---|---|")
    for v, d in sorted(audit["views"].items()):
        L.append("| %s | %d | %s |" % (v, d["count"], "OK" if d["count"] else "**盲區**"))
    L.append("")
    L.append("## 逐項核對")
    L.append("")
    for c in comps:
        pr = pby.get(c["id"], {})
        L.append("### %s %s（%s）" % (c["id"], c.get("name", ""), "/".join(c["_views"]) or "—"))
        L.append("")
        for v in c["_views"]:
            b = c["_bbox"].get(v)
            if b:
                L.append("- 計畫框 @%s：u %.2f..%.2f, v %.2f..%.2f" % (v, b[0], b[2], b[1], b[3]))
        if c.get("objects"):
            L.append("- 對應物件：`%s`" % "`, `".join(c["objects"]))
        if pr.get("params"):
            for p in pr["params"]:
                mark = {"confirmed": "OK", "unmatched": "**虛報**",
                        "no-value": "**未填**"}.get(p["status"], "待確認")
                val = "-" if p["value"] is None else ("%.4g" % float(p["value"]))
                L.append("- 參數 %s = %s ［%s → %s］%s"
                         % (p["name"], val, p["declared"] or "?", mark,
                            ("  ← 圖面 %s" % ", ".join(p["matched"])) if p["matched"] else ""))
        else:
            L.append("- 參數：**尚未列出**")
        L.append("")
        L.append("- [ ] 圖上可見　- [ ] 位置／比例正確　- [ ] 有標註數字")
        L.append("- 圖上確認：")
        L.append("- 備註：")
        L.append("")
    L.append("## 圖譜對照（缺件）")
    L.append("")
    L.append("對照 `assets/anatomy/<品類>.md` 的六面清單／成對組件表，逐項確認元件表是否已涵蓋：")
    L.append("")
    L.append("- 圖譜有列、元件表沒有的 → 補進元件表，或在元件表 meta 說明為何不需要。")
    L.append("- 圖上看得見、兩邊都沒有的 → 這才是真正的漏件，優先補。")
    L.append("- 成對組件（左右／前後）逐對點名，缺一即錯。")
    L.append("")
    if ann:
        L.append("## 圖面標註總表（%d 項，供對照）" % len(ann))
        L.append("")
        L.append("| 標註項 | 值 (mm) |")
        L.append("|---|---|")
        for k in sorted(ann):
            L.append("| `%s` | %.4g |" % (k, ann[k]))
        L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
def _selftest():
    fails = []

    def chk(name, cond, detail=""):
        if not cond:
            fails.append("%s %s" % (name, detail))
        print("  %-34s %s %s" % (name, "ok" if cond else "FAIL",
                                 detail if not cond else ""))

    # --- 幾何 ---
    aabb = [0, 0, 0, 10, 20, 30]
    chk("front.aabb", aabb_to_view_bbox(aabb, "front") == [0, 0, 10, 30])
    chk("rear.aabb", aabb_to_view_bbox(aabb, "rear") == [-10, 0, 0, 30])
    chk("side.aabb", aabb_to_view_bbox(aabb, "side") == [0, 0, 20, 30])
    chk("top.aabb", aabb_to_view_bbox(aabb, "top") == [0, 0, 10, 20])
    chk("mirror.rear.u", aabb_to_view_bbox([10, 0, 0, 20, 1, 1], "rear") == [-20, 0, -10, 1])
    chk("mirror.back.u", aabb_to_view_bbox([0, 10, 0, 1, 20, 1], "back") == [-20, 0, -10, 1])
    chk("aabb.unsorted", aabb_to_view_bbox([10, 20, 30, 0, 0, 0], "front") == [0, 0, 10, 30])
    chk("delta.world.front", view_delta_to_world("front", 3.0, 5.0) == [3.0, 0.0, 5.0])
    chk("delta.world.rear", view_delta_to_world("rear", 3.0, 5.0) == [-3.0, 0.0, 5.0])
    chk("angle.axes.same", angle_between_axes([1, 0, 0], [1, 0, 0]) == 0.0)
    chk("angle.axes.neg", angle_between_axes([1, 0, 0], [-1, 0, 0]) == 0.0)
    chk("angle.axes.90", angle_between_axes([1, 0, 0], [0, 1, 0]) == 90.0)

    # --- v1 升級 ---
    v1 = {"schema": SCHEMA_V1, "components": [
        {"id": "A-1", "name": "機身", "view": "front", "bbox_mm": [-39, 0, 39, 163],
         "source": "measured"},
        {"id": "A-2", "name": "顯示", "view": "front",
         "center_mm": [0, 80], "size_mm": [72, 158], "params": {"w": 72.0}},
    ]}
    comps, meta = normalize_table(v1)
    chk("v1.count", len(comps) == 2)
    chk("v1.views", comps[0]["_views"] == ["front"])
    chk("v1.bbox.expand", comps[1]["_bbox"]["front"] == [-36.0, 1.0, 36.0, 159.0])
    chk("v1.params.dict", comps[1]["_params"] == [{"name": "w", "value": 72.0}])
    bp = to_blueprint_v1(comps)
    chk("v1.to_blueprint.schema", bp["schema"] == SCHEMA_V1)
    chk("v1.to_blueprint.count", len(bp["components"]) == 2)
    chk("v1.to_blueprint.fields", all("bbox_mm" in x and "view" in x for x in bp["components"]))

    # --- v2 多視圖 ---
    v2 = {"schema": SCHEMA, "subject": "T", "components": [
        {"id": "B-1", "name": "平台", "views": ["rear", "side"],
         "bbox_mm": {"rear": [21, 91, 36, 163], "side": [-4.4, 91, -1.6, 163]},
         "params": [{"name": "length_mm", "value": 72.05, "source": "annotation"},
                    {"name": "thickness_mm", "value": 2.70, "source": "annotation"},
                    {"name": "guess_mm", "value": 99.9, "source": "annotation"}],
         "objects": ["Mst_Plateau*"], "axis": [0, 0, 1]},
    ]}
    comps2, meta2 = normalize_table(v2)
    chk("v2.views", comps2[0]["_views"] == ["rear", "side"])
    chk("v2.meta", meta2.get("subject") == "T")

    # --- 覆蓋 ---
    calib = {
        "subject": {"name": "T"},
        "views": {
            "front": {"contour_mm": [[-39, 0], [39, 0], [39, 163], [-39, 163]]},
            "rear": {"contour_mm": [[-39, 0], [39, 0], [39, 163], [-39, 163]]},
            "side": {"contour_mm": [[-4.4, 0], [4.4, 0], [4.4, 163], [-4.4, 163]]},
        },
        "annotated_dims_mm": {"rear": {"plateau_len": 72.05, "camera_plateau_height": 2.7}},
    }
    cov = audit_coverage(comps2, calib)
    chk("cov.components", cov["stats"]["component_count"] == 1)
    chk("cov.blind_front", cov["stats"]["blind_views"] == ["front"])
    chk("cov.problems.blind", any("盲區" in p for p in cov["problems"]))
    chk("cov.inside", not any("超出" in p for p in cov["problems"]), str(cov["problems"]))

    # 超框應該被抓到
    over = dict(comps2[0])
    over = normalize_component({"id": "B-9", "name": "超框", "views": ["front"],
                                "bbox_mm": {"front": [-50, 0, 50, 163]}})
    cov2 = audit_coverage([over], calib)
    chk("cov.overflow", any("超出" in p for p in cov2["problems"]), str(cov2["problems"]))

    # 刻意凸出的構成元件：標 exclude_from_containment 後不列違規，但仍計入視圖覆蓋
    exc = normalize_component({"id": "B-8", "name": "凸出件（按鍵）", "views": ["front"],
                               "exclude_from_containment": True,
                               "bbox_mm": {"front": [-50, 0, 50, 163]}})
    cov3 = audit_coverage([exc], calib)
    chk("cov.exclude.no.problem", not any("超出" in p for p in cov3["problems"]),
        str(cov3["problems"]))
    chk("cov.exclude.still.counted",
        cov3["stats"]["per_view_counts"].get("front") == 1, str(cov3["stats"]))
    chk("cov.exclude.recorded",
        bool(cov3["views"]["front"].get("excluded_over")), str(cov3["views"]["front"]))

    # --- 參數 ---
    par = audit_params(comps2, calib)
    st = par["items"][0]["params"]
    chk("param.confirmed", st[0]["status"] == "confirmed", str(st[0]))
    chk("param.matched.key", "rear.plateau_len" in st[0]["matched"], str(st[0]["matched"]))
    chk("param.unmatched", st[2]["status"] == "unmatched", str(st[2]))
    chk("param.stats", par["stats"]["confirmed"] == 2 and par["stats"]["unmatched"] == 1,
        str(par["stats"]))
    chk("param.problem", any("虛報" in p for p in par["problems"]))

    # --- checklist ---
    md = render_checklist(comps2, calib, audit=cov, params=par)
    chk("checklist.head", md.startswith("# 元件核對清單"))
    chk("checklist.has.comp", "B-1" in md and "圖上可見" in md)
    chk("checklist.has.ann", "rear.plateau_len" in md)
    chk("checklist.legend", "圖譜對照" in md)

    # --- compare ---
    measured = {"schema": MEASURED_SCHEMA, "blend": "x.blend", "unit_to_mm": 1000.0,
                "components": [
                    {"id": "B-1", "objects": ["Mst_Plateau"],
                     "aabb_mm": [-21, -4.4, 91, -36, -1.6, 163],
                     "centroid_mm": [0, 0, 0],
                     "axes": [[0, 0, 1], [1, 0, 0], [0, 1, 0]]},
                ]}
    cmp1 = compare(comps2, measured)
    rec = cmp1["items"][0]
    chk("cmp.status.ok", rec["status"] == "ok", str(rec.get("views")))
    chk("cmp.pos.exact", rec["views"]["rear"]["d_center"] == [0.0, 0.0],
        str(rec["views"]["rear"]))
    chk("cmp.axis.ok", rec["axis"]["ok"] is True)
    chk("cmp.no.problem", not cmp1["problems"], str(cmp1["problems"]))

    # 故意偏 2mm 尺寸 + 90° 方向
    bad = {"schema": MEASURED_SCHEMA, "blend": "x.blend", "components": [
        {"id": "B-1", "objects": ["Mst_Plateau"],
         "aabb_mm": [-21, -4.4, 91, -34, -1.6, 165],
         "axes": [[1, 0, 0], [0, 0, 1], [0, 1, 0]]}]}
    cmp2 = compare(comps2, bad)
    chk("cmp.bad.status", cmp2["items"][0]["status"] == "fail")
    chk("cmp.bad.size", cmp2["stats"]["size_fail"] >= 1, str(cmp2["stats"]))
    chk("cmp.bad.angle", cmp2["stats"]["ang_fail"] == 1, str(cmp2["stats"]))
    chk("cmp.bad.problem.text",
        any("長軸方向偏差" in p for p in cmp2["problems"]), str(cmp2["problems"]))
    chk("cmp.bad.suggest", bool(cmp2["items"][0].get("suggest")))

    # 模型缺件
    miss = {"schema": MEASURED_SCHEMA, "blend": "x.blend", "components": [
        {"id": "Z-9", "objects": ["Mst_Other"], "aabb_mm": [0, 0, 0, 1, 1, 1]}]}
    cmp3 = compare(comps2, miss)
    chk("cmp.miss.model", cmp3["stats"]["missing_in_model"] == 1)
    chk("cmp.not.in.table", cmp3["stats"]["not_in_table"] == 1)
    chk("cmp.miss.problem", any("找不到對應物件" in p for p in cmp3["problems"]))

    # void 元件（開口）：不進缺件清單，只驗 host
    voidc = [dict(comps2[0], id="V-1", void=True, host="Mst_Plateau")]
    void_meas = {"schema": MEASURED_SCHEMA, "blend": "x.blend", "components": [
        {"id": "V-1", "void": True, "host": "Mst_Plateau", "host_present": True,
         "objects": ["Mst_Plateau"], "aabb_mm": None, "axes": []}]}
    cmp4 = compare(voidc, void_meas)
    chk("cmp.void.ok", cmp4["items"][0]["status"] == "void-ok",
        str(cmp4["items"][0]))
    chk("cmp.void.stat", cmp4["stats"]["void_ok"] == 1 and
        cmp4["stats"]["missing_in_model"] == 0, str(cmp4["stats"]))
    chk("cmp.void.no.problem", not cmp4["problems"], str(cmp4["problems"]))
    void_host_gone = {"schema": MEASURED_SCHEMA, "blend": "x.blend", "components": [
        {"id": "V-1", "void": True, "host": "Mst_Gone", "host_present": False,
         "aabb_mm": None}]}
    cmp5 = compare(voidc, void_host_gone)
    chk("cmp.void.host_missing", cmp5["items"][0]["status"] == "void-host-missing" and
        cmp5["stats"]["missing_in_model"] == 1, str(cmp5["stats"]))
    chk("cmp.void.host.problem", any("host" in p for p in cmp5["problems"]),
        str(cmp5["problems"]))

    # --- CP1-C 外觀規格 ---
    app_ok = [normalize_component({"id": "P-1", "name": "背板", "level": 4,
                                   "views": ["rear"],
                                   "bbox_mm": {"rear": [-1, 0, 1, 2]},
                                   "appearance": {"material": "Mat_Glass*",
                                                  "flat_axis": "y",
                                                  "max_extent_mm": 0.05,
                                                  "evidence": "photo:rear.jpg"}})]
    a1 = audit_appearance(app_ok)
    chk("appear.ok", not a1["problems"], str(a1["problems"]))
    chk("appear.stats", a1["stats"]["material_patterns"] == 1 and
        a1["stats"]["flat_limits"] == 1, str(a1["stats"]))

    a2 = audit_appearance([normalize_component(
        {"id": "P-2", "name": "裸件", "level": 4, "views": ["rear"],
         "bbox_mm": {"rear": [-1, 0, 1, 2]}})])
    chk("appear.missing", any("沒有宣告外觀" in p for p in a2["problems"]),
        str(a2["problems"]))

    a3 = audit_appearance([normalize_component(
        {"id": "P-3", "name": "無依據", "level": 4, "views": ["rear"],
         "bbox_mm": {"rear": [-1, 0, 1, 2]}, "appearance": {"material": "Mat_X*"}})])
    chk("appear.no_evidence", any("缺 evidence" in p for p in a3["problems"]),
        str(a3["problems"]))

    a4 = audit_appearance([normalize_component(
        {"id": "P-4", "name": "內部件", "level": 4, "views": ["rear"],
         "bbox_mm": {"rear": [-1, 0, 1, 2]},
         "appearance_skipped": "內部不可見件"})])
    chk("appear.skipped", not a4["problems"] and a4["stats"]["skipped"] == 1,
        str(a4["stats"]))

    a5 = audit_appearance([normalize_component(
        {"id": "P-5", "name": "半套", "level": 4, "views": ["rear"],
         "bbox_mm": {"rear": [-1, 0, 1, 2]},
         "appearance": {"flat_axis": "y", "evidence": "photo:x.jpg"}})])
    chk("appear.pair", any("必須成對出現" in p for p in a5["problems"]),
        str(a5["problems"]))

    # --- 衝突停損 ---
    conf = normalize_component({
        "id": "C-1", "name": "底板高", "level": 3, "views": ["rear"],
        "bbox_mm": {"rear": [-1, 0, 1, 2]},
        "params": [{"name": "plateau_len", "value": 72.05, "source": "annotation",
                    "conflicts": [{"value": 70.2, "source": "measured"}]}]})
    p1 = audit_params([conf], calib)
    chk("conflict.blocked", p1["stats"].get("conflict") == 1 and
        any("尚未裁定" in x for x in p1["problems"]), str(p1["problems"]))
    chk("conflict.verdict", p1["items"][0]["verdict"] == "conflict",
        str(p1["items"][0]["verdict"]))

    p2 = audit_params([normalize_component({
        "id": "C-2", "name": "底板高", "level": 3, "views": ["rear"],
        "bbox_mm": {"rear": [-1, 0, 1, 2]},
        "params": [{"name": "plateau_len", "value": 72.05, "source": "annotation",
                    "conflicts": [{"value": 70.2, "source": "measured"}],
                    "resolved_by": "annotation",
                    "resolution_note": "圖面標註優先於掃描"}]})], calib)
    chk("conflict.resolved", not p2["problems"], str(p2["problems"]))

    # --- 元件表深度 ---
    c_deep = audit_coverage([normalize_component(
        {"id": "D-1", "name": "深件", "level": 6, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}})], calib)
    chk("depth.ok", not any("拆解深度不足" in x for x in c_deep["problems"]),
        str(c_deep["problems"]))
    chk("depth.hist", c_deep["stats"]["level_histogram"] == {"6": 1},
        str(c_deep["stats"]))
    c_shallow = audit_coverage(comps2, calib)
    chk("depth.shallow", any("拆解深度不足" in x for x in c_shallow["problems"]),
        str(c_shallow["problems"]))
    c_ex = audit_coverage([normalize_component(
        {"id": "E-1", "name": "豁免", "level": 2, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}, "depth_exempt": "單一鈑金件"})], calib)
    chk("depth.exempt", not any("拆解深度不足" in x for x in c_ex["problems"]),
        str(c_ex["problems"]))
    # audit_depth() 獨立於 calib／三視圖（原創設計類唯一跑得到的閘門）：同一份元件表，
    # 淺的擋、深的過、有 depth_exempt 的放行——證明深度判準只有這一份，沒有複製邏輯。
    d_shallow = audit_depth(comps2, min_level=MIN_EXPECTED_COMPONENT_LEVEL)
    chk("depth.standalone.blocks",
        any("拆解深度不足" in x for x in d_shallow["problems"]), str(d_shallow["problems"]))
    d_deep = audit_depth([normalize_component(
        {"id": "D-2", "name": "深件", "level": 6, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}})],
        min_level=MIN_EXPECTED_COMPONENT_LEVEL_ORIGINAL)
    chk("depth.standalone.ok", not d_deep["problems"], str(d_deep["problems"]))
    d_exempt = audit_depth([normalize_component(
        {"id": "E-2", "name": "豁免件", "level": 3, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}, "depth_exempt": "單一射出件"})],
        min_level=MIN_EXPECTED_COMPONENT_LEVEL_ORIGINAL)
    chk("depth.standalone.exempt", not d_exempt["problems"], str(d_exempt["problems"]))

    # --- CP2 外觀：材質與貼合厚度 ---
    app_comp = [normalize_component({
        "id": "M-1", "name": "磁吸環", "level": 3, "views": ["rear"],
        "bbox_mm": {"rear": [-28.75, 44.92, 28.75, 102.42]},
        "objects": ["Back_MagSafe"],
        "appearance": {"material": "Mat_MagSafe*", "flat_axis": "y",
                       "max_extent_mm": 0.05, "evidence": "photo:rear.jpg"}})]
    m_ok = {"schema": MEASURED_SCHEMA, "components": [
        {"id": "M-1", "objects": ["Back_MagSafe"],
         "aabb_mm": [-28.75, 0.0, 44.92, 28.75, 0.02, 102.42],
         "materials": ["Mat_MagSafe"]}]}
    e1 = compare(app_comp, m_ok)
    chk("extent.ok", e1["items"][0]["extent"]["ok"] is True,
        str(e1["items"][0].get("extent")))
    chk("material.ok", e1["items"][0]["material"]["ok"] is True)
    chk("appearance.cmp.clean", not e1["problems"], str(e1["problems"]))

    m_bad = {"schema": MEASURED_SCHEMA, "components": [
        {"id": "M-1", "objects": ["Back_MagSafe"],
         "aabb_mm": [-28.75, 0.0, 44.92, 28.75, 0.35, 102.42],
         "materials": ["Mat_Plastic"]}]}
    e2 = compare(app_comp, m_bad)
    chk("extent.fail", e2["stats"]["extent_fail"] == 1, str(e2["stats"]))
    chk("material.fail", e2["stats"]["material_fail"] == 1, str(e2["stats"]))
    chk("appearance.cmp.problem",
        any("材質不符" in p for p in e2["problems"]) and
        any("超過上限" in p for p in e2["problems"]), str(e2["problems"]))

    # --- 版本史 / 凍結違規 ---
    base = {"schema": SCHEMA, "components": [
        {"id": "L-1", "name": "凍結件", "level": 4, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}, "locked": True, "verified_at": "v3"},
        {"id": "L-2", "name": "自由件", "level": 4, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}}]}
    nxt = {"schema": SCHEMA, "components": [
        {"id": "L-1", "name": "凍結件", "level": 4, "views": ["front"],
         "bbox_mm": {"front": [-2, 0, 2, 2]}, "locked": True, "verified_at": "v3"},
        {"id": "L-2", "name": "自由件", "level": 4, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}, "change_note": "名稱與說明調整"},
        {"id": "L-3", "name": "新件", "level": 4, "views": ["front"],
         "bbox_mm": {"front": [-1, 0, 1, 2]}}]}
    dr = diff_tables(base, nxt)
    chk("diff.added", dr["stats"]["added"] == 1, str(dr["stats"]))
    chk("diff.changed", dr["stats"]["changed"] == 1, str(dr["stats"]))
    chk("diff.unchanged", dr["stats"]["unchanged"] == 1, str(dr["stats"]))
    chk("diff.locked", dr["stats"]["locked_changed"] == 1 and
        any("已凍結" in p for p in dr["problems"]), str(dr["problems"]))
    chk("diff.note_missing", dr["stats"]["note_missing"] == 1 and
        any("沒有 change_note" in w for w in dr["warnings"]), str(dr["warnings"]))
    mdd = render_diff(dr, old_label="a.json", new_label="b.json")
    chk("diff.md.title", mdd.startswith("# 元件表變更紀錄"), mdd[:80])
    chk("diff.md.row", "L-1" in mdd and "bbox_mm" in mdd, mdd[:400])
    chk("diff.md.problems", "## 違規" in mdd)

    # --- 一輪鎖一個元件群（scope）---
    dsc = diff_tables(base, nxt, scope=["L-2"])
    chk("diff.scope.flagged", dsc["stats"]["out_of_scope"] == 2 and
        any("scope）外" in p for p in dsc["problems"]), str(dsc["problems"]))
    chk("diff.scope.stats", dsc["stats"]["scoped"] is True and
        dsc["scope"] == ["L-2"], str(dsc["stats"]))
    chk("diff.scope.ok", not any("scope）外" in p for p in
        diff_tables(base, nxt, scope=["L-1", "L-2", "L-3"])["problems"]))
    mdsc = render_diff(dsc, old_label="a.json", new_label="b.json")
    chk("diff.scope.md", "本輪修改範圍（scope）" in mdsc, mdsc[:600])

    # --- 偏差對照表（CP2 報告） ---
    md2 = render_compare(cmp1, subject="測試主體",
                         tolerances={"pos_tol_mm": DEFAULT_POS_TOL_MM})
    chk("cmpmd.title", md2.startswith("# 元件校正（CP2）"))
    chk("cmpmd.subject", "- 主體：測試主體" in md2, md2[:200])
    chk("cmpmd.header", "| 元件 | 名稱 | 視圖 |" in md2)
    chk("cmpmd.row", "| B-1 |" in md2, md2[200:900])
    chk("cmpmd.axis", "長軸方向" in md2, md2[400:1200])
    chk("cmpmd.problems", "## 問題" in md2)
    chk("cmpmd.void_table", "開口類元件" not in md2)  # cmp1 沒有 void 元件
    md3 = render_compare(cmp4, subject="開口測試")
    chk("cmpmd.void.table", "開口類元件" in md3 and "host 存在" in md3, md3[:600])
    md4 = render_compare(cmp3, subject="缺件測試")
    chk("cmpmd.missing.section", "模型裡找不到" in md4, md4[:600])

    # --- 檔案往返 ---
    tmp = os.path.join(os.environ.get("TEMP", "."), "_component_lib_selftest.json")
    save_table(comps2, tmp, meta2)
    back, meta3 = load_table(tmp)
    chk("roundtrip.views", back[0]["_views"] == ["rear", "side"])
    chk("roundtrip.bbox", back[0]["_bbox"]["side"][3] == 163.0)
    chk("roundtrip.meta", meta3.get("schema") == SCHEMA)
    try:
        os.remove(tmp)
    except OSError:
        pass

    print("TOTAL_FAILED: %d" % len(fails))
    for x in fails:
        print("  FAIL:", x)
    return 1 if fails else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _dump_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    return path


def _dump_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _print_issues(tag, issues):
    print("[%s] %d issue(s)" % (tag, len(issues)))
    for m in issues:
        print("   - %s" % m)


def main(argv=None):
    ap = argparse.ArgumentParser(description="component_lib — 元件表 × 三視圖 對賬")
    sub = ap.add_subparsers(dest="cmd")

    a = sub.add_parser("audit", help="CP1：覆蓋/盲區 + 拆解深度 + 參數可查性 + 外觀規格")
    a.add_argument("--calib", required=True)
    a.add_argument("--components", required=True)
    a.add_argument("--out", required=True)

    c = sub.add_parser("checklist", help="產出視覺核對清單（Markdown）")
    c.add_argument("--calib", required=True)
    c.add_argument("--components", required=True)
    c.add_argument("--out", required=True)

    m = sub.add_parser("compare", help="CP2：規劃 vs 實測")
    m.add_argument("--calib", required=True)
    m.add_argument("--components", required=True)
    m.add_argument("--measured", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--pos-tol", dest="pos_tol", type=float, default=DEFAULT_POS_TOL_MM,
                   help="位置偏差門檻 mm（預設 %(default)s；依主體尺度調整）")
    m.add_argument("--size-tol", dest="size_tol", type=float, default=DEFAULT_SIZE_TOL_MM,
                   help="尺寸偏差門檻 mm（預設 %(default)s）")
    m.add_argument("--ang-tol", dest="ang_tol", type=float, default=DEFAULT_ANG_TOL_DEG,
                   help="方向偏差門檻度（預設 %(default)s）")

    d = sub.add_parser("diff", help="CP1-D：版本史（兩個元件表的變更）+ 凍結/範圍違規")
    d.add_argument("--old", required=True, help="上一版元件表 JSON")
    d.add_argument("--new", required=True, help="本版元件表 JSON")
    d.add_argument("--out", required=True)
    d.add_argument("--scope", default=None,
                   help="本輪允許修改的元件 id（逗號分隔，支援 fnmatch 樣式）；"
                        "給了就把範圍外的變更判為違規（§16.9.5 規則 4）")

    p = sub.add_parser("depth", help="CP1-A0：拆解深度（§11 Stage A item 3，不需 calib）")
    p.add_argument("--components", required=True)
    p.add_argument("--min-level", dest="min_level", type=int,
                   default=MIN_EXPECTED_COMPONENT_LEVEL_ORIGINAL,
                   help="最低期望層級（預設 %(default)s＝§11 的六級；"
                        "三視圖流程要沿用 CP1 的 4 也可以）")
    p.add_argument("--out", default=None,
                   help="可選：落 component_depth.json/.md 的目錄；不給只印結果")

    sub.add_parser("selftest", help="不需要外部檔案的自我測試")

    args = ap.parse_args(argv)
    if args.cmd == "selftest" or not args.cmd:
        return _selftest()

    if args.cmd == "diff":
        scope = [s.strip() for s in args.scope.split(",") if s.strip()] \
            if args.scope else None
        res = diff_tables(_load_json(args.old), _load_json(args.new), scope=scope)
        _dump_json(os.path.join(args.out, "component_diff.json"), res)
        md = render_diff(res, old_label=os.path.basename(args.old),
                         new_label=os.path.basename(args.new))
        _dump_text(os.path.join(args.out, "component_diff.md"), md)
        _print_issues("warnings", res["warnings"])
        _print_issues("diff", res["problems"])
        return 1 if res["problems"] else 0

    comps, meta = load_table(args.components)

    if args.cmd == "depth":
        depth = audit_depth(comps, min_level=args.min_level)
        if args.out:
            _dump_json(os.path.join(args.out, "component_depth.json"),
                       {"schema": "component_depth/1", "subject": meta.get("subject"),
                        "revision": meta.get("revision"), **depth})
            L = ["# 元件表拆解深度（CP1-A0，§11 Stage A item 3）", "",
                 "門檻：LEVEL %d" % args.min_level, "",
                 json.dumps(depth["stats"], ensure_ascii=False, indent=1), "",
                 "## 問題", ""]
            L += ["- %s" % x for x in depth["problems"]] or ["- (無)"]
            _dump_text(os.path.join(args.out, "component_depth.md"), "\n".join(L) + "\n")
        print("[depth] min_level=%d max_level=%d components=%d"
              % (args.min_level, depth["stats"]["max_level"],
                 depth["stats"]["component_count"]))
        _print_issues("depth", depth["problems"])
        return 1 if depth["problems"] else 0

    calib = _load_json(args.calib)

    if args.cmd == "audit":
        cov = audit_coverage(comps, calib)
        par = audit_params(comps, calib)
        app = audit_appearance(comps)
        open_items = [str(x) for x in (meta.get("open_items") or [])]
        doc = {"schema": "component_audit/1", "subject": meta.get("subject"),
               "revision": meta.get("revision"),
               "coverage": cov, "params": par, "appearance": app,
               "open_items": open_items,
               "problems": cov["problems"] + par["problems"] + app["problems"]}
        _dump_json(os.path.join(args.out, "component_audit.json"), doc)
        L = ["# 元件對賬（CP1）", "",
             "## 覆蓋", "", json.dumps(cov["stats"], ensure_ascii=False, indent=1), "",
             "## 參數來源", "", json.dumps(par["stats"], ensure_ascii=False, indent=1), "",
             "## 外觀規格", "", json.dumps(app["stats"], ensure_ascii=False, indent=1), "",
             "## 未結案（open_items，不擋但必須出現在交付說明）", ""]
        L += ["- %s" % x for x in open_items] or ["- (無)"]
        L += ["", "## 問題", ""]
        L += ["- %s" % p for p in doc["problems"]] or ["- (無)"]
        _dump_text(os.path.join(args.out, "component_audit.md"), "\n".join(L) + "\n")
        _print_issues("coverage", cov["problems"])
        _print_issues("params", par["problems"])
        _print_issues("appearance", app["problems"])
        if open_items:
            print("[open_items] %d 項未結案：" % len(open_items))
            for x in open_items:
                print("   - %s" % x)
        return 1 if doc["problems"] else 0

    if args.cmd == "checklist":
        md = render_checklist(comps, calib, subject=meta.get("subject"))
        path = _dump_text(os.path.join(args.out, "component_checklist.md"), md)
        print("checklist -> %s (%d chars)" % (path, len(md)))
        return 0

    if args.cmd == "compare":
        res = compare(comps, _load_json(args.measured), calib)
        _dump_json(os.path.join(args.out, "component_compare.json"), res)
        md = render_compare(
            res, subject=meta.get("subject"),
            tolerances={"pos_tol_mm": args.pos_tol, "size_tol_mm": args.size_tol,
                        "ang_tol_deg": args.ang_tol})
        _dump_text(os.path.join(args.out, "component_compare.md"), md)
        _print_issues("compare", res["problems"])
        return 1 if res["problems"] else 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    # Tolerate launch through Blender's bundled interpreter: strip Blender's own
    # arguments (everything up to and including the first "--") so the CLI also
    # works as `blender --background --python component_lib.py -- <cmd> ...` on
    # machines that ship Blender but no standalone Python (SKILL.md 16.9.4).
    _argv = sys.argv
    sys.exit(main(_argv[_argv.index("--") + 1:] if "--" in _argv else None))
