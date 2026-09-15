# KEYWORDS: blender, bpy, material, 材質, scene_pkg
"""材質工廠（§16）：全部材質在 build_materials() 一次建齊，回傳 name→Material dict。

改顏色/粗糙度/金屬度只碰本檔。命名規則：Mat_<用途>（Mat_Glass、Mat_Oak…），
禁止 Cube.001 式匿名材質。程序化紋理優先（§10.1 材質軸）：
T.make_mat（純色）/ T.add_noise_color_mat（混染）/ T.make_wood_mat / T.make_fabric_mat。
"""
import build_template as T


def build_materials() -> dict:
    mats = {
        # "glass": T.make_mat("Mat_Glass", (0.85, 0.9, 0.95), roughness=0.05, metallic=0.0),
        "demo_body": T.add_noise_color_mat("Mat_DemoBody", (0.45, 0.47, 0.5), (0.32, 0.34, 0.37), scale=8.0),
        "demo_accent": T.make_mat("Mat_DemoAccent", (0.72, 0.45, 0.18), roughness=0.3, metallic=0.85),
    }
    T.log("materials", f"材質建齊 {len(mats)} 種：{sorted(mats)}")
    return mats
