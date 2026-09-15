# KEYWORDS: blender, bpy, bmesh, building, facade, window grid, procedural architecture, 建築, 立面, 窗格, 程序化建築
"""building_lib.py — 程序化建築立面生成（凍結模組，與 shape_lib.py/road_lib.py 同級）。

範圍（bpy 進階技巧調研，2026-09-08）：查證確認真正做「參數化樓層/窗格立面生成」的
外掛（ProceduralBuildingGenerator 等）都是 GPL 授權——不能照抄程式碼（本 repo 授權
政策只准 MIT/Apache/BSD），這裡是**從公開概念重寫**的獨立實作：把建築的四面牆各自
建成 floors×bays 網格，逐格用 `bmesh.ops.inset_individual()` 內縮+往內推出負景深，
一次操作同時做出「窗框」跟「窗戶內凹」兩件事（真實建築的窗戶幾乎都比牆面本身內縮
幾公分，純平面貼窗戶紋理在斜角光線下會立刻穿幫，這是本函式存在的理由）。

只做「單棟量體、規則格狀立面」——不做曲面/非矩形平面建築、不做結構性構件（梁柱/
樓板厚度可見的剖面），這些是額外的建模範疇，超出「補窗格立面生成缺口」這個明確
目標。真正需要複雜建築造型時，本函式的量體可以當作 shape_lib.py 進一步雕塑的起點
（例如再用 taper() 收分做退縮式摩天大樓輪廓）。

材質：`wall_mat`/`window_mat` 兩個參數直接傳現成的 `bpy.types.Material`（例如
`mat_lib.make_concrete()`/`make_glass()` 的產物），函式自己 append 到正確的
material_index 順序，不需要、也**不要**呼叫端事後自己 `obj.data.materials.clear()`
再 append——實測抓到一個真正的 Blender API 陷阱：`mesh.materials.clear()` 會把
**所有面的 material_index 重設成 0**，即使原本清空前一個材質都沒有（這支函式
回傳的是全新 mesh，本來就零材質槽，沒有東西需要清）。這條陷阱之前在
`add_procedural_wear()`/`road_lib.add_lane_markings()` 學到的「先清空再 append
避免殘留空槽」的既有慣例，套用在**這支函式的回傳物件上是相反的錯誤**——那兩支
函式清的是「別的操作留下的殘留材質槽」，這支函式從一開始就沒有殘留物，`.clear()`
在這裡只會把本函式辛苦分好的窗戶/牆面材質索引全部抹平成牆面，窗戶「消失」
（不是幾何消失，是材質索引消失，肉眼看渲染圖窗戶跟牆面同一個顏色）。

驗證：Blender 5.1.2 headless（2026-09-08）：4 面牆 floors×bays 網格頂點數/面數用
公式反推驗證（非目測）、`bmesh.ops.recalc_face_normals()` 後用實際法向量方向確認
四面牆法向量正確朝外（不是隨機朝向，錯誤朝向會讓 inset 往外凸而非內凹）、渲染圖
肉眼確認窗格排列規則且有真實內凹深度陰影（不是平貼紋理的假窗）。

2026-09-09 新增（建築外觀實測，見 `anatomy/buildings/_INDEX.md`）：

- `assemble_building(width, depth, floor_specs, name, bays)`——由下而上逐層組裝，
  取代 `generate_facade()` 整棟套用同一個網格的做法，`floor_specs` 允許每層
  各自決定窗比例/內縮深度/材質，做出中段變化的立面節奏。**`bays` 一律整棟
  單一參數，不能逐層變化**——實測抓到真實 bug：早期版本允許逐層不同 bays，
  混用 3 種 bays 產生 144 條非流形邊（樓層交界頂點對不上），改成單一參數後
  歸零。材質索引指派改用「inset 操作前後的面集合差集」直接抓出每層新產生的
  窗框面（不是猜測 z 座標範圍屬於哪一層——多樓層材質不同時，猜測法在樓層
  交界的浮點誤差邊界容易出錯，因果關係法完全不會錯）。已用 15 層混合材質的
  測試塔驗證：Z 高度加總精確吻合、各樓層牆面材質索引各自正確（不會互相污染）、
  0 非流形邊。
- `make_entrance_canopy()`/`add_balcony()`/`add_ac_units()`——一樓雨遮、住宅
  懸挑陽台、冷氣機（依查證數據預設加開放式百葉而非密封罩，密封罩會讓散熱
  效率降最多 34%）。三支都是獨立於樓體 mesh 之外的附加構件（真實建築這些
  本來就是結構獨立的附加物，不需要修改/重新開洞樓體本身）。已用組裝一棟含
  一樓雨遮+12 個陽台+12 台冷氣機（含百葉）的完整住宅塔樓驗證：物件計數、
  頂點數、雨遮的世界座標範圍（確認掛在建築正面外側，不是穿進樓體內部）
  全部數值正確；渲染圖肉眼確認一樓雨遮、標準層陽台/冷氣機交錯排列位置正確。
- `make_pitched_roof(width, depth, wall_top_z, ridge_height, eave_overhang, style,
  roof_mat, gable_wall_mat, name)`——真正的斜屋頂量體（查證結論直接產物：歐風
  建築的孟莎/斜屋頂、日式建築的破風/寄棟屋頂都需要真正的斜屋頂幾何，平頂+
  裝飾線腳做不出這兩種風格的觀感，見 `anatomy/buildings/european.md`/
  `japanese_house.md`）。技法跟 §13.10 車體工作流「切一圈新邊→移動頂段頂點」
  是同一套邏輯，只是建成獨立量體（懸挑超出牆面，不跟牆體共用頂點）。
  `style='gable'`（雙坡+封起的三角形山牆）或 `'hip'`（四坡收頭，寬深比極端
  時自動退化成四角錐攢尖頂，不需要呼叫端判斷）。**已知的、刻意的設計**：
  回傳物件是開放底面的殼（只有屋頂本身，底部跟牆體交界處沒有面）——流形
  檢查會看到固定 4 條邊界邊（屋簷底部那一圈），這不是 bug，是「屋頂坐在
  牆體上」這個組裝方式的自然結果，不要誤判成需要修的非流形問題；如果邊界邊
  數量不是 4（例如出現額外的內部非流形邊），那才是真正的問題。已用
  gable/hip 兩種 style 各自驗證：頂點/面數、Z 高度範圍精確符合 wall_top_z+
  ridge_height、X 範圍精確符合 eave_overhang 懸挑量、邊界邊數量精確等於 4、
  且確認沒有任何邊被 >2 個面共用（真正的拓樸錯誤指標）；渲染圖肉眼確認
  懸挑屋頂+封閉山牆的輪廓清楚可辨識為「有斜屋頂的房子」，不是方塊量體。

2026-09-11 新增：`even_bays()`（目標模矩 → 格數＋均分單位長度，立面柱網/節奏間距用）、
`assemble_building(..., bay_target=, base_z=)`（前者改給「希望的柱距」自動反推格數，
後者讓本函式以指定 z 起算，支援基座/裙樓式疊層量體）、`make_lightning_rod()`（屋頂
避雷針＋頂端航空障礙燈，含自發光紅燈的預設材質與日光下的讀色陷阱說明）。

匯入慣例：import building_lib as BL
"""
import random

import bmesh
import bpy
from mathutils import Vector


def even_bays(length: float, target: float) -> tuple:
    """目標模矩 → `(格數, 每格實際單位長度)`（2026-09-11 新增）。

    做法：`count = max(1, round(length / target))`、`unit = length / count`——呼叫端給
    「希望的間距」而不是硬寫格數，反推格數後把長度**均分**，所以圖案在角邊永遠收得
    乾淨，改樓寬時不必回頭調其他常數（固定格數的寫法在樓寬變動時會在角落留殘料細條，
    或者整排窗格被不均勻地拉扯）。`target` 本身可以是費波那契數（§15.2 細節節奏）。

    回傳 `(count:int, unit:float)`；`length`/`target` 非正數即 raise（不靜默回傳 0）。
    """
    if length <= 0 or target <= 0:
        raise ValueError(f"even_bays: length/target 需為正數（收到 {length}/{target}）")
    count = max(1, round(length / target))
    return count, length / count


