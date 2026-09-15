# KEYWORDS: blender, bpy, build, 入口, main, scene_pkg
"""場景包入口（§16）：唯一執行檔。組裝 config→materials→geometry/layout→assertions→render。

用法（在 scene_pkg 資料夾的上層執行）：
  blender --background --python scene_pkg/build.py            # 正式渲染
  blender --background --python scene_pkg/build.py -- --calib # 校準快渲（寫完第一個動作，§9.6.3）

修改定位表：改光照/比例/相機→config.py；改材質→materials.py；
改某物件外形→geometry.py 對應 make_xxx；改擺位→layout.py/config.PLACEMENTS；
加斷言→assertions.py；元件拆解深度不足→components.json（§11 item 3 的閘門輸入）。
永遠不需要重寫整包。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                       # 場景包內互相 import
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)                 # build_template.py 所在層

import config
if config.SKY_DOMINANT:
    os.environ["BLENDER_TEMPLATE_SKY_DOMINANT"] = "1"   # 必須在 import build_template 前
import build_template as T

import materials
import layout
import assertions


def subject() -> dict:
    mats = materials.build_materials()
    info = layout.build_scene(mats)
    assertions.verify_scene()
    return info


if __name__ == "__main__":
    T.set_camera(**config.CAMERA)
    # §11 Stage A item 3 的拆解深度閘門輸入——main() 在建場景之前先檢查，深度不足即 exit 1
    T.set_components_json(config.COMPONENTS_JSON)
    T.main(subject_fn=subject,
           preset_overrides=config.PRESET_OVERRIDES,
           preset=config.PRESET,
           out_dir=config.OUT_DIR)
