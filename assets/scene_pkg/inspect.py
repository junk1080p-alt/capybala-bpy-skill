# KEYWORDS: blender, bpy, inspect, 檢視, 除錯, debug, scene state, 場景狀態, scene_pkg
"""場景包第七件：常駐場景檢視腳本（§16；2026-09-11 新增）。

**為什麼要獨立一支常駐腳本，而不是臨時貼一段 Python 就算**：臨時片段貼完就散掉，
同一個「這批 .blend 到底裝了什麼」的問題每次都要重寫一遍；這支腳本可以重複跑、
輸出落檔、跨 session 逐輪比對（`.blend` 開起來之後的資料層事實，跟渲染圖長什麼樣
是兩個獨立維度——見 SKILL.md §7.8 收尾非視覺 Probe）。

**用途（全部不需要視覺能力）**：
1. 交付前的資料層檢查：HDRI 有沒有真的接上、玻璃的 Transmission 數值是不是真的
   設到位、有沒有物件的材質槽是空的、母版有沒有忘記隔離（入鏡）。
2. 構圖量化：主體在畫面裡的位置/佔比（`build_template.frame_coverage()`），
   不靠肉眼看圖猜。
3. 逐清單核對：物件名/類型/頂點數/面數/材質/世界包圍盒——Stage C 對照圖譜點名
   缺件時，比肉眼掃渲染圖可靠。

**用法**（兩種都支援；在場景包上層或任意位置執行皆可）：
    blender --background --python scene_pkg/inspect.py -- --json .capybala/artifacts/inspect.json
    blender --background path/to/scene.blend --python scene_pkg/inspect.py -- --json out.json
    blender --background --python scene_pkg/inspect.py -- --blend out/scene.blend --json out.json

**除錯契約（R052-R055）**：本檔是專責除錯檔，函式一律 `debug_` 前綴、可整檔移除
（刪掉這個檔對正式流程零影響），提供三類——
- `debug_get_state()`  結構化狀態 JSON（物件/材質/世界/燈光/相機/量測）
- `debug_get_objects()` 逐物件明細（供 Stage C 對照圖譜逐項核對）
- `debug_show_ids()`   穩定、不截斷的 ID 標籤（`id=005 name=Inst_Lamp_03`）
另含 `debug_check_materials()`/`debug_check_framing()` 兩個資料層斷言型檢查。
"""
import argparse
import json
import os
import sys