def generate_facade(width: float, depth: float, height: float, floors: int, bays: int,
                    window_ratio: float = 0.65, recess: float = 0.08, name: str = "Building",
                    wall_mat=None, window_mat=None):
    """建一棟長方體量體，四面外牆各自劃分成 floors（垂直，樓層數）× bays（水平，
    開間數）的窗格網格，每格內縮出一個真正凹陷的窗戶（不是平貼紋理）。

    參數順序刻意採 (width, depth, height) 對應世界座標 (X, Y, Z) 軸序——跟
    `add_box()` 的 `size` tuple 是同一個 XYZ 慣例，不要憑直覺套用「寬高深」
    的口語順序（這支函式第一版就是這樣寫錯的，測試時實測抓到：Y/Z 兩軸的
    實際範圍互換，因為呼叫端跟函式簽名對這兩個字的順序認知不一致——這正是
    這份調研報告一直在強調的「盲寫程式碼容易犯的錯」的活生生案例，用參數
    順序跟既有慣例對齊來從源頭消除，而不是靠呼叫端自己小心）。

    width/depth：建築水平方向的兩個軸長（公尺，width 對應前後牆寬度=X 軸、
    depth 對應左右牆寬度=Y 軸）。height：建築總高（Z 軸）。floors：樓層數
    （每層一排窗格，樓層高度 =
    height/floors，本函式不支援不等樓層高，需要的話呼叫端事後用 shape_lib 手動
    調整個別頂點）。bays：每層每面牆的開間數（窗格數）。

    window_ratio：每格裡「窗戶部分」占格子面積的邊長比例（0~1，例如 0.65 代表
    窗戶邊長是格子邊長的 65%，四周留 17.5% 當窗框/牆墩）。recess：窗戶內縮深度
    （公尺，沿牆面法向量往建築內部推——這個深度是視覺上「看得出來有凹陷」的
    關鍵參數，太小（<0.03m）在中景以上幾乎看不出差異）。

    回傳建好的 obj（材質索引 0=牆面、1=窗戶，見檔頭材質索引慣例說明）。
    """
    if floors < 1 or bays < 1:
        raise ValueError("generate_facade: floors/bays 必須 >= 1")

    bm = bmesh.new()
    vert_cache = {}

    def get_vert(co):
        key = (round(co.x, 6), round(co.y, 6), round(co.z, 6))
        v = vert_cache.get(key)
        if v is None:
            v = bm.verts.new(co)
            vert_cache[key] = v
        return v

    def build_wall(to_world):
        """to_world(u_frac, v_frac) -> Vector，u_frac/v_frac 各為 0~1 的格線參數。
        u 對應這面牆自己的水平方向（bays 分段），v 對應垂直方向（floors 分段）。
        共用頂點快取確保相鄰牆在共同角落焊接成同一個頂點，不留接縫。
        """
        us = [i / bays for i in range(bays + 1)]
        vs = [j / floors for j in range(floors + 1)]
        grid = [[get_vert(to_world(u, v)) for v in vs] for u in us]
        wall_faces = []
        for i in range(bays):
            for j in range(floors):
                f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
                wall_faces.append(f)
        return wall_faces

    all_window_faces = []
    # 四面牆：u_frac 沿各自的水平軸，v_frac 沿共同的高度軸。
    all_window_faces += build_wall(lambda u, v: Vector((u * width, 0.0, v * height)))          # front (y=0)
    all_window_faces += build_wall(lambda u, v: Vector(((1 - u) * width, depth, v * height)))  # back (y=depth)
    all_window_faces += build_wall(lambda u, v: Vector((0.0, (1 - u) * depth, v * height)))    # left (x=0)
    all_window_faces += build_wall(lambda u, v: Vector((width, u * depth, v * height)))        # right (x=width)

    # 屋頂/地板封面：早期版本只用 4 個角頂點封一個大四邊面，實測抓到這樣封不對——
    # 牆面頂/底排是 bays+1 個頂點的細分邊（每個 bay 一段），跟只有 4 個角的大面
    # 邊界對不上（T-junction），量出 56 條「只被 1 個面用到」的非流形邊，全部
    # 精確落在 z=0/z=height。修法：屋頂/地板改成貼著牆面頂/底排實際頂點走一圈
    # 的 n-gon，跟 build_wall() 用同一組 `us` 分段、同一個 get_vert() 快取，
    # 保證焊接到牆面已經建好的同一批頂點，不是另外生一批對不上的新頂點。
    us = [i / bays for i in range(bays + 1)]

    def perimeter_loop(v_target):
        loop = []
        for u in us[:-1]:
            loop.append(get_vert(Vector((u * width, 0.0, v_target * height))))          # front
        for u in us[:-1]:
            loop.append(get_vert(Vector((width, u * depth, v_target * height))))        # right
        for u in us[:-1]:
            loop.append(get_vert(Vector(((1 - u) * width, depth, v_target * height))))  # back
        for u in us[:-1]:
            loop.append(get_vert(Vector((0.0, (1 - u) * depth, v_target * height))))    # left
        return loop

    bm.faces.new(perimeter_loop(1.0))                    # roof
    bm.faces.new(list(reversed(perimeter_loop(0.0))))    # floor (reversed winding, fixed up below anyway)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    margin = (1.0 - window_ratio) / 2.0
    thickness_per_face = []
    for f in all_window_faces:
        # inset_individual 的 thickness 是絕對長度，不是比例——每格尺寸可能因
        # floors/bays 不整除而略有差異，這裡用該面實際邊長換算，保證每格的窗框
        # 寬度視覺上一致，不是套用同一個絕對數字導致格子大小不一時窗框粗細不均。
        edge_len = (f.verts[1].co - f.verts[0].co).length
        thickness_per_face.append(edge_len * margin)
    avg_thickness = sum(thickness_per_face) / len(thickness_per_face) if thickness_per_face else 0.0
    # 實測釐清 inset_individual() 語意（bmesh 官方文件沒寫清楚，靠實測探到）：
    # 回傳值 `result['faces']` 是新長出來的「窗框側壁」環狀面，原本傳進去的
    # all_window_faces 參照在操作後**仍然有效**，且變成內縮+推入後的「窗戶
    # 玻璃面」本身——一開始猜反了，以為原參照會失效改用回傳值，結果回傳值
    # 才是窗框、原參照才是窗戶，兩個都各自實測驗證過才確定下來。
    bmesh.ops.inset_individual(bm, faces=all_window_faces, thickness=avg_thickness,
                               depth=-abs(recess), use_even_offset=True)
    window_face_set = set(all_window_faces)
    for f in bm.faces:
        f.material_index = 1 if f in window_face_set else 0

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # 材質槽一律由本函式自己 append（見檔頭「材質」段落的 .clear() 陷阱說明）——
    # 這是全新 mesh，從來沒有材質槽，呼叫端不需要、也不該事後自己清空再 append。
    mesh.materials.append(wall_mat or _default_wall_mat())
    mesh.materials.append(window_mat or _default_window_mat())
    return obj


def _mat_index(materials, mat):
    """把 mat 加進 materials 列表（不重複——用物件 identity 比對，不是名稱字串），
    回傳它在列表裡的索引。多樓層/多構件共用同一個 wall_mat 物件時，重複呼叫這支
    只會拿到同一個索引，不會疊出重複材質槽。
    """
    for i, m in enumerate(materials):
        if m is mat:
            return i
    materials.append(mat)
    return len(materials) - 1


