# KEYWORDS: blender, bpy, polyhaven, hdri, asset, fetch, 抓現成, 家具, 天空, download
# asset_fetch_lib.py — 外部現成資產抓取函數庫（凍結模組，§19）
# 驗證環境：Blender 5.1.2 headless（2026-09-08 probe 實測，直接對 Poly Haven 公開 API）
#
# 定位：任何「非本次任務主體設計」的物件（家具/裝飾/道具/尤其 HDRI 天空）一律抓現成的，
# 不要手調/手建（§7.7「現成優先」公約的落地函數）。Poly Haven 全站 CC0，免署名、免授權、
# 免 API key，直接 HTTP 下載即可——不需要 blender-mcp/GUI session（那是 Tier 2，這裡整條
# 走 Tier 1 無頭 CLI）。
#
# ═══ 實測關鍵事實 ═══
# 1. api.polyhaven.com 完全公開、零金鑰：/assets?type=hdris|models|textures 列清單，
#    /files/{id} 給每個解析度/格式的真實下載網址（dl.polyhaven.org）。
# 2. HDRI 套用：World.node_tree 預設就有 "Background" 節點（5.1 沿用 4.x 行為，只有
#    World.use_nodes 屬性本身噴 6.0 deprecation 警告，不影響功能）。建
#    ShaderNodeTexEnvironment，image=bpy.data.images.load(path)，接到 Background 的
#    Color 輸入即可。實測：套用 aarfontein_dirt_road 2k HDRI 後渲染 LUMA mean=122——
#    證明是真的在打光，不是純黑貼圖。
# 3. 家具/道具模型：Poly Haven 的 "models" 分類真的有家具（ArmChair_01、
#    BarberShopChair_01 等，categories 含 "furniture"）。/files/{id} 的 "blend" 鍵給
#    .blend 檔直接下載網址（1k/2k/4k 三檔，數字是內嵌貼圖解析度，不是面數）。
#    bpy.data.libraries.load(path, link=False) 讀出 data_from.objects 清單，link 進
#    collection 即可（**辨識實際進來的物件請用「附加前後的物件名快照差集」，不要讀
#    with 區塊之後的 data_to/data_from 清單**，見 fetch_polyhaven_model 的註解）——
#    實測 ArmChair_01 附完整幾何（3230 verts，
#    尺寸 0.848×0.766×1.065m，寫實家具比例）。
# 4. 兩者都不需要事先安裝任何 extension/addon——純 HTTP 下載 + bpy 內建 API。
# 5. 只下載 .blend 檔本身不夠：模型內部貼圖路徑是相對於 .blend 自己所在資料夾的
#    "textures/xxx.jpg" 相對路徑，不下載就會在渲染時噴 "Image file ... does not exist"
#    （幾何正常、材質全空，實測踩過）。/files/{id} 回應裡 blend→{res}→blend→include
#    這個 map 就是「相對路徑 → 下載網址」的完整清單，fetch_polyhaven_model() 已內建
#    自動抓取並放到正確的相對位置，手寫其他下載邏輯時要記得比照。
# 6. api.polyhaven.com 會 403 擋掉 Python urllib 預設 User-Agent，dl.polyhaven.org
#    （實際檔案下載）測試中沒出現這個問題，但兩邊都帶同一組 header 更省事更安全。
import bpy
import os
import re
import tempfile
import urllib.request
import json

POLYHAVEN_API = "https://api.polyhaven.com"
POLYHAVEN_DL = "https://dl.polyhaven.org/file/ph-assets"


# api.polyhaven.com 403-blocks the default Python-urllib/x.y User-Agent (實測，2026-09-08) —
# a browser-like UA is required. dl.polyhaven.org (actual file downloads) did not show this
# behavior in testing, but sending the same header everywhere is simpler and harmless.
_UA_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; capybala-blender-skill/1.0)"}


def _http_get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=_UA_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_download(url, dest_path, timeout=60):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers=_UA_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())
    return dest_path


# PNG/JPEG/GIF/WEBP magic-byte signatures — same allowlist/logic as the app's own
# read_image_native (native-coding-tools.ts detectImageMime(); or whatever the equivalent
# vision-input tool is called on your own agent platform), ported here because a bad
# download of this exact shape already bit the app side once (2026-09-10 Famicom reference-image
# incident: a failed fetch silently saved an HTML error page with a .png extension, and the model
# kept re-reading a "reference image" that was actually unreadable garbage). Logo/decal downloads
# are exactly the same risk — a dead link or a blocked hotlink often returns a small HTML page,
# not a 404, so relying on the HTTP status code alone is not enough.
_IMAGE_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"RIFF", "webp"),  # WEBP: RIFF....WEBP — checked loosely below (4-byte prefix only)
)


