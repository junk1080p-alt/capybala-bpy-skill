# KEYWORDS: blender, bpy, material, 材質庫, mat_lib, 皮革, 木紋, 混凝土, 拉絲金屬, 鍍膜, 塑膠, 布料, 賽璐璐, cel, toon, 3渲2, 卡通著色, 平塗, 色階, 凍結模組
"""mat_lib.py — 基礎材質生成函數庫（凍結模組，§9.3 同款規則）。

用法（§16.1 場景包）：
    copy_skill_resource_native 取出到 .capybala/test-scripts/mat_lib.py（與 build_template.py 同層），
    場景包 materials.py 只做兩件事：
        1. import mat_lib as M，呼叫 M.make_xxx(...) 並用 Mat_<用途> 命名；
        2. 定義本任務專屬材質（lib 沒有的）。
    禁止把 lib 函數全文複製進場景包（§9.6.1 P6），禁止改 lib 本體——要修正改 skill asset 再重新 copy。

所有 factory 回傳 bpy.types.Material，全部程序化（無外部貼圖檔，headless 安全）。
Socket 名稱差異一律走 set_socket() 候選清單（§8 API 落差防呆）：5.1 實名優先、4.x 舊名備援，
全不命中印 WARNING 不中斷（PROJECT-RULES：禁止 silent catch）。
依賴 build_template 的 log/fail（同目錄存在即可）；獨立使用時自動降級為 print/sys.exit。
驗證：Blender 5.1.2 headless（見 §17 round10 驗證紀錄）。

座標空間（2026-09-08 修正，§17.3）：全部 7 個帶程序化紋理的 factory 內部的
Noise/Wave/Voronoi 節點都經 `_obj_coords()` 接 Object 座標，不是 Blender 預設的
Generated 座標——Generated 座標把物件包圍盒正規化，同一個 grain_scale 套在小
物件跟大平面上會有天差地遠的實際紋理密度（教室/咖啡廳地板事故根因）。新增
factory、或修改既有 factory 加新的 Noise/Wave/Voronoi 節點時，Vector 輸入
一律接 `_obj_coords(nt, name)`，不要留空。

紋理/顏色變化（2026-09-08 修正）：座標空間修好後又踩到下一個坑——同一個
factory＋同樣參數在不同物件上（地板/桌面/門）呼叫多次，紋理圖案跟顏色卻
「千篇一律」，像同一塊木板複製貼上（使用者實測回饋）。原因是這些程序化節點
本身完全決定性（同輸入→同輸出），沒有任何東西讓不同呼叫產生不同結果。
`_obj_coords()` 現在會依材質名稱疊加一個決定性隨機座標平移+三軸旋轉（`_name_seed()`
用 zlib.crc32 從 name 推導，不能用內建 hash()——那個受 PYTHONHASHSEED 影響，
CALIB 跟正式渲染是兩次獨立行程，同一個材質可能算出不同結果，畫面就對不起來）；
旋轉才是關鍵——單純平移對 Wave 這種週期性條紋幾乎沒有視覺效果，旋轉才會真正
改變條紋/雲紋的方向；
`make_wood`/`make_leather`/`make_stone`/`make_concrete`/`make_fabric` 這五個
「天然材質」另外用 `_jitter_color()` 對 base 色票做小幅決定性微調（同一批
「同色」原木/石材本來就有天然深淺差異）。`make_metal`/`make_plastic`/`make_paint`
等「量產材質」故意不做顏色微調——同一批工廠塗裝的塑膠/烤漆件本來就該是同一個
顏色，那裡的一致性是對的，不是缺陷。
"""
import bpy
import colorsys
import math
import random
import zlib

# ---------------------------------------------------------------- 真實材質量測參考
# 查證非實測（2026-09-09，來源見下；不是這台機器渲染驗證過的數字，是公開量測資料庫
# 查到的物理常數）。背景：材質參數若只憑感覺手調，容易「看起來對但不夠真實」——
# 查證後確認：IOR、金屬 F0 反射率這類數值不需要用猜的，公開發表的量測資料庫本來
# 就查得到這些常數。以下只收錄**物理常數類**數值（IOR、
# 折射率、金屬 F0 反射率色）——這些跟材質身分綁定，不隨呼叫者意圖變動；**粗糙度
# 不在此列**，因為粗糙度是「表面加工方式」不是「材質身分」的函數（拋光鋁跟拉絲鋁
# 是同一種材質、完全不同的粗糙度），查證時 physicallybased.info 也證實這一點：
# 它的資料庫故意不收錄粗糙度，只收錄 color/IOR/specular/density 這些材質本身的常數，
# 粗糙度留給使用者依實際加工/磨損程度自行決定——本檔各 factory 把 roughness 留成
# 呼叫者可調參數，這個既有設計方向是對的，不需要因為這次查證而改。
#
# 來源：
#   - https://physicallybased.info/ （50+ 材質量測值資料庫：color/IOR/specular/density）
#   - https://pixelandpoly.com/ior.html （常見材質 IOR 對照表）
#   - https://google.github.io/filament/Filament.md.html （介電材質 Fresnel 反射率區間）
#
# IOR（折射率，玻璃/透明材質類 make_glass()/make_coated_glass() 選 ior 參數用）：
#   一般窗玻璃/曹達石灰玻璃 soda-lime 1.520（= make_glass 現有預設，不用改）；
#   硼矽玻璃 borosilicate 1.474-1.520；壓克力/PMMA 1.489-1.492；聚碳酸酯
#   polycarbonate 1.584；聚苯乙烯 polystyrene 1.550；水 1.333（20°C）；
#   光學鍍膜鏡頭玻璃常見範圍 1.5-1.9（make_coated_glass 現有預設 1.62 落在此範圍內）。
#
# 介電材質（非金屬）Specular 基準：Blender Principled BSDF 的 Specular/Specular IOR
# Level 預設值 0.5 本身就對應約 4% Fresnel 反射率（Filament 文件：一般介電材質
# 反射率集中在 4-5.6% 這個窄帶，塑膠/玻璃約 4-5%，布料約 4-5.6%）——這解釋了
# 為什麼 Blender 把非金屬預設值定在 0.5：那不是隨便選的中間值，是物理量測的
# 折衷代表值。physicallybased.info 的 Specular 欄位剛好是同一個 0-1 尺度
# （驗證：其 Concrete 條目 Specular=0.510，幾乎等於 Blender 預設 0.5），可以
# 直接當 Specular/Specular IOR Level 的參考起點：混凝土 0.51、大理石（拋光）0.79、
# 磚 0.095、陶土 0.21、紙 0.83——多孔/霧面材質明顯低於預設、拋光石材明顯高於
# 預設，這跟直覺一致（本檔 make_concrete 原本手調 0.25 明顯偏低，已依此調整）。
#
# 金屬 F0 反射率色（make_metal()/make_brushed_metal() 的 color 參數）：
# physicallybased.info 只回傳單一代表值不是完整 RGB，這裡改採業界廣泛引用的
# metal F0 sRGB 三色數值（Naty Hoffman／Adobe Substance 系列 PBR 教材通用數字，
# 非本次唯一來源，是長期公開的行業共識值）：鋁 (0.91,0.92,0.92)、鉻 (0.55,0.56,0.55)、
# 不鏽鋼 (0.63,0.65,0.65)、金 (1.00,0.85,0.57)、銅 (0.95,0.64,0.54)、黃銅
# (0.91,0.78,0.42)、銀 (0.95,0.93,0.88)——這些數值已併入 METAL_PRESETS。

METAL_PRESETS = {
    "aluminum": (0.91, 0.92, 0.92),
    "chrome": (0.55, 0.56, 0.55),
    "steel": (0.63, 0.65, 0.65),
    "gold": (1.00, 0.85, 0.57),
    "copper": (0.95, 0.64, 0.54),
    "brass": (0.91, 0.78, 0.42),
    "silver": (0.95, 0.93, 0.88),
}

try:
    import build_template as T
    _log = T.log
    _fail = T.fail
except ImportError:  # 獨立探測模式降級
    import sys
    def _log(step, msg): print(f"[{step}] {msg}")
    def _fail(step, msg):
        print(f"[{step}] FATAL: {msg}")
        sys.exit(1)


# ---------------------------------------------------------------- 基礎工具

def set_socket(bsdf, names: list, value) -> bool:
    """依候選名稱順序設定 Principled socket；全不命中 WARNING（禁止 silent catch）。"""
    for n in names:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return True
    _log("mat_lib", f"WARNING: socket 候選 {names} 全不命中，跳過")
    return False


def principled(mat: bpy.types.Material):
    """取得 (node_tree, Principled BSDF)；找不到即 fail fast。"""
    mat.use_nodes = True
    nt = mat.node_tree
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return nt, n
    _fail("mat_lib", f"{mat.name} 找不到 Principled BSDF")


def _name_seed(name: str) -> int:
    """從材質名稱決定性推導一個整數種子。

    不能用 Python 內建 hash()——那個受 PYTHONHASHSEED 影響，同一個字串在
    CALIB 跟正式渲染這兩次「獨立行程」裡可能算出不同的雜湊值，材質外觀就會
    對不起來（使用者看 CALIB 覺得可以，正式渲染卻變了）。zlib.crc32 是純數學
    運算，同一個字串在任何行程、任何時候都得到同一個結果。
    """
    return zlib.crc32(name.encode("utf-8"))


