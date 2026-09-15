# -*- coding: utf-8 -*-
# KEYWORDS: blender, bpy, component, 元件表, measure, 量測, aabb, pca, 校正, triview
"""component_measure —— 從 .blend 量出元件表每個元件的實測值（Blender headless）

定位（SKILL.md §16.9.4）
------------------------------------------------------------------
`component_lib.compare()` 的另一半：對賬模組負責「比」，本檔負責「量」。
載入指定的 .blend，依元件表的 `objects` 樣式找到對應物件，算出：

  aabb_mm     世界軸對齊包圍盒 [x0,y0,z0,x1,y1,z1]（mm）
  centroid_mm 全部頂點的世界質心（mm）
  axes        PCA 主軸（世界單位向量，由長到短）——供方向偏差檢查
  materials   該元件用到的材質名（去重、排序；空槽記 '(empty)'）——供外觀對賬
  parts       多個物件匹配時，逐物件的 AABB（mm）與材質

元件表標了 `"void": true` 的元件（USB 孔／麥克風孔／SIM 卡槽／喇叭網孔這類**開口**）
不量 AABB——開口本身沒有 mesh，把 host 整塊量下來只會得到 host 的尺寸。此時改為驗證
`"host"` 是否存在，回報 `void=True` + `host_present`；「量不到」與「沒建」是兩件事。

輸出 schema `components_measured/1`，直接餵給：

    python assets/component_lib.py compare --calib C --components K --measured M --out DIR

關鍵實作注意
------------------------------------------------------------------
  * `transform_apply()` 會把 loc/rot/scale 全部烘進 mesh（SKILL.md §8 #9），
    所以位置一律用 `matrix_world @ v.co` 計算，**不讀 object.location/rotation**。
  * 世界座標 → mm 需要單位換算：`--unit-to-mm`（預設 1000，即 1 unit = 1 m，
    這是場景包把 mm 除以 1000 建模後的慣例）。場景若直接以 mm 建模，傳 1。
  * 物件名匹配用 fnmatch 萬用字元（`Mst_Camera*`），不區分大小寫。

CLI
------------------------------------------------------------------
    blender --background --python component_measure.py -- \
        --blend <scene.blend> --components <components.json> --out <measured.json> \
        [--unit-to-mm 1000]
    blender --background --python component_measure.py -- --selftest

已知限制
------------------------------------------------------------------
  1. 只量 MESH 物件；CURVE/EMPTY 等非網格物件不會貢獻頂點，但若是元件的唯一
     代表物件（例如以 EMPTY 當樞軸），會被記成 vert_count=0 而不是 missing。
  2. `objects` 樣式若同時匹配到母版（park_master 停遠處）與實例，AABB 會橫跨兩者
     ——請在元件表用更精確的樣式（`Inst_*` 而非 `*`）。
  3. PCA 主軸只在點雲有明顯長寬比時才有意義；接近立方體的元件，axes 順序不穩定，
     不要拿它做方向斷言（改用 AABB 的各軸跨距）。
"""

import argparse
import fnmatch
import json
import math
import os
import sys

import bpy
import numpy as np

MEASURED_SCHEMA = "components_measured/1"
DEFAULT_UNIT_TO_MM = 1000.0
PCA_MAX_POINTS = 20000          # SVD 取樣上限（超過就隨機抽樣）
DEFAULT_RNG_SEED = 20260912     # 抽樣固定種子，重跑可重現


# --------------------------------------------------------------------------
# 場景側
# --------------------------------------------------------------------------
def _mesh_objects():
    bpy.context.view_layer.update()
    return [o for o in bpy.data.objects if o.type == "MESH"]


def resolve_objects(patterns):
    """依 fnmatch 樣式找出 mesh 物件（不區分大小寫），保持輸入順序。"""
    objs = _mesh_objects()
    out = []
    for pat in patterns or []:
        p = str(pat).lower()
        for o in objs:
            if o in out:
                continue
            if fnmatch.fnmatch(o.name.lower(), p):
                out.append(o)
    return out


def _materials_of(objs):
    """物件用到的材質名（去重、排序）；空材質槽記成 '(empty)'。

    外觀對賬（component_lib 的 `appearance.material`）靠這份清單驗——「該是白的
    閃光燈渲成黑的」這類問題，材質名對不上就是對不上，不用等渲染出來用眼睛看。
    """
    names = set()
    for o in objs:
        slots = getattr(o.data, "materials", None) or []
        if not slots:
            names.add("(empty)")
            continue
        for m in slots:
            names.add(m.name if m else "(empty)")
    return sorted(names)