def assemble_building(width: float, depth: float, floor_specs: list, name: str = "Building",
                      bays: int | None = None, bay_target: float | None = None,
                      base_z: float = 0.0):
    """由下而上逐層堆疊組裝建築量體——取代 `generate_facade()` 整棟套用同一個
    網格的做法，`floor_specs` 允許每一層各自決定窗比例/內縮深度/材質，做出「中間
    樓層交錯變化」的立面節奏（例如中段一圈材質不同的腰帶樓層、頂樓窗比例縮小）
    ，對齊真實建築設計常見手法：整段標準層規則重複，特定分區換一種窗格/材質，
    不是逐層隨機打亂。

    **`bays`（開間數/柱網分格）是整棟建築單一參數，不是逐層可調**——這是刻意的
    設計限制，不是能力不足：實測發現若允許每層各自不同的 bays，相鄰樓層的牆面
    網格分格數不一樣，樓層交界處的頂點無法對齊焊接，會產生大量非流形邊（跟
    `generate_facade()` 修過的屋頂/地板 T-junction 是同一類問題，只是這裡發生
    在每一個 bays 改變的樓層交界，不是只有頂/底兩處）。真實建築的結構柱網本來
    就是整棟一致的，樓層之間變化的通常是窗比例/材質/退縮深度，不是柱距本身
    ——這個限制其實更貼近真實建築邏輯，不是妥協。

    **`bay_target`（2026-09-11 新增）**：改給「希望的柱距」而不是硬寫格數——內部走
    `even_bays(width, bay_target)` 反推格數再把樓寬均分，所以改樓寬時圖案自動在角邊
    收齊，不必回頭重算 bays（固定格數的寫法在樓寬變動時會在角落留殘料細條）。
    給了 `bay_target` 就以它為準、`bays` 被忽略；兩者都沒給則沿用 `bays=6`。

    **`base_z`（2026-09-11 新增）**：本函式由 `z=base_z` 起算樓層堆疊（預設 0.0），
    回傳的 `floor_z_offsets` 也帶這個偏移。用途是**基座/裙樓式量體**——一樓（或低樓層
    裙樓）平面尺寸比上方塔樓大的建築大量存在（基座提供門廳/商業空間的大面積，塔樓
    只佔基地一部分），做法是呼叫本函式兩次：先建低矮的裙樓量體（較大的 width/depth、
    `base_z=0`），再把塔樓量體以 `base_z=裙樓總高` 疊上去（較小的 width/depth），
    兩者各自是獨立 mesh、共用同一個基準平面。沒有這個參數時，第二個量體只會從地面
    重新長一次，跟裙樓完全重疊。

    floor_specs：由下而上排列的 dict 清單，每個 dict 可含：
        height（樓層高度，公尺，必要）
        window_ratio（預設 0.6）
        recess（預設 0.12）
        wall_mat/window_mat（該層材質，留空繼承**目前為止最後一個有指定值的樓層**
        ——這樣呼叫端只需要在材質真的换的那一層寫一次，不必每個 dict 都重複填）
        window_variant_mat/window_variant_prob（2026-09-09 新增，選填；住宅大樓
        參考案例：約 13% 窗戶隨機換成帶自發光的暖色玻璃模擬「已入住」，見
        `residential.md`「隨機已入住暖光窗」MUST 列）——原本 window_mat 只能整層
        統一，這兩個參數讓同一層裡的個別窗格（bay）有 `window_variant_prob` 的
        機率改用 `window_variant_mat`，其餘仍用 window_mat；不給 window_variant_mat
        就完全不啟用，行為跟舊版一致。呼叫端要可重現的話記得自己先 `random.seed()`。

    回傳 (obj, floor_z_offsets)：floor_z_offsets 是每層樓**底部**世界 z 高度的
    清單（跟 floor_specs 一一對應），供 `add_balcony()`/`add_ac_units()` 這類
    「在第幾層做什麼」的函式使用，呼叫端不需要自己重新累加樓層高度。

    已知限制：跟 `generate_facade()` 一樣只做規則矩形平面——單次呼叫不支援「同一棟
    內部的平面尺寸變化」。**基座/裙樓式（一樓比樓上大）用 `base_z` 疊兩個獨立量體
    達成**（見上方 `base_z` 段落）；**上窄下寬的退縮式輪廓**則在組裝完整棟之後再用
    `shape_lib.taper()`/`loop_cut()`+`move_verts()` 對整體量體後製雕塑，不要企圖
    在這支函式內部處理平面尺寸變化。
    """
    if not floor_specs:
        raise ValueError("assemble_building: floor_specs 不可為空")
    if bay_target is not None:
        # 目標模矩優先：給「希望的柱距」比硬寫格數耐用（見 even_bays()）
        bays, _bay_unit = even_bays(width, bay_target)
    if bays is None:
        bays = 6
    if bays < 1:
        raise ValueError("assemble_building: bays 必須 >= 1")

    bm = bmesh.new()
    vert_cache = {}

    def get_vert(co):
        key = (round(co.x, 6), round(co.y, 6), round(co.z, 6))
        v = vert_cache.get(key)
        if v is None:
            v = bm.verts.new(co)
            vert_cache[key] = v
        return v

    materials: list = []
    floor_z_offsets = []
    z = base_z
    last_wall_mat = None
    last_window_mat = None

    for spec in floor_specs:
        h = spec.get("height")
        if not h or h <= 0:
            raise ValueError(f"assemble_building: floor_specs 每項都需要正數 height，收到 {spec}")
        window_ratio = spec.get("window_ratio", 0.6)
        recess = spec.get("recess", 0.12)
        wall_mat = spec.get("wall_mat") or last_wall_mat or _default_wall_mat()
        window_mat = spec.get("window_mat") or last_window_mat or _default_window_mat()
        last_wall_mat, last_window_mat = wall_mat, window_mat
        window_variant_mat = spec.get("window_variant_mat")
        window_variant_prob = spec.get("window_variant_prob", 0.0)

        floor_z_offsets.append(z)
        z0, z1 = z, z + h
        us = [i / bays for i in range(bays + 1)]

        def build_wall(to_world):
            grid = [[get_vert(to_world(u, v)) for v in (0.0, 1.0)] for u in us]
            faces = []
            for i in range(bays):
                f = bm.faces.new((grid[i][0], grid[i + 1][0], grid[i + 1][1], grid[i][1]))
                faces.append(f)
            return faces

        floor_window_faces = []
        floor_window_faces += build_wall(lambda u, v, z0=z0, z1=z1: Vector((u * width, 0.0, z0 + v * (z1 - z0))))
        floor_window_faces += build_wall(lambda u, v, z0=z0, z1=z1: Vector(((1 - u) * width, depth, z0 + v * (z1 - z0))))
        floor_window_faces += build_wall(lambda u, v, z0=z0, z1=z1: Vector((0.0, (1 - u) * depth, z0 + v * (z1 - z0))))
        floor_window_faces += build_wall(lambda u, v, z0=z0, z1=z1: Vector((width, u * depth, z0 + v * (z1 - z0))))

        # A freshly bm.faces.new()-created face has a NULL (0,0,0) normal until something
        # explicitly computes one — this function only called recalc_face_normals() once, at
        # the very end on the whole finished mesh (after the roof/floor caps), which is too late
        # for inset_individual() below: its `depth` argument moves the inset face along THIS
        # face's *current* normal, and multiplying by a zero-length normal is a silent no-op.
        # Real-world symptom (2026-09-09, found via a commercial-tower skill-compliance check):
        # thickness/depth both evaluate as if they were 0 — the "window" stays the full,
        # unshrunk, unrecessed bay face and the "frame" faces inset_individual still creates
        # collapse to zero-area — CALIB/assertions all still PASS (nothing here raises or
        # measures recess depth) and the render can still look plausible from a distance, so
        # this went undetected until someone opened the .blend and measured vertex coordinates.
        # Recalculating just this floor's faces (not the whole bm) keeps this cheap per iteration.
        bmesh.ops.recalc_face_normals(bm, faces=floor_window_faces)

        margin = (1.0 - window_ratio) / 2.0
        thicknesses = [(f.verts[1].co - f.verts[0].co).length * margin for f in floor_window_faces]
        avg_thickness = sum(thicknesses) / len(thicknesses) if thicknesses else 0.0
        wall_idx = _mat_index(materials, wall_mat)
        window_idx = _mat_index(materials, window_mat)
        if avg_thickness > 0:
            # inset_individual 只新增面、從不刪除已存在的面（實測釐清，見
            # generate_facade() docstring）——用「操作前的面集合」差集抓出這一輪
            # 新長出的窗框環側壁面，直接指到**這一層自己的** wall_idx。不用事後
            # 憑 z 座標範圍去猜哪個面屬於哪一層——每層材質可能不同，猜測法容易
            # 在樓層交界的浮點誤差邊界上出錯，直接用操作本身的因果關係最可靠。
            faces_before = set(bm.faces)
            bmesh.ops.inset_individual(bm, faces=floor_window_faces, thickness=avg_thickness,
                                       depth=-abs(recess), use_even_offset=True)
            new_frame_faces = set(bm.faces) - faces_before
            for f in new_frame_faces:
                f.material_index = wall_idx
        variant_idx = _mat_index(materials, window_variant_mat) if window_variant_mat else None
        for f in floor_window_faces:
            f.material_index = (variant_idx if variant_idx is not None and random.random() < window_variant_prob
                                else window_idx)
        z = z1

    # 用最後一組材質當屋頂/地板封面材質（頂/底面不屬於任何一層的牆，沒有天然
    # 歸屬，用整棟最後使用的牆面材質收尾，符合「屋頂顏色跟頂樓外牆一致」的
    # 一般直覺）。
    roof_wall_idx = _mat_index(materials, last_wall_mat)

    def perimeter_loop(z_target):
        us = [i / bays for i in range(bays + 1)]
        loop = []
        for u in us[:-1]:
            loop.append(get_vert(Vector((u * width, 0.0, z_target))))
        for u in us[:-1]:
            loop.append(get_vert(Vector((width, u * depth, z_target))))
        for u in us[:-1]:
            loop.append(get_vert(Vector(((1 - u) * width, depth, z_target))))
        for u in us[:-1]:
            loop.append(get_vert(Vector((0.0, (1 - u) * depth, z_target))))
        return loop

    roof_face = bm.faces.new(perimeter_loop(z))
    floor_face = bm.faces.new(list(reversed(perimeter_loop(base_z))))
    roof_face.material_index = roof_wall_idx
    floor_face.material_index = roof_wall_idx

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for m in materials:
        mesh.materials.append(m)
    return obj, floor_z_offsets


