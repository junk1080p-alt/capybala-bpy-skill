# KEYWORDS: blender, bpy, geometry, 幾何, 工廠函數, make, 母版, scene_pkg
"""元件工廠（§16/§14）：每類資產一個 make_xxx(mats) → 母版物件。

規則：
1. 母版在局部座標建成、原點=接地中心；只建幾何+掛材質，不擺位（擺位是 layout 的事）。
2. 母版建完呼叫 T.park_master()（hide_render 隔離，禁止高空存放）。
3. 方向性組件隨建隨驗（§12/§13 斷言寫在工廠內，錯誤攔截在單一份）。
4. 比例常數從 config.PROPORTIONS 讀，分段用 T.golden_series/T.fib_split 生成。
"""
import build_template as T


def make_demo_block(mats: dict):
    """示範母版：一個帶倒角的盒子。實際任務替換成 make_tower/make_car/…"""
    obj = T.add_box("Mst_DemoBlock", (0.6, 0.6, 0.9), (0, 0, 0.45),
                    mat=mats["demo_body"], bevel=0.02)
    return T.park_master(obj)