def _verts_world(obj):
    """obj 的世界座標頂點（N x 3，單位＝場景單位）。"""
    n = len(obj.data.vertices)
    if n == 0:
        return np.zeros((0, 3), dtype=np.float64)
    co = np.empty(n * 3, dtype=np.float32)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(n, 3).astype(np.float64)
    m = np.array(obj.matrix_world, dtype=np.float64)
    return co @ m[:3, :3].T + m[:3, 3]


def stack_points(objs, max_points=PCA_MAX_POINTS, seed=DEFAULT_RNG_SEED):
    """把多個物件的世界頂點疊成一份點雲；總數超過 max_points 時隨機抽樣。"""
    chunks = [_verts_world(o) for o in objs]
    chunks = [c for c in chunks if len(c)]
    if not chunks:
        return np.zeros((0, 3), dtype=np.float64), 0
    total = sum(len(c) for c in chunks)
    pts = np.vstack(chunks) if len(chunks) > 1 else chunks[0]
    if total > max_points:
        rng = np.random.default_rng(seed)
        idx = rng.choice(total, size=max_points, replace=False)
        pts = pts[np.sort(idx)]
    return pts, total


def aabb_of(points):
    """點雲 → [x0,y0,z0,x1,y1,z1]；空點雲回 None。"""
    if len(points) == 0:
        return None
    lo = points.min(axis=0)
    hi = points.max(axis=0)
    return [float(lo[0]), float(lo[1]), float(lo[2]),
            float(hi[0]), float(hi[1]), float(hi[2])]


def pca_axes(points):
    """PCA 主軸（世界單位向量，由長到短）。點數不足或退化回 []。"""
    if len(points) < 4:
        return []
    c = points.mean(axis=0)
    x = points - c
    try:
        _, sv, vt = np.linalg.svd(x, full_matrices=False)
    except np.linalg.LinAlgError:
        return []
    # 奇異值為 0 的方向沒有資訊，剔除（例如完全扁平的薄板，第三軸無意義）
    scale = float(sv[0]) if len(sv) else 0.0
    keep = [i for i in range(min(3, len(vt))) if scale <= 1e-12 or sv[i] > scale * 1e-6]
    return [[float(v) for v in vt[i]] for i in keep]


def measure_component(comp, unit_to_mm):
    """單一元件 → 量測記錄。

    `comp["void"]` 為真時，這個元件是 host 上的**開口**（USB 孔、麥克風孔、SIM 卡槽、
    喇叭網孔）——它本身沒有 mesh，AABB 無從量起（把 host 整塊量下來只會得到 host 的
    尺寸，不是開口的尺寸）。此時改為驗證 `comp["host"]` 是否存在：host 在，代表這個面
    確實被建出來、開口是在實體上挖的；host 不在才是真的缺件。回報 `void=True` +
    `host_present`，由 component_lib.compare() 判讀，不冒充尺寸量測。
    """
    pats = comp.get("objects", [])
    if comp.get("void"):
        host_pats = [comp["host"]] if comp.get("host") else []
        hosts = resolve_objects(host_pats)
        return {
            "id": comp.get("id"), "name": comp.get("name", ""),
            "objects": [o.name for o in hosts], "patterns": list(pats),
            "missing": not hosts, "void": True, "host": comp.get("host"),
            "host_present": bool(hosts), "vert_count": 0, "parts": [],
            "aabb_mm": None, "centroid_mm": None, "axes": [],
        }
    objs = resolve_objects(pats)
    rec = {"id": comp.get("id"), "name": comp.get("name", ""),
           "objects": [o.name for o in objs], "patterns": list(pats),
           "missing": False, "vert_count": 0, "parts": [],
           "materials": _materials_of(objs)}

    if not objs:
        rec["missing"] = True
        rec["aabb_mm"] = None
        rec["centroid_mm"] = None
        rec["axes"] = []
        return rec

    for o in objs:
        pts_o = _verts_world(o)
        a = aabb_of(pts_o)
        rec["parts"].append({
            "object": o.name,
            "aabb_mm": None if a is None else [round(v * unit_to_mm, 4) for v in a],
            "vert_count": int(len(pts_o)),
            "materials": _materials_of([o]),
        })

    pts, total = stack_points(objs)
    aabb = aabb_of(pts)
    rec["vert_count"] = int(total)
    rec["aabb_mm"] = None if aabb is None else [round(v * unit_to_mm, 4) for v in aabb]
    if len(pts):
        cen = pts.mean(axis=0)
        rec["centroid_mm"] = [round(float(v) * unit_to_mm, 4) for v in cen]
    else:
        rec["centroid_mm"] = None
    rec["axes"] = [[round(float(v), 6) for v in ax] for ax in pca_axes(pts)]
    return rec


