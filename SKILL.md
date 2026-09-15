# Blender Automation Skill (verified: Blender 5.1.2, English UI)

> **寫作公約（禁止再回填下列四類內容）**：本文件只寫「要怎麼做／不要怎麼做」與其判準，不得再出現——
> 1. **事故／失誤的經過與根因敘事**（「事故還原」「根因分析」「共同根因」「背景（修正原因）」「實測教訓」「為什麼會設計錯」這類用故事交代規則由來的段落）。規則照寫，緣由不寫。
> 2. **參考來源的來歷標註**（學了哪個模型、哪份參考案例、誰逆向分析出來的）。
> 3. **把特定人說過的話當成規則依據的引述**（規則直接寫成規則，不交代是誰要求的）。
> 4. **變更紀錄式的日期戳記**（哪一天新增／哪一天修正／哪一天起生效這類標註與版本變更說明）。


> **版本漂移警告**：本 skill 針對驗證機 Blender **5.1.2**（build 2026-05-19, branch blender-v5.1-release, Python 3.13.9）實測驗證。選單、快捷鍵、bpy API 隨大版本變動；若安裝版本 ≠ 5.1.x，先跑「版本偵測」並對照 https://docs.blender.org/manual/en/<版本>/ 。

> **這份 skill 怎麼讀，取決於你自己的判斷力**：本 skill 的 Stage A→B→C 強制流程、v3-floor 數值下限（§10.1）、以及「一律先用 helper lib」的要求，是針對**執行速度快、但建模判斷力較弱的模型**校準出來的鷹架——目的是確保這類模型也能穩定交出不低於某個底線的成果。**如果你是明顯更強、更有建築/工業設計判斷力的模型**：§0（路徑解析協議）、§8（Blender 5.1 API 落差表）、§9.5/§10.2 裡標明「機器安全限制」「實測數值」的段落是這台機器/這個 Blender 版本的**客觀事實**，不受你的能力高低影響，請照樣遵守；但 Stage A→B→C 的流程順序、v3-floor 的數值下限、以及是否要呼叫 `build_template.py`/`building_lib.py`/`mat_lib.py` 這幾個 helper lib，都只是**輔助**——如果你判斷自己直接寫 raw bpy/bmesh、或用不同的工作流程能做出更好的成果，不需要被這些鷹架綁住，只要最終成果經得起使用者檢驗即可。
>
> **`assets/anatomy/`/`assets/examples/` 裡的組件清單/技法範例同樣是地板，不是天花板**：這些文件記錄的是「已知會被漏掉、值得明講出來的必要組件/技法」，內容深度反映的是**寫這份文件當下查證到、或實戰踩過坑的程度**，不是這個品類所有可能存在的細節的完整清單——**你自己對這個品類的認識如果比文件寫得更細，永遠以你自己的判斷為準，直接把文件沒提到的細節加上去**，不要因為某個組件/工法沒被圖譜點名就假設「不需要」或「這樣才是標準答案」。反過來，如果讀了圖譜以後發現自己原本想畫的細節比圖譜列的還粗略，圖譜列出的才是**最低限度**，不是可以拿來當藉口簡化的理由。這份 skill 的圖譜/範例庫仍在持續擴充，任何時候都可能不是該品類目前已知最細緻的版本——把它們當「防漏檢查清單」讀，不要當「照抄範本」讀。

## 0. Blender 路徑解析協議（跨機器強制，禁止寫死路徑）

**本 skill 隨 app 發到每台電腦，任何寫死 `C:\Program Files\...\blender.exe` 的做法都是定時炸彈。** 每個任務開工時照以下順序解析一次：

1. **工作區快取**：`<workspace>\.capybala\blender-path.txt` 存在且路徑仍有效 → 直接用（本工作區解析過就永不重找）。
2. **跑 `assets/find_blender.ps1`**（skill 資產，六級 cascade 一次完成）：
   ```powershell
   powershell -NoProfile -File <skill_dir>\assets\find_blender.ps1 -CacheFile <workspace>\.capybala\blender-path.txt
   ```
   成功輸出 `BLENDER_PATH=<exe>` + `BLENDER_VERSION=<version>` 並自動寫快取；cascade 順序 = 快取 → `BLENDER_PATH` 環境變數 → PATH → 登錄 Uninstall 機碼 → 常見位置 glob（Program Files / LOCALAPPDATA / Steam / Downloads portable）→ 全失敗 exit 1。
3. **exit 1 時**：問使用者 blender.exe 完整路徑**一次**，答案寫進快取檔，之後永不重複問。

解析到的路徑存進 PowerShell 變數，本 skill 所有範例命令一律用 `& $blender` 形式：
```powershell
$blender = (Get-Content <workspace>\.capybala\blender-path.txt -Raw).Trim()
& $blender --version
```

### 本機環境事實（驗證機範例，其他機器以解析結果為準）

- 驗證機安裝路徑：`C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`（registry 級命中）
- UI 語言：英文。GPU：Intel Arc B370 — Cycles GPU 支援有限，**渲染預設走 CPU**；長渲染用 create_background_task 丟背景。
- **UIA 樹回傳 0 個元素**（inspect_window fallbackUsed=true，純 OCR 模式）。Blender 是自繪 UI，不提供 Windows UIA；OCR 座標可用但不穩定（例：「Help」辨識成「HeIp」）。→ **不要用 UI 點擊路線操作 Blender**，一律走腳本。
- ahujasid/blender-mcp 於驗證機已安裝（id 以 mcp_list_native 為準；uvx 路徑因機器而異，驗證機為 `%USERPROFILE%\.local\bin\uvx.exe blender-mcp`，22 工具）。Blender addon 已啟用，GUI 開啟時 MCP server 自動監聽。其他機器照 §7.2 安裝流程。
- **Blender 內嵌 Python 有 numpy 2.3.4**（實測）：渲染後可在腳本內直接 `bpy.data.images.load()` 讀回 PNG 算亮度統計，不需要外部 PIL。

## 0.5 Skill Assets（可復用參考檔，隨 skill 保存）

**核心引擎／場景骨架**

- **`assets/find_blender.ps1`**——Blender 路徑六級 cascade 解析（§0），每個新任務/新機器開工第一步。
- **`assets/build_template.py`**——通用建模渲染範本。任何建模任務：`copy_skill_resource_native` 取出到 `.capybala/test-scripts/build_template.py`（**凍結模組，不改內容**），場景腳本依 §9.6.1 用 `import build_template as T` + `T.main(subject_fn=..., preset_overrides=...)` 引用。**中大型/需迭代任務改用場景包**（§16.1，六件拆分：config/materials/geometry/layout/assertions/build，改一處只碰一檔）。**禁止**引用工作區暫存腳本當範本。
  - 內建：`verify_orientation_math()`（方向自檢）、`PRESETS`（studio/outdoor_golden/night/space 曝光配方）、`LUMA_STATS` 亮度守衛、`park_master()`/`instance()`（§14 母版復用）、`SKY_DOMINANT`、**黃金比例工具組**（§15：`PHI`/`FIB`/`fib_split()`/`golden_series()`/`nearest_fib()`/`assert_proportion()`，分段/收分/節奏數字一律由它生成，禁止手填）、`cut_hole()`/`carve_depression()`（§13.10 布林挖洞/挖凹陷）、`save_object_asset()`/`append_object_asset()`（§16.6 跨任務資產庫）、`auto_frame_and_light()`（§15.4 依主體包圍盒自動算相機構圖+三點燈+畫幅，`energy_scale` 參數統一 derate 三點式與太陽避免漏光）、`auto_night_fill(objects, ambient_scale)`（`night` PRESET 的對等版——依**全部入鏡場景物件**（不只主體）的包圍盒自動算兩盞低能量冷色 AREA 補光，取代舊版寫死世界原點、不隨場景尺度縮放的單顆 `InteriorLight`；practical light（燈籠/招牌等）仍由呼叫端自己放、仍是畫面焦點，這支只保底場景其餘範圍不會崩成純黑，見 §10.2）、`curved_eave_roof()`/`parametric_surface()`（§13.10 任意參數曲面/東亞翹角屋頂）、`export_glb(filepath, objects)`（GLB 匯出，`export_extras=True` 保留 custom property，§13.10 可轉動零件小節）、`assert_inset_margins()`（§13 內嵌元件留白斷言）、`assert_within_radius(objs, center_xy, max_r, label, tol)`（見 §13.13：一組物件的水平位置必須落在指定圓形範圍內，任何「把物件散佈/插入某個圓形容器造型」的擺位算完都該呼叫一次，不要只靠人眼看渲染圖）、`assert_ring_hollow(obj, center_xy, z_range, label)`（從中心往上發射射線探測，命中物件自己的面就代表「應該中空的環」其實沒挖空——圓柱體預設端面（`NGON` 單一多邊形或 `TRIFAN` 三角扇皆可測到）殘留原地會整片擋住後方物件，渲染像蓋了一層不透光的蓋子，曝光/LUMA_STATS 這類數值檢查完全測不出來；任何「先建圓柱體、之後打算挖空做環/管/圈」的流程建完都該呼叫一次，優先改用 `flat_ring()` 從源頭避免這個坑）、`world_point()`/`assert_slope_angle(obj, local_p0, local_p1, base_dir, expected_deg, label, tol_deg)`（§13.12 斜面/斜度數值斷言，世界座標量測，不用靠肉眼從渲染圖猜角度）、`rigid_group_transform(objects, pivot, rotation_deg, axis, translation)`（§13.10 多部件子總成先軸對齊建好、最後一次套用剛體變換，取代每個零件各自心算旋轉）、`mark_side_attached(obj, host=None, stand_off=None)`（§13.9 標記懸臂/側向鎖固物件，讓 `T.main()` 的自動懸空審查不會誤報；`host`/`stand_off` 是**會被檢驗的宣告**，不是寫了就算）、`mark_joint_attached(obj, host=None, max_gap=None, note=None)`（§13.9 **第三類安裝方式**——接頭/軸承/同軸嵌合件：卡鉗跨碟盤、輪轂穿羊角軸承、輪胎壓配輪圈。既不靠重力平放、也不是面對面貼合，兩道既有審查對它都只會產生雜訊；`host` 必填、`max_gap` 是對宿主的接合包絡，由 `audit_joint_attachment()` 逐件檢驗，`main()` 對所有 `_joint_attached` 物件自動跑並寫進 `SCENE_STATE.auto_geometry_audit.joint_attachment`）、`audit_joint_attachment(objects=None, max_gap=None)`／`assert_joint_attachment(...)`（同上稽核與其硬性關卡版；未宣告宿主的接頭件一律回報）、`joint_attached_stats()`（回報接頭標記規模，供配額界線判斷）、`mark_assembly_mate(a, b, note=None)`（§13.9 **意圖裝配配對**宣告——AABB 判穿模對同軸嵌合件天生全命中，宣告過的配對在 `audit_interpenetration()` 被跳過，且跳過的對數會記 log，不是靜默放行）、`surface_gap(obj, hosts=None, probe=None)`（量物件網格到宿主表面的最短距離：BVH 相交判定＋頂點/面心最近面查詢；外殼與停放母版自動排除）、`audit_attachment_contact(objects=None, hosts=None, max_gap=None)`（**貼附件貼合稽核**——§13.9：抓「標記成側向鎖固、卻根本沒貼到宿主」的浮空件；`main()` 對所有 `_side_attached` 物件自動跑、寫進 `SCENE_STATE.auto_geometry_audit.attachment_contact`）、`assert_attachment_contact(...)`（同上的硬性關卡版，超差 exit 1）、`side_attached_stats()`（回報標記規模，供配額界線判斷）、`assert_in_frame()`/`audit_framing()`/`frame_coverage()`（§15.4 構圖入鏡量化：主體有沒有完整入鏡、佔畫面多少比例，`main()` 會自動跑 soft 版並寫進 SCENE_STATE）、`audit_horizon_surfaces()`/`audit_horizon_line()`（§10.5 **太空場景假地平線**兩道審查——渲染前找「朝上＋掠射角入鏡＋跨 ≥15% 畫面寬」的面，渲染後找「亮度跳躍 ≥20/255 ＋橫向連續 ≥22% 寬」的亮邊；`PRESET == "space"` 時 `main()` 兩道都自動跑，寫進 `SCENE_STATE.auto_geometry_audit.horizon_surfaces` 與 `SCENE_STATE.horizon_audit`）、`mark_framing_exclude()`（§15.4 把刻意延伸到畫面外的量體排除出構圖審查）、`write_scene_provenance()`/`write_build_report()`（§7.8：`.blend` 自描述 ＋ `<OUT_DIR>/report.json` 建置報告）、`apply_socket_overrides(mats, overrides, label)`（**鏡頭專屬外觀覆寫**——把「材質鍵→[(socket, 值)]」的資料 dict 依鏡頭套用到既有材質上，不改寫節點鏈；同一場景不同鏡頭要不同反光程度時用它，見 `anatomy/buildings/_INDEX.md` hero 鏡頭段）、`mirror_sky_fraction(host, cam_loc)`/`assert_mirror_sky_fraction(host, cam_loc, min_frac, label, hard)`（**鏡面立面仰角定律**——量「立面上高於相機的比例」＝會反射天空的比例；機位拉高會讓拋光帷幕反射深色地面、整棟渲成黑石板，這是幾何/光學問題不是材質問題，建築 hero 鏡頭動工前先算一次）、`set_engine()`（§9.5 EEVEE 佈局預覽通道，`BLENDER_TEMPLATE_ENGINE=eevee` 是等價的環境變數入口）、`setup_cel_studio()`/`set_ground_mat()`/`set_ground_void()`/`request_outline()`（`set_ground_void()` 見 §10.5——太空場景讓地面不入鏡、但**留在場景裡當懸空審查的支撐面**；其餘三支＝**3 渲 2 展示卡模式**——單一主體/產品的 cel 版本展示卡：EEVEE + Standard + 單盞 SUN(`angle=0`，唯一明暗界線來源) + 低能量 `CelFill` + 純色中性背景 + cel 色塊地面 + 背面法外殼，一次呼叫取代 `auto_frame_and_light()`；`sun_offset_deg`（預設 -40°）是太陽相對相機的水平偏移，**設 0 會讓明暗界線縮在輪廓線上、畫面主體消失**；`request_outline()` 解掉「背面法外殼要讀相機矩陣、但相機是 `main()` 內部才建」的時序問題；ORTHO 相機的線寬走 `outline_push_distance(ortho_scale=...)` 的專屬公式（與距離無關），量測寫進 `SCENE_STATE.outline`）、`set_view_transform(name)`（`'agx'` 預設／`'standard'`——**3 渲 2 賽璐璐必須用 standard**，否則色票會被 AgX 打歪；**注意它只記 override、實際套用在 `setup_render()` 內**，不走 `T.main()` 的腳本要自己補 `scene.view_settings.view_transform="Standard"`）、`setup_freestyle(thickness, color)`（3 渲 2 全場單一線寬外輪廓線；EEVEE/Cycles 都可用）、`setup_selective_outline(fg_collections, bg_collections, ...)`（**ZZZ 級選擇性描邊**——FG collection 粗深線、BG collection 細淡線，走 Freestyle `select_by_collection` 實測分層正確；與 `setup_freestyle()` 互斥二選一）、`outline_push_distance(px, distance, res, lens, sensor_width, sensor_fit)`／`make_outline_shell(target, push, ...)`／`setup_inverse_hull(objects, px, ...)`／`measure_outline_shell()`／`audit_outline_shell(shell, target, expected_push)`（**背面法外輪廓 inverse hull——《罪惡裝備》系列自 Xrd 起畫線的主力**，官方 CEDEC2024 講題就叫「背面法」。**Blender 不支援 multipass shader**（官方環境對照表明載 ✕），所以這條路一定要複製**真幾何**：沿 bmesh 幾何平均法線外推（＝官方所稱「第二組法線」，天然不受硬邊／自訂分割法線影響）→ 只畫背面 → 外推處在剪影露出來即為線。線寬依相機距離與焦距自動補償 `push = px·distance·sensor_width/(lens·長邊像素)`（官方 `B=A·tan(θ)` 補上「要幾個像素」的收斂形式）；逐部位線寬／要不要線用頂點色 `Col` 的 alpha（0.5 標準／1.0 兩倍／0＝無線，實測四檔逐位命中）；`z_offset` 把外殼往相機反方向推＝只剩最外圈剪影線（實測線畫素 0.326%→0.106%）。外殼自動登錄 `OUTLINE_SHELLS`，`main()` 的自動穿模／懸空審查據此排除。**舊版「禁用反轉外殼」是過度概括**——失敗的 7 種全是 shader／modifier 路線，缺的正是「真外殼」＋「只畫背面」）、`make_internal_line(name, points, width, mat, plane_normal, lift)`（**內描邊**——皺褶／分件／瓦楞這類圖案**內部**的線，背面法畫不出來；幾何版「本村線」，與貼圖解析度無關、放大不糊）、`setup_anime_post(bloom_threshold, bloom_strength, vignette)`（**動畫攝影後製**——高門檻局部泛光 Fog Glow + 選填暗角；5.1 合成器 group 內 GroupInput 不收渲染畫面、必須自放 `CompositorNodeRLayers`，本函式已內建正確接法）、`audit_band_count(render_path, max_bands=4, min_share, roi)`（**3 渲 2 色階數審計**——量化後統計各色塊佔比，佔比 ≥`min_share` 的色格數 > `max_bands` 即列入 issues；`view_transform=Standard` 時 `main()` 自動跑 soft 版寫進 `SCENE_STATE.band_audit` 並印 `BAND_STATS:`。**`max_bands` 要按材質數與路線調整**——實測純平塗單一 cel 材質 3 階、三材質 5 階、程序化寫實材質 7 階、**漸層 cel 單材質 5-7 階**（受光帶是連續漸層）；進階路線不要用 ≤4 當門檻，改驗邊界梯度/代表色 hex（見風格卡）。它只量階數、**不驗色相**：AgX 誤用實測階數不變、只有色值歪，要驗得比對 `top[].hex`）。這五支與 `mat_lib.make_cel()`/`make_cel_advanced()`/`make_toon()` 配套，整組用法見 §10.4 與 `styles/genre/anime-cel-daylight.md`；**元件表拆解深度閘門**（§11 Stage A item 3）——`set_components_json()`/`audit_component_depth()`/`assert_component_depth(components_path, min_level=)`，全表最深 LEVEL < `MIN_COMPONENT_LEVEL`(6) 且最深分支沒寫 `depth_exempt` 理由即 exit 1。這道閘門只讀 JSON、**不需要 calib／三視圖，所以原創設計類（§16.9.0 B 類）也跑得到**；`main()` 依 `COMPONENTS_JSON`／`BLENDER_COMPONENTS_JSON` 在建場景之前自動跑，結果寫進 `SCENE_STATE.component_depth`。
- **`assets/scene_pkg/`**——場景包七件骨架（§16.1）：build.py 入口 / config.py 全參數 / materials.py 材質工廠 / geometry.py 元件工廠 / layout.py 擺位 / assertions.py 語義斷言 / **inspect.py 常駐場景檢視**（§7.8；按需執行、不進渲染流程，可整檔移除）／**components.json 元件表**（§11 Stage A item 3；`config.COMPONENTS_JSON` → `T.set_components_json()`，main() 在建場景前檢查、不達 LEVEL 6 即 exit 1）。取出到 `.capybala/test-scripts/<task>_pkg/`。命名規則（Mst_/Inst_/Mat_/Lgt_/Env_ 前綴）與修改定位表見 §16.2/§16.3。

**造型與材質工具**

- **`assets/mat_lib.py`**——材質生成函數庫（凍結模組，§17.3）：24 個 factory（金屬/拉絲/陽極鋁/皮革/織物/木紋/清水混凝土/石材/玻璃/鍍膜/塑膠/橡膠/烤漆/自發光/水/草地/土壤/瀝青/磚/陶瓷/霧面玻璃/碳纖維/鋪面/光束），全程序化無外部貼圖。`hex_to_linear()` 轉風格卡色票。`METAL_PRESETS`：`make_metal(name, preset="aluminum"/"chrome"/"steel"/"gold"/"copper"/"brass"/"silver")` 套真實金屬 F0 色。`add_procedural_wear(mat, edge_color, dirt_color, level="light"/"medium"/"heavy", edge_intensity, dirt_intensity, ao_distance)`——既有材質追加磨損/髒污疊層（Pointiness 模擬掉漆、AO 模擬積灰）。`level` 一次決定疊色強度+遮罩範圍（坦克/廢棄機具這類重度磨損載具用 `level="heavy"`），`edge_intensity`/`dirt_intensity` 仍可個別覆寫。`make_glass(name, tint, ior, roughness, specular)`——`specular` 為新增參數（預設 0.5 不影響既有呼叫）：**透明薄殼蓋在細節表面上方**（錶鏡蓋錶盤、儀表玻璃蓋刻度盤）**時務必覆寫成 0.15-0.25**，留預設會讓菲涅爾反射蓋過穿透、底下細節整片死白看不到（見 `assets/anatomy/watch.md` 關鍵技術決策#12）。**已知限制**：Pointiness 在低面數/粗糙整物 bevel 網格上會暈染全平面，host 需要 `shape_lib.bevel_edges()` 局部邊緣才有銳利效果；`ao_distance` 需依主體尺度縮放。`make_asphalt(name, base, roughness, wetness)`——`wetness` 為新增參數（預設 0.0 不影響既有呼叫，向下相容）：濕路面不是額外疊 Transmission 水層，是把 Roughness 大幅壓低+疊積水斑塊遮罩，霓虹/招牌會在地面留下清楚鏡面反射拖影（夜景/賽博龐克類場景的關鍵效果，完整驗證記錄見該函式 docstring）。取出到 `.capybala/test-scripts/mat_lib.py`，materials.py 只 import 引用，禁止複製函數體（P6）。
- **`assets/proportions_lib.py`**——比例計算機（凍結模組）：`car_proportions(length, category=)`（sedan/suv/bus/truck）、`human_proportions(height, gender, style=, heads=)`（realistic/chibi）、`furniture_proportions(item)`（chair/table_dining/table_coffee/sofa/cabinet/bed/desk）、`stair_proportions(total_rise, width)`（2×riser+tread≈0.63m 安全公式）、`door_window_proportions(kind)`、`container_proportions(height, kind)`（bottle/jar）、**`ergonomic_reference(height)`——沒有專屬計算機的品類先查這份**（眼高/肩高/肘高/伸手範圍/手掌/握把直徑/步幅）。回傳值都能 kwargs 覆寫；畫車/家具/建築元件/角色前先呼叫，取代憑感覺填數字。
- **`assets/detail_lib.py`**——幾何細節函數庫（凍結模組，§17.4）：`knurl_ring()` 滾花環、`dial_grooves()` 刻度刻痕、`grip_strip()` 防滑凸點、`ridge_lines()` 平行脊線、`seam_ring()` 接縫環、`make_screw()` 螺絲件、`make_text()` 3D 文字（前後成對刻字用 `rot=(π/2,0,0)`/`(π/2,0,π)`，見函式 docstring）、`arc_text_ring()` 沿圓柱面弧線刻字、`join_into()` 細節併入母版、`audit_detail_density()` 細節密度審計、`saddle_stitches(host_name, p0, p1, count, stitch_len_ratio, radius, mat, offset)`（沿路徑等距排列短線段模擬皮件縫線的虛線顆粒感，`stitch_len_ratio<1` 留針距間隙，不是一條連續實線，見 `assets/anatomy/watch.md`）。局部座標作業改為**世界座標作業**（2026-09-14 修正：原敘述與實作矛盾）、凸出量 ≥0.3mm 防共面（§8#11）；`knurl_ring()`/`dial_grooves()`/`seam_ring()`/`arc_text_ring()` 另有 `center=` 徑向中心（不給＝自動取宿主世界包圍盒中心，**宿主不在原點時不要硬寫 (0,0)**——舊版會讓整圈滾花/刻痕/接縫環/弧線刻字靜默留在世界原點，底盤實測受害 3 件、內裝案例再回報同一族 4 支；明給值與宿主軸心差 >5mm 直接 fail）。
- **`assets/shape_lib.py`**——造型雕塑函數庫（凍結模組，§13.10）：`loop_cut()`/`select_verts_by_bounds()`/`move_verts()`/`bevel_edges()`（精確選邊倒角）/`add_mirror()`/`boolean_union()`/`taper()`/`clean_boolean_result()`（布林後清共面碎面）/`add_weighted_normal()`（改善倒角刻面感，加在修飾器堆疊最後）/`linear_array()`（直線重複）/`curve_tube(name, points, radius, mat, resolution, smooth)`（沿折線串圓管，燈管/纜線/扶手；`smooth=False` 預設 POLY 硬折線、`smooth=True` 改 BEZIER+AUTO 切線自然彎曲，線材/軟管等會自然垂墜的構件用 `smooth=True`）/`truss()`（箱型桁架）/`coil_spring()`（真螺旋彈簧）/`flat_decal()`（自由造型平面貼花）/`anchor()`/`relative_loc()`（相對定位，取代手寫絕對座標）/`basis_quat(x_dir,y_dir,z_dir)`（由三方向向量組旋轉四元數——`mathutils.Matrix((a,b,c))` 是拿 a/b/c 當列組矩陣，物件旋轉要的是行，直接手組必反著轉，一律用這支）/`cut_window(obj, cutter, glass_mat, frame_inset, recess)`（薄殼曲面開窗，不用布林、改整片內縮+內推景深，窗戶曲率直接繼承 host 原曲面）/`parametric_surface(name, u_res, v_res, fn, mat, smooth, solidify)`（任意 `fn(u,v)->xyz` 網格化，穹頂/馬鞍面/翹角屋頂/布料垂墜通用）/`curved_eave_roof(name, center, sides, ridge_z, eave_r, rise, ...)`（東亞翹角屋頂，`parametric_surface` 的具體應用）/`tapered_rod(name, a, b, r1, r2, mat)`（單椎體兩端粗細不同，車製桌腳/欄杆望柱）/`radial_dish(name, center, rings, segments, profile_fn, mat)`（極座標網格，碗/鞍形座椅面）/`lathe(name, profile_fn, z_list, segments, mat)`（車床 revolve，`profile_fn(z)->radius`，球棒/瓶身/車削桌腳/旋鈕——旋轉對稱**實心**造型，剖面是高度的單值函數）/`lathe_profile(name, points, segments, mat, center, cap_start, cap_end)`（見 `assets/anatomy/vessel.md`：吃一串 `(r,z)` 點、允許剖面路徑反折，`lathe()` 的單值函數限制做不出的雙層中空容器——碗/杯/花瓶/捲邊鍋沿，同一高度外壁跟內壁是兩個不同半徑——改用這支；端點 `r≈0` 自動視為封閉極點並 `remove_doubles` 焊接，端點 `r≠0` 則加三角扇封面，`cap_start`/`cap_end` 可關閉）/`profile_loft(name, y_list, section_fn, mat, cap_ends)`（車體式縱向 loft，`section_fn(y)->[(x,z),...]` 任意不對稱剖面；**回傳 `(obj, section_fn)`，車身附加面板一律查 `section_fn(y)` 取真實寬高，不要另外猜常數**，見下方§13.10 規則 8）／`domed_spoke_ring(name, center, axis_normal, up_hint, r_inner, r_outer, dome_depth, count, tube_r, mat, ring_radii, ring_tube_r)`（放射穹頂輻條環：拋物線深度公式 `depth(r)=dome_depth*(1-(r/r_outer)**2)`，喇叭網罩/傘骨/篩網這類「中心凹陷或凸起、邊緣跟外緣夾圈齊平」的結構，不要每根輻條手動給固定 Y 值）／`swept_blade(name, root_r, tip_r, axis_center, phase_deg, half_width_fn, sweep_fn, twist_fn, thickness, bevel_width, mat, plane)`（扭掠扇葉/螺旋槳：半徑方向同時取樣弦寬/掃掠角/扭轉三個呼叫端自訂函式，取代「一片矩形扭轉幾度」的平板做法，`phase_deg` 做多片圓周陣列）／`flat_ring(name, center, axis_normal, up_hint, r_inner, r_outer, thickness, mat, segments)`（任意朝向的扁平環形量體——錶圈/鏡頭卡口環/輪圈胎唇/喇叭盆邊，內外徑+厚度四圈面，不是貼在表面的紋理）／`gear_wheel(name, center, axis_normal, up_hint, radius, teeth, face_width, mat, root_ratio, hub_r, hub_depth, spoke_count, spoke_r, spoke_mat)`（真實梯形輪齒剪影的齒輪片，可選中心軸座+放射輻條，回傳 `(gear_obj, hub_obj_or_None, spokes_list)`——外觀導向靜態齒輪，非嚙合精度漸開線齒形）／`domed_disc(name, center, axis_normal, up_hint, radius, dome_height, mat, rings, segments, dome_power, solidify)`（實心穹頂圓盤——直接組 `parametric_surface()` 的 fn，深度公式跟 `domed_spoke_ring()` 同一套拋物線慣例，但這支是**連續填滿曲面**不是放射輻條，適合錶鏡/鏡片這類需要真的擋光+折射的透明實面）。全部函式讀寫世界座標，bmesh 操作。

**程序化生成**

- **`assets/geonodes_lib.py`**——Geometry Nodes 散布工具（凍結模組）：`scatter_along_curve()` 沿曲線等弧長散布+切線對齊、`scatter_on_surface()` 依密度沿表面散布+法向對齊。**兩者一律 `realize=False` 預設**（`realize=True` 前過 `REALIZE_POLY_BUDGET`=500,000 安全檢查，超支 raise——RealizeInstances 在 instance 數×單一實例 polys 夠大時會直接崩潰）。已知限制：曲線散布後 `curve_obj.bound_box` 不反映 GN 修飾器實際幾何範圍，`auto_frame_and_light()` 對它構圖不準，另傳真正 MESH 參考或用 evaluated depsgraph 量測。
- **`assets/road_lib.py`**——單段道路生成（凍結模組，不含路口/路網自動生成）：`make_road_curve(points, width, thickness, banking_deg)` 回傳 `(road_obj, length_m)`，轉 mesh 後 U 軸對應沿路長度 0~1。`conform_to_terrain(road_obj, terrain_obj, offset)` Shrinkwrap 貼合地形。`add_lane_markings(road_obj, length_m, style)`——呼叫時機在 `convert(target='MESH')` 之後。
- **`assets/building_lib.py`**——程序化建築立面生成（凍結模組，單棟量體+規則格狀立面，不含曲面/非矩形建築）：`generate_facade(width, depth, height, floors, bays, window_ratio, recess, name, wall_mat, window_mat)`——參數順序對齊世界座標 XYZ 軸序。**材質務必透過 `wall_mat`/`window_mat` 參數傳入，不要事後對回傳物件呼叫 `.materials.clear()` 再 append**（會把所有面 `material_index` 重設成 0）。`assemble_building(width, depth, floor_specs, name, bays)`——由下而上逐層組裝，`floor_specs` 逐層指定窗比例/內縮/材質，`bays` 整棟單一參數（逐層不同會在樓層交界產生非流形邊）；`floor_specs` 的 `window_variant_mat`/`window_variant_prob`——同層個別窗格依機率換材質，模擬隨機已入住暖光窗。`make_entrance_canopy()`/`add_balcony()`/`add_ac_units()`/`make_pergola()`——一樓雨遮/陽台/冷氣機/屋頂平台涼棚，獨立於樓體 mesh 之外的附加構件。`add_balcony(..., cheek_mat=...)`——給值會在陽台兩端加一對分戶側牆，實測對立面「凹凸/浮雕感」的貢獻比欄杆本身更大（垂直於立面、斜側光下會投影），陽台覆蓋率低+沒有側牆是立面讀起來扁平的主因之一，見 `anatomy/buildings/residential.md`。`add_interior_blockout(width, depth, floor_z_offsets, floor_height, floor_indices, column_mat, desk_mat, core_mat, column_grid, column_size, inset, desk_spacing, desk_size, desk_row_skip, include_core, core_size, core_offset, include_stairs, stair_width, stair_steps, seed)`——真透射玻璃立面背後若中空，渲染出來整片立面接近純黑方塊（材質選對也救不回來，缺的是幾何），這支函式補粗模柱網+電梯/樓梯核心+桌椅打破真空觀感。**第一版用細圓柱+隨機散布桌椅+柱子只在抽樣樓層出現**，實戰上色後發現三個問題：承重柱太細不像真實結構柱、柱子逐層生成導致「有的層有有的沒有」（柱子本來就該貫通全高）、桌椅是圓底座對不齊方形桌面。**已重寫**：柱子改方形斷面+加粗（預設 0.45m）+固定貫通 `floor_z_offsets[0]` 到頂（跟 `floor_indices` 無關）；新增電梯/樓梯核心（`include_core`/`include_stairs`，貫通全高的粗量體+真的分階的樓梯）；桌子改規則等距網格（`desk_spacing`/`desk_row_skip` 控制排距跟走道節奏）+ 方形桌側板取代圓柱椅子，不是隨機散布。見 `anatomy/buildings/_INDEX.md`「玻璃立面背後：室內粗模」完整前後對照。`make_parking_lot(center, rows, cols, stall_width, stall_depth, aisle_width, pavement_mat, line_mat)`——基地周邊地面元素常年只有「種幾棵樹+一條馬路」，這支補平面停車格鋪面+白線，`stall_width`/`stall_depth` 未經查證，動工時以肉眼觀感微調。`make_pitched_roof(width, depth, wall_top_z, ridge_height, eave_overhang, style, roof_mat, gable_wall_mat, name)`——真正斜屋頂量體，`style='gable'`/`'hip'`，回傳物件底面刻意不封（屋頂坐在牆體上）。`even_bays(length, target)`——目標模矩→`(格數, 均分單位長度)`，立面柱網/節奏間距一律由它反推，不要硬寫格數（見 §15.2 細節節奏）。`assemble_building(..., bay_target=, base_z=)`——`bay_target` 改給「希望的柱距」自動反推格數並均分樓寬（改樓寬時圖案自動在角邊收齊）；`base_z` 讓整棟以指定高度起算，**基座/裙樓式量體（一樓平面比樓上大）就是呼叫本函式兩次、第二次把 `base_z` 設成裙樓總高**，不要讓第二個量體從地面重長一次。`make_lightning_rod(roof_z, x, y, mast_height, ...)`——屋頂避雷針＋頂端航空障礙燈（自發光紅燈；日光級 preset 下 AgX 會把純自發光壓成近白，見 §10.3 同一套讀色限制）。
- **`assets/nature_lib.py`**——自然資產函數庫（凍結模組，§18）：`make_tree()`（Sapling Tree Gen 9 樹種，散布用輕量化 816~2086 polys/棵）、`make_terrain()`（ANT Landscape 31 種 preset）、`make_terrain_pure_bpy()`（零 extension 退路）、`make_rock()`（Rock Generator）、`scatter_on_surface()`（GN 散布，生產禁 realize）、`flatten_pad(terrain, center, pad_z, pad_radius, blend_radius)`（地形上挖平建築基地+向外平滑過渡，避免建築懸空/陷入地形）、`nature_report()`。檔頭 16 條 5.1 實測事實使用前必讀（含 `lakes_1`/`lakes_2`/`river` preset 的殘留 `Landscape_plane` 陷阱）。Sapling/ANT/Rock Generator 是 extension，首次使用需 CLI 安裝（§19 授權閘門）。

**三視圖複刻工具**

