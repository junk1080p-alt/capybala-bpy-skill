# KEYWORDS: blender, bpy, assertion, 斷言, 驗證, 方向, scene_pkg
"""場景級語義斷言（§16/§12/§13/§15）：build 完成後、渲染前跑，失敗即 exit 1。

可用工具（全在 build_template）：
  T.assert_axis_perp(obj, travel_dir, label)     軸向件⊥行進方向（輪子）
  T.assert_long_axis_aligned(obj, road_dir, …)   長軸件∥道路（車輛停放）
  T.assert_mount_offset(face, pole, label, min)  資訊面不穿心（招牌）
  T.assert_proportion(actual, target, label)     比例偏差 >8% 攔截（§15）
  T.world_axis(obj)                              局部軸的世界方向
  T.assert_component_depth(path, min_level=6)    元件表拆解深度（§11 Stage A item 3）
                                                 ——main() 已依 config.COMPONENTS_JSON
                                                 自動跑，這裡列出供手動補跑／單獨重驗
斷言一律用世界座標頂點（transform_apply 後 object.location 失效，§8#9）。
"""
import bpy
import build_template as T


def verify_scene() -> None:
    bpy.context.view_layer.update()
    # 示範：確認實例存在且未被母版 hide 旗標污染
    insts = [o for o in bpy.data.objects if o.name.startswith("Inst_")]
    if not insts:
        T.fail("assertion", "找不到任何 Inst_* 實例——layout 未執行或命名違規")
    hidden = [o.name for o in insts if o.hide_render]
    if hidden:
        T.fail("assertion", f"實例繼承了母版 hide 旗標（instance() 漏還原？）：{hidden}")
    masters = [o for o in bpy.data.objects if o.name.startswith("Mst_")]
    exposed = [o.name for o in masters if not o.hide_render]
    if exposed:
        T.fail("assertion", f"母版未隔離將入鏡：{exposed}（§14.1 必呼叫 park_master）")
    T.log("assertions", f"場景斷言通過：{len(insts)} 實例 / {len(masters)} 母版")
