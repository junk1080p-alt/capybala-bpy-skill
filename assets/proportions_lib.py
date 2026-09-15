# KEYWORDS: blender, bpy, proportions, 比例, 計算機, car, vehicle, human, body, chibi, 車體, 人體
"""proportions_lib.py — 比例計算機（凍結模組，與 mat_lib.py/shape_lib.py 同級）。

輸入主尺寸（車長/身高），回傳各部件建議尺寸 dict，取代手填猜測值。所有回傳值
都是經驗法則起點，不是精確工程規格；呼叫端用 **kwargs 覆寫任一 key 都直接生效。

匯入慣例：import proportions_lib as PR
"""


def car_proportions(length: float, category: str = "sedan", **overrides) -> dict:
    """車長 → 各部件建議尺寸。category: sedan/suv/bus/truck。

    回傳 keys：width, height, wheelbase, front_overhang, rear_overhang,
    wheel_diameter, wheel_width, door_front_w, door_rear_w, grille_w, grille_h,
    plate_w, plate_h, headlight_w, headlight_h, turn_signal_w, turn_signal_h,
    exhaust_d, ground_clearance。

    door_front_w == door_rear_w（四門均分 wheelbase，扣一段 B 柱寬）；真實車輛
    前後門寬度常有些微差異，這裡先給等寬起點，需要不對稱自行覆寫。
    """
    R = {
        "sedan": dict(width=0.37, height=0.30, wheelbase=0.58,
                     wheel_d_of_h=0.44, wheel_w_of_d=0.35,
                     grille_w_of_w=0.55, grille_h_of_h=0.20,
                     head_w_of_w=0.18, head_h_of_h=0.10,
                     ground_clear_of_h=0.10, doors=4),
        "suv": dict(width=0.38, height=0.38, wheelbase=0.60,
                   wheel_d_of_h=0.40, wheel_w_of_d=0.36,
                   grille_w_of_w=0.60, grille_h_of_h=0.24,
                   head_w_of_w=0.17, head_h_of_h=0.11,
                   ground_clear_of_h=0.14, doors=4),
        "bus": dict(width=0.24, height=0.27, wheelbase=0.50,
                   wheel_d_of_h=0.30, wheel_w_of_d=0.32,
                   grille_w_of_w=0.40, grille_h_of_h=0.12,
                   head_w_of_w=0.10, head_h_of_h=0.06,
                   ground_clear_of_h=0.08, doors=2, door_w=1.1),
        "truck": dict(width=0.30, height=0.45, wheelbase=0.55,
                     wheel_d_of_h=0.28, wheel_w_of_d=0.38,
                     grille_w_of_w=0.50, grille_h_of_h=0.16,
                     head_w_of_w=0.16, head_h_of_h=0.09,
                     ground_clear_of_h=0.10, doors=2, door_w=0.95),
    }
    if category not in R:
        raise ValueError(f"car_proportions: 未知 category '{category}'（可用：{list(R)}）")
    r = R[category]
    width = length * r["width"]
    height = length * r["height"]
    wheelbase = length * r["wheelbase"]
    overhang = length - wheelbase
    wheel_d = height * r["wheel_d_of_h"]
    door_w = r.get("door_w", wheelbase / 2 - 0.05)  # 4門均分 wheelbase；2門(bus/truck)用固定實際門寬
    out = {
        "width": width, "height": height, "wheelbase": wheelbase,
        "front_overhang": overhang * 0.45, "rear_overhang": overhang * 0.55,
        "wheel_diameter": wheel_d, "wheel_width": wheel_d * r["wheel_w_of_d"],
        "door_front_w": door_w, "door_rear_w": door_w,
        "grille_w": width * r["grille_w_of_w"], "grille_h": height * r["grille_h_of_h"],
        "plate_w": 0.36, "plate_h": 0.13,
        "headlight_w": width * r["head_w_of_w"], "headlight_h": height * r["head_h_of_h"],
        "turn_signal_w": width * r["head_w_of_w"] * 0.35,
        "turn_signal_h": height * r["head_h_of_h"] * 0.5,
        "exhaust_d": max(0.05, height * 0.05),
        "ground_clearance": height * r["ground_clear_of_h"],
        "doors": r["doors"],
    }
    out.update(overrides)
    return out


def human_proportions(height: float, gender: str = "male", style: str = "realistic",
                      heads: float = 3.0, **overrides) -> dict:
    """身高 → 各部位建議尺寸/高度（Z=0 為腳底）。gender: male/female（僅影響寬度）。
    style: realistic（7.5 頭身經典美術比例）/ chibi（Q 版，heads 決定頭身比，預設 3）。

    回傳 keys：head_height, shoulder_z, chest_z, waist_z, hip_z, knee_z, ankle_z,
    shoulder_width, hip_width, arm_length, torso_length, leg_length。"""
    wide = gender.lower() != "female"
    if style == "chibi":
        head_h = height / heads
        out = {
            "head_height": head_h,
            "shoulder_z": height * 0.62, "chest_z": height * 0.50,
            "waist_z": height * 0.42, "hip_z": height * 0.32,
            "knee_z": height * 0.16, "ankle_z": height * 0.02,
            "shoulder_width": head_h * (1.35 if wide else 1.25),
            "hip_width": head_h * (1.20 if wide else 1.30),
            "arm_length": height * 0.30,
        }
    else:
        head_h = height / 7.5
        out = {
            "head_height": head_h,
            "shoulder_z": height * 0.82, "chest_z": height * 0.73,
            "waist_z": height * 0.62, "hip_z": height * 0.50,
            "knee_z": height * 0.28, "ankle_z": height * 0.04,
            "shoulder_width": head_h * (2.00 if wide else 1.80),
            "hip_width": head_h * (1.55 if wide else 1.75),
            "arm_length": height * 0.44,
        }
    out["torso_length"] = out["shoulder_z"] - out["hip_z"]
    out["leg_length"] = out["hip_z"]
    out.update(overrides)
    return out