- **`assets/triview_lib.py`**——三視圖（正／側／頂）參考圖的**影像端**：載入與二值化（`load_image`/`to_gray`/`otsu_threshold`/`to_ink_mask`）、前處理（`fill_holes` 補剖面線內部空隙、`largest_component` 甩掉尺寸線、`label_components`）、定位（`find_panels` 留白溝切分、`find_body_candidates` 降採樣連通塊＋長寬比、`tighten_body_bbox` 墨量密度收斂）、輪廓（`trace_outer_contour` Moore 追蹤、`simplify_contour` Douglas-Peucker、`normalize_contour` 起點/纏繞正規化）、單視圖入口（`extract_silhouette` 通用、`extract_view_body` 機身、`extract_thin_body` 薄型側視圖）、校準（`calibrate_view` 以一個已知長度鎖定 px_per_mm、`to_mm_contour` 翻正 y、`check_consistency`、`cross_view_ratio`）、驗證（`iou_contours`/`hausdorff`/`render_overlay` 疊圖）、資料（`save_calib`/`load_calib`，schema `triview_calib/1`）。**執行環境是純 Python 3 + numpy + Pillow，不經 bpy**（與 `overlay_tools.py` 同一先例；Pillow 延遲載入，故 Blender 端仍可 import 只為呼叫 load/save_calib）。`--selftest` 不需外部檔案。實戰手冊與實測數據見 `.capybala/notes/triview-workflow.md`。
- **`assets/triview_build.py`**——三視圖的**幾何端**：`profile_to_slab`（把 2D 輪廓做成厚板）、`build_visual_hull`（兩視圖視覺外殼：正視圖沿深度拉伸 ∩ 側視圖沿寬度拉伸）、`cleanup_mesh`（焊接＋有限溶解）、`add_bevel`、`extend_axis_scale`（共同軸等比外擴解共面）、`polygon_sanity`（自交/退化守衛）、`render_ortho`（正交回渲，取景中心為主體世界中心）、`measure_render`（讀回 alpha 量測 mm）、`footprint_dims`、`build_report`、`assert_spec`（尺寸超差 raise）、`_selftest`。以 `blender --background --python triview_build.py -- <calib.json> <out_dir>` 執行，或 `-- --selftest` 自測。**布林固定用 `MANIFOLD` solver，禁用 `EXACT`**（見 §16.9）。
- **`assets/triview_loft.py`**——三視圖的 **Stage 3（站點斷面放樣）+ Stage 4（拓撲正規化）**。視覺外殼數學上必然填平輪廓內側的凹陷，且輸出是布林碎面；本檔改走車廠工序「沿主軸切片 → 逐站斷面 → 橋接成單一連續曲面」。`plan_axes(views)`（有 `top` 視圖→沿長軸取樣，否則沿共同軸；回傳世界軸映射 `axes` 與取樣/跨度軸索引）、`contour_range`、`station_grid(range_a, range_b, stations, eps_frac, distribution)`（站點範圍取交集；`distribution='cosine'` 預設在兩端加密——端部通常正是曲率最大的圓角/收邊，均勻分站會把端部切方）、`scan_spans(contour, sample_idx, span_idx, samples)`（掃描線 even-odd 求所有交點並配對成 span，回報 `n_runs`；`n_runs>1` 就是「該站輪廓有缺口」的偵測訊號）、`section_polygon`（固定 `4*(arc_segs+1)` 點的圓角矩形斷面，固定點數是逐站橋接的必要條件）、`build_station_loft(...)`（逐站橋接、兩端全四邊封蓋、`recalc_face_normals` 統一外翻、軸向左手序自動反轉斷面點序；回報 `gap_stations`/`max_span_runs`/`corner_radius_source`）、`resolve_corner_radius_mm(calib, mode, explicit)`（斷面圓角是**第三個平面**的性質、量測不到，優先序＝顯式 > 對應平面的圖面標註 > 估計，用了不同平面會標 `+plane_mismatch`）、`quadriflow_retopo(obj, ...)`（包裝 `bpy.ops.object.quadriflow_remesh`，5.1.2 無頭實測把布林碎面重拓成全四邊零非流形，0.06–0.11s；`op_name` 可換，API 缺席 raise 不靜默降級）、`measure_topology(obj)`（四邊占比/三角/n-gon/非流形邊）。以 `blender --background --python triview_loft.py -- <calib.json> <out_dir> [--stations N] [--a-view ...] [--corner-radius-mm R] [--no-retopo]` 執行，或 `-- --selftest`。**它不取代 `triview_build`**：外殼擅長「兩視圖就成形、無凹陷」的物件，放樣擅長「需要沿主軸逐站修形、且要乾淨四邊拓撲」的物件。
- **`assets/blueprint_lib.py`**——三視圖「**標註平面圖**」產生器（§16.9.3）。把量測輪廓畫回原圖並打上兩類可引用編號：**元件標註**（`A-1`…，來自 Stage A 元件表，含內縮狀態）與**特徵標註**（`F1`…，輪廓切成 LINE／CURVE／CORNER／SHORT／SPIKE 並附長度、弦偏差、轉折角、外接圓半徑）。`segments_from_contour(pts_mm, view, corner_min_deg, min_feature_mm, major_min_mm, fit_tol_mm)` 切分特徵（**切分前先做折線擬合**，`fit_tol_mm` 預設 0.35mm 併掉掃描階梯雜訊，避免同一條弧被切成十幾個編號，見 §16.9.5 規則 6；`major_min_mm` 控制主要/次要分級，薄型視圖要調小否則真實階差會被整批歸為次要）；`normalize_components`／`load_components`／`save_components`（schema `blueprint_components/1`，支援 `bbox_mm` 或 `center_mm`+`size_mm`）；`component_containment`／`assert_component_within_contour`（bbox 中心需在輪廓內 + 面積比 ≥ `min_area_frac`，圓角切角不算違規，構成元件可標 `exclude_from_containment`）；`build_annotations`（產生後端無關圖元 + 標籤避讓，回報 `label_overlaps`）；`emit_svg`（真文字、可內嵌底圖 base64）/`emit_png`（字級隨 scale 縮放、缺 CJK 字型降級並 WARNING）；`render_blueprint(calib, out_dir, components, images, extra_contours, major_min_mm, ...)` 一次產出 `<out>/blueprint_<view>.svg|.png` + `blueprint_data.json`。**純 Python 3 + numpy + Pillow（不經 bpy）**，同 `triview_lib` 先例；`--selftest` 不需外部檔案。**`extra_contours` 可餵回渲輪廓（Stage C 疊圖比對）**。
- **`assets/component_lib.py`**——Stage A 元件表 × 三視圖的**對賬層**（§16.9.4），CP1／CP2 兩個檢查點的實作。純 Python 3 stdlib（不經 bpy、不需 numpy/Pillow；亦可由 Blender 端 import 或執行）。`audit_coverage()`（視圖盲區／框超出量測輪廓／**元件表拆解深度**——深度判準與不需 calib／三視圖的 `audit_depth()` 同源，全表最深 level < 4 判不足，`depth_exempt` 只認最深那個元件）、`audit_params()`（參數可查性，來源分五級 `annotation`/`measured`/`derived`/`estimated`/`missing`，宣告 `annotation` 卻在 `annotated_dims_mm` 找不到同值者判**虛報**；帶 `conflicts` 卻沒有 `resolved_by` 判 `conflict` 擋下）、`audit_appearance()`（**外觀規格斷言**：`appearance` 含必填 `evidence`，或 `appearance_skipped` 說明理由，`flat_axis`/`max_extent_mm` 成對）、`render_checklist()`（產出給視覺逐項核對的 Markdown）、`compare()`（CP2：規劃值 vs 實測值，比尺寸／位置／方向／材質與貼合厚度並提出建議修正常數）、`diff_tables()`（**版本史 ＋ 凍結違規 ＋ 本輪 scope 違規**，`locked` 被改動或 scope 外變更即 exit 1，見 §16.9.5）。資料契約 schema `components/2`（`blueprint_components/1` 自動升級讀入），`to_blueprint_v1()` 攤平成 blueprint_lib 吃得下的形狀。座標系同 `triview_calib` 的 `contour_mm`；**`rear`/`back` 是鏡像視圖（u 取負）**，填表照圖上看到的左右填、不要直接抄世界 x。`--selftest` 不需外部檔案；機器上沒有獨立 python 時可用 `blender --background --python component_lib.py -- <cmd> ...` 執行。
- **`assets/component_measure.py`**——上一支的另一半（§16.9.4），Blender headless。載入 `.blend`，依元件表的 `objects` 樣式（fnmatch、不分大小寫）找到物件，量出 `aabb_mm`／`centroid_mm`／PCA `axes`／逐件 `parts`，輸出 schema `components_measured/1` 餵給 `component_lib compare`。位置一律用 `matrix_world @ v.co` 計算（`transform_apply()` 會把 loc/rot/scale 烘進 mesh，見 §8 #9），世界座標→mm 由 `--unit-to-mm`（預設 1000，即 1 unit = 1 m）換算。以 `blender --background --python component_measure.py -- --blend S --components K --out M` 執行，或 `-- --selftest`。

- **`assets/space_lib.py`**——太空／軌道場景資產庫（凍結模組，§10.5）：`sun_direction(elev, azim)`（與 `build_lights()` 的 `sun_elev_deg`/`sun_azim_deg` 同一套慣例）、`make_sun_disc(...)`（**相機專用日盤**——自發光球，per-object ray visibility 只留 `camera`、其餘五項全關，否則它會變成第二顆太陽；名稱帶 `Env_` 前綴 → `main()` 的自動審查自動排除）、`make_star_points(...)`（**真幾何星點**，正交相機唯一可靠的點狀星做法；N 顆共用 1 份 icosphere mesh、細分預設 2＝80 面，**不可降到 1**：20 面的球在 5–7px 下讀成方塊）、`make_star_map(...)`（程序化 equirect 星空圖：**純低頻銀河帶**，`star_count` 預設 0 不畫點狀星；明暗塊走平滑升採樣，**禁止方塊遮罩**）、`install_star_world(...)`（把星空圖接上 World 的 `Background.Color`，`interpolation` 固定 Linear）、`frame_elev_range()`／`auto_band_center()`／`audit_band_framing()`（**銀河帶取景**：把「帶被地平線或畫面邊緣切斷」變成可驗的判準，`make_star_map(band_center_deg="auto")` 就是它的自動版，需在 `build_camera()` 之後跑）、`space_report()`、`--selftest`。

**外部資產**

- **`assets/asset_fetch_lib.py`**——外部現成資產抓取（凍結模組，§19）：`fetch_hdri()`（Poly Haven HDRI）、`fetch_polyhaven_model()`（Poly Haven 模型/家具 append）、`polyhaven_search()`、`analyze_reference_model()`（§19.4，匯入參考檔量測尺寸/階層後清除，只留文字摘要）。零金鑰、零 extension、Tier 1 CLI 全程可行。**§7.7：HDRI／自然元素優先用這個或程序化生成；家具/道具預設手建（跟場景擬真度一致），抓現成是依任務判斷的可選手段**。

**參考文件**

- **`assets/anatomy/`**（§13.7）：`camera.md`（旁軸相機六面組件清單+成對組件表）、`car.md`（房車/跑車六面組件清單+比例計算機用法+「最低限度表現原則」：功能性 MUST 部件不需可動機構，但至少刻分模線/做出小型物件，不能完全省略幾何）、`fan.md`（桌扇/電風扇：前後網罩是拋物線穹頂不是平面、扇葉參數化扭掠曲面、**立柱到扇頭的連接件走 U 形吊架+左右側樞紐、不是直桿插進馬達中心**）、`_TEMPLATE.md`。建模產品類主體前必查。`assets/anatomy/spaces/`（§13.8）：`classroom.md`（教室必備元素+動線 MUST 判準）、`japanese_street.md`（日式街道招牌/基礎設施/街道家具——秋葉原/原宿/橋下商店街/拱廊等場域類型先選一個，電柱電線是最高辨識度但最常被忽略的元素；動漫風格路線搭配 `styles/genre/anime-cel-daylight.md` 風格卡管著色/打光/配色，兩者分工不要只讀一份）、`_TEMPLATE.md`——空間類主體用「七類候選+MUST/OPTIONAL 反思測試」取代六面清單。`assets/anatomy/buildings/`：`_INDEX.md`（逐層組裝策略+一樓共通必備元素+細緻度分區原則+**屋頂天際線構件（避雷針/航空障礙燈）**+**裙樓/基座量體（一樓平面大於標準層）**）、`residential.md`/`office.md`（WWR/樓層高等查證數值，以及高層避雷針與基座裙樓的品類適用性）、`flagship_hq.md`（非組件清單，是「選一個差異化維度大幅執行」的決策框架）、`european.md`/`japanese_house.md`（斜屋頂是必要條件不是裝飾選配）。建模建築外觀主體前必查。
- **`assets/styles/`**——設計師風格庫（§17）：`_INDEX.md`（觸發詞路由表）+`_TEMPLATE.md`+四領域 13 張風格卡（architecture/interior/industrial/genre）。主 skill 只載目錄，風格卡按需 read_file_native（或你的 agent 平台上等價的讀檔工具）。
- **`assets/examples/`**——組合範例庫：跟 `anatomy/`（組件清單）、`styles/`（美術方向）不同，這裡是「多個 lib 組合、從空白場景到成品」的完整工作流範例。`_INDEX.md`+`_TEMPLATE.md`+三份範例：`car.md`（造型+開窗+材質+比例計算機，含 bus/truck/suv 差異）、`building.md`（立面生成+局部造型+陽台散布）、`road.md`（道路三函式+路燈散布+地形貼合）。按需 read_file_native（或你的 agent 平台上等價的讀檔工具）。
  - 校準模式：環境變數 `BLENDER_TEMPLATE_CALIB=1`（960×540/48spp 快渲）、`BLENDER_TEMPLATE_PRESET=<preset>`、`BLENDER_TEMPLATE_OUT=<dir>`、`BLENDER_TEMPLATE_SKY_DOMINANT=1`（仰視高塔/俯瞰大場景）。場景包模式下 PRESET/OUT_DIR/CAMERA 直接從 config.py 傳入 `T.main(preset=..., out_dir=...)` + `T.set_camera(**config.CAMERA)`，免環境變數。

## 1. 路由優先級（高→低，照序選用）

**建模一律無條件用 Tier 1（headless bpy 腳本），除非使用者明確指名要用 MCP／開 Blender 視窗／GUI 操作**——這不是風格偏好，是實測結論：直接用 MCP 互動操作或視窗點擊建模，成品品質明顯比 headless bpy 腳本差（結構/比例/材質都不受控，逐步互動下每一步的品質都無法像腳本一樣被審查/重跑）。Tier 2（MCP）的正確用途是**場景檢查/除錯/讀取現有 `.blend` 資料**（§7.3/§7.8 這類「無視覺內省」用途）跟**抓 Poly Haven 以外的素材庫**（Sketchfab/Hyper3D 等），不是建模的替代路徑——看到「畫一個 XXX」「建一個 XXX 模型」這類建模請求，不管句子裡有沒有提到 Blender，一律先假設走 Tier 1，除非使用者話裡明確要求「用 MCP」「開 Blender 給我看」「用視窗操作」。

### Tier 1 — 無頭模式 CLI（批次/導出/渲染，已實測可用，建模預設路徑）
```powershell
$blender = (Get-Content <workspace>\.capybala\blender-path.txt -Raw).Trim()  # §0 解析協議
& $blender --background --python script.py
```
- 適合：批次建模、GLB/FBX/OBJ 導出、渲染、檔案轉換、場景驗證。不需要 GUI、不需要使用者在場。
- script.py 寫到 `.capybala/test-scripts/`（R050）；stdout 的 print 會直接回傳到 run_powershell 結果，用 `Select-String` 過濾。
- 渲染輸出範例：`bpy.ops.render.render(write_still=True)`（輸出到 //render/ 或 output 設定路徑）。
- **快速 API 探測**：`--python-expr "import bpy; ..."` 一次跑一小段探測碼（見 §9），不用寫完整腳本檔。

### Tier 2 — Blender MCP（只用於場景檢查/除錯/素材庫抓取，**不是建模路徑**，使用者明確要求才用）→ 詳見 §7 使用指南
兩個候選，驗證機 Blender 5.1.2 兩者皆可用：
- **官方 Blender Lab MCP**（https://www.blender.org/lab/mcp-server/ ，源碼 https://projects.blender.org/lab/blender_mcp ）：要求 Blender 5.1+，內建 bpy 文件與手冊檢索工具，工具面含場景/物件摘要、缺檔檢查、linked libraries、截圖、視口導航、渲染、Python 執行。addon 以拖放安裝（需拖兩次：先加 Blender Lab repo，再裝 addon）。
- **ahujasid/blender-mcp**（27k★, MIT，2026-09 仍活躍提交）：社群最主流，支援素材庫（Poly Haven / Sketchfab / Poly Pizza / Hyper3D Rodin / Hunyuan3D），有 `BLENDER_MCP_SAFE_MODE=1` 安全模式（2026-09 新增）。**驗證機已裝**（見 §0）。
- 替代候選：carlosh7/blender-mcp（223 工具，需防選擇器塞爆）、Blender MCP Pro（15 核心工具懶加載，最貼 Capybala 的 tool-selection 上限）。

### Tier 3 — 執行中 GUI 的 Python Console（需要使用者看著畫面時）
- GUI 已開時：Scripting workspace 底部有 Python Interactive Console（實機 OCR 確認存在）。
- 但本工具組**沒有鍵盤輸入工具**，無法可靠注入程式碼到 console → 實際上仍退回 Tier 1（另開無頭實例改同一個 .blend 檔）或 Tier 2（socket）。僅當使用者親手貼程式碼時才用這條。

### Tier 4 — UI 自動化（最後手段，原則上不用）
- 只有 OCR 座標可參考（inspect_window mode="unified"）。視窗已最大化時 OCR 較準（C005）。
- 若真要走：用快捷鍵優先於點擊（見 §3 表），每次動作後重新 inspect 確認狀態，不可盲打連招。

## 2. bpy 核心速查（已對 5.1.2 實測 operator 存在）

實測確認可用：`bpy.ops.mesh.primitive_cube_add`、`bpy.ops.object.mode_set`、`bpy.ops.render.render`、`bpy.ops.wm.save_as_mainfile`、`bpy.ops.export_scene.gltf`。

```python
import bpy

# 清空預設場景（無頭腳本開頭標準動作）
bpy.ops.wm.read_factory_settings(use_empty=True)

# 建模
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "MyCube"

# 材質
mat = bpy.data.materials.new(name="Red")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)
cube.data.materials.append(mat)

# Edit Mode 進出
bpy.ops.object.mode_set(mode='EDIT')   # 或 'OBJECT'/'SCULPT'
bpy.ops.object.mode_set(mode='OBJECT')

# 渲染（Cycles CPU，Arc GPU 不可靠）
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64
scene.render.filepath = "//out/render.png"
bpy.ops.render.render(write_still=True)

# 導出 GLB
bpy.ops.export_scene.gltf(filepath="//out/model.glb", export_format='GLB')

# 存檔
bpy.ops.wm.save_as_mainfile(filepath="//out/scene.blend")
```

**數值化場景內省（視覺驗證的替代品，R051 精神）**——不能看截圖時，印 JSON 當 ground truth：
```python
import bpy, json
state = {
  "objects": [{"name": o.name, "type": o.type,
               "loc": [round(v,3) for v in o.location],
               "dims": [round(v,3) for v in o.dimensions]} for o in bpy.data.objects],
  "materials": [m.name for m in bpy.data.materials],
  "engine": bpy.context.scene.render.engine,
}
print("SCENE_STATE:" + json.dumps(state))
```
渲染任務的 SCENE_STATE 必須**加列渲染與曝光參數**（samples、resolution、view_transform、look、降噪、霧密度、太陽仰角+方位、compositor 是否掛上、**LUMA_STATS 亮度統計**、`engine_requested`/`engine_actual` 與 `exposure_enforced`、`auto_geometry_audit`（含 `framing` 子欄位）、`component_depth`（元件表拆解深度，§11 item 3））——參數化設計值就是無視覺時的 ground truth（R051）。亮度統計寫法見 assets/build_template.py 的 `luma_stats()`（numpy + bpy.data.images，實測與 PIL 結果一致）。

## 3. 選單與工作區結構（實機 OCR + 官方 5.1 文件交叉驗證）

**頂部選單列**：File | Edit | Render | Window | Help
**工作區頁籤**：Layout, Modeling, Sculpting, UV Editing, Texture Paint, Shading, Animation, Rendering, Compositing, Geometry Nodes, Scripting（Ctrl-PageUp/PageDown 切換）
**3D Viewport 標頭（Object Mode）**：Mode 下拉（Ctrl-Tab）、View、Select、Add（Shift-A）、Object 選單；右側：Transform Orientation（逗號鍵）、Pivot Point（句點鍵）、Snapping（Shift-Tab）、Proportional editing（O）、X-Ray（Alt-Z）、Viewport Shading。
**右側面板**：Outliner（Scene Collection → Collection → Cube/Light/Camera）＋ Properties（Render Engine=EEVEE 預設、Sampling、Viewport/Samples、Render 區）。
**底部（Scripting 頁）**：Python Interactive Console 3.13.9。右下角顯示版本號 5.1.2。
**視埠著色提醒**：Solid 模式預設全灰無材質色（使用者常誤以為「沒 render」）——要彩色按 `Z` → Material Preview，或 `F12` 全渲染，`Numpad 0` 看相機視角。

## 4. 預設快捷鍵表（來源：docs.blender.org/manual/en/5.1 官方 Default Keymap，非記憶）

### 通用
| 鍵 | 動作 |
|---|---|
| Ctrl-O / Ctrl-S / Ctrl-N | 開檔 / 存檔 / 新檔 |
| Ctrl-Z / Shift-Ctrl-Z | 復原 / 重做 |
| F2 | 重新命名啟用項目 |
| F3 | Menu Search（萬用操作搜尋，等同 bpy.ops.wm.search_menu）|
| F9 | Adjust Last Operation（調整上一步參數）|
| F11 / F12 | 顯示渲染視窗 / 渲染當前幀 |
| Q | Quick access（我的最愛）|
| Ctrl-Spacebar | 最大化當前 Area |
| X / Delete | 刪除（有確認框 / 無確認框）|

### 編輯共通（3D Viewport、UV、Graph 等）
| 鍵 | 動作 |
|---|---|
| A | 全選 |
| Alt-A / 雙擊 A | 取消全選 |
| Ctrl-I | 反選 |
| H / Shift-H / Alt-H | 隱藏選中 / 隱藏未選 / 顯示全部 |
| T / N | 切換 Toolbar / Sidebar |
| G / R / S | 移動 / 旋轉 / 縮放（拖曳中按 Ctrl=吸附粗刻度、Shift=精細、Shift-Ctrl=更細）|

### 3D Viewport 專屬
| 鍵 | 動作 |
|---|---|
| MMB / Shift-MMB / Ctrl-MMB | 軌視 / 平移 / 縮放 |
| Tab | 切換 Edit Mode |
| Ctrl-Tab | Pose Mode（骨架）或模式切換 pie menu |
| 1 / 2 / 3 | Edit Mode 切頂點/邊/面（Shift 加選）|
| Shift-A | Add 選單（新增物件）|
| `（AccentGrave）| 導航 pie menu |
| Numpad 0/1/3/7 | 相機/前/右/上視角（標準慣例）|

### 動畫 & Python
| 鍵 | 動作 |
|---|---|
| I / Alt-I | 插入 / 清除關鍵幀 |
| Ctrl-C（懸停在 operator 按鈕上）| **複製該操作的 Python 命令**（錄 bpy 腳本神器）|
| Shift-Ctrl-C（懸停在欄位上）| 複製 data path（寫 driver/腳本用）|

### 欄位懸停
Ctrl-C/V 複製貼上單值；Ctrl-Alt-C/V 複製整組向量/顏色；Backspace 重置預設；Ctrl-Wheel 微調。

## 5. 疑難排解來源（scoped search hints）

- 官方開發者文件：`site:docs.blender.org/manual/en/5.1 <topic>`（操作手冊）、`site:docs.blender.org/api/current <module>`（bpy API）
- 官方論壇：`site:blenderartists.org <topic>`
- Q&A：`site:blender.stackexchange.com <topic>`
- 官方 issue tracker（確認 bug）：`https://projects.blender.org/blender/blender/issues`
- MCP 安全/架構討論：`site:devtalk.blender.org blender mcp`
- Reddit：`site:reddit.com/r/blender <topic>`
- Release notes：`https://developer.blender.org/docs/release_notes/5.1/`（5.1 重點：Python 3.13、VFX Platform 2026、Grease Pencil fill 改版、Node Tools 需全域唯一 idname）
- **版本 API 落差**：`site:developer.blender.org/docs/release_notes/5.0 <topic>` + 4.x→5.x Python API 變更頁

## 6. 已知侷限（誠實記錄）

- 精確幾何數學（格點、曲線、對齊）與相機擺位是 LLM 公認弱項，複雜成品需人工收尾。
- 本工具組無滑鼠/鍵盤注入工具 + Blender 無 UIA → GUI 直接操控實際上不可行，別浪費回合嘗試。
- Cycles 在 Intel Arc B370 上 GPU 渲染支援有限，預設 CPU；EEVEE viewport 預覽無此問題。
- 驗證一律用 §2 的 SCENE_STATE JSON + LUMA_STATS 亮度守衛 + §11 Stage C 的 describe_image 評圖，不依賴截圖判讀。
- **訓練語料的 bpy 知識以 2.8–4.x 為主**——寫 5.x 腳本前必讀 §8 落差表，遇陌生 API 先 probe（§9）。
- **訓練語料同樣缺「方向直覺」**：四元數/歐拉角的旋轉方向（前傾 vs 後仰、左 vs 右）LLM 極易搞反且不報錯——一律照 §12 方向公約並用斷言自檢。

## 7. Blender MCP 使用指南（最佳實踐）

來源：ahujasid/blender-mcp README、blender.org/lab/mcp-server、devtalk.blender.org MCP 安全討論串、StraySpark 2026 架構對比。

### 7.1 選用決策

**本節不是建模路徑**——建模一律走 §1 Tier 1 headless bpy，見 §1 開頭強制規則。以下只是「使用者明確要求用 MCP/GUI」或「需要場景檢查/除錯/素材庫抓取」時，兩套 MCP 該選哪個：
- **場景分析/除錯/文件檢索為主** → 官方 Blender Lab MCP（內建 bpy 文件 RAG，5.1+ 限定，驗證機符合）。
- **素材庫/跨工具編排為主**（Poly Haven 以外，例如 Sketchfab/Poly Pizza/Hyper3D/Hunyuan3D）→ ahujasid/blender-mcp。
- **使用者明確要求要用 MCP 互動建模** → ahujasid/blender-mcp，多步編排與可組合性較好；單發專項任務（生成一張貼圖）傳統 addon 更省 token。

### 7.2 安裝（ahujasid 版，Windows）
1. 裝 uv（**官方安裝器，不要用 pip install uv**）：`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`，再把 `%USERPROFILE%\.local\bin` 加進 User PATH，重啟客戶端。
2. MCP client 配置：`{"command":"uvx","args":["blender-mcp"]}`。GUI 啟動的客戶端抓不到 PATH 時報 `spawn uvx ENOENT` → Windows 解法：`"command":"cmd","args":["/c","uvx","blender-mcp"]`，或用 uvx 絕對路徑 `C:\Users\<you>\.local\bin\uvx.exe`。
3. 裝 Blender addon：`uvx blender-mcp install-addon`（自動複製到 addons 資料夾，留 .bak）；或 `uvx blender-mcp addon-paths` 查路徑手動裝。Blender 內 Edit → Preferences → Add-ons → 啟用 **Interface: MCP for Blender**。
4. 連線：3D Viewport 按 `N` → **MCP for Blender** 頁籤 → 勾需要的功能（素材庫等）→ **Start MCP Server**（舊版按鈕名 Connect to Claude）。
5. **只跑一個 MCP server 實例**（Claude Desktop 和 Cursor 不可同時連）。
6. 環境變數：`BLENDER_HOST`（預設 localhost）、`BLENDER_PORT`（預設 9876）、`BLENDER_MCP_SAFE_MODE=1`（**建議開**：阻擋檔案讀寫/子程序/網路/常駐代碼，擋下時回傳原因讓 AI 改寫）、`DISABLE_TELEMETRY=true`（可關遙測）。
7. conda/pyenv 環境衝突：args 加 `"--python","3.11"` + env `UV_PYTHON_PREFERENCE=only-managed`；舊快取出問題跑 `uv cache clean blender-mcp; uvx --refresh blender-mcp`。
8. 官方 Lab 版安裝：addon zip 從 https://projects.blender.org/lab/blender_mcp/releases 拖放進 Blender（**拖兩次**：第一次加 Lab repo，第二次裝 addon），MCP server 用 `.mcpb` bundle 或照 wiki Setup 從源碼裝。
9. Capybala 內建安裝：mcp_install_native(mode=custom, command=uvx 絕對路徑, args=["blender-mcp"]) → mcp_reconnect_native 確認 22 工具；工具清單需重啟 Capybala/新對話才注入。

### 7.3 標準工作循環（每次任務照跑）
1. **先 get_scene_info**（MCP 工具呼叫，不是 Python）拿到 JSON：所有物件、燈光、相機、名稱。
2. **依 scene info 的精確物件名**寫 bpy 代碼（不要猜名字，Blender 會自動加 .001 後綴）。
3. **execute_blender_code** 執行；代碼結尾 print 結果或回傳 SCENE_STATE JSON（§2 模板）供驗證。
4. **驗證**：有視覺能力 → get_viewport_screenshot 比對；無視覺（本工具組常態）→ 用數值內省 JSON 當 ground truth（R051）。
5. **失敗** → 讀 error message 就地修參數重發（debug 循環），不要整個重規劃。
6. 腳本成功但結果不對是常態（「執行成功 ≠ 建出正確的東西」）——**步驟 4 不可省**。
7. **把新主體加進既有場景（get_scene_info 裡已經有其他物件/相機/燈光）時，禁止假設既有 Camera/Light 對新主體仍然有效——新主體尺寸跟既有場景差異大時，必須重新算相機位置與燈光**。判準：新主體最長邊跟既有相機到原點距離量級差超過 3-5 倍，或既有燈光是 POINT/SPOT 這類有效範圍有限的燈種，就要重新算——`T.set_camera(loc, target)` 用新主體實際 bbox 重新算、燈光换成新主體尺度合理的類型與能量（大型建築通常是 SUN，不是 POINT）。問題不在幾何函式本身，而是「相機/燈光沒有跟著新主體重新校準」這個步驟被跳過了。

### 7.4 提示與拆分原則
- 複雜操作**拆小步**：一次 execute_code 做一件事，timeout 錯誤的首要解法就是拆細。
- 具體 prompt 勝過模糊 prompt：「Create a sphere at (0,0,3) with red metallic material, radius 1」優於「加個好看的球」。
- 迭代式建模：每輪「改一步→驗證→下一步」，不要一口氣發 200 行大腳本。
- 官方 Lab 版擅長的分析型 prompt 範例：「Analyze the scene and list outliers: objects with highest polygon count but smaller size from the camera point of view」「Which objects are using material X」「Find objects with bad normals」。
- 素材庫：Poly Pizza 適合 low-poly 遊戲素材（單檔 .glb、可 filter licence="CC0" 免署名；CC-BY 約 69% 需署名，匯入時署名自動寫進物件 custom property `polypizza_attribution`）。

### 7.5 安全（必讀）
- `execute_blender_code` 以**當前使用者權限**執行任意 Python：可刪檔、讀本地路徑、發網路請求。官方與 devtalk 共識：理想環境是防火牆 VM；實務最低要求 → **執行任何 AI 代碼前先存檔**（Ctrl-S），重要專案先備份 .blend。
- 開 `BLENDER_MCP_SAFE_MODE=1` 可擋檔案/網路/子程序類危險代碼，正常建模材質渲染不受影響。
- 官方 Lab 版的 weak_sandbox.py 如其名——不是安全邊界，只擋明顯惡意操作。
- 高階 MCP 工具（inspect/create primitive/material）應是預設路徑，raw Python 是升級路徑；能不用 execute_code 就不用。

### 7.6 疑難排解（README 官方表）
| 問題 | 解法 |
|---|---|
| 連線失敗 | 確認 Blender addon 的 server 已 Start；**不要**自己在終端跑 uvx（client 會自己拉）；第一發命令偶爾不通，重發即可 |
| Timeout | 把請求拆小步 |
| Poly Pizza 下載被 Cloudflare 擋 | static.poly.pizza 擋資料中心/VPN IP，與 API key 無關；換一般網路重試，或手動下 .glb 走 File → Import → glTF 2.0 |
| 一直連不上 | 重啟 Claude/client **和** Blender addon server 兩邊 |
| addon 升級 | 重跑 `uvx blender-mcp install-addon` → Blender 內 disable/re-enable addon → 重新 Start MCP Server |
| **連線逾時，且不確定是不是 Blender 根本沒開** | 這是跟上面幾列**不同的故障**——上面幾列都假設 Blender GUI 已經在跑，只是 addon/server 端沒配合。先用 `Get-Process -Name blender -ErrorAction SilentlyContinue` 確認進程存不存在；真的沒有才是這一列的情境，見 §7.8——AI 可以自己啟動 Blender，不用假設「addon 沒 Start」反覆重連一個根本沒有進程在監聽的 port |

### 7.7 現成資產範圍：僅限環境/自然元素強制抓現成，家具道具改為預設手建

**新公約——依物件性質分兩類，只有一類仍然強制抓現成**：

1. **環境/自然元素（強制抓現成或程序化生成，維持原規則不變）**：
   - **HDRI／天空／環境光罩**：沒有例外，一律用 `assets/asset_fetch_lib.py` 的 `fetch_hdri()` 抓 Poly Haven 現成 HDRI，不手調 Sky Texture 節點（效果明顯生硬）。HDRI 是環境光源不是可特寫檢視的物體，不會有寫實度並排衝突的問題。
   - **樹木／花草／地形／石頭等自然元素**：優先用 `assets/nature_lib.py`（§18）程序化生成（Sapling Tree Gen / ANT Landscape / Rock Generator / GN 散布），沒有合適的程序化選項時才用 `asset_fetch_lib` 抓現成模型頂替。**禁止**用 primitives 手搭圓柱+球冠充樹/石頭（塑膠感，§10.1 環境敘事軸不合格）。這類元素本身形態自由度高、觀眾對其「精確幾何」的期待值低，程序化/現成的自然變化感反而比手建規則圖形更好看，不會有寫實度落差問題。
2. **家具／道具／裝飾等「設計場景裡的其他實體物件」（改為預設手建，抓現成降級為可選手段）**：
   - **預設做法**：跟設計主體用同一套建模語言手建——套用 §17 `mat_lib.py`/`detail_lib.py` factory，讓家具的材質/顏色**真正落在** Stage A 規劃的色票裡（這是相較舊版的額外好處：解決了色票對不上的問題），擬真度也跟場景其餘部分一致，不會有「這裡特別寫實、那裡特別簡陋」的違和感。
   - **`asset_fetch_lib.fetch_polyhaven_model()` / `polyhaven_search()` 仍然保留、仍然可用**——但改成**依任務判斷的可選工具**，不再是預設路徑。適合考慮抓現成的情境：使用者明確要求「用真實家具/寫實資產」、任務本身就是以寫實度為目標（例如產品攝影棚背景道具）、或某件道具極其複雜、手建成本遠超任務預算（例如需要精密機構的家電）。抓現成時仍要留意：材質不會自動對齊色票，且會與場景其餘手建部分產生擬真度落差，這是明知的取捨，不是免費的升級。
   - **RAP HARNESS**（`agent.v2.rapHarnessEnabled`，Retrieve→Adapt→Present 資產策略）目前由使用者自行開關，本節不因此變更其預設值——RAP HARNESS 若開啟時傾向抓取，是使用者自己的選擇，跟這裡「預設手建家具」的一般性建議是兩件事，互不覆蓋。

**技術路由（保留，供環境元素與「使用者判斷後決定要抓」的家具兩種情境使用）**：
1. **`assets/asset_fetch_lib.py`（§19）**——直接打 Poly Haven 公開 API（零金鑰、零安裝、CC0 免署名），headless 一次搞定：
   - `fetch_hdri(asset_id, resolution)` → 下載 HDRI 並直接套進 World 環境貼圖（實測：套用後渲染 LUMA mean=122，證明真的在打光）。
   - `fetch_polyhaven_model(asset_id, resolution)` → 下載 .blend 檔並 append 進場景（實測：`ArmChair_01` 附完整幾何，3230 verts，0.848×0.766×1.065m 寫實家具尺寸）——**用前先讀本節「新公約」判斷這次是不是真的適合抓現成**。
   - `polyhaven_search(query, asset_type)` → 本地端過濾找資產 id（Poly Haven 的 models 分類真的有家具，categories 含 "furniture"，不是只有 HDRI/材質）。
2. **blender-mcp（§7.2，Tier 2）作為 Poly Haven 以外的補充**——Sketchfab/Poly Pizza/Hyper3D 這些平台沒有公開 REST API 可以像 asset_fetch_lib 那樣直接打，才需要走 MCP 這條路（需要 GUI session）；Poly Haven 本身用 asset_fetch_lib 直接抓更快、不用開 GUI。
3. **禁止**為了「省事」自己手調 HDRI 以外的天空打光方案。
4. **只要用 `asset_fetch_lib.fetch_polyhaven_model()` 抓了任何物件、set location 之後，強制跑 `build_template.py` 的 `assert_within_room()` / `assert_grounded()`**——CALIB/正式渲染兩關只驗證曝光/比例，不檢查擺位是否合理，純靠人眼事後挑，程式碼沒有防線。**手建的物件同樣建議跑這兩個斷言**（放置錯誤不分手建或抓現成，只是抓現成的來源模型陌生度較高、實測更容易踩坑）：
   - set location 後呼叫 `T.assert_within_room(obj, room_bounds, label)`（`room_bounds` 從 `config.PROPORTIONS` 的房間尺寸算，一般是以房間中心為原點的 `((-w/2,w/2), (-d/2,d/2), None)`——z 軸通常不檢查，交給下面的 `assert_grounded` 專門處理）。
   - 任何擺在非地板（z=0）支撐面上的物件（吧台台面、桌面、層架），呼叫 `T.assert_grounded(obj, expected_base_z, label)`——`expected_base_z` 必須是**實際量到**的支撐面世界頂面 z（例如讀 `Bar_Top` 物件的世界頂點算 max z），不能用 config 裡「設計上應該在哪」的假設值去反推。
   - `assets.py`（每個場景包的斷言檔，§16）在既有的比例/主體存在檢查之外，把上面兩個呼叫也一併寫進 `verify_scene()`——CALIB 通過不代表擺位合理，兩者是獨立的檢查維度。

### 7.8 AI 自行開啟 Blender + 收尾非視覺 Probe

**背景**：實測發現 AI 遇到 blender-mcp 連不上時，常卡在「以為是 addon 沒 Start」反覆重連，實際上是 **Blender 進程根本沒有在跑**——這是兩種完全不同的故障，§7.6 舊表只涵蓋「Blender 已開但 addon/server 沒配合」這一種。