def make_pitched_roof(width: float, depth: float, wall_top_z: float, ridge_height: float,
                      eave_overhang: float = 0.3, style: str = "gable",
                      roof_mat=None, gable_wall_mat=None, name: str = "Roof"):
    """真正的斜屋頂量體（2026-09-09 新增，歐風/日式建築查證結論直接產物）：
    平頂+裝飾線腳**做不出**歐風建築的孟莎/斜屋頂觀感（查證：缺斜屋頂會被誤讀成
    「新古典風辦公樓」），日式建築（破風/寄棟屋頂）更是完全無法用平頂近似
    （查證：缺斜屋頂+深出簷，肉眼完全無法辨識為日式建築）——這支函式存在的
    理由就是把「斜屋頂」這個真正必要的幾何補上，不是裝飾層級的東西。

    技法：跟 §13.10 車體工作流「拉一個長方體→切一圈新邊→移動頂段頂點做出
    擋風玻璃斜角」是**同一套邏輯**（切出屋脊線、把屋脊頂點抬高），只是這裡是
    從零開始建一個獨立的屋頂量體（不是對牆體物件動刀）——真實屋頂本來就需要
    懸挑超出牆面（`eave_overhang`），跟牆體是不同的量體，牆體+屋頂各自獨立
    建構、屋頂底部貼合牆頂高度即可，不需要牆體跟屋頂共用頂點。

    width/depth：牆體 footprint（不含懸挑，通常跟 `assemble_building()`/
    `generate_facade()` 用同一組數字）。wall_top_z：牆頂世界 z 高度（屋頂底部
    貼合這個高度）。ridge_height：屋脊比牆頂高出的量（公尺，決定屋頂坡度，
    越大坡度越陡）。eave_overhang：屋頂懸挑超出牆面的水平距離（公尺）——**日式
    建築這個數值要明顯拉大**（查證：出簷深是日式建築的核心特徵之一，不是可有
    可無的細節，經驗值可以抓到 1.0m 以上；歐風建築維持中等懸挑 0.3-0.6m 即可）。

    style：`'gable'`（雙坡懸山頂——屋脊沿 X 軸中線，兩端是垂直的三角形山牆，
    本函式一併封起來用 `gable_wall_mat` 上色，代表牆體延伸到屋頂內的三角形
    部分）或 `'hip'`（四坡廡殿/歇山頂——四邊都往屋脊收，屋脊縮短、兩端斜面
    收頭，沒有垂直山牆；建築寬深比夠極端時屋脊會收成單一頂點，自動退化成
    四角錐/攢尖頂，不需要呼叫端另外判斷）。

    回傳建好的 obj（材質索引 0=屋面 roof_mat，1=山牆 gable_wall_mat——只有
    `style='gable'` 才會用到索引 1，hip 屋頂沒有山牆面，但仍統一回傳兩個
    材質槽以保持呼叫端邏輯一致，不需要依 style 判斷材質槽數量）。
    """
    if style not in ("gable", "hip"):
        raise ValueError(f"make_pitched_roof: 未知 style '{style}'（可用：gable/hip）")

    e = eave_overhang
    z0, z1 = wall_top_z, wall_top_z + ridge_height
    x0, x1 = -e, width + e
    y0, y1 = -e, depth + e
    ridge_y = (y0 + y1) / 2.0

    bm = bmesh.new()
    eave = {
        "fl": bm.verts.new((x0, y0, z0)), "fr": bm.verts.new((x1, y0, z0)),
        "bl": bm.verts.new((x0, y1, z0)), "br": bm.verts.new((x1, y1, z0)),
    }

    if style == "gable":
        ridge_x0, ridge_x1 = x0, x1
    else:
        hip_inset = min((y1 - y0) / 2.0, (x1 - x0) / 2.0)
        ridge_x0, ridge_x1 = x0 + hip_inset, x1 - hip_inset
    r0 = bm.verts.new((ridge_x0, ridge_y, z1))
    r1 = bm.verts.new((ridge_x1, ridge_y, z1))

    roof_faces = []
    roof_faces.append(bm.faces.new((eave["fl"], eave["fr"], r1, r0)))  # front slope
    roof_faces.append(bm.faces.new((eave["br"], eave["bl"], r0, r1)))  # back slope

    gable_faces = []
    if style == "gable":
        gable_faces.append(bm.faces.new((eave["fl"], r0, eave["bl"])))   # left gable wall
        gable_faces.append(bm.faces.new((eave["fr"], eave["br"], r1)))  # right gable wall
    else:
        roof_faces.append(bm.faces.new((eave["fl"], r0, eave["bl"])))   # left hip slope
        roof_faces.append(bm.faces.new((eave["fr"], eave["br"], r1)))  # right hip slope

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    roof_idx = 0
    gable_idx = 1
    for f in roof_faces:
        f.material_index = roof_idx
    for f in gable_faces:
        f.material_index = gable_idx

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(roof_mat or _default_wall_mat())
    mesh.materials.append(gable_wall_mat or _default_wall_mat())
    return obj