def _obj_coords(nt, name: str):
    """回傳這個材質節點樹的紋理取樣座標——Object 座標（不是 Blender 預設的
    Generated）疊加一個依材質名稱決定性推導的隨機偏移。

    座標空間修正（2026-09-08 教室/咖啡廳地板事故根因）：本檔每個程序化材質的
    Noise/Wave/Voronoi 節點 Vector 輸入原本都沒接線——Blender 對沒接線的 Vector
    輸入預設走 Generated 座標，這個座標系統把物件自己的包圍盒正規化到固定範圍，
    代表同一個 grain_scale 數值在一張小書桌（0.6m）跟一片大地板（8m）上會產生
    完全不同的實際紋理密度：桌上看起來是細緻木紋，地板上被拉伸成又寬又假的
    斑馬紋（使用者原話：「地板材質不好，感覺跟桌子一樣」）。改用 Object 座標——
    這是物件自己的局部座標；`add_box()`/`add_cyl()` 建出來的物件都已經
    transform_apply 過，局部座標本來就是以公尺為單位的真實尺寸，grain_scale
    數值在任何大小的物件上都代表同一個實際紋理密度，不用再逐物件微調。

    隨機偏移+旋轉（2026-09-08 下一輪修正，實測校準版）：光修座標空間後又踩到
    「不同物件呼叫同一個 factory＋同樣參數，紋理圖案卻長得一模一樣」——地板/
    桌面/門三處木紋「千篇一律」，像同一塊木板複製貼上（使用者實測回饋）。
    **第一版只加平移，實測發現沒用**：Wave 節點的條紋是週期性圖案，單純平移
    只是移動相位，人眼完全看不出「移動過的條紋」跟「沒移動的條紋」有什麼不同
    ——三塊木板側著看還是像同一片木板複製貼上。真正讓外觀不同的是**旋轉**：
    改變取樣方向會讓 Wave 的條紋朝向不同方向（不是同一批平行線），Noise/Voronoi
    的雲紋走向也會跟著變，肉眼一眼就能分辨。改用 `ShaderNodeMapping` 同時做
    平移（給 Noise/Voronoi 的相位變化）+ 三軸隨機旋轉（給 Wave 的方向變化，
    也順便讓 Noise/Voronoi 的雲紋走向不同）。偏移/旋轉量從 `name`（例如
    "Mat_Floor" vs "Mat_DeskTop"）決定性推導，不同材質名稱自動得到不同結果，
    同一個名稱在 CALIB 跟正式渲染兩次獨立行程裡永遠得到同一個結果（可重現）。
    """
    rng = random.Random(_name_seed(name))
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Location"].default_value = (
        rng.uniform(-50.0, 50.0), rng.uniform(-50.0, 50.0), rng.uniform(-50.0, 50.0))
    mapping.inputs["Rotation"].default_value = (
        rng.uniform(0.0, math.tau), rng.uniform(0.0, math.tau), rng.uniform(0.0, math.tau))
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    return mapping.outputs["Vector"]


def _jitter_color(base: tuple, name: str, amount: float = 0.05) -> tuple:
    """依材質名稱對色票做小幅決定性微調（預設 ±5%），只用在「天然材質」
    （木/皮/石/混凝土/織物）——同一批「同色」原木/石材本來就有天然深淺差異，
    不是每個「同色」材質都該長得一模一樣（2026-09-08 使用者實測回饋）。

    刻意不用在 make_metal/make_plastic/make_paint 這類「量產材質」：同一批
    工廠塗裝的塑膠件/烤漆件本來就該是同一個顏色，那裡的一致性是對的，不是缺陷
    ——量產材質不要呼叫這個函式。種子推導方式同 `_name_seed()`，同一個名稱
    永遠得到同一個微調結果（可重現，見 `_obj_coords()` 的說明）。
    """
    rng = random.Random(_name_seed(name) ^ 0x5EED)
    return tuple(max(0.0, min(1.0, c * (1.0 + rng.uniform(-amount, amount)))) for c in base)


def hex_to_linear(hex_str: str) -> tuple:
    """設計色票 '#RRGGBB' → Blender 線性 RGB tuple（sRGB 轉換）。
    風格卡（§17）色票一律給 hex + 本函數預轉換值；禁止把 hex 直接當 default_value 填。"""
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (round(f(r), 5), round(f(g), 5), round(f(b), 5))


# ---------------------------------------------------------------- 金屬族