**明文授權**：AI 有權自行啟動 Blender.exe，不需要每次都先問使用者——啟動一個本機應用程式視窗，風險並不高於本 skill §0 已經授權的「自己解析路徑、自己跑 headless CLI」。

1. **連線前先確認進程是否存在**，不要看到逾時就直接假設是 addon 沒 Start：
   ```powershell
   Get-Process -Name blender -ErrorAction SilentlyContinue
   ```
2. **沒有結果才是真的沒開，自己開，非阻塞**：
   ```powershell
   Start-Process -FilePath $blender -ArgumentList "`"$blendPath`""
   ```
   帶一個 `.blend` 路徑當參數＝直接開那個檔案（沒有既有 `.blend` 就開空場景）。`Start-Process` 立刻返回，不會卡住對話——**不要**加 `--background`，那是 Tier 1 無頭模式，這裡要的是有 GUI 視窗的互動實例。
3. **等待 MCP server 就緒**：驗證機的 addon 是「GUI 開啟時自動監聽」（見 §0），多數情況不需要使用者手動點 Start——啟動後輪詢連線（例如每 2 秒重試一次 `get_scene_info`，最多等 30-40 秒讓 Blender 完成啟動+載入場景）比一次性判定「連不上」更可靠。
4. **輪詢逾時才問使用者**：提示「Blender 已開啟，麻煩到 3D Viewport 按 N → MCP for Blender 頁籤 → Start MCP Server」——這是舊 addon 版本或使用者關掉自動監聽時的剩餘情境，不要一開始就跳這步。

**用途一：收尾非視覺 Probe（建議併入 Stage C，補「只靠 describe_image」的盲區）**

§7.3 步驟 4 已經確立「無視覺時用數值內省 JSON 當 ground truth」（R051）這個原則，但目前只用在 Tier 2 互動建模的過程中——同一個原則同樣適用於 **Tier 1 無頭批次建完的最終成品**：describe_image 只看得到「渲染出來長什麼樣」，看不到「場景資料本身對不對」——World 有沒有真的接上 HDRI 環境貼圖、玻璃材質的 Transmission 數值是不是真的設到位、相機/建築的垂直軸是不是真的照 §12 方向公約走、有沒有物件材質槽是空的——這些都是渲染圖肉眼不一定看得出來、但 `execute_blender_code` 幾行 Python 就能直接查到的資料層級問題，不需要模型有視覺能力。

**場景包任務不需要臨時貼片段**：`assets/scene_pkg/inspect.py` 是這套 probe 的常駐版（§16.1 第七件）——對任一個 `.blend` 跑一次，就得到物件/材質/世界/燈光/相機的結構化 JSON（含空材質槽、Transmission 數值、母版是否忘記隔離、構圖覆蓋率、穩定 ID 標籤），寫到 `--json` 指定的路徑，可跨 session 逐輪比對；臨時貼片段只留給這支腳本沒涵蓋的一次性問題。

**場景資料自描述（自動、不需要額外步驟）**：`write_scene_provenance()` 把本次建置的參數、量測數據、鏡頭清單寫成場景自訂屬性（`bp_params`/`bp_metrics`/`bp_shots`）——`.blend` 檔本身就帶著「這是什麼、用什麼參數建的」，日後（同一對話後續輪次、別的 session、甚至交給別人）開檔即可追溯，不必回頭翻對話或腳本；`write_build_report()` 另外在 `<OUT_DIR>/report.json` 落一份建置報告（逐樓層高度/寬度/樓地板面積、逐物件面數與材質）。`main()` 會自動呼叫兩者，呼叫端不需要做任何事——驗收時把 `report.json` 當「建了什麼」的帳本、`inspect.py` 的 JSON 當「場景裡實際有什麼」的實測，兩份一起看。

正式渲染完成、`.blend` 已用 `save_as_mainfile()` 存檔（`build_template.py` 內建這步）後，照上面 1-3 步開啟這個 `.blend`，跑一次收尾 probe，例如：
```python
# execute_blender_code
import bpy
world = bpy.context.scene.world
env_nodes = [n for n in world.node_tree.nodes if n.type == 'TEX_ENVIRONMENT']
print("HDRI_LOADED:", bool(env_nodes) and env_nodes[0].image is not None)

for mat in bpy.data.materials:
    bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.use_nodes else None
    trans = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission") if bsdf else None
    if trans:
        print(mat.name, "transmission=", trans.default_value)

