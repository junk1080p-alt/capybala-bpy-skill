# KEYWORDS: blender, bpy, space, 太空, 軌道, starfield, 星空, 星點, sun disc, 日盤, 銀河, 環境貼圖, 真空, 鏡頭光暈
"""太空／軌道場景資產庫（凍結模組，與 mat_lib / nature_lib / road_lib 同層；§0.5）。

真空場景的三條事實決定這裡所有函式的做法：

1. **沒有介質 → 天空不是光源。** 背景亮度不是打光的結果，是 World 底色本身。底色要壓到
   `1e-5` 級——AgX 會把 1e-3 級（例如 0.0035）抬升成一層固定灰幕（量測 54.7/255、std=0），
   星點對比全部被吃掉。`build_template.PRESETS["space"]` 的 `bg_color` 就是按這條校準的。
2. **唯一主光是 SUN**（無限遠平行光、沒有距離衰減）；補光只能走「行星反照／深空環境反射」
   這類極弱光源，能量隨場景尺度用 `diag²` 縮放（`build_template.auto_space_fill()`）。
3. **點狀星在正交相機下會退化。** 環境貼圖的 mip 選擇在 ORTHO 場景把點狀星糊成均勻灰
   （同一張貼圖：PERSP 空景最亮 218、ORTHO 場景變常數 45.7，`dark_pct` 85.5% → 0%）。
   → 點狀星一律用**真幾何**（`make_star_points()`）；環境貼圖只負責低頻的銀河帶輝光
   （`make_star_map()` / `install_star_world()`）。

太陽本身不會入鏡（相機直視太陽＝過曝白板）。要放一顆**只給相機看**的自發光球當日盤
（`make_sun_disc()`）——per-object ray visibility 只留 `camera`，其餘
`diffuse/glossy/transmission/shadow/volume_scatter` 全關，否則它會變成第二顆太陽
（照亮整個場景、在天上投出陰影）。入鏡與否用 `build_template.assert_disc_in_frame()` 驗。

座標公約同 `build_template`：世界座標 Z-up、主體正面朝 -Y；所有函式讀寫世界座標。

用法（scene_pkg 的 geometry.py 內）：

    import space_lib as SP
    SP.make_star_points(count=420, radius=420.0, emissive_mat=mat["Mat_Star"])
    SP.make_sun_disc(direction=SP.sun_direction(18.0, -118.0), distance=260.0,
                     emissive_mat=mat["Mat_SunDisc"])
    T.request_world_hook(lambda: SP.install_star_world(star_map_path, strength=1.0))

**掛勾時序**：World 是 `build_template.build_world()` 在 `main()` 裡建的（而且它會
`bpy.data.worlds.new()` 整個換掉），星空環境貼圖如果在 `subject_fn()` 期間就接上去，
會被 `build_world()` 直接蓋掉 → 一律走 `T.request_world_hook()`，由 `main()` 在
`build_world()` 之後執行。
"""
import bpy
import json
import math
import os
import random
import tempfile

from mathutils import Vector, Euler

SPACE_STARS: list = []   # 幾何星點物件名（Env_ 前綴，main() 的自動審查自動排除）
SPACE_DISCS: list = []   # 相機專用日盤物件名
SPACE_INFO: dict = {}    # 最近一次各函式的參數摘要（寫進 SCENE_STATE 的 space 欄位）


def _log(step: str, msg: str) -> None:
    print(f"SPACE_LOG:[{step}] {msg}", flush=True)


def _default_emissive(name: str, color: tuple, strength: float):
    """自發光材質：優先用 mat_lib.make_emissive()（單一真相源），取不到才本地建一份
    等價節點（Base Color 壓黑，避免自發光物件同時是一顆白色漫射球）。"""
    try:
        import mat_lib as _M
        return _M.make_emissive(name, color=color, strength=strength)
    except Exception:  # noqa: BLE001 - 沒有 mat_lib 時的保底路徑
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            for key in ("Base Color",):
                if key in bsdf.inputs:
                    bsdf.inputs[key].default_value = (0.0, 0.0, 0.0, 1.0)
            for key in ("Emission Color", "Emission"):
                if key in bsdf.inputs:
                    bsdf.inputs[key].default_value = (*color, 1.0)
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = strength
        return mat


