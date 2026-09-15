# KEYWORDS: blender, bpy, template, 範本, 骨架, studio, golden hour, 曝光, luma, ergonomics, 人體工學, render, 渲染, golden ratio, 黃金比例, fibonacci, 費波那契, proportion, 曲線
"""Blender 5.1 通用建模渲染範本（skill asset，實測校準版）。

用途：任何「畫一個 3D 模型/場景」任務的起點骨架——複製本檔到
.capybala/test-scripts/build_template.py（凍結模組，不改內容），場景腳本
build_<task>.py 依 skill §9.6.1 用 import 引用：
  import build_template as T
  T.main(subject_fn=my_subject, preset_overrides={...})
只寫場景工廠函數與 layout，其餘（材質工具/曝光配方/方向數學自檢/渲染/亮度驗證）
直接沿用。禁止把本檔函數全文複製進場景腳本（Round 6 實錘：雙重維護必漂移）。

本範本內建的防線（對應實測踩過的坑）：
1. verify_orientation_math()——啟動即斷言四元數方向公約（椅子靠背前傾事故的根因：
   繞 +X 正角把 +Z 頂部帶向 -Y，與直覺相反；Blender 右手定則 Y→Z）。
2. 曝光配方 PRESETS——studio/outdoor_golden/night 三組實測參數，禁止憑感覺填燈光能量。
3. LUMA_STATS 亮度驗證——渲染後讀回 PNG 算亮度統計，落不在目標帶即 exit 1
   （v3 小木屋 mean=2.8 死黑、椅子 mean=191.5 過曝，都是「跑通但效果錯」）。
4. park_master()/instance()——§14 母版復用配套（Round 5 浦東塔實戰驗證）：
   母版隔離一律 hide_render（禁止高空存放，transform_apply 會烘掉 location），
   實例 linked copy 共享 mesh + 自動還原 hide 旗標，REUSE 計數進 SCENE_STATE。
5. SKY_DOMINANT——天空占比 >50% 構圖（仰視高塔/俯瞰大場景）設環境變數
   BLENDER_TEMPLATE_SKY_DOMINANT=1，sky_strength 自動 ×0.7（Round 5 實測 0.32→0.21 入帶）。
6. 黃金比例工具組（skill §15，使用者指定核心設計原則）——PHI/PHI_INV/FIB 常數、
   fib_split()/golden_series()/nearest_fib()/assert_proportion()：分段結構、主次體量、
   腰線位置、細節節奏的數字一律由它生成，禁止手填 50/50 或等距均分。
7. assert_within_room()/assert_grounded()（§7.7 新增，溫馨咖啡廳事故）——CALIB/亮度驗證
   完全不檢查「座標合不合理」：沙發/單椅擺位座標直接超過牆體位置、花瓶擺位假設的支撐面
   跟母版工廠函式實際蓋的位置對不上，兩個問題都跑通 exit=0，肉眼看渲染圖才發現家具穿牆、
   花瓶懸空。asset_fetch_lib 抓完現成資產 set location 後強制呼叫這兩個斷言。
8. assert_min_gap()（§13.8 新增，高中教室無走道事故）——桌椅網格用等距最小家具間距填滿
   整個房間，assert_within_room/assert_grounded 都過，但完全沒有一條路比其他間距明顯
   更寬，肉眼看是「擠成一團、沒有路可以走」。任何有多組家具/座位的空間類主體，Stage A
   規劃階段必須明確列出至少一條主要動線（見 assets/anatomy/spaces/），用這個斷言驗證
   實際淨空間距達到最低標準（一般抓 ≥0.75-0.9m）。
9. audit_interpenetration()/audit_floating()/audit_spacing()（§13.9 新增，通用幾何審查）——
   前面 7、8 兩點都要「呼叫端已經知道該檢查誰、預期關係是什麼」；這三個反過來，給一批
   物件自己去發現有沒有穿模/重疊/懸空/擺位離群，不用預先知道正確答案。回傳問題清單
   （不直接 fail），用 report_or_fail() 決定要不要真的擋下來。容許誤差全部參數化
   （tol/max_gap/max_sink/tolerance_ratio），只抓「量得出來」的問題，不抓肉眼看不出來
   的浮點/貼合誤差。貼在凸面宿主（圓柱/球/外殼）上的附件另走 surface_gap()/
   audit_attachment_contact()——AABB 判重疊對這類宿主天生無效（宿主的包圍盒是一整個
   方盒，貼在曲面上的附件其 AABB 必然落在盒內），所以 mark_side_attached() 排除懸空
   檢查之後，由這道貼合稽核接手：main() 對所有 _side_attached 物件自動跑，結果寫進
   SCENE_STATE.auto_geometry_audit.attachment_contact。
10. add_box()/add_cyl() origin 慣例統一（2026-09-08 修正，便利商店輪事故）——修正前
    add_cyl() 不呼叫 transform_apply，母版 origin 停在 loc；add_box() 會（且 5.1 的
    transform_apply(scale=True) 連帶烘掉 location/rotation，§8#9），兩者不一致。同場景
    混用 box-host 與 cyl-host 母版時，instance() 的 z 補償公式得依 host 用哪個 primitive
    建而分兩套算——這正是路燈/垃圾桶（cyl host）跟其餘家具（box host）混用、耗掉 4 個
    回合才抓出的懸空/深埋根因。現場 probe 實測驗證：cyl 補上 transform_apply(scale=True)
    後世界座標網格範圍不變，只是 origin 慣例統一成跟 add_box 一致——之後任何 host 母版
    不分 primitive 種類，instance() 的 z 都是單一套算法，見 add_cyl() docstring。
11. cut_hole()——布林差集挖洞（§13.10 新增，CNC 機床式建模操作字彙）——本範本原本只有
    「量體」（add_box/add_cyl）跟「表面裝飾」（detail_lib 滾花/刻痕）兩類操作，完全沒有
    「移除材料」——導致窗洞/門洞/鑽孔這類真實開孔只能用「該處不建量體」假造，做不出洞壁
    厚度，是「基礎形狀拼接感」的根因之一。用法：cutter 完全貫穿 host 厚度後呼叫
    `cut_hole(host, cutter)`，EXACT 求解器已 Blender 5.1.2 實測驗證（牆體開窗洞：16 verts
    潔淨洞口、raycast 內外正確通過/受阻）。
12. main() 自動幾何審查（2026-09-08 新增，東方明珠塔連續兩輪事故）——`audit_interpenetration()`/
    `audit_floating()` 原本要呼叫端自己記得叫，一次性腳本常常忘記：v1 三根主柱相距 7m、
    半徑各 4.5m（4.5+4.5=9>7）互相重疊 2m 沒被攔下、v2 上球到太空艙之間憑空缺了 70m
    連接段也沒被攔下，兩次都是渲染出去、使用者肉眼發現才知道。**現在只要走 `T.main()`，
    這兩個審查在 `subject_fn()` 建完後自動跑**（`hard=False` 只報告不擋渲染，容差沿用
    函式既有預設值，不是新發明的容差邏輯；mesh 物件數 >300 自動跳過並記 log，避免 O(n²)
    拖慢大場景），結果寫進 log 與 `SCENE_STATE.auto_geometry_audit`，Stage C 必查這個欄位。
    已用兩起事故的真實數字複現驗證：三根柱兩兩重疊、雙球都懸空，全部正確抓到。
13. auto_frame_and_light()（2026-09-08 新增，東方明珠塔近黑曝光根因修正）——build_camera()/
    build_lights() 的機位與三點式燈位/能量原本是為 ~1-2m demo 物件校準的固定絕對座標，
    直接套用在遠超出這個尺度的主體（例：468m 高塔）上，機位形同貼著塔基站、燈光能量差
    好幾個數量級，肉眼看到的「近黑曝光」只是表象。同一輪調查另外抓到相機 clip_end 預設
    1000m 的坑：機位一旦被拉遠超過這個距離（含用 set_camera() 手動拉遠的情況），主體
    整個落在遠裁切面外變不可見，只剩世界背景色——build_camera() 已一併修正為依實際對焦
    距離重算 clip_start/clip_end，不吃預設值。subject_fn() 建完主體後呼叫一次
    `T.auto_frame_and_light(mesh_objs, style="product"|"dramatic")`，用主體世界包圍盒
    對角線 diag 算相機距離與三點燈位置/能量/尺寸（能量公式含 diag² 距離平方反比校正），
    main() 隨後跑到 build_camera()/build_lights() 會自動讀到這次算出的覆寫值。已用
    0.15m/2m/468m 三種尺度（3000 倍範圍）實測驗證亮度統計完全一致（mean/clipped/dark
    三項全部相同），且 clip 修正前後對照確認過 468m 案例原本會整個落在裁切面外。
14. assert_in_frame()/audit_framing()/frame_coverage()（§15.4 構圖層，2026-09-11 新增）——
    build_camera() 算完相機、setup_render() 定完畫幅之後，「主體有沒有完整入鏡、在畫面
    裡佔多大」用包圍盒 8 角點的 NDC 投影數字回答，不必等渲染出來肉眼猜。main() 會自動
    跑 soft 版 audit_framing()（排除地面/環境件，只報告不擋），結果寫進
    SCENE_STATE.auto_geometry_audit.framing；要當硬性關卡的呼叫端用 assert_in_frame()。
15. 場景自描述 + 建置報告（2026-09-11 新增）——write_scene_provenance() 把參數/量測/
    skill 版本寫進 scene 自訂屬性（bp_* 鍵），main() 在存檔前與渲染後各寫一次，
    `.blend` 本身自描述、不必依賴 stdout；write_build_report() 把 SCENE_STATE ＋
    逐物件明細 ＋ 逐鏡頭輸出檔落成 `<OUT_DIR>/report.json`。setup_scene_units() 設公制
    單位與不透明底，存檔一律 compress=True。
16. set_engine()/BLENDER_TEMPLATE_ENGINE（2026-09-11 新增）——EEVEE 佈局預覽通道，
    「幾何對不對」類問題十秒內出圖，不必等 Cycles 的 2-5 分鐘；適用範圍與三個限制
    （Transmission 材質不同路徑／無完整 GI 與降噪／曝光守衛只報告不擋）見該函式 docstring。
17. 背面法外輪廓（outline_push_distance/make_outline_shell/setup_inverse_hull/
    measure_outline_shell/audit_outline_shell/make_internal_line，2026-09-13 新增）——
    3 渲 2 的線從「後處理描邊」升級成「幾何外殼」：複製真幾何、沿幾何平均法線外推、
    只畫背面，剪影處露出即為線。線寬依相機距離與焦距自動補償（固定線寬會近景粗黑邊、
    遠景鋸齒）；逐部位線寬用頂點色 alpha；z_offset 可只留最外圈剪影線。外殼登錄
    OUTLINE_SHELLS，main() 的自動幾何審查自動排除。完整研究與實測數據見
    `.capybala/notes/gg-xrd-cel-techniques.md`。
18. setup_cel_studio()/set_ground_mat()/request_outline()（2026-09-13 新增）——3 渲 2 的
    「展示卡模式」：EEVEE + Standard + 一盞 SUN(angle=0) + 低能量 CelFill + 純色中性
    背景 + cel 地面 + 背面法外殼，一次呼叫取代 auto_frame_and_light()。PBR 的展示卡設定
    （三點式 AREA + AgX + noise 地面）搬進 cel 會壞三件事（三條明暗界線各自糊掉硬邊界／
    色票被 AgX 打歪／地面是寫實紋理），這支是同一張卡在 cel 下的對等版本——單一主體
    請求走這條，要一整條街的敘事場景才走天空＋構件那條（styles/genre/anime-cel-daylight.md）。
    request_outline() 解掉「背面法外殼要讀相機矩陣、但相機是 main() 內部才建的」時序問題；
    ORTHO 相機的線寬走 outline_push_distance(ortho_scale=...) 的專屬公式（與距離無關），
    量測結果寫進 SCENE_STATE.outline。

用法：
  blender --background --python build_template.py            # 正式渲染（1280x720, 256spp，跑佔位示範）
  blender --background --python build_template.py -- --calib # 校準快渲（960x540, 48spp）
  blender --background --python build_<task>.py              # 引用模式：場景腳本（推薦，§9.6.1）
"""
import bmesh
import bpy
import glob
import json
import math
import os
import shutil
import sys
import tempfile
import datetime
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree

# ---------- CONFIG（每個任務改這裡） ----------
_OUT_DIR_FALLBACK = os.path.join(tempfile.gettempdir(), "blender_template_demo")
# 交付物該落哪裡：**任務自己的輸出目錄**（例：<workspace>/output/<task>，使用者要打開、交付、
# 續改的那一份），不是工具/skill 自己的暫存目錄。2026-09-14 汽車底盤案例：交付在
# C:\AI\CAR-PARTS\output\chassis，而這裡的預設值是工具自己的 demo 目錄，兩者不一致＝交付物
# 事後找不到的風險。下面是「沒有任何呼叫端指定輸出目錄」時的 fallback，main() 落在 fallback
# 時會印 WARNING 指名這件事。
OUT_DIR = os.environ.get("BLENDER_TEMPLATE_OUT", _OUT_DIR_FALLBACK)
PRESET = os.environ.get("BLENDER_TEMPLATE_PRESET", "studio")  # studio | outdoor_golden | night
CALIB = "--calib" in sys.argv or os.environ.get("BLENDER_TEMPLATE_CALIB") == "1"
# 天空占比 >50% 的構圖（低角度仰視高塔/俯瞰大場景）設 1：sky_strength 自動 ×0.7 起跑
# （Round 5 浦東塔實測：16mm 仰視天空占六成，0.32 → calib mean=187.2 超帶；0.21 → 164.9 入帶。skill §10.2#8）
SKY_DOMINANT = os.environ.get("BLENDER_TEMPLATE_SKY_DOMINANT") == "1"
# 佈局預覽引擎（2026-09-11 新增；本機 Blender 5.1.2 headless 實測：EEVEE 確實可跑，
# 引擎識別字只有 'BLENDER_EEVEE'——5.1 的 enum 沒有 _NEXT 也沒有 WORKBENCH）。
# 'cycles'（預設）＝正式成品路線；'eevee'＝佈局預覽（構圖/比例/穿模快篩），
# 三個明知的限制與適用範圍見 set_engine() docstring——預覽圖不可用於曝光校準。
ENGINE = os.environ.get("BLENDER_TEMPLATE_ENGINE", "cycles").lower()
EEVEE_SAMPLES = 64
# 色調映射（2026-09-13 新增；環境變數 BLENDER_TEMPLATE_VIEW_TRANSFORM=standard 等價）。
# 預設 AgX 不變——PBR 路線（studio/outdoor_golden/night）的曝光帶是照 AgX 校準的，
# 不要為了別的原因改它。**3 渲 2／賽璐璐路線才需要 'Standard'**（見 set_view_transform()）。
VIEW_TRANSFORM = os.environ.get("BLENDER_TEMPLATE_VIEW_TRANSFORM", "AgX")

# 2026-09-09 新增（實測事故：一棟高樓用預設 16:9 橫幅渲，主體塞不滿畫面上下已經頂到
# 邊緣、左右卻空一大片，見 SKILL.md §10.3）。ASPECT 三選一，長邊畫素數維持不變
# （16:9/9:16 長邊 1920、短邊 1080；1:1 長短邊都是 1080，總畫素量跟 16:9 相近，
# 不會因為換比例就變模糊或過重）。**full 解析度 2026-09-11 從 1280x720/720x1280/
# 960x960 提升到 1920x1080/1080x1920/1080x1080**（一般俗稱的「Full HD」標準三種
# 畫幅），舊解析度在近景細節（招牌文字、小型構件）上明顯不夠銳利。calib（CALIB
# 快渲/曝光校準用）維持 full 的 0.75 倍不變（1440x810/810x1440/810x810）——calib
# 本來就只是曝光快篩，不是最終品質，不需要跟著提到 Full HD。_ASPECT_LOCKED 追蹤
# 呼叫端是否已經手動呼叫 set_aspect() 明確指定過——`auto_frame_and_light()`
# （§15.4）會依主體實際包圍盒的高寬比自動選一個合理值，但只在呼叫端**沒有**手動
# 鎖定時才動，不會覆寫明確指定的選擇。
ASPECT = "16:9"          # '16:9' | '9:16' | '1:1'
_ASPECT_LOCKED = False
_ASPECT_SIZES = {
    "16:9": {"calib": (1440, 810), "full": (1920, 1080)},
    "9:16": {"calib": (810, 1440), "full": (1080, 1920)},
    "1:1":  {"calib": (810, 810), "full": (1080, 1080)},
}


def set_aspect(aspect: str) -> None:
    """明確指定畫幅比例（scene_pkg 用，§16）：在 import 本模組後、呼叫 main() 前設定。
    `aspect` 為 '16:9'（橫幅，寬物件/場景類）/'9:16'（直幅，高樓/直立產品）/'1:1'
    （方幅，接近立方體比例的主體）。呼叫後 `auto_frame_and_light()` 不會再自動覆寫，
    尊重呼叫端的明確選擇。"""
    global ASPECT, RENDER_RES, _ASPECT_LOCKED
    if aspect not in _ASPECT_SIZES:
        fail("config", f"set_aspect: 未知比例 '{aspect}'（可用：{list(_ASPECT_SIZES)}）")
    ASPECT = aspect
    RENDER_RES = _ASPECT_SIZES[aspect]["calib" if CALIB else "full"]
    _ASPECT_LOCKED = True
    log("camera", f"set_aspect 覆寫：{ASPECT}（{RENDER_RES[0]}x{RENDER_RES[1]}）")


def set_engine(name: str) -> None:
    """切換渲染引擎（2026-09-11 新增）。在 import 本模組後、呼叫 main() 前設定；
    環境變數 `BLENDER_TEMPLATE_ENGINE=eevee` 是等價的無程式碼入口。

    `name='cycles'`（預設）：正式成品路線——CPU + 降噪 + 256spp，曝光守衛強制生效。

    `name='eevee'`：**佈局預覽專用**——「幾何對不對」類的問題（構圖/比例/穿模/
    Z-fighting/漏件）十秒內就能出圖回答，不需要等 Cycles 的 2-5 分鐘。本機
    Blender 5.1.2 headless 實測可用（128x128 全流程 2.46 秒出圖；引擎 enum 只有
    'BLENDER_EEVEE'，5.1 沒有 _NEXT 這個識別字）。**三個明知的限制，不要在正式
    交付時用**：① `mat_lib.make_glass()` 這類 Transmission=1 材質在 EEVEE 下不走
    同一條路徑，穿透/折射表現與成品不一致，預覽圖裡的玻璃顏色/透明度不可信；
    ② EEVEE 沒有 Cycles 的完整 GI 與降噪，陰影與間接光落差大；③ 因此曝光守衛
    （LUMA 目標帶）在 EEVEE 模式下**只報告不擋**（`SCENE_STATE.exposure_enforced
    = false`）——不要拿預覽圖的 LUMA 值去調正式配方的能量，兩者不是同一個物理。
    正確用法：EEVEE 快速迭代到構圖/比例定案 → 切回 cycles 跑 CALIB 校曝光 →
    再跑正式渲染。

    **唯一例外（2026-09-13 新增）：3 渲 2／賽璐璐路線（`mat_lib.make_cel()` 的
    ShaderToRGB 節點鏈）EEVEE 就是成品引擎**——這條路線切回 cycles 不報錯但會安靜地
    做錯（實測：主體最亮的 base 階整片消失、畫面塌到 mid 階、色票全歪），所以上面
    「EEVEE 迭代 → 切 cycles 校曝光」的順序**不適用**；改為 EEVEE 直接出成品，品質
    保證看色階數（`audit_band_count()`）＋ `set_view_transform('standard')` ＋
    `setup_freestyle()`，見 `styles/genre/anime-cel-daylight.md` 與 SKILL.md §9.5。"""
    global ENGINE
    if name not in ("cycles", "eevee"):
        fail("config", f"set_engine: 未知引擎 '{name}'（可用：cycles/eevee）")
    ENGINE = name
    log("render", f"set_engine 覆寫：{ENGINE}")


def set_view_transform(name: str) -> None:
    """切換色調映射（2026-09-13 新增）。`name='agx'`（預設）／`name='standard'`。
    環境變數 `BLENDER_TEMPLATE_VIEW_TRANSFORM=standard` 是等價的無程式碼入口。

    **3 渲 2／賽璐璐（`styles/genre/anime-cel-daylight.md`）必須用 'standard'**：
    實測同一個 `mat_lib.make_cel()` 材質，AgX 下主色階 #E89490(232,148,144) →
    #C29490(194,148,144)，紅通道掉 38，且最暗階被壓掉——「色票一比一還原」只在
    Standard 成立。

    **PBR 路線不要用 'standard'**：studio/outdoor_golden/night 的曝光目標帶（§10.2）
    是照 AgX 校準的，換掉會讓整條曝光守衛失去意義。

    `'standard'`（＝ 3 渲 2 路線）下 LUMA 曝光帶本來就不能當品質保證（EEVEE 的
    `exposure_enforced=False`，只報告不擋），改看**色階數**——`T.main()` 偵測到
    `VIEW_TRANSFORM == "Standard"` 會自動跑一次 `audit_band_count()` soft 審計，
    寫進 `SCENE_STATE.band_audit` 並印出 `BAND_STATS:` 一行。
    """
    global VIEW_TRANSFORM
    key = {"agx": "AgX", "standard": "Standard"}.get(name.lower())
    if key is None:
        fail("config", f"set_view_transform: 未知色彩映射 '{name}'（可用：agx/standard）")
    VIEW_TRANSFORM = key
    log("render", f"set_view_transform 覆寫：{VIEW_TRANSFORM}")


def setup_freestyle(thickness: float = 2.4, color=(0.007, 0.00605, 0.01161),
                    silhouette: bool = True, border: bool = True, crease: bool = True,
                    linestyle_name: str = "OutlineStyle") -> dict:
    """掛上 Freestyle 外輪廓線（3 渲 2／賽璐璐的必要元件，見
    `styles/genre/anime-cel-daylight.md`）。render 之前呼叫即可。

    **兩種描邊路線，依需求挑一個（不要同時用，會疊線）**：
      - `setup_inverse_hull()`——背面法（inverse hull），《罪惡裝備》系列用的就是這個。
        線寬可逐部位控制、可以只留最外圈剪影線、線是幾何所以放大不糊。代價是每個
        要描邊的物件多一份幾何，且線寬要自己依鏡頭距離算（本檔的
        `outline_push_distance()` 已經把公式包好）。
      - 本函式（Freestyle）——不必複製幾何、單一線寬全場通用，適合線寬不講究的
        快渲或遠景；`setup_selective_outline()` 是它的前景/背景分層版。
    舊版本寫「禁用反轉外殼」是**過度概括**：實測失敗的 7 種寫法全部是 shader／modifier
    路線（Solidify `offset=±1` × `use_flip_normals`、等比放大複製 × 法線反轉），
    0 種畫出可量測的輪廓線（暗色畫素佔比 0.0%）、其中 4 種還把主體高光階整片吃掉
    ——根因是 Blender 不支援 multipass shader，以及「反轉了面法線卻沒有只畫背面」。
    補上「真外殼 + 只畫背面」這兩步之後就成立（見 `make_outline_shell()`）。
    Freestyle 仍是可用的選項：EEVEE 與 Cycles **都可用**、headless 可跑
    （實測 2.7s／2.9s 出圖），線色畫素佔比 0.9-1.1%。

    **5.1 API 陷阱（本函式已內建處理）**：`lineset.linestyle` 預設是 `None`，直接寫
    `.color` 會 `AttributeError: 'NoneType' object has no attribute 'color'`——必須先
    `bpy.data.linestyles.new()` 指派一個 LineStyle 資料塊。

    color 給**線性**值（`mat_lib.hex_to_linear('#14121C')` → (0.007,0.00605,0.01161)），
    不要填「看起來夠黑的 0-1 灰」。thickness 2-3（1080p 下約 2-3px）；實測 2.4px 線
    因抗鋸齒混色，核心畫素落在 (67,58,70) 比理論值亮——**要更黑的線請加粗，不要靠
    把色值調更黑硬救**。`silhouette`/`border`/`crease` 三者都開＝輪廓 + 邊界 + 摺線。

    回傳設定摘要（供 SCENE_STATE 記錄）。**不要在 cel 材質內另外做描邊**，會出現雙線。
    """
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("LineSet")
    ls.select_silhouette = silhouette
    ls.select_border = border
    ls.select_crease = crease
    ls.select_edge_mark = False
    if ls.linestyle is None:  # 5.1：LineSet 預設沒有 LineStyle 資料塊
        ls.linestyle = bpy.data.linestyles.new(linestyle_name)
    ls.linestyle.color = color
    ls.linestyle.thickness = thickness
    info = {"freestyle": True, "thickness": thickness, "color": list(color),
            "silhouette": silhouette, "border": border, "crease": crease}
    log("render", f"setup_freestyle：thickness={thickness} color={tuple(round(c, 4) for c in color)}")
    return info


def setup_selective_outline(fg_collections=None, bg_collections=None,
                            fg_thickness: float = 2.6, fg_color=(0.014, 0.012, 0.015),
                            bg_thickness: float = 1.1, bg_color=(0.26, 0.25, 0.30),
                            silhouette: bool = True, border: bool = True,
                            crease: bool = True) -> dict:
    """ZZZ 級選擇性描邊：前景物件粗深線、背景建築細淡線（或無線）。

    絕區零／原神級畫面的描邊不是全場單一線寬——**焦點物件（角色/道具/車輛）用粗深色
    線勾出剪影，背景建築/遠景用細淡線甚至不描**，畫面才有景深層級。全場同線寬會把
    背景拉到跟前景同一平面，是「塑膠感」來源之一。

    實作走 Freestyle 的 `select_by_collection`（Blender 5.1.2 headless 實測，
    `.capybala/test-scripts/zzz_look_proto.py` m10：FG collection 出粗深線、
    BG collection 無線，分層正確）。`fg_collections`/`bg_collections` 傳 collection
    名稱字串清單；傳 None 的那一組不建 lineset（＝不描）。

    用法：場景包 layout 階段把物件分進 `FG`/`BG` 兩個 collection（命名自訂），
    render 前呼叫本函式。與 `setup_freestyle()` 互斥——**兩者只選一個**，
    同時呼叫會出現兩套 lineset 疊線。
    """
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    made = []
    for tag, colls, thick, col in (("FG", fg_collections, fg_thickness, fg_color),
                                   ("BG", bg_collections, bg_thickness, bg_color)):
        if not colls:
            continue
        for cname in colls:
            c = bpy.data.collections.get(cname)
            if c is None:
                log("render", f"WARNING: setup_selective_outline 找不到 collection {cname}，跳過")
                continue
            ls = fs.linesets.new(f"LS_{tag}_{cname}")
            ls.select_by_collection = True
            ls.collection = c
            ls.collection_negation = "INCLUSIVE"
            ls.select_silhouette = silhouette
            ls.select_border = border
            ls.select_crease = crease
            ls.select_edge_mark = False
            if ls.linestyle is None:  # 5.1：LineSet 預設沒有 LineStyle 資料塊
                ls.linestyle = bpy.data.linestyles.new(f"Style_{tag}_{cname}")
            ls.linestyle.color = col
            ls.linestyle.thickness = thick
            made.append({"tag": tag, "collection": cname, "thickness": thick})
    log("render", f"setup_selective_outline：{made}")
    return {"selective_outline": made}


def setup_anime_post(bloom_threshold: float = 0.85, bloom_strength: float = 0.12,
                     bloom_size: float = 7.0, vignette: float = 0.0) -> dict:
    """動畫攝影後製（localized bloom + 選填暗角）：5.1 合成器掛 Fog Glow。

    舊卡「不建議疊 Bloom」的禁令只適用於**全場低門檻泛光**（平塗色塊被光暈污染）。
    ZZZ 級畫面的做法是**高門檻局部泛光**——只有自發光招牌/燈管/高光點超過 threshold
    才暈開，平塗色塊不受影響（實測 threshold=0.85 + strength=0.12 下灰底牆面零污染）。

    **5.1 API 陷阱（本函式已內建處理）**：scene compositor 的 node group 內
    **GroupInput 不會收到渲染畫面**——group 必須自己放 `CompositorNodeRLayers`
    取像素。只接 GroupInput 的 group 實測輸出全黑/全白垃圾（bisect 實測：
    comp_only 變體 mean_rgb=[0,0,0]）。末端接 NodeGroupOutput（group 內沒有
    Composite 節點，見 §8 落差表 #6）。
    """
    sc = bpy.context.scene
    cg = bpy.data.node_groups.new("AnimePost", "CompositorNodeTree")
    cg.interface.new_socket("Image", socket_type="NodeSocketColor", in_out="INPUT")
    cg.interface.new_socket("Image", socket_type="NodeSocketColor", in_out="OUTPUT")
    gout = cg.nodes.new("NodeGroupOutput")
    rl = cg.nodes.new("CompositorNodeRLayers")
    last = rl.outputs["Image"]
    if bloom_strength > 0.0:
        glare = cg.nodes.new("CompositorNodeGlare")
        glare.inputs["Type"].default_value = "Fog Glow"
        glare.inputs["Threshold"].default_value = bloom_threshold
        glare.inputs["Strength"].default_value = bloom_strength
        glare.inputs["Size"].default_value = bloom_size
        cg.links.new(last, glare.inputs["Image"])
        last = glare.outputs["Image"]
    if vignette > 0.0:
        ell = cg.nodes.new("CompositorNodeEllipseMask")
        ell.width = 1.6
        ell.height = 1.6
        blur = cg.nodes.new("CompositorNodeBlur")
        blur.filter_type = "FAST_GAUSS"
        blur.use_relative = True
        blur.factor_x = 35.0
        blur.factor_y = 35.0
        inv = cg.nodes.new("CompositorNodeInvert")
        mixv = cg.nodes.new("ShaderNodeMixRGB") if hasattr(bpy.types, "ShaderNodeMixRGB") \
            else cg.nodes.new("CompositorNodeMixRGB")
        mixv.blend_type = "MULTIPLY"
        mixv.inputs["Fac"].default_value = vignette
        cg.links.new(ell.outputs[0], blur.inputs[0])
        cg.links.new(blur.outputs[0], inv.inputs["Color"])
        cg.links.new(last, mixv.inputs["Color1"])
        cg.links.new(inv.outputs[0], mixv.inputs["Color2"])
        last = mixv.outputs[0]
    cg.links.new(last, gout.inputs[0])
    sc.compositing_node_group = cg
    log("render", f"setup_anime_post：bloom thr={bloom_threshold} str={bloom_strength} "
                  f"size={bloom_size} vignette={vignette}")
    return {"anime_post": True, "bloom_threshold": bloom_threshold,
            "bloom_strength": bloom_strength, "vignette": vignette}


# ---------------------------------------------------------------- 太空後製（鏡頭光暈）
def request_world_hook(fn) -> None:
    """登記「World 建完之後才執行」的函式，`main()` 在 `build_world()` 之後呼叫一次。

    用途：太空場景的星空環境貼圖必須接在 `build_world()` **之後**——那個函式會
    `bpy.data.worlds.new()` 整個換掉 World，在 `subject_fn()` 期間先接上的貼圖會被
    直接蓋掉（貼圖接了、渲染出來仍是純色背景）。跟 `request_outline()`／
    `request_lens_flare()` 同一種「登記 → main() 在正確時序執行」的解法。
    """
    global PENDING_WORLD_HOOK
    PENDING_WORLD_HOOK = fn


def request_lens_flare(**kwargs) -> None:
    """登記鏡頭光暈設定，`main()` 在 `setup_render()` 之後執行（時序理由見 PENDING_FLARE 註解）。"""
    global PENDING_FLARE
    PENDING_FLARE = dict(kwargs)


def setup_lens_flare(p=None, glare_type: str = "Ghosts", threshold: float = 48.0,
                     strength: float = 0.9, size: float = 0.25, iterations: int = 7,
                     mix: float = 1.0, keep_bloom: bool = True, vignette: float = 0.0,
                     label: str = "flare") -> dict:
    """鏡頭光暈（單一合成器鏈：RLayers →［Fog Glow］→ Glare → Mix(ADD) →［暗角］→ Output）。

    **5.1 API 落差（全部實測，見 §8 落差表）**：

    - 鬼影張數是 `Iterations`，**不是 `Size`**；`Size` 的作用域是 Bloom／Fog Glow。
    - `Size` 是 0–1 的 FACTOR：**賦值不夾、評估時飽和**——1.0／2.0／7.0 三組渲出的
      統計逐位元相同（等於覆蓋整張圖）。要「只暈一點」必須填 <1（例如 0.25）。
    - **`mix` 屬性不存在**（`hasattr(node,"mix")=False`；RNA 屬性列與 input sockets
      都沒有），混合量走 `Strength`——而 `Strength` 與 `Size` 不同：它 >1 仍單調增益
      （實測 0.1→4.0 對應 mean 15.19→24.35）。
    - 節點有三個輸出：`Image`／`Glare`／`Highlights`；本函式取 `Glare`＝**純光暈**，
      疊在（可選的）泛光底圖上，比死調門檻可控。
    - `Threshold` 是**原始亮度值**（不是 0–1，RNA soft_max=10000），要夾在「星點峰值」
      與「日盤亮度」之間：太低 → 每顆星都長出失焦光斑（整張圖被數千個光斑淹沒）；
      太高 → 什麼都不觸發。實測可用區間 40–60（星點峰值約 36、日盤 150）。
    - **節點移除會連帶移除連線**：逐鏡切換光斑節點之後若不把末端重接回
      `NodeGroupOutput`，下一鏡整張全黑（實測 mean 0.3）。本函式每次都**整條鏈重建、
      末端一定重接**，從結構上避開這個坑，不依賴呼叫端記得。

    `mix`＝光暈疊加比例（Mix 節點的 Fac：0＝純底圖、1＝底圖＋完整光暈）；
    `strength`＝光暈強度（>1 有效）；`glare_type`＝`Ghosts`（鬼影鏈，鏡頭感主要來源）／
    `Streaks`／`Fog Glow`／`Bloom`／`Simple Star`／`Sun Beams`／`Kernel`。
    `keep_bloom` ＋ `p`（配方 dict）＝沿用配方裡的 Fog Glow 泛光，讓泛光與光暈在同一條
    鏈上疊，不再各自搶 `compositing_node_group`。回傳實際套用的參數（寫進 SCENE_STATE）。
    """
    sc = bpy.context.scene
    use_bloom = bool(keep_bloom and p is not None)
    cg = bpy.data.node_groups.new(f"{label}_post", "CompositorNodeTree")
    cg.interface.new_socket("Image", socket_type="NodeSocketColor", in_out="OUTPUT")
    gout = cg.nodes.new("NodeGroupOutput")
    rl = cg.nodes.new("CompositorNodeRLayers")   # group 內 GroupInput 收不到畫面，必須自放
    base = rl.outputs["Image"]
    if use_bloom:
        bg_node = cg.nodes.new("CompositorNodeGlare")
        bg_node.inputs["Type"].default_value = "Fog Glow"
        bg_node.inputs["Threshold"].default_value = p["bloom_threshold"]
        bg_node.inputs["Size"].default_value = min(1.0, float(p["bloom_size"]))
        cg.links.new(base, bg_node.inputs["Image"])
        base = bg_node.outputs["Image"]
    flare = None
    if strength > 0.0:
        flare = cg.nodes.new("CompositorNodeGlare")
        flare.inputs["Type"].default_value = glare_type
        flare.inputs["Threshold"].default_value = threshold
        flare.inputs["Strength"].default_value = strength
        flare.inputs["Size"].default_value = min(1.0, float(size))
        if "Iterations" in flare.inputs:
            flare.inputs["Iterations"].default_value = int(iterations)
        cg.links.new(rl.outputs["Image"], flare.inputs["Image"])
    last = base
    if flare is not None and mix > 0.0:
        mixn = (cg.nodes.new("ShaderNodeMixRGB") if hasattr(bpy.types, "ShaderNodeMixRGB")
                else cg.nodes.new("CompositorNodeMixRGB"))
        mixn.blend_type = "ADD"
        mixn.inputs["Fac"].default_value = min(1.0, float(mix))
        cg.links.new(base, mixn.inputs["Color1"])
        cg.links.new(flare.outputs["Glare"], mixn.inputs["Color2"])
        last = mixn.outputs[0]
    if vignette > 0.0:
        ell = cg.nodes.new("CompositorNodeEllipseMask")
        ell.width = 1.6
        ell.height = 1.6
        blur = cg.nodes.new("CompositorNodeBlur")
        blur.filter_type = "FAST_GAUSS"
        blur.use_relative = True
        blur.factor_x = 35.0
        blur.factor_y = 35.0
        inv = cg.nodes.new("CompositorNodeInvert")
        mixv = (cg.nodes.new("ShaderNodeMixRGB") if hasattr(bpy.types, "ShaderNodeMixRGB")
                else cg.nodes.new("CompositorNodeMixRGB"))
        mixv.blend_type = "MULTIPLY"
        mixv.inputs["Fac"].default_value = vignette
        cg.links.new(ell.outputs[0], blur.inputs[0])
        cg.links.new(blur.outputs[0], inv.inputs["Color"])
        cg.links.new(last, mixv.inputs["Color1"])
        cg.links.new(inv.outputs[0], mixv.inputs["Color2"])
        last = mixv.outputs[0]
    cg.links.new(last, gout.inputs[0])   # 末端一定重接（5.1 節點移除斷線 → 下一鏡全黑）
    sc.compositing_node_group = cg
    info = {"glare_type": glare_type, "threshold": threshold, "strength": strength,
            "size": min(1.0, float(size)), "iterations": int(iterations),
            "mix": min(1.0, float(mix)), "bloom": use_bloom, "vignette": vignette,
            "nodes": len(cg.nodes)}
    FLARE_INFO.update(info)
    log("compositor", f"鏡頭光暈 {glare_type}：threshold={threshold} strength={strength} "
                      f"size={info['size']} iterations={iterations} mix={info['mix']} "
                      f"bloom={use_bloom}")
    return info


# ---------------------------------------------------------------- 3 渲 2 背面法外輪廓（inverse hull）
# 《罪惡裝備》系列自 Xrd 起所有旗艦作品畫輪廓線都用這個技法——官方 CEDEC2024 的講題
# 就叫「背面法」，他們自己在教材裡說這個手法已經用了 20 年以上、至今仍是第一線做法。
# 三個必須先知道的事實，少了任何一個都會做出「看起來像、但完全不是那回事」的線：
#
#   1. **Blender 不支援 multipass shader**——官方教材的環境對照表把 Blender 明確標成 ✕
#      （MAYA/3ds Max/Softimage 是 〇、Unity 有條件支援、UE4 要改引擎）。也就是說
#      「同一份 mesh 用 shader 畫兩次、第二次畫背面」這條主流路，在 Blender 走不通，
#      **一定要真的複製一份幾何**。這正是舊版本「反轉外殼實測 7 種寫法 0 種畫得出線」
#      的根因：那 7 種全部是 shader／modifier 路線，缺的是真外殼＋只畫背面這一步。
#   2. 線寬（＝外殼推出去的距離）**不能是固定常數**，得隨相機距離與 FOV 一起變。
#      距離拉遠 4 倍，外推距離也要跟著變 4 倍，畫面寬度才不變；鏡頭 zoom in（改 FOV
#      而不是改距離）時 tan(FOV/2) 變小，外推距離要跟著變小，線才不會跟著變粗。
#   3. 線寬與「這個部位要不要線」要能**逐部位／逐頂點**控制，才能做出漫畫的線的強弱
#      （臉頰粗、下巴細、睫毛不要線）。他們把這個控制值放在頂點色的 alpha：0.5 是標準、
#      0 是完全沒有線、1.0 是最粗（標準的兩倍）。
#
# 另外還有一個關鍵設計：**打光用的法線跟畫線用的法線是兩套**。日式卡渲為了控制陰影
# 會刻意改頂點法線（把頭髮法線球面化之類），改完之後外殼就推不直、線會斷；硬邊
# （hard edge）也會讓相鄰法線各指一個方向、外殼散開。他們的解法是準備兩組法線：
# 一組給打光、一組專門給背面法。本檔的做法是——母體愛怎麼改法線都行，**外殼一律沿
# bmesh 的幾何平均法線外推**（`v.normal`，不受自訂分割法線／硬邊影響），天生就是
# 那「第二組法線」，不需要額外存一份資料。

OUTLINE_SHELLS: set = set()   # main() 的自動幾何審查據此排除外殼，見 PARKED_MASTERS 同款註解


def outline_push_distance(px: float, distance: float, res: tuple | None = None,
                          lens: float | None = None, sensor_width: float = 36.0,
                          sensor_fit: str = "AUTO",
                          ortho_scale: float | None = None) -> float:
    """螢幕空間固定線寬 → 世界空間外推距離（背面法線寬的關鍵公式）。

    官方教材把背面法最常被忽略的坑講得很白：線寬（＝外殼推出去多少）不能是固定值。
    只寫一個固定 mm 數，近景會變成粗黑邊、遠景會細到起鋸齒；而且就算距離不變，
    光改 FOV（zoom in）線寬也會再跑掉一次。他們給的關係式是 `B = A · tan(θ)`
    （A＝相機到頂點的距離、θ＝FOV/2，B 就是外推量）。

    本函式把那個關係式補上「這條線在畫面上要佔幾個像素」這一項，直接回傳要推多遠：

        push = px · distance · sensor_width / (lens · 長邊像素數)

    等價於 `(px / 長邊像素數) · 2 · distance · tan(half_fov)`——因為
    `tan(atan(sensor_width / 2·lens))` 就是 `sensor_width / 2·lens`，兩邊相消後
    收斂成上面那個乾淨的形式。距離拉遠 → push 線性變大（畫面上線寬不變）；
    lens 變長（zoom in）→ push 變小（線不會跟著變粗）。兩件事一次解決。

    實測（1920×1080、50mm、36mm sensor、距離 5m、要 2.4px）→ push = 4.5mm；
    距離 20m → 18mm（4 倍，與距離成正比，符合教材的關係式）。

    `sensor_fit='AUTO'`（Blender 預設）時 sensor_width 對應**長邊**；本函式據此挑
    res 的長邊當分母——橫幅挑寬、直幅挑高，不必呼叫端自己判斷。

    **`ortho_scale`：ORTHO 相機走這條，不要用上面的透視公式**（3 渲 2 展示卡預設的
    就是 ORTHO 相機）。ORTHO 沒有透視，畫面寬度恆等於 ortho_scale、與相機距離無關，
    所以 world-per-pixel = ortho_scale / 長邊像素：

        push = px · ortho_scale / 長邊像素數

    跟 distance/lens 完全脫鉤——這才是「螢幕空間固定線寬」在 ORTHO 下的正確解。
    套透視公式會多乘一個 `distance·sensor_width/lens`（預設構圖 diag×1.8、35mm、
    sensor 36mm ≈ ×1.85），而且距離一改線寬就跟著變，ORTHO 的線寬本來就該是常數。
    實測（1920×1080、ortho_scale=2.8m、要 2.4px）→ push = 3.5mm，改變相機距離
    量到的值不變。
    """
    res = RENDER_RES if res is None else res
    if sensor_fit == "HORIZONTAL":
        long_px = res[0]
    elif sensor_fit == "VERTICAL":
        long_px = res[1]
    else:
        long_px = max(res)
    if long_px <= 0:
        fail("outline", f"outline_push_distance: res 不合法（{res}）")
    if ortho_scale:
        return px * ortho_scale / long_px          # ORTHO：與距離/焦距無關
    lens = (CAM_LENS if lens is None else lens) or 1.0
    if lens <= 0.0:
        fail("outline", f"outline_push_distance: 焦距必須 > 0（收到 {lens}）")
    if distance <= 0.0:
        fail("outline", f"outline_push_distance: distance/res 不合法（{distance}, {res}）")
    return px * distance * sensor_width / (lens * long_px)


def _read_vertex_alpha(me, attr_name: str, fill: float):
    """讀頂點色 alpha（每個頂點一個值）；沒有該屬性或全是空的回 None。

    POINT 域直接取；CORNER 域對每個頂點取平均——Blender 的 color_attribute_add
    預設建 CORNER/BYTE_COLOR，不支援 CORNER 的話這個功能等於不能用。沒有值可取的
    頂點填 `fill`（＝標準線寬，不是「沒有線」）。
    """
    a = me.color_attributes.get(attr_name) if hasattr(me, "color_attributes") else None
    if a is None:
        return None
    n = len(me.vertices)
    vals = [0.0] * n
    cnt = [0] * n
    if a.domain == 'POINT':
        for i in range(min(n, len(a.data))):
            vals[i] = float(a.data[i].color[3])
            cnt[i] = 1
    elif a.domain == 'CORNER':
        for li, loop in enumerate(me.loops):
            vi = loop.vertex_index
            if 0 <= vi < n:
                vals[vi] += float(a.data[li].color[3])
                cnt[vi] += 1
    else:
        log("outline", f"WARNING: 頂點色 '{attr_name}' 是 {a.domain} 域，只支援 POINT/CORNER，忽略")
        return None
    if not any(cnt):
        return None
    return [(vals[i] / cnt[i]) if cnt[i] else fill for i in range(n)]


_OUTLINE_MAT_CACHE: dict = {}


def _default_outline_material(mode: str):
    """借 mat_lib 的 factory（單一真相源）；找不到就 fail 而不是自己重寫一份。

    cache 跨呼叫共用——但 Blender 的 datablock 會被 `read_factory_settings()` 整批清掉，
    留下的參照會變成失效的 StructRNA（實測：同一支腳本裡先建了外殼、之後又 reset 一次
    場景，第二次呼叫就炸 `ReferenceError: StructRNA of type Material has been removed`）。
    所以每次取用前先確認它還活著。
    """
    cached = _OUTLINE_MAT_CACHE.get(mode)
    if cached is not None:
        try:
            cached.name          # 碰一下：已釋放的 datablock 會在這裡拋 ReferenceError
        except ReferenceError:
            cached = None
    if cached is None:
        try:
            import mat_lib as _M
        except ImportError:
            fail("outline", "make_outline_shell: 沒給 mat，且同層找不到 mat_lib.py——"
                            "請 copy_skill_resource_native 取出 mat_lib.py 到腳本同層")
        cached = _M.make_cel_outline(f"Mat_Outline_{mode}", mode=mode)
        _OUTLINE_MAT_CACHE[mode] = cached
    return cached


def make_outline_shell(target: bpy.types.Object, push: float, mat=None,
                       name: str | None = None, alpha_attr: str = "Col",
                       alpha_ref: float = 0.5, z_offset: float = 0.0,
                       cam=None, collection=None, mode: str = "cull") -> bpy.types.Object:
    """為 `target` 建一個背面法外殼（inverse hull），回傳外殼物件。

    做法（對應上面那三個事實）：
      1. 取 `target` 的 **evaluated mesh**（含 bevel 等 modifier 的實際結果）複製一份，
         烘進世界座標。
      2. 每個頂點沿 **bmesh 幾何平均法線**外推 `push`，再乘上該頂點的線寬權重
         `alpha(頂點色 alpha) / alpha_ref`——這就是「第二組法線」與逐部位線寬的落地。
      3. 反轉面法線（`mode='cull'` 時），配上只畫背面的材質——外推出來的部分在剪影處
         露出來，就成了一條線。**反轉了面法線卻沒有只畫背面，外殼會整片蓋住母體**
         （舊版 4 種寫法把主體高光階整片吃掉的就是這個）。
      4. `z_offset` 把整片外殼沿視線方向往相機的反方向推——推得夠遠時，只有最外圈的
         剪影線露得出來、內部的線全部被母體蓋掉。這是官方教材「背面をずらす」那一招
         （他們用來處理髮尖、鼻子這種不希望有線、或表情變形時突然冒出線的地方）。

    `alpha_attr` 指到頂點色屬性名（預設 `Col`）；母體沒有這個屬性時所有頂點權重 1.0
    （＝均勻線寬），不會報錯。`mat` 不給時自動向 mat_lib 借 `make_cel_outline()`。

    外殼會被登錄進 `OUTLINE_SHELLS`，`main()` 的自動穿模／懸空審查會跳過它們
    （外殼天生緊貼母體、底下也沒有支撐面，不排除的話每個外殼都會洗出假警報）。
    """
    if target is None or target.type != 'MESH':
        fail("outline", f"make_outline_shell: target 必須是 MESH 物件（收到 {target}）")
    if push <= 0.0:
        fail("outline", f"make_outline_shell: push 必須 > 0（收到 {push}）")
    if mat is None:
        mat = _default_outline_material(mode)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(deps)
    me_src = ev.to_mesh()
    try:
        mw = ev.matrix_world
        coords = [mw @ v.co for v in me_src.vertices]
        faces = [tuple(p.vertices) for p in me_src.polygons]
        alphas = _read_vertex_alpha(me_src, alpha_attr, alpha_ref)
    finally:
        ev.to_mesh_clear()
    if not coords or not faces:
        fail("outline", f"make_outline_shell: '{target.name}' 評估後沒有幾何（空 mesh？）")

    bm = bmesh.new()
    bverts = [bm.verts.new(co) for co in coords]
    bm.verts.index_update()
    dropped = 0
    for f in faces:
        try:
            bm.faces.new([bverts[i] for i in f])
        except ValueError:
            dropped += 1
    bm.normal_update()
    if dropped:
        log("outline", f"WARNING: {target.name} 有 {dropped} 個面無法複製（退化/重複），略過")
    scaled = 0
    for i, v in enumerate(bverts):
        w = 1.0
        if alphas is not None:
            w = max(0.0, min(2.0, alphas[i] / alpha_ref))
            if abs(w - 1.0) > 1e-6:
                scaled += 1
        if w <= 0.0:
            continue          # alpha <= 0 ＝這個部位不要線（官方教材的 0 值語意）
        v.co = v.co + v.normal * (push * w)
    if mode == "cull":
        bmesh.ops.reverse_faces(bm, faces=bm.faces)

    obj_name = name or f"Outline_{target.name}"
    me = bpy.data.meshes.new(obj_name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    obj = bpy.data.objects.new(obj_name, me)
    if collection is None:
        collection = target.users_collection[0] if target.users_collection else bpy.context.collection
    collection.objects.link(obj)
    if z_offset:
        cam = cam or bpy.context.scene.camera
        if cam is not None:
            # 注意：母體常經 add_box()/add_cyl() 的 transform_apply（§8 #9）→ location 已歸零、
            # 幾何烘在世界座標，讀 obj.location 會拿到 (0,0,0) 而不是物件真正的位置。
            # 一律用幾何包圍盒中心算視線方向。
            centre = sum((obj.matrix_world @ Vector(c) for c in obj.bound_box),
                         Vector((0.0, 0.0, 0.0))) / 8.0
            bpy.context.view_layer.update()   # 相機矩陣同理，讀之前先確認已更新（§8 #9）
            view = centre - cam.matrix_world.translation
            if view.length > 1e-9:
                obj.location = obj.location + view.normalized() * z_offset
        else:
            log("outline", f"WARNING: {obj_name} 指定了 z_offset 但場景沒有相機，略過該位移")
    OUTLINE_SHELLS.add(obj.name)
    log("outline", f"{obj_name}：push={push * 1000:.2f}mm 逐頂點加權 {scaled}/{len(bverts)} "
                   f"mode={mode} z_offset={z_offset * 1000:.1f}mm")
    return obj


def setup_inverse_hull(objects, px: float = 2.4, mat=None, exclude=None,
                       name_prefix: str = "Outline_", z_offset: float = 0.0,
                       alpha_attr: str = "Col", alpha_ref: float = 0.5,
                       mode: str = "cull", cam=None) -> dict:
    """一次為一批物件建背面法外殼，線寬自動依各自與相機的距離算（`px`＝畫面像素寬）。

    相機必須先就位（`build_camera()`/`set_camera()` 之後、`bpy.ops.render.render()` 之前
    呼叫）。回傳 `{"shells": [...], "info": {母體名: {distance_m, push_m}}}` 供
    SCENE_STATE 記錄——線寬是**算出來的數值**，跟 LUMA 一樣該進 JSON 而不是只留在腦裡。

    場景包用法：layout 完成、相機定案後，把要描邊的物件（FG collection 內容）
    丟進來即可。要「只有最外圈剪影線」就給 `z_offset`（≈ push 的 3-6 倍）；要
    Freestyle 那套全場單線寬就先不要用這個，兩套描邊會疊線。
    """
    cam = cam or bpy.context.scene.camera
    if cam is None:
        fail("outline", "setup_inverse_hull: 場景沒有相機——請先 build_camera() 或 set_camera()")
    # 相機的 matrix_world 要等 depsgraph 更新才會反映剛指派的 location（§8 #9 同一類坑）。
    # 少了這行，**第一個**物件會用過期的相機矩陣算距離——實測差 6.7 倍（真正的 7.22m
    # 被算成 1.07m），第二個物件才對（make_outline_shell 內部的 evaluated_depsgraph_get()
    # 順手觸發了更新）。症狀是同一批物件的線寬完全不成比例，而且渲染圖上不容易看出來。
    bpy.context.view_layer.update()
    cam_loc = cam.matrix_world.translation
    # ORTHO 相機的線寬跟距離/焦距無關（見 outline_push_distance() docstring）——
    # 讀出來交給它走專屬公式，不要拿透視公式硬算。
    cam_ortho = cam.data.ortho_scale if getattr(cam.data, "type", None) == "ORTHO" else None
    excl = set(exclude or [])
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    shells, info = [], {}
    for o in objs:
        if o is None or getattr(o, "type", None) != 'MESH' or o.name in excl:
            continue
        if o.name in OUTLINE_SHELLS:
            log("outline", f"WARNING: {o.name} 本身就是外殼，跳過（不要對外殼再套外殼）")
            continue
        centre = sum((o.matrix_world @ Vector(c) for c in o.bound_box),
                     Vector((0.0, 0.0, 0.0))) / 8.0
        dist = (centre - cam_loc).length
        push = outline_push_distance(px, dist, ortho_scale=cam_ortho)
        sh = make_outline_shell(o, push, mat=mat, name=f"{name_prefix}{o.name}",
                                alpha_attr=alpha_attr, alpha_ref=alpha_ref,
                                z_offset=z_offset, cam=cam, mode=mode)
        shells.append(sh)
        info[o.name] = {"distance_m": round(dist, 4), "push_m": round(push, 6),
                        "formula": "ortho" if cam_ortho else "perspective"}
    log("outline", f"setup_inverse_hull：{len(shells)} 個外殼，px={px} z_offset={z_offset * 1000:.1f}mm、"
                   f"線寬公式={'ortho(scale=' + str(round(cam_ortho, 3)) + ')' if cam_ortho else 'perspective'}")
    return {"shells": shells, "info": info, "px": px, "mode": mode,
            "push_formula": "ortho" if cam_ortho else "perspective"}


def request_outline(objects, px: float = 2.4, z_offset: float = 0.0, mat=None,
                    alpha_attr: str = "Col", alpha_ref: float = 0.5,
                    mode: str = "cull") -> None:
    """登記「相機就位後再建背面法外殼」的請求（3 渲 2 用）——在 `subject_fn()` 裡呼叫。

    為什麼不直接呼叫 `setup_inverse_hull()`：那支要讀相機矩陣來算線寬，而相機是
    `main()` 內部 `build_camera()` 跑完才存在的——`subject_fn()` 執行當下場景裡根本
    沒有相機，直接呼叫會 fail（這是 3 渲 2 路線過去最難接上的一段）。本函式只登記
    請求，`main()` 會在 `build_camera()` 之後、`setup_render()` 之前自動執行一次
    `setup_inverse_hull()`，線寬拿的是**真正的最終相機**（ORTHO 走 ortho 公式、
    透視走距離公式），量測結果寫進 `SCENE_STATE.outline`。

    重複呼叫＝以最後一次為準（外殼只建一次，不會疊兩層線）。
    """
    global PENDING_OUTLINE
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    if not objs:
        fail("outline", "request_outline: objects 不可為空")
    PENDING_OUTLINE = {"objects": list(objs), "px": px, "z_offset": z_offset, "mat": mat,
                       "alpha_attr": alpha_attr, "alpha_ref": alpha_ref, "mode": mode}
    log("outline", f"已登記背面法外殼請求：{len(objs)} 個物件、px={px}"
                   "（相機就位後由 main() 執行 setup_inverse_hull）")


def measure_outline_shell(shell: bpy.types.Object, target: bpy.types.Object,
                          sample: int = 240) -> dict:
    """量測外殼頂點到母體表面的最近距離分佈（回傳 min/median/max，單位 m）。

    `target` 用原始（未 evaluate）mesh 的 `closest_point_on_mesh()`——母體有 bevel 等
    modifier 時量到的距離會比外殼實際推的距離略小，這是預期誤差，容差要留。
    """
    verts = list(shell.data.vertices) if (shell is not None and shell.type == 'MESH') else []
    if not verts or target is None or target.type != 'MESH':
        return {"n": 0}
    step = max(1, len(verts) // max(1, sample))
    inv = target.matrix_world.inverted()
    ds = []
    for v in verts[::step]:
        p_world = shell.matrix_world @ v.co
        ok, loc, _nor, _idx = target.closest_point_on_mesh(inv @ p_world)
        if ok:
            ds.append((p_world - (target.matrix_world @ loc)).length)
    if not ds:
        return {"n": 0}
    ds.sort()
    return {"n": len(ds), "min_m": ds[0], "median_m": ds[len(ds) // 2], "max_m": ds[-1]}


def audit_outline_shell(shell: bpy.types.Object, target: bpy.types.Object,
                        expected_push: float, tol_frac: float = 0.35,
                        sample: int = 240) -> list:
    """數值驗證外殼：實際外推距離 vs 期望值（回傳問題清單，不直接 fail）。

    渲染圖上「有線」不等於線寬對——跟 LUMA／色階審計同一個道理，能量得出來的就用數值
    抓。中位數應該落在 `expected_push · (1 ± tol_frac)`；同時回報最小／最大值——逐頂點
    alpha 加權本來就會讓分佈變寬，那是預期行為不是問題，所以判準看中位數不看極值。
    """
    m = measure_outline_shell(shell, target, sample)
    if not m.get("n"):
        return [f"audit_outline_shell: {getattr(shell, 'name', shell)} → "
                f"{getattr(target, 'name', target)} 取樣不到最近距離（空 mesh 或物件無效）"]
    med, lo, hi = m["median_m"], m["min_m"], m["max_m"]
    log("outline", f"audit_outline_shell {shell.name}→{target.name}："
                   f"中位 {med * 1000:.2f}mm（期望 {expected_push * 1000:.2f}mm）"
                   f"範圍 {lo * 1000:.2f}–{hi * 1000:.2f}mm，n={m['n']}")
    if med < expected_push * (1.0 - tol_frac) or med > expected_push * (1.0 + tol_frac):
        return [f"{shell.name} 外推距離中位數 {med * 1000:.2f}mm 偏離期望 "
                f"{expected_push * 1000:.2f}mm 超過 {tol_frac * 100:.0f}%"
                f"——檢查 push 參數或母體是否被其他 modifier 改變了形狀"]
    return []


def make_internal_line(name: str, points, width: float, mat,
                       plane_normal=(0.0, 1.0, 0.0), lift: float = 0.002) -> bpy.types.Object:
    """內描邊（線在輪廓內部、不靠背面法）——官方教材稱之為「本村線」的手法。

    背面法只畫得出**剪影線**；衣服皺褶、肌肉線、分件線這種**圖案內部的線**它畫不出來。
    官方原本的解法很巧妙：在模型上重疊頂點（同位置一顆真的、一顆假的），把假頂點的 UV
    埋進貼圖上一條軸對齊的黑邊裡，於是那條黑邊就會沿著預定路徑蓋在模型表面——好處是
    **與貼圖解析度無關**，拉到超特寫也不會糊掉（一般畫在貼圖上的線一放大就爛掉）。

    他們的做法需要 UV 重排與貼圖佈局，本函式走**幾何版**：直接沿路徑鋪一條細帶
    （ribbon），給它平塗的線色材質。保留的是同一個真正重要的性質——**線是幾何、
    不是貼圖取樣，放大到特寫依然銳利**——省掉的是 UV 重排那道人工。

    `points`＝世界座標點列；`width`＝線寬（世界單位，通常給 `push × 2` 左右）；
    `plane_normal`＝這條線躺在哪個表面（貼合面的世界法線，決定線帶的展向）；
    `lift`＝沿法線抬高，避免與母體共面 Z-fighting（§8 #11，預設 2mm）。
    """
    pts = [Vector(p) for p in points]
    if len(pts) < 2:
        fail("outline", f"make_internal_line({name}): 至少需要 2 個點（收到 {len(pts)}）")
    if width <= 0.0:
        fail("outline", f"make_internal_line({name}): width 必須 > 0（收到 {width}）")
    n = Vector(plane_normal)
    if n.length < 1e-9:
        fail("outline", f"make_internal_line({name}): plane_normal 不可為零向量")
    n.normalize()
    half = width * 0.5
    bm = bmesh.new()
    rail_a, rail_b = [], []
    for i, p in enumerate(pts):
        a = pts[i - 1] if i > 0 else pts[i]
        b = pts[i + 1] if i + 1 < len(pts) else pts[i]
        tan = (b - a)
        if tan.length < 1e-9:
            tan = Vector((1.0, 0.0, 0.0))
        tan.normalize()
        side = tan.cross(n)
        if side.length < 1e-9:      # 路徑與表面法線平行 → 沒有可展的展向
            log("outline", f"WARNING: make_internal_line({name}) 第 {i} 點的切線與 plane_normal "
                           f"平行，該點用預設展向")
            side = Vector((1.0, 0.0, 0.0)).cross(n)
            if side.length < 1e-9:
                side = Vector((1.0, 0.0, 0.0))
        side.normalize()
        base = p + n * lift
        rail_a.append(bm.verts.new(base + side * half))
        rail_b.append(bm.verts.new(base - side * half))
    bm.verts.index_update()
    for i in range(len(pts) - 1):
        try:
            bm.faces.new((rail_a[i], rail_b[i], rail_b[i + 1], rail_a[i + 1]))
        except ValueError:
            pass
    bm.normal_update()
    if not bm.faces:
        bm.free()
        fail("outline", f"make_internal_line({name}): 沒有成功建出任何面")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat is not None:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    log("outline", f"{name}：{len(me.polygons)} 段，寬 {width * 1000:.1f}mm，抬升 {lift * 1000:.1f}mm")
    return obj


RENDER_RES = _ASPECT_SIZES[ASPECT]["calib" if CALIB else "full"]
RENDER_SAMPLES = 48 if CALIB else 256
SEED = 20260906  # 固定種子，結果可重現
# 上限留一半給系統（12 核機器）：Blender CPU 渲染預設吃滿所有邏輯核心，實測曾與 Electron+Node
# 同時把虛擬記憶體榨到見底、觸發 Windows AppHang（2026-09-07 事故，見 project memory）。
MAX_RENDER_THREADS = 6

# ---------- 曝光配方（實測校準，勿憑感覺改） ----------
# luma_band = 渲染後全圖亮度均值 (0-255) 的合格區間；clipped_max = 過曝面積比上限 %
PRESETS = {
    "studio": {
        # 棚拍純主體：深灰微水泥地 + 中性灰純色背景（2026-09-09 起取代 Sky IBL，
        # flat_background=True，見 build_world() docstring）+ 三點式
        "flat_background": True, "bg_color": (0.18, 0.18, 0.18),
        "ground_a": (0.17, 0.17, 0.175), "ground_b": (0.135, 0.135, 0.14),
        "sky_strength": 0.18, "sky_turbidity": 2.0, "sky_ground_albedo": 0.25,
        "sun_elev_deg": 32.0, "sun_azim_deg": -140.0, "sun_energy": 1.0,
        "sun_color": (1.0, 0.97, 0.92),
        "key_energy": 30.0, "fill_energy": 9.0, "rim_energy": 16.0,
        "fog_density": 0.0,
        "bloom_threshold": 3.0, "bloom_size": 5,
        "luma_band": (100.0, 170.0), "clipped_max": 0.5, "dark_max": 12.0,
    },
    "outdoor_golden": {
        "flat_background": False,  # 主體嵌在真實戶外環境的敘事場景，需要真實天空
        # 戶外黃金時刻：太陽仰角 ≥15°、暖色方向光、Sky IBL 中等
        # 校準教訓 1：太陽必須與相機同側（azim 約 -90°~-160°，相機在 -X-Y 象限）——
        #   azim=+128° 會變成背光，主體全黑（實測 mean=18.9 觸發曝光守衛）。
        # 校準教訓 2：fog_density 必須 0——world Volume Scatter 介質無限延伸，
        #   Sky 背景光穿過無窮距離散射體 → 透射率指數衰減到 0 → 全黑
        #   （實測：同參數無霧 mean=197.9，開霧 0.008 → mean=0.3）。
        #   這是 v3 小木屋黑圖的真正根因。白天場景要霧/上帝光 → 改用有限域
        #   volume domain box 包住場景，不可用 world volume（見 skill §8 #8）。
        "ground_a": (0.20, 0.32, 0.11), "ground_b": (0.26, 0.40, 0.15),
        "sky_strength": 0.32, "sky_turbidity": 2.2, "sky_ground_albedo": 0.25,
        "sun_elev_deg": 18.0, "sun_azim_deg": -135.0, "sun_energy": 2.4,
        "sun_color": (1.0, 0.82, 0.58),
        "key_energy": 0.0, "fill_energy": 0.0, "rim_energy": 0.0,  # 戶外不用三點式
        "interior_energy": 0.0,
        "fog_density": 0.0,       # 白天禁用 world volume（見上方教訓 2）
        "bloom_threshold": 1.2, "bloom_size": 7,
        "luma_band": (95.0, 175.0), "clipped_max": 0.8, "dark_max": 25.0,
    },
    "night": {
        "flat_background": False,  # 夜景敘事場景，天空/月光是氛圍的一部分
        # 夜景：practical light 主導 + 月光冷色低能量；天空僅微弱環境光
        # 校準教訓：地面/主體反射率低時 pure practical 不夠，月光 energy 0.4 +
        # sky 0.08 打底才離開死黑區（實測 0.25/0.04 → mean=12.6 觸發守衛）。
        "ground_a": (0.06, 0.07, 0.085), "ground_b": (0.045, 0.05, 0.065),
        "sky_strength": 0.08, "sky_turbidity": 2.0, "sky_ground_albedo": 0.1,
        "sun_elev_deg": 8.0, "sun_azim_deg": -120.0, "sun_energy": 0.4,
        "sun_color": (0.7, 0.78, 1.0),  # 月光冷色
        "key_energy": 0.0, "fill_energy": 0.0, "rim_energy": 0.0,
        "interior_energy": 150.0,
        "fog_density": 0.015,
        "bloom_threshold": 1.0, "bloom_size": 9,
        # dark_max 2026-09-11 從 70 下修至 55（拉麵屋台夜景事故：實測 dark_pct=59.4%
        # 仍在舊上限 70% 之內「通過」，但渲染圖除了 practical light 熱點以外幾乎全黑，
        # 70% 對夜景而言太寬鬆——55% 才是「大部分畫面仍有基礎可辨識度」的合理上限，
        # 跟 check_exposure() 新增的 mean-vs-p50 中位數落差檢查互為雙保險）。
        "luma_band": (15.0, 70.0), "clipped_max": 1.5, "dark_max": 55.0,
        # mean-vs-p50 落差上限：只有夜景需要這道檢查（practical light 稀疏、
        # 平均值被少數熱點撐高的失敗模式）。棚拍/戶外不設 = 停用——深色背景 +
        # 明亮主體本來就是大落差，那不是缺陷。
        "p50_gap_max": 18.0,
    },
    "space": {
        # 真空／軌道場景（2026-09-13 新增，§10.5）：天空不是光源——沒有介質，背景亮度
        # 由 World 底色本身決定，是「背景色」而不是「打光」的結果。
        "flat_background": True,
        # 1e-5 級是硬性下界：AgX 會把 1e-3 級（實測 0.0035）抬成一層固定灰幕
        # （量測 54.7/255、std=0），星點對比會被那層灰幕整片吃掉。掛上星空環境貼圖後
        # （space_lib.install_star_world）這個值只扮演「沒掛貼圖時的天光底」。
        "bg_color": (1.0e-5, 1.2e-5, 2.0e-5),
        # 地面在太空場景不該入鏡，但**不能省略**——main() 無條件 build_ground()，
        # 且懸空審查要拿它當支撐面。正解是保留這塊大平面、把配色壓到近黑（同 cel 路線
        # 用 set_ground_mat() 壓黑的做法）。0.012 級讓接地物件仍有一層極淡的著地面與
        # 陰影，讀得出「有東西站在上面」而不是純粹的虛空。
        "ground_a": (0.012, 0.012, 0.016), "ground_b": (0.006, 0.006, 0.010),
        "sky_strength": 0.0, "sky_turbidity": 2.0, "sky_ground_albedo": 0.05,
        # 唯一主光：SUN（無限遠平行光、沒有距離衰減）。仰角別低於 10°，否則鏡面物件的
        # 受光面會縮成一條邊。方位要與相機同側（§10.2#3），且必須和
        # space_lib.make_sun_disc() 的方向一致（日盤是純視覺物件、不參與打光）。
        "sun_elev_deg": 26.0, "sun_azim_deg": 55.0, "sun_energy": 3.2,
        "sun_color": (1.0, 0.96, 0.90),
        "key_energy": 0.0, "fill_energy": 0.0, "rim_energy": 0.0,
        "fog_density": 0.0,
        # bloom_size 必須 <1：5.1 實測 Glare 的 Size 是 0–1 的 FACTOR，**賦值不夾、
        # 評估時飽和**（1.0/2.0/7.0 三組渲出的統計逐位元相同＝覆蓋整張圖，旋鈕形同
        # 常數）。其他三組 preset 的 5/7/9 都落在同一個飽和區，見 §8 落差表。
        "bloom_threshold": 60.0, "bloom_size": 0.25,
        # 曝光帶刻意放寬：黑底佔畫面絕大多數，全畫面平均亮度天然就低——**正解是放寬
        # 整圖的帶、另外去驗主體可見像素比（audit_framing 的 coverage），不是把燈加亮**
        # （加亮只會污染校準基準）。dark_max 放到 98% 是因為星空場景本來就幾乎全黑。
        "luma_band": (1.0, 45.0), "clipped_max": 2.0, "dark_max": 98.0,
    },
}

# 相機（棚拍構圖實測可用；場景類任務自行調整）
CAM_LOC = (-1.35, -1.85, 1.05)
CAM_TARGET = (0.0, 0.02, 0.48)
CAM_LENS = 35
CAM_FSTOP = 2.8
# 2026-09-09 新增（查證：四個獨立驗證案例——相機/大樓/舞台/卡丁車——全部用
# ORTHO 相機，不是預設 PERSP。ORTHO 避免透視相機在近距離特寫時的桶狀/邊緣拉伸失真，
# 構圖留白也直接用 ortho_scale 一個數字控制，不用像透視相機那樣同時兼顧距離+FOV
# 兩個互相影響的變數才能保證「主體全身入鏡+留白」。CAM_TYPE='PERSP' 保留原本行為
# 當預設，不影響任何既有腳本；auto_frame_and_light()（§15.4）2026-09-09 起改用 ORTHO。
CAM_TYPE = "PERSP"          # 'PERSP' | 'ORTHO'
CAM_ORTHO_SCALE = 2.0        # 只在 CAM_TYPE='ORTHO' 時生效
# auto_frame_and_light() 覆寫三點式燈光位置/能量/尺寸時寫入這裡；build_lights() 一律優先
# 讀這個而不是 PRESETS 的固定絕對座標。None = 沿用舊行為（人體尺度棚拍固定配方）。
LIGHT_RIG_OVERRIDE: dict | None = None
# auto_night_fill()（2026-09-11 新增）覆寫夜景場景的基礎覆蓋補光時寫入這裡；
# build_lights() 讀到非 None 時改用這組診斷過範圍的補光，取代舊版寫死在世界原點、
# 不隨場景尺度縮放的單顆 InteriorLight。None = 沿用舊行為。
NIGHT_FILL_OVERRIDE: dict | None = None
# 太陽的圓盤角（半影寬度）：cel 的明暗界線必須是硬邊 → 0.0°，PBR 維持 4.0°（軟陰影）。
# None = 沿用 PBR 的 4.0°。setup_cel_studio() 會設成 0.0。
SUN_ANGLE_DEG: float | None = None
# cel 模式的陰影品質（setup_cel_studio() 設定；build_lights() 建完 SUN 後套用）。
# None = 沿用 Blender 預設。EEVEE 的陰影來自 shadow map，預設解析度不足時主體自投影的
# 明暗界線會出現沿網格排列的鋸齒（實測：提高網格細分數完全無效，因為那不是幾何問題）。
CEL_SHADOW_SETTINGS: dict | None = None
# 地面材質覆寫：地面一律由 build_ground() 建（懸空審查要拿它當支撐面），但 3 渲 2 不能
# 用程序化 noise 混染（cel 的表面必須是乾淨色塊）——set_ground_mat() 換成呼叫端的地面
# 材質後，build_ground() 只建同一塊大平面，不套 noise/距離漸層。None = 沿用舊行為。
GROUND_MAT_OVERRIDE = None
# 地面可見度覆寫（set_ground_void() 設定）：太空／真空場景沒有地面，但 main() 一定呼叫
# build_ground()（地面是自動懸空審查的支撐面、也是構圖審查預設排除的環境件）——刪掉它
# 會讓 ray_cast 失去支撐面。這裡讓地面「留在場景裡、相機與鏡面卻看不到」。
# None = 地面照常入鏡。
GROUND_VIS_OVERRIDE: dict | None = None
# 場景模式函式（setup_cel_studio() 等）寫入的強制配方覆寫；main() 在建場景前套用，
# 顯式傳給 main() 的 preset_overrides 仍然優先（呼叫端可再覆蓋）。
PRESET_AUTO_OVERRIDES: dict = {}
# 相機就位後才建得出來的東西：背面法外殼要讀相機矩陣算線寬，而相機是 main() 內部
# build_camera() 跑完才存在的——subject_fn() 當下場景裡沒有相機。request_outline()
# 登記請求，main() 在 build_camera() 之後、setup_render() 之前執行。
PENDING_OUTLINE: dict | None = None
OUTLINE_INFO: dict = {}   # 外殼線寬量測（母體名 → 距離/外推量），寫進 SCENE_STATE
# 太空場景的基礎補光覆寫（auto_space_fill() 設定）：build_lights() 讀到非 None 時用它
# 取代 auto_night_fill() 的補光——太空沒有大氣散射，兩盞補光只能是「行星反照」與
# 「深空環境反射」這種極弱來源，能量常數刻意比夜景再低一個量級。None = 未啟用。
SPACE_FILL_OVERRIDE: dict | None = None
# 鏡頭光暈請求（request_lens_flare() 設定）：scene.compositing_node_group 一次只能掛
# 一個 group，而 setup_render() 會用它建 bloom group——在 subject_fn() 期間直接呼叫
# setup_lens_flare() 會被後面的 setup_render() 整個蓋掉。登記式呼叫由 main() 在
# setup_render() 之後執行（跟 PENDING_OUTLINE 同一種時序解法）。
PENDING_FLARE: dict | None = None
FLARE_INFO: dict = {}     # 光暈實際套用的參數，寫進 SCENE_STATE
# World 建完之後才做得成的事（太空星空環境貼圖：build_world() 會 bpy.data.worlds.new()
# 整個換掉 World，提早接上的環境貼圖會被蓋掉）。main() 在 build_world() 之後執行一次。
PENDING_WORLD_HOOK = None


def set_camera(loc: tuple, target: tuple, lens: int = 35, fstop: float = 2.8,
               cam_type: str = "PERSP", ortho_scale: float | None = None) -> None:
    """相機參數覆寫（scene_pkg 用，§16）：在 import 本模組後、呼叫 main() 前設定。

    不呼叫則沿用上方棚拍預設。scene_pkg/build.py 從 config.CAMERA 讀值轉發。
    cam_type='ORTHO' 時 ortho_scale 必給（構圖留白的唯一控制量，見 §10.3 案例）；
    lens/fstop 對 ORTHO 相機無意義（正交投影沒有景深/焦距概念），會被忽略。"""
    global CAM_LOC, CAM_TARGET, CAM_LENS, CAM_FSTOP, CAM_TYPE, CAM_ORTHO_SCALE
    CAM_LOC = tuple(loc)
    CAM_TARGET = tuple(target)
    CAM_LENS = int(lens)
    CAM_FSTOP = float(fstop)
    CAM_TYPE = "ORTHO" if cam_type.upper() == "ORTHO" else "PERSP"
    if CAM_TYPE == "ORTHO" and ortho_scale is not None:
        CAM_ORTHO_SCALE = float(ortho_scale)
    log("camera", f"set_camera 覆寫：loc={CAM_LOC} target={CAM_TARGET} "
                  f"{'ORTHO scale=' + str(CAM_ORTHO_SCALE) if CAM_TYPE == 'ORTHO' else f'{CAM_LENS}mm f/{CAM_FSTOP}'}")

# ---------- 基礎設施 ----------

def log(step: str, msg: str) -> None:
    """結構化日誌：時間戳 + 步驟名 + 結果。"""
    print(f"[{datetime.datetime.now():%H:%M:%S}] {step}: {msg}", flush=True)


def fail(step: str, msg: str) -> None:
    """fail fast：印人類可讀錯誤並以非零碼結束（禁止 silent catch）。"""
    print(f"[{datetime.datetime.now():%H:%M:%S}] {step}: ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def verify_orientation_math() -> None:
    """啟動即斷言方向公約（實測 probe 驗證，Blender 5.1.2）。

    公約（右手定則，繞 +X 正角把 +Y 帶向 +Z、把 +Z 帶向 -Y）：
      Quaternion((1,0,0), +θ) @ (0,0,1)  →  y < 0  = 頂部倒向 -Y（「前傾」，若主體正面朝 -Y）
      Quaternion((1,0,0), -θ) @ (0,0,1)  →  y > 0  = 頂部倒向 +Y（「後仰」）
    椅子靠背事故根因：腳本註解宣稱「+θ 後仰」但實際是前傾，且從未被數值斷言抓出來。
    任何「傾斜」類建模一律用 lean_back_quat()/lean_fwd_quat()，不要手寫符號。
    """
    v_pos = Quaternion((1.0, 0.0, 0.0), math.radians(10.0)) @ Vector((0.0, 0.0, 1.0))
    v_neg = Quaternion((1.0, 0.0, 0.0), math.radians(-10.0)) @ Vector((0.0, 0.0, 1.0))
    if not (v_pos.y < 0 and v_neg.y > 0):
        fail("orientation", f"四元數方向公約失效（+θ y={v_pos.y:.3f}, -θ y={v_neg.y:.3f}）"
                            "——Blender 版本行為變更？重新 probe 並更新 skill §8")
    log("orientation", "方向公約自檢通過：繞+X 正角=頂部向-Y（前傾），負角=向+Y（後仰）")


def lean_back_quat(deg: float) -> Quaternion:
    """繞 X 軸「後仰」（頂部向 +Y）。前提：主體正面朝 -Y（相機側）。deg>0。"""
    return Quaternion((1.0, 0.0, 0.0), -math.radians(abs(deg)))


def lean_fwd_quat(deg: float) -> Quaternion:
    """繞 X 軸「前傾」（頂部向 -Y）。deg>0。僅用於刻意設計（如桌面傾斜），座椅靠背禁用。"""
    return Quaternion((1.0, 0.0, 0.0), math.radians(abs(deg)))


# ---------- 美感比例工具（SKILL §15：黃金比例 × 費波那契 × 曲線美感） ----------
# 使用者指定核心設計原則：1:1.618、0.618/0.382 分割與費波那契節奏套用到
# 整體長寬高、主次體量、分段結構、腰線/分割線、重心位置與細節節奏。
# 硬性工程尺寸（人體工學 §12.5、安裝規範 §13.5）優先於比例美感（§15.5 裁決順序）。

PHI = 1.6180339887498949        # 黃金比例 φ
PHI_INV = 0.6180339887498949    # 1/φ = φ-1
FIB = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987)  # 節奏/間距常用段


def fib_split(total: float) -> tuple:
    """黃金分割：回傳 (大段 0.618×total, 小段 0.382×total)。

    用途（§15.2）：主次體量比、腰線/分割線位置（0.382H 低腰線穩重、0.618H 高腰線挺拔）、
    視覺重心高度。禁止 50/50 對半分配。
    """
    big = round(total * PHI_INV, 6)
    return (big, round(total - big, 6))


def golden_series(total: float, n: int) -> list:
    """n 段黃金收分序列：相鄰段比 = 0.618，歸一化使總和 = total（§15.2 分段結構）。

    典型用途：塔身/椅背/櫃體的由下而上收分（第一段最大）。
    例：golden_series(400, 8) ≈ [156.1, 96.5, 59.6, 36.9, 22.8, 14.1, 8.7, 5.4]（probe 實測）。
    """
    if n < 2:
        fail("proportion", f"golden_series n={n}：至少 2 段才有收分節奏")
    raw = [PHI_INV ** i for i in range(n)]
    s = sum(raw)
    return [round(total * r / s, 6) for r in raw]


def nearest_fib(value: float) -> int:
    """最接近 value 的費波那契數（§15.2 細節節奏：窗格/鰭板/格柵間距、倒角半徑序列）。"""
    return min(FIB, key=lambda f: abs(f - value))


def assert_proportion(actual: float, target: float, label: str, tol: float = 0.08) -> None:
    """比例斷言（§15.1.3）：|actual/target - 1| > tol 即 exit 1。

    「跑通但比例走樣」與「跑通但方向錯」同罪——SCENE_STATE 的比例審計靠它落地。
    tol 預設 8%：容許建模取整誤差，攔截「手填差不多值」的漂移。
    """
    if target == 0:
        fail("proportion", f"{label}: target=0 無法計算比例")
    dev = abs(actual / target - 1.0)
    if dev > tol:
        fail("proportion", f"{label}: 實際 {actual:.4f} vs 黃金目標 {target:.4f}，"
                           f"偏差 {dev * 100:.1f}% > 容差 {tol * 100:.0f}%（§15——禁止手填近似值）")


# ---------- 組件常識斷言（SKILL §13；十字路口輪事故預防） ----------

def world_axis(obj: bpy.types.Object, local_axis: Vector = Vector((0, 0, 1))) -> Vector:
    """物件局部軸在世界座標的方向（單位向量）。讀前呼叫方需 view_layer.update()。"""
    c0 = obj.matrix_world @ Vector((0, 0, 0))
    c1 = obj.matrix_world @ local_axis
    return (c1 - c0).normalized()


def assert_axis_perp(obj: bpy.types.Object, travel_dir: Vector, label: str,
                     local_axis: Vector = Vector((0, 0, 1)), tol: float = 0.1) -> None:
    """軸向件斷言：obj 的 local_axis（世界系）必須⊥ travel_dir（§13.4）。

    典型用途：輪子（local_axis=柱體軸 (0,0,1)，travel_dir=車行進方向）。
    十字路口輪事故：輪軸=(0,1,0) 沿車身前後向（應為左右向），組合四元數心算錯誤。
    """
    axis = world_axis(obj, local_axis)
    dot = abs(axis.dot(travel_dir.normalized()))
    if dot > tol:
        fail("assertion", f"{label}: 軸向 {tuple(round(v,3) for v in axis)} 與行進方向 "
                          f"{tuple(round(v,3) for v in travel_dir.normalized())} 不垂直（|dot|={dot:.3f}>{tol}）")


def world_point(obj: bpy.types.Object, local_point: Vector) -> Vector:
    """物件局部座標點在世界座標的位置。讀前呼叫方需 view_layer.update()。"""
    return obj.matrix_world @ Vector(local_point)


def rigid_group_transform(objects: list, pivot, rotation_deg: float = 0.0, axis: str = 'Z',
                          translation: tuple = (0.0, 0.0, 0.0)) -> None:
    """多部件子總成「先軸對齊建好、最後一次套用剛體變換」（2026-09-10 新增，移植自
    紅白機參考案例——比較 famicom_v3 事故：手把由多個零件組成，每個零件各自算
    自己的最終世界座標/角度，結果傾斜角度跟主機側邊卡槽對不上、看起來像獨立立牌而不是
    嵌入式手把；正確做法反過來——整支手把（外殼/面板/D鍵/按鈕/刻字/螺絲/線材固定座）
    全部先用簡單、容易互相對齊的軸對齊座標建好，等全部零件都定位好了，才對整個集合
    一次套用同一個旋轉+平移矩陣。這保證子總成內部的相對關係跟建造時完全一致——不可能
    出現「某個零件的旋轉用了另一套公式，跟其他零件不一致」，因為根本沒有第二套公式：
    全部零件共用同一個最終變換。

    這是本 skill 已反覆踩過的同一類事故的通用解法：§12 椅背前傾事故、§13 十字路口輪軸
    事故、紅白機 v3 手把貼合角度事故，共同根因都是「子總成裡每個相關部件各自獨立心算
    旋轉/位移」。子總成需要整體傾斜/移動到最終姿態時，優先用這支函式，不要讓每個零件
    分別計算自己的最終世界座標。

    典型用法：子總成的每個零件建在 collection/群組裡（`active = group(...)` 或單純收集
    進一個 list），全部建完後：
        rigid_group_transform(list(controller_group.objects), pivot=(x, y, z),
                              rotation_deg=-7.0, axis='Z')

    objects: 這個子總成的全部物件。
    pivot: 世界座標旋轉軸心（子總成的裝配基準點，例如手把嵌入卡槽的接觸邊緣中點，
    不是隨便一個座標——旋轉軸心選錯，角度公式再對，位置還是會偏）。
    rotation_deg/axis: 繞 pivot、繞世界座標 X/Y/Z 其中一軸旋轉的角度。正負號跟任何
    旋轉一樣不能心算，先用 `--python-expr` probe 一個已知向量驗證方向再套用。
    translation: 旋轉之後再套用的世界座標平移（例如整支手把再往外挪一點對齊卡槽）。

    直接改寫每個物件的 `matrix_world`（世界座標保真變換，不受物件各自 local origin/
    parent 影響）。呼叫後記得 `bpy.context.view_layer.update()` 再讀取任何 world 座標。
    """
    axis_vec = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}.get(axis.upper())
    if axis_vec is None:
        fail("config", f"rigid_group_transform: 未知 axis '{axis}'（可用：X/Y/Z）")
    pivot_v = Vector(pivot)
    rot = Matrix.Rotation(math.radians(rotation_deg), 4, axis_vec)
    xf = Matrix.Translation(pivot_v) @ rot @ Matrix.Translation(-pivot_v)
    xf = Matrix.Translation(Vector(translation)) @ xf
    for o in objects:
        o.matrix_world = xf @ o.matrix_world
    bpy.context.view_layer.update()


def assert_slope_angle(obj: bpy.types.Object, local_p0: Vector, local_p1: Vector,
                       base_dir: Vector, expected_deg: float, label: str,
                       tol_deg: float = 3.0) -> float:
    """斜面/斜度斷言（§13.12，紅白機卡匣艙蓋斜面案例）：量測 obj 局部座標兩點連線
    （local_p0→local_p1，例如斜面的下緣與上緣）在世界座標下與 base_dir（通常是主體
    水平面的某個方向向量，例如 Vector((1,0,0))）的夾角，跟 expected_deg 比對。

    這個函式解決的是「斜度幾度」這種評圖時人眼/視覺模型從一張渲染圖幾乎不可能準確
    讀出來的數值——Blender 自己的幾何是精確的，不需要靠猜。expected_deg 應該來自
    Stage A 研究到的真實規格或設計簡報訂的數字，不是憑這個斷言反推「應該是多少」。
    用世界座標量測，不受物件自身旋轉/父階層影響；回傳實測角度供 SCENE_STATE 記錄。
    """
    p0 = world_point(obj, local_p0)
    p1 = world_point(obj, local_p1)
    edge_dir = (p1 - p0)
    if edge_dir.length < 1e-9:
        fail("assertion", f"{label}: local_p0/local_p1 兩點重合，無法定義斜面方向")
    dot = max(-1.0, min(1.0, edge_dir.normalized().dot(base_dir.normalized())))
    raw = math.degrees(math.acos(dot))
    actual = min(raw, 180.0 - raw)  # 斜度取銳角，不管邊向量指向哪一側
    if abs(actual - expected_deg) > tol_deg:
        fail("assertion", f"{label}: 斜度實測 {actual:.1f}° 與預期 {expected_deg:.1f}° "
                          f"差距 {abs(actual - expected_deg):.1f}° 超出容差 {tol_deg}°（世界座標量測）")
    return actual


def assert_mount_offset(face_obj: bpy.types.Object, pole_obj: bpy.types.Object,
                        label: str, min_offset: float) -> None:
    """資訊面安裝偏移斷言：面中心到桿軸心的水平距離 ≥ min_offset（§13.3/13.4）。

    十字路口輪事故：號誌牌中心與桿軸心距離 0.000m（穿心掛桿，正面被壓）。
    min_offset 建議 = 面厚/2 + 桿半徑 + 0.02。
    """
    def hcenter(o):
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        return (sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs))
    fx, fy = hcenter(face_obj)
    px, py = hcenter(pole_obj)
    dist = math.hypot(fx - px, fy - py)
    if dist < min_offset:
        fail("assertion", f"{label}: 資訊面中心距桿軸心 {dist:.3f}m < 下限 {min_offset:.3f}m（穿心安裝）")


def assert_long_axis_aligned(obj: bpy.types.Object, road_dir: Vector, label: str,
                             max_deg: float = 15.0) -> None:
    """長軸件斷言：obj 最長世界尺寸軸必須與 road_dir 對齊（§13.4，車沿路停放）。

    十字路口輪事故：轎車長軸沿世界 Y 垂直橫停在東西向道路上（yaw 語義翻譯錯）。
    """
    # dimensions 本就是世界軸對齊包圍盒 → 水平最長軸方向即世界單位軸
    if obj.dimensions.x >= obj.dimensions.y:
        long_dir = Vector((1.0, 0.0, 0.0))
    else:
        long_dir = Vector((0.0, 1.0, 0.0))
    rd = road_dir.normalized()
    ang = math.degrees(math.acos(min(1.0, abs(long_dir.dot(rd)))))
    if ang > max_deg:
        fail("assertion", f"{label}: 長軸與道路方向夾角 {ang:.1f}° > {max_deg}°（橫向/未對齊）")


def assert_within_room(obj: bpy.types.Object, room_bounds: tuple, label: str, tol: float = 0.02) -> None:
    """物件世界包圍盒必須落在房間內部邊界內（§7.7 現成資產擺位後強制跑一次）。

    溫馨咖啡廳事故（2026-09-08）：沙發/單椅/木餐椅/咖啡桌的擺位座標直接寫超過牆體位置
    （牆在 x=3.0，家具卻擺在 x=3.0~3.4），CALIB 與正式渲染都跑通、exit=0，肉眼看渲染圖
    才發現家具穿牆、半個在室外——根因是完全沒有程式化檢查，全靠人眼事後挑。asset_fetch_lib
    抓完現成資產、set location 之後，一律呼叫本函式驗證。

    room_bounds: ((x_min,x_max), (y_min,y_max), (z_min,z_max))，某軸傳 None 跳過該軸不檢查
    （例如天花板/吊燈本來就該貼近或超過牆體上緣，z 軸可能不適用同一組邊界）。
    tol：容許誤差（貼牆家具背板剛好碰到牆面、倒角造成的極小穿出）。
    """
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    axis_names = ("x", "y", "z")
    for i, bounds in enumerate(room_bounds):
        if bounds is None:
            continue
        lo, hi = bounds
        vals = [c[i] for c in corners]
        vmin, vmax = min(vals), max(vals)
        if vmin < lo - tol or vmax > hi + tol:
            fail("assertion", f"{label}: {axis_names[i]} 範圍 [{vmin:.3f}, {vmax:.3f}] "
                              f"超出房間邊界 [{lo:.3f}, {hi:.3f}]（穿牆/伸出室外）")


def assert_grounded(obj: bpy.types.Object, expected_base_z: float, label: str, tol: float = 0.03) -> None:
    """物件底部世界 z 必須貼合預期支撐面，不懸空、不陷入（§7.7 現成資產擺位後強制跑一次）。

    溫馨咖啡廳事故（2026-09-08）：擺花瓶時假設吧台蓋在 config 設定的座標上，但吧台母版
    工廠函式實際忽略了那個位移、蓋在別處，花瓶因此懸空在吧台真正位置以外的半空中——兩處
    程式碼各自「看似合理」，只有實際量測支撐面世界座標才抓得出來，不能憑座標算式互相假設。

    expected_base_z：這個物件底部理論上該在的世界 z——用實際量到的支撐面世界頂面 z
    （例如 bar_top 物件 vertices 的 max z），不要用假設的設計值；地板上直接放置傳 0.0。
    tol：容許誤差（家具腳墊高度、地板厚度）。
    """
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    base_z = min(c.z for c in corners)
    if abs(base_z - expected_base_z) > tol:
        fail("assertion", f"{label}: 底部 z={base_z:.3f} 偏離預期支撐面 z={expected_base_z:.3f}"
                          f"（偏差 {abs(base_z - expected_base_z):.3f}m > 容差 {tol:.3f}m——懸空或陷入）")


def assert_min_gap(group_a, group_b, min_gap: float, label: str) -> None:
    """兩組物件之間的水平淨空間距斷言（§13.8 動線/走道，教室無走道事故新增）。

    高中教室 v2 事故（2026-09-08）：Stage A 規劃階段完全沒把「動線」列進必備元素，
    桌椅網格用等距最小間距（0.65m）填滿整個房間——assert_within_room/assert_grounded
    都通過（家具沒穿牆、沒懸空），CALIB 曝光也過帶，但肉眼看渲染圖是「擠成一團、
    沒有路可以走」的教室，因為根本沒有一條路徑比其他家具間距明顯更寬。這個問題
    不是穿模/懸空這類幾何錯誤，是純粹「動線」這個功能性需求完全沒有被檢查過。

    group_a/group_b：單一物件或物件 list（例如「左半邊桌椅」vs「右半邊桌椅」、
    「最後一排桌椅」vs「後牆」）——只比較 XY 水平投影（走道是地面通行問題，不比較
    Z 高度）。算兩組世界座標包圍盒之間的最短水平距離。
    min_gap：最小淨空間（公尺）。一般走道抓 0.75-0.9m（對應常見建築規範的最小
    通道寬度）——這個數字要明顯大於一般家具與家具之間的正常間距（通常 0.3-0.6m），
    走道要「看得出來是走道」，不是隨便一個比較大的間距就充數。
    """
    def bbox_2d(objs):
        objs = objs if isinstance(objs, (list, tuple)) else [objs]
        xs, ys = [], []
        for o in objs:
            for v in o.bound_box:
                w = o.matrix_world @ Vector(v)
                xs.append(w.x)
                ys.append(w.y)
        return min(xs), max(xs), min(ys), max(ys)
    ax0, ax1, ay0, ay1 = bbox_2d(group_a)
    bx0, bx1, by0, by1 = bbox_2d(group_b)
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    gap = math.hypot(dx, dy) if (dx > 0 and dy > 0) else max(dx, dy)
    if gap < min_gap:
        fail("assertion", f"{label}: 兩組物件淨空間距 {gap:.3f}m < 走道下限 {min_gap:.3f}m"
                          "（§13.8 動線是必備元素，不是家具間隙就能替代）")


def assert_within_radius(objs, center_xy: tuple, max_r: float, label: str, tol: float = 0.0) -> None:
    """一組物件的水平位置必須落在指定圓形範圍內（2026-09-11 新增，拉麵屋台筷子事故）。

    事故根因：筷子插入筷筒的擺位公式用線性偏移（`a = -0.05 + i*0.02`）決定每根筷子的
    x/y，這個偏移範圍（±5cm，疊加 y 分量後最遠達 5.8cm）從沒跟筷筒的實際內半徑（4.5cm）
    做過交叉檢查——公式本身沒有語法或邏輯錯誤，錯在「算出一個分散範圍」跟「這個範圍
    真的落在容器半徑內」是兩件事，沒人驗證過第二件事，結果兩根筷子插到筒外懸空、
    肉眼一看就知道是 bug，但 CALIB/正式渲染的 exit code 都是 0。

    任何「把一組物件散佈/插入某個圓形容器造型」的擺位（筷筒裡的筷子、花瓶裡的花、
    筆筒裡的筆、瓶口周圍的螺絲、圓形陣列的裝飾釘），算完偏移公式、建好物件之後，
    都該呼叫一次本函式，不要只靠人眼看渲染圖才發現穿出容器外。

    objs：單一物件或物件 list。center_xy：容器中心的世界 `(x, y)`（只檢查水平投影，
    插入深度不夠/懸空另外用 `assert_grounded()`/`assert_min_gap()` 檢查，職責不重疊）。
    max_r：容器**內部**可用半徑——是開口內徑，不是容器外壁半徑，兩者容易搞混（筷筒
    壁本身有厚度，能放筷子的範圍比外觀半徑小一圈）。tol：容許誤差，物件本身有粗細時
    可以留一點餘裕，預設 0 表示物件中心點必須嚴格落在 `max_r` 之內。"""
    bpy.context.view_layer.update()
    items = objs if isinstance(objs, (list, tuple)) else [objs]
    cx, cy = center_xy
    violations = []
    for o in items:
        loc = o.matrix_world.translation
        r = math.hypot(loc.x - cx, loc.y - cy)
        if r > max_r + tol:
            violations.append(f"{o.name}(r={r:.3f})")
    if violations:
        fail("assertion", f"{label}: {len(violations)} 個物件水平距中心超出容許半徑 "
                          f"{max_r:.3f}m（容差{tol:.3f}m）——{', '.join(violations)}")


def assert_ring_hollow(obj, center_xy: tuple, z_range: tuple, label: str) -> None:
    """驗證一個「應該中空」的環狀物件真的有挖空，不是圓柱體殘留的底蓋面把洞堵住
    （2026-09-11 新增，機械錶錶圈事故）。

    事故根因：`Bezel_Ring`（錶圈）用圓柱體當起點建造，意圖之後挖穿中心做出環狀，
    但挖孔這一步從沒真的執行——`primitive_cylinder_add()` 預設自帶的頂/底面原封不動
    留在物件上，等於錶圈中心被一片不透光的「蓋子」直接封死。渲染結果是整片死白/
    死黑（依材質而定）蓋住蓋子後面的所有東西（這次是錶鏡+錶盤全部被擋住），肉眼
    一看就是「應該看得到裡面的地方看不到」，但**曝光/LUMA_STATS/dark_pct/mean-p50
    落差這類數值檢查全部測不出來**（蓋子本身材質/亮度都在合理範圍內，問題不是
    「太暗」或「太亮」，是「這裡本來該透空卻被實心面擋住」，跟亮度統計是兩個維度
    的問題）。這次實測踩過的排查陷阱：改材質粗糙度/反光度/specular、調燈光能量、
    關 bloom、關 caustics、限制 Cycles 反彈次數——全部沒用，因為問題從頭到尾是
    幾何，不是材質或光照，只有物理移除那片殘留面才解決。

    **實作用射線探測，不是量頂點半徑**（2026-09-11 實測修正：第一版本函式量測
    「有沒有頂點落在內半徑以內」，但 Blender `primitive_cylinder_add()` 預設的
    端面填法是 `NGON`——整片洞口只用外緣既有頂點圍成單一多邊形，不會另外生出
    一個中心頂點，量頂點半徑的版本完全抓不到這種蓋子，實測直接漏放過一個刻意
    重現的壞案例才發現。射線探測法不管蓋子是 `NGON` 單一多邊形、`TRIFAN` 三角扇、
    還是任何其他分面方式，只要中心真的被擋住就一定測得到）：從 `center_xy` 往
    `z_range` 上方發射一條射線，命中這個物件自己的任何一個面，就代表中心沒有
    真的挖空。

    任何「先建圓柱體、之後打算挖空做成環/管/圈」的建造流程（錶圈、o 型環、墊圈、
    畫框、甜甜圈狀量體），建好之後都該呼叫一次本函式，不要只憑「我有打算挖空」
    的印象就跳過驗證——挖孔步驟被跳過或失敗時不會報錯，只會在渲染圖上看到一片
    不該存在的擋光面。優先選擇：從一開始就用 `shape_lib.flat_ring()`（§0.5，不
    經過圓柱體+挖孔這個中間步驟，直接生成正確的中空環）取代「圓柱體+事後挖孔」
    這個更容易漏步驟的流程；已經用圓柱體+挖孔流程建造、或不確定挖孔是否成功時，
    才需要靠本函式事後驗證。

    obj：要檢查的物件。center_xy：環的中心世界座標 `(x, y)`。z_range：`(z_lo,
    z_hi)`——射線探測的世界座標高度範圍，通常包住這個環物件本身的厚度即可，
    不需要抓太大。"""
    bpy.context.view_layer.update()
    cx, cy = center_xy
    z_lo, z_hi = z_range
    inv = obj.matrix_world.inverted()
    origin_local = inv @ Vector((cx, cy, z_lo - 0.01))
    direction_local = (inv.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    max_dist = (z_hi - z_lo) + 0.02
    hit, loc, normal, face_idx = obj.ray_cast(origin_local, direction_local, distance=max_dist)
    if hit:
        world_hit = obj.matrix_world @ loc
        fail("assertion", f"{label}: {obj.name} 中心 ({cx:.4f},{cy:.4f}) 往上發射的探測射線"
                          f"擊中了物件自己的面（世界座標 {tuple(round(c, 4) for c in world_hit)}，"
                          f"face index {face_idx}）——這個「環」中心沒有真的挖空，可能是圓柱體"
                          "底蓋殘留面（機械錶錶圈事故同款 bug）：渲染會呈現一片不透光的蓋子"
                          "擋住後方物件，曝光/LUMA_STATS 這類數值檢查完全測不出來。")


def assert_inset_margins(host_obj, content_obj, label: str, sides: str = "LRT",
                         tol: float = 0.10, equal_tol: float = 0.15) -> dict:
    """內嵌元件（螢幕/按鍵群/銘牌/面板）與所在殼體邊緣的留白，抓「每一邊各自猜
    一個數字、沒人檢查是否對稱」這類問題（來源：iPod Classic 案例實測事故——
    螢幕左右留白各 4.2mm，上緣留白卻是 10.1mm，超過 2 倍差距，肉眼一看就覺得
    「螢幕位置怪怪的」，根因是 `win_top_z`/寬度置中是兩組互不相關的常數，從沒
    人要求兩者留白要互相參照）。

    真實工業設計裡，內嵌元件的留白幾乎一定是**刻意選定**的比例關係——最常見
    是三邊（左右+上，或左右+下）等寬，第四邊可以不同（例如手機螢幕下巴），
    但「不同」也該是設計決策的結果，不是算錯或沒算。**沒有明確參考數據時，
    預設抓等寬留白**——這比任意兩個不相關的數字更接近「看起來經過設計」的觀感。

    `sides`：檢查host左緣('L')/右緣('R')/上緣('T')/下緣('B')留白是否互相相等，
    預設 "LRT"（螢幕類最常見：左右上三邊等寬、下緣留給實體按鍵/logo 不強制）。
    `tol`：host/content 世界包圍盒量測容差。`equal_tol`：留白彼此間容許的相對
    差異比例（預設 15%——留 15% 餘裕給「上緣刻意留多一點放喇叭孔」這類真實
    案例，超過這個比例大概率是沒對齊，不是刻意設計）。

    回傳量到的四邊留白 dict（`{"L":, "R":, "T":, "B":}`，單位公尺），供呼叫端
    log 記錄或自行做更細的判斷；`sides` 指定的邊彼此差異超過 `equal_tol` 則
    `fail()`。"""
    bpy.context.view_layer.update()
    hc = [host_obj.matrix_world @ Vector(c) for c in host_obj.bound_box]
    cc = [content_obj.matrix_world @ Vector(c) for c in content_obj.bound_box]
    hx0, hx1 = min(c.x for c in hc), max(c.x for c in hc)
    hz0, hz1 = min(c.z for c in hc), max(c.z for c in hc)
    cx0, cx1 = min(c.x for c in cc), max(c.x for c in cc)
    cz0, cz1 = min(c.z for c in cc), max(c.z for c in cc)
    margins = {"L": cx0 - hx0, "R": hx1 - cx1, "T": hz1 - cz1, "B": cz0 - hz0}
    checked = {k: v for k, v in margins.items() if k in sides}
    vals = list(checked.values())
    if vals and (max(vals) - min(vals)) > equal_tol * max(abs(v) for v in vals):
        detail = ", ".join(f"{k}={v*1000:.1f}mm" for k, v in checked.items())
        fail("assertion", f"{label}: 內嵌留白不等寬（{detail}）——差異超過 {equal_tol*100:.0f}%，"
                          "多半是各邊各自設常數、沒有互相參照，不是刻意的設計選擇")
    return margins


# ---------- 通用幾何審查（§13.9；穿模/重疊/懸空/離群間距——一次掃整批物件） ----------
# 跟上面 assert_within_room/assert_grounded/assert_min_gap 的差別：那三個都要呼叫端
# 「已經知道該檢查誰、預期關係是什麼」（房間邊界、支撐面高度、走道兩側分組）。
# 這裡三個 audit_* 函式反過來——給一批物件，函式自己去發現有沒有異常，不需要預先
# 知道正確答案是什麼。代價是這類「自動發現」天生有假陽性風險（家具零件之間本來就
# 該貼合/相切），所以全部回傳問題清單（不直接 fail），由呼叫端用 report_or_fail()
# 決定要不要真的擋下來——先看清單合不合理，比照舊三個斷言「錯就直接 fail」更保守。

ASSEMBLY_MATES: dict = {}          # mark_assembly_mate() 登錄的意圖裝配配對：frozenset({a, b}) → note


def mark_assembly_mate(a, b, note: str = None) -> None:
    """宣告兩個零件是「刻意裝配在一起」的一對（§13.9；2026-09-14 新增）——供
    `audit_interpenetration()` 跳過這對，且跳過的對數會被記錄（不是靜默放行）。

    來源（2026-09-14，汽車底盤案例）：AABB 判穿模對**同軸嵌合件**天生全命中——卡鉗跨在
    碟盤上、輪圈套住輪胎、羊角軸承包住輪轂，兩件的世界包圍盒必然三軸都重疊，實測一台車
    自動審查回報 102 筆「穿模」，逐筆查證全是正確裝配。這種配對有兩條路，可以只用一條、
    也可以兩條並用：
      (1) **宣告配對**：`T.mark_assembly_mate("Brake_Caliper_F_L", "Brake_Disc_F_L")`，之後
          `audit_interpenetration()` 不再回報這一對——適合「本來就該嵌合/壓配」的固定配對；
      (2) **改用網格級判定**：`audit_interpenetration(objects, mode="bvh")`，AABB 只當候選
          快篩、結論由 BVH 面相交給——良好裝配（有淨空）的嵌合件自然不再命中，連宣告都不用。
    宣告負責語意（這對本來就該嵌合）、BVH 負責抓真正互穿（有互穿的嵌合件在 BVH 模式下照樣
    被回報），兩者互補。
    """
    pair = frozenset((str(a), str(b)))
    if len(pair) != 2:
        fail("assembly_mate", f"mark_assembly_mate({a!r}, {b!r})：兩端必須是相異的物件名")
    ASSEMBLY_MATES[pair] = str(note) if note else ""


def audit_interpenetration(objects: list, tol: float = 0.01, mode: str = "aabb",
                           respect_mates: bool = True) -> list:
    """兩兩掃描物件世界包圍盒，抓「穿模/重疊」候選（§13.9）。

    只有三軸重疊量都 ≥ tol 才回報——物件邊緣貼合（牆接地板、桌腳接桌面、椅背接
    椅座）本來就會在某一軸剛好重疊到 0 或極小值，這是正常的「相接」不是「穿模」；
    真正的穿模/重疊會在三個軸向都有實質重疊量。tol 預設 0.01m（1cm）——容忍
    浮點誤差跟肉眼看不出來的貼合誤差，只抓「看得出來/量得出來」的重疊。
    複雜度 O(n²)，物件數 >300 建議先用命名規則分批（同一批家具內部比較）而非
    整場景互比，避免無意義的跨區配對（窗跟吧台本來就不會互相穿模，不用比）。

    **`mode`——AABB 是篩子，不是結論**（2026-09-14 新增，來源：汽車底盤案例）：
      · `"aabb"`（預設）：只比世界包圍盒，輸出格式與舊版逐字相同（既有場景行為不變）。
        邊界貼合的方盒/家具/建築配對適用。
      · `"bvh"`：AABB 只當候選快篩（成本仍是幾次浮點比較），通過快篩的配對再用
        `BVHTree.overlap()` 做**網格級**面相交判定，只有真的互穿才回報。**機構/總成場景
        （同軸嵌合件）用這個**：車用總成實測 AABB 模式回報 102 筆「穿模」，逐筆查證全是
        卡鉗×碟盤、輪圈×輪胎、羊角×輪轂這類正確裝配——真正該抓的一筆沒漏，但雜訊會把
        訊號淹掉。曲面宿主（圓柱/球/外殼）上的附件同理（見 §13.9）。注意兩點：面與面
        **剛好貼合（淨空 0）也可能被判相交**，裝配件之間留一點公差即可；非 mesh 物件
        （曲線/空物件）無法做網格判定，會退回 AABB 候選並在訊息裡說明。
    **`respect_mates`**：預設 True 時跳過 `mark_assembly_mate()` 宣告過的配對（意圖裝配）。
    跳過的對數不靜默——有跳過就印一行 log 讓它可被稽核。
    """
    if mode not in ("aabb", "bvh"):
        fail("audit", f"audit_interpenetration(mode={mode!r})：只接受 'aabb' 或 'bvh'")
    bpy.context.view_layer.update()
    def bbox(o):
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))
    boxes = [(o, bbox(o)) for o in objects]
    issues = []
    bvh_cache: dict = {}
    n_mate_skipped = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            obj_a, ((ax0, ax1), (ay0, ay1), (az0, az1)) = boxes[i]
            obj_b, ((bx0, bx1), (by0, by1), (bz0, bz1)) = boxes[j]
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            oz = min(az1, bz1) - max(az0, bz0)
            if not (ox >= tol and oy >= tol and oz >= tol):
                continue
            name_a, name_b = obj_a.name, obj_b.name
            if respect_mates and frozenset((name_a, name_b)) in ASSEMBLY_MATES:
                n_mate_skipped += 1
                continue
            if mode == "bvh":
                for _o in (obj_a, obj_b):
                    if _o.name not in bvh_cache:
                        bvh_cache[_o.name] = _host_bvh([_o])[0]
                bvh_a, bvh_b = bvh_cache[name_a], bvh_cache[name_b]
                if bvh_a is None or bvh_b is None:
                    issues.append(f"{name_a} × {name_b}: AABB 三軸重疊 {ox:.3f}×{oy:.3f}×{oz:.3f}m，"
                                  "但網格無法評估（BVH 建樹失敗或非 mesh），退回 AABB 候選回報")
                    continue
                if not bvh_a.overlap(bvh_b):
                    continue
                issues.append(f"{name_a} × {name_b}: 網格相交（BVH 實測；AABB 重疊 "
                              f"{ox:.3f}×{oy:.3f}×{oz:.3f}m）")
            else:
                issues.append(f"{name_a} × {name_b}: 三軸重疊 {ox:.3f}×{oy:.3f}×{oz:.3f}m（穿模/重疊候選）")
    if n_mate_skipped:
        log("geometry_audit", f"audit_interpenetration: {n_mate_skipped} 組已宣告的意圖裝配配對"
                              "（mark_assembly_mate）跳過回報")
    return issues


def audit_floating(objects: list, max_gap: float = 0.01, max_sink: float = 0.01) -> list:
    """物件底面往下 raycast，抓「懸空/陷入」（§13.9）——跟 assert_grounded 的差別：
    不需要事先手動算好 expected_base_z，直接問場景「這個物件底下有沒有東西接住它」。

    每個物件從底面 5 個取樣點（bbox 底面四角+中心）垂直向下打一條 ray，找最近的
    命中面。淨空距離 > max_gap 判定懸空；命中面在物件底部之上（物件陷進去了）
    超過 max_sink 判定陷入。5m 內完全沒打中任何東西 = 嚴重懸空（或物件飄出場景外）。
    只傳「應該落地/落在某個面上」的物件清單——天花板燈、吊燈這類本來就該懸空的
    物件不要傳進來（跟 assert_grounded 一樣，呼叫端自己排除）。

    **max_gap/max_sink 預設 10mm 是建築/家具尺度校準的，小型精密產品務必自己覆寫成
    更小的值**（2026-09-09 新增，相機案例實測抓到的真實盲區）：一台 138mm
    寬的復古相機，過片扳手臂懸空 2.6mm——這個縫隙完全在 10mm 預設容差內，本函式跑過
    回報「無問題」，但實際渲染/開 `.blend` 檢查都看得出來是真的懸空（2.6mm 相對於
    扳手臂自己只有 1.6mm 的厚度，比例上非常明顯）。10mm 對一棟建築的窗框或一件家具
    的腳墊是合理容差，對零件本身只有個位數 mm 厚的小型產品完全不成比例。**呼叫端
    務必依主體實際尺度覆寫**：小型產品（<0.3m）建議 max_gap/max_sink 收到 0.001-0.002
    (1-2mm)；一般家具/器材（0.3-2m）維持預設 10mm 尚可；建築/大型場景可以放寬到
    50-100mm。不要對任何尺度的主體都照抄預設值。

    **bbox 快篩前置（2026-09-10 新增，來源：復古腳踏車案例——368 個物件超過 `T.main()`
    自動審查的舊版單一門檻 300，整項審查被跳過，腳架懸空這種一秒鐘該抓到的問題沒人
    攔）**：每個物件先用便宜的 bbox 比較（`O(n²)` 但每次只是 6 個浮點數比較，真正的
    瓶頸從來不是這裡，是下面的 `scene.ray_cast()`）找「正下方有沒有另一個物件的 bbox
    頂面落在 `max_gap` 容差內」——找得到就直接判定「有支撐候選」、跳過這個物件的
    raycast；找不到才進入下面真正的逐點 raycast（5 取樣點 × 最多 4 層鑽透，這才是
    昂貴的部分）。這個快篩只會**省掉不必要的 raycast**、不會漏掉真正的懸空——快篩
    容差用的是呼叫端傳入的 `max_gap` 本身（不是放寬過的門檻），任何 bbox 距離超過
    `max_gap` 的物件一律照樣進入完整 raycast 驗證，快篩不合格不代表懸空、只代表
    「不能單靠 bbox 快速斷定沒事，要驗證」。實測：良好裝配的場景（大多數零件真的
    彼此接觸）能省掉 80%+ 的 raycast，讓這支函式在物件數更高的場景也能負擔得起。
    """
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    issues = []
    _bbox_cache = []
    for o in objects:
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        _bbox_cache.append((o, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    for idx, o in enumerate(objects):
        _, x0, x1, y0, y1, zmin, _zmax = _bbox_cache[idx]
        has_bbox_support = False
        for jdx, (p, px0, px1, py0, py1, _pz0, pz1) in enumerate(_bbox_cache):
            if p is o:
                continue
            if px1 < x0 or px0 > x1 or py1 < y0 or py0 > y1:
                continue  # XY 足跡不重疊，不可能是正下方支撐
            if abs(pz1 - zmin) <= max_gap:
                has_bbox_support = True
                break
        if has_bbox_support:
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        samples = [(x0, y0), (x0, y1), (x1, y0), (x1, y1), (cx, cy)]
        best_gap = None
        for sx, sy in samples:
            # 起點稍微抬高，仍在物件自己的水平範圍內——第一擊常常打到物件自己的
            # 底面（尤其取樣點就是 bbox 底面四角/中心本身），必須連續往下鑽過自己
            # 才找得到真正在下面的支撐面，不能一遇到自己就整個取樣點放棄。
            origin = Vector((sx, sy, zmin + 0.05))
            remaining = 5.0
            for _ in range(4):  # 最多鑽過 4 層重疊物件，正常情境 1-2 次就夠
                hit, loc, _normal, _idx, hit_obj, _matrix = scene.ray_cast(deps, origin, Vector((0.0, 0.0, -1.0)), distance=remaining)
                if not hit:
                    break
                if hit_obj is o:
                    step = (origin.z - loc.z) + 0.0005
                    remaining -= step
                    origin = Vector((sx, sy, loc.z - 0.0005))
                    if remaining <= 0:
                        break
                    continue
                gap = zmin - loc.z
                if best_gap is None or abs(gap) < abs(best_gap):
                    best_gap = gap
                break
        if best_gap is None:
            issues.append(f"{o.name}: 底部 5 個取樣點往下 5m 內都沒偵測到任何支撐面（嚴重懸空或飄出場景外）")
        elif best_gap > max_gap:
            issues.append(f"{o.name}: 底部與最近支撐面淨空 {best_gap:.3f}m > 容許 {max_gap:.3f}m（懸空）")
        elif best_gap < -max_sink:
            issues.append(f"{o.name}: 底部陷入支撐面 {-best_gap:.3f}m > 容許 {max_sink:.3f}m（陷入）")
    return issues


def mark_side_attached(obj: bpy.types.Object, host: str = None, stand_off: float = None) -> None:
    """標記這個物件是側向鎖固/懸臂固定，不是靠重力平放在下方支撐面上（2026-09-10 新增，
    來源：長征二號F發射台案例——T.main() 的自動幾何審查把全部 mesh 物件無差別餵進
    audit_floating()，但這支函式自己的文件早就寫明「只傳應該落地的物件清單，呼叫端
    自己排除」；懸臂吊車臂、螺栓鎖在桁架/桅杆側面的告示牌、格狀桁架的斜撐/環箍、
    鎖在梯柱側面的爬梯踏階——這類物件底下天生不會有任何東西，向下 raycast 的
    audit_floating 邏輯對它們一定會誤判懸空，因為它們根本不是「放在什麼上面」，
    是「鎖在旁邊」。在建構函式裡建好這類物件後立刻呼叫本函式（設一個 custom
    property），T.main() 的自動審查會據此跳過它們，不需要呼叫端自己維護排除清單、
    也不影響 audit_interpenetration（穿模檢查不受此標記影響，側向鎖固一樣可能穿模）。

    **排除懸空檢查是減法，這裡同時把它變成有帳可查的宣告（§13.9）**：`host` 宣告這個
    零件的宿主（物件名，只量它、不受場景其他幾何干擾），`stand_off` 宣告它與宿主表面
    之間「刻意保留」的距離（公尺，預設不給＝預期直接貼合、只剩防共面裕度）。兩個宣告
    都會被 audit_attachment_contact() 當**預期值**檢驗——只宣告不量測的排除，就是
    整批物件從檢查清單消失，這支函式不接受那種用法。
    """
    obj["_side_attached"] = True
    if host:
        obj["_attach_host"] = str(host)
    if stand_off is not None:
        obj["_attach_stand_off"] = float(stand_off)
    if obj.name not in SIDE_ATTACHED:
        SIDE_ATTACHED.append(obj.name)


# ---------- 貼附件貼合審查（§13.9；凸面宿主專用） ----------

ATTACH_CONTACT_DEFAULT_GAP = 0.02   # 20mm：貼附件離宿主表面的容許淨空（呼叫端依主體尺度覆寫）
SIDE_ATTACHED: list = []            # mark_side_attached() 登錄的物件名——排除懸空檢查要有帳可查


def side_attached_stats() -> dict:
    """回報側向鎖固標記的規模（§13.9）——「排除假警報」是減法，這裡讓減法的範圍可見：
    `count` 是登錄件數、`declared_host`/`declared_stand_off` 是有宣告的件數。T.main()
    在標記數 ≥10 且超過全部 mesh 物件一半時印 WARNING，因為那等於懸空審查對這批物件停用。
    """
    objs = [o for o in bpy.data.objects if o.get("_side_attached")]
    return {
        "count": len(objs),
        "declared_host": sum(1 for o in objs if o.get("_attach_host")),
        "declared_stand_off": sum(1 for o in objs if o.get("_attach_stand_off") is not None),
        "objects": [o.name for o in objs],
    }


# ---------- 接頭/軸承連接（§13.9；2026-09-14 新增） ----------
ATTACH_JOINT_DEFAULT_GAP = 0.05    # 50mm：接頭/軸承件的預設接合包絡（呼叫端依主體尺度覆寫）
JOINT_ATTACHED: list = []          # mark_joint_attached() 登錄的物件名


def mark_joint_attached(obj, host=None, max_gap: float = None, note: str = None) -> None:
    """標記「以接頭/軸承/同軸嵌合與宿主連接」的物件——重力支撐與側向鎖固之外的第三類。

    來源（2026-09-14，汽車底盤案例）：車用/機械總成大量零件靠**接頭**連接——卡鉗跨在碟盤
    上、輪轂穿在羊角軸承裡、螺栓把兩件鎖在一起、輪胎胎唇壓配在輪圈上。這些零件：
      · 底下沒有任何東西（不是重力平放）→ `audit_floating()` 一定誤報懸空；
      · 也不是「貼在宿主表面上」（是軸心對軸心的嵌合）→ 硬用 `mark_side_attached()` 排除
        懸空、再交給 `audit_attachment_contact()` 量表面間距，同一件東西會換成被回報
        「離宿主表面 0.048m（貼附件浮空）」，而且它報的「最近宿主」還是全場任意的另一件
        （實測：卡鉗螺栓的最近宿主被判成輪胎）——雜訊只是換個形式，繼續淹沒真正的問題。
    本類別的判準因此是**對宿主的一條距離上界**（`max_gap`，預設 50mm）：接頭件與它的宿主
    只要落在接合包絡內就算通過，不要求面對面貼合。`host` **必填**（物件名）——只排除不
    量測的豁免這支函式不接受，沒宣告宿主的 joint 件會被稽核直接回報。

    用法：建好這類零件當下呼叫 `T.mark_joint_attached(obj, host="Brake_Disc_F_L")`；需要
    更緊/更鬆的包絡就傳 `max_gap=`（公尺）。`note=` 可記下連接方式（鉸接/螺栓/軸承），寫進
    `.blend` 自訂屬性供日後追溯。
    """
    obj["_joint_attached"] = True
    if host:
        obj["_joint_host"] = str(host)
    if max_gap is not None:
        obj["_joint_max_gap"] = float(max_gap)
    if note:
        obj["_joint_note"] = str(note)
    if obj.name not in JOINT_ATTACHED:
        JOINT_ATTACHED.append(obj.name)


def joint_attached_stats() -> dict:
    """回報接頭/軸承標記的規模——跟 `side_attached_stats()` 一樣讓「排除」的範圍可見：
    `count` 是登錄件數、`declared_host` 是有宣告宿主的件數（本類別必填，這個數字低於
    count 就是有物件漏宣告，稽核會逐件回報）。"""
    objs = [o for o in bpy.data.objects if o.get("_joint_attached")]
    return {
        "count": len(objs),
        "declared_host": sum(1 for o in objs if o.get("_joint_host")),
        "objects": [o.name for o in objs],
    }


def audit_joint_attachment(objects: list = None, max_gap: float = None,
                           sample_limit: int = 2000) -> list:
    """接頭/軸承件連結稽核（§13.9；2026-09-14 新增）：抓「宣告成接頭連接、卻飛到宿主接合
    包絡之外」的零件。

    為什麼需要：接頭件被排除在 `audit_floating()` 之外（向下的 ray_cast 對它們全是假警報），
    排除之後就沒有別的檢查在看它們還在不在宿主身上——跟 `mark_side_attached()` 同一條原則：
    減法必須有加法。判準：`surface_gap(obj, host=宣告宿主) ≤ max_gap`（`max_gap` 預設
    `ATTACH_JOINT_DEFAULT_GAP`＝50mm，物件自己宣告的 `_joint_max_gap` 優先）。網格真正相交
    （零件插進/穿過宿主，同軸嵌合的常態）由 `surface_gap()` 的相交測試回傳 0，直接通過——
    刻意裝配不該當成缺陷；要抓真穿模用 `audit_interpenetration(mode="bvh")`，或把這一對
    用 `mark_assembly_mate()` 宣告起來。

    `objects=None` 時自動取全部 `_joint_attached` 物件。**沒宣告宿主的一定回報**——接頭類別
    的意義是「有帳可查的豁免」，宣告不出宿主等於這件東西兩道審查都不看它。
    """
    objs = list(objects) if objects is not None else [o for o in bpy.data.objects if o.get("_joint_attached")]
    if not objs:
        return []
    tol = ATTACH_JOINT_DEFAULT_GAP if max_gap is None else float(max_gap)
    issues = []
    probe_cache: dict = {}
    for o in objs:
        host = o.get("_joint_host")
        if not host:
            issues.append(f"{o.name}: 接頭/軸承標記必須宣告宿主（mark_joint_attached(obj, host=...)）"
                          "——否則它同時不在懸空審查、也不在任何貼合稽核的視野內")
            continue
        key = str(host)
        if key not in probe_cache:
            cand = [bpy.data.objects[key]] if key in bpy.data.objects else []
            probe_cache[key] = _host_bvh(cand)[0] if cand else None
        probe = probe_cache[key]
        if probe is None:
            issues.append(f"{o.name}: 宣告的接頭宿主 {host} 不存在（_joint_host 用物件名，改名後要同步）")
            continue
        declared_gap = o.get("_joint_max_gap")
        allowed = float(declared_gap) if declared_gap is not None else tol
        gap, _point = surface_gap(o, probe=probe, sample_limit=sample_limit)
        if gap is None:
            issues.append(f"{o.name}: 網格沒有可量測的頂點，接頭連結無法量測")
        elif gap > allowed:
            issues.append(f"{o.name}: 離接頭宿主 {host} {gap:.3f}m > 接合包絡 {allowed:.3f}m"
                          "（宣告為接頭/軸承連接，實際卻不在宿主身上）")
    return issues


def assert_joint_attachment(objects: list = None, max_gap: float = None,
                            label: str = "joint_attachment", hard: bool = True) -> None:
    """硬性關卡版：接頭/軸承件必須落在宿主接合包絡內（§13.9），超差即 fail()（hard=True 預設）。"""
    issues = audit_joint_attachment(objects, max_gap=max_gap)
    report_or_fail(issues, step=label, hard=hard)


def _host_bvh(objs: list):
    """把一批 mesh 的 evaluated 幾何合成一棵世界座標 BVH（貼附件量測用）。

    外殼（OUTLINE_SHELLS，貼著主體外推建立）與停放中的母版（PARKED_MASTERS，座標停在
    設計單位）一律排除——兩者都會讓「到最近表面的距離」量出無意義的近 0 值。
    回傳 (bvh, vert_count)；沒有可用幾何時 (None, 0)。
    """
    deps = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        if o.type != 'MESH' or o.name in OUTLINE_SHELLS or o.name in PARKED_MASTERS:
            continue
        try:
            o_eval = o.evaluated_get(deps)
            me = o_eval.to_mesh()
        except Exception as exc:  # noqa: BLE001
            log("attachment_contact", f"WARNING: {o.name} 幾何評估失敗、略過（{exc}）")
            continue
        base = len(verts)
        mw = o.matrix_world
        verts.extend([mw @ v.co for v in me.vertices])
        polys.extend([tuple(base + i for i in poly.vertices) for poly in me.polygons])
        o_eval.to_mesh_clear()
    if not verts or not polys:
        return None, 0
    return BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0), len(verts)


def _host_name_at(hosts: list, point, eps: float = 0.01):
    """診斷用：回報哪個宿主的最外包盒含住這個點（找不到回 None）。"""
    if point is None:
        return None
    for h in hosts:
        corners = [h.matrix_world @ Vector(c) for c in h.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        if (min(xs) - eps <= point.x <= max(xs) + eps
                and min(ys) - eps <= point.y <= max(ys) + eps
                and min(zs) - eps <= point.z <= max(zs) + eps):
            return h.name
    return None


def surface_gap(obj, hosts: list = None, probe=None, sample_limit: int = 2000):
    """量「物件網格 → 宿主表面」的最短距離（§13.9 貼附件貼合審查的核心量測）。

    回傳 (gap_m, nearest_point)；無法量測時 (None, None)。

    判定順序（兩步都不能省）：
      1. **相交測試**：物件與宿主的 BVH 有實際面相交 → 回傳 0.0。零件插進/嵌進宿主時
         它的頂點落在宿主內部，頂點到表面的距離不是 0（一根插進去 0.3m 的銷，最近的
         頂點可能離表面 0.1m），只有相交測試答得出「真的接觸了」。
      2. 未相交 → 取物件頂點**與面心**到宿主表面的最近距離（`BVHTree.find_nearest`），這才是
         真正的淨空量。面心必須一起取樣（只取頂點會系統性高估：一片 0.3m 見方的平板貼在
         R=2.1m 的圓柱上，離面最近的是**板面中心**，只量頂點會把 10mm 讀成 16mm——曲率誤差
         ≈ 半寬²/(2R)）。`sample_limit` 只在高面數物件上抽樣（均勻跳點）——抽樣是成本考量，
         代價是「最深接觸處」可能被跳過；本函式量到的值是**真值的上界**，用來判定浮空
         （間距遠大於容差）沒有問題，不要拿它量微米級的貼合精度（真正接觸用步驟 1 的相交
         測試，那一步是精確的）。

    `hosts` 給一批物件、或以 `probe=` 傳入先建好的樹（同一宿主上量多件時共用，避免重複
    建樹）。`hosts=None` 時用場景其餘 mesh（自動排除自身、外殼、母版）當宿主候選。
    """
    bpy.context.view_layer.update()
    if probe is None:
        if hosts is None:
            hosts = [o for o in bpy.data.objects
                     if o.type == 'MESH' and o is not obj
                     and o.name not in OUTLINE_SHELLS and o.name not in PARKED_MASTERS]
        probe, _n = _host_bvh(list(hosts))
    if probe is None:
        return None, None
    obj_bvh, _n_obj = _host_bvh([obj])
    if obj_bvh is not None and probe.overlap(obj_bvh):
        return 0.0, None
    mw = obj.matrix_world
    pts = [mw @ v.co for v in obj.data.vertices]
    pts.extend([mw @ poly.center for poly in obj.data.polygons])  # 面心：見下方取樣說明
    if not pts:
        return None, None
    if sample_limit and len(pts) > sample_limit:
        step = max(1, len(pts) // sample_limit)
        pts = pts[::step]
    best_dist, best_pt = None, None
    for pt in pts:
        loc, _normal, _index, dist = probe.find_nearest(pt)
        if loc is None:
            continue
        if best_dist is None or dist < best_dist:
            best_dist, best_pt = dist, loc
    return best_dist, best_pt


def audit_attachment_contact(objects: list = None, hosts: list = None,
                             max_gap: float = None, sample_limit: int = 2000) -> list:
    """貼附件貼合稽核（§13.9）：抓「標記成側向鎖固、卻根本沒貼到宿主」的浮空件。

    為什麼需要：`audit_floating()` 靠向下 ray_cast，天生只認重力式平放支撐；側向鎖固/
    懸臂件（扶手、貼在艙體/外殼上的附件、桁架斜撐）必須靠 `mark_side_attached()` 排除，
    排除之後就沒有別的檢查在看這批物件「有沒有真的碰到宿主」——**減法做完必須補上加法**，
    這支就是那個加法，`T.main()` 對所有帶 `_side_attached` 的物件自動跑一次。

    判準：`min(附件頂點到宿主表面距離) ≤ stand_off + max_gap`（`stand_off` 是物件用
    `mark_side_attached(obj, stand_off=...)` 宣告的預期淨空，預設 0＝必須貼合，只剩防
    共面裕度）。已相交（零件插進宿主）→ 0，直接通過。

    `objects=None` 時自動取全部 `_side_attached` 物件；`hosts=None` 時宿主候選＝場景其餘
    mesh（排除自身、外殼、母版）。物件宣告了 `_attach_host` 時只量那個宿主，宣告的物件名
    不存在會回報（改名後要同步），不會靜默換別的宿主蒙混過去。
    """
    objs = list(objects) if objects is not None else [o for o in bpy.data.objects if o.get("_side_attached")]
    if not objs:
        return []
    tol = ATTACH_CONTACT_DEFAULT_GAP if max_gap is None else float(max_gap)
    if hosts is not None:
        host_list = [h for h in hosts if h.type == 'MESH']
    else:
        names = {o.name for o in objs}
        host_list = [o for o in bpy.data.objects
                     if o.type == 'MESH' and o.name not in names
                     and o.name not in OUTLINE_SHELLS and o.name not in PARKED_MASTERS]
    global_probe = None
    declared_cache = {}
    issues = []
    for o in objs:
        declared = o.get("_attach_host")
        expect = o.get("_attach_stand_off")
        if declared:
            key = str(declared)
            if key not in declared_cache:
                cand = [h for h in host_list if h.name == key]
                if not cand and key in bpy.data.objects:
                    cand = [bpy.data.objects[key]]
                declared_cache[key] = _host_bvh(cand)[0] if cand else None
            probe = declared_cache[key]
            if probe is None:
                issues.append(f"{o.name}: 宣告的宿主 {declared} 不存在（_attach_host 用物件名，改名後要同步）")
                continue
        else:
            if global_probe is None:
                global_probe = _host_bvh(host_list)[0]
            probe = global_probe
            if probe is None:
                issues.append(f"{o.name}: 場景內找不到任何可當宿主的 mesh，貼合無法量測")
                continue
        gap, point = surface_gap(o, probe=probe, sample_limit=sample_limit)
        if gap is None:
            issues.append(f"{o.name}: 網格沒有可量測的頂點，貼合無法量測")
            continue
        allowed = float(expect) if expect is not None else 0.0
        if gap > allowed + tol:
            host_note = f"宿主={declared}" if declared else f"最近宿主={_host_name_at(host_list, point) or '未判定'}"
            declared_note = f"，宣告 stand_off={allowed:.3f}m" if expect is not None else ""
            issues.append(f"{o.name}: 離宿主表面 {gap:.3f}m > 容許 {allowed + tol:.3f}m"
                          f"（貼附件浮空{declared_note}；{host_note}）")
        elif expect is not None and gap < allowed - tol:
            issues.append(f"{o.name}: 離宿主表面 {gap:.3f}m 小於宣告 stand_off {allowed:.3f}m "
                          f"− 容差 {tol:.3f}m（未到位或已穿透）")
    return issues


def assert_attachment_contact(objects: list = None, host=None, max_gap: float = None,
                              label: str = "attachment_contact", hard: bool = True) -> None:
    """硬性關卡版：貼附件必須貼在宿主表面（§13.9），超差即 fail()（hard=True 預設）。

    `host` 給物件名或物件本身時只量該宿主；不給則每個物件用自己宣告的 `_attach_host`
    （沒宣告的用場景其餘 mesh）。場景包把它寫進 assertions.py 的 verify_scene()——跟
    §13.9 其他審查同一個原則：排除假警報的地方，要有對應的硬性檢查接手。
    """
    objs = list(objects) if objects is not None else [o for o in bpy.data.objects if o.get("_side_attached")]
    hosts = None
    if host is not None:
        hosts = [bpy.data.objects[host]] if isinstance(host, str) else [host]
    issues = audit_attachment_contact(objs, hosts=hosts, max_gap=max_gap)
    report_or_fail(issues, step=label, hard=hard)


def audit_spacing(objects: list, label: str, tolerance_ratio: float = 0.4) -> list:
    """同批實例的最近鄰間距離群值掃描，抓「某一件擺位間距明顯跟其他不一樣」（§13.9）
    ——網格/序列擺位時，某一件座標算錯、跟鄰居距離特別近或特別遠，肉眼在渲染圖裡
    不一定看得出來（尤其物件數量多、視角遠時），但數值上抓得到。

    tolerance_ratio：容許偏離中位數的比例，預設 0.4（最近鄰距離低於中位數 0.6 倍
    或高於 1.4 倍才算離群）——網格擺位理論上間距完全一致，只是浮點運算/黃金比例
    收分序列本身就有自然差異，抓太緊會誤報正常設計差異，0.4 是抓明顯錯誤、放過
    正常差異的折衷值。物件數 <3 沒有統計意義，直接回傳空清單。
    """
    bpy.context.view_layer.update()
    positions = [(o.name, o.matrix_world.translation.to_2d()) for o in objects]
    if len(positions) < 3:
        return []
    dists = []
    for i, (_name, pos) in enumerate(positions):
        nearest = min((pos - other_pos).length for j, (_, other_pos) in enumerate(positions) if j != i)
        dists.append(nearest)
    sorted_d = sorted(dists)
    median = sorted_d[len(sorted_d) // 2]
    issues = []
    if median <= 0:
        return issues
    for (name, _pos), d in zip(positions, dists):
        if d < median * (1 - tolerance_ratio) or d > median * (1 + tolerance_ratio):
            issues.append(f"{label}/{name}: 最近鄰距離 {d:.3f}m 偏離中位數 {median:.3f}m 超過 "
                          f"{tolerance_ratio * 100:.0f}%（擺位離群）")
    return issues


def report_or_fail(issues: list, step: str = "geometry_audit", hard: bool = True) -> None:
    """統一處理 audit_* 函式回傳的問題清單：全部印出來，hard=True（預設）才真的 fail()。

    audit_* 天生有假陽性風險（自動發現異常，不是驗證已知答案），所以先印出全部
    項目讓人/模型自己判斷合不合理，比照 assert_* 系列「錯就直接 fail」更保守；
    真的要放行已知的假陽性，在呼叫端把該物件從傳入的 objects 清單過濾掉，
    不要直接把這個函式改成 hard=False 全部放行。
    """
    if not issues:
        return
    for line in issues:
        log(step, f"ISSUE: {line}")
    if hard:
        fail(step, f"{len(issues)} 個幾何問題（見上方逐條列出）")


# ---------- 資產復用（SKILL §14；modular kit 理念） ----------

def place_copy(master: bpy.types.Object, name: str, loc: tuple, yaw_deg: float = 0.0,
               scale: float = 1.0, mat_override: bpy.types.Material = None) -> bpy.types.Object:
    """復用母版：共享 mesh data 的連結實例（§14.1）。只允許 loc/繞Z yaw/uniform scale/材質槽四種變體。

    禁止在循環體內重複 primitive_*_add 逐份重畫；母版需先在局部座標建好、原點=接地中心。
    """
    inst = master.copy()          # 共享 inst.data（unique_geometries 不增加）
    inst.name = name
    inst.location = loc
    inst.rotation_mode = "QUATERNION"
    inst.rotation_quaternion = Quaternion((0, 0, 1), math.radians(yaw_deg))
    if scale != 1.0:
        inst.scale = (scale, scale, scale)
    if mat_override is not None:
        if len(inst.material_slots) > 0:
            # 物件級材質覆寫：data 仍共享（Blender material slot 可 per-object override）
            inst.material_slots[0].material = mat_override
        else:
            # 母版無材質槽時才複製 data（犧牲共享換取變體，屬退化情形）
            inst.data = inst.data.copy()
            inst.data.materials.append(mat_override)
    bpy.context.collection.objects.link(inst)
    return inst


# ---------- 材質工具（5.1 實測可用） ----------

def make_mat(name: str, color: tuple, roughness: float = 0.85, metallic: float = 0.0,
             emission: tuple = None, emission_strength: float = 0.0) -> bpy.types.Material:
    """Principled BSDF 純色材質，可選自發光。"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True  # 5.1 會噴 6.0 deprecation warning，無害（skill §8 #7）
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def add_noise_color_mat(name: str, c_a: tuple, c_b: tuple, scale: float,
                        roughness: float = 0.9, detail: float = 6.0) -> bpy.types.Material:
    """Noise→ColorRamp 兩色混染（物件座標空間）：草地/石紋/水泥/織物基底。"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c_a, 1.0)
    ramp.color_ramp.elements[1].color = (*c_b, 1.0)
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_wood_mat(name: str, c_a: tuple = (0.62, 0.45, 0.26),
                  c_b: tuple = (0.42, 0.28, 0.14)) -> bpy.types.Material:
    """程序化木紋：Wave 拉絲 + ColorRamp，物件座標 Z 壓縮成橫紋。"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (12.0, 12.0, 0.6)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 9.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c_a, 1.0)
    ramp.color_ramp.elements[1].color = (*c_b, 1.0)
    ramp.color_ramp.elements[0].position = 0.38
    ramp.color_ramp.elements[1].position = 0.62
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def make_fabric_mat(name: str, c_a: tuple, c_b: tuple) -> bpy.types.Material:
    """程序化織物（bouclé 類）：高頻 Noise 顆粒 + Bump 微起伏。"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 260.0
    noise.inputs["Detail"].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c_a, 1.0)
    ramp.color_ramp.elements[1].color = (*c_b, 1.0)
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bsdf.inputs["Roughness"])
    bsdf.inputs["Roughness"].default_value = 0.92
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.006
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------- 鏡頭專屬外觀覆寫（資料驅動的「反光 pass」） ----------
# 同一個場景在不同鏡頭下需要的外觀不一樣：俯視鏡頭要霧面鋪面，低角度逆光鏡頭要反光
# 鋪面；遠景立面要緞面鋁，特寫要拋光。把它做成「材質鍵 -> [(socket, 值)]」的資料 dict
# 依鏡頭套用，而不是為每個鏡頭複製一份材質工廠、或改寫 materials.py 的節點鏈——維持
# §16.3「鏡頭專屬設定住 config.py」的定位表原則：換鏡頭只改資料，不碰節點代碼。
SOCKET_ALIASES = {
    "Specular": ["Specular IOR Level", "Specular"],
    "Transmission": ["Transmission Weight", "Transmission"],
    "Emission": ["Emission Color", "Emission"],
    "EmissionColor": ["Emission Color", "Emission"],
    "Clearcoat": ["Coat Weight", "Clearcoat"],
}


def _set_bsdf_socket(bsdf, socket_name: str, value) -> bool:
    """設定 Principled socket；4.x→5.x 改名的走候選清單（§8 落差表）。
    跟 `mat_lib.set_socket()` 同一套精神，但本範本不 import mat_lib（凍結模組各自
    獨立、可單獨複製到 test-scripts/ 使用），所以這裡保留一份最小實作。"""
    for cand in SOCKET_ALIASES.get(socket_name, [socket_name]):
        if cand in bsdf.inputs:
            bsdf.inputs[cand].default_value = value
            return True
    log("materials", f"WARNING: socket {socket_name!r} 候選全不命中，跳過（不中斷）")
    return False


def apply_socket_overrides(mats: dict, overrides: dict, label: str = "look") -> int:
    """把「鏡頭專屬的外觀微調」當資料套用到既有材質 dict 上（回傳成功套用的 socket 數）。

    mats：`build_materials()` 回傳的 name/key -> Material dict（本函式只讀，不改結構）。
    overrides：`{材質鍵: [(socket 名稱, 值), ...]}`。材質鍵對不上時 WARNING 並跳過該鍵
    ——**不 fail**：同一份覆寫表跨任務重用時（不同場景的材質鍵本來就不一樣）允許部分
    命中，全部對不上才是真的寫錯，那時 log 會列出找不到的鍵。
    label：log 標籤（通常傳鏡頭名，方便對照是哪個鏡頭的 look）。

    已知前提：只對「參數型材質」有效——Roughness／Specular IOR Level 這類 socket 沒有
    被節點連線接管時，直接寫 `default_value` 才有意義（`mat_lib.make_metal()`／
    `make_glass()`／`make_stone()`／`make_paving()` 都是這種）。反過來，原本就把該
    socket 交給節點驅動的材質（例如 `make_asphalt(wetness>0)` 的 Roughness 由積水遮罩
    驅動）會被連線蓋掉——**需要覆寫的材質不要選那些已把該 socket 接出去的 factory**，
    或改去覆寫它沒有連線的其他 socket。

    用法（scene_pkg 的 materials.py，建完材質 dict 之後）：
        if C.REFLECTIVE:
            T.apply_socket_overrides(m, C.LOOK_OVERRIDES, label=C.SHOT)
    """
    applied, missed = 0, []
    for key, edits in overrides.items():
        mat = mats.get(key)
        if mat is None:
            missed.append(key)
            continue
        if not mat.use_nodes:
            log("materials", f"WARNING: {mat.name} 沒有節點樹，跳過 {key} 的覆寫")
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            log("materials", f"WARNING: {mat.name} 找不到 Principled BSDF，跳過 {key}")
            continue
        for socket_name, value in edits:
            if _set_bsdf_socket(bsdf, socket_name, value):
                applied += 1
    if missed:
        log("materials", f"WARNING: apply_socket_overrides({label}) 找不到材質鍵 {missed}，已跳過")
    log("materials", f"apply_socket_overrides({label}): 套用 {applied} 項 socket 覆寫"
                     f"（覆寫表 {len(overrides)} 個材質鍵）")
    return applied


# ---------- 幾何工具 ----------

def add_box(name: str, size: tuple, loc: tuple, rot=None, quat=None, mat=None,
            bevel: float = 0.0) -> bpy.types.Object:
    """尺寸/位置精確的盒子（scale 已 apply）；rot=歐拉 或 quat=四元數；bevel>0 加倒角。"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    if quat is not None:
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = quat
    elif rot is not None:
        obj.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        mod = obj.modifiers.new(name="Bevel", type="BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(35.0)
    if mat is not None:
        obj.data.materials.append(mat)
    return obj


def add_cyl(name: str, radius: float, depth: float, loc: tuple, mat=None,
            rot=None, quat=None, verts: int = 24) -> bpy.types.Object:
    """圓柱（圓木/柱/桿通用）；loc/rot 已 apply（2026-09-08 修正，見下方「origin 慣例統一」）。

    origin 慣例統一（2026-09-08，便利商店輪實測事故）：修正前 add_cyl() 不呼叫
    transform_apply，obj.location 建完仍停在 loc，跟 add_box()（transform_apply
    後 location 歸零、世界座標烘進 mesh，§8#9）origin 慣例不一致——同一場景混用
    box-host 母版與 cyl-host 母版時，instance() 的 z 補償公式必須跟著 host 用哪個
    primitive 建而分兩套算，這正是便利商店輪路燈/垃圾桶（cyl host）跟其餘家具
    （box host）混用、耗掉 4 個回合才抓出的懸空/深埋根因。現場 probe 實測驗證
    （見 build_template.py 對應 git 歷史）：cyl 補呼叫 transform_apply(scale=True)
    後，世界座標網格範圍完全不變，只是 obj.location 跟著歸零、統一成 add_box()
    的慣例——之後任何 host 母版無論用 add_box 或 add_cyl 建，origin 都在
    obj-transform 歸零後的 (0,0,0)、mesh 已烘進世界座標，instance() 不需要再依
    primitive 種類分別計算 z 補償。
    """
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    if quat is not None:
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = quat
    elif rot is not None:
        obj.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True)
    if mat is not None:
        obj.data.materials.append(mat)
    return obj


def cut_hole(host: bpy.types.Object, cutter: bpy.types.Object, apply: bool = True,
             delete_cutter: bool = True, solver: str = 'EXACT') -> bpy.types.Object:
    """布林差集挖洞（§13.10 CNC 機床式建模操作字彙，2026-09-08 新增）：host 減去 cutter。

    真實開孔（窗洞/門洞/鑽孔/通風孔/線孔/卡槽/沉頭孔）一律走這個函數，不要用
    「該處不建量體」的假開口帶過——那樣做不出洞壁厚度、視覺上就是拼接感的根源
    （使用者原話：「BLENDER 有很多工具 AI 從不會想去用，比如挖洞、倒圓角……
    看到的成品老是一些基礎形狀的拼接」）。

    **要挖穿的貫通孔**：cutter 必須完全貫穿 host 的實體厚度（兩端都露出 host
    表面之外），否則挖不透、只留一個凹坑。沉頭孔/埋頭孔用兩次疊加（先寬淺、
    再窄深，同軸心）。
    **要挖凹陷不是貫通孔**（2026-09-09 澄清，實測卡丁車座椅事故：座椅坐墊
    該有一個人坐進去的凹陷曲面，實際渲染出來卻是一塊平板——查證後發現正是
    這段文字把「只留凹坑」講成失敗案例，模型因此以為 `cut_hole()` 不適用於
    座椅這種真正需要凹坑的情境，於是乾脆不挖，退化成平板）：**「只留一個
    凹坑」本身不是失敗，是不是你要的形狀取決於 cutter 有沒有故意只穿入
    host 一部分**——座椅坐墊/碗/水槽/嵌入式螢幕這類非貫穿凹陷，cutter 就是
    要刻意只穿入 host 一部分（球體/橢球，中心點落在 host 表面之下），這種
    情境改用下面的 `carve_depression()`，不要因為這段文字誤判成不能用。
    EXACT 求解器對常見的軸對齊方形/圓形切割最穩定，FAST 較快但對非流形/共面
    邊界容易出錯，預設用 EXACT（Blender 5.1.2 實測：牆體挖窗洞，16 verts 潔淨
    四邊形洞口、洞口內外 raycast 正確通過/受阻，無殘留 cutter 幾何）。
    """
    bpy.context.view_layer.objects.active = host
    mod = host.modifiers.new(name="Bool_Cut", type='BOOLEAN')
    mod.object = cutter
    mod.operation = 'DIFFERENCE'
    mod.solver = solver
    if apply:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if delete_cutter:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return host


def carve_depression(host: bpy.types.Object, center: tuple, radii: tuple,
                     apply: bool = True, solver: str = 'EXACT') -> bpy.types.Object:
    """在 host 實體上挖出一個平滑凹陷——座椅坐墊、碗、水槽、嵌入式螢幕/按鍵這類
    「非貫穿」凹坑的標準做法（2026-09-09 新增，來源：卡丁車座椅實測事故，見
    `cut_hole()` docstring 的澄清段）。跟 `cut_hole()` 是同一套布林差集機制，
    差別只在 cutter 的穿透深度：`cut_hole()` 的 cutter 要求兩端都穿出 host
    表面（挖穿），這支函式用一個球體/橢球 cutter，刻意只讓一部分穿入 host——
    球體露出 host 表面的那一冠（cap）決定凹口大小，中心埋進 host 多深決定
    凹陷多深，布林差集後留下的凹痕正是目標形狀。

    center：橢球中心世界座標——通常落在 host 頂面之下（例如座椅坐墊頂面 z 減去
    想要的凹陷深度），中心埋越深、凹陷越深。radii：(rx, ry, rz) 橢球三軸半徑，
    扁一點的 rz（相對 rx/ry 小）做淺凹陷（坐墊/托盤），三軸接近相等做碗狀凹陷
    （水槽/湯碗）。想要凹陷邊緣更硬朗（不是平滑過渡到圓弧邊緣，例如嵌入式方形
    螢幕凹槽）改用 `cut_hole()` 搭配方塊 cutter、cutter 只部分穿入即可，這支
    函式專門處理球面過渡的柔和凹陷。

    回傳挖好的 host（跟 `cut_hole()` 同款慣例，cutter 預設用完即刪）。"""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=center)
    cutter = bpy.context.active_object
    cutter.name = f"{host.name}_DepressionCutter"
    cutter.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return cut_hole(host, cutter, apply=apply, solver=solver)


# ---------- 母版/實例復用（skill §14；Round 5 浦東塔實戰驗證，復用率 85.4%） ----------

REUSE: dict = {}  # 母版名 → 實例數，SCENE_STATE 回報復用統計
# 已 park 的母版名集合（park_master() 登錄）。main() 的自動幾何審查與構圖審查據此
# 排除母版：母版建在設計單位、座標留在原點，跟實際場景差 1000 倍——不排除的話
# 「依場景 bbox 對角線縮放的容差」會被單一個母版撐到上限 5cm（實測：主體 0.18m
# 的 iPhone、母版 Mst_LensAssembly 16.2m），懸空審查與構圖審查同時灌入假警報，
# 真正的問題被雜訊淹沒。
PARKED_MASTERS: set = set()


def park_master(obj: bpy.types.Object) -> bpy.types.Object:
    """母版隔離：hide_render 排除出鏡。

    教訓（Round 5 calib 實測事故）：不能用「母版放 z=10000 高空」的招——
    add_box 內 transform_apply 在 5.1 會把 location 一併烘進 mesh（skill §8 #9），
    母版物件座標歸零掉回原點入鏡。正確做法：母版 mesh 建在原點、
    hide_render 隔離，實例自帶世界座標。
    （2026-09-08 更新：add_cyl 先前不 apply transform、origin 停在 loc，
    與 add_box 不一致，已修正為兩者一致——見 add_cyl() docstring「origin 慣例統一」。）
    """
    obj.hide_render = True
    obj.hide_viewport = True
    PARKED_MASTERS.add(obj.name)   # main() 的自動審查據此排除母版，見 PARKED_MASTERS 註解
    return obj


def instance(master: bpy.types.Object, name: str, loc: tuple,
             rot_z: float = 0.0, scale: float = 1.0) -> bpy.types.Object:
    """§14 母版實例化：linked copy 共享 mesh，只動白名單變體（loc/繞Z旋轉/uniform scale）。

    copy() 會繼承母版的 hide 旗標，必須還原——漏掉這行實例全都不渲染。

    rot_z 單位是**度**，跟這個檔案裡 place_copy() 的 yaw_deg 是同一個單位公約
    （呼叫端一律傳度數，例如「轉 180 度面向黑板」）。2026-09-08 修正：這裡曾經把
    rot_z 未經 math.radians() 轉換直接塞進 rotation_euler（bpy 的 rotation_euler
    內部單位是弧度）——實測踩坑：教室 v2 場景每張椅子傳 rot_z=180.0，結果變成
    180 弧度（=10313.24°，對 360 取餘＝233.24°），跟預期的「轉半圈面向黑板」
    差了 53°，30 張椅子全部歪斜同一個角度，肉眼看就是「每張椅子都是歪的」。

    **`rotation_mode` 陷阱（2026-09-10 新增，雷峰塔欄杆歪斜實測事故）**：`copy()`
    連 `master.rotation_mode` 一起複製——如果母版是用 `add_cyl(..., quat=...)`
    建的（例如欄杆扶手母版：圓柱預設沿 Z，靠 quat 轉成沿 X 躺平做水平橫桿），
    母版的 `rotation_mode` 停在 `'QUATERNION'`。以前這裡直接 `dup.rotation_euler
    = (0,0,radians(rot_z))`——**`rotation_mode='QUATERNION'` 時 Blender 完全
    忽略 `rotation_euler` 欄位，實際變換只看 `rotation_quaternion`**，這行等於
    沒寫，每個實例的世界朝向全部停在母版原本那個固定方向，跟呼叫端傳的 `rot_z`
    完全無關。實測案例：八角塔欄杆扶手母版建在局部 X 軸、`instance()` 對 8 個面
    分別傳不同 `rot_z`（各面切線角），結果全部 8 面的扶手朝向一模一樣（母版原始
    朝向），渲染出來是一堆對不齊柱位、朝奇怪角度斜插出去的紅色長條，肉眼像是
    「欄杆歪了」，實際跟頂點/位置座標無關，純粹是這個 mode 沒被重置。現在無論
    母版原本是哪種 rotation_mode，都先強制轉成 `'XYZ'` euler 再賦值，`rot_z`
    永遠對得上：
    """
    dup = master.copy()  # 共享 obj.data
    dup.name = name
    dup.hide_render = False
    dup.hide_viewport = False
    dup.location = loc
    if rot_z:
        dup.rotation_mode = 'XYZ'  # 見上方 docstring：母版可能是 QUATERNION，不重置這行 rot_z 會被忽略
        dup.rotation_euler = (0.0, 0.0, math.radians(rot_z))
    if scale != 1.0:
        dup.scale = (scale, scale, scale)
    bpy.context.collection.objects.link(dup)
    REUSE[master.name] = REUSE.get(master.name, 0) + 1
    return dup


# ---------- 跨任務資產庫（§16.6，2026-09-08 新增） ----------
# 上面 park_master()/instance() 解決的是「同一個場景包裡」的母版復用；這兩支函式把
# 復用範圍擴大到「同一次對話累積設計的多個獨立物件」跟「以後複製到別的專案繼續用」——
# 使用者原話：「先設計一台貨車，再設計一台公車……最後要求組合這些物件組成一個馬路
# DEMO，我可以再把這些物件將來再 COPY 到別處繼續用」。

def save_object_asset(objs, name: str, library_dir: str = ".capybala/asset_library") -> str:
    """把 objs（單一物件或物件清單）連同其材質/mesh 資料寫成獨立可攜的
    `<library_dir>/<name>.blend`，並更新同目錄的 `manifest.json` 索引。回傳寫出的
    .blend 路徑。

    這個檔案**不是**整個場景的 `save_as_mainfile()`——只含這個物件（+它依賴的材質/
    mesh data-block），之後可以直接把 `<library_dir>/` 整個資料夾複製到別的機器/
    專案繼續用（本 skill 材質全部走 mat_lib 程序化節點，沒有外部貼圖依賴，不需要
    額外 pack）。實測（Blender 5.1.2，2026-09-08）：另開一個全新、乾淨的 Blender
    行程 `append_object_asset()` 讀回，材質/世界座標/多物件群組關係全部正確。

    多物件 asset（例如貨車=車頭+車斗兩個物件）建議先各自建好、確認語義斷言（§13）
    通過，再一起傳進 objs 存成一個 asset；如果之後要用 `instance()` 大量複製這個
    asset，appende 完後先用 `detail_lib.join_into()` 合併成單一物件再 park_master。
    """
    if isinstance(objs, bpy.types.Object):
        objs = [objs]
    os.makedirs(library_dir, exist_ok=True)
    blend_path = os.path.join(library_dir, f"{name}.blend")

    bpy.context.view_layer.update()
    all_verts_world = []
    for o in objs:
        all_verts_world.extend([o.matrix_world @ v.co for v in o.data.vertices])
    if all_verts_world:
        xs = [v.x for v in all_verts_world]
        ys = [v.y for v in all_verts_world]
        zs = [v.z for v in all_verts_world]
        dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    else:
        dims = (0.0, 0.0, 0.0)

    bpy.data.libraries.write(blend_path, set(objs), fake_user=True)

    manifest_path = os.path.join(library_dir, "manifest.json")
    manifest = []
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    manifest = [m for m in manifest if m.get("name") != name]
    manifest.append({
        "name": name,
        "blend_path": os.path.basename(blend_path),
        "object_names": [o.name for o in objs],
        "dims_m": [round(d, 3) for d in dims],
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    log("asset_library", f"已存檔 {name} → {blend_path}（{len(objs)} 物件，dims={dims}）")
    return blend_path


def append_object_asset(name: str, library_dir: str = ".capybala/asset_library",
                         loc: tuple = (0.0, 0.0, 0.0), rot_z: float = 0.0) -> list:
    """從 `library_dir/<name>.blend`（`save_object_asset()` 存的）append 物件進目前
    場景，回傳匯入的物件清單。以匯入物件群組的世界包圍盒中心（XY）+ 最低點（Z，
    接地基準）為基準，整體平移到 loc、繞這個基準點做 Z 軸旋轉 rot_z（**單位是度**，
    跟 `instance()`/`place_copy()` 同一個單位公約）。

    匯入後通常接 `park_master()` + `instance()` 走正常的母版復用流程（這支函式的
    定位是「把一個之前設計好的物件從資產庫拿回目前場景」，不是「擺位」本身）；
    多次在同一個場景放同一個 asset，appende 一次、剩下用 `instance()` 複製，不要
    每個位置各自呼叫一次 `append_object_asset()`（會重複佔用 mesh data，違反
    §14 母版=1 原則）。
    """
    blend_path = os.path.join(library_dir, f"{name}.blend")
    # 2026-09-14（內裝案例回報）：不要再把 with 區塊之後的 data_to.objects 當真相——
    # 清單在區塊結束後是否仍可信不是 API 契約保證的（Blender 只保證區塊內有效），且
    # 曾出現「回報成功、物件一件都沒進來」的症狀。改用附加前後的物件名快照差集辨識
    # （同 asset_fetch_lib.analyze_reference_model 2026-09-08 事故後的做法），並在實際
    # 新增數為 0 或短少時當場回報——成功回報必須有實際進場景的物件背書。
    before_names = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        wanted = len(data_from.objects)
        data_to.objects = data_from.objects

    imported = [bpy.data.objects[n] for n in sorted(set(bpy.data.objects.keys()) - before_names)]
    if not imported:
        fail("asset_library", f"append {name} 失敗：{blend_path} 宣告 {wanted} 個物件，實際"
                              "一件都沒進場景（不要相信回傳清單，要數實際新增的物件）")
    if len(imported) < wanted:
        log("asset_library", f"WARNING: append {name} 只進來 {len(imported)}/{wanted} 個物件")
    for o in imported:
        bpy.context.collection.objects.link(o)

    bpy.context.view_layer.update()
    all_verts_world = []
    for o in imported:
        all_verts_world.extend([o.matrix_world @ v.co for v in o.data.vertices])
    xs = [v.x for v in all_verts_world]
    ys = [v.y for v in all_verts_world]
    zs = [v.z for v in all_verts_world]
    center = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)))
    target = Vector(loc)
    delta = target - center

    rad = math.radians(rot_z)
    for o in imported:
        o.location += delta
        rel = o.location - target
        new_x = rel.x * math.cos(rad) - rel.y * math.sin(rad)
        new_y = rel.x * math.sin(rad) + rel.y * math.cos(rad)
        o.location = target + Vector((new_x, new_y, rel.z))
        o.rotation_euler.z += rad

    log("asset_library", f"已從資產庫 append {name}（{len(imported)} 物件）→ loc={loc}")
    return imported


def export_glb(filepath: str, objects: list | None = None) -> str:
    """匯出 GLB（2026-09-10 新增）——目前 pipeline 只存 `.blend`+渲染 PNG，從沒有
    真正匯出過可攜格式，但這正是把模型交給遊戲引擎/動畫軟體/網頁 3D（three.js/
    Unity/Unreal/Godot 全部原生吃 glTF）的必要步驟，不做這步等於模型永遠鎖死在
    Blender 裡。`objects=None` 匯出目前場景全部 MESH/EMPTY/ARMATURE 物件；只想
    匯出某個子集就自己篩好傳進來。

    父子階層（`shape_lib.rotation_pivot()` 建的樞軸 EMPTY、未來的 ARMATURE 骨架）
    會被 glTF 完整保留成 node 階層——這是「零件能不能在引擎裡被轉」的關鍵：引擎
    看到的是這個階層本身，不是渲染出來的像素，樞軸沒建對，匯出的模型在引擎裡
    還是不能轉。匯出前用 `bpy.context.view_layer.update()` 確保階層/變換都算過
    一輪，避免匯出到還沒更新的過期 transform。

    **`export_extras=True`（實測抓到的真坑，不是預設就對）**：Blender 的 glTF
    匯出器 `export_extras` 參數預設是 `False`——`rotation_pivot()` 寫在物件自訂
    屬性上的 `axis`/`limit_deg_min`/`limit_deg_max` 這類中介資料，不手動開這個
    參數**完全不會**出現在匯出檔裡，直接解析 GLB 的 JSON 才抓到這個坑（節點
    階層都對，`extras` 卻全部是 `None`）。本函式已固定帶上這個參數，呼叫端
    不需要自己記得。"""
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    if objects is None:
        objects = [o for o in bpy.data.objects if o.type in ('MESH', 'EMPTY', 'ARMATURE')]
    for o in objects:
        o.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True, export_format='GLB',
                              export_extras=True)
    log("export", f"GLB 匯出完成 {filepath}（{len(objects)} 物件，含父子階層）")
    return filepath


# ---------- 主體（佔位示範——每個任務替換這裡） ----------

def build_subject() -> dict:
    """佔位主體：基座 + 織物球 + 木紋方塊 + 黃銅環，演練全部材質工具與後仰公約。

    任務替換時遵守：
    - 人體工學件（座椅/床/樓梯等）先在 CONFIG 註明「使用者面向 = -Y」，
      靠背/傾斜一律用 lean_back_quat()，禁止手寫四元數符號。
    - 主體原點放在 (0,0,0) 附近、坐落於 z=0 地面，相機預設才構圖正確。
    """
    mats = {
        "fabric": make_fabric_mat("DemoFabric", (0.55, 0.55, 0.54), (0.42, 0.42, 0.41)),
        "wood": make_wood_mat("DemoWood"),
        "brass": make_mat("DemoBrass", (0.85, 0.65, 0.20), roughness=0.25, metallic=0.95),
        "dark": make_mat("DemoDark", (0.05, 0.05, 0.055), roughness=0.5, metallic=0.8),
    }
    # §15 示範：擺位用黃金分割生成，禁止手填「差不多中間」
    ped_w = 0.9
    big, small = fib_split(ped_w)           # 0.556 / 0.344——主件放 0.382 側、次件放 0.618 側
    add_box("Pedestal", (ped_w, ped_w, 0.12), (0, 0, 0.06), mat=mats["dark"], bevel=0.02)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.24, segments=48, ring_count=24,
                                         location=(-big / 2, small / 2 - 0.07, 0.12 + 0.24))
    sphere = bpy.context.active_object
    sphere.name = "DemoSphere"
    sphere.data.materials.append(mats["fabric"])
    add_box("DemoCube", (0.30, 0.30, 0.30), (small / 2, -big / 2 + 0.10, 0.12 + 0.15),
            rot=(0, 0, math.radians(18)), mat=mats["wood"], bevel=0.02)
    bpy.ops.mesh.primitive_torus_add(location=(0.0, 0.0, 0.12 + 0.52),
                                     major_radius=0.10, minor_radius=0.018,
                                     major_segments=48, minor_segments=16)
    torus = bpy.context.active_object
    torus.name = "DemoTorus"
    torus.data.materials.append(mats["brass"])
    # 後仰示範板（驗證 lean_back_quat 方向：頂部必須向 +Y）
    back = add_box("DemoBackrest", (0.5, 0.06, 0.4), (0, 0.30, 0.12 + 0.30),
                   quat=lean_back_quat(12.0), mat=mats["fabric"], bevel=0.02)
    bpy.context.view_layer.update()  # 無頭模式需先刷新 depgraph
    # 注意：5.1 的 transform_apply(scale=True) 會把 loc/rot 全部烘進 mesh（skill §8 #8），
    # matrix_world 變單位矩陣——方向驗證必須直接看世界座標顶点，不能靠物件 transform。
    world_verts = [back.matrix_world @ v.co for v in back.data.vertices]
    top_vert = max(world_verts, key=lambda v: v.z)
    base_y = 0.30
    if top_vert.y < base_y:
        fail("ergonomics", f"後仰板最高點 y={top_vert.y:.3f} < {base_y}——未向 +Y 後仰，方向公約被破壞")
    log("subject", f"佔位主體完成（5 物件，後仰板最高點 y={top_vert.y:.3f} 向 +Y 通過）")
    return {"subject_objects": 5}


# ---------- 環境 / 燈光 / 相機 / 渲染 ----------

def build_world(p: dict) -> None:
    """Sky IBL + 可選體積霧（5.1 API：sky 參數掛節點屬性，非 input sockets——skill §8 #3）。

    **2026-09-09 新增 `flat_background`**（查證多個純主體參考案例後確認：
    展示卡/純物件棚拍不該用 Sky IBL，改用中性灰純色背景+純三點式 AREA 燈——見
    SKILL.md §10.3）。過去這個結論只能靠呼叫端自己 `T.build_world = _solid_world`
    monkey-patch 整個函式才能套用（camera_pkg 案例的做法），沒有變成真正的預設——
    結果卡丁車案例完全沒套用，還是走舊版 Sky IBL 路徑，渲染出來「泛白」沒有真實
    陰影深度（實測：p1=59.2，最暗的 1% 像素都不夠暗，全畫面缺乏對比）。現在
    `PRESETS["studio"]["flat_background"]=True`（真正的預設，不用每個任務自己
    monkey-patch），`PRESETS["outdoor_golden"/"night"]` 仍是 `False`——那兩個
    是「主體嵌在真實戶外環境」的敘事場景，需要真實天空，不受這次修正影響。
    """
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    bg = wnt.nodes["Background"]
    wout = wnt.nodes["World Output"]
    if p.get("flat_background"):
        bg.inputs["Color"].default_value = (*p.get("bg_color", (0.18, 0.18, 0.18)), 1.0)
        bg.inputs["Strength"].default_value = 1.0
        log("world", f"純色中性灰背景 {p.get('bg_color', (0.18, 0.18, 0.18))}"
                     "（§10.3 展示卡預設，取代 Sky IBL——不是 monkey-patch，是 PRESET 本身的行為）")
        return
    try:
        sky = wnt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "MULTIPLE_SCATTERING"
        sky.turbidity = p["sky_turbidity"]
        sky.ground_albedo = p["sky_ground_albedo"]
        sky.sun_elevation = math.radians(p["sun_elev_deg"])
        sky.sun_rotation = math.radians(p["sun_azim_deg"])
        sky.sun_intensity = 0.4
        wnt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = p["sky_strength"]
        log("world", f"Sky IBL 啟用（strength={p['sky_strength']}, 仰角={p['sun_elev_deg']}°）")
    except Exception as exc:  # noqa: BLE001 - 降級要留紀錄
        log("world", f"WARNING: Sky 設定失敗，降級為中性灰背景: {exc}")
        bg.inputs["Color"].default_value = (0.5, 0.52, 0.55, 1.0)
        bg.inputs["Strength"].default_value = 0.6
    if p["fog_density"] > 0:
        if p["sky_strength"] > 0.15:
            # world volume 會吃掉 Sky 背景光（無限介質透射率→0，實測 mean 0.3）——
            # 白天场景禁止 world volume；要霧請改有限域 domain box（skill §8 #8）
            fail("world", f"fog_density={p['fog_density']} 與 sky_strength={p['sky_strength']} 並存"
                          " = world volume 吞掉天空背景必黑圖；白天請設 fog_density=0")
        try:
            vol = wnt.nodes.new("ShaderNodeVolumeScatter")
            vol.inputs["Density"].default_value = p["fog_density"]
            vol.inputs["Color"].default_value = (1.0, 0.92, 0.82, 1.0)
            wnt.links.new(vol.outputs["Volume"], wout.inputs["Volume"])
            log("world", f"體積霧啟用（density={p['fog_density']}，夜景限定 ≤0.02 鐵律）")
        except Exception as exc:  # noqa: BLE001
            log("world", f"WARNING: 體積霧設定失敗，跳過: {exc}")


def add_stylized_sky(zenith_color=(0.10, 0.42, 0.82), horizon_color=(0.62, 0.78, 0.93),
                     cloud_color=(0.97, 0.97, 0.98), cloud_coverage: float = 0.0,
                     cloud_scale: float = 3.0, cloud_softness: float = 0.25,
                     strength: float = 1.0) -> None:
    """程序化天空：天頂/地平線雙色漸層 + 選填雲層（2026-09-11 新增，日式動漫街景
    參考渲染逆向分析，見 `styles/genre/anime-cel-daylight.md`）。

    **跟 `build_world()` 的 Sky Texture（Nishita 大氣散射）是兩條不同路徑，
    不要混用同一次呼叫**：Nishita 算得出物理正確的藍天漸層跟太陽光暈，但**本身
    不會畫出真正的積雲形狀**——參考渲染那種「大片高飽和純淨藍天+幾朵邊緣分明的
    白色積雲」是額外疊加的效果，不是 Sky Texture 內建能力。這支函式改走純色雙色
    漸層（色彩完全可控，不受大氣模擬參數牽制）+ Noise 遮罩畫「雲」——**這不是
    真正的體積雲**（沒有雲的立體厚度/自身陰影），是貼在天空背景上的 2D 雲形色塊，
    色彩可以準確對齊參考圖，但沒有真雲的體積感/透視縮放，動工前要讓使用者知道
    這個取捨（真正的體積雲需要 Volume Scatter+Mesh Domain，成本遠高於這支函式，
    非必要不要做）。

    zenith_color/horizon_color：天頂/地平線色——真實晴空因為地平線大氣散射路徑
    更長而偏白/偏淡，天頂更深更飽和，`horizon_color` 應該明顯比 `zenith_color`
    更淺/更不飽和，兩色太接近天空會顯得平淡沒有層次（實測校準：日景晴空可用
    `zenith=(0.10,0.42,0.82)` 天頂深藍、`horizon=(0.62,0.78,0.93)` 地平線淺藍白，
    對齊參考渲染的高飽和度晴空印象）。cloud_coverage：0.0（無雲，預設，向下
    相容）~1.0（幾乎滿天雲）；參考渲染那種「幾朵邊緣分明積雲、大片留白純淨藍天」
    約對應 0.2-0.35，不要調太高蓋過藍天本身。cloud_scale 越大雲塊越多越碎；
    cloud_softness 控制雲緣羽化（真實積雲邊緣偏硬朗，0.15-0.25 比較接近，數值
    越高邊緣越糊）。

    呼叫前提：`world.use_nodes=True` 且 `Background`/`World Output` 節點已存在
    （`build_world()` 跑過，或手動 `world = bpy.data.worlds.new(...)` 之後自己
    `use_nodes=True`）——本函式直接覆寫 `Background` 的 `Color` 輸入，不新建
    World。"""
    world = bpy.context.scene.world
    if world is None or not world.use_nodes:
        fail("world", "add_stylized_sky: 需要先有 world.use_nodes=True 的 World（build_world() 或手動建立）")
    wnt = world.node_tree
    bg = next((n for n in wnt.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        fail("world", "add_stylized_sky: World 節點樹找不到 Background 節點")

    coord = wnt.nodes.new("ShaderNodeTexCoord")
    sep = wnt.nodes.new("ShaderNodeSeparateXYZ")
    wnt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    grad_fac = wnt.nodes.new("ShaderNodeMapRange")
    grad_fac.inputs["From Min"].default_value = -0.05
    grad_fac.inputs["From Max"].default_value = 0.65
    grad_fac.clamp = True
    wnt.links.new(sep.outputs["Z"], grad_fac.inputs["Value"])
    sky_mix = wnt.nodes.new("ShaderNodeMixRGB")
    sky_mix.inputs["Color1"].default_value = (*horizon_color, 1.0)
    sky_mix.inputs["Color2"].default_value = (*zenith_color, 1.0)
    wnt.links.new(grad_fac.outputs["Result"], sky_mix.inputs["Fac"])
    final_socket = sky_mix.outputs["Color"]

    if cloud_coverage > 0.0:
        noise = wnt.nodes.new("ShaderNodeTexNoise")
        wnt.links.new(coord.outputs["Generated"], noise.inputs["Vector"])
        noise.inputs["Scale"].default_value = cloud_scale
        noise.inputs["Detail"].default_value = 5.0
        ramp = wnt.nodes.new("ShaderNodeValToRGB")
        lo = max(0.0, 1.0 - cloud_coverage - cloud_softness)
        hi = max(lo + 0.01, 1.0 - cloud_coverage)
        ramp.color_ramp.elements[0].position = lo
        ramp.color_ramp.elements[1].position = hi
        wnt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        # 雲只出現在地平線以上（Z>0），避免雲塊被鏡射到地面方向
        above_horizon = wnt.nodes.new("ShaderNodeMath")
        above_horizon.operation = "GREATER_THAN"
        above_horizon.inputs[1].default_value = 0.05
        wnt.links.new(sep.outputs["Z"], above_horizon.inputs[0])
        cloud_mask = wnt.nodes.new("ShaderNodeMath")
        cloud_mask.operation = "MULTIPLY"
        wnt.links.new(ramp.outputs["Color"], cloud_mask.inputs[0])
        wnt.links.new(above_horizon.outputs["Value"], cloud_mask.inputs[1])
        cloud_mix = wnt.nodes.new("ShaderNodeMixRGB")
        cloud_mix.inputs["Color2"].default_value = (*cloud_color, 1.0)
        wnt.links.new(final_socket, cloud_mix.inputs["Color1"])
        wnt.links.new(cloud_mask.outputs["Value"], cloud_mix.inputs["Fac"])
        final_socket = cloud_mix.outputs["Color"]

    wnt.links.new(final_socket, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    log("world", f"add_stylized_sky: zenith={zenith_color} horizon={horizon_color} "
                f"cloud_coverage={cloud_coverage}")


def add_night_stars(density: float = 40.0, dot_size: float = 0.010, brightness: float = 3.0) -> None:
    """夜空星點（2026-09-11 新增，配合 `add_stylized_sky()` 的夜景版本使用，同一份
    參考渲染逆向分析）：Voronoi `DISTANCE_TO_EDGE` 在每個胞元邊界附近形成細線網格、
    在胞元中心形成距離最大的暗點——這裡故意反過來取「距離邊界最遠＝胞元中心」
    這個特性不合用，改用標準 F1 距離場（每個亂數種子點附近距離趨近 0）配合
    `LESS_THAN` 閾值，胞元中心點本身形成小圓斑，密度/大小分別由 `density`
    （Voronoi Scale，越大星點越多越密）跟 `dot_size`（距離閾值，越大星點越大）
    控制。星點用 ADD 疊加在既有背景色上（不是取代），數值可以超過 1.0（World
    背景色是 HDR，不會被夾在 0-1，`brightness` 越高星點在渲染裡越亮/越有
    「發光感」，不是單純泛白）。**只加在地平線以上**（跟 `add_stylized_sky()`
    的雲遮罩同一個防呆理由）。

    呼叫順序：先呼叫 `add_stylized_sky()`（或任何已經把顏色接上 `Background.Color`
    的設定）建好夜空底色漸層，再呼叫本函式疊加星點——本函式會讀取 `Background.
    Color` 目前的連線當作星點疊加的底圖，沒有既有連線則退回讀取 `Background.Color`
    的靜態值。"""
    world = bpy.context.scene.world
    if world is None or not world.use_nodes:
        fail("world", "add_night_stars: 需要先有 world.use_nodes=True 的 World")
    wnt = world.node_tree
    bg = next((n for n in wnt.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        fail("world", "add_night_stars: World 節點樹找不到 Background 節點")

    existing_socket = None
    if bg.inputs["Color"].links:
        existing_socket = bg.inputs["Color"].links[0].from_socket
    else:
        base = wnt.nodes.new("ShaderNodeRGB")
        base.outputs[0].default_value = bg.inputs["Color"].default_value
        existing_socket = base.outputs[0]

    coord = wnt.nodes.new("ShaderNodeTexCoord")
    sep = wnt.nodes.new("ShaderNodeSeparateXYZ")
    wnt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    voro = wnt.nodes.new("ShaderNodeTexVoronoi")
    voro.voronoi_dimensions = "3D"
    voro.feature = "F1"
    voro.inputs["Scale"].default_value = density
    wnt.links.new(coord.outputs["Generated"], voro.inputs["Vector"])
    star_mask = wnt.nodes.new("ShaderNodeMath")
    star_mask.operation = "LESS_THAN"
    star_mask.inputs[1].default_value = dot_size
    wnt.links.new(voro.outputs["Distance"], star_mask.inputs[0])
    above_horizon = wnt.nodes.new("ShaderNodeMath")
    above_horizon.operation = "GREATER_THAN"
    above_horizon.inputs[1].default_value = 0.05
    wnt.links.new(sep.outputs["Z"], above_horizon.inputs[0])
    star_final = wnt.nodes.new("ShaderNodeMath")
    star_final.operation = "MULTIPLY"
    wnt.links.new(star_mask.outputs["Value"], star_final.inputs[0])
    wnt.links.new(above_horizon.outputs["Value"], star_final.inputs[1])
    star_scaled = wnt.nodes.new("ShaderNodeMath")
    star_scaled.operation = "MULTIPLY"
    star_scaled.inputs[1].default_value = brightness
    wnt.links.new(star_final.outputs["Value"], star_scaled.inputs[0])

    add_node = wnt.nodes.new("ShaderNodeMixRGB")
    add_node.blend_type = "ADD"
    add_node.inputs["Fac"].default_value = 1.0
    wnt.links.new(existing_socket, add_node.inputs["Color1"])
    wnt.links.new(star_scaled.outputs["Value"], add_node.inputs["Color2"])
    wnt.links.new(add_node.outputs["Color"], bg.inputs["Color"])
    log("world", f"add_night_stars: density={density} dot_size={dot_size} brightness={brightness}")


def build_ground(p: dict) -> None:
    """地面：Noise 兩色混染大平面（棚拍=深灰微水泥，戶外=草地色）+ 遠距離霧化漸層。

    **2026-09-09 尺寸從 30x30m 改成 2000x2000m**（實測事故：高樓案例地面邊緣直接
    穿幫入鏡）。**2026-09-10 三輪修正**（運動場案例，前兩輪都實測無效，完整記錄
    避免重蹈，這不是隨手一次就對的問題）：

    第一輪——尺寸放大到 20000m + 用「離世界原點的距離」算外緣漸層。**無效**：
    半徑放大後，固定比例（外緣 12%）換算出的畫面角度寬度反而縮小，漸層帶被壓縮
    到不到 2 像素，肉眼看跟硬邊沒兩樣。

    第二輪——改用 `ShaderNodeLayerWeight` 的 `Facing`（視線跟地面法向量掠射角）。
    邏輯方向沒錯，但**實測同樣無效，用像素取樣證實**（運動場重渲後邊緣位置、
    色值完全沒變）：真正的根因比想像中更底層——**畫面裡那條硬邊本身不是「地面
    材質在邊緣附近變了顏色」，是「這條視線光到底有沒有打到地面網格」的幾何
    on/off 邊界**。相機仰角固定時，每條視線光跟地面的夾角 θ 決定它會在多遠處
    命中地面（`d = 相機高度 / tan(θ)`）——θ 越接近 0（越貼近相機水平視線）、
    命中距離 d 越大，直到超過地面網格實際的半徑（10000m）之後，這條視線光根本
    打不到任何地面，直接落到世界背景色。這個「打得到/打不到」邊界的角度寬度
    在像素取樣層級趨近於 0（打到地面的最後一個像素本身，Facing 值都還遠高於
    掠射角門檻）——materal 端的漸層邏輯（不管是距離版還是 Facing 版）都只能
    改變「打到地面的像素」的顏色，改變不了「根本沒打到地面」的像素，兩種版本
    的漸層都被壓縮在命中邊界正上方那 1-2 個像素內，實際完全不可見。

    第三輪（目前版本）——**漸層必須在網格實際邊緣「之前」就已經完全退到霧色**，
    不能是「越接近邊緣顏色越淡、恰好在邊緣淡完」（前兩輪都是這個設計，必然被
    幾何邊界卡住）。改用 `ShaderNodeCameraData` 的 `View Distance`（每個著色點到
    **相機**的實際距離，不是到世界原點——場景主體/相機位置每次都不同，用相機
    當參考點才對每個鏡頭都準）：`fade_start`（預設 2500m）到 `fade_end`（預設
    8500m，留在地面實際半徑 10000m 以內）之間線性霧化，**到 8500m 處地面色已經
    100% 等於霧色**——等到視線終於因為角度太淺而打不到地面網格（通常落在
    9000m+ 甚至更遠處），畫面上那個位置早就已經是霧色，跟世界背景色銜接，
    「打不到地面」的幾何邊界因此被完全藏起來，不會再露出硬邊。`fade_start`/
    `fade_end` 可經 `preset_overrides={"ground_fade_start":..., "ground_fade_end":...}`
    覆寫（主體巨大、相機拉得比運動場更遠時，兩個值都要跟著放大，維持 `fade_end`
    明顯小於地面半徑 10000m 的安全邊界）。

    **狀態誠實記錄（2026-09-10，未解決，先擱置）**：第三輪重渲後用像素取樣直接比對
    邊緣座標——**RGB 數值跟前兩輪一模一樣，連一碼都沒變**，這版一樣沒有實際生效。
    `View Distance` 節點本身用獨立除錯材質量過、數值合理，接線也用程式檢查過確實
    連到 Map Range，但最終渲染結果就是量不到任何漸層效果，懷疑是色調映射（AgX）
    或渲染管線某個還沒抓到的環節把已經算出來的漸層值蓋掉了，尚未找到真正原因。
    **這支函式目前對「相機拉遠+低仰角看巨大主體」這類邊緣穿幫問題實際上沒有防護
    效果**，`fade_start`/`fade_end`/`ground_fade_color` 這幾個參數目前形同虛設，
    不要假設這裡已經解決——遇到同樣的穿幫問題，暫時只能用「拉高鏡頭仰角、避免
    接近水平視角」這種鏡頭選角層面的迴避，不是這支函式能處理的。下次要接手這個
    問題，直接從「渲染結果證實漸層節點值沒有反映在最終像素」這個事實往下查，
    不要重複前三輪已經排除的假設（離原點距離/掠射角/相機距離三種漸層依據都已
    證實無效或無法驗證生效）。"""
    if GROUND_MAT_OVERRIDE is not None:
        # 3 渲 2：地面用呼叫端給的 cel 材質（見 set_ground_mat()）——同一塊大平面，
        # 但不套 noise 混染與距離霧化（那兩者都是寫實紋理語言，會摧毀色塊）。
        add_box("Ground", (20000.0, 20000.0, 0.1), (0, 0, -0.05), mat=GROUND_MAT_OVERRIDE)
        log("environment", f"地面完成（20000x20000m，材質由 set_ground_mat() 覆寫為 "
                           f"'{GROUND_MAT_OVERRIDE.name}'——乾淨色塊、無 noise/距離漸層）")
        return
    mat = add_noise_color_mat("Ground", p["ground_a"], p["ground_b"], scale=6.0,
                              roughness=0.6, detail=9.0)
    half_size = 10000.0
    fade_color = p.get("ground_fade_color", (0.72, 0.75, 0.80))
    fade_start = p.get("ground_fade_start", 2500.0)
    fade_end = p.get("ground_fade_end", 8500.0)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    base_color_link = bsdf.inputs["Base Color"].links[0]
    ground_color_socket = base_color_link.from_socket
    cam_data = nt.nodes.new("ShaderNodeCameraData")
    map_range = nt.nodes.new("ShaderNodeMapRange")
    map_range.inputs["From Min"].default_value = fade_start
    map_range.inputs["From Max"].default_value = fade_end
    map_range.inputs["To Min"].default_value = 0.0
    map_range.inputs["To Max"].default_value = 1.0
    map_range.clamp = True
    fade_mix = nt.nodes.new("ShaderNodeMixRGB")
    fade_mix.inputs["Color2"].default_value = (*fade_color, 1.0)
    nt.links.new(cam_data.outputs["View Distance"], map_range.inputs["Value"])
    nt.links.new(ground_color_socket, fade_mix.inputs["Color1"])
    nt.links.new(map_range.outputs["Result"], fade_mix.inputs["Fac"])
    nt.links.new(fade_mix.outputs["Color"], bsdf.inputs["Base Color"])
    add_box("Ground", (half_size * 2, half_size * 2, 0.1), (0, 0, -0.05), mat=mat)
    # 2026-09-10：log 訊息刻意不寫「取代硬邊」——這個漸層機制目前實測未生效（見本函式
    # docstring 的誠實記錄），只寫客觀存在的設定值，不要在 log 裡暗示問題已解決。
    log("environment", f"地面完成（{half_size*2:.0f}x{half_size*2:.0f}m 程序化混染，"
                       f"外緣霧化漸層設定 {fade_start:.0f}-{fade_end:.0f}m〔實測未生效，"
                       f"見 build_ground() docstring〕）")


def build_lights(p: dict) -> None:
    """太陽 + 三點式（棚拍）/ practical（戶外夜景）。能量值來自實測配方，勿手調。"""
    elev, azim = math.radians(p["sun_elev_deg"]), math.radians(p["sun_azim_deg"])
    sun_dir = Vector((math.cos(elev) * math.cos(azim),
                      math.cos(elev) * math.sin(azim),
                      math.sin(elev)))
    bpy.ops.object.light_add(type="SUN", location=tuple(sun_dir * 8.0))
    sun = bpy.context.active_object
    sun.name = "Sun"
    _sun_scale = LIGHT_RIG_OVERRIDE.get("energy_scale", 1.0) if LIGHT_RIG_OVERRIDE else 1.0
    sun.data.energy = p["sun_energy"] * _sun_scale
    sun.data.color = p["sun_color"]
    # cel 路線要 0.0°（切斷半影、明暗界線才夠硬），PBR 維持 4.0°——見 SUN_ANGLE_DEG。
    sun.data.angle = math.radians(4.0 if SUN_ANGLE_DEG is None else SUN_ANGLE_DEG)
    if CEL_SHADOW_SETTINGS:
        # EEVEE 的陰影來自 shadow map：預設解析度下，主體**自投影**的明暗界線會沿網格
        # 鋸齒化（實測把 UV 球從 48×24 提到 192×96 完全沒改善——那不是幾何面數問題，
        # 是 shadow map 的取樣解析度）。`shadow_maximum_resolution` 是世界空間的最小
        # 取樣間距，給小值＝提高解析度。
        for _attr, _val in CEL_SHADOW_SETTINGS.items():
            try:
                setattr(sun.data, _attr, _val)
            except (AttributeError, TypeError) as exc:  # noqa: BLE001
                log("lighting", f"WARNING: SUN.{_attr} 設定失敗（{exc}），沿用預設")
        log("lighting", f"cel 陰影品質：{CEL_SHADOW_SETTINGS}")
    sun.rotation_euler = (-sun_dir).to_track_quat("-Z", "Y").to_euler()
    if LIGHT_RIG_OVERRIDE is not None:
        for name, loc, energy, size, color, target in LIGHT_RIG_OVERRIDE["lights"]:
            bpy.ops.object.light_add(type="AREA", location=loc)
            lt = bpy.context.active_object
            lt.name = name
            lt.data.energy = energy
            lt.data.size = size
            lt.data.color = color
            lt.rotation_euler = (Vector(target) - lt.location).to_track_quat("-Z", "Y").to_euler()
        log("lighting", f"三點式（auto_frame_and_light 覆寫，bbox_diag={LIGHT_RIG_OVERRIDE['bbox_diag']:.2f}m，"
                        f"style={LIGHT_RIG_OVERRIDE['style']}）")
    elif p["key_energy"] > 0:
        for name, loc, energy, size, color in (
            ("KeyLight", (-1.8, -1.4, 2.4), p["key_energy"], 2.2, (1.0, 0.97, 0.92)),
            ("FillLight", (2.2, -0.8, 1.3), p["fill_energy"], 2.0, (0.92, 0.94, 1.0)),
            ("RimLight", (0.9, 2.2, 1.9), p["rim_energy"], 1.6, (1.0, 0.93, 0.85)),
        ):
            bpy.ops.object.light_add(type="AREA", location=loc)
            lt = bpy.context.active_object
            lt.name = name
            lt.data.energy = energy
            lt.data.size = size
            lt.data.color = color
            lt.rotation_euler = (Vector((0, 0, 0.45)) - lt.location).to_track_quat("-Z", "Y").to_euler()
        log("lighting", f"三點式：Sun {p['sun_energy']} + Key {p['key_energy']}"
                        f" + Fill {p['fill_energy']} + Rim {p['rim_energy']}")
    _fill_rig = SPACE_FILL_OVERRIDE or NIGHT_FILL_OVERRIDE
    if _fill_rig is not None:
        for name, loc, energy, size, color, target in _fill_rig["lights"]:
            bpy.ops.object.light_add(type="AREA", location=loc)
            lt = bpy.context.active_object
            lt.name = name
            lt.data.energy = energy
            lt.data.size = size
            lt.data.color = color
            lt.rotation_euler = (Vector(target) - lt.location).to_track_quat("-Z", "Y").to_euler()
        _fill_tag = ("auto_space_fill 太空（行星反照＋暖色輪廓）" if SPACE_FILL_OVERRIDE
                     else "auto_night_fill 夜景")
        log("lighting", f"基礎覆蓋補光（{_fill_tag} 覆寫，"
                        f"bbox_diag={_fill_rig['bbox_diag']:.2f}m）——"
                        "取代舊版寫死世界原點的單顆 InteriorLight")
    elif p.get("interior_energy", 0) > 0:
        bpy.ops.object.light_add(type="POINT", location=(0.0, 0.0, 1.5))
        interior = bpy.context.active_object
        interior.name = "InteriorLight"
        interior.data.energy = p["interior_energy"]
        interior.data.color = (1.0, 0.75, 0.45)
        interior.data.shadow_soft_size = 0.4  # 5.1：無 radius 屬性（skill §8 #1）
        log("lighting", f"practical 室內光 {p['interior_energy']}W（舊版固定世界原點單顆點光，"
                        "場景較大或物件不集中在原點附近時建議改用 auto_night_fill()）")


def build_camera() -> float:
    """相機 + 景深；回傳對焦距離。CAM_TYPE='ORTHO' 時跳過景深（正交投影沒有景深概念，
    aperture/focus_distance 對它無意義，硬設只會是死參數）。

    **2026-09-11 實測驗證**：`CAM_TYPE='ORTHO'` 路徑從未呼叫 `cam.data.dof.use_dof
    = True`，且 Blender 新建相機物件的 `dof.use_dof` 預設就是 `False`——實測直接
    查詢剛建好的 ORTHO 相機物件屬性確認 `use_dof=False`，ORTHO 渲染保證不會有景深
    模糊，這條規則本來就成立，不是這次才修的 bug。`auto_frame_and_light()`（本檔
    最常用的相機/燈光入口）本身就會呼叫 `set_camera(cam_type="ORTHO", ...)`，所以
    絕大多數場景腳本走的都是這條保證清晰的路徑；只有呼叫端**自己**明確要求
    `cam_type="PERSP"`（或完全不呼叫 `set_camera()`/`auto_frame_and_light()`，
    落到模組層級預設 `CAM_TYPE="PERSP"`）才會啟用真正的景深模糊（預設 f/2.8，
    是刻意設計來模擬商業攝影棚淺景深，不是失誤）。

    **如果渲染圖看起來「模糊/朦朧」但確定用的是 ORTHO 相機，兇手通常不是景深，
    是 `setup_render()` 的 Fog Glow 合成器泛光**——這個效果對任何場景的高亮處
    （反光金屬、自發光招牌/窗戶、鏡面高光）一律套用，且完全獨立於相機類型，
    實測用同一個 ORTHO 場景關掉/開啟 Fog Glow 直接比對：一般幾何邊緣（文字/方塊
    輪廓）銳利度沒有差異，但高亮物件周圍會冒出明顯的柔光暈染/橫向光暈條紋，肉眼
    容易誤判成「整張圖有點糊」。想要完全銳利無暈染的技術感渲染，調高
    `preset_overrides` 的 `bloom_threshold`（拉高到明顯高於畫面最亮處的亮度值，
    等於實質關閉泛光觸發），不要誤以為要去改相機/景深設定。**`bloom_size` 在既有
    配方的值上調不動**——它是 0–1 的 FACTOR 且 ≥1 已飽和（見 §8 落差表），要真的
    縮小暈染範圍必須填 <1 的值（例如 0.25）。"""
    bpy.ops.object.camera_add(location=CAM_LOC)
    cam = bpy.context.active_object
    cam.name = "Camera"
    direction = Vector(CAM_TARGET) - Vector(CAM_LOC)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if CAM_TYPE == "ORTHO":
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = CAM_ORTHO_SCALE
    else:
        cam.data.lens = CAM_LENS
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = CAM_FSTOP
        cam.data.dof.focus_distance = direction.length
    # clip_end 預設 1000m——主體＋機位距離一旦超過（例如高塔類大尺度主體用 set_camera()
    # 拉遠機位），整個主體會落在遠裁切面外變成完全不可見，只剩世界背景色，肉眼會誤判成
    # 「曝光死黑」而不是「其實根本沒渲染到主體」（auto_frame_and_light() 實測踩過這個坑，
    # 見該函式與 §13 pitfall 13）。一律依實際對焦距離重算，不吃預設值。
    cam.data.clip_start = max(0.001, direction.length * 0.01)
    cam.data.clip_end = max(1000.0, direction.length * 4.0)
    bpy.context.scene.camera = cam
    log("camera", f"機位 {CAM_LOC}，"
                  f"{'ORTHO scale=' + str(CAM_ORTHO_SCALE) if CAM_TYPE == 'ORTHO' else f'{CAM_LENS}mm f/{CAM_FSTOP}'}")
    return direction.length


def auto_frame_and_light(objects: list, style: str = "product",
                          azimuth_deg: float = -125.0, elevation_deg: float = 35.0,
                          ortho_margin: float = 1.4, energy_scale: float = 1.0) -> dict:
    """依主體實際世界包圍盒自動算相機構圖 + 三點式棚拍燈光，取代寫死的人體尺度絕對座標
    （§13 pitfall 13 新增，東方明珠塔事故根因：build_camera()/build_lights() 的固定機位
    /燈位是為 ~1-2m demo 物件校準的，直接套在 468m 高塔上機位形同貼著塔基站，燈光能量
    也差了幾個數量級——近黑曝光只是表象，實際問題是整組配方跟主體完全不成比例）。

    用法：subject_fn() 建完主體幾何後，在 return 前呼叫一次：
        T.auto_frame_and_light(mesh_objs, style="product")
    subject_fn 一結束、main() 接著跑到 build_lights()/build_camera() 時會自動讀到這次
    算出的覆寫值——不需要呼叫端自己再叫 set_camera() 或碰 PRESETS。

    objects: 要納入構圖的物件（通常是 subject_fn 建的全部 mesh），用這批物件世界座標
    包圍盒的聯集算主體中心與對角線長度 diag，接下來相機距離、三燈位置、三燈能量、三燈
    尺寸全部用 diag 的倍數表示，不是寫死公尺數——同一份配方對 0.15m 的水杯跟 468m 的
    高樓都成立（3000 倍尺度範圍實測驗證，見 skill research notes）。
    style: "product"（三點式棚拍，中性均勻照亮，clipped≈2.5%）或 "dramatic"
    （對比更強、fill 更弱、rim 更亮，clipped≈5%）。
    azimuth_deg/elevation_deg: 相機繞主體中心的水平/垂直觀察角，0°=沿 +X 看，
    90°=垂直俯視。**預設 2026-09-09 由 35.0 改成 -125.0**（相機案例實測抓到
    的真實 bug：舊預設 35° 讓相機落在主體 +Y 側往回看——本 skill §11/§16.1 全域約定
    「主體正面朝 -Y（觀眾/相機側）」，35° 那組角度剛好把相機擺到主體**背面**，渲染
    出來是背面特寫不是正面——-125° 讓相機落在 -Y 側，同樣 35° 偏角構出四分之三視角，
    但看的是正面。呼叫端如果自己的主體正面朝別的方向，記得覆寫這兩個參數，不要照抄
    預設值當萬用解。
    ortho_margin：2026-09-09 新增，取代舊版透視相機（`lens=35, fstop=4.0`）——查證
    四個獨立驗證案例（相機/大樓/舞台/卡丁車）全部用 ORTHO 相機構圖，不是
    PERSP：ORTHO 避免透視相機近距離特寫的邊緣拉伸失真，構圖留白只用 ortho_scale 一個
    數字直接控制，不用像透視相機那樣同時兼顧距離+FOV 才能保證「主體全身入鏡+有留白」
    （相機案例實測反例：透視相機+diag*1.8 距離組合渲得太貼近，主體幾乎頂到
    畫面邊緣，沒有留白）。ortho_margin 直接乘在 diag 上得到 ortho_scale——1.4 保守
    給約 40% 餘裕（主體 2D 投影範圍恆 ≤ 3D diag，1.4 倍已經算寬裕留白，不需要為了
    「留更多白」盲目調更大，那樣主體在畫面裡反而顯小）。

    回傳 dict（純供呼叫端 log/斷言用，不需要餵回其他函式）：
    {"bbox_diag": float, "cam_loc": tuple, "cam_target": tuple}。

    已知限制：
    1. 能量公式是對著單一材質、面朝主光源的簡單量體（立方體）實測校準的——複雜主體
       （多材質、深凹面、高反光）實際 clipped/dark 比例可能偏離這個基準，仍建議照 §2
       走 CALIB 快渲 + luma_stats/check_exposure 驗證，不要假設這個函式必然入帶。
       **2026-09-09 新增實測證據**：拋光 chrome 材質主體（相機案例）舊版
       （PERSP 相機+azimuth 35°+三輪疊加修正：sun_energy×0.55、clipped_max 放寬、
       三燈能量再×0.375）渲出 mean=184.9 仍過曝、且是背面特寫。改成本次修正版（ORTHO
       相機+azimuth -125°+三燈能量單次乘 0.45，不疊加其他修正）後**同一份場景重渲
       實測 mean=168.4（入帶 100-170）、clipped_pct=3.71%（chrome 鏡面高光，物理
       預期內）**——單次 derate 就夠，不需要三層疊加。呼叫端如果主體有大面積高反光
       金屬（chrome/拋光鋁/鏡面漆），**建議動工前就先傳 `energy_scale=0.4~0.5` 起跑**，
       不要等 CALIB 過曝了才一輪一輪盲猜修正——猜的時候模型本來就看不到渲染結果，
       每一輪都是無意義的盲改。
       **這個 0.4-0.5 倍率是為高反光金屬校準的，不要跨材質照抄**（2026-09-09 新增，
       卡丁車實測事故：啞光塑膠車身照搬相機案例的 0.35 derate，LUMA mean=163.5 雖然
       落在 100-170 帶內、沒有觸發任何守衛，但飽和紅色被沖淡成粉紅色，跟色彩無關的
       陰影銳利度/bloom/取樣數/AgX look 全部測過都不是主因——實測把 derate 再乘 0.4
       （累計 0.14）才讓紅色恢復飽和，mean 落到 119.7、p1 從 48.6 掉到 17.4，肉眼
       比對前後差異巨大。**同一個 LUMA 帶內的數值不代表視覺效果一樣好**——啞光/
       漫反射材質為主的主體，若渲染出來「泛白、顏色不飽和」而不是「反光鏡面過曝」，
       別照搬 chrome 那組 0.4-0.5，重新用實際渲染比對找出讓色彩飽和的能量水位，
       常見數值範圍可能要到 0.1-0.2 這個量級。
       **`energy_scale` 參數（2026-09-09 新增，取代舊版「呼叫端自行改寫
       `LIGHT_RIG_OVERRIDE["lights"]`」的手法）**——香港的士案例實測抓到的真正 bug：
       舊手法只把三點式 AREA 燈能量乘上 derate（`LIGHT_RIG_OVERRIDE["lights"]` 重寫成
       `energy*0.38`），但 `build_lights()` 的太陽光是**獨立**讀 `p["sun_energy"]`，
       跟三點式完全脫鉤——derate 沒碰到太陽，studio 預設 `sun_energy=1.0` 全額命中大片
       引擎蓋/車頂平面，這才是泛白的主因，不是三點式沒 derate 夠。相機案例的舊 fix
       同樣只調了三點式，太陽同樣被漏掉，只是主體形狀（鏡筒為主，無大片平面）沒讓這個
       漏洞這麼顯眼。改用 `energy_scale` 這**唯一入口**後，三點式與太陽用同一個倍率
       連動縮放，物理上不可能再漏掉其中一個光源——呼叫端只需要傳一個數字，不用自己
       手改 `LIGHT_RIG_OVERRIDE` 內容。實測（香港的士，diag=5.36m，energy_scale=0.15）：
       derate 前 mean=168.2/p1=76.7（車身視覺泛白，跟舊版三點式-only 手法症狀一致）→
       derate 後 mean=122.9/p1=29.1，車身紅漆側板肉眼確認飽和，跟卡丁車最終校準值同一
       量級——三個獨立材質案例（chrome/啞光塑膠/glossy 車漆）收斂到同一個 0.14-0.2
       倍率區間，不是巧合，是 studio 預設基準能量本身對「多材質+GI 互相反射」的真實
       場景偏高（單一材質簡單量體校準值不足以代表複雜主體）。**目前沒有一個能自動判斷
       「這個主體該用多少 energy_scale」的公式**，仍然要靠 CALIB 實測比對——但至少
       用這個參數以後，derate 不會再漏掉太陽這個光源。
    2. 只管主體本身的曝光與構圖，不動 build_world()/build_ground() 的天空/地面配方——
       PRESETS 的 luma_band 是為「主體填滿大半畫面」的棚拍構圖校準的全畫面亮度均值；
       細長/巨大主體（例：高塔）用這個函式構圖後，畫面裡主體以外的天空/地面占比會
       明顯變大，全畫面 mean 可能被大量深色背景拉低而觸發 check_exposure() 假警報，
       即使主體本身在畫面裡曝光正確、清晰可見（468m 塔實測驗證：mean=19.9 觸發
       studio 預設的 luma_band 下限，但實際渲染圖裡塔身清楚可見、無死黑無過曝）。
       這種情況下應改用 preset_overrides 放寬 luma_band，或另外只對主體所在畫面
       區域算亮度，不要照抄 studio 預設的 100-170 帶。
    """
    style_energy = {"product": 1.0, "dramatic": 1.15}
    if style not in style_energy:
        fail("config", f"auto_frame_and_light: 未知 style '{style}'（可用：product/dramatic）")
    bpy.context.view_layer.update()
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    if not objs:
        fail("assertion", "auto_frame_and_light: objects 不可為空")
    xs, ys, zs = [], [], []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    xmin, xmax, ymin, ymax, zmin, zmax = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    center = Vector(((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2))
    diag = Vector((xmax - xmin, ymax - ymin, zmax - zmin)).length
    if diag < 1e-6:
        fail("assertion", "auto_frame_and_light: 包圍盒對角線接近 0，objects 可能沒有實際幾何")

    # 依主體實際高寬比自動選畫幅（2026-09-09 新增，見 set_aspect() 說明）——只在呼叫端
    # 沒有手動 set_aspect() 鎖定時才動，尊重明確指定的選擇。height_z 相對水平最大跨度
    # 的比例 >1.3 判定「高」用直幅 9:16（高樓/直立產品）、<0.7 判定「寬」用橫幅 16:9
    # （道路/街景/寬幅場景），中間維持預設方幅 1:1。
    if not _ASPECT_LOCKED:
        height_z = zmax - zmin
        horiz = max(xmax - xmin, ymax - ymin) or 1e-6
        ratio = height_z / horiz
        auto_aspect = "9:16" if ratio > 1.3 else "16:9" if ratio < 0.7 else "1:1"
        if auto_aspect != ASPECT:
            set_aspect(auto_aspect)
            log("camera", f"auto_frame_and_light: 依主體高寬比({ratio:.2f})自動選畫幅 {auto_aspect}")

    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    cam_dist = diag * 1.8  # 實測經驗值：ORTHO 相機距離不影響構圖，只需夠遠避免穿模
    cam_dir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    cam_loc = center + cam_dir * cam_dist
    set_camera(tuple(cam_loc), tuple(center), cam_type="ORTHO", ortho_scale=diag * ortho_margin)

    # AREA 光能量隨距離平方衰減，300 是對 diag≈1m 立方體實測校準出的基準常數
    # （key_const=300 → mean=81.7, clipped=2.5%，見 skill research notes 校準紀錄）；
    # ×diag² 讓同一個常數對任何尺度的主體都得出相近的相對亮度，不用呼叫端自己猜能量值。
    key_const = 300.0 * style_energy[style]
    fill_const = 300.0 * (0.4 if style == "product" else 0.12)
    rim_const = 300.0 * (0.5 if style == "product" else 0.6)
    key_color = (1.0, 0.97, 0.92) if style == "product" else (1.0, 0.9, 0.8)
    lights = []
    for name, ang_h, ang_v, energy, size_ratio, color in (
        ("KeyLight", az - math.radians(45), math.radians(30), key_const, 1.1, key_color),
        ("FillLight", az + math.radians(50), math.radians(20), fill_const, 1.0, (0.92, 0.94, 1.0)),
        ("RimLight", az + math.radians(170), math.radians(35), rim_const, 0.7, (1.0, 0.93, 0.85)),
    ):
        dir_vec = Vector((math.cos(ang_v) * math.cos(ang_h), math.cos(ang_v) * math.sin(ang_h), math.sin(ang_v)))
        loc = center + dir_vec * diag * 1.3
        lights.append((name, tuple(loc), energy * (diag ** 2) * energy_scale,
                       max(0.05, diag * size_ratio), color, tuple(center)))

    global LIGHT_RIG_OVERRIDE
    LIGHT_RIG_OVERRIDE = {"lights": lights, "bbox_diag": diag, "style": style,
                          "energy_scale": energy_scale}
    log("lighting", f"auto_frame_and_light: style={style} bbox_diag={diag:.2f}m "
                    f"center={tuple(round(c, 2) for c in center)} cam_dist={cam_dist:.2f}m "
                    f"energy_scale={energy_scale}")
    return {"bbox_diag": diag, "cam_loc": tuple(cam_loc), "cam_target": tuple(center)}


# 3 渲 2 展示卡的補光基準常數（跟自動構圖同一套 diag² 距離平方反比慣例；數值實測校準，
# 見 setup_cel_studio() docstring）。這個數字換算成實際照射量大約是太陽的 10%——cel 的
# fill 只負責「暗階不要掉到死黑」，不參與明暗界線。**不要憑「PBR 三點式的 key=300」的
# 印象填大數字**：實測填 20（＝太陽的 1.3 倍）時陰影階直接歸零 0.0%、整顆主體飽和到
# 最亮階 98%，硬邊界完全消失。
CEL_STUDIO_FILL_CONST = 1.5


def set_ground_mat(mat, name: str = "Ground") -> None:
    """把 `build_ground()` 的地面材質換成呼叫端提供的（3 渲 2 用乾淨色塊地面，見
    `setup_cel_studio()`）。地面物件本身仍由 `build_ground()` 建——懸空審查要拿它當
    支撐面、構圖審查預設排除它——只是不套程序化 noise 混染與距離霧化（那兩者是寫實
    紋理語言，會摧毀 cel 的色塊）。"""
    global GROUND_MAT_OVERRIDE
    if mat is None:
        fail("config", "set_ground_mat: mat 不可為 None")
    GROUND_MAT_OVERRIDE = mat
    log("world", f"地面材質覆寫：{getattr(mat, 'name', mat)}（cel 地面：無 noise、無距離漸層）")


def make_void_ground_mat(name: str = "Mat_VoidGround"):
    """全透明地面材質（Alpha=0）：地面完全消失，連陰影與反射都沒有。

    跟 `set_ground_void()` 預設的 ray-visibility 模式的差別：全透明是**材質**層級，光線
    直接穿過去，地面不投影也不反彈；ray-visibility 模式只擋相機與鏡面，地面仍提供接觸
    陰影（物件不會讀成完全漂浮）。ray_cast 兩者都照常命中。
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        fail("world", "make_void_ground_mat: 找不到 Principled BSDF 節點")
    for key, val in (("Base Color", (0.0, 0.0, 0.0, 1.0)), ("Roughness", 1.0),
                     ("Metallic", 0.0)):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = val
    if "Alpha" not in bsdf.inputs:
        fail("world", "make_void_ground_mat: Principled 沒有 Alpha socket")
    bsdf.inputs["Alpha"].default_value = 0.0
    return mat


def apply_ground_void(obj=None, name: str = "Ground") -> None:
    """把 `set_ground_void()` 登記的可見度覆寫套用到地面物件（`main()` 在 `build_ground()`
    之後呼叫一次）。沒登記、或場景裡找不到地面時什麼都不做。"""
    if GROUND_VIS_OVERRIDE is None:
        return
    obj = obj or bpy.data.objects.get(name)
    if obj is None:
        log("environment", f"WARNING: set_ground_void() 已登記，但場景裡找不到地面物件 "
                           f"'{name}'——覆寫未套用")
        return
    applied = []
    for attr, val in GROUND_VIS_OVERRIDE.items():
        try:
            setattr(obj, attr, val)
            applied.append(f"{attr}={val}")
        except (AttributeError, TypeError) as exc:  # noqa: BLE001
            log("environment", f"WARNING: 地面 {attr} 設定失敗（{exc}）——該項覆寫未生效")
    log("environment", "地面可見度覆寫：" + "、".join(applied)
        + "（幾何仍在場景裡，懸空審查的 ray_cast 支撐面照常）")


def set_ground_void(alpha: float | None = None, name: str = "Ground") -> None:
    """太空／真空場景：讓 `build_ground()` 的地面在畫面裡消失，但幾何仍留在場景中。

    `main()` 無條件呼叫 `build_ground()`（地面是自動懸空審查的支撐面、也是構圖審查預設
    排除的環境件），直接刪掉會讓 ray_cast 失去支撐面。這支提供兩條「留著但不入鏡」的路：

    - `alpha=None`（預設）：per-object ray visibility——`visible_camera=False`（鏡頭看
      不到）、`visible_glossy=False`（鏡面物件不會把它反射進畫面）、
      `visible_transmission=False`。`visible_diffuse`／`visible_shadow` 保持 True，
      地面**仍提供接觸陰影**，ray_cast 照常命中。
    - `alpha=0.0`：地面材質改成全透明（`make_void_ground_mat()`）——連陰影也沒有，場景
      完全讀成真空（軌道／太空站構圖用這條）。會覆寫 `set_ground_mat()` 先前指定的材質。

    **不要**用「把地面配色壓到近黑」代替：地面仍在畫面裡，太陽掠射時會在畫面下緣留下
    一條比星雲帶還亮的灰帶（實測該處亮達 85/255），鏡面物件還會把那塊灰板反射進來——
    星雲帶被這條硬邊切斷的最常見原因就是它。近黑配色只適用於「仍想要一塊看得見的地」。
    """
    global GROUND_MAT_OVERRIDE, GROUND_VIS_OVERRIDE
    if alpha is not None:
        GROUND_MAT_OVERRIDE = make_void_ground_mat()
        log("world", "地面改為全透明材質（Alpha=0）——連陰影一併消失")
    GROUND_VIS_OVERRIDE = {"visible_camera": False, "visible_glossy": False,
                           "visible_transmission": False}
    log("world", f"已登記地面可見度覆寫（{name}：相機／鏡面／穿透不可見，支撐面照常）")


def setup_cel_studio(objects, azimuth_deg: float = -125.0, elevation_deg: float = 32.0,
                     ortho_margin: float = 1.4, sun_energy: float = 2.0,
                     sun_offset_deg: float = -40.0, sun_elev_deg: float | None = None,
                     fill: bool = True, fill_scale: float = 1.0,
                     bg_color=(0.22, 0.22, 0.23), ground_mat=None,
                     outline: bool = True, outline_px: float = 2.4,
                     outline_z_offset: float = 0.0) -> dict:
    """3 渲 2 的**展示卡模式**（單一主體 + ORTHO 棚拍構圖）——一次把 cel 路線需要的
    場景設定全部接好。在 `subject_fn()` 裡呼叫，取代 `auto_frame_and_light()`。

    **為什麼不能直接沿用 PBR 的展示卡設定**（§10.3：中性灰背景 + 三點式 AREA + AgX）：
    cel 用那組會壞三件事——① 三盞能量相當的 AREA 燈各自產生一條明暗界線，硬邊界糊成
    好幾條（cel 的界線只能有一個來源）；② AgX 會把色票打歪（cel 必須 Standard）；
    ③ 地面是程序化 noise 混染，跟「cel 表面必須是乾淨色塊」直接衝突。這支就是同一張
    展示卡的 cel 版本：EEVEE + Standard + 一盞 SUN（`angle=0`，唯一決定明暗界線）+
    低能量 fill + 純色中性背景 + cel 地面 + 背面法外殼，參數直接寫進 main() 的配方覆寫。

    **跟敘事街景模式的分工**：單一主體/產品/一棟建築的「展示卡」請求走這支；要一整個
    街區、天空佔比、招牌堆疊的敘事場景才走 `japanese_street.md` ＋本卡天空配方那條。
    過去沒有這條路，單一主體也會被拉去蓋一整條街——模型本身沒問題，卻被場景拖低檔次。

    objects：要入鏡的主體（決定構圖與所有尺度）。呼叫前先把材質建好。
    elevation_deg／azimuth_deg：相機角度（同時決定太陽高度）。
    `sun_offset_deg`：**太陽相對相機的水平偏移，預設 -40°**——這是 cel 展示卡最關鍵的
    一個參數，不能設 0。太陽跟相機完全同向時，明暗界線會落在主體的輪廓線上（只看得到
    一條細細的陰影月牙、甚至完全看不到），「明暗界線落在哪裡」正是這個路線的畫面主體。
    偏 35-50° 讓界線橫過可見面；繼續加大到接近背光（>90°）就變成剪影。
    `sun_elev_deg`：太陽仰角，預設跟相機同高（`elevation_deg`）。建議 30-45°：太低
    界線壓在輪廓邊緣、太高（頂光）對比消失。
    sun_energy：唯一的明暗界線來源／整體明暗水位。太小→受光面吃不出漸層（只在中階附近）、
    太大→整片飽和到最亮階（漸層消失）。預設值是實測校準值，見下方「預設值怎麼來的」段。
    fill／fill_scale：cel 的補光只負責「暗階不要掉到純黑」，刻意比 PBR 三點式的 key
    低一個數量級（`CEL_STUDIO_FILL_CONST`）；`fill=False` 只留 SUN，是最乾淨的兩階
    （平面感強的構圖、要極高對比時用）。
    bg_color：純色背景（線性 RGB）。**不用天空**——天空漸層＋雲是敘事街景模式的語言，
    展示卡要的是能讓主體色塊跳出來的中性灰。
    ground_mat：傳 `mat_lib.make_cel_advanced()` 的地面材質。不傳會 WARNING 並沿用
    程序化 noise 地面（跟 cel 色塊語言衝突，只在臨時實驗時可接受）。
    outline：順手登記背面法外殼（`request_outline()`；相機就位後由 `main()` 建，
    線寬用真正的最終相機算，ORTHO 走 ortho 公式）。

    回傳 dict：`{"bbox_diag", "cam_loc", "cam_target", "preset_overrides", "sun_energy",
    "fill", "outline_px", "engine", "view_transform"}`——供 log/斷言用。

    **預設值怎麼來的**（實測：Blender 5.1.2 headless、EEVEE、960×540 calib；
    量測對象＝**單一 cel 材質的參考球**，`.capybala/test-scripts/cel_studio_probe.py`
    的 `SCENE=sphere`——這個量法用「最近色階分類」算主體像素落在各色階的比例（cel 走
    Emission 輸出 ＋ Standard 色調映射，色票一比一還原，所以可以用顏色數直接量），
    **只有單一材質的場景才量得準**）。`bg_color=0.22`（線性）、`sun_offset_deg=-40°`
    時（shadow / mid / high，%）：

      sun_energy 1.8 → 46.8 / 53.2 / 0.0    受光面吃不到最亮階，整體偏暗、漸層不見
      sun_energy 2.0 → 36.2 / 36.8 / 27.0   ← 預設值（陰影有份量、受光帶留有完整漸層）
      sun_energy 2.2 → 26.2 / 24.1 / 49.7   受光面開始飽和到最亮階
      sun_energy 3.0 → 15.6 / 10.3 / 74.2   只剩最亮階與陰影兩階，漸層幾乎消失

    `fill=False` 在 2.0 實測 37.7 / 36.2 / 26.1——與預設（有 fill）幾乎相同，證實
    `CelFill` 是「暗階不要掉到死黑」的保底、不參與明暗界線。
    `sun_offset_deg=0` 實測陰影只剩 2-10%（界線縮在輪廓線上、只看得到一條月牙）——這是
    這個模式最容易被忽略、又最影響成敗的一個參數。

    **多物件／多材質的展示卡（例如一顆球＋一根柱＋一個方塊）不要用上面那個量法調參**：
    最近色階分類只認一組色族，其他材質的像素會被誤歸到鄰近色階（實測同一組參數在
    三材質場景量到「陰影 71%」，但渲染圖上受光面明明佔了一半）——那種場景請直接看
    渲染圖調 `sun_energy`，或只對單一材質給 `roi`。
    """
    global SUN_ANGLE_DEG, LIGHT_RIG_OVERRIDE, CEL_SHADOW_SETTINGS
    bpy.context.view_layer.update()
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    if not objs:
        fail("config", "setup_cel_studio: objects 不可為空（要傳入全部入鏡的主體）")

    set_engine("eevee")
    set_view_transform("standard")
    SUN_ANGLE_DEG = 0.0        # 切斷半影：cel 的明暗界線必須是硬邊
    CEL_SHADOW_SETTINGS = {"shadow_maximum_resolution": 0.0001,
                           "use_shadow_jitter": False,
                           "shadow_filter_radius": 0.0}
    for _attr, _val in (("shadow_resolution_scale", 4.0), ("shadow_ray_count", 4),
                        ("shadow_step_count", 8)):
        try:
            setattr(bpy.context.scene.eevee, _attr, _val)
        except (AttributeError, TypeError) as exc:  # noqa: BLE001
            log("lighting", f"WARNING: scene.eevee.{_attr} 設定失敗（{exc}）")
    PRESET_AUTO_OVERRIDES.update({
        "flat_background": True, "bg_color": tuple(bg_color),
        "key_energy": 0.0, "fill_energy": 0.0, "rim_energy": 0.0,
        "sun_energy": float(sun_energy),
        "sun_elev_deg": abs(float(elevation_deg)) if sun_elev_deg is None else float(sun_elev_deg),
        "sun_azim_deg": float(azimuth_deg) + float(sun_offset_deg),
        "fog_density": 0.0,
    })
    rig = auto_frame_and_light(objs, style="product", azimuth_deg=azimuth_deg,
                               elevation_deg=elevation_deg, ortho_margin=ortho_margin,
                               energy_scale=1.0)
    if fill:
        center = Vector(rig["cam_target"])
        diag = rig["bbox_diag"]
        ang_h, ang_v = math.radians(azimuth_deg + 50.0), math.radians(20.0)
        dir_vec = Vector((math.cos(ang_v) * math.cos(ang_h),
                          math.cos(ang_v) * math.sin(ang_h), math.sin(ang_v)))
        loc = center + dir_vec * diag * 1.3
        LIGHT_RIG_OVERRIDE = {
            "lights": [("CelFill", tuple(loc),
                        CEL_STUDIO_FILL_CONST * fill_scale * (diag ** 2),
                        max(0.05, diag * 1.2), (0.92, 0.94, 1.0), tuple(center))],
            "bbox_diag": diag, "style": "cel_studio", "energy_scale": fill_scale}
    else:
        LIGHT_RIG_OVERRIDE = None   # 只留 SUN：最乾淨的兩階，適合平面感強的構圖
    if ground_mat is not None:
        set_ground_mat(ground_mat)
    else:
        log("world", "WARNING: setup_cel_studio 沒收到 ground_mat——地面會沿用程序化 noise "
                     "混染（與 cel 的乾淨色塊語言衝突）；請傳 mat_lib.make_cel_advanced() 的地面材質")
    if outline:
        request_outline(objs, px=outline_px, z_offset=outline_z_offset)
    log("lighting", f"setup_cel_studio：EEVEE + Standard、SUN {sun_energy}（angle=0，唯一明暗界線）"
                    f" + {'CelFill' if fill else '無 fill'}、bg={tuple(bg_color)}、"
                    f"outline={'on px=' + str(outline_px) if outline else 'off'}、"
                    f"diag={rig['bbox_diag']:.2f}m")
    return {"bbox_diag": rig["bbox_diag"], "cam_loc": rig["cam_loc"],
            "cam_target": rig["cam_target"], "preset_overrides": dict(PRESET_AUTO_OVERRIDES),
            "sun_energy": float(sun_energy), "fill": bool(fill),
            "outline_px": outline_px if outline else None,
            "engine": ENGINE, "view_transform": VIEW_TRANSFORM}


def auto_night_fill(objects: list, ambient_scale: float = 1.0) -> dict:
    """夜景場景的「基礎覆蓋率」補光——`night` PRESET 的 `auto_frame_and_light()` 對等版
    （2026-09-11 新增，來源：拉麵屋台夜景事故：整個場景只有呼叫端自己放的 4 顆小範圍
    practical 點光（燈籠+吊燈，集中在棚頂附近），加上 `build_lights()` 舊版寫死在世界
    原點的單顆 `InteriorLight`——兩者都不隨場景實際尺度縮放，板凳/圓凳/背景這些同樣
    入鏡的物件落在有效照射半徑之外，渲染結果除了燈籠/招牌本身幾乎全黑。實測數據：
    mean=30.2（技術上落在 night 帶 15-70 內）、dark_pct=59.4%、但 p50（中位數）只有
    6.4、飽和度量測 0.058／1.0——「平均值合格」跟「畫面看得見」是兩回事，見
    `check_exposure()` 新增的 mean-vs-p50 檢查）。

    跟 `auto_frame_and_light()` 的分工不同，不是取代關係：那支是「主體棚拍三點式
    強光」（product/dramatic 風格，光本身就是重點）；這支是「夜景場景的最低限度月光/
    環境覆蓋」——practical light（燈籠、招牌、窗戶透光、爐火）依然由呼叫端自己
    `bpy.ops.object.light_add()` 放、依然是畫面視覺焦點，這支只負責確保鏡頭範圍內
    「沒有被 practical light 照到的地方」不會直接崩成純黑死角。一個看不見板凳/背景的
    夜景不是「有氣氛」，是「拍失敗了看不出場景」。

    用法：`subject_fn()` 建完**全部**會入鏡的場景物件（不是只有主體——板凳/圓凳/
    背景building/地面陳設這些都要算進去，這支用它們的世界包圍盒聯集決定補光要照多
    遠）後，在 `return` 前呼叫一次：
        T.auto_night_fill(all_scene_objs)
    `main()` 接著跑到 `build_lights()` 時會自動讀到這次算出的覆寫值，取代舊版寫死在
    世界原點、不隨場景尺度縮放的單顆 `InteriorLight`（月光 SUN 不受影響，`SUN` 是
    無限遠平行光源，本來就沒有距離衰減，不需要跟著場景尺度調整）。

    ambient_scale：微調補光整體強度，預設 1.0 對應本函式自己的校準基準（headless
    Blender 實測：4.5m 直徑的拉麵屋台+板凳+圓凳全場景，`ambient_scale=1.0` 讓
    mean≈38、p50 從 6.4 拉到 24 以上、mean-p50 落差從 23.8 收斂到 18 以內，同時
    practical light 熱點仍明顯是畫面最亮的焦點，沒有被蓋過）。跟
    `auto_frame_and_light()` 的已知限制一樣：這是對單一場景尺度/材質組合校準的基準，
    不保證任何場景都直接命中帶內，建好先跑 CALIB 用 LUMA_STATS（尤其新增的 p50/
    mean-p50 欄位）驗證，不要假設預設值萬用。

    回傳 dict（供 log/斷言用）：`{"bbox_diag": float}`。"""
    bpy.context.view_layer.update()
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    if not objs:
        fail("assertion", "auto_night_fill: objects 不可為空（要傳入全部入鏡場景物件，不是只有主體）")
    xs, ys, zs = [], [], []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    xmin, xmax, ymin, ymax, zmin, zmax = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    center = Vector(((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2))
    diag = Vector((xmax - xmin, ymax - ymin, zmax - zmin)).length
    if diag < 1e-6:
        fail("assertion", "auto_night_fill: 包圍盒對角線接近 0，objects 可能沒有實際幾何")

    # 兩盞大尺寸、低能量、冷中性色的 AREA 補光，從場景上方前側跟後側各打一盞——尺寸
    # 跟強度都用 diag 縮放（同 auto_frame_and_light() 的 diag²距離平方反比校正邏輯），
    # 但常數（fill_const=16）刻意抓得比 product 三點式的 key_const=300 低一個量級以上，
    # 這是「墊底不搶戲」的補光，不是打亮整個場景的主光。
    fill_const = 16.0 * ambient_scale
    lights = []
    for name, ang_h, ang_v, energy_const, size_ratio, color in (
        ("NightFill_Front", math.radians(-125.0), math.radians(50.0), fill_const, 1.6, (0.55, 0.66, 0.95)),
        ("NightFill_Back", math.radians(55.0), math.radians(40.0), fill_const * 0.7, 1.4, (0.60, 0.68, 0.90)),
    ):
        dir_vec = Vector((math.cos(ang_v) * math.cos(ang_h), math.cos(ang_v) * math.sin(ang_h), math.sin(ang_v)))
        loc = center + dir_vec * diag * 1.2
        lights.append((name, tuple(loc), energy_const * (diag ** 2), max(0.3, diag * size_ratio),
                       color, tuple(center)))

    global NIGHT_FILL_OVERRIDE
    NIGHT_FILL_OVERRIDE = {"lights": lights, "bbox_diag": diag}
    log("lighting", f"auto_night_fill: bbox_diag={diag:.2f}m center={tuple(round(c, 2) for c in center)} "
                    f"ambient_scale={ambient_scale}")
    return {"bbox_diag": diag}


def auto_space_fill(objects: list, ambient_scale: float = 1.0) -> dict:
    """真空場景的基礎補光——`auto_night_fill()` 的太空對等版（§10.5）。

    **太空沒有三點式的物理來源**：真空沒有介質散射、沒有大氣、沒有地面反彈，場景裡唯一
    的光源就是那一顆 SUN。所以：

    - 三點式（key/fill/rim）一律 0（`PRESETS["space"]` 已設 0）——**不要用
      `auto_frame_and_light()`**，那支會配三點式，等於在太空裡憑空放了三盞棚燈。
    - 只補兩盞**極弱**的大面積燈，對應兩個真實存在的次要來源：冷藍色的「行星反照／
      深空環境反射」（從下方來，因為那是行星在腳下的反射）與暖色的「太陽在構造邊緣的
      散射」（輪廓光）。
    - 能量常數刻意比 `auto_night_fill()`（fill_const=16）再低一個量級
      （`fill_const=3.0`），並隨 bbox diag² 縮放（同 §15.4 的距離平方反比校正）——
      這支只負責「背光面不要崩成純黑」，不是把場景打亮。

    用法同 `auto_night_fill()`：`subject_fn()` 建完**全部會入鏡的場景物件**後呼叫一次，
    `main()` 跑到 `build_lights()` 時自動讀到覆寫值（`SPACE_FILL_OVERRIDE` 優先於
    `NIGHT_FILL_OVERRIDE`）。回傳 `{"bbox_diag": float}`。
    """
    bpy.context.view_layer.update()
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    if not objs:
        fail("assertion", "auto_space_fill: objects 不可為空（要傳入全部入鏡場景物件，不是只有主體）")
    xs, ys, zs = [], [], []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    xmin, xmax, ymin, ymax, zmin, zmax = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    center = Vector(((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2))
    diag = Vector((xmax - xmin, ymax - ymin, zmax - zmin)).length
    if diag < 1e-6:
        fail("assertion", "auto_space_fill: 包圍盒對角線接近 0，objects 可能沒有實際幾何")

    fill_const = 3.0 * ambient_scale
    lights = []
    for name, ang_h, ang_v, energy_const, size_ratio, color in (
        # 行星反照：來自行星方向（下方）的冷藍環境反射
        ("SpaceFill_Planet", math.radians(-70.0), math.radians(-28.0), fill_const, 2.0, (0.42, 0.56, 0.95)),
        # 太陽散射／輪廓：從主光相對側的高處補一圈暖色邊緣
        ("SpaceFill_Rim", math.radians(125.0), math.radians(42.0), fill_const * 0.8, 1.6, (1.0, 0.86, 0.70)),
    ):
        dir_vec = Vector((math.cos(ang_v) * math.cos(ang_h), math.cos(ang_v) * math.sin(ang_h),
                          math.sin(ang_v)))
        loc = center + dir_vec * diag * 1.3
        lights.append((name, tuple(loc), energy_const * (diag ** 2), max(0.3, diag * size_ratio),
                       color, tuple(center)))

    global SPACE_FILL_OVERRIDE
    SPACE_FILL_OVERRIDE = {"lights": lights, "bbox_diag": diag}
    log("lighting", f"auto_space_fill: bbox_diag={diag:.2f}m center={tuple(round(c, 2) for c in center)} "
                    f"ambient_scale={ambient_scale}（行星反照＋暖色輪廓，三點式保持關閉）")
    return {"bbox_diag": diag}


# 相機固定在世界軸的六個正交角度（無透視畸變，§13.12 D）。角度定義沿用 auto_frame_and_light()
# 同一套 azimuth/elevation 慣例：0°=+X 方向看、90°=垂直俯視、主體正面朝 -Y（§11/§16.1）。
# "left"/"right" 是相機所在的世界軸側（-X/+X），不是「模型解剖學上的左右手」——跟參考照片
# 對照時用世界方位判斷是哪一面，不要用人稱視角套。top 用 89.9° 不用整數 90°，避免
# to_track_quat 在視線正好垂直時 up 向量退化、相機 roll 不穩定（實測驗證見函式內測試）。
_ORTHO_VIEW_ANGLES = {
    "front": (-90.0, 0.0),
    "back": (90.0, 0.0),
    "left": (180.0, 0.0),
    "right": (0.0, 0.0),
    "top": (0.0, 89.9),
}


def render_ortho_views(objects: list, out_dir: str, out_prefix: str = "ortho",
                       views: tuple = ("front", "back", "left", "right", "top"),
                       ortho_margin: float = 1.15, on_view_rendered=None) -> dict:
    """§13.12 D：正交無透視畸變六視圖（不含 bottom，實務很少需要），供評圖跟真實參考
    照片逐項比對用，不是最終成品渲染。

    在主場景（world/lights/材質全部已經建好，通常在 main() 跑完正式渲染之後）呼叫——
    移動場景既有相機到 `_ORTHO_VIEW_ANGLES` 定義的五個精確角度分別重渲，渲染引擎/
    降噪/色彩管理/世界光沿用當前場景設定，不重建；結束後把相機還原回呼叫前的狀態，
    不影響後續任何操作或最終成品相機/構圖。

    **`on_view_rendered(view_name, render_path)` 回呼（2026-09-10 新增，實測抓到的坑）**：
    這支函式結束時會把相機還原，如果需要對某一視角呼叫 `export_label_projections()`
    燒標籤座標，**絕對不能等這支函式整個 return 之後才呼叫**——相機那時已經被還原成
    呼叫前的狀態（通常是主渲染的 3/4 藝術視角），算出來的座標會對應到錯的相機、
    貼到那個視角的圖上位置全部是錯的（2026-09-10 實測踩到：呼叫端各自獨立呼叫
    `render_ortho_views(views=("front",))` 再呼叫 `export_label_projections()`，
    拿到的 JSON 座標其實是原本 3/4 視角算出來的，跟 front 視圖完全對不上，三個
    元件標籤全部貼歪）。正確做法是傳 `on_view_rendered` 回呼，在**相機還停留在該
    視角、還沒被還原**的當下就呼叫 `export_label_projections()`：
        T.render_ortho_views(objs, out_dir,
            on_view_rendered=lambda view, path: T.export_label_projections(
                components, os.path.join(out_dir, f"labels_{view}.json")))

    跟 auto_frame_and_light() 的差異：那支函式的 azimuth/elevation 是為了「好看的
    3/4 藝術視角」，任意角度都會帶有透視畸變（即使是 ORTHO 相機，鏡頭方向本身
    不對著任何一個主軸也會讓輪廓角度跟真實正視圖不同）；這支函式固定在 90° 整數倍
    的軸向角度，才能跟同樣近正面/長焦拍攝的參考照片做逐項位置/比例比對，兩者用途
    不同、不互相取代。

    回傳 {view_name: 檔案路徑}。"""
    scene = bpy.context.scene
    cam = scene.camera
    if cam is None:
        fail("assertion", "render_ortho_views: 場景沒有現有相機，需先跑過 main()/build_camera()")
    orig_loc = cam.location.copy()
    orig_rot = cam.rotation_euler.copy()
    orig_type = cam.data.type
    orig_ortho_scale = cam.data.ortho_scale
    orig_clip_start, orig_clip_end = cam.data.clip_start, cam.data.clip_end

    bpy.context.view_layer.update()
    objs = objects if isinstance(objects, (list, tuple)) else [objects]
    if not objs:
        fail("assertion", "render_ortho_views: objects 不可為空")
    xs, ys, zs = [], [], []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    xmin, xmax, ymin, ymax, zmin, zmax = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    center = Vector(((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2))
    diag = Vector((xmax - xmin, ymax - ymin, zmax - zmin)).length
    if diag < 1e-6:
        fail("assertion", "render_ortho_views: 包圍盒對角線接近 0，objects 可能沒有實際幾何")
    cam_dist = diag * 1.8

    os.makedirs(out_dir, exist_ok=True)
    results = {}
    for view in views:
        if view not in _ORTHO_VIEW_ANGLES:
            fail("config", f"render_ortho_views: 未知視角 '{view}'，可用：{list(_ORTHO_VIEW_ANGLES)}")
        az_deg, el_deg = _ORTHO_VIEW_ANGLES[view]
        az, el = math.radians(az_deg), math.radians(el_deg)
        cam_dir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
        cam_loc = center + cam_dir * cam_dist
        direction = center - cam_loc
        cam.location = cam_loc
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = diag * ortho_margin
        cam.data.clip_start = max(0.001, direction.length * 0.01)
        cam.data.clip_end = max(1000.0, direction.length * 4.0)
        bpy.context.view_layer.update()
        path = os.path.join(out_dir, f"{out_prefix}_{view}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        results[view] = path
        log("render", f"render_ortho_views: {view} (az={az_deg} el={el_deg}) -> {path}")
        if on_view_rendered is not None:
            on_view_rendered(view, path)  # 相機仍在這個視角，還沒還原——見上方 docstring 警告

    cam.location = orig_loc
    cam.rotation_euler = orig_rot
    cam.data.type = orig_type
    cam.data.ortho_scale = orig_ortho_scale
    cam.data.clip_start, cam.data.clip_end = orig_clip_start, orig_clip_end
    bpy.context.view_layer.update()
    return results


def export_label_projections(components: list, out_json_path: str) -> str:
    """§13.12 C：把元件世界座標投影成螢幕像素座標，寫成 JSON 供 `assets/overlay_tools.py`
    （在 Blender 外、一般 Python + Pillow 環境執行，用 run_python_native 或你的 agent
    平台上等價的「執行一段腳本」工具呼叫）讀取後
    疊標籤圖。**畫框/畫字這類點陣圖影像處理不能寫在這支腳本裡**——2026-09-10 實測確認
    Blender 5.1.2 內建 Python（3.13）沒有裝 Pillow（`import PIL` 直接 ModuleNotFoundError），
    這支函式只負責算好投影座標交棒出去，不嘗試在 bpy 環境裡畫圖。

    components: `[(label, point), ...]`——`point` 可以是 `bpy.types.Object`（取其世界
    座標**包圍盒中心**，不是 `matrix_world.translation`：本 skill 的 `add_box()`/
    `add_cyl()` 慣例是建完立刻 `transform_apply()` 把位置烘進網格、物件自身
    `location` 歸零（§14 母版復用段落已記錄這個慣例），對這樣的物件取
    `matrix_world.translation` 一律是 (0,0,0)，2026-09-10 實測直接踩到——三個不同
    位置的元件全部投影到同一個像素點。改用 `obj.bound_box` 經 `matrix_world` 變換
    後取中心點，才是不論物件是否 transform_apply 過都成立的真正世界座標）或世界座標
    tuple/`Vector`（元件形狀不規則、包圍盒中心不代表視覺重點時手動指定，例如一個
    L 形物件的包圍盒中心可能落在物件本體之外）。用場景目前的相機（`scene.camera`）
    跟目前渲染解析度換算，呼叫時機通常緊接在某次 `bpy.ops.render.render()`（或
    `render_ortho_views()` 單一視角）之後，確保 JSON 裡的座標跟當下那張渲染圖是
    同一個相機狀態算出來的。

    畫面外或在相機後方的元件會被排除、不寫進 JSON（呼叫端可比對輸入輸出數量差，知道
    「這個元件在目前這個角度本來就看不到」，不是投影算錯）。

    JSON 結構：`{"width": int, "height": int, "labels": [{"id": str, "px": float,
    "py": float}, ...]}`——px/py 是圖片座標系（原點左上角、Y 向下），直接對應
    PIL 等大多數影像工具的像素座標慣例，不需要呼叫端再轉換。"""
    import bpy_extras.object_utils as object_utils
    scene = bpy.context.scene
    cam = scene.camera
    if cam is None:
        fail("assertion", "export_label_projections: 場景沒有相機")
    W = scene.render.resolution_x
    H = scene.render.resolution_y
    bpy.context.view_layer.update()
    out_labels = []
    skipped = []
    for label, point in components:
        if isinstance(point, bpy.types.Object):
            corners = [point.matrix_world @ Vector(c) for c in point.bound_box]
            wp = sum(corners, Vector((0, 0, 0))) / len(corners)
        else:
            wp = Vector(point)
        co = object_utils.world_to_camera_view(scene, cam, wp)
        if co.z <= 0 or not (0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0):
            skipped.append(str(label))
            continue
        out_labels.append({"id": str(label), "px": co.x * W, "py": (1.0 - co.y) * H})
    data = {"width": W, "height": H, "labels": out_labels}
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log("render", f"export_label_projections: {len(out_labels)}/{len(components)} 個元件在畫面內"
                  f"{f'，畫面外/相機後方略過：{skipped}' if skipped else ''} -> {out_json_path}")
    return out_json_path


# ---------- 鏡面立面仰角定律（建築 hero 鏡頭） ----------
# 垂直鏡面（拋光帷幕牆、玻璃幕、拋光石材）反射時**保留入射光線的仰角**：牆面上高於
# 相機的那一段，反射的是相機上方的天空（明亮）；低於相機的那一段，反射的是相機側的
# 地面（暗）。所以同一棟拋光帷幕大樓，**相機壓低**→立面大面積反射天空、讀起來是明亮
# 銀白；**相機拉高**→立面大部分反射深色地面、整棟渲染成黑石板，材質參數再怎麼調都
# 救不回來（這是幾何/光學問題，不是材質問題；ORTHO 與 PERSP 都適用，正交光線一樣保留
# 仰角）。鏡頭規劃階段先用這組函式把「立面上高於鏡頭的比例」算出來，再決定機位高度。

def mirror_sky_fraction(host, cam_loc=None) -> dict:
    """量測「這個垂直鏡面立面上，高於相機（＝反射天空）的高度比例」（只量測、不判定）。

    host：立面物件（帷幕塔身／玻璃幕／拋光石材牆），量它的世界包圍盒底面/頂面 z。
    cam_loc：相機世界座標；不給就讀 `bpy.context.scene.camera` 目前位置。
    回傳：{"base_z","top_z","cam_z","above_cam_m","frac_above_cam","frac_mirrors_ground"}，
    `frac_above_cam = (top_z - cam_z) / (top_z - base_z)`，夾在 0-1。
    """
    bpy.context.view_layer.update()
    zs = [(host.matrix_world @ Vector(c)).z for c in host.bound_box]
    base_z, top_z = min(zs), max(zs)
    if cam_loc is None:
        cam = bpy.context.scene.camera
        if cam is None:
            fail("assertion", "mirror_sky_fraction: 場景沒有相機，請直接傳 cam_loc")
        cam_loc = tuple(cam.matrix_world.translation)
    cam_z = float(cam_loc[2])
    span = max(1e-6, top_z - base_z)
    frac = max(0.0, min(1.0, (top_z - cam_z) / span))
    return {"base_z": round(base_z, 3), "top_z": round(top_z, 3), "cam_z": round(cam_z, 3),
            "above_cam_m": round(top_z - cam_z, 3), "frac_above_cam": round(frac, 4),
            "frac_mirrors_ground": round(1.0 - frac, 4)}


def assert_mirror_sky_fraction(host, cam_loc=None, min_frac: float = 0.6,
                               label: str = "mirror_facade", hard: bool = False) -> dict:
    """檢查鏡面立面「高於相機的比例」是否足夠（預設門檻 0.6；hard=False 只警告）。

    hard=True 時低於門檻直接 fail（exit 1）——用在「這個鏡頭就是要那面鏡子反射天空」
    的明確意圖下。一般情況用預設 hard=False 取警告即可：不是每個含拋光立面的場景都靠
    立面反光當賣點，遠處小面積反射不影響觀感。
    """
    m = mirror_sky_fraction(host, cam_loc)
    msg = (f"鏡面立面 {host.name}: 高於相機 {m['above_cam_m']}m / 立面全高 "
           f"{round(m['top_z'] - m['base_z'], 3)}m = {m['frac_above_cam']:.0%} 反射天空"
           f"（相機 z={m['cam_z']}m → {m['frac_mirrors_ground']:.0%} 反射地面）")
    if m["frac_above_cam"] < min_frac:
        text = (f"{label}: {msg}——低於門檻 {min_frac:.0%}，立面會以反射深色地面為主、"
                f"讀起來偏暗；把機位壓低到立面高度的 {round((1.0 - min_frac) * 100)}% "
                f"以下再渲")
        if hard:
            fail("assertion", text)
        log("assertion", f"WARNING: {text}")
    else:
        log("assertion", msg)
    return m


# ---------- 構圖入鏡斷言（§15.4；2026-09-11 新增） ----------
# 「主體有沒有完整入鏡、在畫面裡佔多大」用投影數字回答，取代「渲染完肉眼看圖猜」——
# 同一類問題（幾何算錯）不該只能靠肉眼發現，見 §13.9 的自動幾何審查同一套精神。
# 跟 export_label_projections() 的差別：那支只投影元件包圍盒**中心**一點、用途是疊
# 標籤圖；本組投影包圍盒**8 個角點**、用途是判斷「有沒有被構圖裁掉」與「佔比」。
FRAMING_GROUND_NAMES = ("Ground",)   # build_ground() 建的物件名（不是 Env_ 前綴，見該函式）


def mark_framing_exclude(obj: bpy.types.Object) -> None:
    """標記這個物件不列入「主體入鏡」審查（2026-09-11 新增）。
    用途同 mark_side_attached()：T.main() 的自動構圖審查對全部 mesh 物件無差別掃描，
    但「刻意延伸到畫面外」的物件（背景城市量體、遠景色塊、純參考量體）被算進來會製造
    假警報。建構這類物件時當下呼叫一次，不必在 main() 端維護排除清單。"""
    obj["_framing_exclude"] = True


def _is_environment_obj(obj) -> bool:
    """地面/環境件不算「主體」——它們本來就該鋪滿或超出畫面。規則：build_ground()
    建的 'Ground' 物件、§16.2 命名公約的 'Env_' 前綴環境件、或呼叫端用
    mark_framing_exclude() 標記過的物件。"""
    return (bool(obj.get("_framing_exclude")) or obj.name in FRAMING_GROUND_NAMES
            or obj.name.startswith("Env_"))


def frame_coverage(objects: list | None = None, margin: float = 0.02) -> dict:
    """量測「一組物件在目前相機畫面裡的位置與佔比」（只量測、不判定，2026-09-11 新增）。

    把每個物件世界包圍盒的 8 個角點用 `bpy_extras.object_utils.world_to_camera_view()`
    投影進相機 NDC（u/v 各落在 0~1 表示在畫面內），回報聯集範圍與覆蓋率。呼叫時機必須
    在 `build_camera()`（scene.camera 就位）與 `setup_render()`（畫幅比定案，NDC 的 u 軸
    隨 aspect 縮放）之後。

    `objects=None` 自動取全部「可渲染且非環境件」的 mesh 物件（見 `_is_environment_obj()`）
    ——把涵蓋整個畫面的大地面也算進主體桶，會讓每個鏡頭都回報「主體超出畫面」的假警報，
    預設就把地面排除。

    回傳 dict：`objects`（數量）、`u_range`/`v_range`（投影聯集範圍）、`coverage`
    （裁到 [0,1] 後的面積比，0.5 = 主體佔畫面一半）、`fits`（沒有角點落在
    `[-margin, 1+margin]` 之外、也沒有角點在相機後方）、`behind_camera`、
    `outside_count`、`outside`（物件名清單）。無有效投影點時 `u_range`/`v_range`
    為 None、`coverage` 為 0.0。
    """
    import bpy_extras.object_utils as object_utils
    scene = bpy.context.scene
    cam = scene.camera
    if cam is None:
        fail("framing", "frame_coverage: 場景沒有相機（須在 build_camera() 之後呼叫）")
    if objects is None:
        objects = [o for o in bpy.data.objects
                   if o.type == "MESH" and not o.hide_render and not _is_environment_obj(o)]
    bpy.context.view_layer.update()
    us, vs = [], []
    behind, outside = [], []
    for obj in objects:
        obj_out = False
        for corner in obj.bound_box:
            co = object_utils.world_to_camera_view(scene, cam, obj.matrix_world @ Vector(corner))
            if co.z <= 0.0:
                obj_out = True
                if obj.name not in behind:
                    behind.append(obj.name)
                continue
            us.append(co.x)
            vs.append(co.y)
            if not (-margin <= co.x <= 1.0 + margin and -margin <= co.y <= 1.0 + margin):
                obj_out = True
        if obj_out and obj.name not in behind and obj.name not in outside:
            outside.append(obj.name)
    if not us:
        return {"objects": len(objects), "u_range": None, "v_range": None, "coverage": 0.0,
                "fits": False, "behind_camera": behind, "outside_count": len(objects),
                "outside": outside}
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    coverage = (max(0.0, min(1.0, u1) - max(0.0, u0)) * max(0.0, min(1.0, v1) - max(0.0, v0)))
    return {"objects": len(objects), "u_range": (round(u0, 3), round(u1, 3)),
            "v_range": (round(v0, 3), round(v1, 3)), "coverage": round(coverage, 4),
            "fits": (not behind and not outside),
            "behind_camera": behind, "outside_count": len(outside), "outside": outside}


def audit_framing(objects: list | None = None, min_coverage: float = 0.02,
                  margin: float = 0.02) -> dict:
    """構圖審查：`frame_coverage()` 的量測結果 ＋ `issues` 問題清單（**不直接 fail**，
    語意同 audit_interpenetration/audit_floating 家族，由呼叫端決定 hard/soft）。

    兩個判準：① 主體有角點落在畫面外或相機後方（構圖裁切／相機根本沒對準主體）；
    ② 覆蓋率低於 `min_coverage`（主體在畫面裡太小，多半是相機沒有依主體實際 bbox
    重新校準——§15.4 auto_frame_and_light() 的職責）。預設 `min_coverage=0.02`
    （畫面 2%）是刻意寬鬆的下限，只抓「明顯算錯」，不是抓美感。"""
    m = frame_coverage(objects, margin=margin)
    issues = []
    if m["behind_camera"]:
        issues.append(f"有 {len(m['behind_camera'])} 個主體物件的包圍盒角點落在相機後方"
                      f"（{', '.join(m['behind_camera'][:5])}）——相機沒對準主體？")
    elif m["outside_count"]:
        issues.append(f"有 {m['outside_count']} 個主體物件的包圍盒角點落在畫面外"
                      f"（{', '.join(m['outside'][:5])}）——主體被構圖裁切")
    if m["coverage"] < min_coverage:
        issues.append(f"主體只佔畫面 {m['coverage'] * 100:.1f}% < 下限 "
                      f"{min_coverage * 100:.1f}%——在畫面裡太小，檢查相機是否依主體"
                      f"實際包圍盒重新校準（§15.4）")
    m["issues"] = issues
    return m


def assert_in_frame(objects: list | None = None, min_coverage: float = 0.02,
                    max_coverage: float = 1.0, margin: float = 0.02,
                    label: str = "主體", hard: bool = True) -> dict:
    """主體入鏡斷言（§15.4；2026-09-11 新增）：`hard=True`（預設）問題清單非空即 exit 1。

    跟 audit_* 家族的差別：這裡的判準是「相機有沒有算對」，不是「自動發現未知問題」，
    所以跟 `assert_slope_angle()`/`assert_within_radius()` 同級、預設就擋。T.main() 的
    自動審查走 soft 版 `audit_framing()`（只寫進 SCENE_STATE 不擋渲染）。

    `max_coverage` 預設 1.0（不設上限）；要表達「主體不該塞滿畫面、要留白」的構圖
    意圖時由呼叫端調低（例如 0.75）。"""
    m = audit_framing(objects, min_coverage=min_coverage, margin=margin)
    if m["coverage"] > max_coverage:
        m["issues"].append(f"{label}佔畫面 {m['coverage'] * 100:.1f}% > 上限 "
                           f"{max_coverage * 100:.1f}%（留白不足）")
    for line in m["issues"]:
        log("framing", f"ISSUE: {line}")
    if hard and m["issues"]:
        fail("framing", f"{label} 入鏡斷言失敗：{'；'.join(m['issues'])}")
    log("framing", f"{label} 入鏡檢查：coverage={m['coverage'] * 100:.1f}% "
                   f"u={m['u_range']} v={m['v_range']} fits={m['fits']}")
    return m


def assert_disc_in_frame(disc, cam=None, label: str = "日盤", margin: float = 0.0,
                         hard: bool = True) -> dict:
    """日盤入鏡斷言（§10.5）：把日盤球心的世界座標投影進相機 NDC，判它是否落在畫面內。

    太空場景的太陽是**刻意擺上去的視覺錨點**，不是背景裝飾——沒入鏡就等於這張圖沒有
    太陽（逆光、鏡面高光、鏡頭光暈的整個敘事都不成立），所以這是斷言而不是警告
    （`hard=True` 預設：未入鏡即 exit 1）。

    判準：球心投影在畫面內、且球體與畫面有交集（用視半徑換算成 NDC 半徑再判斷，
    所以「球心剛好出界但球體還有一半在畫面裡」算入鏡）。`margin` 可為負＝要求離邊緣
    至少這麼多 NDC（例如 -0.05 表示日盤要留在邊界內 5%）。

    `cam` 不給就用 `scene.camera`——必須在 `build_camera()` 之後呼叫（相機是 `main()`
    內部才建的，`subject_fn()` 當下場景裡還沒有相機）。
    """
    from bpy_extras import object_utils
    scene = bpy.context.scene
    cam = cam or scene.camera
    if cam is None:
        fail("framing", "assert_disc_in_frame: 場景沒有相機（需在 build_camera() 之後呼叫）")
    bpy.context.view_layer.update()
    center = disc.matrix_world.translation
    co = object_utils.world_to_camera_view(scene, cam, center)
    radius = max(disc.dimensions.x, disc.dimensions.y) * 0.5
    if cam.data.type == "ORTHO":
        half_w = cam.data.ortho_scale * 0.5
    else:
        dist = (center - cam.matrix_world.translation).length
        half_w = dist * math.tan(cam.data.angle * 0.5) if dist > 1e-9 else 1.0
    r_ndc = radius / half_w if half_w > 1e-9 else 0.0
    in_frame = bool(co.z > 0.0
                    and (co.x + r_ndc) > (0.0 - margin) and (co.x - r_ndc) < (1.0 + margin)
                    and (co.y + r_ndc) > (0.0 - margin) and (co.y - r_ndc) < (1.0 + margin))
    info = {"disc": disc.name, "ndc": [round(co.x, 4), round(co.y, 4)],
            "ndc_radius": round(r_ndc, 4), "behind_camera": bool(co.z <= 0.0),
            "in_frame": in_frame}
    log("framing", f"{label}入鏡檢查：{disc.name} ndc=({co.x:.3f},{co.y:.3f}) r={r_ndc:.3f} "
                   f"in_frame={in_frame}")
    if hard and not in_frame:
        fail("framing", f"{label} 不在畫面內（ndc={info['ndc']} r={info['ndc_radius']}）——"
                        "太空場景的日盤是視覺錨點，沒入鏡＝這張圖沒有太陽："
                        "調整 sun_elev_deg/sun_azim_deg 或相機構圖後重跑")
    return info


def setup_render(p: dict, render_path: str) -> bool:
    """Cycles CPU + 降噪 + AgX + 合成器 Bloom（5.1 API：node_groups + compositing_node_group，
    Glare 參數是 input sockets、枚舉含空格——skill §8 #4/#5/#6）。回傳 bloom 是否掛上。

    `set_engine("eevee")` 時改走 EEVEE 佈局預覽（樣本數用 `EEVEE_SAMPLES`、跳過
    Cycles 專屬設定）——適用範圍與三個限制見 `set_engine()` docstring。AgX 色調映射、
    合成器 Bloom、畫幅、輸出格式兩個引擎共用（曝光曲線一致，但 EEVEE 的 GI/降噪
    不同，LUMA 數值仍不可互相比較）。"""
    scene = bpy.context.scene
    if ENGINE == "eevee":
        scene.render.engine = "BLENDER_EEVEE"   # 5.1：enum 僅此一值（無 _NEXT，實測）
        scene.eevee.taa_render_samples = EEVEE_SAMPLES
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"  # Intel Arc B370 Cycles GPU 支援有限，一律 CPU
        scene.render.threads_mode = "FIXED"
        scene.render.threads = MAX_RENDER_THREADS  # 上限 6，不吃滿全部核心（見上方 CONFIG 註解）
        scene.cycles.samples = RENDER_SAMPLES
        scene.cycles.use_denoising = True
    scene.render.resolution_x = RENDER_RES[0]
    scene.render.resolution_y = RENDER_RES[1]
    scene.render.filepath = render_path
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = VIEW_TRANSFORM
    if VIEW_TRANSFORM == "AgX":
        scene.view_settings.look = "AgX - Punchy"  # 5.1：AgX look 枚舉帶前綴（skill §8 #2）
    # 非 AgX（3 渲 2 用 'Standard'）沒有 AgX look，維持預設 'None'——硬塞會 TypeError
    try:
        cnt = bpy.data.node_groups.new("TemplateBloom", "CompositorNodeTree")
        scene.compositing_node_group = cnt
        cnt.nodes.clear()
        cnt.interface.new_socket("Image", socket_type="NodeSocketColor", in_out="OUTPUT")
        rl = cnt.nodes.new("CompositorNodeRLayers")
        glare = cnt.nodes.new("CompositorNodeGlare")
        glare.inputs["Type"].default_value = "Fog Glow"
        # 5.1 實測：Glare 的 Size 是 0–1 的 FACTOR，**賦值不夾、評估時飽和**——≥1 的值
        # 一律覆蓋整張圖（studio 5／outdoor_golden 7／night 9 三組渲出的統計逐位元相同），
        # 這個旋鈕在那些配方上形同常數。這裡主動夾到 1.0 並在超標時出聲，避免「調了
        # size 但畫面完全沒變」的無效迭代（見 §8 落差表）。
        if float(p["bloom_size"]) >= 1.0:
            log("compositor", f"WARNING: bloom_size={p['bloom_size']} ≥ 1 已在飽和區"
                              "（Glare Size 是 0–1 的 FACTOR，≥1 一律覆蓋整張圖）——"
                              "要縮小暈染請填 <1 的值（例如 0.25）")
        glare.inputs["Size"].default_value = min(1.0, float(p["bloom_size"]))
        glare.inputs["Threshold"].default_value = p["bloom_threshold"]
        comp = cnt.nodes.new("NodeGroupOutput")
        cnt.links.new(rl.outputs["Image"], glare.inputs["Image"])
        cnt.links.new(glare.outputs["Image"], comp.inputs["Image"])
        log("compositor", f"Bloom 啟用（threshold={p['bloom_threshold']}, size={p['bloom_size']}）")
        return True
    except Exception as exc:  # noqa: BLE001
        log("compositor", f"WARNING: 合成器設定失敗，跳過 Bloom: {exc}")
        return False


def luma_stats(render_path: str) -> dict:
    """讀回渲染 PNG 算亮度統計（Blender 內嵌 numpy 實測可用）。"""
    import numpy as np
    img = bpy.data.images.load(render_path)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    lum8 = np.clip(lum * 255.0, 0, 255)
    stats = {
        "mean": round(float(lum8.mean()), 1),
        "p1": round(float(np.percentile(lum8, 1)), 1),
        "p50": round(float(np.percentile(lum8, 50)), 1),
        "p99": round(float(np.percentile(lum8, 99)), 1),
        "clipped_pct": round(float((lum8 >= 250).mean() * 100), 2),
        "dark_pct": round(float((lum8 <= 10).mean() * 100), 2),
    }
    bpy.data.images.remove(img)
    return stats


def check_exposure(stats: dict, p: dict) -> list:
    """亮度統計 vs 配方目標帶；回傳違規清單（空=通過）。"""
    problems = []
    lo, hi = p["luma_band"]
    if not (lo <= stats["mean"] <= hi):
        direction = "過曝" if stats["mean"] > hi else "過暗"
        problems.append(f"mean={stats['mean']} 不在目標帶 {lo}-{hi}（{direction}）")
    if stats["clipped_pct"] > p["clipped_max"]:
        problems.append(f"高光 clipping {stats['clipped_pct']}% > 上限 {p['clipped_max']}%")
    if stats["dark_pct"] > p["dark_max"]:
        problems.append(f"死黑面積 {stats['dark_pct']}% > 上限 {p['dark_max']}%")
    # 2026-09-11 新增（拉麵屋台夜景事故）：mean/dark_pct 各自「合格」，仍可能是「少數
    # practical light 熱點（燈籠/招牌）把平均值撐高，畫面其餘大部分仍接近全黑」的假
    # 通過——dark_pct 的單一二元門檻（像素是否 ≤10）看不出這種分佈形狀，p50（中位數）
    # 才會。實測案例：mean=30.2（落在 night 帶 15-70 內）、dark_pct=59.4%（低於當時
    # 70% 上限）雙雙「通過」，但 p50=6.4（中位數幾乎純黑，代表過半像素接近全黑）、
    # 飽和度量測只有 0.058／1.0，肉眼看渲染圖是「只有燈籠/招牌亮，其餘完全看不到任何
    # 東西」——mean 被小範圍熱點拉高不代表「畫面大部分看得見」，兩者是不同的訊號。
    # 只對夜景生效（preset 給了 p50_gap_max 才檢查）：這道門檻描述的是「光源覆蓋
    # 不足」，棚拍深色背景 + 明亮主體、戶外天空 + 地面陰影本來就會產生大落差，
    # 對它們套用等於把正常構圖判成缺陷。
    gap_max = p.get("p50_gap_max")
    gap = stats["mean"] - stats["p50"]
    if gap_max is not None and gap > gap_max:
        problems.append(f"mean({stats['mean']}) 遠高於中位數 p50({stats['p50']})，"
                        f"差距 {gap:.1f} > {gap_max}——像是「少數熱點撐高平均值、大部分範圍"
                        f"仍接近全黑」而不是均勻的夜景氛圍，檢查 practical light／"
                        f"auto_night_fill() 覆蓋範圍是否真的照到鏡頭看得到的整個場景，"
                        f"不是只照到主體附近")
    return problems


def audit_band_count(render_path: str, max_bands: int = 4, min_share: float = 0.01,
                     quant_step: int = 16, roi: tuple | None = None) -> dict:
    """色階數審計（2026-09-13 新增）：數「這張圖有幾個有效色塊」——3 渲 2／賽璐璐
    判定成品合格的主指標（見 `styles/genre/anime-cel-daylight.md`、`set_view_transform()`）。

    做法：每像素 RGB 量化到每通道 `quant_step` 階，統計各色格佔比，佔比 ≥ `min_share`
    的色格才算「一個色階」。回傳 `bands`（階數）、`top`（各階代表色 hex ＋ 佔比）與
    `issues`（階數 > `max_bands` 時的描述）。**soft 審計，不直接 fail**，語意同
    `audit_framing()`/`audit_interpenetration()` 家族，由呼叫端決定 hard/soft。

    `roi=(x0, y0, x1, y1)`：歸一化座標（0-1、原點在**左下**、符合 Blender 像素列序），
    只審計該矩形，預設 None＝全畫面。`roi` 完全落在畫面外時 fail fast（exit 1）。

    **實測基準（Blender 5.1.2 headless EEVEE、260x190、單一 SUN、`min_share=0.01`）**：
      - 單一 cel 材質填滿畫面：**3 階**（#E8E8D8 69.8%／#A8B8D8 18.6%／#F8E8D8 6.9%）
        ——正是風格卡說的「明暗階數上限 3」；`max_bands=4` 這個預設值就是對這種構圖的判準。
      - 三材質（牆／招牌／路面）小場景：**5 階**——**階數會隨材質數成長**，多材質街景
        不該照 `max_bands=4` 判死：要嘛按「材質數 × 明暗階數」上調 `max_bands`，要嘛
        傳 `roi` 只量單一表面（實測只量畫面右半 → 4 階）。
      - 程序化寫實材質（`make_concrete` 的 noise/bump）：**7 階**（`min_share=0.05` 仍 5 階）
        ——**紋理污染抓得到**，這是本審計真正能攔的錯。
      - 同構圖換成 flat PBR（Principled 平面）：5 階——**「階數不超標」不等於「材質路線
        正確」**，平面幾何本來就不會爆階，兩件事要分開驗。

    **本函式抓不到的事（重要）**：階數對**色調映射**不敏感——同一個 cel 場景 AgX vs
    Standard 實測**都是 5 階**（AgX 是逐像素曲線，平塗色塊還是平塗），但代表色 hex 從
    #E84828 變 #C84838（「色票一比一」被破壞）。**要驗 AgX 誤用必須比對 `top[].hex` 與
    風格卡色票**，只看 `bands` 會漏掉；同理本函式只量「階數多寡」，不驗色相正確性。

    已知限制：反鋸齒邊緣與 Freestyle 描邊線產生的小佔比色格靠 `min_share` 濾掉；兩色
    漸層天空（`add_stylized_sky()`）實測在 260x190 只佔 1 個量化格、沒有額外拉高階數。
    判讀前先確認 `max_bands` 對不對得上這個場景的材質數，再用 `issues` 下判斷。
    """
    import numpy as np
    img = bpy.data.images.load(render_path)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    if roi is not None:
        x0, y0, x1, y1 = roi
        c0, c1 = int(round(min(x0, x1) * w)), int(round(max(x0, x1) * w))
        r0, r1 = int(round(min(y0, y1) * h)), int(round(max(y0, y1) * h))
        c0, r0 = max(c0, 0), max(r0, 0)
        c1, r1 = min(c1, w), min(r1, h)
        arr = arr[r0:r1, c0:c1]
    if arr.size == 0:
        fail("band_audit", f"roi={roi} 落在畫面外（{w}x{h}），沒有可審計的像素")
    rgb8 = np.clip(arr[..., :3] * 255.0, 0, 255).astype(np.uint8)
    q = (rgb8 // quant_step).astype(np.uint32)
    packed = (q[..., 0] << 16) | (q[..., 1] << 8) | q[..., 2]
    uniq, counts = np.unique(packed, return_counts=True)
    total = int(counts.sum())
    top = []
    half = quant_step // 2
    for i in np.argsort(counts)[::-1]:
        share = counts[i] / total
        if share < min_share:
            break
        r, g, b = int(uniq[i] >> 16), int((uniq[i] >> 8) & 0xFF), int(uniq[i] & 0xFF)
        rep = (r * quant_step + half, g * quant_step + half, b * quant_step + half)
        top.append({"rgb": list(rep), "hex": "#%02X%02X%02X" % rep,
                    "pct": round(float(share) * 100, 2)})
    issues = []
    if len(top) > max_bands:
        issues.append(f"有效色階數 {len(top)} > 上限 {max_bands}（佔比 ≥{min_share * 100:.0f}% "
                      f"的色格）——3 渲 2 的**單一材質**明暗階數上限是 3（例外 4），但階數"
                      f"會隨材質數成長（實測：單一 cel 材質 3 階、三材質小場景 5 階、程序化"
                      f"寫實材質 7 階）。先確認這個場景的材質數對不對得上 max_bands，或改傳 "
                      f"roi 只量單一表面；階數明顯爆量通常代表打光把平面感打散了，或混進了"
                      f"程序化寫實紋理材質（見 styles/genre/anime-cel-daylight.md）")
    return {"bands": len(top), "max_bands": max_bands, "min_share": min_share,
            "quant_step": quant_step, "roi": list(roi) if roi else None,
            "top": top, "issues": issues, "render": render_path}


def audit_horizon_surfaces(objects: list | None = None, cam=None, min_up_dot: float = 0.85,
                           max_view_angle_deg: float = 15.0, min_span_frac: float = 0.15) -> dict:
    """假地平線**前置**審查（真空／太空場景，§10.5）——渲染前就跑，不必等渲完看圖。

    真空場景的假地平線不會憑空出現：它一定來自一個**朝上的面**（世界法線 `n.z` ≥
    `min_up_dot`）以接近平行的視角（視角 ≤ `max_view_angle_deg`）出現在畫面裡，邊緣
    在畫面上變成一條平直亮線。這支把這種面找出來，並回報它投影到畫面後的水平跨度。

    三個判準同時成立才列入：① 面是朝上的（`n.z ≥ min_up_dot`）；② 掠射角入鏡
    （面中心到相機的方向與面法線夾角，偏離 90° 的值 ≤ `max_view_angle_deg`）；
    ③ 投影跨度 ≥ `min_span_frac`（畫面寬比例，小零件不算）。

    **不要用「材質已經夠暗/夠霧面」來放行**：掠射角的 Fresnel 反射率對任何材質都趨近 1，
    實測把底座換成 base 0.03／roughness 0.8 的暗霧面烤漆、並關掉全部補光之後，底座頂面
    仍然把太陽打成一道亮邊（亮度跳躍 20–23/255、橫向連續 49% 畫面寬，審計照樣攔下來）——
    亮度來自掠射高光，不是漫反射，所以「改暗改霧面」單獨用是**無效的修法**。有效的只有
    三條：① 把這個面移出畫面／直接不要它（太空場景本來就不需要底座撐物件）；② 把該面
    的 Specular IOR Level 設 0（連 Fresnel 一起關掉，純漫反射自然壓暗）；③ 讓相機不再
    以掠射角看它（改變機位，不是改材質）。

    `objects` 預設 None＝掃描全部 MESH 物件；`Ground`／`Env_` 前綴／`mark_framing_exclude()`
    標記過的物件自動排除（地面走 `set_ground_void()`，環境件不是畫面主體）。回傳
    `{"issues", "candidates", "scanned", "camera", "objects_skipped"}`，**soft，不直接
    fail**（語意同 audit_* 家族）。

    跟 `audit_horizon_line()` 是互補的兩道：這支**便宜、渲染前就攔**；那支看得到真實像素、
    但要等渲完，且能抓到「非掠射角但一樣亮」的橫向亮邊。兩支都跑最穩。
    """
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    cam = cam or scene.camera
    if cam is None:
        return {"issues": ["假地平線前置審查：場景裡沒有相機，無法投影"], "candidates": [],
                "scanned": 0, "camera": None, "objects_skipped": 0}
    if objects is None:
        objects = [o for o in scene.objects if o.type == "MESH"]
    skipped = 0
    candidates, issues = [], []
    for obj in objects:
        if obj.type != "MESH" or _is_environment_obj(obj):
            skipped += 1
            continue
        mw = obj.matrix_world
        nmat = mw.to_3x3()
        worst = None
        for poly in obj.data.polygons:
            n = (nmat @ poly.normal)
            if n.length < 1e-9:
                continue
            n = n.normalized()
            if n.z < min_up_dot:
                continue
            co = [mw @ obj.data.vertices[i].co for i in poly.vertices]
            center = sum(co, Vector((0.0, 0.0, 0.0))) / len(co)
            to_cam = (cam.matrix_world.translation - center)
            if to_cam.length < 1e-6:
                continue
            view_angle = abs(90.0 - math.degrees(n.angle(to_cam)))
            if view_angle > max_view_angle_deg:
                continue
            ndc = [world_to_camera_view(scene, cam, p) for p in co]
            inside = [(u, v) for u, v, _d in ndc if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0]
            if len(inside) < 2:
                continue
            us = [u for u, _v in inside]
            span = max(us) - min(us)
            if span < min_span_frac:
                continue
            area = 0.0
            for k in range(1, len(co) - 1):                 # 扇形切面積（世界座標，m²）
                area += (co[k] - co[0]).cross(co[k + 1] - co[0]).length * 0.5
            cand = {"object": obj.name, "area_m2": round(area, 3), "n_z": round(n.z, 3),
                    "view_angle_deg": round(view_angle, 2), "span_frac": round(span, 3)}
            if worst is None or cand["span_frac"] > worst["span_frac"]:
                worst = cand
        if worst is not None:
            candidates.append(worst)
            issues.append(
                f"{worst['object']} 有一個朝上平面（{worst['area_m2']}m²）以 "
                f"{worst['view_angle_deg']:.1f}° 掠射角入鏡、水平跨畫面 "
                f"{worst['span_frac'] * 100:.0f}%——真空場景裡它的邊緣會把太陽打成一道平直"
                f"亮線、讀成地平線。掠射 Fresnel 對任何材質都趨近 1，改材質沒有用；修法是"
                f"移出畫面/不要這個面、把 Specular IOR Level 設 0，或改變機位（見 §10.5）")
    return {"issues": issues, "candidates": candidates, "scanned": len(objects),
            "camera": cam.name, "objects_skipped": skipped}


def audit_horizon_line(render_path: str, max_jump: float = 20.0, min_run_frac: float = 0.22,
                       edge_margin: float = 0.02, merge_rows: int = 4) -> dict:
    """假地平線審計（真空／太空場景，§10.5）——抓「畫面裡一條橫向亮邊把星空切斷」。

    判準（兩個條件同時成立才算，避免星點/物件高光被誤判成一條線）：① 某一列的平均亮度
    與相鄰列差 ≥ `max_jump`（0-255）；② 亮的那一側在同一列上有連續 ≥ `min_run_frac ×
    畫面寬` 的像素同時高於「暗側均值 + 0.6 × 跳躍量」。相鄰列（`merge_rows` 內）合併成
    同一個事件，回報最嚴重那列的位置、跳躍量與橫向連續比例。畫面上下緣 `edge_margin`
    以內不採計（畫框本身不是假地平線）。

    **為什麼需要它**：`set_ground_void()` 只管 `Ground` 這個物件；**主體自帶的底座/平台
    不在它的守備範圍**，而以掠射角入鏡的近水平面，其邊緣亮度可以到背景的 10 倍以上
    （實測：背景 12/255 vs 平台亮邊 215/255），肉眼讀成地平線、把雲狀銀河帶切斷。

    回傳 `{"issues", "events", "worst", "size", "max_jump", "min_run_frac", "render"}`，
    **soft，不直接 fail**。`main()` 在 `PRESET == "space"` 時自動跑一次並印 `HORIZON_AUDIT:`
    一行、寫進 `SCENE_STATE.horizon_audit`；其他 preset 不跑（一般場景的地板/平台入鏡
    本來就是正常的）。要當硬性關卡就自行檢查 `issues` 或呼叫端自己 raise。
    """
    import numpy as np
    img = bpy.data.images.load(render_path)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    # 影像列序是 bottom-up（row 0 = 畫面底部）：回報前換算成「離畫面頂端幾 %」，
    # 跟人看圖的直覺一致。
    lum = np.clip(arr[..., :3].mean(axis=2) * 255.0, 0.0, 255.0)
    row_mean = lum.mean(axis=1)
    lo, hi = int(round(edge_margin * h)), h - int(round(edge_margin * h))
    events, i = [], max(1, lo)
    while i < min(h, hi):
        d = float(row_mean[i] - row_mean[i - 1])
        if abs(d) >= max_jump:
            bright_row = i if d > 0 else i - 1
            dark_mean = float(row_mean[i - 1] if d > 0 else row_mean[i])
            mask = lum[bright_row] > (dark_mean + 0.6 * abs(d))
            best = run = best_start = start = 0
            for k in range(w):
                if mask[k]:
                    if run == 0:
                        start = k
                    run += 1
                    if run > best:
                        best, best_start = run, start
                else:
                    run = 0
            if best >= min_run_frac * w:
                events.append({
                    "y_frac": round(1.0 - bright_row / float(h - 1), 3),
                    "jump": round(abs(d), 1),
                    "run_frac": round(best / float(w), 3),
                    "run_x": [round(best_start / float(w - 1), 3),
                              round((best_start + best - 1) / float(w - 1), 3)],
                    "dark_side_mean": round(dark_mean, 1),
                    "bright_side_mean": round(float(row_mean[bright_row]), 1),
                })
                i += merge_rows            # 同一條線的相鄰列不重複回報
                continue
        i += 1
    issues = [
        f"畫面 y={e['y_frac'] * 100:.1f}% 處有一條橫向亮邊：亮度跳躍 {e['jump']:.0f}/255、"
        f"橫向連續 {e['run_frac'] * 100:.0f}% 畫面寬（暗側 {e['dark_side_mean']:.0f} → 亮側 "
        f"{e['bright_side_mean']:.0f}）——真空場景裡這會讀成地平線、把銀河帶切斷。修法：把"
        f"造成它的近水平面改暗改霧面或移出畫面（見 §10.5）" for e in events]
    worst = max(events, key=lambda e: e["jump"] * e["run_frac"]) if events else None
    return {"issues": issues, "events": events, "worst": worst, "size": [w, h],
            "max_jump": max_jump, "min_run_frac": min_run_frac, "render": render_path}


# ---------- 元件表拆解深度閘門（§11 Stage A item 3 / §16.9.5 規則 7） ----------
# §11 把「元件表遞迴拆到 LEVEL 6」寫成 MUST，但它原本是整份 skill 裡唯一一條純靠自律的
# MUST——亮度有 LUMA 帶、方向有語義斷言、細節有密度審計，全部都會 exit 1，只有規劃深度
# 沒有任何一道程式關卡。後果是場景照樣交出 252 物件 / 8 母版、元件深度卻停在 L2–L3 的
# 成果，而沒有東西會攔。這裡把閘門補上：元件表路徑宣告在 `BLENDER_COMPONENTS_JSON`
# （或呼叫 `set_components_json()`），`main()` 在建場景之前先跑一次，深度不足即 exit 1。
# **這道檢查只讀 JSON，不需要 calib／三視圖**——所以原創設計類（§16.9.0 B 類，沒有參考圖
# 可量、被 triview 明文排除）也走得到，不會再被「triview 不適用」擋在門外。
COMPONENTS_JSON: str | None = os.environ.get("BLENDER_COMPONENTS_JSON") or None
# 原創設計類的期望深度＝§11 的六級。元件天然拆不到那麼深的表，用 `depth_exempt` 寫理由
# （不要為了湊層級硬造不存在的子零件）。
MIN_COMPONENT_LEVEL = 6


def set_components_json(path: str | None) -> None:
    """宣告本任務的元件表路徑（§11 Stage A item 3）。場景包 build.py 在 `main()` 前呼叫。"""
    global COMPONENTS_JSON
    COMPONENTS_JSON = path or None


def audit_component_depth(components_path: str,
                          min_level: int = MIN_COMPONENT_LEVEL) -> dict:
    """元件表拆解深度審計（§11 Stage A item 3）——**不需要 calib／三視圖**。

    回傳 `{"path", "min_level", "component_count", "level_histogram", "max_level",
    "depth_exempt", "problems"}`；`problems` 非空＝深度不足或表讀不到。吃 §16.9.4 的
    `components/2`（也接受純 list），只看得懂 `level` 與 `depth_exempt` 兩個欄位——
    視圖覆蓋/參數可查性/外觀規格那些檢查仍由 component_lib 負責，不在這裡重做。
    """
    result = {"path": components_path, "min_level": min_level, "component_count": 0,
              "level_histogram": {}, "max_level": 0, "depth_exempt": [], "problems": []}
    try:
        with open(components_path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        result["problems"].append(f"元件表無法讀取（{components_path}）：{exc}")
        return result
    comps = doc.get("components") if isinstance(doc, dict) else doc
    if not isinstance(comps, list) or not comps:
        result["problems"].append(
            f"元件表沒有任何元件（{components_path}）——§11 Stage A item 3 要求層級式元件表")
        return result
    hist, exempt, exempt_ignored = {}, [], []
    for c in comps:
        if not isinstance(c, dict):
            continue
        lv = c.get("level")
        if isinstance(lv, int) and not isinstance(lv, bool):
            hist[lv] = hist.get(lv, 0) + 1
    max_level = max(hist) if hist else 0
    # 豁免只認「最深那一層」的元件（判準與 component_lib.audit_depth() 一致——本檔會被
    # 單獨複製到任務目錄、不能 import component_lib，所以這裡是刻意的第二份實作，
    # 改動時兩邊要同步）。淺層元件寫 depth_exempt 不計入放行，只記進返回值的
    # depth_exempt_ignored 供查核。
    for c in comps:
        if not isinstance(c, dict) or not str(c.get("depth_exempt", "") or "").strip():
            continue
        lv = c.get("level")
        if max_level and isinstance(lv, int) and not isinstance(lv, bool) and lv == max_level:
            exempt.append(str(c.get("id", "?")))
        else:
            exempt_ignored.append(str(c.get("id", "?")))
    result.update(component_count=len(comps),
                  level_histogram={str(k): hist[k] for k in sorted(hist)},
                  max_level=max_level, depth_exempt=exempt,
                  depth_exempt_ignored=exempt_ignored)
    if max_level < min_level and not exempt:
        result["problems"].append(
            f"元件表最深只到 LEVEL {max_level}（< {min_level}）：拆解深度不足——"
            "元件表拆到多細，直接決定後面能逐件校正到多細；把大元件底下的小元件"
            "（按鈕/墊片/螺絲/密封件…）遞迴拆出來，或在意義上確實拆不動的元件上寫 "
            "`depth_exempt` 說明理由")
    return result


def assert_component_depth(components_path: str, min_level: int = MIN_COMPONENT_LEVEL,
                           label: str = "component_depth", hard: bool = True) -> dict:
    """深度閘門的硬性關卡版：`hard=True`（預設）有問題即 exit 1。

    自動接線見 `main()`（宣告了 `COMPONENTS_JSON` 就會跑）；場景包 `verify_scene()` 若
    要自己再跑一次，直接呼叫這支即可（同一份真相源，重跑無副作用）。
    """
    result = audit_component_depth(components_path, min_level=min_level)
    if result["problems"]:
        msg = (f"{label}: " + "；".join(result["problems"])
               + f"（元件表 {components_path}，最深 LEVEL {result['max_level']}）")
        if hard:
            fail("component_depth", msg)
        log("component_depth", "WARNING: " + msg)
    return result


# ---------- 場景自描述 / 建置報告（2026-09-11 新增） ----------
# SCENE_STATE 只是 stdout 的一次性輸出——關掉終端就沒有了，`.blend` 本身也完全不自描述。
# 這組函式讓「這個檔案是哪組參數、哪個 skill 版本、什麼引擎生的、量到什麼」跟著檔案走：
# 一年後（或另一個 session）打開 .blend 不必外部 JSON 就知道來源；建築類任務的
# report.json 同時是「樓層/構件清單」與「建置履歷」，也是回報使用者的現成素材。
SKILL_VERSION_TAG = "blender-automation-51"


def setup_scene_units() -> None:
    """公制單位 + 不透明底（2026-09-11 新增）。`.blend`/GLB 帶正確的單位語意（公尺），
    且輸出 PNG 不帶 alpha——透明底 PNG 在評圖/合成時背景會被讀成純白，容易誤判成
    「主體過曝」；`.blend` 在 Blender 裡開起來也不會有「本體尺寸 1.0 是什麼單位」的疑問。"""
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.render.film_transparent = False
    log("setup", f"單位={scene.unit_settings.system} "
                 f"film_transparent={scene.render.film_transparent}（不透明底）")


def _scene_metrics(p: dict) -> dict:
    """場景量化摘要（自描述與 report.json 共用）。"""
    mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
    return {
        "object_count": len(bpy.data.objects),
        "mesh_objects": len(mesh_objs),
        "unique_meshes": sum(1 for m in bpy.data.meshes if m.users > 0),
        "materials": len(bpy.data.materials),
        "total_verts": sum(len(o.data.vertices) for o in mesh_objs),
        "total_polys": sum(len(o.data.polygons) for o in mesh_objs),
        "preset": PRESET,
        "aspect": ASPECT,
        "engine_requested": ENGINE,
        "engine_actual": bpy.context.scene.render.engine,
        "resolution": list(RENDER_RES),
        "samples": RENDER_SAMPLES,
        "units": bpy.context.scene.unit_settings.system,
    }


def _json_default(value):
    """`json.dumps(..., default=...)` 的共用 fallback（2026-09-13 新增）。

    SCENE_STATE / report.json / `.blend` 自描述都會把「呼叫端回傳的東西」整包序列化。
    呼叫端的 `subject()` 只要回傳一個含 bpy 物件的 dict（例如把 `park_master()` 的母版
    直接塞進 `out["masters"]`），`json.dumps()` 就拋 TypeError——而且是在管線的最後一步
    炸掉，report.json 從此不存在，驗收只能靠 stdout。bpy 物件一律取其 `.name`（比 repr
    可讀、也對得上 §16.2 的前綴命名），其餘不可序列化型別退回 `str()`。
    """
    name = getattr(value, "name", None)
    if isinstance(name, str) and name:
        return name
    return str(value)


def write_scene_provenance(p: dict, subject_info=None, extra: dict | None = None) -> dict:
    """把參數/量測寫進 scene 自訂屬性（`bp_*` 鍵），讓 `.blend` 自描述（2026-09-11 新增）。

    `T.main()` 在存檔前呼叫一次、渲染完拿到 LUMA 後再呼叫一次（第二次把 luma/交付檔
    資訊經 `extra` 併入 `bp_metrics`，並重新存檔）。回傳實際寫入的 dict，方便呼叫端
    放進 SCENE_STATE。只寫字串（Blender 自訂屬性支援 str/int/float，JSON 字串最不容易
    在讀取端踩到型別轉換問題）。"""
    prov = {
        "bp_skill_version": SKILL_VERSION_TAG,
        "bp_params": json.dumps({"preset": PRESET, "calib": CALIB,
                                 **{k: str(v) for k, v in p.items()}}, ensure_ascii=False),
        "bp_metrics": json.dumps({**_scene_metrics(p), **(extra or {})},
                                 ensure_ascii=False, default=_json_default),
    }
    if isinstance(subject_info, dict):
        prov["bp_subject"] = json.dumps(subject_info, ensure_ascii=False,
                                        default=_json_default)
    for key, value in prov.items():
        bpy.context.scene[key] = value
    log("provenance", f"場景自描述已寫入 {sorted(prov)}")
    return prov


def write_build_report(state: dict, out_dir: str | None = None) -> str:
    """把建置報告落檔成 `<OUT_DIR>/report.json`（2026-09-11 新增）。

    內容 = SCENE_STATE ＋ 逐物件明細（verts/faces/材質/尺寸/世界中心）＋ 逐鏡頭輸出檔
    （路徑/bytes/mtime，含 `history/` 底下的歷程圖）。失敗只記 WARNING 不中斷主流程
    （報告是附加價值，不是交付主體）。"""
    out_dir = out_dir or OUT_DIR
    report = dict(state)
    # 材質槽可能是 None（布林挖洞/切割後 Blender 會留下空槽），一律過濾掉——
    # 直接 m.name 會在這種物件上 AttributeError（實測：Famicom 主體布林挖卡帶井後
    # 出現空槽，report 落檔整個炸掉）。
    report["objects_detail"] = [
        {"name": o.name, "type": o.type,
         "verts": len(o.data.vertices) if o.type == "MESH" else 0,
         "faces": len(o.data.polygons) if o.type == "MESH" else 0,
         "materials": [m.name for m in o.data.materials if m] if o.type == "MESH" else [],
         "dims_m": [round(v, 3) for v in o.dimensions],
         "world_center_m": [round(v, 3) for v in _world_bbox_center(o)]}
        for o in bpy.data.objects]
    shots = []
    for path in ([os.path.join(out_dir, "render.png")]
                 + sorted(glob.glob(os.path.join(out_dir, "history", "*.png")))):
        if os.path.isfile(path):
            shots.append({"path": path, "bytes": os.path.getsize(path),
                          "mtime": datetime.datetime.fromtimestamp(
                              os.path.getmtime(path)).isoformat(timespec="seconds")})
    report["shots"] = shots
    report_path = os.path.join(out_dir, "report.json")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log("report", f"建置報告已落檔 {report_path}（{len(report['objects_detail'])} 物件、"
                      f"{len(shots)} 張輸出圖）")
    except OSError as exc:  # noqa: BLE001
        log("report", f"WARNING: 建置報告落檔失敗（不影響交付產物）: {exc}")
    return report_path


def _world_bbox_center(obj) -> Vector:
    """世界座標包圍盒中心——不能用 `obj.location`：本 skill 的 add_box()/add_cyl() 慣例
    是建完立刻 transform_apply() 把位置烘進網格、物件自身 location 歸零（§14），對這樣
    的物件取 location 一律得到 (0,0,0)（同 export_label_projections() docstring 記過的坑）。"""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(corners, Vector((0.0, 0.0, 0.0))) / len(corners)


# ---------- 主流程 ----------

def main(subject_fn=None, preset_overrides: dict | None = None,
         preset: str | None = None, out_dir: str | None = None,
         export_glb_path: str | None = None) -> None:
    """建模渲染主流程。

    引用模式（§9.6.1，推薦）：場景腳本 import 本模組後呼叫
    T.main(subject_fn=my_subject, preset_overrides={"sky_strength": 0.21})——
    subject_fn 取代預設佔位 build_subject()，preset_overrides 微調曝光配方
    （拷貝後覆蓋，不改 PRESETS 本體）。直接執行（__main__）時兩者皆為 None，
    跑佔位示範，行為與舊版一致。

    scene_pkg 模式（§16）：preset/out_dir 顯式引數優先於環境變數——
    build.py 可直接傳 config 值，免在 import 前設定環境變數的時序陷阱。

    `export_glb_path`（2026-09-10 新增）：給路徑就在存檔後自動匯出 GLB（呼叫
    `export_glb()`，匯出目前場景全部 MESH/EMPTY/ARMATURE，含 `shape_lib.
    rotation_pivot()` 建的樞軸階層）——任務需要交付可攜格式（遊戲引擎/動畫/
    網頁 3D）就傳這個參數，不用自己在 subject_fn 外面另外呼叫一次。留 None
    （預設）行為跟以前完全一樣，只存 `.blend`+渲染 PNG，不強制每個任務都要
    匯出 GLB。"""
    global PRESET, OUT_DIR, RENDER_RES, RENDER_SAMPLES
    if preset is not None:
        PRESET = preset
    if out_dir is not None:
        OUT_DIR = out_dir
    if os.path.abspath(OUT_DIR) == os.path.abspath(_OUT_DIR_FALLBACK):
        log("out_dir", f"WARNING: 輸出目錄未指定，落在內建 fallback {OUT_DIR}——交付物"
                       "（render.png/scene.blend/report.json）不會出現在任務的輸出目錄。"
                       "傳 out_dir=（或設環境變數 BLENDER_TEMPLATE_OUT）指向任務輸出目錄"
                       "（例：<workspace>/output/<task>）")
    # CALIB 在 import 時已決定（環境變數/--calib）；若呼叫方在 import 後才改環境，這裡補抓一次
    # FIX 2026-09-10（電風扇案例事故）：這裡原本無條件覆寫 RENDER_RES 成寫死的 16:9 形狀
    # (960,540)/(1280,720)，完全沒檢查 _ASPECT_LOCKED——set_aspect('9:16'/'1:1') 在 import
    # 後、main() 前呼叫，原本設計是「叫過就鎖住，之後不再被覆寫」（見 set_aspect() 自己的
    # docstring 與 auto_frame_and_light() 對同一個旗標的尊重），但這裡漏了同一道檢查，
    # 每次 main() 執行都會把使用者明確指定的直幅/方幅畫幅悄悄改回橫幅，set_aspect() 形同
    # 沒有作用。RENDER_SAMPLES 跟畫幅無關，一律照常更新。
    RENDER_SAMPLES = 48 if ("--calib" in sys.argv or os.environ.get("BLENDER_TEMPLATE_CALIB") == "1") else 256
    if not _ASPECT_LOCKED:
        # 沒呼叫 set_aspect() 時落回 ASPECT 目前的值（= 預設 '16:9'），**解析度一律由
        # _ASPECT_SIZES 決定**（full 1920x1080 / calib 1440x810）——舊版這裡寫死
        # (960,540)/(1280,720) 是 2026-09-11 把 full 升到 Full HD 時漏改的殘留值，
        # 導致「沒有手動鎖畫幅」的場景全部只渲到 720p、比 §10.1 的 Full HD 下限還低。
        RENDER_RES = _ASPECT_SIZES[ASPECT]["calib" if ("--calib" in sys.argv or os.environ.get("BLENDER_TEMPLATE_CALIB") == "1") else "full"]
    if PRESET not in PRESETS:
        fail("config", f"未知 PRESET '{PRESET}'（可用：{list(PRESETS)}）")
    if ENGINE not in ("cycles", "eevee"):
        fail("config", f"未知 ENGINE '{ENGINE}'（可用：cycles/eevee）")
    p = dict(PRESETS[PRESET])  # 拷貝，避免改動配方本體
    if preset_overrides:
        unknown = set(preset_overrides) - set(p)
        if unknown:
            fail("config", f"preset_overrides 含未知鍵 {sorted(unknown)}（可用：{sorted(p)}）")
        p.update(preset_overrides)
        log("config", f"preset_overrides 套用：{preset_overrides}")
    if SKY_DOMINANT:
        # 天空占比 >50% 的構圖直接套配方 sky_strength 必過曝（skill §10.2#8）
        p["sky_strength"] = round(PRESETS[PRESET]["sky_strength"] * 0.7, 3)
        log("config", f"SKY_DOMINANT=1：sky_strength {PRESETS[PRESET]['sky_strength']} → {p['sky_strength']}（×0.7）")
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
    except OSError as exc:
        fail("precondition", f"無法建立輸出目錄 {OUT_DIR}: {exc}")
    blend_path = os.path.join(OUT_DIR, "scene.blend")
    render_path = os.path.join(OUT_DIR, "render.png")
    log("precondition", f"OUT_DIR={OUT_DIR} PRESET={PRESET} CALIB={CALIB} res={RENDER_RES}")

    # 元件表拆解深度閘門（§11 Stage A item 3）：宣告了元件表就必須通過；沒宣告則在
    # SCENE_STATE 留一筆警告——「MUST 卻沒有東西在管」正是這條規則過去的實際狀態，
    # 這裡讓它有 exit code。放在建場景之前＝CALIB 階段就 fail fast，不用等渲染完才發現。
    component_depth = None
    if COMPONENTS_JSON:
        component_depth = assert_component_depth(COMPONENTS_JSON)
        log("component_depth",
            f"元件表深度 PASS：{component_depth['component_count']} 元件、"
            f"最深 LEVEL {component_depth['max_level']}（門檻 {MIN_COMPONENT_LEVEL}）")
    else:
        log("component_depth",
            "WARNING: 未宣告元件表（BLENDER_COMPONENTS_JSON / set_components_json）——"
            "§11 Stage A item 3 的六級拆解沒有任何東西在管，請設定後重跑")

    verify_orientation_math()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    log("setup", "場景已清空（factory settings, empty）")
    setup_scene_units()

    subject_info = (subject_fn or build_subject)()

    # 場景模式函式（setup_cel_studio() 等）是在 subject_fn() **內部**才寫入配方覆寫／切換
    # 引擎與色彩映射的——所以這兩件事都必須在 subject_fn() 之後才讀。寫在前面會拿到空的
    # 覆寫與舊引擎（實測踩過：五組不同 sun_energy 渲出位元完全相同的圖，因為覆寫根本沒生效）。
    if PRESET_AUTO_OVERRIDES:
        p.update(PRESET_AUTO_OVERRIDES)
        log("config", f"場景模式配方覆寫套用：{sorted(PRESET_AUTO_OVERRIDES)}")
    # EEVEE 是佈局預覽通道：GI/降噪與材質路徑都和 Cycles 不同，LUMA 不可互比，避免
    # 「拿預覽圖的亮度去調正式配方能量」這種把預覽當成品的誤用（見 set_engine()）。
    exposure_enforced = (ENGINE != "eevee")

    # 地面先建（2026-09-11 修正）：下面的自動懸空審查要拿地面當支撐面——原本
    # build_ground() 排在審查之後，任何「直接站在地面上」的物件（廣場鋪面、地坪、
    # 基座、道路）在審查當下場景裡根本沒有地面可打，一律被回報「底部 5 個取樣點
    # 往下 5m 內都沒偵測到任何支撐面（嚴重懸空或飄出場景外）」。實測對照：200m
    # 鋪面大板 + 20000m 地面這組幾何，先建地面 → 0 問題；地面不存在 → 假警報
    # （同一組幾何、同一組容差）。build_ground() 只讀 p（地面配色/漸層參數），
    # 不依賴 subject_fn 的產物，提前呼叫無副作用。
    build_ground(p)
    # 太空／真空場景（set_ground_void()）：地面物件剛建好，這裡套用可見度覆寫——幾何與
    # ray_cast 支撐面照常，但相機與鏡面物件看不到它（地面留在畫面上會變成一條比銀河帶
    # 還亮的灰帶，把星雲帶硬生生切斷）。
    apply_ground_void(bpy.data.objects.get("Ground"))

    # 自動幾何審查（2026-09-08 新增，東方明珠塔連續兩輪事故：v1 三根主柱互相重疊 2m、
    # v2 上球到太空艙之間憑空缺了 70m 連接段，兩次都是 §13.9 的 audit_interpenetration/
    # audit_floating 一秒鐘就能抓到的問題，但因為是一次性腳本、沒人手動呼叫，兩次都直接
    # 渲染出去才被使用者肉眼發現）。**只要走 T.main()，這兩個審查自動跑，不需要呼叫端
    # 記得呼叫**——report_or_fail 用 hard=False（只報告不擋渲染，容差沿用函式既有預設值
    # 1cm，不是新發明的容差邏輯），寫進 log 與 SCENE_STATE 的 auto_geometry_audit 欄位，
    # Stage C 看 SCENE_STATE 時務必檢查這個欄位。
    #
    # **2026-09-10 拆成兩道獨立門檻（來源：復古腳踏車案例，368 個物件超過舊版單一門檻
    # 300，兩項審查整組被跳過，腳架懸空這種一秒鐘該抓到的問題沒人攔）**：舊版把兩個
    # 審查綁在同一個門檻，但兩者真正的成本天差地遠——`audit_interpenetration` 每次
    # 比較只是 6 個浮點數大小比較，就算 O(n²)，物件數上千也不過零點幾秒；真正貴的是
    # `audit_floating` 的 `scene.ray_cast()`（每個物件最多 20 次真的場景光線投射查詢）。
    # 兩者不該共用同一個保守門檻——interpenetration 門檻大幅拉高（1500），floating
    # 門檻維持較保守（800，該函式 2026-09-10 起自帶 bbox 快篩前置，見其 docstring，
    # 已經比舊版快得多，800 對它而言仍算安全）。
    # 環境件（Ground 物件名與 Env_ 前綴）不列入審查清單：巨型地面/鋪面會把「依場景
    # bbox 縮放的容差」直接撐到上限 5cm，讓主體該有的細容差失效（138mm 相機要用
    # ~1.4mm 去抓 2.6mm 的懸空扳手臂，被撐成 5cm 就抓不到）；而且巨型平地跟誰比都是
    # 「貼合」，沒有穿模資訊。地面本身仍留在場景裡——audit_floating() 用 ray_cast 打
    # 整個場景，照樣能當支撐面（所以上面必須先 build_ground()）。
    _mesh_objs = [o for o in bpy.data.objects
                  if o.type == 'MESH'
                  and o.name not in FRAMING_GROUND_NAMES
                  and not o.name.startswith("Env_")
                  and o.name not in PARKED_MASTERS
                  and o.name not in OUTLINE_SHELLS]
    _INTERPEN_LIMIT = 1500
    _FLOATING_LIMIT = 800
    auto_audit_summary = {
        "interpenetration": [], "floating": [],
        "interpenetration_ran": False, "floating_ran": False,
        "interpenetration_skip_reason": None, "floating_skip_reason": None,
        # 保留舊欄位相容（兩者都跑才算 True，避免既有讀取 auto_audit_summary["ran"] 的
        # 呼叫端誤判成「兩項都跑了」）：
        "ran": False, "reason": None,
    }
    _xs, _ys, _zs = [], [], []
    for _o in _mesh_objs:
        for _c in _o.bound_box:
            _w = _o.matrix_world @ Vector(_c)
            _xs.append(_w.x); _ys.append(_w.y); _zs.append(_w.z)
    # 2026-09-09 新增（相機案例：過片扳手臂懸空 2.6mm，固定 1cm 容差完全
    # 沒抓到）——容差跟著主體實際尺度縮放，不再對任何尺度都套同一個 1cm，邏輯跟
    # auto_frame_and_light() 依 bbox diag 縮放燈光能量是同一類修正。1% of diag，
    # 下限 1mm（避免極小主體縮到 0 失去意義）、上限 5cm（避免巨型場景容差爆炸）。
    _scene_diag = (Vector((max(_xs) - min(_xs), max(_ys) - min(_ys), max(_zs) - min(_zs))).length
                  if _xs else 1.0)
    _scaled_tol = max(0.001, min(0.05, _scene_diag * 0.01))
    log("geometry_audit", f"自動審查容差依主體尺度縮放：diag={_scene_diag:.2f}m → tol={_scaled_tol*1000:.1f}mm")

    if len(_mesh_objs) > _INTERPEN_LIMIT:
        auto_audit_summary["interpenetration_skip_reason"] = (
            f"跳過：{len(_mesh_objs)} 個 mesh 物件超過穿模審查上限 {_INTERPEN_LIMIT}（大場景改手動分批呼叫 audit_interpenetration）")
        log("geometry_audit", auto_audit_summary["interpenetration_skip_reason"])
    else:
        auto_audit_summary["interpenetration_ran"] = True
        auto_audit_summary["interpenetration"] = audit_interpenetration(_mesh_objs, tol=_scaled_tol)

    if len(_mesh_objs) > _FLOATING_LIMIT:
        auto_audit_summary["floating_skip_reason"] = (
            f"跳過：{len(_mesh_objs)} 個 mesh 物件超過懸空審查上限 {_FLOATING_LIMIT}（大場景改手動分批呼叫 audit_floating，或對子總成分批傳入）")
        log("geometry_audit", auto_audit_summary["floating_skip_reason"])
    else:
        auto_audit_summary["floating_ran"] = True
        # audit_floating() 自己的文件寫明「只傳應該落地的物件清單，呼叫端自己排除
        # 天花板燈/吊燈這類本來就該懸空的物件」，但這裡是自動全物件掃描，沒有呼叫端
        # 可以排除——改成排除呼叫 mark_side_attached() 標記過的物件（懸臂/側向鎖固
        # 件），不然每個發射塔架、吊車、桁架告示牌都會洗出一堆假警報，真正的懸空
        # 問題會被淹沒在雜訊裡（長征二號F發射台案例：168 物件跑出數十筆懸空警告，
        # 其中大多數是格狀桁架斜撐/懸臂吊車臂/側鎖告示牌，不是真的懸空）。
        # 接頭/軸承連接件（mark_joint_attached）同理——卡鉗跨碟盤、輪轂穿羊角軸承，
        # 底下天生沒有東西，一併排除（2026-09-14 汽車底盤案例）。
        _floating_check_objs = [o for o in _mesh_objs
                                if not o.get("_side_attached") and not o.get("_joint_attached")]
        auto_audit_summary["floating"] = audit_floating(_floating_check_objs, max_gap=_scaled_tol, max_sink=_scaled_tol)

    # 貼附件貼合審查（2026-09-13 新增，§13.9）：標記成側向鎖固的物件被排除在懸空審查
    # 之外（那是必要的減法——向下的 ray_cast 對微重力/懸臂件全是假警報），但減法做完
    # 必須補上加法，否則這批物件就沒有任何檢查在看「有沒有真的碰到宿主」：實測整站
    # 123 件全標記 → 106 件浮在艙體外 0.04–0.58m，照樣通過 CALIB、曝光守衛、語義斷言
    # 與深度閘門，直到肉眼看到。這裡對所有 _side_attached 物件自動跑貼合稽核（預設就開，
    # 不依賴呼叫端記得呼叫），容差依主體尺度縮放（0.5% of diag，2mm–30mm）。
    _ATTACH_LIMIT = 600
    _attach_objs = [o for o in _mesh_objs if o.get("_side_attached")]
    _joint_objs = [o for o in _mesh_objs if o.get("_joint_attached")]
    _attach_tol = max(0.002, min(0.03, _scene_diag * 0.005))
    auto_audit_summary["attachment_contact"] = {
        "ran": False, "checked": 0, "tolerance_m": _attach_tol, "issues": [], "skip_reason": None,
        "side_attached_total": len(_attach_objs),
        "declared_host": sum(1 for o in _attach_objs if o.get("_attach_host")),
    }
    _ac = auto_audit_summary["attachment_contact"]
    if not _attach_objs:
        _ac["skip_reason"] = "無物件被 mark_side_attached() 標記（沒有被排除的懸空檢查，故無需替代稽核）"
    elif len(_attach_objs) > _ATTACH_LIMIT:
        _ac["skip_reason"] = (f"跳過：{len(_attach_objs)} 件側向鎖固件超過貼合稽核上限 {_ATTACH_LIMIT}"
                              "（改在 assertions.py 分批呼叫 audit_attachment_contact / assert_attachment_contact）")
        log("attachment_contact", _ac["skip_reason"])
    else:
        _ac["ran"] = True
        _ac["checked"] = len(_attach_objs)
        _ac["issues"] = audit_attachment_contact(_attach_objs, max_gap=_attach_tol)
        if _ac["issues"]:
            log("attachment_contact", f"貼合稽核發現 {len(_ac['issues'])} 件未貼合宿主（不擋渲染，Stage C 必查 "
                                      "SCENE_STATE.auto_geometry_audit.attachment_contact）："
                                      + "；".join(_ac["issues"][:8]))
        else:
            log("attachment_contact", f"貼合稽核通過：{len(_attach_objs)} 件側向鎖固件全部貼在宿主表面"
                                      f"（容差 {_attach_tol * 1000:.1f}mm）")
        # 配額界線（§13.9）：排除假警報的機制被全站套用時，「懸空檢查」對這些物件等於不存在。
        _excluded_n = len(_attach_objs) + len(_joint_objs)
        if _excluded_n >= 10 and _excluded_n > 0.5 * len(_mesh_objs):
            log("attachment_contact", f"WARNING: {_excluded_n}/{len(_mesh_objs)} 個 mesh 物件被排除在懸空審查外"
                                      f"（側向鎖固 {len(_attach_objs)} ＋ 接頭/軸承 {len(_joint_objs)}，>50%）"
                                      "——請確認每一件都經上面兩道稽核（貼合 / 接頭包絡）逐件檢驗（§13.9）")

    # 接頭/軸承連接稽核（2026-09-14 新增，§13.9）：車用/機械總成大量零件靠接頭連接（卡鉗跨
    # 碟盤、輪轂穿羊角軸承、螺栓鎖固），這類件既沒有向下支撐（懸空審查假警報），也不是面對面
    # 貼合——用貼合稽核量只會換成另一種雜訊（實測一台車：334 件被標記側向鎖固、只有 3 件宣告
    # 宿主，310 件被回報「離宿主表面 0.048m」，而且報的「最近宿主」還是全場任意的另一件）。
    # 第三類標記讓它們用「對宿主的接合包絡」被檢驗，而不是兩道審查都不看。
    _joint_tol = max(0.005, min(0.05, _scene_diag * 0.01))
    auto_audit_summary["joint_attachment"] = {
        "ran": False, "checked": 0, "tolerance_m": _joint_tol, "issues": [], "skip_reason": None,
        "joint_attached_total": len(_joint_objs),
        "declared_host": sum(1 for o in _joint_objs if o.get("_joint_host")),
    }
    _jc = auto_audit_summary["joint_attachment"]
    if not _joint_objs:
        _jc["skip_reason"] = "無物件被 mark_joint_attached() 標記（沒有被排除的懸空檢查，故無需替代稽核）"
    elif len(_joint_objs) > _ATTACH_LIMIT:
        _jc["skip_reason"] = (f"跳過：{len(_joint_objs)} 件接頭/軸承件超過稽核上限 {_ATTACH_LIMIT}"
                              "（改在 assertions.py 分批呼叫 audit_joint_attachment / assert_joint_attachment）")
        log("joint_attachment", _jc["skip_reason"])
    else:
        _jc["ran"] = True
        _jc["checked"] = len(_joint_objs)
        _jc["issues"] = audit_joint_attachment(_joint_objs, max_gap=_joint_tol)
        if _jc["issues"]:
            log("joint_attachment", f"接頭連結稽核發現 {len(_jc['issues'])} 件不在宿主接合包絡內（不擋渲染，"
                                    "Stage C 必查 SCENE_STATE.auto_geometry_audit.joint_attachment）："
                                    + "；".join(_jc["issues"][:8]))
        else:
            log("joint_attachment", f"接頭連結稽核通過：{len(_joint_objs)} 件接頭/軸承件全在宿主"
                                    f"接合包絡 {_joint_tol * 1000:.1f}mm 內")

    auto_audit_summary["ran"] = auto_audit_summary["interpenetration_ran"] and auto_audit_summary["floating_ran"]
    auto_audit_summary["reason"] = auto_audit_summary["interpenetration_skip_reason"] or auto_audit_summary["floating_skip_reason"]
    n_issues = (len(auto_audit_summary["interpenetration"]) + len(auto_audit_summary["floating"])
                + len(auto_audit_summary["attachment_contact"]["issues"])
                + len(auto_audit_summary["joint_attachment"]["issues"]))
    if n_issues:
        log("geometry_audit", f"自動審查發現 {n_issues} 項問題（不擋渲染，Stage C 必查 SCENE_STATE.auto_geometry_audit）：" +
            "；".join(auto_audit_summary["interpenetration"] + auto_audit_summary["floating"]
                      + auto_audit_summary["attachment_contact"]["issues"]
                      + auto_audit_summary["joint_attachment"]["issues"]))
    elif auto_audit_summary["interpenetration_ran"] or auto_audit_summary["floating_ran"]:
        log("geometry_audit", "自動審查通過：無穿模/懸空問題")

    build_world(p)
    build_lights(p)
    focus = build_camera()
    # World 建完之後才做得成的事（太空星空環境貼圖）：build_world() 會整個換掉 World，
    # 提早接上的環境貼圖會被蓋掉。掛勾排在 build_camera() **之後**，是因為銀河帶的自動
    # 取景（space_lib.make_star_map(band_center_deg="auto")）要拿真正的相機算「這條帶會
    # 不會被地平線或畫面上下緣切斷」——那正是星空被硬邊裁斷的成因，這個順序就是解法。
    # build_lights()／build_camera() 都不碰 World，排到後面一樣安全。
    if PENDING_WORLD_HOOK is not None:
        try:
            PENDING_WORLD_HOOK()
        except Exception as exc:  # noqa: BLE001
            log("world", f"WARNING: world hook 執行失敗（{exc}）——星空環境貼圖未接上，"
                         "背景只剩 Preset 的底色")
    # 背面法外殼（3 渲 2）：request_outline() 的請求在這裡執行——相機剛就位，
    # 線寬才是拿真正的最終相機算的（ORTHO 走 ortho 公式），且早於渲染。
    if PENDING_OUTLINE is not None:
        _out = setup_inverse_hull(PENDING_OUTLINE["objects"], px=PENDING_OUTLINE["px"],
                                  mat=PENDING_OUTLINE["mat"],
                                  z_offset=PENDING_OUTLINE["z_offset"],
                                  alpha_attr=PENDING_OUTLINE["alpha_attr"],
                                  alpha_ref=PENDING_OUTLINE["alpha_ref"],
                                  mode=PENDING_OUTLINE["mode"])
        OUTLINE_INFO.update(_out["info"])
        log("outline", f"request_outline 執行完成：{len(_out['shells'])} 個外殼、"
                       f"線寬公式={_out['push_formula']}（寫入 SCENE_STATE.outline）")
    bloom_ok = setup_render(p, render_path)
    # 鏡頭光暈（太空／一般場景後製）：一定要在 setup_render() **之後**——那個函式會用
    # compositing_node_group 建 bloom group，而在 subject_fn() 期間先建的 group 會被它
    # 整個蓋掉（scene.compositing_node_group 一次只能掛一個）。這支會重建整條鏈並把
    # 泛光一起納入，等於取代 setup_render() 的 bloom group；失敗降級為純 bloom。
    if PENDING_FLARE is not None:
        try:
            setup_lens_flare(p=p, **PENDING_FLARE)
        except Exception as exc:  # noqa: BLE001
            log("compositor", f"WARNING: 鏡頭光暈設定失敗（{exc}）——降級為純 bloom，"
                              "交付產物不受影響")

    # 構圖入鏡審查（2026-09-11 新增，§15.4）：相機算完、畫幅定案之後才有意義——
    # 「主體有沒有完整入鏡、在畫面裡佔多大」用投影數字回答，不必等渲染出來肉眼猜。
    # 排除地面/環境件（_is_environment_obj()）：把涵蓋整個畫面的大地面也算進主體桶，
    # 會讓每個鏡頭都回報「主體超出畫面」的假警報，預設就排除。
    _framing_objs = [o for o in _mesh_objs if not _is_environment_obj(o)]
    framing_summary = audit_framing(_framing_objs)
    auto_audit_summary["framing"] = framing_summary
    if framing_summary["issues"]:
        log("framing", "構圖審查發現問題（不擋渲染，Stage C 必查 "
                       "SCENE_STATE.auto_geometry_audit.framing）："
                       + "；".join(framing_summary["issues"]))
    else:
        log("framing", f"構圖審查通過：主體 {framing_summary['objects']} 件、"
                       f"覆蓋率 {framing_summary['coverage'] * 100:.1f}%、"
                       f"u={framing_summary['u_range']} v={framing_summary['v_range']}")

    # 假地平線前置審查（§10.5 太空場景）：真空裡「近水平面以掠射角入鏡」＝畫面上會出現
    # 一條平直亮線把星空切斷。這道幾何檢查在渲染**前**就跑完，不必等渲完看圖；渲染後另有
    # audit_horizon_line() 用真實像素兜底。**只在太空 Preset 跑**——一般場景的地板/平台
    # 本來就該入鏡，不是缺陷，跑它只會製造假警報。
    horizon_surface_audit = None
    if PRESET == "space":
        try:
            horizon_surface_audit = audit_horizon_surfaces(_framing_objs)
            auto_audit_summary["horizon_surfaces"] = horizon_surface_audit
            print("HORIZON_SURFACES:" + json.dumps(horizon_surface_audit, default=_json_default),
                  flush=True)
            if horizon_surface_audit["issues"]:
                log("horizon", "假地平線前置審查發現問題（不擋渲染，Stage C 必查 "
                               "SCENE_STATE.auto_geometry_audit.horizon_surfaces）："
                               + "；".join(horizon_surface_audit["issues"]))
            else:
                log("horizon", f"假地平線前置審查通過：{horizon_surface_audit['scanned']} 件主體"
                               f"沒有以掠射角入鏡的朝上平面")
        except Exception as exc:  # noqa: BLE001
            log("horizon", f"WARNING: 假地平線前置審查失敗（不影響交付產物）: {exc}")

    # 場景自描述（2026-09-11 新增）：存檔前先把參數/量測寫進 scene 自訂屬性，`.blend`
    # 本身就能回答「這是哪組參數、什麼引擎生的」，不必依賴外部 JSON 或 stdout。
    write_scene_provenance(p, subject_info)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)  # 壓縮：同級案例 280KB
        log("save", f"場景已存檔 {blend_path}（compress=True）")
    except Exception as exc:  # noqa: BLE001
        fail("save", f"存檔失敗: {exc}")

    if export_glb_path:
        try:
            export_glb(export_glb_path)
        except Exception as exc:  # noqa: BLE001
            fail("export", f"GLB 匯出失敗: {exc}")

    try:
        bpy.ops.render.render(write_still=True)
        log("render", f"渲染完成 {render_path}")
    except Exception as exc:  # noqa: BLE001
        fail("render", f"渲染失敗: {exc}")
    if not os.path.isfile(render_path):
        fail("verify", f"渲染檔不存在: {render_path}")

    # 渲染歷程存檔（2026-09-10 新增，取代「渲染前 Remove-Item/rm -f 清空舊 render.png」
    # 的舊慣例——使用者原話：「我人不在就卡在那邊」，刪檔案這類 destructive 操作在
    # 無人值守時會卡在權限確認上，整個流程被鎖死。render.png 本身被 bpy 直接覆寫，
    # 不需要任何 shell 層級的刪除動作；stale-output 的防呆改交給下面 luma_stats 前
    # 的 mtime 新鮮度斷言（呼叫端 Stage C 仍應核對 render.png 的 mtime 晚於本次
    # blender 進程啟動時刻，見 SKILL.md §9.6.4 rule 3）。這裡額外把每次渲染複製
    # 一份到 history/ 底下、檔名帶時間戳記，副作用是保留了完整的渲染歷程軌跡，
    # 不用特別去重建就能回顧每一輪迭代的視覺差異。歷程存檔失敗不擋主流程。
    try:
        hist_dir = os.path.join(OUT_DIR, "history")
        os.makedirs(hist_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tag = "calib" if CALIB else "full"
        shutil.copy2(render_path, os.path.join(hist_dir, f"render_{stamp}_{tag}.png"))
    except OSError as exc:  # noqa: BLE001
        log("render", f"WARNING: 渲染歷程存檔失敗（不影響正式產出）: {exc}")

    stats = luma_stats(render_path)
    print("LUMA_STATS:" + json.dumps(stats, default=_json_default), flush=True)
    problems = check_exposure(stats, p)
    # 色階數審計（2026-09-13 新增）：3 渲 2／賽璐璐（VIEW_TRANSFORM=='Standard'）的成品
    # 合格線不是 LUMA 帶——EEVEE 下曝光守衛只報告不擋（exposure_enforced=False），這條
    # 路線改看色階數。跟 §15.4 audit_framing() 同一個 soft 慣例：自動跑一次寫進
    # SCENE_STATE.band_audit、stdout 印 BAND_STATS，不擋渲染；呼叫端仍可用回傳值自行
    # hard-fail。審計失敗不擋交付產物。
    band_audit = None
    if VIEW_TRANSFORM == "Standard":
        try:
            band_audit = audit_band_count(render_path)
            print("BAND_STATS:" + json.dumps(band_audit, default=_json_default), flush=True)
            if band_audit["issues"]:
                log("band_audit", "WARNING: " + "；".join(band_audit["issues"]))
        except Exception as exc:  # noqa: BLE001
            log("band_audit", f"WARNING: 色階數審計失敗（不影響交付產物）: {exc}")
    # 假地平線審計（§10.5 太空場景，渲染後）：跟前置的幾何檢查互補——這道用**真實像素**
    # 量「畫面裡有沒有一條橫向亮邊把星空切斷」，抓得到幾何檢查放行、實際卻仍亮的平台
    # （幾何檢查只判角度/跨度/材質，看不到實際打光結果）。同樣 soft、不擋交付產物；
    # 只在太空 Preset 跑（一般場景的地板邊緣不是缺陷）。
    horizon_audit = None
    if PRESET == "space":
        try:
            horizon_audit = audit_horizon_line(render_path)
            print("HORIZON_AUDIT:" + json.dumps(horizon_audit, default=_json_default), flush=True)
            if horizon_audit["issues"]:
                log("horizon", "假地平線審計發現問題（不擋渲染，Stage C 必查 "
                               "SCENE_STATE.horizon_audit）：" + "；".join(horizon_audit["issues"]))
            else:
                log("horizon", "假地平線審計通過：畫面裡沒有橫向亮邊切斷星空")
        except Exception as exc:  # noqa: BLE001
            log("horizon", f"WARNING: 假地平線審計失敗（不影響交付產物）: {exc}")
    # 自描述補齊最終量測（LUMA/交付檔/曝光問題）後重新存檔——讓 `.blend` 帶著這次
    # 實際量到的結果，而不是只有開跑前的參數。重存成本可忽略，失敗不擋主流程。
    write_scene_provenance(p, subject_info, extra={
        "luma": stats, "blend": blend_path, "render": render_path,
        "render_bytes": os.path.getsize(render_path) if os.path.isfile(render_path) else 0,
        "exposure_problems": problems, "exposure_enforced": exposure_enforced,
    })
    try:
        bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    except Exception as exc:  # noqa: BLE001
        log("save", f"WARNING: 自描述回寫存檔失敗（不影響交付產物）: {exc}")
    state = {
        "objects": [{"name": o.name, "type": o.type,
                     "loc": [round(v, 3) for v in o.location],
                     "dims": [round(v, 3) for v in o.dimensions]} for o in bpy.data.objects],
        "object_count": len(bpy.data.objects),
        "materials": [m.name for m in bpy.data.materials],
        "preset": PRESET,
        "engine": bpy.context.scene.render.engine,
        "engine_requested": ENGINE,
        "exposure_enforced": exposure_enforced,
        "samples": RENDER_SAMPLES,
        "resolution": list(RENDER_RES),
        "view_transform": bpy.context.scene.view_settings.view_transform,
        "look": bpy.context.scene.view_settings.look,
        "compositor_bloom": bloom_ok,
        "sun_elevation_deg": p["sun_elev_deg"],
        "fog_density": p["fog_density"],
        "dof_fstop": CAM_FSTOP,
        "focus_distance": round(focus, 3),
        "luma": stats,
        "band_audit": band_audit,
        "horizon_audit": horizon_audit,
        "mesh_reuse": {  # §14.5 復用統計：unique 遠小於 mesh_objects 才證明復用成立
            "mesh_objects": sum(1 for o in bpy.data.objects if o.type == "MESH"),
            "unique_meshes": sum(1 for m in bpy.data.meshes if m.users > 0),
            "assets_reused": REUSE,  # instance() 計數：母版名 → 實例數（空 = 未用母版模式）
        },
        "subject": subject_info,
        "component_depth": component_depth,
        "outline": dict(OUTLINE_INFO),
        "flare": dict(FLARE_INFO),
        "auto_geometry_audit": auto_audit_summary,
        "blend": blend_path,
        "render": render_path,
        "render_bytes": os.path.getsize(render_path),
    }
    print("SCENE_STATE:" + json.dumps(state, default=_json_default), flush=True)
    write_build_report(state)
    if problems:
        if exposure_enforced:
            fail("exposure", "曝光驗證未通過：" + "；".join(problems)
                            + " —— 調整 PRESET 能量/天空強度後重渲（对照 skill §10.2 帶狀標準）")
        log("exposure", "WARNING: EEVEE 佈局預覽模式——曝光問題只報告不擋（"
                        + "；".join(problems)
                        + "）——預覽圖不可用於校準能量，見 set_engine() docstring")
    log("done", f"全部通過：{len(bpy.data.objects)} 物件、曝光 "
                f"{'PASS' if not problems else 'WARN'}（mean={stats['mean']}）")


if __name__ == "__main__":
    main()