empty_slots = [o.name for o in bpy.data.objects if o.type == 'MESH' and len(o.data.materials) == 0]
print("object_count=", len(bpy.data.objects), "empty_material_slots=", empty_slots)
```
把 probe 結果併入 SCENE_STATE JSON（§2）當作跟 LUMA_STATS 平行的一個驗證維度，而不是只在 Stage C 文字回覆裡口頭提一句——這樣同一個 `.blend` 之後（同一對話後續輪次，或使用者自己重新開啟）仍然查得到當時驗證過什麼。

**用途二：完工展示（加分項，非強制）**——Stage C 評圖完成、使用者沒有要求修改之後，除了照現有慣例回報 render PNG 路徑，可額外照上面第 1-2 步用 Blender GUI 打開最終 `.blend`（純展示用途可省略第 3-4 步的 MCP 連線等待）——比只給檔案路徑更直觀，使用者接下來想自己微調也已經開好視窗。找不到 `.blend`（例如任務只要求純渲染）或使用者已經開著 Blender 忙別的事，就略過，不要為了展示硬生生搶走使用者原本的視窗焦點。

## 8. Blender 5.1 API 落差表（實戰驗證）

訓練語料/網路教學的 bpy 幾乎全是 **2.8–4.x** 時代；Blender 5.x 做了多處破壞性變更，每個落差都要在執行期爆錯→probe→patch→重跑（單點耗 1–3 回合）。以下是**已在驗證機 5.1.2 實測確認**的落差，寫腳本前對照：

| # | 舊寫法（4.x 語料） | Blender 5.1 實際 | 錯誤形態 |
|---|---|---|---|
| 1 | `light.data.radius = 0.4`（點/聚光） | **屬性已移除** → 用 `light.data.shadow_soft_size` | AttributeError |
| 2 | `view_settings.look = "Warm"`（Filmic） | Filmic 無 Warm look；AgX 的 look 枚舉**帶前綴**：`"AgX - Punchy"`（不是 "Punchy"） | 賦值無效/枚舉錯 |
| 3 | Nishita 天空用 `sky.inputs["Sun Elevation"]` | **參數改掛節點屬性**：`sky.sky_type = "MULTIPLE_SCATTERING"`、`sky.turbidity`、`sky.ground_albedo`（sky_type 僅剩 4 種舊枚舉，無 "NISHITA" 字面值） | KeyError |
| 4 | 合成器 `scene.use_nodes=True; cnt = scene.node_tree` | **Scene.node_tree 已移除** → `cnt = bpy.data.node_groups.new("Name", "CompositorNodeTree")` + `scene.compositing_node_group = cnt`（屬性名是 **compositing**_node_group，不是 compositor_node_group） | AttributeError |
| 5 | `glare.glare_type = 'FOG_GLOW'`（節點屬性+大寫枚舉） | Glare 的 **Type/Size/Threshold 改為 input sockets**，枚舉是**含空格的顯示名**：`glare.inputs["Type"].default_value = "Fog Glow"` | AttributeError/枚舉錯 |
| 6 | 合成器 group 末端接 `CompositorNodeComposite` | group 內**不存在 Composite 節點** → 用 `NodeGroupOutput`，且**必須先**建 interface OUTPUT socket（`cnt.interface.new_socket("Image", socket_type="NodeSocketColor", in_out="OUTPUT")`），NodeGroupOutput 才有對應輸入 | 節點不存在 |
| 7 | `mat.use_nodes = True` | 5.1 仍可用，但噴 Blender 6.0 deprecation warning（噪音，不影響）；新代碼可改 `mat.node_tree` 直接存在即為 True | 警告 |
| 8 | World 體積霧（Volume Scatter 接 World Output）可與 Sky 背景並存做「上帝光」 | **無限介質吞掉 Sky 背景光**：背景光穿過無窮距離散射體，透射率指數衰減→0 → 整圖全黑。實測同參數：無霧 mean=197.9，霧 density 僅 0.008 → **mean=0.3（100% 死黑）**。**白天/有 Sky 背景的場景禁用 world volume**；真要霧/上帝光 → 建有限域 volume domain box（cube + volume scatter material）包住場景 | 整圖全黑、不報錯 |
| 9 | `bpy.ops.object.transform_apply(scale=True)` 只烘 scale，loc/rot 保留 | **loc + rot + scale 全部烘進 mesh**，物件 transform 變 identity（實測：apply 後 location=(0,0,0)、quaternion=(1,0,0,0)）。方向/位置驗證**不能讀 object.location/rotation**，要用世界座標頂點：`[o.matrix_world @ v.co for v in o.data.vertices]`（讀前先 `bpy.context.view_layer.update()`）。**連帶坑**：母版/實例模式下「把母版放 z=10000 高空避鏡」失效——location 被烘成零，母版全部掉回原點入鏡；母版隔離一律用 `hide_render=True`（範本 `park_master()`/`instance()` 已內建配套，§14）。**第二個連帶坑**：範本 `add_box()` 會呼叫這行、`add_cyl()` 修正前不會——同場景混用兩種 primitive 當 host 母版時 origin 慣例不一致，instance() 的 z 補償公式得依 host 用哪個 primitive 建分兩套算。已修正 `add_cyl()` 也呼叫此行、origin 慣例統一（見 build_template.py `add_cyl()` docstring），之後 host 母版不分 primitive 種類、instance() 只用一套 z 算法 | 驗證邏輯靜默失效；母版入鏡；（已修正）母版懸空/深埋 |
| 10 | `Quaternion((1,0,0), +θ)` 直覺上是「往後仰」 | **右手定則**：繞 +X 正角把 +Z 頂部帶向 **-Y**。probe 實測：`Quaternion((1,0,0), radians(9)) @ Vector((0,0,1))` → y=-0.156。若主體「正面朝 -Y（相機側）」，正角=**前傾**（椅背倒向坐者＝錯誤方向），負角=後仰。方向一律用命名函數（assets 範本的 `lean_back_quat()`/`lean_fwd_quat()`），禁止手寫符號+靠直覺 | 方向錯、不報錯 |
| 11 | 兩塊路面 box 頂面同 z 疊放「沒差」 | **Z-fighting**：同高度共面重疊在 Cycles 渲染成隨機暗塊/閃爍（實測：路口中央純黑正方形）。正交道路**必拆段**——路口區域只保留一層路面，各路臂只鋪到路口邊界為止；任何共面貼合（貼花、標線）改用微小 z 偏移（≥0.005）或 shrinkwrap/decal | 暗塊、不報錯 |
| 12 | GN 散布節點組把 instance 雲直連 GroupOutput | **宿主幾何被「取代」**：輸出前必須 `GeometryNodeJoinGeometry` 合併「GroupInput（宿主）+ instance 雲」再接 GroupOutput，否則宿主地形評估 0 頂點、渲染只剩天空（Round 13 端到端實測，nature_lib 已內建） | 整景空、不報錯 |
| 13 | GN CollectionInfo 引用 `hide_render=True` 的母版 | **渲染評估時直接跳過** → 散布結果空。散布源母版改「遠處停放」（loc x=300+ 相機視窗外）隔離——§14 hide_render 公約的唯一例外 | 散布不出、不報錯 |
| 14 | 隨機值節點叫 `GeometryNodeRandomValue`；新 node group 自帶 GroupInput/Output | 真名 **`FunctionNodeRandomValue`**（GeometryNode* 前綴搜不到），4 個輸出 socket 同名 "Value"（要用 bl_idname+enabled 挑）；新建 `GeometryNodeTree` **不含** GroupInput/Output，必須 `gn.nodes.new("NodeGroupInput")` 手動建 | AttributeError/KeyError |
| 15 | `direction.to_track_quat("Z","Y")` 讓相機看向目標 | 相機前向是 **-Z**：`to_track_quat("Z","Y")` 實測 forward·direction = **-1.0**（相機背對目標，拍出來全是天空）。一律 `to_track_quat("-Z","Y")`，建完用 forward 軸 dot 斷言 ≈1 自檢 | 拍空、不報錯 |
| 16 | `obj.modifiers.new(name, "ARRAY")` 之後只設定 `use_constant_offset`/`constant_offset_displace` 就假設「只會往那個方向疊」 | **新建 Array modifier 的 `use_relative_offset` 預設是 `True`**（`relative_offset_displace` 預設 `(1,0,0)`，即物件自身 X 尺寸的 100%），沒有手動關掉的話，Constant Offset 跟這個預設的 Relative Offset 會**同時疊加**——每疊一份不只往 constant offset 的方向移動，還會額外沿物件自身 X 寬度平移一次，兩者向量合成的結果是**斜線爬升**，不是筆直的一排（2026-09-09 住宅大樓 20 層陽台/冷氣/立面實測：只想要垂直疊樓層，卻疊出對角線「天梯」，且每個物件斜的方向/角度都不同——因為方向取決於各自的寬度、以及該物件是否還帶了其他旋轉，例如冷氣機因為 `join_objs()` 把帶 90° 旋轉的風扇圓柱當作合併目標，局部 Z 位移被那個旋轉轉到別的世界軸，疊加上這個預設 Relative Offset 又多一個方向的位移，兩層問題疊在一起）。**任何只要垂直/單軸疊樓層、疊窗、疊陽台的 Array modifier，建立後必須明確 `mod.use_relative_offset = False`**——這不是可以省略的預設安全值，Blender 的實際預設剛好是「開」。`shape_lib.py` 的 `linear_array()` 刻意保留 `use_relative_offset=True` 是另一種正當用途（沿物件自身尺寸接龍排列螺栓/欄杆），跟這裡「只要 constant offset」的情境要分清楚，不要把那支函式的寫法直接套過來。`building_lib.assemble_building()` 從根本上避開這個坑——它不是用 Array modifier 疊樓層，是逐層直接生成真正的幾何，疊樓層/疊陽台/疊冷氣一律優先用它，不要自己疊 Array modifier | 物件排成對角線「天梯」、不報錯、CALIB 曝光可能正常通過 |
| 17 | `bm.faces.new(...)` 建完面就馬上對它跑 `bmesh.ops.inset_individual(..., depth=...)` | **剛用 `bm.faces.new()` 建出來的面，法向量預設是 `(0,0,0)`**（空向量），不會自動算好——要等明確呼叫 `bmesh.ops.recalc_face_normals()` 或 `bm.normal_update()` 之後才有真正的方向。`inset_individual()` 的 `depth` 參數是沿著**面目前的法向量**位移，用一個零長度向量位移，數學上等於位移量恆為 0——`thickness`（内縮寬度）跟 `depth`（内推深度）兩者都會受影響，實測結果是**面沒有內縮、也沒有內推，`inset_individual` 看起來像完全沒執行過，但函式呼叫本身零報錯、回傳值看起來也正常**（2026-09-09 商辦大樓 skill 規範查核意外挖出：`assemble_building()` 逐層迴圈裡對剛建好的牆面直接呼叫 `inset_individual()` 挖窗，但整個函式只在最後、迴圈跑完、屋頂/地板封面都建完之後才呼叫一次 `recalc_face_normals()`——逐層挖窗的當下每一面的法向量都還是空的。結果是「窗戶」跟「牆」材質確實照 `window_ratio` 分好了，CALIB 曝光、assertions 全部 PASS，肉眼看渲染圖也未必看得出異樣（尤其配合高反光玻璃材質，反光本身就能製造出立體感的錯覺），但直接打開 `.blend` 量測窗戶頂點世界座標，會發現整片牆完全平坦、window_ratio 對應的內縮/內推深度是 0——這是一個「渲染圖可能看起來沒問題、但幾何本身是錯的」的陷阱，光憑 Stage C 的 describe_image 評圖抓不出來，要嘛信任這個已修正的版本，要嘛比照 §7.8 的 probe 手法直接查頂點座標）。**已在 `building_lib.py` 修正**：`assemble_building()` 現在每一層建完牆面後、呼叫 `inset_individual()` 前，先對**這一層自己的面**跑一次 `recalc_face_normals()`（只對這批面做，不是整個 `bm`，維持每層迭代的開銷不變）。**這個坑不是 `assemble_building()` 專屬**——任何自己手刻 bmesh、對剛建出來的面立刻做「沿法向量位移」類操作（`inset_individual` 的 `depth`、`extrude_face_region` 的位移方向等）都要先確認法向量是不是真的算過，不要預設 `bm.faces.new()` 已經幫你算好 | `inset_individual`/其他依賴面法向量的 bmesh 操作看起來完全沒生效、不報錯、下游驗證（CALIB/assertions/描述評圖）可能全部正常通過 |

| 18 | 用 `v.co[i] *= scale`（任何以**世界原點**為中心的頂點縮放/旋轉）做收分/漸縮/收窄 | **頂點座標就是世界座標**（§8 #9 的 `transform_apply` 已把 loc 烘進 mesh），不是零件局部座標——以原點為中心縮放垂直軸會連帶**平移**整個斷面（`scale` 離 1 越遠、零件離原點越遠，位移越大），而物件 transform 仍是 identity，任何讀 `obj.location`/`rotation` 的檢查都看不到。**垂直軸縮放一律以「該斷面自身的外框中心」為基準**（`shape_lib.taper()` 已按此實作：先算垂直兩軸各自的 min/max 中點，再以該中點縮放） | 零件被移走/壓扁、位置與厚度同時跑掉，位置類斷言與 CALIB 照樣全過、不報錯 |
| 19 | Glare 節點照 4.x 的用法寫（`glare.mix`、拿 `Size` 當鬼影張數、`glare_type` 屬性） | 5.1 實測四點：① **`mix` 屬性不存在**（RNA 屬性列與 input sockets 都沒有），混合量走 **`Strength`**（與 `Size` 不同——>1 仍單調增益）；② **鬼影張數是 `Iterations`**，`Size` 只作用於 Bloom／Fog Glow 且是 **0–1 的 FACTOR：「賦值不夾、評估時飽和」**——1.0/2.0/7.0 三組渲出的統計逐位元相同（＝覆蓋整張圖），`PRESETS` 既有三組的 5/7/9 全部落在飽和區、旋鈕形同常數，要真的縮小暈染必須填 <1（例如 0.25）；③ 合成器節點有三個輸出 `Image`/`Glare`/`Highlights`（取 `Glare` 得純光暈）；④ **節點移除會連帶移除連線**——逐鏡切換後不重接末端＝下一鏡整張全黑（實測 mean 0.3）。`Threshold` 是**原始亮度值**不是 0–1（RNA soft_max 10000），要夾在星點峰值與日盤亮度之間（實測可用 40–60）。正確用法＝`setup_lens_flare()`（整條鏈重建、末端一定重接）。**太空場景不使用這支**——鬼影鏈在真空背景上讀成髒點與塊狀物（§10.5 #8） | 調了 `Size` 畫面完全不變／`mix` 只能印 WARNING／下一鏡全黑 |

**曝光陷阱總表**：
1. **全黑**：world volume + Sky 背景（#8，主因）；或太陽背光（azim 與相機異側）；或仰角過低 + AgX 壓暗部。
2. **過曝**：棚拍三點式能量憑感覺填（Key 160W 實測過曝）；Sky strength 白天 1.0；Glare threshold 過低全圖泛光。椅子 v2 修正後 mean 仍 191.5（使用者實感「過亮過曝」）。
3. **防範**：一律用 assets/build_template.py 的 PRESETS 實測配方 + LUMA_STATS 守衛（§10.2 目標帶），禁止手填能量值。

## 9. 防禦性編碼守則（避免 API 落差浪費回合）

1. **陌生 API 先 probe，不要憑記憶寫**：用 `--python-expr` 一次跑小段探測碼確認屬性/socket/枚舉存在再寫進正式腳本：
   ```powershell
   & $blender --background --python-expr "import bpy; g=bpy.data.node_groups.new('T','CompositorNodeTree'); gl=g.nodes.new('CompositorNodeGlare'); print('PROBE:', [i.name for i in gl.inputs])"
   ```
2. **非關鍵效果一律 try/except + log 降級**（天空、合成器、DoF）：失敗要 print WARNING 並降級到保底效果，禁止 silent catch（PROJECT-RULES），也禁止整個腳本因一個裝飾效果炸掉。
3. **骨架一律從 skill asset 取**：`copy_skill_resource_native(source="assets/build_template.py")` → 存為 `.capybala/test-scripts/build_template.py`（凍結模組），場景腳本 import 引用之（§9.6.1）。**禁止**引用工作區暫存腳本當範本（暫存檔會被刪），禁止從空白憑記憶重寫，也禁止把模板函數全文複製進場景腳本。
4. **SCENE_STATE JSON 帶渲染+曝光參數**（§2）：view_transform、look、samples、霧密度、太陽仰角+方位、compositor_bloom、**LUMA_STATS** 都要回傳——執行期爆錯之外，「跑通但效果錯」只能靠這些數值抓。
5. 新踩的坑 → 立即 `save_app_lesson_native`（process=blender）並考慮補進本表（update_skill_native）；若範本本身需要修正，直接 patch `assets/build_template.py`（skill asset 是活的，用 update_skill_native 或經使用者同意後改）。

### 9.5 渲染調用規範（強制）

1. **Preflight 先行**：投入完整腳本前，先花 5 秒確認 blender.exe 能跑：
   ```powershell
   & $blender --background --python-expr "import bpy; print('PREFLIGHT OK', bpy.app.version_string)"
   ```
   （`find_blender.ps1` 已含 --version 驗證，跑過 cascade 可視為 preflight 通過；但換了新腳本環境/新機器時仍建議跑一次。）
2. **禁止在渲染前另外下 `Remove-Item`/`rm -f` 清空 render.png/scene.blend**：刪檔案這類 destructive shell 操作在無人值守時會卡在權限確認上鎖死流程。`bpy.ops.render.render(write_still=True)` 本來就直接覆寫 `render_path`，不需要額外刪除步驟；stale-output 防呆交給規則 3 的 mtime 新鮮度斷言。`main()` 額外把每次渲染備份到 `<OUT_DIR>/history/render_<時間戳>_<calib|full>.png`，順便保留完整渲染歷程。
3. **describe_image 前斷言檔案新鮮度**：render.png 的 mtime 必須晚於本次 blender 進程啟動時刻、size > 100KB，兩者任一不成立就是評到舊圖/半成品——禁止直接評。
   ```powershell
   Get-Item <OUT_DIR>\render.png | Select-Object LastWriteTime, Length
   ```
4. **進程模式二選一，禁止混用**：
   - **首選**：前台 run_powershell + `timeout_ms=0`（渲染是有限時任務，1080p/256spp CPU 約 2–5 分鐘），stdout 直接拿到 SCENE_STATE/LUMA_STATS。
   - 备选：background=true + 輪詢 log 檔（僅當預期 >10 分鐘）。
   - **禁止**前台失敗後不讀 stderr 就改背景重發。前台快速返回（<60 秒）幾乎必然是腳本錯誤，先讀輸出再動作。
5. **佈局預覽通道（EEVEE）與成品通道（Cycles）分開**：`T.set_engine("eevee")`（或環境變數 `BLENDER_TEMPLATE_ENGINE=eevee`）改走 EEVEE，用途是「幾何對不對」的快篩——構圖/比例/穿模/Z-fighting/漏件十秒內就有答案，不必等 Cycles 的完整渲染（5.1 的引擎識別字是 `BLENDER_EEVEE`；換機器/換版本時先用 §9 的 probe 確認 headless 真的出得了圖，不要假設）。三個限制照抄自 `set_engine()` docstring，不可忽略：① `mat_lib.make_glass()` 這類 Transmission=1 材質在 EEVEE 下不走同一條路徑，玻璃顏色/透明度不可信；② 沒有 Cycles 的完整 GI 與降噪，陰影/間接光落差大；③ 曝光守衛在 EEVEE 模式下**只報告不擋**（`SCENE_STATE.exposure_enforced=false`）。**禁止**拿預覽圖的 LUMA 值去調正式配方的能量——正確順序是「EEVEE 迭代幾何定案 → 切回 cycles 跑 CALIB 校曝光 → 正式渲染」。

   **唯一例外：3 渲 2／賽璐璐路線（`styles/genre/anime-cel-daylight.md`）EEVEE 就是成品引擎，不是預覽**——`mat_lib.make_cel()`/`make_cel_advanced()` 的 `Diffuse → ShaderToRGB → ColorRamp → Emission` 是 **EEVEE 專屬節點路徑**，切回 cycles **不報錯但會安靜地做錯**（實測：主體最亮的 base 階整片消失、畫面塌到 mid 階，色票全歪）。所以這條路線**不套用**上面「EEVEE 迭代 → 切 cycles 校曝光 → 正式渲染」的順序，而是 `set_engine("eevee")` 直接出成品 ＋ `set_view_transform("standard")`（並確認 `scene.view_settings.view_transform` 真的等於 Standard）＋ 描邊二選一（`setup_selective_outline()` 預設／`setup_freestyle()` 全場單線寬）＋ 選配 `setup_anime_post()` 局部泛光。

   此時品質保證**不是** LUMA 帶（EEVEE 下 `exposure_enforced` 仍是 `false`，曝光問題只報告不擋），而是**色階數與各階佔比**：量 `T.audit_band_count(render_path, max_bands=4)`（`VIEW_TRANSFORM == 'Standard'` 時 `main()` 會自動跑 soft 版並寫進 `SCENE_STATE.band_audit`，stdout 另印一行 `BAND_STATS:`）。**判準依材質數**：實測單一 cel 材質 3 階、三材質 5 階、程序化寫實材質 7 階（`max_bands=4` 是「單一材質面」的判準，多材質全景請上調、或給 `roi` 只量一個面）；而且**階數對色調映射不敏感**——AgX 誤用實測階數不變、只有色值歪（#E84828 → #C84838），要驗 AgX 誤用得另外比對 `top[].hex` 與風格卡色票。**禁止**只憑「沒有觸發曝光警報」判定三渲二成品合格——那條守衛在這條路線上本來就不生效。

### 9.6 腳本組織指引（消滅「8 分鐘盲寫 + 10 連發 patch + 12 分鐘靜態覆盤」）

1. **模板引用不複製（P6，Round 6 實錘）**：`copy_skill_resource_native` 取 build_template.py 存到 `.capybala/test-scripts/build_template.py` 後**視為凍結模組**，場景腳本 `build_<task>.py` 用 import 引用，**禁止把模板函數全文複製進場景腳本**：
   ```python
   import os, sys
   os.environ["BLENDER_TEMPLATE_OUT"] = OUT_DIR      # 環境變數必須在 import 前設好
   os.environ["BLENDER_TEMPLATE_PRESET"] = "outdoor_golden"
   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
   import build_template as T

   def my_subject() -> dict: ...   # 只寫場景工廠函數與 layout（§9.6.2 結構）

   T.main(subject_fn=my_subject, preset_overrides={"sky_strength": 0.21})
   ```
   **雙重維護且必然漂移**。引用模式下腳本縮到 ~1/3、模板修正天然全域生效。曝光微調一律經 `preset_overrides` dict 傳入，不改模板本體；模板 copy 進工作區後如需修正，**改 skill asset 本體再重新 copy**（單一真相源）。
2. **元件工廠結構**：每類資產一個 `make_xxx()` 函數（make_traffic_light/make_sign/make_streetlamp…），函數內自帶方向斷言（§12）隨建隨驗；layout 段只負責擺位，不混幾何細節。**中大型/需迭代任務一律升级为場景包六件拆分（§16.1）**——工廠住 geometry.py、擺位住 layout.py、參數住 config.py，改一處只碰一檔；命名照 §16.2 前綴制（Mst_/Inst_/Mat_），修改定位照 §16.3 查表。
3. **以跑代審（P5，強制）**：**腳本寫完後的第一個動作必須是跑 `--calib`（~6-10 秒），禁止先對整份腳本做靜態覆盤**。calib 自檢斷言 6 秒就能 fail fast 攔下這類錯誤。靜態覆盤只允許針對 calib 報出的**具體錯誤**做局部檢查，禁止無錯誤前提下的整腳本推理審查。
4. **分段驗證，不等全寫完**：layout 完成（物件就位、相機燈光設定好）就先跑 `--calib` 快渲——方向錯、共面 Z-fighting、曝光帶外都在這一步被抓到，而不是整份寫完、正式渲染 2 分鐘後才發現。
5. **修幾何靠 probe 不靠連發 patch**：號誌臂/燈頭方向這類空間關係，先用 `--python-expr` 印出實際世界座標頂點確認，再一次改對；禁止「改一處→跑一回合→再改」的盲修循環。
6. **調參數後必須讀回實測值（強制）**：patch 回報成功、語法正確、渲染照跑、斷言全過，都不代表那段程式碼真的在跑。實測案例：同一符號有兩份同名函式，新版被貼在舊版 `return` 之後成了死碼，於是**改了參數、量出來的數字一字不變**（仍是舊公式的精確值），白調好幾輪。規則：任何「調參數」的修改都要有一段讀回量測值的驗證；出現「參數改了、輸出數字沒動」→ 第一個懷疑對象是**同一符號的第二份定義／`return` 之後的死碼**（用 `^def <name>` 清單核對函式數量，regex 要帶 `m` flag）。

## 10. 最低品質標準（V3 Floor）——任何 3D 模型請求的強制下限

**第一次交付就必須達到下表水準**，不允許先交陽春版再等使用者要求升級。v3 是「最低標準」，不是「驚豔標準」。

### 10.1 七軸最低規格（缺任一軸 = 不合格）

| 軸 | 最低要求（v3 floor） | v1 反例（禁止） |
|---|---|---|
| **幾何** | 物件 ≥100（場景類）；主體結構用真實構件堆疊（疊木/疊瓦），不用整塊扁平盒充數；開口用布林差集挖真洞、外露邊緣主動決定倒角/圓角半徑；非 primitive 輪廓（載具/家電外殼/瓶身）用 `shape_lib.py` 切割塑形，不用方塊/圓柱硬拼（§13.10 CNC 機床/造型雕塑式建模操作字彙，禁止零倒角的基礎形狀直接拼接） | 41 物件、四面牆=空心盒；窗洞用「該處不建量體」假造、外露邊緣一律銳邊零倒角；車體/家電就是幾個方塊圓柱疊在一起 |
| **比例** | 主體分段/主次體量/腰線位置依 §15.0 選定的比例/構成系統生成（黃金比例/對稱/簡單整數比/模矩制擇一並寫理由，禁止的是「沒選系統隨手填一個差不多的數值」，不是禁止對稱系統本身要求的真正 1:1）；選黃金比例系統時遵守 §15.3 大小曲線對比 | 沒說明依據、隨手填「差不多一半」 |
| **材質** | ≥12 種材質；至少主體+地面用**程序化紋理**（Noise/Wave→ColorRamp），非全純色；**一律先查 assets/mat_lib.py 的 24 個 factory（§17.3），場景包 materials.py 只寫 lib 沒有的專屬材質** | 11 種純色；每個任務重寫皮革/拉絲銀函數 |
| **微細節** | 可轉/可按/可握件必有微觀起伏：轉盤/鈕 = detail_lib.knurl_ring 滾花（齒數 34/55/89）、握把 = grip_strip 凸點、刻度面 = dial_grooves；產品類主體過 audit_detail_density ≥25%；接縫/螺絲/刻字用 detail_lib 標準件 | 光滑圓柱轉盤（塑膠感）、零螺絲零接縫的「無縫玩具」 |
| **環境敘事** | ≥5 類環境元素（植栽、路徑、石頭、生活道具…）；**樹木/花草/地形/石頭優先用 `assets/nature_lib.py`（§18）程序化生成，沒有合適選項才退回 `asset_fetch_lib` 抓現成**；**生活道具/家具預設跟場景其餘部分一起手建（材質走 mat_lib/detail_lib，能對齊色票），抓現成是依任務判斷的可選手段，不強制（§7.7：避免手建主體與寫實抓取家具擬真度不一致）**；**禁止 primitives 手搭圓柱+球冠充樹/石頭**；加 `random` 微擾（旋轉/縮放/位置抖動）避免排列整齊的塑膠感 | 裸草地+3棵塑膠圓柱樹；或家具寫實度與手建主體明顯不一致 |
| **燈光** | 預設（取代舊版 IBL 強制，見 §10.3）：中性灰純色 World 背景（不掛 Sky Texture/HDRI）+ 三點式 AREA 燈（色溫錯開的 key/fill/rim）+ AgX，純物件與建築展示卡構圖都適用。仍要求 IBL/真實天空的情境：主體嵌在真實戶外環境的敘事場景（黃金時刻街景、夜景、室內日照敘事），走 `outdoor_golden`/`night` PRESETS，`fetch_hdri()` 為可選工具 | 單盞平光/憑感覺填能量/手調 Sky Texture 打光生硬 |
| **渲染** | Full HD 三選一（16:9=1920×1080/9:16=1080×1920/1:1=1080×1080）、≥256 samples、降噪、AgX（look 帶前綴）、相機真焦距+DoF（**只在 `CAM_TYPE='PERSP'` 時生效，`ORTHO` 保證無景深模糊，實測驗證見 `build_template.build_camera()` docstring**）、可加合成器 bloom（Fog Glow 泛光獨立於相機類型，高亮處周圍會暈染，不要跟景深模糊搞混，想要技術感零暈染畫面調高 `bloom_threshold`/縮小 `bloom_size`） | 48 samples，calib 解析度是 full 的 0.75 倍（1440×810/810×1440/810×810） |

**物件數是下限不是上限**：上表「幾何」軸的 `≥100` 是最低下限不是天花板。拆分粒度對應真實零件數——這個部件現實中是不是真的可以拆下來的獨立零件？是，給它自己的物件；不是（同一片鈑金/玻璃的不同角度區段），用連續 mesh 塑形（loft 分站數/subdivision/bevel segments），不要為了衝物件數硬拆連續曲面（§13.10 規則 7：玻璃艙拆成 11 片獨立薄板不共頂點，渲出來像插了幾片船帆）。
**資源安全閥**：CALIB 階段留意渲染耗時異常拉長（機器曾在物件/面數過大時 CPU 渲染吃到 5.7GB 觸發 Windows AppHang，§10.2#6），超出安全水位先降解析度/物件數。

### 10.2 曝光規範（實測數據校準版——目標是「第一張 render 就 WOW」）

曝光不是「不黑不白」就好，要有明確目標帶。

**硬性規則**：
1. **亮度目標帶（渲染後 LUMA_STATS mean 必落帶內，否則腳本 exit 1 自動擋下）**：
   - 棚拍純主體 studio：**100–170**（深灰地+受控三點式，主體突出、陰影有層次）
   - 戶外黃金時刻 outdoor_golden：**95–175**
   - 夜景 night：**15–70**（dark_pct ≤55%；practical light 是視覺焦點）
   - clipping（≥250 像素面積）≤0.5–1.5%；死黑（≤10）依場景 ≤12–70%
2. **燈光能量禁止憑感覺填**——一律用 assets/build_template.py 的 PRESETS（實測校準值：studio Key=30/Fill=9/Rim=16/Sun=1.0 + sky_strength=0.18；golden Sun=2.4 + sky 0.32；night Sun=0.4 月光 + interior 150 + sky 0.08）。要調整就以配方為基準 ±20% 微調，再用 CALIB 快渲驗證。
3. **太陽方位必須與相機同側**（相機在 -X-Y 象限時 azim 取 -90°~-160°）——背光=主體死黑（實測 mean 18.9）。
4. **白天場景禁用 world volume**（§8#8）；太陽仰角 ≥15°（除非簡報明確夜景）；體積霧仅限夜景且 density ≤0.015。
5. **先校準再正式渲染**：新場景/新參數先 `BLENDER_TEMPLATE_CALIB=1`（1440×810/48spp，約 10 秒）確認 LUMA PASS，再跑 1920×1080/256spp 正式版（見 §0.5 build_template.py 條目）——省掉「渲染 2 分鐘才發現全黑」的浪費。
6. **CPU 執行緒上限（強制）**：`setup_render()` 一律設 `scene.render.threads_mode='FIXED'` + `scene.render.threads=MAX_RENDER_THREADS`（預設 6）——不設會吃滿所有邏輯核心，曾觸發 Windows AppHang（渲染中途音訊卡頓/視窗停止回應）。禁止為了渲染快調回 `AUTO`/調高。
6. **AgX + Punchy 會推高光、壓暗部**：主體是淺色（白布/淺灰）時 mean 天然偏高，寧可把目标带内数值压到带中下段（110–140），使用者實感才是「棚拍質感」而非「過曝」。
7. SCENE_STATE 必回傳曝光參數 + LUMA_STATS；describe_image 評圖時「整體亮度」列首要檢查項，**並在回覆中報告實際 mean 值**。
8. **天空占比 >50% 的構圖（仰視高塔/高層俯瞰大場景），sky_strength 先減 30% 起跑**——配方值是按「主體占畫面多數」校準的，天空權重高就必過曝。環境變數 `BLENDER_TEMPLATE_SKY_DOMINANT=1` 自動把 sky_strength ×0.7。
9. **`check_exposure()` 新增 mean 與 p50（中位數）落差檢查，落差 >18 會回報問題**：mean/dark_pct 各自合格，仍可能是「少數 practical light 熱點（燈籠/招牌）撐高平均值，畫面其餘大部分接近全黑」的假通過——mean/dark_pct 都合格，仍可能是少數 practical light 熱點撐高平均值、畫面其餘接近全黑的假通過（p50 幾乎為 0）。**夜景場景（含所有會入鏡的板凳/圓凳/背景等物件，不是只有主體）建完後一律呼叫 `T.auto_night_fill(all_scene_objs)`**（`auto_frame_and_light()` 的夜景對等版，§0.5）——依全場景包圍盒自動算兩盞低能量冷色 AREA 補光，取代舊版寫死世界原點、不隨場景尺度縮放的單顆 `InteriorLight`；practical light 仍由呼叫端自己放、仍是視覺焦點，這支只保底其餘範圍不會崩成純黑死角（實測：呼叫後 mean 48.3、p50 從 6.4 拉到 34.3、dark_pct 從 59.4% 降到 5.0%，practical light 熱點仍明顯是畫面最亮的焦點）。

### 10.3 純主體/展示卡構圖（無真實環境敘事）請求的 floor

「一張椅子」「一棟大樓外觀」這類請求：物件數下限放寬（大樓類仍受§10.1「幾何」軸整體規則約束），但**材質程序化、燈光三點式（key/fill/rim）、渲染規格、曝光規範照樣強制**；地面給深灰微水泥或低反光地板（淺色地面會反光抬升全圖亮度），禁止裸物體懸浮在虛空。

**3 渲 2／賽璐璐路線的展示卡用對應版本，不是照搬這一段**：單一主體（產品/單一建築/單一道具）走 cel 時，`subject_fn()` 裡呼叫一次 `T.setup_cel_studio(mesh_objs, ground_mat=...)` 取代 `T.auto_frame_and_light()`——它把同一張展示卡在 cel 下的必要設定一次接好（EEVEE + Standard + 一盞 SUN `angle=0`（唯一明暗界線來源）+ 低能量 `CelFill` + 純色中性背景 + cel 色塊地面 + 背面法外殼），並自動把配方覆寫、引擎、色彩映射寫進 `main()`。**照搬 PBR 那組（三點式 AREA + AgX + 噪聲地面）會壞三件事**：三盞能量相當的燈各自產生一條明暗界線（硬邊界糊成好幾條）、AgX 把色票打歪、地面是寫實紋理。判準：單一主體的展示卡 = 這條；要整個街區/天空/招牌堆疊的敘事場景 = 風格卡的天空配方那條，兩者不可混。

**背景/燈光預設（取代舊版「IBL 強制」）**：純主體/展示卡構圖（含建築外觀展示卡）一律用中性灰純色 World 背景（不掛 Sky Texture/HDRI）+ 三點式 AREA 燈（暖色 Key + 冷色 Rim + 中性 Fill，色溫刻意錯開）+ AgX，比 IBL 強制流程效果好且更穩定。新預設：

1. **World 背景改純色中性灰，不掛 Sky Texture/HDRI 節點**——`asset_fetch_lib.fetch_hdri()` 對純主體/展示卡構圖不再是強制項（`build_template.build_world()` 目前仍會建 Sky Texture 節點；這類任務改走這條新預設時，呼叫端應改用純色 World 背景而非 `build_world()` 的 Sky IBL 路徑）。色值參考：相機 `(0.18, 0.18, 0.18)`、大樓 `(0.35, 0.35, 0.35)`，依主體色調/尺度微調（大樓案例背景色偏亮，跟建築本身淺色調外牆搭配）。**`add_stylized_sky(zenith_color, horizon_color, cloud_color, cloud_coverage, cloud_scale, cloud_softness, strength)`/`add_night_stars(density, dot_size, brightness)`**——`build_world()` 的 Nishita Sky Texture 算得出物理正確但偏淡的晴空、算不出真正的積雲形狀；這兩支改走純色雙色漸層+選填雲/星點遮罩（不是真體積雲/真星空，色彩可控但沒有立體感），日式動漫街景風格卡（`styles/genre/anime-cel-daylight.md`）的天空配方直接靠這兩支實現，校準值見該風格卡。
2. **三點式 AREA 燈至少 2-3 盞、色溫刻意錯開**（暖 Key 主光 + 冷 Rim 勾邊光 + 中性 Fill 補光，必要時加一盞低能量 SUN 補強方向性陰影）——不要三盞燈都同色溫，會扁、沒有攝影棚的層次感。能量/角度以主體實際包圍盒為準（`build_template.auto_frame_and_light()`，§15.4），不要憑感覺手填絕對座標；大樓這種真實公尺尺度的主體，AREA 燈能量會遠大於小型產品（案例中兩盞分別是 65000W/45000W，size 55/40）——**能量數值本身沒有意義，重點是依主體實際包圍盒尺度縮放，不要照抄案例的絕對數字**。
3. 地面仍是深灰微水泥/低反光平面，不換成純白或淺色——這條不變。
4. AgX view transform 照舊必做，這是那個漸層層次感的關鍵一環，不是背景本身有漸層貼圖。
5. **這條例外只到「純主體/展示卡構圖」為止**——任務明確要「嵌在真實戶外/城市環境」的敘事場景（黃金時刻街景、夜景、有日照穿透窗戶的室內敘事）不適用，這類繼續走 `outdoor_golden`/`night` PRESETS 並可用 `fetch_hdri()`（§7.7、§10.1 燈光軸不受影響）。
6. **大樓案例額外驗證值得抄的細節**（非燈光,但同一份腳本裡的技巧）：
   - **隨機「已入住」暖光窗**：約 10-15% 的窗戶玻璃材質換成帶自發光的暖色調（`gm = warm if random.random() < .13 else glass`），製造「有些戶亮燈、不是每扇窗都一樣」的生活感，比全樓窗戶同一種玻璃材質更真實——**大樓/住宅類主體的窗戶材質應比照辦理**。**注意**：在「純主體/展示卡構圖」這種明亮 studio 級曝光下，純 `make_emissive()` 不管 strength 給多少，AgX 都會壓成近乎純白，暖色調完全看不出來（見 `mat_lib.make_emissive()` docstring、`anatomy/buildings/residential.md` 陽台/窗戶段落）。這個情境改用 Transmission=1.0 的暖色玻璃（Base Color 直接給飽和暖色，不是靠 Emission 撐色相）+ Emission strength 只給 1.0-1.5 當輕微加成；真正「發光」的效果留給 `night` preset/`auto_night_fill()` 場景。
   - **固定亂數種子**（`random.seed(24)`）：任何用到 `random` 做微擾/隨機挑選的場景腳本，開頭固定種子——同一份腳本重跑（例如只改了某個無關參數）結果要可重現，不是每次重新擲骰子，這樣才能真正做到「改一處只影響一處」。
7. **這兩次案例同時驗證、不需要改動的既有設計**：`mat_lib.make_leather()` 的 noise+bump 顆粒皮革節點鏈、`build_template.auto_frame_and_light()` 的三點式 AREA 燈架構、逐物件套 Bevel+Weighted Normal 的收邊紀律——這次真正要修的只有「World 背景該用純色還是 Sky/HDRI」這一項判斷。**陽台覆蓋率**：只做兩端角落陽台的立面讀起來扁平像貼裝飾，陽台覆蓋率要拉到大部分／接近整面寬度，且每道陽台都搭配 `cheek_mat` 分戶側牆參數，才有真實的量體進退感——完整前後對比見 `anatomy/buildings/residential.md` 陽台段落、跨品類通用原則見 `anatomy/buildings/_INDEX.md`。

**可選加值：灰盒城市語境（僅建築/街景類展示卡）**——純主體展示卡若只有一棟樓浮在深灰地上，尺度感偏弱；加一圈成本近乎零的量體語境（幾個遠方量體＋鋪面＋一條馬路＋人行道/廣場鋪面），鏡頭立刻讀得出「這棟樓在城市裡多大」。這不是敘事場景（不切 `outdoor_golden`/`night` 路線、不重建一整條街），仍是展示卡構圖＋純色背景，只是不再是真空。這些背景量體一律 `T.mark_framing_exclude()` 排除出構圖審查——它們刻意延伸到畫面外，算進「主體」只會製造假警報（§15.4）。

### 10.4 風格專屬註記

- **遊戲資產風（low-poly/toon）**：色調走莫蘭迪/馬卡龍、幾何簡化但仍需程序化紋理或至少 vertex color 變化；**廣角場景中號誌類小物件（紅綠燈、號誌牌、路燈頭）可放大至真實比例的 1.2–1.5 倍**——可讀性優先於精確比例（實測：燈頭 z≈3.5–4.4m 在廣角下存在感弱）。遠景建築剪影**至少加窗格細節**（emissive 小方塊或 UV 格紋），純白立方體在評圖中會顯得敷衍。
- **3 渲 2／賽璐璐（日式場景預設，見 `styles/genre/anime-cel-daylight.md`）**：**預設走進階路線（漸層 cel）**——`mat_lib.make_cel_advanced()`（硬陰影邊界 + 受光帶內漸層 + AO 接觸陰影 + 冷色 rim），遠景/快渲才降級 `make_cel()` 純平塗三階；Cycles 備援 `make_toon()`。**單一主體的展示卡走 `T.setup_cel_studio()`**（§10.3 cel 段：EEVEE + Standard + 單盞 SUN(`angle=0`) + `CelFill` + 純色中性背景 + cel 地面 + 背面法外殼，一次接好）——本路線不去蓋一整條街，模型本身沒問題也會被隨手拼的場景拖低檔次。**禁用程序化寫實紋理系列**（concrete/stone/wood/leather/brushed_metal/add_procedural_wear）；色調映射必須 `T.set_view_transform('standard')` 且**確認真的套上**（該函式只記 override、套用在 `setup_render()` 內，不走 `T.main()` 要自己補 `scene.view_settings.view_transform="Standard"`）；描邊**優先走背面法** `T.setup_inverse_hull()`（《罪惡裝備》系列自 Xrd 起的畫線主力：線寬隨距離/FOV 自動補償、可逐部位用頂點色 alpha 控制、`z_offset` 可只留最外圈剪影線；**必須用真幾何**——Blender 不支援 multipass shader，舊版寫「禁用反轉外殼」是過度概括，實測失敗的 7 種全是 shader/modifier 路線，缺的正是「真外殼」＋「只畫背面」這兩步），快渲或遠景才用 Freestyle 的 `T.setup_selective_outline()`（FG 粗深線/BG 細淡線）或 `setup_freestyle()`（全場單線寬）——**三者只選一個，同時用會疊線**；圖案**內部**的線（皺褶/分件/瓦楞）背面法畫不出，用 `T.make_internal_line()`。**此路線預設不畫車與人**——這類主體在量化著色下造型保真度最低，會成為全圖最明顯的破口；要「有人在生活」的氛圍改用鐵捲門半開/晾衣桿/靜止腳踏車/自動販賣機/路邊雜物堆（`anatomy/spaces/japanese_street.md`）。**5.1 API 陷阱**：① `lineset.linestyle` 預設是 `None`，直接寫 `.color` 會 AttributeError；② **scene compositor 的 node group 內 GroupInput 不會收到渲染畫面**——group 必須自己放 `CompositorNodeRLayers`（只接 GroupInput 實測輸出全黑/全白），`T.setup_anime_post()` 已內建正確接法。**這條路線的合格線不是 LUMA 帶也不是「≤4 階」**——EEVEE 下曝光守衛只報告不擋（`exposure_enforced=false`）；漸層 cel 的受光帶是連續漸層、量化色格數天然 5-7 階，進階路線改驗：陰影邊界梯度寬度 ≤2px、`top[].hex` 比對**這次實際採用的色**（用途是抓 AgX 誤用造成的色偏）；**色彩配額與飽和度上限不列入驗收**（審美判斷，見風格卡）。「≤4 階」門檻只適用基礎平塗路線的單一材質面（實測純平塗單材質 3 階、三材質 5 階、程序化寫實 7 階；多材質全景上調或給 `roi`）。
- **寫實風**：比例嚴守真實規範；細節堆疊優先於放大。

### 10.5 太空／真空場景（orbit / vacuum）

**完整規則+陷阱表+校準基準已搬到 `assets/examples/space_scene.md`（2026-09-13，原節過長，
SKILL.md 瘦身抽出對象之一，內容未刪減）**——動工前先讀那份，這裡只留最容易忘記、會直接
搞砸整張圖的三條救命索：

1. **真空 = 沒有介質 = 天空不是光源**：背景亮度是 World 底色本身，不是打光結果；三點式一律
   關掉，只留 `auto_space_fill()` 的兩盞極弱冷/暖補光。`PRESETS["space"]` ＋ `space_lib.py`
   （§0.5）是配方入口。
2. **地面不能入鏡，但不能刪掉**——`T.set_ground_void()`（讓地面對相機/鏡面不可見，仍留著當
   `audit_floating()` 的支撐面）；**主體自己的底座/水平面也不能以掠射角入鏡**，那會變成一條
   把星空切斷的假地平線，`T.audit_horizon_surfaces()`／`audit_horizon_line()` 兩道審查在
   `PRESET=="space"` 時自動跑，兩者都是硬規則不是建議。
3. **點狀星一律用真幾何 `make_star_points()`**（環境貼圖在正交相機下會糊成均勻灰），銀河帶
   環境貼圖走 `make_star_map()` + `request_world_hook()`；日盤 `make_sun_disc()` 只留
   `camera` 可見，**不要**呼叫 `request_lens_flare()`（太空版鬼影鏈讀成髒點，成效為負）。

完整的 11 條硬性規則、陷阱數字、`PRESETS["space"]` 校準基準、常見錯誤表，見
`assets/examples/space_scene.md`。

## 11. 模型生成工作流程（Stage A→B→C，強制）

3D 繪圖與一般任務不同：**禁止接一句話就開畫，也禁止 render 後無限自我迭代**。以下三階段對任何「畫一個 3D 模型/場景」請求強制執行。

### Stage A — 設計簡報（動工前，必做）

1. **擴寫 ≥300 字設計描述**：風格流派、造型細節、材質顏色、尺寸比例、使用場景與氛圍、鏡頭構圖與光線方向，具體到可直接建模的程度（不是複述使用者原話）。**命中風格觸發詞（§17.1 _INDEX.md）→ 讀風格卡，比例/色票/材質段直接引用卡片數值**。**產品類主體 → 查 assets/anatomy/ 組件圖譜（§13.7），組件清單從圖譜六面表抄，成對組件逐對列出**。**空間類主體 → 查 assets/anatomy/spaces/ 必備元素圖譜（§13.8），逐項標 MUST/OPTIONAL，動線永遠是 MUST**（規劃階段沒列出來的東西，後面任何驗證都救不回來）。**必含「比例規劃段」（§15.1）**：選用哪個比例系統（黃金比例/對稱/簡單整數比/模矩制，§15.0）與具體數字（`fib_split`/`golden_series` 算好，不手填）。**必含「文字裝飾段」**：主動考慮這次場景有沒有適合放 3D 文字裝飾的位置，沒有也要明講「本次不用」。
2. **主體是真實存在、有名字的物件/建築/地標時（不是憑空原創設計），必須先上網搜尋官方/維基百科等權威來源查真實參數**——尺寸、結構配置、關鍵數字（例如東方明珠塔：塔高 468m、三根直徑 9m 圓筒相距 7m 品字排列、三根與地面 60° 斜撐、11 個球體各自的直徑與所在高度），寫進簡報當作建模依據的具體數字來源，不是憑印象或猜測（先查維基百科拿到完整結構參數，遠比只憑感覺建模可靠）。這跟 §19.4 RAP007「抓 3D 參考檔研究比例」是同一件事的兩種來源，**文字規格頁優先於 3D 參考檔的絕對尺寸**：對幾何邏輯單純、被詳盡記錄的地標/建築，維基百科這類來源給的數字通常比隨便一個業餘上傳的 3D 模型更可信——§19.4 已記錄實測：一個東方明珠塔 Sketchfab 參考模型的絕對尺寸是任意建模單位（量出來 1.4×1.4×2.687），跟真實 468m 完全對不上，維基百科查到的數字才是真正的真相源。3D 參考檔適合拿來研究文字規格講不清楚的東西（車身鈑金曲率、複雜造型的整體形態邏輯），不是拿來當唯一的比例依據；兩者可以同時用，互相佐證。**有視覺能力時，額外做 §13.12 的規劃期正交參考圖研究**（頂/前/側/後視角，核對整體裝配關係+色調材質），在動工前而不是建完渲染後抓出結構性錯誤。**「要不要找圖、誰去找、找哪一等級、找不到怎麼辦」一律照 §16.9.0 判定**，本條只負責「真實物件必須查權威參數」這件事本身。
3. **元件表規劃（MUST）**：把主體拆解成一份**層級式元件表**，這份表本身就是 Stage B 要照抄的施工圖，不是先寫一段風格氛圍描述、開工後再臨場即興湊零件：
   - **編號（MUST，複刻真實物件時尤其關鍵）**：每一項給穩定編號（`A-1`/`A-2`/`A-2.1`……），Stage B 物件命名或建構函式帶上同一編號——複刻真實物件時 Stage C 要走 §13.12 逐項核對，沒有編號就沒有東西可以精確對應「評圖說哪裡不對」跟「該改哪個物件」。
   - **大元件**：六面/樓層級別的主量體（相機＝鏡頭組/機身/頂蓋控制群；大樓＝一樓大廳/標準層/屋頂；家具＝椅腳/椅座/椅背…）。
   - **小元件（MUST 拆到至少 LEVEL 6）**：每個大元件底下的具體構件，逐項對應 §13.7/§13.8 圖譜的六面清單/成對組件表/必備元素清單——圖譜列出的每一項都要出現在表裡。**遞迴繼續往下拆，不是拆一層就停**：LEVEL 1=主體本身、LEVEL 2=大元件、LEVEL 3=小元件、LEVEL 4=小元件的子部件、LEVEL 5=再往下一層、LEVEL 6=再更下一層（例：車體(1)→輪子(2)→輪框(3)→煞車鉗(4)→來令片(5)→固定螺栓(6)）。**LEVEL 6 是複雜機械/建築類主體的最低期望值，不是每條分支都要硬湊配額**（規劃階段的文字深度本身幾乎零運算成本，真正的邊界不是算力，是判準同 §10.1「物件數是下限不是上限」：這個部件現實中是不是真的還能再拆出更細的獨立零件，是就繼續拆，不是（例如螺絲鎖到底）就停，不要硬造不存在的子零件）。停在 LEVEL 2-3 不再往下想才是要糾正的懶惰模式。
   - **組合方式與挖洞/凹凸描述（MUST）**：小元件彼此的相對位置/朝向/裝配關係，不是只列名稱。**拆到接近 LEVEL 6 的葉節點時，描述必須包含材質+尺寸+表面凹凸紋理**（例：輪胎要寫材質、大小、表面 ^ 形胎紋是凹的，不是只寫「輪胎」兩字）。**父元件容納子元件時要明講該位置需不需要挖空**（例：車體要註明放輪胎的四個位置需挖成空心，避免穿模）——對應 §13.10 `cut_hole()`（貫穿孔）/`carve_depression()`（座椅/碗類不貫穿凹陷）。
   - **內嵌元件留白（MUST）**：任何嵌在殼體/邊框裡的元件（螢幕、按鍵群、銘牌、面板、車牌），簡報階段就要明講留白比例（預設等寬三邊或四邊，特殊留白要註明理由，不是各邊各自猜一個數字）。動工後至少呼叫一次 `T.assert_inset_margins(host, content, label)`（§13.9）驗證——不要只靠肉眼看習慣了就以為對稱。
   - **連接/過渡件的路徑要明講從哪一側進入，不是只給造型描述（MUST）**：支架、頸部接頭、轉軸、線材這類「連接兩個大元件」的過渡件，如果它連接的其中一端**被另一個有輪廓/網狀/包覆結構的子總成包住或圍繞**（護網、外殼、罩子——例如電風扇馬達被前後網罩夾在中間），元件表光寫「這個接頭長什麼形狀」（例：「車削造型」）不夠，**必須額外明講它要從哪一側/哪個深度範圍進入那個被包覆的元件**（例：「頸部接頭從網罩後緣**之後**的深度接上馬達底部，不從網罩輪廓內側直接連過去」）。這條沒寫清楚時，Stage B 建模會很自然地選「兩點之間畫直線」這條最直覺的路徑——但連接件的兩端一旦分屬「包覆結構的前方」跟「包覆結構的後方」，直線路徑在幾何上必然會跟包覆結構的輪廓相交，等於連接件從外面看會「穿過」護網/外殼，肉眼在渲染圖上就是一條桿子插進網子裡的違和畫面。跟「組合方式」規則是同一類要求（裝配關係不是只列名稱），這裡特別拉出來是因為「造型」類描述（車削/收分/弧面）很容易讓人誤以為已經講完這個元件該講的事，忘了它還有一個「怎麼繞過鄰近結構」的路徑問題沒回答。
   - **左右/前後成對元件走鏡像關係，不是各自獨立猜數字（MUST）**：現實中本來就該對稱的成對元件（左右兩個把手、左右兩顆螺絲、前後兩片面板……），元件表只定義**一份**尺寸/位置參數，另一份明講「鏡射（X 軸取負）」，不要讓 AI 對兩側分別各自估一次數字——分開猜，落差不會剛好是 0。**提醒**：不是每一對「看起來左右都有」的元件都真的該對稱（例如紅白機的 POWER 鍵跟 RESET 鍵是兩個不同功能的按鍵，各自的尺寸/位置本來就不必相同）——判準是「現實中這對元件是不是同一個模具/同一個設計、只是裝在鏡射位置」，是才套鏡像關係，不是同一設計、只是剛好都在左右兩側的不同功能元件，各自定義即可，不要為了套用這條規則而假造對稱。
   - **材質（MUST，含線材）**：表裡每一個小元件都要指定 `mat_lib.py` 哪個 factory（24 種，§17.3），寫到 `make_metal(preset="chrome")` 這種可直接抄進 materials.py 的程度，不是「深色金屬」這種形容詞。24 種都不合適時，簡報要明講「需新增 factory，理由是現有都不是這個質感」。**電線/纜線/軟管這類線材元件不能漏列材質**——`shape_lib.curve_tube(smooth=True)`（§13.10）現在能建出真正會自然垂墜彎曲的線材幾何，材質同樣要指定（通常 `make_rubber()`），過去容易因為「不是實體量體」被跳過，現在有能力畫好就不能再漏。
   - **邊緣處理（MUST）**：外露邊緣的每個小元件都要在表裡寫明倒角/導圓角半徑（或明講「刻意銳邊，理由是＿＿」），不是留到 Stage B 寫代碼時才想到、然後圖方便用 `add_box()` 預設的 `bevel=0.0`。半徑抓法照 §13.10 規則 2：小型手持物 1–3mm、家具家電 2–5mm、建築構件 5–20mm；有風格卡照卡片走。**這條沒進元件表，`add_box()` 零倒角的預設值就會悄悄變成實際結果**——不是 Stage B 忘記加，是 Stage A 從來沒把這個決定放進施工圖。
   - **貼附件的安裝關係（MUST）**：任何貼在另一個量體表面上的零件（扶手、貼箱、舷窗、貼花、刻字、外掛平台…）都要在表裡寫出**宿主 + 安裝方式（徑向貼附／鎖固／支架）+ 預期間距**，Stage B 用 `T.assert_attachment_contact()` 驗（§13.9）。只寫「貼在艙體上」等於沒寫——擺位高度會被實作成「宿主外接半徑 + 一個安全間隙」，檢查器全過、畫面上是浮的。
   - **拆解深度有可執行閘門（MUST，交付條件）**：元件表存成 `<task>_pkg/components.json`（schema `components/2`，格式見 §16.9.4），並在 `config.py` 宣告 `COMPONENTS_JSON`（或設環境變數 `BLENDER_COMPONENTS_JSON`）——`T.main()` 會在**建場景之前**跑 `T.assert_component_depth()`，全表最深 LEVEL < 6、且最深那個分支沒有寫 `depth_exempt` 理由，即 exit 1。純文字寫成 MUST 而沒有閘門＝一定會被跳過，這是本 skill 唯一一條曾經如此的規則，也是「物件數達標卻讀起來粗糙」唯一能被自動攔下來的關卡；規劃階段改一行文字的代價，跟建完才發現要重拆的差距就是這道閘門的價值。原創設計類（沒有三視圖可量）同樣適用——這支檢查不需要 calib（見 §16.9.0 B 類）。
   - 不再走「AI 生概念圖→讀圖回填簡報」的路線——改成一次規劃出元件表（大元件/小元件/組合方式），比生圖→讀圖→轉譯回文字精確、便宜、且可直接比對圖譜逐項核對。
4. **使用者提供參考圖時**（跟上面「AI 自己生圖」是兩件事，這條路徑保留；本條只管「怎麼把圖讀進來」，兩條路線依當前模型是否支援視覺二選一）：
   1. **當前模型支援視覺**（Claude/GPT-5.6 系列/Gemini/Grok 目前都是）→ 直接呼叫 `read_image_native(path=<使用者提供的檔案路徑>)`（或你的 agent 平台上等價的視覺輸入工具），圖片會真的以圖片內容送進這一輪對話——這是唯一一個真正讓你「親眼看到」一張圖的工具，不是文字轉述。呼叫前不確定目前模型支不支援視覺也沒關係，工具自己會判斷，不支援時回傳 `[READ_IMAGE_DENIED]` 而不是靜默失敗。
   2. **當前模型不支援視覺，或就是想要一份結構化文字描述**（例如要把描述結果整理進簡報、或跨模型比對）→ 用 `describe_image(image_path=<使用者提供的檔案路徑>, detail="rich")`，點名造型/比例/材質/顏色/風格特徵的提示詞讀出結構化描述，併入上面的元件表當佐證依據。
   - 背景：這個工具組（agent-v2）原本完全沒有原生視覺輸入通道——聊天室貼的圖片、任何工具回傳的截圖，全部都到不了模型（MCP 圖片會在送進模型前被 host 攔截替換成純文字）。`read_image_native`（或你的 agent 平台上等價的視覺輸入工具）是專門為此新增的原生工具，繞過這個限制，讓有視覺能力的模型真的看到檔案內容；`describe_image` 則是原本就有、對任何模型都能用的「委託視覺模型描述」退路，兩者互補，不是誰取代誰。
5. **反問確認（這是 harness「少反問」的明文例外）**：把設計簡報+元件表呈現給使用者，**等一次確認**才進 Stage B。確認輪只問一次、問題打包（風格對不對/要不要調整/直接開工）。使用者說「你決定」就直接以簡報為準開工。
6. **簡報定稿/修改都要落地成 SPEC，不要只留在對話裡（MUST）**：
   - 使用者**確認**簡報，或 Stage C 期間**修改**了元件表/設計決策，當輪就要把完整簡報（擴寫描述+完整元件表，不是摘要）用 `write_file_native`（或你的 agent 平台上等價的寫檔工具）寫進 `${WORKSPACE_DIR}/SPEC-PLAN.md`，然後呼叫 `create_workspace_spec_native`（`referenceFile` 指向這個檔案），steps 列 Stage B/C 的實際建構步驟。確認輪之後每次簡報內容有異動，重寫 `SPEC-PLAN.md` 覆蓋即可（`create_workspace_spec_native` 本來就是「建立或取代」語意）。
   - **不要用 `${WORKSPACE_DIR}/notes/`**：notes/ 是設計給「會過期的分析結論」用的研究快取，20MB 滿了會直接淘汰舊筆記、不備份，且本來就不會在每個 session 開頭自動注入；SPEC.md + referenceFile 才是每個 session 開頭自動載入、且完成/清除時才會封存的機制，這才是「簡報必須跨 session/跨 compact 不遺失」該用的地方。
   - 這條跟 Stage B 步驟 1 的 SPEC 沒有衝突——同一個 SPEC 物件，`referenceFile` 放簡報全文，`steps` 放建構進度，兩者本來就該同步存在。

### 文字裝飾建議（3D 文字是本 skill 的強項，Stage A 必須主動考慮）

`detail_lib.make_text()`（§17.4）走 `text_add`→`convert(target="MESH")`，文字內容/字體/尺寸/擠出厚度/倒角全是精確數值控制，不像程序化紋理或手建曲面容易失真——文字是少數「做出來一定跟預想一樣」的環節，值得主動利用，不是等使用者要求才想到。

**強制公約**：

1. **Stage A 設計簡報必須主動評估**這個場景/主體有沒有「合理會出現文字」的位置——不是每個場景都要硬塞文字，但要**主動想過**，不能預設略過。判斷依據：現實中這個空間/物件本來就會有文字嗎？（教室黑板本來就會寫字、產品面板本來就有型號刻字、招牌本來就有店名、書本封面本來就有書名——這些是「合理」；憑空在一個原本不該有字的表面貼字則不合理，不要為了用而用。）
2. **有合理位置就在簡報寫清楚**：文字內容、位置、材質/發光與否、字體感（用 `bevel`/`extrude` 參數描述，例如「粉筆字感＝細倒角+白色 emissive 微弱自發光」「刻字感＝黑色凹陷+無倒角」）。**沒有合理位置也要在簡報明講「本次場景不適合加文字裝飾，略過」**——差別在於「想過但決定不用」跟「根本沒想到」，Stage C 事後看得出來簡報有沒有這一段。
3. **文字內容本身要看情境自己決定，不要生硬套用範例**——舉例僅供理解「什麼叫合理的文字裝飾」，不是模板：教室黑板可以寫當日日期、值日生、一句話（不是規定寫什麼）；產品面板可以刻型號/品牌字；書櫃可以有書名；招牌可以有店名。**每個任務的文字內容要貼合任務本身的情境自己想，禁止不假思索複製某個範例的字面內容**。
4. **落地走 `detail_lib.make_text()`**（§17.4）：文字面朝向觀眾時 `rot=(π/2,0,0)`，凸出量 `extrude≥0.9mm` 防共面（§8#11 同款規則），`align_center_x=True` 避免文字跑版。材質視情境給 `mat_lib` 對應 factory（粉筆白字用 `make_paint` 或 `make_emissive` 微弱自發光；金屬刻字用 `make_metal` 深色）。**文字要出現在彎曲表面（鏡筒品牌刻字、轉盤刻度數字）時改走 `detail_lib.arc_text_ring()`**——整段文字硬貼一塊平面再包上圓柱，字會看起來浮空/不服貼，arc_text_ring 逐字元沿曲率排列才是刻字的正確做法。

### 磨損/髒污效果（材質做完後的加分項，Stage A 必須主動考慮）

`mat_lib.add_procedural_wear()`（§17.3）已經存在一段時間，但過去只被列在 §0.5 資產清單裡當成「有這個工具」，Stage A 從來沒有主動要求評估要不要用——結果是坦克/軍用載具/戶外廢棄機具這類「現實中一定會有磨損痕跡」的主體，簡報階段沒人想到要規劃，materials.py 寫完基礎材質就直接收工，磨損效果形同不存在的功能。跟文字裝飾建議是同一種「能力存在但沒進 Stage A checklist，就等於沒人用」的模式，用同一種方式修正。

**強制公約**：

1. **Stage A 設計簡報必須主動評估**這個主體現實中會不會有磨損/髒污痕跡——判斷依據：這是全新出廠的物件，還是有使用/服役/戶外曝露歷史的物件？軍用載具（坦克/裝甲車/軍艦）、工程機具、老舊工業設備、戶外廢棄物、二手/古董產品——這些**預設就該有**磨損；全新展示品、室內精品、剛出廠的消費性電子——預設不用，硬加反而不符合設計簡報本身設定的情境。**沒有理由也要在簡報明講「本次物件全新狀態，不加磨損」**，跟文字裝飾建議同一個「想過但決定不用」vs「根本沒想到」的差別。
2. **有需要就在元件表寫清楚**：哪些材質要疊磨損（通常是外露金屬/烤漆件，不是每個材質都要）、大概什麼程度（light/medium/heavy）——理由要對應現實（例如「履帶/砲塔長期戶外服役、邊角碰撞掉漆嚴重→heavy；車內儀表面板較少接觸→light 或不加」），不是每個材質都套同一個 level 應付了事。
3. **落地走 `mat_lib.add_procedural_wear(mat, level=...)`**：材質 factory（`make_metal`/`make_paint`/...）建完基礎材質後，直接對同一個 `mat` 物件呼叫這支函式疊加，不用重建材質。`level="heavy"` 對應坦克/廢棄機具這類重度磨損；`level="light"` 對應保養良好/較新物件的輕微使用痕跡；不給則是 `"medium"`。**邊緣效果要銳利，host 幾何需要有足夠的邊緣密度**（§13.10 `shape_lib.bevel_edges()` 對實際選取的邊做局部倒角）——用一整個物件套一次性粗糙 bevel 的低面數量體，磨損效果會暈染到整個平面而不是只有邊角，這是函式本身文件已經寫明的已知限制，不是新問題。
4. **`ao_distance` 依主體尺度縮放**：同 §13.9 `audit_floating` 的 `max_gap`/`max_sink` 縮放邏輯，小型道具用預設 0.05m 附近，大型載具/建築要相應調大，否則 AO 抓不到正確的局部凹處。

### 品牌標誌／圖標貼花（複刻真實商標時優先於手刻幾何）

**新做法：已有清晰圖片就不要用幾何湊，直接貼上去**。真實世界的品牌標誌/警示符號/QR code/認證標章絕大多數上網就找得到清晰、免費、透明背景的圖檔，抓一張下來當貼花紋理，形狀 100% 準確，比手刻布林幾何準、快、還更省 token（不需要猜咬口半徑/凹口深度/葉片角度這些永遠調不準的參數）。

**強制公約（複刻真實存在的商標/圖標時適用，原創設計的標誌仍走手繪/程序化路線）**：

1. **元件表規劃階段就決定用貼花，不是動工後卡關才想到**：判準——這個標誌/圖標是不是「現實中真實存在、有官方標準形狀」的東西（品牌 LOGO、道路警示符號、認證標章、QR code、國旗）？是 → 貼花優先；原創設計的抽象圖案/使用者自訂圖騰 → 仍走手繪幾何或程序化紋理，貼花不適用（沒有「正確答案」圖片可抓）。
2. **抓圖走 `asset_fetch_lib.fetch_reference_image(url, dest_path)`**（新增）：下載到本機後會自動驗證檔案開頭的 magic bytes 確認真的是圖片，不是失效連結/防盜鏈回傳的 HTML 錯誤頁偽裝成的 `.png`（同一類失敗已經在參考圖抓取流程炸過一次，這裡直接在下載階段複用同一道防線）——驗證失敗會丟例外並刪除壞檔，不會留著讓後面的貼花步驟拿一張看不懂的檔案去貼。優先找**透明背景**版本（PNG，Alpha 決定標誌輪廓）；找不到透明背景版才退而求其次用完整方形圖，此時貼花的 `width`/`height` 務必按圖片實際長寬比設，否則會被拉伸變形。
3. **貼上去走 `detail_lib.apply_image_decal(name, image_path, width, height, center, normal, up, proud, roughness, metallic, emission_strength)`**（新增）：`normal`/`up` 決定貼花朝向，跟 §12 方向公約的世界座標判斷方式一致；`proud` 比照 §8#11 防共面慣例，貼在曲面上（例如 iPod/iPhone 背板的輕微弧度）務必按實際曲率加大，不然邊緣會看起來嵌入/穿透表面。貼花材質預設走簡單 Principled BSDF（不吃 `mat_lib` 24 種 factory），`roughness`/`metallic`/`emission_strength` 三個參數已經夠覆蓋「霧面貼紙／鏡面金屬標／面板夜光標誌」這幾種常見情境。
4. **仍然可以疊材質效果**：真實蘋果標是鏡面拋光金屬浮雕，不是印刷貼紙平貼——`apply_image_decal` 的 `metallic`/`roughness` 就是為了讓貼花能帶一點金屬質感，不是只能做平面印刷貼紙的效果；不需要為了「質感」又跑去疊一層手刻幾何，兩種手法疊加只會回到原本的問題。
   - **跟 `shape_lib.flat_decal()`（§17.4）的分工**：`flat_decal` 要呼叫端自己給一圈世界座標點描出輪廓——本質上還是「手刻形狀」，只是用頂點代替布林，一樣有「複雜曲線描不準」的老問題；`apply_image_decal` 用真實點陣圖，形狀直接來自圖片本身，不需要描邊。複刻真實商標優先用 `apply_image_decal`；車身閃電/隊標這類原創或找不到現成圖檔的不規則色塊，才是 `flat_decal` 的場合。
5. **抓不到可用圖片時才退回手刻幾何**，且要在簡報裡明講「本次未能取得標誌透明底圖，改用幾何近似，可能跟真實形狀有落差」——不要為了「一定要貼圖」卡在搜圖/抓圖步驟不動，抓不到就是抓不到，退回手刻並記明缺口。

### Stage B — 建模渲染（照 §10 floor + §12 方向公約 + §13 組件常識 + §14 資產復用執行）

1. §0 路徑解析（快取 → find_blender.ps1 cascade）→ `$blender` 變數就緒。
2. `copy_skill_resource_native` 取出 `assets/build_template.py` → 存為 `.capybala/test-scripts/build_template.py`（凍結模組）；**中大型/需迭代任務再取出 `assets/scene_pkg/` 六件骨架 → 存為 `.capybala/test-scripts/<task>_pkg/`（§16.1 場景包）**；小型一次性任務才用單檔 `build_<task>.py` 照 §9.6.1 import 引用（`T.main(subject_fn=..., preset_overrides=...)`），採 §9.6.2 元件工廠結構，禁止從零盲寫、禁止複製模板函數。**產品/建築/室內類主體同時取出 `assets/mat_lib.py` + `assets/detail_lib.py`（§17.3/§17.4，與 build_template.py 同層）；車輛/角色類主體另取出 `assets/proportions_lib.py`（比例計算機，先算尺寸再建模，不要憑感覺填數字）**——materials.py 引用 factory、geometry.py 引用細節件，禁止重寫同款節點鏈/滾花幾何。場景含植栽/地形再取出 `assets/nature_lib.py`（§18，同層）——樹/地形母版與散布一律走 lib，禁止手搭。
3. 選 PRESET（studio/outdoor_golden/night）；場景腳本設 `BLENDER_TEMPLATE_OUT`/`BLENDER_TEMPLATE_PRESET` 環境變數（import 前），曝光微調經 `preset_overrides` 傳入。
4. **人體工學件先過 §12 方向檢查清單；所有組件先過 §13 三問（觀眾/行進/支撐）；產品類主體先過 §13.7 組件圖譜（六面清單+成對組件+細節地板）；主體比例先過 §15 規劃（先選定 §15.0 的比例/構成系統並寫理由，分段/腰線/曲線等常數依所選系統的對應工具生成）；命中風格觸發詞先過 §17 風格卡落地 checklist**再寫幾何代碼；中大型場景（>150 物件）按 §14 用工廠+連結實例組織資產。
5. **腳本寫完第一個動作 = 跑 CALIB 快渲（以跑代審，§9.6.3）**：layout 完成即跑（~6-10 秒），方向、母版入鏡、Z-fighting、曝光帶全在此步攔截；**禁止先做整腳本靜態覆盤**；LUMA PASS 後才繼續堆細節。
6. 正式渲染照 §9.5：渲染前清空輸出目錄、前台 + timeout_ms=0、快速返回（<60s）先讀 stderr。
7. SCENE_STATE JSON（含 LUMA_STATS 與 `component_depth`）驗證通過才算完成建模；`component_depth.problems` 非空＝Stage A 的六級拆解沒落地，回 Stage A 補元件表再重跑，不要當成可忽略的警告。

### Stage C — 視覺評審（render 後，必做）

0. **不要對建後渲染跑結構化逐項評圖或任何大規模照評語重寫**：複刻真實物件該做的參考圖比對，放在 §13.12（Stage A 規劃期）做過了；這裡（建後）維持下面 1-7 的原始輕量流程——看一眼、講出看到什麼、列問題、問使用者，得到同意才動手，一輪一個方向。看到問題不要自己反覆用像素取樣/裁圖再三確認，那是 Stage A 的工作。
1. **先斷言 render.png 新鮮度**（§9.5.3：mtime 晚於本次啟動、size>100KB），通過才 describe_image 看圖（detail=normal 以上）。
2. **把看到的實際效果寫進回覆**：構圖、色調、亮暗（**含 LUMA mean 實際值**）、主體清晰度、氛圍——使用者看不到圖時這段就是他的眼睛；看得到時這段證明你真的檢查過。
3. **主動列出發現的問題 + 修改建議**（例：「整體偏暗，mean 僅 2.8，主因 world volume 吞天光；建議 fog_density=0 改用 domain box，改完會回到黃金時刻」）。
4. **然後問使用者要不要改，得到同意才動手**——禁止看到小問題就自動重渲染。唯一例外：大問題（全黑/全白、主體崩壞、構圖完全錯誤、**人體工學方向錯**）可直接修一次再回報，但也要在回報中說明修了什麼。
5. 修改以「一輪一個方向」為限，避免無限迭代；每次改完回到本 Stage 重評。**複刻真實物件（三視圖流程）時，狀態管理（一輪一個元件群、凍結件要先解鎖）見 §16.9.5；若使用者指出的是「大量元件位置／大小／方向都錯」而不是零星微調，動工前先回 §16.9.0 判定要不要補／重取參考圖。**
6. **檢討筆記的數字以 trace 為準（P7）**：總耗時/渲染耗時/各輪耗時等必須從 session trace 或計時輸出摘錄，不得憑感覺估——Round 6 實測：筆記寫「約 20 分鐘」、trace 實為 31m35s，漏算模型生成時間低報 1/3。
7. **建議額外跑 §7.8 的收尾非視覺 Probe**：本 Stage 的 describe_image 只能看到「渲染出來長什麼樣」，看不到 HDRI 有沒有真的接上、材質數值對不對、方向公約有沒有真的落實這類資料層級問題——§7.8 用 blender-mcp 開啟成品 `.blend` 直接查場景資料，補這塊盲區，不需要視覺能力。

### 流程總覽

```
使用者一句話 → [Stage A] 風格觸發詞?→讀風格卡(§17) | 產品類?→讀組件圖譜(§13.7)
            → ≥300字設計簡報(比例規劃段+色票) + 元件表(LEVEL 1-6+遞迴拆解→組合方式+挖洞/凹凸描述+內嵌留白→材質factory，逐項對照圖譜)
            → 複刻真實物件+有視覺能力 → §13.12 規劃期正交參考圖研究(頂/前/側/後視角，核對裝配關係+色調，直接修元件表)
            → 反問確認一次 → [Stage B] §0 路徑解析 → copy build_template + scene_pkg + mat_lib + detail_lib
            → §12 方向檢查 + §13.7 圖譜核對 + §17 checklist → layout 完成即 CALIB 校準(攔截方向/缺件/Z-fighting/曝光)
            → 清輸出目錄 → 正式渲染(前台, §9.5)
            → [Stage C] 新鮮度斷言 → describe_image 評圖(含方向語義+缺件提問) → 回覆描述所見(含 mean)+列問題+提建議
            → 問 user → (同意才)查 §16.3 定位表修改 → 重評
            → (建議)§7.8 收尾非視覺 Probe：AI 自行開 Blender → get_scene_info/execute_blender_code 查 HDRI/材質/方向 → 併入 SCENE_STATE
            → (加分項)§7.8 完工展示：AI 自行開 Blender 載入成品 .blend 供使用者直接檢視