def _smooth_noise(rng, height: int, width: int, cells_y: int, cells_x: int):
    """低頻**平滑**雜訊場（由 `cells_y × cells_x` 隨機網格雙線性升採樣而來）。

    銀河帶的明暗塊用這個，**不可**用 `np.repeat` 造常數方塊：16×16 的硬邊方格在
    equirect 貼圖上等於 2.8° 的方格，鋪在大面積天空上、再被鏡面物件反射，就是肉眼
    一眼可見的方格棋盤。雙線性升採樣同時滿足「大尺度有起伏」與「相鄰 cell 連續」。

    **u（經度）方向必須環狀連續**：等距長方投影的左右緣在球面上是同一條經線，粗網格
    的內插要讓最後一欄接回第一欄（`xs` 取到 `cx`、索引取模），否則貼圖在 u=0/1 會留下
    一個跳變——實測帶內那一欄平均跳 4.18/255、最大 10/255，而正常相鄰欄梯度只有
    0.28/255（差 15 倍），鋪到天上就是一條把銀河帶切斷的垂直硬邊。
    """
    import numpy as np
    cy, cx = max(2, int(cells_y)), max(2, int(cells_x))
    coarse = rng.random((cy, cx))
    ys = np.linspace(0.0, cy - 1.0, height)
    xs = np.linspace(0.0, cx, width)        # 到 cx（不是 cx-1）：最後一欄接回第一欄
    y0 = np.floor(ys).astype(np.int64)
    x0 = np.floor(xs).astype(np.int64)
    y1 = np.minimum(y0 + 1, cy - 1)
    xi = x0                                  # 未取模的索引：wx 必須用它算
    x0 = x0 % cx                             # 環狀（經度週期）：最後一欄接回第一欄
    x1 = (xi + 1) % cx
    wy = (ys - y0)[:, None]
    wx = (xs - xi)[None, :]
    top = coarse[y0][:, x0] * (1.0 - wx) + coarse[y0][:, x1] * wx
    bot = coarse[y1][:, x0] * (1.0 - wx) + coarse[y1][:, x1] * wx
    return top * (1.0 - wy) + bot * wy


def sun_direction(elev_deg: float = 18.0, azim_deg: float = -118.0) -> Vector:
    """太陽方向單位向量（世界座標，Z-up）。慣例與 `build_lights()` 的
    `sun_elev_deg`/`sun_azim_deg` 完全一致（azim 0°=+X、90°=+Y、仰角 0°=地平線）。

    **日盤與 SUN 燈必須指向同一個方向**——日盤是純視覺物件、不參與打光，打光方向只由
    preset 的 `sun_elev_deg`/`sun_azim_deg` 決定；兩者不一致時畫面會出現「日盤在天上
    東邊、物體卻被西邊的光照亮」的矛盾。改這裡的數字要同步改 preset（或反過來）。
    """
    e, a = math.radians(elev_deg), math.radians(azim_deg)
    return Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))


def make_sun_disc(direction, distance: float = 260.0, angular_diameter_deg: float = 0.85,
                  center=(0.0, 0.0, 0.0), color=(1.0, 0.96, 0.88), strength: float = 150.0,
                  emissive_mat=None, name: str = "Env_SunDisc",
                  segments: int = 32, rings: int = 16):
    """相機專用日盤（自發光球；per-object ray visibility 只留 `camera`）。

    `direction` 是太陽方向的單位向量（用 `sun_direction()` 產生）；球心放在
    `center + direction * distance`。球半徑由視直徑反算：`r = distance · tan(視直徑/2)`。

    - **視直徑 0.85° 是校準值**：真實太陽視直徑 0.526°，但太空場景的日盤要當「視覺錨點」
      讀得出來，0.85° 在 68mm 鏡頭下是乾淨的小圓盤；再大（實測 1.15°）就會暈成一顆
      饅頭、失去「點光源」的讀感。
    - `distance` 不影響畫面大小（視角才是），只影響深度層與 `clip_end` 需求——
      **務必確認相機 `clip_end > distance`**，否則日盤落在遠裁切面外、整顆消失，
      畫面只剩星星（`build_camera()` 的 clip_end = `max(1000, 對焦距離×4)`，300m 內安全）。
    - `strength` 是自發光強度（線性輻射亮度），同時是鏡頭光暈的門檻下界參考：
      日盤 150、星點約 26 → `setup_lens_flare(threshold=…)` 夾在兩者之間（實測 40–60）。

    ray visibility 六項：只留 camera=True，其餘五項 False。這是「出現在畫面裡但不參與
    任何光照計算」的唯一做法。名稱帶 `Env_` 前綴 → `main()` 的自動懸空/穿模/構圖審查
    自動排除（它本來就懸在太空、也不屬「主體」桶）；入鏡與否另外用
    `assert_disc_in_frame()` 驗，兩者是獨立的檢查維度。
    """
    d = Vector(direction)
    if d.length < 1e-9:
        raise ValueError("make_sun_disc: direction 不可為零向量")
    d = d.normalized()
    radius = distance * math.tan(math.radians(angular_diameter_deg) * 0.5)
    loc = Vector(center) + d * distance
    try:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                             radius=radius, location=tuple(loc))
    except TypeError:  # 舊版 operator 參數名差異的保底
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, rings=rings,
                                             radius=radius, location=tuple(loc))
    obj = bpy.context.active_object
    obj.name = name
    try:
        bpy.ops.object.shade_smooth()
    except Exception:  # noqa: BLE001 - 著色平滑失敗不影響可用性
        pass
    mat = emissive_mat or _default_emissive("Mat_SunDisc", color, strength)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    # per-object ray visibility（Cycles）：只給相機看
    for attr, val in (("visible_camera", True), ("visible_diffuse", False),
                      ("visible_glossy", False), ("visible_transmission", False),
                      ("visible_shadow", False), ("visible_volume_scatter", False)):
        try:
            setattr(obj, attr, val)
        except (AttributeError, TypeError) as exc:  # noqa: BLE001
            _log("sun_disc", f"WARNING: {attr} 設定失敗（{exc}）——日盤可能變成第二顆太陽")
    SPACE_DISCS.append(obj.name)
    SPACE_INFO["sun_disc"] = {"name": obj.name, "distance": distance,
                              "radius": round(radius, 4),
                              "angular_diameter_deg": angular_diameter_deg,
                              "strength": strength,
                              "direction": [round(v, 4) for v in d]}
    _log("sun_disc", f"{obj.name} 距離={distance}m 半徑={radius:.4f}m "
                     f"視直徑={angular_diameter_deg}° 自發光={strength}（ray visibility 只留 camera）")
    return obj


