# KEYWORDS: blender, bpy, nature, tree, terrain, scatter, sapling, ant landscape, geometry nodes, 樹, 地形, 散布, 植栽, 自然
# nature_lib.py — 自然資產函數庫（凍結模組，§18）
# 驗證環境：Blender 5.1.2 headless（Round 13，2026-09-07 probe r13b~r13n 實測）
#
# 三大能力：
#   make_tree(preset, ...)     — Sapling Tree Gen 參數化樹（9 種官方 preset + 輕量化覆蓋）
#   make_terrain(...)          — ANT Landscape 地形（31 種官方 preset）或純 bpy 退路
#   scatter_on_surface(...)    — Geometry Nodes 散布（instance 形態，生產禁 realize）
#
# ═══ 5.1 實測關鍵事實（違反任一條 = 崩潰或靜默失敗）═══
# 1. Sapling/ANT 在 5.1 是 extension（非內建 addon）：模組名
#    bl_ext.blender_org.sapling_tree_gen / bl_ext.blender_org.antlandscape
#    headless 用 addon_utils.enable(mod, default_set=False) 啟用即可。
#    首次使用前需 CLI 安裝（一次性）：
#      blender --background --python-expr "import bpy; bpy.context.preferences.system.use_online_access=True; bpy.ops.wm.save_userpref()"
#      blender --command extension sync
#      blender --command extension install blender_org.sapling_tree_gen
#      blender --command extension install blender_org.antlandscape
# 2. tree_add 參數名與 4.x 教學不同：seed（非 randomSeed）；handleType/chooseSet 是
#    數字字串 enum（'0'/'1'…）。presetName+chooseSet 直調實測不生效 →
#    標準路線 = 讀 preset 檔 dict → 過濾 RNA 屬性 → 展開呼叫（本 lib 內建）。
# 3. tree_add 產 3 物件：leaves(MESH) + tree(CURVE) + treemesh(MESH)。
#    makeMesh=True 才出 treemesh；scatter 前必須 join leaves+treemesh 成單一母版。
# 4. Sapling preset 原生參數極重（weeping_willow leaves=150 → 6 萬+ polys/棵，
#    douglas_fir 4 級 → 15.7 萬葉 verts，單棵 7.7 秒）。散布用一律套 LIGHT_OVERRIDES
#    輕量化（實測 816~2086 polys/棵、0.03~0.1s）；hero 近景樹才可用原生重量。
# 5. landscape_add enum：noise_type 19 種（'blender_texture'/'hetero_terrain'…）、
#    edge_falloff='0'~'3'（字串！非 EDGE_LEVEL）。preset 檔是 op.xxx=val 逐行賦值，
#    解析後過濾 RNA 再展開呼叫。
# 6. Random Value 節點真名 = FunctionNodeRandomValue（GeometryNode* 前綴搜不到）。
#    它的 4 個輸出 socket 同名 "Value"（Vector/Float/Int/Bool）→ 必須用
#    bl_idname=="NodeSocketVector" and enabled 挑選，禁止 outputs["Vector"]。
# 7. 新建 GeometryNodeTree 不含 GroupInput/GroupOutput 節點 → 必須
#    gn.nodes.new("NodeGroupInput") / ("NodeGroupOutput") 手動建。
# 8. GN modifier 掛在 terrain 上時，禁止在 node group 內用 ObjectInfo 引用 terrain
#    自己（循環依賴 → 評估出 0 幾何）。宿主幾何走 Group Input socket 自動流入。
# 9. ★RealizeInstances 記憶體炸彈：density 0.5 × 9025 面 × 數萬 polys 樹 realize
#    → 4.8GB Malloc null → EXCEPTION_ACCESS_VIOLATION 崩潰。生產散布一律
#    realize=False（instance 形態 Cycles 原生渲染，零 depsgraph 展開）；
#    只在「實例數 × 單棵 polys < 50 萬」的驗證場景才允許 realize。
# 10. Texture NOISE 舊屬性（noise_scale/noise_basis）在 5.1 已移除 → Displace+Noise
#     texture 地形路線不可控；純 bpy 退路改用 mathutils.noise.hetero_terrain 直接
#     寫頂點（實測 129×129 grid 0.07s）。
# 11. 同一物件堆兩個 GN 散布 modifier：第二個的 Group Input 收到前一個的 instance 雲
#     → DistributePointsOnFaces 在 instance 上失效 → 評估 0 幾何（self-test 實測）。
#     一個宿主物件只掛一個散布 modifier；需要第二套散布時用獨立宿主。
# 12. ★GN 散布節點組輸出必須用 GeometryNodeJoinGeometry 把「宿主幾何（GroupInput）
#     + instance 雲」合併後再接 GroupOutput——只接 instance 雲時宿主地形被整個
#     「取代」：評估後宿主 0 頂點、渲染全空只剩天空，不報錯（Round 13 端到端實測）。
# 13. GN CollectionInfo 在渲染評估時跳過 hide_render=True 的物件 → 散布源母版
#     不可用 hide_render 隔離，改「遠處停放」（loc x=300+ 之類相機視野外）。
#     這是 §14 母版隔離公約在 GN 散布場景的唯一例外（Round 13 實測）。
# 14. Rock Generator（Extra Mesh Objects extension, 補「石頭」這個 §10.1 環境敘事軸的洞）
#     的 `bpy.ops.mesh.add_mesh_rock` 用 addon_utils.enable() 啟用後**看得到**（在
#     dir(bpy.ops.mesh) 裡）但**呼叫會噴 AttributeError「could not be found」**——這個
#     extension 必須用 `bpy.ops.preferences.addon_enable(module=...)` 才會真的完成
#     operator 註冊（Sapling/ANT 兩者用 addon_utils.enable() 就正常，這是 extra_mesh_objects
#     專屬的行為差異，2026-09-08 實測）。
# 15. ★Sapling treemesh 的樹幹幾何**全部藏在 Skin modifier 裡**——object data 本體
#     0 面（評估後才有 108k+ 面）。join 時 modifier 被吞掉 → 樹幹整棵消失、
#     場景只剩葉子（「白樹」的真正根因，Round 14b probe 實測）。join 前必須
#     modifier_apply(SKIN)；light 模式再 Decimate 壓到 LIGHT_TRUNK_TARGET，
#     材質也要在 join 前逐物件掛（treemesh=樹皮、leaves=葉）。
#
# 匯入慣例：import nature_lib as N（2026-09-09 補上——本檔案先前是唯一沒有明訂
# 別名的 lib，§16.2 單字母變數名禁區的別名清單已列出，避免場景腳本自己即興發明
# 撞名，見便利商店輪事故）。
import bpy
import addon_utils
import ast
import json
import math
import os
import sys
import time