```

## 12. 方向與人體工學公約

**強制公約**：
1. **座標系約定**：每個任務在 CONFIG 註明「使用者/觀眾面向 = -Y（相機側）」；主體正面朝 -Y。
2. **方向一律用命名函數**（範本內建 `lean_back_quat()`/`lean_fwd_quat()`），禁止手寫 `Quaternion((1,0,0), ±θ)` 靠直覺選符號。函數內部符號已 probe 實測錨定。
3. **啟動斷言**：腳本開頭跑 `verify_orientation_math()`——用實際四元數乘 (0,0,1) 斷言方向公約仍成立（Blender 升級若改變行為會立即 fail fast，而不是靜默建出反向模型）。
4. **人體工學件建模後立即做語義方向斷言**（不只看 loc/dims）：
   - 座椅靠背：最高點世界座標 y **>** 靠背底部 y（向後仰），斷言失敗即 exit 1；
   - 樓梯/斜坡：上升方向與行進方向一致；桌面：水平；床頭：靠牆側。
   - 斷言用**世界座標頂點**（`matrix_world @ v.co`，讀前 `view_layer.update()`）——因為 transform_apply 後 object.location/rotation 已失效（§8#9）。
5. **人體工學常識表**（設計簡報階段就要對照，不要建完才發現）：座椅靠背後仰 5–15°、坐高 40–45cm、坐深 40–45cm；吧台椅坐高 60–65cm/75–80cm（配 90/105cm 吧台）；桌面高 72–75cm；床面高 45–55cm。使用者是人、會坐會躺會靠的物件，傾斜方向永遠是「支撑人往後靠」而不是「壓向人」。
6. **Stage C 評圖提示詞必須包含方向檢查**：describe_image 時明確問「靠背向哪個方向傾斜？人坐上去會往後靠還是被往前推？」——外觀描述不含方向語義，要主動問。

## 13. 組件常識公約（朝向與安裝位置的語義驗證）

**強制公約**：

1. **組件三問（設計簡報階段對每個組件回答，寫進腳本註解）**：
   - **給誰看/給誰用？**（觀眾=駕駛？行人？相機？）→ 決定資訊面/功能面的朝向。
   - **沿什麼方向運作？**（輪子滾動方向=車行進方向、車身長軸=道路方向、斑馬線條紋⊥行人通過方向）
   - **裝在什麼上、偏移到哪一側？**（牌面在桿的迎車側、燈頭懸在路面上方、椅背在坐墊後方）
2. **旋轉組合禁止心算**：兩個以上四元數/歐拉角組合（`q1 @ q2`、`rot=(a,b,c)`+`quat=`）必須先 `--python-expr` probe 出一個單位向量經組合後的世界座標，確認符合三問答案再寫進腳本。輪子這種「軸向件」probe 的斷言對象是**軸向量**（`(0,0,1)` 經變換後應≈世界 ±X 或 ±Y，視行進方向而定），不是位置。
3. **安裝偏移量常數化**：招牌/燈箱/旗面類「掛在桿上的面」一律定義 `MOUNT_OFFSET`（面中心到桿軸心的水平距離 ≥ 面厚/2 + 桿半徑），禁止預設 0（穿心）。
4. **場景級語義斷言（verify_scene_assertions 必含以下檢查，世界座標頂點計算，失敗即 exit 1）**：
   - **軸向件**：每個輪子的軸向量與該車行進方向垂直（`abs(dot(axis, forward)) < 0.1`）；
   - **長軸件**：車身/船身/機身長軸與所屬道路/水面方向對齊（角度差 <15°）或明確註記為「橫向展示」；
   - **資訊面**：招牌/廣告面法線與「觀眾位置」的點積 >0，且面中心到支撐桿軸心距離 ≥ MOUNT_OFFSET；
   - **懸臂件**：紅綠燈/路燈的燈頭世界座標投影落在路面（或人行道）範圍內，不在桿的正下方。
5. **常識安裝規範速查**（來源：美國 MUTCD §2A.20 等，已濃縮；寫實場景照此，遊戲風可放寬 50% 但禁止歸零）：
   - 路側標誌牌面⊥車流方向、迎向來車；桿裝於牌背中央或側邊，牌面與路緣水平淨距 ≥0.3m（市區）；
   - 號誌燈面迎向它管控的車流，懸於路面上方或路側 4.5–5.5m 高；
   - 路燈臂伸向被照面（車道/人行道），燈頭在路面上方而非桿頂正上方；
   - 車輛沿路邊平行停放，車身長軸∥路緣，距路緣 0.3m 內；
   - 輪子軸向⊥行進方向；前輪可有轉向角但同軸兩輪平行。
6. **Stage C 評圖提示詞必須點名方向語義**：對組件逐个問「這輛車的輪子軸向對嗎？車是平行路邊停的嗎？這面招牌的正面有沒有被它的桿子擋住？」——本輪實證：泛泛問「描述這張圖」永遠抓不到這類錯誤。

### 13.7 產品組件圖譜（「組件缺件」比「組件裝反」更隱蔽）

**強制公約**：

1. **產品類主體（相機/手錶/音響/家電/車輛等「有公认組件清單的工業品」）建模前必查組件圖譜**：`assets/anatomy/<品類>.md` 存在 → read_file_native（或你的 agent 平台上等價的讀檔工具）讀取，Stage A 設計簡報的組件清單**以圖譜為底線起手**（六面逐面列，缺件在簡報階段暴露給使用者確認）；不存在 → 照 `assets/anatomy/_TEMPLATE.md` 現場建圖譜（web search 該品類 anatomy/exploded view/teardown 2-3 輪佐證，禁止純憑記憶列），建完存回 skill assets 供下次復用。**旋轉對稱容器類（碗/杯/瓶/花瓶等，見 `assets/anatomy/vessel.md`）是例外**：這類主體沒有前後左右六面語義，圖譜改用「剖面路徑」格式描述，不套用六面表，Stage A 簡報照該圖譜自己的格式起手，不要硬套六面表結構。
   - **圖譜是地板，不是天花板（見下方獨立說明段）**：圖譜列出的組件是「至少要有這些，缺了算漏件」的最低要求，**不是「只需要這些、多了算過度發揮」**。判斷力足夠的模型如果知道這個品類現實中還有圖譜沒寫到的細節（例如圖譜寫了「錶帶要有縫線」，模型知道金屬鏈帶錶款鏈節之間還需要銷釘連接、圖譜這版剛好還沒寫到這點），**直接加上去，不要因為圖譜沒提就跳過，也不要因為圖譜沒提就以為那樣不對**。圖譜的存在是「防止漏掉常被忽略的必要組件」，不是「限制細節上限」。
2. **六面清單制**：圖譜按 前/後/頂/底/左/右 六面列組件——單面視角渲染看不到的組件是誤判高發區，六面制強制「背面也有東西」。
3. **成對組件表**：貫通結構（觀景窗前窗↔目鏡、螢幕↔感應器、左右背帶環）單獨列表，**缺一即錯**；assertions.py 對每對組件寫存在性斷言（例：背面必須存在含 Glass 材質的窗件）。
4. **細節地板**：每個「可轉/可按/可握」組件必須有微觀起伏——轉盤/鈕必上 `detail_lib.knurl_ring()` 滾花（齒數走費波那契 34/55/89），握把必上 `grip_strip()` 防滑紋，刻度面必上 `dial_grooves()`。光滑圓柱轉盤 = 塑膠感（Round 9 使用者實評）。場景級用 `audit_detail_density()` 審計（細節件占比 ≥25%，build 階段統計零件數傳入）。
5. **Stage C 評圖提示詞加問缺件**：「這個品類的背面通常有什麼？圖裡看得到嗎？」——渲染只有單視角時，用 SCENE_STATE 的六面組件清單對照圖譜核對，不能只靠評圖。
6. **最低限度表現原則（通用規則，見 `anatomy/car.md`/`anatomy/_TEMPLATE.md`）**：功能性 MUST 部件不等於要做出可動機構，判準是「這個部件不存在，現實中這個品類還能不能正常運作」：不能（車沒有門+門把，人上不了車）就是 MUST，即使不用真的能開闔，也至少要刻出分模線+建出對應小型物件（門把手），不能整片渲成沒有分件痕跡的實心量體。這是第 1 條「六面清單」的延伸——圖譜解決「有沒有想到這個組件」，這條解決「想到了但因為不用真的能動就乾脆不畫」的偷懶模式。
   **手部接觸面延伸**：任何真實使用情境下會被手握持/操作的表面（球棒/球拍握把、工具把手、門把、方向盤、旋鈕、扶手），現實中幾乎不會是光滑表面——一定有止滑處理（纏帶螺旋紋、滾花、菱形防滑紋、肋條）。這類表面規劃階段要明確列出止滑處理方式，動工時套 `detail_lib.knurl_ring()`/`grip_strip()` 或沿表面手動加螺旋/肋條幾何，不是套個材質就算完工——材質決定顏色/反光，紋理才是「看起來真的能握」的視覺訊號。

### 13.8 空間類主體必備元素清單（「規劃階段漏列」比「組件裝反」更難救）

**強制公約**：

1. **空間類主體（房間/場景，非單一產品——教室、咖啡廳、辦公室、展廳等）建模前必查空間圖譜**：`assets/anatomy/spaces/<空間類型>.md` 存在 → read_file_native（或你的 agent 平台上等價的讀檔工具）讀取，Stage A 設計簡報的「必備元素清單」段**直接從圖譜抄**；不存在 → 照 `assets/anatomy/spaces/_TEMPLATE.md` 現場建圖譜，建完存回 skill assets 供下次復用。
2. **七類候選清單，寧可多列不要自我審查漏列**：結構殼體（牆/地板/天花板/門窗）、功能核心物件（這個空間類型存在的理由本身——教室的黑板、咖啡廳的吧台）、座位/工作站、**動線/走道**、收納、照明、裝飾/氛圍。
3. **每個候選元素跑反思測試**：「拿掉這個，這裡還算不算是這個空間類型？」——算 → 標 OPTIONAL（例如教室缺風扇）；不算 → 標 **MUST**（結構性/功能性必需，Stage A 不准跳過，例如教室缺動線）。
4. **動線永遠是 MUST，且要獨立驗證，不能用「家具間隙」矇混**：任何有多組家具/座位的空間，Stage A 必須明確宣告至少一條主要動線的位置與寬度；Stage B 擺位完成後用 `assert_min_gap(group_a, group_b, min_gap, label)`（`build_template.py` §13.8 新增）驗證那條動線的實際淨空間距達到最低標準（一般抓 ≥0.75-0.9m，對應常見建築規範的最小通道寬度）——這條路徑要**明顯比其他家具間距更寬**，不是隨便找一個比較大的縫隙就充數。
5. **Stage A 簡報必須逐項對照圖譜回報**：MUST 項目全部要在簡報裡指出「在哪、多大」；OPTIONAL 項目可以列出但聲明「本次先不做」，讓使用者在確認階段就看得到取捨，而不是動工後才被動發現漏了什麼。
6. **每次實戰踩到新空間類型的坑** → 回填該空間圖譜的「常見錯誤模式」欄（同 §13.7 muscle memory 機制）。

### 13.9 通用幾何審查——穿模/重疊/懸空/擺位離群（一次掃一批物件，不用預先知道正確答案）

**定位**：§7.7 的 `assert_within_room`/`assert_grounded` 與 §13.8 的 `assert_min_gap` 都是「呼叫端已經知道該檢查誰、預期關係是什麼」（房間邊界、支撐面高度、走道兩側分組）——本節反過來，給一批物件，函式自己去發現有沒有異常，不需要事先知道正確答案。**容許誤差全部參數化，只抓量得出來的問題，不抓肉眼看不出來的浮點/貼合誤差**——這是使用者明確要求的容忍原則。

**三個函式（`build_template.py`）**：

1. **`audit_interpenetration(objects, tol=0.01, mode="aabb", respect_mates=True)`**——兩兩掃描物件世界包圍盒，三軸重疊量都 ≥ tol 才回報。物件邊緣貼合（牆接地板、桌腳接桌面）本來就會在某一軸剛好重疊到 0，這是正常的「相接」不是穿模；只有三個軸向都有實質重疊量才是真正的穿模/重疊候選。tol 預設 1cm。複雜度 O(n²)，物件數多時建議先用命名規則分批比較（同一批家具內部），不要整場景互比。**`mode`（2026-09-14 新增）**：`"aabb"`（預設）只比包圍盒、輸出與舊版逐字相同；`"bvh"` 把 AABB 當候選快篩、通過的配對再用 `BVHTree.overlap()` 做**網格級**面相交判定，只有真的互穿才回報——**機構/總成場景（同軸嵌合件）用這個**。曲面宿主上的附件同理（見下方「AABB 判重疊天生不可用」段）。`respect_mates=True`（預設）跳過 `mark_assembly_mate()` 宣告過的意圖裝配配對，跳過幾對會記進 log。
2. **`audit_floating(objects, max_gap=0.01, max_sink=0.01)`**——每個物件底面 5 個取樣點（bbox 底面四角+中心）垂直往下 raycast，找最近的支撐面；連續鑽過自己的底面（避免第一擊打到物件自己），一路找到下面真正的東西。淨空距離 > max_gap 判定懸空；命中面在物件底部之上超過 max_sink 判定陷入。跟 `assert_grounded` 的差別是不需要事先手動算好 `expected_base_z`。**自帶 bbox 快篩前置**：物件正下方已有其他物件 bbox 頂面落在 `max_gap` 容差內就直接判定有支撐、跳過該物件真正的 raycast，只有找不到 bbox 候選才進入完整逐點 raycast——快篩只省成本，不會漏掉真懸空（快篩門檻就是 `max_gap` 本身，不是放寬過的值）。**這支函式的邏輯天生只認「重力式平放支撐」**：天花板燈、吊燈、懸臂吊車臂、螺栓鎖在桁架/桅杆側面的告示牌、格狀桁架的斜撐/環箍、鎖在梯柱側面的爬梯踏階——這類「側向鎖固/懸臂固定」而不是「放在什麼上面」的物件，底下天生不會有任何東西，一定會被向下 raycast 誤判懸空，不要傳進來檢查。**手動呼叫時**自己把這類物件從 `objects` 清單過濾掉；**跑到 `T.main()` 自動審查時**（見下）改成建好物件當下立刻呼叫 `T.mark_side_attached(obj)` 標記（可一併宣告 `host=`/`stand_off=`，見下方第 4 條），因為自動審查沒有呼叫端可以現場過濾清單。
3. **`audit_spacing(objects, label, tolerance_ratio=0.4)`**——同批實例的最近鄰間距離群值掃描，抓「某一件擺位間距明顯跟其他不一樣」（網格/序列擺位時，某一件座標算錯，肉眼在物件數量多、視角遠時不一定看得出來，但數值上抓得到）。tolerance_ratio 預設 0.4：最近鄰距離低於中位數 0.6 倍或高於 1.4 倍才算離群。

4. **`audit_attachment_contact(objects=None, hosts=None, max_gap=None)`**——貼附件貼合稽核：抓「被 `mark_side_attached()` 排除在懸空審查之外、卻根本沒貼到宿主」的浮空件（量測核心是 `surface_gap()`，見 §0.5）。判定：物件與宿主的網格**相交** → 間距 0（零件插進/嵌進宿主時它的頂點根本不在表面上，只有相交測試答得出「真的接觸了」）；未相交 → 取物件**頂點與面心**到宿主表面的最近距離（只取頂點會系統性高估：0.3m 見方的平板貼在 R=2.1m 圓柱上，最近的是板面中心，量頂點會把 10mm 讀成 16mm）。宿主候選自動排除物件自身、外殼（`OUTLINE_SHELLS`，貼著主體外推建立）、停放中的母版（`PARKED_MASTERS`，座標停在設計單位）——實測包住量測物件的假外殼會把 0.43m 讀成 0.002m。物件可用 `mark_side_attached(obj, host="...", stand_off=0.35)` 宣告宿主與刻意保留的距離，稽核就改驗「實際間距 ≈ 宣告值」——**宣告本身是被檢驗的對象**，宣告了不存在的宿主名會直接回報。

**用法**：這幾個 audit_* 函式都回傳問題清單（`list[str]`），**不直接 `fail()`**——自動發現天生有假陽性風險，先用 `report_or_fail(issues, step, hard=True)` 印出全部項目讓人/模型判斷合不合理，`hard=True`（預設）才真的擋下來；真的是已知的合理誤報，把該物件從傳進去的 `objects` 清單過濾掉，不要圖方便把 `hard` 關掉全部放行。

**建議時機**：中大型場景（>20 個實例，或任何有多組家具/座位的空間類主體）在 CALIB 通過、正式渲染前，`assertions.py::verify_scene()` 裡至少跑一次 `audit_interpenetration`（全部主體+配角實例）跟 `audit_floating`（排除已知懸空件）；同一批網格/序列擺位（例如課桌椅、路燈、窗單元）額外跑 `audit_spacing`。

**排除假警報必須同時補上該族群的實質檢查（減法要有加法）**：`audit_floating()` 只認重力式平放支撐，側向鎖固/懸臂件靠 `mark_side_attached()` 排除是必要的——但排除之後如果沒有等價的替代檢查，這批物件就沒有任何東西在看「有沒有真的碰到宿主」：實測整站 123 件全標記 → 106 件浮在艙體外 0.04–0.58m，照樣通過 CALIB、曝光守衛、語義斷言與深度閘門，直到肉眼看到。規則：**凡是用「排除」讓某支審查閉嘴的地方，同一個提交裡必須補上針對該族群量測「真正該成立的那個關係」的檢查**；`T.main()` 對所有 `_side_attached` 物件自動跑 `audit_attachment_contact()`（預設就開，不依賴呼叫端記得），結果寫進 `SCENE_STATE.auto_geometry_audit.attachment_contact`（`ran`/`checked`/`tolerance_m`/`issues`/`side_attached_total`/`declared_host`，Stage C 必查）。**配額界線**：標記數 ≥10 且超過全部 mesh 物件一半時 `main()` 印 WARNING——排除機制被全站套用時，懸空審查對這批物件等於不存在，必須靠上面這道貼合稽核接手。

**AABB 判重疊對「凸面宿主上的附件」天生不可用**：圓柱/球/外殼宿主的包圍盒是一整個方盒，任何貼在曲面上的附件其 AABB 必然落在這個方盒裡——`audit_interpenetration()` 對這類配對只剩兩種結局：把附件推離宿主（公分級浮空，卻因為「不重疊」而完全通過），或整批誤報重疊（實測一片離艙面 16mm 的貼附板仍被回報三軸重疊 0.30×0.22×0.24m；修正後全站回報 104 筆「主體 × 貼附件」重疊，逐筆看全是真實裝配）。判準：**宿主是凸面/曲面時，host↔attachment 配對的穿模結論不採信 AABB，改用 `audit_attachment_contact()` 量間距**；真的要抓穿模得換網格/BVH 相交判定。

**機構/總成件的「同軸嵌合」是同一類問題的最大宗（2026-09-14 汽車底盤案例）**：卡鉗跨在碟盤上、輪圈套住輪胎、羊角軸承包住輪轂——這些配對的 AABB 必然三軸重疊，`audit_interpenetration()` 實測回報 **102 筆「穿模」**，逐筆查證全是正確裝配（真正該抓的一筆都沒漏，但雜訊會把訊號淹掉）。處理方式兩條，可並用：① **`audit_interpenetration(objects, mode="bvh")`**——AABB 只當快篩、結論由 BVH 面相交給，良好裝配（有淨空/公差）的嵌合件自然不再命中；② **`mark_assembly_mate(a, b, note=...)`**——宣告「這一對本來就該嵌合/壓配」，AABB 模式就不再回報這一對（跳過幾對會記 log）。**這類零件的「浮空」是另一種形式的雜訊**：它們底下沒有任何東西（懸空審查假警報）、表面也沒有面對面貼合（用貼合稽核量會回報「離宿主表面 0.048m」，而且報的「最近宿主」還是全場任意的另一件——實測卡鉗螺栓的最近宿主被判成輪胎）。**第三類標記 `mark_joint_attached(obj, host=...)` 就是為了它們**：`host` 必填、`max_gap` 是對宿主的接合包絡（預設 50mm），由 `audit_joint_attachment()` 逐件量測並寫進 `auto_geometry_audit.joint_attachment`（`ran`/`checked`/`tolerance_m`/`issues`/`joint_attached_total`/`declared_host`），與 `mark_side_attached()` 一起被排除在懸空審查外、但**不合併計算**（兩類各有各的替代稽核）。實測一台底盤：334 件被標記成側向鎖固、其中只有 3 件宣告宿主，結果 310 件被回報浮空——**「標記」要配「宣告宿主」才有意義，只標不宣告等於換一種雜訊**。**內裝案例（同日第二輪，同一台車的座艙）重現同一模式且規模更大**：內裝新增 291 件、全場 663 件，稽核回報 500+ 筆穿模與 300+ 筆貼合異常，逐項查證同樣全是同軸嵌合件（卡鉗×碟盤、輪圈×輪胎、羊角×輪轂），已定稿的 368 件底盤幾何一件未改——同軸嵌合的雜訊會隨場景規模等比例膨脹，機構/總成場景**開場就該**用 `mode="bvh"`＋`mark_joint_attached()`，不要等回報爆量再逐筆人工查證。

**配額界線（更新）**：側向鎖固＋接頭/軸承兩類被排除的件數合計 ≥10 且超過全部 mesh 物件一半時，`main()` 印 WARNING——排除機制被全站套用時，懸空審查對這批物件等於不存在，必須靠兩道替代稽核逐件接手。**接續輪次的實務做法**：內裝案例實測 516/629 件被標成側向鎖固（其中幾乎全是接頭類卻沒宣告宿主），該批物件的懸空審查因此等同停用——後續新增零件時**分批標記**（只標本輪新增件），或直接把同軸件改用 `mark_joint_attached()`，讓替代稽核接手，而不是靠停用。

**反模式：禁止「調大間隙讓審查器閉嘴」**：任何「為了讓某支檢查通過而調大的間隙/偏移常數」都是 smell（實例：貼附件離宿主表面留 0.10m，理由寫在註解裡是「AABB 隨之外擴 0.07，OFF 必須大於這個外擴量，才不會跨進宿主 AABB」——AABB 審查只判重疊量、不判間隙，所以這 0.10m 讓檢查全綠，在 4.2m 徑的艙體上卻是肉眼一眼可見的浮空）。規則：**檢查器不適用某類幾何時，修檢查器（換量測方法/排除該類配對），不是把幾何搬開讓它閉嘴**；貼合間隙用毫米級防共面裕度即可（`MOUNT_GAP = 0.005` 一級），這個常數必須服務視覺、不能服務檢查器。

**擺在圓柱/球等凸面上的附件：高度用「該切向位置的實際表面」，不是最高母線或外接半徑**：圓柱半徑 R、軸在 (y=0, z=Z) 時，切向偏移 y 處的表面高度是 `Z + sqrt(R² − y²)`；寫成 `Z + R + OFF` 會隨 |y| 增大而線性浮空（R=2.10、y=1.55 → 表面只有 1.417，差 0.683m；全站 123 件裡 106 件因此浮空）。同一原則也管「用零件外接尺寸代替實際安裝面」的情形——軸向沿徑向的驅動機構，決定貼合的是內側半長而不是半徑。擺完用 `assert_attachment_contact()` 驗，不要靠肉眼看渲染圖。

**母版 canonical 安裝面契約**：`make_xxx()` 的「安裝面」必須有實際幾何落在該平面——(a) 法蘭環/環形件以**底緣**落在安裝面（中心 z 取厚度一半，別讓底緣懸空）；(b) 圓柱/球這類「最低點只是切線」的零件要有實體安裝座/支架，不要拿切線當安裝面；(c) 有 stand-off 的零件在 `mark_side_attached(..., stand_off=)` 宣告，由稽核檢驗；(d) 貼合曲面的貼花，`proud` 只補**離散化弦垂 + 防共面裕度**，不要補整片弧的弓高（整片弧弓高 `R(1−cos(θ/2))` 會讓逐列已落在曲面上的貼花浮起公分級：實測 0.107m）。元件表（§11 Stage A item 3）要在每個貼附件的條目寫出「宿主 + 安裝方式 + 預期間距」。

**`T.main()` 現在自動跑前兩項，不必等呼叫端記得**：一次性 raw script（不是正式 scene_pkg）最容易忘記手動呼叫這幾個審查——而這些問題本來一秒鐘就能被 `audit_interpenetration`/`audit_floating` 攔下。現在 `subject_fn()` 建完後，`main()` 會自動對全部 mesh 物件跑這兩項（`hard=False`，只報告不擋渲染），結果寫進 `SCENE_STATE.auto_geometry_audit`——**Stage C 視覺評審時這個欄位一定要查**，跟 LUMA_STATS 同等級的必查項目。**同一個欄位裡的 `framing` 子欄位是構圖入鏡審查的結果**（主體覆蓋率/是否被裁切，見 §15.4），跟穿模/懸空一次查完，不要只讀前兩項。**改成兩道獨立門檻，不再共用一個 300（來源：復古腳踏車案例——368 個物件超過舊版單一門檻，兩項審查整組被跳過，腳架懸空這種一秒鐘該抓到的問題沒人攔，只跑了針對性語義斷言）**：`audit_interpenetration` 每次比較只是 6 個浮點數大小比較，就算 O(n²) 物件數上千也不過零點幾秒，門檻拉高到 1500；`audit_floating` 的 `scene.ray_cast()` 才是真正貴的部分，門檻維持較保守的 800，但這支函式本身 自帶 bbox 快篩前置（物件正下方已經有其他物件 bbox 頂面落在容差內，直接判定有支撐、跳過該物件的 raycast，只有找不到 bbox 支撐候選才進入真正的逐點 raycast）——良好裝配的場景通常能省掉 80%+ 的 raycast，800 門檻對它而言仍算安全。兩者各自獨立判斷是否要跳過，不會再因為其中一項物件數超標就把另一項也一起犧牲；`SCENE_STATE.auto_geometry_audit` 現在分別回報 `interpenetration_ran`/`floating_ran`/各自的 `_skip_reason`，Stage C 檢查時兩個欄位都要看，不能只看舊版那個合併的 `ran`。物件數真的超過兩道門檻的巨型場景，仍照上一段建議手動分批呼叫。這個自動審查不取代 §16 scene_pkg 裡明確寫在 assertions.py 的針對性斷言，是多一層「就算忘記寫斷言也攔得到明顯錯誤」的保底。**懸空檢查自動排除 `mark_side_attached()` 標記過的物件**：自動審查對全部 mesh 物件無差別呼叫 `audit_floating`，但這支函式的懸空判定天生只認重力式平放支撐——之前這條路徑沒有任何過濾機制，一個有發射塔架/吊車/桁架告示牌這類懸臂結構的場景，168 個物件能洗出數十筆懸空假警報，真正的懸空問題被淹沒在雜訊裡，`SCENE_STATE.auto_geometry_audit` 這個欄位形同虛設。現在 `main()` 會自動跳過帶 `mark_side_attached()` 標記的物件——**建構這類懸臂/側向鎖固元件的工廠函式裡，建好物件當下就要呼叫 `T.mark_side_attached(obj)`**，不是事後才想到；沒標記的話自動審查一樣會誤報，只是這次有了正確的排除方法，不是無解。穿模檢查（`audit_interpenetration`）不受此標記影響，側向鎖固一樣可能穿模，一樣要抓。**容差依主體實際 bbox 對角線縮放**（`max(1mm, min(5cm, diag*1%))`，不再固定 1cm——相機案例實測抓到盲區：一台 138mm 寬相機的過片扳手臂懸空 2.6mm，固定 1cm 容差完全在容許範圍內、審查回報「無問題」，但 2.6mm 相對於扳手臂自己只有 1.6mm 厚度是明顯懸空。手動呼叫 `audit_interpenetration`/`audit_floating`（大場景分批呼叫時）也要記得比照這個縮放邏輯自己算 `tol`/`max_gap`/`max_sink`，不要照抄函式原本的 1cm 預設值——那是給呼叫端沒指定時的保底值，不是任何尺度都適用的正確值。

**環境件不進自動審查清單（地面除外原則）**：`T.main()` 的自動審查只掃**主體物件**，`Ground` 物件與 `Env_` 前綴的環境件不列入比較——兩個理由：① 主體尺度才是容差縮放的依據，把 20000m 的地面算進場景 bbox 會讓容差直接頂到上限（138mm 相機該用約 1.4mm 容差去抓 2.6mm 的懸空扳手臂，被撐成 5cm 就完全失效）；② 巨型平地跟誰比都是「貼合」，沒有穿模資訊。**地面本身仍留在場景裡**——`audit_floating` 用 `scene.ray_cast()` 打的是整個場景，所以地面照樣能當支撐面；這也要求地面必須在審查前就建好（`main()` 已把 `build_ground()` 提到審查之前——實測：直接站在地面上的鋪面大板，在舊順序下會被回報「嚴重懸空」，新順序下 0 問題）。

**母版也不進自動審查清單（`park_master()` 自動登錄）**：母版是為了實例復用而建的樣板，幾何留在**設計單位**（mm 數值）、座標停在原點後被 `park_master()` 以 `hide_render` 隔離，跟已換算成公尺的實例差 1000 倍。不排除的話，`_scaled_tol = max(1mm, min(5cm, diag*1%))` 這條「依場景 bbox 對角線縮放」的容差會被單一個母版撐到上限——實測 iPhone 案例：主體 0.18m、`Mst_LensAssembly` 16.2m，容差從應有的 1.8mm 變成 5cm，同時懸空審查與構圖審查灌入數十筆假警報（母版的 `loc=(0,0,0)` 讓它被判「嚴重懸空」、落在相機後方被判「沒對準主體」），真正的問題被雜訊淹沒。**`park_master()` 現在會把母版名登錄進模組層的 `PARKED_MASTERS`，`main()` 的自動審查與構圖審查據此排除**——所有走範本母版流程的場景自動受益，呼叫端不需要做任何事。前提是母版一律經 `park_master()` 隔離（本來就是 §14 的強制公約）。

**Stage A 就該做的算術可行性檢查**：把研究到的真實數字（例如「三根柱、直徑 9m、中心相距 7m」）套進多件結構配置前，先手算一次「兩兩間距 vs 直徑總和」有沒有物理上矛盾（4.5+4.5=9 > 7 就是會重疊，不是視角問題）。問題多半出在研究來源的兩個數字對不上（例如「相距」是圓心距還是淨空間隙沒交叉檢查），不是函式壞掉。就算是一次性 raw script，建完也該至少呼叫一次 `T.audit_interpenetration()`。

### 13.10 CNC 機床式建模操作字彙（基礎形狀拼接症候群的反制）

**CNC 機床視角**：真實世界的產品/建築幾何不管是鑄造、射出成型、CNC 加工、木工還是營建，都是「基礎量體 + 一組有限的標準加工操作」疊代出來的，不是憑空長出複雜曲面。「量體」（`add_box`/`add_cyl`）跟「表面裝飾」（`detail_lib`）之外，還缺「移除材料」這類操作——任何洞（窗洞/門洞/鑽孔/通風孔/線孔/卡槽）不能只靠「該處不建量體」假造，做不出有厚度的洞壁。

**CNC 加工操作 → Blender 對應表**：

| CNC/製造操作 | 真實效果 | Blender 對應技法 | 狀態 |
|---|---|---|---|
| 鑽孔/銑孔/開槽（drilling/milling/slotting） | 貫穿或不貫穿的孔洞、卡槽，看得到洞壁厚度 | 布林差集（Boolean DIFFERENCE） | **新增**：`build_template.cut_hole(host, cutter)`，已 Blender 5.1.2 實測驗證 |
| 倒角/去毛邊（chamfer/deburr） | 銳邊變成小斜面 | `bevel(width, segments=1)` | 已有（`add_box(bevel=...)`），但預設 `0.0`——未主動指定就是零倒角，等於預設「沒去毛邊」 |
| 導圓角（fillet） | 銳邊變成圓弧過渡面 | `bevel(width, segments≥3)` | 同上，半徑/分段數要主動決定，不是放著預設值不管 |
| 沉頭孔/埋頭孔（counterbore/countersink） | 兩段式孔（寬淺+窄深，螺絲頭沉進表面） | 兩次 `cut_hole()` 同軸疊加（先寬淺、再窄深） | 用現有函式組合即可，不需要新工具 |
| 滾花/刻度（knurling/engraving） | 表面規則凹凸紋理 | `detail_lib.knurl_ring()`/`dial_grooves()` | 已有（§17.4） |
| 陣列孔/陣列肋（patterned holes/ribs） | 規則重複的孔/肋 | 迴圈呼叫 `cut_hole()`，或 `instance()` 大量複製凸起件（§14） | 機制已有，過去很少被用在「孔」上，只用在外部裝飾件 |
| 挖凹陷/沖壓成型（non-through recess/stamping） | **不貫穿**的平滑凹坑——座椅坐墊、碗、水槽、嵌入式螢幕/按鍵 | 布林差集，但 cutter 只部分穿入 host（球體/橢球，中心埋在表面之下） | **新增**：`build_template.carve_depression(host, center, radii)` |

**規則**：

1. **有厚度的實體上出現開口，一律用 `cut_hole()` 布林差集**——窗洞、門洞、通風孔、把手孔、線孔、按鈕孔、插槽都算。**禁止**用「該處不建量體」的假開口帶過（做不出洞壁厚度，遠看沒差、近景/斜角一眼看穿是假的），除非那個開口在現實中本來就是「組件間的自然分件縫」而不是「挖出來的洞」（例如兩塊預製牆板中間的接縫）。
   - **「開口」不是只有貫穿孔**：座椅坐墊、碗、水槽、嵌入式螢幕/按鍵這類**不貫穿的平滑凹陷**，一樣是「該挖掉的地方就要真的挖掉」，不是隨手一塊平板了事——只是改用 `carve_depression(host, center, radii)`（cutter 刻意只部分穿入 host 的球體/橢球）而不是 `cut_hole()`（cutter 要求兩端都穿透）。判準：**這個部位在現實中是不是靠「移除材料」做出來的凹面**（座椅坐墊是模具沖壓/發泡成型出的凹陷，不是一塊實心方塊貼在骨架上）——是，就挖；不是（例如純裝飾用的貼合曲面），才維持實心量體。
2. **造型主體的外露邊緣，必須主動決定倒角/導圓角半徑**——哪怕只是 1–2mm 的去毛邊，不是留著 `add_box` 預設的 `bevel=0.0` 銳邊不管。數位精度的 90° 直角在真實世界的鑄造/加工/木工件上幾乎不存在，是「基礎形狀直接拼接」最明顯的視覺破綻。半徑怎麼定：有風格卡時照卡片走（§17：精密工業風小圓角、低多邊形大圓角、黃金比例費波那契分級 §15.3）；沒有風格卡時抓一個跟主體尺度成比例的合理值——小型手持物 1–3mm、家具家電 2–5mm、建築構件 5–20mm，不是留零。
3. **判準是「這個邊/這個洞在對應的真實製造方式下會不會自然帶有斜面/圓角/是實體挖出來的」，不是「每個邊都要處理」**——結構縫隙、被其他物件完全遮蔽的內部/背面邊、真正的功能性直角（例如結構承重角）不需要，機械套用在每一個 primitive 上反而是另一種形式的「沒有理解只是套公式」。
4. **迴轉對稱的車製/CNC 加工件（錶冠/旋鈕/按鈕/把手頭/瓶蓋這類小零件，也包含錶殼中殼這類「整支產品最大塊但本質仍是車製件」的量體）一律用 `shape_lib.lathe(profile_fn)`/`lathe_profile(points)`/`tapered_rod()`，不能只用 `add_cyl()`+`bevel()` 或 `flat_ring()` 頂替**（本規則適用於任何現實中車床車出來的迴轉體，不限零件大小）：`add_cyl()`+`BEVEL` modifier／`flat_ring()` 都只能維持等直徑或固定厚度的剖面、最多在邊緣切一圈小圓角，剖面輪廓本身完全不變——但真實車製零件的半徑是沿軸向連續變化的（頂端常收窄或做出小圓頂，根部常有一圈收腰過渡，大型中殼常中段微凸或略往下收窄貼合人體），這是「拉伸+邊緣倒角」這個組合結構性做不到的，不是倒角半徑加大就能補。凡是「現實中會用車床/CNC 車削成形」的迴轉件——錶冠、旋鈕、按鈕頭、瓶蓋、錶殼中殼、車削桌腳/欄杆望柱、球棒——一律用 `lathe(profile_fn(z)->radius, z_list, segments, mat)`（剖面是高度的單值函數）／`lathe_profile(points, segments, mat)`（剖面路徑允許反折，中殼下緣有內縮台階這類形狀要用這支）／兩端粗細不同時用 `tapered_rod(a, b, r1, r2, mat)`，不要預設走 `add_cyl()`/`flat_ring()`。**`flat_ring()` 本身沒有錯，適用場景是刻意保持等厚、兩端平齊的環（錶圈、鏡頭卡口環）——判準是「這個量體的設計本意就是等厚扁平環」還是「只是偷懶沒車出真正輪廓」，不是看量體大小。**
5. **厚度/直徑不要憑「安全感」給大，要有真實比例依據**（真實錶冠厚度:直徑常見比例約 0.35–0.5，不是接近 1:1；沒有查證真實數字時，很容易本能地選一個防禦性偏大值。）`assets/proportions_lib.py`（§0.5）`ergonomic_reference()`/相機/家具等各品類計算機已經覆蓋常見品類，沒有專屬計算機的小型硬體，查真實產品規格或至少對照同類尺度物件的比例，不要無查證地選「看起來安全」的厚度。
6. **把一組物件散佈/插入某個圓形容器造型後，一律呼叫 `assert_within_radius(objs, center_xy, max_r, label)` 驗證，不要只靠公式「看起來合理」**：任何「筷子插進筷筒」「花插進花瓶」「筆插進筆筒」「螺絲繞瓶口一圈」這類擺位，公式本身有沒有語法錯誤跟「算出來的範圍是否真的落在容器半徑內」是兩個獨立的問題，寫完擺位公式後就該呼叫一次驗證，不能只憑「這個公式看起來合理」就跳過檢查。

**造型雕塑操作 → `shape_lib.py`（§0.5）**：上面的表只解決「移除材料挖洞」跟「統一去毛邊」，不解決「非 primitive 輪廓」問題——car/家電外殼/瓶身這類造型，本質是「量體→局部切割出新頂點→移動頂點塑形」疊代出來的，對應 `shape_lib.py` 的操作：

| 操作 | 效果 | 函式 |
|---|---|---|
| 切割量體、新增邊迴圈 | 在指定位置切出新的頂點/邊，供後續移動塑形 | `loop_cut(obj, axis, position)` |
| 篩選特定頂點 | 從目前頂點裡挑出符合世界座標範圍的子集 | `select_verts_by_bounds(obj, x=, y=, z=)` |
| 移動選定頂點 | 把篩選出來的頂點整體平移，改變局部造型（例如擋風玻璃斜角） | `move_verts(obj, target_coords, delta)` |
| 精確選邊倒角/導圓角 | 只倒特定邊（跟 `add_box` 的全物件統一倒角不同，適合手動編輯過的不規則 mesh） | `bevel_edges(obj, edge_endpoints=… 或 angle_limit_deg=…)` |
| 左右/前後對稱造型 | 只建一半，鏡射出另一半 | `add_mirror(obj, axis)` |
| 兩個量體融合成一個連續表面 | 布林聯集（跟 `join` 不同——`join` 只是資料合併，交界處不會重新計算表面，近看兩塊量體是分開拼上去的；`boolean_union` 真的會在交界處重算拓撲） | `boolean_union(a, b)` |
| 收分/漸縮輪廓 | 沿軸向線性縮放剖面（車頭變窄、瓶頸內縮、塔身收分） | `taper(obj, axis, factor, pivot)`（垂直軸以**該斷面自身外框中心**為基準縮放，非世界原點，見 §8 #18） |
| 螺旋彈簧/線圈 | 真正算螺旋路徑再用 curve_tube 一次成型（避震器彈簧），不是疊一排 torus 假裝 | `coil_spring(name, a, b, coil_radius, turns, tube_radius, mat)` |
| 相對定位（取代手寫絕對座標） | 讀某物件目前世界座標包圍盒，回傳其上一個具名參考點（六面+中心，面上可指定滑動位置），host 物件尺寸/位置改了重跑腳本自動跟著對——簡化版取自論文 mate-driven placement 概念（見 §16.1） | `anchor(obj, face, frac)` 底層版／`relative_loc(obj, face, frac, offset)` 日常直接餵 loc 參數的版本 |
| 任意參數曲面（穹頂/馬鞍面/自訂曲面） | 呼叫端給 `fn(u,v)->(x,y,z)`，照網格取樣連面、可選補厚度，不用每種曲面重寫一次頂點/面索引邏輯 | `parametric_surface(name, u_res, v_res, fn, mat, smooth, solidify)` |
| 東亞式翹角曲面屋頂（中式/日式塔樓、亭子——西式人字屋頂 `make_pitched_roof()` 做不出屋簷角上揚的連續曲面） | `parametric_surface()` 的具體應用：徑向下凹+屋簷邊緣上揚+**翼角在多邊形角落額外起翹**（三段可調指數分別控制屋脊/屋簷/轉角的曲率集中程度），已實測驗證（八角亭渲染確認翹角輪廓正確，見 skill research notes） | `curved_eave_roof(name, center, sides, ridge_z, eave_r, rise, ...)` |

**多部件子總成的整體傾斜/擺位（`build_template.rigid_group_transform()`，跟下面 `rotation_pivot()` 是兩件不同的事，不要混用）**：子總成（手把、燈頭、鏡筒轉盤）需要整體傾斜/移動到最終姿態，但**不需要日後在遊戲引擎裡即時旋轉**（那才是下面 `rotation_pivot()` 的場景）——優先用 `T.rigid_group_transform(objects, pivot, rotation_deg, axis, translation)`：每個零件先用簡單、容易互相對齊的軸對齊座標建好，全部建完後對整組物件一次套用同一個旋轉+平移矩陣，物件間的相對關係保證跟建造時完全一致。全部零件共用同一個最終變換，沒有第二套公式可以互相對不上。

**可轉動零件的樞軸空物件**：日後可能需要單獨旋轉的整組零件（輪子、車門、砲塔、方向盤），組裝時用 `shape_lib.rotation_pivot(name, loc, children, parent_pivot=None, axis=None, limit_deg=None)` 在旋轉軸心建一個 EMPTY 把零件 parent 給它，之後只轉 EMPTY 本地軸即可。支援疊套（`parent_pivot`）做「轉向+自轉」複合旋轉：`SteerPivot → SpinPivot → 輪胎`，轉向轉 SteerPivot、自轉只轉 SpinPivot，兩者互不干擾——跟真實汽車轉向柱+輪軸同一套機構邏輯；同一個 host 物件上多個互相獨立的樞軸（例如相機的對焦環+光圈環）互為手足、不疊套。`axis`/`limit_deg`（純標記，不強制幾何）寫成自訂屬性，供引擎查該轉哪軸/合理角度範圍。跟 §11 GUIDES 錨點（純參考、不 parent 任何東西）是兩種用途；命名帶零件用途+旋轉軸（例如 `Wheel_FL_SpinPivot`）。匯出 GLB（`build_template.export_glb()`）時這個父子階層+`axis`/`limit_deg` 都會完整保留（已用 GLB JSON 直接解析驗證：4 輪轉向+自轉、離心車門鉸鏈、同物件雙獨立旋鈕，階層/旋轉四元數/extras 全部正確）。

**車體工作流範例（照使用者描述的步驟，Blender 5.1.2 實測驗證）**：
```
body = T.add_box("CarBody", size=(1.8, 4.2, 1.1), loc=(0, 0, 0.55))      # ① 主體量體
new_loop = SL.loop_cut(body, axis='Y', position=0.3)                     # ② 擋風玻璃分界線切一圈新邊
top = [c for c in new_loop if abs(c[2] - 1.1) < 0.01]                    # ③ 篩出這一圈最上面那排（車頂高附近）
SL.move_verts(body, top, delta=(0, 1.0, -0.5))                           # ④ 上緣往後往下移＝擋風玻璃斜角
SL.bevel_edges(body, angle_limit_deg=15.0, width=0.03, segments=3)       # ⑤ 整體去毛邊/導圓角
```
（步驟③也可以用 `select_verts_by_bounds(body, z=(1.09, 1.11))` 達到同樣效果，兩種篩選方式都可以）

**額外規則**：

4. **需要非 primitive 輪廓（車體、家電曲面外殼、瓶身、任何真實世界不是純方塊/圓柱的物體）時，優先用「量體 + `loop_cut`/`select_verts_by_bounds`/`move_verts` + `bevel_edges`」這套流程**，不要因為找不到現成 primitive、風格卡沒教，就退回方塊/圓柱直接拼接。
5. **對稱造型（絕大多數載具/家電/家具/建築正面）用 `add_mirror` 只建一半**，不要兩邊分別手算鏡射座標各建一次——手算容易做出左右不對稱的細節誤差，鏡射保證絕對對稱。
6. **需要把兩個獨立量體真正融合成一個連續表面時用 `boolean_union`，不要用 `join`**——`join` 只是把 mesh 資料合併成一份 data-block，重疊/相交處的表面拓撲完全沒有重新計算，近景/斜角一眼看得出是兩塊分開的量體硬拼在一起。
7. **多片曲面需要在漸變角度下保持視覺連續時（擋風玻璃→車頂→後窗這類三段式玻璃艙、引擎蓋→葉子板的曲面過渡），一律建成單一連續 mesh（`loop_cut`/`select_verts_by_bounds`/`move_verts` 分段塑形，或 `shape_lib.profile_loft()` 縱向 loft），禁止「N 個獨立 `add_box` 各自算旋轉角度貼上去」。獨立薄板之間沒有共享頂點、沒有曲率銜接，相鄰面法向差距夠大肉眼就讀成「拼裝」不是「連續表面」，跟座標數值對不對無關，是方法論本身的局限。車體殼體已經是單一連續 mesh 時，玻璃艙不要用獨立物件貼合，改用 `cut_window()` 直接在殼體上挖窗，窗戶幾何直接繼承殼體曲率，結構上不可能出現船帆問題。

8. **貼附在 `profile_loft()` 車身上的面板（車窗/飾條/保桿）寬度/位置不能猜固定常數，一律呼叫車身回傳的 `section_fn(y)` 查該位置真實剖面範圍。** 車身本體是 profile 算出來的、面板卻憑經驗猜一個常數，兩者真相源不一致就會出現面板比車身實際外緣寬、懸空凸出車殼的錯位——`profile_loft()` 回傳 `(obj, section_fn)` 正是為了讓兩者共用同一個真相源，不要丟掉這個回傳值只拿 obj。

### 13.11 附加構件的功能／人體工學／安全性審查（不只是「方向裝對」）

**適用範圍**：任何有高差、有開口、供人接近或使用的附加構件，光是「幾何存在、位置方向合理」不夠，還要再過一輪功能／人體工學／安全性檢查才算驗證完畢，不是查完幾何就結案。

**強制公約（Stage A 設計簡報階段，對每個「人會接觸/接近」的附加構件各答一次，寫進簡報，不是動工後才補想）**：

1. **功能性**：這個構件的存在理由，它真的做得到嗎？（陽台懸挑板要能承載站立重量的量體比例、冷氣室外機的百葉罩要真的透空能散熱不是密封裝飾、雨遮的懸挑範圍要真的覆蓋到入口動線而不是純裝飾性地掛在牆上）
2. **人體工學**：尺寸是不是抓在「給真人用」的合理區間，不是隨手填一個視覺上看起來對的數字？（欄杆/扶手高度、門把/開關的離地高度、走道淨寬——這類尺寸現實中都有標準參考值可查，不是憑感覺）
3. **安全性**：少了這個構件、或這個構件被做得不夠明顯，會不會製造出使用者一眼就能認出的安全疑慮？（任何有高差的開口邊緣——陽台、露台、屋頂平台、樓梯——沒有欄杆或矮牆本身就是明確缺陷；欄杆材質選得太透明/太接近背景色而讓人**看不出**它存在，效果上等同於這個安全構件沒有發揮作用，即使幾何上它確實在那裡——見上面 `residential.md` 提到的材質偽裝陷阱，這正是「幾何過了但功能沒過」的實例）

跟三問一樣，這輪檢查的重點在 Stage A 就先想清楚並寫進簡報，不是等 Stage C 使用者質疑了才回頭查證。

### 13.12 真實物件複刻——規劃期參考圖研究（取代舊版「建後規格化逐項評圖」）

**新流程**：規劃期（Stage A）主動做參考圖研究，把「複刻真實物件」這件事最容易出錯的環節（整體裝配關係、構型與方向語義、色調/材質）在動工前釐清；建模完成後（Stage C）維持 §11 原本的輕量評圖流程（描述所見→列問題→問使用者→一輪一個方向），**不要再對建後渲染跑本節這套結構化逐項評圖或任何大規模照評語重寫**。

**Stage A 強制公約（只適用「複刻真實存在的物件/建築/產品」；原創設計不適用）**：

1. **元件表定稿前，用參考圖核對裝配關係**：首選「正交／垂直視角」——頂視圖、正視圖、側視圖、背視圖，透視畸變最小、單一面完整配置看得最清楚（多數品牌型錄圖/維基百科條目圖/拆解評測照片會有這類角度）。**沒有正交視角可用時（找不到、或找到但品質不達標），一般照片不是只能看顏色**：挑 1–3 張角度盡量分散到接近正／側／頂的照片，仍足以核對整體裝配關係、子元件相對位置、方向語義（標線走向、字向、機構朝向）與缺件——這些判讀不受透視畸變影響，效果明顯優於純憑文字規格想像。圖到手後用 `read_image_native`（或你的 agent 平台上等價的視覺輸入工具）實際看過（不支援視覺的模型略過本條，只靠 §11 Stage A item 2 的文字規格研究），核對元件表裡的整體裝配關係、相對位置、元件是否遺漏——**尤其是「這個元件是不是嵌入/固定在主體上」這類裝配關係**，靠參考視角一眼就能看穿，不需要等建完渲染再回頭發現。**照片除了判讀構型與方向，也能提供比例／角度的粗略推估**——但推估值一律標為估計（元件表 `params[].source` 給 `estimated`），有圖面標註或官方規格時以那些覆蓋。
2. **顏色/材質/表面質感沒把握的元件，同一階段一併查清楚**：肉眼判讀參考圖的色調（深栗紅 vs 粉橘這類色相/明度差異，正交視角下比透視渲染更容易判斷），有能力的話用 `run_python_native`（或你的 agent 平台上等價的「執行一段腳本」工具）+ PIL 對參考圖做像素取樣拿到具體 RGB 數值，直接寫進元件表的材質欄位（`mat_lib` factory 的 `base`/`color` 參數），不要留到建完渲染出來才發現顏色偏了。
3. **這個階段抓到的問題直接修元件表文字，不用等 Stage B**：改一段文字描述幾乎零成本，跟建完之後要重寫 geometry.py/materials.py+重渲+再評圖的成本天差地遠——這正是視覺模型在這個任務裡該扮演的角色：花在規劃期的判讀，不是花在建後審查的判讀。
4. 角度/斜度類數值不靠這裡的視覺判讀量化——查得到真實角度就寫進 `expected_deg`，查不到就用同類產品常識合理值並註明是估計值；**建完後用 `T.assert_slope_angle(obj, local_p0, local_p1, base_dir, expected_deg, label, tol_deg=3.0)`**（`build_template.py`，§0.5）直接量世界座標數值驗證，不需要視覺、也不屬於本節的規劃期研究範疇。
5. **讀圖手段只有兩種，不得自行發明第三種**：`read_image_native`（真視覺輸入；或你的 agent 平台上等價的視覺輸入工具）與 `describe_image()`（委託視覺模型產生結構化文字描述）——尤其禁止把圖片轉成 ASCII／像素文字自己「量化判讀」（token 成本比正常讀圖貴上十倍以上、資訊量還大幅縮水）。
   - **看不到就照文字規格繼續，在簡報裡誠實記一筆**：元件表用 §11 Stage A item 2 的文字規格研究完成即可，在簡報加一句「＿＿元件本輪未能完成視覺核對（原因：＿＿），依文字規格研究建模，留待使用者確認後續是否需要」——不要為了「一定要親眼看過」拖住整個規劃階段不推進。
   - **反問確認時把這個缺口攤在使用者面前**：跟其他規劃決策一起打包問，使用者可能會說「沒差，先建」，也可能會說「這個元件很關鍵，我另外找圖給你」——這是使用者該做的取捨，不是模型自己不斷加碼嘗試就能解決的問題。

## 14. 資產復用公約（遊戲工業 modular kit 理念——中大型場景強制）

**為什麼**：遊戲環境美術的標準實踐是 modular kit——一套基礎資產 + 網格對齊 + 到處復用，靠**放置與少量變體**製造多樣性，而不是每個實例重畫（來源：World of Level Design "Modular Environment Design 101"、ScienceDirect 2021 modular architecture 研究、80.lv UE5 modular environment——一致結論：統一網格與尺寸是關鍵，復用省時且視覺一致）。LLM 逐個手寫幾何的額外害處：每份實例都是一次「重新心算旋轉/位置」的機會——§13 三處錯誤全部發生在「每個實例各算一次」的代碼路徑上；**復用=錯誤只可能发生一次，修一次全場景生效**。

**強制規則（場景 >150 物件或同類組件 ≥3 份時）**：

1. **工廠函數只建一次母版**：`make_xxx()` 建出單一母物件（或 collection），全部實例經 `obj.copy()` + `obj.data` 共享 + `bpy.context.collection.objects.link()` 放置，禁止循環體內重複呼叫 `primitive_*_add` 逐份重畫。母版幾何**在局部座標建成、原點放接地中心**，實例只給 (loc, yaw)——旋轉只在放置層發生一次，且是繞 Z 的純 yaw（最不易錯的自由度）。
   - **母版隔離一律 `hide_render=True`，禁止「高空存放」**（`add_box` 內 `transform_apply(scale=True)` 會把 location 也烘成零，見 §8 #9）。實例 `copy()` 會**繼承 hide 旗標**，放置後必須還原 `hide_render=False`。範本已內建配套：母版建完呼叫 `park_master(obj)`，放置一律走 `instance(master, name, loc, yaw_deg, scale)`——自動共享 mesh、還原旗標、只允許白名單變體（yaw/scale/loc）。
   - **`add_box()`/`add_cyl()` origin 慣例已統一**：`add_cyl()` 也呼叫 `transform_apply(scale=True)`，之後任何 host 母版不分 primitive 種類，origin 都在建完後歸零、mesh 已烘進世界座標，`instance()` 的 loc 就是最終世界座標，不需要為特定 primitive 另外心算補償值。
2. **變體白名單（保持多樣性的合法手段，僅此四種）**：材質槽替換（車身色）、uniform scale ±15%、繞 Z 旋轉、位置抖動。**禁止**變體：幾何拓撲、非 uniform scale、繞 X/Y 的實例級旋轉（那是母版設計的職責，如 §13 輪軸）。
3. **結構件零變體**：電線桿/路燈桿/號誌桿/欄杆/人孔蓋等「城市基礎設施」一律完全相同（位置旋轉外）——現實中它們就是量產件；把變體預算留給有機物（樹用 nature_lib.make_tree 多 preset/多 seed 生成 2–3 個母版 + GN scatter 的 scale/yaw 隨機化，§18）與人工物（車輛配色）。
4. **母版建完立即過 §13 斷言**再複製放置——錯誤攔截在單一份，而不是散佈 36 條斑馬線之後。
5. **SCENE_STATE 增報復用統計**：`{"assets_reused": {"zebra_stripe": 36, "streetlight": 4, ...}, "unique_geometries": N}`——unique 數遠小於物件數即證明復用成立；若某類組件 unique==count，就是退化成逐份重畫，違反本節。
6. 斑馬線條紋、路緣石、標線虛線這類**重複圖形**優先用單一母版 + 等距放置（或 array modifier），禁止每條一個独立 add_box 呼叫塊。
7. **第三條路：批次化量體（僅限「大量相同、不需要個別身分」的重複桿件）**——母版＋實例解決的是「同一份幾何放很多次」；把 N 份相同構件直接烘進**同一個 mesh**（一支 bmesh 逐件寫入頂點/面，最後每個材質出一個物件）是第三條路，物件數與每物件開銷歸零，適合帷幕牆豎框/百葉/欄杆/桁架桿這類動輒上千件、不需要個別命名/變體/逐件斷言的東西。**兩個必須遵守的細節**：① **透明材質單獨一個 mesh**——玻璃跟實體桿件混在同一個 mesh 裡，桿件內部的面會讓透明排序變成災難；② 走這條路等於放棄逐件倒角與細節密度（§10.1 的幾何/微細節軸要另外補回來），且改一個參數就要重建整個 mesh。需要個別命名、材質變體、逐件斷言的物件（路燈/招牌/車輛/家具）仍走母版＋實例，不要混用。

## 15. 美感比例公約（多重比例/構成系統——依風格與場景挑選，禁止無理由預設單一公式）

**選用理由**：黃金比例／費波那契是實測有效、保留使用的工具之一，但不再是預設值——Stage A 設計簡報必須先判斷這次適合哪一種（或哪幾種）比例／構成系統並寫出理由，再套用對應工具。

### 15.0 可選的比例/構成系統（依風格判斷，可混用；不是只能選一種）

| 系統 | 核心手法 | 適合的風格/情境（可對照 §17 風格卡） |
|---|---|---|
| **黃金比例 × 費波那契**（原主線，見 §15.1~§15.4） | 0.618/0.382 分割、費波那契收分/節奏、黃金螺旋輪廓 | 有機、流動、需要「自然生長感」的造型——侘寂/japandi、曲面產品、需要不對稱張力的構圖 |
| **對稱與均衡**（新增） | 主軸真正鏡射對稱（1:1 是刻意選擇，不是偷懶）；不對稱時用「視覺重量」判斷左右/上下是否均衡，不套公式 | 莊嚴、正式、紀念性、秩序感——古典/紀念性建築、現代主義極簡（如 Mies van der Rohe 式格柵）、正面對稱的門面/展台 |
| **簡單整數比／模矩制**（新增） | 1:2、2:3、3:4、3:5 等易讀整數比；或定一個基準模矩單位，所有尺寸取模矩的整數倍 | 理性、工業、克制的秩序感——Bauhaus/Braun Rams 式工業設計、Mid-century Modern、需要「規格化」語感的產品 |
| **對比與焦點**（新增，可疊加在任何系統上） | 刻意在尺度/材質/色彩/光線上製造一個強對比的焦點物件，其餘元素退為襯托 | 任何風格皆可疊加——尤其展示類/hero shot 構圖 |
| **留白與簡約**（新增） | 刻意保留大面積無裝飾的空間/表面，用「少」本身傳達高級感，不強求每個角落都有節奏/細節 | 日式極簡、侘寂、極簡工業設計；也呼應本專案 UI 設計哲學的 Kenya Hara 留白美學 |

**選擇順序**：命中 §17 風格觸發詞時，優先採用風格卡「形式語言」段指定的系統（§17.5 原規則不變）；沒有風格卡或風格卡未指定時，Stage A 簡報自行判斷並寫一句理由（例：「這次是溫馨咖啡廳，選黃金比例+費波那契呼應 hygge 有機感」或「這次是極簡展廳，選對稱+模矩制呼應秩序感」）。**禁止的是「沒有理由、預設套用黃金比例」，不是禁止使用黃金比例本身**——選定某個系統後，該系統要求的結果（包含對稱系統本身要求的真正 1:1）都不算違規，不要再套用舊版「禁止 50/50」的字面規則去否定一個刻意選擇的對稱設計。

### 15.1 強制流程（Stage A/B 各一步 + SCENE_STATE 回報）

1. **Stage A 設計簡報必含「比例規劃段」**：先寫**這次選用的系統（見 §15.0）與理由**，再依所選系統寫出具體數字——黃金比例系統：費波那契分段方案（例：塔身 400m 八段收分 = 156.1 + 96.5 + 59.6 + 36.9 + 22.8 + 14.1 + 8.7 + 5.4）、主次體量比、腰線/重心位置；對稱系統：對稱軸位置＋兩側質量分佈說明；模矩制：模矩單位＋各部件的模矩倍數。元件表「組合方式」段的描述也應反映所選系統的構成語言，保持整份簡報的設計語言一致（見 §11 元件表規劃）。
2. **Stage B 幾何常數依所選系統的對應工具生成**：黃金比例系統一律用 `fib_split`/`golden_series`/`nearest_fib`（§15.2 速查表）；對稱系統用鏡射建模（`bpy.ops.object.mirror` 或先建半邊再鏡射）；模矩制在 config.py 定義模矩常數，尺寸一律取整數倍。**禁止的是「沒有選定系統、隨手填一個看起來差不多的數值」**，不是禁止任何特定的數字結果。
3. **SCENE_STATE 回報比例審計**：JSON 加一個 `proportion_system` 欄位（記錄這次選了哪個系統/理由），主體關鍵比例（依系統而定）列入 JSON，並跑 `assert_proportion` 驗證是否落在規劃值附近——「跑通但比例走樣」跟「跑通但方向錯」同罪，要靠數值抓，不分用哪個系統。

### 15.2 黃金比例系統套用點速查表（選用黃金比例系統時適用；其他系統見 §15.0 手法欄）

**範本工具（assets/build_template.py，選用本系統時一律引用禁止手算）**：
`PHI`/`PHI_INV`/`FIB` 常數、`fib_split(total)` → (0.618段, 0.382段)、`golden_series(total, n)` → n 段收分序列（每段=前段×0.618，歸一化到總長）、`nearest_fib(value)` → 最接近的費波那契數、`assert_proportion(actual, target, label, tol=0.08)` → 比例斷言（超差 exit 1）。

| 設計決策 | 用法 | 工具 |
|---|---|---|
| 整體長寬高 | 兩維比取 1:1.618（橫幅）或 1:0.618（縱幅）；三維避免三邊全等或 1:1:1 | 手算常數 + assert_proportion |
| 主次體量 | 主體:次體 = 1.618:1 或 1:0.618（次體永遠是主體的 0.618 或 0.382 級，不允許 0.5） | fib_split |
| 分段結構（塔身/椅背/櫃體） | n 段收分 = golden_series；分割線放 0.382H / 0.618H，不放 0.5H | golden_series |
| 腰線 / 特徵線 / 分割線 | 高度 = 0.382×總高（低腰線，穩重）或 0.618×總高（高腰線，挺拔） | fib_split |
| 重心位置 | 視覺重心落在 0.382H（下盤穩）或 0.618H（輕盈）——避開 0.5H 的正中無聊 | fib_split |
| 細節節奏（窗格/鰭板/格柵間距） | 間距序列取費波那契數（單位 cm 或 ×10cm）：8, 13, 21, 34…；大小細節對比 = 1:0.382 | nearest_fib |
| 輪廓曲線 | 見 §15.3 | — |

### 15.3 曲線美感專則（黃金比例系統專用細則）

1. **大小曲線對比**：主輪廓用大曲率半徑的長曲線（大 C 形/S 形），細節用半徑 = 主曲線 ×0.382 或 ×0.618 的小曲線呼應——大曲線定調、小曲線點睛，兩者半徑比禁止 1:1。
2. **收放節奏**：曲線段的長度序列走費波那契（例：S 形側面線的三段弧長比 21:13:8），使「收」與「放」有自然生長感而非等分。
3. **過渡曲面**：兩體量交接處用 0.618 位置的漸變過渡（bevel/fillet 半徑也走費波那契級數：大倒角 21mm、中 13mm、小 8mm），避免生硬直角與均勻圓角兩種極端。
4. **黃金螺旋參照**：收分輪廓（塔身、花瓶、椅背曲線）可錨定黃金螺旋——每轉 90° 半徑 ×0.618，或離散版：相鄰分段半徑比 ≈0.618（`golden_series` 的收分序列直接可用）。
5. **張力來源**：黃金比例系統下優雅 ≠ 對稱無聊，允許並鼓勵非對稱平衡——主曲線偏 0.382 側、次曲線在 0.618 側呼應，形成視覺張力。（若這次選的是「對稱與均衡」系統，張力來源改用材質/色彩/細節對比取得，不強求非對稱。）
6. **bpy 落地提示**：曲線輪廓優先用 `bpy.ops.curve.primitive_bezier_curve_add` + 控制點錨定費波那契座標，再 `convert to mesh`；或 NURBS 曲面。禁止用多段直線 box 堆出「假曲線」（棱線在渲染下必現形）。

### 15.4 構圖與相機（渲染層的比例）

- 主體在畫面中的位置：黃金比例/對比焦點系統——水平/垂直偏離正中，落在 0.382 或 0.618 分割線（三分法的黃金比例精確版）；對稱系統——主體可以刻意置中，正中央本身就是這個系統要傳達的莊嚴/秩序感，不強制偏心。**選定對稱系統後，相機構圖預設就該置中，不要為了「畫面比較好看/留前景」又悄悄把 camera target 偏移掉**（構圖必須跟簡報宣告的比例系統一致；確有理由偏移時要在簡報寫明理由）——如果真的有理由要偏移，必須在 Stage A 簡報寫清楚理由，不要在沒有說明的情況下悄悄偏移。
- 相機高度：拍建築/高塔取 0.382×主體高（低機位仰視，莊嚴）；拍桌面物件取 0.618×主體高（俯角，親切）。
- DoF 對焦點：前景:背景景深比 ≈ 0.382:0.618，主體銳利區落在黃金分割深度（對稱/模矩制系統下此項為選用，非必要）。
- **`build_template.auto_frame_and_light(objects, style="product"|"dramatic")`**——`build_camera()`/`build_lights()` 原本的機位/三點燈固定絕對座標是為 ~1-2m demo 物件校準的，直接套用在遠超這個尺度的主體（例：468m 高塔）上機位形同貼著塔基站，燈光能量也差好幾個數量級，肉眼看到的「近黑曝光」只是表象。這個函式用主體實際世界包圍盒對角線 `diag` 算相機距離與三點燈位置/能量/尺寸（能量公式含 diag² 距離平方反比校正），`subject_fn()` 建完主體後呼叫一次即可，`main()` 隨後跑到 `build_camera()`/`build_lights()` 會自動讀到覆寫值，不需要呼叫端自己再算 `set_camera()` 參數或猜燈光能量。已用 0.15m/2m/468m 三種尺度（3000 倍範圍）實測驗證亮度統計完全一致。同一輪也修正了 `build_camera()` 的 `clip_end`（原本吃 Blender 預設 1000m，機位一拉遠超過這個距離主體會整個落在遠裁切面外變不可見，只剩世界背景色）。**已知限制**：只管主體本身曝光/構圖，不動天空/地面配方——細長/巨大主體用這個函式構圖後，畫面裡天空/地面占比會明顯變大，全畫面 `check_exposure()` 的 `luma_band` 可能被大量背景拉低觸發假警報，即使主體本身曝光正確清晰可見；這種情況改用 `preset_overrides` 放寬 `luma_band`，不要照抄 studio 預設的 100-170 帶。

**構圖入鏡的量化斷言**（`auto_frame_and_light()` 算完相機之後的下一步）：「主體有沒有完整入鏡、佔畫面多少比例」要用投影數字回答，不要等渲染出來肉眼猜。`T.frame_coverage(objects)` 把物件包圍盒 8 個角點投影進相機 NDC，回報 `u_range`/`v_range`/`coverage`（裁到 [0,1] 後的面積比）/`fits`/`outside`；`T.audit_framing()` 加上判準回傳問題清單（soft 版，不擋）；`T.assert_in_frame(objects, min_coverage=…, max_coverage=…, hard=True)` 是硬性關卡版（`max_coverage` 調低即表達「主體不該塞滿畫面、要留白」）。**預設排除地面/環境件**（`Ground` 物件、`Env_` 前綴、`T.mark_framing_exclude()` 標記過的）——把涵蓋整個畫面的大地面算進「主體」，每個鏡頭都會誤報主體超出畫面。呼叫時機必須在相機就位、畫幅定案之後（NDC 的 u 軸隨 aspect 縮放）；`T.main()` 在 `build_camera()`＋`setup_render()` 之後自動跑 soft 版，結果寫進 `SCENE_STATE.auto_geometry_audit.framing`。

**地面邊緣穿幫（運動場案例——已知問題，未解決，記錄現況避免重複踩坑）**：`auto_frame_and_light()` 把相機拉遠是正確的，但沒處理「拉遠後地面這塊有限大小的平面，邊緣會不會被拍到」——低仰角（接近水平視角，空拍/大型場景建立鏡頭常見）鏡頭看巨大主體時，地面平面的實際邊緣會穿幫成一條硬邊，把地面跟天空/背景切開，不會是「延伸到地平線」該有的樣子。**已嘗試三種修法，用像素取樣直接比對重渲結果，三種都證實無效**：(1) 離世界原點距離算漸層——半徑放大後漸層帶的畫面角度寬度反而縮小，壓縮到不到 2 像素；(2) `ShaderNodeLayerWeight` 掠射角漸層——方向沒錯但漸層永遠卡在「命中/沒命中地面網格」的幾何邊界正上方，一樣被壓縮到看不見；(3) `ShaderNodeCameraData` 的 `View Distance` 相機距離漸層——節點本身數值量過是合理的，但最終渲染結果完全沒有反映漸層效果，懷疑跟色調映射或渲染管線某個環節有關，尚未找到真正原因。**`build_ground()` 目前只保留地面放大到 20000x20000m 這個部分（有實際幫助，但不能單獨解決低仰角案例），漸層機制的程式碼還在但實測不生效，不要假設這個問題已經解決**。遇到同樣的穿幫問題，目前只能靠鏡頭選角迴避（拉高仰角、避免太貼近水平視角），不是這支函式能處理的——詳細除錯記錄見 `build_ground()` 自己的 docstring。

### 15.5 例外與優先級（衝突時的裁決順序）

1. 人體工學硬性尺寸（§12.5）> 任何比例系統——坐高 42cm 不會為了湊 0.618 或湊模矩改數值。
2. 真實安裝規範（§13.5）> 任何比例系統——號誌高度 4.5–5.5m 照規範，比例美感用在桿臂長度、牌面寬高比等自由維度。
3. 結構合理性 > 形式比例——承重、懸臂、連接處以工程常識為準。
4. 風格卡指定的系統（§17.5）> Stage A 自選系統 > 隨手預設黃金比例——黃金比例現在是「眾多選項之一」，不是起點。
5. 整體和諧 > 局部公式——「若局部不適合嚴格套用公式，請以整體和諧與設計合理性為優先」，這句話現在同樣適用於「為了硬套某個系統而破壞整體協調」，不是只針對黃金比例。
6. **遊戲資產風可放寬**：low-poly/toon 風格不強求任何系統的精確數值，以節奏感/識別度為目標。

## 16. BPY 編程規範（命名 × 檔案拆分 × 修改定位）

**定位**：本節核心工程原則——「規劃成物件容易單獨修改；需要修改某些東西時容易定位，無須每次重寫整個大檔」。單檔大腳本每改一處都要重新生成／覆盤整檔，思考時間與出錯率都隨檔案長度上升，本節把「改一處只碰一檔」變成強制架構。

### 16.1 場景包（scene_pkg）檔案拆分規則——任何非一次性任務強制

`copy_skill_resource_native` 取出 `assets/scene_pkg/` 七件骨架到 `.capybala/test-scripts/<task>_pkg/`，`build_template.py` 放其**上層**（凍結模組，§9.6.1）：

```
.capybala/test-scripts/
├── build_template.py      # 凍結模組（skill asset copy，不改內容）
└── <task>_pkg/            # 場景包
    ├── build.py           # 入口：組裝+渲染，唯一執行檔，幾乎不改
    ├── config.py          # 所有可調參數：TASK/PRESET/OUT_DIR/PRESET_OVERRIDES/CAMERA/PROPORTIONS/PLACEMENTS
    ├── materials.py       # build_materials() → name→Material dict，全部材質集中於此
    ├── geometry.py        # make_xxx(mats) 元件工廠：每類資產一個函數，只建母版不擺位
    ├── layout.py          # build_scene(mats)：只做 T.instance() 擺位，禁混幾何
    ├── assertions.py      # verify_scene()：§12/§13/§15 語義斷言集中於此
    ├── components.json    # §11 item 3 元件表：main() 拆解深度閘門的輸入（config.COMPONENTS_JSON）
    └── inspect.py         # 常駐場景檢視（§7.8）：按需執行、不進渲染流程、可整檔移除