def _detect_image_kind(data: bytes) -> str | None:
    for magic, kind in _IMAGE_MAGIC:
        if data.startswith(magic):
            if kind == "webp" and data[8:12] != b"WEBP":
                continue
            return kind
    return None


def fetch_reference_image(url: str, dest_path: str, timeout: int = 30) -> str:
    """下載一張參考圖／貼花來源圖到本機（LOGO、品牌標誌、警示符號等），供
    read_image_native（或你的 agent 平台上等價的視覺輸入工具）檢視或
    detail_lib.apply_image_decal() 直接當貼花紋理用——不是為了
    HDRI/家具模型（那兩個用上面的 fetch_hdri()/fetch_polyhaven_model()），是給「上網抓一張
    現成的標誌/圖示」這個更輕量的需求用。

    下載後立刻檢查檔案開頭的 magic bytes，確認真的是圖片而不是偽裝成圖片副檔名的 HTML
    錯誤頁（失效連結/防盜鏈擋下來的網站常常回 200 但內容是一頁 HTML，不是圖片內容）——
    這正是 2026-09-10 紅白機案例的真實根因，同一類失敗這裡直接在下載階段就攔下來，不留到
    read_image_native（或等價的視覺輸入工具）才發現看不懂。驗證失敗時刪除已下載的壞檔並丟例外，不留下垃圾檔案
    讓呼叫端誤以為抓圖成功。"""
    _http_download(url, dest_path, timeout=timeout)
    with open(dest_path, "rb") as f:
        head = f.read(16)
    kind = _detect_image_kind(head)
    if kind is None:
        preview = head[:200].decode("utf-8", errors="replace")
        os.remove(dest_path)
        raise ValueError(
            f"fetch_reference_image({url}) 下載內容不是圖片（開頭不符任何已知圖片格式的 "
            f"magic bytes，很可能是失效連結/防盜鏈回傳的 HTML 錯誤頁）：{preview!r}"
        )
    print(f"[ASSET_FETCH] fetch_reference_image: {url} -> {dest_path}（{kind}，已驗證為真實圖片）")
    return dest_path


def polyhaven_search(query, asset_type="hdris", limit=10):
    """關鍵字搜尋 Poly Haven 資產（本地端過濾，API 本身不支援全文搜尋）。

    Args:
        query: 關鍵字（比對 name/categories/tags，不分大小寫）
        asset_type: "hdris" | "models" | "textures"
        limit: 回傳筆數上限
    Returns:
        list[dict] — 每筆 {"id":..., "name":..., "categories":[...]}
    """
    catalog = _http_get_json(f"{POLYHAVEN_API}/assets?type={asset_type}")
    q = query.lower()
    hits = []
    for asset_id, meta in catalog.items():
        haystack = " ".join([
            asset_id, str(meta.get("name", "")),
            " ".join(meta.get("categories", [])), " ".join(meta.get("tags", [])),
        ]).lower()
        if q in haystack:
            hits.append({"id": asset_id, "name": meta.get("name", asset_id),
                        "categories": meta.get("categories", [])})
        if len(hits) >= limit:
            break
    return hits


def fetch_hdri(asset_id, resolution="2k", cache_dir=None):
    """下載 Poly Haven HDRI 並套用為 World 環境貼圖（取代自己調的 Sky Texture）。

    Args:
        asset_id: Poly Haven HDRI 資產 id（用 polyhaven_search("...", "hdris") 找）
        resolution: "1k"|"2k"|"4k"|"8k"（一般場景 2k 足夠；hero 近景天空可用 4k）
        cache_dir: 快取資料夾；None=系統暫存目錄下 polyhaven_cache/
    Returns:
        bpy.types.World — 已套用好 HDRI 的 world（回傳現有 scene.world）
    """
    files = _http_get_json(f"{POLYHAVEN_API}/files/{asset_id}")
    hdri_files = files.get("hdri", {})
    if resolution not in hdri_files:
        raise ValueError(f"'{asset_id}' 沒有 {resolution} 解析度，可用：{sorted(hdri_files)}")
    url = hdri_files[resolution]["hdr"]["url"]
    cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "polyhaven_cache")
    dest = os.path.join(cache_dir, f"{asset_id}_{resolution}.hdr")
    if not os.path.exists(dest):
        _http_download(url, dest)

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    # 移除舊的 Environment Texture 節點（重複呼叫時不留殘影節點）
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeTexEnvironment":
            nt.nodes.remove(n)
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(dest)
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    print(f"[ASSET_FETCH] fetch_hdri({asset_id}, {resolution}): applied, file={dest}")
    return world


