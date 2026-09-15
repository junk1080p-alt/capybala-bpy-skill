# KEYWORDS: blender, bpy, layout, 擺位, instance, 復用, scene_pkg, anchor, 相對定位
"""擺位層（§16/§14）：只做 T.instance(master, ...) 放置，禁止混入幾何細節。

規則：
1. 實例命名 Inst_<母版名去前綴>_<序號>（Inst_DemoBlock_01），方便 SCENE_STATE 定位。
2. 擺位資料從 config.PLACEMENTS 讀；臨時加一個實例=加一行，不用碰其他檔。
3. 變體白名單四種：loc / 繞Z yaw / uniform scale / 材質槽（§14.2）。
4. **絕對座標 vs 相對錨點（2026-09-09 新增，§13.10）**：config.PLACEMENTS 裡的
   `loc` 可以是手寫的絕對 (x,y,z)（下面 demo_block 的用法），也可以改用
   `shape_lib.relative_loc(host_obj, face, frac, offset)` 算出來（下面
   demo_marker 的用法）——後者的好處是 host 物件的尺寸/位置日後調整，依附它的
   物件位置**重跑腳本就自動跟著對**，不用逐一手動改座標。中大型/多元件任務優先
   用相對錨點，純粹孤立不依附任何東西的物件（例如場景裡的第一個主體本身）才用
   絕對座標。
"""
import build_template as T
import config
import geometry
import shape_lib as SL


def build_scene(mats: dict) -> dict:
    """建全部母版 + 擺全部實例；回傳 subject_info（進 SCENE_STATE）。"""
    masters = {
        "demo_block": geometry.make_demo_block(mats),
    }
    placements = config.PLACEMENTS.get("demo_block",
                                       [{"loc": (0, 0, 0), "yaw": 0, "scale": 1.0}])
    first_instance = None
    for i, pl in enumerate(placements, 1):
        inst = T.instance(masters["demo_block"], f"Inst_DemoBlock_{i:02d}",
                          tuple(pl["loc"]), rot_z=pl.get("yaw", 0), scale=pl.get("scale", 1.0))
        if first_instance is None:
            first_instance = inst
    # 相對錨點示例：一個小標記貼在第一個實例的 +X 面正中央、往外推 5cm——
    # demo_block 尺寸日後改了，這個標記重跑腳本會自動貼著新的面，不用改這行數字。
    if first_instance is not None:
        marker_loc = SL.relative_loc(first_instance, '+X', frac=(0.5, 0.5), offset=(0.05, 0, 0))
        T.instance(masters["demo_block"], "Inst_DemoMarker_01", marker_loc, scale=0.15)
    T.log("layout", f"擺位完成：{sum(len(v) for v in (config.PLACEMENTS or {'d': placements}).values())} 實例 + 1 相對錨點示例")
    return {"masters": list(masters), "instances": T.REUSE}