```

**拆分鐵律**：
1. **依賴單向**：build → (config, materials, layout, assertions)；layout → (config, geometry)；geometry → config。禁止反向或循環 import。
2. **數值零散落**：任何尺寸/能量/座標/顏色常數只能住在 config.py 或對應工廠函數頂部具名常數——修改時 grep 常數名直達，不在 800 行代碼裡找魔法數字（PROJECT-RULES 魔法值條款的落地）。
3. **每檔頂部 KEYWORDS 註解**（PROJECT-RULES）：`# KEYWORDS: blender, bpy, material, 材質…`，讓 search_files_native 一發定位。
4. **函數職責單一**：make_xxx 只建母版（局部座標、原點=接地中心、隨建隨驗方向斷言、結尾 park_master）；layout 只擺位（T.instance + 白名單變體）；assertions 只驗證不建模。
5. **小型一次性任務**（純主體、<50 物件、確定不會迭代）可降級用單檔 build_<task>.py（§9.6.1 引用模式）；但使用者明說「之後要改」或任務是中大型場景 → 一律場景包，不賭。
6. **`config.PLACEMENTS`/`PROPORTIONS` 優先用相對錨點，不是只准填絕對座標**（見 §13.10 `shape_lib.anchor()`/`relative_loc()`，layout.py 有可執行範例）——這是本 skill 對「事後能不能改參數不用整個重來」這個問題的簡化答案（查證見 arXiv 2601.12234《Proc3D》論文，該論文用完整的「程序化緊湊圖」讓生成模型事後可調參數、編輯快 400 倍；咱們沒有那套圖形表示，但同樣的效果用「config.py 集中參數 + layout.py 用 anchor 算相對位置」這個既有架構本來就能達到大半：改 config.PROPORTIONS 裡的一個尺寸常數，重跑腳本，所有靠 `relative_loc()` 依附在那個物件上的東西自動跟著對，不用逐一手動改座標）。純孤立、不依附任何東西的物件（例如場景主體本身）才用絕對座標，這條不變。