def _mesh_box(name: str, size, loc):
    """局部用的簡易長方體（不依賴 build_template，維持本檔自我獨立慣例）——
    size=(x,y,z) 全長，loc=中心世界座標，transform_apply 後 origin 在 loc，
    跟 build_template.add_box() 是同一套 origin 慣例，混用不會有 §8#9 那種
    origin 不一致坑。"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def _mesh_cyl(name: str, radius: float, depth: float, loc):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, vertices=12)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def make_entrance_canopy(width: float, depth: float, floor_height: float,
                         canopy_width: float = None, canopy_depth: float = 3.0,
                         canopy_thickness: float = 0.25, canopy_z_ratio: float = 0.85,
                         support_mat=None, canopy_mat=None, name: str = "Canopy"):
    """建築正面（`assemble_building()` 的 front wall，y=0 那一側）入口雨遮：一片
    懸挑板+兩根細支柱，對應住宅/辦公大樓一樓「遮雨迎賓道」需求（見
    `anatomy/buildings/_INDEX.md` 的一樓必備元素）。獨立於樓體 mesh 之外建構
    ——真實建築的雨遮結構本來就是獨立附加構件，不是立面本身的一部分，這裡照
    現實做法拆成獨立物件，不需要修改/重新開洞 `assemble_building()` 產出的樓體。

    width/depth：主樓體的寬深（用跟 `assemble_building()` 呼叫時同一組數字，
    雨遮會自動掛在建築正面 X 軸中心）。floor_height：一樓樓層高度（`floor_specs`
    第一項的 `height`），決定雨遮掛的高度。canopy_width：雨遮板寬度，預設 None
    時用 `width*0.4`（覆蓋入口區域，不是整片立面寬）。canopy_depth：雨遮懸挑
    深度（公尺，往建築前方 -Y 方向延伸，對應人行道/迎賓道範圍）。

    回傳 (canopy_obj, [support_obj_left, support_obj_right])。
    """
    if canopy_width is None:
        canopy_width = width * 0.4
    cz = floor_height * canopy_z_ratio
    canopy_obj = _mesh_box(f"{name}_Slab", (canopy_width, canopy_depth, canopy_thickness),
                           (width / 2.0, -canopy_depth / 2.0, cz + canopy_thickness / 2.0))
    canopy_obj.data.materials.append(canopy_mat or _default_wall_mat())

    support_r = 0.1
    supports = []
    for side in (-1, 1):
        x = width / 2.0 + side * (canopy_width / 2.0 - support_r * 3)
        y = -canopy_depth + support_r * 3
        sup = _mesh_cyl(f"{name}_Support_{'L' if side < 0 else 'R'}", support_r, cz, (x, y, cz / 2.0))
        sup.data.materials.append(support_mat or _default_wall_mat())
        supports.append(sup)
    return canopy_obj, supports


_WALL_AXES = {
    # (along_axis_index, fixed_axis_index, outward_sign) — along_axis is which world axis
    # `pos_along_wall` moves on; fixed_axis is which world axis `wall_coord` pins; outward_sign
    # is the direction the component projects away from the building volume on that wall.
    "front": (0, 1, -1),   # X moves along, Y pinned, projects -Y — assemble_building()'s y=0 face
    "back":  (0, 1, +1),   # X moves along, Y pinned, projects +Y — assemble_building()'s y=depth face
    "left":  (1, 0, -1),   # Y moves along, X pinned, projects -X — assemble_building()'s x=0 face
    "right": (1, 0, +1),   # Y moves along, X pinned, projects +X — assemble_building()'s x=width face
}


def _wall_box_loc(wall: str, wall_coord: float, pos_along_wall: float, outward_offset: float) -> tuple:
    """Shared placement math for any of `assemble_building()`'s four faces — see _WALL_AXES.
    `outward_offset` is how far the component's center sits from the wall plane, signed positive
    meaning "away from the building" regardless of which wall (the per-wall outward sign is
    applied here so callers never have to reason about ±X/±Y themselves)."""
    along_axis, fixed_axis, sign = _WALL_AXES[wall]
    coords = [0.0, 0.0]
    coords[along_axis] = pos_along_wall
    coords[fixed_axis] = wall_coord + sign * outward_offset
    return (coords[0], coords[1])


def _wall_box_size(wall: str, along_size: float, fixed_axis_size: float, height: float) -> tuple:
    """(x, y, z) box dimensions for a component whose span-along-the-wall is `along_size` and
    whose span-along-the-wall's-fixed-axis (i.e. its footprint in the projection direction, or
    its thickness for a flat panel like a railing) is `fixed_axis_size` — front/back walls run
    along X so `along_size` becomes the X dimension; left/right walls run along Y so it becomes
    the Y dimension instead. Keeps add_balcony()/add_ac_units() from duplicating this swap."""
    along_axis, _fixed_axis, _sign = _WALL_AXES[wall]
    return (along_size, fixed_axis_size, height) if along_axis == 0 else (fixed_axis_size, along_size, height)


def add_balcony(pos_along_wall: float, z_bottom: float, width: float = 2.4, depth: float = 1.2,
                slab_thickness: float = 0.12, railing_height: float = 1.0,
                wall: str = "front", wall_coord: float = 0.0,
                railing_mat=None, slab_mat=None, name: str = "Balcony",
                cheek_mat=None, cheek_thickness: float = 0.15):
    """住宅立面最常見、最好辨識的懸挑陽台類型（projecting balcony——見
    `anatomy/buildings/residential.md` 的陽台類型說明；退縮式/Juliet 陽台不需要
    額外幾何，前者用 `assemble_building()` 的 `recess` 加大即可近似，後者窗戶
    本身到地+一道欄杆，不需要呼叫這支函式）：一片懸挑板+一道玻璃欄杆，掛在
    `assemble_building()` 產出樓體四面牆的其中一面外側。

    **2026-09-09 前只支援 front（y=0）一面**——查證確認真實住宅大樓的陽台通常
    分布在至少兩面（不會全部集中在鏡頭面向的那一面，不同房間格局需要各自的
    對外陽台），`wall` 參數新增後才真正做得到；呼叫端規劃立面時記得主動分配到
    多面，不要因為「反正鏡頭看不到」就只做正面那一面。

    pos_along_wall：陽台在**該面牆自身方向**上的中心座標（`wall='front'/'back'`
    時是世界 X；`wall='left'/'right'` 時是世界 Y）——呼叫端自己決定要對齊哪個
    開間中心，通常是 `width_per_bay * (bay_index + 0.5)`（`left`/`right` 面則用
    `depth_per_bay * (bay_index + 0.5)`，若該面也用相同柱網分格）。z_bottom：
    陽台板底部世界 z 高度（通常是該樓層 `floor_z_offsets[i]` 加窗台高，不是
    樓層地板本身的高度，陽台不會跟樓板同高懸空）。wall：`'front'`（y=0 面，
    預設，向下相容舊呼叫）/`'back'`（y=depth 面）/`'left'`（x=0 面）/`'right'`
    （x=width 面）。wall_coord：該面牆固定軸的世界座標——`front`/`left` 通常是
    0.0（與預設值相同）、`back` 通常填 `assemble_building()` 的 `depth`、
    `right` 通常填 `width`。

    **`cheek_mat`（2026-09-11 新增，日式住宅塔樓案例驗證）**：給了才會在陽台
    兩端各加一片跟陽台同深、頂到欄杆高度的側牆（隔戶用的實體分戶牆，真實
    住宅大樓陽台常見構件，不是裝飾）。這不只是功能構件——**這對面「凹凸感」
    的貢獻比欄杆本身更大**：欄杆是薄玻璃/金屬件，正面看幾乎是一條線；側牆
    垂直於立面凸出，在斜側光下會在相鄰陽台之間投下清楚的陰影，是整片立面
    讀起來有沒有真實量體感的關鍵——同一顆鏡頭實測比對：只有欄杆+陽台板的
    立面（陽台覆蓋率低、side 牆缺席）渲染出來偏平、陽台看起來像貼在牆上的
    裝飾；陽台覆蓋率提高到接近整面寬度、且每個陽台都加上這對側牆之後，
    立面呈現出連續、有真實進退的浮雕感，跟參考渲染的落差明顯縮小（見
    `anatomy/buildings/residential.md` 陽台段落的完整前後對比記錄）。
    `cheek_thickness` 預設 0.15（150mm，一般分戶牆厚度量級）。

    回傳 `(slab_obj, railing_obj)`；`cheek_mat` 給值時回傳
    `(slab_obj, railing_obj, [cheek_a_obj, cheek_b_obj])`。
    """
    slab_x, slab_y = _wall_box_loc(wall, wall_coord, pos_along_wall, depth / 2.0)
    slab_obj = _mesh_box(f"{name}_Slab", _wall_box_size(wall, width, depth, slab_thickness),
                         (slab_x, slab_y, z_bottom + slab_thickness / 2.0))
    slab_obj.data.materials.append(slab_mat or _default_wall_mat())

    railing_thickness = 0.02
    rail_x, rail_y = _wall_box_loc(wall, wall_coord, pos_along_wall, depth - railing_thickness)
    railing_obj = _mesh_box(f"{name}_Railing", _wall_box_size(wall, width, railing_thickness, railing_height),
                            (rail_x, rail_y, z_bottom + slab_thickness + railing_height / 2.0))
    railing_obj.data.materials.append(railing_mat or _default_window_mat())

    if cheek_mat is None:
        return slab_obj, railing_obj

    cheek_h = slab_thickness + railing_height
    cheeks = []
    for s, tag in ((-1, "A"), (1, "B")):
        a = pos_along_wall + s * (width / 2.0 - cheek_thickness / 2.0)
        cx, cy = _wall_box_loc(wall, wall_coord, a, depth / 2.0)
        cheek_obj = _mesh_box(f"{name}_Cheek{tag}", _wall_box_size(wall, cheek_thickness, depth, cheek_h),
                              (cx, cy, z_bottom + cheek_h / 2.0))
        cheek_obj.data.materials.append(cheek_mat)
        cheeks.append(cheek_obj)
    return slab_obj, railing_obj, cheeks


def add_ac_units(along_positions: list, z_bottom: float, unit_size=(0.9, 0.5, 0.35),
                 wall: str = "front", wall_coord: float = 0.0,
                 louver: bool = True, unit_mat=None, louver_mat=None,
                 name: str = "AC"):
    """住宅立面冷氣室外機（見 `anatomy/buildings/residential.md` AC 章節，調研
    數據：完全密封的裝飾罩會讓散熱效率降最多 34%、額外耗電——真實作法是外露在
    服務陽台，或用開放式百葉罩遮蔽視覺但不擋風，不是實心箱子悶住）。
    `louver=True`（預設）在機組正面加一層水平百葉格柵（真的有空隙，不是貼皮）；
    `louver=False` 完全外露不加任何遮蔽（服務陽台常見做法）。

    **2026-09-09 前只支援 front（y=0）一面**，`wall` 參數新增後可掛在
    `assemble_building()` 四面牆的任一面——語意同 `add_balcony()`：規劃立面時
    冷氣機通常會跟著陽台/服務陽台一起分佈在多面，不要只集中在鏡頭面向那一面。

    along_positions：每台機組在**該面牆自身方向**上的中心位置清單（`wall=
    'front'/'back'` 時是世界 X；`'left'/'right'` 時是世界 Y；呼叫端自己決定
    間距——研究建議機組間至少留一個機身寬度方便維修動線，不是無縫排列）。
    z_bottom：機組底部世界 z 高度（通常掛在窗台下方或陽台地板上）。wall/
    wall_coord：同 `add_balcony()`——選哪一面牆、該面牆固定軸的世界座標。

    回傳 list of (unit_obj, louver_obj_or_None)。
    """
    uw, ud, uh = unit_size
    results = []
    for i, pos in enumerate(along_positions):
        ux, uy = _wall_box_loc(wall, wall_coord, pos, ud / 2.0)
        unit_obj = _mesh_box(f"{name}_{i}", _wall_box_size(wall, uw, ud, uh), (ux, uy, z_bottom + uh / 2.0))
        unit_obj.data.materials.append(unit_mat or _default_wall_mat())
        louver_obj = None
        if louver:
            n_slats = 5
            slat_h = uh / (n_slats * 2)
            lx, ly = _wall_box_loc(wall, wall_coord, pos, ud + 0.02)
            for s in range(n_slats):
                slat_z = z_bottom + (s + 0.5) * (uh / n_slats)
                louver_obj = _mesh_box(f"{name}_{i}_Louver_{s}", _wall_box_size(wall, uw * 1.05, 0.02, slat_h),
                                       (lx, ly, slat_z))
                louver_obj.data.materials.append(louver_mat or _default_wall_mat())
        results.append((unit_obj, louver_obj))
    return results


def make_pergola(center: tuple, width: float, depth: float, height: float,
                 post_size: float = 0.16, beam_size: float = 0.20,
                 slat_count: int = 18, slat_size: float = 0.10,
                 post_mat=None, beam_mat=None, name: str = "Pergola") -> list:
    """屋頂平台/庭院涼棚（pergola）——四根立柱+兩根長邊橫梁+一整排平行棚頂格柵，
    不是一片實心屋頂板（2026-09-09 新增，來源：住宅大樓參考案例的屋頂平台，
    見 SKILL.md §10.3；本 skill 原本沒有這個構件，屋頂平台類任務只能拿 add_box()
    手拼一片實心遮陽板，質感差很多）。

    center：涼棚中心世界座標 (x, y, z)——z 是**格柵頂面**高度，立柱從 z=0（呼叫端
    自己決定這個 0 是屋突平台面還是別的基準面，本函式不管地面在哪）算到 z 頂。
    width/depth：涼棚覆蓋範圍（沿世界 X/Y）。height：立柱高度（從地面到橫梁底）。
    slat_count：格柵根數，沿 width 方向等距排列——根數越多間隙越密，真實涼棚
    格柵間隙通常跟格柵本身寬度相近（不是縫隙比格柵寬很多的稀疏柵欄）。
    post_size/beam_size/slat_size：立柱截面邊長/橫梁截面邊長/格柵截面邊長
    （皆為方形截面邊長，不是矩形長寬）。

    回傳所有生成物件的 list（4 柱 + 2 梁 + slat_count 根格柵），呼叫端視需要
    自行 join_into 一個母版（跟 detail_lib 的細節件是同一個模式）。"""
    cx, cy, cz = center
    beam_z = cz - beam_size / 2.0
    parts = []
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, py = cx + sx * (width / 2.0 - post_size), cy + sy * (depth / 2.0 - post_size)
        post = _mesh_box(f"{name}_Post_{'L' if sx < 0 else 'R'}{'F' if sy < 0 else 'B'}",
                         (post_size, post_size, height), (px, py, height / 2.0))
        post.data.materials.append(post_mat or _default_wall_mat())
        parts.append(post)
    for sy in (-1, 1):
        by = cy + sy * (depth / 2.0 - post_size)
        beam = _mesh_box(f"{name}_Beam_{'F' if sy < 0 else 'B'}",
                         (width, beam_size, beam_size), (cx, by, beam_z))
        beam.data.materials.append(beam_mat or _default_wall_mat())
        parts.append(beam)
    for s in range(slat_count):
        sx = cx - width / 2.0 + (s + 0.5) * (width / slat_count)
        slat = _mesh_box(f"{name}_Slat_{s:02d}", (slat_size, depth, slat_size), (sx, cy, cz))
        slat.data.materials.append(beam_mat or _default_wall_mat())
        parts.append(slat)
    return parts


def make_lightning_rod(roof_z: float, x: float = 0.0, y: float = 0.0, mast_height: float = 6.0,
                       base_size: float = 0.7, base_height: float = 0.5,
                       mast_radius: float = 0.05, beacon_radius: float = 0.18,
                       mast_mat=None, base_mat=None, beacon_mat=None,
                       name: str = "LightningRod") -> dict:
    """屋頂避雷針 + 頂端航空障礙燈（2026-09-11 新增）。

    高層建築屋頂的兩個必備安全構件，現實中通常就在同一根桅杆上：**避雷針**（尖頂
    金屬桅杆＝接閃器）與**航空障礙燈**（紅色警示燈，讓飛機看得見這棟樓的高度——
    超高層建築依法規必須設置，也是高空天際線上最容易辨識的紅點）。兩件都缺席時，
    屋頂讀起來就是「一個平面蓋子」；補上之後屋頂才讀成「真的在營運的高樓」。

    `roof_z`：屋頂面世界 z（通常是 `floor_z_offsets[-1] + 最後一層高度`，有女兒牆
    時取女兒牆頂）。`x`/`y`：桅杆平面位置（慣例放屋頂角落或機房旁，不是正中央——
    真實避雷針是接閃器，位置跟著屋頂最高處/機房走）。`mast_height`：桅杆高度（公尺，
    超高層常見 5-15m 等級）。`base_size`/`base_height`：底座基座（實際屋面要做防水
    收頭，桅杆不是直接插在屋頂面上）。`mast_radius`/`beacon_radius`：桅杆半徑／頂端
    燈具半徑。要更真實的收分桅杆，可用 `shape_lib.tapered_rod()` 取代這支的圓柱桅杆
    （本檔維持自我獨立慣例，不 import shape_lib）。

    **`beacon_mat` 的顏色陷阱**：預設 `_default_beacon_mat()` 是自發光紅，但**日光級
    preset（studio/outdoor_golden）下 AgX 會把純自發光壓成接近純白，紅點只在夜景/
    暗環境讀得出來**（同 §10.3「已入住暖光窗」的同一套機制）；白天要明確的紅色，
    改用飽和紅色非自發光材質，或在 Stage C 評圖時確認實際讀到的顏色。

    回傳 `{"base": obj, "mast": obj, "beacon": obj}`——三個獨立物件（基座/桅杆/燈具
    在現實中是不同工序的構件，拆開方便個別換材質），要併成單一母版用
    `detail_lib.join_into()`。
    """
    base = _mesh_box(f"{name}_Base", (base_size, base_size, base_height),
                     (x, y, roof_z + base_height / 2.0))
    base.data.materials.append(base_mat or _default_wall_mat())

    mast_bottom = roof_z + base_height
    mast = _mesh_cyl(f"{name}_Mast", mast_radius, mast_height,
                     (x, y, mast_bottom + mast_height / 2.0))
    mast.data.materials.append(mast_mat or _default_wall_mat())

    beacon = _mesh_cyl(f"{name}_Beacon", beacon_radius, beacon_radius * 2.0,
                       (x, y, mast_bottom + mast_height + beacon_radius))
    beacon.data.materials.append(beacon_mat or _default_beacon_mat())
    return {"base": base, "mast": mast, "beacon": beacon}


def _default_beacon_mat():
    """航空障礙燈預設材質：飽和紅底 + 自發光（夜間可見；日光 preset 下 AgX 會壓成
    近白，見 make_lightning_rod() docstring 的顏色陷阱說明）。5.1 socket 名為
    'Emission Color'/'Emission Strength'（4.x 語料是 'Emission'），用 .get() 取、
    取不到時印 WARNING 降級（不靜默失敗）。"""
    mat = bpy.data.materials.new("Beacon_Red_Default")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.65, 0.03, 0.03, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.35
    for socket_name, value in (("Emission Color", (1.0, 0.06, 0.05, 1.0)),
                               ("Emission Strength", 8.0)):
        sock = bsdf.inputs.get(socket_name)
        if sock is None:
            print(f"WARNING: _default_beacon_mat: 找不到 socket '{socket_name}'"
                  f"（Blender 版本差異？發光效果降級為純色）", flush=True)
            continue
        sock.default_value = value
    return mat


def _default_wall_mat():
    mat = bpy.data.materials.new("Building_Wall_Default")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.72, 0.7, 0.66, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    return mat


def _default_window_mat():
    mat = bpy.data.materials.new("Building_Window_Default")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.04, 0.06, 0.09, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.15
    bsdf.inputs["Metallic"].default_value = 0.2
    return mat


# ---------------------------------------------------------------- 室內粗模（透明玻璃後方）

def add_interior_blockout(width: float, depth: float, floor_z_offsets: list, floor_height: float,
                          floor_indices: list, column_mat, desk_mat, core_mat=None,
                          column_grid: tuple = (6.0, 6.0), column_size: float = 0.45,
                          inset: float = 1.2, desk_spacing: tuple = (2.4, 3.2),
                          desk_size: tuple = (1.3, 0.65, 0.05), desk_row_skip: int = 4,
                          include_core: bool = True, core_size: tuple = (3.2, 4.4),
                          core_offset: tuple = (0.0, 0.0), include_stairs: bool = True,
                          stair_width: float = 1.4, stair_steps: int = 12,
                          seed: int = 0, name_prefix: str = "Interior") -> list:
    """透明玻璃立面背後的室內粗模：承重柱網+電梯/樓梯核心+辦公桌陣列——2026-09-11
    新增，2026-09-11 second pass 依實戰回饋重寫（第一版用細圓柱當柱子、圓形椅子跟
    桌面沒對齊、隨機散布桌椅、柱子只在抽樣樓層出現，四個問題都是真實觀感缺陷，
    不是小毛病，這裡整支重寫，不是微調）：

    **1. 承重柱改成方形、加粗、貫通全高**——真實高樓結構柱斷面常見 400-800mm
    等級（不是裝飾用的細圓桿），且結構柱本來就是**貫通整棟樓的連續構件**，不會
    「這層有柱子、那層沒有」；舊版把柱子跟桌椅椅子一樣按 `floor_indices` 逐層
    生成，同一根柱子在不同樓層之間斷開、甚至完全消失，是明顯的幾何錯誤，不是
    「抽樣省物件數」可以合理化的取捨。**新版柱子固定貫通 `floor_z_offsets[0]`
    到最後一層樓頂**（跟 `floor_indices` 選了哪幾層完全無關），只有桌椅/樓梯
    才按 `floor_indices` 抽樣（那些東西本來就樓層與樓層之間互相獨立，抽樣合理）。

    **2. 新增電梯/樓梯核心**：`include_core=True`（預設）在樓體內部加一個明顯
    更粗、貫通全高的核心量體（`core_size` 預設 3.2×4.4m，真實電梯機房+樓梯間
    的量級），視覺上立刻讀出「這是一棟有服務核心的真實大樓」，不是桌椅隨機散布
    的空殼。`include_stairs=True` 額外在核心旁加一段階梯狀量體（真的分階，不是
    一片斜板），`stair_steps` 控制階數，只在 `floor_indices` 選中的樓層生成。

    **3. 辦公桌改成方形箱體、規則網格、密度降低**——桌子是一片扁平箱體（**不是
    圓形**）+ 一片直立的「屏風/桌側板」箱體（不是圓柱椅子，圓柱底座本來就跟
    方形桌面對不齊，方形桌側板天生跟桌面同一個座標系對齊，不會有這個問題）；
    排列改成**規則等距網格**（`desk_spacing` 控制行列間距），不是隨機散布——
    每隔 `desk_row_skip` 排空一整排當走道，模擬真實辦公室的走道節奏，不是
    `desk_density` 那種逐格擲骰子的隨機疏密（那樣永遠排不出「整齊排辦公桌」
    的觀感，密度感覺也難控制）。

    **不追求辦公空間級細節，粗模等級就達到目的**：桌子/柱子/核心都是方盒，不需要
    真的建鍵盤/螢幕/電梯門——只要有量體在接住穿透玻璃的光線、投出陰影、打破純黑
    真空的觀感，就已經比完全中空好非常多；細節密度可以留給真的需要室內近景鏡頭
    的任務再加。

    width/depth：建築量體外牆尺寸（跟 `assemble_building()` 呼叫時同一組數字）。
    floor_z_offsets/floor_height：`assemble_building()` 回傳的 `floor_z_offsets`+
    該樓層高度（多層高度不同時呼叫端自己逐層呼叫本函式，但柱子/核心本來就該
    貫通到頂，逐層呼叫時注意柱子會重複生成，多樓層高度不同的塔樓建議只呼叫一次、
    `floor_height` 傳標準層代表值，柱子貫通到「假設全樓等高」算出的頂）。
    floor_indices：要放桌椅/樓梯的樓層索引清單——不需要每層都放，中低樓層/鏡頭
    容易看到的樓層優先（柱子/核心不受這個清單影響，永遠貫通全高）。

    column_grid/column_size：柱網間距（常見 6-9m）+ 柱斷面邊長（預設 0.45m）。
    inset：柱列/核心/桌椅離玻璃內側面的退縮距離。desk_spacing/desk_size：桌位
    網格間距+單張桌子尺寸。desk_row_skip：每隔幾排空一排當走道（4 = 每 4 排空
    1 排）。include_core/core_size/core_offset：電梯/樓梯核心開關+尺寸+相對
    樓體中心的偏移（真實核心通常不在正中央，偏一側或角落）。include_stairs/
    stair_width/stair_steps：樓梯開關+寬度+階數。`seed` 保留給未來的隨機化
    擴充（目前的規則網格排列不吃亂數，只是保留參數向下相容）。

    回傳所有新建物件的 list（柱/核心/樓梯/桌子混在一起，未 join——呼叫端可以
    自行決定要不要 `join_into()` 併入樓體，或保持獨立物件方便之後個別調整）。
    """
    objs = []
    z_bottom = floor_z_offsets[0]
    z_top = floor_z_offsets[-1] + floor_height
    total_h = z_top - z_bottom

    col_gx, col_gy = column_grid
    nx = max(1, round((width - 2.0 * inset) / col_gx))
    ny = max(1, round((depth - 2.0 * inset) / col_gy))
    xs = [inset + (width - 2.0 * inset) * (i / nx) for i in range(nx + 1)]
    ys = [inset + (depth - 2.0 * inset) * (j / ny) for j in range(ny + 1)]

    core_w, core_d = core_size
    core_cx = width / 2.0 + core_offset[0]
    core_cy = depth / 2.0 + core_offset[1]

    # ---- 1. 承重柱：方形斷面，貫通全高，跟 floor_indices 無關 ----
    for xi, x in enumerate(xs):
        for yi, y in enumerate(ys):
            # 柱子落在核心footprint內的跳過，避免跟核心互相穿插
            if (core_cx - core_w / 2.0 - 0.4 < x < core_cx + core_w / 2.0 + 0.4 and
                    core_cy - core_d / 2.0 - 0.4 < y < core_cy + core_d / 2.0 + 0.4):
                continue
            c = _mesh_box(f"{name_prefix}_Col_{xi:02d}{yi:02d}",
                         (column_size, column_size, total_h),
                         (x, y, z_bottom + total_h / 2.0))
            c.data.materials.append(column_mat)
            objs.append(c)

    # ---- 2. 電梯/樓梯核心：明顯更粗，貫通全高 ----
    if include_core:
        core = _mesh_box(f"{name_prefix}_Core", (core_w, core_d, total_h),
                         (core_cx, core_cy, z_bottom + total_h / 2.0))
        core.data.materials.append(core_mat or column_mat)
        objs.append(core)

    if include_stairs:
        step_d = 0.28
        step_run = step_d * stair_steps
        stair_x = core_cx + core_w / 2.0 + stair_width / 2.0 + 0.35
        stair_y0 = core_cy - step_run / 2.0
        for fi in floor_indices:
            fz = floor_z_offsets[fi]
            step_h = floor_height / stair_steps
            for s in range(stair_steps):
                step = _mesh_box(f"{name_prefix}_Stair_F{fi:02d}_{s:02d}",
                                 (stair_width, step_d, step_h * (s + 1)),
                                 (stair_x, stair_y0 + (s + 0.5) * step_d, fz + step_h * (s + 1) / 2.0))
                step.data.materials.append(core_mat or column_mat)
                objs.append(step)

    # ---- 3. 辦公桌：方形箱體，規則網格，定期空排當走道 ----
    dx, dy = desk_spacing
    dw, dd, dtop_t = desk_size
    desk_h = 0.72
    for fi in floor_indices:
        z0 = floor_z_offsets[fi]
        row_i = 0
        y = inset + dy / 2.0
        while y < depth - inset - dy / 2.0:
            row_i += 1
            if desk_row_skip and row_i % desk_row_skip == 0:
                y += dy
                continue
            x = inset + dx / 2.0
            while x < width - inset - dx / 2.0:
                in_core = (core_cx - core_w / 2.0 - 0.5 < x < core_cx + core_w / 2.0 + 0.5 and
                          core_cy - core_d / 2.0 - 0.5 < y < core_cy + core_d / 2.0 + 0.5)
                if not in_core:
                    desk = _mesh_box(f"{name_prefix}_Desk_F{fi:02d}_R{row_i:02d}_{x:.1f}",
                                     (dw, dd, dtop_t), (x, y, z0 + desk_h))
                    desk.data.materials.append(desk_mat)
                    objs.append(desk)
                    panel = _mesh_box(f"{name_prefix}_DeskPanel_F{fi:02d}_R{row_i:02d}_{x:.1f}",
                                      (dw * 0.92, 0.04, desk_h - 0.06),
                                      (x, y - dd / 2.0, z0 + (desk_h - 0.06) / 2.0))
                    panel.data.materials.append(desk_mat)
                    objs.append(panel)
                x += dx
            y += dy
    return objs


# ---------------------------------------------------------------- 停車格

def make_parking_lot(center: tuple, rows: int, cols: int, stall_width: float = 2.6,
                     stall_depth: float = 5.2, aisle_width: float = 6.5,
                     line_width: float = 0.10, pavement_mat=None, line_mat=None,
                     name: str = "ParkingLot"):
    """地面平面停車格（不是地下停車場/機械停車，範圍只到「一片鋪面+畫白線」）。

    **`stall_width`/`stall_depth` 未經 web 查證精確標準**——是小型車停車格常見
    量級的合理估計，動工時以肉眼觀感為準微調，不要當成硬性規格（跟本 skill 其他
    未查證項目的誠實標註慣例一致，見 `anatomy/spaces/japanese_street.md` 檔頭）。

    rows=1（單排，例如靠建築物側牆停車）或 rows=2（雙排面對面夾一條行車動線，
    `aisle_width` 是那條動線的寬度）是最常見的兩種佈局；rows>2 時只在最外側
    兩排加止滑/停止線，中間排不加——多排停車場的實際動線設計比這支函式處理的
    複雜，這裡只覆蓋最常見的路邊/廣場級停車配置，不是完整停車場規劃工具。

    回傳 `(pavement_obj, line_objs)`。
    """
    cx, cy = center
    total_w = cols * stall_width
    total_d = rows * stall_depth + max(0, rows - 1) * aisle_width
    pavement = _mesh_box(f"{name}_Pavement", (total_w, total_d, 0.05), (cx, cy, 0.025))
    pavement.data.materials.append(pavement_mat or _default_wall_mat())
    lmat = line_mat or _default_window_mat()

    lines = []
    x0 = cx - total_w / 2.0
    y_cursor = cy - total_d / 2.0
    for r in range(rows):
        row_y0 = y_cursor
        row_y1 = row_y0 + stall_depth
        row_cy = (row_y0 + row_y1) / 2.0
        for c in range(cols + 1):
            lx = x0 + c * stall_width
            ln = _mesh_box(f"{name}_R{r}_Div{c:02d}", (line_width, stall_depth, 0.006),
                           (lx, row_cy, 0.053))
            ln.data.materials.append(lmat)
            lines.append(ln)
        back_y = None
        if r == 0:
            back_y = row_y0
        if r == rows - 1 and rows > 1:
            back_y = row_y1
        if back_y is not None:
            stop = _mesh_box(f"{name}_R{r}_Stop", (total_w, line_width, 0.006),
                             (cx, back_y, 0.053))
            stop.data.materials.append(lmat)
            lines.append(stop)
        y_cursor = row_y1 + aisle_width
    return pavement, lines