def fetch_polyhaven_model(asset_id, resolution="1k", loc=(0, 0, 0), cache_dir=None):
    """下載 Poly Haven 模型（含家具）並 append 進場景——非主體物件的標準抓取路徑。

    Args:
        asset_id: Poly Haven model 資產 id（用 polyhaven_search("...", "models") 找）
        resolution: "1k"|"2k"|"4k"（貼圖解析度，非面數；場景配角用 1k 通常夠）
        loc: 放置位置
        cache_dir: 快取資料夾；None=系統暫存目錄下 polyhaven_cache/
    Returns:
        list[bpy.types.Object] — 這個 .blend 檔內含的所有物件（通常 1 個，複合資產可能多個）
    """
    files = _http_get_json(f"{POLYHAVEN_API}/files/{asset_id}")
    blend_files = files.get("blend", {})
    if resolution not in blend_files:
        raise ValueError(f"'{asset_id}' 沒有 {resolution} 解析度的 blend 檔，可用：{sorted(blend_files)}")
    entry = blend_files[resolution]["blend"]
    url = entry["url"]
    cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "polyhaven_cache")
    dest = os.path.join(cache_dir, f"{asset_id}_{resolution}.blend")
    if not os.path.exists(dest):
        _http_download(url, dest)
    # The .blend references its textures via paths RELATIVE TO ITSELF (e.g. "textures/xxx.jpg") —
    # downloading only the .blend leaves those unresolved (Cycles logs "Image file ... does not
    # exist" and the model renders without its real material, confirmed live 2026-09-08). The API's
    # "include" map gives every dependent file's relative path + URL; fetch each one next to the
    # .blend so its relative links resolve.
    dest_dir = os.path.dirname(dest)
    for rel_path, dep in (entry.get("include") or {}).items():
        dep_dest = os.path.join(dest_dir, rel_path.replace("/", os.sep))
        if not os.path.exists(dep_dest):
            _http_download(dep["url"], dep_dest)

    # 2026-09-14（內裝案例回報）：with 區塊之後的 data_to.objects 不可當真相——改用附加前後
    # 的物件名快照差集辨識（同 analyze_reference_model 2026-09-08 事故後的做法），並在一個
    # 都沒進來時直接 raise，不讓「回報成功卻沒東西」靜默過關。
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(dest, link=False) as (data_from, data_to):
        data_to.objects = data_from.objects
    new_names = sorted(set(bpy.data.objects.keys()) - before)
    if not new_names:
        raise RuntimeError(
            f"fetch_polyhaven_model({asset_id}, {resolution})：append {dest} 後場景沒有"
            "任何新物件——檔案可能損毀或路徑失效（不要相信回傳清單，要數實際新增的物件）")
    added = []
    for name_new in new_names:
        obj = bpy.data.objects[name_new]
        bpy.context.collection.objects.link(obj)
        added.append(obj)
    if added:
        root = added[0]
        # Some Poly Haven model bundles are composite -- confirmed live 2026-09-08:
        # anthurium_botany_01 links in as 6 separate plant objects, not 1, arranged at small
        # offsets from each other in the SOURCE .blend's own local space. Only translating
        # `root` (as every existing caller does via root.location = loc) left the other 5 behind
        # at those raw source-file coordinates, which landed them scattered on the destination
        # scene's floor near world origin -- looked like stray plant sprigs "growing" out of the
        # floor with no connection to the actual asset that was placed. Parenting every sibling to
        # root with its CURRENT world matrix captured as matrix_parent_inverse means whatever the
        # caller does next to root (location, rotation_euler, scale -- the only three things any
        # existing caller touches) carries the whole bundle along together as one rigid group,
        # exactly like moving a single object would.
        root_matrix = root.matrix_world.copy()
        for sibling in added[1:]:
            sibling.parent = root
            sibling.matrix_parent_inverse = root_matrix.inverted()
        root.location = loc
    print(f"[ASSET_FETCH] fetch_polyhaven_model({asset_id}, {resolution}): "
          f"{len(added)} object(s) — {[o.name for o in added]}")
    return added