### 16.2 命名規則（物件/材質/函數/檔名四層，全部強制）

| 層 | 規則 | 例 | 反例（禁止） |
|---|---|---|---|
| Blender 物件 | 前綴標明身分：`Mst_`=母版、`Inst_<母版>_<NN>`=實例、`Lgt_`=燈光、`Env_`=環境件；主體大件可直接語義名 | `Mst_StreetLamp`、`Inst_StreetLamp_03`、`Lgt_Sun`、`Env_Ground` | `Cube.017`、`Cylinder.004`（Blender 自動名=定位噩夢） |
| 材質 | `Mat_<用途>`；變體加後綴 `_v<N>` | `Mat_Glass`、`Mat_CarPaint_v2` | `Material.003` |
| Python 函數 | 工廠=`make_<asset>`；擺位=`place_<asset>` 或 layout 統一 `build_scene`；材質=`build_materials`；斷言=`verify_scene`/`assert_<語義>` | `make_traffic_light`、`assert_axis_perp` | `do_stuff`、`build2` |
| 檔名 | 場景包=`<task>_pkg/`（snake_case）；單檔模式=`build_<task>.py`；探測=`probe_<topic>.py` | `pudong_tower_pkg/` | `final_v3_REAL.py` |

**為什麼前綴制重要**：SCENE_STATE JSON 回傳幾百個物件時，`Inst_StreetLamp_*` 一篩就是全部路燈；斷言腳本用前綴抓族群（母版入鏡檢查=抓 `Mst_*` 且 hide_render=False）；describe_image 發現「左邊第二盞路燈歪了」時，Inst 序號與 layout 擺位序一一對照，直接定位到 config.PLACEMENTS 那一行。

**單字母變數名禁區**：本 skill 已建立的模組別名慣例是 `T`=build_template、`M`=mat_lib（mat_lib.py 檔頭明文規定）；`detail_lib` 原本**沒有**明訂別名，場景腳本自行即興取名可能與比例常數撞名（其中一個被靜默覆蓋）。**現況**：detail_lib.py 現在明訂別名 `DL`（`import detail_lib as DL`），避免未來場景各自即興發明。**規則**：(1) 每個 lib 模組檔頭明訂的別名保留給對應模組，不得挪用做其他變數名——目前完整清單（新增 lib 都要記得回來補這裡）：`T`=build_template、`M`=mat_lib、`DL`=detail_lib、`SL`=shape_lib、`GN`=geonodes_lib、`RL`=road_lib、`BL`=building_lib、`N`=nature_lib、`TV`=triview_lib、`TB`=triview_build、`TL`=triview_loft、`BP`=blueprint_lib、`CL`=component_lib（`component_measure` 是 CLI 入口、不被其他模組 import，故不佔別名、`SP`=space_lib）；(2) 比例/尺寸類常數一律用完整語意名（`STORE_D`/`ROOM_DEPTH`/`WALL_H`），不用裸單字母——就算這次沒撞到已知別名，裸單字母在幾百行的 geometry.py/layout.py 裡也容易在別的地方意外重複賦值。

### 16.3 修改定位表（Stage C 迭代時的唯一入口——先查表再動手，禁止重寫）

| 使用者說… | 只改這個檔 | 改什麼 |
|---|---|---|
| 「太暗/太亮/氣氛不對」 | `config.py` | `PRESET` 換配方 或 `PRESET_OVERRIDES` 微調（±20%，§10.2#2） |
| 「鏡頭太遠/角度不對/背景太多」 | `config.py` | `CAMERA` dict（loc/target/lens/fstop） |
| 「顏色/質感不對」 | `materials.py` | 對應 `Mat_*` 的顏色/粗糙度/金屬度參數 |
| 「那個物件形狀不對」 | `geometry.py` | 對應 `make_xxx()` 單一函數 |
| 「位置/朝向/數量不對」 | `config.py` 的 `PLACEMENTS`（改資料）；複雜擺位邏輯才動 `layout.py` | 加/刪/改一行 dict |
| 「比例不美/分段怪」 | `config.py` 的 `PROPORTIONS` + geometry 內 `T.golden_series` 呼叫 | §15 工具重生成，禁手填 |
| 「渲染太慢想先預覽」 | 不改檔 | 執行時加 `-- --calib`（960×540/48spp） |
| 「cel 展示卡太暗/太亮/明暗界線位置怪」 | `geometry.py`/`layout.py` 的 `T.setup_cel_studio()` 呼叫參數 | `sun_energy`（明暗水位）、`sun_offset_deg`（界線落在哪，不可設 0）、`bg_color`、`fill`/`fill_scale`；相機角度改 `azimuth_deg`/`elevation_deg`/`ortho_margin` |
| 「斷言誤報/要加新檢查」 | `assertions.py` | `verify_scene()` 加一條，用 T.assert_* 工具 |
| 「拆解深度不足被閘門擋下」 | `components.json`（遞迴補拆解層級；意義上真的拆不動才在**最深那個元件**寫 `depth_exempt` 理由）；門檻本身改 `config.py` 的 `COMPONENTS_JSON`／環境變數 `BLENDER_COMPONENTS_JSON` | 見 §11 Stage A item 3／§16.9.5 規則 7 |
| 「樹假/植栽太疏太密/地形不對」 | `config.py`（preset/density/seed 參數）；換樹種才動 `geometry.py` 的 make_tree 呼叫 | nature_lib 參數（§18）：樹種 preset、seed、light、scatter density |
| 「照這幾張三視圖/工程圖把東西複刻出來」 | `config.py`（ROI/已知尺寸/spec_mm）；輪廓不準才回頭調影像端參數；放樣參數（`--stations`/`--a-view`/`--corner-radius-mm`）與斷面圓角來源看 `triview_loft_report.json` 的 `loft` 段 | 見 §16.9：ROI 與已知長度住 config、輪廓住 triview_calib.json、斷面圓角住 calib 的 `annotated_dims_mm`、幾何常數住 geometry |
| 「平面圖的標註位置/編號不對」或「想多標/少標某些線」 | 元件編號與框位改元件 JSON（`components`）；標註密度/字級改 `render_blueprint` 的 `font_px`/`label_minor`/`major_min_mm`；切分邏輯才動 `blueprint_lib.py` 的 `segments_from_contour`/`build_annotations` | 見 §16.9.3：元件框住元件 JSON、特徵切分住 `segments_from_contour`、版面與避讓住 `build_annotations` |
| 「元件表的框位/參數不對」或「模型跟元件表對不上」 | CP1 改元件 JSON（`components` 的 `bbox_mm`/`params`/`objects` 樣式）；CP2 改 `component_lib compare` 的容差（`pos_tol_mm`/`size_tol_mm`/`ang_tol_deg`）；量測端換 `--unit-to-mm` | 見 §16.9.4：規劃值住元件 JSON、實測值住 `components_measured`、容差住 compare 參數 |
| 「改了一輪，之前對的地方又被改壞了」或「已驗證區被動到」 | 不改檔；跑 `component_lib diff --old <上一版> --new <本版> [--scope ...]`，看 `locked_changed`／`out_of_scope` 計數 | 見 §16.9.5：凍結住元件 JSON 的 `locked`+`verified_at`、本輪範圍住 `--scope`、變更理由住 `change_note` |
| 「顏色/材質/貼合厚度跟照片不符」 | 元件 JSON 的 `appearance`（`material`／`flat_axis`+`max_extent_mm`／`evidence`）＋ `materials.py` 對應 `Mat_*` | 見 §16.9.5 規則 5：外觀規格住元件 JSON、實際材質住 materials.py |
| 「同一條弧被切成十幾段編號」或「圖上短邊/折返一大堆」 | 不改檔；調 `render_blueprint` 的 `fit_tol_mm`（先擬合後編號），必要時 `major_min_mm` | 見 §16.9.3：擬合住 `segments_from_contour` 的 `fit_tol_mm` |
| 「附件浮空／沒貼在宿主表面上」 | 不改檔 | 跑 `audit_attachment_contact()`（或看 `SCENE_STATE.auto_geometry_audit.attachment_contact` 定位是哪幾件）；擺位高度改用該處實際表面（圓柱 `sqrt(R²−y²)`），刻意保留的間距用 `mark_side_attached(..., stand_off=)` 宣告 | 見 §13.9：浮空是擺位公式與母版安裝面的問題，不是材質/燈光 |
| 「機構/總成件被判穿模或被判浮空」（卡鉗×碟盤、輪圈×輪胎、羊角×輪轂這類同軸嵌合件） | 不改幾何：建構這類零件當下呼叫 `mark_joint_attached(obj, host=...)`（第三類安裝方式；`host` 必填），固定嵌合配對再加 `mark_assembly_mate(a, b)` | 穿模：`audit_interpenetration(..., mode="bvh")`（AABB 對同軸嵌合件天生全命中，實測一台底盤 102 筆全為正確裝配）；浮空：看 `auto_geometry_audit.joint_attachment`（接頭件）與 `.attachment_contact`（貼附件）——實測 334 件標記只有 3 件宣告宿主、卻回報 310 筆浮空 | 見 §13.9：AABB 是篩子不是結論；「標記」要配「宣告宿主」 |
| 「太空場景太黑/星點太少/銀河帶糊成一片灰/銀河帶被一條直線切斷/日盤不在畫面裡」 | `config.py`（`PRESET="space"`）＋ subject_fn 內的 `space_lib` 參數 | 星點密度/尺寸 → `make_star_points(count=, size_range=, strength=)`；銀河帶 → `make_star_map(band_glow=, band_center_deg="auto", band_width_deg=)`（0.06/14 會洗成均勻灰，用 0.035/7）；**帶被切斷 → `band_center_deg="auto"`（依相機自動取景）＋ `T.set_ground_void()`（地面不入鏡）＋ 移除主體自帶的水平底座（`T.audit_horizon_surfaces()` 指名是哪個物件）**；日盤 → `make_sun_disc(angular_diameter_deg=0.85, distance=)` ＋ 相機 `sun_elev/azim` 同步；**光暈 → 太空版已取消，不要呼叫 `request_lens_flare()`** | 見 §10.5：曝光帶別改能量，改「主體可見像素比」；成片方格子先查銀河帶明暗塊是不是方塊遮罩、星點球細分是不是 <2；帶被切斷先跑 `SP.audit_band_framing()` 看是 blocking（地平線切斷）還是 note（框邊裁切），再看 `SCENE_STATE.horizon_audit`（像素層亮邊）與 `auto_geometry_audit.horizon_surfaces`（幾何層掠射面）；**底座改暗改霧面無效**（掠射 Fresnel） |

**迭代流程（Stage C 修改輪強制）**：查表 → 只 patch 目標檔的目標段落（apply_patch_native）→ 重跑 build.py（CALIB 先行）→ 重評。**禁止**為了改一盞燈的能量重新生成整個場景包；**禁止**把修改散進多個檔（同一次修改只應觸及表上一格）。

### 16.4 模板庫（預先準備，隨 skill 保存）

- **`assets/build_template.py`**——凍結引擎層：曝光配方/LUMA 守衛/方向數學/黃金比例工具/母版實例/§13 斷言工具/渲染管線，函式清單見 §0.5。`set_camera()` 支援 `cam_type`/`ortho_scale`（ORTHO 相機）。`auto_frame_and_light()`（§15.4）預設 ORTHO+`azimuth_deg=-125.0`（相機在主體 -Y 前方，符合 §11/§16.1「正面朝 -Y」約定），依主體包圍盒自動算構圖+三點燈，任意尺度通用。`export_glb(filepath, objects=None)`——匯出 GLB 供遊戲引擎/動畫軟體使用，保留父子階層（`shape_lib.rotation_pivot()` 樞軸/未來 ARMATURE 骨架），固定帶 `export_extras=True`（實測抓到真坑：這個參數預設 `False`，不開的話樞軸的 `axis`/`limit_deg` 自訂屬性完全不會進 GLB 的 `extras` 欄位，節點階層仍然正確、但引擎查不到旋轉軸/角度限制中介資料）。`main(..., export_glb_path=)` 可在存檔後自動呼叫，之前 pipeline 只存 `.blend`+渲染 PNG，從沒有真正匯出過可攜格式。
- **`assets/scene_pkg/`**——場景包七件骨架 ＋ 元件表（§16.1），每檔含完整 docstring 說明職責與規則，取出即用；demo 內容（Mst_DemoBlock×1 實例）跑通全管線後再逐檔替換成任務內容。
- **`assets/mat_lib.py` / `assets/detail_lib.py`**——材質 factory ×14 與細節標準件 ×8（§17.3/§17.4，凍結模組）；產品類任務與 scene_pkg 一併取出。
- **`assets/nature_lib.py`**——自然資產 ×5 函數（§18，凍結模組）：Sapling 樹 / ANT 地形 / 純 bpy 地形退路 / GN 散布 / nature_report；含植栽或地形的場景必取。（§13.7/§17，markdown 知識資產，read_file_native（或你的 agent 平台上等價的讀檔工具）按需讀取，不出現在場景包）。
- **`assets/space_lib.py`**——太空／軌道場景 ×7 函數（§10.5，凍結模組）：日盤／真幾何星點／程序化銀河帶星空圖／世界貼圖接線／報告／selftest；含規則與**掛勾時序**（星空必須走 `request_world_hook()`）。**假地平線的兩道審查在 `build_template.py`**（不在這支）：`audit_horizon_surfaces()`（渲染前、幾何層）與 `audit_horizon_line()`（渲染後、像素層），`PRESET=="space"` 時 `main()` 自動跑。含太空場景或真空敘事的任務必取。
- **`assets/find_blender.ps1`**——路徑解析（§0）。
- 骨架的 demo 場景本身就是冒煙測試：新機器/新版本 Blender 先跑一次 scene_pkg 原樣（CALIB），通過才開始改——把「環境壞了」與「我寫錯了」分開診斷。

### 16.5 與其他章節的關係

- §9.6（腳本組織）管「怎麼寫得快」（模板引用、以跑代審）；本節管「怎麼改得快」（拆分、命名、定位）。單檔模式=§9.6.1；場景包=本節，中大型/需迭代任務的預設。
- §13/§14 的斷言與母版規則在場景包裡有了**固定住址**：斷言住 assertions.py、母版住 geometry.py、實例住 layout.py——檢查「有沒有照公約做」變成「有沒有填對檔案」。
- §11 Stage B 流程引用順序更新：路徑解析 → 取 build_template.py + scene_pkg 骨架 → 填 config → 填 materials/geometry/layout/assertions → CALIB → 正式渲染。
- 本節（16.1-16.5）管「一個任務內部」怎麼拆檔減少重寫；§16.6 把同一個原則延伸到「同一次對話累積的多個獨立設計任務」，且要求成果可攜——兩者是同一個工程原則在不同範圍的應用，不是兩套規則。

### 16.6 跨任務資產庫（多物件累積 → 組合 Demo 工作流）

這是 §16.1「場景包拆分」的自然延伸：把「減少重寫」的範圍從單一任務擴大到**同一次對話累積的多個獨立設計任務**（例如先設計貨車、公車、轎車、交通號誌、馬路元件，最後組合成一個 DEMO），成果要求**可攜**（複製到別的專案還能用），不只這次對話有效。

**目錄慣例**：

```
.capybala/
├── test-scripts/              # 既有：各任務 scene_pkg（過程檔案，迭代用）
├── artifacts/                 # 既有：各任務渲染輸出
└── asset_library/             # 新增：跨任務持久資產庫（整個 workspace 共用，不屬於任一任務）
    ├── manifest.json          # 索引：name/blend_path/object_names/dims_m/created_at
    ├── truck.blend
    ├── bus.blend
    ├── sedan.blend
    ├── stop_sign.blend
    └── road_straight.blend
```

**兩支函式（`build_template.py`）**：

| 函式 | 時機 | 效果 |
|---|---|---|
| `save_object_asset(objs, name, library_dir=".capybala/asset_library")` | 一個物件（貨車/公車/號誌…）設計完成、CALIB/§13 語義斷言都通過之後 | 把 objs（單一物件或清單）連同其材質/mesh 資料寫成獨立可攜的 `<name>.blend`（不是整個場景的 `save_as_mainfile()`），並更新 manifest |
| `append_object_asset(name, library_dir=..., loc=, rot_z=)` | 組合 Demo 階段 | 從資產庫把先前存的物件 append 回目前場景，自動平移到 `loc`（已接地）、繞 Z 軸旋轉 `rot_z`（單位度，同 `instance()` 公約） |

實測（Blender 5.1.2）：完整存→讀往返驗證，讀回時用**全新、乾淨的 Blender 行程**（模擬「以後在別的專案/別的對話繼續用」，不是同一個 session 裡的記憶體殘留）——材質、多物件群組關係、世界座標（含旋轉後的包圍盒中心/接地面）全部正確；append 完接 `detail_lib.join_into()` 合併多物件 asset → `park_master()`/`instance()` 走既有母版復用流程，全鏈路驗證通過。

**工作流範例（照使用者描述的場景）**：

1. 「設計一台貨車」——走正常 Stage A→C 流程，開自己的 `truck_pkg/`（§16.1）建好 `Mst_Truck_Cab`/`Mst_Truck_Bed`，CALIB/斷言過 → `T.save_object_asset([cab, bed], "truck")`。
2. 「再設計一台公車」「再設計一台轎車」「設計交通號誌」「設計馬路元件」——每個都是**獨立**的 Stage A→C 週期（各自的比例/材質/風格可以完全不同），完成後各自 `save_object_asset(...)`。這幾步**不需要**共用同一個 scene_pkg，各自開自己的 `<task>_pkg/` 即可——資產庫本來就是為了打破「一個場景包只能裝一種東西」的限制。
3. 「組合成馬路 DEMO」——新開 `road_demo_pkg`，`geometry.py`/`layout.py` 改用 `T.append_object_asset("truck", loc=…)`/`append_object_asset("bus", loc=…)`/… 逐一取回先前設計好的物件放置，**不重新設計、不重新寫幾何**——這正是「減少重寫」延伸到跨任務範圍的具體實現。同款車要放好幾輛時，`append_object_asset` 只呼叫一次拿到母版，其餘用 `join_into` 併成單一物件後 `park_master`+`instance()` 複製，不要每個位置各自 append 一次（會重複佔用 mesh data，違反 §14 母版=1 原則）。
4. 「以後複製到別處繼續用」——把整個 `.capybala/asset_library/` 資料夾複製到別的 workspace/專案，`append_object_asset(..., library_dir=<新路徑>)` 就能取用，不依賴這次對話或原本的 workspace 存活。

**規則**：

1. **只有「設計完成、通過驗證」的物件才進資產庫**——半成品/還在反覆修改的不要存，資產庫是定稿版本的集合，不是中間存檔（中間迭代仍走既有的 `.capybala/test-scripts/<task>_pkg/`，跟 §16.1 的關係不變）。
2. **命名一律用語意化英文小寫底線**（`truck`/`stop_sign`/`road_straight`），不要用任務代號或流水號——`append_object_asset()` 呼叫端要能顧名思義，manifest 也才好讀。
3. **`manifest.json` 是唯一真相源**，不要在別處（例如某個場景包的 `config.py`）平行維護第二份資產清單——需要列出資產庫現有哪些物件時讀 `manifest.json`，不要 `os.listdir()` 猜檔名（存檔時檔名固定是 `<name>.blend`，但 manifest 才有 dims/物件數這些猜不出來的中繼資料）。
4. **append 既有 `.blend` 一律用「物件名快照差集」辨識，不要相信回傳清單**——`bpy.data.libraries.load()` 的 `data_from`/`data_to` 清單只在 `with` 區塊內有效，區塊結束後才去讀它**不是 API 契約保證**的行為（底盤→內裝接續案例回報「回報成功、物件一件都沒進來」）。正確寫法：先 `before = set(bpy.data.objects.keys())`，`with ... as (data_from, data_to): data_to.objects = data_from.objects`，再 `imported = [bpy.data.objects[n] for n in sorted(set(bpy.data.objects.keys()) - before)]`，且**必須斷言 `imported` 非空**才回報成功。`append_object_asset()` 已內建這道檢查（實測 2026-09-14，Blender 5.1：區塊後讀 `data_to.objects`／`data_from.objects` 目前仍拿得到物件，但那是實作現況、不是契約，所以照上面的寫法走）。要 append **整個既有場景**（不只資產庫裡的單一物件）時，`bpy.ops.wm.append(filepath=..., directory=..., filename=...)` 的 `directory` 必須指到檔內那一層（`<x.blend>/Object`）——少一層會直接 raise `nothing indicated`（實測），不會靜默成功。

### 16.7 街區/城市尺度：兩階段分區生成

**跟 §16.1 scene_pkg 的差別**：scene_pkg 拆分解決的是「一棟建築內部」的檔案組織；本節解決**再大一級的尺度**——一整個街區/城市，由幾十到幾百個地塊組成，每個地塊是住宅/商業/公園/道路/河道等不同用途。這種尺度如果直接套 scene_pkg 的 geometry.py/layout.py 兩件式，會變成一個巨大的 if/elif 分支，「這格要放什麼」跟「這格具體怎麼建」的邏輯全部糾纏在一起，改一處常常要重新理解整段。

**兩階段模式**：

1. **第一階段：純分區分類，不建任何幾何**——遍歷整個網格（例如 `N×N` 格，每格 `T` 公尺），只根據格子座標（行列索引落在哪個區間）判定這格的**用途分類**（`kind`：lot/road/river/bridge/park/civic/plaza/promenade…），存進一份純資料清單（`[{"column":,"row":,"type":,"center":[x,y]},...]`）。這一步完全不呼叫任何建模函式，只做分類判斷——道路網、河道、公園/市政/廣場等特殊地塊的位置全部在這一步一次決定，之後不再更動。
2. **第二階段：照分類清單逐格生成幾何**——遍歷第一階段產出的分類清單，`kind=='lot'` 的格子再依「這格落在城市的哪個大區域」（例如邊緣→透天厝、中心→高樓、沿街→店面）決定要呼叫哪個 `make_xxx()` 工廠；`kind=='road'`/`'river'`/`'park'` 等各自對應固定的建造邏輯。

**這個拆分對應的是查證過的業界作法**：CGA shape grammar（ESRI CityEngine 的建築生成語言）就是「先分割量體規劃、逐步細化」的正式版——本節是它的簡化實作，不是我們自己發明的做法，是一個已經被大量城市/建築生成引擎驗證過的正確方向。

**規則**：

1. **分類結果務必匯出成獨立 JSON**（例如 `<task>_layout.json`：grid 尺寸、cell_size、種子、每格的 column/row/type/center），不要只留在腳本內部的記憶體變數裡——這份 JSON 是這個街區的「規劃書」，事後要調整某個地塊的用途（例如「把這格從住宅改公園」）可以先改 JSON 再重新驅動生成，不用回頭改一大段建模判斷式；也方便另一個工具/另一次對話讀取查詢「這格是什麼」而不用重新解析整個腳本。
2. **分區判斷邏輯（第一階段）跟地塊生成邏輯（第二階段）務必是兩個獨立迴圈**，不要合併成一個迴圈裡又判斷分區又建幾何——分開之後，「城市規劃改了」（改分區規則）跟「這棟房子想長更好看」（改生成工廠）是兩個互不干擾的修改，各自只碰一段程式碼。
3. **每個地塊物件命名 + 自訂屬性雙重記錄分類**（例如物件名 `TILE_<col>_<row> | <type>`，同時掛 `obj['Type']`/`obj['Grid_X']`/`obj['Grid_Y']` 自訂屬性）——這樣不管是看 Outliner 物件名還是用 `execute_blender_code` 查詢自訂屬性，都能反查任一格的分類，不用對照外部 JSON。
4. **城市/街區尺度的第二台攝影機建議走正上方俯視「規劃圖」（非 3/4 鳥瞰）**：`camera.rotation_euler=(0,0,0)`、位置正上方、ORTHO——這是都市計畫/建築的標準交付物「總平面圖」，跟 §10.3 已經確立的「hero 3/4 鳥瞰」是互補的兩種用途，不是重複；城市/街區尺度任務兩者都給，單一建築/產品尺度通常只需要 hero view。

### 16.8 室內/房間尺度

室內場景（客廳/臥室/辦公室這類「一個房間內部」尺度）之前沒有專屬技法段——`styles/interior/` 只有材質/比例風格卡（scandinavian/japandi-wabisabi/midcentury-modern），沒有**房間結構本身怎麼搭**的技法。以下三點是新確認的技法，跟 §16.1 scene_pkg 的檔案拆分規則並存（房間結構複雜時一樣照場景包六件式拆）。

1. **可拆牆娃娃屋構圖（多視角室內展示的標準做法）**：牆面/天花板一律建成**真實存在的物件**（不要為了「方便看到室內」就乾脆不建某面牆——那樣 GLB/`.blend` 檔案就永久缺這面牆，日後想從另一個角度看會發現牆是真的不存在，不是鏡頭選擇問題），構圖時對每一台攝影機**分別**設定哪些牆/天花板 `hide_render=True`：俯瞰全局構圖通常隱藏面向鏡頭的兩面牆+天花板（露出室內配置一次看全），室內視平線構圖則把牆面/天花板/掛畫全部 `hide_render=False`（貼近真實眼睛在室內看到的樣子，缺牆反而露餡）。每次切換攝影機前用一段明確的 `wall.hide_render=False/True` 陳述式切換，不要用「乾脆不建這面牆」規避——那是犧牲了模型的完整性換取單一視角方便，之後任何想要的第二種構圖都補不回來。
2. **窗外背景用 `visible_camera=False`，不要真的建一個完整戶外場景**：窗玻璃是穿透材質，鏡頭直接穿過去看到的東西還是需要存在——但不需要花力氣建一整片可信的戶外環境，只要建幾個簡化的色塊/模糊量體（一片色板代表遠方天空/牆面、幾顆壓扁的橢球代表模糊的遠樹），把這些背景物件的 `obj.visible_camera=False`（Cycles per-object 光線可見度開關，`Object.visible_camera`/`visible_glossy`/`visible_transmission`/`visible_shadow` 同一族 API，本 skill 目前只有這裡用到，來源見案例中 `area()` 燈光用 `visible_glossy=False`/`visible_transmission=False` 避免燈具本身在反光/折射面上露出光斑）。這樣鏡頭直接看不到這些背景物件本身，但它們的顏色/光線**仍然會透過窗玻璃的 Transmission 折射/反射進畫面**（`mat_lib.make_glass()` 現有的 Transmission=1 配方即可，不需要新材質）——玻璃窗看出去有內容，但建模成本只是幾個色塊，不是重建一整個房子外部。
3. **窗簾/披毯這類軟性懸垂布料，直接用 `shape_lib.parametric_surface()`（§13.10）**，不要拿多片平面拼接（同 §13.10 規則 7 的連續曲面原則，布料版）：窗簾的 `fn(u,v)` 疊加兩個不同頻率的 sin 波（大波=主要垂墜折痕、小波=細碎皺褶）算出每個網格點的 y 偏移；懸垂披毯的 `fn(u,v)` 用分段公式——`t` 小於某個門檻時 z 維持平整（布料還貼在座面上），超過門檻後 z 隨 t 線性下墜（布料垂下座椅邊緣），再疊加一個小 sin 波做垂墜皺褶。兩者都是「先寫好 fn(u,v) 的數學式，再交給 `parametric_surface()` 網格化+可選 `solidify` 補布料厚度」，跟屋頂翹角是同一套機制、不同的 fn——這正是 `parametric_surface()` 設計成通用工具而不是專屬屋頂函式的原因。

### 16.9 三視圖複刻工作流（triview——把雕塑問題轉成量測問題）

**完整內容已搬到 `assets/examples/triview_reconstruction.md`（2026-09-13，原節 430 行、
超過 SKILL.md 當時篇幅四分之一，是這一輪瘦身的最大抽出對象，內容未刪減）**——核心洞見、
六階段分工、`triview_lib`/`triview_build`/`triview_loft` 三端檔案分工、7 條強制規則、
8 項實測陷阱表、適用邊界與實測誤差數字，全部在那份檔案裡，**動工前一律先讀那份，不要憑
本節的摘要就動手**。

**一句話摘要**：AI 建模最致命的三個弱點是「盲寫座標、看不到中途、對連續曲面沒手感」；三視圖
把**發明**這個環節抽掉，剩下的是「校準 → 萃取 → 放樣 → 驗證」，正好是量測問題不是雕塑問題。
**啟動門檻（要不要用、用哪一等級、能證到什麼程度）見 §16.9.0**——這是先決條件，不是讀完
本節才決定，任何複刻任務動工前都要先過那一關。

以下 §16.9.0–§16.9.5 保留原本的小節結構當**索引**，每節只留最關鍵的判準/一句話結論，
完整操作細節（含 CLI、schema、七條狀態管理規則的完整表格）一律在上述檔案裡找。

### 16.9.0 啟動判準（使用門檻的唯一來源）

**本節是「要不要用參考圖、誰去找、用哪一種、能證到什麼程度、找不到怎麼辦」的唯一判準，且只在兩個時機被引用**：規劃初期（§11 Stage A，還沒動工、決定要不要找圖）與校正期（§11 Stage C，已建模但被使用者指出大量元件位置/大小/方向錯誤）。其餘章節不重述、也不指向本節。

**一句話總則**：有真實對應物 → 圖優先於猜；原創設計 → 風格／比例系統優先於圖；圖的等級決定它能證什麼，不能跨級使用——**高階圖缺位時低階圖仍然可用，只是精度下降、必須標明是估計**——沒有正交圖時，普通照片仍能讀對構型與方向，並提供比例／角度的粗略推估；**有推估永遠優於憑空亂畫**（完全沒有圖就開工，等於整套尺寸全靠猜，比拿照片推估更差）。

**步驟一 · 任務性質（決定「要不要去找圖」）**

| 性質 | 判別 | 動作 |
|---|---|---|
| **A 複刻真實存在的物件** | 有名字、有官方來源，或使用者明說「照這個做」 | **強制找圖**：文字規格（§11 Stage A item 2）＋正交圖（存在時）＋照片推估（無正交圖時 1–3 張）＋色調判讀 |
| **B 原創設計** | 沒有可對應的真實型號，或使用者說「自由發揮」 | **不找尺度圖、不進 triview**；走風格卡（§17）＋比例系統（§15）＋`proportions_lib`。參考圖只能當**造型語彙**看——原創設計沒有可對應的真實尺寸，比例一律走 §15 比例系統與 §17 風格卡。**但元件表與拆解深度照樣要過**——原創設計仍必須產出 `components.json` 並通過 `component_lib depth`（不需 calib／三視圖、預設 6 級，§11 Stage A item 3）；「不進 triview」不等於「不受任何檢查」，這正是它過去唯一一條寫成 MUST 卻沒有閘門的規則 |
| **C 使用者主動提供圖** | 對話裡有附檔/連結，不分等級 | 先讀（§11 Stage A item 4），再依步驟二判它能幹嘛 |
| **D 既有場景加件／改件** | 不涉及主體複刻（「在那張桌上加個杯子」） | **不啟動** triview 流程 |

**步驟二 · 素材等級（決定「這張圖能證什麼」）**