def scene_units():
    u = bpy.context.scene.unit_settings
    return {"scale_length": float(u.scale_length), "length_unit": str(u.length_unit)}


def measure_all(comps, unit_to_mm=DEFAULT_UNIT_TO_MM):
    return [measure_component(c, unit_to_mm) for c in comps]


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
def _selftest():
    fails = []

    def chk(name, cond, detail=""):
        if not cond:
            fails.append("%s %s" % (name, detail))
        print("  %-30s %s %s" % (name, "ok" if cond else "FAIL",
                                 detail if not cond else ""))

    bpy.ops.wm.read_factory_settings(use_empty=True)

    # A: 位置 (0.01, 0, 0.1)、尺寸 0.01 x 0.02 x 0.05 m
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.01, 0.0, 0.1))
    a = bpy.context.active_object
    a.name = "Mst_BoxA"
    a.scale = (0.01, 0.02, 0.05)
    bpy.ops.object.transform_apply(scale=True)
    a.data.materials.append(bpy.data.materials.new("Mat_Test"))

    # B: 繞 Z 轉 90°，長軸原本沿 Y（0.2）→ 轉後沿 X
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.3, 0.0))
    b = bpy.context.active_object
    b.name = "Mst_BoxB"
    b.scale = (0.01, 0.1, 0.005)
    b.rotation_euler = (0.0, 0.0, math.radians(90.0))
    bpy.ops.object.transform_apply(rotation=True, scale=True)

    comps = [
        {"id": "A", "name": "boxA", "objects": ["Mst_BoxA"]},
        {"id": "B", "name": "boxB", "objects": ["Mst_BoxB"]},
        {"id": "C", "name": "nope", "objects": ["Does_Not_Exist*"]},
    ]
    res = measure_all(comps, unit_to_mm=1000.0)
    m = {r["id"]: r for r in res}

    # --- A：AABB 與世界座標一致 ---
    want = [5.0, -10.0, 75.0, 15.0, 10.0, 125.0]
    got = m["A"]["aabb_mm"]
    ok = got is not None and all(abs(got[i] - want[i]) < 0.01 for i in range(6))
    chk("aabb.units_mm", ok, "got=%s want=%s" % (got, want))
    chk("missing.false", m["A"]["missing"] is False)
    chk("verts.count", m["A"]["vert_count"] == 8, str(m["A"]["vert_count"]))
    chk("parts.count", len(m["A"]["parts"]) == 1)

    # --- 材質（供外觀對賬） ---
    chk("materials.recorded", m["A"]["materials"] == ["Mat_Test"], str(m["A"]["materials"]))
    chk("materials.empty_slot", m["B"]["materials"] == ["(empty)"], str(m["B"]["materials"]))
    chk("materials.part_level", m["A"]["parts"][0]["materials"] == ["Mat_Test"],
        str(m["A"]["parts"][0]))

    # --- B：轉 90° 後長軸落在世界 X ---
    ax = m["B"]["axes"]
    chk("pca.has_axes", len(ax) >= 2, str(ax))
    chk("pca.long_axis_x", bool(ax) and abs(ax[0][0]) > 0.99,
        "axes[0]=%s" % (ax[0] if ax else None))
    bb = m["B"]["aabb_mm"]
    chk("pca.rot90.swapped", bb is not None
        and abs((bb[3] - bb[0]) - 100.0) < 0.05 and abs((bb[4] - bb[1]) - 10.0) < 0.05,
        str(bb))

    # --- C：找不到物件 ---
    chk("missing.true", m["C"]["missing"] is True)
    chk("missing.null_aabb", m["C"]["aabb_mm"] is None)
    chk("missing.no_axes", m["C"]["axes"] == [])

    # --- 萬用字元與大小寫 ---
    chk("fnmatch.wildcard", [o.name for o in resolve_objects(["Mst_Box*"])] ==
        ["Mst_BoxA", "Mst_BoxB"],
        str([o.name for o in resolve_objects(["Mst_Box*"])]))
    chk("fnmatch.case", [o.name for o in resolve_objects(["mst_boxa"])] == ["Mst_BoxA"])

    # --- 多物件聯集 ---
    u = measure_component({"id": "AB", "objects": ["Mst_Box*"]}, 1000.0)
    chk("union.parts", len(u["parts"]) == 2, str(len(u["parts"])))
    chk("union.span_x", abs((u["aabb_mm"][3] - u["aabb_mm"][0]) - 100.0) < 0.05,
        str(u["aabb_mm"]))

    # --- 單位換算可調 ---
    r1 = measure_component({"id": "A", "objects": ["Mst_BoxA"]}, 1.0)
    chk("unit_to_mm.1", abs(r1["aabb_mm"][3] - 0.015) < 1e-6, str(r1["aabb_mm"]))

    # --- void 元件（開口）：不量 AABB，只驗證 host 存在 ---
    v_ok = measure_component(
        {"id": "V1", "name": "usb aperture", "void": True, "host": "Mst_BoxA*"}, 1000.0)
    chk("void.flag", v_ok.get("void") is True)
    chk("void.host_present", v_ok["host_present"] is True and v_ok["missing"] is False,
        str(v_ok))
    chk("void.no_aabb", v_ok["aabb_mm"] is None)
    chk("void.objects_are_hosts", v_ok["objects"] == ["Mst_BoxA"], str(v_ok["objects"]))
    v_bad = measure_component(
        {"id": "V2", "void": True, "host": "Mst_NoSuchHost"}, 1000.0)
    chk("void.host_missing", v_bad["missing"] is True and v_bad["host_present"] is False)
    v_none = measure_component({"id": "V3", "void": True}, 1000.0)
    chk("void.no_host_declared", v_none["missing"] is True)

    # --- 空元件表 ---
    chk("empty.table", measure_all([], 1000.0) == [])

    print("TOTAL_FAILED: %d" % len(fails))
    for x in fails:
        print("  FAIL:", x)
    return 1 if fails else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    ap = argparse.ArgumentParser(description="component_measure — 量測 .blend 的元件實測值")
    ap.add_argument("--blend", help="要量的 .blend（省略＝用當前場景）")
    ap.add_argument("--components", help="元件表 JSON（component_lib schema）")
    ap.add_argument("--out", help="輸出 measured JSON")
    ap.add_argument("--unit-to-mm", type=float, default=DEFAULT_UNIT_TO_MM,
                    dest="unit_to_mm", help="1 場景單位 = 幾 mm（預設 1000）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.blend:
        if not os.path.isfile(args.blend):
            print("ERROR: blend not found: %s" % args.blend)
            return 2
        bpy.ops.wm.open_mainfile(filepath=args.blend)

    if not args.components:
        print("ERROR: --components is required (or use --selftest)")
        return 2

    doc = _load_json(args.components)
    comps = doc.get("components", doc) if isinstance(doc, dict) else doc

    measured = measure_all(comps, unit_to_mm=args.unit_to_mm)
    out = {
        "schema": MEASURED_SCHEMA,
        "blend": os.path.abspath(args.blend) if args.blend else "(current scene)",
        "unit_to_mm": args.unit_to_mm,
        "scene_units": scene_units(),
        "components": measured,
    }

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print("measured -> %s" % os.path.abspath(args.out))

    n_missing = sum(1 for m in measured if m["missing"])
    print("COMPONENT_MEASURE: %d component(s), %d missing" % (len(measured), n_missing))
    for m in measured:
        if m["missing"]:
            print("   MISSING %s %s (patterns=%s)" % (m["id"], m["name"], m["patterns"]))
        elif m.get("void"):
            print("   %-6s %-24s VOID (host=%s present)"
                  % (m["id"], m["name"], m["host"]))
        else:
            bb = m["aabb_mm"]
            size = [round(bb[3] - bb[0], 2), round(bb[4] - bb[1], 2), round(bb[5] - bb[2], 2)]
            print("   %-6s %-24s objs=%d verts=%d size_mm=%s"
                  % (m["id"], m["name"], len(m["objects"]), m["vert_count"], size))
    return 1 if n_missing else 0


if __name__ == "__main__":
    _argv = sys.argv
    _argv = _argv[_argv.index("--") + 1:] if "--" in _argv else []
    sys.exit(main(_argv))