def make_metal(name: str, color=None, roughness: float = 0.25,
               metallic: float = 1.0, preset: str = None) -> bpy.types.Material:
    """純色金屬（最快起點）：Chrome/鋁/鋼/黃銅皆可用 color+roughness 表達。
    **preset**（2026-09-09 新增，查證真實 F0 反射率色，見檔頭「真實材質量測參考」）：
    給 `preset="aluminum"/"chrome"/"steel"/"gold"/"copper"/"brass"/"silver"` 之一直接
    套用查證過的真實金屬反射率色（`METAL_PRESETS`），比手填 color 猜色準確。
    仍給 `color` 就照舊用自訂色（例如非寫實風格化配色），`color`/`preset` 二選一，
    都不給時退回鋁（最常見的通用金屬）。roughness 是加工/拋光程度，不是材質身分的
    一部分，查證後確認留給呼叫者依實際加工手感自訂是對的，不因此次查證而改。

    **粗糙度務必依表面積/顯眼度分級，不要整台主體所有金屬件共用同一個 roughness**
    （2026-09-09 新增，相機案例實測抓到的真實 bug：頂蓋/底板這種大面積
    平面跟快門盤/背帶環這類小飾件全部套 `roughness=0.15`，渲染出來大平面在棚拍
    AREA 燈下變成一整片鏡子，直射光源被鏡面反射成大片燒白色帶，小飾件反而沒事——
    同一個材質在不同面積的表面上，視覺後果天差地遠）。經驗法則：**表面積越大/
    越平坦，roughness 給越高**（0.28-0.35，緞面/拉絲感，對應 `make_brushed_metal()`
    或本函式傳較高 roughness）；**表面積小/曲面/裝飾性強的飾件才用低 roughness**
    （0.10-0.20，接近鏡面，例如刻度盤、螺絲頭、鏡筒環）——不是「這個東西材質定位
    是拋光鉻」就整個機身都給同一個 roughness 數字，機身大面板跟裝飾小飾件在真實
    產品上幾乎從不共用同一種拋光工藝。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    final_color = color if color is not None else METAL_PRESETS.get(preset, METAL_PRESETS["aluminum"])
    bsdf.inputs["Base Color"].default_value = (*final_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def make_brushed_metal(name: str, color=(0.78, 0.78, 0.80), rough_mid: float = 0.22,
                       aniso_strength: float = 0.12) -> bpy.types.Material:
    """拉絲金屬：Noise 擾動 Roughness 近似各向異性拉絲紋（camera_pkg 實戰校準版）。"""
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = rough_mid
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = 60.0
    tex.inputs["Detail"].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    lo = max(rough_mid - aniso_strength, 0.02)
    ramp.color_ramp.elements[0].color = (lo, lo, lo, 1.0)
    ramp.color_ramp.elements[1].color = (rough_mid + aniso_strength * 0.8,
                                         rough_mid + aniso_strength * 0.8,
                                         rough_mid + aniso_strength * 0.8, 1.0)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


def make_anodized(name: str, color=(0.02, 0.02, 0.025), roughness: float = 0.38) -> bpy.types.Material:
    """陽極氧化鋁（Apple 味核心材質）：金屬=1 + 中高粗糙 + 微 specular，色層在氧化層內。"""
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], 0.55)
    # 極細磨砂擾動
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = 4000.0
    tex.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (roughness - 0.03,) * 3 + (1.0,)
    ramp.color_ramp.elements[1].color = (roughness + 0.03,) * 3 + (1.0,)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


# ---------------------------------------------------------------- 皮革/織物

def make_leather(name: str, base=(0.028, 0.026, 0.024), bump_scale: float = 0.0025,
                 grain_scale: float = 900.0, roughness: float = 0.72,
                 pebble_scale: float = 0.0) -> bpy.types.Material:
    """荔枝皮/光面皮：高頻 Noise 凹凸 + 天然色差混色。grain_scale 大=細紋（荔枝皮
    900），小=大紋（瘋馬皮 300）。

    `pebble_scale`（2026-09-10 新增，來源：運動球參考案例籃球皮革，比對
    後確認優於原本的純 Noise 凹凸）：>0 時疊加一層 Voronoi Distance→反轉 Bump
    做出籃球/顆粒皮革那種圓潤顆粒感（不是 Noise 的模糊起伏，是明確的胞狀邊界，
    真實顆粒皮革視覺特徵）——兩層 bump 疊加（細紋 Noise 打底+顆粒 Voronoi 主體），
    不是取代原本的 Noise 層。數值參考：籃球顆粒用 `pebble_scale=110~120`。"""
    base = _jitter_color(base, name)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = grain_scale
    tex.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[1].position = 0.62
    dark = tuple(c * 0.78 for c in base)
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_scale
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    normal_out = bump.outputs["Normal"]
    if pebble_scale > 0:
        pebble = nt.nodes.new("ShaderNodeTexVoronoi")
        nt.links.new(_obj_coords(nt, name + "_pebble"), pebble.inputs["Vector"])
        pebble.inputs["Scale"].default_value = pebble_scale
        pebble_bump = nt.nodes.new("ShaderNodeBump")
        pebble_bump.invert = True
        pebble_bump.inputs["Strength"].default_value = 0.43
        pebble_bump.inputs["Distance"].default_value = 0.009
        nt.links.new(pebble.outputs["Distance"], pebble_bump.inputs["Height"])
        nt.links.new(normal_out, pebble_bump.inputs["Normal"])
        normal_out = pebble_bump.outputs["Normal"]
    nt.links.new(normal_out, bsdf.inputs["Normal"])
    return mat


def make_fabric(name: str, base=(0.55, 0.53, 0.48), bump_scale: float = 0.0012,
                weave_scale: float = 1400.0, roughness: float = 0.92) -> bpy.types.Material:
    """織物/布面：超高頻 Noise 凹凸 = 織紋，微 sheen（5.x Coat 降級容忍）。"""
    base = _jitter_color(base, name)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = weave_scale
    tex.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_scale
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    set_socket(bsdf, ["Sheen Weight", "Sheen"], 0.25)
    return mat


# ---------------------------------------------------------------- 木/石/混凝土

def make_wood(name: str, base=(0.32, 0.18, 0.09), dark=None, grain_scale: float = 6.0,
              roughness: float = 0.55, grain_axis: str = 'Z',
              coat_weight: float = 0.0, coat_roughness: float = 0.32) -> bpy.types.Material:
    """程序化木紋（2026-09-10 第二次重新設計，來源：四木材閱讀角參考案例，
    實測比對後認可，取代第一版的 Wave 底方案）。

    第一版仍以 Wave（週期圖案）驅動底色，尺度一放大還是容易讀出規律感。新版改用
    案例驗證過的配方：**純 Noise 驅動、沿 `grain_axis` 各向異性拉伸座標**
    （紋理沿該軸拉得細長、垂直方向變化快，模擬真實木紋長纖維+橫向粗細不均），
    無週期性圖案、不會有規律條紋風險。底色 ColorRamp 只是打底，紋理可讀性主要
    靠 bump；`coat_weight`>0 加一層薄 Coat 模擬上漆/上油的成品木作光澤（原木/
    未加工木作留 0）。

    `base`=主色（原淺色/邊材），`dark`=紋理深色（None 時自動取 base×0.35，紋理
    對比比第一版更貼近真實木材的深淺跨度）。`grain_axis`：紋理拉長方向，直向
    木作（書櫃側板/門片/桌腳）用 'Z'，橫向長板（地板長邊/層板/桌面長邊）用量體
    實際長軸。

    **多物件木作務必用同一份材質（同一個 make_wood() 呼叫回傳值，append 給所有
    物件），不要每個物件各呼叫一次**——本函式內建 Object Info 的 Random 輸出
    驅動每個物件±約 10% 的獨立明暗微調，同一份材質套在 N 個物件上會自動長出
    「同一批木料、深淺略有不同」的真實感（地板逐塊木地板/書架逐層層板的自然
    做法），每個物件各自呼叫一次 factory 反而會各自拿到新的統一色，失去這個
    效果且浪費材質數量。"""
    base = _jitter_color(base, name)
    if dark is None:
        dark = tuple(c * 0.35 for c in base)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    if coat_weight > 0:
        set_socket(bsdf, ["Coat Weight", "Clearcoat"], coat_weight)
        set_socket(bsdf, ["Coat Roughness", "Clearcoat Roughness"], coat_roughness)
    obj_vec = _obj_coords(nt, name)

    axis_stretch = {'X': (2.0, 40.0, 9.0), 'Y': (9.0, 2.0, 40.0), 'Z': (40.0, 9.0, 2.0)}[grain_axis.upper()]
    stretch_node = nt.nodes.new("ShaderNodeVectorMath")
    stretch_node.operation = 'MULTIPLY'
    stretch_node.inputs[1].default_value = axis_stretch
    nt.links.new(obj_vec, stretch_node.inputs[0])

    noise = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(stretch_node.outputs["Vector"], noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = grain_scale * 0.35
    noise.inputs["Detail"].default_value = 3.5
    if "Roughness" in noise.inputs:
        noise.inputs["Roughness"].default_value = 0.62

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    info = nt.nodes.new("ShaderNodeObjectInfo")
    variation = nt.nodes.new("ShaderNodeMapRange")
    variation.inputs["To Min"].default_value = 0.88
    variation.inputs["To Max"].default_value = 1.08
    nt.links.new(info.outputs["Random"], variation.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], mix.inputs[1])
    nt.links.new(variation.outputs["Result"], mix.inputs[2])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_concrete(name: str, base=(0.42, 0.41, 0.39), pit_scale: float = 0.0006,
                  roughness: float = 0.88, specular: float = 0.45) -> bpy.types.Material:
    """清水混凝土（安藤味核心材質）：Voronoi 氣孔 + 大尺度色差。
    specular 預設 2026-09-09 由 0.25 上調到 0.45（查證非實測，見檔頭「真實材質量測
    參考」）：physicallybased.info 量測的混凝土 Specular=0.510，接近 Blender 介電
    材質預設值 0.5，原本的 0.25 明顯偏低（等於把混凝土做得比大部分介電材質更啞光，
    查無依據）；改 0.45 保守貼近量測值，同時留一點餘裕給 CALIB 快渲驗證觀感。"""
    base = _jitter_color(base, name)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], specular)
    obj_vec = _obj_coords(nt, name)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(obj_vec, vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = 600.0
    noise = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(obj_vec, noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[1].position = 0.60
    dark = tuple(c * 0.88 for c in base)
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = pit_scale
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_stone(name: str, base=(0.5, 0.48, 0.45), roughness: float = 0.75,
              specular: float = 0.55) -> bpy.types.Material:
    """石材/大理石近似：大尺度 Noise 雲紋 + 細顆粒 bump。
    specular 2026-09-09 新增參數（查證非實測，見檔頭「真實材質量測參考」）：預設 0.55
    是介於粗琢石材與拋光大理石之間的保守值；量測到的拋光大理石 Specular 高達 0.79，
    真的要做拋光石材（大堂地坪、櫃台）可以呼叫時傳 `specular=0.79` 拉高光澤感，粗獷
    毛面石材（外牆基座、戶外鋪面）可以壓低到 0.3-0.4。"""
    base = _jitter_color(base, name)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], specular)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[1].position = 0.65
    light = tuple(min(c * 1.18, 1.0) for c in base)
    ramp.color_ramp.elements[0].color = (*base, 1.0)
    ramp.color_ramp.elements[1].color = (*light, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.0009
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------- 玻璃/鏡片

def make_glass(name: str, tint=(0.9, 0.92, 0.95), ior: float = 1.52,
               roughness: float = 0.03, specular: float = 0.5) -> bpy.types.Material:
    """透明玻璃：Transmission + IOR（socket 名走候選清單，§8#4x→5.x 改名防呆）。
    ior 預設 1.52 = 一般窗玻璃/曹達石灰玻璃（soda-lime，最常見的建築/產品玻璃），
    查證真實範圍（見檔頭「真實材質量測參考」）：硼矽玻璃 1.47-1.52、壓克力/PMMA
    1.49、聚碳酸酯 1.58、水 1.33——需要特定材質質感時可覆寫，不要憑感覺亂填。

    **`specular`（2026-09-11 新增參數，同一個坑連續在兩個獨立機械錶案例重演）**：
    `Specular IOR Level` 預設 0.5（沿用 Blender 節點預設，過去這支函式沒有暴露這個
    參數、呼叫端也不知道要覆寫）在**薄殼透明面蓋在一個有細節的表面上方**這個情境
    （錶鏡蓋錶盤、儀表玻璃蓋刻度盤、展示櫃玻璃蓋商品）會把菲涅爾反射強度撐得太高，
    棚拍等級的 key/fill 燈光打上去，反射光直接蓋過穿透光，底下的表面細節（指針/
    文字/刻度）整片被反射沖成一片死白/死灰，肉眼完全看不到錶盤——**這不是穿透率
    設錯，`Transmission Weight` 本來就是對的，兇手是反射分量太強**。兩次獨立的
    機械錶案例都踩到同一個坑（第一次靠呼叫端手動 `set_socket(bsdf, ["Specular IOR
    Level","Specular"], 0.22)` 補救，但那個修正從沒進到這支函式或圖譜裡，第二次
    重新踩了一次），現在把參數直接暴露出來，**任何「透明薄殼蓋在細節表面上」的
    情境呼叫時覆寫成 0.15-0.25**（模擬真實抗反射鍍膜的低反射率），一般用途（窗戶/
    瓶身/水面這類穿透物件本身就是被看的對象，不是蓋在別的細節上）維持預設 0.5
    即可，不用跟著調。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*tint, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Transmission Weight", "Transmission"], 1.0)
    set_socket(bsdf, ["IOR"], ior)
    set_socket(bsdf, ["Specular IOR Level", "Specular"], specular)
    return mat


def make_coated_glass(name: str, tint=(0.010, 0.012, 0.045), ior: float = 1.62,
                      specular: float = 0.8, roughness: float = 0.06) -> bpy.types.Material:
    """多層鍍膜鏡片（相機鏡頭/眼鏡）：深色 tint + 高 specular = 藍紫鍍膜反射感。
    ior 預設 1.62 落在光學鍍膜鏡頭玻璃常見範圍 1.5-1.9 內（查證見檔頭「真實材質量測
    參考」），不是隨便選的數字。

    **不要拿來做建築窗戶/帷幕玻璃（2026-09-11 日式住宅大樓案例驗證的真實 bug）**：
    這支函式模擬的是鏡頭鍍膜那種「高吸收+高反射」的光學材質，預設 tint 逼近全黑
    （(0.01,0.012,0.045)），套在一整棟大樓的窗戶上，每一格窗實際渲染出來是完全
    不透光的黑色方塊——肉眼幾乎分不出「這是窗戶玻璃」還是「這格窗根本沒挖空」，
    跟真實建築窗戶（就算是深色反射玻璃）該有的通透層次感完全是兩回事。這個誤用
    在 `examples/building.md` 的兩段示範程式碼裡都存在（`window_mat = M.make_coated_
    glass(...)`），已一併修正。**建築窗戶請用 `make_glass()`**，`tint` 選中間色調
    （實測驗證可用範圍如 `(0.16,0.22,0.26)` 這種偏藍綠的中灰藍，太淺會通透到看不出
    玻璃感、太深會重演這支函式的黑洞問題），`specular` 抓 0.4-0.55、`roughness`
    0.05-0.08，實測在同一背景色前 `make_glass()` 能清楚透出背景色調（有玻璃感），
    `make_coated_glass()` 預設值則完全遮蔽背景（見 `anatomy/buildings/residential.md`
    材質基調段落的完整驗證記錄）。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*tint, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Transmission Weight", "Transmission"], 1.0)
    set_socket(bsdf, ["IOR"], ior)
    set_socket(bsdf, ["Specular IOR Level", "Specular"], specular)
    return mat


# ---------------------------------------------------------------- 塑膠/橡膠/漆

def make_plastic(name: str, base=(0.05, 0.05, 0.055), roughness: float = 0.42,
                 clearcoat: bool = False, coat_rough: float = 0.08) -> bpy.types.Material:
    """塑膠：非金屬 + 中低粗糙。clearcoat=True 走 5.x Coat socket（4.x 無則自動降級 WARNING）。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if clearcoat:
        set_socket(bsdf, ["Coat Weight", "Clearcoat"], 1.0)
        set_socket(bsdf, ["Coat Roughness", "Clearcoat Roughness"], coat_rough)
    return mat