| 等級 | 素材 | 可證範圍 | 禁止 |
|---|---|---|---|
| **L1** | 正交尺寸圖：真正交視圖＋標註數字、官方工程圖 | triview 全流程（階段 0–4 校準／輪廓／成形／拓樸 ＋ 階段 6 閉環驗證）；標註尺寸寫成硬性斷言（`assert_spec`）。階段 5 曲面與細節由既有 lib 接手，不屬本流程 | — |
| **L2** | 透視照：產品照／宣傳照／評測照 | 色調、材質、裝配關係、**構型與方向語義**（標線／機構的走向、字體朝向、子元件相對位置、大區塊結構）、缺件核對（§13.12）、**比例的粗略推估** | 推估值一律標 `estimated`，**不得與圖面標註／官方規格同級引用**；同主體有後者時一律以它覆蓋 |
| **L3** | 3D 參考檔（`.obj`/`.fbx`/`.gltf`/`.stl`…） | 只量整體比例／階層（§19.4，量完即丟） | **幾何不得進最終輸出** |
| **L4** | 只有官方規格數字 | 規格驅動建模：數字寫成 `assert_spec` 硬點，造型用 `shape_lib.profile_loft()` 剖面控制點描述 | **不假裝做過 triview** |

**L1 缺位時 L2 的角色**：正交圖找不到時不等於只能憑規格想像——挑 1–3 張角度分散的照片，
逐張判讀構型/方向/比例（不受透視畸變影響，因為讀的是「有沒有、朝哪邊、誰在誰旁邊」不是
長度），推估值標 `estimated`，有權威值時一律讓位。完整說明與實測案例見檔案。

**步驟三 · 找圖責任**：A 類使用者沒給圖 → AI 負責主動搜（2–3 輪就停）；C 類使用者已給直接
用；完全找不到 → 照文字規格建模+在簡報明講「屬造型判讀」；圖讀不出來 → 兩次工具嘗試不成
就停，不得無限糾結重試。細節見檔案。

**步驟四 · 建模對象分流**：重複件/陣列/規則格狀 → 既有流程（`building_lib` 等），不需要
三視圖；對稱/有主軸/輪廓可放樣（手機/家電/車/船/瓶罐/家具）→ 有 L1 走 triview、無 L1 走
規格驅動+L2 照片補判讀；有機造型/布料/植栽/地形 → 既有流程（`nature_lib` 等）。

**順序**：一（要不要找）→ 二（能證什麼）→ 三（誰去找）→ 四（成形路線）。門檻只在這一節；
其他章節要改判準時回來改這裡，不得就地新增第二份。

### 16.9.1 本工作流**不取代**既有 Stage A（最高優先約束）

三視圖解決的只有一件事：**把「這個物件的空間關係、位置、大小」從猜測變成量測**，不解決
「這是什麼、由哪些零件組成、該給什麼材質」——那仍是 §11 Stage A 的職責，**必須保留，一點
都不能少**（資料蒐集、元件拆解、反問確認、既有 lib 體系）。正確接法是**兩者相乘**：Stage A
的資料蒐集+元件拆解永遠先做，有 L1 三視圖時六階段提供每個零件的確切尺寸，無 L1 時走規格
驅動建模——元件表照樣逐項存在，差別只在尺寸欄位是量測值還是官方數字。「元件表 × 三視圖
對賬」（§16.9.4）跟「迭代狀態管理」（§16.9.5）是這條相乘關係的落地機制。完整推導見檔案。

### 16.9.2 兩條成形路線怎麼選（外殼 vs 放樣）

視覺外殼 `triview_build`（兩輪廓布林交集，兩視圖就夠成形，但填平輪廓內側凹陷）vs 站點放樣
`triview_loft`（沿主軸逐站掃描，天生全四邊拓撲零非流形，凹陷同樣填平但會回報
`max_span_runs` 讓你看到）。兩者共用同一套「回渲 → mm 量測 → 閉環 IoU」驗證。完整比較表、
已知代價數字、與 §19.4「3D 參考檔研究」的關係見檔案。

### 16.9.3 標註平面圖（blueprint_lib——人可以指著它說話的那張圖）

`assets/blueprint_lib.py` 把量測輪廓畫回原圖，打上元件編號（`A-1`…，來自 Stage A 元件表）
與特徵編號（`F1`…，輪廓切成直線/曲線/轉折/短邊/折返，先做折線擬合併掉掃描階梯雜訊再發
編號，見「迭代狀態管理」規則 6）——填一個「Stage A 元件表是純文字、看不出哪個元件在哪」的
洞，讓使用者能用「`A-3` 位置不對」回報而不必描述座標。輸出 SVG/PNG/JSON。完整編號規則、
內縮斷言判準、五項已知限制見檔案。

### 16.9.4 元件表 × 三視圖 對賬（`component_lib` 比、`component_measure` 量——兩個檢查點）

Stage A 元件表與三視圖之間的雙向對賬：**CP1**（規劃期，元件表完成後、Stage B 動工前）用
`component_lib.py` 的 `audit_coverage()`/`audit_params()`/`audit_appearance()` 四項檢查
（覆蓋／參數／外觀／版本史）任一有問題即 exit 1，不得帶著問題進 Stage B；**CP2**（建模後）
用 `component_measure.py`（Blender headless）先量、`component_lib compare` 後比，逐項比對
尺寸/位置/方向並提出建議修正常數。資料契約 schema `components/2`、CLI 用法、七條強制規則、
四項已知限制，全部在檔案裡——尤其**開口類元件（USB孔/喇叭網孔等）要標 `void`+`host`，不要
硬量 AABB**（實測 iPhone 案例：誤指到連接器舌片，報出假的 2.5mm 尺寸偏差），這條最容易漏。

### 16.9.5 迭代狀態管理（`component_lib`——「改壞已驗證區」的煞車）

七條規則、全部有可執行檢查：①已驗證區凍結（`locked`+`verified_at`）②單一真相源+版本史
（禁止 `_v2`/`_v3` 平行檔）③衝突強制停損（`conflicts`/`resolved_by`，沒裁決即 exit 1）
④一輪鎖一個元件群（`diff --scope`）⑤外觀也要有規格與依據（`appearance`+必填 `evidence`）
⑥先擬合後編號 ⑦元件表拆解深度（三視圖流程 level<4、原創設計 level<6 即擋下）。**優先序
（規則 3 的裁決依據）**：圖面標註 > 量測輪廓 > 推算 > 估計，圖面標註與量測衝突且無法用
第二獨立來源裁決時**停下來問使用者一次**，不是自己選一個。完整表格、CLI、凍結生命週期見
檔案。

## 17. 設計師風格庫（Designer Style Library——「一句話風格」的落地系統）

**定位**：使用者一句「索尼味的數碼相機」「安藤忠雄風的小教堂」，AI 讀風格卡後應能**不靠 generate_image/describe_image 就還原該風格 80%**——卡片精確到色票 hex、比例常數、mat_lib 材質參數、detail_lib 細節件清單。這比圖像描述工具更可靠（圖像只能讀回「深色金屬感」，卡片能給出 `make_anodized(color=hex_to_linear('#141416'), roughness=0.42)`）。

### 17.1 目錄與載入路由（主 skill 只放目錄，卡片按需載入）

```
assets/styles/
├── _INDEX.md                  # 總目錄：觸發詞路由表 + 使用流程（Stage A 必讀）
├── _TEMPLATE.md               # 風格卡欄位定義（新增風格照此格式）
├── architecture/              # 建築：ando-tadao / mies-van-der-rohe / zaha-hadid / kuma-kengo
├── interior/                  # 室內：scandinavian / japandi-wabisabi / midcentury-modern
├── genre/                     # 通用風格類型：low-poly-cute / anime-cel-daylight（日間 3 渲 2）
└── industrial/                # 工業設計：sony / apple-ive / braun-rams / retro-future-80s / leica-classic
```

**路由規則**：使用者話語命中 `_INDEX.md` 觸發詞 → read_file_native（或你的 agent 平台上等價的讀檔工具）讀該風格卡 → 設計簡報的比例/色票/材質段直接引用卡片數值。多風格混搭：主卡為骨、副卡只借單項（色票或材質）。卡片不存在：照 `_TEMPLATE.md` 現場建卡（web search 2-3 輪佐證，憑記憶條目標 (unverified)），存回 skill assets 復用。

**預設路由（使用者沒指定風格時）**：場景主題是**日式街道/街景/和風街區** → 一律 `genre/anime-cel-daylight.md`（日間 3 渲 2），不要退回寫實 PBR。（**夜景/霓虹風格卡 `genre/anime-neon-tokyo.md` 已於 2026-09-13 下架重做**——使用者實測夜景成品不達標，決策是先把白天做好；目前沒有夜景卡可路由，使用者明確要夜景時照 `_TEMPLATE.md` 現場建卡或明說尚未支援，不要用寫實夜色充數。）反之，非日式的一般場景**不要**自動套動畫風——預設路由只對日式場景生效。

### 17.2 風格卡欄位契約（每張卡必含，格式見 _TEMPLATE.md）

★必填六段：一句話定位 / 理念（帶出處）/ **形式語言**（比例常數+圓角策略+線條+對稱性——直接映射 config.PROPORTIONS）/ **色票**（hex + 線性 RGB；**起點參考非配額**——占比與忌避色只在「無其他依據」時當提示，使用者指定色或參考圖優先）/ **材質映射表**（部位→mat_lib factory→參數，可直接貼進 materials.py）/ **細節特徵**（detail_lib 函數+參數）/ 落地 checklist（Stage B 動工前逐條核對）。
☆選填三段：燈光渲染建議（PRESET 微調）/ 代表作（建模參考錨點）/ Prompt 模板（**不再是 Stage A 預設流程的一部分**，見 §11 元件表規劃；只在使用者明確要求先看一張 2D 概念示意圖時才用得上，非必填）。

### 17.3 材質模擬現況與 lib 化（回答「材質是怎麼做的」）

**現況（Round 9 實測）**：材質在場景包 materials.py 手写節點鏈——Principled BSDF 參數 + Noise/Wave/Voronoi 程序化紋理 + ColorRamp 混色 + Bump 凹凸，全程序化無外部貼圖檔（headless 安全、無缺檔風險）。皮革=高頻 Noise 凹凸+天然色差；拉絲銀=Noise 擾動 Roughness 近似各向異性；鍍膜=Transmission+高 Specular。

**lib 化（強制）**：24 種常用材質抽成 `assets/mat_lib.py` factory，每個任務不再重寫同一套節點鏈（P6：單一真相源，修正全域生效）。場景包 materials.py 只剩兩職責：① import mat_lib 呼叫 factory 並命名 Mat_*；② 定義本任務專屬材質。**風格卡的材質映射表直接指向 factory 名**，「換風格」=換參數呼叫，不動節點代碼。

**24 種完整清單**：`make_metal`/`make_brushed_metal`/`make_anodized`（金屬族）、`make_leather`（`pebble_scale>0` 疊加 Voronoi 反轉 bump 做顆粒皮革，籃球/球類用 110-120）/`make_fabric`（皮革織物）、`make_wood`/`make_concrete`/`make_stone`（木石混凝土）、`make_glass`/`make_coated_glass`/`make_frosted_glass`（玻璃族）、`make_plastic`/`make_rubber`/`make_paint`/`make_carbon_fiber`（塑膠複合材料）、`make_emissive`（自發光）、`make_water`/`make_grass`/`make_soil`/`make_asphalt`（環境地景）、`make_brick`/`make_ceramic`（建築材質）、`make_paving`（鋸切石材鋪面：方正板塊+凹陷接縫，廣場/人行道/前庭/停車場；Object 座標直連、不套名稱抖動以保持網格正交）/`make_light_shaft`（光束/光柱：Emission×Transparent、徑向衰減×高度淡出，探照燈/紀念光柱用）。`make_brick` 的 specular 預設值查證自 physicallybased.info 真實量測數據（見檔頭「真實材質量測參考」）。

**非寫實著色（3 渲 2／賽璐璐）另加**：`make_cel()`（EEVEE + Diffuse→ShaderToRGB→CONSTANT ColorRamp 的三階平塗，色票一比一還原，基礎路線）／`make_cel_advanced()`（**進階漸層 cel，預設路線**——LINEAR 4-stop ramp 做「硬陰影邊界 + 受光帶內漸層」+ AO 接觸陰影 + LayerWeight Facing 冷色邊緣光；ZZZ/原神級畫面的著色核心，見 `styles/genre/anime-cel-daylight.md`）／`make_toon()`（Toon BSDF，Cycles 備援路線）／`make_cel_outline(name, color, mode)`（**背面法線材質**，`mode='cull'` 配反轉法線的外殼、`'backfacing'` 走 Geometry.Backfacing 全透明正面，兩條實測都通；配 `build_template.make_outline_shell`）／`cel_shadow_color(base, hue_shift, sat_gain, val_gain)`（**設計過的陰影色**——HSV 位移：明度壓低＋飽和度依明度補強＋色相往冷側跑，近灰自動給冷紫；《罪惡裝備》的 SSS Texture 與《藍色協議》CEDEC2021 做法的簡化版）。這幾支是本檔**唯一的非寫實路線**，**禁止與程序化寫實紋理系列（concrete/stone/wood/leather/brushed_metal/add_procedural_wear）混用**——雜訊/凹凸/磨損會直接摧毀色塊。搭配的色調映射、描邊與後製見 `build_template.set_view_transform()`／`setup_inverse_hull()`／`setup_selective_outline()`／`setup_freestyle()`／`setup_anime_post()`。

**Blender 5.1 socket 實名**（probe 實測，寫 shader 參數對照）：`Coat Weight`/`Coat Roughness`（=4.x Clearcoat）、`Sheen Weight`、`Emission Color`/`Emission Strength`、`Transmission Weight`、`Specular IOR Level`、`Subsurface Scale`、`Thin Film IOR`（新功能：薄膜干涉=鍍膜彩虹感，相機鏡片可試）。未知 socket 一律走 `set_socket()` 候選清單，WARNING 不中斷。

**座標空間**：`mat_lib.py` 帶程序化紋理的 factory 一律用 **Object 座標**（`_obj_coords(nt, name)`，接 `ShaderNodeTexCoord` 的 Object 輸出），不留空 Vector 輸入——空輸入預設走 Generated 座標（把包圍盒正規化），同一個 `grain_scale` 在 0.6m 書桌跟 8m 地板上會產生完全不同的紋理密度（地板被拉伸成假斑馬紋）。Object 座標下 `grain_scale` 在任何大小的物件上代表同一個實際紋理密度。新建材質 factory 務必沿用這個慣例。

**紋理/顏色變化**：座標空間修好後，使用者又指出「同一個 factory 套用在不同物件（地板/桌面/門）上，紋理跟顏色卻千篇一律，像同一塊木板複製貼上」——程序化節點本身完全決定性，同輸入必產生同輸出，光修座標空間不會讓「不同物件」的紋理彼此不同。`_obj_coords()` 現在額外用 `ShaderNodeMapping` 對 Object 座標疊加一個依材質**名稱**（`name` 參數，例如 `"Mat_Floor"` vs `"Mat_DeskTop"`）決定性推導的隨機平移+三軸旋轉：平移解決 Noise/Voronoi 的相位變化，**旋轉才是關鍵**——單純平移對 Wave 這種週期性條紋幾乎沒有視覺效果（人眼看不出「相位不同」的條紋差異），旋轉才會真正改變條紋/雲紋的方向，一眼就能分辨不同材質實例（實測校準：先只做平移，肉眼確認完全沒用，才加上旋轉）。`make_wood`/`make_leather`/`make_stone`/`make_concrete`/`make_fabric` 這五個「天然材質」另外用 `_jitter_color()` 對色票做 ±5% 決定性微調（同一批「同色」原木/石材本來就有天然深淺差異）；`make_metal`/`make_plastic`/`make_paint` 等「量產材質」刻意不做顏色微調——同一批工廠塗裝的塑膠/烤漆件本來就該是同一個顏色。**決定性種子一律從 `name` 用 `zlib.crc32` 推導，不能用內建 `hash()`**——那個受 `PYTHONHASHSEED` 影響，CALIB 跟正式渲染是兩次獨立行程，用內建 hash 會讓同一個材質在兩次渲染裡長得不一樣。

**金屬粗糙度務必依表面積/顯眼度分級（相機案例實測抓到）**：`make_metal()`/`make_brushed_metal()` 這類金屬 factory，**不要整台主體所有金屬件共用同一個 roughness**——實測反例：一台相機的頂蓋/底板（大面積平面）跟快門盤/背帶環（小飾件）全部套 `roughness=0.15`，渲染出來大平面在棚拍 AREA 燈下變成一整片鏡子，直射光源被鏡面反射成大片燒白色帶，同一個材質在不同面積的表面上視覺後果天差地遠。經驗法則：**表面積越大/越平坦，roughness 給越高**（0.28-0.35，緞面/拉絲感）；**表面積小/曲面/裝飾性強的飾件才用低 roughness**（0.10-0.20，接近鏡面）——真實產品的機身大面板跟裝飾小飾件幾乎從不共用同一種拋光工藝，「材質定位是拋光鉻」不代表整台主體每一寸金屬都給同一個粗糙度數字。詳見 `mat_lib.make_metal()` docstring。

**大面積表面的現成紋理選項（§7.7 精神延伸，非強制）**：座標空間修正後，程序化材質在任何尺寸物件上都能有正確、一致的紋理密度，但程序化紋理終究是「數學算出來的規律圖案」，跟真實照片掃描的材質相比，在大面積、近距離特寫鏡頭（例如地板/牆面占滿畫面下半部的鏡頭）下還是可能不夠自然。§7.7 已經開放「家具/道具可依任務判斷抓現成，不強制」——**同樣的判斷邏輯可以延伸到大面積表面材質**：`asset_fetch_lib.py` 目前只用 Poly Haven 的 `hdris`/`models` 分類，其實 Poly Haven 也有 `textures` 分類（真實掃描的 PBR 貼圖，CC0 免署名），`polyhaven_search(query, "textures")` 已經可以查到。**但這條路線需要額外的 UV 展開支援**——`add_box()`/`add_cyl()` 這類基礎建模函式建出來的物件沒有跑過任何 UV **展開**（`smart_project`/`unwrap`/`cube_project` 這類供貼圖/紋理映射用的操作），真的要套用真實掃描貼圖，要先幫這些基礎建模函式加上這類 UV 展開，這是比座標空間修正更大的架構改動，**目前先不做**，僅記錄在此供之後評估——沒有實際踩到「程序化紋理在特寫鏡頭下明顯不夠好」的坑之前，不建議為了這個去動 UV 這塊。（釐清用詞範圍：上面「完全不依賴 UV」的舊說法不夠精確——`road_lib.py`（§0.5）的 `make_road_curve()` 把帶 bevel_object 的曲線轉成 mesh 後，Blender **會**自動產生一組 UV，`add_lane_markings()` 也真的在用這組 UV 的 U 軸驅動車道線材質；但那是「曲線轉 mesh 的副產物 UV」，用途是程序化 shader 數學計算，跟這裡討論的「幫貼真實掃描貼圖展開 UV」是完全不同的兩件事，兩者不衝突，只是容易被籠統的「有沒有 UV」這句話混為一談。）

### 17.4 細節地板（Round 9「轉盤應有凹凸線條」的制度化）

任何「可轉/可按/可握/可讀刻度」的組件，光滑素面 = 不合格（塑膠感）。`assets/detail_lib.py` 標準件：
- **knurl_ring**（滾花環）：轉盤/鈕/對焦環側面，齒數 34/55/89（費波那契，§15.2 細節節奏）；
- **dial_grooves**（頂面刻痕）：放射刻度溝，每 3 條加粗=節奏對比；
- **grip_strip**（凸點陣列）：握把防滑、speaker 孔陣列（Braun/Apple 簽名視覺）；
- **ridge_lines**（平行脊線）：橡膠握紋/散熱鰭/通風槽——`axis` 是脊線本身延伸的方向，`space_axis`是脊線群彼此排開的方向，兩者互相獨立、必須分開指定。**平放的水平面**（車頂機組散熱鰭這類，脊線跟排開方向都在同一個水平面上）**一定要明確傳 `space_axis`**——只傳 `axis='X'` 沒傳 `space_axis` 時會退回舊預設「沿 X 延伸、沿 Z 排開」（那是給握把這種垂直圓柱設計的），脊線會疊在同一個 (x,y) 沿 Z 往上長，不是貼合表面的散熱鰭；
- **seam_ring**（接縫環）：裝配分模線，真實感來源；`center=` 同 knurl_ring（不給＝自動取宿主軸心——2026-09-14 內裝案例：舊版環心寫死世界原點，零件不在原點時整圈接縫留在原點）；
- **make_screw**（十字螺絲）：外露螺絲是機械誠實風格（Sony/80s）的識別件；
- **make_text**（3D 文字）：LOGO/刻度刻字標準路徑（text_add→extrude→convert mesh→CENTER 對齊）；
- **arc_text_ring**（弧線刻字）：逐字元沿圓柱面排列並自轉貼合曲率，鏡筒品牌刻字（如 "ARGENT OPTICS"）、光圈環數字這類「文字必須跟著曲面走」的場合用它，不要整段文字硬貼平面；`center=` 同 knurl_ring（不給＝自動取宿主軸心——舊版字元整圈繞世界原點，內裝案例的儀表刻度數字就是這個坑）。
- **`shape_lib.flat_decal`**（自由造型平面貼花）：車身閃電/隊標這類不規則輪廓，`from_pydata` 直接建單面 N-gon，不是文字也不是矩形貼片能表達的形狀（見 §13.10）。
- **`detail_lib.apply_image_decal`**（真實圖片貼花）＋**`asset_fetch_lib.fetch_reference_image`**（下載並驗證參考圖/貼花來源圖）：複刻真實商標/圖標優先於手刻幾何走這條路——上網抓一張清晰、免費、透明背景的官方標誌圖直接貼上去，形狀 100% 準確（見「品牌標誌／圖標貼花」小節）。

**細節件不另立物件**：join_into 併入宿主母版（§14 母版=1 原則，實例數不炸）。**密度審計**：audit_detail_density ≥25%（build 階段統計，不足 exit 1——「跑通但平淡」要靠數值抓，與 LUMA 守衛同構）。

### 17.5 與其他章節的關係

- Stage A（§11）：命中觸發詞必讀風格卡，簡報的比例段/材質段引用卡片數值，色票段以卡片為**起點**（使用者指定色/參考圖優先），元件表的組合方式描述引用卡片「形式語言」段。
- Stage B：config.PROPORTIONS ← 卡片形式語言；materials.py ← 卡片材質映射表（mat_lib）；geometry.py ← 卡片細節特徵（detail_lib）；assertions.py ← 卡片落地 checklist 轉成斷言（細節密度/特徵件存在性）。
- SCENE_STATE 增報 `style_card`（引用卡名）——風格引用可追溯即可；**色彩配額不做審計**（那是審美判斷，交給人眼與參考圖）。
- §15 黃金比例與風格卡衝突時：卡片形式語言優先（風格是使用者指定的設計意圖），但節奏類（間距/齒數/分段）仍走費波那契。
- 風格卡是**活文件**：實戰發現卡片參數與渲染結果不符 → 回填卡片（單一真相源，同 §9.3.5 skill asset 修正規則）。

## 18. 自然資產庫 nature_lib.py（植栽 × 地形 × 散布——Round 13 補洞）

漂亮的樹來自 Sapling Tree Gen 參數化 / Geometry Nodes 散布 / Poly Haven 現成掃描資產（§7.7），不是手刻圓柱+球冠充數。

**資產**：`assets/nature_lib.py`（凍結模組，與 mat_lib/detail_lib 同層）。Blender 5.1.2 headless 實測（Round 13）：selftest PASS（0.47s；realize 驗證 polys 9025→21271 證明散布生效）+ 端到端渲染 PASS（960×540/48spp 3.2s、LUMA mean=95.1、describe_image 確認地形與遠景散布樹入鏡）。

**一次性安裝**（Sapling/ANT 在 5.1 是 extension，非內建 addon；未安裝時 ensure_extensions() raise 含指引，不 silent）：

```powershell
& $blender --background --python-expr "import bpy; bpy.context.preferences.system.use_online_access=True; bpy.ops.wm.save_userpref()"
& $blender --command extension sync
& $blender --command extension install blender_org.sapling_tree_gen
& $blender --command extension install blender_org.antlandscape
```

**API 速查**：

| 函數 | 用途 | 關鍵點 |
|---|---|---|
| `make_tree(preset, seed, scale, light=True, bark_mat=None, leaf_mat=None)` | Sapling 參數化樹 → 單一 joined MESH 母版 | 9 官方樹種（TREE_PRESETS）；**散布必用 light=True**（原生 weeping_willow 6 萬+ polys/棵 → 輕量化 816~2086）；hero 近景單棵才 light=False；事實 #15：樹幹幾何藏在 Skin modifier，lib 已內建 join 前 apply + light 模式 Decimate 到 6000 面；材質用 bark_mat/leaf_mat 在 join 前逐物件掛（join 後分槽會抓錯 base） |
| `make_terrain(preset, size, subdivisions)` | ANT Landscape 地形 | 31 種官方 preset（mountain/canyon/dunes/volcano…） |
| `make_terrain_pure_bpy(size, subdivisions, amplitude)` | 零 extension 退路 | mathutils.noise.hetero_terrain 直寫頂點，129×129 實測 0.07s；ANT 不可用時保底 |
| `flatten_pad(terrain, center, pad_z, pad_radius, blend_radius)` | 地形上挖平一塊建築基地、向外平滑過渡回原始地形，避免建築懸空/陷入地形 | `pad_radius` 內拉平到 `pad_z`，`pad_radius`~`+blend_radius` 線性內插過渡，之外不動；地形建好、建築動工前呼叫 |
| `make_rock(seed, scale, deform, rough, detail)` | Rock Generator 石頭 | 事實 #14：extension 必須用 `bpy.ops.preferences.addon_enable()` 啟用，`addon_utils.enable()` 啟用後呼叫仍會失敗；補「石頭」這個環境元素的洞 |
| `scatter_on_surface(terrain, instances, density, seed, realize=False)` | GN 散布（instance 形態） | **生產 realize 必須 False**（事實 #9：realize 大場景 → 4.8GB Malloc null 崩潰）；≥2 物種自動走 Collection+PickInstance；回傳 (mod, gn, dist) 供事後調參 |
| `nature_report()` | SCENE_STATE 附加段 | 樹/地形/石頭/散布統計（polys、density、seed）——R051 數值 ground truth |

**強制規則**（nature_lib 檔頭 15 條 5.1 實測事實，違反任一 = 崩潰或靜默失敗）：
1. 生產散布 `realize=False`（instance 形態 Cycles 原生渲染、零 depsgraph 展開）；只在「實例數 × 單棵 polys < 50 萬」的驗證場景才允許 realize=True（lib 內建預算檢查）。
2. 散布源母版**不可** `hide_render=True`（事實 #13：CollectionInfo 渲染評估跳過它 → 散布空）——改「遠處停放」（loc x=300+ 相機視窗外）。**這是 §14 hide_render 公約的唯一例外。**
3. 一個宿主物件只掛**一個**散布 modifier（事實 #11：第二個的 GroupInput 收到前一個的 instance 雲 → DistributePointsOnFaces 失效 → 0 幾何）。
4. GN 節點組輸出必須 JoinGeometry 合併宿主+instance（事實 #12，lib 已內建；手寫 GN 散布時照抄）。
5. 樹種選擇：闊葉（weeping_willow/japanese_maple/white_birch…）vs 針葉（douglas_fir/small_pine）依氣候帶與場景風格；同一場景 2–3 種 preset × 不同 seed 輪換（§14 有機物變體）。
6. `make_rock` 是 `bpy.ops.preferences.addon_enable()`，**不是** `addon_utils.enable()`——事實 #14，跟 Sapling/ANT 的啟用方式不同，別憑另兩個的經驗套用。
7. 樹幹幾何在 Skin modifier 裡（事實 #15）：任何 join/導出 treemesh 前必先 `modifier_apply(SKIN)`，否則樹幹整棵消失只剩葉子（Round 14b probe 實測：未 apply 時 object data 0 面、評估後 108,148 面）。`make_tree` 已內建；繞過 lib 手動處理 Sapling 產物時照抄。

## 19. 外部資產抓取（asset_fetch_lib.py）與 Extension 安裝授權閘門（強制）

**背景**：§7.7 要求 HDRI／自然元素一律抓現成或程序化生成，本節是落地的技術路由 + 一次性安裝的使用者授權流程。家具/道具已改為預設手建，但 `asset_fetch_lib.py` 的家具抓取功能仍保留，本節技術路由對「判斷後決定要抓」的情境同樣適用。

### 19.1 `asset_fetch_lib.py` API 速查（對 Poly Haven 公開 API 實測）

| 函數 | 用途 | 關鍵點 |
|---|---|---|
| `polyhaven_search(query, asset_type, limit)` | 找資產 id | 本地端關鍵字過濾（API 本身不支援全文搜尋）；`asset_type="hdris"\|"models"\|"textures"` |
| `fetch_hdri(asset_id, resolution)` | 抓 HDRI 套進 World | 直接改 `world.node_tree` 的 Background 節點；實測套用後 LUMA mean=122（真的在打光，不是黑貼圖） |
| `fetch_polyhaven_model(asset_id, resolution)` | 抓模型/家具 append 進場景 | `bpy.data.libraries.load(link=False)`；實測 `ArmChair_01` 附完整幾何 |

**實測關鍵事實**：
1. `api.polyhaven.com` 會 403 擋掉 Python `urllib` 預設的 User-Agent（`Python-urllib/x.y`），必須自帶瀏覽器風格 UA header——lib 已內建 `_UA_HEADERS`，手寫其他 HTTP 呼叫打這個 API 時要記得帶上。
2. Poly Haven 全站 CC0、零金鑰——**不需要**§19.2 的授權閘門（沒有安裝任何東西，純 HTTP 下載+讀檔），跟下面 Sapling/ANT/Rock Generator 的 extension 安裝是兩回事，不要混為一談。
3. Poly Haven 的 "models" 分類真的有家具（categories 含 "furniture"），不是只有材質/HDRI——`polyhaven_search("chair", "models")` 這類查詢是合法且有效的路線。
4. **只抓 .blend 檔本身，材質會全空**：模型內部貼圖路徑是相對於 .blend 自己所在資料夾的 `textures/xxx.jpg`，只下載 .blend 會在渲染時噴「Image file ... does not exist」（幾何正常、材質消失，實測踩過）。`/files/{id}` 回應裡 `blend→{res}→blend→include` 這個 map 就是完整的「相對路徑→下載網址」清單，`fetch_polyhaven_model()` 已內建自動一併抓取並放到正確相對位置——手寫其他下載邏輯（不透過這個函數）時務必比照處理。

### 19.2 Extension 安裝授權閘門（Sapling / ANT Landscape / Rock Generator 共用）

**強制規則**：這三個 extension（§18 nature_lib.py 依賴）需要連網一次性安裝。**第一次要用到任何一個、且這個工作區還沒問過使用者時，必須先在對話中詢問一次，取得同意才安裝**，之後同一個工作區永不重問：

1. 檢查工作區授權快取：`.capybala/blender-extensions-approved.json` 是否存在。
   - 存在 → 已授權過，直接跳到步驟 3。
   - 不存在 → 繼續步驟 2。
2. **在對話中明確詢問使用者一次**（範例措辭，依實際任務調整）：「這個任務會用到 Blender 官方擴充套件平台上的免費工具（Sapling Tree Gen 生成樹、ANT Landscape 生成地形、Rock Generator 生成石頭），需要連網下載安裝一次，之後這個工作區不會再問。要現在安裝嗎？」——得到明確同意才進行下一步；使用者拒絕就退回 primitives 手搭（品質較差但不需要安裝任何東西，§7.7 的「禁止」是品質建議，不是在使用者明確拒絕安裝時也要硬闖）。
3. 使用者同意後執行安裝（§18 已列過的指令，三個一起裝，一次授權涵蓋全部）：
   ```powershell
   & $blender --background --python-expr "import bpy; bpy.context.preferences.system.use_online_access=True; bpy.ops.wm.save_userpref()"
   & $blender --command extension sync
   & $blender --command extension install blender_org.sapling_tree_gen
   & $blender --command extension install blender_org.antlandscape
   & $blender --command extension install blender_org.extra_mesh_objects
   ```
4. 安裝成功後寫入授權快取（`write_file_native`，或你的 agent 平台上等價的寫檔工具，記錄同意時間，供之後除錯用）：
   ```json
   {"approved": true, "approvedAt": "<ISO 時間戳>", "extensions": ["sapling_tree_gen", "antlandscape", "extra_mesh_objects"]}
   ```
5. 之後任何任務、任何 session，只要這個工作區的 `.capybala/blender-extensions-approved.json` 存在，就直接呼叫 `nature_lib.py` 的函數，**不再詢問**——這個快取檔的定位跟 §0 的 `blender-path.txt` 一樣：問一次、記住、永久複用。

### 19.3 調研過但不推薦的外掛（記錄結論，避免之後重新調研一輪）

- **Blendkit（原 BlenderKit，2026 改名）**：免費方案的模型下載條款模糊不清（官方 FAQ 未明確保證家具類模型在免費方案內，材質/筆刷確定免費但模型不確定），且整個產品的設計就是「內嵌在 3D 檢視窗裡的 App Store」，靠滑鼠拖放操作——這份 skill 已確認「本工具組無滑鼠/鍵盤注入工具」（§6），沒有可行的無頭腳本操作路徑。**不推薦安裝。**
- **Poly Haven 官方 addon**（Asset Browser 整合）：官方公開 API 已經證實可以直接無頭抓取（§19.1），官方 addon 主要價值是「在 GUI 裡用滑鼠瀏覽」，對這份 skill 的無頭優先架構沒有額外幫助，反而多一個安裝步驟。**不推薦安裝，直接用 `asset_fetch_lib.py`。**
- 若使用者之後有新的外掛需求，比照本節格式記錄調研結論（推薦或不推薦都要記，附查證日期），不要每次任務都重新調研一輪。

### 19.4 3D 參考檔研究（RAP007——研究比例/結構，禁止直接用於輸出）

**定位**：跟 §19.1 的「抓現成、直接用進最終輸出」是兩件事——這節對應核心 harness 規則 **RAP007**（`src/shared/agent-v2-harness.ts`，全域規則、不只這份 skill）：即使是任務主體本身，也可以抓一個真實世界的參考（照片/藍圖/現成 3D 模型）純粹拿來研究比例/尺寸/結構，但**絕對不能把參考檔的幾何本身帶進最終輸出**——最終交付還是要用這份 skill 自己的工具（`shape_lib`/`add_box`/profile-loft 等）從零建出來，只是建的時候心裡有底。

**工具**：`asset_fetch_lib.analyze_reference_model(filepath)`——匯入任意常見格式的參考檔，量完尺寸立刻把匯入物件從場景移除，只回傳文字/數字摘要（`{source_file, format, part_count, overall:{dims_m}, parts:[{name, dims_m, center_m, material, vert_count}]}`）。這個「量完就刪」不是建議，是函式本身強制執行的——呼叫端物理上拿不到殘留的參考幾何，RAP007 的界線不是靠自律遵守，是工具設計上就不給機會犯規。

**支援格式**（Blender 5.1.2 實測內建、不需要裝 extension）：`.obj` `.fbx` `.gltf`/`.glb` `.stl` `.ply` `.usd`/`.usda`/`.usdc`/`.usdz` `.abc`。`.dae`（Collada）沒有內建 importer，需要另外裝 extension，走一輪 §19.2 授權閘門。

**為什麼不是「找一種 AI 最容易直接讀的原始格式」**：每種格式都有各自的問題——OBJ 是純文字但稍微複雜的模型就是幾千行頂點座標，直接讀原始內容會塞爆 context；glTF(.gltf) 是 JSON 讀得到場景階層，但真正的頂點/索引資料通常在另外的 base64/外部 .bin，JSON 本身看不到幾何；FBX 是複雜二進位格式，幾乎不可能當文字直接讀；STL 只有三角網格，沒有物件命名/階層，語意最貧乏。與其要求呼叫端猜「這次的參考檔能不能直接讀」，統一交給 Blender 內建 importer 解析、只回傳量出來的數字最穩妥。

**座標軸警告**（實測發現）：OBJ 等格式傳統上是 Y-up 慣例，Blender importer 預設自動轉成 Z-up——回傳的 `dims_m`/`center_m` 一律是 Blender 世界座標（Z=高），不是參考檔原始作者標記的軸序，不要假設 `dims_m[1]` 就是原檔案裡的「高」。

**用法**：Stage A 設計簡報階段，若決定要對主體做參考研究，先呼叫這支函式拿到真實比例摘要，簡報裡明講「已研究 XX 參考檔，學到 XX 比例/結構」——跟現有「web search 真實尺寸引用 CarsGuide/Wikipedia」是同一個精神，只是這次的研究對象是 3D 檔而不是 2D 規格頁。

**場景包整合**（§16.1）：geometry.py `import nature_lib` 生成樹/地形母版；layout.py 做擺位與 scatter 呼叫；config.py 存 preset/density/seed 常數；SCENE_STATE 加 `nature_report()`。「樹假/太疏/地形不對」照 §16.3 定位表改 config，不重寫幾何。