def ergonomic_reference(height: float = 1.70, **overrides) -> dict:
    """人體工學基準尺寸（Z=0 腳底站姿）——**沒有專屬計算機的品類，先查這份**：
    任何「跟人互動/人使用」的物件，尺寸都能從人體基準推：握把直徑參考
    `grip_diameter`、按鍵/開關間距參考 `finger_width`、台面高度參考
    `elbow_height`、頭頂淨空參考 `reach_up`，比憑感覺猜一個數字可靠。

    回傳 keys：eye_height_standing, eye_height_seated, shoulder_height,
    elbow_height, reach_up, reach_forward, hand_length, hand_width,
    grip_diameter, finger_width, stride_length, step_over_max。"""
    out = {
        "eye_height_standing": height * 0.93, "eye_height_seated": height * 0.69,
        "shoulder_height": height * 0.82, "elbow_height": height * 0.62,
        "reach_up": height * 1.24, "reach_forward": height * 0.42,
        "hand_length": height * 0.108, "hand_width": height * 0.045,
        "grip_diameter": 0.032, "finger_width": 0.018,
        "stride_length": height * 0.42, "step_over_max": height * 0.25,
    }
    out.update(overrides)
    return out


def furniture_proportions(item: str, **overrides) -> dict:
    """家具人體工學建議尺寸（固定經驗值，非依主尺寸縮放——家具尺寸本來就該貼合
    人體，不隨「這件家具多大」線性縮放）。item：chair/table_dining/table_coffee/
    sofa/cabinet/bed/desk。任一值 kwargs 覆寫。"""
    R = {
        "chair": dict(seat_height=0.45, seat_depth=0.43, seat_width=0.45,
                     back_height=0.40, back_angle_deg=100, leg_thickness=0.04),
        "table_dining": dict(height=0.74, top_thickness=0.04,
                             knee_clearance=0.29, leg_thickness=0.06),
        "table_coffee": dict(height=0.42, top_thickness=0.035, leg_thickness=0.05),
        "sofa": dict(seat_height=0.42, seat_depth=0.58, back_height=0.62,
                    arm_height=0.22, arm_width=0.18, cushion_thickness=0.12),
        "cabinet": dict(depth=0.35, shelf_spacing=0.30, plinth_height=0.08,
                        door_thickness=0.02),
        "bed": dict(frame_height=0.45, mattress_thickness=0.25,
                   headboard_height=1.0, width_single=0.90, width_double=1.50,
                   length=2.0),
        "desk": dict(height=0.74, top_thickness=0.035, knee_clearance=0.60),
    }
    if item not in R:
        raise ValueError(f"furniture_proportions: 未知 item '{item}'（可用：{list(R)}）")
    out = dict(R[item])
    out.update(overrides)
    return out


def stair_proportions(total_rise: float, width: float = 1.0, **overrides) -> dict:
    """樓層淨高 → 階梯建議尺寸。經驗公式 2×踏步高+踏步深 ≈ 0.63m（人因安全標準，
    這條公式錯了肉眼立刻看出「這樓梯很怪」，不是可以隨便湊數的地方）。

    回傳 keys：num_steps, riser_height, tread_depth, width, handrail_height,
    headroom。"""
    riser_target = 0.17
    num_steps = max(1, round(total_rise / riser_target))
    riser = total_rise / num_steps
    tread = 0.63 - 2 * riser
    out = {
        "num_steps": num_steps, "riser_height": riser, "tread_depth": max(0.22, tread),
        "width": width, "handrail_height": 0.95, "headroom": 2.05,
    }
    out.update(overrides)
    return out


def door_window_proportions(kind: str, **overrides) -> dict:
    """門窗標準規格（固定值，跟家具同理不隨建物尺度縮放）。kind：interior_door/
    exterior_door/window_standard/window_large。"""
    R = {
        "interior_door": dict(width=0.85, height=2.03, frame_thickness=0.05),
        "exterior_door": dict(width=0.95, height=2.10, frame_thickness=0.06),
        "window_standard": dict(width=1.0, height=1.2, sill_height=0.9, frame_thickness=0.06),
        "window_large": dict(width=1.8, height=1.6, sill_height=0.6, frame_thickness=0.07),
    }
    if kind not in R:
        raise ValueError(f"door_window_proportions: 未知 kind '{kind}'（可用：{list(R)}）")
    out = dict(R[kind])
    out.update(overrides)
    return out


def container_proportions(height: float, kind: str = "bottle", **overrides) -> dict:
    """容器總高 → 各段比例。kind：bottle/jar。

    回傳 keys：diameter, cap_height, neck_height, shoulder_height, base_height,
    label_band_bottom, label_band_top。"""
    R = {
        "bottle": dict(d_of_h=0.32, cap=0.09, neck=0.15, shoulder=0.10, base=0.02,
                      label_bottom=0.30, label_top=0.65),
        "jar": dict(d_of_h=0.55, cap=0.14, neck=0.06, shoulder=0.08, base=0.03,
                   label_bottom=0.25, label_top=0.75),
    }
    if kind not in R:
        raise ValueError(f"container_proportions: 未知 kind '{kind}'（可用：{list(R)}）")
    r = R[kind]
    out = {
        "diameter": height * r["d_of_h"], "cap_height": height * r["cap"],
        "neck_height": height * r["neck"], "shoulder_height": height * r["shoulder"],
        "base_height": height * r["base"],
        "label_band_bottom": height * r["label_bottom"],
        "label_band_top": height * r["label_top"],
    }
    out.update(overrides)
    return out