# ═══════════════════════════════════════
# 常數
# ═══════════════════════════════════════

SAPLING_MOD = "bl_ext.blender_org.sapling_tree_gen"
ANT_MOD = "bl_ext.blender_org.antlandscape"
ROCK_MOD = "bl_ext.blender_org.extra_mesh_objects"

# Sapling 官方 9 樹種 preset（隨 extension 安裝）
TREE_PRESETS = (
    "callistemon", "douglas_fir", "japanese_maple", "quaking_aspen",
    "small_maple", "small_pine", "weeping_willow", "white_birch", "willow",
)

# ANT 官方地形 preset（部分常用；完整 31 種見 extension presets 目錄）
TERRAIN_PRESETS = (
    "default", "default_large", "mountain_1", "mountain_2", "canyon", "canyons",
    "cliff", "dunes", "volcano", "mesa", "mounds", "river", "lakes_1", "lakes_2",
    "large_terrain", "rock", "slick_rock", "planet", "voronoi_hills", "billow",
    "ridged", "abstract", "another_noise", "cauliflower_hills", "crystalline",
    "flatstones", "gully", "planet_noise", "techno_cell", "tech_effect",
    "vlnoise_turbulence", "yin_yang",
)

# 散布用輕量化覆蓋（事實 #4：原生 preset 重量會炸 realize/拖慢生成）
LIGHT_OVERRIDES = {
    "levels": 3, "leaves": 18, "bevelRes": 2, "resU": 4,
    "branches": (0, 10, 8, 0), "curveRes": (5, 4, 3, 1),
    "leafScale": 0.25, "leafScaleX": 0.4,
}

# 散布版樹幹 Skin apply 後的面數上限（原生 108k+ 面 ×800 棵 = 災難；
# Decimate ratio 壓到此值，instance 形態下每棵共享同一 mesh 記憶體仍只有一份，
# 但 viewport/depsgraph 評估與 Cycles BVH 建置都吃面數）（事實 #15）
LIGHT_TRUNK_TARGET = 6000

# realize 安全預算（事實 #9）：實例數 × 單棵 polys 上限
REALIZE_POLY_BUDGET = 500_000

_EXTENSION_DIRS_CACHE = {}


# ═══════════════════════════════════════
# 內部工具
# ═══════════════════════════════════════