def make_star_points(count: int = 420, radius: float = 420.0, center=(0.0, 0.0, 0.0),
                     size_range=(0.12, 0.55), color=(1.0, 0.98, 0.94),
                     strength: float = 26.0, seed: int = 7, emissive_mat=None,
                     avoid_dirs=None, avoid_deg: float = 14.0, prefix: str = "Env_Star",
                     subdivisions: int = 2) -> list:
    """真幾何星點（等向散布在一層球殼上）——點狀星的**唯一可靠做法**（正交相機照樣成立，
    見模組檔頭第 3 條）。

    共用一份 icosphere mesh data（母版＋實例，§14），只有 location/scale 逐顆不同 →
    400 顆星只有 1 份 mesh、開銷可忽略。物件名帶 `Env_` 前綴 → `main()` 的自動穿模/
    懸空/構圖審查自動排除。

    - `size_range`：單顆星球的半徑範圍（公尺）。實際畫面上的星點大小 ≈
      `2·size/distance`（弧度）；`radius=420`、`size=0.12…0.55` → 0.03°–0.15° ≈ 1–5 px
      （1920 寬、~54° 水平視角），是清楚的點而不是糊塊。
    - `subdivisions`：共用 mesh 的細分級數。**1 級只有 20 面，投影出來是多邊形剪影**
      ——星點在畫面上拉到 5–7 px 時，肉眼直接讀成「一顆小方塊／小石頭」。預設 2（80 面）
      在 ≤8 px 下輪廓已經是圓的；hero 鏡頭或刻意放大的亮星再上 3。全部實例共用同一份
      mesh data，升級細分只增加**那一份** mesh 的面數，不會乘上星點數量。
    - `avoid_dirs`／`avoid_deg`：要避開的方向清單（通常是太陽方向）。星點疊在日盤附近
      會被日盤的亮度吃掉，也可能落進鏡頭光暈的鬼影鏈裡；開一個圓錐把那個範圍濾掉。
    - `strength`：自發光強度。太低在 AgX 下變成灰點、太高會連星點都觸發光暈
      （門檻區間見 `setup_lens_flare()`；實測星點峰值約 36、日盤 150）。

    回傳建立的物件清單。
    """
    rng = random.Random(seed)
    avoid = [Vector(v).normalized() for v in (avoid_dirs or [])]
    cos_avoid = math.cos(math.radians(avoid_deg))
    mat = emissive_mat or _default_emissive("Mat_Star", color, strength)
    center_v = Vector(center)
    made: list = []
    base = None
    tries = 0
    while len(made) < count and tries < count * 40:
        tries += 1
        z = rng.uniform(-1.0, 1.0)
        phi = rng.uniform(0.0, 2.0 * math.pi)
        r_xy = math.sqrt(max(0.0, 1.0 - z * z))
        d = Vector((r_xy * math.cos(phi), r_xy * math.sin(phi), z))
        if any(d.dot(a) > cos_avoid for a in avoid):
            continue
        dist = radius * rng.uniform(0.9, 1.1)
        size = size_range[0] * (size_range[1] / size_range[0]) ** rng.random()
        if base is None:
            try:
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0)
            except TypeError:  # 舊版參數名保底
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, size=1.0)
            base = bpy.context.active_object
            base.data.materials.clear()
            base.data.materials.append(mat)
            obj = base
        else:
            obj = base.copy()          # 共享 mesh data（§14 母版=1 原則）
            bpy.context.collection.objects.link(obj)
        obj.name = f"{prefix}_{len(made):04d}"
        obj.scale = (size, size, size)
        obj.location = tuple(center_v + d * dist)
        SPACE_STARS.append(obj.name)
        made.append(obj)
    if len(made) < count:
        _log("star_points", f"WARNING: 只放下 {len(made)}/{count} 顆星（avoid 圓錐太大？）")
    SPACE_INFO["star_points"] = {"count": len(made), "radius": radius,
                                 "size_range": list(size_range), "strength": strength,
                                 "seed": seed, "shared_mesh": 1}
    _log("star_points", f"{len(made)} 顆星（半徑 {radius}m，尺寸 {size_range}，"
                        f"自發光 {strength}，共用 1 份 mesh，avoid_deg={avoid_deg}）")
    return made