import bpy

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for _p in (_HERE, _PARENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:                                    # frame_coverage() 住在 build_template（凍結模組）
    import build_template as T
    _HAS_TEMPLATE = True
except Exception as _exc:               # noqa: BLE001
    print(f"WARNING: inspect: 無法 import build_template（{_exc}）——"
          f"構圖量化檢查將跳過，其餘檢查照常", flush=True)
    T = None
    _HAS_TEMPLATE = False


def _bbox_world(obj):
    """世界座標包圍盒 (min, max)。不能用 obj.location：add_box()/add_cyl() 慣例是建完
    立刻 transform_apply()、物件自身 location 歸零（§14），讀 location 一律得到 0。"""
    from mathutils import Vector
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = [min(c[i] for c in corners) for i in range(3)]
    hi = [max(c[i] for c in corners) for i in range(3)]
    return lo, hi


def debug_get_objects() -> list:
    """逐物件明細：name/type/verts/faces/materials/dims/世界包圍盒。
    供 Stage C 用「實際場景裡有哪些東西」對照圖譜逐項點名缺件。"""
    out = []
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        entry = {"name": obj.name, "type": obj.type,
                 "hide_render": bool(obj.hide_render),
                 "parent": obj.parent.name if obj.parent else None}
        if obj.type == "MESH":
            lo, hi = _bbox_world(obj)
            entry.update({
                "verts": len(obj.data.vertices),
                "faces": len(obj.data.polygons),
                "materials": [m.name for m in obj.data.materials],
                "dims_m": [round(v, 3) for v in obj.dimensions],
                "bbox_min_m": [round(v, 3) for v in lo],
                "bbox_max_m": [round(v, 3) for v in hi],
                "custom_props": {k: str(v) for k, v in obj.items() if k != "_RNA_UI"},
            })
        out.append(entry)
    return out


def debug_get_state() -> dict:
    """結構化狀態（等同 T.main() 的 SCENE_STATE 核心欄位，但任何既有 .blend 都能跑）。"""
    scene = bpy.context.scene
    mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
    world = scene.world
    hdri_nodes = []
    if world is not None and world.use_nodes and world.node_tree is not None:
        hdri_nodes = [n.image.name for n in world.node_tree.nodes
                      if n.type == "TEX_ENVIRONMENT" and n.image is not None]
    state = {
        "blend_loaded": bpy.data.filepath or None,
        "object_count": len(bpy.data.objects),
        "mesh_objects": len(mesh_objs),
        "unique_meshes": sum(1 for m in bpy.data.meshes if m.users > 0),
        "materials": [m.name for m in bpy.data.materials],
        "total_verts": sum(len(o.data.vertices) for o in mesh_objs),
        "total_polys": sum(len(o.data.polygons) for o in mesh_objs),
        "collections": [c.name for c in bpy.data.collections],
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "view_transform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "film_transparent": bool(scene.render.film_transparent),
        "unit_system": scene.unit_settings.system,
        "world_hdri": hdri_nodes,
        "lights": [{"name": o.name, "type": o.data.type,
                    "energy": round(float(getattr(o.data, "energy", 0.0)), 3),
                    "size": round(float(getattr(o.data, "size", 0.0)), 3)}
                   for o in bpy.data.objects if o.type == "LIGHT"],
        "cameras": [{"name": o.name, "type": o.data.type,
                     "lens": round(float(getattr(o.data, "lens", 0.0)), 2),
                     "ortho_scale": round(float(getattr(o.data, "ortho_scale", 0.0)), 3),
                     "dof": bool(o.data.dof.use_dof)}
                    for o in bpy.data.objects if o.type == "CAMERA"],
        "scene_provenance": {k: bpy.context.scene[k] for k in
                             ("bp_skill_version", "bp_metrics", "bp_params", "bp_subject")
                             if k in bpy.context.scene},
    }
    return state


def debug_check_materials() -> dict:
    """資料層材質檢查（渲染圖看不出來的問題）：空材質槽、玻璃類材質的 Transmission 值、
    母版是否忘記隔離（`Mst_*` 且 hide_render=False 就代表會入鏡，§14 違規）。"""
    empty_slots = [o.name for o in bpy.data.objects
                   if o.type == "MESH" and len(o.data.materials) == 0]
    transmission, emissive = {}, {}
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.node_tree is None:
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        t_sock = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
        e_sock = bsdf.inputs.get("Emission Strength")
        if t_sock is not None and float(t_sock.default_value) > 0.0:
            transmission[mat.name] = round(float(t_sock.default_value), 3)
        if e_sock is not None and float(e_sock.default_value) > 0.0:
            emissive[mat.name] = round(float(e_sock.default_value), 3)
    exposed_masters = [o.name for o in bpy.data.objects
                       if o.name.startswith("Mst_") and not o.hide_render]
    issues = []
    if empty_slots:
        issues.append(f"{len(empty_slots)} 個 mesh 物件完全沒有材質：{empty_slots[:8]}")
    if exposed_masters:
        issues.append(f"{len(exposed_masters)} 個母版未隔離（會入鏡，§14）：{exposed_masters[:8]}")
    return {"empty_material_slots": empty_slots, "transmission_materials": transmission,
            "emissive_materials": emissive, "exposed_masters": exposed_masters,
            "issues": issues}


def debug_check_framing(objects: list | None = None) -> dict:
    """構圖量化（需 build_template）：主體在目前相機畫面裡的位置/佔比。
    沒有相機或 build_template 不可用時回傳 `{"skipped": <原因>}`，不中斷。"""
    if not _HAS_TEMPLATE:
        return {"skipped": "build_template 不可用"}
    if bpy.context.scene.camera is None:
        return {"skipped": "場景沒有相機"}
    return T.frame_coverage(objects)


def debug_show_ids() -> list:
    """穩定、不截斷的 ID 標籤（R054）：`id=005 name=Inst_Lamp_03 type=MESH`。
    物件順序按名稱排序，所以同一批檔案重跑會得到同一組 id。"""
    lines = []
    for i, obj in enumerate(sorted(bpy.data.objects, key=lambda o: o.name)):
        lines.append(f"id={i:03d} name={obj.name} type={obj.type}")
    for line in lines:
        print("INSPECT_ID:", line, flush=True)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="scene_pkg inspect: 場景資料層檢視")
    parser.add_argument("--json", dest="json_path", default=None,
                        help="結構化結果輸出 JSON 路徑（.capybala/artifacts/ 底下為宜）")
    parser.add_argument("--blend", dest="blend_path", default=None,
                        help="要開啟的 .blend（也可以用 blender --background <file> 傳）")
    parser.add_argument("--ids", action="store_true", help="額外印出穩定 ID 標籤")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    if args.blend_path:
        bpy.ops.wm.open_mainfile(filepath=args.blend_path)

    result = {
        "state": debug_get_state(),
        "objects": debug_get_objects(),
        "material_checks": debug_check_materials(),
        "framing": debug_check_framing(),
    }
    if args.ids:
        result["id_labels"] = debug_show_ids()

    print("INSPECT_SUMMARY:" + json.dumps({
        "objects": result["state"]["object_count"],
        "materials": len(result["state"]["materials"]),
        "engine": result["state"]["engine"],
        "hdri": result["state"]["world_hdri"],
        "material_issues": result["material_checks"]["issues"],
        "framing": {k: result["framing"].get(k) for k in
                    ("objects", "coverage", "fits", "issues", "skipped")},
    }, ensure_ascii=False), flush=True)

    if args.json_path:
        out_path = os.path.abspath(args.json_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"INSPECT_WRITTEN: {out_path}", flush=True)


if __name__ == "__main__":
    main()