# ═══ 參考研究（RAP007，2026-09-08 新增）═══
# 定位：跟上面幾支「抓現成、直接用進最終輸出」完全不同——這支是給「研究真實參考、
# 自己重新建模」用的（RAP007：主體本身也可以抓參考，但只能拿來研究比例/結構，
# 不能把參考檔的幾何本身帶進最終輸出）。函式本身強制落實這條界線：分析完立刻把
# 匯入的物件從場景移除，呼叫端拿到的只有文字/數字摘要，物理上不可能不小心把參考
# 幾何殘留在最終場景裡。
#
# 為什麼不是「找一種 AI 最容易直接讀的原始格式」，而是做這支轉換函式：
# 每一種常見格式都有自己的問題——OBJ 是純文字但稍微複雜的模型就是幾千行頂點座標，
# LLM 直接讀原始內容根本塞不下 context；glTF(.gltf) 是 JSON、場景階層讀得到，
# 但實際頂點/索引資料通常在另外的 base64/外部 .bin，JSON 本身看不到真正的幾何；
# FBX 是 Autodesk 的複雜二進位格式，幾乎不可能直接當文字讀；STL 只有三角網格，
# 沒有物件命名/階層，語意最貧乏。與其要求呼叫端猜「這次的參考檔是哪種格式、能不能
# 直接讀」，不如統一交給 Blender 自己的內建 importer 解析（Blender 5.1.2 實測內建
# 支援 obj/fbx/gltf/glb/stl/ply/usd*/abc，不需要另外裝 extension），我們只需要
# 講「量出來的數字」，不需要呼叫端自己解析任何一種原始格式。
def analyze_reference_model(filepath: str) -> dict:
    """匯入任意常見格式的參考 3D 檔，量測尺寸/階層後立刻從場景移除，只回傳文字/數字
    摘要——供 RAP007「研究參考、自己重新建模」流程使用，絕不能把回傳物件當最終輸出用
    （這支函式本身已經把匯入物件清乾淨，呼叫端根本拿不到殘留的參考幾何）。

    支援格式（依副檔名自動判斷；Blender 5.1.2 內建，未實測 .dae/Collada，那個沒有
    內建 importer，需要另外裝 extension，§19 授權閘門走一輪）：
    .obj .fbx .gltf .glb .stl .ply .usd/.usda/.usdc/.usdz .abc

    座標軸警告（實測發現，非猜測）：OBJ 等格式傳統上是 Y-up 慣例，Blender importer
    預設會自動轉換成 Blender 自己的 Z-up——量出來的 dims_m/center_m 一律是 Blender
    世界座標（Z=高），**不是**參考檔原始作者標記的軸序，看到「高度」以 Blender 的
    Z 軸為準，不要假設回傳的 dims_m[1]（第二個數字）就是原檔案裡的「高」。

    絕對尺寸不可信（實測發現，2026-09-08 東方明珠塔 Sketchfab 參考驗證）：業餘上傳的
    參考檔常常沒有照真實比例建模——實測一個東方明珠塔參考模型（真實高度 468m），量出
    來的 dims_m 是 [1.4, 1.4, 2.687]，是任意的建模單位，跟真實世界公尺完全對不上。
    **這支函式的 dims_m/center_m 只在「同一個參考檔內部」才有意義（各部件之間的相對
    比例），跨到真實世界的絕對尺寸一律以 web 搜尋到的官方/維基資料為準，不要相信參考
    模型的絕對數字**——這正是 RAP007 要求「只研究比例/結構，不直接採信」的原因之一。

    清場涵蓋所有匯入物件、不分類型（2026-09-08 事故修正）：glTF/GLB 匯入除了 MESH
    物件，還會建立 Empty 之類的階層節點（實測東方明珠塔 GLB：36 個 mesh + 3 個
    hierarchy empty，共 39 個新物件）。清場只清 MESH 曾經漏掉那 3 個 empty，導致
    分析完場景不是空的，直接違反 RAP007「絕不留下參考幾何」的界線——現在清場範圍是
    「所有新增物件」，不只是 MESH 子集。

    Returns:
        {"source_file", "format", "part_count", "overall": {"dims_m"},
         "parts": [{"name", "dims_m", "center_m", "material", "vert_count"}, ...]}
        dims_m/center_m 都是世界座標公尺，material 是材質名稱或 None。
    """
    ext = os.path.splitext(filepath)[1].lower()
    before = set(bpy.data.objects[:])

    if ext == ".obj":
        bpy.ops.wm.obj_import(filepath=filepath)
    elif ext == ".fbx":
        bpy.ops.wm.fbx_import(filepath=filepath)
    elif ext in (".gltf", ".glb"):
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=filepath)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=filepath)
    elif ext in (".usd", ".usda", ".usdc", ".usdz"):
        bpy.ops.wm.usd_import(filepath=filepath)
    elif ext == ".abc":
        bpy.ops.wm.alembic_import(filepath=filepath)
    else:
        raise ValueError(f"analyze_reference_model 不支援的格式：{ext}"
                          f"（支援 obj/fbx/gltf/glb/stl/ply/usd*/abc；.dae 需另裝 extension，§19）")

    bpy.context.view_layer.update()
    # 2026-09-08 事故修正：glTF/GLB 匯入除了 MESH 物件，還會建 Empty 之類的階層節點
    # （實測東方明珠塔 GLB：36 個 mesh + 3 個 hierarchy empty，共 39 個新物件）。
    # 摘要統計只看得懂 MESH 的幾何數字，但**清場一定要清掉全部新增物件，不分類型**——
    # 只清 MESH 曾經漏掉那 3 個 empty，導致清場後場景不是空的，直接違反 RAP007
    # 「絕不留下參考幾何」的界線。all_imported 才是清場範圍，imported（MESH 子集）
    # 只用來收集摘要數字。
    all_imported = [o for o in bpy.data.objects if o not in before]
    imported = [o for o in all_imported if o.type == 'MESH']

    parts = []
    all_x, all_y, all_z = [], [], []
    for o in imported:
        verts = [o.matrix_world @ v.co for v in o.data.vertices]
        if not verts:
            continue
        xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
        all_x += xs; all_y += ys; all_z += zs
        parts.append({
            "name": o.name,
            "dims_m": [round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4), round(max(zs) - min(zs), 4)],
            "center_m": [round((max(xs) + min(xs)) / 2, 4), round((max(ys) + min(ys)) / 2, 4), round((max(zs) + min(zs)) / 2, 4)],
            "material": (o.data.materials[0].name if o.data.materials else None),
            "vert_count": len(o.data.vertices),
        })

    overall = None
    if all_x:
        overall = {"dims_m": [round(max(all_x) - min(all_x), 4),
                              round(max(all_y) - min(all_y), 4),
                              round(max(all_z) - min(all_z), 4)]}

    summary = {
        "source_file": os.path.basename(filepath),
        "format": ext,
        "part_count": len(parts),
        "overall": overall,
        "parts": parts,
    }

    # 立即清乾淨：分析完不留任何幾何/節點在場景裡（RAP007 的「研究不留用」界線由這裡
    # 強制執行，不是靠呼叫端自律）。清場範圍是 all_imported（不分物件類型），不是
    # imported（MESH 子集）——見上面 2026-09-08 事故修正說明。
    for o in all_imported:
        data_block = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data_block is not None and data_block.users == 0:
            if isinstance(data_block, bpy.types.Mesh):
                bpy.data.meshes.remove(data_block)
            elif isinstance(data_block, bpy.types.Armature):
                bpy.data.armatures.remove(data_block)
            elif isinstance(data_block, bpy.types.Camera):
                bpy.data.cameras.remove(data_block)
            elif isinstance(data_block, bpy.types.Light):
                bpy.data.lights.remove(data_block)

    print(f"[ASSET_FETCH] analyze_reference_model({summary['source_file']}): "
          f"{summary['part_count']} part(s), overall dims_m={overall['dims_m'] if overall else None} "
          f"— 已清除匯入幾何，僅回傳摘要")
    return summary


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hits = polyhaven_search("dirt road", "hdris", limit=3)
    print("[ASSET_FETCH_SELFTEST] search hits:", hits)
    assert hits, "polyhaven_search 沒找到任何 HDRI，API 可能無法連線"
    world = fetch_hdri(hits[0]["id"], "1k")
    assert world.node_tree.nodes.get("Background") is not None
    print("[ASSET_FETCH_SELFTEST] PASS")