def _fail(step: str, msg: str):
    """硬性失敗：印出可據以行動的訊息並以非零碼結束（同 build_template.fail() 的慣例）。"""
    print(f"SPACE_FAIL:[{step}] {msg}", flush=True)
    raise SystemExit(1)


def _ndc(cam, direction, dist: float = 100.0):
    """把「世界方向」投影進相機 NDC（回傳 (x, y, z)，x/y 在 0–1、z 是深度）。

    針孔投影下 NDC 只取決於方向、與距離無關，所以固定 `dist` 即可；用
    `world_to_camera_view` 而不是自己算 FOV 三角函數，是為了同時涵蓋 PERSP/ORTHO、
    sensor_fit 與畫幅比例（解析式要分好幾種情況，這裡一次解決）。
    """
    from bpy_extras import object_utils
    loc = cam.matrix_world.translation
    p = loc + Vector(direction).normalized() * dist
    return object_utils.world_to_camera_view(bpy.context.scene, cam, p)


def frame_elev_range(cam=None, step_deg: float = 0.2):
    """數值掃描：回傳相機畫面（沿相機自身方位角的那條垂直中線）涵蓋的仰角範圍。

    回傳 `(lo_deg, hi_deg)`；場景沒有相機、或畫面內掃不到任何方向時回 `(None, None)`。
    **已知簡化**：只掃垂直中線——透視相機左右兩側同一仰角的方向會略微偏離這個區間
    （水平視角越大偏越多）。用途是判斷「帶會不會被地平線／畫面上下緣切斷」，這個精度
    足夠；要更嚴謹得另外沿水平方向掃描。
    """
    scene = bpy.context.scene
    cam = cam or scene.camera
    if cam is None:
        return (None, None)
    bpy.context.view_layer.update()
    forward = cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    azim = math.degrees(math.atan2(forward.y, forward.x))
    lo = hi = None
    e = -89.0
    while e <= 89.0:
        co = _ndc(cam, sun_direction(e, azim))
        if co.z > 0.0 and 0.0 <= co.y <= 1.0:
            if lo is None:
                lo = e
            hi = e
        e += step_deg
    return (lo, hi)


def band_span(band_center_deg: float, band_width_deg: float, k: float = 2.5):
    """銀河帶的「可見仰角範圍」＝中心 ± k·σ（`make_star_map()` 的高斯 σ = band_width_deg）。

    k 預設 2.5 → 高斯尾端只剩峰值 4.4%（肉眼等同消失），用這個範圍判斷「帶有沒有被切」。
    """
    return (band_center_deg - k * band_width_deg, band_center_deg + k * band_width_deg)


def _ground_camera_visible(name: str = "Ground") -> bool:
    """地面在畫面上看不看得見——「地平線切斷銀河帶」這個缺陷只有地面看得見時才成立。

    `visible_camera=False`（`build_template.set_ground_void()` 的預設模式）或材質
    Alpha≈0（同一支的 alpha 模式）都算看不見；場景裡沒有地面物件時回 False。
    """
    obj = bpy.data.objects.get(name)
    if obj is None:
        return False
    if not getattr(obj, "visible_camera", True):
        return False
    for m in getattr(obj.data, "materials", []):
        if m is None or not m.use_nodes:
            continue
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None and "Alpha" in bsdf.inputs:
            if bsdf.inputs["Alpha"].default_value <= 0.001:
                return False
    return True