def make_rubber(name: str, base=(0.02, 0.02, 0.022), roughness: float = 0.88) -> bpy.types.Material:
    """橡膠/軟膠握把：極高粗糙、零金屬、微 subsurface 感（省略，純粗糙即可）。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def make_paint(name: str, base=(0.012, 0.012, 0.014), roughness: float = 0.30,
               metallic: float = 0.1, clearcoat: bool = True) -> bpy.types.Material:
    """烤漆（汽車/家電外殼）：色漆層 + 默認 clearcoat 亮漆面。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if clearcoat:
        set_socket(bsdf, ["Coat Weight", "Clearcoat"], 0.9)
        set_socket(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.05)
    return mat


def make_emissive(name: str, color=(1.0, 0.85, 0.6), strength: float = 8.0) -> bpy.types.Material:
    """自發光（燈絲/螢幕/指示燈）：Emission socket 候選防呆。

    **在明亮日光場景（`studio`/`outdoor_golden` 等亮度較高的 preset）下用來做「已入住
    暖光窗」，效果比預期差很多（2026-09-11 實測驗證）**：這支函式回傳的 Principled
    BSDF 除了 Emission 以外其餘 socket 全是預設值（不透明白色 Base Color、Roughness
    0.5），在強日光環境光下，Emission strength 從 0.9 一路測到 7.0，AgX 色調映射全部
    把這塊面壓成近乎純白/米白的實心卡片——**跟旁邊沒開燈的窗戶幾乎分不出差異，「暖
    色」根本看不出來，只看到一片死白**，這正是這個技巧真正物理成立的場景是黃昏/夜景
    （環境光夠暗，emission 才會顯著比周圍亮且保留色相），不是白天棚拍級曝光。白天
    場景硬做這個效果，實測比較好的替代方案：不要用純 `make_emissive()`，改用一個
    Transmission=1.0 的 Principled BSDF、Base Color 直接給飽和暖色（如 `(0.55,0.40,
    0.22)`，不是靠 Emission 撐色相）、Emission strength 只給 1.0-1.5 當作輕微加成，
    這樣至少能在白天場景保留可辨識的暖色調（不會被壓成白色），但不會有真正「發光」的
    視覺效果——那個效果只有在 `night` preset/`auto_night_fill()` 場景下才值得做，
    白天場景這個細節的報酬遠低於預期，值得衡量是否要做（見
    `anatomy/buildings/residential.md` 常見錯誤區的完整驗證記錄）。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    set_socket(bsdf, ["Emission Color", "Emission"], (*color, 1.0))
    set_socket(bsdf, ["Emission Strength"], strength)
    return mat


def make_light_shaft(name: str, color=(0.70, 0.79, 1.0), strength: float = 55.0,
                     core: float = 0.88, radial_power: float = 1.7,
                     z_fade: float = 0.70) -> bpy.types.Material:
    """光束／光柱（探照燈、紀念光柱、夜間投射燈、上帝光）。

    `Emission` 混合 `Transparent BSDF`，混合因子＝「徑向邊緣衰減 × 高度淡出 × core」
    ——所以一根圓柱從外面看是**中間濃、邊緣柔散、往上淡出**的霧狀光柱，不是一根自體
    發光的實心塑膠管。這是光束類材質唯一正確的做法：純 `make_emissive()` 套在圓柱上
    會得到邊緣銳利、亮度均勻的實心發光柱，跟真實探照燈光柱的體積散射外觀完全不同。

    參數（下列 strength/core 是「兩棟 400m 高塔、約 1000m 視框」夜間場景的校準值，
    小場景要往下調 strength，core 可以維持）：
    - `color`：冷白藍 (0.70,0.79,1.0)＝一般探照燈／氙氣燈；暖黃用 (1.0,0.88,0.62)。
    - `strength`：Emission 強度，**必須顯著大於 1**（校準 55）——光柱要打穿夜景
      preset 的環境光、並在 Fog Glow 合成器裡拉出輝光；值太低會被夜色吃掉、幾乎看不見。
    - `core`：軸心濃度上限（0-1）。越大核心越濃越像實體；0.88 是「濃但不死板」的值。
    - `radial_power`：徑向衰減指數。1.0＝線性，越大邊緣收得越快、光柱越細越銳利；
      1.7 對應邊緣有明顯柔散的自然感。
    - `z_fade`：頂端淡出高度（Generated Z 的 0-1 比例；0.70＝上方 30% 用來淡出）。
      真實光柱在高空會被大氣擴散吃掉，頂端硬切會很假。

    擺位提醒：本材質靠 `Generated` 座標（物件自身包圍盒正規化）算徑向/高度衰減，
    **一根光柱就是一個圓柱物件**（半徑/高度直接決定光柱粗細與長度），不要多根共用
    一個物件；Generated 不含世界尺度，光柱拉到 1350m 長也不會讓衰減變形。
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    emis = nt.nodes.new("ShaderNodeEmission")
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    emis.inputs["Color"].default_value = (*color, 1.0)
    emis.inputs["Strength"].default_value = strength
    nt.links.new(trans.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emis.outputs["Emission"], mix.inputs[2])

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])

    def _sub(socket, value):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "SUBTRACT"
        n.inputs[1].default_value = value          # socket - value
        nt.links.new(socket, n.inputs[0])
        return n.outputs["Value"]

    def _sq(socket):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "MULTIPLY"
        nt.links.new(socket, n.inputs[0])
        nt.links.new(socket, n.inputs[1])
        return n.outputs["Value"]

    # 徑向距離：Generated XY 以 0.5 為軸心，r = √(dx²+dy²) × 2（邊緣略 >1 再由 clamp 收）
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(_sq(_sub(sep.outputs["X"], 0.5)), add.inputs[0])
    nt.links.new(_sq(_sub(sep.outputs["Y"], 0.5)), add.inputs[1])
    root = nt.nodes.new("ShaderNodeMath")
    root.operation = "POWER"
    root.inputs[1].default_value = 0.5
    nt.links.new(add.outputs["Value"], root.inputs[0])
    radial = nt.nodes.new("ShaderNodeMath")
    radial.operation = "MULTIPLY"
    radial.inputs[1].default_value = 2.0
    nt.links.new(root.outputs["Value"], radial.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(radial.outputs["Value"], inv.inputs[1])   # 1 - 徑向
    clamp = nt.nodes.new("ShaderNodeClamp")
    clamp.inputs["Min"].default_value = 0.0
    clamp.inputs["Max"].default_value = 1.0
    nt.links.new(inv.outputs["Value"], clamp.inputs["Value"])
    falloff = nt.nodes.new("ShaderNodeMath")
    falloff.operation = "POWER"
    falloff.inputs[1].default_value = radial_power
    nt.links.new(clamp.outputs["Result"], falloff.inputs[0])

    # 高度淡出：頂端（Generated Z → 1）收掉
    zfade = nt.nodes.new("ShaderNodeMapRange")
    zfade.inputs["From Min"].default_value = 0.0
    zfade.inputs["From Max"].default_value = max(0.01, z_fade)
    zfade.inputs["To Min"].default_value = 1.0
    zfade.inputs["To Max"].default_value = 0.0
    zfade.clamp = True
    nt.links.new(sep.outputs["Z"], zfade.inputs["Value"])

    alpha = nt.nodes.new("ShaderNodeMath")
    alpha.operation = "MULTIPLY"
    nt.links.new(falloff.outputs["Value"], alpha.inputs[0])
    nt.links.new(zfade.outputs["Result"], alpha.inputs[1])
    scale = nt.nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = core
    nt.links.new(alpha.outputs["Value"], scale.inputs[0])
    nt.links.new(scale.outputs["Value"], mix.inputs[0])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    _log("mat_lib", f"make_light_shaft: {name} strength={strength} core={core} z_fade={z_fade}")
    return mat


# ---------------------------------------------------------------- 環境地景（水/草地/土壤/瀝青）
# 2026-09-09 新增（使用者反饋：內建材質種類不夠）——直接證據：近期案例分析中，住宅大樓/
# 演唱會舞台這類場景都至少手刻了一種本檔沒提供的材質（大樓案例的水池/培養土/
# 草皮，舞台案例的地面），`road_lib.py` 也把瀝青材質寫死在 `add_lane_markings()` 內部、
# 沒有暴露成可重用 factory——同一種材質被不同場景各自重寫，正是本檔開頭 P6「單一真相源」
# 要避免的事，優先補這幾個環境地景類材質，不是隨便湊數量。

def make_water(name: str, base=(0.02, 0.06, 0.08), roughness: float = 0.02,
               ior: float = 1.333) -> bpy.types.Material:
    """靜水/水池/水景：Transmission + 真實 IOR 1.333（查證見檔頭「真實材質量測參考」），
    比常見的「給高 Metallic 假造反光」手法（案例實測中也常見這招）物理更
    正確——metallic 反光的角度分佈跟真水不一樣，近距離特寫容易穿幫。細微 Noise bump
    模擬水面微波紋；靜水池可傳 roughness 更低（0.01），有風的水面調高（0.05-0.15）。"""
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Transmission Weight", "Transmission"], 1.0)
    set_socket(bsdf, ["IOR"], ior)
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = 8.0
    tex.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.02
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_grass(name: str, base=(0.16, 0.28, 0.09), roughness: float = 0.85) -> bpy.types.Material:
    """草坪/草皮地面：大尺度 Noise 混色近似草葉密度變化 + 細顆粒 bump，零金屬零光澤。
    真的要單株草葉幾何用 `nature_lib.py`（§18），這支只解決「一片草坪的地面材質」。"""
    base = _jitter_color(base, name)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = 20.0
    tex.inputs["Detail"].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.65
    dark = tuple(c * 0.6 for c in base)
    light = tuple(min(c * 1.3, 1.0) for c in base)
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*light, 1.0)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.003
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_soil(name: str, base=(0.08, 0.055, 0.03), roughness: float = 0.95) -> bpy.types.Material:
    """裸土/花圃培養土：高頻 Voronoi 顆粒感 + 大尺度色差，極高粗糙近乎純漫反射。"""
    base = _jitter_color(base, name)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], 0.15)
    obj_vec = _obj_coords(nt, name)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(obj_vec, vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = 300.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[1].position = 0.6
    dark = tuple(c * 0.7 for c in base)
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.0015
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_asphalt(name: str, base=(0.045, 0.045, 0.05), roughness: float = 0.85,
                 wetness: float = 0.0) -> bpy.types.Material:
    """瀝青路面/廣場鋪面通用版（2026-09-09 新增：`road_lib.py` 原本把同款材質寫死在
    `add_lane_markings()` 內部，非道路情境（廣場/舞台地板/停車場）沒有路徑重用，這支
    是抽出來的可重用版——`road_lib.py` 內部那份保留不動，避免動既有驗證過的道路生成
    邏輯）。細顆粒 Noise 模擬骨材顆粒感，低反光。

    **`wetness`（2026-09-11 新增，日式動漫夜景風格卡驗證用）**：0.0（預設，向下相容，
    行為跟舊版完全一致）~1.0（濕潤路面，霓虹/招牌會在地面留下清楚的鏡面反射拖影，
    賽博龐克夜景的關鍵地面效果）。實測驗證真實技法：濕路面**不是**額外疊一層
    Transmission 水膜（那是給靜水池/水窪這種有實際深度的水體用，`make_water()` 已經
    做這個），濕柏油路只是表面一層薄水膜，物理上就是 Principled BSDF 本身的低
    roughness——把 `roughness` 大幅壓低（乾地面 0.85 → 濕地面骨材顆粒的低點只要
    0.04-0.08）就會產生清楚的鏡面反射，不需要額外的 Transmission/IOR。同時真實濕地面
    不是均勻一片同樣濕——用第二層較大尺度的 Noise 當「積水斑塊遮罩」驅動 Roughness
    在「濕但不積水」（roughness 對半衰減）跟「真的有積水的凹陷處」（roughness 壓到
    0.04-0.08）之間漸變，比整片均勻低 roughness 更接近真實濕路面的斑駁反光感。
    `base` 顏色也會隨 `wetness` 等比例壓暗（濕瀝青比乾瀝青明顯更暗更飽和，不只是
    反光變強）。這是夜景/賽博龐克類場景的專屬參數，濕地面反光效果就是靠它，
    不是另開新材質（原夜景風格卡 2026-09-13 已下架重做中）。"""
    base = _jitter_color(base, name)
    if wetness > 0.0:
        base = tuple(c * (1.0 - 0.55 * wetness) for c in base)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], 0.3 if wetness <= 0.0 else 0.5)
    tex = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_obj_coords(nt, name), tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = 800.0
    tex.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[1].position = 0.58
    dark = tuple(c * 0.75 for c in base)
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.0008
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    if wetness > 0.0:
        puddle_tex = nt.nodes.new("ShaderNodeTexNoise")
        nt.links.new(_obj_coords(nt, name + "_puddle"), puddle_tex.inputs["Vector"])
        puddle_tex.inputs["Scale"].default_value = 3.0
        puddle_tex.inputs["Detail"].default_value = 4.0
        puddle_range = nt.nodes.new("ShaderNodeMapRange")
        puddle_range.inputs["From Min"].default_value = 0.0
        puddle_range.inputs["From Max"].default_value = 1.0
        puddle_range.inputs["To Min"].default_value = max(0.04, roughness * (1.0 - wetness))
        puddle_range.inputs["To Max"].default_value = max(0.06, roughness * (1.0 - 0.4 * wetness))
        nt.links.new(puddle_tex.outputs["Fac"], puddle_range.inputs["Value"])
        nt.links.new(puddle_range.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


def make_paving(name: str, base=(0.30, 0.295, 0.285), tile: float = 2.4,
                joint_size: float = 0.035, roughness: float = 0.78,
                specular: float = 0.30, tone_variation: float = 0.93,
                joint_darken: float = 0.86, bump: float = 0.12) -> bpy.types.Material:
    """鋸切石材鋪面（廣場／人行道／前庭／停車場地坪）：方正板塊＋凹陷接縫。

    跟 `make_asphalt()`（連續骨材顆粒、無接縫）與 `make_concrete()`（無接縫澆置面）
    的差別就在這裡：鋪面地坪的視覺特徵是**規則板塊網格與接縫陰影**，不是顆粒感，兩者
    不能互相頂替。大面積板塊地坪用這支，車道／柏油路用 `make_asphalt()`。

    座標刻意用 **Object 座標直連**、不經過 `_obj_coords()`——鋪面網格必須跟建築正交
    對齊，而 `_obj_coords()` 會對座標疊加依材質名稱推導的隨機三軸旋轉，接上去整片鋪面
    會歪成非正交的斜格，那不是鋪面。這是本檔唯一刻意不走 `_obj_coords()` 的例外，不要
    為了「跟其他材質一致」把它改回去。

    參數（依尺度的直覺校準值）：
    - `tile`：單塊板材邊長（m）。廣場大板 2.4、人行道小板 1.5、停車場／車道 3.0。
    - `joint_size`：接縫寬（m）。2.4m 大板約 0.035、1.5m 小板約 0.028。
    - `roughness`／`specular`：鋪面石材通常霧面（0.78-0.84）＋中等 specular（0.26-0.30）。
      **要做「反光鋪面」的鏡頭（低角度逆光、雨後、霓虹夜景）不要在這裡整片拉低
      roughness 變鏡子，改用 `build_template.apply_socket_overrides()` 依鏡頭套用**
      ——同一份材質在俯視與低角度鏡頭下需要的反光程度不同，那是鏡頭屬性不是材質屬性。
    - `tone_variation`／`joint_darken`：板材色調差（0.93＝約 ±7% 隨機板材色）與接縫壓暗倍率。
    - `bump`：接縫凹凸強度。
    """
    base = _jitter_color(base, name, 0.04)
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], specular)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0                       # 對齊網格，不是交丁砌
    brick.inputs["Scale"].default_value = 1.0 / max(1e-3, tile)
    brick.inputs["Mortar Size"].default_value = joint_size
    brick.inputs["Mortar Smooth"].default_value = 0.02
    brick.inputs["Color1"].default_value = (*base, 1.0)
    brick.inputs["Color2"].default_value = (*[c * tone_variation for c in base], 1.0)
    brick.inputs["Mortar"].default_value = (*[c * joint_darken for c in base], 1.0)
    nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    nt.links.new(brick.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    _log("mat_lib", f"make_paving: {name} tile={tile}m joint={joint_size}m rough={roughness}")
    return mat


# ---------------------------------------------------------------- 磚/陶瓷/特殊玻璃/複合材料

def make_brick(name: str, base=(0.42, 0.22, 0.16), mortar=(0.62, 0.60, 0.55),
               brick_scale: float = 8.0, roughness: float = 0.85,
               specular: float = 0.095) -> bpy.types.Material:
    """磚牆：Brick Texture 節點原生磚縫圖案（非手排 box 逐塊拼），砂漿縫用獨立顏色。
    specular 預設 0.095 = physicallybased.info 量測磚材真實值（查證見檔頭「真實材質
    量測參考」），明顯低於 Blender 介電材質預設 0.5——磚是多孔材質，反光比大部分
    介電材質弱很多，這個數字不是隨便選的。"""
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Specular IOR Level", "Specular"], specular)
    brick = nt.nodes.new("ShaderNodeTexBrick")
    nt.links.new(_obj_coords(nt, name), brick.inputs["Vector"])
    brick.inputs["Color1"].default_value = (*base, 1.0)
    brick.inputs["Color2"].default_value = (*tuple(min(c * 1.15, 1.0) for c in base), 1.0)
    brick.inputs["Mortar"].default_value = (*mortar, 1.0)
    brick.inputs["Scale"].default_value = brick_scale
    brick.inputs["Mortar Size"].default_value = 0.02
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.002
    nt.links.new(brick.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_ceramic(name: str, base=(0.92, 0.91, 0.88), roughness: float = 0.12) -> bpy.types.Material:
    """上釉陶瓷/衛浴瓷件：非金屬、低粗糙高光澤，均勻無紋理（跟 `make_stone` 的關鍵差異：
    陶瓷是人工燒製均質表面，不該有天然石材那種雲紋/色差，故意不接程序化紋理）。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    set_socket(bsdf, ["Specular IOR Level", "Specular"], 0.55)
    return mat


def make_frosted_glass(name: str, tint=(0.92, 0.94, 0.96), ior: float = 1.52,
                       roughness: float = 0.35) -> bpy.types.Material:
    """霧面/噴砂玻璃：跟 `make_glass()` 同一套 Transmission+IOR，差別只在 roughness 拉高
    到讓透射模糊（浴室窗/燈罩/隱私玻璃）——物理上是同一種玻璃、不同表面處理，獨立
    命名是為了讓元件表可以直接指名這個質感，不用每次自己重新猜 roughness 數值。"""
    mat = bpy.data.materials.new(name=name)
    _, bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*tint, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    set_socket(bsdf, ["Transmission Weight", "Transmission"], 1.0)
    set_socket(bsdf, ["IOR"], ior)
    return mat


def make_carbon_fiber(name: str, base=(0.015, 0.015, 0.018), roughness: float = 0.28) -> bpy.types.Material:
    """碳纖維編織：Checker Texture 近似 2x2 斜紋編織明暗交錯（非真實編織幾何，程序化
    近似）+ 高光 Coat 層模擬表層樹脂光澤。"""
    mat = bpy.data.materials.new(name=name)
    nt, bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    set_socket(bsdf, ["Coat Weight", "Clearcoat"], 0.6)
    set_socket(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.08)
    checker = nt.nodes.new("ShaderNodeTexChecker")
    nt.links.new(_obj_coords(nt, name), checker.inputs["Vector"])
    checker.inputs["Scale"].default_value = 400.0
    checker.inputs["Color1"].default_value = (*tuple(c * 0.5 for c in base), 1.0)
    checker.inputs["Color2"].default_value = (*tuple(min(c * 2.2, 0.08) for c in base), 1.0)
    nt.links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


# ---------------------------------------------------------------- 磨損/髒污後製疊層

# 磨損強度預設（2026-09-10 新增，來源：使用者問「坦克這類重度磨損載具怎麼做」時發現
# 舊版文件自己寫著「重度磨損可以把 edge_ramp 下端點往 0.4 降、dirt_ramp 上端點往 0.5
# 提高」，但當時的函式簽章根本沒有把 ramp 端點暴露成參數——這句建議實際上做不到，
# 呼叫端要嘛不知道、要嘛得自己 monkey-patch。三檔預設把「輕度/中度/重度」實際兜成
# 可呼叫的參數組合，medium 數值刻意跟舊版硬編碼預設完全一致（向後相容，沒傳 level
# 的既有呼叫行為不變）；heavy 就是採用文件裡原本那句建議的確切數字。
_WEAR_LEVEL_PRESETS = {
    "light":  {"edge_intensity": 0.3,  "dirt_intensity": 0.25, "edge_lo": 0.80, "edge_hi": 0.95, "dirt_hi": 0.25},
    "medium": {"edge_intensity": 0.5,  "dirt_intensity": 0.4,  "edge_lo": 0.70, "edge_hi": 0.93, "dirt_hi": 0.35},
    "heavy":  {"edge_intensity": 0.75, "dirt_intensity": 0.6,  "edge_lo": 0.40, "edge_hi": 0.90, "dirt_hi": 0.50},
}


def add_procedural_wear(mat: bpy.types.Material, edge_color=(0.85, 0.83, 0.78),
                        dirt_color=(0.05, 0.045, 0.04), level: str = "medium",
                        edge_intensity: float | None = None,
                        dirt_intensity: float | None = None,
                        ao_distance: float = 0.05) -> bpy.types.Material:
    """磨損/髒污後製疊層（2026-09-08 新增，bpy 進階技巧調研；2026-09-10 補上 level 預設，
    來源：使用者問「坦克這類重度磨損載具要怎麼做」）：對**已存在**的材質追加兩層遮罩式
    混色，不重建材質——任何本檔 factory 產物（make_metal/make_wood/...）都能直接套用。
    做法是程序化渲染的標準技法，不是取巧：`ShaderNodeNewGeometry` 的 `Pointiness` 輸出
    量測「這個點有多凸」，凸邊/尖角處數值高，混入 edge_color 模擬碰撞掉漆/氧化外露
    （真實物件的邊角最容易被摸/撞到，漆層或鍍層最先在那裡剝落）；`ShaderNodeAmbientOcclusion`
    的 AO 輸出量測「這個點被周圍幾何遮蔽的程度」，凹處/縫隙數值低，混入 dirt_color 模擬
    積灰納垢（灰塵沉積在角落而非平坦外露面，是最基本的環境瑕疵物理直覺）。兩者都是
    Blender 核心節點，零外部貼圖/外部工具依賴。

    **level="light"/"medium"/"heavy"**：一次決定「疊色強度」+「遮罩範圍多集中在真正
    尖銳的邊緣/最深的縫隙」這兩件事（見下方 `_WEAR_LEVEL_PRESETS`），不需要自己湊 5 個
    數字。medium 是預設、也是舊版唯一存在時的固定行為；light 適合較新/保養良好的物件；
    heavy 適合坦克/廢棄機具/戶外裸露多年的載具這類「邊角大面積掉漆、縫隙塞滿泥垢」的
    情境——遮罩範圍明顯擴大，不會只圈到最尖銳的那一小圈邊。`edge_intensity`/
    `dirt_intensity` 仍可個別覆寫（例如想要 heavy 的遮罩範圍但保留較低的疊色強度），
    不覆寫則沿用所選 level 的數值。

    ao_distance 是 AO 節點的取樣半徑（世界單位，公尺）——這個值需要跟物件實際尺度成
    比例（跟 auto_frame_and_light() 的燈光能量需要依 bbox 縮放是同一類問題）：一個
    0.3m 的道具用預設 0.05m 半徑抓得到正確的局部凹處，但一棟 30m 的建築物用同樣半徑
    幾乎抓不到任何遮蔽（縫隙尺度差太多），需要呼叫端依主體尺度自行調大。

    只疊 Base Color，不動 Roughness/Metallic——同時疊多個 socket 的磨損效果容易互相
    打架、難以個別調整，這裡先做視覺上最直接見效的顏色疊層，之後有需要再擴充。

    已知限制（實測發現，非猜測）：`Pointiness` 是逐頂點量測、線性內插到整個面——低面數
    網格（例：一個只有 8-14 個頂點的箱型體整體套一次 `bpy.ops.mesh.bevel()`）的單一大平面
    只有四個角頂點，角頂點的高 Pointiness 值會內插「暈染」到整個平面中央，而不是只集中在
    真正的邊緣附近，實測會看到整個表面都偏向 edge_color、不是預期的「只有邊角變色」。
    這不是這個函式能單獨修正的問題（它不碰幾何，只接受現成材質）——邊緣效果要銳利，
    host 物件本身需要有足夠的邊緣密度（例：`shape_lib.bevel_edges()` 對實際選取的邊做
    局部倒角，而不是整個物件套一次性的粗糙 bevel），這也是本 skill §13.10 一貫要求
    「用 shape_lib 塑形，不用方塊硬拼」的同一個道理在材質層的體現。AO/dirt 這一路
    （凹角/縫隙判定）不受這個限制影響，任何幾何上真實存在的凹處都能正確偵測到。
    """
    if level not in _WEAR_LEVEL_PRESETS:
        _fail("mat_lib", f"add_procedural_wear: 未知 level={level!r}，只接受 {list(_WEAR_LEVEL_PRESETS)}。")
    preset = _WEAR_LEVEL_PRESETS[level]
    edge_intensity = preset["edge_intensity"] if edge_intensity is None else edge_intensity
    dirt_intensity = preset["dirt_intensity"] if dirt_intensity is None else dirt_intensity

    nt, bsdf = principled(mat)
    base_input = bsdf.inputs["Base Color"]
    if base_input.links:
        base_socket = base_input.links[0].from_socket
    else:
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = tuple(base_input.default_value)
        base_socket = rgb.outputs[0]

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    edge_ramp = nt.nodes.new("ShaderNodeValToRGB")
    # 實測校準（2026-09-08）：門檻設太低（0.55-0.85）連平坦面的中性 Pointiness 值都會
    # 被遮罩抓到，整個表面都被邊緣色蓋過去，不是只有真正尖銳的邊角——0.7-0.93（medium）
    # 才只圈到真正的凸邊/尖角；heavy 刻意放寬下端點到 0.4，讓遮罩涵蓋更多表面。
    edge_ramp.color_ramp.elements[0].position = preset["edge_lo"]
    edge_ramp.color_ramp.elements[1].position = preset["edge_hi"]
    nt.links.new(geo.outputs["Pointiness"], edge_ramp.inputs["Fac"])
    edge_fac = nt.nodes.new("ShaderNodeMath")
    edge_fac.operation = "MULTIPLY"
    edge_fac.inputs[1].default_value = edge_intensity
    nt.links.new(edge_ramp.outputs["Alpha"], edge_fac.inputs[0])
    edge_mix = nt.nodes.new("ShaderNodeMixRGB")
    edge_mix.inputs["Color2"].default_value = (*edge_color, 1.0)
    nt.links.new(base_socket, edge_mix.inputs["Color1"])
    nt.links.new(edge_fac.outputs["Value"], edge_mix.inputs["Factor"])

    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = ao_distance
    # AO 輸出 1.0=完全曝露、0.0=完全遮蔽——髒污該長在「遮蔽」處，所以 ramp 兩端點的
    # alpha 刻意反過來設（低 Fac→高 alpha），不是預設的黑到白遞增。上端點（dirt_hi）
    # 隨 level 放寬，heavy 讓髒污蔓延到更曝露的面，不是只留在最深的縫隙裡。
    dirt_ramp = nt.nodes.new("ShaderNodeValToRGB")
    dirt_ramp.color_ramp.elements[0].position = 0.0
    dirt_ramp.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    dirt_ramp.color_ramp.elements[1].position = preset["dirt_hi"]
    dirt_ramp.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 0.0)
    nt.links.new(ao.outputs["AO"], dirt_ramp.inputs["Fac"])
    dirt_fac = nt.nodes.new("ShaderNodeMath")
    dirt_fac.operation = "MULTIPLY"
    dirt_fac.inputs[1].default_value = dirt_intensity
    nt.links.new(dirt_ramp.outputs["Alpha"], dirt_fac.inputs[0])
    dirt_mix = nt.nodes.new("ShaderNodeMixRGB")
    dirt_mix.inputs["Color2"].default_value = (*dirt_color, 1.0)
    nt.links.new(edge_mix.outputs["Color"], dirt_mix.inputs["Color1"])
    nt.links.new(dirt_fac.outputs["Value"], dirt_mix.inputs["Factor"])

    nt.links.new(dirt_mix.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


# ---------------------------------------------------------------- 3 渲 2／賽璐璐（NPR）
# 2026-09-13 新增。來源：日式街景 3 渲 2 探測（Blender 5.1.2 headless 實測），完整
# 驗證紀錄與風格色票見 `styles/genre/anime-cel-daylight.md`。這兩支是本檔唯一的
# **非寫實著色** factory，其餘 factory 全是 PBR 路線——不要拿 PBR 材質混搭它們
# （程序化雜訊/凹凸/磨損會直接摧毀平塗色塊）。

CEL_SHADOW_TINT = (0.10, 0.07, 0.22)   # 自動推導暗階時的位移目標（動畫陰影往藍紫跑）
CEL_TINT_MIX = 0.30                    # 暗階往 CEL_SHADOW_TINT 混合的比例
CEL_DEFAULT_STOPS = (0.35, 0.68)       # 中階／亮階在明暗值上的分界


def _cel_band(base: tuple, k: float) -> tuple:
    """由 base 推導同色系的中階/暗階（base×k 再往 CEL_SHADOW_TINT 混）。

    只用在呼叫端「沒有明示 mid/shadow」的場合。風格卡有色票三階時一律直接傳入，
    不要靠這支推導——動畫陰影色是獨立色塊，不是同一色打暗。
    """
    t = CEL_TINT_MIX * (1.0 - k)
    return tuple(max(0.0, min(1.0, base[i] * k + CEL_SHADOW_TINT[i] * t)) for i in range(3))


def make_cel(name: str, base=(0.8, 0.3, 0.28), mid=None, shadow=None,
             stops: tuple = CEL_DEFAULT_STOPS,
             emission_strength: float = 1.0) -> bpy.types.Material:
    """賽璐璐（3 渲 2）平塗材質：Diffuse → ShaderToRGB → CONSTANT ColorRamp → Emission。

    實測（Blender 5.1.2 headless，220x160）：三階輸出的 sRGB 值與傳入的線性色票
    **完全相符**（(0.82,0.30,0.28)/(0.58,0.20,0.30)/(0.30,0.10,0.26) → 實測
    #E89490/#C87C95/#985D8C），畫素高度集中在 3 個色階（top-5 直方圖格佔 96.8%）。
    因為最終輸出走 Emission，**打光不會改變色票**——這是它比 `make_toon()` 可靠的
    根本原因（打光只決定「哪一階落在哪裡」）。

    **兩個必要前提，違反任一個都會「安靜地做錯」（不報錯但結果歪）**：
      1. 渲染引擎必須是 EEVEE。同一組節點丟給 Cycles 不會報錯，但最亮的 base 階
         整個消失、畫面塌到中間階（實測 100% 落在 mid band）。
      2. `scene.view_settings.view_transform` 必須是 'Standard'
         （`build_template.set_view_transform('standard')`）。AgX 下同一個材質的主
         色階實測 #E89490(232,148,144) → #C29490(194,148,144)，紅通道掉 38，且最
         暗階被壓掉。

    mid/shadow 不給時由 `_cel_band()` 推導（同色系打暗 + 往紫位移）；風格卡有色票
    時一律直接傳該卡的三階線性值。
    """
    mid = _cel_band(base, 0.62) if mid is None else mid
    shadow = _cel_band(base, 0.34) if shadow is None else shadow
    if "ShaderNodeShaderToRGB" not in dir(bpy.types):
        _fail("mat_lib", f"{name}: 這個 Blender 版本沒有 ShaderToRGB 節點，make_cel 無法使用")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    dif.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"   # 硬邊界，不做漸層——這是「賽璐璐」的定義
    e0 = ramp.color_ramp.elements[0]
    e0.position, e0.color = 0.0, (*shadow, 1.0)
    e1 = ramp.color_ramp.elements[1]
    e1.position, e1.color = stops[0], (*mid, 1.0)
    e2 = ramp.color_ramp.elements.new(stops[1])
    e2.color = (*base, 1.0)
    emi = nt.nodes.new("ShaderNodeEmission")
    set_socket(emi, ["Strength"], emission_strength)
    nt.links.new(dif.outputs[0], s2rgb.inputs[0])
    nt.links.new(s2rgb.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], emi.inputs["Color"])
    nt.links.new(emi.outputs[0], out.inputs["Surface"])
    eng = getattr(bpy.context.scene.render, "engine", "")
    if "EEVEE" not in eng:
        _log("mat_lib", f"WARNING: {name} 是 cel 材質但引擎是 {eng}——ShaderToRGB 只在 "
                        f"EEVEE 有意義，Cycles 下不報錯但色階會歪（見 docstring）")
    return mat


def make_cel_advanced(name: str, base=(0.72, 0.70, 0.66), mid=None, shadow=None,
                      high=None, rim_color=(0.30, 0.45, 0.70),
                      rim_strength: float = 0.45, rim_power: float = 3.0,
                      ao_distance: float = 0.6, ao_strength: float = 1.0,
                      stops: tuple = (0.28, 0.31),
                      emission_strength: float = 1.0) -> bpy.types.Material:
    """進階賽璐璐（ZZZ／原神級「漸層 cel」）：硬陰影邊界 + 受光帶內漸層 + AO 接觸陰影 + Facing 邊緣光。

    與 `make_cel()`（純平塗三階）的差別——現代二遊（絕區零／原神）已不是傳統二分
    陰影：陰影邊界仍是硬的，但**受光面內部有一段柔和漸層**（mid→high），加上縫隙處
    的 AO 接觸陰影與面向鏡頭的冷色邊緣光，畫面才有「高級感」而不是塑膠平塗。
    實測（Blender 5.1.2 headless，`.capybala/test-scripts/zzz_look_proto.py` A/B 同框）：
    左舊式 CONSTANT 三階 vs 右本函式——受光面漸層、圓柱曲面上的明暗過渡、物件落地處
    的接觸陰影三者皆可見，且陰影邊界維持硬邊。

    節點鏈：Diffuse → ShaderToRGB → RGBToBW → ColorRamp(LINEAR, 4 stops:
    shadow@0 / shadow@stops[0] / mid@stops[1] / high@1) → AO×MapRange → MULTIPLY
    → LayerWeight.Facing^rim_power×rim_strength → ADD(rim_color) → Emission。
    stops[0]→stops[1] 的窄間隔（預設 0.28→0.31）就是「硬邊界」；stops[1]→1.0 的
    長間隔就是受光帶內的柔和漸層。

    必要前提同 `make_cel()`：EEVEE + view_transform='Standard'，違反會安靜地做錯。
    色票哲學見 `styles/genre/anime-cel-daylight.md` 的「進階路線」段：環境走**低飽和
    灰底**、焦點物件才給高飽和色——本函式的預設 base 就是灰底，不是舊卡的米白。
    """
    mid = base if mid is None else mid
    shadow = _cel_band(base, 0.45) if shadow is None else shadow
    high = tuple(min(1.0, base[i] * 1.18 + 0.02) for i in range(3)) if high is None else high
    if "ShaderNodeShaderToRGB" not in dir(bpy.types):
        _fail("mat_lib", f"{name}: 這個 Blender 版本沒有 ShaderToRGB 節點，make_cel_advanced 無法使用")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    dif.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "LINEAR"
    cr.elements[0].position, cr.elements[0].color = 0.0, (*shadow, 1.0)
    cr.elements[1].position, cr.elements[1].color = stops[0], (*shadow, 1.0)
    e_mid = cr.elements.new(stops[1])
    e_mid.color = (*mid, 1.0)
    e_high = cr.elements.new(1.0)
    e_high.color = (*high, 1.0)
    nt.links.new(dif.outputs[0], s2rgb.inputs[0])
    nt.links.new(s2rgb.outputs[0], bw.inputs[0])
    nt.links.new(bw.outputs[0], ramp.inputs[0])
    last = ramp.outputs[0]
    if ao_strength > 0.0:
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = ao_distance
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 1.0 - 0.45 * ao_strength
        mr.inputs["To Max"].default_value = 1.0
        comb = nt.nodes.new("ShaderNodeCombineColor")
        mult = nt.nodes.new("ShaderNodeMixRGB")
        mult.blend_type = "MULTIPLY"
        mult.inputs["Fac"].default_value = 1.0
        nt.links.new(ao.outputs["AO"], mr.inputs["Value"])
        for i in range(3):
            nt.links.new(mr.outputs[0], comb.inputs[i])
        nt.links.new(last, mult.inputs["Color1"])
        nt.links.new(comb.outputs[0], mult.inputs["Color2"])
        last = mult.outputs[0]
    if rim_strength > 0.0:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.35
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = rim_power
        sc = nt.nodes.new("ShaderNodeMath")
        sc.operation = "MULTIPLY"
        sc.inputs[1].default_value = rim_strength
        add = nt.nodes.new("ShaderNodeMixRGB")
        add.blend_type = "ADD"
        add.inputs["Color2"].default_value = (*rim_color, 1.0)
        nt.links.new(lw.outputs["Facing"], pw.inputs[0])
        nt.links.new(pw.outputs[0], sc.inputs[0])
        nt.links.new(sc.outputs[0], add.inputs["Fac"])
        nt.links.new(last, add.inputs["Color1"])
        last = add.outputs[0]
    emi = nt.nodes.new("ShaderNodeEmission")
    set_socket(emi, ["Strength"], emission_strength)
    nt.links.new(last, emi.inputs["Color"])
    nt.links.new(emi.outputs[0], out.inputs["Surface"])
    eng = getattr(bpy.context.scene.render, "engine", "")
    if "EEVEE" not in eng:
        _log("mat_lib", f"WARNING: {name} 是 cel 材質但引擎是 {eng}——ShaderToRGB 只在 "
                        f"EEVEE 有意義，Cycles 下不報錯但色階會歪（見 make_cel docstring）")
    return mat


def make_toon(name: str, base=(0.8, 0.3, 0.28), size: float = 0.5,
              smooth: float = 0.0, component: str = "DIFFUSE") -> bpy.types.Material:
    """Toon BSDF 平塗材質（3 渲 2 的 **Cycles 備援路線**）。

    實測（Blender 5.1.2 headless）：`ShaderNodeBsdfToon` 在 Cycles 下可渲染、可出階
    （實測 9 個亮度帶），但**最亮階會被推爆成近白**（SUN energy 3.0 + Standard 下測
    到 (255,187,180)，紅色主色階消失）。走這條路線請把 SUN 能量壓到 1.2-1.8，或直接
    改用 `make_cel()`（EEVEE + ShaderToRGB，色票一比一）。

    限制：Toon BSDF 只有一個 Color 輸入，做不出「陰影往紫位移」的獨立色塊——陰影就是
    同一色打暗。需要三階獨立色票時只能用 `make_cel()`。
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    t = nt.nodes.new("ShaderNodeBsdfToon")
    t.inputs["Color"].default_value = (*base, 1.0)
    try:
        t.component = component
    except (AttributeError, TypeError):
        _log("mat_lib", f"WARNING: {name} 的 Toon BSDF 不接受 component='{component}'，沿用預設")
    set_socket(t, ["Size"], size)
    set_socket(t, ["Smooth"], smooth)
    nt.links.new(t.outputs[0], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------- 背面法外輪廓（3 渲 2）


def make_cel_outline(name: str, color=(0.020, 0.018, 0.032), mode: str = "cull",
                     strength: float = 1.0) -> bpy.types.Material:
    """背面法（inverse hull）外輪廓線材質——**只畫背面**的平塗線色。

    《罪惡裝備》系列自 Xrd 起所有旗艦作品都用這個技法畫輪廓線（官方 CEDEC2024 講題
    就叫「背面法」，他們自己說這手法已經用了 20 年以上、至今仍在第一線）。原理：複製
    同一份 mesh、沿法線往外推，然後**只渲染它的背面**——外推出去的部分在剪影處露出來
    就成了一條線。線寬由「推多遠」決定，與貼圖解析度無關，拉到特寫也不糊。

    **Blender 不支援 multipass shader**（官方教材的環境對照表明載 Blender ✕），
    所以「同一份 mesh 用 shader 畫兩次」在 Blender 走不通，必須複製**真幾何**——
    也就是 `build_template.make_outline_shell()`。本函式只管材質。

    `mode` 兩種，效果都是只讓背面通過：
      - `'cull'`（預設）：開 `use_backface_culling`，**要求外殼 mesh 的法線已被反轉**
        （`make_outline_shell()` 會翻）。正面被剔除、背面留下，成本最低。
      - `'backfacing'`：用 `Geometry.Backfacing` 在 shader 內把正面切成全透明，
        不依賴剔除行為、外殼法線**不用**反轉。相容性最好，代價是每個像素多一次分支。

    顏色給**線性**值（`hex_to_linear('#14121C')`），預設近黑偏冷紫——日式卡渲的線色
    慣例不是純黑，純黑會讓線讀成剪紙。線色走 Emission、不受燈光影響，與 cel 材質同一
    套哲學（打光只決定色階落點，不改變色票）。

    **反轉了面法線卻沒有只畫背面，外殼會整片蓋住母體**——這正是舊版本「反轉外殼實測
    7 種寫法 0 種畫得出來、其中 4 種還把高光階整片吃掉」的原因，缺的就是這一步。
    """
    if mode not in ("cull", "backfacing"):
        _fail("mat_lib", f"{name}: mode 只能是 'cull'/'backfacing'（收到 {mode}）")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (*color, 1.0)
    set_socket(emi, ["Strength"], strength)
    if mode == "cull":
        nt.links.new(emi.outputs[0], out.inputs["Surface"])
        mat.use_backface_culling = True
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(emi.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        # EEVEE 的透明排序設定：4.2 起叫 surface_render_method，4.1 以前叫 blend_method。
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            if hasattr(mat, attr):
                try:
                    setattr(mat, attr, val)
                except (TypeError, AttributeError) as e:
                    _log("mat_lib", f"WARNING: {name} 設定 {attr} 失敗（{e}），沿用預設")
                break
    return mat


def cel_shadow_color(base: tuple, hue_shift: float = -18.0,
                     sat_gain: float = 1.30, val_gain: float = 0.52) -> tuple:
    """由 base 色票推導「設計過的」陰影色——暗部是獨立色塊，不是同一色打暗。

    日式卡渲的陰影色是有設計的：**暗部要提飽和、色相往冷側位移**（暖色系的陰影偏紅、
    冷色系偏藍紫），否則暗面會讀成「髒掉」而不是「另一個顏色」。官方教材舉的例子是
    動畫現場的「色彩設計」——皮膚的陰影偏紅、布料的陰影偏洗舊色。《藍色協議》在
    CEDEC2021 把這件事拆成 HSV 的分段修正：先轉 HSV，依原始明度決定飽和/明度的補正
    幅度（越暗補越多，暗部才不會整片糊掉），色相再依冷暖區間位移。

    本函式是那套做法的簡化版（純數學、不碰 bpy）：`base` 吃**線性**色票，回傳**線性**
    陰影色。`hue_shift` 單位度（負＝往暖/紅側、正＝往藍紫側）；`sat_gain` 是飽和度
    倍率、且**依原色明度自動放大**（`1 + (sat_gain-1)·(1-V)`，暗色補更多）；
    `val_gain` 是明度倍率。近灰的顏色（S≈0）色相位移無意義，會自動給一點冷紫偏移，
    免得灰暗部讀成純黑。

    用途：風格卡只給 base 色票時，用這支生成陰影色再傳給 `make_cel()`/`make_cel_advanced()`
    的 `shadow=`；比 `_cel_band()` 的固定混色更能對應不同色系。三階都已經定好的色票
    就直接傳，不要繞這一圈。
    """
    def lin_to_srgb(c):
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055

    def srgb_to_lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    srgb = [max(0.0, min(1.0, lin_to_srgb(max(0.0, min(1.0, base[i]))))) for i in range(3)]
    h, s, v = colorsys.rgb_to_hsv(*srgb)
    if s < 0.02:              # 近灰：色相位移無意義，直接給一點冷紫，避免暗部變純黑
        s = 0.06
        h = 0.72
    else:
        h = (h + hue_shift / 360.0) % 1.0
        s = min(1.0, s * (1.0 + (sat_gain - 1.0) * (1.0 - v)))
    v = max(0.0, min(1.0, v * val_gain))
    out = colorsys.hsv_to_rgb(h, s, v)
    return tuple(srgb_to_lin(c) for c in out)


# ---------------------------------------------------------------- 註冊表（風格卡引用用）

FACTORIES = {
    "metal": make_metal, "brushed_metal": make_brushed_metal, "anodized": make_anodized,
    "leather": make_leather, "fabric": make_fabric, "wood": make_wood,
    "concrete": make_concrete, "stone": make_stone, "glass": make_glass,
    "coated_glass": make_coated_glass, "plastic": make_plastic, "rubber": make_rubber,
    "paint": make_paint, "emissive": make_emissive,
    # 2026-09-09 新增（環境地景 + 磚/陶瓷/特殊玻璃/複合材料，見上方各 factory 的新增背景註解）
    "water": make_water, "grass": make_grass, "soil": make_soil, "asphalt": make_asphalt,
    "brick": make_brick, "ceramic": make_ceramic, "frosted_glass": make_frosted_glass,
    "carbon_fiber": make_carbon_fiber,
    # 2026-09-13 新增（非寫實著色，見上方 3 渲 2 段落）
    "cel": make_cel, "cel_advanced": make_cel_advanced, "toon": make_toon,
    # 2026-09-13 新增（背面法外輪廓，配 build_template.make_outline_shell/setup_inverse_hull）
    "cel_outline": make_cel_outline,
}


def build_all(prefix: str = "Mat_Lib") -> dict:
    """一次建齊全部 factory 的示範材質（冒煙測試/風格預覽用）；回傳 name→Material。"""
    mats = {}
    for key, fn in FACTORIES.items():
        mats[f"{prefix}_{key}"] = fn(f"{prefix}_{key}")
    _log("mat_lib", f"build_all 建齊 {len(mats)} 種")
    return mats