def _ext_root():
    """extension 安裝根目錄（跨機器解析：APPDATA 標準路徑）"""
    if "root" in _EXTENSION_DIRS_CACHE:
        return _EXTENSION_DIRS_CACHE["root"]
    candidates = [
        os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation",
                     "Blender", "5.1", "extensions", "blender_org"),
        os.path.join(os.environ.get("HOME", ""), ".config", "blender", "5.1",
                     "extensions", "blender_org"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            _EXTENSION_DIRS_CACHE["root"] = c
            return c
    raise FileNotFoundError(
        "找不到 Blender extension 目錄。請先執行一次性安裝（見檔頭註解 #1）：\n"
        "  blender --command extension sync\n"
        "  blender --command extension install blender_org.sapling_tree_gen\n"
        "  blender --command extension install blender_org.antlandscape")


def ensure_extensions():
    """啟用 Sapling + ANT extension（headless 安全；未安裝時 raise 含指引）"""
    enabled = []
    for mod in (SAPLING_MOD, ANT_MOD):
        try:
            addon_utils.enable(mod, default_set=False, persistent=False)
            enabled.append(mod)
        except Exception as e:
            raise RuntimeError(
                f"extension {mod} 啟用失敗：{e}\n"
                "請先執行一次性安裝（見檔頭註解 #1）：\n"
                "  blender --background --python-expr \"import bpy; "
                "bpy.context.preferences.system.use_online_access=True; "
                "bpy.ops.wm.save_userpref()\"\n"
                "  blender --command extension sync\n"
                f"  blender --command extension install blender_org.{mod.split('.')[-1]}")
    _ext_root()  # 確認 preset 目錄可達
    return enabled


def ensure_rock_extension():
    """啟用 Rock Generator（extra_mesh_objects）——事實 #14：必須用
    bpy.ops.preferences.addon_enable()，addon_utils.enable() 啟用後呼叫仍會失敗。"""
    try:
        bpy.ops.preferences.addon_enable(module=ROCK_MOD)
    except Exception as e:
        raise RuntimeError(
            f"extension {ROCK_MOD} 啟用失敗：{e}\n"
            "請先執行一次性安裝：\n"
            "  blender --command extension sync\n"
            "  blender --command extension install blender_org.extra_mesh_objects")
    if not hasattr(bpy.ops.mesh, "add_mesh_rock"):
        raise RuntimeError(f"{ROCK_MOD} 已啟用但 add_mesh_rock 仍未註冊——回報 skill 維護者")


def _load_sapling_preset(name):
    """讀 Sapling preset .py（內容是單行 dict literal）→ dict"""
    if name not in TREE_PRESETS:
        raise ValueError(f"未知樹種 preset '{name}'，可用：{TREE_PRESETS}")
    path = os.path.join(_ext_root(), "sapling_tree_gen", "presets", name + ".py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    return ast.literal_eval(src[src.index("{"):])


def _load_ant_preset(name):
    """讀 ANT preset .py（op.xxx = val 逐行賦值）→ dict（已過濾 RNA 屬性）"""
    if name not in TERRAIN_PRESETS:
        raise ValueError(f"未知地形 preset '{name}'，可用：{TERRAIN_PRESETS}")
    path = os.path.join(_ext_root(), "antlandscape", "presets", "operator",
                        "mesh.landscape_add", name + ".py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    props = set(p.identifier for p in
                bpy.ops.mesh.landscape_add.get_rna_type().properties)
    prm = {}
    for line in src.splitlines():
        line = line.strip()
        if line.startswith("op."):
            k, _, v = line[3:].partition("=")
            k = k.strip()
            if k in props:
                try:
                    prm[k] = ast.literal_eval(v.strip())
                except Exception:
                    pass  # 表達式值（非 literal）跳過，用 operator 預設
    return prm


def _rv_vector_socket(node):
    """FunctionNodeRandomValue 的 Vector 輸出（4 個同名 Value，用 bl_idname 挑）"""
    for s in node.outputs:
        if s.bl_idname == "NodeSocketVector" and s.enabled:
            return s
    raise KeyError("RandomValue 無 enabled Vector 輸出（data_type 未設 FLOAT_VECTOR？）")


def _rv_set_minmax(node, lo, hi):
    vec_ins = [s for s in node.inputs if s.bl_idname == "NodeSocketVector"]
    vec_ins[0].default_value = lo
    vec_ins[1].default_value = hi


# ═══════════════════════════════════════
# 公開 API
# ═══════════════════════════════════════

def make_tree(preset="weeping_willow", seed=0, scale=None, loc=(0, 0, 0),
              name=None, light=True, leaves_extra=None, overrides=None,
              bark_mat=None, leaf_mat=None):
    """Sapling Tree Gen 參數化樹 → 單一 joined MESH 母版（原點=接地中心）。

    Args:
        preset: TREE_PRESETS 之一（9 種官方樹種）
        seed: 隨機種子（同 seed 同形態，可復現）
        scale: 樹高（米）；None=preset 原生 scale
        loc: 母版放置位置（母版建完通常 park 到遠處，由 instance() 放置）
        name: 母版名；None=f"Mst_Tree_{preset}"
        light: True=套 LIGHT_OVERRIDES 輕量化（散布必用，事實 #4）；
               False=原生重量（僅 hero 近景單棵）
        leaves_extra: 額外葉數覆蓋（light 模式下微調葉量）
        overrides: dict，任意 tree_add 參數覆蓋（最後套用，最高優先）
        bark_mat: 樹皮材質（join 前掛到 treemesh；None=不掛，事實 #15）
        leaf_mat: 葉材質（join 前掛到 leaves；None=不掛）
    Returns:
        bpy.types.Object — joined MESH 母版（樹幹+葉单一物件）
    """
    ensure_extensions()
    props = set(p.identifier for p in
                bpy.ops.curve.tree_add.get_rna_type().properties)
    prm = _load_sapling_preset(preset)
    prm = {k: v for k, v in prm.items() if k in props}
    prm["seed"] = seed
    prm["makeMesh"] = True
    prm["showLeaves"] = True
    if scale is not None:
        prm["scale"] = float(scale)
    if light:
        prm.update({k: v for k, v in LIGHT_OVERRIDES.items() if k in props})
        if leaves_extra is not None:
            prm["leaves"] = int(leaves_extra)
    if overrides:
        prm.update({k: v for k, v in overrides.items() if k in props})

    before = set(o.name for o in bpy.data.objects)
    bpy.ops.curve.tree_add(**prm)
    new = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"tree_add({preset}) 未產生 MESH 物件（新物件：{[o.name for o in new]}）")

    # join leaves + treemesh → 單一母版（事實 #3）
    # 注意：CURVE 物件不可參與 join（join 會把它刪除 → 後續迭代 ReferenceError）
    bpy.ops.object.select_all(action="DESELECT")
    # 5.1 實測（Round 14b probe）：treemesh 的樹幹幾何全在 Skin modifier 裡——
    # 未 apply 時 object data 0 面，join 會把 modifier 吞掉 → 樹幹整棵消失
    # （場景只剩葉子 = 「白樹」的真正根因，事實 #15）。apply 後原生 108k+ 面，
    # 散布必過重 → light 模式再 Decimate 壓到 LIGHT_TRUNK_TARGET。
    tm = next((m for m in meshes if "treemesh" in m.name.lower()), None)
    if tm is not None:
        bpy.ops.object.select_all(action="DESELECT")
        tm.select_set(True)
        bpy.context.view_layer.objects.active = tm
        for mod in list(tm.modifiers):
            if mod.type == "SKIN":
                bpy.ops.object.modifier_apply(modifier=mod.name)
        trunk_raw = len(tm.data.polygons)
        if light and trunk_raw > LIGHT_TRUNK_TARGET:
            dm = tm.modifiers.new(name="Decimate", type="DECIMATE")
            dm.ratio = LIGHT_TRUNK_TARGET / trunk_raw
            bpy.ops.object.modifier_apply(modifier=dm.name)
        print(f"[NATURE] make_tree 樹幹 Skin apply: {trunk_raw} → {len(tm.data.polygons)} polys",
              flush=True)

    # 材質分槽改「join 前逐物件掛材質」（Round 14b 修正：base_polys 法實測抓到
    # 0 面 helper 當 base → 整棵樹含樹幹全被塗葉材）。join 會保留各面
    # material_index 並合併材質槽，逐物件掛材最穩。
    if bark_mat or leaf_mat:
        for m in meshes:
            is_leaf = "leave" in m.name.lower() or "leaf" in m.name.lower()
            mat = leaf_mat if is_leaf else bark_mat
            if mat is not None and m.type == "MESH":
                m.data.materials.clear()
                m.data.materials.append(mat)
                for poly in m.data.polygons:
                    poly.material_index = 0
        n_leaf_polys = sum(len(m.data.polygons) for m in meshes
                           if ("leave" in m.name.lower() or "leaf" in m.name.lower()))
        n_bark_polys = sum(len(m.data.polygons) for m in meshes
                           if not ("leave" in m.name.lower() or "leaf" in m.name.lower()))
        print(f"[NATURE] make_tree 材質分槽(join前逐物件): 幹面 {n_bark_polys}, 葉面 {n_leaf_polys} "
              f"(bark={bark_mat.name if bark_mat else None}, leaf={leaf_mat.name if leaf_mat else None})",
              flush=True)
    # base 優先挑真的 treemesh 且面數 >0（防 0 面 helper）
    base = next((m for m in meshes if "treemesh" in m.name.lower() and len(m.data.polygons) > 0),
                max(meshes, key=lambda o: len(o.data.polygons)))
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = base
    if len(meshes) > 1:
        bpy.ops.object.join()
    # 清掉殘留 CURVE（tree 曲線母版，joined mesh 已含幾何）
    for o in list(new):
        try:
            if o.type == "CURVE":
                bpy.data.objects.remove(o, do_unlink=True)
        except ReferenceError:
            pass  # 已被 join 等作業刪除

    base.name = name or f"Mst_Tree_{preset}"
    base.location = loc
    # 原點移到接地中心（樹底 z=min）
    zs = [v.co.z for v in base.data.vertices]
    if zs:
        base.location.z = loc[2] - min(zs)
        bpy.ops.object.select_all(action="DESELECT")
        base.select_set(True)
        bpy.context.view_layer.objects.active = base
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        base.location = loc
    print(f"[NATURE] make_tree({preset}, seed={seed}, light={light}): "
          f"{len(base.data.vertices)} verts, {len(base.data.polygons)} polys")
    return base


def make_terrain(preset="mountain_1", size=60.0, subdivisions=96, loc=(0, 0, 0),
                 name="Env_Terrain", overrides=None):
    """ANT Landscape 地形 → MESH 物件。

    Args:
        preset: TERRAIN_PRESETS 之一（31 種官方地形）
        size: 地形邊長（米，正方形）
        subdivisions: 網格細分（96 → 9216 verts；128+ 注意 scatter 面數）
        overrides: dict，任意 landscape_add 參數覆蓋（amplitude/noise_type…）
    Returns:
        bpy.types.Object — 地形 MESH
    """
    ensure_extensions()
    prm = _load_ant_preset(preset)
    prm.update({"mesh_size": size, "mesh_size_x": size, "mesh_size_y": size,
                "subdivision_x": subdivisions, "subdivision_y": subdivisions})
    if overrides:
        props = set(p.identifier for p in
                    bpy.ops.mesh.landscape_add.get_rna_type().properties)
        prm.update({k: v for k, v in overrides.items() if k in props})

    before = set(o.name for o in bpy.data.objects)
    bpy.ops.mesh.landscape_add(**prm)
    new = [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]
    if not new:
        raise RuntimeError(f"landscape_add({preset}) 未產生 MESH（新物件：{[o.name for o in new]}）")
    # 事實 #16（2026-09-09 補上，使用者實測踩到）：湖泊/河流類 preset（lakes_1/lakes_2/
    # river 實測確認，其餘 preset 通常沒有）landscape_add 除了真正的地形網格，還會
    # 額外殘留一個命名為 "Landscape_plane"（可能帶 .001/.002 後綴）的 4 頂點水平面
    # （z=0 全覆蓋整個 mesh_size 範圍）——舊版直接拿 new[0] 當地形，順序恰好對時看似
    # 正常，但殘留的那個平面從未被處理，留在場景裡當一塊蓋住湖盆/推高整體曝光的
    # 白色大平面（使用者原話：「蓋湖盆+推高曝光」）。改用頂點數挑真地形（残留平面
    # 固定 4 頂點，真地形至少 (subdivisions+1)²，兩者數量級差距懸殊，用頂點數選
    # 不會選錯），其餘新物件一律刪除，不留殘留幾何。
    terr = max(new, key=lambda o: len(o.data.vertices))
    for o in new:
        if o is not terr:
            bpy.data.objects.remove(o, do_unlink=True)
    terr.name = name
    terr.location = loc
    zs = [v.co.z for v in terr.data.vertices]
    print(f"[NATURE] make_terrain({preset}, size={size}, subdiv={subdivisions}): "
          f"{len(terr.data.vertices)} verts, z=[{min(zs):.2f},{max(zs):.2f}]")
    return terr


def make_terrain_pure_bpy(size=60.0, subdivisions=128, amplitude=3.0,
                          noise_scale=0.08, seed=0, loc=(0, 0, 0),
                          name="Env_Terrain"):
    """純 bpy 地形退路（零 extension 依賴，事實 #10）。

    mathutils.noise.hetero_terrain 直接寫頂點。129×129 實測 0.07s。
    適用：ANT extension 不可用 / 需要完全可復現的簡單地形。
    """
    import mathutils
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=subdivisions + 1, y_subdivisions=subdivisions + 1,
        size=size, location=loc)
    g = bpy.context.active_object
    g.name = name
    for v in g.data.vertices:
        n = mathutils.noise.hetero_terrain(
            mathutils.Vector((v.co.x * noise_scale + seed,
                              v.co.y * noise_scale, 0)),
            1.0, 2.0, 8, 0.5, noise_basis="PERLIN_ORIGINAL")
        v.co.z = n * amplitude
    g.data.update()
    zs = [v.co.z for v in g.data.vertices]
    print(f"[NATURE] make_terrain_pure_bpy(size={size}, subdiv={subdivisions}): "
          f"{len(g.data.vertices)} verts, z=[{min(zs):.2f},{max(zs):.2f}]")
    return g


def flatten_pad(terrain, center, pad_z: float, pad_radius: float,
                blend_radius: float) -> None:
    """在地形上挖出一塊平坦建築基地，向外平滑過渡回原始地形（來源：
    雷峰塔參考案例，塔基所在的八角平台就是這樣跟周圍山坡接起來的，2026-09-09 新增）。

    解決的問題：`make_terrain()`/`make_terrain_pure_bpy()` 目前只會對整片地形套
    統一的噪聲/位移，蓋房子的地方一樣凹凸不平——建築物要嘛底部懸空要嘛陷進地形，
    兩種都要事後手動调整地形頂點才能救。這個函式直接原地修改 `terrain` 的頂點：
    - 距離 center 在 `pad_radius` 內：整片拉平到 `pad_z`（建築基地本身）。
    - 在 `pad_radius`~`pad_radius+blend_radius` 之間：`pad_z` 跟原本地形高度線性
      內插過渡（`frac = (dist - pad_radius) / blend_radius`），避免基地邊緣跟
      周圍地形出現一圈斷崖。
    - 超過 `pad_radius+blend_radius`：完全不動，保留原始地形起伏。

    呼叫時機：地形建好之後、建築物 subject_fn 動工之前——先量好建築基地半徑
    （通常是建築本身佔地包圍盒的水平對角線一半，再加一點餘裕），`pad_z` 給
    建築物想要落地的世界 Z（通常 0，或呼叫端自訂的地坪高度）。"""
    for v in terrain.data.vertices:
        dist = math.sqrt((v.co.x - center[0]) ** 2 + (v.co.y - center[1]) ** 2)
        if dist <= pad_radius:
            v.co.z = pad_z
        elif dist <= pad_radius + blend_radius:
            frac = (dist - pad_radius) / blend_radius
            v.co.z = pad_z * (1 - frac) + v.co.z * frac
    terrain.data.update()
    print(f"[NATURE] flatten_pad(center={center}, pad_z={pad_z}, "
          f"pad_radius={pad_radius}, blend_radius={blend_radius}) 完成")


def make_rock(seed=0, scale=1.0, loc=(0, 0, 0), name=None,
              deform=5, rough=2.5, detail=3, overrides=None):
    """Rock Generator（Extra Mesh Objects extension）→ 單一 MESH 母版。

    補 §10.1「環境敘事」要求的「石頭」這個元素——之前 nature_lib 只有樹/地形/散布，
    石頭完全空缺（跟樹木洞是同一個「說了要有卻沒給生成函數」模式）。

    Args:
        seed: 隨機種子（user_seed，同 seed 同形狀）
        scale: 整體縮放（米級）
        loc: 放置位置
        name: 母版名；None=f"Mst_Rock_{seed}"
        deform: 表面變形量（0~10，越高越崎嶇）
        rough: 表面粗糙細節（0~10）
        detail: 細分等級（0~5，越高面數越多；散布用建議 ≤3）
        overrides: dict，任意 add_mesh_rock 參數覆蓋（最後套用，最高優先）
    Returns:
        bpy.types.Object — 石頭 MESH 母版（原點=接地中心）
    """
    ensure_rock_extension()
    prm = dict(
        num_of_rocks=1, use_random_seed=False, user_seed=seed,
        scale_X=(scale * 0.85, scale * 1.15), scale_Y=(scale * 0.85, scale * 1.15),
        scale_Z=(scale * 0.6, scale * 0.9),
        deform=deform, rough=rough, detail=detail, display_detail=min(detail, 2),
        smooth_fac=1.0, smooth_it=2, use_scale_dis=True,
    )
    if overrides:
        prm.update(overrides)

    before = set(o.name for o in bpy.data.objects)
    bpy.ops.mesh.add_mesh_rock(**prm)
    new = [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]
    if not new:
        raise RuntimeError(f"add_mesh_rock(seed={seed}) 未產生 MESH 物件")
    rock = new[0]
    # num_of_rocks=1 只該產生一顆；多餘的（極少數種子下 operator 內部行為）合併避免散落
    for extra in new[1:]:
        bpy.data.objects.remove(extra, do_unlink=True)

    rock.name = name or f"Mst_Rock_{seed}"
    zs = [v.co.z for v in rock.data.vertices]
    rock.location = (loc[0], loc[1], loc[2] - min(zs)) if zs else loc
    print(f"[NATURE] make_rock(seed={seed}, scale={scale}): "
          f"{len(rock.data.vertices)} verts, {len(rock.data.polygons)} polys")
    return rock


def scatter_on_surface(terrain, instances, density=0.1, seed=42,
                       scale_range=(0.8, 1.2), random_yaw=True,
                       name="ScatterGN", realize=False):
    """Geometry Nodes 散布：把 instances（單一物件或物件清單）散布到 terrain 表面。

    ★生產散布 realize 必須 False（事實 #9 記憶體炸彈）——instance 形態由
    Cycles 渲染時原生展開，depsgraph 零記憶體；to_mesh() 讀不到實例屬正常。
    多樹種輪換 = CollectionInfo + Pick Instance（實測 OK）。

    Args:
        terrain: 宿主 MESH 物件（GN modifier 掛它身上；宿主幾何走 Group Input）
        instances: 單一 bpy object 或 object 清單（≥2 自動走 Collection+PickInstance）
        density: 每平方公尺實例數（0.1 ≈ 60m 地形 900 棵；按需求調）
        seed: 散布隨機種子
        scale_range: (min, max) uniform 隨機縮放
        random_yaw: True=每實例隨機繞 Z 旋轉（0~2π）
        realize: True=RealizeInstances（僅驗證用，且自動檢查 REALIZE_POLY_BUDGET）
        name: node group / modifier 名
    Returns:
        (modifier, node_group, dist_node) — dist_node 供事後調 density/seed
    """
    if not isinstance(instances, (list, tuple)):
        instances = [instances]
    instances = [o for o in instances if o is not None]
    if not instances:
        raise ValueError("scatter_on_surface: instances 為空")

    # realize 安全檢查（事實 #9）
    if realize:
        est_instances = density * len(terrain.data.polygons) * 0.01  # 粗估
        max_polys = max(len(o.data.polygons) for o in instances)
        budget_est = est_instances * max_polys
        if budget_est > REALIZE_POLY_BUDGET:
            raise ValueError(
                f"realize=True 預估 {budget_est:.0f} polys 超預算 {REALIZE_POLY_BUDGET}："
                f"density={density} × {len(terrain.data.polygons)} 面 × {max_polys} polys/實例。"
                "請降 density、改 light 樹、或 realize=False（生產標準）。")

    gn = bpy.data.node_groups.new(name, "GeometryNodeTree")
    gn.interface.new_socket("Geometry", socket_type="NodeSocketGeometry", in_out="INPUT")
    gn.interface.new_socket("Geometry", socket_type="NodeSocketGeometry", in_out="OUTPUT")
    gin = gn.nodes.new("NodeGroupInput")    # 事實 #7：手動建
    outn = gn.nodes.new("NodeGroupOutput")

    dist = gn.nodes.new("GeometryNodeDistributePointsOnFaces")
    dist.inputs["Density"].default_value = density
    dist.inputs["Seed"].default_value = seed
    inst = gn.nodes.new("GeometryNodeInstanceOnPoints")

    # instance 來源：單物件 ObjectInfo / 多物件 CollectionInfo+PickInstance
    if len(instances) == 1:
        info = gn.nodes.new("GeometryNodeObjectInfo")
        info.inputs["Object"].default_value = instances[0]
        src_socket = info.outputs["Geometry"]
    else:
        col = bpy.data.collections.new(f"{name}_Col")
        bpy.context.scene.collection.children.link(col)
        for o in instances:
            if o.name not in col.objects:
                col.objects.link(o)
        colinfo = gn.nodes.new("GeometryNodeCollectionInfo")
        colinfo.inputs["Collection"].default_value = col
        # 事實：5.1 CollectionInfo 輸出 socket 名 = "Instances"（非 "Geometry"）
        src_socket = next(s for s in colinfo.outputs
                          if s.bl_idname == "NodeSocketGeometry" and s.enabled)
        inst.inputs["Pick Instance"].default_value = True

    gn.links.new(gin.outputs[0], dist.inputs["Mesh"])   # 事實 #8：宿主幾何走 GroupInput
    gn.links.new(src_socket, inst.inputs["Instance"])
    gn.links.new(dist.outputs["Points"], inst.inputs["Points"])

    tail = inst.outputs["Instances"]
    # 隨機 yaw
    if random_yaw:
        rot = gn.nodes.new("GeometryNodeRotateInstances")
        rv_rot = gn.nodes.new("FunctionNodeRandomValue")   # 事實 #6
        rv_rot.data_type = "FLOAT_VECTOR"
        _rv_set_minmax(rv_rot, (0.0, 0.0, 0.0), (0.0, 0.0, 6.2832))
        gn.links.new(inst.outputs["Instances"], rot.inputs["Instances"])
        gn.links.new(_rv_vector_socket(rv_rot), rot.inputs["Rotation"])
        tail = rot.outputs["Instances"]
    # 隨機縮放
    if scale_range and scale_range != (1.0, 1.0):
        scl = gn.nodes.new("GeometryNodeScaleInstances")
        rv_scl = gn.nodes.new("FunctionNodeRandomValue")
        rv_scl.data_type = "FLOAT_VECTOR"
        lo, hi = scale_range
        _rv_set_minmax(rv_scl, (lo, lo, lo), (hi, hi, hi))
        gn.links.new(tail, scl.inputs["Instances"])
        gn.links.new(_rv_vector_socket(rv_scl), scl.inputs["Scale"])
        tail = scl.outputs["Instances"]
    # realize（僅驗證）
    if realize:
        real = gn.nodes.new("GeometryNodeRealizeInstances")
        gn.links.new(tail, real.inputs["Geometry"])
        tail = real.outputs["Geometry"]

    # ★JoinGeometry：宿主地形幾何 + instance 雲 → 輸出（事實 #12）
    # 缺這步 = 地形被 instance 雲「取代」，評估後宿主 0 頂點、渲染全空
    join = gn.nodes.new("GeometryNodeJoinGeometry")
    gn.links.new(gin.outputs[0], join.inputs["Geometry"])
    gn.links.new(tail, join.inputs["Geometry"])
    gn.links.new(join.outputs["Geometry"], outn.inputs[0])

    mod = terrain.modifiers.new(name, "NODES")
    mod.node_group = gn
    print(f"[NATURE] scatter_on_surface: {len(instances)} 種 × density={density} "
          f"→ {terrain.name}（realize={realize}）")
    return mod, gn, dist


def nature_report():
    """SCENE_STATE 附加段：nature 資產統計（物件數/preset/散布參數）"""
    rep = {"trees": [], "terrains": [], "rocks": [], "scatters": []}
    for o in bpy.data.objects:
        if o.name.startswith("Mst_Tree_"):
            rep["trees"].append({"name": o.name, "polys": len(o.data.polygons),
                                 "verts": len(o.data.vertices)})
        if o.name.startswith("Env_Terrain"):
            rep["terrains"].append({"name": o.name, "polys": len(o.data.polygons)})
        if o.name.startswith("Mst_Rock_"):
            rep["rocks"].append({"name": o.name, "polys": len(o.data.polygons)})
        for m in o.modifiers:
            if m.type == "NODES" and m.node_group and "Scatter" in m.node_group.name:
                dist = next((n for n in m.node_group.nodes
                             if n.bl_idname == "GeometryNodeDistributePointsOnFaces"), None)
                rep["scatters"].append({
                    "host": o.name, "node_group": m.node_group.name,
                    "density": dist.inputs["Density"].default_value if dist else None,
                    "seed": dist.inputs["Seed"].default_value if dist else None})
    return rep


# ═══════════════════════════════════════
# 自检（直接執行本檔時跑煙霧測試）
# ═══════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tree1 = make_tree("weeping_willow", seed=42, scale=8.0, loc=(300, 0, 0))
    tree2 = make_tree("japanese_maple", seed=7, scale=6.0, loc=(340, 0, 0))
    tree3 = make_tree("small_pine", seed=13, scale=7.0, loc=(380, 0, 0))
    rock1 = make_rock(seed=1, scale=1.2, loc=(300, 20, 0))
    rock2 = make_rock(seed=2, scale=0.8, loc=(310, 25, 0))
    assert len(rock1.data.vertices) > 4, "make_rock 產出的幾何太簡陋"
    terr = make_terrain("mountain_1", size=60.0, subdivisions=96)
    mod, gn, dist = scatter_on_surface(
        terr, [tree1, tree2, tree3], density=0.1, seed=42)
    # realize 驗證必須用「獨立」地形：GN modifier 堆疊時，第二個 modifier 的
    # Group Input 收到的是前一個的 instance 雲 → DistributePointsOnFaces 在
    # instance 上失效 → 評估出 0 幾何（Round 13 self-test 實測踩坑）。
    terr2 = make_terrain("mountain_1", size=60.0, subdivisions=96,
                         loc=(0, 100, 0), name="Env_Terrain_Verify")
    mod2, gn2, dist2 = scatter_on_surface(
        terr2, tree1, density=0.004, seed=99, name="ScatterVerify", realize=True)
    dg = bpy.context.evaluated_depsgraph_get()
    m = terr2.evaluated_get(dg).to_mesh()
    verify_polys = len(m.polygons)
    print(f"[NATURE_SELFTEST] verify polys={verify_polys} "
          f"(base={len(terr2.data.polygons)})")
    assert verify_polys > len(terr2.data.polygons), \
        f"realize 驗證失敗：評估 polys {verify_polys} 未超過基底，散布未生效"
    terr2.modifiers.remove(mod2)
    rep = nature_report()
    print("NATURE_SELFTEST_REPORT:" + json.dumps(rep, ensure_ascii=False))
    print(f"[NATURE_SELFTEST] total {round(time.time() - t0, 2)}s — PASS")