def make_star_map(path: str, width: int = 2048, height: int = 1024,
                  band_glow: float = 0.05, band_center_deg: float | str = "auto",
                  band_width_deg: float = 16.0, band_modulation: float = 0.45,
                  star_count: int = 0, star_brightness: float = 2.5,
                  star_radius_px: float = 1.4, seed: int = 11) -> str:
    """程序化 equirect 星空圖（PNG）：低頻**銀河帶**輝光 ＋ 少量點狀星。

    用途只有一個——**低頻的銀河帶**（大面積、低對比、有明暗塊）。點狀星**預設不畫**
    （`star_count=0`）：貼圖上的星斑只是固定幾個 texel 的亮塊，天空一大片被放大之後讀成
    方點，正交相機下還會被 mip 選擇糊掉（檔頭第 3 條）——銳利星點一律交給
    `make_star_points()` 的真幾何。`star_count>0` 只在「PERSP 遠景、幾何星點來不及鋪滿天」
    時當補丁用，且要配 `star_radius_px≥1.5` 才不會讀成方點。

    實作：等距長方投影（equirect）經緯網格上算「高斯帶 × 縱向調變」的輝光，再疊兩層
    **平滑**低頻雜訊（`_smooth_noise()`，不是方塊遮罩）製造明暗塊。**決定性**（固定 seed），
    重跑結果逐位元相同——同 §10.3 的 `random.seed` 公約，CALIB 與正式渲染不會長得不一樣。

    `band_glow` 是帶的峰值亮度（線性）。這是**背景色**不是光源：環境貼圖的整體增益由
    `install_star_world(strength=…)` 再乘一次，兩者相乘才是畫面上的背景亮度。

    回傳寫出的 PNG 路徑。呼叫端負責把它交給 `install_star_world()`。
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    if isinstance(band_center_deg, str):
        # "auto"：銀河帶自動取景——把帶塞進畫面、並在地面看得見時抬到地平線之上。
        # 需要相機，所以呼叫端必須在 build_camera() 之後才產生貼圖（標準做法是走
        # build_template.request_world_hook()，那支已改到相機就位之後才執行）。
        if band_center_deg != "auto":
            _fail("star_map", f"band_center_deg 只接受數值或 'auto'，收到 {band_center_deg!r}")
        band_center_deg, _fit = auto_band_center(band_width_deg=band_width_deg, k=2.5)
        _log("star_map", f"band_center_deg='auto' → {band_center_deg}°（取景資訊 {_fit}）")
    v = (np.arange(height, dtype=np.float64) + 0.5) / height          # 0(南)–1(北)
    u = (np.arange(width, dtype=np.float64) + 0.5) / width            # 0–1 經度
    lat = (v - 0.5) * math.pi                                          # 緯度 -pi/2..pi/2
    band = np.exp(-0.5 * ((lat - math.radians(band_center_deg))
                          / math.radians(band_width_deg)) ** 2)
    # 帶內不均勻（真實銀河帶有明暗塊與暗塵帶，不是一條均勻的亮帶）
    mod = (1.0 - band_modulation) + band_modulation * (
        np.sin(u * 2.0 * math.pi * 3.0 + 0.7) ** 2)
    glow = np.outer(band * band_glow, mod)                             # (H, W)
    # 帶內明暗塊：兩層**平滑**低頻雜訊（大尺度起伏 ＋ 中尺度紋理）。
    # 一律走 _smooth_noise()，不可用 np.repeat 造方塊遮罩（見該函式 docstring）。
    coarse = _smooth_noise(rng, height, width, max(3, height // 24), max(4, width // 24))
    fine = _smooth_noise(rng, height, width, max(6, height // 8), max(8, width // 8))
    glow = glow * (0.55 + 0.90 * coarse) * (0.85 + 0.30 * fine)
    # 點狀星（在貼圖上只是小高斯斑；銳利星點由 make_star_points() 負責）
    r = int(max(1, round(star_radius_px)))
    ys, xs = np.mgrid[-r:r + 1, -r:r + 1]
    falloff = np.exp(-(xs ** 2 + ys ** 2) / (2.0 * max(0.35, star_radius_px) ** 2))
    for _ in range(int(star_count)):
        cy = int(rng.integers(0, height))
        cx = int(rng.integers(0, width))
        mag = float(star_brightness) * (0.25 + 0.75 * float(rng.random()) ** 3)
        y0, y1 = max(0, cy - r), min(height, cy + r + 1)
        x0, x1 = max(0, cx - r), min(width, cx + r + 1)
        fy0, fy1 = y0 - (cy - r), y1 - (cy - r)
        fx0, fx1 = x0 - (cx - r), x1 - (cx - r)
        glow[y0:y1, x0:x1] += mag * falloff[fy0:fy1, fx0:fx1]
    rgba = np.empty((height, width, 4), dtype=np.float32)
    rgba[..., 0] = glow
    rgba[..., 1] = glow
    rgba[..., 2] = glow * 1.06       # 極輕微的冷偏（星光是偏藍的多，但不要調成藍色圖）
    rgba[..., 3] = 1.0
    img = bpy.data.images.new("StarMap", width=width, height=height,
                              alpha=True, float_buffer=True)
    img.pixels.foreach_set(rgba.ravel())
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    saved = os.path.abspath(path)
    bpy.data.images.remove(img)      # 省一份 2M 像素緩衝；環境貼圖另外 load 一次
    SPACE_INFO["star_map"] = {"path": saved, "size": [width, height],
                              "band_glow": band_glow, "star_count": int(star_count),
                              # 帶參數是 audit_band_framing() 的預設輸入來源（呼叫端不給
                              # 參數時讀這裡）——不記下來，取景稽核就只能靠人記得傳值。
                              "band_center_deg": round(float(band_center_deg), 3),
                              "band_width_deg": round(float(band_width_deg), 3),
                              "peak": round(float(glow.max()), 4)}
    _log("star_map", f"{saved} {width}x{height} 帶峰值={float(glow.max()):.4f} "
                     f"（低頻銀河帶；銳利星點走 make_star_points()）")
    return saved


def install_star_world(star_map_path: str, strength: float = 1.0,
                       rotation_deg: float = 0.0):
    """把星空圖接上 World 的 `Background.Color`（環境貼圖，EQUIRECTANGULAR）。

    **前提**：World 已存在（`build_world()` 跑過）——本函式只改既有的 World 節點樹，
    不新建 World；因此必須在 `build_template.main()` 的 `build_world()` 之後執行，
    專案內的標準做法是 `T.request_world_hook(...)`（見模組檔頭）。

    `strength` 疊在 `Background.Strength` 上（真空場景維持 1.0 即可，背景亮度由貼圖
    本身的數值決定——`bg_color` 的 1e-5 是「完全不掛貼圖」時的天光底；掛了星空圖之後，
    貼圖的暗部（≈0）就接手扮演那個角色）。
    `rotation_deg` 繞世界 Z 軸轉貼圖，用來把銀河帶擺到鏡頭看得到的位置。
    """
    if not os.path.isfile(star_map_path):
        raise FileNotFoundError(f"install_star_world: 找不到星空圖 {star_map_path}")
    world = bpy.context.scene.world
    if world is None or not world.use_nodes:
        raise RuntimeError("install_star_world: 需要已有 world.use_nodes=True 的 World"
                          "（build_world() 或 request_world_hook() 之後才呼叫）")
    wnt = world.node_tree
    bg = next((n for n in wnt.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        raise RuntimeError("install_star_world: World 節點樹找不到 Background 節點")
    tex = wnt.nodes.new("ShaderNodeTexEnvironment")
    tex.image = bpy.data.images.load(star_map_path)
    tex.projection = "EQUIRECTANGULAR"
    tex.interpolation = "Linear"    # 明確指定：Closest 會把貼圖 texel 放大成硬邊方塊
    if abs(rotation_deg) > 1e-9:
        coord = wnt.nodes.new("ShaderNodeTexCoord")
        mapping = wnt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(rotation_deg))
        wnt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
        wnt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    wnt.links.new(tex.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    SPACE_INFO["star_world"] = {"path": star_map_path, "strength": strength,
                                "rotation_deg": rotation_deg,
                                "image": tex.image.name}
    _log("star_world", f"星空環境貼圖接上（{os.path.basename(star_map_path)}，"
                       f"strength={strength}，rot={rotation_deg}°）")
    return tex


def auto_band_center(cam=None, band_width_deg: float = 16.0, k: float = 2.5,
                     frame_margin_deg: float = 1.0, horizon_deg: float = 0.0):
    """回傳 `(center_deg, info)`：銀河帶中心仰角的自動取景建議值。

    目的是讓「帶的可見範圍（中心 ± k·σ）」完整落在畫面內，而地面看得見時再抬到地平線
    之上——帶被地平線或畫面邊緣硬切斷，是星空構圖最常見的醜畫面。
    `make_star_map(band_center_deg="auto")` 內部就是呼叫這支。

    演算法：掃出畫面涵蓋的仰角範圍 `[lo_f, hi_f]`，扣掉帶半寬 `k·σ` 與邊界留白得到允許
    區間；地面可見時把下界再抬到「地平線 + 留白 + 半寬」。預設取畫面正中（帶在畫面裡最
    完整），被允許區間夾住。`info["fits"]=False` 表示帶比畫面還高，任何中心值都會被框邊
    切到——此時唯一的解法是縮小 `band_width_deg` 或換更廣的鏡頭。
    """
    scene = bpy.context.scene
    cam = cam or scene.camera
    half = k * band_width_deg
    info = {"camera": getattr(cam, "name", None), "band_width_deg": band_width_deg,
            "k": k, "half_span_deg": round(half, 2)}
    if cam is None:
        info.update({"reason": "場景沒有相機（需在 build_camera() 之後）→ 沿用預設中心 8.0°",
                     "fits": None})
        return 8.0, info
    lo_f, hi_f = frame_elev_range(cam=cam)
    info["frame_span"] = [lo_f, hi_f]
    ground_visible = _ground_camera_visible()
    info["ground_visible"] = ground_visible
    if lo_f is None:
        info.update({"reason": "畫面內掃不到任何方向 → 沿用預設中心 8.0°", "fits": None})
        return 8.0, info
    lo_ok = lo_f + frame_margin_deg + half
    hi_ok = hi_f - frame_margin_deg - half
    if ground_visible:
        lo_ok = max(lo_ok, horizon_deg + frame_margin_deg + half)
    fits = lo_ok <= hi_ok
    center = max(lo_ok, min(hi_ok, 0.5 * (lo_f + hi_f))) if fits else lo_ok
    info.update({"fits": bool(fits), "allowed_center_range": [round(lo_ok, 2), round(hi_ok, 2)],
                 "center_deg": round(center, 2)})
    if not fits:
        info["warning"] = (f"帶（半寬 {half:.1f}°）比畫面高度（{hi_f - lo_f:.1f}°）還大，"
                           "任何中心值都會被框邊裁到——縮小 band_width_deg 或改更廣的鏡頭")
    _log("band", f"自動取景中心 {center:.2f}°（畫面 {lo_f:.1f}~{hi_f:.1f}°，"
                 f"地面可見={ground_visible}，fits={fits}）")
    return round(center, 2), info


def audit_band_framing(cam=None, band_center_deg=None, band_width_deg=None, k: float = 2.5,
                       horizon_deg: float = 0.0, residual_threshold: float = 0.05,
                       hard: bool = False) -> dict:
    """銀河帶取景稽核：帶有沒有被「看得見的地平線」硬切斷、或被畫面上下緣裁掉。

    不給參數時用 `make_star_map()` 記在 `space_report()` 裡的值（最近一次產生的星空圖）。

    判準分兩級：
    - **blocking（硬性）**：地面在畫面上看得見（`_ground_camera_visible()`）、帶下緣低於
      地平線、而地平線處的帶亮度仍有 >`residual_threshold` 峰值（預設 5%）——一條平直
      硬邊穿過雲狀帶，最難看的一種。`hard=True` 時直接 exit 1。
    - **notes（提示）**：帶的可見範圍超出畫面上下緣。大尺度雲狀帶在特寫鏡頭被框邊裁切
      本來就自然，只列出不擋。

    `suggested_center_deg` 是修正後的建議中心值（`auto_band_center()` 的結果）。
    """
    src = SPACE_INFO.get("star_map", {})
    if band_center_deg is None:
        band_center_deg = src.get("band_center_deg")
    if band_width_deg is None:
        band_width_deg = src.get("band_width_deg")
    if band_center_deg is None or band_width_deg is None:
        _fail("band", "audit_band_framing: 沒有帶參數可用——先呼叫 make_star_map()，"
                      "或顯式給 band_center_deg / band_width_deg")
    scene = bpy.context.scene
    cam = cam or scene.camera
    if cam is None:
        _fail("band", "audit_band_framing: 場景沒有相機（需在 build_camera() 之後呼叫）")
    lo_f, hi_f = frame_elev_range(cam=cam)
    lo_b, hi_b = band_span(band_center_deg, band_width_deg, k)
    ground_visible = _ground_camera_visible()
    residual = math.exp(-0.5 * ((horizon_deg - band_center_deg)
                                / max(1e-6, band_width_deg)) ** 2)
    blocking, notes = [], []
    if ground_visible and lo_b < horizon_deg and residual > residual_threshold:
        blocking.append(
            f"銀河帶被地平線硬切斷：帶下緣 {lo_b:.1f}° 低於地平線 {horizon_deg:.1f}°，而地平線處"
            f"仍有 {residual * 100:.0f}% 帶亮度 → 一條平直硬邊穿過雲狀帶。"
            f"解法：band_center_deg 抬到 ≥ {horizon_deg + k * band_width_deg:.1f}°，"
            "或呼叫 build_template.set_ground_void() 讓地面不入鏡")
    if hi_f is not None:
        if hi_b > hi_f:
            notes.append(f"帶上緣 {hi_b:.1f}° 超出畫面上緣 {hi_f:.1f}°"
                         "（提示：大尺度雲狀帶在特寫鏡頭被框邊裁切是自然的，不擋）")
        if lo_b < lo_f:
            notes.append(f"帶下緣 {lo_b:.1f}° 低於畫面下緣 {lo_f:.1f}°（提示：同上）")
    suggested, fit_info = auto_band_center(cam=cam, band_width_deg=band_width_deg, k=k)
    result = {"camera": getattr(cam, "name", None), "band_center_deg": band_center_deg,
              "band_width_deg": band_width_deg, "k": k,
              "band_span": [round(lo_b, 2), round(hi_b, 2)], "frame_span": [lo_f, hi_f],
              "ground_visible": ground_visible, "residual_at_horizon": round(residual, 4),
              "blocking": blocking, "notes": notes, "issues": blocking + notes,
              "suggested_center_deg": suggested, "fit_info": fit_info, "ok": not blocking}
    _log("band", f"取景稽核：帶 {lo_b:.1f}~{hi_b:.1f}°、畫面 {lo_f}~{hi_f}°、"
                 f"地面可見={ground_visible}、blocking={len(blocking)}、notes={len(notes)}")
    if hard and blocking:
        _fail("band", "；".join(blocking))
    return result


def space_report() -> dict:
    """SCENE_STATE 附加段（同 nature_lib.nature_report() 的定位）：星點/日盤/星空圖統計
    ——數值 ground truth，無視覺時用它回答「星星到底放了幾顆、日盤在哪」。"""
    return {"stars": len(SPACE_STARS), "discs": list(SPACE_DISCS), **SPACE_INFO}


def selftest() -> dict:
    """不需外部檔案的自我測試：星空圖產生／世界貼圖接線／星點散布／日盤 ray visibility。
    以 `blender --background --python space_lib.py -- --selftest` 執行。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SPACE_STARS.clear(); SPACE_DISCS.clear(); SPACE_INFO.clear()
    out = os.path.join(tempfile.gettempdir(), "space_lib_selftest")
    checks = {}
    path = make_star_map(os.path.join(out, "star_map.png"), width=512, height=256,
                         star_count=120, seed=3)
    checks["star_map_written"] = os.path.isfile(path) and os.path.getsize(path) > 1000
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    tex = install_star_world(path, rotation_deg=25.0)
    checks["env_linked"] = bool(next(n for n in world.node_tree.nodes
                                     if n.type == "BACKGROUND").inputs["Color"].links)
    stars = make_star_points(count=24, radius=100.0, seed=5)
    checks["star_count"] = len(stars) == 24 and len(SPACE_STARS) == 24
    checks["star_shared_mesh"] = len({o.data.name for o in stars}) == 1
    disc = make_sun_disc(direction=sun_direction(20.0, -120.0), distance=100.0, center=(0, 0, 0))
    checks["disc_radius"] = abs(disc.dimensions.x / 2.0
                                - 100.0 * math.tan(math.radians(0.85) / 2)) < 1e-3
    checks["disc_camera_only"] = (disc.visible_camera is True
                                  and disc.visible_diffuse is False
                                  and disc.visible_glossy is False
                                  and disc.visible_transmission is False
                                  and disc.visible_shadow is False)
    checks["report_keys"] = {"stars", "discs", "star_map", "sun_disc"} <= set(space_report())
    # --- 等距長方貼圖的 u 方向必須環狀連續（否則出現切斷銀河帶的垂直硬邊）---
    import numpy as np
    from numpy.random import default_rng as _drng
    _n = _smooth_noise(_drng(1), 64, 128, 5, 7)
    checks["equirect_seamless"] = bool(np.abs(_n[:, 0] - _n[:, -1]).max() < 1e-9)
    # --- 銀河帶取景稽核（「自動避免帶被硬邊切斷」的機制）---
    checks["band_auto_no_camera"] = auto_band_center(band_width_deg=7.0)[0] == 8.0
    bpy.ops.object.camera_add(location=(0.0, -8.0, 1.0))
    _cam = bpy.context.active_object
    _cam.name = "SelfTestCam"
    _cam.data.lens = 28
    _cam.rotation_euler = (math.radians(100.0), 0.0, 0.0)     # 朝 +Y、光軸上仰 10°
                                                             # （rot_x<90° 是往下看）
    bpy.context.scene.camera = _cam
    bpy.context.view_layer.update()
    _lo, _hi = frame_elev_range(cam=_cam)
    checks["frame_span_sane"] = _lo is not None and 8.0 < (_hi - _lo) < 45.0
    _ground = bpy.data.objects.new("Ground", bpy.data.meshes.new("GroundMesh"))
    _gm = bpy.data.materials.new("Mat_GroundStub")
    _gm.use_nodes = True
    _ground.data.materials.append(_gm)
    bpy.context.collection.objects.link(_ground)
    checks["ground_visible_detect"] = _ground_camera_visible()
    _bad = audit_band_framing(cam=_cam, band_center_deg=2.0, band_width_deg=7.0)
    checks["band_cut_detected"] = bool(_bad["blocking"]) and _bad["ok"] is False
    _ground.visible_camera = False
    checks["band_needs_visible_ground"] = not audit_band_framing(
        cam=_cam, band_center_deg=2.0, band_width_deg=7.0)["blocking"]
    _, _fit_ok = auto_band_center(cam=_cam, band_width_deg=7.0)
    checks["auto_fits_when_no_ground"] = bool(_fit_ok.get("fits"))
    _ground.visible_camera = True
    _cv, _fv = auto_band_center(cam=_cam, band_width_deg=3.0)
    checks["auto_center_above_horizon"] = (_cv - 2.5 * 3.0) >= 0.0
    checks["auto_center_fits_with_ground"] = bool(_fv.get("fits"))
    verdict = all(checks.values())
    result = {"checks": checks, "verdict": "PASS" if verdict else "FAIL",
              "report": space_report()}
    print("SPACE_SELFTEST:" + json.dumps(result, default=str), flush=True)
    if not verdict:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    else:
        print("space_lib: 這是凍結模組，請在場景腳本 import 使用（--selftest 自我測試）",
              flush=True)
