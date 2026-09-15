# KEYWORDS: blender, bpy, config, 參數, 命名規則, scene_pkg
"""場景包設定（§16）：所有可調參數集中在本檔，改光照/比例/輸出只碰這裡。

禁止在其他模組寫死任何數值常數——尺寸、能量微調、相機、preset 選擇全部收進來。
"""
import os

# ---------- 任務身分 ----------
TASK = "demo_pkg"          # 場景包名（snake_case，與資料夾同名）
PRESET = "studio"          # studio | outdoor_golden | night（配方見 build_template.PRESETS）
# 交付物放哪裡＝**任務自己的輸出目錄**（例：<workspace>/output/<task>——使用者要打開、交付、
# 續改的那一份），不是工具/skill 自己的暫存目錄。2026-09-14 汽車底盤案例：交付在
# C:\AI\CAR-PARTS\output\chassis，這裡的預設值卻指到 skill 自己的 artifacts/，兩者不一致
# ＝交付物事後找不到的風險。下面的相對路徑只是「沒人指定時」的 fallback；正式任務請改成任務
# 輸出目錄，或設環境變數 BLENDER_TEMPLATE_OUT（main() 落在 fallback 時會印 WARNING）。
OUT_DIR = os.environ.get(
    "BLENDER_TEMPLATE_OUT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "artifacts", TASK))

# 曝光微調（±20% 以內，skill §10.2#2）；空 dict = 純配方。
# demo 場景只有一個 0.6m 方塊、畫面大部分是深灰地面（實測 coverage=0.29、mean=69.7），
# 而 studio 的 luma_band(100-170) 是為「主體填滿大半畫面」校準的——照 §15.4 的既有結論
# 放寬下緣即可，不要為了讓 demo 過關去調能量（那會污染整個 studio 配方的校準基準）。
PRESET_OVERRIDES: dict = {"luma_band": (55.0, 175.0)}

# 天空占比 >50% 構圖（仰視高塔/俯瞰大場景）：True → sky_strength 自動 ×0.7
SKY_DOMINANT = False

# ---------- 元件表（§11 Stage A item 3：拆解深度閘門的輸入） ----------
# main() 會讀這個檔案，最深 LEVEL < 6 即 exit 1（未宣告則只記 WARNING 進 SCENE_STATE）。
# 這道閘門只讀 JSON、不需要參考圖或 calib，所以原創設計類（沒有三視圖可量）同樣適用——
# 拆解深度是「物件很多、讀起來卻很粗糙」唯一能被自動攔下來的結構性檢查。
COMPONENTS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components.json")

# ---------- 相機（構圖層，§15.4） ----------
CAMERA = {
    "loc": (-1.35, -1.85, 1.05),
    "target": (0.0, 0.02, 0.48),
    "lens": 35,
    "fstop": 2.8,
}

# ---------- 主體比例（§15：一律由黃金比例工具生成，禁止手填近似值） ----------
# 例：PROPORTIONS = {"body_h": 400, "segments": 8} → geometry 用 T.golden_series 分段
PROPORTIONS: dict = {}

# ---------- 擺位（layout.py 專用；loc 一律 (x, y, z)，yaw 單位=度） ----------
# 例：LAMPS = [{"loc": (3, -2, 0), "yaw": 45}, ...]
# 2026-09-09：loc 除了手寫絕對座標，也可以在 layout.py 裡改用
# shape_lib.relative_loc(host, face, frac, offset) 對某個已建好的物件算出相對位置
# 再填進來——host 尺寸/位置改了，相對定位的物件重跑腳本會自動跟著對，不用逐一手動
# 改座標（見 layout.py 的 demo_marker 範例、SKILL.md §13.10/§16.1）。
PLACEMENTS: dict = {}
